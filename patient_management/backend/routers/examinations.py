from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from schemas.examination import (
    ExaminationCreate, ExaminationUpdate, ExaminationResponse,
    DetectionResult, AIReportSchema
)
from crud import (
    get_examination, get_examinations, create_examination,
    update_examination, delete_examination, confirm_examination,
    discard_examination, get_examination_stats
)
import os
import uuid
import json
import requests
from fastapi.responses import FileResponse

router = APIRouter()

UPLOAD_DIR = "./uploads"
TEMP_DIR = "./temp"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

DIFY_API_KEY = "app-wCpiSXmHIc8l3LcmIWg4Kj8q"
DIFY_BASE_URL = "http://localhost/v1"
DIFY_WORKFLOW_ID = "822b5bd0-0ac3-4606-8813-d687723bc490"

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

def upload_to_dify(file_path: str) -> dict:
    url = f"{DIFY_BASE_URL}/files/upload"
    headers = {"Authorization": f"Bearer {DIFY_API_KEY}"}
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/jpeg")}
        data = {"user": "patient-management"}
        response = requests.post(url, headers=headers, files=files, data=data)
    response.raise_for_status()
    return response.json()

def run_dify_workflow(file_id: str, user_info: str = "") -> dict:
    url = f"{DIFY_BASE_URL}/workflows/run"
    headers = {
        "Authorization": f"Bearer {DIFY_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": {
            "ct": {"type": "image", "transfer_method": "local_file", "upload_file_id": file_id},
            "user_infor": user_info
        },
        "response_mode": "blocking",
        "user": "patient-management"
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def parse_dify_result(outputs: dict) -> list:
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
    return detections

def draw_bboxes_pil(image_path: str, detections: list, output_path: str = None):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    image_w, image_h = img.size
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
        x1, y1, x2, y2 = int(x1 * image_w / 1024), int(y1 * image_h / 1024), int(x2 * image_w / 1024), int(y2 * image_h / 1024)
        draw.rectangle([x1, y1, x2, y2], outline="#00FF00", width=3)
        label_cn = CLASS_NAME_CN.get(class_name, class_name)
        label = f"{label_cn}: {confidence:.2f}"
        text_bbox = draw.textbbox((x1, y1), label, font=font)
        draw.rectangle([text_bbox[0]-2, text_bbox[1]-2, text_bbox[2]+2, text_bbox[3]+2], fill="#00FF00")
        draw.text((x1, y1-25), label, fill="#000000", font=font)
    if output_path is None:
        output_path = image_path.replace(".jpg", "_annotated.png").replace(".png", "_annotated.png")
    img.save(output_path)
    return output_path

@router.get("/examinations", response_model=dict)
def list_examinations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    total, exams = get_examinations(db, skip=skip, limit=page_size, patient_id=patient_id, status=status, start_date=start_date, end_date=end_date)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "examinations": [
            {
                "id": e.id,
                "patient_id": e.patient_id,
                "patient_name": e.patient.name if e.patient else "Unknown",
                "exam_date": e.exam_date.isoformat(),
                "referring_doctor": e.referring_doctor,
                "status": e.status,
                "is_temporary": e.is_temporary,
                "detection_summary": f"检测到{len(e.detections)}项异常" if e.detections else "无异常",
                "created_at": e.created_at.isoformat()
            }
            for e in exams
        ]
    }

@router.post("/examinations", response_model=ExaminationResponse)
def create_examination_endpoint(exam: ExaminationCreate, db: Session = Depends(get_db)):
    db_exam = create_examination(db, exam)
    return {
        "id": db_exam.id,
        "patient_id": db_exam.patient_id,
        "patient_name": db_exam.patient.name if db_exam.patient else "Unknown",
        "exam_date": db_exam.exam_date.isoformat(),
        "referring_doctor": db_exam.referring_doctor,
        "status": db_exam.status,
        "questionnaire": db_exam.questionnaire,
        "original_image_path": db_exam.original_image_path,
        "annotated_image_path": db_exam.annotated_image_path,
        "detections": db_exam.detections,
        "ai_report": db_exam.ai_report,
        "pdf_path": db_exam.pdf_path,
        "is_temporary": db_exam.is_temporary,
        "created_at": db_exam.created_at
    }

@router.get("/examinations/{exam_id}", response_model=ExaminationResponse)
def get_examination_endpoint(exam_id: int, db: Session = Depends(get_db)):
    exam = get_examination(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    return {
        "id": exam.id,
        "patient_id": exam.patient_id,
        "patient_name": exam.patient.name if exam.patient else "Unknown",
        "exam_date": exam.exam_date.isoformat(),
        "referring_doctor": exam.referring_doctor,
        "status": exam.status,
        "questionnaire": exam.questionnaire,
        "original_image_path": exam.original_image_path,
        "annotated_image_path": exam.annotated_image_path,
        "detections": exam.detections,
        "ai_report": exam.ai_report,
        "pdf_path": exam.pdf_path,
        "is_temporary": exam.is_temporary,
        "created_at": exam.created_at
    }

@router.put("/examinations/{exam_id}", response_model=ExaminationResponse)
def update_examination_endpoint(exam_id: int, exam: ExaminationUpdate, db: Session = Depends(get_db)):
    db_exam = update_examination(db, exam_id, exam)
    if not db_exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    return db_exam

@router.delete("/examinations/{exam_id}")
def delete_examination_endpoint(exam_id: int, db: Session = Depends(get_db)):
    if not delete_examination(db, exam_id):
        raise HTTPException(status_code=404, detail="Examination not found")
    return {"message": "Examination deleted successfully"}

@router.post("/examinations/{exam_id}/upload")
async def upload_image(exam_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    exam = get_examination(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")

    file_ext = os.path.splitext(file.filename)[1].lower()
    filename = f"{uuid.uuid4().hex[:8]}{file_ext}"
    file_path = os.path.join(TEMP_DIR if exam.is_temporary else UPLOAD_DIR, filename)

    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    exam = get_examination(db, exam_id)
    exam.original_image_path = file_path
    db.commit()

    return {"image_path": file_path}

@router.post("/examinations/{exam_id}/analyze")
def analyze_examination(exam_id: int, db: Session = Depends(get_db)):
    exam = get_examination(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    if not exam.original_image_path or not os.path.exists(exam.original_image_path):
        raise HTTPException(status_code=400, detail="No image uploaded")

    try:
        # 构建患者信息字符串
        patient = exam.patient
        user_info = f"姓名:{patient.name} 年龄:{patient.age} 性别:{'男' if patient.gender == 'male' else '女'}"

        # 问卷信息
        if exam.questionnaire:
            q = exam.questionnaire
            user_info += f"\n主要症状: {','.join(q.get('main_symptoms', []))}"
            user_info += f"\n吸烟史: {q.get('smoking_history', '未填写')}"
            user_info += f"\n检查目的: {q.get('exam_purpose', '未填写')}"

        dify_file_info = upload_to_dify(exam.original_image_path)
        file_id = dify_file_info["id"]

        dify_result = run_dify_workflow(file_id, user_info)

        data = dify_result.get("data", {})
        outputs = data.get("outputs", {})
        detections = parse_dify_result(outputs)

        annotated_path = None
        if detections:
            annotated_path = draw_bboxes_pil(exam.original_image_path, detections)

        ai_report = {
            "diagnosis": outputs.get("reasoning_content", ""),
            "recommendations": "",
            "patient_friendly": ""
        }

        exam.detections = detections
        exam.ai_report = ai_report
        exam.annotated_image_path = annotated_path
        exam.status = "completed"
        db.commit()

        return {"detections": detections, "ai_report": ai_report}
    except Exception as e:
        exam.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/examinations/{exam_id}/confirm")
def confirm_examination_endpoint(exam_id: int, db: Session = Depends(get_db)):
    exam = confirm_examination(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    return {"message": "Examination confirmed", "is_temporary": False}

@router.post("/examinations/{exam_id}/discard")
def discard_examination_endpoint(exam_id: int, db: Session = Depends(get_db)):
    if not discard_examination(db, exam_id):
        raise HTTPException(status_code=404, detail="Examination not found")
    return {"message": "Examination discarded"}

@router.get("/examinations/{exam_id}/pdf")
def get_examination_pdf(exam_id: int, db: Session = Depends(get_db)):
    exam = get_examination(db, exam_id)
    if not exam:
        raise HTTPException(status_code=404, detail="Examination not found")
    if not exam.pdf_path or not os.path.exists(exam.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(exam.pdf_path, media_type="application/pdf", filename=f"report_{exam_id}.pdf")

@router.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    return get_examination_stats(db)
