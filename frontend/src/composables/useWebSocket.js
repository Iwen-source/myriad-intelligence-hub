/**
 * WebSocket 实时推送客户端 composable
 * 
 * 用于接收后端实时告警推送（设备告警、交易预警、环境超标等）
 * 
 * 使用示例：
 *   import { useWebSocket } from '@/composables/useWebSocket'
 *   const { isConnected, alerts, connect, disconnect } = useWebSocket()
 *   connect()
 * 
 * 告警消息格式：
 *   {
 *     type: 'DEVICE_ALERT' | 'TRANSACTION_ALERT' | 'ENV_ALERT' | 'SYSTEM_NOTIFICATION' | 'PONG',
 *     title: string,
 *     content: string,
 *     timestamp: number
 *   }
 */
import { ref, onUnmounted } from 'vue'

// 从环境变量或默认值获取后端地址
const WS_BASE = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:8088/api/ws`

export function useWebSocket() {
  const isConnected = ref(false)
  const alerts = ref([])
  const maxAlerts = 50 // 最多保留50条未读告警

  let ws = null
  let reconnectTimer = null
  let heartbeatTimer = null

  function connect() {
    if (ws && ws.readyState === WebSocket.OPEN) return

    const token = localStorage.getItem('token') || ''
    ws = new WebSocket(`${WS_BASE}/alerts?token=${encodeURIComponent(token)}`)

    ws.onopen = () => {
      console.log('[WS] 连接成功')
      isConnected.value = true
      startHeartbeat()
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        // 心跳响应忽略
        if (msg.type === 'PONG') return

        // 新告警插到列表头部
        alerts.value.unshift({
          ...msg,
          time: new Date(msg.timestamp).toLocaleString('zh-CN'),
          read: false
        })
        // 限制数量
        if (alerts.value.length > maxAlerts) {
          alerts.value = alerts.value.slice(0, maxAlerts)
        }
      } catch (e) {
        console.warn('[WS] 消息解析失败:', event.data)
      }
    }

    ws.onclose = (event) => {
      console.log('[WS] 连接关闭:', event.code)
      isConnected.value = false
      stopHeartbeat()
      // 自动重连（5秒后）
      if (!reconnectTimer) {
        reconnectTimer = setTimeout(() => {
          reconnectTimer = null
          connect()
        }, 5000)
      }
    }

    ws.onerror = (err) => {
      console.error('[WS] 连接错误:', err)
      ws.close()
    }
  }

  function disconnect() {
    stopHeartbeat()
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  function startHeartbeat() {
    stopHeartbeat()
    // 每30秒发送心跳
    heartbeatTimer = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  /** 标记指定告警为已读 */
  function markAsRead(index) {
    if (alerts.value[index]) {
      alerts.value[index].read = true
    }
  }

  /** 清空所有告警 */
  function clearAlerts() {
    alerts.value = []
  }

  /** 未读告警数 */
  function getUnreadCount() {
    return alerts.value.filter(a => !a.read).length
  }

  // 组件卸载时自动断开
  if (typeof onUnmounted === 'function') {
    onUnmounted(disconnect)
  }

  return {
    isConnected,
    alerts,
    connect,
    disconnect,
    markAsRead,
    clearAlerts,
    getUnreadCount
  }
}
