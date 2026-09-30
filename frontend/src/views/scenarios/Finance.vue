<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <!-- ==================== 交易列表 ==================== -->
      <el-tab-pane label="交易列表" name="transactions">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>交易记录</span>
              <div>
                <el-select v-model="transFilter.riskLevel" placeholder="风险等级" clearable style="width:130px;margin-right:8px">
                  <el-option label="高风险" value="高" />
                  <el-option label="中风险" value="中" />
                  <el-option label="低风险" value="低" />
                  <el-option label="正常" value="正常" />
                </el-select>
                <el-select v-model="transFilter.status" placeholder="状态" clearable style="width:120px;margin-right:8px">
                  <el-option label="已处理" value="已处理" />
                  <el-option label="待处理" value="待处理" />
                  <el-option label="已拦截" value="已拦截" />
                </el-select>
                <el-button type="primary" @click="loadTransactions">查询</el-button>
              </div>
            </div>
          </template>
          <el-table :data="transactions" stripe v-loading="loading" border>
            <el-table-column label="序号" type="index" width="60" />
            <el-table-column prop="transactionNo" label="交易编号" min-width="150" />
            <el-table-column prop="userName" label="用户" width="120" />
            <el-table-column label="金额" width="110">
              <template #default="{row}">¥{{ row.amount != null ? row.amount.toLocaleString() : '-' }}</template>
            </el-table-column>
            <el-table-column prop="transactionType" label="类型" width="100" />
            <el-table-column label="风险评分" width="100">
              <template #default="{row}">{{ row.riskScore != null ? row.riskScore.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="riskLevel" label="风险等级" width="100">
              <template #default="{row}">
                <el-tag :type="riskLevelTag(row.riskLevel)" size="small" effect="dark">{{ row.riskLevel }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{row}">
                <el-tag :type="row.status==='已处理'?'success':row.status==='待处理'?'warning':'danger'" size="small">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 风控规则 ==================== -->
      <el-tab-pane label="风控规则" name="rules">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>风控规则列表</span>
              <el-button type="success" @click="openRuleDialog">＋ 添加规则</el-button>
            </div>
          </template>
          <el-table :data="rules" stripe v-loading="loadingRules" border>
            <el-table-column prop="ruleName" label="规则名称" min-width="140" />
            <el-table-column prop="ruleType" label="类型" width="100" />
            <el-table-column prop="condition" label="条件" min-width="180" />
            <el-table-column prop="threshold" label="阈值" width="100" />
            <el-table-column prop="riskLevel" label="风险等级" width="100">
              <template #default="{row}">
                <el-tag :type="riskLevelTag(row.riskLevel)" size="small" effect="dark">{{ row.riskLevel }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="enabled" label="启用" width="80">
              <template #default="{row}">
                <el-switch v-model="row.enabled" @change="toggleRule(row)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="150" fixed="right">
              <template #default="{row}">
                <el-button size="small" @click="editRule(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeleteRule(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 📊 仪表盘 ==================== -->
      <el-tab-pane label="📊 仪表盘" name="dashboard">
        <div v-loading="dashLoading">
          <!-- 概览卡片 -->
          <el-row :gutter="16" style="margin-bottom:16px">
            <el-col :span="6" v-for="s in dashCards" :key="s.label">
              <div class="stat-box" :style="{borderTop:`3px solid ${s.color}`}">
                <span class="num" :style="{color:s.color}">{{ s.value }}</span>
                <span class="lab">{{ s.label }}</span>
              </div>
            </el-col>
          </el-row>

          <!-- AI 风险摘要 -->
          <el-card v-if="dashReport" shadow="never" style="margin-bottom:16px;border-left:4px solid #409eff">
            <template #header>
              <span><el-icon><ChatDotSquare /></el-icon> 🧠 AI 风控状态摘要</span>
              <AiSourceTag :result="dashReport" ml-text="ML模型" fallback-text="规则引擎" />
            </template>
            <div class="ai-report-text">{{ dashReport.reportText?.replace(/\n/g, '<br>') || '' }}</div>
          </el-card>

          <!-- 风险趋势 + 分布 -->
          <el-row :gutter="16">
            <el-col :span="14">
              <el-card shadow="never" style="margin-bottom:16px">
                <template #header><span><el-icon><TrendCharts /></el-icon> 风险趋势</span></template>
                <div ref="trendChartRef" class="chart-container"></div>
              </el-card>
            </el-col>
            <el-col :span="10">
              <el-card shadow="never" style="margin-bottom:16px">
                <template #header><span><el-icon><PieChart /></el-icon> 风险类型分布</span></template>
                <div ref="pieChartRef" class="chart-container"></div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 实时风险预警滚动 -->
          <el-card v-if="dashAlerts.length" shadow="never" style="margin-bottom:16px;border-left:4px solid #f56c6c">
            <template #header>
              <span><el-icon><WarningFilled /></el-icon> 🚨 实时风险预警</span>
              <el-tag size="small" type="danger" style="margin-left:8px">{{ dashAlerts.length }} 条预警</el-tag>
            </template>
            <div class="alert-scroll-wrap">
              <div v-for="(a, i) in dashAlerts" :key="i" class="alert-item">
                <el-tag :type="a.severity==='紧急'?'danger':'warning'" size="small" effect="dark">{{ a.severity }}</el-tag>
                <span class="alert-txno">{{ a.transactionNo }}</span>
                <span class="alert-user">{{ a.userName }}</span>
                <span class="alert-amount">¥{{ a.amount?.toLocaleString() }}</span>
                <span class="alert-score" :style="{color:a.riskScore>80?'#f56c6c':'#e6a23c'}">评分: {{ a.riskScore }}</span>
                <span class="alert-type">{{ a.type }}</span>
                <span class="alert-time">{{ formatTime(a.time) }}</span>
              </div>
            </div>
          </el-card>

          <!-- 近期风险交易 -->
          <el-card shadow="never">
            <template #header><span><el-icon><List /></el-icon> 近期高风险交易</span></template>
            <el-table :data="dashboardRecentRisks" size="small" stripe max-height="320">
              <el-table-column prop="transactionNo" label="交易编号" min-width="140" />
              <el-table-column prop="userName" label="用户" width="100" />
              <el-table-column label="金额" width="100">
                <template #default="{row}">¥{{ row.amount != null ? row.amount.toLocaleString() : '-' }}</template>
              </el-table-column>
              <el-table-column prop="riskScore" label="风险评分" width="90">
                <template #default="{row}">
                  <el-tag :type="row.riskScore>80?'danger':'warning'" size="small">{{ row.riskScore }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="createTime" label="时间" min-width="150">
                <template #default="{row}">{{ formatTime(row.createTime) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ==================== 🤖 AI风控分析 ==================== -->
      <el-tab-pane label="🤖 AI风控分析" name="analysis">
        <div v-loading="analysisLoading">

          <!-- 行1: 用户画像 + 规则命中 -->
          <el-row :gutter="16" style="margin-bottom:16px">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span><el-icon><User /></el-icon> 👤 用户行为画像</span>
                  <el-tag size="small" type="info" style="float:right">{{ userProfiles.length }} 个用户</el-tag>
                </template>
                <div class="profile-scroll" style="max-height:380px;overflow-y:auto">
                  <div v-for="p in userProfiles" :key="p.userId" class="profile-card" :style="{borderLeft:`4px solid ${p.riskLevel==='高风险'?'#f56c6c':p.riskLevel==='中风险'?'#e6a23c':'#67c23a'}`}">
                    <div class="prof-header">
                      <span class="prof-name">{{ p.userName }}</span>
                      <el-tag :type="p.riskLevel==='高风险'?'danger':p.riskLevel==='中风险'?'warning':'success'" size="small" effect="dark">{{ p.riskLevel }}</el-tag>
                    </div>
                    <div class="prof-body">
                      <div class="prof-row"><span>交易次数</span><b>{{ p.totalTransactions }}</b></div>
                      <div class="prof-row"><span>总金额</span><b>¥{{ p.totalAmount?.toLocaleString() }}</b></div>
                      <div class="prof-row"><span>平均金额</span><b>¥{{ p.avgAmount?.toLocaleString() }}</b></div>
                      <div class="prof-row"><span>风险比例</span><b>{{ p.riskRatio }}%</b></div>
                      <div class="prof-row"><span>消费模式</span><b>{{ p.spendingPattern }}</b></div>
                    </div>
                    <div class="prof-footer">
                      <el-progress :percentage="p.securityScore" :stroke-width="10"
                        :color="p.securityScore>=80?'#67c23a':p.securityScore>=50?'#e6a23c':'#f56c6c'"
                        :format="()=>'安全评分 '+p.securityScore" />
                    </div>
                  </div>
                  <el-empty v-if="!userProfiles.length" description="暂无用户数据" />
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never" style="margin-bottom:16px">
                <template #header><span><el-icon><DataAnalysis /></el-icon> 风控规则命中统计</span></template>
                <div ref="barChartRef" class="chart-container"></div>
              </el-card>
              <el-card shadow="never">
                <template #header><span><el-icon><DataBoard /></el-icon> 规则有效率</span></template>
                <div v-if="ruleHits.length" style="padding:4px 0;max-height:200px;overflow-y:auto">
                  <div v-for="item in ruleHits" :key="item.ruleName" style="margin-bottom:12px">
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;font-size:13px">
                      <span>{{ item.ruleName }}</span>
                      <span :style="{color:item.effectiveness==='高效'?'#67c23a':item.effectiveness==='有效'?'#e6a23c':'#909399'}">{{ item.effectiveness }}</span>
                    </div>
                    <el-progress
                      :percentage="Math.min(100, (item.hitCount || 0) * 10)"
                      :stroke-width="14"
                      :color="item.effectiveness==='高效'?'#67c23a':item.effectiveness==='有效'?'#e6a23c':'#dcdfe6'"
                    />
                  </div>
                </div>
                <el-empty v-else description="暂无规则数据" />
              </el-card>
            </el-col>
          </el-row>

          <!-- 行2: 多维度风险评估雷达图 -->
          <el-card shadow="never" style="margin-bottom:16px">
            <template #header>
              <span><el-icon><Monitor /></el-icon> 🎯 多维度风险评估雷达</span>
              <div style="float:right">
                <el-select v-model="multiRiskTxId" placeholder="选择交易ID" style="width:160px;margin-right:8px">
                  <el-option v-for="tx in transactions" :key="tx.id" :label="'#'+tx.id+' '+tx.userName" :value="tx.id" />
                </el-select>
                <el-button type="primary" size="small" @click="loadMultiRisk">分析</el-button>
              </div>
            </template>
            <el-row :gutter="20">
              <el-col :span="12">
                <div ref="radarChartRef" class="chart-container" style="height:280px"></div>
              </el-col>
              <el-col :span="12">
                <div v-if="multiRiskResult" class="multi-risk-info">
                  <el-alert :title="'综合风险评分: ' + multiRiskResult.totalRiskScore" :type="multiRiskResult.totalRiskScore>70?'error':multiRiskResult.totalRiskScore>40?'warning':'success'" show-icon style="margin-bottom:12px" />
                  <div class="multi-risk-dims">
                    <div v-for="d in multiRiskResult.dimensions" :key="d.name" class="dim-item">
                      <span class="dim-name">{{ d.name }}</span>
                      <el-progress :percentage="d.value" :color="d.value>70?'#f56c6c':d.value>40?'#e6a23c':'#67c23a'" :stroke-width="12" />
                    </div>
                  </div>
                  <p style="margin-top:12px;color:#909399;font-size:13px">
                    💡 最弱环节：<b style="color:#f56c6c">{{ multiRiskResult.weakestLink }}</b>
                  </p>
                </div>
                <div v-else class="multi-risk-empty">
                  <el-icon :size="40" color="#dcdfe6"><Monitor /></el-icon>
                  <p>选择交易并点击「分析」查看多维度风险评估</p>
                </div>
              </el-col>
            </el-row>
          </el-card>

          <!-- 行3: 可疑交易 + 趋势预测 -->
          <el-row :gutter="16" style="margin-bottom:16px">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span><el-icon><WarningFilled /></el-icon> 🚩 可疑交易智能检测</span>
                  <el-tag size="small" type="danger" style="margin-left:8px">{{ suspiciousTx.length }}</el-tag>
                </template>
                <div class="suspicious-scroll" style="max-height:300px;overflow-y:auto">
                  <div v-for="s in suspiciousTx" :key="s.transactionId" class="sus-item">
                    <div class="sus-header">
                      <el-tag :type="s.alertLevel==='严重'?'danger':'warning'" size="small" effect="dark">{{ s.alertLevel }}</el-tag>
                      <span class="sus-user">{{ s.userName }}</span>
                      <span class="sus-amount" style="color:#f56c6c">¥{{ s.amount?.toLocaleString() }}</span>
                    </div>
                    <div class="sus-body">
                      <span>🔍 {{ s.suspiciousReason }}</span>
                    </div>
                    <div class="sus-footer">
                      <span>📋 {{ s.suggestion }}</span>
                      <span style="float:right;color:#909399;font-size:12px">{{ formatTime(s.time) }}</span>
                    </div>
                  </div>
                  <el-empty v-if="!suspiciousTx.length" description="未检测到可疑交易" />
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span><el-icon><TrendCharts /></el-icon> 📈 交易量趋势预测（未来7天）</span>
                </template>
                <div ref="predictionChartRef" class="chart-container" style="height:250px"></div>
                <div style="max-height:180px;overflow-y:auto;margin-top:8px">
                  <el-table :data="trendPrediction" size="small" stripe max-height="180">
                    <el-table-column prop="date" label="日期" width="100">
                      <template #default="{row}">{{ row.date?.slice(5) }}</template>
                    </el-table-column>
                    <el-table-column prop="dayOfWeek" label="周" width="50" />
                    <el-table-column label="预测笔数" width="90">
                      <template #default="{row}">{{ row.predictedCount }}</template>
                    </el-table-column>
                    <el-table-column label="高风险" width="70">
                      <template #default="{row}">
                        <el-tag size="small" type="danger">{{ row.highRiskCount }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="置信区间" min-width="120">
                      <template #default="{row}">{{ row.confidenceRange }}</template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- 行4: AI 风险评估报告 -->
          <el-card shadow="never" style="border-left:4px solid #409eff">
            <template #header>
              <span><el-icon><Document /></el-icon> 📋 AI 金融风控评估报告</span>
              <AiSourceTag :result="aiReport" ml-text="ML模型" fallback-text="规则引擎" style="float:right;margin-right:8px" />
              <el-tag size="small" type="primary" style="float:right">自动生成 · {{ aiReport?.generatedAt ? formatTime(aiReport.generatedAt) : '' }}</el-tag>
            </template>
            <el-row :gutter="16" style="margin-bottom:12px">
              <el-col :span="4" v-for="s in reportStats" :key="s.label">
                <div class="stat-box-sm"><span class="num-sm">{{ s.value }}</span><span class="lab-sm">{{ s.label }}</span></div>
              </el-col>
            </el-row>
            <div v-if="aiReport" class="ai-report-text">{{ aiReport.reportText?.replace(/\n/g, '<br>') || '' }}</div>
            <el-empty v-else description="正在生成报告..." />
          </el-card>

        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- ===== 规则对话框 ===== -->
    <el-dialog v-model="showRuleDialog" :title="editRuleMode?'编辑规则':'添加规则'" width="550px">
      <el-form :model="ruleForm" label-width="100px">
        <el-form-item label="规则名称"><el-input v-model="ruleForm.ruleName" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="ruleForm.ruleType" style="width:100%">
            <el-option label="金额阈值" value="金额阈值" />
            <el-option label="频繁交易" value="频繁交易" />
            <el-option label="异地登录" value="异地登录" />
            <el-option label="设备指纹" value="设备指纹" />
            <el-option label="行为异常" value="行为异常" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件"><el-input v-model="ruleForm.condition" /></el-form-item>
        <el-form-item label="阈值"><el-input-number v-model="ruleForm.threshold" style="width:100%" /></el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="ruleForm.riskLevel" style="width:100%">
            <el-option label="高" value="高" />
            <el-option label="中" value="中" />
            <el-option label="低" value="低" />
            <el-option label="正常" value="正常" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="ruleForm.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRuleDialog=false">取消</el-button>
        <el-button type="primary" @click="saveRule">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getFinanceTransactions, saveFinanceTransaction, deleteFinanceTransaction,
  getFinanceRules, saveFinanceRule, updateFinanceRule, deleteFinanceRule,
  getFinanceDashboard, evaluateRisk,
  getRuleHits,
  getFinanceTrendPrediction, getUserBehaviorProfiles,
  getSuspiciousTransactions, getMultiDimensionalRisk,
  getTransactionNetwork, getRiskAssessmentReport,
  getFinanceAlerts, getRiskTrend
} from '../../api/modules'
import { ElMessage, ElMessageBox } from 'element-plus'
import AiSourceTag from '../../components/AiSourceTag.vue'
import {
  ChatDotSquare, TrendCharts, PieChart, WarningFilled, List,
  User, DataAnalysis, DataBoard, Monitor, Document
} from '@element-plus/icons-vue'

const activeTab = ref('transactions')
const loading = ref(false)
const loadingRules = ref(false)
const dashLoading = ref(false)
const analysisLoading = ref(false)

/* ===== 工具 ===== */
function riskLevelTag(level) {
  if (!level) return 'info'
  if (level === '高' || level === '严重') return 'danger'
  if (level === '中') return 'warning'
  if (level === '低') return 'info'
  return 'success'
}

function formatTime(t) {
  if (!t) return '—'
  return t.length > 16 ? t.substring(0, 16) : t
}

/* ===== 交易列表 ===== */
const transactions = ref([])
const transFilter = ref({ riskLevel: '', status: '' })

async function loadTransactions() {
  loading.value = true
  try {
    const params = {}
    if (transFilter.value.riskLevel) params.riskLevel = transFilter.value.riskLevel
    if (transFilter.value.status) params.status = transFilter.value.status
    const res = await getFinanceTransactions(params)
    transactions.value = res.data || []
  } catch {} finally { loading.value = false }
}

/* ===== 风控规则 ===== */
const rules = ref([])
const showRuleDialog = ref(false)
const editRuleMode = ref(false)
const ruleForm = ref({})

function openRuleDialog() { ruleForm.value = { enabled: true }; editRuleMode.value = false; showRuleDialog.value = true }
function editRule(row) { ruleForm.value = { ...row }; editRuleMode.value = true; showRuleDialog.value = true }

async function loadRules() {
  loadingRules.value = true
  try { const r = await getFinanceRules(); rules.value = r.data || [] } catch {} finally { loadingRules.value = false }
}

async function saveRule() {
  try {
    if (ruleForm.value.id) { await updateFinanceRule(ruleForm.value.id, ruleForm.value) }
    else { await saveFinanceRule(ruleForm.value) }
    ElMessage.success('保存成功'); showRuleDialog.value = false; await loadRules()
  } catch {}
}

async function toggleRule(row) {
  try { await updateFinanceRule(row.id, { enabled: row.enabled }); ElMessage.success(row.enabled ? '已启用' : '已禁用') }
  catch { row.enabled = !row.enabled }
}

async function handleDeleteRule(id) {
  try { await ElMessageBox.confirm('确定删除该规则？', '确认'); await deleteFinanceRule(id); ElMessage.success('删除成功'); await loadRules() }
  catch {}
}

/* =========================================================
   📊 仪表盘
   ========================================================= */
const dashCards = ref([])
const dashReport = ref(null)
const dashboardRecentRisks = ref([])
const dashAlerts = ref([])
const pieChartRef = ref(null)
const trendChartRef = ref(null)
let pieChart = null
let trendChart = null

async function loadDashboard() {
  dashLoading.value = true
  try {
    const [dashRes, reportRes, alertsRes, trendRes] = await Promise.all([
      getFinanceDashboard(),
      getRiskAssessmentReport(),
      getFinanceAlerts(),
      getRiskTrend()
    ])

    const d = dashRes.data
    dashCards.value = [
      { label: '总交易数', value: d.totalTransactions || 0, color: '#409eff' },
      { label: '风险交易', value: d.riskTransactionCount || 0, color: '#f56c6c' },
      { label: '风险率', value: d.riskRate || '0%', color: '#e6a23c' },
      { label: '今日新增风险', value: d.todayRiskCount || 0, color: '#f56c6c' }
    ]
    dashboardRecentRisks.value = d.recentHighRiskTransactions || []
    dashReport.value = reportRes.data
    dashAlerts.value = alertsRes.data || []

    nextTick(() => {
      renderPieChart(d.riskDistribution || [])
      renderTrendChart(trendRes.data || [])
    })
  } catch {} finally { dashLoading.value = false }
}

function renderPieChart(data) {
  if (!pieChartRef.value) return
  if (pieChart) pieChart.dispose()
  pieChart = echarts.init(pieChartRef.value)
  const chartData = typeof data === 'object' && !Array.isArray(data)
    ? Object.entries(data).map(([k, v]) => ({ name: k, value: v }))
    : data.map(item => ({ name: item.label || item.type || item.name, value: item.value || item.count || 0 }))
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    series: [{
      type: 'pie', radius: ['35%', '60%'],
      data: chartData,
      label: { formatter: '{b}: {d}%' },
      emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' } }
    }]
  })
}

function renderTrendChart(data) {
  if (!trendChartRef.value) return
  if (trendChart) trendChart.dispose()
  trendChart = echarts.init(trendChartRef.value)
  const dates = data.map(d => d.date?.slice(5))
  trendChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let s = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => { s += `${p.marker} ${p.seriesName}: ${p.value}<br/>` })
        return s
      }
    },
    legend: { data: ['总交易', '高风险', '风险率'], top: 0 },
    grid: { left: 50, right: 50, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates, axisLabel: { rotate: 30, fontSize: 11 } },
    yAxis: [
      { type: 'value', name: '交易笔数' },
      { type: 'value', name: '风险率%', max: 100 }
    ],
    series: [
      {
        name: '总交易', type: 'bar', data: data.map(d => d.total || 0),
        itemStyle: { color: 'rgba(64,158,255,0.6)' }
      },
      {
        name: '高风险', type: 'bar', data: data.map(d => d.highRisk || 0),
        itemStyle: { color: 'rgba(245,108,108,0.7)' }
      },
      {
        name: '风险率', type: 'line', yAxisIndex: 1,
        data: data.map(d => d.riskRatio || 0),
        lineStyle: { color: '#e6a23c', width: 3 },
        symbol: 'circle'
      }
    ]
  })
}

/* =========================================================
   🤖 AI风控分析
   ========================================================= */
const ruleHits = ref([])
const userProfiles = ref([])
const suspiciousTx = ref([])
const trendPrediction = ref([])
const aiReport = ref(null)
const reportStats = ref([])
const multiRiskTxId = ref(null)
const multiRiskResult = ref(null)

const barChartRef = ref(null)
const radarChartRef = ref(null)
const predictionChartRef = ref(null)
let barChart = null
let radarChart = null
let predictionChart = null

async function loadAnalysis() {
  analysisLoading.value = true
  try {
    const [ruleRes, userRes, susRes, trendRes, reportRes] = await Promise.all([
      getRuleHits(),
      getUserBehaviorProfiles(),
      getSuspiciousTransactions(),
      getFinanceTrendPrediction(7),
      getRiskAssessmentReport()
    ])

    ruleHits.value = ruleRes.data || []
    userProfiles.value = userRes.data || []
    suspiciousTx.value = susRes.data || []
    trendPrediction.value = trendRes.data || []
    aiReport.value = reportRes.data

    if (aiReport.value) {
      reportStats.value = [
        { label: '总交易', value: aiReport.value.totalTransactions || 0 },
        { label: '高风险', value: aiReport.value.highRiskCount || 0, color: '#f56c6c' },
        { label: '中风险', value: aiReport.value.mediumRiskCount || 0, color: '#e6a23c' },
        { label: '风险金额', value: '¥' + (aiReport.value.highRiskAmount?.toLocaleString() || 0) },
        { label: '启用规则', value: aiReport.value.activeRules || 0 },
        { label: '风险率', value: (aiReport.value.highRiskRatio || 0) + '%' }
      ]
    }

    nextTick(() => {
      if (ruleHits.value.length > 0) {
        renderBarChart(ruleHits.value)
      }
      renderPredictionChart(trendRes.data || [])
    })
  } catch {} finally { analysisLoading.value = false }
}

function renderBarChart(data) {
  if (!barChartRef.value) return
  if (!data || data.length === 0) return
  if (barChart) barChart.dispose()
  barChart = echarts.init(barChartRef.value)
  barChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: 50, right: 20, bottom: 50 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.ruleName || d.type),
      axisLabel: { rotate: 25, fontSize: 11 }
    },
    yAxis: { type: 'value', name: '命中次数' },
    series: [{
      type: 'bar',
      data: data.map(d => d.hitCount || d.count || 0),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#409eff' }, { offset: 1, color: '#79bbff' }
        ])
      },
      barMaxWidth: 50
    }]
  })
}

function renderPredictionChart(data) {
  if (!predictionChartRef.value) return
  if (predictionChart) predictionChart.dispose()
  predictionChart = echarts.init(predictionChartRef.value)
  const labels = data.map(d => d.date?.slice(5))
  predictionChart.setOption({
    tooltip: { trigger: 'axis', formatter: (params) => {
      let s = `<b>${params[0].axisValue}</b><br/>`
      params.forEach(p => { s += `${p.marker} ${p.seriesName}: ${p.value}<br/>` })
      return s
    }},
    legend: { data: ['预测交易量', '高风险交易'], top: 0 },
    grid: { left: 50, right: 20, top: 40, bottom: 20 },
    xAxis: { type: 'category', data: labels, axisLabel: { fontSize: 11 } },
    yAxis: { type: 'value', name: '笔数' },
    series: [
      {
        name: '预测交易量', type: 'bar',
        data: data.map(d => d.predictedCount || 0),
        itemStyle: { color: 'rgba(64,158,255,0.6)' }
      },
      {
        name: '高风险交易', type: 'line',
        data: data.map(d => d.highRiskCount || 0),
        lineStyle: { color: '#f56c6c', width: 2 },
        symbol: 'diamond',
        symbolSize: 8
      }
    ]
  })
}

/* 多维度风险评估 */
async function loadMultiRisk() {
  if (!multiRiskTxId.value) { ElMessage.warning('请选择交易'); return }
  try {
    const r = await getMultiDimensionalRisk(multiRiskTxId.value)
    multiRiskResult.value = r.data
    nextTick(() => {
      if (!radarChartRef.value) return
      if (radarChart) radarChart.dispose()
      radarChart = echarts.init(radarChartRef.value)
      const dims = r.data.dimensions || []
      radarChart.setOption({
        tooltip: {},
        radar: {
          indicator: dims.map(d => ({ name: d.name, max: 100 })),
          shape: 'circle',
          center: ['50%', '50%'],
          name: { textStyle: { fontSize: 11 } }
        },
        series: [{
          type: 'radar',
          data: [{
            value: dims.map(d => d.value),
            areaStyle: { color: 'rgba(64,158,255,0.3)' },
            lineStyle: { color: '#409eff', width: 2 }
          }]
        }]
      })
    })
  } catch {}
}

/* ===== 生命周期 ===== */
onMounted(() => loadTransactions())

watch(activeTab, (tab) => {
  if (tab === 'rules') loadRules()
  if (tab === 'dashboard') nextTick(() => loadDashboard())
  if (tab === 'analysis') nextTick(() => loadAnalysis())
})
</script>

<style scoped>
.flex-between { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }

/* 概览卡片 */
.stat-box { text-align:center; padding:18px 8px; background:#f7f8fa; border-radius:8px; }
.stat-box .num { display:block; font-size:24px; font-weight:bold; }
.stat-box .lab { display:block; font-size:12px; color:#909399; margin-top:4px; }

.stat-box-sm { text-align:center; padding:10px; background:#f0f2f5; border-radius:6px; }
.num-sm { display:block; font-size:18px; font-weight:bold; }
.lab-sm { display:block; font-size:11px; color:#909399; margin-top:2px; }

/* 图表 */
.chart-container { width:100%; height:340px; }

/* AI报告 */
.ai-report-text {
  font-size:13px; line-height:1.8; color:#303133;
  background:#f5f7fa; padding:16px 20px; border-radius:8px;
  white-space:pre-wrap;
}

/* 预警滚动 */
.alert-scroll-wrap { max-height:200px; overflow-y:auto; }
.alert-item {
  display:flex; align-items:center; gap:10px;
  padding:8px 4px; border-bottom:1px solid #f5f5f5; font-size:13px;
}
.alert-item:last-child { border-bottom:none; }
.alert-item:hover { background:#fef0f0; }
.alert-txno { font-weight:bold; min-width:130px; }
.alert-user { color:#666; min-width:80px; }
.alert-amount { color:#f56c6c; min-width:80px; }
.alert-score { min-width:70px; font-weight:bold; }
.alert-type { color:#909399; min-width:60px; }
.alert-time { color:#909399; font-size:12px; }

/* 用户画像卡片 */
.profile-card {
  padding:12px; margin-bottom:10px; border-radius:8px;
  background:#fafafa; border:1px solid #ebeef5;
  transition:transform .15s;
}
.profile-card:hover { transform:translateX(3px); }
.prof-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; }
.prof-name { font-weight:bold; font-size:14px; }
.prof-body { display:grid; grid-template-columns:1fr 1fr; gap:4px 12px; font-size:12px; margin-bottom:8px; }
.prof-row { display:flex; justify-content:space-between; padding:2px 0; }
.prof-row span { color:#909399; }
.prof-row b { color:#303133; }
.prof-footer { margin-top:6px; }

/* 可疑交易 */
.sus-item {
  padding:10px; margin-bottom:8px; border-radius:6px;
  border:1px solid #fde2e2; background:#fef8f8;
}
.sus-header { display:flex; align-items:center; gap:8px; margin-bottom:6px; }
.sus-user { font-weight:bold; }
.sus-amount { margin-left:auto; font-weight:bold; }
.sus-body { font-size:12px; color:#666; margin-bottom:4px; }
.sus-footer { font-size:12px; color:#909399; }

/* 多维度风险 */
.multi-risk-info { padding:8px; }
.multi-risk-empty {
  display:flex; flex-direction:column; align-items:center;
  justify-content:center; padding:40px 0; color:#909399;
}
.multi-risk-empty p { margin-top:12px; font-size:14px; }
.multi-risk-dims .dim-item { margin-bottom:10px; }
.dim-name { display:block; font-size:12px; margin-bottom:4px; }

/* 自定义滚动条 */
.profile-scroll::-webkit-scrollbar,
.suspicious-scroll::-webkit-scrollbar,
.alert-scroll-wrap::-webkit-scrollbar { width:4px; }
.profile-scroll::-webkit-scrollbar-thumb,
.suspicious-scroll::-webkit-scrollbar-thumb,
.alert-scroll-wrap::-webkit-scrollbar-thumb { background:#dcdfe6; border-radius:2px; }
</style>
