from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientDetail
from crud import (
    get_patient, get_patients, create_patient,
    update_patient, delete_patient
)

router = APIRouter()

@router.get("/patients", response_model=dict)
def list_patients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=1000),
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    skip = (page - 1) * page_size
    total, patients = get_patients(db, skip=skip, limit=page_size, search=search)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "patients": [
            {
                **{
                    "id": p.id,
                    "name": p.name,
                    "age": p.age,
                    "gender": p.gender,
                    "phone": p.phone,
                    "created_at": p.created_at.isoformat(),
                    "updated_at": p.updated_at.isoformat(),
                },
                "examination_count": len(p.examinations)
            }
            for p in patients
        ]
    }

@router.post("/patients", response_model=PatientResponse)
def create_patient_endpoint(patient: PatientCreate, db: Session = Depends(get_db)):
    return create_patient(db, patient)

@router.get("/patients/{patient_id}", response_model=PatientDetail)
def get_patient_endpoint(patient_id: int, db: Session = Depends(get_db)):
    patient = get_patient(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {
        "id": patient.id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "phone": patient.phone,
        "created_at": patient.created_at.isoformat(),
        "updated_at": patient.updated_at.isoformat(),
        "examinations": [
            {
                "id": e.id,
                "exam_date": e.exam_date.isoformat(),
                "status": e.status,
                "created_at": e.created_at.isoformat()
            }
            for e in patient.examinations
        ]
    }

@router.put("/patients/{patient_id}", response_model=PatientResponse)
def update_patient_endpoint(patient_id: int, patient: PatientUpdate, db: Session = Depends(get_db)):
    db_patient = update_patient(db, patient_id, patient)
    if not db_patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db_patient

@router.delete("/patients/{patient_id}")
def delete_patient_endpoint(patient_id: int, db: Session = Depends(get_db)):
    if not delete_patient(db, patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"message": "Patient deleted successfully"}