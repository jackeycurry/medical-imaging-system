from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class QuestionnaireSchema(BaseModel):
    main_symptoms: List[str] = []
    symptom_duration: Optional[str] = None
    past_lung_disease: List[str] = []
    smoking_history: Optional[str] = None
    occupational_exposure: List[str] = []
    family_lung_history: Optional[bool] = None
    last_xray_time: Optional[str] = None
    exam_purpose: Optional[str] = None
    notes: Optional[str] = None


class ExaminationBase(BaseModel):
    patient_id: int
    exam_date: str
    referring_doctor: Optional[str] = None
    questionnaire: Optional[QuestionnaireSchema] = None


class ExaminationCreate(ExaminationBase):
    pass


class ExaminationUpdate(BaseModel):
    exam_date: Optional[str] = None
    referring_doctor: Optional[str] = None
    questionnaire: Optional[QuestionnaireSchema] = None
    status: Optional[str] = None


class DetectionResult(BaseModel):
    class_id: int
    class_name: str
    class_name_cn: str
    confidence: float
    bbox: List[float]


class AIReportSchema(BaseModel):
    diagnosis: str
    recommendations: str
    patient_friendly: str


class ExaminationResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: str
    exam_date: str
    referring_doctor: Optional[str]
    status: str
    questionnaire: Optional[QuestionnaireSchema]
    original_image_path: Optional[str]
    annotated_image_path: Optional[str]
    detections: Optional[List[DetectionResult]]
    ai_report: Optional[AIReportSchema]
    pdf_path: Optional[str]
    is_temporary: bool
    created_at: datetime

    class Config:
        from_attributes = True
