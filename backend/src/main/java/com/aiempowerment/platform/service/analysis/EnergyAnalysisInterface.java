package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.model.dto.analysis.*;

import java.util.List;

/**
 * 能源AI分析接口 - 能耗预测、设备异常检测、节能优化
 * 所有返回值均为类型安全的 DTO，不再使用 {@code Map<String, Object>}
 */
public interface EnergyAnalysisInterface {

    /** 能耗趋势预测（未来N天） */
    List<EnergyPredictionDTO> predictEnergyConsumption(int days);

    /** 设备异常检测 */
    List<DeviceAnomalyDTO> detectDeviceAnomalies();

    /** 节能优化建议 */
    List<OptimizationTipDTO> getEnergyOptimizationTips();

    /** 能源设备详细分析（增强版） */
    EnergyDeviceAnalysisDTO getEnergyDeviceAnalysis();

    /** 能源AI摘要报告（增强版） */
    EnergySummaryReportDTO getEnergySummaryReport();
}
