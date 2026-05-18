<template>
  <div class="patient-list">
    <div class="toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索姓名或电话..."
        style="width: 300px"
        @change="fetchPatients"
      />
      <el-button type="primary" @click="showAddDialog">新建患者</el-button>
    </div>

    <el-table :data="patients" v-loading="loading" stripe>
      <el-table-column prop="id" label="ID" width="80" />
      <el-table-column prop="name" label="姓名" />
      <el-table-column prop="age" label="年龄" width="80" />
      <el-table-column prop="gender" label="性别" width="80">
        <template #default="{ row }">
          {{ row.gender === 'male' ? '男' : '女' }}
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="电话" />
      <el-table-column prop="examination_count" label="检查次数" width="100" />
      <el-table-column prop="created_at" label="创建时间">
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="200">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewDetail(row)">详情</el-button>
          <el-button link type="primary" @click="editPatient(row)">编辑</el-button>
          <el-button link type="danger" @click="deletePatient(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-model:current-page="currentPage"
      :page-size="pageSize"
      :total="total"
      @current-change="fetchPatients"
      layout="total, prev, pager, next"
      style="margin-top: 20px; justify-content: center"
    />

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="500px">
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
        <el-button type="primary" @click="submitForm">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { patientApi } from '../services/api'

const router = useRouter()
const patients = ref([])
const loading = ref(false)
const searchQuery = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)

const dialogVisible = ref(false)
const dialogTitle = ref('新建患者')
const editingId = ref(null)
const patientForm = reactive({
  name: '',
  age: 30,
  gender: 'male',
  phone: ''
})

const fetchPatients = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, page_size: pageSize.value }
    if (searchQuery.value) params.search = searchQuery.value
    const { data } = await patientApi.list(params)
    patients.value = data.patients
    total.value = data.total
  } catch (error) {
    ElMessage.error('获取患者列表失败')
  } finally {
    loading.value = false
  }
}

const showAddDialog = () => {
  dialogTitle.value = '新建患者'
  editingId.value = null
  Object.assign(patientForm, { name: '', age: 30, gender: 'male', phone: '' })
  dialogVisible.value = true
}

const editPatient = (row) => {
  dialogTitle.value = '编辑患者'
  editingId.value = row.id
  Object.assign(patientForm, { name: row.name, age: row.age, gender: row.gender, phone: row.phone })
  dialogVisible.value = true
}

const submitForm = async () => {
  try {
    if (editingId.value) {
      await patientApi.update(editingId.value, patientForm)
      ElMessage.success('更新成功')
    } else {
      await patientApi.create(patientForm)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    fetchPatients()
  } catch (error) {
    ElMessage.error(editingId.value ? '更新失败' : '创建失败')
  }
}

const viewDetail = (row) => router.push(`/patients/${row.id}`)

const deletePatient = async (row) => {
  try {
    await ElMessageBox.confirm(`确定删除患者"${row.name}"？`, '提示', { type: 'warning' })
    await patientApi.delete(row.id)
    ElMessage.success('删除成功')
    fetchPatients()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

const formatDate = (dateStr) => new Date(dateStr).toLocaleDateString('zh-CN')

onMounted(fetchPatients)
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  margin-bottom: 20px;
}
</style>
