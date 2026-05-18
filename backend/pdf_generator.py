"""PDF报告生成器 - 使用ReportLab生成PDF文件"""

import io
import base64
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from PIL import Image

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


REPORTS_DIR = Path("D:/Project/test/sec/backend/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# 注册中文字体
try:
    pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/simhei.ttf'))
    DEFAULT_FONT = 'SimHei'
except Exception:
    DEFAULT_FONT = 'Helvetica'

PRIMARY_COLOR = HexColor("#4a90d9")

# 中英文映射 - 用于显示
CLASS_NAME_CN = {
    "Aortic enlargement": "主动脉扩大",
    "Cardiomegaly": "心脏扩大",
    "Enlarged PA": "肺动脉增宽"
}


def make_style(name, parent='Normal', **kwargs):
    """创建使用中文字体的样式"""
    base = kwargs.pop('parent', None)
    if base:
        p = ParagraphStyle(name, parent=base, fontName=DEFAULT_FONT, **kwargs)
    else:
        p = ParagraphStyle(name, fontName=DEFAULT_FONT, **kwargs)
    return p


def format_paragraph_text(text: str) -> List[str]:
    """将文本分割成适合PDF显示的段落列表"""
    if not text:
        return []

    paragraphs = []
    # 先按换行分割
    lines = re.split(r'[\n\r]+', text)

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 处理**加粗** - ReportLab用<b>
        line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)

        # 处理列表项（- 开头）
        if line.startswith('- '):
            line = '- ' + line[2:]

        # 移除无法显示的字符（emoji、特殊符号等）
        # 只保留中文、英文、数字、常用标点
        line = re.sub(r'[\U00010000-\U0010FFFF]', '', line)  # 移除emoji
        line = re.sub(r'[\u2600-\u2B55]', '', line)  # 移除其他符号

        if line:
            paragraphs.append(line)

    return paragraphs


def create_pdf_report(
    report_id: str,
    detections: List[Dict],
    ai_report: Dict[str, str],
    user_info: Dict = None,
    original_image_b64: str = None,
    annotated_image_b64: str = None
) -> str:
    """Create PDF report file."""
    # 默认空字典
    if user_info is None:
        user_info = {}

    pdf_path = REPORTS_DIR / f"{report_id}.pdf"

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )

    styles = getSampleStyleSheet()
    story = []

    # 标题样式
    title_style = make_style('CustomTitle', parent=styles['Heading1'],
        fontSize=24, textColor=PRIMARY_COLOR, spaceAfter=20)
    story.append(Paragraph("胸部X光智能分析报告", title_style))
    story.append(Spacer(1, 10*mm))

    # 基础样式
    normal_style = make_style('ChineseNormal', parent=styles['Normal'])
    heading2_style = make_style('ChineseH2', parent=styles['Heading2'])
    heading3_style = make_style('ChineseH3', parent=styles['Heading3'])

    info_style = make_style('InfoStyle', parent=styles['Normal'])
    timestamp = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")

    # 个人信息部分
    story.append(Paragraph("患者信息", heading2_style))
    story.append(Spacer(1, 3*mm))

    gender_text = "男" if user_info.get('gender') == 'male' else ("女" if user_info.get('gender') == 'female' else "未填写")

    patient_info = [
        f"姓名: {user_info.get('name') or '未填写'}",
        f"年龄: {user_info.get('age') or '未填写'}",
        f"性别: {gender_text}",
        f"联系电话: {user_info.get('phone') or '未填写'}"
    ]
    for info in patient_info:
        story.append(Paragraph(info, normal_style))
        story.append(Spacer(1, 2*mm))

    story.append(Spacer(1, 5*mm))
    story.append(Paragraph("报告信息", heading2_style))
    story.append(Spacer(1, 3*mm))
    story.append(Paragraph(f"报告ID: {report_id}", normal_style))
    story.append(Paragraph(f"生成时间: {timestamp}", normal_style))
    story.append(Paragraph(f"异常检测数量: {len(detections)}", normal_style))
    story.append(Spacer(1, 10*mm))

    temp_files = []
    image_elements = []

    if original_image_b64 or annotated_image_b64:
        story.append(Paragraph("影像资料", heading2_style))
        story.append(Spacer(1, 5*mm))

        if original_image_b64:
            img_data = base64.b64decode(original_image_b64.split(",")[1])
            img = Image.open(io.BytesIO(img_data))
            img_path = REPORTS_DIR / f"{report_id}_original.png"
            img.save(img_path)
            temp_files.append(str(img_path))
            image_elements.append(RLImage(str(img_path), width=80*mm, height=80*mm))

        if annotated_image_b64:
            img_data = base64.b64decode(annotated_image_b64.split(",")[1])
            img = Image.open(io.BytesIO(img_data))
            img_path = REPORTS_DIR / f"{report_id}_annotated.png"
            img.save(img_path)
            temp_files.append(str(img_path))
            image_elements.append(RLImage(str(img_path), width=80*mm, height=80*mm))

        if len(image_elements) == 2:
            table = Table([[image_elements[0], image_elements[1]]], colWidths=[85*mm, 85*mm])
        else:
            table = Table([[image_elements[0]]], colWidths=[170*mm])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        story.append(table)
        story.append(Spacer(1, 10*mm))

    story.append(Paragraph("AI智能分析", heading2_style))
    story.append(Spacer(1, 5*mm))

    diagnosis = ai_report.get('diagnosis', '无') or '无'
    recommendations = ai_report.get('recommendations', '无') or '无'
    patient_friendly = ai_report.get('patient_friendly', '无') or '无'

    # 诊断分析 - 分段显示
    story.append(Paragraph("<b>诊断分析</b>", heading3_style))
    diagnosis_paragraphs = format_paragraph_text(diagnosis)
    for para in diagnosis_paragraphs:
        story.append(Paragraph(para, normal_style))
        story.append(Spacer(1, 3*mm))
    story.append(Spacer(1, 5*mm))

    # 临床建议
    if recommendations and recommendations != '无':
        story.append(Paragraph("<b>临床建议</b>", heading3_style))
        rec_paragraphs = format_paragraph_text(recommendations)
        for para in rec_paragraphs:
            story.append(Paragraph(para, normal_style))
            story.append(Spacer(1, 3*mm))
        story.append(Spacer(1, 5*mm))

    # 患者说明
    if patient_friendly and patient_friendly != '无':
        story.append(Paragraph("<b>患者说明</b>", heading3_style))
        pf_paragraphs = format_paragraph_text(patient_friendly)
        for para in pf_paragraphs:
            story.append(Paragraph(para, normal_style))
            story.append(Spacer(1, 3*mm))
        story.append(Spacer(1, 10*mm))

    # 检测结果详情
    if detections:
        story.append(Paragraph("检测结果详情", heading2_style))
        story.append(Spacer(1, 5*mm))

        for det in detections:
            # 获取中英文名称
            class_name = det.get('class_name', 'Unknown')
            class_name_cn = CLASS_NAME_CN.get(class_name, det.get('class_name_cn', '未知'))

            # Dify没有severity，根据置信度判断严重程度
            confidence = det.get('confidence', 0)
            if confidence >= 0.5:
                severity_text = "高"
            elif confidence >= 0.3:
                severity_text = "中"
            else:
                severity_text = "低"

            detection_text = f"<b>{class_name_cn} ({class_name})</b> - 置信度: {confidence * 100:.1f}% - 严重程度: {severity_text}"
            story.append(Paragraph(detection_text, normal_style))
            story.append(Spacer(1, 3*mm))

    story.append(Spacer(1, 15*mm))
    disclaimer_style = make_style('Disclaimer', parent=styles['Normal'],
        fontSize=9, textColor=HexColor("#999999"), leading=12)
    story.append(Paragraph(
        "免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，不作为最终诊断依据。"
        "最终诊断应由具有执业资格的医师做出。如有疑问，请立即咨询专业医疗机构。",
        disclaimer_style
    ))

    doc.build(story)

    for f in temp_files:
        try:
            os.remove(f)
        except OSError:
            pass

    return str(pdf_path)