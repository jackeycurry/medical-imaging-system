# 胸部X光智能分析系统 - 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建基于 Vue.js + FastAPI + YOLO 的胸部X光异常检测与智能分析报告系统

**Architecture:** 前后端分离架构，Vue.js 前端通过 HTTP 与 FastAPI 后端通信，YOLO 模型进行推理，后端生成结构化分析报告

**Tech Stack:** Vue.js 3, FastAPI, Python 3.8+, YOLOv12s, Ultralytics

---

## 文件结构

```
D:\Project\test\sec\
├── backend/
│   ├── main.py              # FastAPI 入口，路由定义
│   ├── model_loader.py      # YOLO 模型加载与推理
│   ├── report_generator.py  # 分析报告生成逻辑
│   ├── medical_data.py      # 医学解释数据
│   └── requirements.txt    # Python 依赖
├── frontend/
│   ├── index.html           # Vue 入口
│   ├── vite.config.js       # Vite 配置
│   ├── package.json         # npm 依赖
│   └── src/
│       ├── main.js          # Vue 初始化
│       ├── App.vue          # 根组件
│       ├── components/
│       │   ├── DropZone.vue      # 拖拽上传组件
│       │   ├── ResultViewer.vue  # 结果展示组件
│       │   └── ReportPanel.vue   # 分析报告组件
│       └── services/
│           └── api.js       # API 调用服务
├── model/
│   └── best.pt              # YOLO 模型权重
└── docs/
    └── plans/               # 实现计划文档
```

---

## Task 1: 创建后端项目结构

**Files:**
- Create: `D:\Project\test\sec\backend\requirements.txt`
- Create: `D:\Project\test\sec\backend\main.py`
- Create: `D:\Project\test\sec\backend\model_loader.py`
- Create: `D:\Project\test\sec\backend\medical_data.py`
- Create: `D:\Project\test\sec\backend\report_generator.py`

- [ ] **Step 1: 创建目录结构**

```bash
mkdir -p D:/Project/test/sec/backend
mkdir -p D:/Project/test/sec/model
cp D:/Project/test/best.pt D:/Project/test/sec/model/
```

- [ ] **Step 2: 编写 requirements.txt**

```txt
fastapi==0.109.0
uvicorn==0.27.0
python-multipart==0.0.6
ultralytics==8.4.41
numpy==1.26.3
```

- [ ] **Step 3: 编写 medical_data.py - 医学解释数据**

```python
# 10类异常的医学解释数据
MEDICAL_DATA = {
    0: {
        "name_cn": "肺不张",
        "name_en": "Atelectasis",
        "explanation": "肺不张是指肺泡部分或完全塌陷，导致肺组织失去通气功能。常见原因包括支气管阻塞、胸腔积液压迫等。",
        "severity_rules": {"low": 0.4, "medium": 0.7},  # 置信度阈值
        "recommendation": "建议进行胸部CT检查以确定病因，必要时进行支气管镜检查。"
    },
    1: {
        "name_cn": "实变",
        "name_en": "Consolidation",
        "explanation": "肺实变是指肺泡腔被液体、细胞或物质填充，导致肺组织密度增高。常见于肺炎、肺水肿等。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议结合临床症状进行抗感染治疗，定期复查胸片。"
    },
    2: {
        "name_cn": "间质性肺病",
        "name_en": "ILD",
        "explanation": "间质性肺病是一组影响肺间质的疾病总称，表现为肺泡壁增厚、炎症细胞浸润。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进行高分辨率CT检查和肺功能测试，必要时转诊呼吸科。"
    },
    3: {
        "name_cn": "浸润",
        "name_en": "Infiltration",
        "explanation": "肺浸润是指肺组织内出现异常密度影，通常表示炎症或感染过程。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进行实验室检查（如血常规、C反应蛋白），考虑抗感染治疗。"
    },
    4: {
        "name_cn": "肺不透光",
        "name_en": "Lung Opacity",
        "explanation": "肺野不透光是指X光片上本应透光的肺野区域出现密度增高影，提示肺组织病变。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进一步CT检查以明确病变性质和范围。"
    },
    5: {
        "name_cn": "结节/肿块",
        "name_en": "Nodule/Mass",
        "explanation": "肺部结节直径≤3cm，肿块直径>3cm。可为良性（肉芽肿、错构瘤）或恶性（肺癌）。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进行CT增强检查，评估结节特征，必要时进行活检或PET-CT检查。"
    },
    6: {
        "name_cn": "胸腔积液",
        "name_en": "Pleural effusion",
        "explanation": "胸腔积液是指液体异常积聚在胸膜腔内。可能为漏出液（心衰、肾病）或渗出液（感染、肿瘤）。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进行胸腔超声检查评估积液量，必要时行胸腔穿刺抽液化验。"
    },
    7: {
        "name_cn": "胸膜增厚",
        "name_en": "Pleural thickening",
        "explanation": "胸膜增厚是指覆盖在肺表面的胸膜异常增厚，常见于陈旧性炎症、胸膜纤维化等。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "若无明显症状可定期随访，若伴有胸痛或呼吸困难建议进一步检查。"
    },
    8: {
        "name_cn": "气胸",
        "name_en": "Pneumothorax",
        "explanation": "气胸是指气体进入胸膜腔导致肺组织受压塌陷。可为自发性（瘦高体型、肺大疱破裂）或外伤性。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "若气胸量较大或出现呼吸困难，需立即就医。少量气胸可保守观察。"
    },
    9: {
        "name_cn": "肺纤维化",
        "name_en": "Pulmonary fibrosis",
        "explanation": "肺纤维化是肺组织逐渐被纤维结缔组织替代的慢性进展性疾病，导致肺功能进行性下降。",
        "severity_rules": {"low": 0.4, "medium": 0.7},
        "recommendation": "建议进行肺功能检查和高分辨率CT评估纤维化程度，必要时使用抗纤维化药物治疗。"
    }
}

def get_severity(confidence: float, rules: dict) -> str:
    """根据置信度和规则返回严重程度"""
    if confidence < rules["low"]:
        return "轻度"
    elif confidence < rules["medium"]:
        return "中度"
    else:
        return "重度"
```

- [ ] **Step 4: 编写 model_loader.py - YOLO 模型加载与推理**

```python
from ultralytics import YOLO
import torch
from pathlib import Path

MODEL_PATH = Path(__file__).parent.parent / "model" / "best.pt"

class ChestXRayModel:
    _instance = None
    _model = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_model(self):
        if self._model is None:
            self._model = YOLO(str(MODEL_PATH))
            self._model.eval()
        return self._model

    def predict(self, image_path: str, conf_threshold: float = 0.25):
        model = self.load_model()
        results = model(image_path, conf=conf_threshold, verbose=False)
        return results[0]

    def get_detections(self, results):
        """从推理结果中提取检测信息"""
        boxes = results.boxes
        detections = []
        if boxes is not None and len(boxes) > 0:
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                detections.append({
                    "class_id": cls_id,
                    "confidence": conf,
                    "bbox": bbox
                })
        return detections

# 单例全局实例
model_instance = ChestXRayModel()
```

- [ ] **Step 5: 编写 report_generator.py - 分析报告生成**

```python
from medical_data import MEDICAL_DATA, get_severity
import uuid
from datetime import datetime

def generate_report(image_path: str, detections: list) -> dict:
    """生成结构化分析报告"""
    report_id = str(uuid.uuid4())[:8]
    timestamp = datetime.now().isoformat()

    detection_results = []
    for det in detections:
        cls_id = det["class_id"]
        conf = det["confidence"]
        bbox = det["bbox"]

        medical_info = MEDICAL_DATA.get(cls_id, {})
        severity = get_severity(conf, medical_info.get("severity_rules", {"low": 0.4, "medium": 0.7}))

        detection_results.append({
            "class_id": cls_id,
            "class_name": medical_info.get("name_en", "Unknown"),
            "class_name_cn": medical_info.get("name_cn", "未知"),
            "confidence": round(conf, 4),
            "bbox": [round(x, 2) for x in bbox],
            "medical_explanation": medical_info.get("explanation", ""),
            "severity": severity,
            "recommendation": medical_info.get("recommendation", "建议咨询专业医生。")
        })

    # 生成摘要
    if detection_results:
        summary = f"共检测到 {len(detection_results)} 种异常"
        severity_counts = {}
        for det in detection_results:
            sev = det["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1
        summary += f"（轻度{severity_counts.get('轻度', 0)}个、中度{severity_counts.get('中度', 0)}个、重度{severity_counts.get('重度', 0)}个）"
    else:
        summary = "未检测到明显异常"

    return {
        "report_id": report_id,
        "timestamp": timestamp,
        "image_path": image_path,
        "detections": detection_results,
        "summary": summary,
        "total_findings": len(detection_results)
    }
```

- [ ] **Step 6: 编写 main.py - FastAPI 主程序**

```python
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import uvicorn
import os
import uuid
from pathlib import Path
from model_loader import model_instance
from report_generator import generate_report

app = FastAPI(title="Chest X-Ray Analysis API", version="1.0.0")

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 上传文件目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

@app.get("/")
async def root():
    return {"message": "Chest X-Ray Analysis API", "version": "1.0.0"}

@app.get("/api/classes")
async def get_classes():
    """返回所有异常类别定义"""
    from medical_data import MEDICAL_DATA
    classes = []
    for cls_id, info in MEDICAL_DATA.items():
        classes.append({
            "id": cls_id,
            "name_en": info["name_en"],
            "name_cn": info["name_cn"]
        })
    return {"classes": classes}

@app.post("/api/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """上传胸部X光图片进行检测分析"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file uploaded")

    # 保存上传文件
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in [".jpg", ".jpeg", ".png", ".dcm"]:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    file_id = str(uuid.uuid4())
    file_path = UPLOAD_DIR / f"{file_id}{file_ext}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    try:
        # YOLO 推理
        results = model_instance.predict(str(file_path))
        detections = model_instance.get_detections(results)

        # 生成报告
        report = generate_report(str(file_path), detections)

        # 添加标注图片路径
        if results and results.plot_img_path:
            report["annotated_image"] = f"/api/images/{file_id}{file_ext}"

        # 清理上传文件
        os.remove(file_path)

        return JSONResponse(content=report)

    except Exception as e:
        # 清理上传文件
        if file_path.exists():
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/images/{image_id}")
async def get_image(image_id: str):
    """获取标注后的图片"""
    for ext in [".jpg", ".jpeg", ".png"]:
        img_path = UPLOAD_DIR / f"{image_id}{ext}"
        if img_path.exists():
            return FileResponse(img_path, media_type=f"image/{ext[1:]}")
    raise HTTPException(status_code=404, detail="Image not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 7: 安装后端依赖并测试**

```bash
cd D:/Project/test/sec/backend
pip install -r requirements.txt
python -c "from main import app; print('Backend OK')"
```

- [ ] **Step 8: 测试模型推理**

```bash
python -c "
from model_loader import model_instance
results = model_instance.predict('D:/Project/test/analysis/val_predictions/008b3176a7248a0a189b5731ac8d2e95.jpg')
detections = model_instance.get_detections(results)
print(f'Detections: {len(detections)}')
for d in detections:
    print(f'  - Class {d[\"class_id\"]}: {d[\"confidence\"]:.2%}')
"
```

---

## Task 2: 创建前端项目结构

**Files:**
- Create: `D:\Project\test\sec\frontend\package.json`
- Create: `D:\Project\test\sec\frontend\vite.config.js`
- Create: `D:\Project\test\sec\frontend\index.html`
- Create: `D:\Project\test\sec\frontend\src\main.js`
- Create: `D:\Project\test\sec\frontend\src\App.vue`
- Create: `D:\Project\test\sec\frontend\src\components\DropZone.vue`
- Create: `D:\Project\test\sec\frontend\src\components\ResultViewer.vue`
- Create: `D:\Project\test\sec\frontend\src\components\ReportPanel.vue`
- Create: `D:\Project\test\sec\frontend\src\services\api.js`

- [ ] **Step 1: 初始化前端项目**

```bash
cd D:/Project/test/sec
npm create vite@latest frontend -- --template vue
cd frontend
npm install
npm install axios
```

- [ ] **Step 2: 配置 vite.config.js**

```javascript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

- [ ] **Step 3: 编写 api.js - API 调用服务**

```javascript
import axios from 'axios'

const API_BASE = '/api'

export const api = {
  async analyzeImage(file) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await axios.post(`${API_BASE}/analyze`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    return response.data
  },

  async getClasses() {
    const response = await axios.get(`${API_BASE}/classes`)
    return response.data.classes
  }
}
```

- [ ] **Step 4: 编写 DropZone.vue - 拖拽上传组件**

```vue
<template>
  <div
    class="drop-zone"
    :class="{ 'drag-over': isDragOver }"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
    @click="triggerFileInput"
  >
    <input
      ref="fileInput"
      type="file"
      accept="image/*,.dcm"
      @change="onFileSelect"
      style="display: none"
    />
    <div class="drop-content">
      <div class="upload-icon">📤</div>
      <p class="drop-text">拖拽胸部X光图片到此处</p>
      <p class="drop-hint">或点击选择文件 (支持 PNG, JPG, DICOM)</p>
    </div>
    <div v-if="loading" class="loading-overlay">
      <div class="spinner"></div>
      <p>分析中...</p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  loading: Boolean
})

const emit = defineEmits(['file-selected'])

const fileInput = ref(null)
const isDragOver = ref(false)

const triggerFileInput = () => {
  fileInput.value?.click()
}

const onDragOver = () => {
  isDragOver.value = true
}

const onDragLeave = () => {
  isDragOver.value = false
}

const onDrop = (e) => {
  isDragOver.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    emit('file-selected', files[0])
  }
}

const onFileSelect = (e) => {
  const files = e.target.files
  if (files.length > 0) {
    emit('file-selected', files[0])
  }
}
</script>

<style scoped>
.drop-zone {
  border: 3px dashed #ccc;
  border-radius: 16px;
  padding: 60px 40px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  background: #fafafa;
  position: relative;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drop-zone:hover,
.drop-zone.drag-over {
  border-color: #4a90d9;
  background: #f0f7ff;
}

.drop-content {
  pointer-events: none;
}

.upload-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.drop-text {
  font-size: 18px;
  color: #333;
  margin: 0 0 8px 0;
}

.drop-hint {
  font-size: 14px;
  color: #888;
  margin: 0;
}

.loading-overlay {
  position: absolute;
  inset: 0;
  background: rgba(255,255,255,0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 16px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #f3f3f3;
  border-top: 4px solid #4a90d9;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}
</style>
```

- [ ] **Step 5: 编写 ResultViewer.vue - 结果展示组件**

```vue
<template>
  <div class="result-viewer" v-if="result">
    <h3>检测结果</h3>
    <div class="result-summary">{{ result.summary }}</div>

    <div class="detection-list">
      <div
        v-for="(det, idx) in result.detections"
        :key="idx"
        class="detection-item"
      >
        <div class="det-header">
          <span class="det-name">{{ det.class_name_cn }} ({{ det.class_name }})</span>
          <span class="det-conf">{{ (det.confidence * 100).toFixed(1) }}%</span>
        </div>
        <div class="severity-badge" :class="det.severity">
          {{ det.severity }}
        </div>
      </div>
    </div>

    <div v-if="result.detections.length === 0" class="no-findings">
      未检测到明显异常 🎉
    </div>
  </div>
</template>

<script setup>
defineProps({
  result: Object
})
</script>

<style scoped>
.result-viewer {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

h3 {
  margin: 0 0 12px 0;
  color: #333;
}

.result-summary {
  background: #f5f5f5;
  padding: 12px;
  border-radius: 8px;
  margin-bottom: 16px;
  font-size: 14px;
}

.detection-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detection-item {
  border: 1px solid #eee;
  border-radius: 8px;
  padding: 12px;
}

.det-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.det-name {
  font-weight: 600;
  color: #333;
}

.det-conf {
  color: #666;
  font-size: 14px;
}

.severity-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 500;
}

.severity-badge.轻度 {
  background: #e3f2fd;
  color: #1976d2;
}

.severity-badge.中度 {
  background: #fff3e0;
  color: #f57c00;
}

.severity-badge.重度 {
  background: #ffebee;
  color: #d32f2f;
}

.no-findings {
  text-align: center;
  padding: 40px;
  color: #4caf50;
  font-size: 18px;
}
</style>
```

- [ ] **Step 6: 编写 ReportPanel.vue - 分析报告组件**

```vue
<template>
  <div class="report-panel" v-if="result && result.detections.length > 0">
    <h3>📋 医学分析报告</h3>

    <div class="report-meta">
      <span>报告ID: {{ result.report_id }}</span>
      <span>发现异常: {{ result.total_findings }} 项</span>
    </div>

    <div class="report-sections">
      <div
        v-for="(det, idx) in result.detections"
        :key="idx"
        class="report-section"
      >
        <div class="section-header">
          <h4>{{ det.class_name_cn }}</h4>
          <span class="severity-tag" :class="det.severity">{{ det.severity }}</span>
        </div>

        <div class="section-content">
          <div class="info-row">
            <span class="label">英文名：</span>
            <span>{{ det.class_name }}</span>
          </div>
          <div class="info-row">
            <span class="label">置信度：</span>
            <span>{{ (det.confidence * 100).toFixed(1) }}%</span>
          </div>

          <div class="medical-explanation">
            <h5>医学解释</h5>
            <p>{{ det.medical_explanation }}</p>
          </div>

          <div class="recommendation">
            <h5>💡 建议</h5>
            <p>{{ det.recommendation }}</p>
          </div>
        </div>
      </div>
    </div>

    <div class="report-footer">
      <p>⚠️ 本报告仅供辅助参考，不能替代专业医生的诊断意见。</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  result: Object
})
</script>

<style scoped>
.report-panel {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

h3 {
  margin: 0 0 16px 0;
  color: #333;
}

.report-meta {
  display: flex;
  gap: 20px;
  font-size: 13px;
  color: #666;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #eee;
}

.report-sections {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.report-section {
  border: 1px solid #e0e0e0;
  border-radius: 12px;
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e0e0e0;
}

.section-header h4 {
  margin: 0;
  color: #333;
}

.severity-tag {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
}

.severity-tag.轻度 {
  background: #e3f2fd;
  color: #1976d2;
}

.severity-tag.中度 {
  background: #fff3e0;
  color: #f57c00;
}

.severity-tag.重度 {
  background: #ffebee;
  color: #d32f2f;
}

.section-content {
  padding: 16px;
}

.info-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 14px;
}

.label {
  color: #666;
  font-weight: 500;
}

.medical-explanation,
.recommendation {
  margin-top: 12px;
}

.medical-explanation h5,
.recommendation h5 {
  margin: 0 0 6px 0;
  font-size: 13px;
  color: #555;
}

.medical-explanation p,
.recommendation p {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  color: #333;
}

.report-footer {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.report-footer p {
  margin: 0;
  font-size: 12px;
  color: #888;
  text-align: center;
}
</style>
```

- [ ] **Step 7: 编写 App.vue - 根组件**

```vue
<template>
  <div class="app">
    <header class="app-header">
      <h1>🫁 胸部X光智能分析系统</h1>
      <p>基于 YOLO AI 模型的胸部X光异常检测与医学分析报告</p>
    </header>

    <main class="app-main">
      <div class="upload-section">
        <DropZone
          :loading="loading"
          @file-selected="handleFileSelected"
        />
      </div>

      <div v-if="result" class="result-section">
        <div class="result-grid">
          <ResultViewer :result="result" />
          <ReportPanel :result="result" />
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { api } from './services/api'
import DropZone from './components/DropZone.vue'
import ResultViewer from './components/ResultViewer.vue'
import ReportPanel from './components/ReportPanel.vue'

const loading = ref(false)
const result = ref(null)

const handleFileSelected = async (file) => {
  loading.value = true
  result.value = null

  try {
    const data = await api.analyzeImage(file)
    result.value = data
  } catch (error) {
    console.error('Analysis failed:', error)
    alert('分析失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style>
* {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  background: #f0f2f5;
  color: #333;
}

.app {
  min-height: 100vh;
}

.app-header {
  background: linear-gradient(135deg, #1976d2 0%, #42a5f5 100%);
  color: white;
  padding: 40px 20px;
  text-align: center;
}

.app-header h1 {
  font-size: 28px;
  margin-bottom: 8px;
}

.app-header p {
  font-size: 14px;
  opacity: 0.9;
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.upload-section {
  margin-bottom: 40px;
}

.result-section {
  animation: fadeIn 0.3s ease;
}

.result-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

@media (max-width: 768px) {
  .result-grid {
    grid-template-columns: 1fr;
  }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
```

- [ ] **Step 8: 修改 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>胸部X光智能分析系统</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.js"></script>
  </body>
</html>
```

- [ ] **Step 9: 启动前端开发服务器测试**

```bash
cd D:/Project/test/sec/frontend
npm run dev
```

---

## Task 3: 集成测试

- [ ] **Step 1: 启动后端服务**

```bash
cd D:/Project/test/sec/backend
python main.py
# 服务应在 http://localhost:8000 运行
```

- [ ] **Step 2: 启动前端服务（新终端）**

```bash
cd D:/Project/test/sec/frontend
npm run dev
# 服务应在 http://localhost:3000 运行
```

- [ ] **Step 3: 手动测试流程**

1. 打开浏览器访问 http://localhost:3000
2. 拖拽一张胸部X光图片到上传区域
3. 等待分析完成
4. 查看检测结果和分析报告

---

## Task 4: 启动脚本（可选）

**Files:**
- Create: `D:\Project\test\sec\start.bat`

- [ ] **Step 1: 创建启动脚本**

```batch
@echo off
echo Starting Chest X-Ray Analysis System...

echo Starting Backend Server on port 8000...
start "Backend" cmd /k "cd /d D:\Project\test\sec\backend && python main.py"

echo Waiting for backend to start...
timeout /t 5

echo Starting Frontend Server on port 3000...
start "Frontend" cmd /k "cd /d D:\Project\test\sec\frontend && npm run dev"

echo.
echo System starting...
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
pause
```

---

## 验证清单

- [ ] 后端 API 可正常启动
- [ ] YOLO 模型加载成功
- [ ] 图片分析返回正确结果
- [ ] 前端页面可访问
- [ ] 拖拽上传功能正常
- [ ] 检测结果正确显示
- [ ] 分析报告生成正确

---

**Plan complete.** Saved to `D:\Project\test\sec\docs\superpowers\plans\2026-04-24-chest-xray-analysis-plan.md`

**Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
