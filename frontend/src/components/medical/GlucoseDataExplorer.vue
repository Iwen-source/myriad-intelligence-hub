<template>
  <div class="glucose-explorer">
    <el-alert title="9位真实患者的CGM动态血糖监测数据" type="warning" :closable="false" show-icon style="margin-bottom:16px">
      <template #default>
        来自真实临床血糖监测，每位患者的血糖时间序列包含多次测量读数。
        点击患者查看完整血糖趋势图和统计分析。
      </template>
    </el-alert>

    <el-row :gutter="16">
      <!-- 左侧：患者列表 -->
      <el-col :span="6">
        <el-card>
          <template #header><span>👥 患者列表</span></template>
          <div v-if="loadingPatients" class="loading-placeholder"><el-icon class="is-loading" :size="24"><Loading /></el-icon></div>
          <div v-else>
            <div
              v-for="p in patients"
              :key="p.id"
              class="patient-card"
              :class="{ active: selectedPatient === p.id }"
              @click="selectPatient(p.id)"
            >
              <div class="patient-id">患者 {{ p.id }}</div>
              <div class="patient-stats">
                <span>均值: {{ p.mean_glucose }}</span>
                <span>样本: {{ p.samples }}</span>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：血糖趋势 -->
      <el-col :span="18">
        <el-card v-if="!selectedPatient">
          <el-empty description="左侧选择患者查看详细血糖数据" />
        </el-card>

        <template v-else>
          <el-card class="detail-card">
            <template #header>
              <div class="flex-between">
                <span><el-icon><TrendCharts /></el-icon> 患者 {{ selectedPatient }} 血糖趋势</span>
                <div>
                  <el-tag type="success" size="small">均值: {{ patientDetail?.stats?.mean }}</el-tag>
                  <el-tag type="danger" size="small" style="margin-left:4px">最高: {{ patientDetail?.stats?.max }}</el-tag>
                  <el-tag type="info" size="small" style="margin-left:4px">最低: {{ patientDetail?.stats?.min }}</el-tag>
                </div>
              </div>
            </template>

            <div v-if="loadingDetail" class="loading-placeholder"><el-icon class="is-loading" :size="32"><Loading /></el-icon></div>
            <div v-else-if="patientDetail">
              <div ref="glucoseChartRef" style="width:100%;height:400px"></div>

              <el-divider />
              <el-row :gutter="12">
                <el-col :span="8">
                  <el-descriptions :column="1" border size="small" title="📊 统计">
                    <el-descriptions-item label="样本数">{{ patientDetail.stats?.count }}</el-descriptions-item>
                    <el-descriptions-item label="均值±SD">{{ patientDetail.stats?.mean }} ± {{ patientDetail.stats?.std }}</el-descriptions-item>
                    <el-descriptions-item label="中位数">{{ patientDetail.stats?.median }}</el-descriptions-item>
                  </el-descriptions>
                </el-col>
                <el-col :span="8">
                  <el-descriptions :column="1" border size="small" title="📈 范围">
                    <el-descriptions-item label="最低值">{{ patientDetail.stats?.min }}</el-descriptions-item>
                    <el-descriptions-item label="最高值">{{ patientDetail.stats?.max }}</el-descriptions-item>
                    <el-descriptions-item label="波动范围">{{ (patientDetail.stats?.max - patientDetail.stats?.min)?.toFixed(1) }}</el-descriptions-item>
                  </el-descriptions>
                </el-col>
                <el-col :span="8">
                  <el-descriptions :column="1" border size="small" title="⚠️ 风险评估">
                    <el-descriptions-item label="血糖变异系数(CV%)">
                      {{ patientDetail.stats?.std && patientDetail.stats?.mean ? ((patientDetail.stats.std / patientDetail.stats.mean) * 100).toFixed(1) : '--' }}%
                    </el-descriptions-item>
                    <el-descriptions-item label="高低血糖风险">
                      <el-tag :type="riskType" size="small">{{ riskLabel }}</el-tag>
                    </el-descriptions-item>
                  </el-descriptions>
                </el-col>
              </el-row>
            </div>
          </el-card>
        </template>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Loading, TrendCharts } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { getGlucosePatients, getGlucosePatientDetail } from '../../api/modules'

const patients = ref([])
const selectedPatient = ref(null)
const loadingPatients = ref(true)
const loadingDetail = ref(false)
const patientDetail = ref(null)
const glucoseChartRef = ref(null)
let chartInstance = null

const riskType = computed(() => {
  if (!patientDetail.value?.stats) return 'info'
  const cv = (patientDetail.value.stats.std / patientDetail.value.stats.mean) * 100
  if (cv > 36) return 'danger'
  if (cv > 25) return 'warning'
  return 'success'
})

const riskLabel = computed(() => {
  if (!patientDetail.value?.stats) return '--'
  const cv = (patientDetail.value.stats.std / patientDetail.value.stats.mean) * 100
  if (cv > 36) return '高变异 (高风险)'
  if (cv > 25) return '中等变异'
  return '低变异 (稳定)'
})

async function loadPatients() {
  loadingPatients.value = true
  try {
    const res = await getGlucosePatients()
    patients.value = res.data?.patients || res?.patients || []
  } catch (e) {
    ElMessage.error('获取患者列表失败: ' + (e.message || ''))
  } finally {
    loadingPatients.value = false
  }
}

async function selectPatient(id) {
  selectedPatient.value = id
  loadingDetail.value = true
  patientDetail.value = null
  try {
    const res = await getGlucosePatientDetail(id)
    patientDetail.value = res.data || res
    await nextTick()
    renderChart()
  } catch (e) {
    ElMessage.error('获取患者数据失败: ' + (e.message || ''))
  } finally {
    loadingDetail.value = false
  }
}

function renderChart() {
  if (!glucoseChartRef.value || !patientDetail.value?.readings) return
  if (chartInstance) chartInstance.dispose()
  chartInstance = echarts.init(glucoseChartRef.value)

  const readings = patientDetail.value.readings
  const times = readings.map(r => r.time)
  const values = readings.map(r => r.value)

  chartInstance.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        return `时间: ${p.axisValue}<br/>血糖: ${p.value} mmol/L`
      }
    },
    grid: { left: '5%', right: '5%', bottom: '8%', top: '5%' },
    xAxis: {
      type: 'category',
      data: times,
      axisLabel: { rotate: 45, fontSize: 10, interval: 'auto' }
    },
    yAxis: {
      type: 'value',
      name: '血糖 (mmol/L)',
      min: 0,
      max: 20,
      splitLine: { lineStyle: { type: 'dashed' } }
    },
    visualMap: {
      top: 10, right: 10, pieces: [
        { gt: 0, lte: 3.9, color: '#f56c6c' },
        { gt: 3.9, lte: 7.8, color: '#67c23a' },
        { gt: 7.8, lte: 11.1, color: '#e6a23c' },
        { gt: 11.1, color: '#f56c6c' }
      ],
      outOfRange: { color: '#999' }
    },
    series: [{
      type: 'line',
      smooth: true,
      data: values,
      areaStyle: { opacity: 0.1, color: '#409eff' },
      markLine: {
        silent: true,
        data: [
          { yAxis: 3.9, label: { formatter: '低血糖 3.9' }, lineStyle: { color: '#f56c6c', type: 'dashed' } },
          { yAxis: 7.8, label: { formatter: '餐后上限 7.8' }, lineStyle: { color: '#e6a23c', type: 'dashed' } },
          { yAxis: 11.1, label: { formatter: '高血糖 11.1' }, lineStyle: { color: '#f56c6c', type: 'dashed' } }
        ]
      },
      markArea: {
        silent: true,
        data: [
          [{ yAxis: 3.9, itemStyle: { color: 'rgba(245,108,108,0.05)' } }, { yAxis: 0 }],
          [{ yAxis: 7.8, itemStyle: { color: 'rgba(230,162,60,0.05)' } }, { yAxis: 11.1 }],
          [{ yAxis: 11.1, itemStyle: { color: 'rgba(245,108,108,0.05)' } }, { yAxis: 20 }]
        ]
      }
    }],
    dataZoom: [{ type: 'inside' }, { type: 'slider' }]
  })
}

onMounted(loadPatients)
</script>

<style scoped>
.glucose-explorer { min-height: 400px; }
.loading-placeholder { display: flex; justify-content: center; align-items: center; min-height: 200px; }
.patient-card {
  padding: 10px 12px;
  margin-bottom: 6px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #e4e7ed;
}
.patient-card:hover, .patient-card.active {
  border-color: #409eff;
  background: #ecf5ff;
}
.patient-id { font-weight: 600; font-size: 14px; color: #303133; }
.patient-stats { display: flex; gap: 12px; font-size: 12px; color: #909399; margin-top: 4px; }
.detail-card { margin-top: 0; }
.flex-between { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
</style>
