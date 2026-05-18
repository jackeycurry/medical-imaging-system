# Chest X-ray Detection Module Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add chest X-ray detection capability to medical management system - a popup modal where doctors can upload chest images, get AI analysis results from the 8000-port backend, and optionally save results to database.

**Architecture:** Medical management system backend (8084) acts as a gateway - it receives image uploads, calls the chest X-ray analysis service (8000), parses results, and returns to frontend. Analysis results can be saved to the medical_images table with PDF path reference.

**Tech Stack:** Python FastAPI backend, Vue 3 frontend, HTTP calls to external chest X-ray service (8000)

---

## Task 1: Add pdf_path and report_id to MedicalImage Model

**Files:**
- Modify: `medical-system-backend-fastapi/medical-system-backend-fastapi/models.py`

- [ ] **Step 1: Add fields to MedicalImage model**

Find the `MedicalImage` class in `models.py` and add two new fields after `report_id`:

```python
pdf_path = Column(String(500))  # PDF file storage path
```

Note: `report_id` field already exists in the model.

- [ ] **Step 2: Commit**

```bash
git add medical-system-backend-fastapi/medical-system-backend-fastapi/models.py
git commit -m "feat(medical-system): add pdf_path field to MedicalImage model"
```

---

## Task 2: Add Backend API Endpoints

**Files:**
- Modify: `medical-system-backend-fastapi/medical-system-backend-fastapi/main.py`
- Test: Use curl or Postman to verify endpoints

- [ ] **Step 1: Add imports at top of main.py**

Add these imports after existing imports:
```python
import httpx
import tempfile
import shutil
from pathlib import Path
```

- [ ] **Step 2: Add constants for chest X-ray service**

Add after the SECRET_KEY definition:
```python
CHEST_XRAY_SERVICE_URL = "http://localhost:8000"
UPLOAD_DIR = Path("D:/Project/test/sec/backend/uploads")
REPORTS_DIR = Path("D:/Project/test/sec/backend/reports")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 3: Add /api/chest-xray/analyze endpoint**

Add this endpoint after the `external_upload` function (around line 263):

```python
@app.post("/api/chest-xray/analyze", response_model=ApiResponse)
async def analyze_chest_xray(
    file: UploadFile = File(...),
    user_info: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Chest X-ray AI analysis endpoint.
    Receives image, calls chest X-ray service (8000), returns results.
    """
    allowed_extensions = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ".jpg"
    if file_ext not in allowed_extensions:
        return ApiResponse(code=400, message=f"不支持的图片格式: {file_ext}")

    # Save uploaded file temporarily
    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex[:8]}{file_ext}"
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Call chest X-ray service at 8000
        with open(temp_path, "rb") as f:
            files = {"file": (temp_path.name, f, f"image/{file_ext[1:]}")}
            data = {"user_info": user_info or "{}"}
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                try:
                    response = await client.post(
                        f"{CHEST_XRAY_SERVICE_URL}/api/analyze",
                        files=files,
                        data=data
                    )
                except httpx.ConnectError:
                    return ApiResponse(code=503, message="胸片分析服务暂不可用，请稍后重试")
                except httpx.TimeoutException:
                    return ApiResponse(code=504, message="分析超时，请重试")

        if response.status_code != 200:
            return ApiResponse(code=500, message=f"分析失败: {response.text}")

        result = response.json()
        
        return ApiResponse(data={
            "report_id": result.get("report_id"),
            "detections": result.get("detections", []),
            "ai_report": result.get("ai_report", {}),
            "original_image": result.get("original_image"),
            "annotated_image": result.get("annotated_image"),
            "pdf_url": result.get("pdf_url")
        })

    except Exception as e:
        return ApiResponse(code=500, message=f"分析失败: {str(e)}")
    finally:
        if temp_path.exists():
            temp_path.unlink()
```

- [ ] **Step 4: Add /api/chest-xray/save endpoint**

Add this endpoint after the `analyze_chest_xray` function:

```python
from schemas import ImageResultSave

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
            annotated_image=base64.b64decode(request.annotated_image_base64) if request.annotated_image_base64 else None,
            status="已完成",
            report_id=request.patient_id,  # Use patient_id as report_id if provided
            pdf_path=request.annotated_image_base64  # Store reference
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
```

- [ ] **Step 5: Test the analyze endpoint**

Run the medical system backend:
```bash
cd medical-system-backend-fastapi/medical-system-backend-fastapi
python main.py
```

Test with curl (need a test image):
```bash
curl -X POST "http://localhost:8084/api/chest-xray/analyze" -F "file=@test.jpg"
```

Expected: JSON response with detections, original_image, annotated_image

- [ ] **Step 6: Commit**

```bash
git add medical-system-backend-fastapi/medical-system-backend-fastapi/main.py
git commit -m "feat(medical-system): add chest-xray analyze and save endpoints"
```

---

## Task 3: Add Frontend API Methods

**Files:**
- Modify: `medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/src/api/index.js`

- [ ] **Step 1: Add new API methods**

Add these methods to the api object (before the closing `export default {`):

```javascript
analyzeChestXray: (formData) => {
  return api.post('/api/chest-xray/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
},
saveChestXrayResult: (data) => api.post('/api/chest-xray/save', data),
getPatientsBrief: () => api.get('/api/patients/brief'),
```

- [ ] **Step 2: Commit**

```bash
git add medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/src/api/index.js
git commit -m "feat(frontend): add analyzeChestXray and saveChestXrayResult API methods"
```

---

## Task 4: Add Menu Item to Layout

**Files:**
- Modify: `medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/src/views/Layout.vue`

- [ ] **Step 1: Add reactive state for chest X-ray modal**

In the `<script setup>` section, add:
```javascript
const showChestXray = ref(false)
```

- [ ] **Step 2: Add menu item in sidebar**

Find the `<nav>` section and add:
```html
<a @click="showChestXray = true" :class="{ active: showChestXray }">胸片检测</a>
```

- [ ] **Step 3: Import ChestXray component**

Add to imports:
```javascript
import ChestXray from './ChestXray.vue'
```

- [ ] **Step 4: Add ChestXray component to template**

In the `<main class="content">` section, add:
```html
<ChestXray v-if="showChestXray" @close="showChestXray = false" />
```

- [ ] **Step 5: Commit**

```bash
git add medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/src/views/Layout.vue
git commit -m "feat(frontend): add chest-xray menu item to Layout"
```

---

## Task 5: Create ChestXray.vue Component

**Files:**
- Create: `medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/src/views/ChestXray.vue`

- [ ] **Step 1: Create the component file**

Create the complete Vue component with:

```vue
<template>
  <div class="modal" @click.self="$emit('close')">
    <div class="modal-content chest-xray-modal">
      <div class="modal-header">
        <h3>胸片检测</h3>
        <button class="close-btn" @click="$emit('close')">&times;</button>
      </div>

      <div class="modal-body">
        <!-- Upload Section -->
        <div class="upload-section">
          <div class="upload-area" @click="$refs.fileInput.click()">
            <input type="file" ref="fileInput" accept="image/*" @change="handleFileSelect" hidden />
            <div v-if="!previewUrl" class="upload-placeholder">
              <span class="upload-icon">+</span>
              <span>点击上传胸片图片</span>
            </div>
            <div v-else class="image-preview">
              <img :src="previewUrl" alt="胸片预览" />
            </div>
          </div>
        </div>

        <!-- Analyze Button -->
        <button 
          class="btn-analyze" 
          @click="analyze" 
          :disabled="!selectedFile || analyzing"
        >
          {{ analyzing ? '分析中...' : '开始分析' }}
        </button>

        <!-- Results Section -->
        <div v-if="result" class="results-section">
          <h4>检测结果</h4>
          <div class="detections-list">
            <div v-for="(det, idx) in result.detections" :key="idx" class="detection-item">
              <span class="det-name">{{ det.class_name_cn || det.class_name }}</span>
              <div class="confidence-bar">
                <div class="confidence-fill" :style="{ width: (det.confidence * 100) + '%' }"></div>
              </div>
              <span class="confidence-text">{{ (det.confidence * 100).toFixed(0) }}%</span>
            </div>
            <div v-if="result.detections.length === 0" class="no-detection">
              未检测到异常
            </div>
          </div>

          <h4>AI诊断报告</h4>
          <div class="ai-report">
            <pre>{{ result.ai_report?.diagnosis || result.ai_report?.reasoning_content || '暂无' }}</pre>
          </div>

          <!-- Annotated Image -->
          <div v-if="result.annotated_image" class="annotated-section">
            <h4>标注图像</h4>
            <img :src="result.annotated_image" alt="标注图" class="annotated-image" />
          </div>

          <!-- Patient Association -->
          <div class="patient-section">
            <h4>关联患者</h4>
            <div class="patient-input">
              <input 
                v-model="patientName" 
                type="text" 
                placeholder="输入患者姓名或选择已有患者" 
                list="patient-list"
              />
              <datalist id="patient-list">
                <option v-for="p in patients" :key="p.id" :value="p.name" />
              </datalist>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="action-buttons">
            <button class="btn-save" @click="saveToDb">存入数据库</button>
            <button class="btn-cancel" @click="$emit('close')">仅查看</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const emit = defineEmits(['close'])

const selectedFile = ref(null)
const previewUrl = ref('')
const analyzing = ref(false)
const result = ref(null)
const patientName = ref('')
const patients = ref([])
const fileInput = ref(null)

onMounted(() => {
  loadPatients()
})

const loadPatients = async () => {
  try {
    const res = await api.getPatients()
    if (res.data) {
      patients.value = res.data
    }
  } catch (e) {
    console.error('Failed to load patients', e)
  }
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file)
    result.value = null
  }
}

const analyze = async () => {
  if (!selectedFile.value) return
  
  analyzing.value = true
  result.value = null

  const formData = new FormData()
  formData.append('file', selectedFile.value)

  try {
    const res = await api.analyzeChestXray(formData)
    if (res.code === 200 && res.data) {
      result.value = res.data
    } else {
      alert(res.message || '分析失败')
    }
  } catch (err) {
    alert('胸片分析服务暂不可用，请稍后重试')
  } finally {
    analyzing.value = false
  }
}

const saveToDb = async () => {
  if (!patientName.value) {
    alert('请输入患者姓名')
    return
  }

  try {
    const detections = result.value?.detections || []
    const aiReport = result.value?.ai_report || {}
    
    const saveData = {
      patient_name: patientName.value,
      patient_id: '',
      original_filename: selectedFile.value?.name || 'chest_xray',
      detections: JSON.stringify(detections),
      report_content: aiReport.diagnosis || aiReport.reasoning_content || '',
      annotated_image_base64: result.value?.annotated_image?.split(',')[1] || ''
    }

    const res = await api.saveChestXrayResult(saveData)
    if (res.code === 200) {
      alert('已保存到数据库')
      emit('close')
    } else {
      alert(res.message || '保存失败')
    }
  } catch (err) {
    alert('保存失败，请重试')
  }
}
</script>

<style scoped>
.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.6);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.chest-xray-modal {
  background: white;
  border-radius: 12px;
  width: 700px;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid #eee;
  background: #2c3e50;
  color: white;
}

.modal-header h3 {
  margin: 0;
  font-size: 18px;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 28px;
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  padding: 30px;
  overflow-y: auto;
  flex: 1;
}

.upload-section {
  margin-bottom: 20px;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 40px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.3s;
}

.upload-area:hover {
  border-color: #3498db;
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  color: #999;
}

.upload-icon {
  font-size: 48px;
  color: #3498db;
}

.image-preview img {
  max-width: 100%;
  max-height: 300px;
  border-radius: 8px;
}

.btn-analyze {
  width: 100%;
  padding: 14px;
  background: #e67e22;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  margin-bottom: 20px;
}

.btn-analyze:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.results-section h4 {
  margin: 15px 0 10px;
  color: #2c3e50;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.detections-list {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.detection-item {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
}

.detection-item:last-child {
  margin-bottom: 0;
}

.det-name {
  width: 100px;
  font-weight: 500;
}

.confidence-bar {
  flex: 1;
  height: 20px;
  background: #eee;
  border-radius: 10px;
  overflow: hidden;
  margin: 0 10px;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #27ae60, #2ecc71);
  border-radius: 10px;
  transition: width 0.3s;
}

.confidence-text {
  width: 45px;
  text-align: right;
  color: #666;
}

.no-detection {
  text-align: center;
  color: #27ae60;
  padding: 20px;
}

.ai-report {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 15px;
}

.ai-report pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
}

.annotated-section {
  margin-top: 15px;
}

.annotated-image {
  max-width: 100%;
  border-radius: 8px;
  border: 2px solid #eee;
}

.patient-section {
  margin-top: 20px;
}

.patient-input input {
  width: 100%;
  padding: 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
}

.action-buttons {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.btn-save {
  flex: 1;
  padding: 12px;
  background: #27ae60;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  background: #95a5a6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
}
</style>
```

- [ ] **Step 2: Commit**

```bash
git add medical-system-backend-fastapi/medical-system-backend-fastapi/frontend/src/views/ChestXray.vue
git commit -m "feat(frontend): add ChestXray.vue popup component"
```

---

## Task 6: End-to-End Verification

**Files:**
- Test: Run both services

- [ ] **Step 1: Start chest X-ray backend (8000)**

```bash
cd D:/Project/test/sec/backend
python main.py
```

Verify it's running on port 8000.

- [ ] **Step 2: Start medical system backend (8084)**

```bash
cd medical-system-backend-fastapi/medical-system-backend-fastapi
python main.py
```

- [ ] **Step 3: Start medical system frontend (8082)**

```bash
cd medical-system-backend-fastapi/medical-system-backend-fastapi/frontend
npm run dev
```

- [ ] **Step 4: Open browser and test**

1. Navigate to http://localhost:8082
2. Login with admin/123456
3. Click "胸片检测" in sidebar
4. Upload a chest X-ray image
5. Click "开始分析"
6. Verify results display correctly
7. Enter patient name and click "存入数据库"
8. Verify data appears in "影像管理"

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "feat: complete chest-xray detection module integration

- Add pdf_path field to MedicalImage model
- Add /api/chest-xray/analyze endpoint (gateway to 8000 service)
- Add /api/chest-xray/save endpoint
- Add ChestXray.vue popup component
- Integrate into Layout sidebar"
```

---

## Self-Review Checklist

- [ ] All 5 tasks completed with checkboxes
- [ ] No placeholder/TODO comments in code
- [ ] API endpoints match spec (analyze returns detections, ai_report, images)
- [ ] Frontend component matches modal layout from spec
- [ ] Error handling returns friendly Chinese messages
- [ ] Patient association supports both new name and existing patient selection
