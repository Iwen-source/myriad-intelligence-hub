<template>
  <div class="forum-container">
    <!-- Page Header -->
    <div class="forum-header">
      <div class="header-left">
        <h2>📚 技术论坛</h2>
        <span class="header-subtitle">交流 · 分享 · 成长</span>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openPostDialog">
          <el-icon><Plus /></el-icon> 发帖
        </el-button>
      </div>
    </div>

    <!-- ═══ Top: Hot Topics Carousel ═══ -->
    <div class="hot-carousel-section" v-if="hotTopics.length > 0">
      <el-carousel :interval="4000" type="card" height="140px" indicator-position="none">
        <el-carousel-item v-for="(topic, idx) in hotTopics.slice(0, 5)" :key="topic.id">
          <div class="carousel-card" :style="{ background: carouselColors[idx % carouselColors.length] }" @click="openDetail(topic.id)">
            <div class="carousel-rank">#{{ idx + 1 }}</div>
            <div class="carousel-title">{{ topic.title }}</div>
            <div class="carousel-tags">
              <el-tag :type="catTagType(topic.category)" size="small">{{ catLabel(topic.category) }}</el-tag>
              <span class="carousel-score">🔥 {{ topic.score }}</span>
            </div>
            <div class="carousel-stats">
              <span>❤️ {{ topic.likes }}</span>
              <span>💬 {{ topic.comments }}</span>
              <span>👁 {{ topic.views }}</span>
            </div>
          </div>
        </el-carousel-item>
      </el-carousel>
    </div>

    <!-- Stats Bar -->
    <div class="stats-bar" v-if="stats">
      <div class="stat-item">
        <span class="stat-label">📊 总帖子</span>
        <span class="stat-value">{{ stats.totalPosts }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">🤖 AI 算法讨论</span>
        <span class="stat-value">{{ stats.categoryCount?.ai || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">🚀 前沿技术分享</span>
        <span class="stat-value">{{ stats.categoryCount?.tech || 0 }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">🛠 项目实战</span>
        <span class="stat-value">{{ stats.categoryCount?.project || 0 }}</span>
      </div>
    </div>

    <!-- ═══ Loading ═══ -->
    <div v-if="loading" class="loading-wrapper">
      <el-skeleton :rows="6" animated />
    </div>

    <!-- ═══ Main Content: Three columns + Right Panel ═══ -->
    <div v-else class="main-layout">
      <!-- Left three columns -->
      <div class="main-columns">
        <!-- Left column: AI -->
        <div class="forum-column">
          <div class="column-header">
            <h3>🤖 AI 算法讨论</h3>
            <span class="column-count">{{ aiPosts.length }}</span>
          </div>
          <div v-if="aiPosts.length === 0" class="empty-tip">暂无帖子，来发第一篇吧！</div>
          <div v-for="post in aiPosts" :key="post.id" class="post-card">
            <div class="post-title" @click="openDetail(post.id)">{{ post.title }}</div>
            <div class="post-summary">{{ truncate(post.content, 80) }}</div>
            <div class="post-meta">
              <span><el-icon><View /></el-icon> {{ post.views || post.viewCount || 0 }}</span>
              <span>
                <el-button
                  :type="post.isLiked ? 'danger' : 'default'"
                  size="small"
                  :icon="Star"
                  circle
                  @click="handleLike(post)"
                />
                {{ post.likes || post.likeCount || 0 }}
              </span>
              <span><el-icon><ChatDotSquare /></el-icon> {{ post.comments || post.commentCount || 0 }}</span>
              <el-button type="danger" size="small" :icon="Delete" circle @click="handleDelete(post.id)" />
            </div>
          </div>
        </div>

        <!-- Middle column: Tech -->
        <div class="forum-column">
          <div class="column-header">
            <h3>🚀 前沿技术分享</h3>
            <span class="column-count">{{ techPosts.length }}</span>
          </div>
          <div v-if="techPosts.length === 0" class="empty-tip">暂无帖子，来发第一篇吧！</div>
          <div v-for="post in techPosts" :key="post.id" class="post-card">
            <div class="post-title" @click="openDetail(post.id)">{{ post.title }}</div>
            <div class="post-summary">{{ truncate(post.content, 80) }}</div>
            <div class="post-meta">
              <span><el-icon><View /></el-icon> {{ post.views || post.viewCount || 0 }}</span>
              <span>
                <el-button
                  :type="post.isLiked ? 'danger' : 'default'"
                  size="small"
                  :icon="Star"
                  circle
                  @click="handleLike(post)"
                />
                {{ post.likes || post.likeCount || 0 }}
              </span>
              <span><el-icon><ChatDotSquare /></el-icon> {{ post.comments || post.commentCount || 0 }}</span>
              <el-button type="danger" size="small" :icon="Delete" circle @click="handleDelete(post.id)" />
            </div>
          </div>
        </div>

        <!-- Right column: Project -->
        <div class="forum-column">
          <div class="column-header">
            <h3>🛠 项目实战</h3>
            <span class="column-count">{{ projectPosts.length }}</span>
          </div>
          <div v-if="projectPosts.length === 0" class="empty-tip">暂无帖子，来发第一篇吧！</div>
          <div v-for="post in projectPosts" :key="post.id" class="post-card">
            <div class="post-title" @click="openDetail(post.id)">{{ post.title }}</div>
            <div class="post-summary">{{ truncate(post.content, 80) }}</div>
            <div class="post-meta">
              <span><el-icon><View /></el-icon> {{ post.views || post.viewCount || 0 }}</span>
              <span>
                <el-button
                  :type="post.isLiked ? 'danger' : 'default'"
                  size="small"
                  :icon="Star"
                  circle
                  @click="handleLike(post)"
                />
                {{ post.likes || post.likeCount || 0 }}
              </span>
              <span><el-icon><ChatDotSquare /></el-icon> {{ post.comments || post.commentCount || 0 }}</span>
              <el-button type="danger" size="small" :icon="Delete" circle @click="handleDelete(post.id)" />
            </div>
          </div>
        </div>
      </div>

      <!-- Right side panel: Hot Topics -->
      <div class="side-panel">
        <div class="panel-card">
          <div class="panel-header">
            <h4>🔥 热门话题榜</h4>
            <el-tag size="small" type="danger" effect="plain">AI推荐</el-tag>
          </div>
          <div v-if="hotTopics.length === 0" class="empty-tip">暂无数据</div>
          <div v-for="(topic, idx) in hotTopics" :key="topic.id" class="hot-item" @click="openDetail(topic.id)">
            <span class="hot-rank" :class="{ 'top-three': idx < 3 }">{{ idx + 1 }}</span>
            <div class="hot-info">
              <span class="hot-title">{{ topic.title }}</span>
              <div class="hot-meta">
                <el-tag :type="catTagType(topic.category)" size="small">{{ catLabel(topic.category) }}</el-tag>
                <span class="hot-score">🔥 {{ topic.score }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Activity snapshot -->
        <div class="panel-card" v-if="activity">
          <div class="panel-header">
            <h4>📈 活跃概览</h4>
          </div>
          <div class="activity-grid">
            <div class="activity-item">
              <span class="act-num">{{ activity.totalPosts }}</span>
              <span class="act-label">总帖子</span>
            </div>
            <div class="activity-item">
              <span class="act-num">{{ activity.totalLikes }}</span>
              <span class="act-label">总点赞</span>
            </div>
            <div class="activity-item">
              <span class="act-num">{{ activity.totalComments }}</span>
              <span class="act-label">总评论</span>
            </div>
            <div class="activity-item">
              <span class="act-num">{{ activity.dailyPosts }}</span>
              <span class="act-label">日均发帖</span>
            </div>
          </div>
          <div class="activity-bar">
            <div class="bar-label">活跃指数</div>
            <el-progress :percentage="activity.activityScore || 0" :stroke-width="12" striped />
          </div>
        </div>
      </div>
    </div>

    <!-- ═══ Bottom: Trend Chart ═══ -->
    <div class="trend-section" v-loading="trendLoading">
      <div class="section-header">
        <h3>📊 趋势分析</h3>
        <el-tag size="small" type="success" effect="plain">最近30天</el-tag>
      </div>
      <div class="chart-wrapper">
        <v-chart :option="trendOption" autoresize style="width:100%;height:360px" />
      </div>
    </div>

    <!-- ── New Post Dialog ── -->
    <el-dialog v-model="postDialogVisible" title="发布新帖" width="600px" :close-on-click-modal="false">
      <el-form ref="postFormRef" :model="postForm" :rules="postFormRules" label-width="80px">
        <el-form-item label="主题" prop="title">
          <el-input v-model="postForm.title" placeholder="请输入帖子主题" maxlength="100" show-word-limit />
        </el-form-item>
        <el-form-item label="分类" prop="category">
          <el-select v-model="postForm.category" placeholder="请选择分类" style="width:100%">
            <el-option label="AI 算法讨论" value="ai" />
            <el-option label="前沿技术分享" value="tech" />
            <el-option label="项目实战" value="project" />
          </el-select>
        </el-form-item>
        <el-form-item label="内容" prop="content">
          <el-input v-model="postForm.content" type="textarea" :rows="8" placeholder="请输入帖子内容" maxlength="5000" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="postDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitPost">发布</el-button>
      </template>
    </el-dialog>

    <!-- ── Post Detail Dialog ── -->
    <el-dialog v-model="detailDialogVisible" :title="detailPost?.title || '帖子详情'" width="700px" :close-on-click-modal="false">
      <div v-if="detailLoading" class="loading-wrapper"><el-skeleton :rows="4" animated /></div>
      <div v-else-if="detailPost" class="detail-content">
        <div class="detail-body">{{ detailPost.content }}</div>
        <el-divider />
        <div class="detail-meta">
          <span><el-icon><View /></el-icon> 浏览量：{{ detailPost.views || detailPost.viewCount || 0 }}</span>
          <span>
            <el-button :type="detailPost.isLiked ? 'danger' : 'default'" size="small" :icon="Star" circle @click="handleLike(detailPost)" />
            {{ detailPost.likes || detailPost.likeCount || 0 }}
          </span>
          <span><el-icon><ChatDotSquare /></el-icon> 评论数：{{ detailPost.comments || detailPost.commentCount || 0 }}</span>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, View, Star, ChatDotSquare, Delete } from '@element-plus/icons-vue'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart, BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'
import {
  getForumPosts,
  getForumPostDetail,
  addForumPost,
  deleteForumPost,
  likeForumPost,
  getForumStats,
  getForumHotTopics,
  getForumRecommendations,
  getForumTrends,
  getForumActivity
} from '@/api/modules'

// Register ECharts components
use([CanvasRenderer, LineChart, BarChart, GridComponent, TooltipComponent, LegendComponent])

// ── Constants ──
const carouselColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)'
]

const categoryMap = {
  ai: { label: 'AI 算法讨论', tag: 'danger' },
  tech: { label: '前沿技术分享', tag: 'warning' },
  project: { label: '项目实战', tag: 'success' }
}

function catLabel(cat) { return categoryMap[cat]?.label || cat }
function catTagType(cat) { return categoryMap[cat]?.tag || 'info' }

// ── State ──
const loading = ref(false)
const trendLoading = ref(false)
const submitting = ref(false)
const detailLoading = ref(false)
const aiPosts = ref([])
const techPosts = ref([])
const projectPosts = ref([])
const stats = ref(null)
const hotTopics = ref([])
const recommendations = ref([])
const trends = ref([])
const activity = ref(null)
const postDialogVisible = ref(false)
const detailDialogVisible = ref(false)
const detailPost = ref(null)

const postForm = reactive({ title: '', category: '', content: '' })
const postFormRef = ref(null)
const postFormRules = {
  title: [
    { required: true, message: '请输入帖子主题', trigger: 'blur' },
    { min: 2, max: 100, message: '主题长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  category: [{ required: true, message: '请选择分类', trigger: 'change' }],
  content: [
    { required: true, message: '请输入帖子内容', trigger: 'blur' },
    { min: 10, max: 5000, message: '内容长度在 10 到 5000 个字符', trigger: 'blur' }
  ]
}

// ── ECharts Trend Option ──
const trendOption = computed(() => {
  if (!trends.value || trends.value.length === 0) {
    return {
      title: { text: '暂无趋势数据', left: 'center', top: 'center', textStyle: { fontSize: 14, color: '#909399' } },
      xAxis: { type: 'category', data: [] },
      yAxis: { type: 'value' },
      series: []
    }
  }

  const dates = trends.value.map(t => t.date?.slice(5)) // MM-DD
  return {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross', label: { backgroundColor: '#6a7985' } }
    },
    legend: {
      data: ['AI 算法讨论', '前沿技术分享', '项目实战', '总帖数'],
      top: 0
    },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
      axisLabel: { rotate: 45, fontSize: 11 }
    },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      {
        name: 'AI 算法讨论',
        type: 'line',
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
        emphasis: { focus: 'series' },
        data: trends.value.map(t => t.ai || 0)
      },
      {
        name: '前沿技术分享',
        type: 'line',
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
        emphasis: { focus: 'series' },
        data: trends.value.map(t => t.tech || 0)
      },
      {
        name: '项目实战',
        type: 'line',
        smooth: true,
        lineStyle: { width: 2 },
        areaStyle: { opacity: 0.15 },
        emphasis: { focus: 'series' },
        data: trends.value.map(t => t.project || 0)
      },
      {
        name: '总帖数',
        type: 'bar',
        barMaxWidth: 12,
        yAxisIndex: 0,
        itemStyle: { color: 'rgba(64,158,255,0.2)', borderRadius: [4, 4, 0, 0] },
        data: trends.value.map(t => t.total || 0)
      }
    ]
  }
})

// ── Helpers ──
function truncate(text, maxLen) {
  if (!text) return ''
  return text.length > maxLen ? text.slice(0, maxLen) + '…' : text
}

// ── Data Fetching ──
async function fetchData() {
  loading.value = true
  try {
    const [aiRes, techRes, projRes, statsRes, hotRes, actRes] = await Promise.all([
      getForumPosts('ai'),
      getForumPosts('tech'),
      getForumPosts('project'),
      getForumStats(),
      getForumHotTopics(),
      getForumActivity()
    ])
    aiPosts.value = aiRes.data || []
    techPosts.value = techRes.data || []
    projectPosts.value = projRes.data || []
    stats.value = statsRes.data || {}
    hotTopics.value = hotRes.data || []
    activity.value = actRes.data || {}
  } catch (e) {
    ElMessage.error('获取论坛数据失败')
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function fetchTrends() {
  trendLoading.value = true
  try {
    const res = await getForumTrends()
    trends.value = res.data || []
  } catch (e) {
    console.error('获取趋势数据失败', e)
  } finally {
    trendLoading.value = false
  }
}

// ── Like ──
async function handleLike(post) {
  try {
    await likeForumPost(post.id)
    post.isLiked = !post.isLiked

    if (post.likes !== undefined) {
      post.likes = (post.likes || 0) + (post.isLiked ? 1 : -1)
    } else if (post.likeCount !== undefined) {
      post.likeCount = (post.likeCount || 0) + (post.isLiked ? 1 : -1)
    }

    ElMessage.success(post.isLiked ? '已点赞' : '已取消点赞')
  } catch (e) {
    ElMessage.error('操作失败')
    console.error(e)
  }
}

// ── Delete ──
async function handleDelete(id) {
  try {
    await ElMessageBox.confirm('确定要删除该帖子吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await deleteForumPost(id)
    aiPosts.value = aiPosts.value.filter(p => p.id !== id)
    techPosts.value = techPosts.value.filter(p => p.id !== id)
    projectPosts.value = projectPosts.value.filter(p => p.id !== id)
    ElMessage.success('删除成功')
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
      console.error(e)
    }
  }
}

// ── Detail ──
async function openDetail(id) {
  detailDialogVisible.value = true
  detailLoading.value = true
  detailPost.value = null
  try {
    const res = await getForumPostDetail(id)
    detailPost.value = res.data || {}
  } catch (e) {
    ElMessage.error('获取帖子详情失败')
    console.error(e)
  } finally {
    detailLoading.value = false
  }
}

// ── New Post ──
function openPostDialog() {
  postForm.title = ''
  postForm.category = ''
  postForm.content = ''
  postDialogVisible.value = true
}

async function submitPost() {
  if (!postFormRef.value) return
  try { await postFormRef.value.validate() } catch { return }

  submitting.value = true
  try {
    await addForumPost({
      title: postForm.title,
      category: postForm.category,
      content: postForm.content
    })
    ElMessage.success('发布成功')
    postDialogVisible.value = false
    await fetchData()
    await fetchTrends()
  } catch (e) {
    ElMessage.error('发布失败')
    console.error(e)
  } finally {
    submitting.value = false
  }
}

// ── Lifecycle ──
onMounted(() => {
  fetchData()
  fetchTrends()
})
</script>

<style scoped>
.forum-container {
  max-width: 1440px;
  margin: 0 auto;
  padding: 24px;
}

/* ── Header ── */
.forum-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
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
.header-actions {
  display: flex;
  gap: 12px;
}

/* ── Hot Carousel ── */
.hot-carousel-section {
  margin-bottom: 20px;
}
.carousel-card {
  height: 100%;
  border-radius: 12px;
  padding: 20px 24px;
  color: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.carousel-rank {
  position: absolute;
  top: 8px;
  right: 16px;
  font-size: 40px;
  font-weight: 900;
  opacity: 0.15;
  line-height: 1;
}
.carousel-title {
  font-size: 16px;
  font-weight: 700;
  margin-bottom: 8px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.carousel-tags {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.carousel-score {
  font-size: 13px;
  font-weight: 600;
  opacity: 0.9;
}
.carousel-stats {
  display: flex;
  gap: 16px;
  font-size: 12px;
  opacity: 0.8;
}

/* ── Stats Bar ── */
.stats-bar {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 24px;
  padding: 16px 20px;
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}
.stat-item {
  flex: 1;
  min-width: 120px;
  text-align: center;
}
.stat-label {
  display: block;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
}
.stat-value {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--el-color-primary);
}

/* ── Loading ── */
.loading-wrapper {
  padding: 40px 20px;
}

/* ── Main Layout ── */
.main-layout {
  display: flex;
  gap: 20px;
  margin-bottom: 24px;
}
.main-columns {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  min-width: 0;
}

/* ── Side Panel ── */
.side-panel {
  width: 280px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.panel-card {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--el-color-danger);
}
.panel-header h4 {
  margin: 0;
  font-size: 16px;
  color: var(--el-text-color-primary);
}

/* ── Hot Items ── */
.hot-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: background 0.2s;
}
.hot-item:last-child {
  border-bottom: none;
}
.hot-item:hover {
  background: var(--el-fill-color-light);
  border-radius: 6px;
  padding-left: 6px;
  padding-right: 6px;
  margin: 0 -6px;
}
.hot-rank {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--el-fill-color);
  color: var(--el-text-color-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}
.hot-rank.top-three {
  background: linear-gradient(135deg, #f093fb, #f5576c);
  color: #fff;
}
.hot-info {
  flex: 1;
  min-width: 0;
}
.hot-title {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  line-height: 1.4;
  margin-bottom: 4px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.hot-meta {
  display: flex;
  align-items: center;
  gap: 6px;
}
.hot-score {
  font-size: 11px;
  color: var(--el-color-danger);
  font-weight: 600;
}

/* ── Activity Panel ── */
.activity-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}
.activity-item {
  text-align: center;
  padding: 8px;
  background: var(--el-fill-color-lighter);
  border-radius: 8px;
}
.act-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.act-label {
  display: block;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}
.activity-bar {
  padding-top: 4px;
}
.bar-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-bottom: 6px;
}

/* ── Column ── */
.forum-column {
  min-width: 0;
}
.column-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--el-color-primary);
}
.column-header h3 {
  margin: 0;
  font-size: 16px;
  color: var(--el-text-color-primary);
}
.column-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  background: var(--el-fill-color);
  padding: 2px 8px;
  border-radius: 10px;
}

/* ── Empty ── */
.empty-tip {
  text-align: center;
  padding: 30px 0;
  color: var(--el-text-color-placeholder);
  font-size: 13px;
}

/* ── Post Card ── */
.post-card {
  background: var(--el-bg-color-overlay);
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 12px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s, transform 0.15s;
}
.post-card:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}
.post-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-color-primary);
  cursor: pointer;
  margin-bottom: 6px;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.post-title:hover {
  text-decoration: underline;
}
.post-summary {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
  margin-bottom: 10px;
}
.post-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  flex-wrap: wrap;
}
.post-meta span {
  display: inline-flex;
  align-items: center;
  gap: 3px;
}

/* ── Trend Section ── */
.trend-section {
  background: var(--el-bg-color-overlay);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.section-header h3 {
  margin: 0;
  font-size: 18px;
  color: var(--el-text-color-primary);
}
.chart-wrapper {
  min-height: 360px;
}

/* ── Detail Dialog ── */
.detail-content {
  padding: 0 4px;
}
.detail-body {
  font-size: 15px;
  line-height: 1.8;
  color: var(--el-text-color-primary);
  white-space: pre-wrap;
  word-break: break-word;
}
.detail-meta {
  display: flex;
  align-items: center;
  gap: 24px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}
.detail-meta span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

/* ── Responsive ── */
@media (max-width: 1200px) {
  .main-layout {
    flex-direction: column;
  }
  .side-panel {
    width: 100%;
    flex-direction: row;
    flex-wrap: wrap;
  }
  .side-panel .panel-card {
    flex: 1;
    min-width: 240px;
  }
}
@media (max-width: 900px) {
  .main-columns {
    grid-template-columns: 1fr;
  }
  .forum-container {
    padding: 16px;
  }
  .stats-bar {
    gap: 8px;
  }
  .stat-item {
    min-width: 80px;
  }
}
</style>
