<template>
  <div class="ai-consult-page">
    <!-- Hero -->
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">🤖 大模型驱动</div>
        <h1>AI 智能问诊</h1>
        <p class="hero-desc">填写患者信息，AI 大模型辅助分析症状并提供诊断建议</p>
      </div>
    </div>
    <AiDoctor />
  </div>
</template>

<script setup>
import AiDoctor from '../../../components/medical/AiDoctor.vue'
</script>

<style scoped>
.ai-consult-page { max-width: 1100px; margin: 0 auto; padding: 0 4px; }
.hero-section { position: relative; border-radius: 20px; overflow: hidden; margin-bottom: 24px; padding: 44px 40px; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #1e3a5f 0%, #2563eb 50%, #3b82f6 100%); }
.hero-content { position: relative; z-index: 1; text-align: center; color: #fff; }
.hero-badge { display: inline-block; padding: 4px 16px; border-radius: 20px; background: rgba(255,255,255,0.15); font-size: 12px; letter-spacing: 1px; margin-bottom: 14px; }
.hero-content h1 { font-size: 34px; font-weight: 700; margin: 0 0 8px; }
.hero-desc { font-size: 14px; opacity: 0.8; margin: 0; }
</style>
