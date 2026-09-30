<template>
  <div class="page">
    <div class="scenario-hero">
      <h1>AI应用场景</h1>
      <p>探索人工智能在多个行业的实际应用与创新成果</p>
    </div>

    <!-- 重点推荐 - AI智能问诊 -->
    <el-card class="featured-card" shadow="hover" @click="router.push('/scenarios/medical/ai-consult')">
      <div class="featured-content">
        <div class="featured-icon">🤖</div>
        <div class="featured-text">
          <h2>AI 智能问诊</h2>
          <p>大模型驱动的智能诊断系统，描述症状即可获得AI医生的诊断建议与疾病分析</p>
          <el-tag size="small" type="success" effect="dark" class="featured-tag">🔥 热门推荐</el-tag>
          <el-tag size="small" type="warning" effect="dark" class="featured-tag">AI 赋能</el-tag>
        </div>
      </div>
    </el-card>

    <!-- 场景卡片 -->
    <el-row :gutter="20">
      <el-col :xs="24" :sm="12" :md="8" v-for="s in scenarios" :key="s.key">
        <el-card class="scenario-card" shadow="hover" @click="router.push(s.path)">
          <div class="scenario-icon">
            <el-icon :size="40" :color="s.color"><component :is="s.icon" /></el-icon>
          </div>
          <h3>{{ s.title }}</h3>
          <p>{{ s.desc }}</p>
          <div class="scenario-footer">
            <el-tag size="small" :color="s.color" style="color:#fff">{{ s.tag }}</el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { shallowRef } from 'vue'
import { useRouter } from 'vue-router'
import { Lightning, User, Sunny, Money, Van } from '@element-plus/icons-vue'

const router = useRouter()
const scenarios = shallowRef([
  { key: 'medical', title: '医疗诊断', desc: '基于AI的智能诊断系统，辅助医生进行疾病筛查和分析', path: '/scenarios/medical', icon: User, color: '#67c23a', tag: '智慧医疗' },
  { key: 'energy', title: '能源管理', desc: 'AI驱动的智能能源设备监控、能耗分析和预测维护', path: '/scenarios/energy', icon: Lightning, color: '#409eff', tag: '节能减排' },
  { key: 'environment', title: '环境监测', desc: '利用AI技术进行空气质量、水质等环境指标实时监测', path: '/scenarios/environment', icon: Sunny, color: '#e6a23c', tag: '环境保护' },
  { key: 'finance', title: '金融风控', desc: 'AI驱动的金融风险识别、反欺诈和信用评估系统', path: '/scenarios/finance', icon: Money, color: '#f56c6c', tag: '风险控制' },
  { key: 'traffic', title: '交通仿真', desc: '基于AI的城市交通流量预测、拥堵分析和智能调度', path: '/scenarios/traffic', icon: Van, color: '#909399', tag: '智慧交通' }
])
</script>

<style scoped>
.scenario-hero { text-align:center; padding:30px 0 20px; }
.scenario-hero h1 { font-size:28px; color:#303133; margin-bottom:8px; }
.scenario-hero p { color:#909399; }

.featured-card {
  margin-bottom: 24px;
  cursor: pointer;
  border-radius: 16px;
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border: 1px solid #a7f3d0;
  transition: all 0.3s;
}
.featured-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(5, 150, 105, 0.15);
}
.featured-content {
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 8px 0;
}
.featured-icon {
  font-size: 64px;
  line-height: 1;
}
.featured-text h2 {
  margin: 0 0 8px;
  font-size: 22px;
  color: #065f46;
}
.featured-text p {
  margin: 0 0 12px;
  color: #047857;
  font-size: 14px;
}
.featured-tag {
  margin-right: 8px;
}

.scenario-card { cursor:pointer; margin-bottom:20px; text-align:center; padding:20px 0; transition:transform 0.2s; }
.scenario-card:hover { transform:translateY(-4px); }
.scenario-icon { margin-bottom:16px; }
.scenario-card h3 { font-size:18px; margin-bottom:8px; }
.scenario-card p { font-size:13px; color:#909399; line-height:1.7; margin-bottom:12px; min-height:40px; }
.scenario-footer { display:flex; justify-content:center; }
</style>
