<template>
  <div class="patient-management">
    <el-row :gutter="16" style="margin-bottom:16px">
      <el-col :span="6"><div class="stat-box primary"><span class="num">{{ stats.total }}</span><span class="lab">患者总数</span></div></el-col>
      <el-col :span="6"><div class="stat-box warning"><span class="num">{{ stats.pending }}</span><span class="lab">待就诊</span></div></el-col>
      <el-col :span="6"><div class="stat-box"><span class="num" style="color:#409eff">{{ stats.checking }}</span><span class="lab">检查中</span></div></el-col>
      <el-col :span="6"><div class="stat-box success"><span class="num">{{ stats.done }}</span><span class="lab">已确诊</span></div></el-col>
    </el-row>

    <el-card>
      <template #header>
        <div class="flex-between">
          <span><el-icon style="vertical-align:middle"><User /></el-icon> 患者列表</span>
          <div class="flex-gap">
            <el-input v-model="keyword" placeholder="姓名/症状搜索" style="width:160px" clearable @clear="load" />
            <el-select v-model="statusFilter" placeholder="状态" clearable style="width:120px" @change="load">
              <el-option label="待就诊" value="待就诊" />
              <el-option label="检查中" value="检查中" />
              <el-option label="已完成" value="已完成" />
            </el-select>
            <el-button type="primary" @click="load">查询</el-button>
            <el-button type="success" @click="openDialog()">+ 添加患者</el-button>
          </div>
        </div>
      </template>
      <el-table :data="patients" stripe v-loading="loading" highlight-current-row @row-click="viewProfile">
        <el-table-column prop="patientId" label="编号" width="100" />
        <el-table-column prop="name" label="姓名" width="80" />
        <el-table-column label="性别/年龄" width="90">
          <template #default="{ row }">{{ row.gender }} / {{ row.age }}</template>
        </el-table-column>
        <el-table-column prop="symptoms" label="症状" min-width="200" show-overflow-tooltip />
        <el-table-column prop="checkStatus" label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="tagType(row.checkStatus)" size="small" effect="plain">{{ row.checkStatus }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click.stop="$emit('aiConsult', row)">
              <el-icon style="margin-right:2px"><MagicStick /></el-icon>AI问诊
            </el-button>
            <el-button size="small" type="success" link @click.stop="viewProfile(row)">
              <el-icon style="margin-right:2px"><Document /></el-icon>档案
            </el-button>
            <el-button size="small" link @click.stop="openDialog(row)">编辑</el-button>
            <el-button size="small" type="danger" link @click.stop="remove(row.patientId)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 患者对话框 -->
    <el-dialog v-model="showDialog" :title="form.patientId ? '编辑患者' : '添加患者'" width="500px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="性别">
          <el-radio-group v-model="form.gender"><el-radio value="男">男</el-radio><el-radio value="女">女</el-radio></el-radio-group>
        </el-form-item>
        <el-form-item label="年龄"><el-input-number v-model="form.age" :min="0" :max="150" /></el-form-item>
        <el-form-item label="症状"><el-input v-model="form.symptoms" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="form.checkStatus">
            <el-option label="待就诊" value="待就诊" />
            <el-option label="检查中" value="检查中" />
            <el-option label="已完成" value="已完成" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 健康档案抽屉 -->
    <el-drawer v-model="showProfile" :title="profileName + ' 的健康档案'" size="500px">
      <div v-if="profile" class="profile-container">
        <el-descriptions :column="2" border size="small" style="margin-bottom:16px">
          <el-descriptions-item label="性别">{{ profile.patient?.gender }}</el-descriptions-item>
          <el-descriptions-item label="年龄">{{ profile.patient?.age }}岁</el-descriptions-item>
          <el-descriptions-item label="就诊次数">{{ profile.totalVisits }}次</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="tagType(profile.patient?.checkStatus)" size="small">{{ profile.patient?.checkStatus }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="首次就诊">{{ profile.firstVisitDate }}</el-descriptions-item>
          <el-descriptions-item label="最近就诊">{{ profile.lastVisitDate }}</el-descriptions-item>
        </el-descriptions>
        <h4 style="margin:0 0 12px 0;color:#303133"><el-icon><Timer /></el-icon> 诊断时间线</h4>
        <el-timeline v-if="profile.timeline?.length">
          <el-timeline-item v-for="(item, idx) in profile.timeline" :key="idx"
            :timestamp="item.date" placement="top"
            :color="idx === 0 ? '#409eff' : '#e0e0e0'">
            <el-card shadow="hover">
              <p style="margin:0;font-size:13px;color:#606266">{{ item.disease }}</p>
            </el-card>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-else description="暂无诊断记录" :image-size="80" />
      </div>
      <el-skeleton v-else :rows="6" animated />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, MagicStick, Document, Timer } from '@element-plus/icons-vue'
import { getPatients, savePatient, deletePatient as delPatientApi, getPatientHealthProfile } from '../../api/modules'

const emit = defineEmits(['aiConsult'])

const patients = ref([])
const loading = ref(false)
const keyword = ref('')
const statusFilter = ref('')
const showDialog = ref(false)
const form = ref({ gender: '男', age: 30, checkStatus: '待就诊' })
const showProfile = ref(false)
const profileName = ref('')
const profile = ref(null)

const stats = computed(() => {
  const all = patients.value
  return {
    total: all.length,
    pending: all.filter(p => p.checkStatus === '待就诊').length,
    checking: all.filter(p => p.checkStatus === '检查中').length,
    done: all.filter(p => p.checkStatus === '已完成').length
  }
})

function tagType(status) {
  if (status === '已完成') return 'success'
  if (status === '检查中') return 'warning'
  return 'info'
}

async function load() {
  loading.value = true
  try {
    const params = {}
    if (keyword.value) params.keyword = keyword.value
    if (statusFilter.value) params.status = statusFilter.value
    const res = await getPatients(params)
    patients.value = res.data || []
  } catch { ElMessage.error('加载患者列表失败') }
  finally { loading.value = false }
}

function openDialog(row) {
  form.value = row ? { ...row } : { gender: '男', age: 30, checkStatus: '待就诊' }
  showDialog.value = true
}

async function submit() {
  try {
    await savePatient(form.value)
    ElMessage.success('保存成功')
    showDialog.value = false
    await load()
  } catch { ElMessage.error('保存失败') }
}

async function remove(id) {
  try {
    await ElMessageBox.confirm('确定删除该患者？', '确认删除', { type: 'warning' })
    await delPatientApi(id)
    ElMessage.success('删除成功')
    await load()
  } catch { /* cancelled */ }
}

async function viewProfile(row) {
  profileName.value = row.name
  profile.value = null
  showProfile.value = true
  try {
    const res = await getPatientHealthProfile(row.patientId)
    profile.value = res.data || null
  } catch { ElMessage.error('加载健康档案失败') }
}

onMounted(load)
</script>

<style scoped>
.flex-between { display: flex; justify-content: space-between; align-items: center; }
.flex-gap { display: flex; gap: 8px; }
.stat-box { text-align: center; padding: 20px; border-radius: 8px; background: #f0f9ff; }
.stat-box .num { font-size: 28px; font-weight: 700; color: #409eff; display: block; }
.stat-box .lab { font-size: 13px; color: #909399; margin-top: 4px; display: block; }
.stat-box.warning { background: #fdf6ec; }
.stat-box.warning .num { color: #e6a23c; }
.stat-box.success { background: #f0f9eb; }
.stat-box.success .num { color: #67c23a; }
.profile-container { padding: 0 4px; }
</style>
