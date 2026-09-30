<template>
  <div class="extreme-weather">
    <h2 style="margin-bottom:20px">🌤️ 极端天气事件分类</h2>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header><span>📋 环境参数</span></template>
          <el-form label-width="110px" size="small">
            <el-form-item label="PM2.5 (μg/m³)">
              <el-input-number v-model="params.pm25" :min="0" :max="500" style="width:100%" />
            </el-form-item>
            <el-form-item label="PM10 (μg/m³)">
              <el-input-number v-model="params.pm10" :min="0" :max="800" style="width:100%" />
            </el-form-item>
            <el-form-item label="O₃ (μg/m³)">
              <el-input-number v-model="params.o3" :min="0" :max="300" style="width:100%" />
            </el-form-item>
            <el-form-item label="温度 (°C)">
              <el-input-number v-model="params.temperature" :min="-20" :max="45" style="width:100%" />
            </el-form-item>
            <el-form-item label="湿度 (%)">
              <el-input-number v-model="params.humidity" :min="0" :max="100" style="width:100%" />
            </el-form-item>
            <el-form-item label="风速 (m/s)">
              <el-input-number v-model="params.wind_speed" :min="0" :max="30" :step="0.5" style="width:100%" />
            </el-form-item>
            <el-form-item label="季节">
              <el-select v-model="params.season" style="width:100%">
                <el-option :value="0" label="春" /><el-option :value="1" label="夏" />
                <el-option :value="2" label="秋" /><el-option :value="3" label="冬" />
              </el-select>
            </el-form-item>
            <el-form-item label="NO₂ (μg/m³)">
              <el-input-number v-model="params.no2" :min="0" :max="200" style="width:100%" />
            </el-form-item>
            <el-form-item label="SO₂ (μg/m³)">
              <el-input-number v-model="params.so2" :min="0" :max="100" style="width:100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="classify" :loading="loading" style="width:100%">
                🔍 分析天气状况
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header><span>📊 分析结果</span></template>
          <div v-if="!result" style="text-align:center;padding:60px 0;color:#999">
            <el-icon :size="48"><PartlyCloudy /></el-icon>
            <p style="margin-top:12px">输入环境参数后点击分析</p>
          </div>
          <div v-else>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="severity-card" :class="severityClass">
                  <div class="severity-icon">{{ severityIcon }}</div>
                  <div class="severity-label">{{ eventTypeLabel }}</div>
                  <div class="severity-sub">{{ result.severity_level }}</div>
                  <div style="margin-top:8px;font-size:13px">置信度: {{ (result.confidence * 100).toFixed(1) }}%</div>
                </div>
              </el-col>
              <el-col :span="16">
                <el-alert :title="result.advisory || '暂无建议'" :type="advisoryType" show-icon :closable="false" style="margin-bottom:16px" />
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="严重等级">{{ severityLevelLabel }}</el-descriptions-item>
                  <el-descriptions-item label="事件类型">{{ result.event_type || '—' }}</el-descriptions-item>
                  <el-descriptions-item label="PM2.5">{{ params.pm25 }} μg/m³</el-descriptions-item>
                  <el-descriptions-item label="温度">{{ params.temperature }}°C</el-descriptions-item>
                  <el-descriptions-item label="湿度">{{ params.humidity }}%</el-descriptions-item>
                  <el-descriptions-item label="风速">{{ params.wind_speed }} m/s</el-descriptions-item>
                </el-descriptions>
              </el-col>
            </el-row>

            <div style="margin-top:16px">
              <strong>严重等级详情：</strong>
              <el-row :gutter="8" style="margin-top:8px">
                <el-col v-for="lv in levelInfo" :key="lv.key" :span="6">
                  <el-card shadow="hover" :body-style="{padding:'12px'}" style="text-align:center"
                    :class="{ 'active-level': result.severity_level === lv.key }">
                    <div style="font-size:24px;margin-bottom:4px">{{ lv.icon }}</div>
                    <div style="font-size:12px;font-weight:bold">{{ lv.label }}</div>
                    <div style="font-size:11px;color:#999">{{ lv.desc }}</div>
                  </el-card>
                </el-col>
              </el-row>
            </div>
          </div>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header><span>📋 快速场景</span></template>
          <el-row :gutter="12">
            <el-col v-for="(sc, i) in scenarios" :key="i" :span="6">
              <el-card shadow="hover" :body-style="{padding:'12px',cursor:'pointer'}" @click="loadScenario(sc)">
                <div style="font-size:20px;text-align:center">{{ sc.icon }}</div>
                <div style="font-size:12px;text-align:center;margin-top:4px">{{ sc.label }}</div>
              </el-card>
            </el-col>
          </el-row>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { classifyExtremeWeather } from '@/api/modules/environment'

const loading = ref(false)
const result = ref(null)

const params = ref({
  pm25: 35, pm10: 60, o3: 80, no2: 30, so2: 15, co: 1.0,
  temperature: 25, humidity: 60, wind_speed: 5,
  season: new Date().getMonth() < 3 ? 0 : new Date().getMonth() < 6 ? 1 : new Date().getMonth() < 9 ? 2 : 3,
})

const levelInfo = [
  { key: 'normal', icon: '🟢', label: '正常', desc: '适合户外活动' },
  { key: 'advisory', icon: '🟡', label: '关注', desc: '敏感人群注意' },
  { key: 'warning', icon: '🟠', label: '预警', desc: '减少外出' },
  { key: 'emergency', icon: '🔴', label: '警报', desc: '立即防护' },
]

const scenarios = [
  { icon: '☀️', label: '晴朗夏日', pm25: 35, pm10: 60, o3: 120, temperature: 32, humidity: 45, wind_speed: 5, no2: 25, so2: 10, co: 0.8, season: 1 },
  { icon: '🌫️', label: '重度雾霾', pm25: 280, pm10: 350, o3: 50, temperature: 5, humidity: 75, wind_speed: 2, no2: 60, so2: 25, co: 2.5, season: 0 },
  { icon: '🌡️', label: '高温热浪', pm25: 60, pm10: 90, o3: 220, temperature: 39, humidity: 30, wind_speed: 3, no2: 35, so2: 12, co: 1.2, season: 1 },
  { icon: '🌨️', label: '寒潮来袭', pm25: 40, pm10: 70, o3: 40, temperature: -12, humidity: 50, wind_speed: 15, no2: 20, so2: 8, co: 0.6, season: 3 },
]

const severityClass = computed(() => {
  if (!result.value) return ''
  return `severity-${result.value.severity_level}`
})

const severityIcon = computed(() => {
  if (!result.value) return ''
  const icons = { normal: '🟢', advisory: '🟡', warning: '🟠', emergency: '🔴' }
  return icons[result.value.severity_level] || '❓'
})

const eventTypeLabel = computed(() => result.value?.event_type || '—')

const severityLevelLabel = computed(() => {
  if (!result.value) return ''
  const labels = { normal: '正常', advisory: '关注级', warning: '预警级', emergency: '警报级' }
  return labels[result.value.severity_level] || result.value.severity_level
})

const advisoryType = computed(() => {
  if (!result.value) return 'info'
  return result.value.severity_level === 'normal' ? 'success'
    : result.value.severity_level === 'advisory' ? 'warning' : 'error'
})

function loadScenario(sc) {
  Object.assign(params.value, {
    pm25: sc.pm25, pm10: sc.pm10, o3: sc.o3, no2: sc.no2,
    so2: sc.so2, co: sc.co, temperature: sc.temperature,
    humidity: sc.humidity, wind_speed: sc.wind_speed, season: sc.season,
  })
  classify()
}

async function classify() {
  loading.value = true
  try {
    const res = await classifyExtremeWeather({ ...params.value })
    result.value = res.data || res
  } catch {
    // Fallback rule-based
    const p = params.value
    let severity = 'normal'
    if (p.pm25 > 250 || p.temperature > 38) severity = 'warning'
    else if (p.temperature > 35 || p.pm25 > 150) severity = 'advisory'

    const adviceMap = {
      normal: { event: '无异常', text: '天气状况正常，适合户外活动。' },
      advisory: { event: '天气关注', text: '气象条件可能引发轻微环境问题。' },
      warning: { event: '天气预警', text: '⚠️ 极端天气风险较高，注意防护。' },
      emergency: { event: '天气警报', text: '🚨 极端天气事件！立即防护！' },
    }
    const info = adviceMap[severity]
    result.value = {
      severity_level: severity,
      event_type: info.event,
      confidence: 0.65,
      advisory: info.text,
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.extreme-weather { padding: 0 4px }
.severity-card {
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  padding:30px 10px; border-radius:12px; background:#f5f7fa; text-align:center;
  transition: all 0.3s;
}
.severity-normal { background:#f0f9eb; border:2px solid #67c23a }
.severity-advisory { background:#fdf6ec; border:2px solid #e6a23c }
.severity-warning { background:#fef0f0; border:2px solid #f56c6c }
.severity-emergency { background:#fff1f0; border:2px solid #f00; animation:pulse 1.5s infinite }
@keyframes pulse { 0%{box-shadow:0 0 0 0 rgba(255,0,0,0.4)} 50%{box-shadow:0 0 0 10px rgba(255,0,0,0)} }
.severity-icon { font-size:48px; margin-bottom:8px }
.severity-label { font-size:18px; font-weight:bold }
.severity-sub { font-size:13px; color:#666; margin-top:4px }
.active-level { border:2px solid #409eff !important; box-shadow:0 0 8px rgba(64,158,255,0.3) }
</style>
