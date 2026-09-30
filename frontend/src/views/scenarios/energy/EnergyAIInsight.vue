<template>
  <div class="energy-ai-insight">
    <!-- 第一行：预测 + 优化 -->
    <el-row :gutter="20" class="ai-row">
      <el-col :span="8">
        <el-card shadow="never" class="ai-card">
          <template #header>
            <div class="ai-card-header">
              <span><span class="ai-icon">📈</span> 能耗预测（未来7天）</span>
              <AiSourceTag :result="predictionData[0]" ml-text="LSTM模型" fallback-text="统计基线" />
            </div>
          </template>
          <div v-if="predictionData.length > 0" ref="predictionChartRef" style="height:300px;width:100%"></div>
          <el-skeleton v-else :rows="5" animated />
        </el-card>
      </el-col>

      <el-col :span="8">
        <slot name="alert-list" />
      </el-col>

      <el-col :span="8">
        <el-card shadow="never" class="ai-card">
          <template #header>
            <div class="ai-card-header">
              <span><span class="ai-icon">💡</span> 节能优化建议</span>
              <AiSourceTag :result="optimizationList[0]" ml-text="ML模型" fallback-text="规则库" />
              <el-tag type="warning" size="small" effect="dark">
                {{ priorityCount('高') }} 项高优
              </el-tag>
            </div>
          </template>
          <div v-if="optimizationList.length > 0" class="optimize-list">
            <div v-for="item in optimizationList" :key="item.id" class="optimize-item" :class="'priority-' + item.priority">
              <div class="optimize-top">
                <el-tag :type="priorityTag(item.priority)" size="small" effect="dark" class="priority-tag">{{ item.priority }}</el-tag>
                <el-tag size="small" plain class="category-tag">{{ item.category }}</el-tag>
              </div>
              <h4 class="optimize-title">{{ item.title }}</h4>
              <p class="optimize-desc">{{ item.description }}</p>
            </div>
          </div>
          <div v-else style="text-align:center;padding:40px 0;color:#909399">
            <span style="font-size:40px">🌿</span>
            <p style="margin-top:12px">暂无优化建议</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二行：设备能效分析 + AI报告 -->
    <el-row :gutter="20" class="ai-row" style="margin-top:16px">
      <el-col :span="12">
        <el-card shadow="never" class="ai-card">
          <template #header>
            <div class="ai-card-header">
              <span><span class="ai-icon">🔬</span> 设备能效分析</span>
              <div style="display:flex;align-items:center;gap:6px">
                <AiSourceTag :result="deviceAnalysisData" ml-text="ML模型" fallback-text="统计汇总" />
                <el-button size="small" type="primary" plain @click="loadDeviceAnalysis">刷新数据</el-button>
              </div>
            </div>
          </template>
          <div v-if="deviceAnalysisData">
            <el-row :gutter="12" style="margin-bottom:12px">
              <el-col :span="8">
                <div class="mini-stat"><div class="mini-num">{{ deviceAnalysisData.totalConsumption }}</div><div class="mini-label">总能耗(kWh)</div></div>
              </el-col>
              <el-col :span="8">
                <div class="mini-stat"><div class="mini-num">￥{{ deviceAnalysisData.totalCost }}</div><div class="mini-label">总电费</div></div>
              </el-col>
              <el-col :span="8">
                <div class="mini-stat"><div class="mini-num">{{ deviceAnalysisData.avgDailyConsumption }}</div><div class="mini-label">日均(kWh)</div></div>
              </el-col>
            </el-row>
            <div v-if="Object.keys(deviceAnalysisData.topConsumptionDevices || {}).length > 0">
              <h4 class="section-title">🔥 能耗TOP5设备</h4>
              <div v-for="(val, name, idx) in deviceAnalysisData.topConsumptionDevices" :key="name" class="rank-item">
                <span class="rank-num">{{ idx + 1 }}</span>
                <span class="rank-name">{{ name }}</span>
                <el-progress :percentage="Math.min(100, (val / deviceAnalysisData.totalConsumption) * 100)" :stroke-width="16" style="flex:1;margin:0 10px" />
                <span class="rank-val">{{ val }} kWh</span>
              </div>
            </div>
            <div v-if="Object.keys(deviceAnalysisData.efficiencyScores || {}).length > 0" style="margin-top:12px">
              <h4 class="section-title">⭐ 能效评分</h4>
              <div v-for="(score, name) in deviceAnalysisData.efficiencyScores" :key="name" class="eff-item">
                <span class="eff-name">{{ name }}</span>
                <el-rate :model-value="Math.round(score / 20)" disabled :texts="['很差','较差','一般','良好','优秀']" show-text :colors="['#f56c6c','#e6a23c','#909399','#409eff','#67c23a']" />
              </div>
            </div>
          </div>
          <div v-else style="text-align:center;padding:30px;color:#909399">
            <span style="font-size:36px">📊</span>
            <p style="margin-top:8px">点击刷新按钮加载数据</p>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card shadow="never" class="ai-card">
          <template #header>
            <div class="ai-card-header">
              <span><span class="ai-icon">🤖</span> AI智能报告</span>
              <div style="display:flex;align-items:center;gap:6px">
                <AiSourceTag :result="summaryReport" ml-text="ML模型" fallback-text="规则汇总" />
                <el-button size="small" type="primary" plain @click="loadSummaryReport">生成报告</el-button>
              </div>
            </div>
          </template>
          <div v-if="summaryReport">
            <h4 style="margin:0 0 12px;font-size:14px;color:#303133">{{ summaryReport.reportTitle }}</h4>
            <div class="report-summary" style="white-space:pre-wrap;line-height:1.8;font-size:13px;color:#606266;background:#f5f7fa;padding:16px;border-radius:8px">{{ summaryReport.summary }}</div>
            <el-row :gutter="12" style="margin-top:16px">
              <el-col :span="8">
                <div class="mini-stat"><div class="mini-num">{{ summaryReport.totalConsumption }}</div><div class="mini-label">总能耗</div></div>
              </el-col>
              <el-col :span="8">
                <div class="mini-stat"><div class="mini-num" style="color:#e6a23c">￥{{ summaryReport.totalCost }}</div><div class="mini-label">电费</div></div>
              </el-col>
              <el-col :span="8">
                <div class="mini-stat"><div class="mini-num" style="color:#67c23a">{{ summaryReport.carbonEmission }}</div><div class="mini-label">碳排放(kg)</div></div>
              </el-col>
            </el-row>
            <div style="margin-top:12px;display:flex;gap:16px;align-items:center">
              <div><el-tag type="success">{{ summaryReport.normalDevices }} 台运行中</el-tag></div>
              <div><el-tag :type="summaryReport.abnormalDevices > 0 ? 'danger' : 'info'">{{ summaryReport.abnormalDevices > 0 ? '⚠️ ' : '' }}{{ summaryReport.abnormalDevices }} 台异常</el-tag></div>
              <div style="font-size:12px;color:#909399">{{ summaryReport.generateTime }}</div>
            </div>
          </div>
          <div v-else style="text-align:center;padding:30px;color:#909399">
            <span style="font-size:36px">🤖</span>
            <p style="margin-top:8px">点击生成报告按钮获取AI分析</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { getEnergyPrediction, getEnergyAnomalies, getEnergyOptimization } from '../../../api/modules'
import service from '../../../api/index'
import AiSourceTag from '../../../components/AiSourceTag.vue'

const emit = defineEmits(['data-loaded', 'loading-change'])

const predictionData = ref([])
const optimizationList = ref([])
const deviceAnalysisData = ref(null)
const summaryReport = ref(null)

let predictionChart = null
const predictionChartRef = ref(null)

async function loadAIAnalysis() {
  try {
    const [predRes, anomRes, optRes] = await Promise.all([
      getEnergyPrediction(7),
      getEnergyAnomalies(),
      getEnergyOptimization()
    ])
    predictionData.value = predRes.data || []
    const anomalyList = anomRes.data || []
    optimizationList.value = optRes.data || []
    emit('data-loaded', { anomalyList })
  } catch {
    predictionData.value = []
    optimizationList.value = []
    emit('data-loaded', { anomalyList: [] })
  }
  await nextTick()
  initPredictionChart()
}

async function loadDeviceAnalysis() {
  try {
    const res = await service.get('/energy/analysis/device-analysis')
    deviceAnalysisData.value = res.data || null
  } catch { deviceAnalysisData.value = null }
}

async function loadSummaryReport() {
  try {
    const res = await service.get('/energy/analysis/summary-report')
    summaryReport.value = res.data || null
  } catch { summaryReport.value = null }
}

function getPredictionOption(data) {
  if (!data?.length) return {}
  const dates = data.map(d => d.date || '')
  const predicted = data.map(d => d.predicted || 0)
  const lower = data.map(d => d.lowerBound || d.confidenceLower || (d.predicted * 0.85))
  const upper = data.map(d => d.upperBound || d.confidenceUpper || (d.predicted * 1.15))
  return {
    tooltip: { trigger: 'axis', formatter: params => {
      const p = params.find(pr => pr.seriesName === '预测值')
      return p ? `${p.axisValue}<br/>预测: ${p.value} kWh` : ''
    }},
    legend: { data: ['预测值', '置信区间'], bottom: 0, textStyle: { fontSize: 11 } },
    grid: { left: '3%', right: '4%', bottom: '22%', top: '8%', containLabel: true },
    xAxis: { type: 'category', data: dates, boundaryGap: false, axisLabel: { fontSize: 10, rotate: 30 } },
    yAxis: { type: 'value', name: 'kWh', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      { name: '置信区间', type: 'line', data: upper, lineStyle: { width: 0 }, symbol: 'none', areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(103,194,58,0.15)'},{offset:1,color:'rgba(103,194,58,0.01)'}]) }, z: 1 },
      { name: '置信区间', type: 'line', data: lower, lineStyle: { width: 0 }, symbol: 'none', areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:'rgba(103,194,58,0.3)'},{offset:1,color:'rgba(103,194,58,0.05)'}]) }, z: 2 },
      { name: '预测值', type: 'line', data: predicted, smooth: true, symbol: 'diamond', symbolSize: 8, lineStyle: { width: 2, color: '#67c23a' }, itemStyle: { color: '#67c23a' }, z: 3 }
    ]
  }
}

function initPredictionChart() {
  if (predictionChart) { predictionChart.dispose(); predictionChart = null }
  if (!predictionChartRef.value || !predictionData.value.length) return
  predictionChart = echarts.init(predictionChartRef.value)
  predictionChart.setOption(getPredictionOption(predictionData.value))
}

function resizeCharts() {
  if (predictionChart) predictionChart.resize()
}

function priorityTag(p) { return { '高': 'danger', '中': 'warning', '低': 'info' }[p] || 'info' }
function priorityCount(level) { return optimizationList.value.filter(o => o.priority === level).length }

onMounted(() => loadAIAnalysis())
onUnmounted(() => {
  window.removeEventListener('resize', resizeCharts)
  if (predictionChart) predictionChart.dispose()
})
</script>

<style scoped>
.ai-row { min-height: 200px; }
.ai-card { border-radius: 10px; height: 100%; border: 1px solid #e8e8e8; transition: all 0.3s ease; }
.ai-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
.ai-card-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
.ai-icon { margin-right: 4px; }
.section-title { margin: 8px 0; font-size: 13px; color: #606266; }
.optimize-list { max-height: 580px; overflow-y: auto; }
.optimize-item { padding: 14px; border-radius: 8px; margin-bottom: 10px; border-left: 4px solid #909399; background: #fafafa; transition: all 0.2s ease; }
.optimize-item:hover { background: #f0f0f0; }
.optimize-item.priority-高 { border-left-color: #f56c6c; background: #fef0f0; }
.optimize-item.priority-中 { border-left-color: #e6a23c; background: #fdf6ec; }
.optimize-item.priority-低 { border-left-color: #409eff; background: #f0f8ff; }
.optimize-top { display: flex; gap: 6px; margin-bottom: 6px; }
.optimize-title { font-size: 14px; font-weight: 600; color: #303133; margin: 6px 0 4px; }
.optimize-desc { font-size: 12px; color: #606266; margin: 0; line-height: 1.6; }
.rank-item { display: flex; align-items: center; padding: 6px 0; gap: 8px; }
.rank-num { width: 20px; height: 20px; border-radius: 50%; background: #409eff; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex-shrink: 0; }
.rank-name { font-size: 13px; color: #606266; min-width: 80px; flex-shrink: 0; }
.rank-val { font-size: 12px; color: #909399; white-space: nowrap; flex-shrink: 0; }
.eff-item { display: flex; align-items: center; padding: 4px 0; gap: 8px; }
.eff-name { font-size: 12px; color: #606266; min-width: 80px; flex-shrink: 0; }
.mini-stat { text-align: center; padding: 12px 8px; background: #f5f7fa; border-radius: 8px; }
.mini-num { font-size: 20px; font-weight: 700; color: #409eff; }
.mini-label { font-size: 11px; color: #909399; margin-top: 4px; }
.optimize-list::-webkit-scrollbar { width: 4px; }
.optimize-list::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }
.optimize-list::-webkit-scrollbar-track { background: transparent; }
</style>
