<template>
  <div class="ct-workstation">
    <!-- 工具栏 -->
    <div class="ct-toolbar">
      <div class="toolbar-left">
        <span class="toolbar-title">CT 影像分析工作台</span>
        <el-tag v-if="loaded" type="success" size="small" effect="dark">
          {{ shape[0] }}层 × {{ shape[1] }}×{{ shape[2] }}
        </el-tag>
      </div>
      <div class="toolbar-right">
        <el-button :type="showControlPanel ? 'primary' : 'default'" size="small" @click="showControlPanel = !showControlPanel">
          <el-icon><Setting /></el-icon> 控制面板
        </el-button>
        <el-button type="primary" size="small" :loading="loading" @click="showLoadDialog = true">
          <el-icon><Upload /></el-icon> 加载CT数据
        </el-button>
      </div>
    </div>

    <div class="ct-layout" :class="{ 'with-panel': showControlPanel }">
      <!-- 左侧控制面板 -->
      <transition name="slide">
        <div v-if="showControlPanel" class="ct-control-panel">
          <el-scrollbar max-height="calc(100vh - 200px)">
            <!-- 切片导航 -->
            <div class="panel-section">
              <h4><el-icon><Rank /></el-icon> 切片导航</h4>
              <el-slider v-model="currentZ" :min="0" :max="zMax" :step="1" show-input size="small" />
              <div class="slice-info">切片 {{ currentZ }} / {{ zMax }}</div>
            </div>

            <el-divider />

            <!-- 窗宽窗位 -->
            <div class="panel-section">
              <h4><el-icon><Sunny /></el-icon> 窗宽窗位</h4>
              <el-select v-model="windowPreset" size="small" style="width:100%;margin-bottom:8px" @change="onWindowPresetChange">
                <el-option v-for="(val, key) in windowPresets" :key="key" :label="key" :value="key" />
              </el-select>
              <el-slider v-model="windowWidth" :min="10" :max="3000" :step="10" show-input size="small" />
              <span class="param-label">窗宽: {{ windowWidth }}</span>
              <el-slider v-model="windowLevel" :min="-1000" :max="2000" :step="10" show-input size="small" />
              <span class="param-label">窗位: {{ windowLevel }}</span>
            </div>

            <el-divider />

            <!-- 滤波 -->
            <div class="panel-section">
              <h4><el-icon><Filter /></el-icon> 滤波</h4>
              <el-select v-model="filterMode" size="small" style="width:100%;margin-bottom:8px">
                <el-option label="不滤波" value="不滤波" />
                <el-option label="高斯滤波 (DiscreteGaussian)" value="高斯滤波 (DiscreteGaussian)" />
                <el-option label="中值滤波 (Median)" value="中值滤波 (Median)" />
                <el-option label="双边滤波 (Bilateral)" value="双边滤波 (Bilateral)" />
                <el-option label="曲率流 (CurvatureFlow)" value="曲率流 (CurvatureFlow)" />
                <el-option label="各向异性扩散 (GradientAnisotropic)" value="各向异性扩散 (GradientAnisotropic)" />
              </el-select>
              <el-slider v-model="filterVariance" :min="0.1" :max="3.0" :step="0.1" show-input size="small" />
              <span class="param-label">滤波参数: {{ filterVariance.toFixed(1) }}</span>
            </div>

            <el-divider />

            <!-- 显示模式 -->
            <div class="panel-section">
              <h4><el-icon><Monitor /></el-icon> 显示模式</h4>
              <el-radio-group v-model="displayMode" size="small">
                <el-radio-button value="normal">原图</el-radio-button>
                <el-radio-button value="edge">边缘</el-radio-button>
                <el-radio-button value="threshold">阈值</el-radio-button>
              </el-radio-group>
              <template v-if="displayMode === 'edge'">
                <el-select v-model="edgeMethod" size="small" style="width:100%;margin-top:8px">
                  <el-option v-for="m in edgeMethods" :key="m" :label="m" :value="m" />
                </el-select>
                <el-slider v-model="edgeThreshold" :min="10" :max="300" :step="5" show-input size="small" />
                <span class="param-label">阈值: {{ edgeThreshold }}</span>
              </template>
              <template v-if="displayMode === 'threshold'">
                <span class="param-label">阈值范围: [{{ thLow.toFixed(0) }}, {{ thHigh.toFixed(0) }}]</span>
              </template>
            </div>

            <el-divider />

            <!-- 操作按钮 -->
            <div class="panel-section">
              <h4><el-icon><Coin /></el-icon> 操作</h4>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="refreshSlice">
                <el-icon><Refresh /></el-icon> 刷新视图
              </el-button>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="showFilterCompare = !showFilterCompare">
                <el-icon><Grid /></el-icon> 滤波强度对比
              </el-button>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="showHistogram = !showHistogram">
                <el-icon><DataLine /></el-icon> 直方图
              </el-button>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="exec3DSegment">
                <el-icon><MagicStick /></el-icon> 三维分割
              </el-button>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="execMetalDetect">
                <el-icon><Warning /></el-icon> 金属伪影检测
              </el-button>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="showMpr = !showMpr">
                <el-icon><Grid /></el-icon> MPR 多平面视图
              </el-button>
              <el-button size="small" style="width:100%;margin-bottom:4px" @click="generateMontage">
                <el-icon><Picture /></el-icon> 生成拼图
              </el-button>
              <el-button size="small" type="success" style="width:100%;margin-bottom:4px" @click="fetchReport">
                <el-icon><Document /></el-icon> 诊断报告
              </el-button>
              <el-button size="small" type="warning" style="width:100%;margin-bottom:4px" @click="fetchStats">
                <el-icon><DataAnalysis /></el-icon> 统计分析
              </el-button>
              <el-button size="small" type="danger" style="width:100%;margin-bottom:4px" @click="ctAiAnalyzeCall">
                <el-icon><Reading /></el-icon> CT AI 分析
              </el-button>
              <el-button size="small" type="danger" style="width:100%" @click="ctAiArtifactSegmentCall">
                <el-icon><Aim /></el-icon> AI 伪影分割
              </el-button>
            </div>

            <!-- 3D分割参数 -->
            <el-divider />
            <div class="panel-section">
              <h4><el-icon><MagicStick /></el-icon> 三维分割参数</h4>
              <span class="param-label">阈值下限</span>
              <el-slider v-model="segLow" :min="-1200" :max="2000" :step="10" show-input size="small" />
              <span class="param-label">阈值上限</span>
              <el-slider v-model="segHigh" :min="-1200" :max="3000" :step="10" show-input size="small" />
              <span class="param-label">开运算半径: {{ segOpening }}</span>
              <el-slider v-model="segOpening" :min="0" :max="5" :step="1" size="small" />
              <span class="param-label">闭运算半径: {{ segClosing }}</span>
              <el-slider v-model="segClosing" :min="0" :max="5" :step="1" size="small" />
              <span class="param-label">最小体素: {{ segMinSize }}</span>
              <el-slider v-model="segMinSize" :min="0" :max="20000" :step="100" size="small" />
            </div>

            <!-- 金属伪影参数 -->
            <el-divider />
            <div class="panel-section">
              <h4><el-icon><Warning /></el-icon> 金属伪影检测参数</h4>
              <span class="param-label">HU下限: {{ metalLow }}</span>
              <el-slider v-model="metalLow" :min="300" :max="1500" :step="10" size="small" />
              <span class="param-label">HU上限: {{ metalHigh }}</span>
              <el-slider v-model="metalHigh" :min="2000" :max="4000" :step="10" size="small" />
              <span class="param-label">梯度阈值: {{ metalGrad }}</span>
              <el-slider v-model="metalGrad" :min="50" :max="500" :step="5" size="small" />
              <span class="param-label">最小面积: {{ metalMinSize }}</span>
              <el-slider v-model="metalMinSize" :min="10" :max="5000" :step="10" size="small" />
              <el-checkbox v-model="showSegOverlay" label="显示分割叠加" border size="small" style="margin-top:8px" />
              <el-checkbox v-model="showMetalOverlay" label="显示伪影标注" border size="small" style="margin-top:4px" />
            </div>
          </el-scrollbar>
        </div>
      </transition>

      <!-- 主图像区域 -->
      <div class="ct-main">
        <!-- 加载提示 -->
        <div v-if="!loaded" class="ct-empty">
          <el-empty description="点击「加载CT数据」开始分析">
            <el-button type="primary" @click="loadDefaultData">
              <el-icon><Upload /></el-icon> 加载默认CT数据
            </el-button>
            <p style="font-size:12px;color:#999;margin-top:8px">
              支持 NIfTI (.nii.gz) / NRRD (.nrrd)
            </p>
          </el-empty>
        </div>

        <template v-else>
          <!-- 图像显示 -->
          <div class="ct-image-row">
            <div class="ct-image-card">
              <div class="card-label">原始/滤波视图 (第 {{ currentZ }} 层)</div>
              <div class="image-container" v-loading="loadingImage">
                <img v-if="currentImage" :src="'data:image/png;base64,' + currentImage" class="ct-slice-img" />
              </div>
            </div>
            <div class="ct-image-card">
              <div class="card-label">{{ processedLabel }}</div>
              <div class="image-container" v-loading="loadingImage">
                <img v-if="processedImage" :src="'data:image/png;base64,' + processedImage" class="ct-slice-img" />
              </div>
            </div>
          </div>

          <!-- 滤波强度对比 -->
          <el-collapse-transition>
            <div v-if="showFilterCompare" class="ct-compare-row">
              <el-card shadow="hover" class="compare-card">
                <template #header>
                  <span>滤波强度对比 | 第 {{ currentZ }} 层</span>
                  <el-button size="small" text @click="doFilterCompare" style="float:right">
                    <el-icon><Refresh /></el-icon> 刷新
                  </el-button>
                </template>
                <div v-if="compareImages && Object.keys(compareImages).length > 0" class="compare-grid">
                  <div v-for="(img, key) in compareImages" :key="key" class="compare-item">
                    <div class="compare-label">{{ key.replace('strength_', '强度 ') }}</div>
                    <img :src="'data:image/png;base64,' + img" class="compare-img" />
                  </div>
                </div>
                <el-empty v-else description="点击刷新加载对比" :image-size="40" />
              </el-card>
            </div>
          </el-collapse-transition>

          <!-- 直方图 -->
          <el-collapse-transition>
            <div v-if="showHistogram" class="ct-histogram-row">
              <el-card shadow="hover">
                <template #header>
                  <span>灰度直方图 | 第 {{ currentZ }} 层</span>
                  <el-button size="small" text @click="doHistogram" style="float:right">
                    <el-icon><Refresh /></el-icon> 刷新
                  </el-button>
                </template>
                <img v-if="histogramImage" :src="'data:image/png;base64,' + histogramImage" class="histogram-img" />
                <div v-if="histogramStats" class="histogram-stats-grid">
                  <div class="stat-item"><span class="stat-l">HU均值</span><span class="stat-v">{{ histogramStats.mean?.toFixed(1) }}</span></div>
                  <div class="stat-item"><span class="stat-l">HU标准差</span><span class="stat-v">{{ histogramStats.std?.toFixed(1) }}</span></div>
                  <div class="stat-item"><span class="stat-l">范围</span><span class="stat-v">{{ histogramStats.min?.toFixed(0) }} ~ {{ histogramStats.max?.toFixed(0) }}</span></div>
                  <div class="stat-item"><span class="stat-l">P5/P50/P95</span><span class="stat-v">{{ histogramStats.p5?.toFixed(0) }} / {{ histogramStats.p50?.toFixed(0) }} / {{ histogramStats.p95?.toFixed(0) }}</span></div>
                </div>
              </el-card>
            </div>
          </el-collapse-transition>

          <!-- MPR -->
          <el-collapse-transition>
            <div v-if="showMpr" class="ct-mpr-row">
              <el-card shadow="hover">
                <template #header>
                  <span>MPR 多平面重建</span>
                  <el-button size="small" text @click="doMpr" style="float:right">
                    <el-icon><Refresh /></el-icon> 刷新
                  </el-button>
                </template>
                <div class="mpr-sliders">
                  <div class="mpr-slider-item">
                    <span>Axial Z:</span>
                    <el-slider v-model="mprZ" :min="0" :max="zMax" :step="1" show-input size="small" style="flex:1" />
                  </div>
                  <div class="mpr-slider-item">
                    <span>Coronal Y:</span>
                    <el-slider v-model="mprY" :min="0" :max="shape[1] - 1" :step="1" show-input size="small" style="flex:1" />
                  </div>
                  <div class="mpr-slider-item">
                    <span>Sagittal X:</span>
                    <el-slider v-model="mprX" :min="0" :max="shape[2] - 1" :step="1" show-input size="small" style="flex:1" />
                  </div>
                </div>
                <div class="mpr-grid">
                  <div v-if="mprImages.axial" class="mpr-item">
                    <div class="mpr-label">Axial (横断面) Z={{ mprZ }}</div>
                    <img :src="'data:image/png;base64,' + mprImages.axial" class="mpr-img" />
                  </div>
                  <div v-if="mprImages.coronal" class="mpr-item">
                    <div class="mpr-label">Coronal (冠状面) Y={{ mprY }}</div>
                    <img :src="'data:image/png;base64,' + mprImages.coronal" class="mpr-img" />
                  </div>
                  <div v-if="mprImages.sagittal" class="mpr-item">
                    <div class="mpr-label">Sagittal (矢状面) X={{ mprX }}</div>
                    <img :src="'data:image/png;base64,' + mprImages.sagittal" class="mpr-img" />
                  </div>
                </div>
              </el-card>
            </div>
          </el-collapse-transition>

          <!-- 诊断报告 -->
          <el-collapse-transition>
            <div v-if="showReport && reportData" class="ct-report-row">
              <el-card shadow="hover">
                <template #header>
                  <span><el-icon><Document /></el-icon> CT 诊断报告</span>
                  <span style="float:right;font-size:12px;color:#999">{{ reportData.report_time }}</span>
                </template>
                <el-descriptions :column="2" border size="small">
                  <el-descriptions-item label="扫描层数">{{ reportData.scan_info?.slices }}</el-descriptions-item>
                  <el-descriptions-item label="体素总数">{{ reportData.scan_info?.voxel_count?.toLocaleString() }}</el-descriptions-item>
                  <el-descriptions-item label="HU均值">{{ reportData.hu_statistics?.mean?.toFixed(1) }}</el-descriptions-item>
                  <el-descriptions-item label="HU范围">{{ reportData.hu_statistics?.min?.toFixed(0) }} ~ {{ reportData.hu_statistics?.max?.toFixed(0) }}</el-descriptions-item>
                </el-descriptions>
                <el-divider />
                <h4>组织分析</h4>
                <el-progress v-if="reportData.tissue_analysis" :percentage="reportData.tissue_analysis.csf_percent" :text-inside="true" :stroke-width="18" :color="'#409eff'" :format="() => `脑脊液 ${reportData.tissue_analysis.csf_percent.toFixed(1)}%`" />
                <el-progress v-if="reportData.tissue_analysis" :percentage="reportData.tissue_analysis.gray_matter_percent" :text-inside="true" :stroke-width="18" :color="'#67c23a'" :format="() => `灰质 ${reportData.tissue_analysis.gray_matter_percent.toFixed(1)}%`" />
                <el-progress v-if="reportData.tissue_analysis" :percentage="reportData.tissue_analysis.white_matter_percent" :text-inside="true" :stroke-width="18" :color="'#e6a23c'" :format="() => `白质 ${reportData.tissue_analysis.white_matter_percent.toFixed(1)}%`" />
                <el-divider />
                <h4>发现</h4>
                <ul>
                  <li v-for="(f, i) in reportData.findings" :key="i">{{ f }}</li>
                </ul>
                <h4>诊断意见</h4>
                <el-alert :title="reportData.impression" type="info" :closable="false" />
                <h4>建议</h4>
                <ul>
                  <li v-for="(r, i) in reportData.recommendations" :key="i">{{ r }}</li>
                </ul>
              </el-card>
            </div>
          </el-collapse-transition>

          <!-- 统计分析 -->
          <el-collapse-transition>
            <div v-if="showStats && statsData" class="ct-stats-row">
              <el-card shadow="hover">
                <template #header><span>CT 统计分析</span></template>
                <el-tabs>
                  <el-tab-pane label="体数据统计">
                    <el-descriptions :column="2" border size="small">
                      <el-descriptions-item label="形状">{{ statsData.volume_stats?.shape?.join('×') }}</el-descriptions-item>
                      <el-descriptions-item label="HU均值">{{ statsData.volume_stats?.mean_hu?.toFixed(1) }}</el-descriptions-item>
                      <el-descriptions-item label="HU标准差">{{ statsData.volume_stats?.std_hu?.toFixed(1) }}</el-descriptions-item>
                      <el-descriptions-item label="HU范围">{{ statsData.volume_stats?.min_hu?.toFixed(0) }} ~ {{ statsData.volume_stats?.max_hu?.toFixed(0) }}</el-descriptions-item>
                    </el-descriptions>
                  </el-tab-pane>
                  <el-tab-pane label="对称性分析">
                    <el-descriptions v-if="statsData.symmetry_analysis" :column="1" border size="small">
                      <el-descriptions-item label="不对称指数">{{ statsData.symmetry_analysis.asymmetry_index }}</el-descriptions-item>
                      <el-descriptions-item label="最大不对称">{{ statsData.symmetry_analysis.max_asymmetry?.toFixed(1) }} HU</el-descriptions-item>
                      <el-descriptions-item label="最不对称切片">第 {{ statsData.symmetry_analysis.most_asymmetric_slice }} 层</el-descriptions-item>
                    </el-descriptions>
                  </el-tab-pane>
                  <el-tab-pane label="出血评估">
                    <el-descriptions v-if="statsData.hemorrhage_analysis" :column="1" border size="small">
                      <el-descriptions-item label="出血概率">{{ (statsData.hemorrhage_analysis.hemorrhage_probability * 100).toFixed(1) }}%</el-descriptions-item>
                      <el-descriptions-item label="风险等级">
                        <el-tag :type="statsData.hemorrhage_analysis.risk_level === 'high' ? 'danger' : (statsData.hemorrhage_analysis.risk_level === 'medium' ? 'warning' : 'success')">
                          {{ statsData.hemorrhage_analysis.risk_level === 'high' ? '高风险' : (statsData.hemorrhage_analysis.risk_level === 'medium' ? '中风险' : '低风险') }}
                        </el-tag>
                      </el-descriptions-item>
                      <el-descriptions-item label="高密度体素">{{ statsData.hemorrhage_analysis.high_density_voxels?.toLocaleString() }}</el-descriptions-item>
                    </el-descriptions>
                  </el-tab-pane>
                </el-tabs>
              </el-card>
            </div>
          </el-collapse-transition>

          <!-- 拼图 -->
          <el-collapse-transition>
            <div v-if="montageImage" class="ct-montage-row">
              <el-card shadow="hover">
                <template #header><span>CT 多切片拼图</span></template>
                <img :src="'data:image/png;base64,' + montageImage" style="width:100%" />
              </el-card>
            </div>
          </el-collapse-transition>
        </template>
      </div>
    </div>

    <!-- ════════════════ 加载对话框 ════════════════ -->
    <el-dialog v-model="showLoadDialog" title="加载CT数据 / 选择文件" width="620px" :close-on-click-modal="false" @open="onOpenDialog">
      <el-tabs v-model="loadSource" type="border-card">
        <el-tab-pane label="📁 从本机选择文件" name="local">
          <div class="load-mode-select" style="margin-top:8px">
            <el-radio-group v-model="loadMode" class="load-mode-radio">
              <el-radio-button value="dicom_series">
                <el-icon><FolderOpened /></el-icon> DICOM序列
              </el-radio-button>
              <el-radio-button value="mhd_volume">
                <el-icon><Grid /></el-icon> MHD/RAW影像
              </el-radio-button>
              <el-radio-button value="single_image">
                <el-icon><Picture /></el-icon> 单张图像
              </el-radio-button>
              <el-radio-button value="nifti_nrrd">
                <el-icon><Document /></el-icon> NIfTI/NRRD
              </el-radio-button>
            </el-radio-group>
          </div>

          <div style="margin-top:16px">
            <!-- 文件选择器 (根据模式显示不同提示) -->
            <div class="file-picker-area">
              <input
                ref="fileInputRef"
                type="file"
                :webkitdirectory="loadMode === 'dicom_series'"
                :directory="loadMode === 'dicom_series'"
                :accept="getAcceptPattern()"
                multiple
                style="display:none"
                @change="onFileSelected"
              />
              <el-button type="primary" size="large" @click="triggerFilePicker" style="width:100%;height:60px">
                <el-icon style="font-size:24px;margin-right:8px"><FolderOpened /></el-icon>
                <span style="font-size:15px">
                  {{ loadMode === 'dicom_series' ? '选择DICOM文件夹' : '选择文件' }}
                </span>
              </el-button>
              <p style="font-size:12px;color:#909399;text-align:center;margin-top:6px">
                <template v-if="loadMode === 'dicom_series'">
                  选择包含 .dcm 文件的文件夹（自动读取整个序列）
                </template>
                <template v-else-if="loadMode === 'mhd_volume'">
                  选择 .mhd 元文件（自动加载同目录 .raw 文件）
                </template>
                <template v-else-if="loadMode === 'single_image'">
                  选择 .dcm / .png / .jpg / .bmp 图像
                </template>
                <template v-else>
                  选择 .nii / .nii.gz / .nrrd 体数据
                </template>
              </p>
            </div>

            <!-- 已选文件信息 -->
            <div v-if="selectedFilePath" class="selected-file-info">
              <el-alert
                :title="selectedFileLabel"
                type="success"
                :description="'已选择 ' + selectedFileCount + ' 个文件'"
                show-icon
                :closable="false"
              />
            </div>

            <!-- 或手动输入路径 -->
            <el-divider><span style="font-size:12px;color:#999">或者直接输入本地路径</span></el-divider>

            <div class="manual-path-row">
              <el-input
                v-model="manualPath"
                placeholder="例如: D:\CT\(病例名称)\DICOM 或 /home/user/ct.nii.gz"
                clearable
                size="default"
              >
                <template #prepend>📁</template>
              </el-input>
              <el-button type="primary" :disabled="!manualPath" @click="confirmManualPath" style="margin-left:8px">
                加载路径
              </el-button>
            </div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="📂 CQ500数据集" name="cq500">
          <div style="margin-top:8px">
            <el-select v-model="cq500Filter" placeholder="筛选" size="small" style="width:120px;margin-right:8px">
              <el-option label="全部" value="all" />
              <el-option label="仅阳性" value="positive" />
              <el-option label="仅阴性" value="negative" />
              <el-option label="ICH出血" value="ich" />
            </el-select>
            <el-button size="small" @click="fetchCq500List">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
          <el-table
            :data="cq500Cases"
            style="width:100%;margin-top:8px"
            max-height="300px"
            size="small"
            highlight-current-row
            @row-dblclick="onCq500CaseSelect"
          >
            <el-table-column prop="name" label="病例" width="110" />
            <el-table-column prop="category" label="分级" width="60" />
            <el-table-column prop="ich" label="ICH" width="50" />
            <el-table-column prop="sdh" label="SDH" width="50" />
            <el-table-column label="体积" width="70">
              <template #default="{row}">
                <el-tag v-if="row.has_volume" size="small" type="success">已转换</el-tag>
                <el-tag v-else size="small" type="info">无</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{row}">
                <el-button size="small" type="primary" :disabled="!row.has_volume" @click="onCq500CaseSelect(row.name)">
                  加载
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <p v-if="!loadingCases && cq500Cases.length === 0" style="text-align:center;color:#999;font-size:12px">
            点击「刷新」加载病例列表
          </p>
          <p v-if="cq500Cases.length > 0" style="text-align:center;color:#999;font-size:12px;margin-top:4px">
            双击行或点击「加载」按钮加载该病例
          </p>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="showLoadDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!selectedFilePath && !manualPath"
          @click="confirmLoad"
        >
          加载
        </el-button>
      </template>
    </el-dialog>

    <!-- ════════════════ AI伪影分割结果 ════════════════ -->
    <el-dialog v-model="showArtifactResult" title="AI 伪影分割结果 (UNet3D)" width="640px" :close-on-click-modal="true">
      <template v-if="artifactResult">
        <el-descriptions :column="2" border size="small" style="margin-bottom:12px">
          <el-descriptions-item label="伪影体素">{{ artifactResult.artifact_voxels?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="总体素">{{ artifactResult.total_voxels?.toLocaleString() }}</el-descriptions-item>
          <el-descriptions-item label="伪影占比">
            <el-tag :type="artifactResult.artifact_ratio > 0.05 ? 'danger' : 'warning'">
              {{ (artifactResult.artifact_ratio * 100).toFixed(2) }}%
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="模型">{{ artifactResult.model }}</el-descriptions-item>
          <el-descriptions-item label="是否是深度学习">{{ artifactResult.is_deep_learning ? '✅ 是' : '❌ 否' }}</el-descriptions-item>
          <el-descriptions-item label="伪影最严重切片">第 {{ artifactResult.worst_slice }} 层</el-descriptions-item>
        </el-descriptions>

        <div style="text-align:center;margin-bottom:12px">
          <div style="font-size:12px;color:#909399;margin-bottom:4px">当前切片伪影叠加 (红色区域)</div>
          <img v-if="artifactResult.overlay" :src="'data:image/png;base64,' + artifactResult.overlay" style="max-width:100%;border-radius:4px" />
        </div>

        <div v-if="artifactResult.thumbnails && Object.keys(artifactResult.thumbnails).length > 0">
          <div style="font-size:12px;color:#909399;margin-bottom:4px">多切片概览</div>
          <div style="display:flex;flex-wrap:wrap;gap:4px;justify-content:center">
            <div v-for="(img, key) in artifactResult.thumbnails" :key="key" style="width:60px;text-align:center">
              <img :src="'data:image/png;base64,' + img" style="width:60px;height:60px;border-radius:2px;object-fit:cover" />
              <div style="font-size:10px;color:#909399">{{ key }}</div>
            </div>
          </div>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, computed, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Setting, Upload, Rank, Sunny, Filter, Monitor, Coin,
  Refresh, Grid, DataLine, MagicStick, Warning, Picture,
  Document, DataAnalysis, FolderOpened, Folder, Reading, Aim
} from '@element-plus/icons-vue'
import {
  ctNewSession, ctLoadData, ctGetSlice, ctGetMpr, ctFilterCompare,
  ctGetHistogram, ctGetStatistics, ctSegment3d, ctMetalDetect,
  ctGetMontage, ctGenerateReport, ctGetWindowPresets, ctListDataFiles,
  ctAiAnalyze, ctAiArtifactSegment,
  cq500LoadCase, cq500ListCases
} from '../../api/modules'

// ====== 状态 ======
const loading = ref(false)
const loadingImage = ref(false)
const loaded = ref(false)
const showControlPanel = ref(true)

// 加载对话框
const showLoadDialog = ref(false)
const loadMode = ref('dicom_series')
const loadSource = ref('local')  // 'local' | 'cq500'
const fileInputRef = ref(null)
const selectedFilePath = ref('')
const selectedFileLabel = ref('')
const selectedFileCount = ref(0)
const manualPath = ref('')
const selectedFiles = ref([])

// CQ500选中的病例
const cq500SelectedCase = ref('')
const cq500Filter = ref('all')
const cq500Cases = ref([])
const loadingCases = ref(false)

const sessionId = ref('')
const shape = ref([1, 256, 256])
const zMax = computed(() => Math.max(0, shape.value[0] - 1))
const currentZ = ref(0)
const currentImage = ref('')
const processedLabel = ref('处理结果')
const processedImage = ref('')
const displayMode = ref('normal')

// 窗宽窗位
const windowPresets = ref({})
const windowPreset = ref('软组织窗')
const windowWidth = ref(350)
const windowLevel = ref(50)

// 滤波
const filterMode = ref('不滤波')
const filterVariance = ref(0.3)

// 边缘检测
const edgeMethods = ref(['Sobel', 'Canny', 'Laplacian', 'Prewitt'])
const edgeMethod = ref('Sobel')
const edgeThreshold = ref(80.0)

// 阈值
const thLow = ref(0)
const thHigh = ref(100)

// 三维分割
const segLow = ref(200)
const segHigh = ref(2800)
const segOpening = ref(1)
const segClosing = ref(2)
const segMinSize = ref(500)
const showSegOverlay = ref(false)

// 金属伪影
const metalLow = ref(600)
const metalHigh = ref(3500)
const metalGrad = ref(80)
const metalMinSize = ref(30)
const showMetalOverlay = ref(false)

// 面板显示
const showFilterCompare = ref(false)
const showHistogram = ref(false)
const showMpr = ref(false)
const showReport = ref(false)
const showStats = ref(false)
const compareImages = ref({})
const histogramImage = ref('')
const histogramStats = ref(null)
const mprImages = ref({})
const mprZ = ref(0)
const mprY = ref(128)
const mprX = ref(128)
const reportData = ref(null)
const statsData = ref(null)
const montageImage = ref('')

// ====== 方法 ======

async function fetchCq500List() {
  loadingCases.value = true
  try {
    let params = { page: 1, page_size: 200, only_with_volume: true }
    if (cq500Filter.value === 'positive') params.is_positive = true
    else if (cq500Filter.value === 'negative') params.is_positive = false
    else if (cq500Filter.value === 'ich') params.has_ich = true
    const res = await cq500ListCases(params)
    cq500Cases.value = (res.data?.data || res.data || {}).cases || []
  } catch (e) {
    console.warn('CQ500 case list error', e)
  } finally {
    loadingCases.value = false
  }
}

// ====== 文件选择 ======

function getAcceptPattern() {
  switch (loadMode.value) {
    case 'dicom_series': return ''  // folders, accept all
    case 'mhd_volume': return '.mhd'
    case 'single_image': return '.dcm,.png,.jpg,.jpeg,.bmp'
    case 'nifti_nrrd': return '.nii,.nii.gz,.nrrd'
    default: return ''
  }
}

function triggerFilePicker() {
  fileInputRef.value?.click()
}

function onFileSelected(event) {
  const files = event.target.files
  if (!files || files.length === 0) return
  selectedFiles.value = Array.from(files)
  selectedFileCount.value = files.length
  
  if (loadMode.value === 'dicom_series') {
    // 取第一个文件的目录路径
    const firstFile = files[0]
    // webkitRelativePath 给出了文件夹相对路径
    const fullPath = firstFile.webkitRelativePath || firstFile.name
    const dirPath = fullPath.substring(0, fullPath.lastIndexOf('/'))
    selectedFilePath.value = firstFile.webkitRelativePath ? fullPath.split('/')[0] : dirPath
    selectedFileLabel.value = 'DICOM序列目录: ' + (firstFile.webkitRelativePath ? firstFile.webkitRelativePath.split('/')[0] : '已选择')
  } else {
    selectedFilePath.value = files[0].name
    selectedFileLabel.value = '已选择: ' + files[0].name
  }
}

function onOpenDialog() {
  loadSource.value = 'local'
  selectedFilePath.value = ''
  selectedFileLabel.value = ''
  selectedFileCount.value = 0
  manualPath.value = ''
  cq500SelectedCase.value = ''
  selectedFiles.value = []
}

function onCq500CaseSelect(caseKey) {
  // caseKey 可能是字符串（按钮点击）或行对象（双击）
  const key = typeof caseKey === 'string' ? caseKey : (caseKey?.name || '')
  if (!key) return
  cq500SelectedCase.value = key
  loadSource.value = 'cq500'
  loadFromCq500(key)
  showLoadDialog.value = false
}

async function confirmManualPath() {
  if (!manualPath.value) return
  selectedFilePath.value = manualPath.value
  selectedFileLabel.value = '手动路径: ' + manualPath.value
  selectedFileCount.value = 1
  await executeLoadFromPath(manualPath.value)
}

// 执行加载（核心函数）
async function executeLoadFromPath(path) {
  loading.value = true
  showLoadDialog.value = false
  try {
    const res = await ctLoadData({ mode: loadMode.value, local_path: path })
    handleLoadResponse(res)
  } catch (e) {
    const errMsg = e.message || e.response?.data?.message || '未知错误'
    ElMessage.error('加载失败: ' + errMsg)
    // 友好提示并提供备用方案
    ElMessage.info('正在切换到示例数据模式...')
    await loadDefaultData()
  } finally {
    loading.value = false
  }
}

async function loadFromCq500(caseKey) {
  loading.value = true
  try {
    const res = await cq500LoadCase(caseKey)
    handleLoadResponse(res)
  } catch (e) {
    ElMessage.error('CQ500加载失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function loadDefaultData() {
  loading.value = true
  try {
    const res = await ctLoadData({ mode: 'nifti_nrrd', use_default: true })
    handleLoadResponse(res)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

async function confirmLoad() {
  if (!selectedFilePath.value && !manualPath.value && !cq500SelectedCase.value) {
    ElMessage.warning('请先选择文件或输入路径')
    return
  }
  
  if (loadSource.value === 'cq500' && cq500SelectedCase.value) {
    await loadFromCq500(cq500SelectedCase.value)
    return
  }
  
  // 从文件选择器或手动路径加载
  const pathToUse = selectedFilePath.value || manualPath.value
  if (pathToUse) {
    // 验证路径格式
    if (!pathToUse.trim()) {
      ElMessage.warning('路径不能为空')
      return
    }
    const trimmedPath = pathToUse.trim()
    selectedFilePath.value = trimmedPath
    // Show user-friendly message before attempting
    ElMessage.info(`正在尝试加载: ${trimmedPath}，如果失败将自动切换到示例数据`)
    await executeLoadFromPath(trimmedPath)
  }
}

function handleLoadResponse(res) {
  sessionId.value = res.sessionId || res.data?.sessionId || ''
  if (sessionId.value) {
    localStorage.setItem('ct_session_id', sessionId.value)
  }
  const d = res.data || res
  if (d.loaded) {
    shape.value = d.shape || [1, 256, 256]
    currentZ.value = Math.floor(shape.value[0] / 2)
    loaded.value = true
    ElMessage.success(`${d.description || 'CT数据'} 已加载: ${d.z_slices}层 x ${d.width} x ${d.height}`)
    nextTick(async () => {
      await initPresets()
      await refreshSlice()
    })
  } else {
    ElMessage.error('加载失败: ' + (d.error || res.message || '未知错误'))
  }
}

async function initPresets() {
  try {
    const res = await ctGetWindowPresets()
    windowPresets.value = res.data?.presets || {}
  } catch {}
}

function onWindowPresetChange(preset) {
  const p = windowPresets.value[preset]
  if (p) {
    windowWidth.value = p.ww
    windowLevel.value = p.wl
    refreshSlice()
  }
}

function withSession(params = {}) {
  return { ...params, sessionId: sessionId.value }
}

async function refreshSlice() {
  if (!loaded.value) return
  loadingImage.value = true
  try {
    thLow.value = windowLevel.value - windowWidth.value / 4
    thHigh.value = windowLevel.value + windowWidth.value / 4

    const params = withSession({
      z: currentZ.value,
      ww: windowWidth.value,
      wl: windowLevel.value,
      filter: filterMode.value,
      variance: filterVariance.value,
      mode: displayMode.value,
      edge_method: edgeMethod.value,
      edge_threshold: edgeThreshold.value,
      th_low: thLow.value,
      th_high: thHigh.value,
      show_seg: showSegOverlay.value,
      show_metal: showMetalOverlay.value,
    })

    const res = await ctGetSlice(params)
    currentImage.value = res.data?.image_original || ''
    processedImage.value = res.data?.image || ''
    processedLabel.value = displayMode.value === 'edge'
      ? `边缘检测 (${edgeMethod.value})`
      : displayMode.value === 'threshold'
        ? `阈值分割 [${thLow.value.toFixed(0)}, ${thHigh.value.toFixed(0)}]`
        : '处理结果'
  } catch (e) {
    const msg = e.message || e.response?.data?.message || ''
    if (msg.includes('请先加载CT数据')) {
      ElMessage.warning('会话已过期，请重新加载CT数据')
      loaded.value = false
      showLoadDialog.value = true
    } else {
      ElMessage.error('获取切片失败: ' + (msg || e.message || '未知错误'))
    }
  } finally {
    loadingImage.value = false
  }
}

async function doFilterCompare() {
  if (!loaded.value) return
  try {
    const res = await ctFilterCompare(withSession({
      z: currentZ.value,
      filter: filterMode.value,
      ww: windowWidth.value,
      wl: windowLevel.value,
      strengths: [0.3, 0.8, 1.5, 2.5]
    }))
    compareImages.value = res.data?.images || {}
  } catch {
    ElMessage.error('滤波对比失败')
  }
}

async function doHistogram() {
  if (!loaded.value) return
  try {
    const res = await ctGetHistogram(withSession({ z: currentZ.value, bins: 120 }))
    histogramImage.value = res.data?.histogram_image || ''
    histogramStats.value = res.data?.statistics || null
  } catch {
    ElMessage.error('直方图失败')
  }
}

async function doMpr() {
  if (!loaded.value) return
  try {
    const res = await ctGetMpr(withSession({
      z: mprZ.value, y: mprY.value, x: mprX.value,
      ww: windowWidth.value, wl: windowLevel.value,
      show_seg: showSegOverlay.value,
      show_metal: showMetalOverlay.value,
    }))
    mprImages.value = res.data || {}
  } catch {
    ElMessage.error('MPR失败')
  }
}

async function exec3DSegment() {
  if (!loaded.value) return
  try {
    const res = await ctSegment3d(withSession({
      low: segLow.value, high: segHigh.value,
      opening: segOpening.value, closing: segClosing.value,
      min_size: segMinSize.value,
      return_mask: true,
      z_preview: currentZ.value
    }))
    if (res.data?.segmented) {
      ElMessage.success(`三维分割完成! 掩码体素: ${res.data.mask_voxels?.toLocaleString()}`)
      await refreshSlice()
    }
  } catch {
    ElMessage.error('三维分割失败')
  }
}

async function execMetalDetect() {
  if (!loaded.value) return
  try {
    const res = await ctMetalDetect(withSession({
      hu_low: metalLow.value, hu_high: metalHigh.value,
      grad_threshold: metalGrad.value,
      opening: 1, closing: 2,
      min_size: metalMinSize.value,
      return_mask: true,
      z_preview: currentZ.value
    }))
    if (res.data?.detected) {
      const vox = res.data.metal_voxels || 0
      ElMessage.success(`伪影检测完成! 掩码体素: ${vox?.toLocaleString()}`)
      await refreshSlice()
    }
  } catch {
    ElMessage.error('金属伪影检测失败')
  }
}

async function generateMontage() {
  if (!loaded.value) return
  try {
    const res = await ctGetMontage(withSession({ ww: windowWidth.value, wl: windowLevel.value, n_slices: 9 }))
    montageImage.value = res.data?.montage || ''
    ElMessage.success('拼图生成完成')
  } catch {
    ElMessage.error('生成拼图失败')
  }
}

async function ctAiAnalyzeCall() {
  if (!loaded.value) return
  try {
    const res = await ctAiAnalyze(withSession({}))
    if (res.data) {
      ElMessage.success(`AI分析完成: ${res.data.assessment} (异常评分: ${(res.data.abnormality_score * 100).toFixed(1)}%)`)
    }
  } catch (e) {
    ElMessage.error('AI分析失败: ' + (e.message || '调用失败'))
  }
}

// AI 伪影分割结果
const artifactResult = ref(null)
const showArtifactResult = ref(false)

async function ctAiArtifactSegmentCall() {
  if (!loaded.value) {
    ElMessage.warning('请先加载CT数据')
    return
  }
  try {
    ElMessage.info('正在使用UNet3D深度学习模型进行伪影分割，请稍候...')
    const res = await ctAiArtifactSegment(withSession({ z: currentZ.value }))
    if (res.data) {
      artifactResult.value = res.data
      showArtifactResult.value = true
      const ratio = (res.data.artifact_ratio * 100).toFixed(2)
      const voxels = res.data.artifact_voxels.toLocaleString()
      ElMessage.success(`✅ AI伪影分割完成! 伪影体素: ${voxels} (占比${ratio}%)`)
    }
  } catch (e) {
    ElMessage.error('AI伪影分割失败: ' + (e.message || '调用失败'))
  }
}

async function fetchReport() {
  if (!loaded.value || !sessionId.value) {
    ElMessage.warning('请先加载CT数据')
    return
  }
  showReport.value = !showReport.value
  if (!showReport.value) return
  try {
    const res = await ctGenerateReport(withSession({}))
    reportData.value = res.data || res
    ElMessage.success('诊断报告生成完成')
  } catch (e) {
    const msg = e.response?.data?.message || e.message || '生成报告失败'
    ElMessage.error('报告生成失败: ' + msg)
  }
}

async function fetchStats() {
  if (!loaded.value || !sessionId.value) {
    ElMessage.warning('请先加载CT数据')
    return
  }
  showStats.value = !showStats.value
  if (!showStats.value) return
  try {
    const res = await ctGetStatistics(withSession({}))
    statsData.value = res.data || res
    ElMessage.success('统计分析完成')
  } catch (e) {
    const msg = e.response?.data?.message || e.message || '获取统计失败'
    ElMessage.error('统计分析失败: ' + msg)
  }
}

async function fetchAvailableFiles() {
  try {
    const res = await ctListDataFiles()
    console.log('CT可用数据文件:', res.data)
  } catch (e) {
    console.warn('获取文件列表失败(可忽略):', e.message)
  }
}

// ====== 生命期 ======
onMounted(async () => {
  await initPresets()
  await fetchAvailableFiles()
  // sessionId 由 load 端点动态创建, localStorage 中的旧值已失效
  localStorage.removeItem('ct_session_id')
  sessionId.value = ''
})

// ====== 监听 ======
watch(displayMode, () => refreshSlice())
watch(currentZ, () => refreshSlice())

// 自动刷新MPR
watch([mprZ, mprY, mprX], () => {
  if (showMpr.value) doMpr()
})
</script>

<style scoped>
.ct-workstation {
  min-height: 500px;
}

.ct-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  margin-bottom: 0;
}

.toolbar-title {
  font-weight: 600;
  font-size: 15px;
  margin-right: 12px;
}

.ct-layout {
  display: flex;
  gap: 0;
  position: relative;
}

.ct-control-panel {
  width: 320px;
  min-width: 320px;
  background: #f5f7fa;
  border-right: 1px solid #e4e7ed;
  padding: 12px;
  overflow-y: auto;
}

.panel-section h4 {
  margin: 0 0 8px 0;
  font-size: 13px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 4px;
}

.param-label {
  font-size: 11px;
  color: #909399;
  display: block;
  margin: 2px 0 6px;
}

.slice-info {
  text-align: center;
  font-size: 12px;
  color: #606266;
  margin-top: 4px;
}

.ct-main {
  flex: 1;
  padding: 12px;
  overflow-y: auto;
  min-height: 400px;
}

.ct-empty {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.ct-image-row {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.ct-image-card {
  flex: 1;
  background: #001830;
  border-radius: 8px;
  overflow: hidden;
}

.card-label {
  color: #ccc;
  font-size: 12px;
  padding: 6px 12px;
  background: rgba(0,0,0,0.3);
  text-align: center;
}

.image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
}

.ct-slice-img {
  max-width: 100%;
  max-height: 500px;
  object-fit: contain;
}

.compare-grid {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.compare-item {
  flex: 1;
  min-width: 140px;
  text-align: center;
}

.compare-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.compare-img {
  width: 100%;
  border-radius: 4px;
}

.histogram-img {
  width: 100%;
  max-width: 700px;
  display: block;
  margin: 0 auto;
}

.histogram-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-top: 12px;
}

.stat-item {
  display: flex;
  justify-content: space-between;
  padding: 4px 8px;
  background: #f5f7fa;
  border-radius: 4px;
  font-size: 12px;
}

.stat-l { color: #909399; }
.stat-v { color: #303133; font-weight: 600; }

.mpr-sliders {
  margin-bottom: 12px;
}

.mpr-slider-item {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 12px;
  color: #606266;
}

.mpr-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.mpr-item {
  text-align: center;
}

.mpr-label {
  font-size: 11px;
  color: #909399;
  margin-bottom: 4px;
}

.mpr-img {
  width: 100%;
  border-radius: 4px;
}

.file-picker-area {
  border: 2px dashed #dcdfe6;
  border-radius: 8px;
  padding: 16px;
  transition: border-color 0.3s;
}
.file-picker-area:hover {
  border-color: #409eff;
  background: #f5f7fa;
}
.selected-file-info {
  margin-top: 12px;
}
.manual-path-row {
  display: flex;
  align-items: center;
}

.slide-enter-active, .slide-leave-active {
  transition: all 0.3s ease;
}
.slide-enter-from, .slide-leave-to {
  width: 0;
  min-width: 0;
  opacity: 0;
  padding: 0;
  overflow: hidden;
}

/* 加载对话框样式 */
.load-mode-select {
  margin-bottom: 12px;
}

.load-mode-radio {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.load-mode-radio .el-radio-button {
  flex: 1;
}

.load-mode-radio .el-radio-button__inner {
  font-size: 12px;
  padding: 8px 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.file-radio-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
}

.file-radio {
  width: 100%;
  margin-right: 0;
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  transition: border-color 0.2s;
}

.file-radio:hover {
  border-color: #409eff;
}

.file-radio-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.file-radio-name {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  display: flex;
  align-items: center;
  gap: 4px;
}

.file-radio-desc {
  font-size: 11px;
  color: #909399;
  margin-left: 20px;
}
</style>

