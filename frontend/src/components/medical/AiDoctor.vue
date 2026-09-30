<template>
  <div class="ai-doctor-panel">
    <el-alert title="AI 智能问诊（大模型驱动）" type="success" :closable="false" show-icon style="margin-bottom:16px">
      <template #default>
        填写患者信息后，点击「开始诊断」由大模型进行智能分析。诊断结果仅供参考，不构成医疗建议。
      </template>
    </el-alert>

    <el-row :gutter="16">
      <el-col :span="10">
        <el-card>
          <template #header><span><el-icon><ChatDotSquare /></el-icon> 问诊表单</span></template>
          <el-form :model="form" label-width="80px">
            <el-form-item label="患者">
              <el-select v-model="selectedPatientId" filterable placeholder="选择已有患者" style="width:100%" @change="fillInfo">
                <el-option v-for="p in patients" :key="p.patientId" :label="`${p.name} (${p.patientId})`" :value="p.patientId" />
              </el-select>
            </el-form-item>
            <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
            <el-form-item label="年龄"><el-input-number v-model="form.age" :min="0" :max="150" /></el-form-item>
            <el-form-item label="性别">
              <el-radio-group v-model="form.gender"><el-radio value="男">男</el-radio><el-radio value="女">女</el-radio></el-radio-group>
            </el-form-item>
            <el-form-item label="症状"><el-input v-model="form.symptoms" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="持续天数"><el-input-number v-model="form.durationDays" :min="1" :max="365" /></el-form-item>
            <el-form-item label="既往病史"><el-input v-model="form.history" type="textarea" :rows="2" /></el-form-item>
            <el-form-item label="用药情况"><el-input v-model="form.medications" type="textarea" :rows="2" /></el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="consulting" @click="consult">🧠 开始诊断</el-button>
              <el-button @click="resetForm">重置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      <el-col :span="14">
        <el-card>
          <template #header><span><el-icon><Document /></el-icon> 诊断报告</span></template>
          <div v-if="loading" style="text-align:center;padding:40px"><el-progress type="circle" :percentage="80" :stroke-width="6" status="active" /></div>
          <div v-else-if="report" class="report-content" v-html="report" />
          <el-empty v-else description="填写左侧表单后开始诊断" :image-size="80" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { ChatDotSquare, Document } from '@element-plus/icons-vue'
import { aiConsult, getPatients } from '../../api/modules'

const props = defineProps({
  /** 从患者管理传来的预设患者信息 */
  presetForm: { type: Object, default: null }
})

const patients = ref([])
const selectedPatientId = ref('')
const form = ref({ name: '', age: 30, gender: '男', symptoms: '', durationDays: 3, history: '', medications: '' })
const consulting = ref(false)
const loading = ref(false)
const report = ref(null)

function fillInfo(id) {
  const p = patients.value.find(p => p.patientId === id)
  if (p) {
    form.value = { name: p.name, age: p.age, gender: p.gender, symptoms: p.symptoms, durationDays: 3, history: '', medications: '' }
  }
}

function resetForm() {
  form.value = { name: '', age: 30, gender: '男', symptoms: '', durationDays: 3, history: '', medications: '' }
  report.value = null
  selectedPatientId.value = ''
}

async function consult() {
  if (!form.value.symptoms) { ElMessage.warning('请填写症状描述'); return }
  consulting.value = true
  loading.value = true
  report.value = null
  try {
    const res = await aiConsult(form.value)
    report.value = renderDiagnosisReport(res.data || res)
  } catch (e) {
    ElMessage.error('诊断失败，请重试')
    report.value = `<div style="color:#f56c6c;padding:20px">诊断服务暂时不可用，请稍后重试。</div>`
  } finally {
    consulting.value = false
    loading.value = false
  }
}

onMounted(async () => {
  try {
    const res = await getPatients()
    patients.value = res.data || []
  } catch { /* ignore */ }
  if (props.presetForm) {
    form.value = { ...form.value, ...props.presetForm }
  }
})

// 渲染诊断报告HTML — 兼容两种后端格式
function renderDiagnosisReport(data) {
  if (!data) return '<div class="report-empty">无诊断结果</div>'

  // 格式1: MedicalAiDoctorService 的 consult() 返回格式
  if (data.primaryDiagnosis) {
    let html = ''
    html += renderSourceBanner(data)

    // 顶部诊断摘要卡片
    html += '<div class="diagnosis-header">'
    html += `  <div class="diag-main"><span class="diag-icon">🏥</span><span class="diag-title">主要诊断</span></div>`
    html += `  <div class="diag-result">${escHtml(data.primaryDiagnosis)}</div>`
    if (data.recommendedDepartment) {
      html += `  <div class="diag-dept"><span class="dept-badge">🩺 建议科室</span> ${escHtml(data.recommendedDepartment)}</div>`
    }
    html += '</div>'

    // 可能诊断列表
    if (data.possibleDiagnoses && data.possibleDiagnoses.length) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">📋 可能诊断</div>'
      html += '  <div class="diag-list">'
      data.possibleDiagnoses.forEach(d => {
        const typeClass = d.type === '主要诊断' ? 'type-primary' : d.type === '鉴别诊断' ? 'type-diff' : 'type-possible'
        const sevClass = d.severity === '高' ? 'sev-high' : d.severity === '中' ? 'sev-mid' : 'sev-low'
        html += `    <div class="diag-item ${typeClass}">`
        html += `      <div class="diag-name">${escHtml(d.diseaseName)}</div>`
        html += `      <div class="diag-meta">`
        html += `        <span class="confidence-tag">置信度 ${escHtml(String(d.confidence))}%</span>`
        html += `        <span class="sev-tag ${sevClass}">${escHtml(d.severity || '—')}</span>`
        html += `        <span class="type-tag">${escHtml(d.type || '—')}</span>`
        html += `      </div>`
        if (d.explanation) html += `      <div class="diag-reason">💡 ${escHtml(d.explanation)}</div>`
        html += '    </div>'
      })
      html += '  </div>'
      html += '</div>'
    }

    // 检查建议
    if (data.recommendedExams && data.recommendedExams.length) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">🔬 建议检查项目</div>'
      html += '  <ul class="exam-list">'
      data.recommendedExams.forEach(e => { html += `    <li>${escHtml(e)}</li>` })
      html += '  </ul>'
      html += '</div>'
    }

    // 治疗方案
    if (data.treatment) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">💊 治疗方案</div>'
      if (data.treatment.general) {
        html += '  <ul class="treatment-list">'
        data.treatment.general.forEach(t => { html += `    <li>${escHtml(t)}</li>` })
        html += '  </ul>'
      }
      if (data.treatment.typicalDuration && data.treatment.durationUnit) {
        html += `  <div class="duration-info">⏱ 典型病程：约 ${escHtml(data.treatment.typicalDuration)} ${escHtml(data.treatment.durationUnit)}</div>`
      }
      html += '</div>'
    }

    // 推荐用药
    if (data.recommendedMedications && data.recommendedMedications.length) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">💊 推荐用药</div>'
      html += '  <div class="med-grid">'
      data.recommendedMedications.forEach(m => {
        html += '    <div class="med-item">'
        html += `      <div class="med-name">${escHtml(m)}</div>`
        html += '    </div>'
      })
      html += '  </div>'
      html += '</div>'
    }

    // 生活建议
    if (data.lifestyleAdvice && data.lifestyleAdvice.length) {
      html += '<div class="section-card lifestyle">'
      html += '  <div class="section-title">🌿 生活建议</div>'
      html += '  <ul class="life-list">'
      data.lifestyleAdvice.forEach(a => { html += `    <li>${escHtml(a)}</li>` })
      html += '  </ul>'
      html += '</div>'
    }

    // 就医提醒
    if (data.whenToSeeDoctor) {
      html += `<div class="warning-banner">${escHtml(data.whenToSeeDoctor)}</div>`
    }

    // 总述
    if (data.summary) {
      html += '<div class="section-card summary-card">'
      html += `  <div class="summary-text">${escHtml(data.summary)}</div>`
      html += '</div>'
    }

    // 免责声明
    html += `<div class="disclaimer">${escHtml(data.disclaimer || '⚠️ 本诊断结果由AI辅助生成，仅供参考，请以线下医生的专业诊断为准。')}</div>`

    return html
  }

  // 格式2: MedicalAiModelService 的 consult() 返回格式 (DeepSeek API / fallback)
  if (data.possibleDiseases || data.analysisText) {
    let html = ''
    html += renderSourceBanner(data)

    // 严重程度
    if (data.severity) {
      const sevClass = data.severity.level === '轻' ? 'sev-low' : data.severity.level === '中' ? 'sev-mid' : data.severity.level === '重' || data.severity.level === '紧急' ? 'sev-high' : ''
      html += `<div class="diagnosis-header">`
      html += `  <div class="severity-badge ${sevClass}">💡 严重程度：${escHtml(data.severity.level)}</div>`
      html += `  <div class="sev-desc">${escHtml(data.severity.description || '')}</div>`
      html += '</div>'
    }

    // 分析
    if (data.analysisText) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">📝 诊断分析</div>'
      html += `  <div class="analysis-text">${escHtml(data.analysisText)}</div>`
      html += '</div>'
    }

    // 可能疾病
    if (data.possibleDiseases && data.possibleDiseases.length) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">📋 可能疾病</div>'
      html += '  <div class="diag-list">'
      data.possibleDiseases.forEach(d => {
        const probClass = d.probability === '高' ? 'prob-high' : d.probability === '中' ? 'prob-mid' : 'prob-low'
        html += '    <div class="diag-item-simple">'
        html += `      <span class="disease-name">${escHtml(d.name)}</span>`
        html += `      <span class="prob-tag ${probClass}">${escHtml(d.probability)}</span>`
        html += `      <span class="disease-reason">${escHtml(d.reason || '')}</span>`
        html += '    </div>'
      })
      html += '  </div>'
      html += '</div>'
    }

    // 用药
    if (data.medications && data.medications.length) {
      html += '<div class="section-card">'
      html += '  <div class="section-title">💊 推荐用药</div>'
      html += '  <div class="med-grid">'
      data.medications.forEach(m => {
        html += '    <div class="med-item">'
        html += `      <div class="med-name">${escHtml(m.name || '')}</div>`
        if (m.usage) html += `      <div class="med-usage">用法：${escHtml(m.usage)}</div>`
        if (m.note) html += `      <div class="med-note">注意：${escHtml(m.note)}</div>`
        html += '    </div>'
      })
      html += '  </div>'
      html += '</div>'
    }

    // 护理建议
    if (data.care) {
      html += '<div class="section-card lifestyle">'
      html += '  <div class="section-title">🌿 护理建议</div>'
      if (data.care.diet) html += `  <div class="care-item"><span class="care-label">🍜 饮食：</span>${escHtml(data.care.diet)}</div>`
      if (data.care.rest) html += `  <div class="care-item"><span class="care-label">😴 作息：</span>${escHtml(data.care.rest)}</div>`
      if (data.care.nursing) html += `  <div class="care-item"><span class="care-label">🏡 护理：</span>${escHtml(data.care.nursing)}</div>`
      html += '</div>'
    }

    // 就医时机
    if (data.whenToSeeDoctor) {
      html += `<div class="warning-banner">${escHtml(data.whenToSeeDoctor)}</div>`
    }

    // 总结
    if (data.summary) {
      html += '<div class="section-card summary-card">'
      html += `  <div class="summary-text">${escHtml(data.summary)}</div>`
      html += '</div>'
    } else if (data.analysis && data.analysis.analysis) {
      html += '<div class="section-card summary-card">'
      html += `  <div class="summary-text">${escHtml(data.analysis.analysis)}</div>`
      html += '</div>'
    }

    // 免责声明
    html += `<div class="disclaimer">${escHtml(data.disclaimer || '⚠️ 本诊断结果由AI辅助生成，仅供参考，请以线下医生的专业诊断为准。')}</div>`

    return html
  }

  // 兜底
  return `<div class="report-empty">诊断结果格式异常，无法展示</div>`
}

// HTML转义函数
// 来源标注条：诚实区分大模型 / 本地知识库规则，避免伪AI
function renderSourceBanner(data) {
  const src = String(data?.source || '').toLowerCase()
  let label, cls
  if (src.includes('deepseek') || src.includes('llm')) {
    label = '🧠 大模型生成（DeepSeek）'; cls = 'src-ml'
  } else if (data?.isMlGenerated === true) {
    label = '🧠 ML模型生成'; cls = 'src-ml'
  } else {
    label = '📚 本地知识库规则'; cls = 'src-rule'
  }
  return `<div class="ai-source-banner ${cls}">${label}</div>`
}

function escHtml(str) {
  if (!str) return ''
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;')
}</script>

<style scoped>
.report-content { padding: 4px; line-height: 1.6; font-size: 14px; }

/* 诊断摘要头 */
.diagnosis-header {
  background: linear-gradient(135deg, #e6f7ff, #f0f5ff);
  border: 1px solid #91d5ff;
  border-radius: 10px;
  padding: 16px 20px;
  margin-bottom: 14px;
  position: relative;
  overflow: hidden;
}
.diagnosis-header::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  background: linear-gradient(180deg, #1890ff, #69c0ff);
}
.diag-main { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.diag-icon { font-size: 22px; }
.diag-title { font-weight: 600; font-size: 15px; color: #1890ff; }
.diag-result { font-size: 18px; font-weight: 700; color: #1a1a2e; margin: 4px 0; }
.diag-dept { margin-top: 4px; display: flex; align-items: center; gap: 6px; }
.dept-badge {
  display: inline-block;
  background: #e6f7ff;
  color: #1890ff;
  border: 1px solid #91d5ff;
  padding: 1px 10px;
  border-radius: 12px;
  font-size: 12px;
}

/* 分区卡片 */
.section-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 12px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.04);
  transition: box-shadow 0.2s;
}
.section-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.section-card.lifestyle { border-left: 3px solid #52c41a; }
.section-card.summary-card { background: #fafafa; border: 1px dashed #d9d9d9; }
.section-title {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid #f0f0f0;
}

/* 诊断列表 */
.diag-list { display: flex; flex-direction: column; gap: 8px; }
.diag-item {
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 10px 14px;
  transition: all 0.2s;
}
.diag-item:hover { border-color: #409eff; box-shadow: 0 0 6px rgba(64,158,255,0.12); }
.diag-item.type-primary { border-left: 3px solid #f56c6c; background: #fef0f0; }
.diag-item.type-diff { border-left: 3px solid #e6a23c; background: #fdf6ec; }
.diag-item.type-possible { border-left: 3px solid #909399; }
.diag-name { font-weight: 600; font-size: 14px; color: #303133; }
.diag-meta { display: flex; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
.confidence-tag {
  display: inline-block;
  background: #e6f7ff;
  color: #1890ff;
  padding: 0 8px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 20px;
}
.sev-tag {
  display: inline-block;
  padding: 0 8px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 20px;
}
.sev-high { background: #fef0f0; color: #f56c6c; }
.sev-mid { background: #fdf6ec; color: #e6a23c; }
.sev-low { background: #f0f9eb; color: #67c23a; }
.type-tag {
  display: inline-block;
  background: #f4f4f5;
  color: #909399;
  padding: 0 8px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 20px;
}
.diag-reason { color: #606266; font-size: 12px; margin-top: 4px; padding: 4px 8px; background: #fafafa; border-radius: 6px; }

/* AI模型格式 - 简单版 */
.diag-item-simple {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  margin-bottom: 6px;
}
.disease-name { font-weight: 500; min-width: 80px; }
.prob-tag {
  display: inline-block;
  padding: 0 8px;
  border-radius: 10px;
  font-size: 12px;
  line-height: 20px;
  min-width: 30px;
  text-align: center;
}
.prob-high { background: #fef0f0; color: #f56c6c; }
.prob-mid { background: #fdf6ec; color: #e6a23c; }
.prob-low { background: #f0f9eb; color: #67c23a; }
.disease-reason { color: #909399; font-size: 12px; flex: 1; }

/* 检查列表 */
.exam-list { margin: 0; padding: 0; list-style: none; }
.exam-list li {
  padding: 6px 10px;
  margin-bottom: 4px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
  border-left: 3px solid #409eff;
}

/* 治疗列表 */
.treatment-list { margin: 0; padding: 0; list-style: none; }
.treatment-list li {
  padding: 6px 10px;
  margin-bottom: 4px;
  background: #f0f9eb;
  border-radius: 6px;
  font-size: 13px;
  color: #67c23a;
}
.treatment-list li::before { content: '✅ '; }
.duration-info {
  margin-top: 8px;
  padding: 6px 12px;
  background: #fff7e6;
  border-radius: 6px;
  font-size: 13px;
  color: #d46b08;
}

/* 用药网格 */
.med-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.med-item {
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 10px 12px;
  transition: all 0.2s;
}
.med-item:hover { border-color: #52c41a; background: #f0f9eb; }
.med-name { font-weight: 600; font-size: 13px; color: #303133; }
.med-usage { font-size: 12px; color: #606266; margin-top: 2px; }
.med-note { font-size: 11px; color: #f56c6c; margin-top: 2px; }

/* 生活建议 */
.life-list { margin: 0; padding: 0; list-style: none; }
.life-list li {
  padding: 5px 8px;
  margin-bottom: 3px;
  font-size: 13px;
  color: #303133;
}
.life-list li::before { content: '✅ '; }

/* 护理条目 */
.care-item { font-size: 13px; padding: 6px 0; color: #303133; }
.care-label { font-weight: 500; color: #606266; }

/* 严重程度横幅 */
.severity-badge {
  display: inline-block;
  padding: 4px 14px;
  border-radius: 16px;
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
}
.severity-badge.sev-high { background: #fef0f0; color: #f56c6c; border: 1px solid #f56c6c; }
.severity-badge.sev-mid { background: #fdf6ec; color: #e6a23c; border: 1px solid #e6a23c; }
.severity-badge.sev-low { background: #f0f9eb; color: #67c23a; border: 1px solid #67c23a; }
.sev-desc { color: #606266; font-size: 13px; }

/* 分析文本 */
.analysis-text {
  line-height: 1.8;
  color: #303133;
  font-size: 14px;
  padding: 8px;
  background: #fafafa;
  border-radius: 6px;
}

/* 总述 */
.summary-text { line-height: 1.8; color: #606266; font-size: 13px; }

/* 就医提醒 (warning) */
.warning-banner {
  background: linear-gradient(135deg, #fff2f0, #fff7e6);
  border: 1px solid #ffccc7;
  border-radius: 10px;
  padding: 12px 16px;
  margin-bottom: 12px;
  color: #cf1322;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.warning-banner::before { content: '⚠️'; font-size: 16px; }

/* 免责声明 */
.disclaimer {
  background: #f4f4f5;
  border-radius: 8px;
  padding: 10px 14px;
  font-size: 12px;
  color: #909399;
  text-align: center;
  line-height: 1.6;
  margin-top: 8px;
}

/* 空状态 */
.report-empty { color: #909399; text-align: center; padding: 40px 0; font-size: 14px; }

/* AI 来源标注条 */
.ai-source-banner { font-size: 12px; padding: 6px 12px; border-radius: 6px; margin-bottom: 10px; display: inline-block; }
.ai-source-banner.src-ml { background: #f0f9eb; color: #67c23a; border: 1px solid #e1f3d8; }
.ai-source-banner.src-rule { background: #f4f4f5; color: #909399; border: 1px solid #e9e9eb; }
</style>
