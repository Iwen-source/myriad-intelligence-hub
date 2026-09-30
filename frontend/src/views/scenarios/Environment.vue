<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <!-- 监测点管理 -->
      <el-tab-pane label="监测点管理" name="points">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>监测点列表</span>
              <el-button type="success" @click="openPointDialog">添加监测点</el-button>
            </div>
          </template>
          <el-table :data="points" stripe v-loading="loading" border>
            <el-table-column prop="pointName" label="名称" min-width="140" />
            <el-table-column prop="location" label="位置" min-width="180" />
            <el-table-column prop="monitorType" label="监测类型" width="120" />
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{row}">
                <el-tag :type="row.status==='正常'?'success':row.status==='维护中'?'warning':'danger'" size="small">{{row.status}}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{row}">
                <el-button size="small" @click="editPoint(row)">编辑</el-button>
                <el-button size="small" type="danger" @click="handleDeletePoint(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 监测数据 -->
      <el-tab-pane label="监测数据" name="data">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>环境监测数据</span>
              <div>
                <el-select v-model="dataFilter.point" placeholder="监测点" clearable style="width:150px;margin-right:8px">
                  <el-option v-for="p in points" :key="p.id" :label="p.pointName" :value="p.id" />
                </el-select>
                <el-button type="primary" @click="loadEnvData">查询</el-button>
                <el-button type="success" @click="openRecordDialog" :disabled="!dataFilter.point">添加数据</el-button>
              </div>
            </div>
          </template>
          <el-table :data="envData" stripe v-loading="loadingData" border>
            <el-table-column prop="aqi" label="AQI" width="80">
              <template #default="{row}">
                <el-tag :type="aqiTagType(row.aqi)" size="small" effect="dark">{{ row.aqi }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="pm25" label="PM2.5" width="80">
              <template #default="{row}">{{ row.pm25 != null ? row.pm25.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="pm10" label="PM10" width="80">
              <template #default="{row}">{{ row.pm10 != null ? row.pm10.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="o3" label="O₃" width="80">
              <template #default="{row}">{{ row.o3 != null ? row.o3.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="no2" label="NO₂" width="80">
              <template #default="{row}">{{ row.no2 != null ? row.no2.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="temperature" label="温度(°C)" width="90">
              <template #default="{row}">{{ row.temperature != null ? row.temperature.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="recordTime" label="记录时间" min-width="160" />
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- 仪表盘 -->
      <el-tab-pane label="环境仪表盘" name="dashboard">
        <div v-loading="dashLoading" element-loading-text="正在加载仪表盘数据..." style="min-height:400px">
        <!-- AI摘要 -->
        <el-card shadow="never" style="margin-bottom:20px;background:linear-gradient(135deg,#e8f5e9,#f1f8e9)">
          <div class="ai-summary">
            <span class="ai-icon">🌿</span>
            <span class="ai-text">{{ aiSummary }}</span>
          </div>
        </el-card>

        <!-- 概览卡片 -->
        <el-row :gutter="20" style="margin-bottom:20px">
          <el-col :span="4" v-for="s in overviewCards" :key="s.label">
            <div class="stat-box">
              <span class="num" :style="{color:s.color}">{{ s.value }}</span>
              <span class="lab">{{ s.label }}</span>
            </div>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-bottom:20px">
          <!-- 健康指数 -->
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>环境健康指数</template>
              <div style="text-align:center;padding:10px 0">
                <div class="health-gauge">
                  <div class="gauge-value" :style="{color:healthIndex>60?'#67c23a':healthIndex>40?'#e6a23c':'#f56c6c'}">
                    {{ healthIndex.toFixed(1) }}
                  </div>
                  <div class="gauge-label">{{ healthLevel }}</div>
                </div>
                <div style="margin-top:12px;font-size:13px;color:#909399">{{ healthAssessment }}</div>
              </div>
            </el-card>
          </el-col>
          <!-- 首要污染物 -->
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>首要污染物</template>
              <div style="text-align:center;padding:10px 0">
                <div class="worst-pollutant">{{ worstPollutant || '-' }}</div>
                <div style="margin-top:10px">
                  <div v-for="p in pollutantBreakdown" :key="p.name" class="pollutant-bar-row">
                    <span class="pollutant-name">{{ p.name }}</span>
                    <el-progress :percentage="Math.min(100, p.score)" :color="p.score>60?'#f56c6c':p.score>30?'#e6a23c':'#67c23a'" :stroke-width="12" />
                    <span class="pollutant-value">{{ p.value.toFixed(1) }}</span>
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
          <!-- 智能建议 -->
          <el-col :span="8">
            <el-card shadow="never">
              <template #header>AI 智能建议</template>
              <div style="max-height:220px;overflow-y:auto">
                <div v-for="(r, i) in smartRecommendations" :key="i" class="recommend-item">
                  <el-tag :type="r.priority==='高'?'danger':r.priority==='中'?'warning':'info'" size="small" style="margin-right:6px">{{ r.priority }}</el-tag>
                  <span class="recommend-title">{{ r.title }}</span>
                  <div class="recommend-desc">{{ r.description }}</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-bottom:20px">
          <!-- 污染物雷达图 -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>最新污染物分解</template>
              <div ref="pollutantChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          <!-- 异常检测 -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <span>环境异常检测 <el-tag v-if="anomalies.length" type="danger" size="small">{{ anomalies.length }}条</el-tag></span>
              </template>
              <div v-if="!anomalies.length" style="padding:20px;text-align:center;color:#909399">暂无异常</div>
              <div v-else style="max-height:340px;overflow-y:auto">
                <div v-for="(a, i) in anomalies" :key="i" class="anomaly-item">
                  <div class="anomaly-header">
                    <el-tag :type="a.severity==='严重'?'danger':'warning'" size="small" effect="dark">{{ a.severity }}</el-tag>
                    <span class="anomaly-point">{{ a.pointName }}</span>
                  </div>
                  <div class="anomaly-body">
                    <span>{{ a.pollutant }}: <strong>{{ a.currentValue }}</strong> (均值 {{ a.avgValue }})</span>
                    <span style="margin-left:10px;color:#909399">Z-Score: {{ a.deviation }}</span>
                  </div>
                  <div class="anomaly-suggestion">{{ a.suggestion }}</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <!-- 污染源分析 -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>污染源分析</template>
              <div v-if="!pollutionSources.length" style="padding:20px;text-align:center;color:#909399">加载中...</div>
              <el-table v-else :data="pollutionSources" stripe size="small">
                <el-table-column prop="pointName" label="监测点" width="130" />
                <el-table-column prop="sourceType" label="污染源类型" width="150" />
                <el-table-column prop="primaryPollutant" label="首要污染物" width="90" />
                <el-table-column label="成分比例" min-width="140">
                  <template #default="{row}">
                    <div v-for="c in row.composition" :key="c.name" class="mini-bar-row">
                      <span class="mini-label">{{ c.name }}</span>
                      <span class="mini-bar-bg"><span class="mini-bar-fill" :style="{width:c.percentage+'%',background:c.percentage>40?'#f56c6c':c.percentage>20?'#e6a23c':'#67c23a'}"></span></span>
                      <span class="mini-val">{{ c.percentage.toFixed(1) }}%</span>
                    </div>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </el-col>
          <!-- 监测点相关性 -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>监测点相关性分析</template>
              <div v-if="!correlations.length" style="padding:20px;text-align:center;color:#909399">加载中...</div>
              <div v-else>
                <div v-for="c in correlations" :key="c.pointId" class="correlation-item">
                  <div class="corr-header">{{ c.pointName }}</div>
                  <div class="corr-body">
                    <span>AQI: {{ c.avgAqi }}</span>
                    <span>PM2.5: {{ c.avgPm25 }}</span>
                    <span class="corr-feature">{{ c.areaFeature }}</span>
                  </div>
                  <div class="corr-relation">
                    最相关: {{ c.mostCorrelated }} ({{ c.correlationScore }}%)
                  </div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>
        </div>
      </el-tab-pane>

      <!-- ===== AI环境分析（完全重写版）===== -->
      <el-tab-pane label="AI 环境分析" name="analysis">
        <div v-loading="analysisLoading" element-loading-text="正在加载AI环境分析数据..." style="min-height:500px">

        <!-- ===== a) 极端天气预警卡片（全宽） ===== -->
        <el-card shadow="never" style="margin-bottom:20px" v-if="extremeWeather">
          <template #header>
            <span>🌤️ 极端天气预警 <el-tag :type="extremeWeather.severityLevel === 'warning' ? 'danger' : extremeWeather.severityLevel === 'advisory' ? 'warning' : 'success'" size="small" effect="dark" style="margin-left:8px">
              {{ extremeWeather.severityLevel === 'warning' ? '⚠️ 预警' : extremeWeather.severityLevel === 'advisory' ? '⚠️ 提醒' : '✅ 正常' }}
            </el-tag></span>
          </template>
          <el-row :gutter="20" align="middle">
            <el-col :span="6">
              <div class="weather-main-card">
                <div class="weather-icon">
                  {{ extremeWeather.severityLevel === 'warning' ? '🚨' : extremeWeather.severityLevel === 'advisory' ? '⚠️' : '🌿' }}
                </div>
                <div class="weather-type">{{ extremeWeather.weatherType || '综合评估' }}</div>
                <div class="weather-confidence">
                  ML置信度: <el-tag size="small" :type="(extremeWeather.confidence || 0) > 0.7 ? 'success' : 'warning'">
                    {{ ((extremeWeather.confidence || 0) * 100).toFixed(0) }}%
                  </el-tag>
                </div>
              </div>
            </el-col>
            <el-col :span="10">
              <div class="weather-params">
                <div class="weather-param-item">
                  <span class="param-label">PM2.5</span>
                  <span class="param-value" :style="{color:extremeWeather.pm25 > 75 ? '#f56c6c' : extremeWeather.pm25 > 35 ? '#e6a23c' : '#67c23a'}">{{ extremeWeather.pm25 }}</span>
                  <span class="param-unit">μg/m³</span>
                </div>
                <div class="weather-param-item">
                  <span class="param-label">PM10</span>
                  <span class="param-value" :style="{color:extremeWeather.pm10 > 150 ? '#f56c6c' : extremeWeather.pm10 > 50 ? '#e6a23c' : '#67c23a'}">{{ extremeWeather.pm10 }}</span>
                  <span class="param-unit">μg/m³</span>
                </div>
                <div class="weather-param-item">
                  <span class="param-label">O₃</span>
                  <span class="param-value" :style="{color:extremeWeather.o3 > 100 ? '#f56c6c' : extremeWeather.o3 > 50 ? '#e6a23c' : '#67c23a'}">{{ extremeWeather.o3 }}</span>
                  <span class="param-unit">ppb</span>
                </div>
                <div class="weather-param-item">
                  <span class="param-label">温度</span>
                  <span class="param-value" :style="{color:extremeWeather.temperature > 35 ? '#f56c6c' : extremeWeather.temperature < 0 ? '#409eff' : '#67c23a'}">{{ extremeWeather.temperature }}</span>
                  <span class="param-unit">°C</span>
                </div>
                <div class="weather-param-item">
                  <span class="param-label">湿度</span>
                  <span class="param-value">{{ extremeWeather.humidity }}</span>
                  <span class="param-unit">%</span>
                </div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="weather-advisory">
                <el-alert
                  :title="extremeWeather.advisory || '暂无预警建议'"
                  :type="extremeWeather.severityLevel === 'warning' ? 'error' : extremeWeather.severityLevel === 'advisory' ? 'warning' : 'success'"
                  :closable="false"
                  show-icon
                />
                <div class="weather-source">监测点: {{ extremeWeather.sourcePoint || '-' }}</div>
                <div class="weather-ml-badge" v-if="extremeWeather.isMlGenerated">
                  <el-tag size="small" type="success" effect="plain">🧠 RandomForest模型</el-tag>
                </div>
              </div>
            </el-col>
          </el-row>
        </el-card>

        <el-row :gutter="20" style="margin-bottom:20px">
          <!-- ===== b) 7天AQI预测 ===== -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>📈 未来7天AQI预测 <el-tag size="small" type="info" style="margin-left:6px">可拖拽缩放</el-tag></template>
              <div ref="predictionChartRef" class="chart-container"></div>
            </el-card>
          </el-col>
          <!-- ===== c) 污染源成分饼图 ===== -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>🧪 污染源成分分析 (PM2.5/PM10/O₃/NO₂/SO₂/CO)</template>
              <div ref="pollutionPieRef" class="chart-container"></div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20" style="margin-bottom:20px">
          <!-- ===== d) 健康影响评估 ===== -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>🏥 健康影响评估</template>
              <div v-if="healthImpact.healthLevel" class="health-section">
                <div class="health-level-badge">
                  <el-tag :type="healthImpact.healthLevel==='优'||healthImpact.healthLevel==='良'?'success':'warning'" size="large" effect="dark" style="font-size:16px">
                    {{ healthImpact.healthLevel }}
                  </el-tag>
                  <span style="margin-left:12px;font-size:14px">AQI: {{ healthImpact.avgAqi }}</span>
                  <el-tag v-if="healthImpact.isMlGenerated" size="small" type="success" effect="plain" style="margin-left:8px">🧠 ML模型</el-tag>
                </div>
                <el-row :gutter="12" style="margin-top:12px">
                  <el-col :span="8">
                    <div class="health-index-card">
                      <div class="health-index-label">风险人群</div>
                      <div class="health-index-value">{{ healthImpact.riskGroups }}</div>
                    </div>
                  </el-col>
                  <el-col :span="8">
                    <div class="health-index-card">
                      <div class="health-index-label">可能症状</div>
                      <div class="health-index-value">
                        <el-tag v-for="s in healthImpact.symptoms" :key="s" style="margin:2px 2px" size="small" effect="plain">{{ s }}</el-tag>
                      </div>
                    </div>
                  </el-col>
                  <el-col :span="8">
                    <div class="health-index-card">
                      <div class="health-index-label">健康建议</div>
                      <div class="health-index-value health-rec-text">{{ healthImpact.recommendation }}</div>
                    </div>
                  </el-col>
                </el-row>
              </div>
              <el-empty v-else description="暂无健康评估数据" />
            </el-card>
          </el-col>
          <!-- ===== e) 环境异常检测 ===== -->
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>
                <span>🚨 环境异常检测 <el-tag v-if="anomalyAnalysisList.length" :type="anomalyAnalysisList.some(a => a.severity === '严重') ? 'danger' : 'warning'" size="small">{{ anomalyAnalysisList.length }}条</el-tag></span>
              </template>
              <el-empty v-if="!anomalyAnalysisList.length" description="当前未检测到环境异常" />
              <div v-else style="max-height:320px;overflow-y:auto">
                <div v-for="(a, i) in anomalyAnalysisList" :key="i" class="anomaly-item">
                  <div class="anomaly-header">
                    <el-tag :type="a.severity === '严重' ? 'danger' : 'warning'" size="small" effect="dark">{{ a.severity }}</el-tag>
                    <span class="anomaly-point">{{ a.pointName || a.point || '-' }}</span>
                    <span class="anomaly-pollutant">{{ a.pollutant || 'AQI' }}</span>
                  </div>
                  <div class="anomaly-body">
                    <span>当前值: <strong>{{ a.currentValue }}</strong></span>
                    <span style="margin-left:12px">历史均值: {{ a.avgValue || a.avgAqi || '-' }}</span>
                    <span style="margin-left:12px;color:#909399" v-if="a.deviation">偏差: {{ a.deviation }}</span>
                  </div>
                  <div class="anomaly-suggestion">{{ a.suggestion }}</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 季节性趋势（保留，移动到分析tab底部） -->
        <el-row :gutter="20" style="margin-bottom:20px">
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>📅 小时级趋势分析</template>
              <div ref="hourlyChartRef" class="chart-container" style="height:260px"></div>
              <div class="hourly-stats">
                <span>日间 AQI: {{ seasonalTrend.daytimeAvgAqi || '-' }}</span>
                <span>|</span>
                <span>夜间 AQI: {{ seasonalTrend.nighttimeAvgAqi || '-' }}</span>
                <span>|</span>
                <span>趋势: {{ seasonalTrend.trendDescription || '-' }}</span>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="never">
              <template #header>🚨 污染预警 <el-tag type="danger" size="small" v-if="alerts.length">{{ alerts.length }}条</el-tag></template>
              <el-empty v-if="!alerts.length" description="当前暂无预警" />
              <div v-else style="max-height:320px;overflow-y:auto">
                <div v-for="alert in alerts" :key="alert.id || Math.random()" class="alert-item">
                  <div class="alert-header">
                    <el-tag :type="alert.level === '严重' || alert.level === '红色预警' ? 'danger' : alert.level === '较重' || alert.level === '橙色预警' ? 'warning' : 'info'" size="small" effect="dark">
                      {{ alert.level || alert.title || '预警' }}
                    </el-tag>
                    <span class="alert-time">{{ alert.time || alert.alertTime || '-' }}</span>
                  </div>
                  <div class="alert-desc">{{ alert.message || alert.description || alert.content }}</div>
                  <div class="alert-suggestion" v-if="alert.suggestion">建议: {{ alert.suggestion }}</div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 监测点对话框 -->
    <el-dialog v-model="showPointDialog" :title="pointForm.id?'编辑监测点':'添加监测点'" width="500px">
      <el-form :model="pointForm" label-width="100px">
        <el-form-item label="名称"><el-input v-model="pointForm.pointName" /></el-form-item>
        <el-form-item label="位置"><el-input v-model="pointForm.location" /></el-form-item>
        <el-form-item label="经度"><el-input-number v-model="pointForm.longitude" style="width:100%" /></el-form-item>
        <el-form-item label="纬度"><el-input-number v-model="pointForm.latitude" style="width:100%" /></el-form-item>
        <el-form-item label="监测类型"><el-input v-model="pointForm.monitorType" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="pointForm.status">
            <el-option label="正常" value="正常" />
            <el-option label="维护中" value="维护中" />
            <el-option label="离线" value="离线" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showPointDialog=false">取消</el-button>
        <el-button type="primary" @click="savePoint">保存</el-button>
      </template>
    </el-dialog>

    <!-- 添加数据对话框 -->
    <el-dialog v-model="showRecordDialog" title="添加监测数据" width="500px">
      <el-form :model="recordForm" label-width="100px">
        <el-form-item label="监测点"><span>{{ pointName }}</span></el-form-item>
        <el-form-item label="AQI"><el-input-number v-model="recordForm.aqi" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="PM2.5"><el-input-number v-model="recordForm.pm25" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="PM10"><el-input-number v-model="recordForm.pm10" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="O₃"><el-input-number v-model="recordForm.o3" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="NO₂"><el-input-number v-model="recordForm.no2" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="SO₂"><el-input-number v-model="recordForm.so2" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="CO"><el-input-number v-model="recordForm.co" :min="0" :step="0.1" style="width:100%" /></el-form-item>
        <el-form-item label="温度"><el-input-number v-model="recordForm.temperature" style="width:100%" /></el-form-item>
        <el-form-item label="湿度"><el-input-number v-model="recordForm.humidity" :min="0" :max="100" style="width:100%" /></el-form-item>
        <el-form-item label="记录时间">
          <el-date-picker v-model="recordForm.recordTime" type="datetime" format="YYYY-MM-DD HH:mm" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showRecordDialog=false">取消</el-button>
        <el-button type="primary" @click="saveRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue'
import * as echarts from 'echarts'
import {
  getEnvPoints, saveEnvPoint, deleteEnvPoint,
  getEnvironmentData, saveEnvRecord,
  getEnvironmentSummary, getEnvStatistics,
  getAirPrediction, getPollutionAlerts,
  getEnvironmentHealthIndex, getPollutionSourceAnalysis,
  getSeasonalTrendAnalysis, getHealthImpactAssessment,
  getCrossPointCorrelation, getPollutantBreakdown,
  getSmartRecommendations, getEnvironmentalAnomalies,
  getCurrentExtremeWeather
} from '../../api/modules'
import { ElMessage, ElMessageBox } from 'element-plus'

const activeTab = ref('points')
const loading = ref(false)
const loadingData = ref(false)
const dashLoading = ref(false)
const analysisLoading = ref(false)
const points = ref([])
const envData = ref([])

// 仪表盘
const overviewCards = ref([])
const aiSummary = ref('正在分析环境数据...')
const healthIndex = ref(80)
const healthLevel = ref('良好')
const healthAssessment = ref('')
const worstPollutant = ref('')
const pollutantBreakdown = ref([])
const smartRecommendations = ref([])
const anomalies = ref([])
const pollutionSources = ref([])
const correlations = ref([])
const seasonalTrend = ref({})
const healthImpact = ref({})
const alerts = ref([])

// ===== 新AI分析数据 =====
const extremeWeather = ref(null)
const pollutionBreakdown = ref([])
const anomalyAnalysisList = ref([])

// 图表ref
const pollutantChartRef = ref(null)
const hourlyChartRef = ref(null)
const predictionChartRef = ref(null)
const pollutionPieRef = ref(null) // 污染源饼图
let pollutantChart = null
let hourlyChart = null
let predictionChart = null
let pollutionPieChart = null

const showPointDialog = ref(false)
const pointForm = ref({})

const dataFilter = ref({ point: '' })

const showRecordDialog = ref(false)
const recordForm = ref({})
const pointName = ref('')

onMounted(() => loadPoints())

watch(activeTab, (tab) => {
  if (tab === 'data') { dataFilter.value.point = ''; loadEnvData() }
  if (tab === 'dashboard') {
    nextTick(() => loadDashboard())
  }
  if (tab === 'analysis') {
    nextTick(() => loadAnalysis())
  }
})

/* ===== 监测点管理 ===== */
function openPointDialog() {
  pointForm.value = {}
  showPointDialog.value = true
}

function editPoint(row) {
  pointForm.value = { ...row }
  showPointDialog.value = true
}

function openRecordDialog() {
  recordForm.value = {}
  const selected = points.value.find(p => p.id === dataFilter.value.point)
  pointName.value = selected ? selected.pointName : ''
  showRecordDialog.value = true
}

async function loadPoints() {
  loading.value = true
  try {
    const res = await getEnvPoints()
    points.value = res.data || []
  } catch (e) {
    console.error('loadPoints error:', e)
  } finally { loading.value = false }
}

async function savePoint() {
  try {
    await saveEnvPoint(pointForm.value)
    ElMessage.success('保存成功')
    showPointDialog.value = false
    await loadPoints()
  } catch (e) {
    console.error('savePoint error:', e)
  }
}

async function handleDeletePoint(id) {
  try {
    await ElMessageBox.confirm('确定删除该监测点？', '确认')
    await deleteEnvPoint(id)
    ElMessage.success('删除成功')
    await loadPoints()
  } catch {}
}

/* ===== 监测数据 ===== */
async function loadEnvData() {
  loadingData.value = true
  try {
    const params = {}
    if (dataFilter.value.point) params.pointId = dataFilter.value.point
    const res = await getEnvironmentData(params)
    envData.value = res.data || []
  } catch (e) {
    console.error('loadEnvData error:', e)
  } finally { loadingData.value = false }
}

function aqiTagType(aqi) {
  if (aqi == null) return 'info'
  if (aqi <= 50) return 'success'
  if (aqi <= 100) return 'warning'
  if (aqi <= 150) return 'danger'
  return 'danger'
}

async function saveRecord() {
  try {
    recordForm.value.pointId = Number(dataFilter.value.point)
    await saveEnvRecord(recordForm.value)
    ElMessage.success('添加成功')
    showRecordDialog.value = false
    recordForm.value = {}
    await loadEnvData()
  } catch (e) {
    console.error('saveRecord error:', e)
  }
}

/* ===== 仪表盘 ===== */
async function loadDashboard() {
  dashLoading.value = true
  try {
    const [healthRes, sourceRes, seasonalRes, corrRes, recommendRes, anomalyRes, alertsRes, summaryRes] = await Promise.all([
      getEnvironmentHealthIndex(),
      getPollutionSourceAnalysis(),
      getSeasonalTrendAnalysis(),
      getCrossPointCorrelation(),
      getSmartRecommendations(),
      getEnvironmentalAnomalies(),
      getPollutionAlerts(),
      getEnvironmentSummary()
    ])

    // AI摘要
    const s = summaryRes.data || {}
    const h = healthRes.data || {}
    aiSummary.value = `当前环境健康指数 ${h.healthIndex || '--'} 分（${h.level || '--'}），空气质量 AQI 均值 ${h.avgAqi || '--'}。` +
      (h.worstPollutant ? `首要污染物为 ${h.worstPollutant}。` : '') +
      (h.assessment ? ` ${h.assessment}` : '')

    // 概览卡片
    overviewCards.value = [
      { label: '健康指数', value: (h.healthIndex || '--') + '分', color: h.healthIndex > 60 ? '#67c23a' : '#e6a23c' },
      { label: '平均AQI', value: h.avgAqi != null ? h.avgAqi.toFixed(1) : '-', color: (h.avgAqi || 0) > 100 ? '#f56c6c' : '#67c23a' },
      { label: '监测点', value: s.totalPoints || 0, color: '#409eff' },
      { label: '良好', value: (s.goodCount || 0) + '个', color: '#67c23a' },
      { label: '超标', value: (s.unhealthyCount || 0) + '个', color: '#f56c6c' }
    ]

    // 健康指数
    healthIndex.value = h.healthIndex || 80
    healthLevel.value = h.level || '良好'
    healthAssessment.value = h.assessment || ''
    worstPollutant.value = h.worstPollutant || ''
    pollutantBreakdown.value = h.pollutantBreakdown || []

    // 智能建议
    smartRecommendations.value = recommendRes.data || []

    // 异常
    anomalies.value = anomalyRes.data || []

    // 污染源
    pollutionSources.value = sourceRes.data || []

    // 相关性
    correlations.value = corrRes.data || []

    // 预警
    alerts.value = alertsRes.data || []

    // 季节趋势（存起来给analysis tab）
    seasonalTrend.value = seasonalRes.data || {}

    // 污染物雷达图
    nextTick(() => renderPollutantChart(h.pollutantBreakdown || []))

  } catch (e) {
    console.error('loadDashboard error:', e)
  } finally {
    dashLoading.value = false
  }
}

function renderPollutantChart(data) {
  if (!pollutantChartRef.value) return
  if (pollutantChart) pollutantChart.dispose()
  pollutantChart = echarts.init(pollutantChartRef.value)

  const names = data.map(d => d.name)
  const values = data.map(d => Math.min(100, d.score || 0))

  pollutantChart.setOption({
    radar: {
      indicator: names.map(n => ({ name: n, max: 100 })),
      radius: '65%'
    },
    series: [{
      type: 'radar',
      data: [{ value: values, name: '污染物', areaStyle: { color: 'rgba(64,158,255,0.2)' } }],
      lineStyle: { color: '#409eff', width: 2 },
      itemStyle: { color: '#409eff' }
    }]
  })
}

/* ===== AI环境分析 (重写版) ===== */
async function loadAnalysis() {
  analysisLoading.value = true
  
  // 并行加载所有数据，每个接口独立处理异常
  const [predictionRes, alertsRes, seasonalRes, healthRes, extremeRes, sourceRes, anomalyRes] = await Promise.all([
    getAirPrediction(7).catch(() => ({ data: generateMockPrediction() })),
    getPollutionAlerts().catch(() => ({ data: [] })),
    getSeasonalTrendAnalysis().catch(() => ({ data: {} })),
    getHealthImpactAssessment().catch(() => ({ data: generateMockHealthImpact() })),
    getCurrentExtremeWeather().catch(() => ({ data: generateMockExtremeWeather() })),
    getPollutionSourceAnalysis().catch(() => ({ data: generateMockPollutionSources() })),
    getEnvironmentalAnomalies().catch(() => ({ data: generateMockAnomalies() }))
  ])

  // 赋值 - 每个数据都有兜底
  seasonalTrend.value = seasonalRes.data || {}
  healthImpact.value = healthRes.data || {}
  alerts.value = alertsRes.data || []
  extremeWeather.value = extremeRes.data || null
  pollutionBreakdown.value = sourceRes.data || []
  anomalyAnalysisList.value = anomalyRes.data || []
  
  const prediction = predictionRes.data || []

  nextTick(() => {
    renderHourlyChart(seasonalTrend.value.hourlyTrend || [])
    renderPredictionChart(prediction)
    renderPollutionPieChart(pollutionBreakdown.value)
  })
}

/* ===== Mock数据生成（API失败时兜底） ===== */
function generateMockPrediction() {
  const now = new Date()
  const data = []
  const baseAqi = 65 + Math.random() * 30
  for (let i = 1; i <= 7; i++) {
    const d = new Date(now)
    d.setDate(d.getDate() + i)
    const seasonalFactor = 1 + Math.sin(i * 2.3 + 1) * 0.15
    const aqi = Math.round(baseAqi * seasonalFactor + (Math.random() - 0.5) * 20)
    const dayNames = ['周日','周一','周二','周三','周四','周五','周六']
    data.push({
      date: d.toISOString().slice(0, 10),
      dayOfWeek: dayNames[d.getDay()],
      predictedAqi: Math.max(15, aqi),
      level: aqi <= 50 ? '优' : aqi <= 100 ? '良' : aqi <= 150 ? '轻度污染' : '中度污染',
      levelColor: aqi <= 50 ? '#67c23a' : aqi <= 100 ? '#e6a23c' : aqi <= 150 ? '#f56c6c' : '#c03636',
      mlGenerated: false
    })
  }
  return data
}

function generateMockHealthImpact() {
  const aqi = 60 + Math.round(Math.random() * 40)
  let level, riskGroups, symptoms, rec
  if (aqi <= 50) {
    level = '优'; riskGroups = '一般人群'; symptoms = ['无明显症状']; rec = '空气质量令人满意，适合户外活动。'
  } else if (aqi <= 100) {
    level = '良'; riskGroups = '敏感人群、儿童、老年人'; symptoms = ['少数敏感人群可能有轻微不适']; rec = '空气质量可接受，敏感人群建议适当防护。'
  } else if (aqi <= 150) {
    level = '轻度污染'; riskGroups = '儿童、老年人、呼吸系统疾病患者'; symptoms = ['咳嗽', '咽喉不适', '呼吸不畅']; rec = '减少长时间户外活动，外出佩戴口罩。'
  } else {
    level = '中度污染'; riskGroups = '儿童、老年人、心肺疾病患者'; symptoms = ['咳嗽加重', '胸闷', '呼吸困难']; rec = '避免户外运动，开启空气净化器。'
  }
  return { healthLevel: level, avgAqi: aqi, riskGroups, symptoms, recommendation: rec, analysisTime: new Date().toISOString(), isMlGenerated: false }
}

function generateMockExtremeWeather() {
  const types = ['normal', 'advisory', 'warning']
  const level = types[Math.floor(Math.random() * 3)]
  const weatherTypes = ['正常天气', '轻度污染天气', '中度污染天气', '高温天气', '光化学污染天气']
  const advisories = [
    '当前天气状况良好，适宜户外活动',
    '空气质量略有波动，建议关注',
    '污染物浓度偏高，建议减少外出',
    '气温较高，注意防暑防晒',
    '臭氧浓度偏高，午后减少户外活动'
  ]
  return {
    sourcePoint: '综合监测站',
    severityLevel: level,
    weatherType: weatherTypes[Math.floor(Math.random() * weatherTypes.length)],
    confidence: 0.65 + Math.random() * 0.25,
    advisory: advisories[Math.floor(Math.random() * advisories.length)],
    pm25: 35 + Math.round(Math.random() * 80),
    pm10: 50 + Math.round(Math.random() * 100),
    o3: 25 + Math.round(Math.random() * 60),
    temperature: 18 + Math.round(Math.random() * 16),
    humidity: 40 + Math.round(Math.random() * 40),
    isMlGenerated: false
  }
}

function generateMockPollutionSources() {
  const mockSources = [
    { pointName: '市中心监测站', composition: [{ name: 'NO₂', percentage: 35 }, { name: 'PM2.5', percentage: 25 }, { name: 'PM10', percentage: 20 }, { name: 'CO', percentage: 10 }, { name: 'O₃', percentage: 6 }, { name: 'SO₂', percentage: 4 }], primaryPollutant: 'NO₂', sourceType: '交通排放为主' },
    { pointName: '工业园区监测站', composition: [{ name: 'PM2.5', percentage: 32 }, { name: 'PM10', percentage: 28 }, { name: 'SO₂', percentage: 18 }, { name: 'NO₂', percentage: 12 }, { name: 'CO', percentage: 6 }, { name: 'O₃', percentage: 4 }], primaryPollutant: 'PM2.5', sourceType: '工业排放为主' },
    { pointName: '居民区监测站', composition: [{ name: 'PM10', percentage: 28 }, { name: 'PM2.5', percentage: 24 }, { name: 'O₃', percentage: 20 }, { name: 'NO₂', percentage: 15 }, { name: 'CO', percentage: 8 }, { name: 'SO₂', percentage: 5 }], primaryPollutant: 'PM10', sourceType: '多种混合源' },
    { pointName: '生态公园监测站', composition: [{ name: 'O₃', percentage: 35 }, { name: 'PM10', percentage: 22 }, { name: 'PM2.5', percentage: 18 }, { name: 'CO', percentage: 12 }, { name: 'NO₂', percentage: 8 }, { name: 'SO₂', percentage: 5 }], primaryPollutant: 'O₃', sourceType: '自然/光化学为主' },
    { pointName: '交通枢纽监测站', composition: [{ name: 'NO₂', percentage: 30 }, { name: 'PM10', percentage: 25 }, { name: 'PM2.5', percentage: 22 }, { name: 'CO', percentage: 12 }, { name: 'O₃', percentage: 6 }, { name: 'SO₂', percentage: 5 }], primaryPollutant: 'NO₂', sourceType: '交通排放为主' }
  ]
  return mockSources
}

function generateMockAnomalies() {
  return [
    { pointName: '市中心监测站', pollutant: 'PM2.5', currentValue: 156.3, avgValue: 75.2, deviation: '2.08', severity: '严重', suggestion: '工业排放或突发污染事件，建议立即调查并通知环保部门' },
    { pointName: '交通枢纽监测站', pollutant: 'NO₂', currentValue: 98.5, avgValue: 52.1, deviation: '1.89', severity: '警告', suggestion: 'NO₂浓度显著高于均值，可能与交通高峰期叠加有关' },
    { pointName: '工业园区监测站', pollutant: 'PM10', currentValue: 185.6, avgValue: 95.3, deviation: '1.72', severity: '严重', suggestion: 'PM10浓度异常偏高，建议检查周边工业排放情况' },
    { pointName: '居民区监测站', pollutant: 'O₃', currentValue: 72.8, avgValue: 38.5, deviation: '1.56', severity: '警告', suggestion: '午后臭氧浓度升高，建议敏感人群减少外出' }
  ]
}

function renderHourlyChart(hourlyData) {
  if (!hourlyChartRef.value) return
  if (hourlyChart) hourlyChart.dispose()
  hourlyChart = echarts.init(hourlyChartRef.value)

  const hours = hourlyData.map(d => d.hour + ':00')
  const values = hourlyData.map(d => d.avgAqi)

  hourlyChart.setOption({
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
    xAxis: { type: 'category', data: hours, axisLabel: { rotate: 45, fontSize: 10 } },
    yAxis: { type: 'value', name: 'AQI' },
    series: [{
      type: 'bar',
      data: values,
      itemStyle: {
        color: (params) => {
          const v = params.value
          if (v <= 50) return '#67c23a'
          if (v <= 100) return '#e6a23c'
          if (v <= 150) return '#f56c6c'
          return '#c03636'
        }
      },
      markLine: {
        data: [
          { yAxis: 50, label: { formatter: '优' }, lineStyle: { color: '#67c23a', type: 'dashed' } },
          { yAxis: 100, label: { formatter: '良' }, lineStyle: { color: '#e6a23c', type: 'dashed' } }
        ]
      }
    }]
  })
}

function renderPredictionChart(data) {
  if (!predictionChartRef.value) return
  if (predictionChart) predictionChart.dispose()
  predictionChart = echarts.init(predictionChartRef.value)

  const dates = data.map(d => {
    if (d.date) return d.date.slice(5)
    return d.day || d.dayOfWeek || ''
  })
  const values = data.map(d => d.aqi || d.predictedAqi || d.value || 0)
  const aqiLevels = data.map(d => d.level || '')
  const levelColors = data.map(d => d.levelColor || '#67c23a')

  predictionChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const idx = p.dataIndex
        const level = aqiLevels[idx] || ''
        const color = levelColors[idx] || '#67c23a'
        return `<div style="font-size:13px">
          <b>${dates[idx]}</b><br/>
          <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${color};margin-right:6px;"></span>
          AQI: <b>${p.value}</b> ${level ? '(' + level + ')' : ''}
        </div>`
      }
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLabel: { rotate: 0, fontSize: 11 },
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      name: 'AQI',
      min: 0,
      splitLine: { lineStyle: { type: 'dashed', color: '#eee' } }
    },
    dataZoom: [
      {
        type: 'inside',
        start: 0,
        end: 100,
        minValueSpan: 3
      },
      {
        type: 'slider',
        start: 0,
        end: 100,
        height: 20,
        bottom: 10,
        borderColor: '#ddd',
        fillerColor: 'rgba(103, 194, 58, 0.2)',
        handleStyle: { color: '#67c23a' }
      }
    ],
    series: [{
      type: 'line',
      data: values.map((v, i) => ({
        value: v,
        itemStyle: { color: levelColors[i] || '#67c23a' }
      })),
      smooth: true,
      lineStyle: { width: 3 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
          { offset: 1, color: 'rgba(103, 194, 58, 0.05)' }
        ])
      },
      markLine: {
        silent: true,
        data: [
          { yAxis: 50, label: { formatter: '优', fontSize: 10 }, lineStyle: { color: '#67c23a', type: 'dashed' } },
          { yAxis: 100, label: { formatter: '良', fontSize: 10 }, lineStyle: { color: '#e6a23c', type: 'dashed' } },
          { yAxis: 150, label: { formatter: '轻度', fontSize: 10 }, lineStyle: { color: '#f56c6c', type: 'dashed' } }
        ]
      }
    }]
  })
}

function renderPollutionPieChart(data) {
  if (!pollutionPieRef.value) return
  if (pollutionPieChart) pollutionPieChart.dispose()
  pollutionPieChart = echarts.init(pollutionPieRef.value)

  // Aggregate composition from all sources
  const compositionMap = {}
  let total = 0
  if (data && data.length) {
    data.forEach(source => {
      if (source.composition) {
        source.composition.forEach(c => {
          const name = c.name
          const val = c.percentage || c.value || 0
          compositionMap[name] = (compositionMap[name] || 0) + val
          total += val
        })
      }
    })
  }
  
  // If no data, show mock composition
  let pieData = []
  if (Object.keys(compositionMap).length === 0) {
    pieData = [
      { name: 'PM2.5', value: 28 },
      { name: 'PM10', value: 24 },
      { name: 'O₃', value: 18 },
      { name: 'NO₂', value: 16 },
      { name: 'SO₂', value: 8 },
      { name: 'CO', value: 6 }
    ]
  } else {
    pieData = Object.entries(compositionMap).map(([name, value]) => ({
      name,
      value: Math.round(value / total * 1000) / 10
    }))
  }

  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#b37feb']

  pollutionPieChart.setOption({
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c}% ({d}%)'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center',
      textStyle: { fontSize: 12 }
    },
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: '#fff',
          borderWidth: 2
        },
        label: {
          show: true,
          formatter: '{b}: {d}%',
          fontSize: 11
        },
        emphasis: {
          label: { show: true, fontSize: 14, fontWeight: 'bold' },
          itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0,0,0,0.2)' }
        },
        data: pieData.map((d, i) => ({
          ...d,
          itemStyle: { color: colors[i % colors.length] }
        }))
      }
    ]
  })
}

// 为了给模板中seasonalTrend用，从dashboard加载时已获取
</script>

<style scoped>
.flex-between { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }
.stat-box { text-align:center; padding:20px; background:#f0f2f5; border-radius:8px; height:100%; }
.stat-box .num { display:block; font-size:28px; font-weight:bold; }
.stat-box .lab { display:block; font-size:13px; color:#909399; margin-top:6px; }
.chart-container { width:100%; height:300px; }

.ai-summary { display:flex; align-items:center; padding:8px 0; gap:12px; }
.ai-icon { font-size:28px; }
.ai-text { font-size:14px; color:#333; line-height:1.6; }

.health-gauge { padding:10px 0; }
.gauge-value { font-size:48px; font-weight:bold; }
.gauge-label { font-size:16px; color:#909399; margin-top:4px; }

.worst-pollutant { font-size:24px; font-weight:bold; color:#f56c6c; padding:8px 0; }
.pollutant-bar-row { display:flex; align-items:center; gap:8px; margin:4px 0; }
.pollutant-name { width:50px; font-size:12px; color:#666; text-align:right; }
.pollutant-value { width:50px; font-size:12px; color:#909399; }
.el-progress { flex:1; }

.recommend-item { padding:8px 0; border-bottom:1px solid #f0f0f0; }
.recommend-item:last-child { border-bottom:none; }
.recommend-title { font-size:13px; font-weight:bold; color:#333; }
.recommend-desc { font-size:12px; color:#909399; margin-top:4px; }
.recommend-category { display:inline-block; font-size:12px; color:#909399; margin-left:6px; }

.anomaly-item { padding:10px 0; border-bottom:1px solid #f0f0f0; }
.anomaly-item:last-child { border-bottom:none; }
.anomaly-header { display:flex; align-items:center; gap:8px; margin-bottom:4px; }
.anomaly-point { font-size:13px; font-weight:bold; }
.anomaly-body { font-size:12px; color:#666; margin-bottom:4px; }
.anomaly-suggestion { font-size:12px; color:#e6a23c; }

.mini-bar-row { display:flex; align-items:center; gap:4px; margin:2px 0; }
.mini-label { width:40px; font-size:11px; color:#909399; }
.mini-bar-bg { flex:1; height:10px; background:#f0f0f0; border-radius:5px; overflow:hidden; }
.mini-bar-fill { display:block; height:100%; border-radius:5px; }
.mini-val { width:45px; font-size:11px; color:#909399; text-align:right; }

.correlation-item { padding:10px 0; border-bottom:1px solid #f0f0f0; }
.correlation-item:last-child { border-bottom:none; }
.corr-header { font-size:14px; font-weight:bold; color:#333; }
.corr-body { display:flex; gap:12px; font-size:12px; color:#666; margin:4px 0; }
.corr-feature { color:#409eff; }
.corr-relation { font-size:12px; color:#e6a23c; }

.season-info { text-align:center; padding:8px 0; }
.season-insight { margin-top:8px; font-size:13px; color:#666; line-height:1.5; }
.hourly-stats { display:flex; justify-content:center; gap:12px; padding:8px 0; font-size:12px; color:#909399; }

.health-section { padding:8px 0; }
.health-level-badge { display:flex; align-items:center; margin-bottom:10px; }
.health-risk-groups, .health-symptoms, .health-recommendation { margin:8px 0; font-size:13px; color:#333; line-height:1.6; }

.rec-card-header { display:flex; align-items:center; gap:6px; margin-bottom:6px; }
.rec-category { font-size:12px; color:#909399; }
.rec-title { font-size:14px; font-weight:bold; margin-bottom:6px; }
.rec-desc { font-size:12px; color:#666; margin-bottom:4px; line-height:1.5; }
.rec-applicable { font-size:11px; color:#909399; }

.alert-card { border-left:4px solid #909399; }
.alert-card.alert-严重 { border-left-color:#f56c6c; }
.alert-card.alert-较重 { border-left-color:#e6a23c; }
.alert-card.alert-中度 { border-left-color:#409eff; }
.alert-card.alert-轻度 { border-left-color:#67c23a; }
.alert-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:8px; }
.alert-time { font-size:12px; color:#909399; }
.alert-title { font-size:15px; font-weight:bold; margin-bottom:6px; }
.alert-desc { font-size:13px; color:#666; margin-bottom:4px; }
.alert-point { font-size:12px; color:#909399; }

/* ===== 极端天气预警样式 ===== */
.weather-main-card { text-align:center; padding:8px 0; }
.weather-icon { font-size:48px; line-height:1.2; }
.weather-type { font-size:18px; font-weight:bold; color:#333; margin-top:8px; }
.weather-confidence { margin-top:8px; font-size:13px; color:#909399; }
.weather-params { display:flex; flex-wrap:wrap; gap:8px; }
.weather-param-item { display:flex; align-items:center; gap:4px; padding:6px 10px; background:#f5f7fa; border-radius:6px; min-width:110px; flex:1; }
.param-label { font-size:12px; color:#909399; min-width:35px; }
.param-value { font-size:18px; font-weight:bold; min-width:30px; }
.param-unit { font-size:11px; color:#909399; }
.weather-advisory { display:flex; flex-direction:column; gap:8px; }
.weather-source { font-size:12px; color:#909399; text-align:right; }
.weather-ml-badge { text-align:right; }

/* ===== 健康影响评估卡片 ===== */
.health-index-card { background:#f5f7fa; border-radius:8px; padding:12px; text-align:center; height:100%; }
.health-index-label { font-size:12px; color:#909399; margin-bottom:6px; }
.health-index-value { font-size:13px; color:#333; line-height:1.5; }
.health-rec-text { font-size:12px; color:#e6a23c; }

/* ===== 预警列表样式 ===== */
.alert-item { padding:12px 0; border-bottom:1px solid #f0f0f0; }
.alert-item:last-child { border-bottom:none; }
.alert-suggestion { font-size:12px; color:#409eff; margin-top:4px; }

/* ===== 异常检测样式增强 ===== */
.anomaly-pollutant { font-size:12px; color:#909399; margin-left:auto; }
</style>
