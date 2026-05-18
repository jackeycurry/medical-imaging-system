<template>
  <div class="patient-detail" v-loading="loading">
    <el-button @click="$router.back()">返回</el-button>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>患者信息</span>
        <el-button type="primary" size="small" @click="showEditDialog">编辑</el-button>
      </template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="姓名">{{ patient.name }}</el-descriptions-item>
        <el-descriptions-item label="年龄">{{ patient.age }}岁</el-descriptions-item>
        <el-descriptions-item label="性别">{{ patient.gender === 'male' ? '男' : '女' }}</el-descriptions-item>
        <el-descriptions-item label="电话">{{ patient.phone || '-' }}</el-descriptions-item>
        <el-descriptions-item label="创建时间">{{ formatDate(patient.created_at) }}</el-descriptions-item>
        <el-descriptions-item label="更新时间">{{ formatDate(patient.updated_at) }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card style="margin-top: 20px">
      <template #header>
        <span>检查记录 ({{ patient.examinations?.length || 0 }})</span>
        <el-button type="primary" size="small" @click="$router.push('/examinations/new')">新建检查</el-button>
      </template>
      <el-table :data="patient.examinations" stripe>
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="exam_date" label="检查日期" />
        <el-table-column prop="status" label="状态">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作">
          <template #default="{ row }">
            <el-button link type="primary" @click="$router.push(`/examinations/${row.id}`)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑患者" width="500px">
      <el-form :model="patientForm" label-width="80px">
        <el-form-item label="姓名" required>
          <el-input v-model="patientForm.name" />
        </el-form-item>
        <el-form-item label="年龄" required>
          <el-input-number v-model="patientForm.age" :min="0" :max="150" />
        </el-form-item>
        <el-form-item label="性别" required>
          <el-radio-group v-model="patientForm.gender">
            <el-radio value="male">男</el-radio>
            <el-radio value="female">女</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="patientForm.phone" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { patientApi } from '../services/api'

const route = useRoute()
const loading = ref(false)
const patient = ref({})
const dialogVisible = ref(false)
const patientForm = reactive({ name: '', age: 30, gender: 'male', phone: '' })

const fetchPatient = async () => {
  loading.value = true
  try {
    const { data } = await patientApi.get(route.params.id)
    patient.value = data
  } catch (error) {
    ElMessage.error('获取患者信息失败')
  } finally {
    loading.value = false
  }
}

const showEditDialog = () => {
  Object.assign(patientForm, {
    name: patient.value.name,
    age: patient.value.age,
    gender: patient.value.gender,
    phone: patient.value.phone
  })
  dialogVisible.value = true
}

const submitEdit = async () => {
  try {
    await patientApi.update(route.params.id, patientForm)
    ElMessage.success('更新成功')
    dialogVisible.value = false
    fetchPatient()
  } catch (error) {
    ElMessage.error('更新失败')
  }
}

const formatDate = (dateStr) => dateStr ? new Date(dateStr).toLocaleDateString('zh-CN') : '-'
const getStatusType = (status) => ({ pending: 'info', analyzing: 'warning', completed: 'success', failed: 'danger' }[status] || 'info')
const getStatusText = (status) => ({ pending: '待分析', analyzing: '分析中', completed: '已完成', failed: '失败' }[status] || status)

onMounted(fetchPatient)
</script>
