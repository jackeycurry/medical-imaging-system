<template>
  <div class="new-exam">
    <el-button @click="$router.back()">返回</el-button>

    <el-card style="margin-top: 20px">
      <template #header>选择患者</template>
      <el-select v-model="examForm.patient_id" placeholder="请选择患者" filterable style="width: 100%">
        <el-option v-for="p in patients" :key="p.id" :label="`${p.name} (${p.age}岁${p.gender === 'male' ? '男' : '女'})`" :value="p.id" />
      </el-select>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>肺部问卷</template>
      <el-form :model="questionnaire" label-width="140px">
        <el-form-item label="主要症状" required>
          <el-checkbox-group v-model="questionnaire.main_symptoms">
            <el-checkbox value="cough">咳嗽</el-checkbox>
            <el-checkbox value="dyspnea">呼吸困难</el-checkbox>
            <el-checkbox value="chest_pain">胸痛</el-checkbox>
            <el-checkbox value="sputum">咳痰</el-checkbox>
            <el-checkbox value="asymptomatic">无症状</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="症状持续时间">
          <el-select v-model="questionnaire.symptom_duration" placeholder="请选择">
            <el-option value="<1week" label="小于1周" />
            <el-option value="1-4weeks" label="1-4周" />
            <el-option value=">4weeks" label="大于4周" />
          </el-select>
        </el-form-item>
        <el-form-item label="既往肺部疾病">
          <el-checkbox-group v-model="questionnaire.past_lung_disease">
            <el-checkbox value="copd">COPD</el-checkbox>
            <el-checkbox value="asthma">哮喘</el-checkbox>
            <el-checkbox value="tb">肺结核</el-checkbox>
            <el-checkbox value="bronchiectasis">支气管扩张</el-checkbox>
            <el-checkbox value="none">无</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="吸烟史">
          <el-select v-model="questionnaire.smoking_history" placeholder="请选择">
            <el-option value="never" label="从不吸烟" />
            <el-option value="quit" label="已戒烟" />
            <el-option value="smoking" label="目前吸烟" />
          </el-select>
        </el-form-item>
        <el-form-item label="职业暴露">
          <el-checkbox-group v-model="questionnaire.occupational_exposure">
            <el-checkbox value="dust">粉尘</el-checkbox>
            <el-checkbox value="chemical">化学物质</el-checkbox>
            <el-checkbox value="radiation">放射线</el-checkbox>
            <el-checkbox value="none">无</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="家族肺部疾病史">
          <el-radio-group v-model="questionnaire.family_lung_history">
            <el-radio :value="true">有</el-radio>
            <el-radio :value="false">无</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="最近X光检查时间">
          <el-select v-model="questionnaire.last_xray_time" placeholder="请选择">
            <el-option value="<6months" label="小于6个月" />
            <el-option value="6-12months" label="6-12个月" />
            <el-option value=">1year" label="大于1年" />
            <el-option value="never" label="从未做过" />
          </el-select>
        </el-form-item>
        <el-form-item label="检查目的">
          <el-select v-model="questionnaire.exam_purpose" placeholder="请选择">
            <el-option value="routine" label="常规体检" />
            <el-option value="clinic" label="不适就诊" />
            <el-option value="followup" label="随访复查" />
            <el-option value="other" label="其他" />
          </el-select>
        </el-form-item>
        <el-form-item label="其他备注">
          <el-input v-model="questionnaire.notes" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>上传胸部X光图像</template>
      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        accept="image/*"
        :on-change="handleFileChange"
      >
        <el-icon><upload-filled /></el-icon>
        <div>将图像拖到此处，或<em>点击上传</em></div>
      </el-upload>
    </el-card>

    <div style="margin-top: 20px; text-align: center">
      <el-button @click="$router.back()">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">提交并分析</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { examApi, patientApi } from '../services/api'
import { UploadFilled } from '@element-plus/icons-vue'

const router = useRouter()
const patients = ref([])
const submitting = ref(false)
const selectedFile = ref(null)

const examForm = reactive({
  patient_id: null,
  exam_date: new Date().toISOString().split('T')[0]
})

const questionnaire = reactive({
  main_symptoms: [],
  symptom_duration: null,
  past_lung_disease: [],
  smoking_history: null,
  occupational_exposure: [],
  family_lung_history: null,
  last_xray_time: null,
  exam_purpose: null,
  notes: ''
})

const fetchPatients = async () => {
  try {
    const { data } = await patientApi.list({ page: 1, page_size: 1000 })
    patients.value = data.patients
  } catch (error) {
    console.error('获取患者列表失败', error)
  }
}

const handleFileChange = (file) => {
  selectedFile.value = file.raw
}

const handleSubmit = async () => {
  if (!examForm.patient_id) {
    ElMessage.warning('请选择患者')
    return
  }
  if (!selectedFile.value) {
    ElMessage.warning('请上传图像')
    return
  }

  submitting.value = true
  try {
    const { data: exam } = await examApi.create({
      patient_id: examForm.patient_id,
      exam_date: examForm.exam_date,
      referring_doctor: '',
      questionnaire: { ...questionnaire }
    })

    await examApi.upload(exam.id, selectedFile.value)
    await examApi.analyze(exam.id)

    ElMessage.success('分析完成')
    router.push(`/examinations/${exam.id}`)
  } catch (error) {
    ElMessage.error('提交失败: ' + (error.message || '未知错误'))
  } finally {
    submitting.value = false
  }
}

onMounted(fetchPatients)
</script>