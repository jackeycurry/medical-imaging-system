<template>
  <div class="detection-page">
    <div class="page-header">
      <h2>{{ detectionTitle }}</h2>
    </div>

    <div class="page-body">
      <!-- 全局消息提示 -->
      <div v-if="message.text" class="global-message" :class="message.type">
        {{ message.text }}
      </div>

      <!-- 患者信息区 -->
      <div class="section">
        <div class="section-title">
          <span class="title-dot"></span>
          患者信息
        </div>
        <div class="patient-search">
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索已有患者..."
            @input="searchPatients"
          />
          <div v-if="searchResults.length > 0" class="search-dropdown">
            <div
              v-for="p in searchResults"
              :key="p.id"
              class="search-item"
              @click="selectPatient(p)"
            >
              <span class="patient-name">{{ p.name }}</span>
              <span class="patient-info">{{ p.gender }} · {{ p.age }}岁 · {{ p.phone }}</span>
            </div>
          </div>
        </div>

        <div class="form-grid">
          <div class="form-item">
            <label>姓名 <span class="required">*</span></label>
            <input v-model="form.name" type="text" placeholder="患者姓名" />
          </div>
          <div class="form-item">
            <label>性别 <span class="required">*</span></label>
            <select v-model="form.gender">
              <option value="">选择</option>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </div>
          <div class="form-item">
            <label>年龄 <span class="required">*</span></label>
            <input v-model="form.age" type="number" placeholder="年龄" />
          </div>
          <div class="form-item">
            <label>电话 <span class="required">*</span></label>
            <input v-model="form.phone" type="tel" placeholder="手机号码" maxlength="11" />
          </div>
        </div>
      </div>

      <!-- 图片上传区 -->
      <div class="section">
        <div class="section-title">
          <span class="title-dot"></span>
          影像上传
        </div>
        <div class="upload-zone" @click="selectFile">
          <input type="file" ref="fileInput" accept="image/*" @change="handleFileSelect" hidden />
          <template v-if="!previewUrl">
            <div class="upload-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                <polyline points="17,8 12,3 7,8"/>
                <line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
            </div>
            <p class="upload-text" v-if="isPatientInfoComplete">{{ uploadPlaceholder }}</p>
            <p class="upload-hint" v-else>请先填写患者信息</p>
          </template>
          <template v-else>
            <img :src="previewUrl" alt="预览" class="preview-img" />
            <div class="preview-overlay">
              <span>点击更换图片</span>
            </div>
          </template>
        </div>
      </div>

      <!-- 分析按钮 -->
      <button
        class="btn-analyze"
        @click="analyze"
        :disabled="!selectedFile || analyzing"
      >
        <span v-if="analyzing" class="loading-spinner"></span>
        {{ analyzing ? '分析中...' : '开始分析' }}
      </button>

      <!-- 症状选择区 -->
      <div class="section">
        <div class="section-title">
          <span class="title-dot"></span>
          症状描述
          <span class="optional-tag">选填</span>
        </div>
        <template v-if="currentSymptoms.length > 0">
          <div class="symptoms-grid">
            <div class="symptom-item" v-for="symptom in currentSymptoms" :key="symptom.key">
              <label>{{ symptom.label }}</label>
              <div class="radio-group">
                <label class="radio-btn" :class="{ active: form.symptoms[symptom.key] === '有' }">
                  <input type="radio" v-model="form.symptoms[symptom.key]" value="有" />
                  <span>有</span>
                </label>
                <label class="radio-btn" :class="{ active: form.symptoms[symptom.key] === '无' }">
                  <input type="radio" v-model="form.symptoms[symptom.key]" value="无" />
                  <span>无</span>
                </label>
              </div>
            </div>
          </div>
        </template>
        <template v-else>
          <textarea
            v-model="form.customSymptoms"
            placeholder="请描述症状..."
            rows="3"
          ></textarea>
        </template>
        <textarea
          v-model="form.notes"
          placeholder="补充说明..."
          rows="2"
          class="notes-input"
        ></textarea>
      </div>

      <!-- 检测结果 -->
      <div v-if="result" class="section result-section">
        <div class="section-title">
          <span class="title-dot"></span>
          检测结果
        </div>

        <!-- 异常检测列表 -->
        <div class="detections-list">
          <div class="detection-item" v-for="(det, idx) in result.detections" :key="idx">
            <span class="detection-name">{{ det.class_name_cn || det.class_name }}</span>
            <div class="confidence-track">
              <div class="confidence-fill" :style="{ width: (det.confidence * 100) + '%' }"></div>
            </div>
            <span class="confidence-value">{{ (det.confidence * 100).toFixed(0) }}%</span>
          </div>
          <div v-if="!result.detections || result.detections.length === 0" class="no-detection">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <path d="M9 12l2 2 4-4"/>
            </svg>
            <span>未检测到异常</span>
          </div>
        </div>

        <!-- 影像学印象 -->
        <div class="ai-report" v-if="result.ai_report?.impression">
          <div class="report-label">影像学印象</div>
          <div class="report-content impression-box">
            {{ result.ai_report.impression }}
          </div>
        </div>

        <!-- AI 完整诊断报告 -->
        <div class="ai-report" v-if="result.formatted_report">
          <div class="report-label">AI 完整诊断报告</div>
          <div class="report-content formatted-report-box">
            {{ result.formatted_report }}
          </div>
        </div>
        <div class="ai-report" v-else-if="result.ai_report">
          <div class="report-label">AI 诊断报告</div>
          <div class="report-content">
            {{ result.ai_report?.diagnosis || result.ai_report?.reasoning_content || '暂无' }}
          </div>
        </div>

        <!-- 临床建议 -->
        <div class="ai-report" v-if="result.ai_report?.recommendations">
          <div class="report-label">临床建议</div>
          <div class="report-content rec-box">
            {{ result.ai_report.recommendations }}
          </div>
        </div>

        <div class="annotated-image" v-if="result.annotated_image">
          <div class="report-label">标注图像</div>
          <img :src="result.annotated_image" alt="标注图" />
        </div>

        <div class="result-actions">
          <button class="btn-save" @click="saveToDb">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M19 21H5a2 2 0 01-2-2V5a2 2 0 012-2h11l5 5v11a2 2 0 01-2 2z"/>
              <polyline points="17,21 17,13 7,13 7,21"/>
              <polyline points="7,3 7,8 15,8"/>
            </svg>
            保存到数据库
          </button>
          <button v-if="result.pdf_url" class="btn-pdf" @click="downloadPdf">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
              <polyline points="14,2 14,8 20,8"/>
              <line x1="12" y1="18" x2="12" y2="12"/>
              <polyline points="9,15 12,18 15,15"/>
            </svg>
            导出PDF报告
          </button>
        </div>
      </div>
    </div>

    <!-- 重复保存提示弹窗 -->
    <div v-if="showDuplicateModal" class="modal-overlay" @click.self="showDuplicateModal = false">
      <div class="modal-box">
        <div class="modal-icon">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
        </div>
        <div class="modal-title">提示</div>
        <div class="modal-body">该检查结果已保存，请勿重复保存</div>
        <button class="modal-btn" @click="showDuplicateModal = false">我知道了</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '../api'

const props = defineProps({
  detectionType: { type: String, default: 'chest' }
})
const emit = defineEmits(['close'])

const symptomsConfig = {
  chest: [
    { key: 'smoke', label: '吸烟' },
    { key: 'cough', label: '咳嗽' },
    { key: 'chestPain', label: '胸痛' },
    { key: 'dyspnea', label: '呼吸困难' }
  ],
  brain: [
    { key: 'headache', label: '头痛' },
    { key: 'dizziness', label: '头晕' },
    { key: 'nausea', label: '恶心' }
  ],
  retina: [
    { key: 'blurredVision', label: '视力模糊' },
    { key: 'eyePain', label: '眼痛' },
    { key: 'visualDefect', label: '视野缺损' }
  ],
  abdomen: [
    { key: 'abdominalPain', label: '腹痛' },
    { key: 'nausea', label: '恶心呕吐' },
    { key: 'jaundice', label: '黄疸' },
    { key: 'bloating', label: '腹胀' }
  ],
  spine: [
    { key: 'backPain', label: '腰背痛' },
    { key: 'limbNumbness', label: '肢体麻木' },
    { key: 'gaitAbnormal', label: '行走异常' },
    { key: 'trauma', label: '外伤史' }
  ],
  breast: [
    { key: 'breastLump', label: '乳房肿块' },
    { key: 'breastPain', label: '乳房疼痛' },
    { key: 'nippleDischarge', label: '乳头溢液' },
    { key: 'familyHistory', label: '家族史' }
  ],
  cardiovascular: [
    { key: 'chestPain', label: '胸痛' },
    { key: 'palpitation', label: '心悸' },
    { key: 'dyspnea', label: '呼吸困难' },
    { key: 'hypertension', label: '高血压病史' }
  ],
  other: []
}

const detectionTitles = {
  chest: '胸片检测', brain: '脑部检测', retina: '视网膜检测',
  abdomen: '腹部检测', spine: '脊柱检测', breast: '乳腺检测',
  cardiovascular: '心血管检测', other: '其他检测'
}

const uploadPlaceholders = {
  chest: '点击上传胸片图片',
  brain: '点击上传脑部CT/MRI',
  retina: '点击上传视网膜图片',
  abdomen: '点击上传腹部CT/MRI/超声',
  spine: '点击上传脊柱X光/CT/MRI',
  breast: '点击上传乳腺钼靶/超声/MRI',
  cardiovascular: '点击上传心血管CTA/MRA/超声',
  other: '点击上传医学影像'
}

const selectedFile = ref(null)
const previewUrl = ref('')
const analyzing = ref(false)
const result = ref(null)
const saved = ref(false)
const patients = ref([])
const searchText = ref('')
const searchResults = ref([])
const message = ref({ type: '', text: '' })
const showDuplicateModal = ref(false)

const form = reactive({
  name: '', gender: '', age: '', phone: '',
  symptoms: {}, customSymptoms: '', notes: ''
})

const fileInput = ref(null)

const detectionTitle = computed(() => detectionTitles[props.detectionType] || '医学检测')
const uploadPlaceholder = computed(() => uploadPlaceholders[props.detectionType])
const currentSymptoms = computed(() => symptomsConfig[props.detectionType] || [])

const isPatientInfoComplete = computed(() => {
  return form.name && form.gender && form.age && form.phone && /^\d{11}$/.test(form.phone)
})

onMounted(() => { loadPatients(); initSymptoms() })

const initSymptoms = () => {
  const symptoms = {}
  currentSymptoms.value.forEach(s => { symptoms[s.key] = '' })
  form.symptoms = symptoms
}

const loadPatients = async () => {
  try {
    const res = await api.getPatients()
    if (res.data) patients.value = res.data
  } catch (e) { console.error(e) }
}

const searchPatients = () => {
  if (!searchText.value) { searchResults.value = []; return }
  const keyword = searchText.value.toLowerCase()
  searchResults.value = patients.value.filter(p => p.name?.toLowerCase().includes(keyword))
}

const selectPatient = (p) => {
  form.name = p.name || ''
  form.gender = p.gender || ''
  form.age = p.age || ''
  form.phone = p.phone || ''
  searchText.value = ''
  searchResults.value = []
}

const showMessage = (type, text) => {
  message.value = { type, text }
  setTimeout(() => { message.value = { type: '', text: '' } }, 3000)
}

const selectFile = () => {
  if (!isPatientInfoComplete.value) {
    showMessage('warning', '请先填写完整的患者信息')
    return
  }
  fileInput.value.click()
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file)
    result.value = null
    saved.value = false
  }
}

const analyze = async () => {
  if (!selectedFile.value) return
  analyzing.value = true
  result.value = null
  saved.value = false

  const formData = new FormData()
  formData.append('file', selectedFile.value)
  formData.append('user_info', JSON.stringify({
    name: form.name,
    gender: form.gender,
    age: form.age,
    phone: form.phone
  }))
  formData.append('symptoms', JSON.stringify(
    currentSymptoms.value.length > 0 ? { ...form.symptoms } : { custom: form.customSymptoms || '' }
  ))

  try {
    if (props.detectionType === 'chest') {
      const res = await api.analyzeChestXray(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else if (props.detectionType === 'brain') {
      const res = await api.analyzeBrain(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else if (props.detectionType === 'retina') {
      const res = await api.analyzeRetina(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else if (props.detectionType === 'abdomen') {
      const res = await api.analyzeAbdomen(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else if (props.detectionType === 'spine') {
      const res = await api.analyzeSpine(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else if (props.detectionType === 'breast') {
      const res = await api.analyzeBreast(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else if (props.detectionType === 'cardiovascular') {
      const res = await api.analyzeCardiovascular(formData)
      if (res.code === 200 && res.data) {
        result.value = res.data
        showMessage('success', '分析完成')
      } else {
        showMessage('error', res.message || '分析失败')
      }
    } else {
      await new Promise(r => setTimeout(r, 1500))
      result.value = {
        detections: [{ class_name: 'Demo', class_name_cn: '演示发现', confidence: 0.85 }],
        ai_report: { diagnosis: '演示结果，实际功能开发中...' }
      }
    }
  } catch (err) {
    showMessage('error', '分析服务暂不可用')
  } finally {
    analyzing.value = false
  }
}

const saveToDb = async () => {
  if (saved.value) {
    showDuplicateModal.value = true
    return
  }
  if (!isPatientInfoComplete.value) {
    showMessage('warning', '请填写完整的患者信息')
    return
  }

  try {
    const detections = result.value?.detections || []
    const aiReport = result.value?.ai_report || {}
    const symptomsData = props.detectionType === 'other'
      ? { custom: form.customSymptoms }
      : { ...form.symptoms }

    const patientInfo = {
      name: form.name, gender: form.gender, age: form.age, phone: form.phone,
      symptoms: symptomsData, notes: form.notes, detectionType: props.detectionType
    }

    const saveData = {
      patient_name: form.name,
      patient_id: form.phone,
      original_filename: selectedFile.value?.name || 'medical_image',
      detections: JSON.stringify(detections),
      report_content: JSON.stringify({ ai_diagnosis: aiReport.diagnosis || aiReport.reasoning_content || '', patient_info: patientInfo }),
      annotated_image_base64: result.value?.annotated_image?.split(',')[1] || ''
    }

    const res = await api.saveChestXrayResult(saveData)
    if (res.code === 200) {
      saved.value = true
      showMessage('success', '已保存到数据库')
      setTimeout(() => emit('close'), 1500)
    } else {
      showMessage('error', res.message || '保存失败')
    }
  } catch (err) {
    showMessage('error', '保存失败')
  }
}

const downloadPdf = async () => {
  const reportId = result.value?.report_id
  if (!reportId) {
    showMessage('error', '报告ID不存在')
    return
  }
  try {
    showMessage('success', '正在下载PDF报告...')
    const blob = await api.downloadPdf(reportId)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${reportId}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    showMessage('success', 'PDF报告下载完成')
  } catch (err) {
    console.error('PDF download error:', err)
    showMessage('error', 'PDF下载失败，请确认报告已生成')
  }
}
</script>

<style scoped>
.detection-page {
  background: linear-gradient(180deg, #F5F7FA 0%, #FFFFFF 100%);
  min-height: 100vh;
}

.page-header {
  padding: 20px 32px;
  background: #fff;
  border-bottom: 1px solid #E8E8E8;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f1f1f;
}

.page-body {
  padding: 24px 32px;
  min-height: calc(100vh - 72px);
}

.global-message {
  padding: 14px 18px;
  border-radius: 8px;
  margin-bottom: 20px;
  font-size: 14px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.global-message.success {
  background: #F6FFED;
  color: #52C41A;
  border: 1px solid #B7EB8F;
}

.global-message.error {
  background: #FFF1F0;
  color: #FF4D4F;
  border: 1px solid #FFCCC7;
}

.global-message.warning {
  background: #FFFBE6;
  color: #FA8C16;
  border: 1px solid #FFE58F;
}

.section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 20px;
}

.title-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #1677FF;
}

.optional-tag {
  font-size: 12px;
  font-weight: 400;
  color: #999;
  margin-left: 4px;
}

.patient-search {
  position: relative;
  margin-bottom: 16px;
}

.patient-search input {
  width: 100%;
  padding: 12px 14px;
  border: 1px solid #E8E8E8;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.patient-search input:focus {
  outline: none;
  border-color: #1677FF;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.1);
}

.search-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1px solid #E8E8E8;
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
  z-index: 10;
  max-height: 200px;
  overflow-y: auto;
}

.search-item {
  padding: 14px 16px;
  cursor: pointer;
  border-bottom: 1px solid #F0F0F0;
  transition: background 0.15s;
}

.search-item:last-child { border-bottom: none; }
.search-item:hover { background: #F5F7FA; }

.patient-name {
  display: block;
  font-weight: 500;
  color: #1f1f1f;
  margin-bottom: 4px;
}

.patient-info {
  font-size: 13px;
  color: #999;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-item label {
  font-size: 14px;
  color: #666;
}

.form-item input,
.form-item select {
  padding: 10px 12px;
  border: 1px solid #E8E8E8;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.form-item input:focus,
.form-item select:focus {
  outline: none;
  border-color: #1677FF;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.1);
}

.required { color: #FF4D4F; }

.upload-zone {
  border: 2px dashed #D9D9D9;
  border-radius: 12px;
  padding: 48px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
  position: relative;
}

.upload-zone:hover {
  border-color: #1677FF;
  background: #F5F7FA;
}

.upload-icon svg {
  width: 48px;
  height: 48px;
  color: #1677FF;
}

.upload-text {
  color: #666;
  font-size: 14px;
  margin: 12px 0 0;
}

.upload-hint {
  color: #FF4D4F;
  font-size: 14px;
  margin: 12px 0 0;
}

.preview-img {
  max-width: 100%;
  max-height: 280px;
  border-radius: 8px;
}

.preview-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.5);
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}

.upload-zone:hover .preview-overlay { opacity: 1; }
.preview-overlay span { color: #fff; font-size: 14px; }

.btn-analyze {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 14px;
  background: #1677FF;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
  margin-bottom: 20px;
}

.btn-analyze:hover:not(:disabled) { background: #4096FF; }
.btn-analyze:disabled { background: #D9D9D9; cursor: not-allowed; }

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255,255,255,0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.symptoms-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.symptom-item label {
  display: block;
  font-size: 14px;
  color: #666;
  margin-bottom: 8px;
}

.radio-group {
  display: flex;
  gap: 12px;
}

.radio-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px;
  border: 1px solid #E8E8E8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #666;
}

.radio-btn input { display: none; }
.radio-btn.active {
  border-color: #1677FF;
  background: #E6F4FF;
  color: #1677FF;
}

textarea {
  width: 100%;
  padding: 12px;
  border: 1px solid #E8E8E8;
  border-radius: 8px;
  font-size: 14px;
  resize: vertical;
  box-sizing: border-box;
  font-family: inherit;
  transition: border-color 0.2s, box-shadow 0.2s;
}

textarea:focus {
  outline: none;
  border-color: #1677FF;
  box-shadow: 0 0 0 3px rgba(22,119,255,0.1);
}

.notes-input { margin-top: 16px; }

.result-section { border: 1px solid #1677FF; }

.detections-list {
  background: #FAFAFA;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 20px;
}

.detection-item {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.detection-item:last-child { margin-bottom: 0; }

.detection-name {
  width: 100px;
  font-size: 14px;
  font-weight: 500;
  color: #1f1f1f;
}

.confidence-track {
  flex: 1;
  height: 8px;
  background: #E8E8E8;
  border-radius: 4px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: linear-gradient(90deg, #1677FF, #52C41A);
  border-radius: 4px;
  transition: width 0.3s;
}

.confidence-value {
  width: 48px;
  text-align: right;
  font-size: 14px;
  font-weight: 500;
  color: #1677FF;
}

.no-detection {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  color: #52C41A;
  font-size: 14px;
}

.no-detection svg {
  width: 24px;
  height: 24px;
}

.ai-report { margin-bottom: 20px; }

.report-label {
  font-size: 14px;
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 10px;
}

.report-content {
  background: #FAFAFA;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  color: #333;
  white-space: pre-wrap;
  max-height: 500px;
  overflow-y: auto;
}

.impression-box {
  background: #FFF7E6;
  border: 1px solid #FFD591;
  color: #AD6800;
}

.formatted-report-box {
  font-family: 'Consolas', 'Courier New', 'SimHei', monospace;
  font-size: 13px;
  line-height: 1.6;
}

.rec-box {
  background: #F0F5FF;
  border: 1px solid #ADC6FF;
  color: #1D39C4;
}

.annotated-image img {
  max-width: 100%;
  border-radius: 8px;
  border: 1px solid #E8E8E8;
  margin-top: 10px;
}

.result-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
}

.btn-save {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  padding: 14px;
  background: #52C41A;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-save:hover { background: #73D13D; }
.btn-save svg { width: 18px; height: 18px; }

.btn-pdf {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 1;
  padding: 14px;
  background: #FA8C16;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-pdf:hover { background: #FFA940; }
.btn-pdf svg { width: 18px; height: 18px; }

/* 重复保存提示弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-box {
  background: #fff;
  border-radius: 12px;
  padding: 32px 40px 24px;
  text-align: center;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
  max-width: 360px;
  width: 90%;
}

.modal-icon {
  margin-bottom: 16px;
}

.modal-icon svg {
  width: 48px;
  height: 48px;
  color: #FA8C16;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: #1f1f1f;
  margin-bottom: 12px;
}

.modal-body {
  font-size: 14px;
  color: #666;
  margin-bottom: 24px;
  line-height: 1.6;
}

.modal-btn {
  padding: 10px 48px;
  background: #1677FF;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.modal-btn:hover { background: #4096FF; }
</style>
