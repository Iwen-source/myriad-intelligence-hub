<template>
  <div class="douya-root">
    <!-- 对话面板 -->
    <transition name="douya-pop">
      <section v-if="open" class="douya-panel" role="dialog" aria-label="豆芽智能助手">
        <header class="douya-header">
          <div class="douya-id">
            <div class="douya-avatar">🌱</div>
            <div class="douya-id-text">
              <div class="douya-name">
                豆芽 <span class="douya-badge">智能助手</span>
              </div>
              <div class="douya-sub">
                <i class="douya-dot"></i>
                {{ mode === 'llm' ? '大模型在线' : '本地知识库' }} · 万象智枢
              </div>
            </div>
          </div>
          <div class="douya-actions">
            <button class="douya-icon-btn" title="清空对话" @click="clearChat">
              <el-icon><Delete /></el-icon>
            </button>
            <button class="douya-icon-btn" title="收起" @click="open = false">
              <el-icon><Close /></el-icon>
            </button>
          </div>
        </header>

        <div ref="scroller" class="douya-body">
          <div
            v-for="(m, i) in messages"
            :key="i"
            class="douya-msg"
            :class="m.role === 'user' ? 'is-user' : 'is-bot'"
          >
            <div class="douya-bubble">{{ m.content }}</div>
          </div>

          <div v-if="loading" class="douya-msg is-bot">
            <div class="douya-bubble douya-typing"><span></span><span></span><span></span></div>
          </div>

          <!-- 快捷问题 -->
          <div v-if="showSuggestions" class="douya-suggests">
            <div class="douya-suggests-title">你可以这样问我：</div>
            <button
              v-for="(s, i) in suggestions"
              :key="i"
              class="douya-chip"
              @click="send(s)"
            >{{ s }}</button>
          </div>
        </div>

        <footer class="douya-footer">
          <el-input
            v-model="input"
            type="textarea"
            :autosize="{ minRows: 1, maxRows: 4 }"
            resize="none"
            placeholder="问问豆芽任何关于本平台的问题…（Enter 发送 / Shift+Enter 换行）"
            @keydown.enter="onEnter"
          />
          <el-button
            type="primary"
            class="douya-send"
            :loading="loading"
            :disabled="!input.trim()"
            @click="send()"
          >发送</el-button>
        </footer>
      </section>
    </transition>

    <!-- 悬浮按钮 -->
    <button class="douya-fab" :class="{ 'is-open': open }" @click="toggle" title="豆芽 · 智能助手">
      <span class="douya-fab-emoji">🌱</span>
      <span v-if="!open" class="douya-fab-text">豆芽</span>
      <span class="douya-fab-ping"></span>
    </button>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { Delete, Close } from '@element-plus/icons-vue'
import { assistantChat, assistantSuggestions } from '../api/modules/assistant'

const open = ref(false)
const input = ref('')
const loading = ref(false)
const scroller = ref(null)
const mode = ref('local')
const suggestions = ref([
  '这个平台是做什么的？',
  '血糖预测怎么用？',
  'CT 影像工作台能做什么？',
  '金融风控有哪些功能？'
])

const messages = ref([
  {
    role: 'assistant',
    isGreeting: true,
    content: '你好呀，我是豆芽 🌱！万象智枢的智能助手，平台里的功能我门儿清。想了解哪块？直接问我就好～'
  }
])

const showSuggestions = computed(() => messages.value.filter((m) => !m.isGreeting).length === 0)

onMounted(async () => {
  try {
    const res = await assistantSuggestions()
    if (res && res.code === 200 && Array.isArray(res.data) && res.data.length) {
      suggestions.value = res.data.slice(0, 6)
    }
  } catch (e) {
    /* 忽略：使用默认问题 */
  }
})

function toggle() {
  open.value = !open.value
  if (open.value) scrollToBottom()
}

async function scrollToBottom() {
  await nextTick()
  if (scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight
}

function onEnter(e) {
  if (e.shiftKey) return // 允许换行
  e.preventDefault()
  send()
}

function clearChat() {
  messages.value = [
    {
      role: 'assistant',
      isGreeting: true,
      content: '对话已清空～ 我们可以重新开始聊 🌱'
    }
  ]
}

async function send(text) {
  const content = (typeof text === 'string' ? text : input.value).trim()
  if (!content || loading.value) return
  input.value = ''
  messages.value.push({ role: 'user', content })
  scrollToBottom()

  const history = messages.value
    .filter((m) => !m.isGreeting)
    .slice(0, -1) // 去掉刚加入的这条用户消息（作为 message 单独发送）
    .slice(-20)
    .map((m) => ({ role: m.role, content: m.content }))

  loading.value = true
  try {
    const res = await assistantChat({ message: content, history })
    if (res && res.code === 200 && res.data) {
      mode.value = res.data.mode || 'local'
      messages.value.push({ role: 'assistant', content: res.data.reply })
    } else {
      messages.value.push({
        role: 'assistant',
        content: '抱歉，豆芽刚刚开小差了，请稍后再试一次 🌱'
      })
    }
  } catch (e) {
    messages.value.push({
      role: 'assistant',
      content: '连接不上助手服务了，请确认后端已启动后重试 🌱'
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}
</script>

<style scoped>
.douya-root { position: fixed; right: 24px; bottom: 24px; z-index: 3000; }

/* 悬浮按钮 */
.douya-fab {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  height: 52px;
  padding: 0 18px;
  border: none;
  border-radius: 26px;
  cursor: pointer;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  background: linear-gradient(135deg, #22c55e 0%, #0ea5e9 100%);
  box-shadow: 0 8px 22px rgba(16, 185, 129, 0.45);
  transition: transform 0.15s ease, box-shadow 0.2s ease;
  margin-left: auto;
}
.douya-fab:hover { transform: translateY(-2px); box-shadow: 0 12px 26px rgba(16, 185, 129, 0.55); }
.douya-fab.is-open { height: 46px; padding: 0 14px; }
.douya-fab-emoji { font-size: 20px; }
.douya-fab-text { letter-spacing: 1px; }
.douya-fab-ping {
  position: absolute; top: 6px; right: 8px; width: 9px; height: 9px;
  background: #fff; border-radius: 50%; opacity: 0.9;
  animation: douya-ping 1.8s infinite;
}
@keyframes douya-ping {
  0% { box-shadow: 0 0 0 0 rgba(255,255,255,0.7); }
  70% { box-shadow: 0 0 0 8px rgba(255,255,255,0); }
  100% { box-shadow: 0 0 0 0 rgba(255,255,255,0); }
}

/* 面板 */
.douya-panel {
  position: absolute; right: 0; bottom: 66px;
  width: 380px; height: 560px; max-height: calc(100vh - 120px);
  display: flex; flex-direction: column;
  background: #fff; border-radius: 16px; overflow: hidden;
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.28);
  border: 1px solid rgba(15, 23, 42, 0.06);
}
.douya-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 14px;
  background: linear-gradient(135deg, #1d1e2c 0%, #2d3a6b 100%);
  color: #fff;
}
.douya-id { display: flex; align-items: center; gap: 10px; }
.douya-avatar {
  width: 38px; height: 38px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 20px; background: rgba(255,255,255,0.14);
}
.douya-name { font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 6px; }
.douya-badge {
  font-size: 10px; font-weight: 500; padding: 1px 6px; border-radius: 8px;
  background: rgba(34,197,94,0.9); color: #fff;
}
.douya-sub { font-size: 11px; opacity: 0.8; display: flex; align-items: center; gap: 5px; margin-top: 2px; }
.douya-dot { width: 6px; height: 6px; border-radius: 50%; background: #4ade80; display: inline-block; }
.douya-actions { display: flex; gap: 4px; }
.douya-icon-btn {
  border: none; background: transparent; color: #fff; cursor: pointer;
  width: 28px; height: 28px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
  opacity: 0.85;
}
.douya-icon-btn:hover { background: rgba(255,255,255,0.15); opacity: 1; }

.douya-body {
  flex: 1; overflow-y: auto; padding: 14px;
  background: #f6f8fb; display: flex; flex-direction: column; gap: 10px;
}
.douya-msg { display: flex; }
.douya-msg.is-user { justify-content: flex-end; }
.douya-msg.is-bot { justify-content: flex-start; }
.douya-bubble {
  max-width: 82%; padding: 9px 12px; border-radius: 12px;
  font-size: 13.5px; line-height: 1.6; white-space: pre-wrap; word-break: break-word;
}
.is-bot .douya-bubble { background: #fff; color: #1f2937; border: 1px solid #e5e7eb; border-top-left-radius: 4px; }
.is-user .douya-bubble {
  background: linear-gradient(135deg, #22c55e 0%, #16a34a 100%);
  color: #fff; border-top-right-radius: 4px;
}

.douya-typing { display: flex; gap: 4px; align-items: center; }
.douya-typing span {
  width: 6px; height: 6px; border-radius: 50%; background: #9ca3af; display: inline-block;
  animation: douya-blink 1.2s infinite both;
}
.douya-typing span:nth-child(2) { animation-delay: 0.2s; }
.douya-typing span:nth-child(3) { animation-delay: 0.4s; }
@keyframes douya-blink { 0%, 80%, 100% { opacity: 0.25; } 40% { opacity: 1; } }

.douya-suggests { display: flex; flex-wrap: wrap; gap: 8px; padding: 4px 2px; }
.douya-suggests-title { width: 100%; font-size: 12px; color: #94a3b8; }
.douya-chip {
  border: 1px solid #cbd5e1; background: #fff; color: #334155;
  font-size: 12.5px; padding: 6px 10px; border-radius: 14px; cursor: pointer;
  transition: all 0.15s ease;
}
.douya-chip:hover { border-color: #22c55e; color: #16a34a; background: #f0fdf4; }

.douya-footer {
  display: flex; gap: 8px; align-items: flex-end;
  padding: 10px 12px; background: #fff; border-top: 1px solid #eef2f7;
}
.douya-footer :deep(.el-textarea__inner) {
  border-radius: 10px; font-size: 13.5px; box-shadow: none;
}
.douya-send { flex: 0 0 auto; height: 34px; }

/* 动画 */
.douya-pop-enter-active, .douya-pop-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.douya-pop-enter-from, .douya-pop-leave-to { opacity: 0; transform: translateY(12px) scale(0.98); }

@media (max-width: 520px) {
  .douya-panel { width: calc(100vw - 32px); right: -4px; }
}
</style>
