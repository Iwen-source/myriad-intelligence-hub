package com.aiempowerment.platform.service.analysis;

import java.util.List;
import java.util.Map;

/**
 * 交通AI分析接口 - 拥堵预测、路线优化、交通异常检测、场景模拟
 */
public interface TrafficAnalysisInterface {

    /** 拥堵预测 */
    List<Map<String, Object>> predictCongestion(String date);

    /** 路线优化建议 */
    List<Map<String, Object>> getRouteOptimizationTips();

    /** 多日拥堵预测日历 */
    List<Map<String, Object>> predictCongestionCalendar(int days);

    /** 交通仿真沙盘 — what-if 场景分析 */
    Map<String, Object> simulateWhatIf(Long sectionId, Map<String, Object> scenario);

    /** 全路网实时热力图数据 */
    List<Map<String, Object>> getTrafficHeatmap();

    /** AI智能出行建议（最佳出行时段） */
    Map<String, Object> getSmartDepartureTips();

    /** 事故影响分析 — 级联效应 */
    Map<String, Object> analyzeAccidentImpact(Long sectionId);

    /** 天气-交通关联分析 */
    List<Map<String, Object>> analyzeWeatherTrafficCorrelation();

    /** 路段异常流量检测 */
    List<Map<String, Object>> detectTrafficAnomalies();
}