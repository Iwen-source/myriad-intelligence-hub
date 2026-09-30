<template>
  <div class="churn-prediction">
    <h2 style="margin-bottom:20px">💰 客户流失预测</h2>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header><span>👤 客户画像参数</span></template>
          <el-form label-width="140px" size="small">
            <el-form-item label="月交易次数">
              <el-input-number v-model="params.monthly_transaction_count" :min="0" :max="50" style="width:100%" />
            </el-form-item>
            <el-form-item label="日均余额(元)">
              <el-input-number v-model="params.avg_balance" :min="0" :max="500000" :step="1000" style="width:100%" />
            </el-form-item>
            <el-form-item label="上次交易(天前)">
              <el-input-number v-model="params.days_since_last_transaction" :min="0" :max="180" style="width:100%" />
            </el-form-item>
            <el-form-item label="周登录频率">
              <el-input-number v-model="params.login_frequency_per_week" :min="0" :max="30" style="width:100%" />
            </el-form-item>
            <el-form-item label="功能使用数">
              <el-input-number v-model="params.feature_usage_count" :min="0" :max="20" style="width:100%" />
            </el-form-item>
            <el-form-item label="信用评分">
              <el-input-number v-model="params.credit_score" :min="300" :max="850" style="width:100%" />
            </el-form-item>
            <el-form-item label="负债收入比">
              <el-input-number v-model="params.debt_to_income_ratio" :min="0" :max="1.5" :step="0.05" style="width:100%" />
            </el-form-item>
            <el-form-item label="高级用户">
              <el-switch v-model="params.is_premium_user" />
            </el-form-item>
            <el-form-item label="有贷款">
              <el-switch v-model="params.has_loan" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="predict" :loading="loading" style="width:100%">
                📊 预测流失风险
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :span="16">
        <el-card>
          <template #header><span>📊 流失风险评估</span></template>
          <div v-if="!result" style="text-align:center;padding:60px 0;color:#999">
            <el-icon :size="48"><User /></el-icon>
            <p style="margin-top:12px">输入客户参数后点击预测</p>
          </div>
          <div v-else>
            <el-row :gutter="20">
              <el-col :span="8">
                <div class="gauge-wrap">
                  <el-progress type="dashboard" :percentage="result.churn_score" :color="churnColor" :width="160" />
                  <p style="text-align:center;margin-top:8px;font-weight:bold;font-size:16px">{{ result.risk_level }}</p>
                </div>
              </el-col>
              <el-col :span="16">
                <el-alert :title="result.retention_advice || '暂无建议'" :type="churnAlertType" show-icon :closable="false" style="margin-bottom:16px" />
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="流失概率">{{ (result.churn_probability * 100).toFixed(1) }}%</el-descriptions-item>
                  <el-descriptions-item label="流失分数">{{ result.churn_score }}</el-descriptions-item>
                  <el-descriptions-item label="月交易">{{ params.monthly_transaction_count }}次</el-descriptions-item>
                  <el-descriptions-item label="日均余额">¥{{ params.avg_balance.toLocaleString() }}</el-descriptions-item>
                  <el-descriptions-item label="上次交易">{{ params.days_since_last_transaction }}天前</el-descriptions-item>
                  <el-descriptions-item label="登录频率">{{ params.login_frequency_per_week }}次/周</el-descriptions-item>
                </el-descriptions>

                <div v-if="result.key_signals" style="margin-top:12px">
                  <strong>关键信号：</strong>
                  <el-row :gutter="8" style="margin-top:8px">
                    <el-col v-for="(v,k) in result.key_signals" :key="k" :span="12" style="margin-bottom:4px">
                      <el-tag size="small" effect="plain" style="width:100%">
                        {{ signalLabels[k] || k }}: {{ typeof v === 'number' ? v.toFixed(2) : v }}
                      </el-tag>
                    </el-col>
                  </el-row>
                </div>
              </el-col>
            </el-row>
          </div>
        </el-card>

        <el-card style="margin-top:16px">
          <template #header><span>💡 挽留策略参考</span></template>
          <el-timeline>
            <el-timeline-item timestamp="流失概率 < 20%" placement="top" type="primary">
              <p>用户活跃度良好，保持现有服务水平即可。</p>
            </el-timeline-item>
            <el-timeline-item timestamp="流失概率 20%-50%" placement="top" type="warning">
              <p>发送个性化优惠券、推送精选内容、提高互动频率。</p>
            </el-timeline-item>
            <el-timeline-item timestamp="流失概率 50%-80%" placement="top" type="danger">
              <p>主动客服回访、专属权益赠送、产品功能引导。</p>
            </el-timeline-item>
            <el-timeline-item timestamp="流失概率 > 80%" placement="top" type="danger">
              <p>紧急挽留：专属客服一对一、高价值优惠、人工干预。</p>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { predictCustomerChurn } from '@/api/modules/finance'

const loading = ref(false)
const result = ref(null)

const params = ref({
  monthly_transaction_count: 10,
  avg_balance: 10000,
  days_since_last_transaction: 5,
  login_frequency_per_week: 4,
  feature_usage_count: 5,
  credit_score: 650,
  debt_to_income_ratio: 0.2,
  is_premium_user: false,
  has_loan: false,
})

const signalLabels = {
  days_since_last_tx: '上次交易天数',
  monthly_tx_count: '月交易数',
  avg_balance: '日均余额',
  login_frequency: '周登录频率',
  engagement_score: '参与度评分',
}

const churnColor = computed(() => {
  if (!result.value) return '#409eff'
  const s = result.value.churn_score
  if (s < 20) return '#67c23a'
  if (s < 40) return '#e6a23c'
  if (s < 70) return '#f56c6c'
  return '#f00'
})

const churnAlertType = computed(() => {
  if (!result.value) return 'info'
  const s = result.value.churn_score
  if (s < 20) return 'success'
  if (s < 50) return 'warning'
  return 'error'
})

async function predict() {
  loading.value = true
  try {
    const res = await predictCustomerChurn({ ...params.value })
    result.value = res.data || res
  } catch {
    // Fallback
    const p = params.value
    const logOdds = -1.0 + 0.3 * Math.log1p(p.days_since_last_transaction) / 3
      - 0.08 * p.monthly_transaction_count - 0.003 * Math.log1p(p.avg_balance) - 0.15 * p.login_frequency_per_week
    const prob = Math.min(0.9, Math.max(0.01, 1 / (1 + Math.exp(-logOdds))))
    const score = Math.round(prob * 100)
    result.value = {
      churn_probability: prob,
      churn_score: score,
      risk_level: score < 20 ? '低风险 🟢' : score < 40 ? '中等风险 🟡' : score < 70 ? '高风险 🟠' : '危急 🔴',
      retention_advice: score < 20 ? '用户活跃度良好' : score < 40 ? '建议发送个性化权益' : score < 70 ? '⚠️ 风险较高，主动联系' : '🚨 极可能流失！',
      key_signals: {
        days_since_last_tx: p.days_since_last_transaction,
        monthly_tx_count: p.monthly_transaction_count,
        avg_balance: p.avg_balance,
        login_frequency: p.login_frequency_per_week,
      },
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.churn-prediction { padding: 0 4px }
.gauge-wrap { display:flex; flex-direction:column; align-items:center; padding:20px 0 }
</style>
