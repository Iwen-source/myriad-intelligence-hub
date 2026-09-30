<template>
  <div class="energy-alert-list">
    <el-card shadow="never" class="ai-card">
      <template #header>
        <div class="ai-card-header">
          <span><span class="ai-icon">🛡️</span> 设备异常检测</span>
          <el-tag v-if="anomalyList.length > 0" :type="anomalyTagType" size="small" effect="dark">
            {{ anomalyList.length }} 项异常
          </el-tag>
        </div>
      </template>
      <div v-if="anomalyList.length > 0" class="anomaly-list">
        <div v-for="item in anomalyList" :key="item.id" class="anomaly-item" :class="'severity-' + item.severity">
          <div class="anomaly-header">
            <el-tag :type="severityTag(item.severity)" size="small" effect="dark" class="severity-tag">
              {{ severityLabel(item.severity) }}
            </el-tag>
            <span class="anomaly-time">{{ item.time }}</span>
          </div>
          <p class="anomaly-msg">{{ item.message }}</p>
          <p class="anomaly-suggest">{{ item.suggestion }}</p>
        </div>
      </div>
      <div v-else style="text-align:center;padding:40px 0;color:#909399">
        <span style="font-size:40px">✅</span>
        <p style="margin-top:12px">暂无异常，设备运行正常</p>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  anomalyList: { type: Array, default: () => [] }
})

const anomalyTagType = computed(() => {
  if (!props.anomalyList?.length) return 'success'
  const high = props.anomalyList.filter(a => a.severity === 'high' || a.severity === 'critical')
  return high.length > 0 ? 'danger' : 'warning'
})

function severityTag(severity) {
  const map = { critical: 'danger', high: 'danger', medium: 'warning', low: 'info', normal: 'success' }
  return map[severity] || 'info'
}

function severityLabel(severity) {
  const map = { critical: '🚨危急', high: '🔴高', medium: '🟡中', low: '🟢低', normal: '✅正常' }
  return map[severity] || severity
}
</script>

<style scoped>
.ai-card {
  border-radius: 10px; height: 100%; border: 1px solid #e8e8e8;
  transition: all 0.3s ease;
}
.ai-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.06); }
.ai-card-header { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
.ai-icon { margin-right: 4px; }
.anomaly-list { max-height: 580px; overflow-y: auto; }
.anomaly-item {
  padding: 12px 14px; border-radius: 8px; margin-bottom: 10px;
  border-left: 4px solid #909399; background: #fafafa; transition: all 0.2s ease;
}
.anomaly-item:hover { background: #f0f0f0; }
.anomaly-item.severity-critical,
.anomaly-item.severity-high { border-left-color: #f56c6c; background: #fef0f0; }
.anomaly-item.severity-medium { border-left-color: #e6a23c; background: #fdf6ec; }
.anomaly-item.severity-normal { border-left-color: #67c23a; }
.anomaly-item.severity-low { background: #f4f4f5; }
.anomaly-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.severity-tag { font-weight: 600; }
.anomaly-time { font-size: 12px; color: #909399; }
.anomaly-msg { font-size: 13px; font-weight: 600; color: #303133; margin: 4px 0; }
.anomaly-suggest { font-size: 12px; color: #606266; margin: 2px 0 0; padding: 6px 8px; background: rgba(255,255,255,.7); border-radius: 4px; }
.anomaly-list::-webkit-scrollbar { width: 4px; }
.anomaly-list::-webkit-scrollbar-thumb { background: #dcdfe6; border-radius: 2px; }
.anomaly-list::-webkit-scrollbar-track { background: transparent; }
</style>
