from sqlalchemy import Column, Integer, String, Date, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Examination(Base):
    __tablename__ = "examinations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    exam_date = Column(Date, nullable=False, default=datetime.utcnow)
    referring_doctor = Column(String(100), nullable=True)
    status = Column(String(20), default="pending", index=True)  # pending/analyzing/completed/failed
    questionnaire = Column(JSON, nullable=True)
    original_image_path = Column(String(500), nullable=True)
    annotated_image_path = Column(String(500), nullable=True)
    detections = Column(JSON, nullable=True)
    ai_report = Column(JSON, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    is_temporary = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="examinations")