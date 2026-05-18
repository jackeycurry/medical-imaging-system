from sqlalchemy import Column, Integer, String, Text, LargeBinary, DateTime
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password = Column(String(255), nullable=False)
    role = Column(String(20), default="ADMIN")
    real_name = Column(String(100))
    create_time = Column(DateTime, default=func.now())
    update_time = Column(DateTime, default=func.now(), onupdate=func.now())

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, index=True)
    gender = Column(String(10))
    age = Column(Integer)
    idcard = Column(String(18))
    height = Column(Integer)
    weight = Column(Integer)
    phone = Column(String(20))
    disease = Column(String(100))
    address = Column(String(200))
    create_time = Column(DateTime, default=func.now())
    update_time = Column(DateTime, default=func.now(), onupdate=func.now())
    create_by = Column(String(50))

class MedicalRecord(Base):
    __tablename__ = "medical_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String(50), nullable=False, index=True)
    type = Column(String(50))
    diagnosis = Column(String(200))
    symptom = Column(Text)
    smoke_year = Column(Integer)
    create_time = Column(DateTime, default=func.now())
    update_time = Column(DateTime, default=func.now(), onupdate=func.now())
    create_by = Column(String(50))

class MedicalImage(Base):
    __tablename__ = "medical_images"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String(50), index=True)
    patient_id = Column(String(50), index=True)  # 体检号
    image_type = Column(String(20))  # CT/X光
    original_filename = Column(String(200))
    detections = Column(Text)  # JSON格式检测结果
    report_content = Column(Text)  # AI报告
    annotated_image = Column(LargeBinary)  # 标注图片
    status = Column(String(20), default="待检测")
    report_id = Column(String(100))
    pdf_path = Column(String(500))  # PDF file storage path
    create_time = Column(DateTime, default=func.now())
    update_time = Column(DateTime, default=func.now(), onupdate=func.now())
    create_by = Column(String(50))
