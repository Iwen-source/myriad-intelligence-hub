<template>
  <div class="ml-prediction-panels">
    <!-- 概述 -->
    <el-alert title="基于真实临床数据的AI预测模型" type="info" :closable="false" show-icon style="margin-bottom:16px">
      <template #default>
        糖尿病风险模型基于 <strong>PIMA印第安人糖尿病数据集</strong>（768样本，8特征），使用 <strong>PyTorch DNN（BatchNorm+Dropout）</strong> 训练。
        血糖预测基于 <strong>实时CGM动态血糖监测数据</strong>，使用 <strong>PyTorch BiLSTM + Attention</strong> 时序模型。
      </template>
    </el-alert>

    <el-row :gutter="16">
      <!-- ===== 糖尿病风险评估（完整PIMA特征） ===== -->
      <el-col :span="12">
        <el-card class="diabetes-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><WarningFilled /></el-icon> 糖尿病风险预测（PIMA临床模型）</span>
              <el-tag v-if="diabetesResult?.model_info?.is_real_data" type="success" size="small">真实数据模型</el-tag>
            </div>
          </template>

          <!-- 8个PIMA特征输入 -->
          <el-form :model="form" label-width="110px" size="small">
            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="年龄">
                  <el-input-number v-model="form.age" :min="1" :max="120" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="怀孕次数">
                  <el-input-number v-model="form.pregnancies" :min="0" :max="20" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="血糖 (mg/dL)">
              <el-slider v-model="form.glucose" :min="50" :max="250" :step="1" show-input />
              <div class="field-hint">正常: &lt;100 | 偏高: 100-125 | 高: ≥126</div>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="BMI">
                  <el-input-number v-model="form.bmi" :min="10" :max="60" :step="0.1" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="血压 (mmHg)">
                  <el-input-number v-model="form.bloodPressure" :min="40" :max="200" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="皮褶厚度(mm)">
                  <el-input-number v-model="form.skinThickness" :min="0" :max="100" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="胰岛素水平">
                  <el-input-number v-model="form.insulin" :min="0" :max="1000" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="糖尿病家族史">
              <el-slider v-model="form.diabetesPedigree" :min="0.0" :max="2.5" :step="0.01" show-input />
              <div class="field-hint">0=无, &gt;0.5=中度, &gt;1.0=高度遗传风险</div>
            </el-form-item>

            <el-form-item>
              <el-button type="danger" :loading="loading" @click="predictDiabetes" style="width:100%">
                <el-icon><DataAnalysis /></el-icon> 基于DNN模型评估风险
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 结果展示 -->
          <transition name="el-zoom-in-top">
            <div v-if="diabetesResult" class="result-panel">
              <el-divider />
              <h4>评估结果</h4>

              <!-- 风险概率圆环 -->
              <div class="risk-gauge">
                <div class="gauge-value" :style="{ color: riskColor }">{{ diabetesResult.risk_percentage || 0 }}%</div>
                <div class="gauge-label">
                  <el-tag :type="riskTagType" size="large" effect="dark">
                    {{ diabetesResult.risk_label || '未知' }}
                  </el-tag>
                </div>
              </div>

              <!-- 关键风险因素 -->
              <div v-if="diabetesResult.key_factors?.length" class="key-factors">
                <h5>关键风险因素</h5>
                <div v-for="(f, i) in diabetesResult.key_factors" :key="i" class="factor-item">
                  <el-tag :type="f.risk ? 'danger' : 'info'" size="small" effect="plain">{{ f.factor }}</el-tag>
                  <span class="factor-value">{{ f.value }}</span>
                  <span class="factor-status">{{ f.status }}</span>
                </div>
              </div>

              <!-- 健康建议 -->
              <el-alert v-if="diabetesResult.health_advice" :title="diabetesResult.health_advice"
                :type="riskTagType" :closable="false" show-icon style="margin-top:12px" />

              <!-- 体征状态 -->
              <div v-if="diabetesResult.glucose_status || diabetesResult.bmi_status" class="vital-stats" style="margin-top:12px">
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item v-if="diabetesResult.glucose_status" label="血糖状态">
                    <el-tag :type="diabetesResult.glucose_status === '正常' ? 'success' : 'danger'" size="small">
                      {{ diabetesResult.glucose_status }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item v-if="diabetesResult.bmi_status" label="BMI状态">
                    <el-tag :type="diabetesResult.bmi_status === '正常' ? 'success' : 'warning'" size="small">
                      {{ diabetesResult.bmi_status }}
                    </el-tag>
                  </el-descriptions-item>
                </el-descriptions>
              </div>

              <!-- 模型信息 -->
              <div v-if="diabetesResult.model_info" class="model-info" style="margin-top:8px;font-size:11px;color:#999">
                <p>模型: {{ diabetesResult.model_info.name }} | 训练样本: {{ diabetesResult.model_info.samples }}</p>
              </div>
            </div>
          </transition>
        </el-card>
      </el-col>

      <!-- ===== 血糖预测（时序模型） ===== -->
      <el-col :span="12">
        <el-card class="glucose-card">
          <template #header>
            <div class="card-header">
              <span><el-icon><TrendCharts /></el-icon> 血糖预测（BiLSTM时序模型）</span>
              <el-tag type="success" size="small">CGM真实数据</el-tag>
            </div>
          </template>

          <el-form :model="form" label-width="110px" size="small">
            <el-form-item label="当前血糖">
              <el-slider v-model="form.currentGlucose" :min="2" :max="25" :step="0.1" show-input />
              <div class="field-hint">正常空腹: 3.9-6.1 mmol/L | 餐后: &lt;7.8</div>
            </el-form-item>

            <el-form-item label="餐后时长">
              <el-select v-model="form.postprandialHours" style="width:100%">
                <el-option label="空腹" :value="0" />
                <el-option label="餐后1小时" :value="1" />
                <el-option label="餐后2小时" :value="2" />
                <el-option label="餐后3小时" :value="3" />
              </el-select>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="近3天均值">
                  <el-input-number v-model="form.avgGlucose3d" :min="2" :max="25" :step="0.1" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="HbA1c (%)">
                  <el-input-number v-model="form.hba1c" :min="3" :max="15" :step="0.1" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="预测时长">
              <el-radio-group v-model="form.predictionMinutes">
                <el-radio-button :value="30">30分钟</el-radio-button>
                <el-radio-button :value="60">60分钟</el-radio-button>
                <el-radio-button :value="120">120分钟</el-radio-button>
              </el-radio-group>
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="glucoseLoading" @click="predictGlucose" style="width:100%">
                <el-icon><TrendCharts /></el-icon> 基于BiLSTM预测血糖趋势
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 血糖预测结果 -->
          <transition name="el-zoom-in-top">
            <div v-if="glucoseResult" class="result-panel">
              <el-divider />
              <h4>预测结果</h4>

              <!-- 预测值与当前值对比 -->
              <div class="glucose-compare">
                <div class="compare-item">
                  <div class="compare-label">当前血糖</div>
                  <div class="compare-value" style="color:#909399">{{ glucoseResult.current_glucose || form.currentGlucose }} <small>mmol/L</small></div>
                </div>
                <div class="compare-arrow"><el-icon><ArrowRight /></el-icon></div>
                <div class="compare-item">
                  <div class="compare-label">{{ form.predictionMinutes }}分钟后</div>
                  <div class="compare-value" :style="{ color: forecastColor }">{{ glucoseResult.forecast_glucose || '--' }} <small>mmol/L</small></div>
                </div>
              </div>

              <!-- 趋势描述 -->
              <el-alert v-if="glucoseResult.trend" :title="glucoseResult.trend"
                :type="trendAlertType" :closable="false" show-icon style="margin-top:12px" />

              <!-- 风险预警 -->
              <div v-if="glucoseResult.alerts?.length" style="margin-top:12px">
                <h5>预警提醒</h5>
                <el-tag v-for="(a, i) in glucoseResult.alerts" :key="i" :type="a.type === 'danger' ? 'danger' : 'warning'"
                  size="small" style="margin:2px">{{ a.message }}</el-tag>
              </div>

              <!-- 建议 -->
              <div v-if="glucoseResult.suggestions?.length" style="margin-top:12px">
                <h5>管理建议</h5>
                <ul style="margin:4px 0;padding-left:20px;font-size:13px;color:#606266">
                  <li v-for="(s, i) in glucoseResult.suggestions" :key="i">{{ s }}</li>
                </ul>
              </div>

              <!-- 历史趋势图 -->
              <div v-if="glucoseResult.history" style="margin-top:12px">
                <h5>血糖趋势（近24小时模拟）</h5>
                <div ref="glucoseChartRef" style="width:100%;height:200px" />
              </div>
            </div>
          </transition>
        </el-card>
      </el-col>
    </el-row>

    <!-- 对比说明 -->
    <el-card style="margin-top:16px">
      <template #header><span>📊 数据来源与模型说明</span></template>
      <el-descriptions :column="3" border size="small">
        <el-descriptions-item label="糖尿病风险">
          <el-tag type="success" size="small">PyTorch DNN</el-tag> PIMA印第安人数据集
        </el-descriptions-item>
        <el-descriptions-item label="血糖预测">
          <el-tag type="success" size="small">PyTorch BiLSTM</el-tag> 真实CGM监测数据
        </el-descriptions-item>
        <el-descriptions-item label="模型训练">
          基于真实临床数据训练，非模拟数据
        </el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { WarningFilled, DataAnalysis, TrendCharts, ArrowRight } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { diabetesRiskPredict, glucoseForecastPredict } from '../../api/modules'

// 统一表单（糖尿病 + 血糖所有字段）
const form = ref({
  age: 45, pregnancies: 2,
  glucose: 120, bmi: 27.5, bloodPressure: 80,
  skinThickness: 22, insulin: 85, diabetesPedigree: 0.5,
  currentGlucose: 6.5, postprandialHours: 0, avgGlucose3d: 6.2, hba1c: 6.5,
  predictionMinutes: 30
})

const loading = ref(false)
const glucoseLoading = ref(false)
const diabetesResult = ref(null)
const glucoseResult = ref(null)
const glucoseChartRef = ref(null)
let glucoseChartInstance = null

const riskColor = computed(() => {
  if (!diabetesResult.value) return '#909399'
  const p = diabetesResult.value.risk_percentage || 0
  if (p >= 60) return '#f56c6c'
  if (p >= 30) return '#e6a23c'
  return '#67c23a'
})

const riskTagType = computed(() => {
  if (!diabetesResult.value) return 'info'
  const lv = diabetesResult.value.risk_level
  if (lv === 'high') return 'danger'
  if (lv === 'medium') return 'warning'
  return 'success'
})

const forecastColor = computed(() => {
  if (!glucoseResult.value) return '#409eff'
  const fg = glucoseResult.value.forecast_glucose
  if (!fg) return '#409eff'
  if (fg > 11.1) return '#f56c6c'
  if (fg > 7.8) return '#e6a23c'
  return '#67c23a'
})

const trendAlertType = computed(() => {
  if (!glucoseResult.value) return 'info'
  const trend = glucoseResult.value.trend || ''
  if (trend.includes('上升') || trend.includes('偏高')) return 'warning'
  if (trend.includes('下降') && glucoseResult.value.forecast_glucose < 3.9) return 'danger'
  return 'success'
})

async function predictDiabetes() {
  loading.value = true
  diabetesResult.value = null
  try {
    const payload = {
      pregnancies: form.value.pregnancies,
      glucose: form.value.glucose,
      blood_pressure: form.value.bloodPressure,
      skin_thickness: form.value.skinThickness,
      insulin: form.value.insulin,
      bmi: form.value.bmi,
      diabetes_pedigree: form.value.diabetesPedigree,
      age: form.value.age
    }
    const res = await diabetesRiskPredict(payload)
    diabetesResult.value = res.data || res
  } catch (e) {
    ElMessage.error('预测失败: ' + (e.message || ''))
    diabetesResult.value = { risk_level: 'unknown', risk_label: '未知', risk_percentage: 0 }
  } finally {
    loading.value = false
  }
}

async function predictGlucose() {
  glucoseLoading.value = true
  glucoseResult.value = null
  try {
    const payload = {
      current_glucose: form.value.currentGlucose,
      prediction_minutes: form.value.predictionMinutes,
      postprandial_hours: form.value.postprandialHours,
      avg_glucose_3d: form.value.avgGlucose3d,
      hba1c: form.value.hba1c
    }
    const res = await glucoseForecastPredict(payload)
    glucoseResult.value = res.data || res
    await nextTick()
    renderGlucoseChart()
  } catch (e) {
    ElMessage.error('预测失败: ' + (e.message || ''))
  } finally {
    glucoseLoading.value = false
  }
}

function renderGlucoseChart() {
  if (!glucoseResult.value?.history && glucoseChartRef.value) {
    // 生成模拟历史趋势
    const current = form.value.currentGlucose
    const history = []
    for (let i = 24; i >= 0; i--) {
      const base = current + Math.sin(i * 0.5) * 0.8 + Math.sin(i * 0.2) * 0.3
      history.push({
        time: `${String(Math.floor(i / 2)).padStart(2, '0')}:${i % 2 === 0 ? '00' : '30'}`,
        value: Math.round(base * 10) / 10
      })
    }
    glucoseResult.value.history = history
  }

  if (!glucoseChartRef.value || !glucoseResult.value?.history) return

  if (glucoseChartInstance) glucoseChartInstance.dispose()
  glucoseChartInstance = echarts.init(glucoseChartRef.value)

  const history = glucoseResult.value.history
  glucoseChartInstance.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: history.map(h => h.time), axisLabel: { fontSize: 10 } },
    yAxis: { type: 'value', min: 2, max: 16, splitLine: { lineStyle: { type: 'dashed' } } },
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
      type: 'line', smooth: true,
      data: history.map(h => h.value),
      areaStyle: { opacity: 0.15 },
      markLine: {
        silent: true,
        data: [
          { yAxis: 3.9, label: { formatter: '低血糖线 3.9' }, lineStyle: { color: '#f56c6c', type: 'dashed' } },
          { yAxis: 7.8, label: { formatter: '餐后上限 7.8' }, lineStyle: { color: '#e6a23c', type: 'dashed' } },
          { yAxis: 11.1, label: { formatter: '警报线 11.1' }, lineStyle: { color: '#f56c6c', type: 'dashed' } }
        ]
      }
    }]
  })
}
</script>

<style scoped>
.ml-prediction-panels { max-width: 1200px; margin: 0 auto; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.field-hint { font-size: 11px; color: #909399; margin-top: 2px; }

.diabetes-card, .glucose-card { min-height: 500px; }

.result-panel { margin-top: 8px; }
.result-panel h4 { margin: 0 0 8px; color: #303133; font-size: 14px; }
.result-panel h5 { margin: 0 0 6px; color: #606266; font-size: 13px; }

.risk-gauge { text-align: center; padding: 16px 0; }
.gauge-value { font-size: 48px; font-weight: 800; line-height: 1; }
.gauge-label { margin-top: 8px; }

.key-factors { margin-top: 12px; }
.factor-item { display: flex; align-items: center; gap: 8px; padding: 4px 0; font-size: 13px; }
.factor-value { font-weight: 600; color: #303133; }
.factor-status { color: #909399; font-size: 12px; }

.glucose-compare { display: flex; align-items: center; justify-content: center; gap: 20px; padding: 16px 0; }
.compare-item { text-align: center; }
.compare-label { font-size: 12px; color: #909399; margin-bottom: 4px; }
.compare-value { font-size: 28px; font-weight: 700; }
.compare-value small { font-size: 14px; font-weight: 400; }
.compare-arrow { font-size: 24px; color: #dcdfe6; }

ul { margin: 4px 0; padding-left: 20px; font-size: 13px; color: #606266; }
ul li { margin: 2px 0; }
</style>
