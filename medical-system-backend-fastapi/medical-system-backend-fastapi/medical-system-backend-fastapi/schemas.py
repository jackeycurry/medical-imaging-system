from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# ========== User ==========
class UserCreate(BaseModel):
    username: str
    password: str
    role: Optional[str] = "ADMIN"
    real_name: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    real_name: Optional[str]
    create_time: datetime

    class Config:
        from_attributes = True

# ========== Patient ==========
class PatientCreate(BaseModel):
    name: str
    gender: Optional[str] = None
    age: Optional[int] = None
    idcard: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    phone: Optional[str] = None
    disease: Optional[str] = None
    address: Optional[str] = None

class PatientUpdate(BaseModel):
    name: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    phone: Optional[str] = None
    disease: Optional[str] = None
    address: Optional[str] = None

class PatientResponse(BaseModel):
    id: int
    name: str
    gender: Optional[str]
    age: Optional[int]
    phone: Optional[str]
    disease: Optional[str]
    address: Optional[str]
    create_time: datetime

    class Config:
        from_attributes = True

# ========== MedicalRecord ==========
class RecordCreate(BaseModel):
    patient_name: str
    type: Optional[str] = None
    diagnosis: Optional[str] = None
    symptom: Optional[str] = None
    smoke_year: Optional[int] = None

class RecordResponse(BaseModel):
    id: int
    patient_name: str
    type: Optional[str]
    diagnosis: Optional[str]
    symptom: Optional[str]
    smoke_year: Optional[int]
    create_time: datetime

    class Config:
        from_attributes = True

# ========== MedicalImage ==========
class ImageResultSave(BaseModel):
    patient_name: str
    patient_id: Optional[str] = None
    image_type: Optional[str] = None
    original_filename: Optional[str] = None
    detections: Optional[str] = None  # JSON字符串
    report_content: Optional[str] = None
    annotated_image_base64: Optional[str] = None

class ImageResponse(BaseModel):
    id: int
    patient_name: Optional[str]
    patient_id: Optional[str]
    image_type: Optional[str]
    original_filename: Optional[str]
    detections: Optional[str]
    report_content: Optional[str]
    status: Optional[str]
    create_time: datetime

    class Config:
        from_attributes = True

# ========== Auth ==========
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    role: str

class ApiResponse(BaseModel):
    code: int = 200
    message: str = "操作成功"
    data: Optional[Any] = None
