<template>
  <div class="ml-predict-page">
    <!-- Hero -->
    <div class="hero-section">
      <div class="hero-bg"></div>
      <div class="hero-content">
        <div class="hero-badge">📊 临床数据驱动</div>
        <h1>糖尿病 &amp; 血糖预测</h1>
        <p class="hero-desc">基于 PIMA 糖尿病数据集和动态血糖监测数据的 AI 预测模型</p>
      </div>
    </div>

    <el-card class="detail-card">
      <el-tabs v-model="activeTab" type="border-card">
        <el-tab-pane label="🔮 糖尿病风险评估" name="risk">
          <MlPredictions />
        </el-tab-pane>
        <el-tab-pane label="📈 胰岛素-血糖相关性" name="correlation">
          <InsulinGlucoseCorrelation />
        </el-tab-pane>
        <el-tab-pane label="📉 真实CGM血糖数据" name="glucose-data">
          <GlucoseDataExplorer />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import MlPredictions from '../../../components/medical/MlPredictions.vue'
import InsulinGlucoseCorrelation from '../../../components/medical/InsulinGlucoseCorrelation.vue'
import GlucoseDataExplorer from '../../../components/medical/GlucoseDataExplorer.vue'

const activeTab = ref('risk')
</script>

<style scoped>
.ml-predict-page { max-width: 1200px; margin: 0 auto; padding: 0 4px; }
.hero-section { position: relative; border-radius: 20px; overflow: hidden; margin-bottom: 24px; padding: 44px 40px; }
.hero-bg { position: absolute; inset: 0; background: linear-gradient(135deg, #4c1d95 0%, #6d28d9 50%, #8b5cf6 100%); }
.hero-content { position: relative; z-index: 1; text-align: center; color: #fff; }
.hero-badge { display: inline-block; padding: 4px 16px; border-radius: 20px; background: rgba(255,255,255,0.15); font-size: 12px; letter-spacing: 1px; margin-bottom: 14px; }
.hero-content h1 { font-size: 34px; font-weight: 700; margin: 0 0 8px; }
.hero-desc { font-size: 14px; opacity: 0.8; margin: 0; }
.detail-card { border-radius: 16px; }
</style>
