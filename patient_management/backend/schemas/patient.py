from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class PatientBase(BaseModel):
    name: str
    age: int
    gender: str
    phone: Optional[str] = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    phone: Optional[str] = None


class ExaminationSummary(BaseModel):
    id: int
    exam_date: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class PatientResponse(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    examination_count: int = 0

    class Config:
        from_attributes = True


class PatientDetail(PatientBase):
    id: int
    created_at: datetime
    updated_at: datetime
    examinations: List[ExaminationSummary] = []

    class Config:
        from_attributes = True
