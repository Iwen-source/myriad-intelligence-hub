package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.dto.vo.ExtremeWeatherVO;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import com.aiempowerment.platform.model.entity.AirQualityRecord;
import com.aiempowerment.platform.service.EnvironmentService;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 环境监测控制器 - AI应用场景模块
 * 🆕 V4: 新增极端天气事件分类 (真实RandomForest模型)
 */
@Slf4j
@RestController
@RequestMapping("/environment")
@RequiredArgsConstructor
public class EnvironmentController {

    private final EnvironmentService environmentService;
    private final AIAnalysisService aiAnalysisService;
    private final PythonMlClient pythonMlClient;

    // ===== 监测点 CRUD =====
    @GetMapping("/points")
    public ApiResponse<?> getAllPoints() {
        return ApiResponse.success(environmentService.findAllPoints());
    }

    @GetMapping("/points/{id}")
    public ApiResponse<?> getPoint(@PathVariable Long id) {
        return ApiResponse.success(environmentService.findPointById(id));
    }

    @PostMapping("/points")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> savePoint(@RequestBody EnvironmentMonitorPoint point) {
        return ApiResponse.success(environmentService.savePoint(point));
    }

    @DeleteMapping("/points/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deletePoint(@PathVariable Long id) {
        environmentService.deletePoint(id);
        return ApiResponse.success("删除成功");
    }

    // ===== 监测数据 =====
    @GetMapping("/data")
    public ApiResponse<?> getData(@RequestParam(required = false) Long pointId) {
        if (pointId != null) {
            return ApiResponse.success(environmentService.findRecordsByPointId(pointId));
        }
        return ApiResponse.success(environmentService.findAllRecords());
    }

    @PostMapping("/data")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> saveData(@RequestBody AirQualityRecord record) {
        return ApiResponse.success(environmentService.saveAirQualityRecord(record));
    }

    // ===== AI 分析 =====
    @GetMapping("/analysis/prediction")
    public ApiResponse<?> predictAirQuality(@RequestParam(defaultValue = "7") int days) {
        return ApiResponse.success(aiAnalysisService.predictAirQuality(days));
    }

    @GetMapping("/analysis/alerts")
    public ApiResponse<?> getAlerts() {
        return ApiResponse.success(aiAnalysisService.getPollutionAlerts());
    }

    // ===== 新增 AI 环境分析 =====

    @GetMapping("/analysis/health-index")
    public ApiResponse<?> getEnvironmentHealthIndex() {
        return ApiResponse.success(aiAnalysisService.getEnvironmentHealthIndex());
    }

    @GetMapping("/analysis/pollution-source")
    public ApiResponse<?> getPollutionSourceAnalysis() {
        return ApiResponse.success(aiAnalysisService.getPollutionSourceAnalysis());
    }

    @GetMapping("/analysis/seasonal-trend")
    public ApiResponse<?> getSeasonalTrendAnalysis() {
        return ApiResponse.success(aiAnalysisService.getSeasonalTrendAnalysis());
    }

    @GetMapping("/analysis/health-impact")
    public ApiResponse<?> getHealthImpactAssessment() {
        return ApiResponse.success(aiAnalysisService.getHealthImpactAssessment());
    }

    @GetMapping("/analysis/correlation")
    public ApiResponse<?> getCrossPointCorrelation() {
        return ApiResponse.success(aiAnalysisService.getCrossPointCorrelation());
    }

    @GetMapping("/analysis/pollutant-breakdown")
    public ApiResponse<?> getPollutantBreakdown(@RequestParam(required = false) Long pointId) {
        return ApiResponse.success(aiAnalysisService.getPollutantBreakdown(pointId));
    }

    @GetMapping("/analysis/recommendations")
    public ApiResponse<?> getSmartRecommendations() {
        return ApiResponse.success(aiAnalysisService.getSmartRecommendations());
    }

    @GetMapping("/analysis/anomalies")
    public ApiResponse<?> getEnvironmentalAnomalyDetection() {
        return ApiResponse.success(aiAnalysisService.getEnvironmentalAnomalyDetection());
    }

    // ===== 新增：创新 AI 接口 =====

    @GetMapping("/analysis/ai-report")
    public ApiResponse<?> getEnvironmentAiReport() {
        return ApiResponse.success(aiAnalysisService.getEnvironmentAiReport());
    }

    @GetMapping("/analysis/multi-factor-prediction")
    public ApiResponse<?> getMultiFactorPrediction() {
        return ApiResponse.success(aiAnalysisService.getMultiFactorPrediction());
    }

    @GetMapping("/analysis/exposure-risk")
    public ApiResponse<?> getHealthExposureRisk() {
        return ApiResponse.success(aiAnalysisService.getHealthExposureRisk());
    }

    // ===== 统计 =====
    @GetMapping("/summary")
    public ApiResponse<?> getSummary() {
        return ApiResponse.success(environmentService.getSummary());
    }

    @GetMapping("/statistics")
    public ApiResponse<?> getStatistics() {
        return ApiResponse.success(environmentService.getStatistics());
    }

    // ===== 🆕 V4 AI增强: 极端天气事件分类 (真实RandomForest模型) =====

    /**
     * 自动分析当前环境的极端天气分类（基于最新监测数据）
     */
    @GetMapping("/analysis/extreme-weather/current")
    public ApiResponse<?> getCurrentExtremeWeather() {
        return ApiResponse.success(aiAnalysisService.classifyCurrentExtremeWeather());
    }

    /**
     * 用户指定参数进行极端天气分类
     */
    @PostMapping("/analysis/extreme-weather")
    public ApiResponse<?> classifyExtremeWeather(@RequestBody Map<String, Object> weatherParams) {
        // Fill defaults
        if (!weatherParams.containsKey("pm25")) weatherParams.put("pm25", 50);
        if (!weatherParams.containsKey("pm10")) weatherParams.put("pm10", 80);
        if (!weatherParams.containsKey("o3")) weatherParams.put("o3", 80);
        if (!weatherParams.containsKey("temperature")) weatherParams.put("temperature", 20);
        if (!weatherParams.containsKey("humidity")) weatherParams.put("humidity", 60);
        if (!weatherParams.containsKey("wind_speed")) weatherParams.put("wind_speed", 5);
        if (!weatherParams.containsKey("season")) weatherParams.put("season", 1);

        JsonNode result = pythonMlClient.environmentExtremeWeather(weatherParams);
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }

        // Fallback rule-based
        double pm25 = ((Number) weatherParams.getOrDefault("pm25", 50)).doubleValue();
        double temp = ((Number) weatherParams.getOrDefault("temperature", 20)).doubleValue();
        String severity = "normal";
        if (pm25 > 250) severity = "warning";
        else if (temp > 38 || pm25 > 150) severity = "advisory";

        ExtremeWeatherVO fallback = new ExtremeWeatherVO(
                severity,
                0.6,
                severity.equals("normal") ? "天气状况正常" : "建议关注"
        );
        return ApiResponse.success(fallback);
    }
}
