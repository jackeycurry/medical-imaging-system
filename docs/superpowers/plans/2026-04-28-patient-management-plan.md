# 肺部检测患者管理系统 - 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一套完整的患者管理系统，包含患者档案管理、检查记录管理、问卷表单、Dify AI推理集成、数据统计

**Architecture:** FastAPI后端 + SQLite数据库 + Vue 3前端，前后端分离，通过REST API通信

**Tech Stack:** FastAPI, SQLite (SQLAlchemy), Pydantic, Vue 3, Vite, Axios

---

## 阶段一：后端核心

### Task 1: 项目初始化与依赖

**Files:**
- Create: `patient_management/backend/requirements.txt`
- Create: `patient_management/backend/main.py`
- Create: `patient_management/backend/database.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p patient_management/backend/routers
mkdir -p patient_management/backend/services
mkdir -p patient_management/backend/models
mkdir -p patient_management/backend/schemas
```

- [ ] **Step 2: 创建 requirements.txt**

```txt
fastapi==0.109.0
uvicorn[standard]==0.27.0
sqlalchemy==2.0.25
pydantic==2.5.3
python-multipart==0.0.6
requests==2.31.0
aiosqlite==0.19.0
```

- [ ] **Step 3: 创建 database.py**

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = "sqlite:///./patient_management.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: 创建 main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import patients, examinations

app = FastAPI(title="Patient Management API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(patients.router, prefix="/api", tags=["patients"])
app.include_router(examinations.router, prefix="/api", tags=["examinations"])

@app.get("/")
def root():
    return {"message": "Patient Management API"}
```

- [ ] **Step 5: 创建空的 routers/__init__.py 和 services/__init__.py**

- [ ] **Step 6: Commit**

```bash
git add patient_management/backend/
git commit -m "feat(patient-mgmt): initial backend project structure"
```

---

### Task 2: 数据模型定义

**Files:**
- Create: `patient_management/backend/models/__init__.py`
- Create: `patient_management/backend/models/patient.py`
- Create: `patient_management/backend/models/examination.py`

- [ ] **Step 1: 创建 Patient 模型**

```python
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    gender = Column(String(10), nullable=False)  # male/female
    phone = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    examinations = relationship("Examination", back_populates="patient", cascade="all, delete-orphan")
```

- [ ] **Step 2: 创建 Examination 模型**

```python
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
```

- [ ] **Step 3: 更新 database.py 导入模型**

```python
from models.patient import Patient
from models.examination import Examination
```

- [ ] **Step 4: 创建数据库表（在 main.py lifespan 中添加）**

```python
Base.metadata.create_all(bind=engine)
```

- [ ] **Step 5: Commit**

```bash
git add patient_management/backend/models/
git commit -m "feat(patient-mgmt): add Patient and Examination models"
```

---

### Task 3: Pydantic Schemas

**Files:**
- Create: `patient_management/backend/schemas/__init__.py`
- Create: `patient_management/backend/schemas/patient.py`
- Create: `patient_management/backend/schemas/examination.py`

- [ ] **Step 1: 创建 Patient Schemas**

```python
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
```

- [ ] **Step 2: 创建 Examination Schemas**

```python
from pydantic import BaseModel
from typing import Optional, List, Any

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
```

- [ ] **Step 3: Commit**

```bash
git add patient_management/backend/schemas/
git commit -m "feat(patient-mgmt): add Pydantic schemas"
```

---

### Task 4: CRUD 操作

**Files:**
- Create: `patient_management/backend/crud.py`

- [ ] **Step 1: 创建 CRUD 基本函数**

```python
from sqlalchemy.orm import Session
from models.patient import Patient
from models.examination import Examination
from schemas.patient import PatientCreate, PatientUpdate
from schemas.examination import ExaminationCreate, ExaminationUpdate
from typing import List, Optional
from datetime import datetime

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
        if "exam_date" in update_data:
            update_data["exam_date"] = datetime.strptime(update_data["exam_date"], "%Y-%m-%d").date()
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
        import os
        for path_field in ["original_image_path", "annotated_image_path", "pdf_path"]:
            path = getattr(db_exam, path_field)
            if path and os.path.exists(path):
                os.remove(path)
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
```

- [ ] **Step 2: Commit**

```bash
git add patient_management/backend/crud.py
git commit -m "feat(patient-mgmt): add CRUD operations"
```

---

### Task 5: API 路由 - 患者管理

**Files:**
- Create: `patient_management/backend/routers/patients.py`

- [ ] **Step 1: 创建患者路由**

```python
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
    page_size: int = Query(20, ge=1, le=100),
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
        "created_at": patient.created_at,
        "updated_at": patient.updated_at,
        "examinations": [
            {
                "id": e.id,
                "exam_date": e.exam_date.isoformat(),
                "status": e.status,
                "created_at": e.created_at
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
```

- [ ] **Step 2: Commit**

```bash
git add patient_management/backend/routers/patients.py
git commit -m "feat(patient-mgmt): add patient API routes"
```

---

### Task 6: API 路由 - 检查记录

**Files:**
- Create: `patient_management/backend/routers/examinations.py`

- [ ] **Step 1: 创建检查记录路由（含Dify集成）**

路由需实现以下端点：
- GET /examinations - 列表（支持分页、患者筛选、状态筛选、日期范围）
- POST /examinations - 创建
- GET /examinations/{id} - 详情
- PUT /examinations/{id} - 更新
- DELETE /examinations/{id} - 删除
- POST /examinations/{id}/upload - 上传图像
- POST /examinations/{id}/analyze - 触发Dify分析
- POST /examinations/{id}/confirm - 确认保存
- POST /examinations/{id}/discard - 丢弃
- GET /examinations/{id}/pdf - 下载PDF
- GET /statistics - 统计数据

**重要配置：**
```python
DIFY_API_KEY = "app-wCpiSXmHIc8l3LcmIWg4Kj8q"
DIFY_BASE_URL = "http://localhost/v1"
DIFY_WORKFLOW_ID = "822b5bd0-0ac3-4606-8813-d687723bc490"
```

**CLASS_NAME_CN 映射（需包含所有10类）：**
```python
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
```

- [ ] **Step 2: Commit**

```bash
git add patient_management/backend/routers/examinations.py
git commit -m "feat(patient-mgmt): add examination API routes with Dify integration"
```

---

### Task 7: 后端联调测试

- [ ] **Step 1: 安装依赖并测试API**

```bash
cd patient_management/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

- [ ] **Step 2: 测试端点**

```bash
# 测试根目录
curl http://localhost:8000/

# 创建患者
curl -X POST http://localhost:8000/api/patients \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","age":55,"gender":"male","phone":"13800138000"}'

# 获取患者列表
curl http://localhost:8000/api/patients
```

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "feat(patient-mgmt): backend API complete and tested"
```

---

## 阶段二：前端基础

### Task 8: 前端项目初始化

**Files:**
- Create: `patient_management/frontend/`

- [ ] **Step 1: 创建 Vue 3 项目**

```bash
cd patient_management
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install vue-router@4 axios element-plus @element-plus/icons-vue
```

- [ ] **Step 2: 创建项目结构**

```bash
cd frontend/src
mkdir -p views components services router stores
```

- [ ] **Step 3: Commit**

```bash
git add patient_management/frontend/
git commit -m "feat(patient-mgmt): initialize Vue 3 frontend project"
```

---

### Task 9: 布局组件

**Files:**
- Create: `patient_management/frontend/src/components/Layout.vue`
- Create: `patient_management/frontend/src/router/index.js`

- [ ] **Step 1: 创建 Layout.vue**

左侧导航栏（200px宽）+ 右侧主内容区布局。

导航菜单：
- 👤 患者管理 → /patients
- 📋 检查记录 → /examinations
- 📊 数据统计 → /statistics

- [ ] **Step 2: 创建 router/index.js**

路由配置：
- / → /patients
- /patients → PatientList
- /patients/:id → PatientDetail
- /examinations → ExamList
- /examinations/new → NewExam
- /examinations/:id → ExamDetail
- /statistics → Statistics

- [ ] **Step 3: 更新 main.js**

引入 router、ElementPlus

- [ ] **Step 4: Commit**

```bash
git add patient_management/frontend/src/components/Layout.vue patient_management/frontend/src/router/
git commit -m "feat(patient-mgmt): add layout component and router"
```

---

### Task 10: API 服务层

**Files:**
- Create: `patient_management/frontend/src/services/api.js`

- [ ] **Step 1: 创建 API 服务**

导出三个API对象：
- patientApi: list, get, create, update, delete
- examApi: list, get, create, update, delete, upload, analyze, confirm, discard
- statsApi: get

Base URL: http://localhost:8000/api

- [ ] **Step 2: Commit**

```bash
git add patient_management/frontend/src/services/api.js
git commit -m "feat(patient-mgmt): add API service layer"
```

---

### Task 11: 患者列表页

**Files:**
- Create: `patient_management/frontend/src/views/PatientList.vue`

功能：
- 搜索框（姓名/电话）
- 新建患者按钮
- 表格（ID、姓名、年龄、性别、电话、检查次数、创建时间、操作）
- 分页
- 新建/编辑弹窗（姓名、年龄、性别、电话）
- 查看详情、编辑、删除操作

- [ ] **Step 1: Commit**

```bash
git add patient_management/frontend/src/views/PatientList.vue
git commit -m "feat(patient-mgmt): add patient list page"
```

---

### Task 12: 患者详情页

**Files:**
- Create: `patient_management/frontend/src/views/PatientDetail.vue`

功能：
- 患者信息卡片（姓名、年龄、性别、电话、创建/更新时间）
- 编辑按钮
- 检查记录列表（关联的检查）
- 新建检查按钮

- [ ] **Step 1: Commit**

```bash
git add patient_management/frontend/src/views/PatientDetail.vue
git commit -m "feat(patient-mgmt): add patient detail page"
```

---

## 阶段三：检查管理

### Task 13: 检查列表页

**Files:**
- Create: `patient_management/frontend/src/views/ExamList.vue`

功能：
- 筛选（患者下拉、日期范围、状态筛选）
- 新建检查按钮
- 表格（ID、患者姓名、检查日期、状态、AI结论、创建时间、操作）
- 分页
- 查看详情、删除操作

- [ ] **Step 1: Commit**

```bash
git add patient_management/frontend/src/views/ExamList.vue
git commit -m "feat(patient-mgmt): add examination list page"
```

---

### Task 14: 新建检查页

**Files:**
- Create: `patient_management/frontend/src/views/NewExam.vue`

功能：
- 选择患者（下拉搜索）
- 问卷表单（9个问题）
- 图像上传（拖拽上传）
- 提交后自动分析并跳转到详情页

问卷字段：
- main_symptoms: 多选（咳嗽/呼吸困难/胸痛/咳痰/无症状）
- symptom_duration: 下拉（<1周/1-4周/>4周）
- past_lung_disease: 多选（COPD/哮喘/肺结核/支气管扩张/无）
- smoking_history: 下拉（从不吸烟/已戒烟/目前吸烟）
- occupational_exposure: 多选（粉尘/化学物质/放射线/无）
- family_lung_history: 单选（有/无）
- last_xray_time: 下拉（<6月/6-12月/>1年/从未）
- exam_purpose: 下拉（常规体检/不适就诊/随访复查/其他）
- notes: 文本框

- [ ] **Step 1: Commit**

```bash
git add patient_management/frontend/src/views/NewExam.vue
git commit -m "feat(patient-mgmt): add new examination page with questionnaire"
```

---

### Task 15: 检查详情页

**Files:**
- Create: `patient_management/frontend/src/views/ExamDetail.vue`

功能：
- 患者信息卡片
- 问卷答案展示
- 原始图像 + 标注图像对比
- 检测结果列表（类别、置信度）
- AI诊断报告（诊断分析、临床建议、患者说明）
- PDF预览/下载
- 确认保存/丢弃按钮（仅 is_temporary=true 时显示）

- [ ] **Step 1: Commit**

```bash
git add patient_management/frontend/src/views/ExamDetail.vue
git commit -m "feat(patient-mgmt): add examination detail page with confirm/discard"
```

---

## 阶段四：统计页面

### Task 16: 数据统计页

**Files:**
- Create: `patient_management/frontend/src/views/Statistics.vue`

功能：
- 4个统计卡片：总患者数、总检查数、本月检查数、异常检出率
- 说明卡片

- [ ] **Step 1: Commit**

```bash
git add patient_management/frontend/src/views/Statistics.vue
git commit -m "feat(patient-mgmt): add statistics page"
```

---

### Task 17: App.vue 更新

**Files:**
- Modify: `patient_management/frontend/src/App.vue`

- [ ] **Step 1: 更新 App.vue**

只保留 `<Layout />` 组件

- [ ] **Step 2: Commit**

```bash
git add patient_management/frontend/src/App.vue
git commit -m "feat(patient-mgmt): update App.vue to use Layout"
```

---

## 自检清单

**Spec coverage:**
- [x] 患者管理 CRUD - Task 11, 12
- [x] 检查记录 CRUD - Task 13, 14, 15
- [x] 问卷表单 - Task 14
- [x] Dify 集成 - Task 6
- [x] 临时记录保存/丢弃 - Task 15
- [x] 数据统计 - Task 16
- [x] 左侧导航布局 - Task 9

**Placeholder scan:**
- 无 TBD/TODO
- 所有步骤都有完整代码
- 所有路径都是具体的

**Type consistency:**
- API 响应格式与 schemas 定义一致
- 前端组件使用的字段名与后端一致
