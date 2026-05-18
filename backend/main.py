"""FastAPI backend for chest X-ray analysis system - Dify Workflow version."""

import base64
import io
import os
import shutil
import uuid
import json
import requests
from contextlib import asynccontextmanager
from pathlib import Path

from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from report_generator import generate_report
from ai_report_generator import generate_ai_report
from pdf_generator import create_pdf_report


# Dify 配置
DIFY_API_KEY = "app-wCpiSXmHIc8l3LcmIWg4Kj8q"
DIFY_BASE_URL = "http://localhost/v1"
DIFY_WORKFLOW_ID = "822b5bd0-0ac3-4606-8813-d687723bc490"

UPLOAD_DIR = Path("D:/Project/test/sec/backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def upload_to_dify(file_path: str) -> dict:
    """上传图片到Dify，返回文件ID"""
    url = f"{DIFY_BASE_URL}/files/upload"
    headers = {"Authorization": f"Bearer {DIFY_API_KEY}"}

    with open(file_path, "rb") as f:
        files = {"file": (Path(file_path).name, f, "image/jpeg")}
        data = {"user": "backend-api"}
        response = requests.post(url, headers=headers, files=files, data=data)

    response.raise_for_status()
    return response.json()


def run_dify_workflow(file_id: str, user_info: str = "chest_xray_analysis") -> dict:
    """运行Dify工作流进行检测"""
    url = f"{DIFY_BASE_URL}/workflows/run"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "inputs": {
            "user_infor": user_info,
            "ct": {
                "type": "image",
                "transfer_method": "local_file",
                "upload_file_id": file_id
            }
        },
        "response_mode": "blocking",
        "user": "backend-api"
    }

    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()


# 中英文映射
CLASS_NAME_CN = {
    "Atelectasis": "肺不张",
    "Consolidation": "实变",
    "ILD": "间质性肺病",
    "Infiltration": "浸润",
    "Lung Opacity": "肺不透光",
    "Nodule/Mass": "结节/肿块",
    "Pleural Effusion": "胸腔积液",
    "Pleural Thickening": "胸膜增厚",
    "Pneumothorax": "气胸",
    "Pulmonary Fibrosis": "肺纤维化",
    "Aortic enlargement": "主动脉扩大",
    "Cardiomegaly": "心脏扩大",
    "Enlarged PA": "肺动脉增宽"
}

def parse_dify_result(outputs: dict) -> dict:
    """解析Dify工作流返回的结果"""
    body_str = outputs.get("body", "{}")
    detections_data = json.loads(body_str)

    detections = []
    for det in detections_data.get("detections", []):
        class_name = det.get("class_name", "unknown")
        detections.append({
            "class_id": det.get("class_id", 0),
            "class_name": class_name,
            "class_name_cn": CLASS_NAME_CN.get(class_name, class_name),
            "confidence": det.get("confidence", 0),
            "bbox": det.get("bbox", [])
        })

    return {
        "image_size": detections_data.get("image_size", [1024, 1024]),
        "detections": detections
    }


def draw_bboxes_pil(image_path: str, detections: list, output_path: str = None):
    """使用PIL在图片上绘制bbox标注"""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    image_w, image_h = img.size

    # 尝试使用中文字体
    try:
        font = ImageFont.truetype("msyh.ttc", 20)
    except:
        try:
            font = ImageFont.truetype("simhei.ttf", 20)
        except:
            font = ImageFont.load_default()

    for det in detections:
        class_name = det.get("class_name", "unknown")
        confidence = det.get("confidence", 0)
        bbox = det.get("bbox", [])

        if len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox

        # 缩放到原图尺寸 (原图是1024x1024)
        x1 = int(x1 * image_w / 1024)
        y1 = int(y1 * image_h / 1024)
        x2 = int(x2 * image_w / 1024)
        y2 = int(y2 * image_h / 1024)

        # 绘制框 - 绿色
        draw.rectangle([x1, y1, x2, y2], outline="#00FF00", width=3)

        # 绘制标签
        label_cn = CLASS_NAME_CN.get(class_name, class_name)
        label = f"{label_cn}: {confidence:.2f}"

        # 标签背景
        text_bbox = draw.textbbox((x1, y1), label, font=font)
        draw.rectangle([text_bbox[0]-2, text_bbox[1]-2, text_bbox[2]+2, text_bbox[3]+2], fill="#00FF00")

        # 标签文字
        draw.text((x1, y1-25), label, fill="#000000", font=font)

    if output_path is None:
        output_path = image_path.replace(".jpg", "_annotated.jpg").replace(".png", "_annotated.png")

    img.save(output_path)
    return output_path


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("Starting Chest X-ray Analysis API (Dify Workflow)...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Chest X-ray Analysis API",
    description="Chest X-ray analysis system using Dify Workflow",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API information endpoint."""
    return {
        "name": "Chest X-ray Analysis API (Dify)",
        "version": "2.0.0",
        "description": "Chest X-ray analysis system with Dify Workflow",
        "endpoints": {
            "GET /": "API info",
            "GET /api/classes": "Get all class definitions",
            "POST /api/analyze": "Analyze chest X-ray image (via Dify)"
        }
    }


@app.get("/api/classes")
async def get_classes():
    """Get all class definitions."""
    # Dify返回的class_id和MEDICAL_DATA的映射可能不同，这里返回Dify使用的类别
    return {
        "classes": [
            {"class_id": 0, "name_en": "Aortic enlargement", "name_cn": "主动脉扩大"},
            {"class_id": 3, "name_en": "Cardiomegaly", "name_cn": "心脏扩大"},
            {"class_id": 9, "name_en": "Enlarged PA", "name_cn": "肺动脉增宽"},
        ]
    }


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...), user_info: str = Form(None)):
    """
    Analyze a chest X-ray image via Dify Workflow.

    Accepts image file upload, sends to Dify for inference,
    and returns enriched medical report with base64 encoded images.
    """
    # Parse user_info if provided
    user_info_dict = {}
    if user_info:
        try:
            user_info_dict = json.loads(user_info)
        except json.JSONDecodeError:
            pass

    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )

    original_filename = f"{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = UPLOAD_DIR / original_filename

    try:
        # 1. 保存上传的文件
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 2. 读取原始图片并转为base64
        with open(file_path, "rb") as f:
            original_image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 3. 上传到Dify
        print(f"[DEBUG] Uploading file to Dify: {file_path}")
        dify_file_info = upload_to_dify(str(file_path))
        file_id = dify_file_info["id"]
        print(f"[DEBUG] Dify file ID: {file_id}")

        # 4. 运行Dify工作流
        print(f"[DEBUG] Running Dify workflow...")
        # 构建用户信息字符串
        user_info_text = f"姓名:{user_info_dict.get('name','')} 年龄:{user_info_dict.get('age','')} 性别:{user_info_dict.get('gender','')}"
        dify_result = run_dify_workflow(file_id, user_info_text)

        if dify_result.get("code") == "invalid_param":
            raise HTTPException(status_code=400, detail=dify_result.get("message", "Dify error"))

        # 5. 解析Dify返回的结果
        data = dify_result.get("data", {})
        outputs = data.get("outputs", {})

        parse_result = parse_dify_result(outputs)
        detections = parse_result["detections"]
        print(f"[DEBUG] Detections: {detections}")

        # 6. 生成标注图片
        annotated_image_base64 = None
        if detections:
            annotated_path = draw_bboxes_pil(str(file_path), detections)
            with open(annotated_path, "rb") as f:
                annotated_image_base64 = base64.b64encode(f.read()).decode("utf-8")

        # 7. 生成报告（使用Dify的AI分析结果）
        report_id = uuid.uuid4().hex[:8]
        ai_report_text = outputs.get("reasoning_content", "")

        # 构建类似原接口的detections格式
        formatted_detections = []
        for det in detections:
            class_name = det.get("class_name", "unknown")
            formatted_detections.append({
                "class_id": det["class_id"],
                "class_name": class_name,
                "class_name_cn": CLASS_NAME_CN.get(class_name, class_name),
                "confidence": det["confidence"],
                "bbox": det["bbox"]
            })

        # 8. 构建报告
        report = {
            "report_id": report_id,
            "detections": formatted_detections,
            "summary": f"检测到 {len(detections)} 个异常",
            "ai_report": {
                "diagnosis": ai_report_text,
                "detections": formatted_detections
            }
        }

        # 9. 生成PDF
        create_pdf_report(
            report_id=report_id,
            detections=formatted_detections,
            ai_report=report["ai_report"],
            user_info=user_info_dict,
            original_image_b64=f"data:image/{file_ext[1:]};base64,{original_image_base64}",
            annotated_image_b64=f"data:image/png;base64,{annotated_image_base64}" if annotated_image_base64 else None
        )

        # 10. 返回结果
        report["image_id"] = report_id
        report["original_image"] = f"data:image/{file_ext[1:]};base64,{original_image_base64}"
        if annotated_image_base64:
            report["annotated_image"] = f"data:image/png;base64,{annotated_image_base64}"
        report["pdf_url"] = f"/api/report/{report_id}/pdf"
        report["pdf_preview_url"] = f"/api/report/{report_id}/preview"

        # 清理临时文件
        os.remove(file_path)
        if detections and 'annotated_path' in dir():
            try:
                os.remove(annotated_path)
            except:
                pass

        return JSONResponse(content=report)

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Dify API error: {e}")
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Dify API error: {str(e)}")

    except Exception as e:
        print(f"[ERROR] Analysis error: {e}")
        try:
            os.remove(file_path)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/api/report/{report_id}/preview")
async def preview_report_pdf(report_id: str):
    """Preview PDF report in browser"""
    pdf_path = f"D:/Project/test/sec/backend/reports/{report_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return FileResponse(pdf_path, media_type="application/pdf")


@app.get("/api/report/{report_id}/pdf")
async def download_report_pdf(report_id: str):
    """Download PDF report"""
    pdf_path = f"D:/Project/test/sec/backend/reports/{report_id}.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return FileResponse(pdf_path, media_type="application/pdf", filename=f"report_{report_id}.pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
