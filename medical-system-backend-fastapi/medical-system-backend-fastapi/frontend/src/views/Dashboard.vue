<template>
  <div class="dashboard">
    <!-- 页面标题区 -->
    <div class="page-title">
      <div class="title-left">
        <h1>数据概览</h1>
        <p class="subtitle">{{ currentDate }}</p>
      </div>
      <div class="title-right">
        <span class="update-time">数据更新时间: {{ updateTime }}</span>
      </div>
    </div>

    <!-- 核心指标 -->
    <div class="metrics-grid">
      <div class="metric-card" v-for="(metric, idx) in metrics" :key="idx" :style="{ '--accent': metric.color }">
        <div class="metric-glow"></div>
        <div class="metric-header">
          <span class="metric-label">{{ metric.label }}</span>
          <div class="metric-icon" :style="{ background: metric.bgColor }">
            <svg class="icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <template v-if="metric.icon === 'list'">
                <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/>
                <rect x="9" y="3" width="6" height="4" rx="1"/>
                <line x1="9" y1="12" x2="15" y2="12"/>
                <line x1="9" y1="16" x2="13" y2="16"/>
              </template>
              <template v-else-if="metric.icon === 'scan'">
                <circle cx="12" cy="12" r="9"/>
                <path d="M12 3v9l6 3"/>
              </template>
              <template v-else-if="metric.icon === 'alert'">
                <path d="M12 2L2 22h20L12 2z"/>
                <line x1="12" y1="9" x2="12" y2="13"/>
                <circle cx="12" cy="17" r="1" fill="currentColor"/>
              </template>
              <template v-else-if="metric.icon === 'check'">
                <circle cx="12" cy="12" r="9"/>
                <path d="M9 12l2 2 4-4"/>
              </template>
            </svg>
          </div>
        </div>
        <div class="metric-body">
          <span class="metric-value" :style="{ color: metric.color }">{{ metric.value }}</span>
          <span class="metric-unit">{{ metric.unit }}</span>
        </div>
        <div class="metric-sparkline">
          <svg viewBox="0 0 100 30" preserveAspectRatio="none">
            <path :d="metric.sparkline" fill="none" :stroke="metric.color" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="metric-footer">
          <span class="metric-change" :class="metric.changeType">{{ metric.change }}</span>
          <span class="metric-period">较上周</span>
        </div>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="content-grid">
      <!-- 左侧柱状图 -->
      <div class="chart-panel">
        <div class="panel-header">
          <h3>本周就诊量趋势</h3>
          <div class="chart-legend">
            <span class="legend-item"><i class="dot"></i>日均 {{ avgDaily }} 例</span>
          </div>
        </div>
        <div class="chart-body">
          <div class="bar-chart-v3">
            <div class="bar-item" v-for="(day, idx) in weeklyData" :key="idx">
              <div class="bar-tooltip">{{ day.value }}例</div>
              <div class="bar-track">
                <div class="bar-fill" :style="{ height: day.percent + '%', '--delay': idx * 0.1 + 's' }">
                  <div class="bar-shine"></div>
                </div>
              </div>
              <span class="bar-label">{{ day.day }}</span>
            </div>
          </div>
          <div class="chart-stats">
            <div class="stat-item">
              <span class="stat-value">{{ maxDay.value }}</span>
              <span class="stat-label">最高 {{ maxDay.day }}</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-value">{{ minDay.value }}</span>
              <span class="stat-label">最低 {{ minDay.day }}</span>
            </div>
            <div class="stat-divider"></div>
            <div class="stat-item">
              <span class="stat-value">{{ totalWeekly }}</span>
              <span class="stat-label">本周总量</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧环形图 -->
      <div class="chart-panel">
        <div class="panel-header">
          <h3>检测类型分布</h3>
        </div>
        <div class="chart-body donut-body">
          <div class="donut-container">
            <svg class="donut-svg" viewBox="0 0 200 200">
              <defs>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="2" result="coloredBlur"/>
                  <feMerge>
                    <feMergeNode in="coloredBlur"/>
                    <feMergeNode in="SourceGraphic"/>
                  </feMerge>
                </filter>
              </defs>
              <circle class="donut-bg" cx="100" cy="100" r="70"/>
              <circle
                v-for="(segment, idx) in donutData"
                :key="idx"
                class="donut-segment"
                cx="100"
                cy="100"
                r="70"
                :stroke="segment.color"
                :stroke-dasharray="segment.dash"
                :stroke-dashoffset="segment.offset"
                :style="{ '--delay': idx * 0.15 + 's' }"
              />
              <circle class="donut-center-ring" cx="100" cy="100" r="55"/>
            </svg>
            <div class="donut-center">
              <span class="donut-total">{{ totalDetection }}</span>
              <span class="donut-label">总检测</span>
            </div>
          </div>
          <div class="donut-legend">
            <div class="legend-item" v-for="item in donutData" :key="item.label">
              <span class="legend-dot" :style="{ background: item.color }"></span>
              <span class="legend-text">{{ item.label }}</span>
              <span class="legend-value">{{ item.value }}</span>
              <span class="legend-percent">{{ item.percent }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 实时记录面板 -->
    <div class="record-section">
      <div class="record-panel">
        <div class="panel-header">
          <h3>实时记录</h3>
        </div>
        <div class="panel-body">
          <div class="record-tabs">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              :class="{ active: activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
            </button>
          </div>
          <div class="record-list">
            <template v-if="activeTab === 'registration'">
              <div class="record-item" v-for="(item, idx) in registrations" :key="idx" :style="{ '--delay': idx * 0.05 + 's' }">
                <div class="record-avatar" :style="{ background: item.avatarColor }">
                  {{ item.name[0] }}
                </div>
                <div class="record-content">
                  <span class="record-name">{{ item.name }}</span>
                  <span class="record-dept">{{ item.dept }}</span>
                </div>
                <span class="record-badge new">新</span>
                <span class="record-time">{{ item.time }}</span>
              </div>
            </template>
            <template v-else-if="activeTab === 'report'">
              <div class="record-item" v-for="(item, idx) in reports" :key="idx" :style="{ '--delay': idx * 0.05 + 's' }">
                <div class="record-icon document-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                    <polyline points="14,2 14,8 20,8"/>
                    <line x1="16" y1="13" x2="8" y2="13"/>
                    <line x1="16" y1="17" x2="8" y2="17"/>
                  </svg>
                </div>
                <div class="record-content">
                  <span class="record-name">{{ item.patient }}</span>
                  <span class="record-dept">{{ item.type }}</span>
                </div>
                <span class="record-status" :class="item.status">{{ item.statusText }}</span>
              </div>
            </template>
            <template v-else>
              <div class="record-item alert" v-for="(item, idx) in alerts" :key="idx" :style="{ '--delay': idx * 0.05 + 's' }">
                <div class="record-icon" :class="item.level">
                  <svg viewBox="0 0 24 24" fill="currentColor">
                    <circle cx="12" cy="12" r="6"/>
                  </svg>
                </div>
                <div class="record-content">
                  <span class="record-name">{{ item.patient }}</span>
                  <span class="record-dept">{{ item.desc }}</span>
                </div>
                <span class="record-badge" :class="item.level">{{ item.levelText }}</span>
                <span class="record-time">{{ item.time }}</span>
              </div>
            </template>
          </div>
        </div>
      </div>

      <!-- 底部数据栏 -->
      <div class="ticker-panel">
        <div class="ticker-header">
          <span class="ticker-label">今日概览</span>
          <div class="ticker-stats">
            <div class="ticker-stat">
              <span class="ticker-stat-value">342</span>
              <span class="ticker-stat-label">总检查量</span>
            </div>
            <div class="ticker-stat">
              <span class="ticker-stat-value">28</span>
              <span class="ticker-stat-label">异常发现</span>
            </div>
            <div class="ticker-stat">
              <span class="ticker-stat-value">98.2%</span>
              <span class="ticker-stat-label">诊断准确率</span>
            </div>
          </div>
        </div>
        <div class="ticker-chart-wrapper">
          <div ref="tickerChartRef" class="ticker-chart"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'

const currentDate = computed(() => {
  const now = new Date()
  return now.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
})

const updateTime = computed(() => {
  const now = new Date()
  return now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
})

const avgDaily = computed(() => {
  const sum = weeklyData.value.reduce((acc, d) => acc + d.value, 0)
  return Math.round(sum / 7)
})

const totalWeekly = computed(() => {
  return weeklyData.value.reduce((acc, d) => acc + d.value, 0)
})

const maxDay = computed(() => {
  return weeklyData.value.reduce((a, b) => a.value > b.value ? a : b)
})

const minDay = computed(() => {
  return weeklyData.value.reduce((a, b) => a.value < b.value ? a : b)
})

const totalDetection = computed(() => {
  return donutData.value.reduce((acc, d) => acc + d.value, 0)
})

const metrics = ref([
  {
    label: '今日挂号',
    value: 128,
    unit: '人',
    icon: 'list',
    bgColor: '#E6F4FF',
    color: '#1677FF',
    change: '+12%',
    changeType: 'up',
    sparkline: 'M0,25 L15,20 L30,22 L45,15 L60,18 L75,10 L90,12 L100,5'
  },
  {
    label: '今日检查',
    value: 86,
    unit: '例',
    icon: 'scan',
    bgColor: '#F6FFED',
    color: '#52C41A',
    change: '+8%',
    changeType: 'up',
    sparkline: 'M0,20 L15,18 L30,15 L45,12 L60,14 L75,8 L90,10 L100,5'
  },
  {
    label: '异常预警',
    value: 5,
    unit: '例',
    icon: 'alert',
    bgColor: '#FFF7E6',
    color: '#FA8C16',
    change: '-5%',
    changeType: 'down',
    sparkline: 'M0,5 L15,8 L30,12 L45,10 L60,15 L75,18 L90,20 L100,25'
  },
  {
    label: '完成诊断',
    value: 72,
    unit: '份',
    icon: 'check',
    bgColor: '#F9F0FF',
    color: '#722ED1',
    change: '+15%',
    changeType: 'up',
    sparkline: 'M0,25 L15,22 L30,20 L45,18 L60,15 L75,12 L90,8 L100,5'
  }
])

const weeklyData = ref([
  { day: '周一', value: 45, percent: 60 },
  { day: '周二', value: 52, percent: 70 },
  { day: '周三', value: 38, percent: 50 },
  { day: '周四', value: 65, percent: 87 },
  { day: '周五', value: 58, percent: 77 },
  { day: '周六', value: 32, percent: 43 },
  { day: '周日', value: 28, percent: 37 }
])

const donutData = computed(() => {
  const data = [
    { label: '胸部X光', value: 156, color: '#1677FF' },
    { label: '胸部CT', value: 98, color: '#52C41A' },
    { label: 'MRI', value: 67, color: '#722ED1' },
    { label: 'PET-CT', value: 45, color: '#FA8C16' },
    { label: '腹部检测', value: 42, color: '#EB2F96' },
    { label: '脊柱检测', value: 38, color: '#13C2C2' },
    { label: '乳腺检测', value: 29, color: '#FADB14' },
    { label: '心血管检测', value: 35, color: '#2F54EB' }
  ]
  const total = data.reduce((acc, d) => acc + d.value, 0)
  const circumference = 2 * Math.PI * 70
  let offset = 0

  return data.map((d, i) => {
    const percent = Math.round(d.value / total * 100)
    const dash = (d.value / total * circumference) + ' ' + circumference
    const item = {
      ...d,
      percent,
      dash,
      offset: -offset
    }
    offset += d.value / total * circumference
    return item
  })
})

const tabs = [
  { key: 'registration', label: '挂号' },
  { key: 'report', label: '报告' },
  { key: 'alert', label: '预警' }
]

const activeTab = ref('registration')

const registrations = ref([
  { name: '张伟', dept: '呼吸内科', time: '08:30', avatarColor: '#1677FF' },
  { name: '李娜', dept: '心血管科', time: '08:45', avatarColor: '#52C41A' },
  { name: '王强', dept: '胸外科', time: '09:10', avatarColor: '#FA8C16' },
  { name: '刘芳', dept: '呼吸内科', time: '09:25', avatarColor: '#722ED1' },
  { name: '陈明', dept: '神经内科', time: '09:40', avatarColor: '#13C2C2' }
])

const reports = ref([
  { patient: '张伟', type: '胸部CT', status: 'done', statusText: '已完成' },
  { patient: '李娜', type: '胸部X光', status: 'pending', statusText: '处理中' },
  { patient: '王强', type: '胸部CT', status: 'done', statusText: '已完成' },
  { patient: '刘芳', type: 'PET-CT', status: 'pending', statusText: '处理中' }
])

const alerts = ref([
  { patient: '陈军', desc: '肺部阴影增大', level: 'high', levelText: '高危', time: '10:20' },
  { patient: '王丽', desc: '疑似肺结节需复查', level: 'medium', levelText: '中危', time: '09:45' }
])

const tickerItems = ref([
  { label: '胸部X光', value: '34例' },
  { label: 'CT检查', value: '28例' },
  { label: 'MRI检查', value: '15例' },
  { label: 'PET-CT', value: '8例' },
  { label: '超声检查', value: '52例' },
  { label: '心电图', value: '41例' },
  { label: '血常规', value: '96份' },
  { label: '尿常规', value: '38份' },
  { label: '生化检查', value: '67份' },
  { label: '凝血功能', value: '23份' },
  { label: '腹部检测', value: '45例' },
  { label: '脊柱检测', value: '32例' },
  { label: '乳腺检测', value: '19例' },
  { label: '心血管检测', value: '27例' }
])

const tickerChartRef = ref(null)
let tickerChart = null

const initTickerChart = () => {
  if (!tickerChartRef.value) return

  tickerChart = echarts.init(tickerChartRef.value)

  const categories = tickerItems.value.map(item => item.label)
  const values = tickerItems.value.map(item => parseInt(item.value))

  tickerChart.setOption({
    title: {
      text: '各检查项目数量统计',
      left: 'center',
      top: 8,
      textStyle: {
        fontSize: 15,
        fontWeight: 600,
        color: '#1f1f1f'
      }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: params => {
        const p = params[0]
        return `${p.name}<br/><strong>${p.value}</strong> 例/份`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '18%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: categories,
      axisLabel: {
        rotate: 30,
        fontSize: 12,
        color: '#666666'
      },
      axisLine: { lineStyle: { color: '#E8E8E8' } },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      name: '例数/份数',
      nameTextStyle: { color: '#999999', fontSize: 12 },
      axisLabel: { color: '#666666', fontSize: 12 },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: '#F0F0F0' } }
    },
    series: [{
      type: 'bar',
      data: values,
      barWidth: '50%',
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#3b82f6' },
          { offset: 1, color: '#93c5fd' }
        ]),
        borderRadius: [4, 4, 0, 0]
      },
      label: {
        show: true,
        position: 'top',
        fontSize: 12,
        fontWeight: 600,
        color: '#3b82f6'
      },
      animationDuration: 1000,
      animationEasing: 'cubicOut'
    }]
  })
}

const handleResize = () => {
  tickerChart?.resize()
}

onMounted(() => {
  nextTick(() => {
    initTickerChart()
  })
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  tickerChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  --primary: #1677FF;
  --success: #52C41A;
  --warning: #FA8C16;
  --danger: #FF4D4F;
  --purple: #722ED1;
  --text-primary: #1f1f1f;
  --text-secondary: #666666;
  --text-tertiary: #999999;
  --border: #E8E8E8;
  --bg-light: #F5F7FA;
  --bg-white: #FFFFFF;
  --radius: 12px;
  --shadow: 0 1px 2px rgba(0,0,0,0.03), 0 2px 6px rgba(0,0,0,0.04);
  --shadow-hover: 0 8px 24px rgba(22,119,255,0.15);

  padding: 24px 32px;
  background: var(--bg-light);
  min-height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}

.page-title {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
}

.title-left h1 {
  font-size: 26px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0 0 4px;
  letter-spacing: -0.5px;
}

.subtitle {
  font-size: 14px;
  color: var(--text-tertiary);
  margin: 0;
}

.update-time {
  font-size: 13px;
  color: var(--text-tertiary);
}

/* 指标卡片 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.metric-card {
  background: var(--bg-white);
  border-radius: var(--radius);
  padding: 20px;
  box-shadow: var(--shadow);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.metric-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-hover);
}

.metric-glow {
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, var(--accent) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s;
}

.metric-card:hover .metric-glow {
  opacity: 0.03;
}

.metric-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.metric-label {
  font-size: 14px;
  color: var(--text-secondary);
}

.metric-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-svg {
  width: 20px;
  height: 20px;
  color: var(--primary);
}

.metric-body {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.metric-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  transition: color 0.3s;
}

.metric-unit {
  font-size: 14px;
  color: var(--text-tertiary);
}

.metric-sparkline {
  height: 30px;
  margin: 8px 0;
}

.metric-sparkline svg {
  width: 100%;
  height: 100%;
}

.metric-footer {
  display: flex;
  align-items: center;
  gap: 6px;
}

.metric-change {
  font-size: 13px;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
}

.metric-change.up {
  color: var(--success);
  background: rgba(82, 196, 26, 0.1);
}

.metric-change.down {
  color: var(--danger);
  background: rgba(255, 77, 79, 0.1);
}

.metric-period {
  font-size: 12px;
  color: var(--text-tertiary);
}

/* 内容网格 */
.content-grid {
  display: grid;
  grid-template-columns: 1.2fr 1fr;
  gap: 24px;
  margin-bottom: 24px;
}

.chart-panel {
  background: var(--bg-white);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 24px;
  border-bottom: 1px solid var(--border);
}

.panel-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
}

.chart-legend {
  display: flex;
  gap: 16px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--text-secondary);
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--primary);
}

.chart-body {
  padding: 24px;
}

/* 柱状图 v3 */
.bar-chart-v3 {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  height: 200px;
  padding: 0 10px;
}

.bar-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
  position: relative;
}

.bar-tooltip {
  position: absolute;
  top: -30px;
  background: var(--text-primary);
  color: #fff;
  padding: 4px 10px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 500;
  opacity: 0;
  transform: translateY(10px);
  transition: all 0.2s;
  white-space: nowrap;
}

.bar-item:hover .bar-tooltip {
  opacity: 1;
  transform: translateY(0);
}

.bar-track {
  width: 40px;
  height: 100%;
  background: linear-gradient(180deg, #F5F7FA 0%, #E8ECF1 100%);
  border-radius: 8px;
  position: relative;
  overflow: hidden;
}

.bar-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(180deg, var(--primary) 0%, #4096FF 50%, #69B1FF 100%);
  border-radius: 8px;
  transition: height 0.8s cubic-bezier(0.4, 0, 0.2, 1);
  animation: barGrow 1s cubic-bezier(0.4, 0, 0.2, 1) var(--delay) both;
}

.bar-shine {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 50%;
  background: linear-gradient(180deg, rgba(255,255,255,0.3) 0%, transparent 100%);
  border-radius: 8px 8px 0 0;
}

@keyframes barGrow {
  from { height: 0; }
}

.bar-item:hover .bar-fill {
  background: linear-gradient(180deg, #0958D9 0%, var(--primary) 50%, #69B1FF 100%);
}

.bar-label {
  font-size: 13px;
  color: var(--text-tertiary);
  margin-top: 14px;
  font-weight: 500;
}

.chart-stats {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 32px;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.stat-divider {
  width: 1px;
  height: 40px;
  background: var(--border);
}

/* 环形图 */
.donut-body {
  display: flex;
  align-items: center;
  gap: 32px;
}

.donut-container {
  position: relative;
  width: 180px;
  height: 180px;
  flex-shrink: 0;
}

.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.donut-bg {
  fill: none;
  stroke: var(--bg-light);
  stroke-width: 12;
}

.donut-segment {
  fill: none;
  stroke-width: 12;
  stroke-linecap: round;
  animation: donutReveal 1s cubic-bezier(0.4, 0, 0.2, 1) var(--delay) both;
  filter: url(#glow);
}

@keyframes donutReveal {
  from {
    stroke-dasharray: 0 440;
    opacity: 0;
  }
}

.donut-center-ring {
  fill: none;
  stroke: var(--bg-white);
  stroke-width: 20;
}

.donut-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.donut-total {
  display: block;
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
}

.donut-label {
  font-size: 12px;
  color: var(--text-tertiary);
}

.donut-legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.donut-legend .legend-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}

.donut-legend .legend-item:hover {
  background: var(--bg-light);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.legend-text {
  flex: 1;
  font-size: 14px;
  color: var(--text-secondary);
}

.legend-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}

.legend-percent {
  font-size: 12px;
  color: var(--text-tertiary);
  min-width: 40px;
  text-align: right;
}

/* 实时记录 */
.record-section {
  display: grid;
  grid-template-columns: 1fr 1.5fr;
  gap: 24px;
}

.record-panel {
  background: var(--bg-white);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}

.panel-body {
  padding: 0;
}

.record-tabs {
  display: flex;
  padding: 0 24px;
  border-bottom: 1px solid var(--border);
}

.record-tabs button {
  padding: 16px 0;
  margin-right: 24px;
  background: none;
  border: none;
  font-size: 14px;
  color: var(--text-secondary);
  cursor: pointer;
  position: relative;
  transition: color 0.2s;
}

.record-tabs button:hover {
  color: var(--text-primary);
}

.record-tabs button.active {
  color: var(--primary);
  font-weight: 500;
}

.record-tabs button.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: var(--primary);
  border-radius: 2px 2px 0 0;
}

.record-list {
  padding: 8px 24px 16px;
}

.record-item {
  display: flex;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  transition: all 0.2s;
  animation: slideIn 0.3s ease var(--delay) both;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
}

.record-item:last-child {
  border-bottom: none;
}

.record-item:hover {
  background: var(--bg-light);
  margin: 0 -24px;
  padding-left: 24px;
  padding-right: 24px;
  border-radius: 8px;
}

.record-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  flex-shrink: 0;
}

.record-icon {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.record-icon svg {
  width: 20px;
  height: 20px;
}

.record-icon.document-icon {
  color: var(--text-tertiary);
}

.record-icon.high {
  color: var(--danger);
}

.record-icon.medium {
  color: var(--warning);
}

.record-content {
  flex: 1;
  margin-left: 12px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.record-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text-primary);
}

.record-dept {
  font-size: 13px;
  color: var(--text-tertiary);
}

.record-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  margin-right: 12px;
  font-weight: 500;
}

.record-badge.new {
  background: rgba(22, 119, 255, 0.1);
  color: var(--primary);
}

.record-badge.high {
  background: rgba(255, 77, 79, 0.1);
  color: var(--danger);
}

.record-badge.medium {
  background: rgba(250, 173, 20, 0.1);
  color: var(--warning);
}

.record-time {
  font-size: 13px;
  color: var(--text-tertiary);
  flex-shrink: 0;
}

.record-status {
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 4px;
  flex-shrink: 0;
}

.record-status.done {
  background: rgba(82, 196, 26, 0.1);
  color: var(--success);
}

.record-status.pending {
  background: rgba(250, 173, 20, 0.1);
  color: var(--warning);
}

/* 底部数据栏 */
.ticker-panel {
  background: var(--bg-white);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.ticker-header {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ticker-label {
  background: linear-gradient(135deg, var(--primary) 0%, #4096FF 100%);
  color: #fff;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 500;
}

.ticker-stats {
  display: flex;
  gap: 24px;
}

.ticker-stat {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ticker-stat-value {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}

.ticker-stat-label {
  font-size: 13px;
  color: var(--text-tertiary);
}

.ticker-chart-wrapper {
  padding: 12px 16px 16px;
}

.ticker-chart {
  width: 100%;
  height: 400px;
}
</style>
