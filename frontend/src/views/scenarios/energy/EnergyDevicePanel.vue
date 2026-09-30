<template>
  <div class="energy-device-panel">
    <!-- 统计行 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="8">
        <div class="stat-item device-total">
          <div class="stat-icon">📟</div>
          <div class="stat-body">
            <span class="stat-num">{{ devices.length }}</span>
            <span class="stat-label">设备总数</span>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="stat-item device-running">
          <div class="stat-icon">✅</div>
          <div class="stat-body">
            <span class="stat-num">{{ runningCount }}</span>
            <span class="stat-label">运行中</span>
          </div>
        </div>
      </el-col>
      <el-col :span="8">
        <div class="stat-item device-error">
          <div class="stat-icon">⚠️</div>
          <div class="stat-body">
            <span class="stat-num">{{ errorCount }}</span>
            <span class="stat-label">异常设备</span>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 筛选行 -->
    <el-row :gutter="12" class="filter-row">
      <el-col :span="6">
        <el-input v-model="searchType" placeholder="设备类型" clearable @clear="loadDevices">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
      </el-col>
      <el-col :span="5">
        <el-select v-model="searchStatus" placeholder="状态" clearable style="width:100%" @change="loadDevices">
          <el-option label="运行中" value="运行中" />
          <el-option label="待维护" value="待维护" />
          <el-option label="已停机" value="已停机" />
        </el-select>
      </el-col>
      <el-col :span="6">
        <el-input v-model="searchLocation" placeholder="位置" clearable @clear="loadDevices">
          <template #prefix><el-icon><Location /></el-icon></template>
        </el-input>
      </el-col>
      <el-col :span="7" style="text-align:right">
        <el-button type="primary" :icon="Search" @click="loadDevices">查询</el-button>
        <el-button type="success" :icon="Plus" @click="openAddDevice">添加设备</el-button>
      </el-col>
    </el-row>

    <!-- 数据表格 -->
    <el-table :data="devices" stripe v-loading="loading" border style="width:100%" class="energy-table">
      <el-table-column prop="deviceId" label="设备编号" width="180" />
      <el-table-column prop="deviceType" label="类型" width="130">
        <template #default="{ row }">
          <el-tag :color="typeColor(row.deviceType)" style="color:#fff;border:none" size="small">{{ row.deviceType }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="位置" width="160" />
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag :type="row.status==='运行中'?'success':row.status==='待维护'?'warning':'danger'" size="small" effect="dark">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="power" label="功率(kW)" width="100" align="center">
        <template #default="{ row }">{{ row.power || '-' }}</template>
      </el-table-column>
      <el-table-column prop="installDate" label="安装日期" width="120" />
      <el-table-column label="操作" width="180" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain :icon="Edit" @click="editDevice(row)">编辑</el-button>
          <el-button size="small" type="danger" plain :icon="Delete" @click="deleteDevice(row.deviceId)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 设备添加/编辑对话框 -->
    <el-dialog v-model="showDeviceDialog" :title="isEditDevice ? '编辑设备' : '添加设备'" width="520px" class="energy-dialog">
      <el-form :model="deviceForm" label-width="100px" label-position="left">
        <el-form-item label="设备编号">
          <el-input v-model="deviceForm.deviceId" :disabled="isEditDevice" placeholder="请输入设备编号" />
        </el-form-item>
        <el-form-item label="设备类型">
          <el-select v-model="deviceForm.deviceType" placeholder="请选择类型" style="width:100%">
            <el-option label="太阳能板" value="太阳能板" />
            <el-option label="风力发电机" value="风力发电机" />
            <el-option label="蓄电池" value="蓄电池" />
            <el-option label="变压器" value="变压器" />
            <el-option label="电表" value="电表" />
            <el-option label="空调系统" value="空调系统" />
            <el-option label="照明系统" value="照明系统" />
          </el-select>
        </el-form-item>
        <el-form-item label="位置">
          <el-input v-model="deviceForm.location" placeholder="如：A栋-3楼-301" />
        </el-form-item>
        <el-form-item label="功率(kW)">
          <el-input-number v-model="deviceForm.power" :min="0" :step="0.1" style="width:100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="deviceForm.status" style="width:100%">
            <el-option label="运行中" value="运行中" />
            <el-option label="待维护" value="待维护" />
            <el-option label="已停机" value="已停机" />
          </el-select>
        </el-form-item>
        <el-form-item label="安装日期">
          <el-date-picker v-model="deviceForm.installDate" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%" placeholder="选择安装日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showDeviceDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveDeviceForm">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Edit, Delete, Location } from '@element-plus/icons-vue'
import { getDevices, saveDevice, deleteDevice as delDev } from '../../../api/modules'

const loading = ref(false)
const saving = ref(false)
const devices = ref([])
const searchType = ref('')
const searchStatus = ref('')
const searchLocation = ref('')
const showDeviceDialog = ref(false)
const isEditDevice = ref(false)
const deviceForm = ref({ deviceId: '', deviceType: '', location: '', power: 0, status: '运行中', installDate: '' })

const runningCount = computed(() => devices.value.filter(d => d.status === '运行中').length)
const errorCount = computed(() => devices.value.filter(d => d.status === '已停机' || d.status === '待维护').length)

function typeColor(type) {
  const map = {
    '太阳能板': '#67c23a', '风力发电机': '#409eff', '蓄电池': '#e6a23c',
    '变压器': '#909399', '电表': '#00b4d8', '空调系统': '#f56c6c', '照明系统': '#b37feb'
  }
  return map[type] || '#409eff'
}

async function loadDevices() {
  loading.value = true
  try {
    const params = {}
    if (searchType.value) params.deviceType = searchType.value
    if (searchStatus.value) params.status = searchStatus.value
    if (searchLocation.value) params.location = searchLocation.value
    const res = await getDevices(params)
    devices.value = res.data || []
  } catch (e) {
    devices.value = []
  } finally {
    loading.value = false
  }
}

function openAddDevice() {
  isEditDevice.value = false
  deviceForm.value = { deviceId: '', deviceType: '', location: '', power: 0, status: '运行中', installDate: '' }
  showDeviceDialog.value = true
}

function editDevice(row) {
  isEditDevice.value = true
  deviceForm.value = { ...row }
  showDeviceDialog.value = true
}

async function saveDeviceForm() {
  if (!deviceForm.value.deviceId) { ElMessage.warning('请输入设备编号'); return }
  saving.value = true
  try {
    await saveDevice(deviceForm.value)
    ElMessage.success(isEditDevice.value ? '修改成功' : '添加成功')
    showDeviceDialog.value = false
    await loadDevices()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function deleteDevice(id) {
  try {
    await ElMessageBox.confirm('确定删除该设备？删除后不可恢复。', '确认删除', { type: 'warning' })
    await delDev(id)
    ElMessage.success('删除成功')
    await loadDevices()
  } catch { /* cancelled */ }
}

onMounted(() => loadDevices())
</script>

<style scoped>
.stats-row { margin-bottom: 16px; }
.stat-item {
  display: flex; align-items: center; padding: 16px 20px;
  border-radius: 10px; transition: all 0.3s ease;
}
.stat-item:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.08); }
.stat-item.device-total { background: linear-gradient(135deg,#e8f4f8,#d4edf8); border-color: #a8d8ea; }
.stat-item.device-running { background: linear-gradient(135deg,#e8f8e8,#d4edda); border-color: #a3d9b1; }
.stat-item.device-error { background: linear-gradient(135deg,#fde8e8,#f8d4d4); border-color: #e8a8a8; }
.stat-icon { font-size: 28px; margin-right: 14px; }
.stat-body { display: flex; flex-direction: column; }
.stat-num { font-size: 28px; font-weight: 700; color: #303133; line-height: 1.2; }
.stat-label { font-size: 13px; color: #909399; margin-top: 2px; }
.filter-row { margin-bottom: 16px; padding: 12px 16px; background: #f8fafb; border-radius: 8px; align-items: center; }
.energy-table { border-radius: 8px; }
</style>
