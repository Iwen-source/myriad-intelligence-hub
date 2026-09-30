<template>
  <div class="accident-risk">
    <h2 style="margin-bottom:20px">🚗 交通事故风险预测</h2>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header><span>📋 交通参数</span></template>
          <el-form label-width="110px" size="small">
            <el-form-item label="当前时间">
              <el-select v-model="params.hour" style="width:100%">
                <el-option v-for="h in 24" :key="h-1" :label="`${String(h-1).padStart(2,'0')}:00`" :value="h-1" />
              </el-select>
            </el-form-item>
            <el-form-item label="星期">
              <el-select v-model="params.day_of_week" style="width:100%">
                <el-option :value="0" label="周一" /><el-option :value="1" label="周二" />
                <el-option :value="2" label="周三" /><el-option :value="3" label="周四" />
                <el-option :value="4" label="周五" /><el-option :value="5" label="周六" />
                <el-option :value="6" label="周日" />
              </el-select>
            </el-form-item>
            <el-form-item label="天气">
              <el-select v-model="params.weather_code" style="width:100%">
                <el-option :value="0" label="☀️ 晴朗" /><el-option :value="1" label="⛅ 多云" />
                <el-option :value="2" label="🌧️ 降雨" /><el-option :value="3" label="❄️ 降雪" />
                <el-option :value="4" label="🌫️ 大雾" /><el-option :value="5" label="🌪️ 暴风雨" />
              </el-select>
            </el-form-item>
            <el-form-item label="能见度(km)">
              <el-input-number v-model="params.visibility_km" :min="0.1" :max="50" :step="0.5" style="width:100%" />
            </el-form-item>
            <el-form-item label="车道数">
              <el-input-number v-model="params.lanes" :min="1" :max="8" style="width:100%" />
            </el-form-item>
            <el-form-item label="限速(km/h)">
              <el-select v-model="params.speed_limit" style="width:100%">
                <el-option v-for="s in [30,40,50,60,70,80,100,120]" :key="s" :label="`${s} km/h`" :value="s" />
              </el-select>
            </el-form-item>
            <el-form-item label="路型">
              <el-select v-model="params.road_type" style="width:100%">
                <el-option :value="0" label="高速公路" /><el-option :value="1" label="城市道路" />
                <el-option :value="2" label="乡村道路" /><el-option :value="3" label="住宅区" />
              </el-select>
            </el-form-item>
            <el-form-item label="车流量(辆/h)">
              <el-input-number v-model="params.traffic_volume" :min="10" :max="20000" :step="100" style="width:100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="predict" :loading="loading" style="width:100%">
                🚨 分析事故风险
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header><span>📊 风险评估结果</span></template>
          <div v-if="!result" style="text-align:center;padding:60px 0;color:#999">
            <el-icon :size="48"><Warning /></el-icon>
            <p style="margin-top:12px">输入左侧参数后点击分析</p>
          </div>
          <div v-else>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="gauge-wrap">
                  <el-progress type="dashboard" :percentage="result.risk_score" :color="riskColor" :width="160" />
                  <p style="text-align:center;margin-top:8px;font-weight:bold;font-size:16px">
                    {{ result.risk_level }}
                  </p>
                </div>
              </el-col>
              <el-col :span="16">
                <el-alert :title="result.recommendations" :type="alertType" show-icon :closable="false" style="margin-bottom:16px" />
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="事故概率">{{ (result.risk_probability * 100).toFixed(1) }}%</el-descriptions-item>
                  <el-descriptions-item label="风险评分">{{ result.risk_score }}</el-descriptions-item>
                  <el-descriptions-item label="时段">{{ String(params.hour).padStart(2,'0') }}:00</el-descriptions-item>
                  <el-descriptions-item label="天气代码">{{ weatherLabel }}</el-descriptions-item>
                </el-descriptions>
                <div style="margin-top:12px">
                  <strong>关键风险因素：</strong>
                  <el-tag v-for="f in result.key_risk_factors" :key="f" type="danger" style="margin:4px">{{ f }}</el-tag>
                  <el-tag v-if="!result.key_risk_factors?.length" type="success">无明显风险因素</el-tag>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header><span>📈 典型案例参考</span></template>
          <el-table :data="examples" stripe @row-click="loadExample" style="cursor:pointer">
            <el-table-column prop="label" label="场景" width="120" />
            <el-table-column label="条件" min-width="200">
              <template #default="{row}">
                <el-tag size="small">{{ row.hour }}:00</el-tag>
                <el-tag size="small" :type="row.weather_code>=4?'danger':row.weather_code>=2?'warning':'success'">
                  {{ ['晴朗','多云','降雨','降雪','大雾','暴风雨'][row.weather_code] }}
                </el-tag>
                <el-tag size="small">{{ row.road_type===0?'高速':row.road_type===1?'城市':'乡村' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="预计风险" width="100">
              <template #default="{row}">
                <el-tag :type="row.expected>0.5?'danger':'success'" size="small">
                  {{ row.expected>0.5?'高风险':'低风险' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { predictAccidentRisk } from '@/api/modules/traffic'

const loading = ref(false)
const result = ref(null)

const params = ref({
  hour: new Date().getHours(),
  day_of_week: Math.max(0, new Date().getDay() - 1),
  weather_code: 0,
  visibility_km: 10,
  lanes: 4,
  speed_limit: 60,
  road_type: 1,
  traffic_volume: 1000,
})

const weatherLabel = computed(() => ['晴朗','多云','降雨','降雪','大雾','暴风雨'][params.value.weather_code] || '未知')

const riskColor = computed(() => {
  if (!result.value) return '#409eff'
  const s = result.value.risk_score
  if (s < 20) return '#67c23a'
  if (s < 40) return '#e6a23c'
  if (s < 60) return '#f56c6c'
  return '#f00'
})

const alertType = computed(() => {
  if (!result.value) return 'info'
  const s = result.value.risk_score
  if (s < 20) return 'success'
  if (s < 40) return 'warning'
  return 'error'
})

const examples = [
  { label: '深夜大雾', hour:3, weather_code:4, visibility_km:0.5, road_type:0, lanes:2, speed_limit:80, traffic_volume:500, expected:0.9 },
  { label: '早高峰', hour:8, weather_code:0, visibility_km:15, road_type:1, lanes:4, speed_limit:60, traffic_volume:4000, expected:0.3 },
  { label: '正常午后', hour:14, weather_code:1, visibility_km:10, road_type:1, lanes:3, speed_limit:50, traffic_volume:800, expected:0.05 },
  { label: '暴雨高速', hour:18, weather_code:2, visibility_km:1.5, road_type:0, lanes:3, speed_limit:100, traffic_volume:2500, expected:0.7 },
]

function loadExample(row) {
  params.value.hour = row.hour
  params.value.weather_code = row.weather_code
  params.value.visibility_km = row.visibility_km
  params.value.road_type = row.road_type
  params.value.lanes = row.lanes
  params.value.speed_limit = row.speed_limit
  params.value.traffic_volume = row.traffic_volume
  predict()
}

async function predict() {
  loading.value = true
  try {
    const res = await predictAccidentRisk({ ...params.value })
    result.value = res.data || res
  } catch {
    // Fallback
    const p = params.value
    const night = p.hour >= 22 || p.hour <= 5 ? 1 : 0
    const logOdds = -4.5 + 1.2 * night + 0.6 * (p.weather_code >= 2 ? 1 : 0)
      + 1.5 * (p.weather_code >= 4 ? 1 : 0) + 0.3 * Math.log1p(p.traffic_volume) / 3
      + 0.5 * (p.speed_limit >= 80 ? 1 : 0)
    const prob = Math.min(0.9, Math.max(0.01, 1 / (1 + Math.exp(-logOdds))))
    const score = Math.round(prob * 100)
    result.value = {
      risk_probability: prob,
      risk_score: score,
      risk_level: score < 20 ? '低风险 🟢' : score < 40 ? '中等风险 🟡' : score < 60 ? '高风险 🟠' : '危急 🔴',
      recommendations: score < 20 ? '路况正常' : score < 40 ? '注意观察' : score < 60 ? '建议减速绕行' : '⚠️ 风险极高！',
      key_risk_factors: [night ? '夜间行驶' : '', p.weather_code >= 4 ? '恶劣天气' : p.weather_code >= 2 ? '雨雪天气' : ''].filter(Boolean),
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.accident-risk { padding: 0 4px }
.gauge-wrap { display:flex; flex-direction:column; align-items:center; padding:20px 0 }
</style>
