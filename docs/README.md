# 医疗档案管理系统 - 技术文档

## 项目概述

Chest X-ray 智能分析系统 - 基于深度学习的胸片检测与医疗档案管理系统，支持多部位医学影像检测、 AI 诊断报告生成及患者档案管理。

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端 (Browser)                          │
│                     Vue 3 + Vite + Axios                        │
└─────────────────────────────────────────────────────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
                    ▼            ▼            ▼
            ┌───────────┐ ┌───────────┐ ┌───────────┐
            │  Frontend  │ │  Backend   │ │  YOLO API  │
            │  :3000     │ │  :8000     │ │  :8001     │
            │  (Nginx)   │ │  (FastAPI) │ │  (FastAPI) │
            └───────────┘ └───────────┘ └───────────┘
                    │            │            │
                    └────────────┼────────────┘
                                 ▼
                    ┌───────────────────────┐
                    │    SQLite Database     │
                    │  medical_system.db     │
                    └───────────────────────┘
```

---

## 技术栈

### 前端
| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.5.x | 渐进式前端框架 |
| Vite | 8.x | 构建工具 |
| Vue Router | 5.x | 路由管理 |
| Axios | 1.15.x | HTTP 客户端 |
| ECharts | - | 图表可视化 |

### 后端
| 技术 | 版本 | 用途 |
|------|------|------|
| FastAPI | 0.109.x | API 框架 |
| Uvicorn | 0.27.x | ASGI 服务器 |
| SQLAlchemy | 2.0.x | ORM |
| Python-Jose | 3.3.x | JWT 认证 |
| ReportLab | - | PDF 生成 |

### AI 服务
| 技术 | 版本 | 用途 |
|------|------|------|
| PyTorch | 2.x | 深度学习框架 |
| Ultralytics YOLO | 8.1.x | 目标检测模型 |

---

## 目录结构

```
sec/
├── yolo_api/                        # YOLO 检测服务
│   ├── main.py                      # FastAPI 应用
│   ├── best.pt                      # YOLO 模型权重
│   ├── requirements.txt
│   └── Dockerfile
│
├── medical-system-backend-fastapi/
│   └── medical-system-backend-fastapi/
│       ├── medical-system-backend-fastapi/   # 主后端服务
│       │   ├── main.py              # API 入口
│       │   ├── models.py            # 数据模型
│       │   ├── schemas.py           # Pydantic schemas
│       │   ├── database.py           # 数据库配置
│       │   ├── medical_data.py      # 医学数据定义
│       │   ├── report_generator.py   # 报告生成
│       │   ├── ai_report_generator.py # AI 报告
│       │   ├── pdf_generator.py     # PDF 生成
│       │   └── requirements.txt
│       │
│       └── frontend/                 # Vue 前端
│           ├── src/
│           │   ├── views/            # 页面组件
│           │   │   ├── Login.vue
│           │   │   ├── Layout.vue
│           │   │   ├── Dashboard.vue
│           │   │   ├── DetectionAnalysis.vue
│           │   │   ├── Patients.vue
│           │   │   └── Images.vue
│           │   ├── api/             # API 调用
│           │   └── router/          # 路由配置
│           ├── package.json
│           └── Dockerfile
│
├── model/                           # 模型文件
│   └── best.pt                      # YOLO 权重
│
├── start.bat                        # Windows 一键启动
├── start-docker.bat                  # Docker 启动
├── docker-compose.yml               # Docker 编排
└── Dockerfile                       # All-in-One 镜像
```

---

## 模块说明

### 1. YOLO API (:8001)

**职责:** 医学影像目标检测

**接口:**
```
POST /detect
  - 上传图片，返回检测结果
  - 支持胸部 X 光、CT、MRI 等影像

GET /health
  - 健康检查
```

**检测类别 (10 类):**
1. 肺部结节 (Pulmonary Nodule)
2. 肺浸润 (Lung Infiltration)
3. 肺气肿 (Emphysema)
4. 胸腔积液 (Pleural Effusion)
5. 肺不张 (Atelectasis)
6. 肺炎 (Pneumonia)
7. 气胸 (Pneumothorax)
8. 心脏肥大 (Cardiomegaly)
9. 肺纹理增粗 (Increased Lung Markings)
10. 其他异常 (Other Abnormality)

---

### 2. Backend API (:8000)

**职责:** 业务逻辑处理、数据存储

**核心接口:**

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/register | 用户注册 |
| POST | /api/login | 用户登录 |
| GET | /api/classes | 获取检测类别 |
| POST | /api/analyze | 上传影像分析 |
| POST | /api/save | 保存诊断结果 |
| GET | /api/patients | 患者列表 |
| POST | /api/patients | 添加患者 |
| GET | /api/images | 影像列表 |
| GET | /api/report/{id}/pdf | 下载 PDF 报告 |

---

### 3. Frontend (:3000)

**职责:** 用户界面展示

**页面模块:**

| 页面 | 路径 | 功能 |
|------|------|------|
| 登录/注册 | /login | 用户认证 |
| 数据中心 | /home (默认) | 数据概览、图表统计 |
| 影片检测 | /detection | 影像上传与 AI 分析 |
| 患者管理 | /patients | 患者档案 CRUD |
| 影像管理 | /images | 影像资料管理 |

---

## 数据库模型

### Users (用户)
```
id          - 主键
username    - 用户名 (唯一)
password    - 密码哈希
role        - 角色 (admin/user)
created_at  - 创建时间
```

### Patients (患者)
```
id          - 主键
name        - 姓名
gender      - 性别
age         - 年龄
phone       - 电话
address     - 地址
created_at  - 创建时间
```

### DetectionRecords (检测记录)
```
id              - 主键
patient_id      - 患者 ID (外键)
patient_name    - 患者姓名
detection_type  - 检测类型 (chest/brain/retina/other)
original_filename - 原始文件名
detections      - JSON 检测结果
report_content  - JSON AI 诊断报告
annotated_image - 标注图片 Base64
status          - 状态 (pending/completed)
created_at      - 创建时间
```

---

## 部署方式

### 方式一: Windows 一键启动

```batch
双击运行: start.bat
```

### 方式二: Docker All-in-One

```batch
双击运行: start-all-in-one.bat
```

### 方式三: Docker Compose

```bash
docker-compose up -d
```

### 方式四: 手动启动

```bash
# 终端 1: YOLO API
cd yolo_api && python main.py

# 终端 2: Backend
cd medical-system-backend-fastapi/.../medical-system-backend-fastapi
pip install -r requirements.txt
uvicorn main:app --port 8000

# 终端 3: Frontend
cd medical-system-backend-fastapi/.../frontend
npm install && npm run dev
```

---

## 环境要求

| 组件 | 要求 |
|------|------|
| Python | 3.10+ |
| Node.js | 18+ |
| RAM | 8GB+ (推荐 16GB) |
| GPU | NVIDIA GPU (可选，用于 YOLO 加速) |
| Docker | 20.10+ (如使用 Docker) |

---

## 配置说明

### 后端环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| DATABASE_URL | sqlite:///./medical_system.db | 数据库连接 |
| SECRET_KEY | (代码中定义) | JWT 密钥 |
| YOLO_API_URL | http://localhost:8001 | YOLO 服务地址 |

### 前端 API 代理

前端通过 Vite 代理转发 API 请求:
- `/api/*` → Backend :8000
- `/yolo/*` → YOLO API :8001

---

## 安全说明

1. **认证:** JWT Token 存储于 localStorage
2. **密码:** 使用 PassLib 哈希加密
3. **文件上传:** 仅允许图片格式
4. **CORS:** 生产环境需配置正确域名

---

## 更新日志

| 版本 | 日期 | 更新内容 |
|------|------|----------|
| v2.0 | 2026-04-30 | 阿里云风格 UI 升级、Docker 部署支持 |
| v1.0 | 2026-04-24 | 初始版本，基本功能实现 |
