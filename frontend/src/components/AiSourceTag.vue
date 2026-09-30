<template>
  <el-tag
    v-if="state !== 'unknown'"
    size="mini"
    :type="state === 'ml' ? 'success' : (state === 'fallback' ? 'info' : 'warning')"
    effect="plain"
    class="ai-source-tag"
  >
    {{ text }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

/**
 * AiSourceTag — 统一标注一条 AI 结果的来源，避免“伪AI/静默降级”。
 * 兼容后端三类字段写法：
 *   - isMlGenerated (Map 返回值，如环境/交通)
 *   - mlGenerated   (typed DTO / AnalysisMetadata 子类，Jackson 序列化名)
 *   - is_deep_learning (CT 工作站)
 * 也支持显式 source 字符串（如 deepseek-llm / local-kb-rules / lstm_model / statistical_fallback）。
 */
const props = defineProps({
  result: { type: [Object, null], default: null },
  mlText: { type: String, default: 'ML模型' },
  fallbackText: { type: String, default: '规则/统计' },
  unknownText: { type: String, default: '来源未知' }
})

const normalized = computed(() => {
  const r = props.result || {}
  const src = String(r.source || '').toLowerCase()
  if (src.includes('deepseek') || src.includes('llm')) return 'ml'
  if (src.includes('lstm') || src.includes('model') || src.includes('xgb') || src.includes('unet') || src.includes('dnn')) return 'ml'
  if (src.includes('rule') || src.includes('fallback') || src.includes('statistical') || src.includes('kb') || src.includes('heuristic')) return 'fallback'
  const flag = r.isMlGenerated ?? r.mlGenerated ?? r.is_deep_learning
  if (flag === true) return 'ml'
  if (flag === false) return 'fallback'
  return 'unknown'
})

const state = computed(() => normalized.value)

const text = computed(() => {
  if (state.value === 'ml') return props.mlText
  if (state.value === 'fallback') return props.fallbackText
  return props.unknownText
})
</script>

<style scoped>
.ai-source-tag { margin-left: 6px; vertical-align: middle; }
</style>
