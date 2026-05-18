"""FastAPI backend for chest X-ray analysis system."""

import base64
import io
import os
import shutil
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from PIL import Image

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from medical_data import MEDICAL_DATA
from model_loader import model_instance
from report_generator import generate_report
from ai_report_generator import generate_ai_report
from pdf_generator import create_pdf_report


UPLOAD_DIR = Path("D:/Project/test/sec/backend/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("Starting Chest X-ray Analysis API...")
    yield
    print("Shutting down...")


app = FastAPI(
    title="Chest X-ray Analysis API",
    description="Chest X-ray analysis system using YOLO deep learning model",
    version="1.0.0",
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
        "name": "Chest X-ray Analysis API",
        "version": "1.0.0",
        "description": "Chest X-ray analysis system with YOLO model",
        "endpoints": {
            "GET /": "API info",
            "GET /api/classes": "Get all 10 class definitions",
            "POST /api/analyze": "Analyze chest X-ray image"
        }
    }


@app.get("/api/classes")
async def get_classes():
    """Get all 10 class definitions."""
    classes = []
    for class_id, info in MEDICAL_DATA.items():
        classes.append({
            "class_id": class_id,
            "name_en": info["name_en"],
            "name_cn": info["name_cn"],
            "explanation": info["explanation"],
            "severity_rules": info["severity_rules"],
            "recommendation": info["recommendation"]
        })
    return {"classes": classes}


@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Analyze a chest X-ray image.

    Accepts image file upload, runs YOLO model inference,
    and returns enriched medical report with base64 encoded images.
    """
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
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")

    try:
        with open(file_path, "rb") as f:
            original_image_base64 = base64.b64encode(f.read()).decode("utf-8")

        results = model_instance.predict(str(file_path))
        detections = model_instance.get_detections(results)

        result = results[0]
        annotated_image_base64 = None
        if detections:
            annotated_img = result.plot()
            annotated_pil = Image.fromarray(annotated_img)
            buffer = io.BytesIO()
            annotated_pil.save(buffer, format="PNG")
            annotated_image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        report = generate_report(str(file_path), detections)

        ai_report = generate_ai_report(report["detections"])
        report["ai_report"] = ai_report

        print(f"[DEBUG] ai_report type: {type(ai_report)}")
        print(f"[DEBUG] ai_report keys: {ai_report.keys() if isinstance(ai_report, dict) else 'not a dict'}")
        print(f"[DEBUG] ai_report diagnosis length: {len(ai_report.get('diagnosis', ''))}")

        report["image_id"] = report["report_id"]
        report["original_image"] = f"data:image/{file_ext[1:]};base64,{original_image_base64}"
        if annotated_image_base64:
            report["annotated_image"] = f"data:image/png;base64,{annotated_image_base64}"

        create_pdf_report(
            report_id=report["report_id"],
            detections=report["detections"],
            ai_report=ai_report,
            original_image_b64=report.get("original_image"),
            annotated_image_b64=report.get("annotated_image")
        )
        report["pdf_url"] = f"/api/report/{report['report_id']}/pdf"
        report["pdf_preview_url"] = f"/api/report/{report['report_id']}/preview"

        os.remove(file_path)

        return JSONResponse(content=report)

    except Exception as e:
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
