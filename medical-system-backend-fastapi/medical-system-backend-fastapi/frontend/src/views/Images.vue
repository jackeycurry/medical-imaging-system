<template>
  <div class="images">
    <div class="header">
      <h2>影像管理</h2>
      <button @click="showUpload = true">上传影像</button>
    </div>

    <div class="search-bar">
      <input v-model="searchName" placeholder="搜索患者姓名" @input="search" />
    </div>

    <!-- 患者分组列表 -->
    <div class="patient-list">
      <div
        v-for="(group, index) in groupedImages"
        :key="index"
        class="patient-group"
      >
        <div class="patient-header" @click="toggleGroup(index)">
          <div class="patient-info">
            <span class="expand-icon">{{ expandedIndex === index ? '▼' : '▶' }}</span>
            <span class="patient-name">{{ group.patientName }}</span>
            <span class="image-count">共 {{ group.images.length }} 条记录</span>
          </div>
          <div class="patient-meta">
            <span class="latest-time">最新: {{ formatTime(group.latestTime) }}</span>
          </div>
        </div>

        <div v-if="expandedIndex === index" class="patient-images">
          <table>
            <thead>
              <tr>
                <th>体检号</th><th>影像类型</th><th>状态</th><th>创建时间</th><th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="img in group.images" :key="img.id">
                <td>{{ img.patientId || '-' }}</td>
                <td>{{ img.imageType }}</td>
                <td><span :class="'status-' + img.status">{{ img.status }}</span></td>
                <td>{{ formatTime(img.createTime) }}</td>
                <td>
                  <button @click="viewImage(img)" class="btn-view">查看</button>
                  <button @click="deleteImage(img.id)" class="btn-del">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="groupedImages.length === 0" class="empty-state">
        暂无影像记录
      </div>
    </div>

    <!-- 上传影像弹窗 -->
    <div v-if="showUpload" class="modal">
      <div class="modal-content wide">
        <h3>上传影像分析</h3>
        <div class="upload-area">
          <input type="file" accept="image/*" @change="handleFileSelect" ref="fileInput" />
          <div v-if="previewUrl" class="preview">
            <img :src="previewUrl" alt="影像预览" />
          </div>
        </div>
        <input v-model="form.patient_name" placeholder="患者姓名" />
        <input v-model="form.patient_id" placeholder="体检号" />
        <button v-if="selectedFile && !analyzing" @click="analyzeCt" class="btn-analyze">开始分析</button>
        <button v-if="analyzing" class="btn-analyze" disabled>分析中...</button>

        <div v-if="result" class="result-box" :class="{ alert: result.lesionDetected }">
          <div class="result-header">
            <span v-if="result.lesionDetected" class="badge danger">发现病灶</span>
            <span v-else class="badge success">未见异常</span>
            <span class="confidence">置信度: {{ result.confidence }}%</span>
          </div>
          <div class="result-body">
            <p><strong>病灶类型:</strong> {{ result.lesionType }}</p>
            <p><strong>位置估计:</strong> {{ result.position }}</p>
            <p><strong>严重程度:</strong> {{ result.severity }}</p>
            <div class="report">
              <strong>AI报告:</strong>
              <p>{{ result.report }}</p>
            </div>
          </div>
          <button @click="saveToHistory" class="btn-save">保存到历史记录</button>
        </div>

        <div class="btns">
          <button @click="closeUpload">关闭</button>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="viewing" class="modal">
      <div class="modal-content wide">
        <h3>影像详情</h3>
        <div class="detail-grid">
          <div class="detail-item"><label>患者姓名:</label><span>{{ viewing.patientName }}</span></div>
          <div class="detail-item"><label>体检号:</label><span>{{ viewing.patientId }}</span></div>
          <div class="detail-item"><label>影像类型:</label><span>{{ viewing.imageType }}</span></div>
          <div class="detail-item"><label>状态:</label><span>{{ viewing.status }}</span></div>
          <div class="detail-item full" v-if="viewingImage">
            <label>标注影像:</label>
            <div class="image-preview"><img :src="'data:image/png;base64,' + viewingImage" alt="标注图" /></div>
          </div>
          <div class="detail-item full" v-if="viewing.detections"><label>检测结果:</label>
            <div class="detections-formatted">
              <div v-for="(det, idx) in formatDetections(viewing.detections)" :key="idx" class="det-row">
                <span class="det-name">{{ det.class_name_cn || det.class_name }}</span>
                <span class="det-confidence">{{ ((det.confidence || 0) * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
          <div class="detail-item full" v-if="viewing.reportContent"><label>报告内容:</label>
            <div class="report-formatted" v-html="formatReport(viewing.reportContent)"></div>
          </div>
        </div>
        <div class="btns"><button @click="viewing = null">关闭</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../api'

const images = ref([])
const searchName = ref('')
const showUpload = ref(false)
const viewing = ref(null)
const viewingImage = ref(null)
const selectedFile = ref(null)
const previewUrl = ref('')
const analyzing = ref(false)
const result = ref(null)
const fileInput = ref(null)
const expandedIndex = ref(null)
const form = ref({ patient_name: '', patient_id: '' })

const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  const offset = 8 * 60 * 60 * 1000
  const bjTime = new Date(d.getTime() + offset)
  return bjTime.toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-')
}

onMounted(() => fetchImages())

const fetchImages = () => api.getImages().then(res => { if (res.data) images.value = res.data })

const search = () => api.getImages(searchName.value ? { patientName: searchName.value } : {}).then(res => { if (res.data) images.value = res.data })

const groupedImages = computed(() => {
  const groups = {}
  images.value.forEach(img => {
    const name = img.patientName || '未知患者'
    if (!groups[name]) {
      groups[name] = {
        patientName: name,
        images: [],
        latestTime: img.createTime
      }
    }
    groups[name].images.push(img)
    if (img.createTime > groups[name].latestTime) {
      groups[name].latestTime = img.createTime
    }
  })
  return Object.values(groups)
})

const toggleGroup = (index) => {
  expandedIndex.value = expandedIndex.value === index ? null : index
}

const handleFileSelect = (e) => {
  const file = e.target.files[0]
  if (file) {
    selectedFile.value = file
    previewUrl.value = URL.createObjectURL(file)
    result.value = null
  }
}

const analyzeCt = async () => {
  if (!selectedFile.value) return
  analyzing.value = true
  result.value = null

  const reader = new FileReader()
  reader.onload = async (e) => {
    const base64 = e.target.result.split(',')[1]
    try {
      const res = await api.analyzeCt(base64, form.value.patient_name, form.value.patient_id)
      if (res.data) {
        result.value = res.data
      } else {
        alert(res.message || '分析失败')
      }
    } catch (err) {
      alert('分析请求失败')
    } finally {
      analyzing.value = false
    }
  }
  reader.readAsDataURL(selectedFile.value)
}

const saveToHistory = () => {
  if (result.value) {
    fetchImages()
    alert('已保存到历史记录')
  }
}

const viewImage = async (img) => {
  viewingImage.value = null
  const res = await api.getImage(img.id)
  if (res.data) viewing.value = res.data
  try {
    const imgRes = await api.getImageData(img.id)
    if (imgRes.data?.image) viewingImage.value = imgRes.data.image
  } catch (e) { /* 旧记录可能没有图片 */ }
}

const deleteImage = async (id) => { if (confirm('确认删除？')) await api.deleteImage(id) && fetchImages() }

const closeUpload = () => {
  showUpload.value = false
  selectedFile.value = null
  previewUrl.value = ''
  result.value = null
  form.value = { patient_name: '', patient_id: '' }
  if (fileInput.value) fileInput.value.value = ''
}

const formatDetections = (detections) => {
  if (!detections) return []
  try {
    const parsed = typeof detections === 'string' ? JSON.parse(detections) : detections
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const formatReport = (reportContent) => {
  if (!reportContent) return ''
  try {
    const parsed = typeof reportContent === 'string' ? JSON.parse(reportContent) : reportContent
    let html = ''

    if (parsed.patient_info) {
      const info = parsed.patient_info
      html += '<div class="report-section"><h5>患者信息</h5>'
      html += '<p><strong>姓名：</strong>' + (info.name || '-') + '</p>'
      html += '<p><strong>性别：</strong>' + (info.gender || '-') + '</p>'
      html += '<p><strong>年龄：</strong>' + (info.age || '-') + '</p>'
      html += '<p><strong>电话：</strong>' + (info.phone || '-') + '</p>'
      html += '</div>'
    }

    if (parsed.patient_info?.symptoms) {
      const s = parsed.patient_info.symptoms
      html += '<div class="report-section"><h5>症状信息</h5>'
      if (s.smoke) html += '<p><strong>吸烟：</strong>' + s.smoke + '</p>'
      if (s.cough) html += '<p><strong>咳嗽：</strong>' + s.cough + '</p>'
      if (s.chestPain) html += '<p><strong>胸痛：</strong>' + s.chestPain + '</p>'
      if (s.dyspnea) html += '<p><strong>呼吸困难：</strong>' + s.dyspnea + '</p>'
      if (s.notes) html += '<p><strong>补充说明：</strong>' + s.notes + '</p>'
      html += '</div>'
    }

    if (parsed.ai_diagnosis) {
      const diagnosis = parsed.ai_diagnosis.replace(/\n/g, '<br>')
      html += '<div class="report-section"><h5>AI诊断报告</h5><p class="ai-text">' + diagnosis + '</p></div>'
    }

    return html
  } catch {
    return '<p>' + reportContent + '</p>'
  }
}
</script>

<style scoped>
.header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; padding: 20px 24px; background: #fff; border-radius: 8px; border: 1px solid #e8e8e8; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
.header h2 { margin: 0; font-size: 18px; font-weight: 600; color: #1f1f1f; }
.header button { background: #1677FF; color: white; border: none; padding: 10px 20px; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
.header button:hover { background: #4096FF; }
.search-bar { margin-bottom: 15px; }
.search-bar input { padding: 10px 12px; width: 300px; border: 1px solid #e8e8e8; border-radius: 6px; font-size: 14px; transition: border-color 0.2s; }
.search-bar input:focus { outline: none; border-color: #1677FF; }

.patient-list { display: flex; flex-direction: column; gap: 10px; }
.patient-group { background: #fff; border: 1px solid #e8e8e8; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); transition: box-shadow 0.2s; }
.patient-group:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.patient-header { display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; cursor: pointer; transition: background 0.2s; }
.patient-header:hover { background: #F5F7FA; }
.patient-info { display: flex; align-items: center; gap: 12px; }
.expand-icon { color: #999; font-size: 12px; }
.patient-name { font-weight: 600; font-size: 15px; color: #1f1f1f; }
.image-count { background: #E6F4FF; color: #1677FF; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 500; }
.patient-meta { color: #999; font-size: 13px; }

.patient-images { border-top: 1px solid #e8e8e8; }
.patient-images table { width: 100%; border-collapse: collapse; }
.patient-images th { background: #FAFAFA; padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; color: #1f1f1f; border-bottom: 1px solid #e8e8e8; }
.patient-images td { padding: 14px 16px; border-bottom: 1px solid #e8e8e8; font-size: 14px; color: #1f1f1f; }
.patient-images tr:last-child td { border-bottom: none; }
.patient-images tr:hover { background: #F5F7FA; }

.empty-state { text-align: center; padding: 60px 20px; color: #999; font-size: 14px; background: #fff; border-radius: 8px; border: 1px dashed #d9d9d9; }

.status-已完成 { color: #52C41A; font-weight: 500; }
.status-待检测 { color: #FAAD14; }
.btn-view, .btn-del { padding: 6px 12px; border: none; border-radius: 4px; cursor: pointer; margin-right: 8px; font-size: 13px; transition: all 0.2s; }
.btn-view { background: #fff; color: #1677FF; border: 1px solid #1677FF; }
.btn-view:hover { background: #E6F4FF; }
.btn-del { background: #fff; color: #FF4D4F; border: 1px solid #FF4D4F; }
.btn-del:hover { background: #FFF1F0; }

.modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.45); display: flex; justify-content: center; align-items: center; z-index: 1000; backdrop-filter: blur(2px); }
.modal-content { background: #fff; padding: 24px; border-radius: 8px; width: 450px; max-height: 90vh; overflow-y: auto; box-shadow: 0 6px 16px rgba(0,0,0,0.15); }
.modal-content.wide { width: 550px; }
.modal-content h3 { margin: 0 0 20px; font-size: 16px; font-weight: 600; color: #1f1f1f; }
.modal-content form input[type="file"] { margin-bottom: 15px; }
.modal-content form input[type="text"] { width: 100%; padding: 10px 12px; margin-bottom: 12px; border: 1px solid #e8e8e8; border-radius: 6px; box-sizing: border-box; font-size: 14px; transition: border-color 0.2s; }
.modal-content form input[type="text"]:focus { outline: none; border-color: #1677FF; }
.upload-area { margin-bottom: 15px; }
.upload-area .preview { margin-top: 10px; text-align: center; }
.upload-area .preview img { max-width: 100%; max-height: 200px; border-radius: 8px; border: 2px solid #eee; }
.btn-analyze { width: 100%; padding: 12px; background: #1677FF; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; margin-bottom: 15px; transition: background 0.2s; }
.btn-analyze:hover { background: #4096FF; }
.btn-analyze:disabled { background: #D9D9D9; }
.result-box { background: #F5F7FA; border-radius: 8px; padding: 16px; margin-bottom: 15px; border: 1px solid #52C41A; }
.result-box.alert { border-color: #e74c3c; }
.result-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.badge { padding: 4px 12px; border-radius: 12px; font-size: 12px; font-weight: bold; }
.badge.danger { background: #FFF1F0; color: #FF4D4F; }
.badge.success { background: #F6FFED; color: #52C41A; }
.confidence { color: #666; font-size: 14px; }
.result-body p { margin: 8px 0; font-size: 14px; color: #1f1f1f; }
.report { background: white; padding: 10px; border-radius: 6px; margin-top: 10px; }
.report p { margin: 5px 0; font-size: 14px; }
.btn-save { width: 100%; padding: 12px; background: #1677FF; color: white; border: none; border-radius: 6px; cursor: pointer; margin-top: 12px; font-size: 14px; font-weight: 500; transition: background 0.2s; }
.btn-save:hover { background: #4096FF; }
.detail-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin: 20px 0; }
.detail-item.full { grid-column: 1 / -1; }
.detail-item label { font-weight: 600; color: #666; display: block; margin-bottom: 6px; font-size: 13px; }
.detail-item span { color: #1f1f1f; font-size: 14px; }
.detail-item pre { background: #F5F7FA; padding: 12px; border-radius: 6px; margin: 0; white-space: pre-wrap; font-size: 14px; }
.detections-formatted { background: #F5F7FA; padding: 12px; border-radius: 6px; }
.det-row { display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #E8E8E8; }
.det-row:last-child { border-bottom: none; }
.det-name { font-weight: 500; color: #1f1f1f; }
.det-confidence { color: #1677FF; font-weight: 500; }
.image-preview { text-align: center; background: #000; padding: 12px; border-radius: 6px; }
.image-preview img { max-width: 100%; max-height: 400px; border-radius: 4px; }
.report-formatted { background: #F5F7FA; padding: 16px; border-radius: 6px; }
.report-section { margin-bottom: 16px; }
.report-section:last-child { margin-bottom: 0; }
.report-section h5 { margin: 0 0 10px; color: #1f1f1f; font-size: 14px; font-weight: 600; border-bottom: 1px solid #E8E8E8; padding-bottom: 8px; }
.report-section p { margin: 6px 0; font-size: 14px; line-height: 1.6; color: #1f1f1f; }
.report-section .ai-text { background: #fff; padding: 12px; border-radius: 6px; margin-top: 8px; line-height: 1.8; }
.btns { display: flex; gap: 12px; margin-top: 20px; }
.btns button { flex: 1; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; }
.btns button:first-child { background: #fff; color: #666; border: 1px solid #D9D9D9; }
.btns button:first-child:hover { color: #1677FF; border-color: #1677FF; }
</style>
