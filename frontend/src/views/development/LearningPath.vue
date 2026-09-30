<template>
  <div class="learn-page">
    <!-- Hero Header -->
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">AI 智能推荐</div>
        <h1>学习路径规划</h1>
        <p class="hero-desc">上传你的技能画像，AI 为你定制专属成长路线</p>
      </div>
    </div>

    <!-- Skill Assessment Card -->
    <div class="assess-card">
      <div class="assess-header">
        <div class="assess-title">
          <span class="title-icon">🎯</span>
          <span>技能评估</span>
        </div>
        <span class="assess-hint">滑动滑块评估你的熟练度（0-5）</span>
      </div>

      <div class="skill-grid">
        <div v-for="(label, skill) in skillDefs" :key="skill" class="skill-item">
          <div class="skill-label">{{ label }}</div>
          <div class="skill-slider-row">
            <el-slider
              v-model="skillLevels[skill]"
              :min="0" :max="5" :step="1" show-stops
              :marks="sliderMarks"
              :format-tooltip="v => v + '级'"
            />
            <span class="skill-badge" :style="{ background: getLevelColor(skillLevels[skill]) }">
              {{ skillLevels[skill] }}
            </span>
          </div>
        </div>
      </div>

      <div class="assess-footer">
        <div class="exp-field">
          <span class="exp-label">📅 工作经验</span>
          <el-input-number v-model="yearsExperience" :min="0" :max="20" :step="1" controls-position="right" />
          <span class="exp-unit">年</span>
        </div>
        <button class="btn-primary" :class="{ loading: loading }" @click="submitAnalysis" :disabled="loading">
          <span v-if="!loading">🚀 生成学习路径</span>
          <span v-else>⏳ 分析中...</span>
        </button>
      </div>
    </div>

    <!-- Results -->
    <div v-if="results.length" class="results-section">
      <div class="results-header">
        <h2>📋 推荐路径</h2>
        <span class="results-count">共 {{ results.length }} 条</span>
      </div>

      <div class="path-list">
        <div v-for="(item, idx) in results" :key="idx" class="path-card" :style="{ '--accent': pathColors[idx] }">
          <div class="path-rank">{{ idx + 1 }}</div>
          <div class="path-body">
            <div class="path-top">
              <h3>{{ item.path_name }}</h3>
              <div class="match-score" :style="{ color: pathColors[idx] }">
                <svg viewBox="0 0 36 36" class="score-ring">
                  <circle cx="18" cy="18" r="15.9" fill="none" stroke="#eee" stroke-width="2.5" />
                  <circle cx="18" cy="18" r="15.9" fill="none" :stroke="pathColors[idx]" stroke-width="2.5"
                    stroke-linecap="round" :stroke-dasharray="`${(item.match_score / 100) * 100} 100`"
                    transform="rotate(-90 18 18)" />
                </svg>
                <span class="score-value">{{ item.match_score }}%</span>
              </div>
            </div>

            <div class="path-meta">
              <span class="meta-chip">🔥 难度 {{ item.difficulty_stars }}/5</span>
              <span class="meta-chip">⏱ {{ item.duration_months }} 个月</span>
            </div>

            <div class="skills-wrap">
              <span class="skills-label">需要学习：</span>
              <span v-for="(s, si) in item.skills_to_learn" :key="si" class="skill-chip"
                :style="{ background: pathColors[idx] + '18', color: pathColors[idx], borderColor: pathColors[idx] + '40' }">
                {{ s }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { recommendLearningPath } from '@/api/modules/development'
import { ElMessage } from 'element-plus'

const skillDefs = {
  Python: 'Python', Java: 'Java', JavaScript: 'JavaScript',
  'Vue.js/React': 'Vue.js / React', 'Spring Boot': 'Spring Boot',
  Docker: 'Docker', MySQL: 'MySQL', 机器学习: '机器学习',
  深度学习: '深度学习', Git: 'Git'
}
const sliderMarks = { 0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5' }

const skillLevels = reactive(Object.fromEntries(Object.keys(skillDefs).map(k => [k, 2])))
const yearsExperience = ref(1)
const loading = ref(false)
const results = ref([])

const pathColors = ['#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b']

function getLevelColor(v) {
  if (v >= 4) return '#10b981'
  if (v >= 2) return '#f59e0b'
  return '#ef4444'
}

function getScoreColor(s) {
  if (s >= 80) return '#10b981'
  if (s >= 60) return '#f59e0b'
  return '#ef4444'
}

const fallbackResults = [
  { path_name: '全栈 AI 工程师', match_score: 85, difficulty_stars: 4, duration_months: 12, skills_to_learn: ['Python', 'Vue.js', 'FastAPI', 'Docker', 'PostgreSQL', 'TensorFlow'] },
  { path_name: 'AI 应用开发入门', match_score: 65, difficulty_stars: 3, duration_months: 8, skills_to_learn: ['Python', 'JavaScript', 'Flask', '机器学习基础', 'REST API'] },
  { path_name: '深度学习研究员', match_score: 45, difficulty_stars: 5, duration_months: 18, skills_to_learn: ['Python', 'PyTorch', 'Transformer', '强化学习', 'CUDA'] },
  { path_name: '数据科学实战', match_score: 72, difficulty_stars: 3, duration_months: 10, skills_to_learn: ['Python', 'Pandas', 'NumPy', 'Matplotlib', 'SQL', 'Scikit-learn'] },
  { path_name: 'DevOps / MLOps', match_score: 55, difficulty_stars: 4, duration_months: 14, skills_to_learn: ['Docker', 'Kubernetes', 'CI/CD', 'MLflow', 'Terraform'] }
]

async function submitAnalysis() {
  loading.value = true
  try {
    const res = await recommendLearningPath({ skill_levels: { ...skillLevels }, years_experience: yearsExperience.value })
    results.value = (res.data || []).slice(0, 5)
    if (!results.value.length) { ElMessage.warning('使用默认推荐'); results.value = fallbackResults.slice(0, 5) }
    else ElMessage.success('学习路径推荐完成')
  } catch { ElMessage.info('使用离线数据'); results.value = fallbackResults.slice(0, 5) }
  finally { loading.value = false }
}
</script>

<style scoped>
.learn-page { max-width: 1100px; margin: 0 auto; padding: 0 4px; }

/* Hero */
.hero-section { position: relative; border-radius: 20px; overflow: hidden; margin-bottom: 28px; padding: 48px 40px; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 40%, #4338ca 100%); }
.hero-content { position: relative; z-index: 1; text-align: center; color: #fff; }
.hero-badge { display: inline-block; padding: 4px 16px; border-radius: 20px; background: rgba(255,255,255,0.15); font-size: 12px; letter-spacing: 1px; margin-bottom: 16px; backdrop-filter: blur(4px); }
.hero-content h1 { font-size: 36px; font-weight: 700; margin: 0 0 8px; }
.hero-desc { font-size: 15px; opacity: 0.8; margin: 0; }

/* Assessment Card */
.assess-card { background: #fff; border-radius: 16px; padding: 28px; box-shadow: 0 1px 4px rgba(0,0,0,0.06); margin-bottom: 28px; }
.assess-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.assess-title { font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.title-icon { font-size: 22px; }
.assess-hint { font-size: 13px; color: #94a3b8; }

.skill-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.skill-item { padding: 8px 0; }
.skill-label { font-size: 14px; font-weight: 500; color: #334155; margin-bottom: 6px; }
.skill-slider-row { display: flex; align-items: center; gap: 12px; }
.skill-slider-row :deep(.el-slider) { flex: 1; }
.skill-slider-row :deep(.el-slider__runway) { height: 6px; }
.skill-slider-row :deep(.el-slider__bar) { height: 6px; }
.skill-badge { min-width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center; color: #fff; font-size: 13px; font-weight: 700; }

.assess-footer { margin-top: 24px; padding-top: 20px; border-top: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px; }
.exp-field { display: flex; align-items: center; gap: 12px; }
.exp-label { font-size: 14px; font-weight: 500; color: #334155; }
.exp-unit { color: #94a3b8; font-size: 13px; }

.btn-primary { padding: 12px 32px; border: none; border-radius: 12px; font-size: 15px; font-weight: 600; color: #fff; cursor: pointer; background: linear-gradient(135deg, #6366f1, #8b5cf6); transition: all 0.3s; }
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(99,102,241,0.35); }
.btn-primary.loading { opacity: 0.7; pointer-events: none; }

/* Results */
.results-section { margin-top: 8px; }
.results-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.results-header h2 { margin: 0; font-size: 20px; font-weight: 700; color: #1e293b; }
.results-count { font-size: 13px; color: #94a3b8; background: #f1f5f9; padding: 2px 12px; border-radius: 12px; }

.path-list { display: flex; flex-direction: column; gap: 16px; }
.path-card { display: flex; background: #fff; border-radius: 16px; overflow: hidden; box-shadow: 0 1px 4px rgba(0,0,0,0.06); transition: all 0.3s; }
.path-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
.path-rank { width: 56px; display: flex; align-items: center; justify-content: center; font-size: 24px; font-weight: 800; color: var(--accent); background: color-mix(in srgb, var(--accent) 8%, transparent); flex-shrink: 0; }
.path-body { flex: 1; padding: 20px 24px; }
.path-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
.path-top h3 { margin: 0 0 10px; font-size: 17px; font-weight: 600; color: #1e293b; }
.match-score { position: relative; width: 48px; height: 48px; flex-shrink: 0; }
.score-ring { width: 100%; height: 100%; }
.score-value { position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-size: 11px; font-weight: 700; }

.path-meta { display: flex; gap: 8px; margin-bottom: 12px; }
.meta-chip { padding: 3px 12px; border-radius: 8px; font-size: 12px; background: #f1f5f9; color: #475569; }

.skills-wrap { display: flex; align-items: center; flex-wrap: wrap; gap: 6px; }
.skills-label { font-size: 13px; color: #94a3b8; margin-right: 4px; }
.skill-chip { padding: 2px 12px; border-radius: 20px; font-size: 12px; border: 1px solid; }
</style>
