<template>
  <div class="energy-page">
    <el-tabs v-model="activeTab" class="energy-tabs">
      <!-- Tab 1: 设备管理 -->
      <el-tab-pane label="📟 设备管理" name="device">
        <el-card shadow="hover" class="tab-card">
          <template #header>
            <div class="flex-between">
              <span class="card-title">📟 能源设备管理</span>
            </div>
          </template>
          <EnergyDevicePanel />
        </el-card>
      </el-tab-pane>

      <!-- Tab 2: 能耗数据 -->
      <el-tab-pane label="📊 能耗数据" name="consumption">
        <EnergyConsumptionChart />
      </el-tab-pane>

      <!-- Tab 3: AI智能分析 -->
      <el-tab-pane label="🤖 AI智能分析" name="ai-analysis">
        <el-card shadow="hover" class="tab-card">
          <template #header>
            <div class="flex-between">
              <span class="card-title">🤖 AI 智能分析</span>
              <el-tag type="success" effect="dark" size="small">
                <span style="display:inline-flex;align-items:center;gap:4px">⚡ 实时分析</span>
              </el-tag>
            </div>
          </template>
          <EnergyAIInsight @data-loaded="onAiDataLoaded" />
          <template #append>
            <EnergyAlertList :anomaly-list="anomalyList" style="margin-top:16px" />
          </template>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import EnergyDevicePanel from './energy/EnergyDevicePanel.vue'
import EnergyConsumptionChart from './energy/EnergyConsumptionChart.vue'
import EnergyAlertList from './energy/EnergyAlertList.vue'
import EnergyAIInsight from './energy/EnergyAIInsight.vue'

const activeTab = ref('device')
const anomalyList = ref([])

function onAiDataLoaded(data) {
  anomalyList.value = data.anomalyList || []
}
</script>

<style scoped>
.energy-page { padding: 8px; }
.energy-tabs { --el-tabs-header-height: 48px; }
.tab-card {
  border-radius: 12px;
  transition: all 0.3s ease;
}
.tab-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
}
.card-title {
  font-size: 16px;
  font-weight: 600;
  background: linear-gradient(135deg, #409eff, #67c23a);
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
}
.flex-between {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
:deep(.el-tabs__item) {
  font-size: 15px;
  font-weight: 500;
  padding: 0 20px;
}
:deep(.el-tabs__item.is-active) {
  color: #409eff;
  font-weight: 600;
}
:deep(.el-tabs__active-bar) {
  background: linear-gradient(90deg, #409eff, #67c23a);
  height: 3px;
}
:deep(.el-empty__description p) {
  font-size: 13px;
  color: #909399;
}
</style>
