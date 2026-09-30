<template>
  <div class="alert-bell">
    <el-badge :value="unreadCount" :hidden="unreadCount === 0" :max="99" class="bell-badge">
      <el-button :icon="Bell" circle size="small"
        :type="unreadCount > 0 ? 'danger' : 'default'"
        @click="showPanel = !showPanel" />
    </el-badge>

    <!-- 告警面板 -->
    <el-drawer v-model="showPanel" title="实时告警" direction="rtl" size="380px">
      <template #title>
        <div class="drawer-title">
          <span>🔔 实时告警</span>
          <div class="drawer-actions">
            <el-tag v-if="isConnected" type="success" size="small">● 已连接</el-tag>
            <el-tag v-else type="danger" size="small">● 未连接</el-tag>
            <el-button size="small" text :icon="Delete" @click="clearAlerts">清空</el-button>
          </div>
        </div>
      </template>

      <div v-if="alerts.length === 0" class="empty-alerts">
        <el-empty description="暂无告警" :image-size="80" />
      </div>

      <div v-else class="alert-list">
        <div v-for="(alert, idx) in alerts" :key="idx" class="alert-item"
          :class="{ 'alert-unread': !alert.read, 'alert-device': alert.type === 'DEVICE_ALERT',
            'alert-transaction': alert.type === 'TRANSACTION_ALERT',
            'alert-env': alert.type === 'ENV_ALERT',
            'alert-system': alert.type === 'SYSTEM_NOTIFICATION' }"
          @click="markAsRead(idx)">
          <div class="alert-icon">
            <span v-if="alert.type === 'DEVICE_ALERT'">🔧</span>
            <span v-else-if="alert.type === 'TRANSACTION_ALERT'">💰</span>
            <span v-else-if="alert.type === 'ENV_ALERT'">🌍</span>
            <span v-else>📢</span>
          </div>
          <div class="alert-body">
            <div class="alert-title">{{ alert.title }}</div>
            <div class="alert-content">{{ alert.content }}</div>
            <div class="alert-time">{{ alert.time }}</div>
          </div>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Bell, Delete } from '@element-plus/icons-vue'
import { useWebSocket } from '@/composables/useWebSocket'

const showPanel = ref(false)
const { isConnected, alerts, connect, disconnect, markAsRead, clearAlerts, getUnreadCount } = useWebSocket()

const unreadCount = computed(() => getUnreadCount())

// 连接 WebSocket
connect()
</script>

<style scoped>
.bell-badge { margin-right: 8px; }
.drawer-title { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.drawer-actions { display: flex; align-items: center; gap: 8px; }
.empty-alerts { display: flex; align-items: center; justify-content: center; height: 60vh; }
.alert-list { display: flex; flex-direction: column; gap: 8px; }
.alert-item {
  display: flex; gap: 12px; padding: 12px; border-radius: 8px;
  background: #fafafa; cursor: pointer; transition: all 0.2s ease;
  border-left: 4px solid #909399;
}
.alert-item:hover { background: #f0f0f0; }
.alert-unread { background: #f0f8ff; border-left-color: #409eff; }
.alert-device { border-left-color: #f56c6c; }
.alert-transaction { border-left-color: #e6a23c; }
.alert-env { border-left-color: #67c23a; }
.alert-system { border-left-color: #909399; }
.alert-icon { font-size: 24px; flex-shrink: 0; }
.alert-body { flex: 1; min-width: 0; }
.alert-title { font-size: 13px; font-weight: 600; color: #303133; }
.alert-content { font-size: 12px; color: #606266; margin: 4px 0; line-height: 1.4; }
.alert-time { font-size: 11px; color: #909399; }
</style>
