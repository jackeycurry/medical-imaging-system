<template>
  <div class="layout-container">
    <aside class="sidebar">
      <div class="logo">肺部检测管理系统</div>
      <nav class="nav-menu">
        <router-link to="/patients" class="nav-item">
          <span class="nav-icon">👤</span>
          <span>患者管理</span>
        </router-link>
        <router-link to="/examinations" class="nav-item">
          <span class="nav-icon">📋</span>
          <span>检查记录</span>
        </router-link>
        <router-link to="/statistics" class="nav-item">
          <span class="nav-icon">📊</span>
          <span>数据统计</span>
        </router-link>
      </nav>
    </aside>
    <main class="main-content">
      <header class="content-header">
        <h1>{{ pageTitle }}</h1>
      </header>
      <div class="content-body">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const pageTitle = computed(() => {
  const titles = {
    '/patients': '患者管理',
    '/examinations': '检查记录',
    '/statistics': '数据统计',
    '/examinations/new': '新建检查'
  }
  return titles[route.path] || '患者管理系统'
})
</script>

<style scoped>
.layout-container {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  width: 200px;
  background: #1a1a2e;
  color: white;
  display: flex;
  flex-direction: column;
}
.logo {
  padding: 20px;
  font-size: 16px;
  font-weight: bold;
  border-bottom: 1px solid #333;
}
.nav-menu {
  flex: 1;
  padding: 10px 0;
}
.nav-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  color: #aaa;
  text-decoration: none;
  transition: all 0.3s;
}
.nav-item:hover, .nav-item.router-link-active {
  background: #16213e;
  color: white;
}
.nav-icon {
  margin-right: 10px;
}
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #f5f7fa;
}
.content-header {
  padding: 20px 30px;
  background: white;
  border-bottom: 1px solid #e0e0e0;
}
.content-header h1 {
  margin: 0;
  font-size: 24px;
  color: #333;
}
.content-body {
  flex: 1;
  padding: 30px;
  overflow-y: auto;
}
</style>
