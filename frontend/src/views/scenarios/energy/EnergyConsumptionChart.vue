<template>
  <div class="energy-consumption-chart">
    <!-- Tab: 能耗记录 -->
    <el-card shadow="hover" class="tab-card">
      <template #header>
        <div class="flex-between">
          <span class="card-title">📊 能耗数据记录</span>
        </div>
      </template>
      <el-row :gutter="16" class="filter-row">
        <el-col :span="8">
          <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期"
            end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width:100%" />
        </el-col>
        <el-col :span="5">
          <el-select v-model="consFilterDevice" placeholder="选择设备" clearable style="width:100%">
            <el-option v-for="d in devices" :key="d.deviceId" :label="d.deviceId + ' - ' + d.deviceType" :value="d.deviceId" />
          </el-select>
        </el-col>
        <el-col :span="5" style="text-align:right">
          <el-button type="primary" :icon="Search" @click="loadConsumption">查询</el-button>
          <el-button type="success" :icon="Plus" @click="openAddConsumption">添加记录</el-button>
        </el-col>
        <el-col :span="6" style="text-align:right">
          <el-button type="warning" plain :icon="DataAnalysis" @click="showStats = true">能耗统计</el-button>
        </el-col>
      </el-row>
      <el-table :data="consumption" stripe v-loading="consLoading" border style="width:100%" class="energy-table">
        <el-table-column prop="recordId" label="记录ID" width="180" />
        <el-table-column prop="deviceId" label="设备编号" width="160" />
        <el-table-column prop="consumptionValue" label="能耗值(kWh)" width="130" align="center">
          <template #default="{ row }">
            <span class="kwh-value">{{ row.consumptionValue }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="consumptionDate" label="记录日期" width="130" />
        <el-table-column label="操作" width="100">
          <template #default="{ row }">
            <el-button size="small" type="danger" plain @click="deleteConsumption(row.recordId)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 能耗统计面板（折叠） -->
    <el-card v-if="showStats" shadow="hover" class="tab-card" style="margin-top:16px">
      <template #header>
        <div class="flex-between">
          <span class="card-title">📈 能耗统计分析</span>
          <el-button size="small" :icon="Fold" @click="showStats = false">收起</el-button>
        </div>
      </template>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="6">
          <div class="stat-card blue">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ statsData?.totalDevices || 0 }}</div>
              <div class="stat-card-label">设备总数</div>
            </div>
            <div class="stat-card-icon">📟</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card green">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ statsData?.totalConsumption?.toFixed(1) || 0 }}</div>
              <div class="stat-card-label">总能耗 (kWh)</div>
            </div>
            <div class="stat-card-icon">⚡</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card teal">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ avgConsumption }}</div>
              <div class="stat-card-label">平均能耗 (kWh)</div>
            </div>
            <div class="stat-card-icon">🔋</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card purple">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ deviceTypeCount }}</div>
              <div class="stat-card-label">设备类型数</div>
            </div>
            <div class="stat-card-icon">🗂️</div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="24" style="margin-top:24px">
        <el-col :span="10">
          <el-card shadow="never" class="chart-card">
            <template #header><span class="chart-title">各类型设备能耗占比</span></template>
            <div v-if="hasPieData" ref="pieChartRef" style="height:320px;width:100%"></div>
            <el-empty v-else description="暂无能耗占比数据" :image-size="120" />
          </el-card>
        </el-col>
        <el-col :span="14">
          <el-card shadow="never" class="chart-card">
            <template #header><span class="chart-title">能耗趋势</span></template>
            <div v-if="hasTrendData" ref="trendChartRef" style="height:320px;width:100%"></div>
            <el-empty v-else description="暂无能耗趋势数据" :image-size="120" />
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <!-- 能耗添加对话框 -->
    <el-dialog v-model="showConsDialog" title="添加能耗记录" width="480px" class="energy-dialog">
      <el-form :model="consForm" label-width="110px" label-position="left">
        <el-form-item label="设备编号">
          <el-select v-model="consForm.deviceId" placeholder="选择设备" style="width:100%">
            <el-option v-for="d in devices" :key="d.deviceId" :label="d.deviceId + ' - ' + d.deviceType" :value="d.deviceId" />
          </el-select>
        </el-form-item>
        <el-form-item label="能耗值 (kWh)">
          <el-input-number v-model="consForm.consumptionValue" :min="0" :step="0.1" :precision="1" style="width:100%" />
        </el-form-item>
        <el-form-item label="记录日期">
          <el-date-picker v-model="consForm.consumptionDate" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%" placeholder="选择日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showConsDialog = false">取消</el-button>
        <el-button type="primary" :loading="consSaving" @click="saveConsumptionForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, shallowRef, onMounted, onUnmounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, DataAnalysis, Fold } from '@element-plus/icons-vue'
import { getDevices, getConsumption, saveConsumption, getEnergyStats, getEnergyTrend } from '../../../api/modules'

const consLoading = ref(false)
const consSaving = ref(false)
const devices = ref([])
const consumption = ref([])
const dateRange = ref([])
const consFilterDevice = ref('')
const showConsDialog = ref(false)
const consForm = ref({ deviceId: '', consumptionValue: 0, consumptionDate: '' })
const showStats = ref(false)

// 统计
const statsData = ref(null)
const trendData = ref([])
let pieChart = null
let trendChart = null
const pieChartRef = ref(null)
const trendChartRef = ref(null)

const avgConsumption = computed(() => {
  if (!statsData.value?.totalConsumption || !statsData.value?.totalDevices) return '0'
  return (statsData.value.totalConsumption / statsData.value.totalDevices).toFixed(1)
})
const deviceTypeCount = computed(() => {
  if (devices.value.length === 0) return 0
  return new Set(devices.value.map(d => d.deviceType)).size
})
const hasPieData = computed(() => statsData.value?.typeConsumption && Object.keys(statsData.value.typeConsumption).length > 0)
const hasTrendData = computed(() => trendData.value.length > 0)

async function loadDevices() {
  try {
    const res = await getDevices()
    devices.value = res.data || []
  } catch { devices.value = [] }
}

async function loadConsumption() {
  consLoading.value = true
  try {
    const params = {}
    if (dateRange.value?.length === 2) {
      params.startDate = dateRange.value[0]
      params.endDate = dateRange.value[1]
    }
    if (consFilterDevice.value) params.deviceId = consFilterDevice.value
    const res = await getConsumption(params)
    consumption.value = res.data || []
  } catch { consumption.value = [] }
  finally { consLoading.value = false }
}

function openAddConsumption() {
  consForm.value = { deviceId: '', consumptionValue: 0, consumptionDate: '' }
  showConsDialog.value = true
}

async function saveConsumptionForm() {
  if (!consForm.value.deviceId) { ElMessage.warning('请选择设备'); return }
  if (!consForm.value.consumptionDate) { ElMessage.warning('请选择日期'); return }
  consSaving.value = true
  try {
    await saveConsumption(consForm.value)
    ElMessage.success('添加成功')
    showConsDialog.value = false
    await loadConsumption()
  } catch { ElMessage.error('保存失败') }
  finally { consSaving.value = false }
}

async function deleteConsumption(id) {
  try {
    await ElMessageBox.confirm('确定删除该记录？', '确认', { type: 'warning' })
    await saveConsumption({ recordId: id, _delete: true })
    ElMessage.success('删除成功')
    await loadConsumption()
  } catch { /* skip */ }
}

async function loadStats() {
  try {
    const [statsRes, trendRes] = await Promise.all([getEnergyStats(), getEnergyTrend()])
    statsData.value = statsRes.data || null
    trendData.value = trendRes.data || []
  } catch {
    statsData.value = null
    trendData.value = []
  }
  await nextTick()
  initPieChart()
  initTrendChart()
}

function getPieOption(data) {
  const colors = ['#67c23a', '#409eff', '#e6a23c', '#f56c6c', '#909399', '#00b4d8', '#b37feb']
  const entries = Object.entries(data)
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} kWh ({d}%)' },
    legend: { orient: 'vertical', right: '5%', top: 'center', textStyle: { fontSize: 12 } },
    series: [{
      type: 'pie', radius: ['40%', '70%'], center: ['35%', '50%'],
      avoidLabelOverlap: true,
      itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
      label: { show: false },
      emphasis: { label: { show: true, fontSize: 14, fontWeight: 'bold' }, itemStyle: { shadowBlur: 10 } },
      data: entries.map(([k, v], i) => ({ name: k, value: v, itemStyle: { color: colors[i % colors.length] } }))
    }]
  }
}

function getTrendOption(data) {
  if (!data?.length) return {}
  return {
    tooltip: { trigger: 'axis', formatter: params => `${params[0].axisValue}<br/>能耗: ${params[0].value} kWh` },
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
    xAxis: { type: 'category', data: data.map(d => d.date || d.consumptionDate || ''), boundaryGap: false },
    yAxis: { type: 'value', name: 'kWh', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [{
      type: 'line', data: data.map(d => d.value || d.consumptionValue || 0), smooth: true,
      symbol: 'circle', symbolSize: 6, lineStyle: { width: 3, color: '#409eff' },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
        { offset: 0, color: 'rgba(64,158,255,0.35)' }, { offset: 1, color: 'rgba(64,158,255,0.05)' }
      ])},
      itemStyle: { color: '#409eff' }
    }]
  }
}

function initPieChart() {
  if (pieChart) { pieChart.dispose(); pieChart = null }
  if (!pieChartRef.value) return
  const data = statsData.value?.typeConsumption
  if (!data || Object.keys(data).length === 0) return
  pieChart = echarts.init(pieChartRef.value)
  pieChart.setOption(getPieOption(data))
}

function initTrendChart() {
  if (trendChart) { trendChart.dispose(); trendChart = null }
  if (!trendChartRef.value || !trendData.value.length) return
  trendChart = echarts.init(trendChartRef.value)
  trendChart.setOption(getTrendOption(trendData.value))
}

function resizeCharts() {
  if (pieChart) pieChart.resize()
  if (trendChart) trendChart.resize()
}

watch(showStats, (val) => { if (val) nextTick(() => loadStats()) })

onMounted(() => {
  loadDevices()
  loadConsumption()
  window.addEventListener('resize', resizeCharts)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  if (pieChart) pieChart.dispose()
  if (trendChart) trendChart.dispose()
})
</script>

<style scoped>
.tab-card { border-radius: 12px; transition: all 0.3s ease; }
.tab-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.card-title { font-size: 16px; font-weight: 600; background: linear-gradient(135deg,#409eff,#67c23a); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.flex-between { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.filter-row { margin-bottom: 16px; padding: 12px 16px; background: #f8fafb; border-radius: 8px; align-items: center; }
.energy-table { border-radius: 8px; }
.kwh-value { font-weight: 600; color: #409eff; }
.stats-row { margin-bottom: 16px; }
.stat-card { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; border-radius: 10px; transition: all 0.3s ease; cursor: default; }
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
.stat-card.blue { background: linear-gradient(135deg,#e6f7ff,#bae7ff); border: 1px solid #91d5ff; }
.stat-card.green { background: linear-gradient(135deg,#f6ffed,#d9f7be); border: 1px solid #b7eb8f; }
.stat-card.teal { background: linear-gradient(135deg,#e6fffb,#b5f5ec); border: 1px solid #87e8de; }
.stat-card.purple { background: linear-gradient(135deg,#f9f0ff,#efdbff); border: 1px solid #d3adf7; }
.stat-card-body { flex: 1; }
.stat-card-value { font-size: 30px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-card-label { font-size: 13px; color: #606266; margin-top: 4px; }
.stat-card-icon { font-size: 36px; opacity: 0.7; }
.chart-card { border-radius: 10px; border: 1px solid #e8e8e8; }
.chart-title { font-size: 14px; font-weight: 600; color: #303133; }
</style>
