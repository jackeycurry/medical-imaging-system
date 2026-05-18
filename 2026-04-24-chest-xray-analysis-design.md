# 胸部X光智能分析系统 - 设计文档

## 概述

基于 YOLO 模型的胸部X光异常检测与智能分析报告生成系统。

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Vue.js 3 |
| 后端 | FastAPI (Python) |
| 模型 | YOLOv12s (best.pt) |

## 功能需求

### 1. 图片上传
- 拖拽上传 DICOM/PNG/JPG 格式
- 上传进度显示
- 支持多图排队

### 2. YOLO 推理
- 10 类异常检测：Atelectasis、Consolidation、ILD、Infiltration、Lung Opacity、Nodule/Mass、 pleural effusion、 pleural thickening、Pneumothorax、Pulmonary fibrosis
- 返回检测框位置、置信度

### 3. 分析报告
每种检测到的异常包含：
- 异常名称（中英文）
- 检测置信度
- 位置信息
- 医学解释
- 严重程度评估（轻度/中度/重度）
- 后续建议

### 4. 结果展示
- 原图 + 检测框标注
- 检测结果列表
- 完整分析报告面板

## 系统架构

```
┌─────────────┐      HTTP       ┌─────────────┐
│  Vue.js 前端 │  ←──────────→  │  FastAPI 后端 │
│  (拖拽上传)   │   JSON/图片    │  (推理服务)   │
└─────────────┘                └───────┬───────┘
                                       │
                               ┌───────↓───────┐
                               │  YOLO 模型    │
                               │  best.pt     │
                               └───────────────┘
```

## API 设计

### POST /api/analyze
**请求：** multipart/form-data
- file: 图片文件

**响应：**
```json
{
  "image_id": "xxx",
  "detections": [
    {
      "class_id": 4,
      "class_name": "Lung Opacity",
      "confidence": 0.85,
      "bbox": [x1, y1, x2, y2],
      "medical_explanation": "肺野内密度增高影...",
      "severity": "中度",
      "recommendation": "建议进一步CT检查..."
    }
  ],
  "summary": "检测到 X 种异常..."
}
```

### GET /api/classes
返回 10 类异常的元数据定义。

## 目录结构

```
D:\Project\chest-xray-app\
├── frontend/          # Vue.js 项目
│   ├── src/
│   │   ├── components/
│   │   │   ├── DropZone.vue
│   │   │   ├── ResultViewer.vue
│   │   │   └── ReportPanel.vue
│   │   ├── services/
│   │   │   └── api.js
│   │   └── App.vue
│   └── package.json
├── backend/           # FastAPI 项目
│   ├── main.py
│   ├── model.py
│   ├── report.py
│   └── requirements.txt
└── model/
    └── best.pt
```

## 严重程度定义

| 等级 | 置信度范围 | 说明 |
|------|-----------|------|
| 轻度 | < 50% | 需关注，建议随访 |
| 中度 | 50-75% | 建议进一步检查 |
| 重度 | > 75% | 需尽快就医 |

## 医学解释库

每类异常预定义医学解释：
- Atelectasis: 肺不张
- Consolidation: 实变
- ILD: 间质性肺病
- Infiltration: 浸润
- Lung Opacity: 肺不透光
- Nodule/Mass: 结节/肿块
- Pleural effusion: 胸腔积液
- Pleural thickening: 胸膜增厚
- Pneumothorax: 气胸
- Pulmonary fibrosis: 肺纤维化

## 交付物

1. 可运行的 Vue.js 前端应用
2. FastAPI 后端服务
3. YOLO 模型推理集成
4. 结构化分析报告生成
