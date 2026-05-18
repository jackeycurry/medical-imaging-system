<template>
  <div class="patients">
    <div class="header">
      <h2>患者管理</h2>
      <button @click="showAddModal" class="btn-add">新增患者</button>
    </div>

    <div class="search-bar">
      <input v-model="searchName" placeholder="搜索患者姓名" @input="search" />
    </div>

    <table>
      <thead>
        <tr>
          <th>ID</th><th>姓名</th><th>性别</th><th>年龄</th><th>电话</th><th>建档时间</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in patients" :key="p.id">
          <td>{{ p.id }}</td>
          <td>{{ p.name }}</td>
          <td>{{ p.gender }}</td>
          <td>{{ p.age }}</td>
          <td>{{ p.phone }}</td>
          <td>{{ formatTime(p.createTime) }}</td>
          <td>
            <button @click="editPatient(p)" class="btn-edit">编辑</button>
            <button @click="deletePatient(p.id)" class="btn-del">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="showAddLocal || editing" class="modal">
      <div class="modal-content">
        <h3>{{ editing ? '编辑患者' : '新增患者' }}</h3>
        <form @submit.prevent="savePatient">
          <input v-model="form.name" placeholder="姓名 *" required />
          <select v-model="form.gender">
            <option value="">选择性别</option>
            <option value="男">男</option>
            <option value="女">女</option>
          </select>
          <input v-model.number="form.age" type="number" placeholder="年龄" />
          <div class="phone-group">
            <input v-model="form.phone" placeholder="电话 (11位数字)" maxlength="11" @input="validatePhone" />
            <p v-if="phoneError" class="phone-error">{{ phoneError }}</p>
          </div>
          <div class="btns">
            <button type="submit" :disabled="!!phoneError || !form.name">{{ editing ? '保存' : '添加' }}</button>
            <button type="button" @click="closeModal">取消</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const patients = ref([])
const searchName = ref('')
const showAddLocal = ref(false)
const editing = ref(null)
const phoneError = ref('')
const form = ref({ name: '', gender: '', age: '', phone: '' })

onMounted(() => fetchPatients())

const showAddModal = () => {
  editing.value = null
  form.value = { name: '', gender: '', age: '', phone: '' }
  showAddLocal.value = true
}

const formatTime = (time) => {
  if (!time) return '-'
  const d = new Date(time)
  const offset = 8 * 60 * 60 * 1000
  const bjTime = new Date(d.getTime() + offset)
  return bjTime.toLocaleString('zh-CN', { hour12: false }).replace(/\//g, '-')
}

const fetchPatients = () => api.getPatients().then(res => { if (res.data) patients.value = res.data })

const search = () => api.getPatients(searchName.value || undefined).then(res => { if (res.data) patients.value = res.data })

const validatePhone = () => {
  const p = form.value.phone
  if (p && !/^\d+$/.test(p)) {
    phoneError.value = '只能输入数字'
  } else if (p && p.length !== 11) {
    phoneError.value = '必须是11位数字'
  } else {
    phoneError.value = ''
  }
}

const editPatient = (p) => {
  editing.value = p
  form.value = { name: p.name, gender: p.gender, age: p.age, phone: p.phone }
  showAddLocal.value = true
}

const savePatient = async () => {
  if (phoneError.value) return
  const data = { ...form.value }
  if (editing.value) {
    await api.updatePatient(editing.value.id, data)
  } else {
    await api.createPatient(data)
  }
  closeModal()
  fetchPatients()
}

const deletePatient = async (id) => { if (confirm('确认删除？')) await api.deletePatient(id) && fetchPatients() }

const closeModal = () => {
  showAddLocal.value = false
  editing.value = null
  form.value = { name: '', gender: '', age: '', phone: '' }
  phoneError.value = ''
}
</script>

<style scoped>
/* 阿里云风格 */
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding: 20px 24px;
  background: #fff;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.header h2 { margin: 0; font-size: 18px; font-weight: 600; color: #1f1f1f; }
.header .btn-add {
  background: #1677FF;
  color: #fff;
  border: none;
  padding: 10px 20px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}
.header .btn-add:hover { background: #4096FF; }

.search-bar { margin-bottom: 16px; }
.search-bar input {
  padding: 10px 12px;
  width: 300px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.search-bar input:focus {
  outline: none;
  border-color: #1677FF;
  box-shadow: 0 0 0 2px rgba(22,119,255,0.1);
}

table {
  width: 100%;
  background: #fff;
  border-collapse: collapse;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #e8e8e8;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
th, td { padding: 14px 16px; text-align: left; border-bottom: 1px solid #e8e8e8; }
th {
  background: #FAFAFA;
  color: #1f1f1f;
  font-weight: 600;
  font-size: 14px;
}
tr:hover { background: #F5F7FA; }
tr:last-child td { border-bottom: none; }

.btn-edit, .btn-del {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 8px;
  font-size: 13px;
  transition: all 0.2s;
}
.btn-edit {
  background: #fff;
  color: #1677FF;
  border: 1px solid #1677FF;
}
.btn-edit:hover { background: #E6F4FF; }
.btn-del {
  background: #fff;
  color: #FF4D4F;
  border: 1px solid #FF4D4F;
}
.btn-del:hover { background: #FFF1F0; }

.modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0,0,0,0.45);
  display: flex;
  justify-content: center;
  align-items: center;
  backdrop-filter: blur(2px);
}
.modal-content {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  width: 400px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 6px 16px rgba(0,0,0,0.15);
}
.modal-content h3 {
  margin: 0 0 20px;
  font-size: 16px;
  font-weight: 600;
  color: #1f1f1f;
}
.modal-content form input,
.modal-content form select {
  width: 100%;
  padding: 10px 12px;
  margin-bottom: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}
.modal-content form input:focus,
.modal-content form select:focus {
  outline: none;
  border-color: #1677FF;
}
.phone-group { position: relative; }
.phone-error { color: #FF4D4F; font-size: 12px; margin: -8px 0 12px 0; }
.btns { display: flex; gap: 12px; margin-top: 20px; }
.btns button { flex: 1; padding: 10px; border: none; border-radius: 6px; cursor: pointer; font-size: 14px; font-weight: 500; transition: all 0.2s; }
.btns button:first-child { background: #1677FF; color: #fff; }
.btns button:first-child:hover { background: #4096FF; }
.btns button:first-child:disabled { background: #D9D9D9; }
.btns button:last-child { background: #fff; color: #666; border: 1px solid #D9D9D9; }
.btns button:last-child:hover { color: #1677FF; border-color: #1677FF; }
</style>