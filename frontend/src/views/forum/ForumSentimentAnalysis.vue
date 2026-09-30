<template>
  <div class="sentiment-page">
    <!-- ── Header ── -->
    <div class="page-header">
      <div class="header-left">
        <h2>💬 用户情感分析</h2>
        <span class="header-subtitle">批量分析用户评论情感倾向</span>
      </div>
    </div>

    <!-- ═══ Summary Cards ═══ -->
    <div v-if="summary.total > 0" class="summary-section">
      <el-row :gutter="16">
        <el-col :xs="12" :sm="6">
          <div class="summary-card total">
            <div class="summary-icon">📊</div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.total }}</div>
              <div class="summary-label">总条数</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-card positive">
            <div class="summary-icon">😊</div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.positive }}</div>
              <div class="summary-label">积极</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-card negative">
            <div class="summary-icon">😞</div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.negative }}</div>
              <div class="summary-label">消极</div>
            </div>
          </div>
        </el-col>
        <el-col :xs="12" :sm="6">
          <div class="summary-card neutral">
            <div class="summary-icon">😐</div>
            <div class="summary-info">
              <div class="summary-value">{{ summary.neutral }}</div>
              <div class="summary-label">中性</div>
            </div>
          </div>
        </el-col>
      </el-row>
      <div v-if="summary.total > 0" class="overall-tag">
        总体情感: <el-tag :type="overallType" size="large" effect="dark">{{ overallLabel }}</el-tag>
      </div>
    </div>

    <!-- ═══ Input Section ═══ -->
    <div class="input-section">
      <div class="section-title">
        <h3>✍️ 输入待分析文本</h3>
        <el-tag type="info" effect="plain">每行一条，支持批量粘贴</el-tag>
      </div>
      <el-input
        v-model="inputText"
        type="textarea"
        :rows="8"
        placeholder="请在此输入待分析的文本，每行一条...&#10;&#10;示例：&#10;这个功能真的太棒了，使用体验非常好！&#10;产品质量太差了，用了三天就坏了。&#10;今天天气不错，出去走走。"
        clearable
        maxlength="10000"
        show-word-limit
      />
      <div class="form-actions">
        <el-button type="primary" :loading="loading" :disabled="!hasText" @click="submitAnalysis">
          <el-icon><Search /></el-icon> 开始分析
        </el-button>
        <el-button :disabled="!inputText" @click="resetInput">清空</el-button>
        <el-button text type="primary" @click="fillSamples">填入示例文本</el-button>
      </div>
    </div>

    <!-- ═══ Results Section ═══ -->
    <div v-if="results.length > 0" class="results-section" v-loading="loading">
      <div class="section-title">
        <h3>📋 分析结果</h3>
        <el-tag v-if="sourceMode === 'api'" size="small" type="info" effect="plain">后端NLP·关键词规则（非ML）</el-tag>
        <el-tag v-else-if="sourceMode === 'fallback'" size="small" type="warning" effect="plain">本地关键词兜底（非ML）</el-tag>
      </div>

      <el-row :gutter="20">
        <!-- Left: Table -->
        <el-col :xs="24" :md="16">
          <div class="result-card table-card">
            <el-table :data="results" stripe border style="width:100%" max-height="480" size="small">
              <el-table-column label="文本" min-width="200" prop="text">
                <template #default="{ row }">
                  <el-tooltip :content="row.rawText || row.text" placement="top" :show-after="300">
                    <span>{{ row.text }}</span>
                  </el-tooltip>
                </template>
              </el-table-column>
              <el-table-column label="情感" width="90" align="center">
                <template #default="{ row }">
                  <el-tag :type="sentimentType(row.sentiment)" size="small" effect="dark">
                    {{ row.sentiment }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="置信度" width="150" align="center">
                <template #default="{ row }">
                  <el-progress
                    :percentage="Math.round(row.score * 100)"
                    :stroke-width="14"
                    :color="scoreColor(row.score)"
                    :format="() => (row.score * 100).toFixed(1) + '%'"
                  />
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-col>

        <!-- Right: Pie Chart -->
        <el-col :xs="24" :md="8">
          <div class="result-card chart-card">
            <div class="result-card-header">
              <span class="result-card-title">🎯 情感分布</span>
            </div>
            <v-chart :option="pieOption" autoresize style="width:100%;height:300px" />
          </div>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import { analyzeSentiment } from '@/api/modules/forum'

// Register ECharts
use([CanvasRenderer, PieChart, TooltipComponent, LegendComponent])

// ── State ──
const inputText = ref('')
const loading = ref(false)
const results = ref([])
const sourceMode = ref('')

// ── Computed ──
const hasText = computed(() => inputText.value.trim().length > 0)

const summary = computed(() => {
  const items = results.value
  let positive = 0, negative = 0, neutral = 0
  items.forEach(r => {
    if (r.sentiment === '积极') positive++
    else if (r.sentiment === '消极') negative++
    else neutral++
  })
  return {
    total: items.length,
    positive,
    negative,
    neutral
  }
})

const overallType = computed(() => {
  const s = summary.value
  if (s.positive > s.negative && s.positive > s.neutral) return 'success'
  if (s.negative > s.positive && s.negative > s.neutral) return 'danger'
  return 'info'
})

const overallLabel = computed(() => {
  const s = summary.value
  if (s.total === 0) return '—'
  if (s.positive > s.negative && s.positive > s.neutral) return '总体积极 👍'
  if (s.negative > s.positive && s.negative > s.neutral) return '总体消极 👎'
  return '总体中性 😐'
})

// ── Sentiment helpers ──
function sentimentType(s) {
  if (s === '积极') return 'success'
  if (s === '消极') return 'danger'
  return 'info'
}

function scoreColor(score) {
  if (score >= 0.7) return '#67C23A'
  if (score >= 0.4) return '#E6A23C'
  return '#F56C6C'
}

// ── Pie Chart Option ──
const pieOption = computed(() => {
  const s = summary.value
  if (s.total === 0) {
    return {
      title: { text: '暂无数据', left: 'center', top: 'center', textStyle: { fontSize: 14, color: '#909399' } },
      series: []
    }
  }

  const data = [
    { name: '积极', value: s.positive, itemStyle: { color: '#67C23A' } },
    { name: '中性', value: s.neutral, itemStyle: { color: '#909399' } },
    { name: '消极', value: s.negative, itemStyle: { color: '#F56C6C' } }
  ].filter(d => d.value > 0)

  return {
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} 条 ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center',
      textStyle: { fontSize: 12 }
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['45%', '50%'],
        avoidLabelOverlap: false,
        label: {
          show: true,
          formatter: '{b}\n{d}%',
          fontSize: 12
        },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' }
        },
        data
      }
    ]
  }
})

// ── Sample texts ──
const sampleTexts = [
  '这个平台真的太棒了，功能齐全，用户体验非常好！强烈推荐给大家！',
  '产品质量太差了，用了三天就坏了，售后服务也跟不上，非常失望。',
  '今天天气不错，出去走走，感觉心情好了很多。',
  '普通水平，没什么特别之处，凑合能用吧。'
]

function fillSamples() {
  inputText.value = sampleTexts.join('\n')
}

function resetInput() {
  inputText.value = ''
  results.value = []
}

// ── Fallback keyword-based sentiment scoring ──
const positiveKeywords = [
  '棒', '好', '赞', '优秀', '完美', '喜欢', '推荐', '厉害', '不错', '满意',
  '开心', '高兴', '感动', '进步', '成功', '强大', '方便', '实用', '绝了',
  '推荐', '惊艳', '期待', '支持', '加油', '靠谱', '良心', '给力', '宝藏',
  '顶级', '出色', '惊喜', '良心', '友好', '舒适', '稳定', '轻松', '划算'
]

const negativeKeywords = [
  '差', '烂', '垃圾', '失望', '糟糕', '失败', '坑', '后悔', '恶心', '难受',
  '垃圾', '无聊', '烦', '崩溃', '投诉', '缺陷', '问题', '错误', '不行',
  '退钱', '退款', '骗子', '恶心', '糟糕', '一般般', '不想', '讨厌', '厌恶',
  '太差', '太烂', '气人', '心累', '无力', '吐了', '垃圾'
]

function fallbackSentiment(texts) {
  return texts.map(t => {
    const trimmed = t.trim()
    if (!trimmed) return null
    let posCount = 0, negCount = 0
    positiveKeywords.forEach(k => { if (trimmed.includes(k)) posCount++ })
    negativeKeywords.forEach(k => { if (trimmed.includes(k)) negCount++ })

    let sentiment, score
    if (posCount > negCount) {
      sentiment = '积极'
      score = 0.5 + Math.min(0.45, posCount * 0.1)
    } else if (negCount > posCount) {
      sentiment = '消极'
      score = 0.5 + Math.min(0.45, negCount * 0.1)
    } else {
      // Check for question marks — often neutral
      if (trimmed.includes('？') || trimmed.includes('?')) {
        sentiment = '中性'
        score = 0.5
      } else if (trimmed.length < 8) {
        sentiment = '中性'
        score = 0.5
      } else {
        // Slight bias based on length — very short texts tend neutral
        sentiment = '中性'
        score = 0.5
      }
    }

    return {
      text: truncate(trimmed, 60),
      rawText: trimmed,
      sentiment,
      score: Math.round(score * 100) / 100
    }
  }).filter(r => r !== null)
}

// ── Truncate ──
function truncate(text, len) {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '…' : text
}

// ── Submit ──
async function submitAnalysis() {
  const raw = inputText.value.trim()
  if (!raw) {
    ElMessage.warning('请输入待分析的文本')
    return
  }

  const texts = raw.split('\n').map(t => t.trim()).filter(t => t.length > 0)
  if (texts.length === 0) {
    ElMessage.warning('未检测到有效文本')
    return
  }

  loading.value = true
  try {
    const res = await analyzeSentiment({ texts })
    const data = res.data || res
    sourceMode.value = 'api'
    if (Array.isArray(data)) {
      results.value = data.map((r, i) => ({
        text: truncate(texts[i] || '', 60),
        rawText: texts[i],
        sentiment: r.sentiment || '中性',
        score: r.score ?? r.confidence ?? 0.5
      }))
    } else if (data.results && Array.isArray(data.results)) {
      results.value = data.results.map((r, i) => ({
        text: truncate(texts[i] || '', 60),
        rawText: texts[i],
        sentiment: r.sentiment || '中性',
        score: r.score ?? r.confidence ?? 0.5
      }))
    } else {
      throw new Error('Unexpected response format')
    }
  } catch {
    ElMessage.warning('后端 API 暂不可用，使用本地关键词分析')
    sourceMode.value = 'fallback'
    results.value = fallbackSentiment(texts)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Layout ── */
.sentiment-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

/* ── Header ── */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 24px;
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
}
.header-left h2 {
  margin: 0;
  font-size: 24px;
  color: var(--el-text-color-primary);
}
.header-subtitle {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

/* ── Section Title ── */
.section-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.section-title h3 {
  margin: 0;
  font-size: 18px;
  color: var(--el-text-color-primary);
}

/* ── Summary Section ── */
.summary-section {
  margin-bottom: 20px;
}
.summary-card {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s;
}
.summary-card:hover {
  transform: translateY(-2px);
}
.summary-card.total {
  border-left: 4px solid #409EFF;
}
.summary-card.positive {
  border-left: 4px solid #67C23A;
}
.summary-card.negative {
  border-left: 4px solid #F56C6C;
}
.summary-card.neutral {
  border-left: 4px solid #909399;
}
.summary-icon {
  font-size: 28px;
}
.summary-info {
  flex: 1;
}
.summary-value {
  font-size: 26px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  line-height: 1.2;
}
.summary-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
.overall-tag {
  text-align: center;
  margin-top: 16px;
  font-size: 15px;
  color: var(--el-text-color-secondary);
}
.overall-tag .el-tag {
  margin-left: 6px;
}

/* ── Input Section ── */
.input-section {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.form-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 12px;
  flex-wrap: wrap;
}

/* ── Results Section ── */
.results-section {
  margin-top: 8px;
}
.result-card {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.result-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.result-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

/* ── Table ── */
.table-card {
  min-height: 300px;
}

/* ── Chart ── */
.chart-card {
  min-height: 340px;
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .sentiment-page {
    padding: 16px;
  }
}
@media (max-width: 480px) {
  .summary-card {
    padding: 12px 16px;
  }
  .summary-value {
    font-size: 22px;
  }
  .summary-icon {
    font-size: 22px;
  }
}
</style>
