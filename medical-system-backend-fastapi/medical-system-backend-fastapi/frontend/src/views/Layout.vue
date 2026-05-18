<template>
  <div class="layout">
    <aside class="sidebar">
      <h2>医疗档案系统</h2>
      <nav>
        <a @click="switchView('dashboard')" :class="{ active: currentView === 'dashboard' }">
          <svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"/>
            <polyline points="9,22 9,12 15,12 15,22"/>
          </svg>
          数据中心
        </a>
        <div class="nav-dropdown">
          <a @click="toggleDropdown" :class="{ active: showDropdown || currentDetection }">
            影片检测
            <span class="arrow">{{ showDropdown ? '▲' : '▼' }}</span>
          </a>
          <div v-if="showDropdown" class="dropdown-menu">
            <a @click="openDetection('chest')" :class="{ active: currentDetection === 'chest' }">胸片检测</a>
            <a @click="openDetection('brain')" :class="{ active: currentDetection === 'brain' }">脑部检测</a>
            <a @click="openDetection('retina')" :class="{ active: currentDetection === 'retina' }">视网膜检测</a>
            <a @click="openDetection('abdomen')" :class="{ active: currentDetection === 'abdomen' }">腹部检测</a>
            <a @click="openDetection('spine')" :class="{ active: currentDetection === 'spine' }">脊柱检测</a>
            <a @click="openDetection('breast')" :class="{ active: currentDetection === 'breast' }">乳腺检测</a>
            <a @click="openDetection('cardiovascular')" :class="{ active: currentDetection === 'cardiovascular' }">心血管检测</a>
            <a @click="openDetection('other')" :class="{ active: currentDetection === 'other' }">其他检测</a>
          </div>
        </div>
        <a @click="switchView('patients')" :class="{ active: currentView === 'patients' }">患者管理</a>
        <a @click="switchView('images')" :class="{ active: currentView === 'images' }">影像管理</a>
      </nav>
      <div class="user-info">
        <span>{{ username }}</span>
        <button @click="logout">退出</button>
      </div>
    </aside>
    <main class="content">
      <Dashboard v-if="currentView === 'dashboard'" />
      <DetectionAnalysis v-else-if="currentDetection" :detection-type="currentDetection" />
      <Patients v-else-if="currentView === 'patients'" />
      <Images v-else-if="currentView === 'images'" />
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import Patients from './Patients.vue'
import Images from './Images.vue'
import DetectionAnalysis from './DetectionAnalysis.vue'
import Dashboard from './Dashboard.vue'

const router = useRouter()
const currentView = ref('dashboard')
const currentDetection = ref(null)
const showDropdown = ref(false)
const username = ref('')

onMounted(() => {
  username.value = localStorage.getItem('username') || ''
})

const toggleDropdown = () => {
  showDropdown.value = !showDropdown.value
}

const openDetection = (type) => {
  showDropdown.value = false
  currentDetection.value = type
  currentView.value = null
}

const switchView = (view) => {
  showDropdown.value = false
  currentDetection.value = null
  currentView.value = view
}

const logout = () => {
  localStorage.clear()
  router.push('/login')
}
</script>

<style scoped>
.layout { display: flex; height: 100vh; }

/* 阿里云风格侧边栏 */
.sidebar {
  width: 220px;
  background: #fff;
  color: #1f1f1f;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #e8e8e8;
  box-shadow: 2px 0 8px rgba(0,0,0,0.04);
}

.sidebar h2 {
  padding: 20px;
  text-align: center;
  border-bottom: 1px solid #e8e8e8;
  font-size: 16px;
  font-weight: 600;
  color: #1677FF;
}

.sidebar nav { flex: 1; }
.sidebar nav a {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 20px;
  cursor: pointer;
  transition: all 0.2s;
  color: #1f1f1f;
  font-size: 14px;
  border-left: 3px solid transparent;
}

.nav-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.sidebar nav a:hover {
  background: #F5F7FA;
  color: #1677FF;
}
.sidebar nav a.active {
  background: #E6F4FF;
  color: #1677FF;
  border-left-color: #1677FF;
  font-weight: 500;
}

.nav-dropdown { position: relative; }
.nav-dropdown > a {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.arrow { font-size: 10px; color: #999; }

.dropdown-menu {
  background: #FAFAFA;
  border-bottom: 1px solid #e8e8e8;
}
.dropdown-menu a {
  padding-left: 35px;
  font-size: 13px;
  color: #666;
}
.dropdown-menu a:hover {
  background: #E6F4FF;
  color: #1677FF;
}

.user-info {
  padding: 15px 20px;
  border-top: 1px solid #e8e8e8;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #666;
}
.user-info button {
  background: #fff;
  color: #666;
  border: 1px solid #d9d9d9;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.user-info button:hover {
  color: #1677FF;
  border-color: #1677FF;
}

.content {
  flex: 1;
  background: #F5F7FA;
  overflow-y: auto;
  padding: 0;
}

.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #999;
  font-size: 14px;
}
.welcome h2 {
  color: #1f1f1f;
  margin-bottom: 10px;
  font-weight: 500;
}
</style>
