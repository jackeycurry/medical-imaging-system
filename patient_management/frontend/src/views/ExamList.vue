<template>
  <div class="exam-list">
    <div class="toolbar">
      <div class="filters">
        <el-select v-model="filters.patient_id" placeholder="选择患者" clearable filterable style="width: 200px">
          <el-option v-for="p in patients" :key="p.id" :label="p.name" :value="p.id" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" />
        <el-select v-model="filters.status" placeholder="状态" clearable style="width: 120px">
          <el-option value="pending" label="待分析" />
          <el-option value="analyzing" label="分析中" />
          <el-option value="completed" label="已完成" />
          <el-option value="failed" label="失败" />
        </el-select>
      </div>
      <el-button type="primary" @click="$router.push('/examinations/new')">新建检查</el-button>
    </div>

    <el-table :data="examinations" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="patient_name" label="患者姓名" />
      <el-table-column prop="exam_date" label="检查日期" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="detection_summary" label="AI结论" />
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150">
        <template #default="{ row }">
          <el-button link type="primary" @click="$router.push(`/examinations/${row.id}`)">详情</el-button>
          <el-button link type="danger" @click="deleteExam(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @current-change="fetchExaminations"
      layout="total, prev, pager, next"
      style="margin-top: 20px; justify-content: center"
    />
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { examApi, patientApi } from '../services/api'

const examinations = ref([])
const patients = ref([])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const dateRange = ref([])

const filters = reactive({
  patient_id: null,
  status: null
})

const fetchExaminations = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (filters.patient_id) params.patient_id = filters.patient_id
    if (filters.status) params.status = filters.status
    if (dateRange.value?.length === 2) {
      params.start_date = dateRange.value[0]
      params.end_date = dateRange.value[1]
    }
    const { data } = await examApi.list(params)
    examinations.value = data.examinations
    total.value = data.total
  } catch (error) {
    ElMessage.error('获取检查列表失败')
  } finally {
    loading.value = false
  }
}

const fetchPatients = async () => {
  try {
    const { data } = await patientApi.list({ page: 1, page_size: 1000 })
    patients.value = data.patients
  } catch (error) {
    console.error('获取患者列表失败', error)
  }
}

const deleteExam = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除该检查记录？`, '提示', { type: 'warning' })
    await examApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchExaminations()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const formatDate = (dateStr) => new Date(dateStr).toLocaleDateString('zh-CN')
const getStatusType = (status) => ({ pending: 'info', analyzing: 'warning', completed: 'success', failed: 'danger' }[status] || 'info')
const getStatusText = (status) => ({ pending: '待分析', analyzing: '分析中', completed: '已完成', failed: '失败' }[status] || status)

onMounted(() => {
  fetchExaminations()
  fetchPatients()
})
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}
.filters {
  display: flex;
  gap: 10px;
}
</style>
