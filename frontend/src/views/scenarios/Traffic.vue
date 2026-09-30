<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <!-- ==================== 路段管理 ==================== -->
      <el-tab-pane label="路段管理" name="sections">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>路段列表</span>
              <el-button type="success" @click="openSectionDialog">＋ 添加路段</el-button>
            </div>
          </template>
          <el-table :data="sections" stripe v-loading="loading" border>
            <el-table-column label="序号" type="index" width="60" />
            <el-table-column prop="roadName" label="道路名称" min-width="140" />
            <el-table-column prop="sectionName" label="区间" min-width="180" />
            <el-table-column prop="roadType" label="类型" width="100" />
            <el-table-column label="长度(km)" width="100">
              <template #default="{row}">{{ row.length != null ? row.length.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column prop="lanes" label="车道数" width="80" />
            <el-table-column prop="speedLimit" label="限速(km/h)" width="100" />
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{row}">
                <el-tag :type="row.status==='畅通'?'success':row.status==='缓行'?'warning':'danger'" size="small">{{ row.status || '正常' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{row}">
                <el-button size="small" type="danger" @click="handleDeleteSection(row.id)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 流量数据 ==================== -->
      <el-tab-pane label="流量数据" name="flow">
        <el-card>
          <template #header>
            <div class="flex-between">
              <span>交通流量数据</span>
              <div>
                <el-select v-model="flowFilter.sectionId" placeholder="选择路段" clearable style="width:160px;margin-right:8px">
                  <el-option v-for="s in sections" :key="s.id" :label="s.roadName" :value="s.id" />
                </el-select>
                <el-date-picker v-model="flowFilter.date" type="date" placeholder="日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:150px;margin-right:8px" />
                <el-button type="primary" @click="loadFlowData">查询</el-button>
                <el-button type="success" @click="openFlowDialog">＋ 添加记录</el-button>
              </div>
            </div>
          </template>
          <el-table :data="flowRecords" stripe v-loading="loadingFlow" border>
            <el-table-column prop="sectionId" label="路段ID" width="80" />
            <el-table-column label="流量" width="100">
              <template #default="{row}">{{ row.flowCount != null ? row.flowCount.toLocaleString() : '-' }}</template>
            </el-table-column>
            <el-table-column label="平均速度(km/h)" width="130">
              <template #default="{row}">{{ row.avgSpeed != null ? row.avgSpeed.toFixed(1) : '-' }}</template>
            </el-table-column>
            <el-table-column label="拥堵等级" width="100">
              <template #default="{row}">
                <el-tag :type="row.congestionLevel==='畅通'?'success':row.congestionLevel==='轻度拥堵'?'warning':'danger'" size="small" effect="dark">{{ row.congestionLevel || '—' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="记录时间" min-width="160">
              <template #default="{row}">{{ row.recordDate || '-' }} {{ row.recordHour != null ? row.recordHour + ':00' : '' }}</template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ==================== 🚗 AI交通分析 (逐模块加载) ==================== -->
      <el-tab-pane label="🚗 AI交通分析" name="analysis">
        <div>
          <!-- === 概览卡片 (逐卡片加载态) === -->
          <div v-loading="loadingOverview" element-loading-text="加载概览...">
            <el-row :gutter="16" style="margin-bottom:16px">
              <el-col :span="4" v-for="c in overviewCards" :key="c.label">
                <div class="stat-box" :style="{borderTop:`3px solid ${c.color}`}">
                  <span class="num" :style="{color:c.color}">{{ c.value }}</span>
                  <span class="lab">{{ c.label }}</span>
                </div>
              </el-col>
            </el-row>
          </div>

          <!-- === 异常检测滚动告警 (独立加载态) === -->
          <div v-loading="loadingAnomaly" element-loading-text="检测异常...">
            <el-card v-if="anomalyAlerts.length" shadow="never" style="margin-bottom:16px;border-left:4px solid #f56c6c">
              <div class="alert-scroll">
                <el-icon color="#f56c6c" :size="20"><WarningFilled /></el-icon>
                <span style="font-weight:bold;margin:0 8px;color:#f56c6c;white-space:nowrap">AI 异常检测：</span>
                <span class="alert-text">{{ anomalyAlerts[0]?.sectionName || '暂无异常' }} — {{ anomalyAlerts[0]?.possibleCause || '数据正常' }}</span>
                <el-tag v-if="anomalyAlerts[0]?.modelName" size="mini" :type="anomalyAlerts[0]?.isMlGenerated ? 'success' : 'info'" style="margin-left:8px;flex-shrink:0">
                  {{ anomalyAlerts[0]?.modelName || '规则' }}
                </el-tag>
              </div>
            </el-card>
          </div>

          <!-- === 主区域：两列布局 === -->
          <el-row :gutter="16">
            <!-- 左列 -->
            <el-col :span="12">

              <!-- 实时路况热力图 (独立加载态) -->
              <el-card shadow="never" style="margin-bottom:16px">
                <template #header>
                  <div class="flex-between">
                    <span><el-icon><DataAnalysis /></el-icon> 实时路况热力图</span>
                    <div>
                      <el-tag v-if="loadingHeatmap" size="small" type="warning">加载中...</el-tag>
                      <el-tag v-else size="small" type="info">数据每30秒刷新</el-tag>
                      <el-tag v-if="!loadingHeatmap && heatmapData.some(s => s.modelName)" size="small" type="success" style="margin-left:4px">
                        {{ heatmapData.find(s => s.modelName)?.modelName?.includes('xgb') ? 'ML' : '规则' }}
                      </el-tag>
                    </div>
                  </div>
                </template>
                <div v-loading="loadingHeatmap" element-loading-text="加载路况热力图...">
                  <div class="heatmap-grid" v-if="heatmapData.length">
                    <div v-for="s in heatmapData" :key="s.sectionId"
                      class="heatmap-cell"
                      :style="{background:getHeatColor(s.congestionIndex)}">
                      <div class="hm-name">{{ s.roadName }} <el-tag v-if="s.isMlGenerated" size="mini" type="success" style="font-size:9px;margin-left:2px">AI</el-tag></div>
                      <div class="hm-speed">{{ s.avgSpeed }} km/h</div>
                      <div class="hm-flow">🚗 {{ (s.flow || 0).toLocaleString() }}</div>
                      <el-tag size="small" :type="s.congestionLevel==='畅通'?'success':s.congestionLevel==='轻度拥堵'?'warning':s.congestionLevel==='中度拥堵'?'':'danger'" effect="dark" style="margin-top:4px">{{ s.congestionLevel }}</el-tag>
                    </div>
                  </div>
                  <el-empty v-else-if="!loadingHeatmap" description="暂无法获取路况热力图" />
                </div>
              </el-card>

              <!-- AI出行决策助手 (独立加载态) -->
              <el-card shadow="never">
                <template #header>
                  <span><el-icon><Clock /></el-icon> AI智能出行助手</span>
                  <el-tag v-if="departureTips.length && departureTips[0]?.modelName" size="mini" :type="departureTips[0]?.isMlGenerated ? 'success' : 'info'" style="float:right;margin-left:4px">
                    {{ departureTips[0]?.isMlGenerated ? 'ML' : '规则' }}
                  </el-tag>
                  <el-tag v-if="loadingDeparture" size="small" type="warning" style="float:right">分析中...</el-tag>
                </template>
                <div v-loading="loadingDeparture" element-loading-text="分析最佳出行时间...">
                  <el-empty v-if="!departureTips.length" description="暂无可用的出行建议" />
                  <div v-for="tip in departureTips" :key="tip.sectionId" class="departure-card">
                    <div class="dep-header">
                      <el-tag size="small" type="success" effect="dark">{{ tip.bestDepartureHour }}</el-tag>
                      <span class="dep-section">{{ tip.sectionName }}</span>
                      <el-tag size="small" type="warning" effect="plain">避开 {{ tip.worstDepartureHour }}</el-tag>
                    </div>
                    <div class="dep-body">
                      <el-progress :percentage="100 - Math.round((tip.worstSpeed - tip.bestSpeed) / (tip.worstSpeed || 1) * 100)" :stroke-width="8" color="#67c23a">
                        <span style="font-size:12px">速度优势 +{{ Math.round(((tip.worstSpeed || 1) - (tip.bestSpeed || 0)) / (tip.bestSpeed || 1) * 100) }}%</span>
                      </el-progress>
                      <div class="dep-tip">💡 {{ tip.tip }}</div>
                    </div>
                  </div>
                </div>
              </el-card>
            </el-col>

            <!-- 右列 -->
            <el-col :span="12">

              <!-- 24h 流量趋势图 (独立加载态) -->
              <el-card shadow="never" style="margin-bottom:16px">
                <template #header>
                  <div class="flex-between">
                    <span><el-icon><TrendCharts /></el-icon> 24小时交通流量趋势</span>
                    <div>
                      <el-tag v-if="loadingChart" size="small" type="warning">加载中...</el-tag>
                      <el-tag v-else size="small" type="info">蓝色=流量 · 橙色=速度</el-tag>
                    </div>
                  </div>
                </template>
                <div v-loading="loadingChart" element-loading-text="加载流量趋势图...">
                  <div ref="flowChartRef" class="chart-container"></div>
                </div>
              </el-card>

              <!-- 多日拥堵预测 (独立加载态) -->
              <el-card shadow="never">
                <template #header>
                  <div class="flex-between">
                    <span><el-icon><Calendar /></el-icon> 未来7天拥堵预测</span>
                    <el-tag v-if="loadingCalendar" size="small" type="warning">预测中...</el-tag>
                    <el-tag v-else size="small" type="primary">AI 自适应预测</el-tag>
                  </div>
                </template>
                <div v-loading="loadingCalendar" element-loading-text="预测未来拥堵...">
                  <el-empty v-if="!calendarDays.length" description="暂无预测数据" />
                  <div v-else class="calendar-scroll">
                    <div v-for="day in calendarDays" :key="day.date" class="calendar-day-card" :style="{borderLeft: `4px solid ${day.morningCongestion==='严重拥堵'?'#f56c6c':day.morningCongestion==='中度拥堵'?'#e6a23c':day.morningCongestion==='轻度拥堵'?'#409eff':'#67c23a'}`}">
                      <div class="cal-header">
                        <span class="cal-date">{{ formatDateShort(day.date) }}</span>
                        <span class="cal-weekday">{{ day.dayOfWeek }}</span>
                      </div>
                      <div class="cal-body">
                        <div class="cal-peak">
                          <span>🌅 早 <b>{{ day.morningCongestion }}</b></span>
                          <span>{{ (day.morningPeakFlow || 0).toLocaleString() }}辆</span>
                        </div>
                        <div class="cal-peak">
                          <span>🌆 晚 <b>{{ day.eveningCongestion }}</b></span>
                          <span>{{ (day.eveningPeakFlow || 0).toLocaleString() }}辆</span>
                        </div>
                        <div class="cal-status">
                          <el-tag size="small" :type="day.dailyStatus==='高负荷'?'danger':day.dailyStatus==='中负荷'?'warning':'success'" effect="plain">{{ day.dailyStatus }}</el-tag>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </el-card>
            </el-col>
          </el-row>

          <!-- === 交通仿真沙盘（全宽） === -->
          <el-card shadow="never" style="margin:16px 0">
            <template #header>
              <span><el-icon><SetUp /></el-icon> 🧪 交通仿真沙盘 — AI 场景推演</span>
            </template>
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="sim-controls">
                  <el-form label-position="top">
                    <el-form-item label="选择路段">
                      <el-select v-model="simSectionId" placeholder="路段" style="width:100%">
                        <el-option v-for="s in sections" :key="s.id" :label="s.roadName + '-' + s.sectionName" :value="s.id" />
                      </el-select>
                    </el-form-item>
                    <el-form-item label="仿真场景">
                      <el-radio-group v-model="simType" style="width:100%">
                        <el-radio value="add_lane" border style="margin-bottom:8px;width:100%">＋ 增加车道</el-radio>
                        <el-radio value="change_speed" border style="margin-bottom:8px;width:100%">调整限速</el-radio>
                        <el-radio value="optimize_signals" border style="width:100%">绿波优化</el-radio>
                      </el-radio-group>
                    </el-form-item>
                    <el-form-item label="调整幅度">
                      <el-slider v-model="simValue" :min="1" :max="3" :step="1" show-stops :marks="{1:'+1',2:'+2',3:'+3'}" style="width:100%" />
                    </el-form-item>
                    <el-button type="primary" @click="runSimulation" :loading="simLoading" style="width:100%">▶ 运行仿真</el-button>
                  </el-form>
                </div>
              </el-col>
              <el-col :span="18">
                <div v-if="!simResult" class="sim-placeholder">
                  <el-icon :size="48" color="#dcdfe6"><SetUp /></el-icon>
                  <p>选择路段和场景，点击「运行仿真」查看 AI 推演结果</p>
                </div>
                <div v-else class="sim-result">
                  <el-alert :title="simResult.sectionName" type="success" show-icon :description="simResult.impactDescription" style="margin-bottom:12px" />
                  <el-row :gutter="16">
                    <el-col :span="6">
                      <div class="sim-metric">
                        <span class="sim-label">当前平均速度</span>
                        <span class="sim-val">{{ simResult.originalAvgSpeed }} km/h</span>
                      </div>
                    </el-col>
                    <el-col :span="6">
                      <div class="sim-metric">
                        <span class="sim-label">AI仿真预测速度</span>
                        <span class="sim-val" style="color:#67c23a">{{ simResult.predictedAvgSpeed }} km/h</span>
                      </div>
                    </el-col>
                    <el-col :span="6">
                      <div class="sim-metric">
                        <span class="sim-label">速度变化</span>
                        <span class="sim-val" :style="{color:simResult.speedChange > 0 ? '#67c23a' : '#f56c6c'}">{{ simResult.speedChange > 0 ? '↑' : '↓' }} {{ Math.abs(simResult.speedChange) }}%</span>
                      </div>
                    </el-col>
                    <el-col :span="6">
                      <div class="sim-metric">
                        <span class="sim-label">通行能力变化</span>
                        <span class="sim-val" :style="{color:simResult.capacityChange > 0 ? '#67c23a' : '#f56c6c'}">{{ simResult.capacityChange > 0 ? '↑' : '↓' }} {{ Math.abs(simResult.capacityChange) }}%</span>
                      </div>
                    </el-col>
                  </el-row>
                  <el-card shadow="never" style="margin-top:12px;background:#f0f9eb">
                    <el-icon color="#67c23a" :size="18"><InfoFilled /></el-icon>
                    <b>AI 建议：</b>{{ simResult.recommendation }}
                  </el-card>
                </div>
              </el-col>
            </el-row>
          </el-card>

          <!-- === 事故影响分析 + 天气关联（并列两列） === -->
          <el-row :gutter="16">
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span><el-icon><WarningFilled /></el-icon> 交通事故影响分析</span>
                </template>
                <div class="accident-controls">
                  <el-select v-model="accidentSectionId" placeholder="选择发生事故的路段" style="width:70%">
                    <el-option v-for="s in sections" :key="s.id" :label="s.roadName" :value="s.id" />
                  </el-select>
                  <el-button type="danger" @click="loadAccidentImpact" :loading="accidentLoading">分析影响</el-button>
                </div>
                <el-empty v-if="!accidentResult" description="选择路段分析事故影响" />
                <div v-else v-loading="accidentLoading" element-loading-text="分析事故影响...">
                  <el-alert :title="'🚑 ' + accidentResult.accidentLevel + ' — ' + accidentResult.accidentSection" type="error" show-icon style="margin-bottom:12px" />
                  <div class="accident-stats">
                    <div>通行能力下降 <b style="color:#f56c6c">{{ accidentResult.capacityLossPercent }}%</b></div>
                    <div>影响周边 <b>{{ accidentResult.affectedSectionCount }}</b> 个路段</div>
                    <div>预计清除时间 <b>{{ accidentResult.estimatedClearTime }}</b></div>
                  </div>
                  <el-table :data="accidentResult.affectedSections || []" size="small" max-height="200" stripe style="margin-top:8px">
                    <el-table-column prop="sectionName" label="受影响路段" min-width="160" />
                    <el-table-column prop="impactLevel" label="影响程度" width="100">
                      <template #default="{row}">
                        <el-tag :type="row.impactLevel==='严重影响'?'danger':row.impactLevel==='中度影响'?'warning':'info'" size="small">{{ row.impactLevel }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="estimatedDelay" label="预估延误" width="90" />
                  </el-table>
                  <el-divider />
                  <div class="accident-action">
                    <el-button type="primary" size="small" @click="goAccidentRisk">🚨 事故风险实时预测（AI XGBoost）</el-button>
                  </div>
                </div>
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="never">
                <template #header>
                  <span><el-icon><PartlyCloudy /></el-icon> 🌤️ 天气-交通关联分析</span>
                </template>
                <div v-loading="loadingWeather" element-loading-text="加载天气分析...">
                  <el-table v-if="weatherImpact.length" :data="weatherImpact" size="small" max-height="350" stripe>
                    <el-table-column label="模型" width="80">
                      <template #default="{row}">
                        <el-tag v-if="row.modelName" size="mini" :type="row.isMlGenerated ? 'success' : 'info'">
                          {{ row.isMlGenerated ? 'ML' : '规则' }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="weather" label="天气" width="60">
                      <template #default="{row}">
                        <span>{{ row.weather === '晴' ? '☀️' : (row.weather === '小雨' || row.weather === '中雨' || row.weather === '暴雨') ? '🌧️' : row.weather === '大雪' ? '❄️' : '🌫️' }}</span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="temperature" label="温度" width="55" />
                    <el-table-column prop="speedReduction" label="速度下降" width="80">
                      <template #default="{row}">
                        <el-tag :type="row.congestionRisk==='高风险'?'danger':row.congestionRisk==='中风险'?'warning':'success'" size="small" effect="plain">{{ row.speedReduction }}</el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column prop="congestionRisk" label="拥堵风险" width="80" />
                    <el-table-column label="建议" min-width="160">
                      <template #default="{row}">
                        <span style="font-size:12px;color:#666">{{ row.drivingAdvice }}</span>
                      </template>
                    </el-table-column>
                  </el-table>
                  <el-empty v-else-if="!loadingWeather" description="暂无天气关联分析数据" />
                </div>
              </el-card>
            </el-col>
          </el-row>

        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 路段对话框 -->
    <el-dialog v-model="showSectionDialog" title="添加路段" width="520px">
      <el-form :model="sectionForm" label-width="100px">
        <el-form-item label="道路名称"><el-input v-model="sectionForm.roadName" /></el-form-item>
        <el-form-item label="区间"><el-input v-model="sectionForm.sectionName" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="sectionForm.roadType" style="width:100%">
            <el-option label="主干道" value="主干道" />
            <el-option label="次干道" value="次干道" />
            <el-option label="支路" value="支路" />
            <el-option label="快速路" value="快速路" />
            <el-option label="高速" value="高速" />
          </el-select>
        </el-form-item>
        <el-form-item label="长度(km)"><el-input-number v-model="sectionForm.length" :min="0" :step="0.1" style="width:100%" /></el-form-item>
        <el-form-item label="车道数"><el-input-number v-model="sectionForm.lanes" :min="1" :max="12" style="width:100%" /></el-form-item>
        <el-form-item label="限速(km/h)"><el-input-number v-model="sectionForm.speedLimit" :min="20" :max="120" :step="10" style="width:100%" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="sectionForm.status" style="width:100%">
            <el-option label="畅通" value="畅通" />
            <el-option label="缓行" value="缓行" />
            <el-option label="拥堵" value="拥堵" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSectionDialog=false">取消</el-button>
        <el-button type="primary" @click="saveSection">保存</el-button>
      </template>
    </el-dialog>

    <!-- 流量对话框 -->
    <el-dialog v-model="showFlowDialog" title="添加流量记录" width="520px">
      <el-form :model="flowForm" label-width="120px">
        <el-form-item label="路段ID"><el-input-number v-model="flowForm.sectionId" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="车流量"><el-input-number v-model="flowForm.flowCount" :min="0" style="width:100%" /></el-form-item>
        <el-form-item label="平均速度(km/h)"><el-input-number v-model="flowForm.avgSpeed" :min="0" :step="5" style="width:100%" /></el-form-item>
        <el-form-item label="平均通行时间(min)"><el-input-number v-model="flowForm.avgTravelTime" :min="0" :step="0.5" style="width:100%" /></el-form-item>
        <el-form-item label="拥堵等级">
          <el-select v-model="flowForm.congestionLevel" style="width:100%">
            <el-option label="畅通" value="畅通" />
            <el-option label="轻度拥堵" value="轻度拥堵" />
            <el-option label="中度拥堵" value="中度拥堵" />
            <el-option label="严重拥堵" value="严重拥堵" />
          </el-select>
        </el-form-item>
        <el-form-item label="记录日期">
          <el-date-picker v-model="flowForm.recordDate" type="date" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showFlowDialog=false">取消</el-button>
        <el-button type="primary" @click="saveFlowRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  WarningFilled, DataAnalysis, Clock, TrendCharts, Calendar,
  SetUp, InfoFilled, PartlyCloudy
} from '@element-plus/icons-vue'
import {
  getTrafficSections, saveTrafficSection, deleteTrafficSection,
  getTrafficFlow, saveTrafficFlow,
  getTrafficOverview, getTrafficFlowData,
  predictCongestion, getRouteOptimization,
  getPredictionCalendar, getTrafficHeatmap,
  getSmartDepartureTips, analyzeAccidentImpact,
  analyzeWeatherTraffic, detectTrafficAnomalies,
  simulateWhatIf
} from '../../api/modules'

const router = useRouter()

const activeTab = ref('sections')
const loading = ref(false)
const loadingFlow = ref(false)

// ===== 逐模块加载状态 (代替全局 analysisLoading) =====
const loadingOverview = ref(false)
const loadingHeatmap = ref(false)
const loadingDeparture = ref(false)
const loadingChart = ref(false)
const loadingCalendar = ref(false)
const loadingAccident = ref(false)
const loadingWeather = ref(false)
const loadingAnomaly = ref(false)

/* ============ 路段管理 ============ */
const sections = ref([])
const showSectionDialog = ref(false)
const sectionForm = ref({})

function openSectionDialog() { sectionForm.value = {}; showSectionDialog.value = true }

async function loadSections() {
  loading.value = true
  try { const r = await getTrafficSections(); sections.value = r.data || [] } catch {} finally { loading.value = false }
}

async function saveSection() {
  try { await saveTrafficSection(sectionForm.value); ElMessage.success('添加成功'); showSectionDialog.value = false; await loadSections() } catch {}
}

async function handleDeleteSection(id) {
  try { await ElMessageBox.confirm('确定删除该路段？', '确认'); await deleteTrafficSection(id); ElMessage.success('删除成功'); await loadSections() } catch {}
}

/* ============ 流量数据 ============ */
const flowFilter = ref({ sectionId: '', date: '' })
const flowRecords = ref([])
const showFlowDialog = ref(false)
const flowForm = ref({})

async function loadFlowData() {
  loadingFlow.value = true
  try {
    const params = {}
    if (flowFilter.value.sectionId) params.sectionId = flowFilter.value.sectionId
    const r = await getTrafficFlow(params)
    flowRecords.value = r.data || []
  } catch {} finally { loadingFlow.value = false }
}

function openFlowDialog() { flowForm.value = {}; showFlowDialog.value = true }

async function saveFlowRecord() {
  try { await saveTrafficFlow(flowForm.value); ElMessage.success('添加成功'); showFlowDialog.value = false; await loadFlowData() } catch {}
}

/* ============ 🚗 AI交通分析 ============ */
const overviewCards = ref([])
const flowChartRef = ref(null)
const chartContainerRef = ref(null)
let flowChart = null
let chartResizeObserver = null

/** ECharts resize handler - 防抖 */
let resizeTimer = null
function handleChartResize() {
  if (resizeTimer) clearTimeout(resizeTimer)
  resizeTimer = setTimeout(() => {
    if (flowChart && !flowChart.isDisposed()) {
      flowChart.resize()
    }
  }, 200)
}

// 异常告警
const anomalyAlerts = ref([])

// 热力图
const heatmapData = ref([])

// 出行建议
const departureTips = ref([])

// 预测日历
const calendarDays = ref([])

// 仿真沙盘
const simSectionId = ref(null)
const simType = ref('add_lane')
const simValue = ref(1)
const simLoading = ref(false)
const simResult = ref(null)

// 事故影响
const accidentSectionId = ref(null)
const accidentLoading = ref(false)
const accidentResult = ref(null)

// 天气关联
const weatherImpact = ref([])

function getHeatColor(idx) {
  if (idx >= 0.7) return 'linear-gradient(135deg, #fde8e8, #f56c6c30)'
  if (idx >= 0.45) return 'linear-gradient(135deg, #fdf6ec, #e6a23c30)'
  if (idx >= 0.2) return 'linear-gradient(135deg, #ecf5ff, #409eff20)'
  return 'linear-gradient(135deg, #f0f9eb, #67c23a20)'
}

function formatDateShort(d) {
  if (!d) return ''
  const parts = d.split('-')
  return parts[1] + '/' + parts[2]
}

/**
 * 安全请求包装: 每个请求独立 try-catch，失败则使用 mockFallback
 * 替换旧的 Promise.all 方式，防止一个超时导致全崩
 */
async function safeFetch(fn, mockFallback) {
  try {
    const res = await fn()
    return res.data ?? res
  } catch (e) {
    console.warn('[Traffic] API 请求失败，使用模拟数据:', e?.message || e)
    return typeof mockFallback === 'function' ? mockFallback() : mockFallback
  }
}

async function loadAnalysis() {
  // ==================== 1. 概览卡片 ====================
  loadingOverview.value = true
  const ov = await safeFetch(getTrafficOverview, {
    totalSections: 7, intersectionCount: 15,
    avgSpeed: 40, congestionLevel: '轻度拥堵', todayFlow: 35000
  })
  overviewCards.value = [
    { label: '道路总数', value: ov.totalSections || 7, color: '#409eff' },
    { label: '路口数', value: ov.intersectionCount || 15, color: '#67c23a' },
    { label: '平均速度', value: (ov.avgSpeed || 40) + ' km/h', color: '#e6a23c' },
    { label: '拥堵等级', value: ov.congestionLevel || '轻度拥堵', color: '#f56c6c' },
    { label: '今日车流量', value: (ov.todayFlow || 35000).toLocaleString(), color: '#909399' }
  ]
  loadingOverview.value = false

  // ==================== 2. 异常告警 ====================
  loadingAnomaly.value = true
  anomalyAlerts.value = await safeFetch(detectTrafficAnomalies, [
    {
      sectionId: 1, sectionName: '青年大街-浑河桥段',
      recordDate: new Date().toISOString().slice(0, 10),
      hour: new Date().getHours() + ':00',
      expectedFlow: 2850, actualFlow: 4120,
      deviation: '+44%', severity: '警告', type: '流量激增',
      possibleCause: '学校放学 + 商圈活动'
    }
  ])
  loadingAnomaly.value = false

  // ==================== 3. 24h流量图 ====================
  loadingChart.value = true
  const flowRes = await safeFetch(getTrafficFlowData, null)
  const hourlyData = flowRes?.hourlyData || generateMockHourlyData()
  nextTick(() => renderFlowChart(hourlyData))
  loadingChart.value = false

  // ==================== 4. 实时路况热力图 ====================
  loadingHeatmap.value = true
  heatmapData.value = await safeFetch(getTrafficHeatmap, generateMockHeatmap)
  loadingHeatmap.value = false

  // ==================== 5. AI出行建议 ====================
  loadingDeparture.value = true
  const depRes = await safeFetch(getSmartDepartureTips, { tips: generateMockDepartureTips() })
  departureTips.value = (depRes.tips || depRes) || []
  if (!Array.isArray(departureTips.value)) departureTips.value = []
  loadingDeparture.value = false

  // ==================== 6. 预测日历 ====================
  loadingCalendar.value = true
  const rawCal = await safeFetch(() => getPredictionCalendar(7), generateMockCalendar)
  if (Array.isArray(rawCal)) {
    const seen = new Set()
    calendarDays.value = rawCal.filter(d => {
      const key = d.date + '-' + d.sectionId
      if (seen.has(key)) return false
      seen.add(key)
      return true
    }).slice(0, 7)
  }
  loadingCalendar.value = false

  // ==================== 7. 天气关联分析 ====================
  loadingWeather.value = true
  weatherImpact.value = await safeFetch(analyzeWeatherTraffic, generateMockWeatherImpact)
  loadingWeather.value = false
}

/* ===================================================================
 * Mock 数据生成函数 — 每个子模块都有独立的 mock fallback
 * =================================================================== */

function generateMockHourlyData() {
  const data = []
  const seed = [
    { hour:0,flow:180,speed:52 },{ hour:1,flow:120,speed:55 },{ hour:2,flow:80,speed:58 },{ hour:3,flow:60,speed:60 },
    { hour:4,flow:150,speed:57 },{ hour:5,flow:400,speed:50 },{ hour:6,flow:1200,speed:42 },{ hour:7,flow:3800,speed:28 },
    { hour:8,flow:5200,speed:22 },{ hour:9,flow:4100,speed:30 },{ hour:10,flow:2800,speed:38 },{ hour:11,flow:2200,speed:42 },
    { hour:12,flow:2500,speed:40 },{ hour:13,flow:2300,speed:41 },{ hour:14,flow:2100,speed:43 },{ hour:15,flow:2600,speed:39 },
    { hour:16,flow:3500,speed:32 },{ hour:17,flow:4800,speed:20 },{ hour:18,flow:5500,speed:15 },{ hour:19,flow:4500,speed:25 },
    { hour:20,flow:3200,speed:35 },{ hour:21,flow:2100,speed:40 },{ hour:22,flow:1200,speed:45 },{ hour:23,flow:500,speed:48 }
  ]
  for (let h = 0; h < 24; h++) {
    const s = seed[h]
    const jitter = () => Math.round((Math.random() - 0.5) * (s.flow * 0.15))
    const flow = Math.max(0, s.flow + jitter())
    const speedJitter = (Math.random() - 0.5) * 5
    data.push({ hour: h, totalFlow: flow, avgSpeed: parseFloat(Math.max(8, s.speed + speedJitter).toFixed(1)) })
  }
  return data
}

function generateMockHeatmap() {
  const roads = [
    { roadName:'青年大街', sectionName:'浑河桥段', flow:4200, speed:22, lanes:6, length:3.2 },
    { roadName:'浑南大道', sectionName:'金阳大街段', flow:3100, speed:35, lanes:6, length:4.5 },
    { roadName:'南京南街', sectionName:'长白段', flow:2800, speed:38, lanes:4, length:3.8 },
    { roadName:'胜利大街', sectionName:'砂山段', flow:2500, speed:40, lanes:4, length:2.6 },
    { roadName:'文化路', sectionName:'三好街段', flow:3800, speed:25, lanes:4, length:1.8 },
    { roadName:'南北快速干道', sectionName:'小北段', flow:1500, speed:48, lanes:4, length:5.2 },
    { roadName:'二环', sectionName:'南环段', flow:4500, speed:18, lanes:6, length:7.0 }
  ]
  return roads.map((r, i) => {
    const congestionIndex = r.speed >= 40 ? 0.15 : r.speed >= 30 ? 0.35 : r.speed >= 20 ? 0.55 : 0.78
    const level = r.speed >= 50 ? '畅通' : r.speed >= 35 ? '轻度拥堵' : r.speed >= 20 ? '中度拥堵' : '严重拥堵'
    return {
      sectionId: i + 1, roadName: r.roadName, sectionName: r.sectionName,
      flow: r.flow, avgSpeed: r.speed, length: r.length, lanes: r.lanes,
      congestionLevel: level, congestionIndex: congestionIndex,
      longitude: 123.45 + i * 0.01, latitude: 41.78 + i * 0.005
    }
  })
}

function generateMockDepartureTips() {
  return [
    { sectionId:1, sectionName:'青年大街-浑河桥段', bestDepartureHour:'07:00', worstDepartureHour:'08:30', bestSpeed:42, worstSpeed:18, timeSaved:25, tip:'建议 07:00 前出发，比 08:30 高峰期可节省约 25 分钟' },
    { sectionId:2, sectionName:'浑南大道-金阳大街段', bestDepartureHour:'07:15', worstDepartureHour:'09:00', bestSpeed:48, worstSpeed:28, timeSaved:18, tip:'建议 07:15 前出发，比 09:00 高峰期可节省约 18 分钟' },
    { sectionId:3, sectionName:'文化路-三好街段', bestDepartureHour:'06:45', worstDepartureHour:'08:00', bestSpeed:40, worstSpeed:20, timeSaved:22, tip:'建议 06:45 前出发，比 08:00 高峰期可节省约 22 分钟' }
  ]
}

function generateMockCalendar() {
  const days = ['周一','周二','周三','周四','周五','周六','周日']
  const today = new Date()
  return [
    { date:new Date(today).toISOString().slice(0,10), dayOfWeek:days[today.getDay() === 0 ? 6 : today.getDay()-1], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:4200, eveningPeakFlow:5100, morningCongestion:'中度拥堵', eveningCongestion:'严重拥堵', dailyStatus:'高负荷' },
    { date:new Date(today.getTime()+864e5).toISOString().slice(0,10), dayOfWeek:days[(today.getDay()) % 7], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:3900, eveningPeakFlow:4800, morningCongestion:'轻度拥堵', eveningCongestion:'中度拥堵', dailyStatus:'高负荷' },
    { date:new Date(today.getTime()+2*864e5).toISOString().slice(0,10), dayOfWeek:days[(today.getDay()+1) % 7], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:3500, eveningPeakFlow:4200, morningCongestion:'轻度拥堵', eveningCongestion:'中度拥堵', dailyStatus:'中负荷' },
    { date:new Date(today.getTime()+3*864e5).toISOString().slice(0,10), dayOfWeek:days[(today.getDay()+2) % 7], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:2800, eveningPeakFlow:3500, morningCongestion:'畅通', eveningCongestion:'轻度拥堵', dailyStatus:'中负荷' },
    { date:new Date(today.getTime()+4*864e5).toISOString().slice(0,10), dayOfWeek:days[(today.getDay()+3) % 7], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:1800, eveningPeakFlow:2200, morningCongestion:'畅通', eveningCongestion:'畅通', dailyStatus:'低负荷' },
    { date:new Date(today.getTime()+5*864e5).toISOString().slice(0,10), dayOfWeek:days[(today.getDay()+4) % 7], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:1200, eveningPeakFlow:1600, morningCongestion:'畅通', eveningCongestion:'畅通', dailyStatus:'低负荷' },
    { date:new Date(today.getTime()+6*864e5).toISOString().slice(0,10), dayOfWeek:days[(today.getDay()+5) % 7], sectionId:1, sectionName:'青年大街-浑河桥段', morningPeakFlow:2500, eveningPeakFlow:3800, morningCongestion:'畅通', eveningCongestion:'轻度拥堵', dailyStatus:'中负荷' }
  ]
}

function generateMockWeatherImpact() {
  return [
    { weather:'晴', weatherType:'晴', temperature:'26°C', speedReduction:'0%', congestionRisk:'低风险', humidity:'30%', condition:'无', drivingAdvice:'出行条件良好', speedFactor:1.0, affectedSections:'7个路段' },
    { weather:'多云', weatherType:'多云', temperature:'22°C', speedReduction:'8%', congestionRisk:'低风险', humidity:'50%', condition:'无', drivingAdvice:'注意局部阵雨', speedFactor:0.92, affectedSections:'7个路段' },
    { weather:'小雨', weatherType:'雨', temperature:'18°C', speedReduction:'18%', congestionRisk:'中风险', humidity:'70%', condition:'小雨', drivingAdvice:'路面湿滑，注意减速', speedFactor:0.82, affectedSections:'7个路段' },
    { weather:'中雨', weatherType:'雨', temperature:'15°C', speedReduction:'30%', congestionRisk:'中风险', humidity:'85%', condition:'中雨', drivingAdvice:'建议错峰出行，避开易积水路段', speedFactor:0.70, affectedSections:'7个路段' },
    { weather:'暴雨', weatherType:'雨', temperature:'12°C', speedReduction:'50%', congestionRisk:'高风险', humidity:'95%', condition:'暴雨', drivingAdvice:'建议推迟出行或选择公共交通', speedFactor:0.50, affectedSections:'7个路段' },
    { weather:'大雪', weatherType:'雪', temperature:'-5°C', speedReduction:'60%', congestionRisk:'高风险', humidity:'90%', condition:'大雪', drivingAdvice:'建议减速慢行，保持车距，避免非必要出行', speedFactor:0.40, affectedSections:'7个路段' },
    { weather:'雾霾', weatherType:'多云', temperature:'20°C', speedReduction:'40%', congestionRisk:'高风险', humidity:'60%', condition:'雾', drivingAdvice:'开启雾灯，减速慢行，能见度低注意安全', speedFactor:0.60, affectedSections:'7个路段' }
  ]
}

/* ===================================================================
 * ECharts 图表渲染 (含 dataZoom + 响应式)
 * =================================================================== */
function renderFlowChart(data) {
  if (!flowChartRef.value) return

  // 正确销毁旧实例
  if (flowChart && !flowChart.isDisposed()) {
    flowChart.dispose()
  }
  flowChart = echarts.init(flowChartRef.value, null, { renderer: 'canvas' })

  // 注册 resize 观察器
  if (chartResizeObserver) chartResizeObserver.disconnect()
  chartResizeObserver = new ResizeObserver(handleChartResize)
  chartResizeObserver.observe(flowChartRef.value)

  const hours = data.map(d => (d.hour != null ? String(d.hour).padStart(2, '0') : '00') + ':00')
  const flowVals = data.map(d => d.totalFlow || 0)
  const speedVals = data.map(d => d.avgSpeed || 0)

  flowChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let s = `<b>${params[0].axisValue}</b><br/>`
        params.forEach(p => {
          const val = typeof p.value === 'number' ? (p.seriesIndex === 0 ? p.value.toLocaleString() + ' 辆' : p.value + ' km/h') : p.value
          s += `${p.marker} ${p.seriesName}: ${val}<br/>`
        })
        return s
      }
    },
    legend: { data: ['车流量', '平均速度'], top: 0 },
    grid: { left: 55, right: 55, top: 40, bottom: 45 },
    dataZoom: [
      { type: 'inside', start: 0, end: 100, minValueSpan: 6 },
      { type: 'slider', start: 0, end: 100, bottom: 5, height: 20, borderColor: '#dcdfe6' }
    ],
    xAxis: {
      type: 'category', data: hours,
      axisLabel: { rotate: 45, fontSize: 11 },
      boundaryGap: false
    },
    yAxis: [
      { type: 'value', name: '车流量（辆）', axisLabel: { formatter: v => v >= 1000 ? (v/1000).toFixed(0) + 'k' : v } },
      { type: 'value', name: '速度(km/h)', min: 0, max: 70 }
    ],
    series: [
      {
        name: '车流量',
        type: 'line',
        data: flowVals,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#409eff', width: 3 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(64, 158, 255, 0.35)' },
            { offset: 1, color: 'rgba(64, 158, 255, 0.02)' }
          ])
        },
        markLine: {
          silent: true,
          data: [
            { yAxis: 3000, name: '拥堵阈值', lineStyle: { color: '#e6a23c', type: 'dashed' } },
            { yAxis: 1000, name: '畅通阈值', lineStyle: { color: '#67c23a', type: 'dashed' } }
          ]
        }
      },
      {
        name: '平均速度',
        type: 'line',
        yAxisIndex: 1,
        data: speedVals,
        smooth: true,
        symbol: 'diamond',
        symbolSize: 6,
        lineStyle: { color: '#e6a23c', width: 2, type: 'dashed' },
        markLine: {
          silent: true,
          data: [
            { yAxis: 30, name: '拥堵警戒线', lineStyle: { color: '#f56c6c', type: 'dashed' } }
          ]
        }
      }
    ]
  })

  // 窗口 resize 监听
  window.addEventListener('resize', handleChartResize)
}

/* 仿真沙盘 */
async function runSimulation() {
  if (!simSectionId.value) { ElMessage.warning('请先选择路段'); return }
  simLoading.value = true
  try {
    const scenario = { type: simType.value, value: simValue.value }
    const r = await simulateWhatIf(simSectionId.value, scenario)
    simResult.value = r.data
  } catch {} finally { simLoading.value = false }
}

/* 事故影响 — 带 fallback 的版本 */
async function loadAccidentImpact() {
  if (!accidentSectionId.value) { ElMessage.warning('请选择路段'); return }
  accidentLoading.value = true
  try {
    const r = await analyzeAccidentImpact(accidentSectionId.value)
    accidentResult.value = r.data || generateMockAccidentImpact(accidentSectionId.value)
  } catch {
    accidentResult.value = generateMockAccidentImpact(accidentSectionId.value)
  } finally { accidentLoading.value = false }
}

/** 跳转到事故风险预测子页面 */
function goAccidentRisk() {
  const route = router.resolve({ name: 'TrafficAccidentRisk' })
  if (route) {
    router.push({ name: 'TrafficAccidentRisk' })
  } else {
    window.open('/#/scenarios/traffic/accident-risk')
  }
}

function generateMockAccidentImpact(sectionId) {
  const section = sections.value.find(s => s.id === sectionId) || { roadName:'城市主干道', sectionName:'未知段' }
  return {
    accidentSection: section.roadName + '-' + section.sectionName,
    accidentLevel: '一般事故',
    normalFlow: 2800,
    reducedCapacity: 840,
    capacityLossPercent: 70,
    affectedSectionCount: 4,
    totalDivertedFlow: 1680,
    estimatedClearTime: '约40分钟',
    recommendation: '建议引导车辆绕行浑南大道等受影响较小的路段',
    analysisTime: new Date().toISOString(),
    affectedSections: [
      { sectionName:'浑南大道-金阳大街段', impactLevel:'中度影响', extraLoadPercent:25, divertedFlow:480, estimatedDelay:'8分钟' },
      { sectionName:'南京南街-长白段', impactLevel:'轻微影响', extraLoadPercent:12, divertedFlow:240, estimatedDelay:'4分钟' },
      { sectionName:'文化路-三好街段', impactLevel:'轻微影响', extraLoadPercent:8, divertedFlow:160, estimatedDelay:'3分钟' },
      { sectionName:'胜利大街-砂山段', impactLevel:'无影响', extraLoadPercent:3, divertedFlow:60, estimatedDelay:'1分钟' }
    ]
  }
}

/* ============ 生命周期 ============ */
onMounted(() => loadSections())

/** 彻底销毁 ECharts 实例，释放内存 */
function disposeFlowChart() {
  if (flowChart && !flowChart.isDisposed()) {
    flowChart.dispose()
    flowChart = null
  }
  if (chartResizeObserver) {
    chartResizeObserver.disconnect()
    chartResizeObserver = null
  }
  window.removeEventListener('resize', handleChartResize)
  if (resizeTimer) {
    clearTimeout(resizeTimer)
    resizeTimer = null
  }
}

onBeforeUnmount(() => {
  disposeFlowChart()
})

watch(activeTab, (tab, oldTab) => {
  // 切出分析页时释放图表资源
  if (oldTab === 'analysis' && tab !== 'analysis') {
    disposeFlowChart()
  }
  if (tab === 'flow') {
    flowFilter.value = { sectionId: '', date: '' }
    loadFlowData()
  }
  if (tab === 'analysis') {
    nextTick(() => loadAnalysis())
  }
})
</script>

<style scoped>
.flex-between { display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:8px; }

/* 概览卡片 */
.stat-box { text-align:center; padding:18px 8px; background:#f7f8fa; border-radius:8px; }
.stat-box .num { display:block; font-size:24px; font-weight:bold; }
.stat-box .lab { display:block; font-size:12px; color:#909399; margin-top:4px; }

/* 异常告警滚动 */
.alert-scroll { display:flex; align-items:center; }
.alert-text { flex:1; font-size:13px; color:#666; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }

/* 热力图网格 */
.heatmap-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(160px,1fr)); gap:10px; }
.heatmap-cell {
  border-radius:10px; padding:12px; text-align:center;
  border:1px solid #ebeef5; cursor:default; transition:transform .2s;
}
.heatmap-cell:hover { transform:translateY(-2px); box-shadow:0 4px 12px rgba(0,0,0,.08); }
.hm-name { font-weight:bold; font-size:13px; margin-bottom:4px; }
.hm-speed { font-size:18px; font-weight:bold; color:#303133; }
.hm-flow { font-size:11px; color:#909399; margin-top:2px; }

/* 出行建议卡片 */
.departure-card {
  padding:12px; border-bottom:1px solid #ebeef5; transition:background .2s;
}
.departure-card:last-child { border-bottom:none; }
.departure-card:hover { background:#f5f7fa; }
.dep-header { display:flex; align-items:center; gap:8px; margin-bottom:8px; }
.dep-section { flex:1; font-weight:bold; font-size:13px; }
.dep-body { padding-left:4px; }
.dep-tip { font-size:12px; color:#666; margin-top:6px; padding:6px 10px; background:#f0f9eb; border-radius:6px; }

/* 图表 */
.chart-container { width:100%; height:340px; }

/* 预测日历滚动 */
.calendar-scroll { display:flex; gap:10px; overflow-x:auto; padding:4px 0; }
.calendar-day-card {
  min-width:150px; border-radius:8px; padding:12px;
  background:#fafafa; border:1px solid #ebeef5;
}
.cal-header { display:flex; justify-content:space-between; margin-bottom:8px; }
.cal-date { font-weight:bold; font-size:14px; }
.cal-weekday { font-size:12px; color:#909399; }
.cal-body { font-size:12px; }
.cal-peak { display:flex; justify-content:space-between; margin:4px 0; }
.cal-body b { color:#303133; }
.cal-status { text-align:center; margin-top:6px; }

/* 仿真沙盘 */
.sim-controls { padding:4px; }
.sim-placeholder { display:flex; flex-direction:column; align-items:center; justify-content:center; padding:60px 0; color:#909399; }
.sim-placeholder p { margin-top:16px; font-size:14px; }
.sim-result { min-height:100px; }
.sim-metric { text-align:center; padding:12px; background:#f7f8fa; border-radius:8px; }
.sim-label { display:block; font-size:12px; color:#909399; margin-bottom:4px; }
.sim-val { display:block; font-size:20px; font-weight:bold; }

/* 事故分析 */
.accident-controls { display:flex; gap:8px; margin-bottom:12px; }
.accident-stats { display:flex; gap:16px; flex-wrap:wrap; font-size:13px; color:#666; }
.accident-stats div { padding:8px 12px; background:#fef0f0; border-radius:6px; }
.accident-action { text-align:center; padding:8px 0; }

/* 天气图标 */
.weather-icon { font-size:18px; }
</style>
