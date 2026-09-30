package com.aiempowerment.platform.controller;
import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.dto.vo.AccidentRiskVO;
import com.aiempowerment.platform.model.entity.TrafficRoadSection;
import com.aiempowerment.platform.model.entity.TrafficFlowRecord;
import com.aiempowerment.platform.service.TrafficService;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.data.domain.PageRequest;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.util.*;

/**
 * 交通管理控制器 - AI应用场景模块
 * 🆕 V4: 新增事故风险预测 (真实XGBoost模型)
 */
@Slf4j
@RestController
@RequestMapping("/traffic")
@RequiredArgsConstructor
public class TrafficController {

    private final TrafficService trafficService;
    private final AIAnalysisService aiAnalysisService;
    private final PythonMlClient pythonMlClient;

    // ===== 路段管理 =====
    @GetMapping("/sections")
    public ApiResponse<?> getAllSections() {
        return ApiResponse.success(trafficService.findAllSections());
    }

    @PostMapping("/sections")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> saveSection(@RequestBody TrafficRoadSection section) {
        return ApiResponse.success(trafficService.saveSection(section));
    }

    @DeleteMapping("/sections/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deleteSection(@PathVariable Long id) {
        trafficService.deleteSection(id);
        return ApiResponse.success("删除成功");
    }

    // ===== 流量数据 =====
    @GetMapping("/flow")
    public ApiResponse<?> getFlow(@RequestParam(required = false) Long sectionId) {
        if (sectionId != null) {
            return ApiResponse.success(trafficService.findFlowRecordsBySectionId(sectionId));
        }
        return ApiResponse.success(trafficService.findAllFlowRecords());
    }

    @PostMapping("/flow")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> saveFlow(@RequestBody TrafficFlowRecord record) {
        return ApiResponse.success(trafficService.saveFlowRecord(record));
    }

    // ===== AI分析 =====
    @GetMapping("/analysis/congestion")
    public ApiResponse<?> predictCongestion(@RequestParam(required = false) String date) {
        return ApiResponse.success(aiAnalysisService.predictCongestion(date));
    }

    @GetMapping("/analysis/routes")
    public ApiResponse<?> getRouteOptimizationTips() {
        return ApiResponse.success(aiAnalysisService.getRouteOptimizationTips());
    }

    // ===== 新增: 高级AI交通分析接口 =====

    /** 多日拥堵预测日历 */
    @GetMapping("/analysis/prediction-calendar")
    public ApiResponse<?> predictCongestionCalendar(@RequestParam(defaultValue = "7") int days) {
        return ApiResponse.success(aiAnalysisService.predictCongestionCalendar(days));
    }

    /** AI交通仿真实时热力图 */
    @GetMapping("/analysis/heatmap")
    public ApiResponse<?> getTrafficHeatmap() {
        return ApiResponse.success(aiAnalysisService.getTrafficHeatmap());
    }

    /** 智能出行建议 */
    @GetMapping("/analysis/departure-tips")
    public ApiResponse<?> getSmartDepartureTips() {
        return ApiResponse.success(aiAnalysisService.getSmartDepartureTips());
    }

    /** 交通事故影响分析 */
    @GetMapping("/analysis/accident-impact")
    public ApiResponse<?> analyzeAccidentImpact(@RequestParam Long sectionId) {
        return ApiResponse.success(aiAnalysisService.analyzeAccidentImpact(sectionId));
    }

    /** 天气-交通关联分析 */
    @GetMapping("/analysis/weather-impact")
    public ApiResponse<?> analyzeWeatherTrafficCorrelation() {
        return ApiResponse.success(aiAnalysisService.analyzeWeatherTrafficCorrelation());
    }

    /** 交通异常检测 */
    @GetMapping("/analysis/anomalies")
    public ApiResponse<?> detectTrafficAnomalies() {
        return ApiResponse.success(aiAnalysisService.detectTrafficAnomalies());
    }

    /** 交通仿真沙盘 — what-if */
    @PostMapping("/analysis/what-if")
    public ApiResponse<?> simulateWhatIf(@RequestParam Long sectionId, @RequestBody Map<String, Object> scenario) {
        return ApiResponse.success(aiAnalysisService.simulateWhatIf(sectionId, scenario));
    }

    // ===== 分页查询 =====
    @GetMapping("/flow-records/page")
    public ApiResponse<?> getFlowRecordsByPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) Long sectionId) {
        Page<?> result = trafficService.findFlowRecordsByPage(page, size, sectionId);
        return ApiResponse.success(result);
    }

    // ===== 拥堵统计 =====
    @GetMapping("/congestion-stats")
    public ApiResponse<?> getCongestionStats() {
        return ApiResponse.success(trafficService.getCongestionStats());
    }

    // ===== 概览 =====
    @GetMapping("/overview")
    public ApiResponse<?> getOverview() {
        return ApiResponse.success(trafficService.getOverview());
    }

    @GetMapping("/flow-data")
    public ApiResponse<?> getFlowData() {
        return ApiResponse.success(trafficService.getFlowData(LocalDate.now()));
    }

    // ===== 🆕 V4 AI增强: 事故风险实时预测 (XGBoost模型) =====
    @PostMapping("/analysis/accident-risk")
    public ApiResponse<?> predictAccidentRisk(@RequestBody Map<String, Object> trafficParams) {
        // Fill defaults
        if (!trafficParams.containsKey("hour")) trafficParams.put("hour", LocalDate.now().getDayOfMonth() % 24);
        if (!trafficParams.containsKey("day_of_week")) trafficParams.put("day_of_week", LocalDate.now().getDayOfWeek().getValue() % 7);
        if (!trafficParams.containsKey("weather_code")) trafficParams.put("weather_code", 0);
        if (!trafficParams.containsKey("traffic_volume")) trafficParams.put("traffic_volume", 1000);
        if (!trafficParams.containsKey("speed_limit")) trafficParams.put("speed_limit", 60);
        if (!trafficParams.containsKey("congestion_index")) trafficParams.put("congestion_index", 30);
        if (!trafficParams.containsKey("visibility_km")) trafficParams.put("visibility_km", 10);
        if (!trafficParams.containsKey("lanes")) trafficParams.put("lanes", 4);
        if (!trafficParams.containsKey("road_type")) trafficParams.put("road_type", 1);

        JsonNode result = pythonMlClient.trafficAccidentRiskPredict(trafficParams);
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }

        // Fallback heuristic
        int hour = ((Number) trafficParams.getOrDefault("hour", 12)).intValue();
        int weather = ((Number) trafficParams.getOrDefault("weather_code", 0)).intValue();
        int volume = ((Number) trafficParams.getOrDefault("traffic_volume", 1000)).intValue();
        boolean isNight = hour >= 22 || hour <= 5;
        double prob = Math.min(0.8, Math.max(0.01,
                0.05 + (isNight ? 0.15 : 0) + (weather >= 4 ? 0.25 : weather >= 2 ? 0.08 : 0)
                + Math.log1p(volume) / 30.0));
        String riskLevel = prob < 0.2 ? "低风险 🟢" : prob < 0.4 ? "中等风险 🟡"
                : prob < 0.6 ? "高风险 🟠" : "危急 🔴";

        AccidentRiskVO fallback = new AccidentRiskVO(
                Math.round(prob * 10000.0) / 10000.0,
                Math.round(prob * 1000.0) / 10.0,
                riskLevel,
                "注意保持安全车距"
        );
        return ApiResponse.success(fallback);
    }
}
