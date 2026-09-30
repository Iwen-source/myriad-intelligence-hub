<template>
  <div class="trend-page">
    <!-- Hero -->
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">AI 技术瞭望</div>
        <h1>技术趋势分析</h1>
        <p class="hero-desc">追踪 AI 技术演进脉络，洞察前沿发展方向</p>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div v-for="s in summaryStats" :key="s.label" class="stat-card">
        <span class="stat-val">{{ s.value }}</span>
        <span class="stat-lbl">{{ s.label }}</span>
      </div>
    </div>

    <!-- Trend Chart -->
    <div class="chart-card">
      <div class="chart-header">
        <span class="chart-title">📈 年度影响力趋势</span>
        <span class="chart-range">{{ startYear }} — {{ endYear }}</span>
      </div>
      <div ref="trendRef" style="width:100%;height:380px"></div>
    </div>

    <!-- Categories -->
    <div class="cat-grid">
      <div v-for="cat in categories" :key="cat.name" class="cat-card">
        <div class="cat-head">
          <span class="cat-name">{{ cat.name }}</span>
          <span class="cat-count">{{ cat.count }} 项</span>
        </div>
        <p class="cat-desc">{{ cat.description }}</p>
        <div class="cat-tags">
          <span v-for="t in cat.technologies" :key="t" class="cat-tag">{{ t }}</span>
        </div>
      </div>
    </div>

    <!-- Lifecycle -->
    <div class="lifecycle-wrap">
      <div class="lc-header">🔄 技术生命周期</div>
      <div class="lc-grid">
        <div v-for="st in lifecycleStages" :key="st.name" class="lc-card" :style="{ '--accent': st.color }">
          <div class="lc-badge" :style="{ background: st.color }">{{ st.name }}</div>
          <p class="lc-desc">{{ st.description }}</p>
          <div class="lc-techs">
            <span v-for="t in st.technologies" :key="t" class="lc-tech" :style="{ background: st.color + '18', color: st.color, borderColor: st.color + '40' }">{{ t }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Milestones -->
    <div class="milestone-wrap">
      <div class="ms-header">🏆 重要里程碑</div>
      <div class="ms-timeline">
        <div v-for="(ms, i) in milestones" :key="ms.title" class="ms-item" :class="{ major: ms.major, right: i % 2 === 1 }">
          <div class="ms-dot" :style="{ background: ms.color }"></div>
          <div class="ms-body">
            <div class="ms-era">{{ ms.era }}</div>
            <h4 class="ms-title">{{ ms.title }} <span v-if="ms.major" class="ms-badge">重大</span></h4>
            <p class="ms-desc">{{ ms.description }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import { getTrendAnalysis } from '@/api/modules/development'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const trendRef = ref(null)
let trendChart = null
const startYear = 2000, endYear = 2026

const fallbackData = {
  summary: [
    { label: '追踪技术', value: '48 项' },
    { label: '覆盖类别', value: '8 类' },
    { label: '重大突破', value: '12 项' },
    { label: '预测窗口', value: '2026+' }
  ],
  yearlyImpact: (() => {
    const d = []; const base = [3,4,5,6,6,7,8,10,12,14,18,22,25,28,32,38,45,52,58,65,72,78,83,87,91,94,96]
    for (let i = 0; i <= endYear - startYear; i++) d.push({ year: startYear + i, score: base[i] || 92 })
    return d
  })(),
  categories: [
    { name: '机器学习', count: 8, description: '监督、无监督、集成学习等经典算法体系', technologies: ['线性回归','决策树','随机森林','SVM','K-Means','XGBoost','LightGBM','贝叶斯'] },
    { name: '深度学习', count: 7, description: '神经网络驱动的表征学习与端到端建模', technologies: ['CNN','RNN/LSTM','Transformer','GAN','VAE','GNN','自监督'] },
    { name: '自然语言处理', count: 6, description: '让机器理解、生成和交互人类语言', technologies: ['BERT','GPT系列','T5','BART','序列标注','文本生成'] },
    { name: '计算机视觉', count: 6, description: '图像与视频的感知、理解与生成', technologies: ['图像分类','目标检测','语义分割','人脸识别','图像生成','视频理解'] },
    { name: '强化学习', count: 5, description: '智能体通过与环境交互学习最优策略', technologies: ['Q-Learning','DQN','PPO','A3C','SAC'] },
    { name: 'AI基础设施', count: 6, description: '支撑AI开发与部署的底层平台和工具', technologies: ['Docker/K8s','GPU集群','MLflow','Kubeflow','TensorRT','Triton'] },
    { name: '大模型与AGI', count: 5, description: '大规模预训练与通用人工智能探索', technologies: ['GPT-4','LLaMA','Claude','Gemini','MoE架构'] },
    { name: 'AI应用生态', count: 5, description: 'AI技术在行业中的落地实践', technologies: ['AI编程助手','智能客服','AI绘画','自动驾驶','AI科研'] }
  ],
  lifecycleStages: [
    { name: '前沿探索', color: '#ef4444', description: '技术处于早期研究阶段，应用场景尚未明确', technologies: ['AGI架构','类脑计算','量子ML','世界模型'] },
    { name: '新兴增长', color: '#f59e0b', description: '技术逐渐成熟，开始应用于特定领域', technologies: ['多模态大模型','AI Agent','RAG','模型微调'] },
    { name: '快速成熟', color: '#6366f1', description: '技术已形成标准范式，广泛被工业界采用', technologies: ['GPT API','Diffusion','LangChain','向量数据库'] },
    { name: '前沿演进', color: '#64748b', description: '技术已进入主流，但仍在快速进化', technologies: ['自动驾驶','医疗AI','AI芯片','边缘AI'] }
  ],
  milestones: [
    { era: '2006', title: '深度学习复兴', description: 'Hinton 提出深度信念网络，深度学习重新成为研究热点', color: '#ef4444', major: true },
    { era: '2012', title: 'AlexNet 革命', description: '在 ImageNet 上大幅刷新纪录，引爆深度学习革命', color: '#ef4444', major: true },
    { era: '2014', title: '生成对抗网络 GAN', description: 'Ian Goodfellow 提出 GAN，开启生成模型新纪元', color: '#f59e0b', major: false },
    { era: '2017', title: 'Transformer 架构', description: 'Google 发表 "Attention Is All You Need"，奠基大模型时代', color: '#ef4444', major: true },
    { era: '2018', title: 'BERT 预训练范式', description: '双向预训练模型全面超越传统 NLP 方法', color: '#6366f1', major: false },
    { era: '2020', title: 'GPT-3 大语言模型', description: '1750 亿参数展示少样本学习的惊人能力', color: '#ef4444', major: true },
    { era: '2022', title: 'Stable Diffusion AIGC', description: '开源文生图模型爆发，内容创作革命开始', color: '#f59e0b', major: false },
    { era: '2022-23', title: 'ChatGPT 全球引爆', description: '史上增长最快应用，掀起全球 AI 浪潮', color: '#ef4444', major: true },
    { era: '2024', title: '多模态与 AI Agent', description: 'GPT-4V 实现视觉理解，自主智能体兴起', color: '#6366f1', major: false },
    { era: '2025-26', title: '推理与 Agent 时代', description: '推理能力大幅提升，AI Agent 走向规模化', color: '#10b981', major: false }
  ]
}

const summaryStats = ref(fallbackData.summary)
const yearlyImpact = ref(fallbackData.yearlyImpact)
const categories = ref(fallbackData.categories)
const lifecycleStages = ref(fallbackData.lifecycleStages)
const milestones = ref(fallbackData.milestones)

function renderChart() {
  nextTick(() => {
    if (trendChart) trendChart.dispose()
    if (!trendRef.value) return
    trendChart = echarts.init(trendRef.value)
    const years = yearlyImpact.value.map(d => d.year)
    const scores = yearlyImpact.value.map(d => d.score)
    trendChart.setOption({
      tooltip: { trigger: 'axis', formatter: p => `${p[0].axisValue}年<br/>影响力：<strong>${p[0].value}</strong>` },
      grid: { left: 50, right: 30, top: 30, bottom: 45 },
      xAxis: { type: 'category', data: years, axisLabel: { rotate: 40, fontSize: 10 }, boundaryGap: false },
      yAxis: { type: 'value', min: 0, max: 100, name: '影响力评分', nameTextStyle: { color: '#94a3b8', fontSize: 11 } },
      dataZoom: [{ type: 'inside', start: 0 }, { type: 'slider', start: 0, height: 24, bottom: 8 }],
      series: [{
        type: 'line', data: scores, smooth: true, symbol: 'circle', symbolSize: 5,
        lineStyle: { width: 3, color: '#6366f1' },
        areaStyle: { color: new echarts.graphic.LinearGradient(0,0,0,1, [{ offset:0, color:'rgba(99,102,241,0.25)' }, { offset:1, color:'rgba(99,102,241,0.02)' }]) },
        itemStyle: { color: p => p.dataIndex === scores.length - 1 ? '#ef4444' : '#6366f1' },
        markLine: {
          data: [
            { xAxis: '2017', label: { formatter: 'Transformer', color: '#ef4444', fontSize: 10 }, lineStyle: { color: '#ef4444', type: 'dashed' } },
            { xAxis: '2022', label: { formatter: 'ChatGPT', color: '#f59e0b', fontSize: 10 }, lineStyle: { color: '#f59e0b', type: 'dashed' } }
          ]
        },
        markPoint: {
          data: [
            { coord: ['2006', yearlyImpact.value.find(d => d.year===2006)?.score], name: '深度学习', symbol: 'pin', symbolSize: 36, itemStyle: { color: '#f59e0b' } },
            { coord: ['2012', yearlyImpact.value.find(d => d.year===2012)?.score], name: 'AlexNet', symbol: 'pin', symbolSize: 36, itemStyle: { color: '#ef4444' } },
            { coord: ['2020', yearlyImpact.value.find(d => d.year===2020)?.score], name: 'GPT-3', symbol: 'pin', symbolSize: 36, itemStyle: { color: '#10b981' } }
          ]
        }
      }]
    })
  })
}

onMounted(async () => {
  try {
    const res = await getTrendAnalysis()
    const d = res.data || {}
    if (d.yearly_impact?.length) yearlyImpact.value = d.yearly_impact
    if (d.summary) summaryStats.value = d.summary
    if (d.categories?.length) categories.value = d.categories
    if (d.lifecycle_stages?.length) lifecycleStages.value = d.lifecycle_stages
    if (d.milestones?.length) milestones.value = d.milestones
  } catch { ElMessage.info('使用离线趋势数据') }
  finally { renderChart() }
})

onUnmounted(() => { if (trendChart) trendChart.dispose() })
</script>

<style scoped>
.trend-page { max-width: 1100px; margin: 0 auto; padding: 0 4px; }

/* Hero */
.hero-section { position: relative; border-radius: 20px; overflow: hidden; margin-bottom: 24px; padding: 48px 40px; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #0c0a3e 0%, #1e1b4b 50%, #312e81 100%); }
.hero-content { position: relative; z-index: 1; text-align: center; color: #fff; }
.hero-badge { display: inline-block; padding: 4px 16px; border-radius: 20px; background: rgba(255,255,255,0.12); font-size: 12px; letter-spacing: 1px; margin-bottom: 14px; backdrop-filter: blur(4px); }
.hero-content h1 { font-size: 36px; font-weight: 700; margin: 0 0 8px; }
.hero-desc { font-size: 15px; opacity: 0.8; margin: 0; }

/* Stats */
.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #fff; border-radius: 14px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.05); transition: transform 0.2s; }
.stat-card:hover { transform: translateY(-2px); }
.stat-val { display: block; font-size: 26px; font-weight: 700; color: #1e293b; }
.stat-lbl { display: block; font-size: 13px; color: #94a3b8; margin-top: 4px; }

/* Chart */
.chart-card { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); margin-bottom: 24px; }
.chart-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.chart-title { font-size: 16px; font-weight: 600; color: #1e293b; }
.chart-range { font-size: 13px; color: #94a3b8; }

/* Categories */
.cat-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 16px; margin-bottom: 24px; }
.cat-card { background: #fff; border-radius: 14px; padding: 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); transition: all 0.2s; }
.cat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.06); }
.cat-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.cat-name { font-size: 15px; font-weight: 600; color: #1e293b; }
.cat-count { font-size: 12px; color: #94a3b8; background: #f1f5f9; padding: 1px 10px; border-radius: 10px; }
.cat-desc { font-size: 13px; color: #64748b; line-height: 1.6; margin: 0 0 12px; }
.cat-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.cat-tag { padding: 2px 10px; border-radius: 6px; font-size: 11px; background: #f1f5f9; color: #475569; }

/* Lifecycle */
.lifecycle-wrap { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); margin-bottom: 24px; }
.lc-header { font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 20px; }
.lc-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.lc-card { border-radius: 12px; padding: 20px; background: #f8fafc; border-top: 3px solid var(--accent); }
.lc-badge { display: inline-block; padding: 2px 14px; border-radius: 6px; color: #fff; font-size: 13px; font-weight: 600; margin-bottom: 10px; }
.lc-desc { font-size: 13px; color: #64748b; line-height: 1.7; margin: 0 0 14px; }
.lc-techs { display: flex; flex-wrap: wrap; gap: 6px; }
.lc-tech { padding: 2px 10px; border-radius: 16px; font-size: 11px; border: 1px solid; }

/* Milestones */
.milestone-wrap { background: #fff; border-radius: 16px; padding: 28px; box-shadow: 0 1px 4px rgba(0,0,0,0.05); margin-bottom: 24px; }
.ms-header { font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 24px; }
.ms-timeline { position: relative; padding-left: 20px; }
.ms-timeline::before { content: ''; position: absolute; left: 8px; top: 0; bottom: 0; width: 2px; background: #e2e8f0; }
.ms-item { position: relative; padding: 0 0 24px 28px; display: flex; }
.ms-item.major { }
.ms-dot { position: absolute; left: -16px; top: 4px; width: 14px; height: 14px; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 0 2px currentColor; }
.ms-body { flex: 1; }
.ms-era { font-size: 12px; font-weight: 600; color: #6366f1; margin-bottom: 2px; }
.ms-title { margin: 0 0 4px; font-size: 15px; font-weight: 600; color: #1e293b; display: flex; align-items: center; gap: 8px; }
.ms-badge { padding: 0 8px; border-radius: 4px; font-size: 10px; background: #fef2f2; color: #ef4444; font-weight: 600; }
.ms-desc { font-size: 13px; color: #64748b; line-height: 1.6; margin: 0; }
</style>
