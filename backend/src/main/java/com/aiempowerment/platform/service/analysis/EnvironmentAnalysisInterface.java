package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.model.dto.analysis.*;

import java.util.List;
import java.util.Map;

/**
 * 环境AI分析接口 - AQI预测、污染预警、健康评估、环境报告
 * 所有返回值均为类型安全的 DTO
 */
public interface EnvironmentAnalysisInterface {

    /** AQI趋势预测 */
    List<AirQualityPredictionDTO> predictAirQuality(int days);

    /** 污染预警分析 */
    List<PollutionAlertDTO> getPollutionAlerts();

    /** 环境健康指数（综合评分） */
    Map<String, Object> getEnvironmentHealthIndex();

    /** 污染源成分分析 */
    List<Map<String, Object>> getPollutionSourceAnalysis();

    /** 季节性趋势分析 */
    Map<String, Object> getSeasonalTrendAnalysis();

    /** 健康影响评估 */
    Map<String, Object> getHealthImpactAssessment();

    /** 跨监测点相关性分析 */
    List<Map<String, Object>> getCrossPointCorrelation();

    /** 污染物分解雷达图数据 */
    Map<String, Object> getPollutantBreakdown(Long pointId);

    /** AI智能建议 */
    List<Map<String, Object>> getSmartRecommendations();

    /** 异常波动检测 */
    List<Map<String, Object>> getEnvironmentalAnomalyDetection();

    Map<String, Object> getEnvironmentAiReport();

    List<Map<String, Object>> getMultiFactorPrediction();

    Map<String, Object> getHealthExposureRisk();

    /** 基于当前数据的极端天气自动分类 */
    Map<String, Object> classifyCurrentExtremeWeather();
}
