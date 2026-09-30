<template>
  <el-card shadow="never">
    <template #header>
      <div class="lib-header">
        <span class="lib-title"><el-icon><Reading /></el-icon> 疾病知识库</span>
        <div class="lib-controls">
          <el-select v-model="deptFilter" placeholder="按科室筛选" clearable style="width:160px" @change="applyFilters">
            <el-option v-for="d in departments" :key="d" :label="d" :value="d" />
          </el-select>
          <el-input v-model="keyword" placeholder="搜索疾病..." style="width:260px" clearable @input="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </div>
    </template>

    <!-- 概览统计 -->
    <el-row :gutter="12" class="stats-row">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-num">{{ diseases.length }}</div>
          <div class="stat-label">收录疾病</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-num">{{ deptCount }}</div>
          <div class="stat-label">涉及科室</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-num">{{ severityCounts.高 || 0 }}</div>
          <div class="stat-label">高风险疾病</div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-num">{{ severityCounts.中 || 0 }}</div>
          <div class="stat-label">中度风险</div>
        </div>
      </el-col>
    </el-row>

    <!-- 加载中 -->
    <div v-if="loading" style="padding:20px"><el-skeleton :rows="6" animated /></div>

    <!-- 疾病详情 -->
    <div v-else-if="detail" class="detail-container">
      <div class="detail-nav">
        <el-button size="small" @click="detail = null">
          <el-icon><ArrowLeft /></el-icon> 返回列表
        </el-button>
      </div>

      <div class="disease-hero">
        <div class="hero-left">
          <div class="hero-name">{{ detail.name }}</div>
          <div class="hero-alias" v-if="detail.alias && detail.alias !== detail.name">{{ detail.alias }}</div>
          <div class="hero-tags">
            <el-tag :type="detail.severity === '高' ? 'danger' : 'warning'" effect="dark" size="small">
              {{ detail.severity === '高' ? '高风险' : '中风险' }}
            </el-tag>
            <el-tag type="primary" effect="plain" size="small">{{ detail.department }}</el-tag>
            <el-tag type="success" effect="plain" size="small">病程 {{ detail.typicalDuration }}{{ detail.typicalDurationUnit }}</el-tag>
          </div>
        </div>
      </div>

      <!-- 描述 -->
      <el-card shadow="never" class="section-card">
        <template #header><span class="section-title">📖 疾病概述</span></template>
        <p class="desc-text">{{ detail.description }}</p>
      </el-card>

      <!-- 检查建议 -->
      <el-card v-if="detail.exams && detail.exams.length" shadow="never" class="section-card exam-card">
        <template #header><span class="section-title">🔬 建议检查项目</span></template>
        <div class="tag-list">
          <el-tag v-for="e in detail.exams" :key="e" type="primary" effect="plain" class="exam-tag">{{ e }}</el-tag>
        </div>
      </el-card>

      <!-- 治疗方案 -->
      <el-card v-if="detail.treatments && detail.treatments.length" shadow="never" class="section-card treat-card">
        <template #header><span class="section-title">💊 治疗方案</span></template>
        <ul class="check-list">
          <li v-for="t in detail.treatments" :key="t">{{ t }}</li>
        </ul>
      </el-card>

      <!-- 推荐用药 -->
      <el-card v-if="detail.medications && detail.medications.length" shadow="never" class="section-card med-card">
        <template #header><span class="section-title">💊 推荐用药</span></template>
        <el-table :data="medItems" stripe size="small" style="width:100%">
          <el-table-column prop="name" label="药品" min-width="180" />
          <el-table-column prop="dosage" label="用法用量" min-width="200" />
          <el-table-column prop="note" label="备注" min-width="120">
            <template #default="{ row }">{{ row.note || '—' }}</template>
          </el-table-column>
        </el-table>
      </el-card>

      <!-- 生活建议 -->
      <el-card v-if="detail.lifestyleTips && detail.lifestyleTips.length" shadow="never" class="section-card lifestyle-card">
        <template #header><span class="section-title">🌿 生活建议</span></template>
        <ul class="check-list green">
          <li v-for="l in detail.lifestyleTips" :key="l">{{ l }}</li>
        </ul>
      </el-card>

      <!-- 鉴别诊断 -->
      <el-card v-if="detail.differentialDiagnosis && detail.differentialDiagnosis.length" shadow="never" class="section-card diff-card">
        <template #header><span class="section-title">🔍 鉴别诊断</span></template>
        <div v-for="d in detail.differentialDiagnosis" :key="d.name" class="diff-item">
          <div class="diff-name">{{ d.name }} <span class="diff-alias" v-if="d.alias">({{ d.alias }})</span></div>
          <div class="diff-reason">{{ d.keyDifference }}</div>
        </div>
      </el-card>

      <!-- 就医提醒 -->
      <div v-if="detail.whenToSeeDoctor" class="warning-box">
        {{ detail.whenToSeeDoctor }}
      </div>
    </div>

    <!-- 疾病列表 -->
    <el-table v-else :data="filteredDiseases" stripe @row-click="viewDetail" class="disease-table">
      <el-table-column prop="name" label="疾病名称" min-width="160">
        <template #default="{ row }">
          <span class="disease-link">{{ row.name }}</span>
          <span class="disease-alias" v-if="row.alias && row.alias !== row.name">（{{ row.alias }}）</span>
        </template>
      </el-table-column>
      <el-table-column prop="department" label="科室" width="150">
        <template #default="{ row }">
          <el-tag type="primary" effect="plain" size="small">{{ row.department }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="severity" label="风险等级" width="90">
        <template #default="{ row }">
          <el-tag :type="row.severity === '高' ? 'danger' : 'warning'" effect="dark" size="small">{{ row.severity }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="简介" min-width="280" show-overflow-tooltip />
      <el-table-column label="操作" width="80" fixed="right">
        <template #default="{ row }">
          <el-button type="primary" link size="small" @click.stop="viewDetail(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!loading && filteredDiseases.length === 0 && !detail" description="暂无匹配疾病" :image-size="80" />
  </el-card>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Reading, ArrowLeft } from '@element-plus/icons-vue'
import { getDiseaseLibrarySearch, getDiseaseDetail } from '../../api/modules'

const diseases = ref([])
const keyword = ref('')
const loading = ref(false)
const detail = ref(null)
const deptFilter = ref('')

const departments = computed(() => {
  const deps = new Set()
  diseases.value.forEach(d => {
    if (d.department) deps.add(d.department)
  })
  return [...deps].sort()
})

const deptCount = computed(() => departments.value.length)

const severityCounts = computed(() => {
  const counts = {}
  diseases.value.forEach(d => {
    counts[d.severity] = (counts[d.severity] || 0) + 1
  })
  return counts
})

const filteredDiseases = computed(() => {
  let list = diseases.value
  if (deptFilter.value) {
    list = list.filter(d => d.department === deptFilter.value)
  }
  if (keyword.value) {
    const kw = keyword.value.toLowerCase()
    list = list.filter(d =>
      d.name.toLowerCase().includes(kw) ||
      (d.alias && d.alias.toLowerCase().includes(kw)) ||
      (d.description && d.description.toLowerCase().includes(kw))
    )
  }
  return list
})

const medItems = computed(() => {
  if (!detail.value?.medications) return []
  return detail.value.medications.map(m => {
    // parse "药品名 剂量 用法"
    const parts = m.split(/\s+/)
    return {
      name: parts[0] || m,
      dosage: parts.slice(1).join(' ') || '—',
      note: ''
    }
  })
})

async function load() {
  loading.value = true
  try {
    const res = await getDiseaseLibrarySearch({})
    diseases.value = res.data || []
  } catch { ElMessage.error('加载疾病库失败') }
  finally { loading.value = false }
}

function onSearch() {
  if (keyword.value) {
    diseases.value = diseases.value.filter(d =>
      d.name.includes(keyword.value) || (d.alias && d.alias.includes(keyword.value))
    )
  } else {
    load()
  }
}

function applyFilters() {
  // reactive computed handles filtering
}

async function viewDetail(row) {
  try {
    const res = await getDiseaseDetail(row.name)
    detail.value = res.data || row
  } catch {
    detail.value = row
  }
}

onMounted(load)
</script>

<style scoped>
.lib-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.lib-title {
  font-size: 16px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
}
.lib-controls {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* 统计行 */
.stats-row { margin-bottom: 16px; }
.stat-card {
  background: linear-gradient(135deg, #f0f5ff, #e6f7ff);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
  border: 1px solid #d6e4ff;
}
.stat-num { font-size: 28px; font-weight: 700; color: #409eff; line-height: 1.2; }
.stat-label { font-size: 13px; color: #606266; margin-top: 4px; }

/* 详情容器 */
.detail-container { max-width: 900px; margin: 0 auto; }
.detail-nav { margin-bottom: 12px; }

.disease-hero {
  background: linear-gradient(135deg, #667eea, #764ba2);
  border-radius: 12px;
  padding: 24px 28px;
  margin-bottom: 16px;
  color: #fff;
}
.hero-name { font-size: 24px; font-weight: 700; }
.hero-alias { font-size: 14px; opacity: 0.85; margin-top: 4px; }
.hero-tags { display: flex; gap: 8px; margin-top: 12px; }

/* 分区卡片 */
.section-card { margin-bottom: 12px; border-radius: 10px; }
.section-title { font-weight: 600; font-size: 15px; }

.desc-text { line-height: 1.8; color: #303133; font-size: 14px; margin: 0; }

.exam-card { border-left: 3px solid #409eff; }
.treat-card { border-left: 3px solid #67c23a; }
.med-card { border-left: 3px solid #e6a23c; }
.lifestyle-card { border-left: 3px solid #52c41a; background: #f0f9eb; }
.diff-card { border-left: 3px solid #909399; }

.tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.exam-tag { font-size: 13px; padding: 4px 12px; border-radius: 14px; }

/* 勾选列表 */
.check-list { margin: 0; padding: 0; list-style: none; }
.check-list li {
  padding: 5px 8px;
  margin-bottom: 3px;
  font-size: 13px;
  color: #303133;
  line-height: 1.6;
}
.check-list li::before { content: '✅ '; margin-right: 4px; }
.check-list.green li::before { content: '🌿 '; }

/* 鉴别诊断 */
.diff-item {
  padding: 10px 12px;
  margin-bottom: 6px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #e8e8e8;
}
.diff-name { font-weight: 600; font-size: 14px; color: #303133; }
.diff-alias { color: #909399; font-size: 12px; }
.diff-reason { font-size: 13px; color: #606266; margin-top: 4px; padding: 4px 8px; background: #fff; border-radius: 4px; }

/* 就医提醒 */
.warning-box {
  background: linear-gradient(135deg, #fff2f0, #fff7e6);
  border: 1px solid #ffccc7;
  border-radius: 10px;
  padding: 12px 16px;
  color: #cf1322;
  font-size: 13px;
  margin-top: 8px;
}

/* 表格 */
.disease-table { margin-top: 8px; }
.disease-link { font-weight: 500; color: #303133; cursor: pointer; }
.disease-link:hover { color: #409eff; }
.disease-alias { color: #909399; font-size: 12px; }
</style>
