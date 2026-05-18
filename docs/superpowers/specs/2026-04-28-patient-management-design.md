# 肺部检测患者管理系统 - 设计文档

## 1. 概述

**项目名称**：肺部检测患者管理系统
**项目类型**：医疗辅助检测管理系统
**核心功能**：患者档案管理 + 检查记录管理 + Dify AI 推理集成
**技术栈**：FastAPI + SQLite + Vue 3

## 2. 系统架构

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│   Vue 3 前端     │ ←→  │  患者管理系统 API  │ ←→  │  Dify 推理  │
│   (端口 3000)    │     │  (端口 8000/SQLite)│     │  (现有服务)  │
└─────────────────┘     └──────────────────┘     └─────────────┘
```

- **患者管理系统**：独立 FastAPI 项目，管理患者档案和检查记录
- **Dify 推理服务**：复用现有的 Dify 工作流（胸部X光分析）
- **SQLite**：轻量数据库，单机部署无忧

## 3. 数据模型

### 3.1 Patient（患者）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| name | String(100) | 姓名 |
| age | Integer | 年龄 |
| gender | String(10) | 性别：male/female |
| phone | String(20) | 联系电话 |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

### 3.2 Examination（检查记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键，自增 |
| patient_id | Integer | 外键，关联患者 |
| exam_date | Date | 检查日期 |
| referring_doctor | String(100) | 主治医生 |
| status | String(20) | 状态：pending/analyzing/completed/failed |
| questionnaire | JSON | 肺部问卷答案 |
| original_image_path | String(500) | 原始图像路径 |
| annotated_image_path | String(500) | 标注图像路径 |
| detections | JSON | Dify 返回的检测结果 |
| ai_report | JSON | AI 分析报告 |
| pdf_path | String(500) | PDF 报告路径 |
| is_temporary | Boolean | 是否临时记录（待确认保存） |
| created_at | DateTime | 创建时间 |

### 3.3 问卷字段定义

问卷以 JSON 格式存储在 `examination.questionnaire` 中：

| 字段 | 类型 | 说明 |
|------|------|------|
| main_symptoms | List[String] | 主要症状：cough(咳嗽)/dyspnea(呼吸困难)/chest_pain(胸痛)/sputum(咳痰)/asymptomatic(无症状) |
| symptom_duration | String | 症状持续时间：<1week/1-4weeks/>4weeks |
| past_lung_disease | List[String] | 既往肺部疾病：copd/asthma/tb/bronchiectasis/none |
| smoking_history | String | 吸烟史：never/quit/smoking 或 smoking:daily_count |
| occupational_exposure | List[String] | 职业暴露：dust(粉尘)/chemical(化学物质)/radiation(放射线)/none |
| family_lung_history | Boolean | 家族肺部疾病史 |
| last_xray_time | String | 最近X光检查：<6months/6-12months/>1year/never |
| exam_purpose | String | 检查目的：routine(常规体检)/clinic(不适就诊)/followup(随访复查)/other |
| notes | String | 其他病史备注 |

## 4. API 设计

### 4.1 患者管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/patients` | 获取患者列表（支持分页、搜索） |
| POST | `/api/patients` | 创建患者档案 |
| GET | `/api/patients/{id}` | 获取患者详情（含检查记录列表） |
| PUT | `/api/patients/{id}` | 更新患者信息 |
| DELETE | `/api/patients/{id}` | 删除患者（软删除或级联删除检查记录） |

### 4.2 检查记录管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/examinations` | 获取检查列表（支持按患者、日期筛选） |
| POST | `/api/examinations` | 创建检查记录 |
| GET | `/api/examinations/{id}` | 获取检查详情 |
| PUT | `/api/examinations/{id}` | 更新检查信息 |
| DELETE | `/api/examinations/{id}` | 删除检查记录 |
| POST | `/api/examinations/{id}/upload` | 上传图像 |
| POST | `/api/examinations/{id}/analyze` | 触发 Dify 推理 |
| POST | `/api/examinations/{id}/confirm` | 确认保存（is_temporary=false） |
| POST | `/api/examinations/{id}/discard` | 丢弃检查（删除临时文件） |
| GET | `/api/examinations/{id}/pdf` | 下载 PDF 报告 |

### 4.3 响应格式

**患者列表响应**
```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "patients": [...]
}
```

**患者详情响应**
```json
{
  "id": 1,
  "name": "张三",
  "age": 55,
  "gender": "male",
  "phone": "13800138000",
  "examinations": [...],
  "created_at": "2026-04-28T10:00:00Z"
}
```

## 5. 检查流程

1. **创建患者档案**（如已有，跳过）
2. **新建检查记录** → 填写问卷 + 上传胸部X光图像
3. **触发分析** → 调用 Dify 工作流进行 AI 检测
4. **查看结果** → 显示检测结果、AI 报告，预览 PDF
5. **确认保存或丢弃** →
   - **保存** → 正式存储检查记录，关联患者
   - **丢弃** → 删除临时图像和报告，清除分析结果

### 5.1 临时记录机制

检查记录新增字段 `is_temporary`：
- `true`：分析完成待确认，图像和报告暂存临时目录
- `false`：已确认保存，正式存储

临时记录定期清理（如超过24小时未确认）。

## 6. 前端页面结构

### 布局
- **左侧导航栏**（固定宽度 200px）— Logo + 导航菜单
- **右侧主内容区** — 自适应宽度，顶部页面标题 + 操作区 + 内容表格

### 导航菜单

| 图标 | 菜单项 | 页面 |
|------|--------|------|
| 👤 | 患者管理 | 患者列表、增删改查 |
| 📋 | 检查记录 | 检查列表、状态筛选 |
| 📊 | 数据统计 | 检查量趋势、异常检出统计 |

### 6.1 患者管理页面

**顶部区域**
- 搜索框（姓名/电话模糊搜索）
- 筛选条件（可选）
- 新建患者按钮

**表格列**
| 列名 | 说明 |
|------|------|
| ID | 自增编号 |
| 姓名 | 患者姓名 |
| 年龄 | 岁数 |
| 性别 | 男/女 |
| 电话 | 联系电话 |
| 检查次数 | 关联的检查记录数 |
| 创建时间 | 档案创建日期 |
| 操作 | 查看/编辑/删除 |

**分页**
- 底部分页器，每页20条

**新建/编辑弹窗**
- 姓名（必填）
- 年龄（必填）
- 性别（单选）
- 电话（选填）

### 6.2 检查记录页面

**顶部区域**
- 患者下拉筛选
- 日期范围筛选
- 状态筛选（待分析/分析中/已完成/已失败）
- 新建检查按钮

**表格列**
| 列名 | 说明 |
|------|------|
| ID | 自增编号 |
| 患者姓名 | 关联患者 |
| 检查日期 | exam_date |
| 检查目的 | 问卷中的exam_purpose |
| 状态 | pending/analyzing/completed/failed |
| AI结论 | 检测到的异常摘要 |
| 创建时间 | 记录创建时间 |
| 操作 | 查看详情/删除 |

### 6.3 检查详情页

- 患者信息卡片
- 问卷答案展示
- 原始图像 + 标注图像对比
- 检测结果列表（类别、置信度、严重程度）
- AI 诊断报告
- PDF 预览/下载
- **确认保存 / 丢弃按钮**（仅 `is_temporary=true` 时显示）

### 6.4 新建检查页

- 选择患者（下拉搜索）
- 问卷表单（9个问题）
- 图像上传区域（拖拽上传）
- 提交后跳转到分析页面

### 6.5 数据统计页面

**统计卡片**
- 总患者数
- 总检查数
- 本月检查数
- 异常检出率

**图表**
- 每日/每周/每月检查量趋势（折线图）
- 异常类型分布（饼图/柱状图）

**筛选**
- 日期范围
- 患者范围

```
sec/
├── patient_management/          # 新建患者管理系统
│   ├── backend/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── database.py         # SQLite 数据库配置
│   │   ├── models.py           # Pydantic 模型
│   │   ├── crud.py             # 数据库操作
│   │   ├── routers/
│   │   │   ├── patients.py     # 患者管理路由
│   │   │   └── examinations.py # 检查记录路由
│   │   ├── services/
│   │   │   └── dify.py         # Dify 推理服务调用
│   │   └── requirements.txt
│   └── frontend/               # Vue 3 前端
│       └── src/
│           ├── views/          # 页面
│           │   ├── PatientList.vue
│           │   ├── PatientDetail.vue
│           │   ├── ExamList.vue
│           │   ├── ExamDetail.vue
│           │   ├── NewExam.vue
│           │   └── Statistics.vue
│           ├── components/     # 组件
│           │   ├── Layout.vue    # 左侧导航 + 主内容区布局
│           │   ├── PatientForm.vue
│           │   ├── QuestionnaireForm.vue
│           │   └── ImageUploader.vue
│           ├── services/       # API 调用
│           ├── router/         # 路由配置
│           └── stores/         # 状态管理（如需）
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-28-patient-management-design.md
```

## 7. 技术选型理由

- **SQLite**：单机部署简单，10万患者 + 50万检查记录无压力
- **FastAPI**：Python 现代框架，自动文档，类型安全
- **Vue 3**：渐进式框架，与现有前端技术一致
- **复用 Dify**：不重复造轮子，职责单一

## 8. 待确认事项

- [ ] 是否需要用户登录认证？
- [ ] 检查记录删除是软删除还是级联删除？
- [ ] 是否需要数据导出功能（Excel/CSV）？
