package com.aiempowerment.platform.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import org.springframework.web.util.UriComponentsBuilder;


/**
 * Python ML Server HTTP 客户端
 * <p>
 * 调用 Flask ML Server (localhost:5001) 的所有 18+ 个 ML 模型端点
 * V1: 3 个核心预测端点 (medical/finance/environment)
 * V2: 15 个扩展端点 (医疗6 + 金融6 + 环境3)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PythonMlClient {

    private final RestTemplate pythonMlRestTemplate;
    private final ObjectMapper objectMapper;

    @Value("${python.ml.server-url:http://localhost:5001}")
    private String serverUrl;

    // ==================== 通用方法 ====================

    private JsonNode postForJson(String endpoint, Map<String, Object> body) {
        try {
            String url = serverUrl + endpoint;
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);
            ResponseEntity<String> response = pythonMlRestTemplate.exchange(url, HttpMethod.POST, request, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            log.warn("Python ML Server [{}] 调用失败: {}", endpoint, e.getMessage());
            return null;
        }
    }

    /**
     * 通用 GET 请求 — 与 postForJson 保持一致的容错语义：
     * 下游非 2xx 或异常时仅记日志并返回 null，交由调用方处理，
     * 避免下游 4xx/连接失败冒泡为带堆栈的 500。
     */
    private JsonNode getForJson(String endpoint) {
        try {
            String url = serverUrl + endpoint;
            ResponseEntity<String> response = pythonMlRestTemplate.getForEntity(url, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            log.warn("Python ML Server [{}] 调用失败: {}", endpoint, e.getMessage());
            return null;
        }
    }

    /**
     * 通用代理请求 (用于 CT 工作站等复杂端点)
     */
    public JsonNode proxyRequest(String path, String method, String requestBody) {
        try {
            String url = serverUrl + path;
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            
            HttpMethod httpMethod = HttpMethod.valueOf(method.toUpperCase());
            HttpEntity<String> request = new HttpEntity<>(requestBody, headers);
            
            ResponseEntity<String> response = pythonMlRestTemplate.exchange(
                url, httpMethod, request, String.class);
            return objectMapper.readTree(response.getBody());
        } catch (Exception e) {
            log.warn("Python ML Server proxy [{}] 调用失败: {}", path, e.getMessage());
            return null;
        }
    }

    // ==================== V1 核心端点 ====================

    /**
     * ✅ 医疗症状诊断
     * POST /api/predict/medical
     * 输入: {symptoms: "..."} → 输出: {disease, confidence, department, severity, suggestions}
     */
    public JsonNode predictMedical(String symptoms) {
        Map<String, Object> body = new HashMap<>();
        body.put("symptoms", symptoms);
        return postForJson("/api/predict/medical", body);
    }

    /**
     * ✅ 金融交易风险评分
     * POST /api/predict/finance
     * 输入: {amount, hour_of_day, day_of_week, transaction_count_24h, avg_amount_7d, ...}
     * 输出: {risk_score, risk_level, is_anomaly}
     */
    public JsonNode predictFinance(double amount, int hourOfDay, int dayOfWeek,
                                   int transactionCount24h, double avgAmount7d,
                                   int isWeekend, int userAge,
                                   double balanceRatio, double deviceScore) {
        Map<String, Object> body = new HashMap<>();
        body.put("amount", amount);
        body.put("hour_of_day", hourOfDay);
        body.put("day_of_week", dayOfWeek);
        body.put("transaction_count_24h", transactionCount24h);
        body.put("avg_amount_7d", avgAmount7d);
        body.put("is_weekend", isWeekend);
        body.put("user_age", userAge);
        body.put("balance_ratio", balanceRatio);
        body.put("device_score", deviceScore);
        return postForJson("/api/predict/finance", body);
    }

    /**
     * ✅ AQI 空气质量预测
     * POST /api/predict/environment
     * 输入: {pm25, pm10, o3, no2, so2, co, temperature, humidity}
     * 输出: {predicted_aqi, aqi_level, main_pollutant, health_advice}
     */
    public JsonNode predictEnvironment(double pm25, double pm10, double o3,
                                       double no2, double so2, double co,
                                       double temperature, double humidity) {
        Map<String, Object> body = new HashMap<>();
        body.put("pm25", pm25);
        body.put("pm10", pm10);
        body.put("o3", o3);
        body.put("no2", no2);
        body.put("so2", so2);
        body.put("co", co);
        body.put("temperature", temperature);
        body.put("humidity", humidity);
        return postForJson("/api/predict/environment", body);
    }

    // ==================== V2 医疗端点 ====================

    /**
     * ✅ 语义搜索
     * POST /api/v2/medical/semantic-search
     */
    public JsonNode semanticSearch(String query) {
        Map<String, Object> body = new HashMap<>();
        body.put("query", query);
        return postForJson("/api/v2/medical/semantic-search", body);
    }

    // ==================== V2 金融端点 ====================

    /**
     * ✅ 客户分群
     * POST /api/v2/finance/customer-segments
     */
    public JsonNode customerSegments(double avgAmount, int transactionFreq,
                                     double typeDistribution, int activeHour,
                                     double balanceVolatility) {
        Map<String, Object> body = new HashMap<>();
        body.put("avg_amount", avgAmount);
        body.put("transaction_freq", transactionFreq);
        body.put("type_distribution", typeDistribution);
        body.put("active_hour", activeHour);
        body.put("balance_volatility", balanceVolatility);
        return postForJson("/api/v2/finance/customer-segments", body);
    }

    /**
     * ✅ 欺诈检测
     * POST /api/v2/finance/fraud-detect
     */
    public JsonNode fraudDetect(double amount, double distanceFromLast,
                                double timeGap, double amountDeviation,
                                double deviceScore, int isNight,
                                int isInternational) {
        Map<String, Object> body = new HashMap<>();
        body.put("amount", amount);
        body.put("distance_from_last", distanceFromLast);
        body.put("time_gap", timeGap);
        body.put("amount_deviation", amountDeviation);
        body.put("device_score", deviceScore);
        body.put("is_night", isNight);
        body.put("is_international", isInternational);
        return postForJson("/api/v2/finance/fraud-detect", body);
    }

    /**
     * ✅ 财务健康评估
     * POST /api/v2/finance/financial-health
     */
    public JsonNode financialHealth(double monthlyIncome, double monthlyExpense,
                                    double totalSavings, double totalDebt,
                                    int nInvestmentTypes, int yearsEmployed,
                                    int emergencyFundMonths,
                                    double incomeExpenseRatio, double savingsRate,
                                    int investmentDiversity, double debtRatio,
                                    double financialStability) {
        Map<String, Object> body = new HashMap<>();
        body.put("monthly_income", monthlyIncome);
        body.put("monthly_expense", monthlyExpense);
        body.put("total_savings", totalSavings);
        body.put("total_debt", totalDebt);
        body.put("n_investment_types", nInvestmentTypes);
        body.put("years_employed", yearsEmployed);
        body.put("emergency_fund_months", emergencyFundMonths);
        body.put("income_expense_ratio", incomeExpenseRatio);
        body.put("savings_rate", savingsRate);
        body.put("investment_diversity", investmentDiversity);
        body.put("debt_ratio", debtRatio);
        body.put("financial_stability", financialStability);
        return postForJson("/api/v2/finance/financial-health", body);
    }

    /**
     * ✅ 市场趋势预测
     * POST /api/v2/finance/market-trend
     */
    public JsonNode marketTrend(List<Double> pastData) {
        Map<String, Object> body = new HashMap<>();
        body.put("past_data", pastData);
        return postForJson("/api/v2/finance/market-trend", body);
    }

    // ==================== V2 环境端点 ====================

    /**
     * ✅ 污染源解析
     * POST /api/v2/environment/source-apportionment
     */
    public JsonNode sourceApportionment(double pm25, double pm10, double so2,
                                        double no2, double co, double o3) {
        Map<String, Object> body = new HashMap<>();
        body.put("pm25", pm25);
        body.put("pm10", pm10);
        body.put("so2", so2);
        body.put("no2", no2);
        body.put("co", co);
        body.put("o3", o3);
        return postForJson("/api/v2/environment/source-apportionment", body);
    }

    /**
     * ✅ AQI 等级分类预测
     * POST /api/v2/environment/aqi-forecast
     */
    public JsonNode aqiForecast(double pm25, double pm10, double o3,
                                double no2, double so2, double co,
                                double temperature, double humidity) {
        Map<String, Object> body = new HashMap<>();
        body.put("pm25", pm25);
        body.put("pm10", pm10);
        body.put("o3", o3);
        body.put("no2", no2);
        body.put("so2", so2);
        body.put("co", co);
        body.put("temperature", temperature);
        body.put("humidity", humidity);
        return postForJson("/api/v2/environment/aqi-forecast", body);
    }

    /**
     * ✅ 碳排放估算
     * POST /api/v2/environment/carbon-estimate
     */
    public JsonNode carbonEstimate(double electricity, double coal, double oil,
                                   double naturalGas, double productionScale,
                                   double efficiency, int season) {
        Map<String, Object> body = new HashMap<>();
        body.put("electricity", electricity);
        body.put("coal", coal);
        body.put("oil", oil);
        body.put("natural_gas", naturalGas);
        body.put("production_scale", productionScale);
        body.put("efficiency", efficiency);
        body.put("season", season);
        return postForJson("/api/v2/environment/carbon-estimate", body);
    }

    // ==================== V2 交通端点 ====================

    /**
     * 🚗 逐小时流量预测
     * POST /api/v2/traffic/hourly-flow
     * 输出: 24小时逐小时流量、速度、拥堵等级
     */
    public JsonNode trafficHourlyFlow(int dayOfWeek, int isWeekend, int isHoliday,
                                       int season, int weatherCode, int sectionCapacity,
                                       int lanes, int speedLimit, int roadType) {
        Map<String, Object> body = new HashMap<>();
        body.put("day_of_week", dayOfWeek);
        body.put("is_weekend", isWeekend);
        body.put("is_holiday", isHoliday);
        body.put("season", season);
        body.put("weather_code", weatherCode);
        body.put("section_capacity", sectionCapacity);
        body.put("lanes", lanes);
        body.put("speed_limit", speedLimit);
        body.put("road_type", roadType);
        return postForJson("/api/v2/traffic/hourly-flow", body);
    }

    // ==================== V2 教育端点 ====================

    /**
     * 📚 教育评估预测
     * POST /api/v2/education/predict
     * 输入: difficulty_num, student_level_num, hours_per_week, assignment_submit_rate, quiz_attempts, forum_posts, subject
     * 输出: {avg_score, completion_rate, engagement_level, recommendation_score, ...}
     */
    // ==================== V3 医疗真实数据端点 ====================

    /**
     * 🩺 糖尿病风险预测 (基于真实 PIMA 数据)
     * POST /api/v3/medical/diabetes-risk
     * 输入: {pregnancies, glucose, blood_pressure, skin_thickness, insulin, bmi, diabetes_pedigree, age}
     * 输出: {risk_probability, risk_level, health_advice, key_factors, ...}
     */
    public JsonNode diabetesRiskPredict(double pregnancies, double glucose,
                                         double bloodPressure, double skinThickness,
                                         double insulin, double bmi,
                                         double diabetesPedigree, double age) {
        Map<String, Object> body = new HashMap<>();
        body.put("pregnancies", pregnancies);
        body.put("glucose", glucose);
        body.put("blood_pressure", bloodPressure);
        body.put("skin_thickness", skinThickness);
        body.put("insulin", insulin);
        body.put("bmi", bmi);
        body.put("diabetes_pedigree", diabetesPedigree);
        body.put("age", age);
        return postForJson("/api/v3/medical/diabetes-risk", body);
    }

    /**
     * 🩺 血糖时序预测 (基于真实 CGM 数据)
     * POST /api/v3/medical/glucose-forecast
     * 输入: {readings: [12个历史血糖值], predict_minutes: 30|60}
     * 输出: {current_glucose, forecast_glucose, trend, alert, chart_data, ...}
     */
    public JsonNode glucoseForecastPredict(List<Double> readings, int predictMinutes) {
        Map<String, Object> body = new HashMap<>();
        body.put("readings", readings);
        body.put("predict_minutes", predictMinutes);
        return postForJson("/api/v3/medical/glucose-forecast", body);
    }

    /**
     * 🩺 血糖时序预测 (代理模式 — 接受前端简化字段直接转发)
     * POST /api/v3/medical/glucose-forecast
     * 输入: {current_glucose, prediction_minutes, postprandial_hours, avg_glucose_3d, hba1c}
     * 将前端字段原样传递到Python，由Python处理两种输入格式
     */
    public JsonNode proxyGlucoseForecast(Map<String, Object> params) {
        return postForJson("/api/v3/medical/glucose-forecast", params);
    }

    /**
     * 🖥️ CT 影像工作站代理 (替换旧 brain-ct)
     * 转发到 Python 服务器的 /api/ct/* 端点
     */
    public JsonNode ctWorkstationProxy(String ctPath, String method, String requestBody) {
        // ctPath = /ct/ai-analyze 等, 需要转为 /api/medical/ct/ai-analyze
        // 注意 Python Flask Blueprint 注册为 url_prefix='/api/medical/ct'
        String apiPath = ctPath.replaceFirst("/ct", "/api/medical/ct");
        return proxyRequest(apiPath, method, requestBody);
    }

    // educationPredict 已移除（教育模块已删除）

    // ==================== V3 医疗新增数据端点 (GET) ====================

    /**
     * 🩺 PIMA 胰岛素-血糖相关性分析
     * GET /medical/v3/insulin-glucose-correlation
     * 输出: {correlation_coefficient, p_value, significant, scatter_data, summary}
     */
    public JsonNode insulinGlucoseCorrelation() {
        return getForJson("/api/medical/v3/insulin-glucose-correlation");
    }

    /**
     * 🩺 获取所有葡萄糖患者概览
     * GET /medical/v3/glucose-patients
     * 输出: {patients: [{id, file, samples, mean_glucose, ...}]}
     */
    public JsonNode glucosePatients() {
        return getForJson("/api/medical/v3/glucose-patients");
    }

    /**
     * 🩺 获取指定患者的完整血糖时序数据
     * GET /medical/v3/glucose-patient/{patientId}
     * 输出: {patient_id, readings, stats}
     */
    public JsonNode glucosePatientDetail(String patientId) {
        return getForJson("/api/medical/v3/glucose-patient/" + patientId);
    }

    // ==================== V5 交通增强模型 (拥堵/异常/天气/事故/场景) ====================

    /**
     * 🚗 V5 逐小时拥堵预测 (XGBoost)
     * POST /api/v5/traffic/hourly-forecast
     * 输入: {day_of_week, month, is_weekend, is_holiday, weather_code, temperature, humidity, lanes, speed_limit, road_type}
     * 输出: {hourly_data: [{hour, estimatedFlow, estimatedSpeed, congestionLevel}], summary}
     */
    public JsonNode v5TrafficHourlyForecast(int dayOfWeek, int month, int isWeekend,
                                             int isHoliday, int weatherCode,
                                             double temperature, double humidity,
                                             int lanes, int speedLimit, int roadType) {
        Map<String, Object> body = new HashMap<>();
        body.put("day_of_week", dayOfWeek);
        body.put("month", month);
        body.put("is_weekend", isWeekend);
        body.put("is_holiday", isHoliday);
        body.put("weather_code", weatherCode);
        body.put("temperature", temperature);
        body.put("humidity", humidity);
        body.put("lanes", lanes);
        body.put("speed_limit", speedLimit);
        body.put("road_type", roadType);
        return postForJson("/api/v5/traffic/hourly-forecast", body);
    }

    /**
     * 🚨 V5 异常检测增强 (Isolation Forest)
     * POST /api/v5/traffic/anomaly-enhanced
     * 输入: {records: [{section_id, hour, day_of_week, flow_mean, flow_std, speed_mean, speed_std, flow_count, avg_speed, ...}]}
     * 输出: {anomalies, count}
     */
    public JsonNode v5TrafficAnomalyEnhanced(List<Map<String, Object>> records) {
        Map<String, Object> body = new HashMap<>();
        body.put("records", records);
        return postForJson("/api/v5/traffic/anomaly-enhanced", body);
    }

    /**
     * 🌤️ V5 天气-交通影响 (XGBoost)
     * POST /api/v5/traffic/weather-impact
     * 输入: {road_type, hour, temperature, humidity}
     * 输出: {results: [{weather_code, weather_name, predicted_flow, predicted_speed, congestion_risk}]}
     */
    public JsonNode v5TrafficWeatherImpact(int roadType, int hour,
                                            double temperature, double humidity) {
        Map<String, Object> body = new HashMap<>();
        body.put("road_type", roadType);
        body.put("hour", hour);
        body.put("temperature", temperature);
        body.put("humidity", humidity);
        return postForJson("/api/v5/traffic/weather-impact", body);
    }

    /**
     * 🚧 V5 事故影响预测 (GradientBoosting)
     * POST /api/v5/traffic/accident-impact
     * 输入: {section_id, road_type, lanes, speed_limit, hour, day_of_week, accident_severity, normal_flow, normal_speed}
     * 输出: {flow_reduction_pct, speed_reduction_pct, predicted_flow, predicted_speed}
     */
    public JsonNode v5TrafficAccidentImpact(int sectionId, int roadType, int lanes,
                                             int speedLimit, int hour, int dayOfWeek,
                                             double accidentSeverity,
                                             double normalFlow, double normalSpeed) {
        Map<String, Object> body = new HashMap<>();
        body.put("section_id", sectionId);
        body.put("road_type", roadType);
        body.put("lanes", lanes);
        body.put("speed_limit", speedLimit);
        body.put("hour", hour);
        body.put("day_of_week", dayOfWeek);
        body.put("accident_severity", accidentSeverity);
        body.put("normal_flow", normalFlow);
        body.put("normal_speed", normalSpeed);
        return postForJson("/api/v5/traffic/accident-impact", body);
    }

    /**
     * 🔧 V5 场景仿真 (XGBoost)
     * POST /api/v5/traffic/scenario-simulate
     * 输入: {change_type, change_value, road_type, lanes, speed_limit, hour, day_of_week, base_flow, base_speed}
     * 输出: {impact_description, recommendation, predicted_flow, predicted_speed, ...}
     */
    public JsonNode v5TrafficScenarioSimulate(String changeType, int changeValue,
                                               int roadType, int lanes, int speedLimit,
                                               int hour, int dayOfWeek,
                                               double baseFlow, double baseSpeed) {
        Map<String, Object> body = new HashMap<>();
        body.put("change_type", changeType);
        body.put("change_value", changeValue);
        body.put("road_type", roadType);
        body.put("lanes", lanes);
        body.put("speed_limit", speedLimit);
        body.put("hour", hour);
        body.put("day_of_week", dayOfWeek);
        body.put("base_flow", baseFlow);
        body.put("base_speed", baseSpeed);
        return postForJson("/api/v5/traffic/scenario-simulate", body);
    }

    // ==================== V4 增强模块端点 (Energy/Forum/Dev/Traffic/Finance/Environment) ====================

    /**
     * ⚡ 能源负荷预测 (LSTM)
     * POST /api/v2/energy/load-forecast
     * 输入: {historical_loads: [48 values], current_hour, base_load, ...}
     * 输出: {predictions, peak_load, peak_hour, total_kwh, trend}
     */
    public JsonNode energyLoadForecast(List<Double> historicalLoads, int currentHour,
                                        Double baseLoad) {
        Map<String, Object> body = new HashMap<>();
        if (historicalLoads != null && !historicalLoads.isEmpty()) {
            body.put("historical_loads", historicalLoads);
        }
        body.put("current_hour", currentHour);
        body.put("base_load", baseLoad != null ? baseLoad : 150);
        return postForJson("/api/v2/energy/load-forecast", body);
    }

    /**
     * ⚡ 能源设备故障预测 (XGBoost)
     * POST /api/v2/energy/device-failure-predict
     * 输入: 设备运行参数
     * 输出: {failure_probability, risk_level, recommendations}
     */
    public JsonNode energyDeviceFailurePredict(Map<String, Object> deviceParams) {
        return postForJson("/api/v2/energy/device-failure-predict", deviceParams);
    }

    /**
     * 💬 论坛内容质量评分与分类 (NLP)
     * POST /api/v2/forum/analyze-content
     * 输入: {title, body}
     * 输出: {quality_score, category, confidence, key_topics}
     */
    public JsonNode forumAnalyzeContent(String title, String body) {
        Map<String, Object> params = new HashMap<>();
        params.put("title", title != null ? title : "");
        params.put("body", body != null ? body : "");
        return postForJson("/api/v2/forum/analyze-content", params);
    }

    /**
     * 💬 论坛情感分析
     * POST /api/v2/forum/sentiment-analysis
     * 输入: {texts: ["..."]} or {text: "..."}
     * 输出: {results, summary}
     */
    public JsonNode forumSentimentAnalysis(List<String> texts) {
        Map<String, Object> params = new HashMap<>();
        params.put("texts", texts);
        return postForJson("/api/v2/forum/sentiment-analysis", params);
    }

    /**
     * 📚 学习路径推荐
     * POST /api/v2/development/recommend-path
     * 输入: {skill_levels: {skill: score}, years_experience}
     * 输出: {recommendations, user_skill_summary}
     */
    public JsonNode devRecommendLearningPath(Map<String, Double> skillLevels) {
        Map<String, Object> params = new HashMap<>();
        params.put("skill_levels", skillLevels != null ? skillLevels : new HashMap<>());
        return postForJson("/api/v2/development/recommend-path", params);
    }

    /**
     * 🚗 交通事故风险预测 (升级版 XGBoost)
     * POST /api/v2/traffic/accident-risk
     * 输入: 时段/路况/天气参数
     * 输出: {risk_probability, risk_level, recommendations, key_risk_factors}
     */
    public JsonNode trafficAccidentRiskPredict(Map<String, Object> trafficParams) {
        return postForJson("/api/v2/traffic/accident-risk", trafficParams);
    }

    /**
     * 💰 客户流失预测
     * POST /api/v2/finance/customer-churn
     * 输入: 用户行为/交易参数
     * 输出: {churn_probability, risk_level, retention_advice}
     */
    public JsonNode financeCustomerChurnPredict(Map<String, Object> customerParams) {
        return postForJson("/api/v2/finance/customer-churn", customerParams);
    }

    /**
     * 🌤️ 极端天气事件分类
     * POST /api/v2/environment/extreme-weather
     * 输入: 空气质量/气象参数
     * 输出: {severity_level, event_type, confidence, advisory}
     */
    public JsonNode environmentExtremeWeather(Map<String, Object> weatherParams) {
        return postForJson("/api/v2/environment/extreme-weather", weatherParams);
    }

    /**
     * 📊 开发模块: AI 趋势分析
     * POST /api/v2/development/trend-analysis
     * 输入: 可选过滤参数
     * 输出: {trend_data, categories, technology_stages}
     */
    public JsonNode devTrendAnalysis() {
        return postForJson("/api/v2/development/trend-analysis", new HashMap<>());
    }
}
