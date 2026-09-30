<template>
  <div class="correlation-page">
    <el-alert title="基于 PIMA 印第安人糖尿病数据集的胰岛素-血糖相关性分析" type="success" :closable="false" show-icon style="margin-bottom:16px">
      <template #default>
        计算胰岛素水平与血糖浓度之间的 Pearson 相关系数，评估两者的线性相关性及统计显著性。
        有效数据通过排除胰岛素/葡萄糖为0的无效记录得到。
      </template>
    </el-alert>

    <el-row :gutter="16">
      <!-- 左侧：相关性统计 -->
      <el-col :span="8">
        <el-card>
          <template #header><span>📊 相关性统计</span></template>
          <div v-if="loading" class="loading-placeholder"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>
          <div v-else-if="error" style="text-align:center;color:#f56c6c">{{ error }}</div>
          <div v-else-if="data" class="stats-panel">
            <div class="correlation-gauge">
              <div class="r-value" :style="{ color: rColor }">{{ data.correlation_coefficient }}</div>
              <div class="r-label">Pearson r</div>
            </div>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="相关系数 r">
                <el-tag :type="rTagType" size="small">{{ data.correlation_coefficient }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="P 值">{{ data.p_value }}</el-descriptions-item>
              <el-descriptions-item label="统计显著性">
                <el-tag :type="data.significant ? 'success' : 'info'" size="small">{{ data.significant ? '显著 (p&lt;0.05)' : '不显著' }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="样本量">{{ data.sample_size }}</el-descriptions-item>
              <el-descriptions-item label="胰岛素均值±SD">{{ data.summary?.mean_insulin?.toFixed(1) }} ± {{ data.summary?.std_insulin?.toFixed(1) }}</el-descriptions-item>
              <el-descriptions-item label="血糖均值±SD">{{ data.summary?.mean_glucose?.toFixed(1) }} ± {{ data.summary?.std_glucose?.toFixed(1) }}</el-descriptions-item>
            </el-descriptions>

            <el-divider />
            <h4>结果解读</h4>
            <p class="interpretation">
              {{ interpretation }}
            </p>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：散点图 -->
      <el-col :span="16">
        <el-card>
          <template #header><span>📈 胰岛素-血糖散点图</span></template>
          <div v-if="loading" class="loading-placeholder"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>
          <div v-else-if="data">
            <div ref="scatterChartRef" style="width:100%;height:420px"></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getInsulinGlucoseCorrelation } from '../../api/modules'

const data = ref(null)
const loading = ref(true)
const error = ref(null)
const scatterChartRef = ref(null)
let chartInstance = null

const rColor = computed(() => {
  if (!data.value) return '#909399'
  const r = Math.abs(data.value.correlation_coefficient || 0)
  if (r >= 0.5) return '#f56c6c'
  if (r >= 0.3) return '#e6a23c'
  return '#909399'
})

const rTagType = computed(() => {
  if (!data.value) return 'info'
  const r = Math.abs(data.value.correlation_coefficient || 0)
  if (r >= 0.5) return 'danger'
  if (r >= 0.3) return 'warning'
  return 'info'
})

const interpretation = computed(() => {
  if (!data.value) return ''
  const r = data.value.correlation_coefficient
  const absR = Math.abs(r)
  let strength = '无'
  if (absR >= 0.7) strength = '强'
  else if (absR >= 0.3) strength = '中等'
  else if (absR >= 0.1) strength = '弱'

  const direction = r > 0 ? '正相关' : '负相关'
  const sig = data.value.significant ? '具有统计显著性' : '不具有统计显著性'
  
  return `胰岛素与血糖之间存在${strength}${direction}（r=${r}），${sig}。` +
    (r > 0 ? ' 提示胰岛素水平升高与血糖浓度升高存在关联，可能与胰岛素抵抗相关。' : '')
})

async function loadData() {
  loading.value = true
  error.value = null
  try {
    const res = await getInsulinGlucoseCorrelation()
    data.value = res.data || res
    await nextTick()
    renderChart()
  } catch (e) {
    error.value = '获取数据失败: ' + (e.message || '')
    ElMessage.error(error.value)
  } finally {
    loading.value = false
  }
}

function renderChart() {
  if (!scatterChartRef.value || !data.value?.scatter_data) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(scatterChartRef.value)

  const scatterData = data.value.scatter_data.map(d => [d.insulin, d.glucose])

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `胰岛素: ${p.value[0].toFixed(1)}<br/>血糖: ${p.value[1].toFixed(1)}`
      }
    },
    grid: { left: '8%', right: '5%', bottom: '10%', top: '5%' },
    xAxis: {
      type: 'value', name: '胰岛素 (mu U/ml)',
      nameLocation: 'center', nameGap: 30,
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } }
    },
    yAxis: {
      type: 'value', name: '血糖 (mg/dL)',
      nameLocation: 'center', nameGap: 40,
      splitLine: { lineStyle: { type: 'dashed', opacity: 0.3 } }
    },
    series: [{
      type: 'scatter',
      symbolSize: 6,
      data: scatterData,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 1, [
          { offset: 0, color: '#83bff6' },
          { offset: 1, color: '#188df0' }
        ])
      },
      markLine: {
        silent: true,
        data: [
          { yAxis: 126, label: { formatter: '糖尿病阈值 126' }, lineStyle: { color: '#f56c6c', type: 'dashed' } },
          { yAxis: 100, label: { formatter: '空腹偏高 100' }, lineStyle: { color: '#e6a23c', type: 'dashed' } }
        ]
      }
    }],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }]
  })
}

onMounted(loadData)
</script>

<style scoped>
.correlation-page { min-height: 400px; }
.loading-placeholder { display: flex; justify-content: center; align-items: center; min-height: 200px; }
.stats-panel {}
.correlation-gauge { text-align: center; padding: 16px 0; }
.r-value { font-size: 48px; font-weight: 800; }
.r-label { font-size: 14px; color: #909399; margin-top: 4px; }
h4 { margin: 8px 0; font-size: 14px; color: #303133; }
.interpretation { font-size: 13px; color: #606266; line-height: 1.7; }
</style>
