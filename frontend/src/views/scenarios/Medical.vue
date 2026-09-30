<template>
  <div class="medical-page">
    <!-- Hero -->
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">🩺 AI 辅助诊疗</div>
        <h1>医疗诊断</h1>
        <p class="hero-desc">AI 智能问诊 · CT影像分析 · 糖尿病风险预测 · 血糖动态预测 · 患者管理</p>
      </div>
    </div>

    <!-- Stats -->
    <div class="stats-row">
      <div class="stat-card" v-for="s in stats" :key="s.label">
        <span class="stat-val">{{ s.value }}</span>
        <span class="stat-lbl">{{ s.label }}</span>
      </div>
    </div>

    <!-- Quick Actions -->
    <div class="quick-actions">
      <div class="action-card" @click="activeTab = 'ai-consult'">
        <span class="action-icon">🤖</span>
        <span class="action-title">AI 智能问诊</span>
        <span class="action-desc">大模型驱动，分析症状给出诊断建议</span>
      </div>
      <div class="action-card" @click="$router.push('/scenarios/ct-workstation')">
        <span class="action-icon">🖥️</span>
        <span class="action-title">CT 影像工作台</span>
        <span class="action-desc">脑CT伪影检测、三维分割、MPR、AI诊断报告</span>
      </div>
      <div class="action-card" @click="$router.push('/scenarios/medical/ml-predictions')">
        <span class="action-icon">📊</span>
        <span class="action-title">糖尿病 &amp; 血糖预测</span>
        <span class="action-desc">基于真实临床数据的 AI 预测模型</span>
      </div>
      <div class="action-card" @click="activeTab = 'patient'">
        <span class="action-icon">👥</span>
        <span class="action-title">患者管理</span>
        <span class="action-desc">管理患者信息与病历档案</span>
      </div>
      <div class="action-card" @click="activeTab = 'disease'">
        <span class="action-icon">📚</span>
        <span class="action-title">疾病知识库</span>
        <span class="action-desc">查询疾病症状、治疗与用药信息</span>
      </div>
    </div>

    <!-- Main Tabs: AI问诊嵌入总览 -->
    <el-card class="detail-card">
      <el-tabs v-model="activeTab" type="border-card">
        <!-- AI 智能问诊 - 默认激活 -->
        <el-tab-pane label="🤖 AI 智能问诊" name="ai-consult">
          <AiDoctor />
        </el-tab-pane>
        <el-tab-pane label="👥 患者管理" name="patient">
          <PatientManagement @ai-consult="handleAiConsult" />
        </el-tab-pane>
        <el-tab-pane label="📋 诊断记录" name="diagnosis">
          <div class="flex-between" style="margin-bottom:12px">
            <span></span>
            <el-button type="success" @click="openDiagDialog">+ 添加诊断</el-button>
          </div>
          <el-table :data="diagnosis" stripe v-loading="loadingDiag" @row-click="showDiagDetail">
            <el-table-column prop="resultId" label="编号" width="90" />
            <el-table-column label="患者" width="100">
              <template #default="{ row }">{{ getPatientName(row.patientId) }}</template>
            </el-table-column>
            <el-table-column prop="diagnosisDate" label="日期" width="120" />
            <el-table-column label="诊断摘要" min-width="280" show-overflow-tooltip>
              <template #default="{ row }">{{ extractSummary(row.diagnosisResult) }}</template>
            </el-table-column>
            <el-table-column label="操作" width="100">
              <template #default="{ row }">
                <el-button size="small" type="danger" link @click.stop="deleteDiag(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="📖 疾病知识库" name="disease">
          <DiseaseLibrary />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- Add Diag Dialog -->
    <el-dialog v-model="showDiagDialog" title="添加诊断记录" width="600px">
      <el-form :model="diagForm" label-width="80px">
        <el-form-item label="患者">
          <el-select v-model="diagForm.patientId" filterable style="width:100%">
            <el-option v-for="p in patients" :key="p.patientId" :label="`${p.name} (${p.patientId})`" :value="p.patientId" />
          </el-select>
        </el-form-item>
        <el-form-item label="诊断日期"><el-date-picker v-model="diagForm.diagnosisDate" type="date" style="width:100%" value-format="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="诊断结果"><el-input v-model="diagForm.diagnosisResult" type="textarea" :rows="6" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDiagDialog = false">取消</el-button>
        <el-button type="primary" @click="submitDiag">保存</el-button>
      </template>
    </el-dialog>

    <!-- Diag Detail -->
    <el-dialog v-model="showDetailDialog" title="诊断详情" width="600px">
      <div style="white-space:pre-wrap;line-height:1.8;font-size:14px;background:#f8f9fa;padding:16px;border-radius:8px">
        {{ currentDetail?.diagnosisResult }}
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import AiDoctor from '../../components/medical/AiDoctor.vue'
import PatientManagement from '../../components/medical/PatientManagement.vue'
import DiseaseLibrary from '../../components/medical/DiseaseLibrary.vue'
import { getPatients, getDiagnosis, saveDiagnosis, deleteDiagnosis as delDiagApi } from '../../api/modules'

const router = useRouter()
const activeTab = ref('ai-consult')  // 默认激活 AI 智能问诊
const patients = ref([])
const diagnosis = ref([])
const loadingDiag = ref(false)
const showDiagDialog = ref(false)
const diagForm = ref({ patientId: '', diagnosisDate: '', diagnosisResult: '' })
const showDetailDialog = ref(false)
const currentDetail = ref(null)

const stats = [
  { label: '患者总数', value: '--' },
  { label: '诊断记录', value: '--' },
  { label: 'AI 模型', value: '3' },
  { label: '疾病库', value: '50+' }
]

function handleAiConsult(patient) { activeTab.value = 'ai-consult' }
function getPatientName(pid) { return patients.value.find(p => p.patientId === pid)?.name || pid }
function extractSummary(text) { return text ? (text.length > 50 ? text.slice(0, 50) + '...' : text) : '' }

async function loadData() {
  try {
    const [pRes, dRes] = await Promise.all([getPatients(), getDiagnosis()])
    patients.value = pRes.data || []
    diagnosis.value = dRes.data || []
    stats[0].value = patients.value.length || '--'
    stats[1].value = diagnosis.value.length || '--'
  } catch {}
}
function openDiagDialog() { diagForm.value = { patientId: '', diagnosisDate: '', diagnosisResult: '' }; showDiagDialog.value = true }
async function submitDiag() {
  try { await saveDiagnosis(diagForm.value); ElMessage.success('保存成功'); showDiagDialog.value = false; loadData() }
  catch { ElMessage.error('保存失败') }
}
async function deleteDiag(row) {
  try { await delDiagApi(row.resultId); ElMessage.success('已删除'); loadData() }
  catch { ElMessage.error('删除失败') }
}
function showDiagDetail(row) { currentDetail.value = row; showDetailDialog.value = true }
onMounted(loadData)
</script>

<style scoped>
.medical-page { max-width: 1100px; margin: 0 auto; padding: 0 4px; }
.hero-section { position: relative; border-radius: 20px; overflow: hidden; margin-bottom: 24px; padding: 48px 40px; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #14532d 0%, #166534 40%, #059669 100%); }
.hero-content { position: relative; z-index: 1; text-align: center; color: #fff; }
.hero-badge { display: inline-block; padding: 4px 16px; border-radius: 20px; background: rgba(255,255,255,0.15); font-size: 12px; letter-spacing: 1px; margin-bottom: 14px; }
.hero-content h1 { font-size: 36px; font-weight: 700; margin: 0 0 8px; }
.hero-desc { font-size: 15px; opacity: 0.8; margin: 0; }

.stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
.stat-card { background: #fff; border-radius: 14px; padding: 20px; text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,0.05); }
.stat-val { display: block; font-size: 26px; font-weight: 700; color: #1e293b; }
.stat-lbl { display: block; font-size: 13px; color: #94a3b8; margin-top: 4px; }

.quick-actions { display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px; margin-bottom: 24px; }
@media (max-width: 900px) { .quick-actions { grid-template-columns: repeat(2, 1fr); } }
.action-card { background: #fff; border-radius: 14px; padding: 20px 12px; text-align: center; cursor: pointer; box-shadow: 0 1px 4px rgba(0,0,0,0.05); transition: all 0.2s; }
.action-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
.action-icon { display: block; font-size: 32px; margin-bottom: 8px; }
.action-title { display: block; font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 4px; }
.action-desc { display: block; font-size: 11px; color: #94a3b8; line-height: 1.4; }

.detail-card { border-radius: 16px; }
.flex-between { display: flex; justify-content: space-between; align-items: center; }
</style>
