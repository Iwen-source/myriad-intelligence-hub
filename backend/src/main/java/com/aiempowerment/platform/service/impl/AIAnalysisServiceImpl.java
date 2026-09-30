package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.config.AiModelClient;
import com.aiempowerment.platform.model.dto.analysis.*;
import com.aiempowerment.platform.model.entity.*;
import com.aiempowerment.platform.repository.*;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.aiempowerment.platform.service.analysis.EnergyAnalysisService;
import com.aiempowerment.platform.service.analysis.EnvironmentAnalysisService;
import com.aiempowerment.platform.service.analysis.FinanceAnalysisService;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;

import java.util.concurrent.CompletableFuture;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * AI智能分析引擎实现
 *
 * 同时支持两种模式:
 * 1. 真实AI模式: 配置了 DEEPSEEK_API_KEY 后，文本类分析自动调用大模型生成
 * 2. 模拟模式: 未配置API时，基于统计数据和规则引擎进行分析
 *
 * 所有输出中带 isAiGenerated: true 的为真实AI生成结果，false 为模拟/规则分析结果
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AIAnalysisServiceImpl implements AIAnalysisService {

    private final EnergyConsumptionRecordRepository consumptionRepository;
    private final EnergyDeviceRepository energyDeviceRepository;
    private final MedicalDiagnosisResultRepository diagnosisRepository;
    private final MedicalPatientRepository patientRepository;
    private final AirQualityRecordRepository airQualityRepository;
    private final FinanceTransactionRepository financeTransactionRepository;
    private final RiskAlertRuleRepository riskAlertRuleRepository;
    private final TrafficFlowRecordRepository trafficFlowRepository;
    private final TrafficRoadSectionRepository trafficRoadSectionRepository;
    private final EnvironmentMonitorPointRepository envPointRepository;
    private final AiModelClient aiModelClient;
    private final PythonMlClient pythonMlClient;

    // 领域分析服务（拆分自本胖服务）
    private final EnergyAnalysisService energyAnalysisService;
    private final EnvironmentAnalysisService environmentAnalysisService;
    private final FinanceAnalysisService financeAnalysisService;

    // ======================== 能源分析 ========================

    @Override
    public List<EnergyPredictionDTO> predictEnergyConsumption(int days) {
        return energyAnalysisService.predictEnergyConsumption(days);
    }

    @Override
    public List<DeviceAnomalyDTO> detectDeviceAnomalies() {
        return energyAnalysisService.detectDeviceAnomalies();
    }

    @Override
    @SuppressWarnings("unchecked")
    public List<OptimizationTipDTO> getEnergyOptimizationTips() {
        // 尝试AI生成节能优化建议
        long deviceCount = energyDeviceRepository.count();
        long consumptionCount = consumptionRepository.count();
        String context = String.format("共管理%d台设备，能耗记录%d条。请提供5条具体节能建议。", deviceCount, consumptionCount);
        List<Map<String, Object>> aiSuggestions = aiGenerateSuggestions(
            "你是一位能源管理专家。基于以下数据，提供5条具体的节能优化建议。" +
            "每条建议包含：suggestion(建议内容)、expectedSaving(预期节能百分比数字)、priority(高/中/低)、category(设备/行为/策略)。" +
            "返回JSON格式：{\"suggestions\":[{\"suggestion\":\"...\",\"expectedSaving\":15,\"priority\":\"高\",\"category\":\"设备\"}]}",
            context);
        if (aiSuggestions != null) {
            List<OptimizationTipDTO> dtos = new ArrayList<>();
            for (int i = 0; i < aiSuggestions.size(); i++) {
                Map<String, Object> s = aiSuggestions.get(i);
                dtos.add(new OptimizationTipDTO(
                    "ai-" + i,
                    (String) s.getOrDefault("suggestion", "建议"),
                    (String) s.getOrDefault("description", ""),
                    (String) s.getOrDefault("priority", "中"),
                    (String) s.getOrDefault("category", "节能"),
                    true
                ));
            }
            return dtos;
        }
        return energyAnalysisService.getEnergyOptimizationTips();
    }

    @Override
    public EnergyDeviceAnalysisDTO getEnergyDeviceAnalysis() {
        return energyAnalysisService.getEnergyDeviceAnalysis();
    }

    @Override
    public EnergySummaryReportDTO getEnergySummaryReport() {
        return energyAnalysisService.getEnergySummaryReport();
    }

    // ======================== 医疗AI分析 ========================

    /**
     * 医疗症状分析 — 改造版：调用 Python ML 模型
     * 替换了原规则+随机数的伪 AI 逻辑
     */
    @Override
    public List<Map<String, Object>> analyzeSymptomDisease(String symptoms) {
        List<Map<String, Object>> result = new ArrayList<>();
        if (symptoms != null && !symptoms.isEmpty()) {
            // 调用 Python ML 医疗诊断模型
            JsonNode mlResult = pythonMlClient.predictMedical(symptoms);
            if (mlResult != null && "success".equals(mlResult.path("status").asText())) {
                String disease = mlResult.path("disease").asText();
                double confidence = mlResult.path("confidence").asDouble();
                String department = mlResult.path("department").asText();
                String severity = mlResult.path("severity").asText();
                String suggestions = mlResult.path("suggestions").asText();

                String[] parts = symptoms.split("[，,;；]");
                for (String s : parts) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("symptom", s.trim());
                    item.put("possibleDisease", disease);
                    item.put("probability", (int) Math.round(confidence * 100));
                    item.put("department", department);
                    item.put("severity", severity);
                    item.put("suggestions", suggestions);
                    item.put("isMlGenerated", true);
                    result.add(item);
                }
            } else {
                // Fallback: 原规则逻辑
                String[] parts = symptoms.split("[，,;；]");
                for (String s : parts) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("symptom", s.trim());
                    item.put("possibleDisease", s.contains("发热") || s.contains("咳嗽") ? "上呼吸道感染" :
                            s.contains("头痛") ? "偏头痛" : s.contains("腹痛") || s.contains("胃") ? "胃炎" :
                            s.contains("皮疹") ? "过敏性皮炎" : "待进一步检查");
                    item.put("probability", 60 + new Random(s.hashCode()).nextInt(35));
                    item.put("isMlGenerated", false);
                    result.add(item);
                }
            }
        }
        return result.isEmpty() ? List.of(Map.of("message", "请输入有效症状描述")) : result;
    }

    @Override
    public List<Map<String, Object>> findSimilarCases(Long patientId) {
        List<MedicalPatient> allPatients = patientRepository.findAll();
        List<Map<String, Object>> cases = new ArrayList<>();

        // 获取当前患者信息
        MedicalPatient currentPatient = null;
        if (patientId != null) {
            currentPatient = patientRepository.findById(String.valueOf(patientId)).orElse(null);
        }

        // 如果有关键词，尝试用 ML 语义搜索
        boolean mlUsed = false;
        if (currentPatient != null && currentPatient.getSymptoms() != null && !currentPatient.getSymptoms().isEmpty()) {
            JsonNode searchResult = pythonMlClient.semanticSearch(currentPatient.getSymptoms());
            if (searchResult != null && "success".equals(searchResult.path("status").asText())) {
                JsonNode records = searchResult.path("records");
                if (records.isArray()) {
                    for (JsonNode rec : records) {
                        Map<String, Object> item = new LinkedHashMap<>();
                        String recordId = rec.path("recordId").asText();
                        item.put("patientId", recordId);
                        item.put("name", "相似病历");
                        item.put("symptoms", rec.path("summary").asText());
                        item.put("similarity", (int) Math.round(rec.path("relevanceScore").asDouble() * 100));
                        item.put("isMlGenerated", true);
                        cases.add(item);
                    }
                    mlUsed = true;
                }
            }
        }

        // 如果 ML 搜索未返回结果，使用原逻辑（基于 DB 中的患者数据）
        if (!mlUsed) {
            for (MedicalPatient p : allPatients) {
                if (!p.getPatientId().equals(patientId != null ? String.valueOf(patientId) : "")) {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("patientId", p.getPatientId());
                    item.put("name", p.getName());
                    item.put("symptoms", p.getSymptoms());
                    // 用症状文本的哈希做初始相似度
                    int sim = 50;
                    if (currentPatient != null && currentPatient.getSymptoms() != null && p.getSymptoms() != null) {
                        String[] curSyms = currentPatient.getSymptoms().split("[，,;；]");
                        String[] pSyms = p.getSymptoms().split("[，,;；]");
                        long common = Arrays.stream(curSyms).filter(s -> Arrays.stream(pSyms).anyMatch(ps -> ps.contains(s))).count();
                        sim = Math.min(95, 50 + (int) common * 10);
                    }
                    item.put("similarity", sim);
                    item.put("isMlGenerated", false);
                    cases.add(item);
                }
            }
        }

        cases.sort((a, b) -> Integer.compare((Integer) b.get("similarity"), (Integer) a.get("similarity")));
        return cases.stream().limit(5).collect(Collectors.toList());
    }

    @Override
    public Map<String, Object> analyzeDiagnosisTrend() {
        List<MedicalDiagnosisResult> results = diagnosisRepository.findAll();
        Map<String, Long> diagnosisCount = results.stream()
            .filter(r -> r.getDiagnosisResult() != null)
            .collect(Collectors.groupingBy(MedicalDiagnosisResult::getDiagnosisResult, Collectors.counting()));
        Map<String, Object> trend = new LinkedHashMap<>();
        trend.put("totalDiagnoses", results.size());
        trend.put("uniqueDiagnoses", diagnosisCount.size());
        trend.put("topDiagnoses", diagnosisCount.entrySet().stream()
            .sorted(Map.Entry.<String, Long>comparingByValue().reversed()).limit(5)
            .collect(Collectors.toList()));
        trend.put("analysisTime", LocalDateTime.now().toString());
        return trend;
    }

    // ======================== 环境分析 ========================

    @Override
    public List<AirQualityPredictionDTO> predictAirQuality(int days) {
        return environmentAnalysisService.predictAirQuality(days);
    }

    @Override
    public List<PollutionAlertDTO> getPollutionAlerts() {
        return environmentAnalysisService.getPollutionAlerts();
    }

    @Override
    public Map<String, Object> getEnvironmentHealthIndex() {
        return environmentAnalysisService.getEnvironmentHealthIndex();
    }

    @Override
    public List<Map<String, Object>> getPollutionSourceAnalysis() {
        return environmentAnalysisService.getPollutionSourceAnalysis();
    }

    @Override
    public Map<String, Object> getSeasonalTrendAnalysis() {
        // 尝试AI生成季节性趋势分析
        long recordCount = airQualityRepository.count();
        long pointCount = envPointRepository.count();
        String context = String.format("空气质量监测点%d个，历史记录%d条。请分析当前环境趋势。", pointCount, recordCount);
        Map<String, Object> aiResult = aiGenerateReport(
            "你是一位环境数据分析专家。基于以下数据生成季节性趋势分析报告。" +
            "报告包含：currentSeason(当前季节)、overallTrend(总体趋势描述)、" +
            "keyFindings(关键发现的数组)、riskFactors(风险因素的数组)。" +
            "返回JSON格式。",
            context);
        if (aiResult != null) return aiResult;
        return environmentAnalysisService.getSeasonalTrendAnalysis();
    }

    @Override
    public Map<String, Object> getHealthImpactAssessment() {
        return environmentAnalysisService.getHealthImpactAssessment();
    }

    @Override
    public List<Map<String, Object>> getCrossPointCorrelation() {
        return environmentAnalysisService.getCrossPointCorrelation();
    }

    @Override
    public Map<String, Object> getPollutantBreakdown(Long pointId) {
        return environmentAnalysisService.getPollutantBreakdown(pointId);
    }

    @Override
    public List<Map<String, Object>> getSmartRecommendations() {
        return environmentAnalysisService.getSmartRecommendations();
    }

    @Override
    public List<Map<String, Object>> getEnvironmentalAnomalyDetection() {
        return environmentAnalysisService.getEnvironmentalAnomalyDetection();
    }

    @Override
    public Map<String, Object> getEnvironmentAiReport() {
        return environmentAnalysisService.getEnvironmentAiReport();
    }

    @Override
    public List<Map<String, Object>> getMultiFactorPrediction() {
        return environmentAnalysisService.getMultiFactorPrediction();
    }

    @Override
    public Map<String, Object> getHealthExposureRisk() {
        return environmentAnalysisService.getHealthExposureRisk();
    }

    @Override
    public Map<String, Object> classifyCurrentExtremeWeather() {
        return environmentAnalysisService.classifyCurrentExtremeWeather();
    }

    // ===== Finance core methods =====

    @Override
    public TransactionRiskDTO evaluateTransactionRisk(Long transactionId) {
        return financeAnalysisService.evaluateTransactionRisk(transactionId);
    }

    @Override
    public List<RuleHitDTO> analyzeRuleHits() {
        return financeAnalysisService.analyzeRuleHits();
    }

    @Override
    public List<TrendPredictionDTO> predictTransactionTrend(int days) {
        return financeAnalysisService.predictTransactionTrend(days);
    }

    @Override
    public List<UserBehaviorProfileDTO> analyzeUserBehaviorProfiles() {
        return financeAnalysisService.analyzeUserBehaviorProfiles();
    }

    @Override
    public List<SuspiciousTransactionDTO> detectSuspiciousTransactions() {
        return financeAnalysisService.detectSuspiciousTransactions();
    }

    @Override
    public MultiDimensionalRiskDTO getMultiDimensionalRisk(Long transactionId) {
        return financeAnalysisService.getMultiDimensionalRisk(transactionId);
    }

    @Override
    public TransactionNetworkDTO getTransactionNetworkAnalysis() {
        return financeAnalysisService.getTransactionNetworkAnalysis();
    }

    @Override
    public FinanceReportDTO generateRiskAssessmentReport() {
        // 尝试AI生成风险评估报告
        long transactionCount = financeTransactionRepository.count();
        long ruleCount = riskAlertRuleRepository.count();
        String context = String.format("交易记录共%d条，风控规则%d条。请进行风险评估分析。", transactionCount, ruleCount);
        @SuppressWarnings("unchecked")
        Map<String, Object> aiResult = aiGenerateReport(
            "你是一位金融风控专家。基于以下数据生成风险评估报告。" +
            "报告包含：overallRiskLevel(总体风险等级 低/中/高)、totalTransactions(总交易数)、" +
            "highRiskCount(高风险交易数)、mediumRiskCount(中风险交易数)、" +
            "riskFactors(主要风险因素描述)、recommendations(风控建议的数组)。" +
            "返回JSON格式。",
            context);
        if (aiResult != null) {
            FinanceReportDTO fallback = new FinanceReportDTO();
            fallback.setReportTitle("金融风控AI评估报告");
            fallback.setTotalTransactions(((Number) aiResult.getOrDefault("totalTransactions", 0)).longValue());
            fallback.setReportText("🤖 AI 风控状态摘要\n总交易：" + ((Number) aiResult.getOrDefault("totalTransactions", 0)).longValue() + " 笔\n风险等级：" + aiResult.getOrDefault("overallRiskLevel", "-") + "\n" + aiResult.getOrDefault("recommendations", "正在分析..."));
            return fallback;
        }
        return financeAnalysisService.generateRiskAssessmentReport();
    }

    @Override
    public List<RiskAlertDTO> getRealTimeRiskAlerts() {
        return financeAnalysisService.getRealTimeRiskAlerts();
    }

    @Override
    public List<RiskTrendDTO> getRiskTrendData() {
        return financeAnalysisService.getRiskTrendData();
    }

    // ======================== 交通分析 ========================

    @Override
    public List<Map<String, Object>> predictCongestion(String date) {
        // V5: 使用 XGBoost 拥堵预测模型 (traffic_congestion_model.pkl)
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        if (sections.isEmpty()) return new ArrayList<>();
        TrafficRoadSection sec = sections.get(0);

        int dayOfWeek = LocalDate.now().getDayOfWeek().getValue();
        int month = LocalDate.now().getMonthValue();
        int isWeekend = (dayOfWeek >= 6) ? 1 : 0;
        int lanes = sec.getLanes() != null ? sec.getLanes() : 4;
        int speedLimit = sec.getSpeedLimit() != null ? sec.getSpeedLimit() : 60;
        int roadType = sec.getRoadType() != null ?
                ("快速路".equals(sec.getRoadType()) ? 2 : "主干道".equals(sec.getRoadType()) ? 1 : 0) : 0;

        JsonNode v5Result = pythonMlClient.v5TrafficHourlyForecast(
                dayOfWeek, month, isWeekend, 0, 0, 20, 50, lanes, speedLimit, roadType);

        List<Map<String, Object>> predictions = new ArrayList<>();
        if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
            JsonNode hourlyData = v5Result.path("hourly_data");
            for (JsonNode hd : hourlyData) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("hour", String.format("%02d:00", hd.path("hour").asInt()));
                item.put("estimatedFlow", hd.path("estimatedFlow").asInt());
                item.put("estimatedSpeed", hd.path("estimatedSpeed").asDouble());
                item.put("congestionLevel", hd.path("congestionLevel").asText());
                item.put("modelName", hd.has("congestionIndex") ?"xgb_v5_congestion(R²=0.99)":"v2_fallback");
                item.put("isMlGenerated", true);
                predictions.add(item);
            }
            return predictions;
        }

        // Fallback: V2 模型
        int sectionCapacity = lanes * 600;
        JsonNode v2Result = pythonMlClient.trafficHourlyFlow(
                dayOfWeek, isWeekend, 0, 1, 0, sectionCapacity, lanes, speedLimit, roadType);
        if (v2Result != null && "success".equals(v2Result.path("status").asText())) {
            for (JsonNode hd : v2Result.path("hourly_data")) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("hour", String.format("%02d:00", hd.path("hour").asInt()));
                item.put("estimatedFlow", hd.path("estimatedFlow").asInt());
                item.put("estimatedSpeed", hd.path("estimatedSpeed").asDouble());
                item.put("congestionLevel", hd.path("congestionLevel").asText());
                item.put("isMlGenerated", true);
                predictions.add(item);
            }
            return predictions;
        }

        // Last fallback: 数据库统计
        LocalDate queryDate = date != null ? LocalDate.parse(date) : LocalDate.now();
        List<TrafficFlowRecord> recentRecords = trafficFlowRepository.findByRecordDate(queryDate);
        for (int hour = 0; hour < 24; hour++) {
            int h = hour;
            double avgFlow = recentRecords.stream()
                    .filter(r -> r.getRecordHour() == h && r.getFlowCount() != null)
                    .mapToInt(TrafficFlowRecord::getFlowCount)
                    .average().orElse(500);
            double avgSpeed = recentRecords.stream()
                    .filter(r -> r.getRecordHour() == h && r.getAvgSpeed() != null)
                    .mapToDouble(TrafficFlowRecord::getAvgSpeed)
                    .average().orElse(40);
            double cr = avgFlow / (avgSpeed + 1);
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("hour", String.format("%02d:00", hour));
            item.put("estimatedFlow", (int) Math.round(avgFlow));
            item.put("estimatedSpeed", Math.round(avgSpeed * 10.0) / 10.0);
            item.put("congestionLevel", cr > 80 ? "严重拥堵" : cr > 50 ? "中度拥堵" : cr > 25 ? "轻度拥堵" : "畅通");
            item.put("isMlGenerated", false);
            predictions.add(item);
        }
        return predictions;
    }

    @Override
    public List<Map<String, Object>> getRouteOptimizationTips() {
        // V5: 基于 XGBoost 拥堵预测模型实时生成出行建议
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        if (sections.isEmpty()) {
            return List.of(createRouteTip("当前无路段数据", "-", "请先添加路段信息", "-"));
        }

        List<Map<String, Object>> tips = new ArrayList<>();
        int dayOfWeek = LocalDate.now().getDayOfWeek().getValue();
        int month = LocalDate.now().getMonthValue();
        int isWeekend = (dayOfWeek >= 6) ? 1 : 0;

        for (TrafficRoadSection s : sections.stream().limit(5).collect(Collectors.toList())) {
            int lanes = s.getLanes() != null ? s.getLanes() : 4;
            int speedLimit = s.getSpeedLimit() != null ? s.getSpeedLimit() : 60;
            int roadType = s.getRoadType() != null ?
                    ("快速路".equals(s.getRoadType()) ? 2 : "主干道".equals(s.getRoadType()) ? 1 : 0) : 0;

            JsonNode v5Result = pythonMlClient.v5TrafficHourlyForecast(
                    dayOfWeek, month, isWeekend, 0, 0, 20, 50, lanes, speedLimit, roadType);

            int bestHour = 6, worstHour = 18;
            double bestSpeed = 0, worstSpeed = 100;
            boolean isMl = false;

            if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
                isMl = true;
                for (JsonNode hd : v5Result.path("hourly_data")) {
                    int h = hd.path("hour").asInt();
                    if (h < 6 || h > 22) continue;
                    double speed = hd.path("estimatedSpeed").asDouble(40);
                    if (speed > bestSpeed) { bestSpeed = speed; bestHour = h; }
                    if (speed < worstSpeed) { worstSpeed = speed; worstHour = h; }
                }
            } else {
                // Fallback: 数据库
                List<TrafficFlowRecord> recs = trafficFlowRepository.findBySectionId(s.getId());
                Map<Integer, Double> hourlyAvg = recs.stream()
                        .filter(r -> r.getAvgSpeed() != null)
                        .collect(Collectors.groupingBy(TrafficFlowRecord::getRecordHour,
                                Collectors.averagingDouble(TrafficFlowRecord::getAvgSpeed)));
                for (int h = 6; h <= 22; h++) {
                    double avg = hourlyAvg.getOrDefault(h, 30.0);
                    if (avg > bestSpeed) { bestSpeed = avg; bestHour = h; }
                    if (avg < worstSpeed) { worstSpeed = avg; worstHour = h; }
                }
            }

            int timeSaved = Math.max(5, worstSpeed > 0 ? (int) Math.round((worstSpeed - bestSpeed) / worstSpeed * 60) : 5);
            if (timeSaved > 60) timeSaved = 60;

            if (isMl || timeSaved > 10) {
                String sectionName = s.getRoadName() + "-" + s.getSectionName();
                tips.add(createRouteTip("错峰建议 - " + sectionName, sectionName,
                        String.format("最佳出发 %02d:00 (速度 %.0f km/h); 避开 %02d:00 (速度 %.0f km/h), 可节省约 %d 分钟",
                                bestHour, bestSpeed, worstHour, worstSpeed, timeSaved),
                        "预计节省" + timeSaved + "分钟"));
            }
        }

        if (tips.isEmpty()) {
            tips.add(createRouteTip("错峰出行建议", "城区主干道", "建议避开08:30-09:00高峰期", "预计节省20分钟"));
            tips.add(createRouteTip("公交优先", "浑南大道", "该路段设有公交专用道，建议选择公共交通", "环保+省时"));
        }
        return tips;
    }

    // ======================== 工具方法 ========================

    private Map<String, Object> createTip(String id, String title, String description, String priority, String category) {
        Map<String, Object> tip = new LinkedHashMap<>();
        tip.put("id", id);
        tip.put("title", title);
        tip.put("description", description);
        tip.put("priority", priority);
        tip.put("category", category);
        return tip;
    }

    private Map<String, Object> createRouteTip(String title, String section, String description, String benefit) {
        Map<String, Object> tip = new LinkedHashMap<>();
        tip.put("title", title);
        tip.put("section", section);
        tip.put("description", description);
        tip.put("benefit", benefit);
        return tip;
    }

    private String getAqiLevel(int aqi) {
        if (aqi <= 50) return "优";
        if (aqi <= 100) return "良";
        if (aqi <= 150) return "轻度污染";
        if (aqi <= 200) return "中度污染";
        return "重度污染";
    }

    private String getAqiColor(int aqi) {
        if (aqi <= 50) return "#67c23a";
        if (aqi <= 100) return "#e6a23c";
        if (aqi <= 150) return "#f56c6c";
        if (aqi <= 200) return "#e6162d";
        return "#7a1f1f";
    }

    // ======================== 🚗🚗🚗 交通仿真高级 AI 分析 ========================

    @Override
    public List<Map<String, Object>> predictCongestionCalendar(int days) {
        // V5: 使用 XGBoost 模型逐日预测
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        List<Map<String, Object>> calendar = new ArrayList<>();
        LocalDate today = LocalDate.now();

        for (TrafficRoadSection section : sections) {
            int lanes = section.getLanes() != null ? section.getLanes() : 4;
            int speedLimit = section.getSpeedLimit() != null ? section.getSpeedLimit() : 60;
            int roadType = section.getRoadType() != null ?
                    ("快速路".equals(section.getRoadType()) ? 2 : "主干道".equals(section.getRoadType()) ? 1 : 0) : 0;

            for (int d = 0; d < days; d++) {
                LocalDate futureDate = today.plusDays(d);
                int dayOfWeek = futureDate.getDayOfWeek().getValue();
                int month = futureDate.getMonthValue();
                int isWeekend = (dayOfWeek >= 6) ? 1 : 0;

                JsonNode v5Result = pythonMlClient.v5TrafficHourlyForecast(
                        dayOfWeek, month, isWeekend, 0, 0, 20, 50, lanes, speedLimit, roadType);

                double morningPeak = 0; int mpCount = 0;
                double eveningPeak = 0; int epCount = 0;
                double dailyTotal = 0; int totalHours = 0;
                boolean isMl = false;

                if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
                    isMl = true;
                    for (JsonNode hd : v5Result.path("hourly_data")) {
                        int h = hd.path("hour").asInt();
                        double flow = hd.path("estimatedFlow").asDouble();
                        if (h >= 7 && h <= 9) { morningPeak += flow; mpCount++; }
                        if (h >= 17 && h <= 19) { eveningPeak += flow; epCount++; }
                        dailyTotal += flow; totalHours++;
                    }
                }

                if (totalHours == 0) continue;
                morningPeak = mpCount > 0 ? morningPeak / mpCount : 0;
                eveningPeak = epCount > 0 ? eveningPeak / epCount : 0;
                double dailyAvg = dailyTotal / totalHours;

                Map<String, Object> dayData = new LinkedHashMap<>();
                dayData.put("date", futureDate.toString());
                dayData.put("dayOfWeek", futureDate.getDayOfWeek().getDisplayName(
                    java.time.format.TextStyle.FULL, java.util.Locale.CHINESE));
                dayData.put("sectionId", section.getId());
                dayData.put("sectionName", section.getRoadName() + "-" + section.getSectionName());
                dayData.put("morningPeakFlow", Math.round(morningPeak));
                dayData.put("eveningPeakFlow", Math.round(eveningPeak));
                dayData.put("dailyAvgFlow", Math.round(dailyAvg));
                dayData.put("morningCongestion", morningPeak > 5000 ? "严重拥堵" : morningPeak > 3000 ? "中度拥堵" : morningPeak > 1500 ? "轻度拥堵" : "畅通");
                dayData.put("eveningCongestion", eveningPeak > 5000 ? "严重拥堵" : eveningPeak > 3000 ? "中度拥堵" : eveningPeak > 1500 ? "轻度拥堵" : "畅通");
                dayData.put("dailyStatus", dailyAvg > 3500 ? "高负荷" : dailyAvg > 2000 ? "中负荷" : "低负荷");
                dayData.put("modelName", isMl ? "xgb_v5_congestion" : "db_fallback");
                dayData.put("isMlGenerated", isMl);
                calendar.add(dayData);
            }
        }
        return calendar;
    }

    @Override
    public Map<String, Object> simulateWhatIf(Long sectionId, Map<String, Object> scenario) {
        // V5: 使用 XGBoost 场景仿真模型 (traffic_scenario_model.pkl)
        TrafficRoadSection section = trafficRoadSectionRepository.findById(sectionId).orElse(null);
        if (section == null) return Map.of("error", "路段不存在");

        List<TrafficFlowRecord> records = trafficFlowRepository.findBySectionId(sectionId);
        double avgFlow = records.stream()
            .filter(r -> r.getFlowCount() != null)
            .mapToInt(TrafficFlowRecord::getFlowCount)
            .average().orElse(2000);
        double avgSpeed = records.stream()
            .filter(r -> r.getAvgSpeed() != null)
            .mapToDouble(TrafficFlowRecord::getAvgSpeed)
            .average().orElse(40);

        int lanes = section.getLanes() != null ? section.getLanes() : 4;
        int speedLimit = section.getSpeedLimit() != null ? section.getSpeedLimit() : 60;
        int roadType = section.getRoadType() != null ?
                ("快速路".equals(section.getRoadType()) ? 2 : "主干道".equals(section.getRoadType()) ? 1 : 0) : 0;
        String scenarioType = (String) scenario.getOrDefault("type", "add_lane");
        int paramValue = scenario.get("value") instanceof Number ? ((Number) scenario.get("value")).intValue() : 1;

        // V5 模型预测
        JsonNode v5Result = pythonMlClient.v5TrafficScenarioSimulate(
                scenarioType, paramValue, roadType, lanes, speedLimit,
                LocalDateTime.now().getHour(), LocalDate.now().getDayOfWeek().getValue(),
                avgFlow, avgSpeed);

        if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("sectionId", sectionId);
            result.put("sectionName", section.getRoadName() + "-" + section.getSectionName());
            result.put("originalLanes", lanes);
            result.put("originalSpeedLimit", speedLimit);
            result.put("originalAvgSpeed", Math.round(avgSpeed * 10.0) / 10.0);
            result.put("originalDailyFlow", Math.round(avgFlow));
            result.put("scenarioType", scenarioType);
            result.put("scenarioDescription", scenarioType.equals("add_lane") ? "增加 " + paramValue + " 条车道" : "限速调整为 " + paramValue + " km/h");
            result.put("predictedAvgSpeed", v5Result.path("predicted_speed").asDouble());
            result.put("predictedFlowCapacity", v5Result.path("predicted_flow").asInt());
            result.put("speedChange", v5Result.path("speed_change_pct").asDouble());
            result.put("capacityChange", v5Result.path("flow_change_pct").asDouble());
            result.put("impactDescription", v5Result.path("impact_description").asText());
            result.put("recommendation", v5Result.path("recommendation").asText());
            result.put("modelName", "xgb_v5_scenario");
            result.put("simulationTime", LocalDateTime.now().toString());
            result.put("isMlGenerated", true);
            return result;
        }

        // Fallback: 规则引擎
        String impact;
        String recommendation;
        double newSpeed = avgSpeed;
        double newFlow = avgFlow;

        if ("add_lane".equals(scenarioType)) {
            newFlow = avgFlow * (1 + paramValue * 0.12);
            newSpeed = avgSpeed * (1 + paramValue * 0.10);
            impact = String.format("增加%d条车道后，预计流量 %.0f → %.0f (+%.0f%%)",
                    paramValue, avgFlow, newFlow, (newFlow / avgFlow - 1) * 100);
            recommendation = avgFlow / (lanes * 1800.0) > 0.85 ? "增加车道可显著缓解拥堵" : "当前饱和度不高，建议优先优化信号灯";
        } else if ("change_speed".equals(scenarioType)) {
            double ratio = (double) paramValue / speedLimit;
            newSpeed = Math.min(paramValue, avgSpeed * (1 + (ratio - 1) * 0.5));
            newFlow = avgFlow * (1 + (ratio - 1) * 0.3);
            impact = String.format("限速 %d → %d km/h，速度 %.0f → %.0f km/h",
                    speedLimit, paramValue, avgSpeed, newSpeed);
            recommendation = paramValue > speedLimit ? "提高限速缩短通行时间" : "降低限速提高安全性";
        } else {
            impact = "未知场景类型";
            recommendation = "请选择有效的仿真场景";
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("sectionId", sectionId);
        result.put("sectionName", section.getRoadName() + "-" + section.getSectionName());
        result.put("originalLanes", lanes);
        result.put("originalSpeedLimit", speedLimit);
        result.put("originalAvgSpeed", Math.round(avgSpeed * 10.0) / 10.0);
        result.put("originalDailyFlow", Math.round(avgFlow));
        result.put("scenarioType", scenarioType);
        result.put("predictedAvgSpeed", Math.round(newSpeed * 10.0) / 10.0);
        result.put("predictedFlowCapacity", Math.round(newFlow));
        result.put("speedChange", Math.round((newSpeed / avgSpeed - 1) * 100));
        result.put("capacityChange", Math.round((newFlow / (avgFlow > 0 ? avgFlow : 1) - 1) * 100));
        result.put("impactDescription", impact);
        result.put("recommendation", recommendation);
        result.put("isMlGenerated", false);
        result.put("simulationTime", LocalDateTime.now().toString());
        return result;
    }

    private String getScenarioDescription(String type, int value) {
        return switch (type) {
            case "add_lane" -> "增加 " + value + " 条车道";
            case "change_speed" -> "限速调整为 " + value + " km/h";
            case "optimize_signals" -> "信号灯绿波优化 " + value + "%";
            default -> "自定义场景";
        };
    }

    @Override
    public List<Map<String, Object>> getTrafficHeatmap() {
        // V5: 使用 XGBoost 拥堵预测模型构建热力图
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        List<Map<String, Object>> heatmapData = new ArrayList<>();
        int dayOfWeek = LocalDate.now().getDayOfWeek().getValue();
        int month = LocalDate.now().getMonthValue();
        int isWeekend = (dayOfWeek >= 6) ? 1 : 0;
        int nowHour = LocalDateTime.now().getHour();

        double[][] coordinates = {
            {123.45, 41.78}, {123.47, 41.80}, {123.43, 41.76},
            {123.46, 41.75}, {123.44, 41.77}, {123.48, 41.79}, {123.42, 41.74},
            {123.49, 41.81}, {123.41, 41.73}, {123.50, 41.76},
            {123.40, 41.79}, {123.51, 41.77}, {123.39, 41.75}, {123.52, 41.80},
            {123.38, 41.82}, {123.53, 41.78}, {123.44, 41.72}, {123.46, 41.83},
            {123.48, 41.74}, {123.45, 41.79}
        };

        for (int i = 0; i < sections.size(); i++) {
            TrafficRoadSection s = sections.get(i);
            int lanes = s.getLanes() != null ? s.getLanes() : 4;
            int speedLimit = s.getSpeedLimit() != null ? s.getSpeedLimit() : 60;
            int roadType = s.getRoadType() != null ?
                    ("快速路".equals(s.getRoadType()) ? 2 : "主干道".equals(s.getRoadType()) ? 1 : 0) : 0;

            // V5 模型预测当前时段路况
            JsonNode v5Result = pythonMlClient.v5TrafficHourlyForecast(
                    dayOfWeek, month, isWeekend, 0, 0, 20, 50, lanes, speedLimit, roadType);

            double flow = 2000, speed = 40;
            double congestionIndex = 0.5;
            String level = "畅通";
            boolean isMl = false;

            if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
                isMl = true;
                // 找当前小时的数据
                for (JsonNode hd : v5Result.path("hourly_data")) {
                    int h = hd.path("hour").asInt();
                    if (h == nowHour || (h < nowHour && nowHour - h == 1)) {
                        flow = hd.path("estimatedFlow").asDouble(flow);
                        speed = hd.path("estimatedSpeed").asDouble(speed);
                        level = hd.path("congestionLevel").asText(level);
                        congestionIndex = hd.path("congestionIndex").asDouble(congestionIndex);
                        break;
                    }
                }
            } else {
                // Fallback: 数据库
                List<TrafficFlowRecord> recs = trafficFlowRepository.findTop10BySectionIdOrderByRecordHourDesc(s.getId());
                if (!recs.isEmpty()) {
                    TrafficFlowRecord latest = recs.get(0);
                    flow = latest.getFlowCount() != null ? latest.getFlowCount() : flow;
                    speed = latest.getAvgSpeed() != null ? latest.getAvgSpeed() : speed;
                    congestionIndex = Math.min(1.0, Math.max(0.0, 1.0 - speed / 70.0));
                    level = speed >= 50 ? "畅通" : speed >= 35 ? "轻度拥堵" : speed >= 20 ? "中度拥堵" : "严重拥堵";
                }
            }

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("sectionId", s.getId());
            item.put("roadName", s.getRoadName());
            item.put("sectionName", s.getSectionName());
            item.put("longitude", i < coordinates.length ? coordinates[i][0] : 123.45);
            item.put("latitude", i < coordinates.length ? coordinates[i][1] : 41.78);
            item.put("flow", Math.round(flow));
            item.put("avgSpeed", Math.round(speed * 10.0) / 10.0);
            item.put("length", s.getLength());
            item.put("lanes", s.getLanes());
            item.put("congestionLevel", level);
            item.put("congestionIndex", Math.round(congestionIndex * 100.0) / 100.0);
            item.put("modelName", isMl ? "xgb_v5_congestion" : "db_fallback");
            item.put("isMlGenerated", isMl);
            heatmapData.add(item);
        }
        return heatmapData;
    }

    @Override
    public Map<String, Object> getSmartDepartureTips() {
        // V5: 基于 XGBoost 拥堵预测模型给出最佳出行时段
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        List<Map<String, Object>> sectionTips = new ArrayList<>();
        int dayOfWeek = LocalDate.now().getDayOfWeek().getValue();
        int month = LocalDate.now().getMonthValue();
        int isWeekend = (dayOfWeek >= 6) ? 1 : 0;

        for (TrafficRoadSection s : sections) {
            int lanes = s.getLanes() != null ? s.getLanes() : 4;
            int speedLimit = s.getSpeedLimit() != null ? s.getSpeedLimit() : 60;
            int roadType = s.getRoadType() != null ?
                    ("快速路".equals(s.getRoadType()) ? 2 : "主干道".equals(s.getRoadType()) ? 1 : 0) : 0;

            JsonNode v5Result = pythonMlClient.v5TrafficHourlyForecast(
                    dayOfWeek, month, isWeekend, 0, 0, 20, 50, lanes, speedLimit, roadType);

            int bestHour = 6, worstHour = 18;
            double bestSpeed = 0, worstSpeed = 100;
            boolean isMl = false;

            if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
                isMl = true;
                for (JsonNode hd : v5Result.path("hourly_data")) {
                    int h = hd.path("hour").asInt();
                    if (h < 6 || h > 22) continue;
                    double speed = hd.path("estimatedSpeed").asDouble(40);
                    if (speed > bestSpeed) { bestSpeed = speed; bestHour = h; }
                    if (speed < worstSpeed) { worstSpeed = speed; worstHour = h; }
                }
            } else {
                // Fallback: 数据库统计
                List<TrafficFlowRecord> allRecords = trafficFlowRepository.findAll();
                Map<Integer, List<Double>> hourlySpeeds = new HashMap<>();
                for (TrafficFlowRecord r : allRecords) {
                    if (!r.getSectionId().equals(s.getId())) continue;
                    hourlySpeeds.computeIfAbsent(r.getRecordHour(), k -> new ArrayList<>())
                            .add(r.getAvgSpeed() != null ? r.getAvgSpeed() : 30.0);
                }
                for (int h = 6; h <= 22; h++) {
                    double avg = hourlySpeeds.getOrDefault(h, new ArrayList<>()).stream()
                            .mapToDouble(d -> d).average().orElse(30);
                    if (avg > bestSpeed) { bestSpeed = avg; bestHour = h; }
                    if (avg < worstSpeed) { worstSpeed = avg; worstHour = h; }
                }
            }

            int timeSaved = Math.max(5, worstSpeed > 0 ? (int) Math.round((worstSpeed - bestSpeed) / worstSpeed * 60) : 5);
            if (timeSaved > 60) timeSaved = 60;

            Map<String, Object> tip = new LinkedHashMap<>();
            tip.put("sectionId", s.getId());
            tip.put("sectionName", s.getRoadName() + "-" + s.getSectionName());
            tip.put("bestDepartureHour", String.format("%02d:00", bestHour));
            tip.put("worstDepartureHour", String.format("%02d:00", worstHour));
            tip.put("bestSpeed", Math.round(bestSpeed * 10.0) / 10.0);
            tip.put("worstSpeed", Math.round(worstSpeed * 10.0) / 10.0);
            tip.put("timeSaved", timeSaved);
            tip.put("tip", String.format("建议 %02d:00 前出发，比 %02d:00 高峰期可节省约 %d 分钟",
                bestHour, worstHour, timeSaved));
            tip.put("modelName", isMl ? "xgb_v5_congestion" : "db_fallback");
            tip.put("isMlGenerated", isMl);
            sectionTips.add(tip);
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalSections", sections.size());
        result.put("tips", sectionTips);
        result.put("generatedTime", LocalDateTime.now().toString());
        return result;
    }

    @Override
    public Map<String, Object> analyzeAccidentImpact(Long sectionId) {
        // V5: 使用 GradientBoosting 事故影响模型
        TrafficRoadSection accidentSection = trafficRoadSectionRepository.findById(sectionId).orElse(null);
        if (accidentSection == null) return Map.of("error", "路段不存在");

        List<TrafficRoadSection> allSections = trafficRoadSectionRepository.findAll();
        List<TrafficFlowRecord> records = trafficFlowRepository.findAll();

        double normalFlow = records.stream()
            .filter(r -> r.getSectionId().equals(sectionId) && r.getFlowCount() != null)
            .mapToInt(TrafficFlowRecord::getFlowCount)
            .average().orElse(2000);

        int lanes = accidentSection.getLanes() != null ? accidentSection.getLanes() : 4;
        int speedLimit = accidentSection.getSpeedLimit() != null ? accidentSection.getSpeedLimit() : 60;
        int roadType = accidentSection.getRoadType() != null ?
                ("快速路".equals(accidentSection.getRoadType()) ? 2 : "主干道".equals(accidentSection.getRoadType()) ? 1 : 0) : 0;

        double accidentSeverity = normalFlow > 4000 ? 0.7 : normalFlow > 2500 ? 0.4 : 0.2;

        JsonNode v5Result = pythonMlClient.v5TrafficAccidentImpact(
                sectionId.intValue(), roadType, lanes, speedLimit,
                LocalDateTime.now().getHour(), LocalDate.now().getDayOfWeek().getValue(),
                accidentSeverity, normalFlow, 45);

        double flowReductionPct = 50;
        double speedReductionPct = 40;
        boolean isMl = false;

        if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
            flowReductionPct = v5Result.path("flow_reduction_pct").asDouble(50);
            speedReductionPct = v5Result.path("speed_reduction_pct").asDouble(40);
            isMl = true;
        }

        double reducedCapacity = normalFlow * (1 - flowReductionPct / 100);
        String accidentLevel = flowReductionPct > 60 ? "重大事故" : flowReductionPct > 35 ? "一般事故" : "轻微事故";

        List<Map<String, Object>> affectedSections = new ArrayList<>();
        double predictedFlow = normalFlow * (1 - flowReductionPct / 100);

        for (TrafficRoadSection s : allSections) {
            if (s.getId().equals(sectionId)) continue;
            double distance = Math.abs((s.getLength() != null ? s.getLength() : 5)
                    - (accidentSection.getLength() != null ? accidentSection.getLength() : 5));
            double impactFactor = Math.max(0.1, 1.0 - distance / 10.0);
            double divertedFlow = (normalFlow - predictedFlow) * impactFactor * 0.3;

            double sectionNormalFlow = records.stream()
                .filter(r -> r.getSectionId().equals(s.getId()) && r.getFlowCount() != null)
                .mapToInt(TrafficFlowRecord::getFlowCount)
                .average().orElse(1500);

            double extraLoad = divertedFlow / Math.max(sectionNormalFlow, 1);
            String impactLevel = extraLoad > 0.3 ? "严重影响" : extraLoad > 0.15 ? "中度影响" : extraLoad > 0.05 ? "轻微影响" : "无影响";

            Map<String, Object> affected = new LinkedHashMap<>();
            affected.put("sectionId", s.getId());
            affected.put("sectionName", s.getRoadName() + "-" + s.getSectionName());
            affected.put("impactLevel", impactLevel);
            affected.put("extraLoadPercent", Math.round(extraLoad * 100));
            affected.put("divertedFlow", Math.round(divertedFlow));
            affected.put("estimatedDelay", Math.round(extraLoad * 20) + "分钟");
            affectedSections.add(affected);
        }

        affectedSections.sort((a, b) -> Integer.compare(
                ((Number) b.get("extraLoadPercent")).intValue(),
                ((Number) a.get("extraLoadPercent")).intValue()));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("accidentSection", accidentSection.getRoadName() + "-" + accidentSection.getSectionName());
        result.put("accidentLevel", accidentLevel);
        result.put("accidentSeverity", accidentSeverity);
        result.put("normalFlow", Math.round(normalFlow));
        result.put("predictedFlow", Math.round(predictedFlow));
        result.put("reducedCapacity", Math.round(reducedCapacity));
        result.put("flowReductionPct", Math.round(flowReductionPct));
        result.put("speedReductionPct", Math.round(speedReductionPct));
        result.put("affectedSectionCount", affectedSections.size());
        result.put("affectedSections", affectedSections);
        double totalDiverted = affectedSections.stream()
            .mapToDouble(a -> ((Number) a.get("divertedFlow")).doubleValue()).sum();
        result.put("totalDivertedFlow", Math.round(totalDiverted));
        int clearMinutes = (int) Math.round(30 + accidentSeverity * 50);
        result.put("estimatedClearTime", "约" + clearMinutes + "分钟");
        String firstSectionName = affectedSections.isEmpty() ? "其他" : (String) affectedSections.get(0).get("sectionName");
        result.put("recommendation", "建议引导车辆绕行" + firstSectionName + "等受影响较小的路段");
        result.put("modelName", isMl ? "gb_v5_accident_impact" : "rule_fallback");
        result.put("isMlGenerated", isMl);
        result.put("analysisTime", LocalDateTime.now().toString());
        return result;
    }

    @Override
    public List<Map<String, Object>> analyzeWeatherTrafficCorrelation() {
        // V5: 使用 XGBoost 天气影响模型
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        List<Map<String, Object>> correlations = new ArrayList<>();
        int nowHour = LocalDateTime.now().getHour();
        int roadType = 1;

        if (!sections.isEmpty()) {
            TrafficRoadSection s = sections.get(0);
            roadType = s.getRoadType() != null ?
                    ("快速路".equals(s.getRoadType()) ? 2 : "主干道".equals(s.getRoadType()) ? 1 : 0) : 0;
        }

        JsonNode v5Result = pythonMlClient.v5TrafficWeatherImpact(roadType, nowHour, 20, 50);

        String[] weatherNames = {"晴", "多云", "小雨", "中雨", "暴雨", "小雪", "中雪", "大雪", "雾"};
        boolean isMl = false;
        Map<Integer, Map<String, Object>> mlResults = new HashMap<>();

        if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
            isMl = true;
            for (JsonNode r : v5Result.path("results")) {
                int wc = r.path("weather_code").asInt();
                Map<String, Object> data = new HashMap<>();
                data.put("speed", r.path("predicted_speed").asDouble(40));
                data.put("flow", r.path("predicted_flow").asDouble(2000));
                data.put("congestionIndex", r.path("predicted_congestion").asDouble(0.5));
                data.put("risk", r.path("congestion_risk").asText("低风险"));
                mlResults.put(wc, data);
            }
        }

        String[] temps = {"26", "22", "18", "15", "12", "-5", "-8", "-12", "20"};
        String[] humidities = {"10%", "30%", "70%", "85%", "95%", "75%", "80%", "85%", "60%"};
        double[] speedFactors = {1.0, 0.95, 0.88, 0.78, 0.55, 0.80, 0.65, 0.45, 0.65};

        for (int w = 0; w < weatherNames.length; w++) {
            int wc = w;
            double speedFactor = speedFactors[w];
            double flow = 2000, speed = 40;
            String riskLevel = "低风险";

            if (isMl && mlResults.containsKey(wc)) {
                Map<String, Object> data = mlResults.get(wc);
                speed = (double) data.get("speed");
                flow = (double) data.get("flow");
                riskLevel = (String) data.get("risk");
            } else {
                speed = 40 * speedFactor;
                flow = 2000 * (0.85 + speedFactor * 0.15);
                if (speedFactor < 0.6) { riskLevel = "高风险"; }
                else if (speedFactor < 0.8) { riskLevel = "中风险"; }
            }

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("weather", weatherNames[w]);
            item.put("weatherType", weatherNames[w]);
            item.put("temperature", temps[w] + "\u00b0C");
            item.put("humidity", humidities[w]);
            item.put("speedFactor", speedFactor);
            item.put("speedReduction", Math.round((1 - speedFactor) * 100) + "%");
            item.put("flowImpact", Math.round(flow));
            item.put("predictedSpeed", Math.round(speed * 10.0) / 10.0);
            item.put("congestionRisk", riskLevel);
            item.put("affectedSections", sections.size() + "个路段受影响");
            item.put("drivingAdvice", switch (weatherNames[w]) {
                case "暴雨" -> "建议推迟出行或选择公共交通";
                case "大雪" -> "建议减速慢行，保持车距，避免非必要出行";
                case "雾" -> "开启雾灯，减速慢行，能见度低注意安全";
                case "小雨" -> "路面湿滑，注意减速";
                case "中雨" -> "建议错峰出行，避开易积水路段";
                case "多云" -> "注意局部阵雨";
                default -> "出行条件良好";
            });
            item.put("modelName", isMl ? "xgb_v5_weather" : "static_fallback");
            item.put("isMlGenerated", isMl);
            correlations.add(item);
        }
        return correlations;
    }

    @Override
    public List<Map<String, Object>> detectTrafficAnomalies() {
        // V5: 使用 Isolation Forest 异常检测模型
        List<TrafficRoadSection> sections = trafficRoadSectionRepository.findAll();
        List<TrafficFlowRecord> allRecords = trafficFlowRepository.findAll();
        List<Map<String, Object>> anomalies = new ArrayList<>();

        List<Map<String, Object>> mlRecords = new ArrayList<>();
        for (TrafficRoadSection s : sections) {
            List<TrafficFlowRecord> sectionRecs = allRecords.stream()
                    .filter(r -> r.getSectionId().equals(s.getId()) && r.getFlowCount() != null)
                    .collect(Collectors.toList());
            if (sectionRecs.size() < 5) continue;

            double mean = sectionRecs.stream().mapToInt(TrafficFlowRecord::getFlowCount).average().orElse(0);
            double variance = sectionRecs.stream().mapToDouble(r -> Math.pow(r.getFlowCount() - mean, 2)).average().orElse(0);
            double std = Math.sqrt(variance);

            TrafficFlowRecord latest = sectionRecs.get(sectionRecs.size() - 1);

            Map<String, Object> rec = new LinkedHashMap<>();
            rec.put("section_id", s.getId().intValue());
            rec.put("hour", latest.getRecordHour());
            rec.put("day_of_week", LocalDate.now().getDayOfWeek().getValue());
            rec.put("flow_mean", mean);
            rec.put("flow_std", std > 0 ? std : 1);
            rec.put("speed_mean", sectionRecs.stream().filter(r -> r.getAvgSpeed() != null)
                    .mapToDouble(TrafficFlowRecord::getAvgSpeed).average().orElse(40));
            rec.put("speed_std", Math.sqrt(sectionRecs.stream().filter(r -> r.getAvgSpeed() != null)
                    .mapToDouble(r -> Math.pow(r.getAvgSpeed() - 40, 2)).average().orElse(10)));
            rec.put("cong_mean", Math.min(1.0, mean / 5000.0));
            rec.put("cong_std", 0.1);
            rec.put("flow_deviation", latest.getFlowCount() != null ? (latest.getFlowCount() - mean) / Math.max(std, 1) : 0);
            rec.put("speed_deviation", 0.0);
            rec.put("flow_count", latest.getFlowCount() != null ? latest.getFlowCount() : 0);
            rec.put("avg_speed", latest.getAvgSpeed() != null ? latest.getAvgSpeed() : 0);
            mlRecords.add(rec);
        }

        if (!mlRecords.isEmpty()) {
            JsonNode v5Result = pythonMlClient.v5TrafficAnomalyEnhanced(mlRecords);
            if (v5Result != null && "success".equals(v5Result.path("status").asText())) {
                for (JsonNode a : v5Result.path("anomalies")) {
                    Map<String, Object> anomaly = new LinkedHashMap<>();
                    anomaly.put("sectionId", a.path("section_id").asLong());
                    anomaly.put("sectionName", "路段" + a.path("section_id").asLong());
                    anomaly.put("recordDate", LocalDate.now().toString());
                    anomaly.put("hour", LocalDateTime.now().getHour() + ":00");
                    anomaly.put("expectedFlow", a.path("expected_flow").asInt());
                    anomaly.put("actualFlow", a.path("actual_flow").asInt());
                    double deviation = Math.abs(a.path("actual_flow").asDouble() - a.path("expected_flow").asDouble())
                            / Math.max(a.path("expected_flow").asDouble(), 1) * 100;
                    anomaly.put("deviation", Math.round(deviation) + "%");
                    anomaly.put("anomalyType", a.path("anomaly_type").asText());
                    anomaly.put("severity", a.path("severity").asText());
                    anomaly.put("possibleCause", "严重".equals(a.path("severity").asText()) ? "交通事故/封路" : "异常流量模式");
                    anomaly.put("anomalyScore", a.path("anomaly_score").asDouble());
                    anomaly.put("modelName", "iforest_v5_anomaly");
                    anomaly.put("isMlGenerated", true);
                    anomalies.add(anomaly);
                }
            }
        }

        if (anomalies.isEmpty()) {
            for (TrafficRoadSection s : sections) {
                List<TrafficFlowRecord> sectionRecs = allRecords.stream()
                        .filter(r -> r.getSectionId().equals(s.getId()) && r.getFlowCount() != null)
                        .collect(Collectors.toList());
                if (sectionRecs.size() < 5) continue;
                double mean = sectionRecs.stream().mapToInt(TrafficFlowRecord::getFlowCount).average().orElse(0);
                double variance = sectionRecs.stream().mapToDouble(r -> Math.pow(r.getFlowCount() - mean, 2)).average().orElse(0);
                double std = Math.sqrt(variance);
                for (TrafficFlowRecord r : sectionRecs) {
                    if (Math.abs(r.getFlowCount() - mean) > 2 * std && r.getFlowCount() > 0) {
                        Map<String, Object> anomaly = new LinkedHashMap<>();
                        anomaly.put("sectionId", s.getId());
                        anomaly.put("sectionName", s.getRoadName() + "-" + s.getSectionName());
                        anomaly.put("recordDate", r.getRecordDate().toString());
                        anomaly.put("hour", r.getRecordHour() + ":00");
                        anomaly.put("expectedFlow", Math.round(mean));
                        anomaly.put("actualFlow", r.getFlowCount());
                        anomaly.put("deviation", Math.round((r.getFlowCount() - mean) / mean * 100) + "%");
                        anomaly.put("anomalyType", r.getFlowCount() > mean ? "流量激增" : "流量锐减");
                        anomaly.put("severity", Math.abs(r.getFlowCount() - mean) > 3 * std ? "严重" : "警告");
                        anomaly.put("possibleCause", r.getFlowCount() > mean ? "前方拥堵回溢/大型活动" : "交通事故/封路");
                        anomaly.put("isMlGenerated", false);
                        anomalies.add(anomaly);
                        break;
                    }
                }
            }
        }

        return anomalies;
    }

    // ===== 异步 AI 分析方法（@Async 支持） =====

    @Async("aiAnalysisExecutor")
    @Override
    public CompletableFuture<EnergySummaryReportDTO> asyncGenerateEnergyReport() {
        log.info("[异步] 开始生成能源AI报告，线程: {}", Thread.currentThread().getName());
        long start = System.currentTimeMillis();
        EnergySummaryReportDTO result = getEnergySummaryReport();
        long elapsed = System.currentTimeMillis() - start;
        log.info("[异步] 能源AI报告生成完成，耗时: {}ms", elapsed);
        return CompletableFuture.completedFuture(result);
    }

    @Async("aiAnalysisExecutor")
    @Override
    public CompletableFuture<List<Map<String, Object>>> asyncDetectEnvironmentAnomalies() {
        log.info("[异步] 开始环境异常检测，线程: {}", Thread.currentThread().getName());
        long start = System.currentTimeMillis();
        List<Map<String, Object>> result = getEnvironmentalAnomalyDetection();
        long elapsed = System.currentTimeMillis() - start;
        log.info("[异步] 环境异常检测完成，耗时: {}ms", elapsed);
        return CompletableFuture.completedFuture(result);
    }

    @Async("aiAnalysisExecutor")
    @Override
    public CompletableFuture<FinanceReportDTO> asyncGenerateRiskReport() {
        log.info("[异步] 开始生成风险评估报告，线程: {}", Thread.currentThread().getName());
        long start = System.currentTimeMillis();
        FinanceReportDTO result = (FinanceReportDTO) generateRiskAssessmentReport();
        long elapsed = System.currentTimeMillis() - start;
        log.info("[异步] 风险评估报告生成完成，耗时: {}ms", elapsed);
        return CompletableFuture.completedFuture(result);
    }

    @Async("aiAnalysisExecutor")
    @Override
    public CompletableFuture<List<Map<String, Object>>> asyncMultiFactorPrediction() {
        log.info("[异步] 开始多因子AQI预测，线程: {}", Thread.currentThread().getName());
        long start = System.currentTimeMillis();
        List<Map<String, Object>> result = getMultiFactorPrediction();
        long elapsed = System.currentTimeMillis() - start;
        log.info("[异步] 多因子AQI预测完成，耗时: {}ms", elapsed);
        return CompletableFuture.completedFuture(result);
    }

    @Async("aiAnalysisExecutor")
    @Override
    public CompletableFuture<List<SuspiciousTransactionDTO>> asyncDetectSuspiciousTransactions() {
        log.info("[异步] 开始可疑交易检测，线程: {}", Thread.currentThread().getName());
        long start = System.currentTimeMillis();
        List<SuspiciousTransactionDTO> result = detectSuspiciousTransactions();
        long elapsed = System.currentTimeMillis() - start;
        log.info("[异步] 可疑交易检测完成，耗时: {}ms", elapsed);
        return CompletableFuture.completedFuture(result);
    }

    // ======================== AI 辅助工具方法 ========================

    /**
     * 在结果 Map 中添加 AI 生成标记
     * @param result 结果 Map
     * @param isAiGenerated 是否为真实 AI 生成
     */
    private Map<String, Object> withAiFlag(Map<String, Object> result, boolean isAiGenerated) {
        result.put("isAiGenerated", isAiGenerated);
        return result;
    }

    /**
     * 尝试使用 AI 生成文本摘要/报告
     * 如果 AI 不可用，返回 null，调用方应使用模拟结果
     */
    @SuppressWarnings("unchecked")
    private Map<String, Object> aiGenerateReport(String systemPrompt, String dataSummary) {
        Map<String, Object> aiResult = aiModelClient.callAsMap(systemPrompt, dataSummary);
        if (aiResult != null) {
            aiResult.put("isAiGenerated", true);
        }
        return aiResult;
    }

    /**
     * 尝试使用 AI 生成建议列表
     */
    @SuppressWarnings("unchecked")
    private List<Map<String, Object>> aiGenerateSuggestions(String systemPrompt, String dataContext) {
        Map<String, Object> result = aiModelClient.callAsMap(systemPrompt, dataContext);
        if (result != null && result.containsKey("suggestions")) {
            List<Map<String, Object>> suggestions = (List<Map<String, Object>>) result.get("suggestions");
            suggestions.forEach(s -> s.put("isAiGenerated", true));
            return suggestions;
        }
        return null;
    }


}
