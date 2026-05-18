<template>
  <div class="statistics" v-loading="loading">
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.total_patients }}</div>
            <div class="stat-label">总患者数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.total_examinations }}</div>
            <div class="stat-label">总检查数</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.monthly_examinations }}</div>
            <div class="stat-label">本月检查</div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card>
          <div class="stat-card">
            <div class="stat-value">{{ stats.anomaly_rate }}%</div>
            <div class="stat-label">异常检出率</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card style="margin-top: 20px">
      <template #header>说明</template>
      <el-descriptions :column="2" border>
        <el-descriptions-item label="总患者数">系统中所有患者档案的数量</el-descriptions-item>
        <el-descriptions-item label="总检查数">所有检查记录的总数</el-descriptions-item>
        <el-descriptions-item label="本月检查">当月完成的检查数量</el-descriptions-item>
        <el-descriptions-item label="异常检出率">检出至少一项异常的检查占比</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { statsApi } from '../services/api'

const loading = ref(false)
const stats = ref({
  total_patients: 0,
  total_examinations: 0,
  monthly_examinations: 0,
  anomaly_rate: 0
})

const fetchStats = async () => {
  loading.value = true
  try {
    const { data } = await statsApi.get()
    stats.value = data
  } catch (error) {
    ElMessage.error('获取统计数据失败')
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<style scoped>
.stat-card {
  text-align: center;
  padding: 20px;
}
.stat-value {
  font-size: 36px;
  font-weight: bold;
  color: #1a73e8;
}
.stat-label {
  font-size: 14px;
  color: #666;
  margin-top: 10px;
}
</style>
