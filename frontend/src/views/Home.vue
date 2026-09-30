<template>
  <div class="home-page">
    <!-- Hero Banner -->
    <div class="hero">
      <div class="hero-content">
        <h1>万象智枢 <span style="font-size:18px;opacity:0.7;font-weight:normal">MyriHub</span></h1>
        <p>AI赋能多场景智能分析平台 — 覆盖能源管理、环境监测、金融风控、医疗诊断、交通仿真五大行业</p>
        <div class="hero-actions">
          <el-button type="primary" size="large" round @click="router.push('/scenarios')">
            查看场景
          </el-button>
          <el-button size="large" round plain @click="router.push('/login')">
            登录体验
          </el-button>
        </div>
      </div>
    </div>

    <!-- Feature Cards -->
    <div class="features">
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" v-for="mod in modules" :key="mod.key">
          <el-card class="feature-card" shadow="hover" @click="router.push(mod.path)">
            <div class="card-icon">
              <el-icon :size="36" color="#409eff"><component :is="mod.icon" /></el-icon>
            </div>
            <h3>{{ mod.title }}</h3>
            <p>{{ mod.description }}</p>
            <el-tag size="small" type="info">{{ mod.tags }}</el-tag>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- Quick Stats -->
    <el-card class="stats-card" shadow="never">
      <template #header><span>平台概览</span></template>
      <el-row :gutter="20">
        <el-col :span="6" v-for="stat in stats" :key="stat.label">
          <div class="stat-item">
            <span class="stat-value">{{ stat.value }}</span>
            <span class="stat-label">{{ stat.label }}</span>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup>
import { ref, shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { Reading, Monitor, ChatDotRound, Coin } from '@element-plus/icons-vue'

const router = useRouter()

const modules = shallowRef([
  { key: 'energy', title: '⚡ 能源管理', description: '负荷预测、设备故障预测、能耗分析、节能优化建议。AI赋能智能电网与设备运维。', path: '/scenarios/energy', tags: '负荷预测·故障诊断', icon: Monitor },
  { key: 'environment', title: '🌿 环境监测', description: '空气质量监测、AQI预测、污染源分析、极端天气分类。守护生态环境。', path: '/scenarios/environment', tags: 'AQI预测·污染分析', icon: Monitor },
  { key: 'finance', title: '💰 金融风控', description: '交易风险评估、客户流失预测、反欺诈检测、金融健康评分。智能风控体系。', path: '/scenarios/finance', tags: '风控·流失预测', icon: Coin },
  { key: 'medical', title: '🏥 医疗诊断', description: 'AI智能问诊、病历分析、糖尿病风险评估、血糖预测。AI辅助医疗决策。', path: '/scenarios/medical', tags: '问诊·风险评估', icon: Reading },
  { key: 'traffic', title: '🚦 交通仿真', description: '交通流量预测、拥堵分析、事故风险预测、沙盘模拟。智慧交通管理。', path: '/scenarios/traffic', tags: '流量预测·仿真', icon: ChatDotRound }
])

const stats = [
  { label: '应用场景', value: '5' },
  { label: 'AI模型', value: '40+' },
  { label: '数据库表', value: '14' },
  { label: 'RESTful APIs', value: '60+' }
]
</script>

<style scoped>
.home-page { max-width: 1200px; margin: 0 auto; }
.hero {
  background: linear-gradient(135deg, #1d1e2c 0%, #2d3a6b 100%);
  border-radius: 16px;
  padding: 60px 40px;
  text-align: center;
  margin-bottom: 30px;
  color: #fff;
}
.hero h1 { font-size: 36px; margin-bottom: 12px; }
.hero p { font-size: 16px; opacity: 0.8; margin-bottom: 24px; }
.hero-actions { display: flex; gap: 12px; justify-content: center; }
.features { margin-bottom: 30px; }
.feature-card {
  cursor: pointer;
  margin-bottom: 20px;
  transition: transform 0.2s, box-shadow 0.2s;
}
.feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0,0,0,0.1) !important;
}
.card-icon { text-align: center; margin-bottom: 16px; }
.feature-card h3 { text-align: center; font-size: 18px; margin-bottom: 8px; }
.feature-card p { text-align: center; font-size: 13px; color: #909399; margin-bottom: 12px; line-height: 1.6; }
.feature-card .el-tag { display: table; margin: 0 auto; }
.stats-card { margin-bottom: 20px; }
.stats-card :deep(.el-card__header) { font-weight: bold; font-size: 16px; }
.stat-item { display: flex; flex-direction: column; align-items: center; padding: 20px 0; }
.stat-value { font-size: 36px; font-weight: bold; color: #409eff; }
.stat-label { font-size: 14px; color: #909399; margin-top: 6px; }
</style>
