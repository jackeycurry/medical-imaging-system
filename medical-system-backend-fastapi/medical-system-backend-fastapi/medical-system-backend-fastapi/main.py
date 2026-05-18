from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional
import base64
import io
import json
import re
import shutil
from pathlib import Path
import uuid
from PIL import Image, ImageDraw, ImageFont

from database import engine, get_db, Base
from models import User, Patient, MedicalRecord, MedicalImage
from schemas import (
    LoginRequest, LoginResponse, ApiResponse,
    PatientCreate, PatientUpdate, PatientResponse,
    RecordCreate, RecordResponse,
    ImageResultSave, ImageResponse
)

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="医疗档案管理系统", version="1.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def draw_bboxes_pil(image_path: str, detections: list):
    """在图片上绘制检测框，返回 base64 字符串"""
    img = Image.open(image_path)
    draw = ImageDraw.Draw(img)
    image_w, image_h = img.size

    try:
        font = ImageFont.truetype("msyh.ttc", 12)
    except Exception:
        try:
            font = ImageFont.truetype("simhei.ttf", 12)
        except Exception:
            font = ImageFont.load_default()

    for det in detections:
        class_name = det.get("class_name", "unknown")
        class_name_cn = CLASS_NAME_CN.get(class_name, class_name)
        confidence = det.get("confidence", 0)
        bbox = det.get("bbox", [])
        is_approximate = det.get("bbox_approximate", False)

        if len(bbox) != 4:
            continue

        x1, y1, x2, y2 = bbox
        x1 = int(x1 * image_w / 1000)
        y1 = int(y1 * image_h / 1000)
        x2 = int(x2 * image_w / 1000)
        y2 = int(y2 * image_h / 1000)

        # 近似框用橙色虚线，精确框用绿色实线
        if is_approximate:
            color = "#FF8C00"  # 橙色表示不精确
            width = 2
            # 用短线段模拟虚线
            dash_len = 8
            for d in range(0, max(x2 - x1, y2 - y1), dash_len * 2):
                # 上边
                draw.line([(x1 + d, y1), (min(x1 + d + dash_len, x2), y1)], fill=color, width=width)
                # 下边
                draw.line([(x1 + d, y2), (min(x1 + d + dash_len, x2), y2)], fill=color, width=width)
                # 左边
                draw.line([(x1, y1 + d), (x1, min(y1 + d + dash_len, y2))], fill=color, width=width)
                # 右边
                draw.line([(x2, y1 + d), (x2, min(y1 + d + dash_len, y2))], fill=color, width=width)
        else:
            draw.rectangle([x1, y1, x2, y2], outline="#00FF00", width=2)

        # 标签：放在框上方
        label = f"{class_name_cn} {confidence:.2f}"
        text_bbox = draw.textbbox((0, 0), label, font=font)
        tw, th = text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1]
        label_y = max(0, y1 - th - 4)
        label_x = x1
        # 标签背景
        draw.rectangle([label_x - 1, label_y - 1, label_x + tw + 1, label_y + th + 1],
                       fill="#00FF00" if not is_approximate else "#FF8C00")
        draw.text((label_x, label_y), label, fill="#000000", font=font)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


# 简单的JWT token生成（实际项目用python-jose）
SECRET_KEY = "medical-secret-key-2024"
TOKEN_EXPIRE_HOURS = 24

UPLOAD_DIR = Path("D:/Project/test/second/backend/uploads")
REPORTS_DIR = Path("D:/Project/test/second/backend/reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

def create_token(username: str) -> str:
    # 简化版token，实际用python-jose
    import hashlib
    expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=TOKEN_EXPIRE_HOURS)
    token_str = f"{username}:{expire}:{SECRET_KEY}"
    return base64.b64encode(token_str.encode()).decode()

def verify_token(token: str) -> Optional[str]:
    try:
        decoded = base64.b64decode(token.encode()).decode()
        username, expire_str, _ = decoded.split(":")
        expire = datetime.fromisoformat(expire_str)
        if datetime.now(datetime.timezone.utc).replace(tzinfo=None) > expire:
            return None
        return username
    except:
        return None

# 中间件：从header获取用户
def get_current_user(authorization: str = None, db: Session = Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未登录")
    token = authorization.replace("Bearer ", "")
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user

# ========== 初始化管理员账号 ==========
def init_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            admin = User(
                username="admin",
                password="123456",  # 实际项目要加密
                role="ADMIN",
                real_name="系统管理员"
            )
            db.add(admin)
            db.commit()
            print("默认管理员已创建: admin / 123456")
    finally:
        db.close()

from database import SessionLocal

@app.on_event("startup")
async def startup():
    init_admin()

# ========== 健康检查 ==========
@app.get("/")
async def root():
    return {"message": "医疗档案管理系统 API", "version": "1.0.0"}

# ========== 认证接口 ==========
@app.post("/api/auth/login", response_model=ApiResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == request.username).first()
    if not user or user.password != request.password:
        return ApiResponse(code=401, message="用户名或密码错误")

    token = create_token(user.username)
    return ApiResponse(data={
        "access_token": token,
        "username": user.username,
        "role": user.role
    })

@app.post("/api/auth/register", response_model=ApiResponse)
async def register(request: LoginRequest, db: Session = Depends(get_db)):
    import re
    if len(request.password) < 6:
        return ApiResponse(code=400, message="密码长度不能少于6位")
    if not re.search(r"[0-9]", request.password):
        return ApiResponse(code=400, message="密码必须包含数字")
    if not re.search(r"[a-zA-Z]", request.password):
        return ApiResponse(code=400, message="密码必须包含英文字母")
    if db.query(User).filter(User.username == request.username).first():
        return ApiResponse(code=400, message="用户名已存在")

    user = User(username=request.username, password=request.password, role="ADMIN")
    db.add(user)
    db.commit()
    return ApiResponse(message="注册成功")

# ========== 患者档案接口 ==========
@app.get("/api/patients", response_model=ApiResponse)
async def get_patients(name: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Patient)
    if name:
        query = query.filter(Patient.name.contains(name))
    patients = query.order_by(Patient.create_time.desc()).all()

    return ApiResponse(data=[
        {
            "id": p.id, "name": p.name, "gender": p.gender, "age": p.age,
            "phone": p.phone, "disease": p.disease, "address": p.address,
            "createTime": p.create_time.isoformat() if p.create_time else None
        } for p in patients
    ])

@app.post("/api/patients", response_model=ApiResponse)
async def create_patient(request: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(**request.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)

    return ApiResponse(data={
        "id": patient.id, "name": patient.name,
        "createTime": patient.create_time.isoformat() if patient.create_time else None
    })

@app.put("/api/patients/{patient_id}", response_model=ApiResponse)
async def update_patient(patient_id: int, request: PatientUpdate, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return ApiResponse(code=404, message="病人不存在")

    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(patient, key, value)

    db.commit()
    return ApiResponse(message="更新成功")

@app.delete("/api/patients/{patient_id}", response_model=ApiResponse)
async def delete_patient(patient_id: int, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return ApiResponse(code=404, message="病人不存在")

    db.delete(patient)
    db.commit()
    return ApiResponse(message="删除成功")

# ========== 诊疗记录接口 ==========
@app.get("/api/records", response_model=ApiResponse)
async def get_records(patientName: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(MedicalRecord)
    if patientName:
        query = query.filter(MedicalRecord.patient_name.contains(patientName))
    records = query.order_by(MedicalRecord.create_time.desc()).all()

    return ApiResponse(data=[
        {
            "id": r.id, "patientName": r.patient_name, "type": r.type,
            "diagnosis": r.diagnosis, "symptom": r.symptom,
            "smokeYear": r.smoke_year,
            "createTime": r.create_time.isoformat() if r.create_time else None
        } for r in records
    ])

@app.post("/api/records", response_model=ApiResponse)
async def create_record(request: RecordCreate, db: Session = Depends(get_db)):
    record = MedicalRecord(**request.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)

    return ApiResponse(data={
        "id": record.id, "patientName": record.patient_name,
        "createTime": record.create_time.isoformat() if record.create_time else None
    })

@app.delete("/api/records/{record_id}", response_model=ApiResponse)
async def delete_record(record_id: int, db: Session = Depends(get_db)):
    record = db.query(MedicalRecord).filter(MedicalRecord.id == record_id).first()
    if not record:
        return ApiResponse(code=404, message="记录不存在")

    db.delete(record)
    db.commit()
    return ApiResponse(message="删除成功")

# ========== X-Ray 外部系统调用接口 ==========
@app.post("/api/external/upload", response_model=ApiResponse)
async def external_upload(
    patient_name: str,
    patient_id: Optional[str] = None,
    image_type: Optional[str] = "X光",
    original_filename: Optional[str] = None,
    detections: Optional[str] = None,
    report_content: Optional[str] = None,
    annotated_image_base64: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    外部X-Ray识别系统调用的专用接口
    参数说明：
    - patient_name: 患者姓名 (必填)
    - patient_id: 体检号/患者ID (可选)
    - image_type: 影像类型，如 "CT"、"X光"、"MRI" (默认: X光)
    - original_filename: 原始文件名 (可选)
    - detections: 检测结果 JSON 字符串 (可选)
    - report_content: AI报告内容 (可选)
    - annotated_image_base64: 标注图片的base64编码 (可选)
    """
    image = MedicalImage(
        patient_name=patient_name,
        patient_id=patient_id,
        image_type=image_type,
        original_filename=original_filename,
        detections=detections,
        report_content=report_content,
        status="已完成"
    )

    if annotated_image_base64:
        image.annotated_image = base64.b64decode(annotated_image_base64)

    db.add(image)
    db.commit()
    db.refresh(image)

    return ApiResponse(data={
        "id": image.id,
        "patientName": image.patient_name,
        "patientId": image.patient_id,
        "imageType": image.image_type,
        "status": image.status,
        "createTime": image.create_time.isoformat() if image.create_time else None
    })

# YOLO 类别中英文映射
CLASS_NAME_CN = {
    "Aortic enlargement": "主动脉增宽",
    "Atelectasis": "肺不张",
    "Calcification": "钙化灶",
    "Cardiomegaly": "心脏增大",
    "Clavicle fracture": "锁骨骨折",
    "Consolidation": "实变",
    "Diffuse nodular opacities": "弥漫性结节影",
    "Effusion": "胸腔积液",
    "Emphysema": "肺气肿",
    "Enlarged PA": "肺动脉增宽",
    "ILD": "间质性肺病",
    "Infiltration": "浸润",
    "Lung Opacity": "肺透光度改变",
    "Nodule/Mass": "结节/肿块",
}

# 脑部检测类别中英文映射
CLASS_NAME_CN_BRAIN = {
    "Brain hemorrhage": "脑出血",
    "Brain infarction": "脑梗死",
    "Brain tumor": "脑肿瘤",
    "Brain atrophy": "脑萎缩",
    "Hydrocephalus": "脑积水",
    "Skull fracture": "颅骨骨折",
    "Brain edema": "脑水肿",
    "Midline shift": "中线移位",
    "Subdural hematoma": "硬膜下血肿",
    "Epidural hematoma": "硬膜外血肿",
    "Subarachnoid hemorrhage": "蛛网膜下腔出血",
    "White matter lesions": "白质病变",
    "Aneurysm": "动脉瘤",
    "Vascular malformation": "血管畸形",
}

# 视网膜检测类别中英文映射
CLASS_NAME_CN_RETINA = {
    "Diabetic retinopathy": "糖尿病视网膜病变",
    "Macular degeneration": "黄斑变性",
    "Glaucoma suspect": "青光眼可疑",
    "Retinal hemorrhage": "视网膜出血",
    "Retinal detachment": "视网膜脱离",
    "Papilledema": "视乳头水肿",
    "Arteriosclerosis": "视网膜动脉硬化",
    "Microaneurysm": "微动脉瘤",
    "Cotton wool spots": "棉絮斑",
    "Hard exudates": "硬性渗出",
    "Drusen": "玻璃膜疣",
    "Venous beading": "静脉串珠",
    "Macular edema": "黄斑水肿",
    "Retinal vein occlusion": "视网膜静脉阻塞",
}

# 腹部检测类别中英文映射
CLASS_NAME_CN_ABDOMEN = {
    "Liver lesion": "肝脏病变",
    "Gallbladder stone": "胆囊结石",
    "Bile duct dilation": "胆管扩张",
    "Pancreatic mass": "胰腺占位",
    "Splenomegaly": "脾大",
    "Renal cyst": "肾囊肿",
    "Renal stone": "肾结石",
    "Hydronephrosis": "肾积水",
    "Adrenal mass": "肾上腺占位",
    "Ascites": "腹水",
    "Abdominal lymphadenopathy": "腹部淋巴结肿大",
    "Bowel obstruction": "肠梗阻",
    "Abdominal aortic aneurysm": "腹主动脉瘤",
    "Peritoneal thickening": "腹膜增厚",
}

# 脊柱检测类别中英文映射
CLASS_NAME_CN_SPINE = {
    "Vertebral compression fracture": "椎体压缩性骨折",
    "Disc herniation": "椎间盘突出",
    "Spinal stenosis": "椎管狭窄",
    "Scoliosis": "脊柱侧弯",
    "Spondylolisthesis": "椎体滑脱",
    "Osteophyte formation": "骨质增生",
    "Schmorl node": "许莫氏结节",
    "Vertebral hemangioma": "椎体血管瘤",
    "Bone metastasis": "骨转移瘤",
    "Ankylosing spondylitis": "强直性脊柱炎",
    "Spinal tuberculosis": "脊柱结核",
    "Ligament ossification": "韧带骨化",
    "Disc degeneration": "椎间盘退变",
    "Spina bifida": "脊柱裂",
}

# 乳腺检测类别中英文映射
CLASS_NAME_CN_BREAST = {
    "Breast mass": "乳腺肿块",
    "Microcalcification": "微钙化",
    "Architectural distortion": "结构扭曲",
    "Asymmetry": "不对称致密",
    "Skin thickening": "皮肤增厚",
    "Nipple retraction": "乳头内陷",
    "Axillary lymphadenopathy": "腋窝淋巴结肿大",
    "Breast cyst": "乳腺囊肿",
    "Fibroadenoma": "纤维腺瘤",
    "Ductal ectasia": "导管扩张",
    "Intramammary lymph node": "乳腺内淋巴结",
    "Fat necrosis": "脂肪坏死",
    "Focal asymmetry": "局灶性不对称",
    "Breast edema": "乳腺水肿",
}

# 症状描述中英文映射
SYMPTOM_LABELS = {
    "smoke": "吸烟", "cough": "咳嗽", "chestPain": "胸痛", "dyspnea": "呼吸困难",
    "headache": "头痛", "dizziness": "头晕", "nausea": "恶心呕吐",
    "blurredVision": "视力模糊", "eyePain": "眼痛", "visualDefect": "视野缺损",
    "abdominalPain": "腹痛", "jaundice": "黄疸", "bloating": "腹胀",
    "backPain": "腰背痛", "limbNumbness": "肢体麻木", "gaitAbnormal": "行走异常", "trauma": "外伤史",
    "breastLump": "乳房肿块", "breastPain": "乳房疼痛", "nippleDischarge": "乳头溢液", "familyHistory": "家族史",
    "palpitation": "心悸", "hypertension": "高血压病史"
}

def format_symptoms_text(symptoms_json: Optional[str]) -> str:
    """将症状JSON转为可读中文文本，供AI和PDF使用"""
    if not symptoms_json:
        return ""
    try:
        symptoms = json.loads(symptoms_json)
    except (json.JSONDecodeError, TypeError):
        return symptoms_json.strip() if symptoms_json else ""

    if not isinstance(symptoms, dict):
        return str(symptoms)

    parts = []
    for key, value in symptoms.items():
        if key == "custom":
            if value and str(value).strip():
                parts.append(f"其他症状：{value}")
        else:
            label = SYMPTOM_LABELS.get(key, key)
            val_str = str(value).strip()
            if val_str in ("有", "yes", "true", "True", "1"):
                status = "有"
            elif val_str in ("无", "no", "false", "False", "0", ""):
                status = "无"
            else:
                status = val_str
            parts.append(f"{label}：{status}")
    return "；".join(parts) if parts else ""


# 心血管检测类别中英文映射
CLASS_NAME_CN_CARDIOVASCULAR = {
    "Coronary artery stenosis": "冠状动脉狭窄",
    "Coronary calcification": "冠状动脉钙化",
    "Aortic dissection": "主动脉夹层",
    "Aortic stenosis": "主动脉瓣狭窄",
    "Mitral regurgitation": "二尖瓣反流",
    "Left ventricular hypertrophy": "左心室肥厚",
    "Cardiac thrombus": "心腔内血栓",
    "Pericardial effusion": "心包积液",
    "Pulmonary embolism": "肺栓塞",
    "Deep vein thrombosis": "深静脉血栓",
    "Carotid artery plaque": "颈动脉斑块",
    "Ventricular aneurysm": "室壁瘤",
    "Atrial septal defect": "房间隔缺损",
    "Aortic valve calcification": "主动脉瓣钙化",
}


@app.post("/api/chest-xray/analyze", response_model=ApiResponse)
async def analyze_chest_xray(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Chest X-ray AI analysis endpoint.
    Receives image, calls Qwen-VL via DashScope API, returns detections + AI report.
    """
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 调用 Qwen-VL 视觉模型进行异常检测和诊断报告生成
        try:
            qwen_result = await qwen_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        ai_report_text = qwen_result.get("diagnosis", "")
        impression_text = qwen_result.get("impression", "")
        quality_text = qwen_result.get("quality_assessment", "")
        anatomical = qwen_result.get("anatomical_findings", {})

        # 添加中文类别名称
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN.get(en_name, en_name)

        # 构建 fallback 诊断文字
        if not ai_report_text and detections:
            class_names_cn = [d.get("class_name_cn", "未知") for d in detections]
            ai_report_text = f"检测到 {len(detections)} 处异常: {', '.join(class_names_cn)}。建议结合临床症状进一步评估，必要时进行CT检查确认。"

        report_id = f"report_{uuid.uuid4().hex[:8]}"

        # 读取原图并生成标注图
        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": quality_text or "未提供",
            "anatomical_findings": anatomical if anatomical else {},
            "diagnosis": ai_report_text or "模型未返回诊断结果",
            "impression": impression_text or "",
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        # 生成 PDF 格式风格的文本报告（供前端展示）
        report_lines = []
        report_lines.append("╔══════════════════════════════════════╗")
        report_lines.append("║     胸部X光智能分析报告 (AI)        ║")
        report_lines.append("╚══════════════════════════════════════╝")
        report_lines.append("")
        report_lines.append(f"报告编号: {report_id}")
        report_lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"检测异常数: {len(detections)}")
        if symptoms_text:
            report_lines.append("")
            report_lines.append("━" * 40)
            report_lines.append("【零、患者症状描述】")
            report_lines.append(f"  {symptoms_text}")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【一、影像质量评估】")
        report_lines.append(quality_text or "未提供影像质量评估")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【二、解剖分区影像所见】")
        if anatomical:
            region_labels = {
                "lung_fields": "双肺野", "pleura": "胸膜", "mediastinum": "纵隔",
                "heart": "心脏", "diaphragm": "膈肌", "bones": "骨骼", "soft_tissue": "软组织"
            }
            for key, label in region_labels.items():
                value = anatomical.get(key, "")
                if not value:
                    value = "未见明显异常"
                report_lines.append(f"  > {label}：{value}")
        else:
            report_lines.append("  未提供分区描述")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【三、异常检测列表】")
        if detections:
            for i, det in enumerate(detections, 1):
                cn = det.get("class_name_cn", det.get("class_name", "未知"))
                conf = det.get("confidence", 0)
                desc = det.get("description", "")
                approx = " (约)" if det.get("bbox_approximate") else ""
                report_lines.append(f"  {i}. {cn}{approx} [置信度: {conf:.0%}]")
                if desc:
                    report_lines.append(f"     影像特征：{desc}")
        else:
            report_lines.append("  未检测到明确异常")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【四、诊断汇总】")
        for line in ai_report_text.split("\n"):
            if line.strip():
                report_lines.append(f"  {line.strip()}")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【五、影像学印象】")
        impression = impression_text or "未提供影像学印象"
        for line in impression.split("\n"):
            if line.strip():
                report_lines.append(f"  - {line.strip()}")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【六、临床建议】")
        recommendations = qwen_result.get("recommendations", "建议由专业医生复核")
        for line in recommendations.split("\n"):
            if line.strip():
                report_lines.append(f"  - {line.strip()}")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("【七、患者须知】")
        patient_friendly = qwen_result.get("patient_friendly", "请咨询医生获取详细解读")
        for line in patient_friendly.split("\n"):
            if line.strip():
                report_lines.append(f"  {line.strip()}")
        report_lines.append("")
        report_lines.append("━" * 40)
        report_lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
        report_lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")

        formatted_report = "\n".join(report_lines)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            pdf_path = generate_pdf_report(
                report_id=report_id, modality="chest",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()

@app.post("/api/chest-xray/save", response_model=ApiResponse)
async def save_chest_xray_result(request: ImageResultSave, db: Session = Depends(get_db)):
    """
    Save chest X-ray analysis result to database.
    """
    try:
        image = MedicalImage(
            patient_name=request.patient_name,
            patient_id=request.patient_id,
            image_type="胸片",
            original_filename=request.original_filename,
            detections=request.detections,
            report_content=request.report_content,
            annotated_image=base64.b64decode(request.annotated_image_base64) if request.annotated_image_base64 else b'',
            status="已完成"
        )

        db.add(image)
        db.commit()
        db.refresh(image)

        return ApiResponse(data={
            "id": image.id,
            "patientName": image.patient_name,
            "status": image.status,
            "createTime": image.create_time.isoformat() if image.create_time else None
        })
    except Exception as e:
        db.rollback()
        return ApiResponse(code=500, message=f"保存失败: {str(e)}")


# ========== PDF报告接口 ==========
@app.get("/api/report/{report_id}/pdf")
async def get_report_pdf(report_id: str):
    """Serve generated PDF report file."""
    from fastapi.responses import FileResponse
    pdf_path = REPORTS_DIR / f"{report_id}.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或尚未生成")
    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"{report_id}.pdf"
    )


# ========== 脑部影像AI分析接口 ==========

BRAIN_REGION_LABELS = {
    "skull": "颅骨", "extra_axial": "硬膜外/下及蛛网膜下腔",
    "brain_parenchyma": "脑实质", "ventricles": "脑室系统",
    "midline": "中线结构", "vessels": "血管", "sella": "蝶鞍区"
}


def format_brain_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format brain analysis result into structured report text."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║     脑部影像智能分析报告 (AI)        ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")
    lines.append(f"报告编号: {report_id}")
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"检测异常数: {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append("━" * 40)
        lines.append("【零、患者症状描述】")
        lines.append(f"  {symptoms_text}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【一、影像质量评估】")
    lines.append(quality or "未提供影像质量评估")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【二、解剖分区影像所见】")
    if anatomical:
        for key, label in BRAIN_REGION_LABELS.items():
            value = anatomical.get(key, "")
            if not value:
                value = "未见明显异常"
            lines.append(f"  > {label}：{value}")
    else:
        lines.append("  未提供分区描述")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【三、异常检测列表】")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term = det.get("term_explanation", "")
            clinical = det.get("clinical_significance", "")
            lines.append(f"  {i}. {cn} [置信度: {conf:.0%}]")
            if desc:
                lines.append(f"     影像特征：{desc}")
            if term:
                lines.append(f"     术语解释：{term}")
            if clinical:
                lines.append(f"     临床意义：{clinical}")
    else:
        lines.append("  未检测到明确异常")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【四、诊断汇总】")
    for line in diagnosis.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【五、影像学印象】")
    for line in (impression or "未提供").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【六、临床建议】")
    for line in (recommendations or "建议由专业医生复核").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【七、患者须知】")
    for line in (patient_friendly or "请咨询医生获取详细解读").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
    lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")
    return "\n".join(lines)


@app.post("/api/brain/analyze", response_model=ApiResponse)
async def analyze_brain(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Brain CT/MRI AI analysis endpoint."""
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"brain_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_brain_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN_BRAIN.get(en_name, en_name)

        if not qwen_result.get("diagnosis") and detections:
            names_cn = [d.get("class_name_cn", "未知") for d in detections]
            qwen_result["diagnosis"] = f"检测到 {len(detections)} 处异常: {', '.join(names_cn)}。建议结合临床症状进一步评估。"

        report_id = f"brain_{uuid.uuid4().hex[:8]}"

        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": qwen_result.get("quality_assessment", "未提供"),
            "anatomical_findings": qwen_result.get("anatomical_findings", {}),
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": qwen_result.get("impression", ""),
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        formatted_report = format_brain_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            generate_pdf_report(
                report_id=report_id, modality="brain",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate brain PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ========== 视网膜影像AI分析接口 ==========

RETINA_REGION_LABELS = {
    "optic_disc": "视盘", "macula": "黄斑",
    "retinal_vessels": "视网膜血管", "posterior_pole": "后极部视网膜",
    "peripheral_retina": "周边视网膜", "vitreous": "玻璃体"
}

# 腹部区域标签
ABDOMEN_REGION_LABELS = {
    "liver": "肝脏", "gallbladder_biliary": "胆囊及胆道",
    "pancreas": "胰腺", "spleen": "脾脏",
    "kidneys_adrenals": "双肾及肾上腺", "gi_tract": "胃肠道",
    "peritoneum": "腹膜腔", "vessels": "腹部血管",
    "lymph_nodes": "淋巴结", "abdominal_wall": "腹壁"
}

# 脊柱区域标签
SPINE_REGION_LABELS = {
    "spinal_curvature": "脊柱曲度", "vertebral_alignment": "椎体序列",
    "vertebral_body": "各椎体", "intervertebral_disc": "椎间盘",
    "spinal_canal": "椎管", "facet_joints": "小关节",
    "ligaments": "韧带", "soft_tissue": "周围软组织"
}

# 乳腺区域标签
BREAST_REGION_LABELS = {
    "skin": "皮肤", "subcutaneous_fat": "皮下脂肪",
    "breast_parenchyma": "乳腺实质", "retroareolar": "乳晕后区",
    "pectoral_muscle": "胸肌", "axilla": "腋窝"
}

# 心血管区域标签
CARDIOVASCULAR_REGION_LABELS = {
    "coronary_arteries": "冠状动脉", "cardiac_chambers": "各腔室",
    "heart_valves": "心脏瓣膜", "myocardium": "心肌",
    "pericardium": "心包", "aorta": "主动脉",
    "pulmonary_vessels": "肺血管", "peripheral_vessels": "外周血管"
}


def format_retina_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format retina analysis result into structured report text."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║     眼底影像智能分析报告 (AI)        ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")
    lines.append(f"报告编号: {report_id}")
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"检测异常数: {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append("━" * 40)
        lines.append("【零、患者症状描述】")
        lines.append(f"  {symptoms_text}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【一、影像质量评估】")
    lines.append(quality or "未提供影像质量评估")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【二、解剖结构影像所见】")
    if anatomical:
        for key, label in RETINA_REGION_LABELS.items():
            value = anatomical.get(key, "")
            if not value:
                value = "未见明显异常"
            lines.append(f"  > {label}：{value}")
    else:
        lines.append("  未提供分区描述")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【三、异常检测列表】")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term = det.get("term_explanation", "")
            clinical = det.get("clinical_significance", "")
            lines.append(f"  {i}. {cn} [置信度: {conf:.0%}]")
            if desc:
                lines.append(f"     影像特征：{desc}")
            if term:
                lines.append(f"     术语解释：{term}")
            if clinical:
                lines.append(f"     临床意义：{clinical}")
    else:
        lines.append("  未检测到明确异常")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【四、诊断汇总】")
    for line in diagnosis.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【五、影像学印象】")
    for line in (impression or "未提供").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【六、临床建议】")
    for line in (recommendations or "建议由专业医生复核").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【七、患者须知】")
    for line in (patient_friendly or "请咨询医生获取详细解读").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
    lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")
    return "\n".join(lines)


@app.post("/api/retina/analyze", response_model=ApiResponse)
async def analyze_retina(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Retinal fundus image AI analysis endpoint."""
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"retina_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_retina_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN_RETINA.get(en_name, en_name)

        if not qwen_result.get("diagnosis") and detections:
            names_cn = [d.get("class_name_cn", "未知") for d in detections]
            qwen_result["diagnosis"] = f"检测到 {len(detections)} 处异常: {', '.join(names_cn)}。建议结合临床症状进一步评估。"

        report_id = f"retina_{uuid.uuid4().hex[:8]}"

        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": qwen_result.get("quality_assessment", "未提供"),
            "anatomical_findings": qwen_result.get("anatomical_findings", {}),
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": qwen_result.get("impression", ""),
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        formatted_report = format_retina_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            generate_pdf_report(
                report_id=report_id, modality="retina",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate retina PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ========== CT影像AI分析 — 项目演示报告接口 ==========

DEMO_DISCLAIMER = """## 免责声明

> **重要提示：**
>
> **本报告仅供 AI 项目算法演示与技术交流使用，不构成任何临床诊断意见，不作为疾病诊疗、用药或健康管理的依据。**
>
> 报告中呈现的全部影像学特征描述均为 AI 模型自动识别的结果，未经执业医师审核确认。如涉及真实患者影像，请务必由具备相应资质的临床医生结合完整病史、体格检查、实验室检验等信息进行综合判断。"""

DEMO_LIMITATIONS = """## 四、AI 模型局限性说明

**1. AI 仅为辅助工具，不能替代医生诊断**
AI 模型输出的是影像学特征识别结果，而非最终诊断结论。真正的临床诊断需要医生综合患者的病史、症状、体格检查、实验室检验以及其他影像学检查后作出。

**2. AI 可能存在的误判与漏判**
- **假阳性（过度识别）：** AI 可能将正常解剖变异、伪影或良性退行性改变误判为异常。
- **假阴性（漏诊）：** 对于体积微小、密度变化不明显、或与周围组织分界不清的病灶，AI 可能出现漏判。
- **影像质量影响：** 扫描参数、层厚、呼吸伪影、金属植入物伪影等因素均可能降低 AI 分析准确性。
- **罕见/复杂病例：** AI 的训练数据通常以常见疾病为主，对于罕见病、不典型表现或复合病变，识别能力可能不足。

**3. AI 不具备临床推理能力**
AI 模型只能根据输入的影像给出模式匹配结果，不具备人类医生的临床推理、经验判断和综合决策能力。"""


def format_demo_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format Qwen-VL CT analysis result into a project-demo-quality Markdown report."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    # Separate positive and negative findings
    positive_lines = []
    negative_lines = []
    for line in diagnosis.split("\n"):
        line = line.strip()
        if not line:
            continue
        if any(kw in line for kw in ["未见", "无异常", "正常", "未见明显", "无明确", "未发现"]):
            negative_lines.append(line)
        else:
            positive_lines.append(line)

    lines = []
    # Title
    lines.append("# AI 辅助胸部影像学诊断报告")
    lines.append("")
    lines.append("## （项目演示版）")
    lines.append("")
    lines.append(f"**报告编号：** {report_id}")
    lines.append(f"**生成时间：** {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    lines.append(f"**AI 模型：** Qwen-VL (Alibaba Cloud DashScope)")
    lines.append(f"**检测异常数：** {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append(f"**患者症状描述：** {symptoms_text}")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(DEMO_DISCLAIMER)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 1: Patient Info (placeholder)
    lines.append("## 一、患者基本信息")
    lines.append("")
    lines.append("| 项目 | 内容 |")
    lines.append("|------|------|")
    lines.append("| 姓 名 | **（待填写）** |")
    lines.append("| 性 别 | **（待填写）** |")
    lines.append("| 年 龄 | **（待填写）** |")
    lines.append("| 检查日期 | **（待填写）** |")
    lines.append("| 检查类型 | 胸部 CT 平扫 |")
    lines.append("| 检查部位 | 胸部（含纵隔、双肺、胸膜、胸壁） |")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 2: AI Core Conclusion
    lines.append("## 二、AI 诊断核心结论（摘要）")
    lines.append("")

    pos_count = len([d for d in detections if d.get("class_name")])
    neg_count = sum(1 for _ in negative_lines)

    # Build summary paragraph
    summary_parts = []
    summary_parts.append("本次 AI 模型对胸部 CT 影像进行了逐区域分析。")

    if pos_count > 0:
        detection_names = []
        for d in detections:
            cn = d.get("class_name_cn", d.get("class_name", "未知"))
            detection_names.append(cn)
        summary_parts.append(f"共识别出 **{pos_count} 项阳性发现**：{', '.join(detection_names)}。")

    if negative_lines:
        summary_parts.append(f"同时明确了 **{len(negative_lines)} 项阴性正常结果**（如{'、'.join(negative_lines[:3])}等），具有排除性诊断价值。")
    else:
        summary_parts.append("未发现明确异常征象。")

    if impression:
        first_impression = impression.split("\n")[0].strip()
        summary_parts.append(f"最需关注的影像学征象为：**{first_impression}**。")

    lines.append("> " + " ".join(summary_parts))
    lines.append("")

    if positive_lines:
        lines.append("**阳性发现（需关注）：**")
        for pl in positive_lines:
            lines.append(f"- {pl}")
        lines.append("")

    if negative_lines:
        lines.append("**阴性正常结果（排除性价值）：**")
        for nl in negative_lines:
            lines.append(f"- {nl}")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Section 3: Detailed findings
    lines.append("## 三、各诊断结果详细解读")
    lines.append("")

    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            en = det.get("class_name", "未知")
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term_exp = det.get("term_explanation", "")
            clin_sig = det.get("clinical_significance", "")

            lines.append(f"### 结果 {i}：{cn}（{en}）")
            lines.append("")
            lines.append(f"**置信度：** {conf:.0%}")
            lines.append("")

            if desc:
                lines.append(f"**影像特征描述：** {desc}")
                lines.append("")

            lines.append("#### 【术语解释】")
            lines.append("")
            if term_exp:
                lines.append(term_exp)
            else:
                lines.append(f'该发现指影像中出现了与正常解剖结构不符的异常表现，AI 模型将其归类为"{cn}"。具体含义需由影像科医生结合临床资料进一步解读。')
            lines.append("")

            lines.append("#### 【临床意义】")
            lines.append("")
            if clin_sig:
                lines.append(clin_sig)
            else:
                lines.append(f"此发现可能提示胸部存在器质性改变。具体原因多样，可能包括炎症、退行性变、良性病变或其他情况。建议由临床医生结合完整病史和体格检查进行综合评估，必要时安排进一步检查。")
            lines.append("")

            lines.append("#### 【项目说明】")
            lines.append("")
            lines.append(f"*此为 AI 模型基于胸部 CT 影像自动识别的影像学特征（类别：{cn}，置信度：{conf:.0%}）。该结果仅供项目演示参考，需由临床医生结合病史、症状、体格检查及其他辅助检查综合判断，不可单独作为诊疗依据。*")
            lines.append("")
    else:
        lines.append("*本次 AI 分析未检测到明确的异常影像学征象。如临床仍有疑虑，建议由影像科医生人工复核。*")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Section 4: AI Limitations
    lines.append(DEMO_LIMITATIONS)
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 5: Project Summary
    lines.append("## 五、项目总结与声明")
    lines.append("")

    lines.append("本报告基于 **医疗影像 AI 辅助诊断系统** 演示项目自动生成，全部诊断描述来源于 AI 模型对胸部 CT 影像的算法分析，旨在展示以下 AI 辅助诊断能力：")
    lines.append("")
    if pos_count > 0:
        lines.append(f"- **多征象同步检测：** 模型可同时识别 {pos_count} 类不同的影像学特征（{', '.join(detection_names)}），无需针对每种疾病单独部署模型。")

    if negative_lines:
        lines.append("- **阳性与阴性综合判断：** 模型不仅输出异常发现，同时明确标注正常结果，辅助临床缩小鉴别诊断范围、避免过度检查。")

    if any(d.get("confidence", 0) >= 0.7 for d in detections):
        lines.append("- **高置信度异常检出：** 对明显异常征象具有较高识别置信度，可作为临床筛查的\"第一道防线\"。")

    lines.append("- **结构化报告生成：** AI 自动输出包含术语解释、临床意义、影像学印象的结构化报告，降低非专业观众的理解门槛。")
    lines.append("")
    lines.append("> **再次声明：** 本报告仅供 AI 项目演示与技术展示使用，所有 AI 输出结果均 **不能作为临床诊断、治疗决策或健康评估的依据**。实际临床工作中，影像诊断必须由执业医师在充分了解患者临床信息后出具正式诊断报告。")
    lines.append(">")
    lines.append("> AI 辅助诊断的价值在于**提升效率、减少遗漏、辅助决策**，而非替代医生。AI 与医生的关系应是\"**人机协同**\"，共同为患者健康保驾护航。")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*报告结束 · 医疗影像 AI 辅助诊断系统 © 2026 项目演示版*")

    return "\n".join(lines)


@app.post("/api/ct/demo-report", response_model=ApiResponse)
async def ct_demo_report(
    file: UploadFile = File(...),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    CT AI demo report endpoint — returns a detailed project-demo-quality Markdown report.
    Accepts a CT image, runs Qwen-VL analysis, and formats all findings into the demo template.
    """
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".dcm", ".tiff", ".tif"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".png"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"ct_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_ct_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        impression_text = qwen_result.get("impression", "")
        quality_text = qwen_result.get("quality_assessment", "")
        anatomical = qwen_result.get("anatomical_findings", {})

        # Add Chinese class names
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN.get(en_name, en_name)

        report_id = f"ct_report_{uuid.uuid4().hex[:8]}"

        # Read original image
        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        # Draw annotated image
        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        # Build structured ai_report
        ai_report = {
            "quality_assessment": quality_text or "未提供",
            "anatomical_findings": anatomical if anatomical else {},
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": impression_text or "",
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        # Generate demo-format Markdown report
        formatted_demo_report = format_demo_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            generate_pdf_report(
                report_id=report_id, modality="ct",
                detections=detections, ai_report=ai_report,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate CT PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_demo_report": formatted_demo_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ========== CT影像AI分析接口 (ResNet50) ==========
from model_service import analyze_ct_image
from qwen_service import analyze_chest_xray as qwen_analyze
from qwen_service import analyze_ct_image as qwen_ct_analyze
from qwen_service import analyze_brain_image as qwen_brain_analyze
from qwen_service import analyze_retina_image as qwen_retina_analyze
from qwen_service import analyze_abdomen_image as qwen_abdomen_analyze
from qwen_service import analyze_spine_image as qwen_spine_analyze
from qwen_service import analyze_breast_image as qwen_breast_analyze
from qwen_service import analyze_cardiovascular_image as qwen_cardiovascular_analyze
from pdf_generator import generate_pdf_report

@app.post("/api/ct/analyze", response_model=ApiResponse)
async def analyze_ct(
    image_base64: str,
    patient_name: Optional[str] = None,
    patient_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    CT影像AI病灶分析接口
    - image_base64: CT图片的base64编码 (必填)
    - patient_name: 患者姓名 (可选)
    - patient_id: 体检号 (可选)
    返回: 病灶检测结果 + AI报告
    """
    try:
        result = analyze_ct_image(image_base64)

        # 同时保存到数据库
        image = MedicalImage(
            patient_name=patient_name or "未知",
            patient_id=patient_id,
            image_type="CT",
            detections=json.dumps({
                "lesion_detected": result.get('lesion_detected'),
                "lesion_type": result.get('lesion_type'),
                "confidence": result.get('confidence'),
                "position": result.get('position'),
                "severity": result.get('severity')
            }, ensure_ascii=False),
            report_content=result.get('report', ''),
            status="已完成"
        )

        if result.get('annotated_image'):
            image.annotated_image = base64.b64decode(result['annotated_image'])

        db.add(image)
        db.commit()
        db.refresh(image)

        # Generate PDF if report exists
        pdf_url = None
        if result.get('report'):
            try:
                report_id = f"ct_{image.id}"
                generate_pdf_report(
                    report_id=report_id, modality="ct",
                    detections=[{
                        "class_name": result.get('lesion_type', ''),
                        "class_name_cn": CLASS_NAME_CN.get(result.get('lesion_type', ''), result.get('lesion_type', '')),
                        "confidence": float(result.get('confidence', 0)),
                        "position": result.get('position', ''),
                        "severity": result.get('severity', '')
                    }],
                    ai_report={"diagnosis": result.get('report', '')},
                    user_info={"name": patient_name or "未知", "patient_id": patient_id}
                )
                pdf_url = f"/api/report/{report_id}/pdf"
            except Exception as e:
                print(f"[PDF] Failed to generate CT PDF: {e}")

        return ApiResponse(data={
            "id": image.id,
            "patientName": image.patient_name,
            "lesionDetected": result.get('lesion_detected'),
            "lesionType": result.get('lesion_type'),
            "confidence": result.get('confidence'),
            "position": result.get('position'),
            "severity": result.get('severity'),
            "report": result.get('report'),
            "status": image.status,
            "pdf_url": pdf_url
        })
    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
async def save_detection_result(request: ImageResultSave, db: Session = Depends(get_db)):
    image = MedicalImage(
        patient_name=request.patient_name,
        patient_id=request.patient_id,
        image_type=request.image_type,
        original_filename=request.original_filename,
        detections=request.detections,
        report_content=request.report_content,
        status="已完成"
    )

    if request.annotated_image_base64:
        image.annotated_image = base64.b64decode(request.annotated_image_base64)

    db.add(image)
    db.commit()
    db.refresh(image)

    return ApiResponse(data={
        "id": image.id,
        "patientName": image.patient_name,
        "status": image.status,
        "createTime": image.create_time.isoformat() if image.create_time else None
    })

@app.get("/api/images", response_model=ApiResponse)
async def get_images(
    patientName: Optional[str] = None,
    patientId: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(MedicalImage)

    if patientId:
        query = query.filter(MedicalImage.patient_id == patientId)
    elif patientName:
        query = query.filter(MedicalImage.patient_name.contains(patientName))

    images = query.order_by(MedicalImage.create_time.desc()).all()

    return ApiResponse(data=[
        {
            "id": img.id,
            "patientName": img.patient_name,
            "patientId": img.patient_id,
            "imageType": img.image_type,
            "originalFilename": img.original_filename,
            "detections": img.detections,
            "reportContent": img.report_content,
            "status": img.status,
            "createTime": img.create_time.isoformat() if img.create_time else None
        } for img in images
    ])

@app.get("/api/images/{image_id}", response_model=ApiResponse)
async def get_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(MedicalImage).filter(MedicalImage.id == image_id).first()
    if not image:
        return ApiResponse(code=404, message="记录不存在")

    return ApiResponse(data={
        "id": image.id,
        "patientName": image.patient_name,
        "patientId": image.patient_id,
        "imageType": image.image_type,
        "originalFilename": image.original_filename,
        "detections": image.detections,
        "reportContent": image.report_content,
        "status": image.status,
        "createTime": image.create_time.isoformat() if image.create_time else None
    })

@app.get("/api/images/{image_id}/image", response_model=ApiResponse)
async def get_image_data(image_id: int, db: Session = Depends(get_db)):
    image = db.query(MedicalImage).filter(MedicalImage.id == image_id).first()
    if not image or not image.annotated_image:
        return ApiResponse(code=404, message="图片不存在")

    base64_image = base64.b64encode(image.annotated_image).decode()
    return ApiResponse(data={"image": base64_image})

@app.delete("/api/images/{image_id}", response_model=ApiResponse)
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(MedicalImage).filter(MedicalImage.id == image_id).first()
    if not image:
        return ApiResponse(code=404, message="记录不存在")

    db.delete(image)
    db.commit()
    return ApiResponse(message="删除成功")

# ========== 腹部影像AI分析接口 ==========

def format_abdomen_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format abdomen analysis result into structured report text."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║     腹部影像智能分析报告 (AI)        ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")
    lines.append(f"报告编号: {report_id}")
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"检测异常数: {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append("━" * 40)
        lines.append("【零、患者症状描述】")
        lines.append(f"  {symptoms_text}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【一、影像质量评估】")
    lines.append(quality or "未提供影像质量评估")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【二、解剖分区影像所见】")
    if anatomical:
        for key, label in ABDOMEN_REGION_LABELS.items():
            value = anatomical.get(key, "")
            if not value:
                value = "未见明显异常"
            lines.append(f"  > {label}：{value}")
    else:
        lines.append("  未提供分区描述")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【三、异常检测列表】")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term = det.get("term_explanation", "")
            clinical = det.get("clinical_significance", "")
            lines.append(f"  {i}. {cn} [置信度: {conf:.0%}]")
            if desc:
                lines.append(f"     影像特征：{desc}")
            if term:
                lines.append(f"     术语解释：{term}")
            if clinical:
                lines.append(f"     临床意义：{clinical}")
    else:
        lines.append("  未检测到明确异常")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【四、诊断汇总】")
    for line in diagnosis.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【五、影像学印象】")
    for line in (impression or "未提供").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【六、临床建议】")
    for line in (recommendations or "建议由专业医生复核").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【七、患者须知】")
    for line in (patient_friendly or "请咨询医生获取详细解读").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
    lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")
    return "\n".join(lines)


@app.post("/api/abdomen/analyze", response_model=ApiResponse)
async def analyze_abdomen(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Abdomen CT/MRI/Ultrasound AI analysis endpoint."""
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"abdomen_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_abdomen_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN_ABDOMEN.get(en_name, en_name)

        if not qwen_result.get("diagnosis") and detections:
            names_cn = [d.get("class_name_cn", "未知") for d in detections]
            qwen_result["diagnosis"] = f"检测到 {len(detections)} 处异常: {', '.join(names_cn)}。建议结合临床症状进一步评估。"

        report_id = f"abdomen_{uuid.uuid4().hex[:8]}"

        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": qwen_result.get("quality_assessment", "未提供"),
            "anatomical_findings": qwen_result.get("anatomical_findings", {}),
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": qwen_result.get("impression", ""),
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        formatted_report = format_abdomen_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            generate_pdf_report(
                report_id=report_id, modality="abdomen",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate abdomen PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ========== 脊柱影像AI分析接口 ==========

def format_spine_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format spine analysis result into structured report text."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║     脊柱影像智能分析报告 (AI)        ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")
    lines.append(f"报告编号: {report_id}")
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"检测异常数: {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append("━" * 40)
        lines.append("【零、患者症状描述】")
        lines.append(f"  {symptoms_text}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【一、影像质量评估】")
    lines.append(quality or "未提供影像质量评估")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【二、解剖结构影像所见】")
    if anatomical:
        for key, label in SPINE_REGION_LABELS.items():
            value = anatomical.get(key, "")
            if not value:
                value = "未见明显异常"
            lines.append(f"  > {label}：{value}")
    else:
        lines.append("  未提供分区描述")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【三、异常检测列表】")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term = det.get("term_explanation", "")
            clinical = det.get("clinical_significance", "")
            lines.append(f"  {i}. {cn} [置信度: {conf:.0%}]")
            if desc:
                lines.append(f"     影像特征：{desc}")
            if term:
                lines.append(f"     术语解释：{term}")
            if clinical:
                lines.append(f"     临床意义：{clinical}")
    else:
        lines.append("  未检测到明确异常")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【四、诊断汇总】")
    for line in diagnosis.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【五、影像学印象】")
    for line in (impression or "未提供").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【六、临床建议】")
    for line in (recommendations or "建议由专业医生复核").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【七、患者须知】")
    for line in (patient_friendly or "请咨询医生获取详细解读").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
    lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")
    return "\n".join(lines)


@app.post("/api/spine/analyze", response_model=ApiResponse)
async def analyze_spine(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Spine X-ray/CT/MRI AI analysis endpoint."""
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"spine_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_spine_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN_SPINE.get(en_name, en_name)

        if not qwen_result.get("diagnosis") and detections:
            names_cn = [d.get("class_name_cn", "未知") for d in detections]
            qwen_result["diagnosis"] = f"检测到 {len(detections)} 处异常: {', '.join(names_cn)}。建议结合临床症状进一步评估。"

        report_id = f"spine_{uuid.uuid4().hex[:8]}"

        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": qwen_result.get("quality_assessment", "未提供"),
            "anatomical_findings": qwen_result.get("anatomical_findings", {}),
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": qwen_result.get("impression", ""),
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        formatted_report = format_spine_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            generate_pdf_report(
                report_id=report_id, modality="spine",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate spine PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ========== 乳腺影像AI分析接口 ==========

def format_breast_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format breast analysis result into structured report text."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║     乳腺影像智能分析报告 (AI)        ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")
    lines.append(f"报告编号: {report_id}")
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"检测异常数: {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append("━" * 40)
        lines.append("【零、患者症状描述】")
        lines.append(f"  {symptoms_text}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【一、影像质量评估】")
    lines.append(quality or "未提供影像质量评估")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【二、解剖结构影像所见】")
    if anatomical:
        for key, label in BREAST_REGION_LABELS.items():
            value = anatomical.get(key, "")
            if not value:
                value = "未见明显异常"
            lines.append(f"  > {label}：{value}")
    else:
        lines.append("  未提供分区描述")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【三、异常检测列表】")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term = det.get("term_explanation", "")
            clinical = det.get("clinical_significance", "")
            lines.append(f"  {i}. {cn} [置信度: {conf:.0%}]")
            if desc:
                lines.append(f"     影像特征：{desc}")
            if term:
                lines.append(f"     术语解释：{term}")
            if clinical:
                lines.append(f"     临床意义：{clinical}")
    else:
        lines.append("  未检测到明确异常")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【四、诊断汇总】")
    for line in diagnosis.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【五、影像学印象】")
    for line in (impression or "未提供").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【六、临床建议】")
    for line in (recommendations or "建议由专业医生复核").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【七、患者须知】")
    for line in (patient_friendly or "请咨询医生获取详细解读").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
    lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")
    return "\n".join(lines)


@app.post("/api/breast/analyze", response_model=ApiResponse)
async def analyze_breast(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Breast mammography/ultrasound/MRI AI analysis endpoint."""
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"breast_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_breast_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN_BREAST.get(en_name, en_name)

        if not qwen_result.get("diagnosis") and detections:
            names_cn = [d.get("class_name_cn", "未知") for d in detections]
            qwen_result["diagnosis"] = f"检测到 {len(detections)} 处异常: {', '.join(names_cn)}。建议结合临床症状进一步评估。"

        report_id = f"breast_{uuid.uuid4().hex[:8]}"

        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": qwen_result.get("quality_assessment", "未提供"),
            "anatomical_findings": qwen_result.get("anatomical_findings", {}),
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": qwen_result.get("impression", ""),
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        formatted_report = format_breast_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            generate_pdf_report(
                report_id=report_id, modality="breast",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate breast PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


# ========== 心血管影像AI分析接口 ==========

def format_cardiovascular_report(qwen_result: dict, report_id: str, symptoms_text: str = "") -> str:
    """Format cardiovascular analysis result into structured report text."""
    detections = qwen_result.get("detections", [])
    quality = qwen_result.get("quality_assessment", "未提供")
    anatomical = qwen_result.get("anatomical_findings", {})
    diagnosis = qwen_result.get("diagnosis", "")
    impression = qwen_result.get("impression", "")
    recommendations = qwen_result.get("recommendations", "")
    patient_friendly = qwen_result.get("patient_friendly", "")

    lines = []
    lines.append("╔══════════════════════════════════════╗")
    lines.append("║   心血管影像智能分析报告 (AI)        ║")
    lines.append("╚══════════════════════════════════════╝")
    lines.append("")
    lines.append(f"报告编号: {report_id}")
    lines.append(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"检测异常数: {len(detections)}")
    if symptoms_text:
        lines.append("")
        lines.append("━" * 40)
        lines.append("【零、患者症状描述】")
        lines.append(f"  {symptoms_text}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【一、影像质量评估】")
    lines.append(quality or "未提供影像质量评估")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【二、解剖结构影像所见】")
    if anatomical:
        for key, label in CARDIOVASCULAR_REGION_LABELS.items():
            value = anatomical.get(key, "")
            if not value:
                value = "未见明显异常"
            lines.append(f"  > {label}：{value}")
    else:
        lines.append("  未提供分区描述")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【三、异常检测列表】")
    if detections:
        for i, det in enumerate(detections, 1):
            cn = det.get("class_name_cn", det.get("class_name", "未知"))
            conf = det.get("confidence", 0)
            desc = det.get("description", "")
            term = det.get("term_explanation", "")
            clinical = det.get("clinical_significance", "")
            lines.append(f"  {i}. {cn} [置信度: {conf:.0%}]")
            if desc:
                lines.append(f"     影像特征：{desc}")
            if term:
                lines.append(f"     术语解释：{term}")
            if clinical:
                lines.append(f"     临床意义：{clinical}")
    else:
        lines.append("  未检测到明确异常")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【四、诊断汇总】")
    for line in diagnosis.split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【五、影像学印象】")
    for line in (impression or "未提供").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【六、临床建议】")
    for line in (recommendations or "建议由专业医生复核").split("\n"):
        if line.strip():
            lines.append(f"  - {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("【七、患者须知】")
    for line in (patient_friendly or "请咨询医生获取详细解读").split("\n"):
        if line.strip():
            lines.append(f"  {line.strip()}")
    lines.append("")
    lines.append("━" * 40)
    lines.append("免责声明：本报告由AI辅助生成，仅供专业医疗人员参考，")
    lines.append("不作为最终诊断依据。最终诊断应由执业医师做出。")
    return "\n".join(lines)


@app.post("/api/cardiovascular/analyze", response_model=ApiResponse)
async def analyze_cardiovascular(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    symptoms: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Cardiovascular CTA/MRA/Ultrasound AI analysis endpoint."""
    symptoms_text = format_symptoms_text(symptoms)
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    temp_path = UPLOAD_DIR / f"cardio_{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        try:
            qwen_result = await qwen_cardiovascular_analyze(temp_path, symptoms_text)
        except RuntimeError as e:
            return ApiResponse(code=503, message=str(e))

        detections = qwen_result.get("detections", [])
        for d in detections:
            en_name = d.get("class_name", "")
            d["class_name_cn"] = CLASS_NAME_CN_CARDIOVASCULAR.get(en_name, en_name)

        if not qwen_result.get("diagnosis") and detections:
            names_cn = [d.get("class_name_cn", "未知") for d in detections]
            qwen_result["diagnosis"] = f"检测到 {len(detections)} 处异常: {', '.join(names_cn)}。建议结合临床症状进一步评估。"

        report_id = f"cardio_{uuid.uuid4().hex[:8]}"

        with open(temp_path, "rb") as f:
            original_image_b64 = base64.b64encode(f.read()).decode("utf-8")
        original_image = f"data:image/{file_ext[1:]};base64,{original_image_b64}"

        annotated_image = None
        if detections:
            annotated_b64 = draw_bboxes_pil(str(temp_path), detections)
            annotated_image = f"data:image/png;base64,{annotated_b64}"

        ai_report = {
            "quality_assessment": qwen_result.get("quality_assessment", "未提供"),
            "anatomical_findings": qwen_result.get("anatomical_findings", {}),
            "diagnosis": qwen_result.get("diagnosis", ""),
            "impression": qwen_result.get("impression", ""),
            "recommendations": qwen_result.get("recommendations", ""),
            "patient_friendly": qwen_result.get("patient_friendly", ""),
            "summary": f"共检测到 {len(detections)} 个目标"
        }

        formatted_report = format_cardiovascular_report(qwen_result, report_id, symptoms_text)

        # Generate PDF report
        try:
            user_info_dict = {}
            if user_info:
                user_info_dict = json.loads(user_info)
            generate_pdf_report(
                report_id=report_id, modality="cardiovascular",
                detections=detections, ai_report=ai_report,
                user_info=user_info_dict,
                symptoms_text=symptoms_text,
                original_image_b64=original_image,
                annotated_image_b64=annotated_image
            )
        except Exception as e:
            print(f"[PDF] Failed to generate cardiovascular PDF: {e}")

        return ApiResponse(data={
            "report_id": report_id,
            "detections": detections,
            "ai_report": ai_report,
            "formatted_report": formatted_report,
            "original_image": original_image,
            "annotated_image": annotated_image,
            "pdf_url": f"/api/report/{report_id}/pdf"
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8084)
