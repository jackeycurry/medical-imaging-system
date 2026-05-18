from sqlalchemy.orm import Session
from models.patient import Patient
from models.examination import Examination
from schemas.patient import PatientCreate, PatientUpdate
from schemas.examination import ExaminationCreate, ExaminationUpdate
from typing import List, Optional
from datetime import datetime
import os

# Patient CRUD

def get_patient(db: Session, patient_id: int) -> Optional[Patient]:
    return db.query(Patient).filter(Patient.id == patient_id).first()

def get_patients(db: Session, skip: int = 0, limit: int = 20, search: Optional[str] = None):
    query = db.query(Patient)
    if search:
        query = query.filter(
            (Patient.name.contains(search)) | (Patient.phone.contains(search))
        )
    total = query.count()
    patients = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return total, patients

def create_patient(db: Session, patient: PatientCreate) -> Patient:
    db_patient = Patient(**patient.model_dump())
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def update_patient(db: Session, patient_id: int, patient: PatientUpdate) -> Optional[Patient]:
    db_patient = get_patient(db, patient_id)
    if db_patient:
        for key, value in patient.model_dump(exclude_unset=True).items():
            setattr(db_patient, key, value)
        db_patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_patient)
    return db_patient

def delete_patient(db: Session, patient_id: int) -> bool:
    db_patient = get_patient(db, patient_id)
    if db_patient:
        db.delete(db_patient)
        db.commit()
        return True
    return False

# Examination CRUD

def get_examination(db: Session, exam_id: int) -> Optional[Examination]:
    return db.query(Examination).filter(Examination.id == exam_id).first()

def get_examinations(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    patient_id: Optional[int] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    query = db.query(Examination)
    if patient_id:
        query = query.filter(Examination.patient_id == patient_id)
    if status:
        query = query.filter(Examination.status == status)
    if start_date:
        query = query.filter(Examination.exam_date >= start_date)
    if end_date:
        query = query.filter(Examination.exam_date <= end_date)

    total = query.count()
    exams = query.order_by(Examination.created_at.desc()).offset(skip).limit(limit).all()
    return total, exams

def create_examination(db: Session, exam: ExaminationCreate) -> Examination:
    exam_data = exam.model_dump()
    exam_data["exam_date"] = datetime.strptime(exam_data["exam_date"], "%Y-%m-%d").date()
    db_exam = Examination(**exam_data)
    db.add(db_exam)
    db.commit()
    db.refresh(db_exam)
    return db_exam

def update_examination(db: Session, exam_id: int, exam: ExaminationUpdate) -> Optional[Examination]:
    db_exam = get_examination(db, exam_id)
    if db_exam:
        update_data = exam.model_dump(exclude_unset=True)
        exam_date = update_data.pop("exam_date", None)
        if exam_date:
            update_data["exam_date"] = datetime.strptime(exam_date, "%Y-%m-%d").date()
        for key, value in update_data.items():
            setattr(db_exam, key, value)
        db.commit()
        db.refresh(db_exam)
    return db_exam

def delete_examination(db: Session, exam_id: int) -> bool:
    db_exam = get_examination(db, exam_id)
    if db_exam:
        db.delete(db_exam)
        db.commit()
        return True
    return False

def confirm_examination(db: Session, exam_id: int) -> Optional[Examination]:
    db_exam = get_examination(db, exam_id)
    if db_exam:
        db_exam.is_temporary = False
        db.commit()
        db.refresh(db_exam)
    return db_exam

def discard_examination(db: Session, exam_id: int) -> bool:
    db_exam = get_examination(db, exam_id)
    if db_exam:
        for path_field in ["original_image_path", "annotated_image_path", "pdf_path"]:
            path = getattr(db_exam, path_field)
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        db.delete(db_exam)
        db.commit()
        return True
    return False

def get_examination_stats(db: Session):
    total_patients = db.query(Patient).count()
    total_exams = db.query(Examination).count()
    monthly_exams = db.query(Examination).filter(
        Examination.created_at >= datetime.utcnow().replace(day=1)
    ).count()
    completed_exams = db.query(Examination).filter(Examination.status == "completed").count()
    anomaly_count = 0
    exams_with_detections = db.query(Examination).filter(Examination.detections != None).all()
    for exam in exams_with_detections:
        if exam.detections and len(exam.detections) > 0:
            anomaly_count += 1
    anomaly_rate = (anomaly_count / total_exams * 100) if total_exams > 0 else 0
    return {
        "total_patients": total_patients,
        "total_examinations": total_exams,
        "monthly_examinations": monthly_exams,
        "completed_examinations": completed_exams,
        "anomaly_count": anomaly_count,
        "anomaly_rate": round(anomaly_rate, 1)
    }
