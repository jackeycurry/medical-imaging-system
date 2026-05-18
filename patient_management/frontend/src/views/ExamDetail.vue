<template>
  <div class="exam-detail" v-loading="loading">
    <el-button @click="$router.back()">返回</el-button>

    <el-card style="margin-top: 20px">
      <template #header>患者信息</template>
      <el-descriptions :column="4" border>
        <el-descriptions-item label="姓名">{{ exam.patient_name }}</el-descriptions-item>
        <el-descriptions-item label="检查日期">{{ exam.exam_date }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(exam.status)">{{ getStatusText(exam.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(exam.created_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 20px" v-if="exam.questionnaire">
      <template #header>问卷答案</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="主要症状">{{ getSymptomText(exam.questionnaire.main_symptoms) }}</el-descriptions-item>
        <el-descriptions-item label="症状持续时间">{{ getDurationText(exam.questionnaire.symptom_duration) }}</el-descriptions-item>
        <el-descriptions-item label="既往肺部疾病">{{ getDiseaseText(exam.questionnaire.past_lung_disease) }}</el-descriptions-item>
        <el-descriptions-item label="吸烟史">{{ getSmokingText(exam.questionnaire.smoking_history) }}</el-descriptions-item>
        <el-descriptions-item label="职业暴露">{{ getExposureText(exam.questionnaire.occupational_exposure) }}</el-descriptions-item>
        <el-descriptions-item label="家族病史">{{ exam.questionnaire.family_lung_history ? '有' : '无' }}</el-descriptions-item>
        <el-descriptions-item label="最近X光">{{ getXrayText(exam.questionnaire.last_xray_time) }}</el-descriptions-item>
        <el-descriptions-item label="检查目的">{{ getPurposeText(exam.questionnaire.exam_purpose) }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ exam.questionnaire.notes || '-' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 20px" v-if="exam.original_image_path || exam.annotated_image_path">
      <template #header>影像资料</template>
      <div class="image-compare">
        <div class="image-box">
          <p>原始图像</p>
          <el-image v-if="exam.original_image_path" :src="getImageUrl(exam.original_image_path)" fit="contain" style="width: 100%; height: 300px" />
        </div>
        <div class="image-box">
          <p>标注图像</p>
          <el-image v-if="exam.annotated_image_path" :src="getImageUrl(exam.annotated_image_path)" fit="contain" style="width: 100%; height: 300px" />
        </div>
      </div>
    </el-card>

    <el-card style="margin-top: 20px" v-if="exam.detections?.length">
      <template #header>检测结果 ({{ exam.detections.length }}项异常)</template>
      <el-table :data="exam.detections" stripe>
        <el-table-column prop="class_name_cn" label="异常类型" />
        <el-table-column prop="class_name" label="英文名" />
        <el-table-column prop="confidence" label="置信度">
          <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card style="margin-top: 20px" v-if="exam.ai_report">
      <template #header>AI 诊断报告</template>
      <div class="ai-report">
        <h4>诊断分析</h4>
        <p>{{ exam.ai_report.diagnosis || '无' }}</p>
        <h4>临床建议</h4>
        <p>{{ exam.ai_report.recommendations || '无' }}</p>
        <h4>患者说明</h4>
        <p>{{ exam.ai_report.patient_friendly || '无' }}</p>
      </div>
    </el-card>

    <div class="action-buttons" v-if="exam.is_temporary && exam.status === 'completed'">
      <el-button type="danger" @click="handleDiscard">丢弃</el-button>
      <el-button type="success" @click="handleConfirm">确认保存</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { examApi } from '../services/api'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const exam = ref({})

const fetchExam = async () => {
  loading.value = true
  try {
    const { data } = await examApi.get(route.params.id)
    exam.value = data
  } catch (error) {
    ElMessage.error('获取检查详情失败')
  } finally {
    loading.value = false
  }
}

const handleConfirm = async () => {
  try {
    await examApi.confirm(route.params.id)
    ElMessage.success('已保存')
    fetchExam()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const handleDiscard = async () => {
  try {
    await ElMessageBox.confirm('确定丢弃此次检查结果？', '提示', { type: 'warning' })
    await examApi.discard(route.params.id)
    ElMessage.success('已丢弃')
    router.push('/examinations')
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('操作失败')
  }
}

const getImageUrl = (path) => `file://${path}`

const formatDate = (d) => d ? new Date(d).toLocaleString('zh-CN') : '-'
const getStatusType = (s) => ({ pending: 'info', analyzing: 'warning', completed: 'success', failed: 'danger' }[s] || 'info')
const getStatusText = (s) => ({ pending: '待分析', analyzing: '分析中', completed: '已完成', failed: '失败' }[s] || s)

const getSymptomText = (arr) => {
  const map = { cough: '咳嗽', dyspnea: '呼吸困难', chest_pain: '胸痛', sputum: '咳痰', asymptomatic: '无症状' }
  return arr?.map(v => map[v]).join('、') || '-'
}
const getDurationText = (v) => ({ '<1week': '<1周', '1-4weeks': '1-4周', '>4weeks': '>4周' }[v] || '-')
const getDiseaseText = (arr) => {
  const map = { copd: 'COPD', asthma: '哮喘', tb: '肺结核', bronchiectasis: '支气管扩张', none: '无' }
  return arr?.map(v => map[v]).join('、') || '-'
}
const getSmokingText = (v) => ({ never: '从不吸烟', quit: '已戒烟', smoking: '目前吸烟' }[v] || '-')
const getExposureText = (arr) => {
  const map = { dust: '粉尘', chemical: '化学物质', radiation: '放射线', none: '无' }
  return arr?.map(v => map[v]).join('、') || '-'
}
const getXrayText = (v) => ({ '<6months': '<6个月', '6-12months': '6-12个月', '>1year': '>1年', never: '从未做过' }[v] || '-')
const getPurposeText = (v) => ({ routine: '常规体检', clinic: '不适就诊', followup: '随访复查', other: '其他' }[v] || '-')

onMounted(fetchExam)
</script>

<style scoped>
.image-compare {
  display: flex;
  gap: 20px;
}
.image-box {
  flex: 1;
  text-align: center;
}
.ai-report h4 {
  margin: 15px 0 5px;
  color: #333;
}
.ai-report p {
  margin: 0;
  line-height: 1.6;
}
.action-buttons {
  margin-top: 30px;
  text-align: center;
  display: flex;
  gap: 20px;
  justify-content: center;
}
</style>
