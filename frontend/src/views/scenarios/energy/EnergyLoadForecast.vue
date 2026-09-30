<template>
  <div class="energy-load-forecast">
    <!-- 负荷预测标题 & 操作 -->
    <el-card shadow="hover" class="tab-card">
      <template #header>
        <div class="flex-between">
          <span class="card-title">⚡ 能源负荷预测
            <el-tag v-if="engine === 'lstm_model'" size="mini" type="success" effect="plain" style="margin-left:8px">LSTM模型</el-tag>
            <el-tag v-else-if="engine === 'statistical_fallback'" size="mini" type="info" effect="plain" style="margin-left:8px">统计兵底</el-tag>
            <el-tag v-else-if="engine === 'mock'" size="mini" type="warning" effect="plain" style="margin-left:8px">本地模拟数据</el-tag>
          </span>
          <el-button type="primary" :icon="Refresh" :loading="loading" @click="runForecast">
            刷新预测
          </el-button>
        </div>
      </template>

      <!-- 关键指标 -->
      <el-row :gutter="20" class="stats-row">
        <el-col :span="6">
          <div class="stat-card blue">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ forecastResult.peakLoad ?? '--' }}</div>
              <div class="stat-card-label">峰值负荷 (kW)</div>
            </div>
            <div class="stat-card-icon">📈</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card orange">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ forecastResult.peakHour != null ? forecastResult.peakHour + ':00' : '--' }}</div>
              <div class="stat-card-label">峰值时刻</div>
            </div>
            <div class="stat-card-icon">🕐</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card green">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ forecastResult.totalKwh ?? '--' }}</div>
              <div class="stat-card-label">总用电量 (kWh)</div>
            </div>
            <div class="stat-card-icon">🔋</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-card purple">
            <div class="stat-card-body">
              <div class="stat-card-value">{{ forecastResult.trend ?? '--' }}</div>
              <div class="stat-card-label">整体趋势</div>
            </div>
            <div class="stat-card-icon">📉</div>
          </div>
        </el-col>
      </el-row>

      <!-- 24h 负荷预测折线图 -->
      <el-card shadow="never" class="chart-card" style="margin-top:16px">
        <template #header>
          <div class="flex-between">
            <span class="chart-title">🔮 未来 24 小时负荷预测</span>
            <el-tag v-if="lastUpdate" type="info" effect="plain" size="small">
              更新于 {{ lastUpdate }}
            </el-tag>
          </div>
        </template>
        <div ref="chartRef" style="height:380px;width:100%"></div>
      </el-card>

      <!-- 预测详情表格 -->
      <el-card shadow="never" class="chart-card" style="margin-top:16px">
        <template #header>
          <span class="chart-title">📋 逐时负荷明细</span>
        </template>
        <el-table :data="hourlyDetail" stripe border style="width:100%" class="energy-table" v-if="hourlyDetail.length > 0" max-height="400">
          <el-table-column label="时段" width="120" align="center">
            <template #default="{ row }">
              <span class="hour-label">{{ String(row.hour).padStart(2, '0') }}:00</span>
            </template>
          </el-table-column>
          <el-table-column prop="predicted" label="预测负荷 (kW)" width="160" align="center">
            <template #default="{ row }">
              <span class="kwh-value">{{ row.predicted.toFixed(1) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="负荷等级" min-width="120" align="center">
            <template #default="{ row }">
              <el-tag v-if="row.level === 'peak'" type="danger" effect="dark" size="small">高峰</el-tag>
              <el-tag v-else-if="row.level === 'high'" type="warning" effect="plain" size="small">偏高</el-tag>
              <el-tag v-else-if="row.level === 'medium'" type="primary" effect="plain" size="small">中等</el-tag>
              <el-tag v-else type="success" effect="plain" size="small">低谷</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="趋势指示" width="100" align="center">
            <template #default="{ row }">
              <span v-if="row.change === 'up'" style="color:#f56c6c">▲ 上升</span>
              <span v-else-if="row.change === 'down'" style="color:#67c23a">▼ 下降</span>
              <span v-else style="color:#909399">— 持平</span>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无预测数据" :image-size="120" />
      </el-card>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import { getEnergyLoadForecast } from '@/api/modules/energy'

const loading = ref(false)
const lastUpdate = ref('')
let chart = null
const chartRef = ref(null)
const hourlyDetail = ref([])
const engine = ref('')

// 负荷预测结果
const forecastResult = ref({
  peakLoad: '--',
  peakHour: null,
  totalKwh: '--',
  trend: '--'
})

// 生成 48 个历史负荷值（模拟真实数据）
function generateHistoricalLoads() {
  const now = new Date()
  const currentHour = now.getHours()
  const loads = []
  for (let i = 47; i >= 0; i--) {
    const hour = (currentHour - i + 48) % 24
    // 基础正弦波 + 晨峰(7-9点) + 晚峰(17-20点) + 随机噪声
    const base = 150 + 60 * Math.sin((hour / 24) * 2 * Math.PI)
    const morningPeak = hour >= 7 && hour <= 9 ? 50 * Math.sin(((hour - 7) / 3) * Math.PI) : 0
    const eveningPeak = hour >= 17 && hour <= 20 ? 60 * Math.sin(((hour - 17) / 4) * Math.PI) : 0
    const noise = (Math.random() - 0.5) * 20
    loads.push(Math.max(60, Math.round(base + morningPeak + eveningPeak + noise)))
  }
  return loads
}

// 生成 24 小时本地模拟预测数据（备用）
function generateMockForecast() {
  const predictions = []
  for (let h = 0; h < 24; h++) {
    const base = 150 + 60 * Math.sin((h / 24) * 2 * Math.PI)
    const morningPeak = h >= 7 && h <= 9 ? 50 * Math.sin(((h - 7) / 3) * Math.PI) : 0
    const eveningPeak = h >= 17 && h <= 20 ? 60 * Math.sin(((h - 17) / 4) * Math.PI) : 0
    const noise = (Math.random() - 0.5) * 20
    predictions.push(Math.max(60, Math.round((base + morningPeak + eveningPeak + noise) * 10) / 10))
  }
  return predictions
}

// 给每个小时计算等级和变化方向
function enrichHourlyDetail(predictions) {
  const avg = predictions.reduce((a, b) => a + b, 0) / predictions.length
  const sorted = [...predictions].sort((a, b) => b - a)
  const peakThreshold = sorted[Math.floor(sorted.length * 0.2)]
  const highThreshold = sorted[Math.floor(sorted.length * 0.5)]

  return predictions.map((val, idx) => {
    let level = 'low'
    if (val >= peakThreshold) level = 'peak'
    else if (val >= highThreshold) level = 'high'
    else if (val >= avg * 0.85) level = 'medium'

    let change = 'stable'
    if (idx > 0) {
      const diff = predictions[idx] - predictions[idx - 1]
      if (diff > 5) change = 'up'
      else if (diff < -5) change = 'down'
    }

    return { hour: idx, predicted: val, level, change }
  })
}

async function runForecast() {
  loading.value = true
  try {
    const historicalLoads = generateHistoricalLoads()
    const currentHour = new Date().getHours()
    const payload = {
      historical_loads: historicalLoads,
      current_hour: currentHour,
      base_load: 150
    }

    const res = await getEnergyLoadForecast(payload)
    const data = res.data || {}
    engine.value = data.source || 'unknown'

    // 优先使用 API 返回的预测值
    const predictions = data.predicted_loads || generateMockForecast()
    hourlyDetail.value = enrichHourlyDetail(predictions)

    forecastResult.value = {
      peakLoad: data.peak_load != null ? data.peak_load.toFixed(1) : Math.max(...predictions).toFixed(1),
      peakHour: data.peak_hour != null ? data.peak_hour : predictions.indexOf(Math.max(...predictions)),
      totalKwh: data.total_kwh != null ? data.total_kwh.toFixed(1) : predictions.reduce((a, b) => a + b, 0).toFixed(1),
      trend: data.trend || (predictions[predictions.length - 1] > predictions[0] ? '上升 ↑' : predictions[predictions.length - 1] < predictions[0] ? '下降 ↓' : '平稳 →')
    }

    now()
  } catch (err) {
    ElMessage.warning('API 请求失败，使用本地模拟数据展示')
    engine.value = 'mock'
    // 本地回退
    const predictions = generateMockForecast()
    hourlyDetail.value = enrichHourlyDetail(predictions)
    const peakIdx = predictions.indexOf(Math.max(...predictions))
    forecastResult.value = {
      peakLoad: Math.max(...predictions).toFixed(1),
      peakHour: peakIdx,
      totalKwh: predictions.reduce((a, b) => a + b, 0).toFixed(1),
      trend: predictions[predictions.length - 1] > predictions[0] ? '上升 ↑' : predictions[predictions.length - 1] < predictions[0] ? '下降 ↓' : '平稳 →'
    }
    now()
  } finally {
    loading.value = false
    await nextTick()
    initChart()
  }
}

function now() {
  const d = new Date()
  lastUpdate.value = `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

function initChart() {
  if (chart) { chart.dispose(); chart = null }
  if (!chartRef.value || hourlyDetail.value.length === 0) return

  chart = echarts.init(chartRef.value)
  const labels = hourlyDetail.value.map(d => String(d.hour).padStart(2, '0') + ':00')
  const values = hourlyDetail.value.map(d => d.predicted)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: params => {
        const p = params[0]
        const detail = hourlyDetail.value[p.dataIndex]
        const levelMap = { peak: '高峰 ⚠️', high: '偏高 ⚡', medium: '中等 🔵', low: '低谷 ✅' }
        return `<strong>${p.axisValue}</strong><br/>
                负荷: <strong>${p.value.toFixed(1)} kW</strong><br/>
                等级: ${levelMap[detail.level] || '正常'}`
      }
    },
    grid: { left: '3%', right: '6%', bottom: '3%', top: '8%', containLabel: true },
    xAxis: {
      type: 'category',
      data: labels,
      boundaryGap: false,
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: {
      type: 'value',
      name: '负荷 (kW)',
      splitLine: { lineStyle: { type: 'dashed', color: '#e8e8e8' } },
      axisLabel: { fontSize: 11 }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { type: 'slider', start: 0, end: 100, height: 20, bottom: 5 }
    ],
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 7,
      lineStyle: { width: 3, color: '#409eff' },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(64,158,255,0.40)' },
          { offset: 0.5, color: 'rgba(64,158,255,0.15)' },
          { offset: 1, color: 'rgba(64,158,255,0.02)' }
        ])
      },
      itemStyle: {
        color: (params) => {
          const detail = hourlyDetail.value[params.dataIndex]
          if (detail.level === 'peak') return '#f56c6c'
          if (detail.level === 'high') return '#e6a23c'
          if (detail.level === 'medium') return '#409eff'
          return '#67c23a'
        }
      },
      markLine: {
        silent: true,
        data: [
          { type: 'average', name: '平均负荷', label: { formatter: '均值: {c} kW', color: '#606266' }, lineStyle: { color: '#909399', type: 'dashed' } },
          { yAxis: Math.max(...values), name: '峰值', label: { formatter: '峰值: {c} kW', color: '#f56c6c' }, lineStyle: { color: '#f56c6c', type: 'dotted' } }
        ]
      },
      markPoint: {
        data: [
          { type: 'max', name: '峰值', symbolSize: 60, label: { formatter: '{c} kW', color: '#fff' }, itemStyle: { color: '#f56c6c' } }
        ]
      }
    }]
  })
}

function resizeChart() {
  if (chart) chart.resize()
}

onMounted(() => {
  runForecast()
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (chart) chart.dispose()
})
</script>

<style scoped>
.tab-card { border-radius: 12px; transition: all 0.3s ease; }
.tab-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.card-title { font-size: 16px; font-weight: 600; background: linear-gradient(135deg,#409eff,#67c23a); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.flex-between { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.stats-row { margin-bottom: 12px; }
.stat-card { display: flex; align-items: center; justify-content: space-between; padding: 18px 20px; border-radius: 10px; transition: all 0.3s ease; cursor: default; }
.stat-card:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
.stat-card.blue { background: linear-gradient(135deg,#e6f7ff,#bae7ff); border: 1px solid #91d5ff; }
.stat-card.orange { background: linear-gradient(135deg,#fff7e6,#ffe7ba); border: 1px solid #ffd591; }
.stat-card.green { background: linear-gradient(135deg,#f6ffed,#d9f7be); border: 1px solid #b7eb8f; }
.stat-card.purple { background: linear-gradient(135deg,#f9f0ff,#efdbff); border: 1px solid #d3adf7; }
.stat-card-body { flex: 1; }
.stat-card-value { font-size: 28px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-card-label { font-size: 13px; color: #606266; margin-top: 4px; }
.stat-card-icon { font-size: 36px; opacity: 0.7; }
.chart-card { border-radius: 10px; border: 1px solid #e8e8e8; }
.chart-title { font-size: 14px; font-weight: 600; color: #303133; }
.energy-table { border-radius: 8px; }
.hour-label { font-family: monospace; font-weight: 600; color: #409eff; }
.kwh-value { font-weight: 600; color: #409eff; }
</style>
