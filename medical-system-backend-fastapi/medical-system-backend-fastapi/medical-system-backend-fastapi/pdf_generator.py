"""Unified PDF report generator for all medical imaging modalities."""
import io
import base64
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Image as RLImage, Table, TableStyle, PageBreak
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

REPORTS_DIR = Path("D:/Project/test/second/backend/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Register Chinese font
try:
    pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/simhei.ttf'))
    DEFAULT_FONT = 'SimHei'
except Exception:
    try:
        pdfmetrics.registerFont(TTFont('SimHei', 'C:/Windows/Fonts/msyh.ttc'))
        DEFAULT_FONT = 'SimHei'
    except Exception:
        DEFAULT_FONT = 'Helvetica'

PRIMARY_COLOR = HexColor("#4a90d9")

# Modality configuration
MODALITY_CONFIG = {
    "chest": {
        "title": "胸部X光智能分析报告",
        "region_labels": {
            "lung_fields": "双肺野", "pleura": "胸膜", "mediastinum": "纵隔",
            "heart": "心脏", "diaphragm": "膈肌", "bones": "骨骼", "soft_tissue": "软组织"
        }
    },
    "brain": {
        "title": "脑部影像智能分析报告",
        "region_labels": {
            "skull": "颅骨", "extra_axial": "硬膜外/下及蛛网膜下腔",
            "brain_parenchyma": "脑实质", "ventricles": "脑室系统",
            "midline": "中线结构", "vessels": "血管", "sella": "蝶鞍区"
        }
    },
    "retina": {
        "title": "眼底影像智能分析报告",
        "region_labels": {
            "optic_disc": "视盘", "macula": "黄斑",
            "retinal_vessels": "视网膜血管", "posterior_pole": "后极部视网膜",
            "peripheral_retina": "周边视网膜", "vitreous": "玻璃体"
        }
    },
    "ct": {
        "title": "胸部CT影像智能分析报告",
        "region_labels": {
            "soft_tissue": "胸壁软组织及颈部", "bones": "骨骼",
            "mediastinum": "纵隔", "heart_vessels": "心脏及大血管",
            "airways": "气管及支气管", "lung_fields": "双肺野",
            "pleura": "胸膜及胸腔", "diaphragm": "膈肌"
        }
    },
    "abdomen": {
        "title": "腹部影像智能分析报告",
        "region_labels": {
            "liver": "肝脏", "gallbladder_biliary": "胆囊及胆道",
            "pancreas": "胰腺", "spleen": "脾脏",
            "kidneys_adrenals": "双肾及肾上腺", "gi_tract": "胃肠道",
            "peritoneum": "腹膜腔", "vessels": "腹部血管",
            "lymph_nodes": "淋巴结", "abdominal_wall": "腹壁"
        }
    },
    "spine": {
        "title": "脊柱影像智能分析报告",
        "region_labels": {
            "spinal_curvature": "脊柱曲度", "vertebral_alignment": "椎体序列",
            "vertebral_body": "各椎体", "intervertebral_disc": "椎间盘",
            "spinal_canal": "椎管", "facet_joints": "小关节",
            "ligaments": "韧带", "soft_tissue": "周围软组织"
        }
    },
    "breast": {
        "title": "乳腺影像智能分析报告",
        "region_labels": {
            "skin": "皮肤", "subcutaneous_fat": "皮下脂肪",
            "breast_parenchyma": "乳腺实质", "retroareolar": "乳晕后区",
            "pectoral_muscle": "胸肌", "axilla": "腋窝"
        }
    },
    "cardiovascular": {
        "title": "心血管影像智能分析报告",
        "region_labels": {
            "coronary_arteries": "冠状动脉", "cardiac_chambers": "各腔室",
            "heart_valves": "心脏瓣膜", "myocardium": "心肌",
            "pericardium": "心包", "aorta": "主动脉",
            "pulmonary_vessels": "肺血管", "peripheral_vessels": "外周血管"
        }
    }
}

DISCLAIMER_TEXT = (
    "免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，"
    "不作为最终诊断依据。最终诊断应由具有执业资格的医师做出。"
    "如有疑问，请立即咨询专业医疗机构。"
)


def _make_style(name, parent=None, **kwargs):
    """Create a ParagraphStyle with Chinese font."""
    if parent:
        return ParagraphStyle(name, parent=parent, fontName=DEFAULT_FONT, **kwargs)
    return ParagraphStyle(name, fontName=DEFAULT_FONT, **kwargs)


def _strip_html(text: str) -> str:
    """Remove HTML-like tags from text for safe PDF rendering."""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&[a-z]+;', '', text)
    return text


def _format_text(text: str) -> str:
    """Format text for ReportLab: convert markdown bold to <b> tags, escape &."""
    if not text:
        return ""
    text = text.replace('&', '&amp;')
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return text


def _image_from_b64(data_url: str) -> Optional[str]:
    """Decode base64 image data URL and save to temp file. Returns file path."""
    if not data_url or ',' not in data_url:
        return None
    try:
        img_data = base64.b64decode(data_url.split(',')[1])
        img = Image.open(io.BytesIO(img_data))
        img_path = REPORTS_DIR / f"_tmp_{os.urandom(4).hex()}.png"
        img.save(img_path)
        return str(img_path)
    except Exception:
        return None


def _add_section_title(story, styles, title: str):
    """Add a section heading."""
    h2 = _make_style('SectionTitle', parent=styles['Heading2'], fontSize=14, textColor=PRIMARY_COLOR, spaceAfter=10, spaceBefore=14)
    story.append(Paragraph(title, h2))
    story.append(Spacer(1, 3 * mm))


def _add_paragraph_lines(story, text: str, style):
    """Split multi-line text into individual paragraphs."""
    if not text:
        return
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        line = _format_text(line)
        story.append(Paragraph(line, style))
        story.append(Spacer(1, 2 * mm))


def generate_pdf_report(
    report_id: str,
    modality: str,
    detections: List[Dict],
    ai_report: Dict[str, str],
    user_info: Optional[Dict] = None,
    symptoms_text: str = "",
    original_image_b64: Optional[str] = None,
    annotated_image_b64: Optional[str] = None
) -> str:
    """Generate a PDF report for any imaging modality.

    Args:
        report_id: Unique report identifier
        modality: One of chest/brain/retina/ct/abdomen/spine/breast/cardiovascular
        detections: List of detection dicts with class_name, class_name_cn, confidence, etc.
        ai_report: Dict with quality_assessment, anatomical_findings, diagnosis,
                   impression, recommendations, patient_friendly
        user_info: Optional dict with name, age, gender, phone
        original_image_b64: Base64 data URL of original image
        annotated_image_b64: Base64 data URL of annotated image

    Returns:
        Absolute path to the generated PDF file.
    """
    config = MODALITY_CONFIG.get(modality, MODALITY_CONFIG["chest"])
    title = config["title"]
    region_labels = config.get("region_labels", {})

    if user_info is None:
        user_info = {}

    pdf_path = REPORTS_DIR / f"{report_id}.pdf"
    temp_files = []

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()
    story = []

    # --- Title ---
    title_style = _make_style('ReportTitle', parent=styles['Heading1'],
                              fontSize=22, textColor=PRIMARY_COLOR, spaceAfter=16, alignment=1)
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 8 * mm))

    normal = _make_style('CNormal', parent=styles['Normal'], fontSize=10, leading=16)
    small = _make_style('Small', parent=styles['Normal'], fontSize=8, leading=12, textColor=HexColor("#999999"))

    # --- Patient Info ---
    _add_section_title(story, styles, "患者信息")
    gender_raw = str(user_info.get('gender', '')).strip()
    gender_text = "男" if gender_raw in ('male', '男') else ("女" if gender_raw in ('female', '女') else "未填写")
    patient_lines = [
        f"姓名：{user_info.get('name') or '未填写'}",
        f"年龄：{user_info.get('age') or '未填写'}",
        f"性别：{gender_text}",
        f"联系电话：{user_info.get('phone') or '未填写'}"
    ]
    for line in patient_lines:
        story.append(Paragraph(line, normal))
        story.append(Spacer(1, 2 * mm))

    # --- Symptoms ---
    if symptoms_text:
        story.append(Spacer(1, 3 * mm))
        _add_section_title(story, styles, "患者症状描述")
        story.append(Paragraph(symptoms_text.replace("；", "；\n"), normal))
        story.append(Spacer(1, 2 * mm))

    # --- Report Info ---
    story.append(Spacer(1, 3 * mm))
    _add_section_title(story, styles, "报告信息")
    timestamp = datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")
    story.append(Paragraph(f"报告编号：{report_id}", normal))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"生成时间：{timestamp}", normal))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph(f"检测异常数：{len(detections)}", normal))
    story.append(Spacer(1, 6 * mm))

    # --- Images ---
    if original_image_b64 or annotated_image_b64:
        _add_section_title(story, styles, "影像资料")
        image_elements = []

        for b64 in [original_image_b64, annotated_image_b64]:
            if b64:
                img_path = _image_from_b64(b64)
                if img_path:
                    temp_files.append(img_path)
                    image_elements.append(RLImage(img_path, width=75 * mm, height=75 * mm))

        if len(image_elements) == 2:
            t = Table([[image_elements[0], image_elements[1]]], colWidths=[85 * mm, 85 * mm])
        elif len(image_elements) == 1:
            t = Table([[image_elements[0]]], colWidths=[170 * mm])
        else:
            t = None

        if t:
            t.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ]))
            story.append(t)
        story.append(Spacer(1, 6 * mm))

    # --- Quality Assessment ---
    quality = ai_report.get('quality_assessment', '') or '未提供影像质量评估'
    _add_section_title(story, styles, "一、影像质量评估")
    _add_paragraph_lines(story, quality, normal)

    # --- Anatomical Findings ---
    anatomical = ai_report.get('anatomical_findings', {})
    if not isinstance(anatomical, dict):
        anatomical = {}
    _add_section_title(story, styles, "二、解剖分区影像所见")
    if anatomical:
        for key, label in region_labels.items():
            value = anatomical.get(key, '') or '未见明显异常'
            story.append(Paragraph(f"<b>{label}：</b>{value}", normal))
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("未提供分区描述", normal))
    story.append(Spacer(1, 3 * mm))

    # --- Detections ---
    _add_section_title(story, styles, "三、异常检测列表")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get('class_name_cn', det.get('class_name', '未知'))
            en = det.get('class_name', '')
            conf = det.get('confidence', 0)
            desc = det.get('description', '')
            term = det.get('term_explanation', '')
            clinical = det.get('clinical_significance', '')
            approx = ' (约)' if det.get('bbox_approximate') else ''

            name_text = f"{cn}{approx}"
            if en and en != cn:
                name_text += f" ({en})"

            story.append(Paragraph(f"<b>{i}. {name_text}</b>  [置信度：{conf:.0%}]", normal))
            story.append(Spacer(1, 1 * mm))

            if desc:
                story.append(Paragraph(f"    <b>影像特征：</b>{desc}", normal))
                story.append(Spacer(1, 1 * mm))
            if term:
                story.append(Paragraph(f"    <b>术语解释：</b>{term}", normal))
                story.append(Spacer(1, 1 * mm))
            if clinical:
                story.append(Paragraph(f"    <b>临床意义：</b>{clinical}", normal))
                story.append(Spacer(1, 1 * mm))
            story.append(Spacer(1, 2 * mm))
    else:
        story.append(Paragraph("未检测到明确异常", normal))
    story.append(Spacer(1, 3 * mm))

    # --- Diagnosis ---
    diagnosis = ai_report.get('diagnosis', '') or '模型未返回诊断结果'
    _add_section_title(story, styles, "四、诊断汇总")
    _add_paragraph_lines(story, diagnosis, normal)

    # --- Impression ---
    impression = ai_report.get('impression', '') or '未提供影像学印象'
    _add_section_title(story, styles, "五、影像学印象")
    _add_paragraph_lines(story, impression, normal)

    # --- Recommendations ---
    recommendations = ai_report.get('recommendations', '') or '建议由专业医生复核'
    _add_section_title(story, styles, "六、临床建议")
    _add_paragraph_lines(story, recommendations, normal)

    # --- Patient Friendly ---
    patient_friendly = ai_report.get('patient_friendly', '') or '请咨询医生获取详细解读'
    _add_section_title(story, styles, "七、患者须知")
    _add_paragraph_lines(story, patient_friendly, normal)

    # --- Disclaimer ---
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph(DISCLAIMER_TEXT, small))

    # Build PDF
    doc.build(story)

    # Clean up temp image files
    for f in temp_files:
        try:
            os.remove(f)
        except OSError:
            pass

    return str(pdf_path)
