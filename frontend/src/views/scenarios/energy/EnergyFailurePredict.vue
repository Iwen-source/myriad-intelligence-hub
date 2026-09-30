<template>
  <div class="energy-failure-predict">
    <el-card shadow="hover" class="tab-card">
      <template #header>
        <div class="flex-between">
          <span class="card-title">🔧 设备故障预测</span>
          <el-button type="primary" :icon="TrendCharts" :loading="loading" @click="submitPredict">
            开始预测
          </el-button>
        </div>
      </template>

      <el-row :gutter="24">
        <!-- 左侧：参数输入表单 -->
        <el-col :span="14">
          <el-card shadow="never" class="form-card">
            <template #header>
              <span class="chart-title">📝 设备运行参数</span>
            </template>

            <el-form :model="form" label-width="180px" label-position="left" class="predict-form">
              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="设备使用年限 (年)">
                    <el-input-number v-model="form.device_age_years" :min="0" :max="50" :step="1" style="width:100%" placeholder="0-50" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="累计运行时间 (小时)">
                    <el-input-number v-model="form.operating_hours" :min="0" :max="100000" :step="100" style="width:100%" placeholder="0-100000" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="平均温度 (℃)">
                    <el-input-number v-model="form.avg_temperature_c" :min="-20" :max="150" :step="1" :precision="1" style="width:100%" placeholder="-20~150" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="最高温度 (℃)">
                    <el-input-number v-model="form.max_temperature_c" :min="-20" :max="200" :step="1" :precision="1" style="width:100%" placeholder="-20~200" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="振动水平 (mm/s)">
                    <el-input-number v-model="form.vibration_level" :min="0" :max="100" :step="0.5" :precision="1" style="width:100%" placeholder="0~100" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="维护频率 (次/年)">
                    <el-input-number v-model="form.maintenance_frequency" :min="0" :max="365" :step="1" style="width:100%" placeholder="0~365" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-row :gutter="16">
                <el-col :span="12">
                  <el-form-item label="距上次维护天数">
                    <el-input-number v-model="form.days_since_last_maintenance" :min="0" :max="3650" :step="1" style="width:100%" placeholder="0~3650" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <el-form-item label="电压稳定性 (0-1)">
                    <el-input-number v-model="form.voltage_stability" :min="0" :max="1" :step="0.05" :precision="2" style="width:100%" placeholder="0~1" />
                  </el-form-item>
                </el-col>
              </el-row>

              <el-form-item style="margin-top:16px">
                <el-button type="primary" :icon="TrendCharts" :loading="loading" size="large" @click="submitPredict">
                  开始预测
                </el-button>
                <el-button :icon="Refresh" size="large" @click="resetForm">重置参数</el-button>
              </el-form-item>
            </el-form>
          </el-card>
        </el-col>

        <!-- 右侧：预测结果 -->
        <el-col :span="10">
          <el-card shadow="never" class="result-card">
            <template #header>
              <span class="chart-title">🎯 预测结果</span>
            </template>

            <!-- 无结果时 -->
            <el-empty v-if="!hasResult" description='请输入参数并点击"开始预测"' :image-size="100">
              <template #image>
                <div class="empty-icon">🔍</div>
              </template>
            </el-empty>

            <!-- 有结果时 -->
            <div v-else class="result-body">
              <!-- 故障概率仪表盘 -->
              <div class="gauge-section">
                <div ref="gaugeChartRef" style="height:220px;width:100%"></div>
              </div>

              <!-- 风险等级标签 -->
              <div class="risk-badge-section" style="text-align:center;margin-top:8px">
                <el-tag :type="riskTagType" effect="dark" size="large" class="risk-tag">
                  {{ riskLabel }}
                </el-tag>
              </div>

              <!-- 关键因子 -->
              <el-card shadow="never" class="inner-card" style="margin-top:16px">
                <template #header>
                  <span class="inner-card-title">🔑 关键影响因素</span>
                </template>
                <div v-if="keyFactors.length > 0" class="factors-list">
                  <div v-for="(factor, idx) in keyFactors" :key="idx" class="factor-item">
                    <el-tag :type="factor.impact === 'positive' ? 'danger' : 'success'" effect="plain" size="small" class="factor-tag">
                      {{ factor.impact === 'positive' ? '⚠️' : '✅' }}
                    </el-tag>
                    <span class="factor-name">{{ factor.name }}</span>
                    <span class="factor-value" :class="{ 'high': factor.impact === 'positive' }">{{ factor.value }}</span>
                  </div>
                </div>
                <el-empty v-else description="无法分析关键因子" :image-size="80" />
              </el-card>

              <!-- 维护建议 -->
              <el-card shadow="never" class="inner-card" style="margin-top:12px">
                <template #header>
                  <span class="inner-card-title">💡 维护建议</span>
                </template>
                <p class="recommendation-text">{{ recommendation }}</p>
              </el-card>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { TrendCharts, Refresh } from '@element-plus/icons-vue'
import { predictDeviceFailure } from '@/api/modules/energy'

const loading = ref(false)
const hasResult = ref(false)
let gaugeChart = null
const gaugeChartRef = ref(null)

// 表单数据
const form = ref({
  device_age_years: 5,
  operating_hours: 12000,
  avg_temperature_c: 45,
  max_temperature_c: 72,
  vibration_level: 6.5,
  maintenance_frequency: 3,
  days_since_last_maintenance: 180,
  voltage_stability: 0.85
})

// 预测结果
const failureProbability = ref(0)
const riskLabel = ref('')
const riskTagType = ref('success')
const keyFactors = ref([])
const recommendation = ref('')

// 基本 logit 计算本地回退
function computeLogitProbability(params) {
  // 各参数权重系数 (模拟 XGBoost 特征重要性)
  const w = {
    device_age_years: 0.25,
    operating_hours: 0.18,
    avg_temperature_c: 0.10,
    max_temperature_c: 0.12,
    vibration_level: 0.15,
    maintenance_frequency: -0.12,
    days_since_last_maintenance: 0.20,
    voltage_stability: -0.30
  }

  // 归一化各特征到 0~1 范围
  const norm = {
    device_age_years: Math.min(params.device_age_years / 30, 1),
    operating_hours: Math.min(params.operating_hours / 80000, 1),
    avg_temperature_c: Math.min(params.avg_temperature_c / 100, 1),
    max_temperature_c: Math.min(params.max_temperature_c / 150, 1),
    vibration_level: Math.min(params.vibration_level / 50, 1),
    maintenance_frequency: Math.min(params.maintenance_frequency / 52, 1),
    days_since_last_maintenance: Math.min(params.days_since_last_maintenance / 730, 1),
    voltage_stability: 1 - params.voltage_stability  // 越低稳定性越危险
  }

  // 线性组合
  let logit = -2.5  // 截距
  for (const key of Object.keys(w)) {
    logit += w[key] * norm[key]
  }

  // sigmoid 映射到 0~1
  const prob = 1 / (1 + Math.exp(-logit))
  return Math.round(Math.min(1, Math.max(0, prob)) * 100)
}

// 计算关键影响因子
function computeKeyFactors(params, prob) {
  const thresholds = {
    device_age_years: { name: '使用年限', threshold: 10, unit: '年' },
    operating_hours: { name: '运行时长', threshold: 30000, unit: '小时' },
    max_temperature_c: { name: '最高温度', threshold: 80, unit: '℃' },
    vibration_level: { name: '振动水平', threshold: 15, unit: 'mm/s' },
    days_since_last_maintenance: { name: '距上次维护', threshold: 365, unit: '天' },
    voltage_stability: { name: '电压稳定性', threshold: 0.7, unit: '' },
    maintenance_frequency: { name: '维护频率', threshold: 2, unit: '次/年' },
    avg_temperature_c: { name: '平均温度', threshold: 60, unit: '℃' }
  }

  const factors = []
  // 高风险因子
  if (params.device_age_years > thresholds.device_age_years.threshold) {
    factors.push({ name: '设备已老化', value: `${params.device_age_years}年`, impact: 'positive' })
  }
  if (params.operating_hours > thresholds.operating_hours.threshold) {
    factors.push({ name: '运行时间过长', value: `${params.operating_hours}小时`, impact: 'positive' })
  }
  if (params.max_temperature_c > thresholds.max_temperature_c.threshold) {
    factors.push({ name: '最高温度过高', value: `${params.max_temperature_c}℃`, impact: 'positive' })
  }
  if (params.vibration_level > thresholds.vibration_level.threshold) {
    factors.push({ name: '振动异常', value: `${params.vibration_level}mm/s`, impact: 'positive' })
  }
  if (params.days_since_last_maintenance > thresholds.days_since_last_maintenance.threshold) {
    factors.push({ name: '长期未维护', value: `${params.days_since_last_maintenance}天`, impact: 'positive' })
  }
  if (params.voltage_stability < thresholds.voltage_stability.threshold) {
    factors.push({ name: '电压不稳定', value: `${params.voltage_stability}`, impact: 'positive' })
  }

  // 低风险因子 (良好指标)
  if (params.maintenance_frequency >= thresholds.maintenance_frequency.threshold) {
    factors.push({ name: '维护频率充足', value: `${params.maintenance_frequency}次/年`, impact: 'negative' })
  }
  if (params.device_age_years <= 3) {
    factors.push({ name: '设备较新', value: `${params.device_age_years}年`, impact: 'negative' })
  }
  if (params.avg_temperature_c <= 40) {
    factors.push({ name: '运行温控良好', value: `${params.avg_temperature_c}℃`, impact: 'negative' })
  }

  // 如果因子太少，补充通用分析
  if (factors.length === 0) {
    factors.push({ name: '各项参数正常', value: '—', impact: 'negative' })
  }
  if (prob > 60) {
    factors.push({ name: '综合风险偏高', value: `${prob}%`, impact: 'positive' })
  }

  return factors.slice(0, 6)
}

// 根据概率生成维护建议
function generateRecommendation(prob, params) {
  if (prob >= 80) {
    return `🚨 设备故障风险极高 (${prob}%)！建议立即停机检修，更换关键部件。重点关注温度管理和振动异常，同时检查电压稳定性。建议安排全面检测。`
  } else if (prob >= 60) {
    return `⚠️ 设备故障风险较高 (${prob}%)。建议在 ${Math.max(7, Math.round(params.days_since_last_maintenance * 0.1))} 天内安排预防性维护。重点关注${params.max_temperature_c > 75 ? '温度控制' : ''}${params.vibration_level > 12 ? '、减振措施' : ''}${params.voltage_stability < 0.75 ? '、电压调节' : ''}。`
  } else if (prob >= 30) {
    return `📋 设备状态一般 (${prob}%)。建议按计划进行常规维护，${params.days_since_last_maintenance > 200 ? '近期安排一次全面巡检' : '保持当前维护节奏'}。无需紧急干预。`
  } else {
    return `✅ 设备状态良好 (${prob}%)。当前各项参数在安全范围内，请保持定期维护。建议记录运行数据作为基准参考。`
  }
}

// 获取风险标签
function getRiskInfo(prob) {
  if (prob >= 80) return { label: '🔴 极高风险', type: 'danger' }
  if (prob >= 60) return { label: '🟠 较高风险', type: 'warning' }
  if (prob >= 30) return { label: '🟡 中等风险', type: 'primary' }
  return { label: '🟢 低风险', type: 'success' }
}

function initGaugeChart(prob) {
  if (gaugeChart) { gaugeChart.dispose(); gaugeChart = null }
  if (!gaugeChartRef.value) return

  gaugeChart = echarts.init(gaugeChartRef.value)

  // 计算颜色
  let color
  if (prob >= 80) color = '#f56c6c'
  else if (prob >= 60) color = '#e6a23c'
  else if (prob >= 30) color = '#409eff'
  else color = '#67c23a'

  gaugeChart.setOption({
    series: [{
      type: 'gauge',
      startAngle: 200,
      endAngle: -20,
      min: 0,
      max: 100,
      splitNumber: 5,
      progress: {
        show: true,
        width: 12,
        itemStyle: { color }
      },
      axisLine: {
        lineStyle: {
          width: 12,
          color: [
            [0.3, '#67c23a'],
            [0.6, '#409eff'],
            [0.8, '#e6a23c'],
            [1, '#f56c6c']
          ]
        }
      },
      axisTick: {
        show: false
      },
      splitLine: {
        length: 8,
        lineStyle: { width: 2, color: '#999' }
      },
      axisLabel: {
        distance: 16,
        color: '#999',
        fontSize: 11
      },
      pointer: {
        show: true,
        length: '60%',
        width: 4,
        itemStyle: { color }
      },
      detail: {
        valueAnimation: true,
        formatter: '{value}%',
        color: color,
        fontSize: 28,
        fontWeight: 'bold',
        offsetCenter: [0, '40%']
      },
      title: {
        offsetCenter: [0, '70%'],
        fontSize: 13,
        color: '#909399'
      },
      data: [{ value: prob, name: '故障概率' }]
    }]
  })
}

async function submitPredict() {
  loading.value = true
  try {
    const payload = {
      device_age_years: form.value.device_age_years,
      operating_hours: form.value.operating_hours,
      avg_temperature_c: form.value.avg_temperature_c,
      max_temperature_c: form.value.max_temperature_c,
      vibration_level: form.value.vibration_level,
      maintenance_frequency: form.value.maintenance_frequency,
      days_since_last_maintenance: form.value.days_since_last_maintenance,
      voltage_stability: form.value.voltage_stability
    }

    const res = await predictDeviceFailure(payload)
    const data = res.data || {}

    failureProbability.value = data.failure_probability != null
      ? Math.round(data.failure_probability * 100)
      : computeLogitProbability(payload)

    keyFactors.value = data.key_factors || computeKeyFactors(payload, failureProbability.value)
    recommendation.value = data.recommendations || generateRecommendation(failureProbability.value, payload)
  } catch (err) {
    ElMessage.warning('API 请求失败，使用本地模型计算')
    // 本地回退
    failureProbability.value = computeLogitProbability(form.value)
    keyFactors.value = computeKeyFactors(form.value, failureProbability.value)
    recommendation.value = generateRecommendation(failureProbability.value, form.value)
  } finally {
    loading.value = false
    hasResult.value = true
    await nextTick()

    const riskInfo = getRiskInfo(failureProbability.value)
    riskLabel.value = riskInfo.label
    riskTagType.value = riskInfo.type

    initGaugeChart(Math.min(100, Math.max(0, failureProbability.value)))
  }
}

function resetForm() {
  form.value = {
    device_age_years: 5,
    operating_hours: 12000,
    avg_temperature_c: 45,
    max_temperature_c: 72,
    vibration_level: 6.5,
    maintenance_frequency: 3,
    days_since_last_maintenance: 180,
    voltage_stability: 0.85
  }
  ElMessage.info('参数已重置为默认值')
}

function resizeChart() {
  if (gaugeChart) gaugeChart.resize()
}

onMounted(() => {
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  window.removeEventListener('resize', resizeChart)
  if (gaugeChart) gaugeChart.dispose()
})
</script>

<style scoped>
.tab-card { border-radius: 12px; transition: all 0.3s ease; }
.tab-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.08); }
.card-title { font-size: 16px; font-weight: 600; background: linear-gradient(135deg,#409eff,#67c23a); -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
.flex-between { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.form-card { border-radius: 10px; border: 1px solid #e8e8e8; }
.result-card { border-radius: 10px; border: 1px solid #e8e8e8; min-height: 400px; }
.chart-title { font-size: 14px; font-weight: 600; color: #303133; }
.inner-card { border-radius: 8px; border: 1px solid #f0f0f0; }
.inner-card-title { font-size: 13px; font-weight: 600; color: #606266; }
.predict-form .el-form-item { margin-bottom: 18px; }
.result-body { padding: 0 4px; }
.gauge-section { text-align: center; }
.risk-tag { font-size: 15px; padding: 8px 20px; border-radius: 8px; }
.empty-icon { font-size: 60px; line-height: 1; margin-bottom: 8px; }
.factors-list { display: flex; flex-direction: column; gap: 8px; }
.factor-item { display: flex; align-items: center; gap: 8px; padding: 6px 8px; border-radius: 6px; background: #fafafa; }
.factor-tag { min-width: 36px; text-align: center; }
.factor-name { font-size: 13px; color: #303133; flex: 1; }
.factor-value { font-size: 13px; font-weight: 600; color: #67c23a; }
.factor-value.high { color: #f56c6c; }
.recommendation-text { font-size: 13px; line-height: 1.8; color: #606266; margin: 0; padding: 4px 0; white-space: pre-wrap; }
</style>
