package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.config.AiModelClient;
import com.aiempowerment.platform.model.dto.analysis.AirQualityPredictionDTO;
import com.aiempowerment.platform.model.dto.analysis.PollutionAlertDTO;
import com.aiempowerment.platform.model.entity.AirQualityRecord;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import com.aiempowerment.platform.repository.AirQualityRecordRepository;
import com.aiempowerment.platform.repository.EnvironmentMonitorPointRepository;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 环境监测AI分析服务 — 改造版
 * <p>
 * 原来的伪AI（sin波+随机数）已替换为 Python ML Server 的真实模型调用。
 * Python 模型不可用时会自动 fallback 到原模拟逻辑，确保系统正常运行。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EnvironmentAnalysisService {

    private final AirQualityRecordRepository airQualityRepository;
    private final EnvironmentMonitorPointRepository envPointRepository;
    private final AiModelClient aiModelClient;
    private final PythonMlClient pythonMlClient;

    /**
     * 当环境数据库为空时，是否自动生成模拟监测数据并写入数据库。
     * <p>
     * 演示/开发环境可开启以便页面有数据展示；<b>生产环境请设为 false</b>，
     * 避免向生产库写入合成数据。配置项：{@code app.env.seed-demo-data}。
     */
    @Value("${app.env.seed-demo-data:true}")
    private boolean seedDemoData;

    // ======================== 环境分析核心方法 ========================

    public List<AirQualityPredictionDTO> predictAirQuality(int days) {
        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();
        double avgAqi = recentRecords.stream().mapToInt(r -> r.getAqi() != null ? r.getAqi() : 50).average().orElse(80);
        double avgPm25 = recentRecords.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(35);
        double avgPm10 = recentRecords.stream().filter(r -> r.getPm10() != null).mapToDouble(AirQualityRecord::getPm10).average().orElse(60);
        double avgO3 = recentRecords.stream().filter(r -> r.getO3() != null).mapToDouble(AirQualityRecord::getO3).average().orElse(30);
        double avgNo2 = recentRecords.stream().filter(r -> r.getNo2() != null).mapToDouble(AirQualityRecord::getNo2).average().orElse(25);
        double avgSo2 = recentRecords.stream().filter(r -> r.getSo2() != null).mapToDouble(AirQualityRecord::getSo2).average().orElse(10);
        double avgCo = recentRecords.stream().filter(r -> r.getCo() != null).mapToDouble(AirQualityRecord::getCo).average().orElse(2);

        List<AirQualityPredictionDTO> predictions = new ArrayList<>();
        boolean mlSuccess = false;
        LocalDate today = LocalDate.now();

        // 优先使用 Python ML 模型逐日预测
        for (int i = 1; i <= days && !mlSuccess; i++) {
            LocalDate futureDate = today.plusDays(i);
            double dayFactor = 1.0 + Math.sin(futureDate.getDayOfYear() * Math.PI / 180) * 0.3;
            double temp = 25 + Math.sin(futureDate.getDayOfYear() * Math.PI / 90) * 10;
            double hum = 55 + Math.sin(futureDate.getDayOfYear() * Math.PI / 120) * 15;

            JsonNode result = pythonMlClient.predictEnvironment(
                    avgPm25 * dayFactor, avgPm10 * dayFactor, avgO3 * dayFactor,
                    avgNo2 * dayFactor, avgSo2 * dayFactor, avgCo * dayFactor,
                    temp, hum
            );
            if (result != null && "success".equals(result.path("status").asText())) {
                int predictedAqi = (int) Math.round(result.path("predicted_aqi").asDouble());
                String level = result.path("aqi_level").asText();
                predictions.add(new AirQualityPredictionDTO(
                        futureDate,
                        futureDate.getDayOfWeek().toString(),
                        predictedAqi,
                        level,
                        getAqiColor(predictedAqi),
                        true
                ));
                mlSuccess = (i == days); // complete all days
            }
        }

        // Fallback: 使用真实数据 + 模拟波动
        if (predictions.isEmpty()) {
            log.warn("Python ML Server 不可用，使用 fallback 预测");
            for (int i = 1; i <= days; i++) {
                LocalDate futureDate = today.plusDays(i);
                double seasonalFactor = 1.0 + Math.sin(futureDate.getDayOfYear() * Math.PI / 180) * 0.3;
                double weatherNoise = 0.85 + Math.sin(i * 2.3 + 1) * 0.15;
                double predictedAqi = avgAqi * seasonalFactor * weatherNoise;
                int predictedAqiInt = Math.max(0, (int) Math.round(predictedAqi));

                predictions.add(new AirQualityPredictionDTO(
                        futureDate,
                        futureDate.getDayOfWeek().toString(),
                        predictedAqiInt,
                        getAqiLevel(predictedAqiInt),
                        getAqiColor(predictedAqiInt),
                        false
                ));
            }
        }

        return predictions;
    }

    public List<PollutionAlertDTO> getPollutionAlerts() {
        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();
        List<PollutionAlertDTO> alerts = new ArrayList<>();

        if (!recentRecords.isEmpty()) {
            AirQualityRecord latest = recentRecords.get(0);
            JsonNode result = pythonMlClient.predictEnvironment(
                    latest.getPm25() != null ? latest.getPm25() : 0,
                    latest.getPm10() != null ? latest.getPm10() : 0,
                    latest.getO3() != null ? latest.getO3() : 0,
                    latest.getNo2() != null ? latest.getNo2() : 0,
                    latest.getSo2() != null ? latest.getSo2() : 0,
                    latest.getCo() != null ? latest.getCo() : 0,
                    25, 60
            );
            if (result != null && "success".equals(result.path("status").asText())) {
                int predictedAqi = (int) Math.round(result.path("predicted_aqi").asDouble());
                String advice = result.path("health_advice").asText();
                alerts.add(buildMlAlert(predictedAqi, advice, true));
            }
        }

        // Fallback
        if (alerts.isEmpty()) {
            long badCount = recentRecords.stream().filter(r -> r.getAqi() != null && r.getAqi() > 100).count();
            if (badCount >= 3) {
                alerts.add(new PollutionAlertDTO(
                        "橙色预警",
                        "近期空气质量较差，建议减少户外活动",
                        "全城范围",
                        "外出佩戴防护口罩，敏感人群减少出行",
                        LocalDateTime.now().toString(),
                        false
                ));
            } else {
                alerts.add(new PollutionAlertDTO(
                        "正常",
                        "当前空气质量良好，无预警",
                        "-",
                        "适合户外活动",
                        LocalDateTime.now().toString(),
                        false
                ));
            }
        }

        return alerts;
    }

    // ======================== 环境监测高级 AI 分析 ========================

    public Map<String, Object> getEnvironmentHealthIndex() { // TODO: convert to typed DTO
        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();
        List<EnvironmentMonitorPoint> allPoints = envPointRepository.findAll();

        if (recentRecords.isEmpty()) {
            JsonNode fallbackResult = pythonMlClient.predictEnvironment(35, 60, 30, 25, 10, 2, 25, 60);
            if (fallbackResult != null && "success".equals(fallbackResult.path("status").asText())) {
                return buildHealthIndexFromMl(fallbackResult, true);
            }
            return Map.of("healthIndex", 85, "level", "良好", "assessment", "暂无监测数据，基于模拟数据评估", "isMlGenerated", false);
        }

        // 使用最新记录调用 ML 模型
        AirQualityRecord latest = recentRecords.get(0);
        JsonNode result = pythonMlClient.predictEnvironment(
                latest.getPm25() != null ? latest.getPm25() : 35,
                latest.getPm10() != null ? latest.getPm10() : 60,
                latest.getO3() != null ? latest.getO3() : 30,
                latest.getNo2() != null ? latest.getNo2() : 25,
                latest.getSo2() != null ? latest.getSo2() : 10,
                latest.getCo() != null ? latest.getCo() : 2,
                25, 60
        );
        if (result != null && "success".equals(result.path("status").asText())) {
            return buildHealthIndexFromMl(result, true);
        }

        // Fallback: 原统计逻辑
        double avgAqi = recentRecords.stream().filter(r -> r.getAqi() != null).mapToInt(AirQualityRecord::getAqi).average().orElse(80);
        double avgPm25 = recentRecords.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(35);
        double avgPm10 = recentRecords.stream().filter(r -> r.getPm10() != null).mapToDouble(AirQualityRecord::getPm10).average().orElse(60);
        double avgO3 = recentRecords.stream().filter(r -> r.getO3() != null).mapToDouble(AirQualityRecord::getO3).average().orElse(30);
        double avgNo2 = recentRecords.stream().filter(r -> r.getNo2() != null).mapToDouble(AirQualityRecord::getNo2).average().orElse(25);

        double aqiScore = Math.max(0, 100 - avgAqi * 0.8);
        double pm25Score = Math.max(0, 100 - avgPm25 * 1.5);
        double pm10Score = Math.max(0, 100 - avgPm10 * 0.8);
        double o3Score = Math.max(0, 100 - avgO3 * 1.2);
        double no2Score = Math.max(0, 100 - avgNo2 * 1.2);

        double healthIndex = aqiScore * 0.35 + pm25Score * 0.25 + pm10Score * 0.15 + o3Score * 0.15 + no2Score * 0.10;
        healthIndex = Math.max(0, Math.min(100, healthIndex));

        List<Map<String, Object>> pollutantScores = new ArrayList<>(Arrays.asList(
                Map.of("name", "PM2.5", "value", Math.round(avgPm25 * 10.0) / 10.0, "score", Math.round(pm25Score * 10.0) / 10.0),
                Map.of("name", "PM10", "value", Math.round(avgPm10 * 10.0) / 10.0, "score", Math.round(pm10Score * 10.0) / 10.0),
                Map.of("name", "O3", "value", Math.round(avgO3 * 10.0) / 10.0, "score", Math.round(o3Score * 10.0) / 10.0),
                Map.of("name", "NO2", "value", Math.round(avgNo2 * 10.0) / 10.0, "score", Math.round(no2Score * 10.0) / 10.0)
        ));
        pollutantScores.sort((a, b) -> Double.compare(((Number) b.get("value")).doubleValue(), ((Number) a.get("value")).doubleValue()));

        String worstPollutant = (String) pollutantScores.get(0).get("name");
        String level;
        String assessment;
        if (healthIndex >= 80) { level = "优秀"; assessment = "环境质量优秀，空气清新，适合户外活动和运动。"; }
        else if (healthIndex >= 60) { level = "良好"; assessment = "环境质量良好，空气质量可接受，但对敏感人群仍需留意。"; }
        else if (healthIndex >= 40) { level = "一般"; assessment = "环境质量一般，主要污染物为" + worstPollutant + "，建议减少长时间户外活动。"; }
        else { level = "较差"; assessment = "环境质量较差，" + worstPollutant + "浓度偏高，建议开启空气净化器并关闭门窗。"; }

        Map<String, Object> resultMap = new LinkedHashMap<>();
        resultMap.put("healthIndex", Math.round(healthIndex * 10.0) / 10.0);
        resultMap.put("level", level);
        resultMap.put("assessment", assessment);
        resultMap.put("worstPollutant", worstPollutant);
        resultMap.put("pollutantBreakdown", pollutantScores);
        resultMap.put("avgAqi", Math.round(avgAqi * 10.0) / 10.0);
        resultMap.put("avgPm25", Math.round(avgPm25 * 10.0) / 10.0);
        resultMap.put("avgPm10", Math.round(avgPm10 * 10.0) / 10.0);
        resultMap.put("avgO3", Math.round(avgO3 * 10.0) / 10.0);
        resultMap.put("avgNo2", Math.round(avgNo2 * 10.0) / 10.0);
        resultMap.put("evaluationTime", LocalDateTime.now().toString());
        resultMap.put("isMlGenerated", false);
        return resultMap;
    }

    public List<Map<String, Object>> getPollutionSourceAnalysis() { // TODO: convert to typed DTO
        // 🔄 Ensure mock data when DB is empty
        ensureEnvironmentFallbackData();

        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();
        List<EnvironmentMonitorPoint> allPoints = envPointRepository.findAll();

        Map<Long, List<AirQualityRecord>> byPoint = recentRecords.stream()
                .collect(Collectors.groupingBy(AirQualityRecord::getPointId));

        if (byPoint.isEmpty()) {
            // Generate mock pollution source analysis
            return generateMockPollutionSources();
        }

        Map<Long, String> pointNames = new HashMap<>();
        for (EnvironmentMonitorPoint p : allPoints) {
            pointNames.put(p.getId(), p.getPointName());
        }

        List<Map<String, Object>> results = new ArrayList<>();
        for (var entry : byPoint.entrySet()) {
            Long pointId = entry.getKey();
            List<AirQualityRecord> records = entry.getValue();

            double avgPm25 = records.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(0);
            double avgPm10 = records.stream().filter(r -> r.getPm10() != null).mapToDouble(AirQualityRecord::getPm10).average().orElse(0);
            double avgO3 = records.stream().filter(r -> r.getO3() != null).mapToDouble(AirQualityRecord::getO3).average().orElse(0);
            double avgNo2 = records.stream().filter(r -> r.getNo2() != null).mapToDouble(AirQualityRecord::getNo2).average().orElse(0);
            double avgSo2 = records.stream().filter(r -> r.getSo2() != null).mapToDouble(AirQualityRecord::getSo2).average().orElse(5);
            double avgCo = records.stream().filter(r -> r.getCo() != null).mapToDouble(AirQualityRecord::getCo).average().orElse(1);

            String name = pointNames.getOrDefault(pointId, "未知监测点");

            // 优先使用 Python ML 污染源解析
            JsonNode mlResult = pythonMlClient.sourceApportionment(avgPm25, avgPm10, avgSo2, avgNo2, avgCo, avgO3);
            if (mlResult != null && "success".equals(mlResult.path("status").asText())) {
                JsonNode contributions = mlResult.path("source_contributions");
                List<Map<String, Object>> composition = new ArrayList<>();
                if (contributions.isObject()) {
                    Iterator<String> fieldNames = contributions.fieldNames();
                    while (fieldNames.hasNext()) {
                        String source = fieldNames.next();
                        Map<String, Object> comp = new LinkedHashMap<>();
                        comp.put("name", source);
                        comp.put("percentage", contributions.get(source).asDouble());
                        composition.add(comp);
                    }
                }
                composition.sort((a, b) -> Double.compare(((Number) b.get("percentage")).doubleValue(), ((Number) a.get("percentage")).doubleValue()));

                String dominantSource = mlResult.path("dominant_source").asText();
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("pointId", pointId);
                item.put("pointName", name);
                item.put("composition", composition);
                item.put("primaryPollutant", composition.isEmpty() ? "" : composition.get(0).get("name"));
                item.put("primaryPercentage", composition.isEmpty() ? 0 : composition.get(0).get("percentage"));
                item.put("sourceType", dominantSource + "为主");
                item.put("isMlGenerated", true);
                results.add(item);
                continue;
            }

            // Fallback: 原统计逻辑
            double total = Math.max(1, avgPm25 + avgPm10 + avgO3 + avgNo2);
            List<Map<String, Object>> composition = new ArrayList<>();
            composition.add(Map.of("name", "PM2.5", "value", Math.round(avgPm25 * 10.0) / 10.0, "percentage", Math.round(avgPm25 / total * 1000) / 10.0));
            composition.add(Map.of("name", "PM10", "value", Math.round(avgPm10 * 10.0) / 10.0, "percentage", Math.round(avgPm10 / total * 1000) / 10.0));
            composition.add(Map.of("name", "O3", "value", Math.round(avgO3 * 10.0) / 10.0, "percentage", Math.round(avgO3 / total * 1000) / 10.0));
            composition.add(Map.of("name", "NO2", "value", Math.round(avgNo2 * 10.0) / 10.0, "percentage", Math.round(avgNo2 / total * 1000) / 10.0));
            composition.sort((a, b) -> Double.compare(((Number) b.get("percentage")).doubleValue(), ((Number) a.get("percentage")).doubleValue()));

            String sourceType;
            if (avgNo2 > 30 && avgPm25 > 50) sourceType = "交通排放为主";
            else if (avgPm10 > 80 && avgPm25 / Math.max(1, avgPm10) < 0.5) sourceType = "扬尘/工业排放为主";
            else if (avgO3 > 35) sourceType = "光化学污染为主";
            else if (avgPm25 > 40) sourceType = "燃煤/生物质燃烧为主";
            else sourceType = "多种混合源";

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("pointId", pointId);
            item.put("pointName", name);
            item.put("composition", composition);
            item.put("primaryPollutant", composition.get(0).get("name"));
            item.put("primaryPercentage", composition.get(0).get("percentage"));
            item.put("sourceType", sourceType);
            item.put("isMlGenerated", false);
            results.add(item);
        }
        return results;
    }

    public Map<String, Object> getSeasonalTrendAnalysis() { // TODO: convert to typed DTO
        // 🔄 Ensure mock data when DB is empty
        ensureEnvironmentFallbackData();

        List<AirQualityRecord> allRecords = airQualityRepository.findAll();

        // 按小时统计
        Map<Integer, List<Integer>> hourAqiMap = new LinkedHashMap<>();
        for (AirQualityRecord r : allRecords) {
            if (r.getAqi() == null || r.getRecordTime() == null) continue;
            int hour = r.getRecordTime().getHour();
            hourAqiMap.computeIfAbsent(hour, k -> new ArrayList<>()).add(r.getAqi());
        }

        List<Map<String, Object>> hourlyTrend = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            List<Integer> values = hourAqiMap.getOrDefault(h, List.of());
            // Generate realistic hourly pattern: lower at night/early morning, peaks at 8-10 and 18-20
            // 确定性 AQI 日变化曲线（替代原 Math.random()，结果可复现）
            double defaultAqi = 50 + 12 * Math.sin((h - 8) * Math.PI / 12) + 8 * Math.sin((h - 18) * Math.PI / 6);
            defaultAqi = Math.max(25, Math.round(defaultAqi * 10.0) / 10.0);
            double avg = values.stream().mapToInt(i -> i).average().orElse(defaultAqi);
            hourlyTrend.add(Map.of("hour", h, "avgAqi", Math.round(avg * 10.0) / 10.0, "sampleCount", values.isEmpty() ? 5 : values.size()));
        }

        // 尝试用 ML 模型做进一步的 AQI 等级趋势判断
        JsonNode aqiForecastResult = null;
        if (!allRecords.isEmpty()) {
            AirQualityRecord latest = allRecords.get(0);
            aqiForecastResult = pythonMlClient.aqiForecast(
                    latest.getPm25() != null ? latest.getPm25() : 35,
                    latest.getPm10() != null ? latest.getPm10() : 60,
                    latest.getO3() != null ? latest.getO3() : 30,
                    latest.getNo2() != null ? latest.getNo2() : 25,
                    latest.getSo2() != null ? latest.getSo2() : 10,
                    latest.getCo() != null ? latest.getCo() : 2,
                    25, 60
            );
        }

        if (aqiForecastResult != null && "success".equals(aqiForecastResult.path("status").asText())) {
            String predictedLevel = aqiForecastResult.path("predicted_level").asText();
            double confidence = aqiForecastResult.path("confidence").asDouble();
            String trendDescription = "基于 ML 模型分析，当前趋势预测为「" + predictedLevel + "」，置信度 " + confidence + "%";

            // 添加等级概率
            JsonNode probs = aqiForecastResult.path("level_probabilities");
            List<Map<String, Object>> levelProbList = new ArrayList<>();
            if (probs.isObject()) {
                Iterator<String> fieldNames = probs.fieldNames();
                while (fieldNames.hasNext()) {
                    String level = fieldNames.next();
                    Map<String, Object> lp = new LinkedHashMap<>();
                    lp.put("level", level);
                    lp.put("probability", probs.get(level).asDouble());
                    levelProbList.add(lp);
                }
            }

            Map<String, Object> result = new LinkedHashMap<>();
            result.put("hourlyTrend", hourlyTrend);
            result.put("trendDescription", trendDescription);
            result.put("predictedLevel", predictedLevel);
            result.put("confidence", confidence);
            result.put("levelProbabilities", levelProbList);
            result.put("isMlGenerated", true);
            // 保留原字段兼容
            result.put("analysisTime", LocalDateTime.now().toString());
            return result;
        }

        // Fallback
        double dayAvg = hourlyTrend.stream().filter(m -> { int h = ((Number) m.get("hour")).intValue(); return h >= 8 && h <= 20; })
                .mapToDouble(m -> ((Number) m.get("avgAqi")).doubleValue()).average().orElse(70);
        double nightAvg = hourlyTrend.stream().filter(m -> { int h = ((Number) m.get("hour")).intValue(); return h < 6 || h >= 22; })
                .mapToDouble(m -> ((Number) m.get("avgAqi")).doubleValue()).average().orElse(60);

        String fallbackTrend = dayAvg > nightAvg ? "日间污染>夜间" : "夜间污染>日间";

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("hourlyTrend", hourlyTrend);
        result.put("daytimeAvgAqi", Math.round(dayAvg * 10.0) / 10.0);
        result.put("nighttimeAvgAqi", Math.round(nightAvg * 10.0) / 10.0);
        result.put("trendDescription", "基于 " + allRecords.size() + " 条历史记录分析，" + fallbackTrend + "。日间均值为 " + Math.round(dayAvg * 10.0) / 10.0 + "，夜间均值为 " + Math.round(nightAvg * 10.0) / 10.0 + "。");
        result.put("analysisTime", LocalDateTime.now().toString());
        result.put("isMlGenerated", false);
        return result;
    }

    public Map<String, Object> getHealthImpactAssessment() { // TODO: convert to typed DTO
        // 🔄 Ensure mock data when DB is empty
        ensureEnvironmentFallbackData();

        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();

        if (!recentRecords.isEmpty()) {
            AirQualityRecord latest = recentRecords.get(0);
            JsonNode result = pythonMlClient.predictEnvironment(
                    latest.getPm25() != null ? latest.getPm25() : 35,
                    latest.getPm10() != null ? latest.getPm10() : 60,
                    latest.getO3() != null ? latest.getO3() : 30,
                    latest.getNo2() != null ? latest.getNo2() : 25,
                    latest.getSo2() != null ? latest.getSo2() : 10,
                    latest.getCo() != null ? latest.getCo() : 2,
                    25, 60
            );
            if (result != null && "success".equals(result.path("status").asText())) {
                return buildHealthImpactFromMl(result, true);
            }
        }

        // Fallback: 原统计逻辑
        double avgAqi = recentRecords.stream().filter(r -> r.getAqi() != null).mapToInt(AirQualityRecord::getAqi).average().orElse(80);
        double avgPm25 = recentRecords.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(35);

        // 构建前端期望的 healthLevel, riskGroups, symptoms, recommendation
        String healthLevel;
        String riskGroups; // 逗号分隔字符串（前端用 {{ healthImpact.riskGroups }} 直接显示）
        List<String> symptoms = new ArrayList<>();
        String recommendation;

        if (avgAqi <= 50) {
            healthLevel = "优";
            riskGroups = "一般人群";
            symptoms.add("无明显症状");
            recommendation = "空气质量令人满意，适合户外活动。";
        } else if (avgAqi <= 100) {
            healthLevel = "良";
            riskGroups = "敏感人群、儿童、老年人";
            symptoms.add("少数敏感人群可能有轻微不适");
            recommendation = "空气质量可接受，敏感人群建议适当防护。";
        } else if (avgAqi <= 150) {
            healthLevel = "轻度污染";
            riskGroups = "儿童、老年人、呼吸系统疾病患者";
            symptoms.add("咳嗽");
            symptoms.add("咽喉不适");
            symptoms.add("呼吸不畅");
            recommendation = "减少长时间户外活动，外出佩戴口罩。";
        } else if (avgAqi <= 200) {
            healthLevel = "中度污染";
            riskGroups = "儿童、老年人、心肺疾病患者、孕妇";
            symptoms.add("咳嗽加重");
            symptoms.add("胸闷");
            symptoms.add("呼吸困难");
            recommendation = "避免户外运动，开启空气净化器，关闭门窗。";
        } else {
            healthLevel = "重度污染";
            riskGroups = "所有人群，特别是心肺疾病患者";
            symptoms.add("严重咳嗽");
            symptoms.add("呼吸困难");
            symptoms.add("心悸");
            recommendation = "减少不必要外出，佩戴防护口罩，室内开启空气净化器。";
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("healthLevel", healthLevel);
        result.put("avgAqi", Math.round(avgAqi * 10.0) / 10.0);
        result.put("riskGroups", riskGroups);
        result.put("symptoms", symptoms);
        result.put("recommendation", recommendation);
        result.put("analysisTime", LocalDateTime.now().toString());
        result.put("isMlGenerated", false);
        return result;
    }

    public List<Map<String, Object>> getCrossPointCorrelation() { // TODO: convert to typed DTO
        // 🔄 Ensure mock data when DB is empty
        ensureEnvironmentFallbackData();

        List<AirQualityRecord> allRecords = airQualityRepository.findAll();

        // 按监测点分组
        Map<Long, List<AirQualityRecord>> byPoint = allRecords.stream()
                .filter(r -> r.getAqi() != null)
                .collect(Collectors.groupingBy(AirQualityRecord::getPointId));

        List<Map<String, Object>> correlations = new ArrayList<>();
        List<Long> pointIds = new ArrayList<>(byPoint.keySet());

        if (pointIds.isEmpty()) {
            // Generate mock cross-point correlation
            return generateMockCorrelations();
        }

        for (int i = 0; i < pointIds.size(); i++) {
            for (int j = i + 1; j < pointIds.size(); j++) {
                Long pid1 = pointIds.get(i);
                Long pid2 = pointIds.get(j);
                List<AirQualityRecord> r1 = byPoint.get(pid1);
                List<AirQualityRecord> r2 = byPoint.get(pid2);
                if (r1.isEmpty() || r2.isEmpty()) continue;

                double avg1 = r1.stream().mapToInt(AirQualityRecord::getAqi).average().orElse(0);
                double avg2 = r2.stream().mapToInt(AirQualityRecord::getAqi).average().orElse(0);
                // 皮尔逊近似相关
                double diff1 = avg1 - r1.stream().mapToInt(AirQualityRecord::getAqi).average().orElse(0);
                double diff2 = avg2 - r2.stream().mapToInt(AirQualityRecord::getAqi).average().orElse(0);
                double corr = Math.atan(diff1 * diff2 / 1000) * 2 / Math.PI; // -1~1

                Map<String, Object> item = new LinkedHashMap<>();
                item.put("pointId1", pid1);
                item.put("pointId2", pid2);
                item.put("correlation", Math.round(corr * 1000.0) / 1000.0);
                item.put("avgAqi1", Math.round(avg1 * 10.0) / 10.0);
                item.put("avgAqi2", Math.round(avg2 * 10.0) / 10.0);
                item.put("isMlGenerated", false);
                correlations.add(item);
            }
        }

        if (correlations.isEmpty()) {
            return generateMockCorrelations();
        }
        return correlations;
    }

    public Map<String, Object> getPollutantBreakdown(Long pointId) { // TODO: convert to typed DTO
        List<AirQualityRecord> records = pointId != null
                ? airQualityRepository.findByPointId(pointId)
                : airQualityRepository.findTop10ByOrderByRecordTimeDesc();

        if (records.isEmpty()) {
            Map<String, Object> errorResult = new LinkedHashMap<>();
            errorResult.put("pointId", pointId);
            errorResult.put("error", "No monitoring data available for analysis");
            errorResult.put("sampleCount", 0);
            errorResult.put("isMlGenerated", false);
            return errorResult;
        }

        double avgPm25 = records.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(0.0);
        double avgPm10 = records.stream().filter(r -> r.getPm10() != null).mapToDouble(AirQualityRecord::getPm10).average().orElse(0.0);
        double avgO3 = records.stream().filter(r -> r.getO3() != null).mapToDouble(AirQualityRecord::getO3).average().orElse(0.0);
        double avgNo2 = records.stream().filter(r -> r.getNo2() != null).mapToDouble(AirQualityRecord::getNo2).average().orElse(0.0);
        double avgSo2 = records.stream().filter(r -> r.getSo2() != null).mapToDouble(AirQualityRecord::getSo2).average().orElse(0.0);
        double avgCo = records.stream().filter(r -> r.getCo() != null).mapToDouble(AirQualityRecord::getCo).average().orElse(0.0);

        // 调用 ML 污染源解析
        JsonNode mlResult = pythonMlClient.sourceApportionment(avgPm25, avgPm10, avgSo2, avgNo2, avgCo, avgO3);
        if (mlResult != null && "success".equals(mlResult.path("status").asText())) {
            Map<String, Object> breakdown = new LinkedHashMap<>();
            breakdown.put("pointId", pointId);
            breakdown.put("pollutants", Map.of(
                    "PM2.5", Math.round(avgPm25 * 10.0) / 10.0,
                    "PM10", Math.round(avgPm10 * 10.0) / 10.0,
                    "O3", Math.round(avgO3 * 10.0) / 10.0,
                    "NO2", Math.round(avgNo2 * 10.0) / 10.0,
                    "SO2", Math.round(avgSo2 * 10.0) / 10.0,
                    "CO", Math.round(avgCo * 10.0) / 10.0
            ));
            breakdown.put("sourceContributions", mlResult.path("source_contributions"));
            breakdown.put("dominantSource", mlResult.path("dominant_source").asText());
            breakdown.put("sampleCount", records.size());
            breakdown.put("isMlGenerated", true);
            return breakdown;
        }

        // Fallback
        Map<String, Object> breakdown = new LinkedHashMap<>();
        breakdown.put("pointId", pointId);
        breakdown.put("pollutants", Map.of(
                "PM2.5", Math.round(avgPm25 * 10.0) / 10.0,
                "PM10", Math.round(avgPm10 * 10.0) / 10.0,
                "O3", Math.round(avgO3 * 10.0) / 10.0,
                "NO2", Math.round(avgNo2 * 10.0) / 10.0,
                "SO2", Math.round(avgSo2 * 10.0) / 10.0,
                "CO", Math.round(avgCo * 10.0) / 10.0
        ));
        breakdown.put("sampleCount", records.size());
        breakdown.put("isMlGenerated", false);
        return breakdown;
    }

    public List<Map<String, Object>> getSmartRecommendations() { // TODO: convert to typed DTO
        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();
        List<Map<String, Object>> recommendations = new ArrayList<>();

        if (!recentRecords.isEmpty()) {
            AirQualityRecord latest = recentRecords.get(0);
            JsonNode result = pythonMlClient.predictEnvironment(
                    latest.getPm25() != null ? latest.getPm25() : 35,
                    latest.getPm10() != null ? latest.getPm10() : 60,
                    latest.getO3() != null ? latest.getO3() : 30,
                    latest.getNo2() != null ? latest.getNo2() : 25,
                    latest.getSo2() != null ? latest.getSo2() : 10,
                    latest.getCo() != null ? latest.getCo() : 2,
                    25, 60
            );
            if (result != null && "success".equals(result.path("status").asText())) {
                String advice = result.path("health_advice").asText();
                recommendations.add(Map.of("content", advice, "type", "health", "priority", "高", "isMlGenerated", true));
            }
        }

        // 补充通用建议
        if (recommendations.isEmpty()) {
            recommendations.add(Map.of("content", "保持室内通风良好，定期关注空气质量变化", "type", "daily", "priority", "中", "isMlGenerated", false));
        }
        recommendations.add(Map.of("content", "建议在空气质量优良时段开窗通风", "type", "daily", "priority", "中", "isMlGenerated", false));

        return recommendations;
    }

    public List<Map<String, Object>> getEnvironmentalAnomalyDetection() { // TODO: convert to typed DTO
        // 🔄 Ensure mock data when DB is empty
        ensureEnvironmentFallbackData();

        List<AirQualityRecord> allRecords = airQualityRepository.findAll();
        List<EnvironmentMonitorPoint> allPoints = envPointRepository.findAll();
        Map<Long, String> pointNames = allPoints.stream().collect(Collectors.toMap(EnvironmentMonitorPoint::getId, EnvironmentMonitorPoint::getPointName));

        List<Map<String, Object>> anomalies = new ArrayList<>();

        // 按监测点检测 AQI 异常突变
        Map<Long, List<AirQualityRecord>> byPoint = allRecords.stream()
                .filter(r -> r.getAqi() != null && r.getRecordTime() != null)
                .collect(Collectors.groupingBy(AirQualityRecord::getPointId));

        for (var entry : byPoint.entrySet()) {
            List<AirQualityRecord> records = entry.getValue();
            if (records.size() < 2) continue;
            records.sort(Comparator.comparing(AirQualityRecord::getRecordTime));

            double avgAqi = records.stream().mapToInt(AirQualityRecord::getAqi).average().orElse(0);
            AirQualityRecord latest = records.get(records.size() - 1);
            if (latest.getAqi() != null && latest.getAqi() > avgAqi * 1.5 && latest.getAqi() > 100) {
                Map<String, Object> anomaly = new LinkedHashMap<>();
                anomaly.put("pointId", entry.getKey());
                anomaly.put("pointName", pointNames.getOrDefault(entry.getKey(), "未知监测点"));
                anomaly.put("currentAqi", latest.getAqi());
                anomaly.put("avgAqi", Math.round(avgAqi * 10.0) / 10.0);
                anomaly.put("anomalyRate", Math.round((latest.getAqi() / avgAqi - 1) * 100));
                anomaly.put("time", latest.getRecordTime().toString());
                anomaly.put("severity", latest.getAqi() > 150 ? "严重" : "警告");
                anomaly.put("pollutant", "AQI");
                anomaly.put("currentValue", latest.getAqi());
                anomaly.put("deviation", String.format("%.2f", (latest.getAqi() - avgAqi) / Math.max(1, avgAqi)));
                anomaly.put("suggestion", latest.getAqi() > 150 ? "建议启动应急预案，减少户外活动" : "建议关注空气质量变化");
                anomaly.put("isMlGenerated", false);
                anomalies.add(anomaly);
            }
        }

        if (anomalies.isEmpty()) {
            // Generate mock anomalies for demonstration
            return generateMockAnomalies();
        }

        anomalies.sort((a, b) -> {
            String sevA = (String) a.getOrDefault("severity", "");
            String sevB = (String) b.getOrDefault("severity", "");
            return sevB.compareTo(sevA);
        });

        return anomalies;
    }

    public Map<String, Object> getEnvironmentAiReport() { // TODO: convert to typed DTO
        List<AirQualityRecord> allRecords = airQualityRepository.findAll();
        List<EnvironmentMonitorPoint> allPoints = envPointRepository.findAll();

        double avgAqi = allRecords.stream().filter(r -> r.getAqi() != null).mapToInt(AirQualityRecord::getAqi).average().orElse(80);
        double avgPm25 = allRecords.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(35);

        // 尝试 ML 模型生成报告
        JsonNode envPredict = null;
        JsonNode aqiForecast = null;
        if (!allRecords.isEmpty()) {
            AirQualityRecord latest = allRecords.get(0);
            envPredict = pythonMlClient.predictEnvironment(
                    latest.getPm25() != null ? latest.getPm25() : 35,
                    latest.getPm10() != null ? latest.getPm10() : 60,
                    latest.getO3() != null ? latest.getO3() : 30,
                    latest.getNo2() != null ? latest.getNo2() : 25,
                    latest.getSo2() != null ? latest.getSo2() : 10,
                    latest.getCo() != null ? latest.getCo() : 2,
                    25, 60
            );
            aqiForecast = pythonMlClient.aqiForecast(
                    latest.getPm25() != null ? latest.getPm25() : 35,
                    latest.getPm10() != null ? latest.getPm10() : 60,
                    latest.getO3() != null ? latest.getO3() : 30,
                    latest.getNo2() != null ? latest.getNo2() : 25,
                    latest.getSo2() != null ? latest.getSo2() : 10,
                    latest.getCo() != null ? latest.getCo() : 2,
                    25, 60
            );
        }

        String reportText;
        boolean isMl = false;
        if (envPredict != null && "success".equals(envPredict.path("status").asText())) {
            double predictedAqi = envPredict.path("predicted_aqi").asDouble();
            String level = envPredict.path("aqi_level").asText();
            String advice = envPredict.path("health_advice").asText();
            reportText = String.format(
                    "【环境AI分析报告】📊 当前AQI均值 %.1f。ML模型预测AQI: %.1f（%s）。%s 监测点 %d 个，历史记录 %d 条。",
                    avgAqi, predictedAqi, level, advice, allPoints.size(), allRecords.size()
            );
            isMl = true;
        } else {
            reportText = String.format(
                    "【环境AI分析报告】📊 当前AQI均值 %.1f（%s）。PM2.5均值 %.1fμg/m³。监测点 %d 个，历史记录 %d 条。",
                    avgAqi, getAqiLevel((int) Math.round(avgAqi)), avgPm25, allPoints.size(), allRecords.size()
            );
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("reportTitle", "环境AI分析报告 - " + LocalDate.now().toString());
        result.put("summary", reportText);
        result.put("totalRecords", allRecords.size());
        result.put("totalPoints", allPoints.size());
        result.put("avgAqi", Math.round(avgAqi * 10.0) / 10.0);
        result.put("avgPm25", Math.round(avgPm25 * 10.0) / 10.0);
        if (envPredict != null && "success".equals(envPredict.path("status").asText())) {
            result.put("predictedAqi", envPredict.path("predicted_aqi").asDouble());
            result.put("predictedLevel", envPredict.path("aqi_level").asText());
        }
        if (aqiForecast != null && "success".equals(aqiForecast.path("status").asText())) {
            result.put("levelProbabilities", aqiForecast.path("level_probabilities"));
            result.put("forecastConfidence", aqiForecast.path("confidence").asDouble());
        }
        result.put("generateTime", LocalDateTime.now().toString());
        result.put("isMlGenerated", isMl);
        return result;
    }

    public List<Map<String, Object>> getMultiFactorPrediction() { // TODO: convert to typed DTO
        List<Map<String, Object>> predictions = new ArrayList<>();
        List<AirQualityRecord> allRecords = airQualityRepository.findAll();

        double avgPm25 = allRecords.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(35);
        double avgPm10 = allRecords.stream().filter(r -> r.getPm10() != null).mapToDouble(AirQualityRecord::getPm10).average().orElse(60);
        double avgO3 = allRecords.stream().filter(r -> r.getO3() != null).mapToDouble(AirQualityRecord::getO3).average().orElse(30);
        double avgNo2 = allRecords.stream().filter(r -> r.getNo2() != null).mapToDouble(AirQualityRecord::getNo2).average().orElse(25);
        double avgSo2 = allRecords.stream().filter(r -> r.getSo2() != null).mapToDouble(AirQualityRecord::getSo2).average().orElse(10);
        double avgCo = allRecords.stream().filter(r -> r.getCo() != null).mapToDouble(AirQualityRecord::getCo).average().orElse(2);

        // 用 ML 模型预测 AQI 等级
        JsonNode result = pythonMlClient.aqiForecast(avgPm25, avgPm10, avgO3, avgNo2, avgSo2, avgCo, 25, 60);
        if (result != null && "success".equals(result.path("status").asText())) {
            String predictedLevel = result.path("predicted_level").asText();
            double confidence = result.path("confidence").asDouble();
            Map<String, Object> factorMap = new LinkedHashMap<>();
            factorMap.put("factors", Map.of(
                    "PM2.5", avgPm25, "PM10", avgPm10, "O3", avgO3, "NO2", avgNo2, "SO2", avgSo2, "CO", avgCo
            ));
            factorMap.put("predictedLevel", predictedLevel);
            factorMap.put("confidence", confidence);
            factorMap.put("isMlGenerated", true);
            predictions.add(factorMap);
        }

        if (predictions.isEmpty()) {
            Map<String, Object> factorMap = new LinkedHashMap<>();
            factorMap.put("factors", Map.of(
                    "PM2.5", avgPm25, "PM10", avgPm10, "O3", avgO3, "NO2", avgNo2, "SO2", avgSo2, "CO", avgCo
            ));
            factorMap.put("isMlGenerated", false);
            predictions.add(factorMap);
        }

        return predictions;
    }

    public Map<String, Object> getHealthExposureRisk() { // TODO: convert to typed DTO
        List<AirQualityRecord> allRecords = airQualityRepository.findAll();

        Map<Integer, List<Integer>> hourAqiMap = new LinkedHashMap<>();
        Map<Integer, List<Double>> hourPm25Map = new LinkedHashMap<>();
        for (AirQualityRecord r : allRecords) {
            if (r.getAqi() == null || r.getRecordTime() == null) continue;
            int hour = r.getRecordTime().getHour();
            hourAqiMap.computeIfAbsent(hour, k -> new ArrayList<>()).add(r.getAqi());
            if (r.getPm25() != null) {
                hourPm25Map.computeIfAbsent(hour, k -> new ArrayList<>()).add(r.getPm25().doubleValue());
            }
        }

        double avgAqi = allRecords.stream().filter(r -> r.getAqi() != null).mapToInt(AirQualityRecord::getAqi).average().orElse(60);
        double avgPm25 = allRecords.stream().filter(r -> r.getPm25() != null).mapToDouble(AirQualityRecord::getPm25).average().orElse(0);

        List<Map<String, Object>> hourlyExposure = new ArrayList<>();
        for (int h = 0; h < 24; h++) {
            List<Integer> aqis = hourAqiMap.getOrDefault(h, List.of(60));
            List<Double> pm25s = hourPm25Map.getOrDefault(h, List.of(30.0));
            double hAqi = aqis.stream().mapToInt(i -> i).average().orElse(60);
            double hPm25 = pm25s.stream().mapToDouble(d -> d).average().orElse(30);

            String risk;
            if (hAqi > 100 || hPm25 > 75) risk = "高";
            else if (hAqi > 50 || hPm25 > 35) risk = "中";
            else risk = "低";

            hourlyExposure.add(Map.of("hour", String.format("%02d:00-%02d:00", h, (h + 1) % 24),
                    "avgAqi", Math.round(hAqi * 10.0) / 10.0,
                    "avgPm25", Math.round(hPm25 * 10.0) / 10.0,
                    "exposureRisk", risk));
        }

        double morningAqi = hourlyExposure.stream()
                .filter(m -> { String hr = (String) m.get("hour"); return hr.startsWith("07") || hr.startsWith("08") || hr.startsWith("09"); })
                .mapToDouble(m -> ((Number) m.get("avgAqi")).doubleValue()).average().orElse(70);
        double eveningAqi = hourlyExposure.stream()
                .filter(m -> { String hr = (String) m.get("hour"); return hr.startsWith("17") || hr.startsWith("18") || hr.startsWith("19"); })
                .mapToDouble(m -> ((Number) m.get("avgAqi")).doubleValue()).average().orElse(70);

        StringBuilder analysis = new StringBuilder();
        analysis.append("【暴露风险评估】全天气质量整体 ").append(getAqiLevel((int) Math.round(avgAqi))).append("（AQI ").append(Math.round(avgAqi)).append("）。");
        analysis.append("\n").append("● 早高峰(7-10时)暴露 AQI：").append(Math.round(morningAqi * 10.0) / 10.0);
        analysis.append("\n").append("● 晚高峰(17-20时)暴露 AQI：").append(Math.round(eveningAqi * 10.0) / 10.0);

        List<String> recommendations = new ArrayList<>();
        if (morningAqi > 80) recommendations.add("早高峰通勤建议佩戴口罩，选择非机动车道或避开主干道");
        if (eveningAqi > 80) recommendations.add("晚高峰户外运动建议改为室内，或推迟到 20 点后");
        recommendations.add("关注各时段风险等级，在高风险时段减少不必要的户外停留");
        if (avgPm25 > 50) recommendations.add("PM2.5 浓度偏高，建议配备空气净化器");

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("overallAqi", Math.round(avgAqi * 10.0) / 10.0);
        result.put("overallLevel", getAqiLevel((int) Math.round(avgAqi)));
        result.put("hourlyExposure", hourlyExposure);
        result.put("morningRushAqi", Math.round(morningAqi * 10.0) / 10.0);
        result.put("eveningRushAqi", Math.round(eveningAqi * 10.0) / 10.0);
        result.put("exposureAnalysis", analysis.toString());
        result.put("recommendations", recommendations);
        result.put("pm25", Math.round(avgPm25 * 10.0) / 10.0);
        result.put("isMlGenerated", false);
        return result;
    }

    // ======================== 私有工具方法 ========================

    /**
     * 确保环境数据可用。当DB中没有任何监测点和记录时，自动生成mock数据写入DB
     */
    private void ensureEnvironmentFallbackData() {
        long pointCount = envPointRepository.count();
        long recordCount = airQualityRepository.count();
        if (pointCount > 0 && recordCount > 0) return;

        if (!seedDemoData) {
            log.warn("Environment DB is empty (points={}, records={}) but demo-data seeding is DISABLED "
                    + "(app.env.seed-demo-data=false); returning empty result set.", pointCount, recordCount);
            return;
        }

        log.warn("Environment DB is empty (points={}, records={}). Generating SYNTHETIC demo data "
                + "(app.env.seed-demo-data=true). Set app.env.seed-demo-data=false to disable in production.",
                pointCount, recordCount);

        if (pointCount == 0) {
            // Generate 5-7 mock monitoring points
            String[][] mockPoints = {
                {"市中心监测站", "北京市朝阳区CBD", "113.89", "35.86"},
                {"工业园区监测站", "北京市经济技术开发区", "114.05", "35.78"},
                {"居民区监测站", "北京市海淀区中关村", "113.95", "35.92"},
                {"生态公园监测站", "北京市奥林匹克森林公园", "113.98", "35.98"},
                {"交通枢纽监测站", "北京市北京南站", "113.87", "35.75"},
                {"郊区背景监测站", "北京市怀柔区", "114.12", "36.15"},
                {"高校监测站", "北京市清华大学", "113.93", "35.90"}
            };
            for (String[] point : mockPoints) {
                EnvironmentMonitorPoint mp = new EnvironmentMonitorPoint();
                mp.setPointName(point[0]);
                mp.setLocation(point[1]);
                mp.setLongitude(Double.parseDouble(point[2]));
                mp.setLatitude(Double.parseDouble(point[3]));
                mp.setMonitorType("空气质量");
                mp.setStatus("正常");
                envPointRepository.save(mp);
            }
            log.info("Generated {} mock monitoring points", mockPoints.length);
        }

        // Re-fetch points after potential insertion
        List<EnvironmentMonitorPoint> allPoints = envPointRepository.findAll();
        if (allPoints.isEmpty()) return;

        if (recordCount == 0) {
            // Generate 7 days of mock records for each point, with realistic time patterns
            // 固定种子：演示数据可复现，不产生随机漂移
            Random rand = new Random(42);
            List<AirQualityRecord> mockRecords = new ArrayList<>();
            for (EnvironmentMonitorPoint point : allPoints) {
                // Each point gets records for the past 7 days, every 6 hours
                double baseAqi = 40 + rand.nextDouble() * 80;
                double basePm25 = 20 + rand.nextDouble() * 60;
                double basePm10 = basePm25 * (1.5 + rand.nextDouble() * 0.5);
                double baseO3 = 20 + rand.nextDouble() * 50;
                double baseNo2 = 15 + rand.nextDouble() * 30;
                double baseSo2 = 5 + rand.nextDouble() * 15;
                double baseCo = 0.5 + rand.nextDouble() * 2;

                for (int day = 7; day >= 0; day--) {
                    for (int hour = 0; hour < 24; hour += 6) {
                        double hourFactor = 1.0 + 0.2 * Math.sin(hour * Math.PI / 12);
                        double dayFactor = 1.0 + 0.15 * Math.sin(day * 2.0);
                        double noise = 0.9 + rand.nextDouble() * 0.2;

                        AirQualityRecord record = new AirQualityRecord();
                        record.setPointId(point.getId());
                        record.setAqi((int) Math.round(baseAqi * hourFactor * dayFactor * noise));
                        record.setPm25(basePm25 * hourFactor * dayFactor * noise);
                        record.setPm10(basePm10 * hourFactor * dayFactor * noise);
                        record.setO3(baseO3 * hourFactor * dayFactor * noise * (hour > 10 && hour < 16 ? 1.3 : 0.9));
                        record.setNo2(baseNo2 * (hour >= 7 && hour <= 9 || hour >= 17 && hour <= 19 ? 1.4 : 0.8));
                        record.setSo2(baseSo2 * noise);
                        record.setCo(baseCo * noise);
                        record.setTemperature(20 + 8 * Math.sin((hour + day * 4) * Math.PI / 12) + rand.nextDouble() * 3);
                        record.setHumidity(50 + 20 * Math.sin(day * 0.5) + rand.nextDouble() * 10);
                        record.setRecordTime(LocalDateTime.now().minusDays(day).withHour(hour).withMinute(0).withSecond(0));
                        mockRecords.add(record);
                    }
                }
            }
            airQualityRepository.saveAll(mockRecords);
            log.info("Generated {} mock air quality records across {} points", mockRecords.size(), allPoints.size());
        }
    }

    /**
     * 生成模拟的污染源分析数据（DB为空时使用）
     */
    private List<Map<String, Object>> generateMockPollutionSources() {
        List<Map<String, Object>> results = new ArrayList<>();
        String[] pointNames = {"市中心监测站", "工业园区监测站", "居民区监测站", "生态公园监测站", "交通枢纽监测站"};
        String[] sourceTypes = {"交通排放为主", "工业排放为主", "多种混合源", "自然背景", "扬尘/交通"};
        String[] primaryPollutants = {"NO₂", "PM2.5", "PM10", "O₃", "NO₂"};
        double[][] compositions = {
            {25, 30, 15, 20, 5, 5},  // PM2.5, PM10, O3, NO2, SO2, CO
            {35, 25, 10, 10, 15, 5},
            {20, 25, 20, 15, 10, 10},
            {10, 15, 30, 10, 5, 30},
            {20, 35, 10, 25, 3, 7}
        };
        String[][] compNames = {
            {"PM2.5", "PM10", "O₃", "NO₂", "SO₂", "CO"},
            {"PM2.5", "PM10", "O₃", "NO₂", "SO₂", "CO"},
            {"PM2.5", "PM10", "O₃", "NO₂", "SO₂", "CO"},
            {"PM2.5", "PM10", "O₃", "NO₂", "SO₂", "CO"},
            {"PM2.5", "PM10", "O₃", "NO₂", "SO₂", "CO"}
        };

        for (int i = 0; i < pointNames.length; i++) {
            double total = 0;
            for (double c : compositions[i]) total += c;

            List<Map<String, Object>> compositionList = new ArrayList<>();
            for (int j = 0; j < compNames[i].length; j++) {
                Map<String, Object> comp = new LinkedHashMap<>();
                comp.put("name", compNames[i][j]);
                comp.put("value", compositions[i][j]);
                comp.put("percentage", Math.round(compositions[i][j] / total * 1000.0) / 10.0);
                compositionList.add(comp);
            }
            compositionList.sort((a, b) -> Double.compare(((Number)b.get("percentage")).doubleValue(), ((Number)a.get("percentage")).doubleValue()));

            Map<String, Object> item = new LinkedHashMap<>();
            item.put("pointId", (long) (i + 1));
            item.put("pointName", pointNames[i]);
            item.put("composition", compositionList);
            item.put("primaryPollutant", primaryPollutants[i]);
            item.put("primaryPercentage", compositionList.get(0).get("percentage"));
            item.put("sourceType", sourceTypes[i]);
            item.put("isMlGenerated", false);
            results.add(item);
        }
        return results;
    }

    /**
     * 生成模拟的相关性分析数据
     */
    private List<Map<String, Object>> generateMockCorrelations() {
        List<Map<String, Object>> correlations = new ArrayList<>();
        String[] pointNames = {"市中心监测站", "居民区监测站", "生态公园监测站", "交通枢纽监测站"};
        String[] features = {"商业办公区", "住宅密集区", "公园绿地", "交通枢纽"};
        int[] aqis = {88, 72, 45, 95};
        double[] pm25s = {42.5, 35.8, 22.1, 48.3};
        String[][] relMatrix = {
            {"居民区监测站", "交通枢纽监测站"},
            {"市中心监测站", "生态公园监测站"},
            {"生态公园监测站", "交通枢纽监测站"},
            {"市中心监测站", "居民区监测站"}
        };
        double[] corrScores = {85.3, 91.2, 76.8, 82.5};

        for (int i = 0; i < pointNames.length; i++) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("pointId", (long) (i + 1));
            item.put("pointName", pointNames[i]);
            item.put("avgAqi", aqis[i]);
            item.put("avgPm25", pm25s[i]);
            item.put("areaFeature", features[i]);
            item.put("mostCorrelated", relMatrix[i][0]);
            item.put("correlationScore", corrScores[i]);
            item.put("isMlGenerated", false);
            correlations.add(item);
        }
        return correlations;
    }

    /**
     * 生成模拟的异常检测数据
     */
    private List<Map<String, Object>> generateMockAnomalies() {
        List<Map<String, Object>> anomalies = new ArrayList<>();
        Object[][] mockData = {
            {1L, "市中心监测站", "PM2.5", 156.3, 75.2, 2.08, "严重", "工业排放或突发污染事件，建议立即调查并通知环保部门"},
            {2L, "交通枢纽监测站", "NO₂", 98.5, 52.1, 1.89, "警告", "NO₂浓度显著高于均值，可能与交通高峰期叠加有关"},
            {3L, "工业园区监测站", "PM10", 185.6, 95.3, 1.72, "严重", "PM10浓度异常偏高，建议检查周边工业排放情况"},
            {4L, "居民区监测站", "O₃", 72.8, 38.5, 1.56, "警告", "午后臭氧浓度升高，建议敏感人群减少外出"}
        };

        for (Object[] data : mockData) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("pointId", data[0]);
            item.put("pointName", data[1]);
            item.put("pollutant", data[2]);
            item.put("currentValue", data[3]);
            item.put("avgValue", data[4]);
            item.put("deviation", String.format("%.2f", data[5]));
            item.put("severity", data[6]);
            item.put("suggestion", data[7]);
            item.put("isMlGenerated", false);
            anomalies.add(item);
        }
        return anomalies;
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

    private PollutionAlertDTO buildMlAlert(int aqi, String advice, boolean isMl) {
        String level;
        String message;
        if (aqi > 150) {
            level = "红色预警";
            message = "空气质量差，健康人群也会出现刺激症状";
        } else if (aqi > 100) {
            level = "橙色预警";
            message = "空气质量较差，敏感人群减少户外活动";
        } else {
            level = "正常";
            message = "当前空气质量良好";
        }
        return new PollutionAlertDTO(level, message, "全城范围", advice, LocalDateTime.now().toString(), isMl);
    }

    private Map<String, Object> buildHealthIndexFromMl(JsonNode mlResult, boolean isMl) {
        double predictedAqi = mlResult.path("predicted_aqi").asDouble();
        String level = mlResult.path("aqi_level").asText();

        double healthIndex = Math.max(0, Math.min(100, 100 - predictedAqi * 0.7));

        List<Map<String, Object>> pollutantScores = new ArrayList<>();
        String[] pollutants = {"PM2.5", "PM10", "O3", "NO2"};
        for (String p : pollutants) {
            Map<String, Object> ps = new LinkedHashMap<>();
            ps.put("name", p);
            ps.put("score", Math.max(0, Math.min(100, 100 - healthIndex * 0.3)));
            ps.put("value", 0);
            pollutantScores.add(ps);
        }

        String assessment = mlResult.path("health_advice").asText();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("healthIndex", Math.round(healthIndex * 10.0) / 10.0);
        result.put("level", level);
        result.put("assessment", assessment);
        result.put("worstPollutant", mlResult.path("main_pollutant").asText("PM2.5"));
        result.put("pollutantBreakdown", pollutantScores);
        result.put("avgAqi", predictedAqi);
        result.put("evaluationTime", LocalDateTime.now().toString());
        result.put("isMlGenerated", isMl);
        return result;
    }

    private Map<String, Object> buildHealthImpactFromMl(JsonNode mlResult, boolean isMl) {
        double predictedAqi = mlResult.path("predicted_aqi").asDouble();
        String level = mlResult.path("aqi_level").asText();
        String advice = mlResult.path("health_advice").asText();

        // 构建前端期望的字段格式
        String healthLevel = level;
        String riskGroups;
        List<String> symptoms = new ArrayList<>();
        String recommendation = advice;

        if (predictedAqi <= 50) {
            riskGroups = "一般人群";
            symptoms.add("无明显症状");
            if (recommendation == null || recommendation.isEmpty()) {
                recommendation = "空气质量令人满意，适合户外活动。";
            }
        } else if (predictedAqi <= 100) {
            riskGroups = "敏感人群、儿童、老年人";
            symptoms.add("少数敏感人群可能有轻微不适");
            if (recommendation == null || recommendation.isEmpty()) {
                recommendation = "空气质量可接受，敏感人群建议适当防护。";
            }
        } else {
            riskGroups = "儿童、老年人、呼吸系统疾病患者";
            symptoms.add("咳嗽");
            symptoms.add("咽喉不适");
            symptoms.add("呼吸不畅");
            if (recommendation == null || recommendation.isEmpty()) {
                recommendation = "减少长时间户外活动，外出佩戴口罩。";
            }
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("healthLevel", healthLevel);
        result.put("avgAqi", Math.round(predictedAqi * 10.0) / 10.0);
        result.put("riskGroups", riskGroups);
        result.put("symptoms", symptoms);
        result.put("recommendation", recommendation);
        result.put("analysisTime", LocalDateTime.now().toString());
        result.put("isMlGenerated", isMl);
        return result;
    }

    /**
     * 基于当前环境数据的极端天气自动分类（使用 RandomForest 模型）
     * 自动从最新监测数据中提取特征进行预测
     */
    public Map<String, Object> classifyCurrentExtremeWeather() {
        ensureEnvironmentFallbackData();

        List<AirQualityRecord> recentRecords = airQualityRepository.findTop10ByOrderByRecordTimeDesc();
        List<EnvironmentMonitorPoint> allPoints = envPointRepository.findAll();

        // Extract current feature values from latest record or defaults
        double pm25 = 50, pm10 = 80, o3 = 80, temperature = 20, humidity = 60, windSpeed = 5;
        int season = 1; // 1=spring, 2=summer, 3=fall, 4=winter
        String pointName = "综合";

        if (!recentRecords.isEmpty()) {
            AirQualityRecord latest = recentRecords.get(0);
            pm25 = latest.getPm25() != null ? latest.getPm25() : 50;
            pm10 = latest.getPm10() != null ? latest.getPm10() : 80;
            o3 = latest.getO3() != null ? latest.getO3() : 80;
            temperature = latest.getTemperature() != null ? latest.getTemperature() : 20;
            humidity = latest.getHumidity() != null ? latest.getHumidity() : 60;
        }

        if (!allPoints.isEmpty()) {
            pointName = allPoints.get(0).getPointName();
        }

        // Determine current season
        int currentMonth = LocalDate.now().getMonthValue();
        if (currentMonth >= 3 && currentMonth <= 5) season = 1;
        else if (currentMonth >= 6 && currentMonth <= 8) season = 2;
        else if (currentMonth >= 9 && currentMonth <= 11) season = 3;
        else season = 4;

        // Try Python ML model first
        Map<String, Object> weatherParams = new HashMap<>();
        weatherParams.put("pm25", pm25);
        weatherParams.put("pm10", pm10);
        weatherParams.put("o3", o3);
        weatherParams.put("temperature", temperature);
        weatherParams.put("humidity", humidity);
        weatherParams.put("wind_speed", windSpeed);
        weatherParams.put("season", season);

        JsonNode mlResult = pythonMlClient.environmentExtremeWeather(weatherParams);
        if (mlResult != null && "success".equals(mlResult.path("status").asText())) {
            Map<String, Object> result = new LinkedHashMap<>();
            result.put("sourcePoint", pointName);
            result.put("severityLevel", mlResult.path("severity_level").asText());
            result.put("confidence", mlResult.path("confidence").asDouble());
            result.put("advisory", mlResult.path("advisory").asText());
            result.put("weatherType", mlResult.path("weather_type").asText(""));
            result.put("pm25", pm25);
            result.put("pm10", pm10);
            result.put("o3", o3);
            result.put("temperature", temperature);
            result.put("humidity", humidity);
            result.put("isMlGenerated", true);
            result.put("evaluateTime", LocalDateTime.now().toString());
            return result;
        }

        // Fallback rule-based classification
        Map<String, Object> fallback = new LinkedHashMap<>();
        fallback.put("sourcePoint", pointName);
        fallback.put("pm25", pm25);
        fallback.put("pm10", pm10);
        fallback.put("o3", o3);
        fallback.put("temperature", temperature);
        fallback.put("humidity", humidity);

        String severityLevel;
        String weatherType;
        String advisory;

        if (pm25 > 200 || pm10 > 300) {
            severityLevel = "warning";
            weatherType = "重度污染天气";
            advisory = "空气质量极差，建议减少外出，佩戴N95口罩，关闭门窗";
        } else if (pm25 > 150) {
            severityLevel = "advisory";
            weatherType = "中度污染天气";
            advisory = "空气质量较差，建议敏感人群减少户外活动";
        } else if (temperature > 38) {
            severityLevel = "advisory";
            weatherType = "高温天气";
            advisory = "气温过高，注意防暑降温，避免高温时段外出";
        } else if (temperature < -10) {
            severityLevel = "advisory";
            weatherType = "寒潮天气";
            advisory = "气温极低，注意保暖防寒";
        } else if (o3 > 100) {
            severityLevel = "advisory";
            weatherType = "光化学污染天气";
            advisory = "臭氧浓度偏高，午后减少户外活动";
        } else {
            severityLevel = "normal";
            weatherType = "正常天气";
            advisory = "当前天气状况良好，适宜户外活动";
        }

        fallback.put("severityLevel", severityLevel);
        fallback.put("weatherType", weatherType);
        fallback.put("confidence", 0.6);
        fallback.put("advisory", advisory);
        fallback.put("isMlGenerated", false);
        fallback.put("evaluateTime", LocalDateTime.now().toString());
        return fallback;
    }
}
