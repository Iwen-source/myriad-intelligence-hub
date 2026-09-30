<template>
  <div class="quality-page">
    <!-- ── Header ── -->
    <div class="page-header">
      <div class="header-left">
        <h2>📊 帖子质量分析</h2>
        <span class="header-subtitle">AI 智能评估帖子内容质量</span>
      </div>
    </div>

    <!-- ═══ Input Section ═══ -->
    <div class="input-section">
      <div class="section-title">
        <h3>📝 输入帖子内容</h3>
        <el-tag type="info" effect="plain">输入标题和正文，AI 将自动分析评分</el-tag>
      </div>
      <el-form :model="form" label-width="60px" @submit.prevent="submitAnalysis">
        <el-form-item label="标题">
          <el-input v-model="form.title" placeholder="请输入帖子标题..." clearable maxlength="200" show-word-limit />
        </el-form-item>
        <el-form-item label="正文">
          <el-input
            v-model="form.body"
            type="textarea"
            :rows="6"
            placeholder="请输入帖子正文内容..."
            clearable
            maxlength="5000"
            show-word-limit
          />
        </el-form-item>
        <el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="loading" :disabled="!form.title.trim() && !form.body.trim()" @click="submitAnalysis">
              <el-icon><Search /></el-icon> 开始分析
            </el-button>
            <el-button :disabled="!form.title && !form.body" @click="resetForm">清空</el-button>
          </div>
        </el-form-item>
      </el-form>
    </div>

    <!-- ═══ Sample Analysis Section ═══ -->
    <div class="sample-section">
      <div class="section-title">
        <h3>📋 样本分析</h3>
        <el-tag type="warning" effect="plain">点击示例快速分析</el-tag>
      </div>
      <div class="sample-grid">
        <div
          v-for="(sample, idx) in samples"
          :key="idx"
          class="sample-card"
          :class="{ active: activeSampleIdx === idx }"
          @click="selectSample(idx)"
        >
          <div class="sample-icon">{{ sample.icon }}</div>
          <div class="sample-title">{{ sample.title }}</div>
          <div class="sample-desc">{{ truncate(sample.body, 60) }}</div>
        </div>
      </div>
    </div>

    <!-- ═══ Results Section ═══ -->
    <div v-if="result" class="result-section" v-loading="loading">
      <div class="section-title">
        <h3>📊 分析结果</h3>
        <el-tag v-if="sourceMode === 'api'" size="small" type="info" effect="plain">后端NLP·关键词规则（非ML）</el-tag>
        <el-tag v-else-if="sourceMode === 'fallback'" size="small" type="warning" effect="plain">本地启发式兵底（非ML）</el-tag>
      </div>

      <el-row :gutter="20">
        <!-- Left: Score + Category -->
        <el-col :xs="24" :md="14">
          <div class="result-card score-card">
            <div class="result-card-header">
              <span class="result-card-title">质量评分</span>
              <span class="score-badge" :style="{ color: scoreColor }">{{ result.quality_score }} / 10</span>
            </div>
            <el-progress
              :percentage="result.quality_score * 10"
              :stroke-width="22"
              :color="progressColor"
              striped
              striped-flow
              :duration="6"
            >
              <span class="progress-inner">{{ result.quality_score }} 分</span>
            </el-progress>

            <div class="score-tags">
              <div class="score-tag-item">
                <span class="score-label">内容分类</span>
                <el-tag :type="catTagType(result.category)" effect="dark" size="large">{{ result.category }}</el-tag>
              </div>
              <div class="score-tag-item">
                <span class="score-label">置信度</span>
                <el-tag type="info" effect="plain" size="large">{{ (result.confidence * 100).toFixed(1) }}%</el-tag>
              </div>
              <div class="score-tag-item">
                <span class="score-label">字数统计</span>
                <el-tag type="info" effect="plain" size="large">{{ result.word_count }} 字</el-tag>
              </div>
            </div>
          </div>
        </el-col>

        <!-- Right: Key Topics -->
        <el-col :xs="24" :md="10">
          <div class="result-card topics-card">
            <div class="result-card-header">
              <span class="result-card-title">🔑 关键主题</span>
              <span class="topic-count">{{ result.key_topics.length }}</span>
            </div>
            <div class="topics-list">
              <el-tag
                v-for="(topic, i) in result.key_topics"
                :key="i"
                :type="topicTypes[i % topicTypes.length]"
                size="default"
                effect="light"
                class="topic-tag"
              >
                {{ topic }}
              </el-tag>
              <span v-if="result.key_topics.length === 0" class="empty-tip-mini">未识别出关键主题</span>
            </div>
          </div>
        </el-col>
      </el-row>

      <!-- ── Detailed Breakdown ── -->
      <div class="result-card breakdown-card">
        <div class="result-card-header">
          <span class="result-card-title">📋 评分细项</span>
        </div>
        <div class="breakdown-grid">
          <div v-for="(item, idx) in breakdownItems" :key="idx" class="breakdown-item">
            <div class="breakdown-label">
              <span>{{ item.label }}</span>
              <span class="breakdown-score" :style="{ color: getSubScoreColor(item.score) }">{{ item.score }}分</span>
            </div>
            <el-progress
              :percentage="item.score * 20"
              :stroke-width="14"
              :color="getSubScoreColor(item.score)"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { analyzeContentQuality } from '@/api/modules/forum'

// ── Form ──
const form = ref({ title: '', body: '' })
const loading = ref(false)
const result = ref(null)
const sourceMode = ref('')
const activeSampleIdx = ref(-1)

// ── Category color mapping ──
const categoryColors = {
  '技术讨论': 'primary',
  '项目求助': 'warning',
  '经验分享': 'success',
  '资源推荐': 'danger',
  '行业动态': 'info',
  '求职交流': '',
  '学术问答': 'warning',
  '闲聊灌水': 'info'
}
const categoryTagTypes = {
  '技术讨论': 'primary',
  '项目求助': 'warning',
  '经验分享': 'success',
  '资源推荐': 'danger',
  '行业动态': 'info',
  '求职交流': 'danger',
  '学术问答': 'warning',
  '闲聊灌水': 'info'
}

function catTagType(cat) { return categoryTagTypes[cat] || 'primary' }

// ── Topic tag types ──
const topicTypes = ['', 'success', 'warning', 'info', 'danger', 'primary']

// ── Score colors ──
const scoreColor = computed(() => {
  if (!result.value) return '#909399'
  const s = result.value.quality_score
  if (s >= 8) return '#67C23A'
  if (s >= 6) return '#409EFF'
  if (s >= 4) return '#E6A23C'
  return '#F56C6C'
})

function progressColor(pct) {
  if (pct >= 80) return '#67C23A'
  if (pct >= 60) return '#409EFF'
  if (pct >= 40) return '#E6A23C'
  return '#F56C6C'
}

function getSubScoreColor(score) {
  if (score >= 4) return '#67C23A'
  if (score >= 3) return '#409EFF'
  if (score >= 2) return '#E6A23C'
  return '#F56C6C'
}

// ── Breakdown items ──
const breakdownItems = computed(() => {
  if (!result.value) return []
  const r = result.value
  return [
    { label: '内容完整性', score: r.completeness || 3 },
    { label: '逻辑清晰度', score: r.clarity || 3 },
    { label: '信息密度', score: r.information_density || 3 },
    { label: '语言表达', score: r.expression || 3 },
    { label: '主题相关性', score: r.relevance || 3 }
  ]
})

// ── Sample posts ──
const samples = [
  {
    icon: '💻',
    title: '【技术讨论】深度学习框架对比',
    body: '最近在研究 PyTorch 和 TensorFlow 的最新版本，想和大家聊聊这两个框架在实际项目中的优劣。PyTorch 2.0 的 torch.compile 确实带来了显著的性能提升，而 TensorFlow 的 TFX 生态在工业部署上依然有着不可替代的优势。各位在实际项目中更倾向于使用哪个框架？'
  },
  {
    icon: '🆘',
    title: '【项目求助】WebSocket 连接断开问题',
    body: '求助大佬！我在做一个实时协作平台，WebSocket 连接总是在 30 分钟后自动断开。已经试过心跳检测和重连机制，但似乎还是会断。后端用的是 Spring Boot + Netty，前端是原生 WebSocket。有人遇到过类似问题吗？求指导！'
  },
  {
    icon: '📚',
    title: '【经验分享】我的 LeetCode 刷题方法论',
    body: '从零开始刷了 300 道题，总结了一套适合新手的刷题路线。先掌握数组、链表、栈这些基础数据结构，然后重点练习动态规划和回溯算法。推荐按照"专题训练→限时模拟→错题复盘"三个步骤循环推进。相信坚持 100 天一定会有质变！'
  },
  {
    icon: '🌐',
    title: '【行业动态】GPT-5 来了！AI 行业大洗牌',
    body: 'OpenAI 刚刚发布了 GPT-5 模型，推理能力相比 GPT-4 提升了 3 倍，多模态能力更是质的飞跃。'
  }
]

// ── Helpers ──
function truncate(text, len) {
  if (!text) return ''
  return text.length > len ? text.slice(0, len) + '…' : text
}

// ── Reset ──
function resetForm() {
  form.value = { title: '', body: '' }
  result.value = null
  activeSampleIdx.value = -1
}

// ── Select sample ──
function selectSample(idx) {
  const s = samples[idx]
  form.value = { title: s.title, body: s.body }
  activeSampleIdx.value = idx
  submitAnalysis()
}

// ── Fallback heuristic scoring ──
function fallbackScore(title, body) {
  const text = (title || '') + ' ' + (body || '')
  const wordCount = text.length

  // Heuristic scoring
  let score = 5 // base

  // Length bonus
  if (wordCount > 500) score += 2
  else if (wordCount > 200) score += 1
  else if (wordCount < 50) score -= 2
  else if (wordCount < 20) score -= 3

  // Question mark bonus
  const questions = (text.match(/[？?]/g) || []).length
  if (questions > 2) score += 1

  // Exclamation bonus
  const exclamations = (text.match(/[！!]/g) || []).length
  if (exclamations > 3) score += 1

  // Code blocks suggest technical content
  if (text.includes('```') || text.includes('function') || text.includes('class ')) score += 1

  // Technical keywords
  const techKeywords = ['API', '框架', '算法', '模型', '数据', '系统', '架构', '前端', '后端', '部署', '优化', '性能']
  const hasTech = techKeywords.some(k => text.includes(k))
  if (hasTech) score += 1

  // Punctuation/formatting
  const hasNewlines = (body || '').split('\n').length > 3
  if (hasNewlines) score += 1

  score = Math.max(1, Math.min(10, Math.round(score)))

  // Category detection
  let category = '闲聊灌水'
  if (text.includes('求助') || text.includes('问题') || text.includes('报错')) category = '项目求助'
  else if (text.includes('分享') || text.includes('经验') || text.includes('总结')) category = '经验分享'
  else if (text.includes('推荐') || text.includes('资源') || text.includes('工具') || text.includes('教程')) category = '资源推荐'
  else if (text.includes('行业') || text.includes('发布') || text.includes('新闻') || text.includes('趋势')) category = '行业动态'
  else if (text.includes('面试') || text.includes('求职') || text.includes('offer') || text.includes('招聘')) category = '求职交流'
  else if (text.includes('笔试') || text.includes('作业') || text.includes('考试') || text.includes('课设')) category = '学术问答'
  else if (hasTech || text.includes('技术') || text.includes('代码') || text.includes('编程')) category = '技术讨论'

  // Key topics extraction (simple word frequency)
  const words = text.match(/[\u4e00-\u9fa5]{2,4}/g) || []
  const freq = {}
  words.forEach(w => {
    freq[w] = (freq[w] || 0) + 1
  })
  const keyTopics = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([w]) => w)

  return {
    quality_score: score,
    category,
    confidence: Math.min(0.95, 0.3 + score * 0.07),
    key_topics: keyTopics.length > 0 ? keyTopics : ['帖子', '内容'],
    word_count: wordCount,
    completeness: Math.min(5, Math.max(1, Math.round(wordCount / 100))),
    clarity: Math.min(5, Math.max(1, Math.round(score / 2))),
    information_density: Math.min(5, Math.max(1, Math.round(score / 2.5))),
    expression: Math.min(5, Math.max(1, Math.round(score / 2.2))),
    relevance: Math.min(5, Math.max(1, Math.round(score / 2)))
  }
}

// ── Submit analysis ──
async function submitAnalysis() {
  const title = form.value.title.trim()
  const body = form.value.body.trim()
  if (!title && !body) {
    ElMessage.warning('请输入帖子标题或正文')
    return
  }

  loading.value = true
  try {
    const res = await analyzeContentQuality({ title, body })
    result.value = res.data || res
    sourceMode.value = 'api'
  } catch {
    ElMessage.warning('后端 API 暂不可用，使用本地启发式评分')
    sourceMode.value = 'fallback'
    result.value = fallbackScore(title, body)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* ── Layout ── */
.quality-page {
  max-width: 1100px;
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
}

/* ── Sample Section ── */
.sample-section {
  margin-bottom: 24px;
}
.sample-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.sample-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 16px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}
.sample-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
  border-color: var(--el-color-primary-light-5);
}
.sample-card.active {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 2px var(--el-color-primary-light-7);
}
.sample-icon {
  font-size: 24px;
  margin-bottom: 8px;
}
.sample-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 6px;
  line-height: 1.3;
}
.sample-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
}

/* ── Result Section ── */
.result-section {
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

/* ── Score Card ── */
.score-card {
  min-height: 200px;
}
.score-badge {
  font-size: 28px;
  font-weight: 700;
}
.progress-inner {
  font-size: 13px;
  font-weight: 600;
}
.score-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-top: 20px;
}
.score-tag-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.score-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* ── Topics Card ── */
.topics-card {
  min-height: 200px;
}
.topic-count {
  background: var(--el-color-primary-light-8);
  color: var(--el-color-primary);
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 10px;
}
.topics-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.topic-tag {
  font-size: 13px;
}

/* ── Breakdown ── */
.breakdown-card {
  margin-top: 4px;
}
.breakdown-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
@media (max-width: 600px) {
  .breakdown-grid {
    grid-template-columns: 1fr;
  }
}
.breakdown-item {
  padding: 12px 0;
}
.breakdown-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
  font-size: 14px;
  color: var(--el-text-color-primary);
}
.breakdown-score {
  font-weight: 600;
  font-size: 14px;
}

/* ── Empty ── */
.empty-tip-mini {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
}

/* ── Responsive ── */
@media (max-width: 768px) {
  .quality-page {
    padding: 16px;
  }
  .sample-grid {
    grid-template-columns: 1fr 1fr;
  }
}
@media (max-width: 480px) {
  .sample-grid {
    grid-template-columns: 1fr;
  }
}
</style>
