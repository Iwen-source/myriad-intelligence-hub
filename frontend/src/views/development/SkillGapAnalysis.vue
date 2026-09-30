<template>
  <div class="skillgap-page">
    <!-- Hero -->
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">AI 技能诊断</div>
        <h1>技能差距分析</h1>
        <p class="hero-desc">选择目标岗位，评估当前技能，AI 精准定位你的成长空间</p>
      </div>
    </div>

    <!-- Query Card -->
    <div class="query-card">
      <div class="role-selector">
        <span class="role-label">🎯 目标岗位</span>
        <div class="role-options">
          <div v-for="opt in roleOptions" :key="opt.value" class="role-opt"
            :class="{ active: targetRole === opt.value }" @click="selectRole(opt.value)">
            <span class="role-icon">{{ opt.icon }}</span>
            <span>{{ opt.label }}</span>
          </div>
        </div>
      </div>

      <transition name="fade">
        <div v-if="targetRole" class="skill-board">
          <div class="board-header">
            <span class="board-title">📊 当前技能评估</span>
            <span class="board-hint">拖动滑块调整熟练度（0-5）</span>
          </div>
          <div class="board-grid">
            <div v-for="(label, skill) in currentSkills" :key="skill" class="board-item">
              <div class="board-label">{{ label }}</div>
              <div class="board-slider">
                <el-slider v-model="currentSkills[skill]" :min="0" :max="5" :step="1" show-stops />
                <span class="board-badge" :style="{ background: getLevelColor(currentSkills[skill]) }">{{ currentSkills[skill] }}</span>
              </div>
            </div>
          </div>

          <button class="btn-primary" :class="{ loading }" @click="submitAnalysis" :disabled="loading">
            {{ loading ? '⏳ 分析中...' : '🔍 分析技能差距' }}
          </button>
        </div>
      </transition>
    </div>

    <!-- Results -->
    <transition name="fade">
      <div v-if="showResult" class="results-area">
        <!-- Mastery Ring + Radar -->
        <div class="viz-row">
          <div class="mastery-card">
            <div class="ring-wrap">
              <svg viewBox="0 0 120 120" class="ring-svg">
                <circle cx="60" cy="60" r="52" fill="none" stroke="#e2e8f0" stroke-width="8" />
                <circle cx="60" cy="60" r="52" fill="none" :stroke="masteryColor" stroke-width="8"
                  stroke-linecap="round" :stroke-dasharray="`${(overallMastery / 100) * 326.7} 326.7`"
                  transform="rotate(-90 60 60)" class="ring-circle" />
              </svg>
              <div class="ring-text">
                <span class="ring-value">{{ Math.round(overallMastery) }}%</span>
                <span class="ring-label">综合掌握度</span>
              </div>
            </div>
            <div class="mastery-footer">
              <span class="mastery-role">{{ targetRole }}</span>
            </div>
          </div>
          <div class="radar-card">
            <div ref="radarRef" style="width:100%;height:340px"></div>
          </div>
        </div>

        <!-- Gap Table -->
        <div class="gap-table-wrap">
          <div class="table-head">
            <span class="table-title">📋 详细差距</span>
            <span class="table-hint">按差距从大到小排序</span>
          </div>
          <div class="gap-list">
            <div v-for="row in gapData" :key="row.skill_name" class="gap-row">
              <div class="gap-left">
                <span v-if="row.gap <= 0" class="gap-icon ok">✅</span>
                <span v-else class="gap-icon warn">⚠️</span>
                <span class="gap-skill">{{ row.skill_name }}</span>
              </div>
              <div class="gap-mid">
                <span class="gap-label">当前</span>
                <div class="mini-bar" :style="{ width: (row.current_level / 5) * 100 + '%', background: getLevelColor(row.current_level) }"></div>
                <span class="gap-num">{{ row.current_level }}/5</span>
              </div>
              <div class="gap-mid">
                <span class="gap-label">目标</span>
                <div class="mini-bar" :style="{ width: (row.target_level / 5) * 100 + '%', background: '#6366f1' }"></div>
                <span class="gap-num">{{ row.target_level }}/5</span>
              </div>
              <div class="gap-right">
                <span class="diff-badge" :class="{ gap: row.gap > 0 }">
                  {{ row.gap > 0 ? '+'+ row.gap.toFixed(1) : '达标' }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, reactive, nextTick, onUnmounted } from 'vue'
import { analyzeSkillGap } from '@/api/modules/development'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'

const roleOptions = [
  { label: '全栈开发工程师', value: '全栈开发工程师', icon: '🌐' },
  { label: '后端开发工程师', value: '后端开发工程师', icon: '⚙️' },
  { label: 'AI/ML 工程师', value: 'AI/ML工程师', icon: '🤖' },
  { label: '数据科学家', value: '数据科学家', icon: '📊' },
  { label: 'DevOps 工程师', value: 'DevOps工程师', icon: '🔧' }
]

const roleSkillMap = {
  '全栈开发工程师': { 'Vue.js/React': 'Vue.js/React', 'Node.js': 'Node.js', 'Spring Boot': 'Spring Boot', MySQL: 'MySQL', Docker: 'Docker', Git: 'Git', JavaScript: 'JavaScript' },
  '后端开发工程师': { Java: 'Java', 'Spring Boot': 'Spring Boot', MySQL: 'MySQL', Redis: 'Redis', Docker: 'Docker', Git: 'Git', Linux: 'Linux' },
  'AI/ML工程师': { Python: 'Python', 机器学习: '机器学习', 深度学习: '深度学习', TensorFlow: 'PyTorch', 数据处理: '数据处理', Linux: 'Linux', Docker: 'Docker', 统计学: '统计学' },
  '数据科学家': { Python: 'Python', SQL: 'SQL', 统计学: '统计学', 机器学习: '机器学习', 数据可视化: '数据可视化', 大数据: '大数据' },
  'DevOps工程师': { Docker: 'Docker', Kubernetes: 'K8s', 'CI/CD': 'CI/CD', Linux: 'Linux', Python: 'Python', 云平台: '云平台' }
}

const roleRequirements = {
  '全栈开发工程师': { 'Vue.js/React': 4, 'Node.js': 3, 'Spring Boot': 3, MySQL: 3, Docker: 3, Git: 3, JavaScript: 4 },
  '后端开发工程师': { Java: 4, 'Spring Boot': 4, MySQL: 3, Redis: 3, Docker: 3, Git: 3, Linux: 3 },
  'AI/ML工程师': { Python: 5, 机器学习: 4, 深度学习: 4, TensorFlow: 4, 数据处理: 4, Linux: 3, Docker: 3, 统计学: 3 },
  '数据科学家': { Python: 4, SQL: 3, 统计学: 4, 机器学习: 4, 数据可视化: 3, 大数据: 3 },
  'DevOps工程师': { Docker: 5, Kubernetes: 4, 'CI/CD': 4, Linux: 4, Python: 3, 云平台: 3 }
}

const targetRole = ref('')
const currentSkills = reactive({})
const loading = ref(false)
const showResult = ref(false)
const overallMastery = ref(0)
const gapData = ref([])
const radarRef = ref(null)
let radarChart = null
const masteryColor = '#6366f1'

function getLevelColor(v) { return v >= 4 ? '#10b981' : v >= 2 ? '#f59e0b' : '#ef4444' }

function selectRole(role) {
  targetRole.value = role
  showResult.value = false
  const keys = Object.keys(roleSkillMap[role] || {})
  const n = {}
  keys.forEach(k => { n[k] = 2 })
  Object.assign(currentSkills, n)
}

function buildGapData(analysis) {
  const reqs = roleRequirements[targetRole.value] || {}
  const current = analysis.current_skills || {}
  const rows = []
  let totalTarget = 0, totalCurr = 0
  Object.keys(reqs).forEach(skill => {
    const cur = current[skill] ?? 2
    const tgt = reqs[skill] || 3
    totalTarget += tgt
    totalCurr += Math.min(cur, tgt)
    rows.push({ skill_name: skill, current_level: cur, target_level: tgt, gap: Math.max(0, tgt - cur) })
  })
  rows.sort((a, b) => b.gap - a.gap)
  overallMastery.value = totalTarget > 0 ? +(totalCurr / totalTarget * 100).toFixed(1) : 0
  return rows
}

function renderRadar(rows) {
  const reqs = roleRequirements[targetRole.value] || {}
  const skills = Object.keys(reqs)
  const currentValues = skills.map(s => { const r = rows.find(x => x.skill_name === s); return r ? r.current_level : 0 })
  const targetValues = skills.map(s => reqs[s] || 3)
  nextTick(() => {
    if (radarChart) radarChart.dispose()
    if (!radarRef.value) return
    radarChart = echarts.init(radarRef.value)
    radarChart.setOption({
      radar: { indicator: skills.map(s => ({ name: s, max: 5 })), shape: 'polygon', splitNumber: 5, axisName: { color: '#475569', fontSize: 11 } },
      series: [{
        type: 'radar',
        data: [
          { value: currentValues, name: '当前水平', areaStyle: { color: 'rgba(99,102,241,0.2)' }, lineStyle: { color: '#6366f1', width: 2 }, itemStyle: { color: '#6366f1' } },
          { value: targetValues, name: '目标水平', areaStyle: { color: 'rgba(239,68,68,0.12)' }, lineStyle: { color: '#ef4444', width: 2, type: 'dashed' }, itemStyle: { color: '#ef4444' } }
        ]
      }],
      tooltip: { trigger: 'item' },
      legend: { data: ['当前水平', '目标水平'], bottom: 0, textStyle: { fontSize: 12 } }
    })
  })
}

async function submitAnalysis() {
  if (!targetRole.value) { ElMessage.warning('请先选择目标岗位'); return }
  loading.value = true
  try {
    const res = await analyzeSkillGap({ current_skills: { ...currentSkills }, target_role: targetRole.value })
    const data = res.data || {}
    gapData.value = buildGapData(data)
    renderRadar(gapData.value)
    showResult.value = true
    ElMessage.success('分析完成')
  } catch {
    const current = {}
    Object.keys(roleRequirements[targetRole.value] || {}).forEach(s => { current[s] = currentSkills[s] ?? 2 })
    gapData.value = buildGapData({ current_skills: current, target_role: targetRole.value })
    renderRadar(gapData.value)
    showResult.value = true
    ElMessage.info('使用离线数据')
  } finally { loading.value = false }
}

onUnmounted(() => { if (radarChart) radarChart.dispose() })
</script>

<style scoped>
.skillgap-page { max-width: 1100px; margin: 0 auto; padding: 0 4px; }
.hero-section { position: relative; border-radius: 20px; overflow: hidden; margin-bottom: 28px; padding: 48px 40px; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #0f172a, #1e293b, #334155); }
.hero-content { position: relative; z-index: 1; text-align: center; color: #fff; }
.hero-badge { display: inline-block; padding: 4px 16px; border-radius: 20px; background: rgba(255,255,255,0.1); font-size: 12px; letter-spacing: 1px; margin-bottom: 16px; backdrop-filter: blur(4px); }
.hero-content h1 { font-size: 36px; font-weight: 700; margin: 0 0 8px; }
.hero-desc { font-size: 15px; opacity: 0.8; margin: 0; }

.query-card { background: #fff; border-radius: 16px; padding: 28px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 28px; }
.role-selector { margin-bottom: 20px; }
.role-label { display: block; font-size: 15px; font-weight: 600; color: #1e293b; margin-bottom: 12px; }
.role-options { display: flex; flex-wrap: wrap; gap: 10px; }
.role-opt { padding: 10px 18px; border-radius: 12px; background: #f8fafc; border: 1.5px solid #e2e8f0; cursor: pointer; display: flex; align-items: center; gap: 8px; font-size: 14px; font-weight: 500; color: #475569; transition: all 0.2s; }
.role-opt:hover { border-color: #a5b4fc; background: #eef2ff; }
.role-opt.active { border-color: #6366f1; background: #eef2ff; color: #4338ca; box-shadow: 0 0 0 3px rgba(99,102,241,0.12); }
.role-icon { font-size: 18px; }

.skill-board { border-top: 1px solid #e2e8f0; padding-top: 20px; }
.board-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.board-title { font-size: 16px; font-weight: 600; color: #1e293b; }
.board-hint { font-size: 13px; color: #94a3b8; }
.board-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; }
.board-item { padding: 6px 0; }
.board-label { font-size: 14px; font-weight: 500; color: #334155; margin-bottom: 4px; }
.board-slider { display: flex; align-items: center; gap: 10px; }
.board-slider :deep(.el-slider) { flex: 1; }
.board-slider :deep(.el-slider__runway) { height: 5px; }
.board-slider :deep(.el-slider__bar) { height: 5px; }
.board-badge { min-width: 26px; height: 26px; border-radius: 7px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 12px; font-weight: 700; }

.btn-primary { display: block; width: 100%; margin-top: 20px; padding: 14px; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; color: #fff; cursor: pointer; background: linear-gradient(135deg, #6366f1, #8b5cf6); transition: all 0.3s; }
.btn-primary:hover { box-shadow: 0 8px 24px rgba(99,102,241,0.35); transform: translateY(-1px); }
.btn-primary.loading { opacity: 0.7; pointer-events: none; }

/* Results */
.results-area { margin-top: 8px; }
.viz-row { display: flex; gap: 20px; margin-bottom: 24px; }
.mastery-card { flex: 0 0 220px; background: #fff; border-radius: 16px; padding: 28px 20px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ring-wrap { position: relative; width: 140px; height: 140px; }
.ring-svg { width: 100%; height: 100%; }
.ring-circle { transition: stroke-dasharray 0.8s ease; }
.ring-text { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; }
.ring-value { font-size: 28px; font-weight: 700; color: #1e293b; }
.ring-label { font-size: 12px; color: #94a3b8; margin-top: 2px; }
.mastery-footer { margin-top: 16px; }
.mastery-role { font-size: 13px; color: #6366f1; font-weight: 500; background: #eef2ff; padding: 4px 14px; border-radius: 8px; }

.radar-card { flex: 1; background: #fff; border-radius: 16px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }

.gap-table-wrap { background: #fff; border-radius: 16px; padding: 24px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); }
.table-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.table-title { font-size: 16px; font-weight: 600; color: #1e293b; }
.table-hint { font-size: 13px; color: #94a3b8; }

.gap-list { display: flex; flex-direction: column; gap: 6px; }
.gap-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border-radius: 10px; background: #f8fafc; transition: background 0.2s; }
.gap-row:hover { background: #f1f5f9; }
.gap-left { flex: 0 0 160px; display: flex; align-items: center; gap: 8px; }
.gap-icon { font-size: 14px; }
.gap-skill { font-size: 14px; font-weight: 500; color: #334155; }
.gap-mid { flex: 1; display: flex; align-items: center; gap: 8px; }
.gap-label { font-size: 11px; color: #94a3b8; min-width: 24px; }
.mini-bar { height: 6px; border-radius: 4px; transition: width 0.4s ease; }
.gap-num { font-size: 12px; color: #475569; min-width: 28px; }
.gap-right { flex: 0 0 70px; text-align: right; }
.diff-badge { padding: 2px 12px; border-radius: 8px; font-size: 12px; font-weight: 600; color: #10b981; background: #ecfdf5; }
.diff-badge.gap { color: #ef4444; background: #fef2f2; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
