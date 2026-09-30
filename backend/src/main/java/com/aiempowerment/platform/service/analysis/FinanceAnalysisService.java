package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.common.BusinessException;
import com.aiempowerment.platform.model.dto.analysis.*;
import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.repository.FinanceTransactionRepository;
import com.aiempowerment.platform.repository.RiskAlertRuleRepository;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * 金融风控AI分析服务 — 改造版
 * <p>
 * 原伪AI（规则+随机数）已替换为 Python ML Server 的真实模型调用。
 * ML 不可用时自动 fallback 到原模拟逻辑。
 * <p>
 * 重构说明：所有方法已改为强类型 DTO 返回（不再使用裸 Map），
 * 规则评分分段与合成规则生成已拆分至 {@link FinanceRuleEngine}。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class FinanceAnalysisService {

    private final FinanceTransactionRepository financeTransactionRepository;
    private final RiskAlertRuleRepository riskAlertRuleRepository;
    private final PythonMlClient pythonMlClient;
    private final FinanceRuleEngine ruleEngine;

    // ======================== 金融风控核心方法 ========================

    public TransactionRiskDTO evaluateTransactionRisk(Long transactionId) {
        FinanceTransaction tx = financeTransactionRepository.findById(transactionId).orElse(null);
        if (tx == null) {
            TransactionRiskDTO errorDto = new TransactionRiskDTO();
            errorDto.setTransactionId(transactionId);
            errorDto.setRiskLevel("交易不存在");
            errorDto.setMlGenerated(false);
            return errorDto;
        }

        // 调用 Python ML 模型评估风险
        double amount = tx.getAmount() != null ? tx.getAmount().doubleValue() : 0;
        int hourOfDay = tx.getCreateTime() != null ? tx.getCreateTime().getHour() : 12;
        int dayOfWeek = tx.getCreateTime() != null ? tx.getCreateTime().getDayOfWeek().getValue() : 3;
        int isWeekend = (dayOfWeek == 6 || dayOfWeek == 7) ? 1 : 0;
        double userAge = 30; // 默认值，实际可从用户表获取

        JsonNode mlResult = pythonMlClient.predictFinance(
                amount, hourOfDay, dayOfWeek, 0, 0, isWeekend, 30, 0.5, 1.0
        );

        if (mlResult != null && "success".equals(mlResult.path("status").asText())) {
            double riskScore = mlResult.path("risk_score").asDouble();
            String riskLevel = mlResult.path("risk_level").asText();
            boolean isAnomaly = mlResult.path("is_anomaly").asBoolean(false);

            // 转换风险等级为中文
            String chineseLevel = switch (riskLevel) {
                case "low" -> "低";
                case "medium" -> "中";
                case "high" -> "高";
                default -> "低";
            };

            List<String> riskFactors = new ArrayList<>();
            if (amount > 100000) riskFactors.add("金额过大（>10万）");
            if (isAnomaly) riskFactors.add("异常交易模式");
            if ("转账".equals(tx.getTransactionType())) riskFactors.add("转账交易风险较高");

            TransactionRiskDTO dto = new TransactionRiskDTO();
            dto.setTransactionId(transactionId);
            dto.setTransactionNo(tx.getTransactionNo());
            dto.setRiskScore(Math.round(riskScore * 10.0) / 10.0);
            dto.setRiskLevel(chineseLevel);
            dto.setRiskFactors(riskFactors);
            dto.setAnomalyScore(riskScore);
            dto.setAnomaly(isAnomaly);
            dto.setMlGenerated(true);
            return dto;
        }

        // Fallback: 原规则逻辑
        double riskScore = 0;
        if (tx.getAmount() != null) {
            riskScore += amount > 100000 ? 30 : amount > 50000 ? 20 : amount > 10000 ? 10 : 5;
        }
        if (tx.getRiskScore() != null) {
            riskScore += tx.getRiskScore().doubleValue() * 0.5;
        }
        if ("转账".equals(tx.getTransactionType())) riskScore += 10;
        if ("提现".equals(tx.getTransactionType())) riskScore += 15;
        riskScore = Math.min(100, riskScore);
        String riskLevel = riskScore < 30 ? "低" : riskScore < 60 ? "中" : riskScore < 80 ? "高" : "严重";

        List<String> riskFactors = new ArrayList<>();
        if (amount > 100000) riskFactors.add("金额过大（>10万）");
        if (tx.getTransactionType() != null && tx.getTransactionType().contains("转账")) {
            riskFactors.add("转账交易风险较高");
        }

        double anomalyScore = 0;
        if (tx.getAmount() != null) {
            double avg = financeTransactionRepository.findAll().stream()
                    .filter(t -> t.getId() != null)
                    .mapToDouble(t -> t.getAmount() != null ? t.getAmount().doubleValue() : 0)
                    .average().orElse(1000);
            anomalyScore = Math.min(100, Math.abs(amount - avg) / avg * 50);
        }

        TransactionRiskDTO dto = new TransactionRiskDTO();
        dto.setTransactionId(transactionId);
        dto.setTransactionNo(tx.getTransactionNo());
        dto.setRiskScore(Math.round(riskScore * 10.0) / 10.0);
        dto.setRiskLevel(riskLevel);
        dto.setRiskFactors(riskFactors);
        dto.setAnomalyScore(Math.round(anomalyScore * 10.0) / 10.0);
        dto.setMlGenerated(false);
        return dto;
    }

    public List<RuleHitDTO> analyzeRuleHits() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();
        List<RiskAlertRule> allRules = riskAlertRuleRepository.findAll();

        // If no rules in DB, generate synthetic rules based on transaction data
        if (allRules.isEmpty()) {
            log.info("No risk alert rules found in DB, generating synthetic rule statistics from {} transactions", allTx.size());
            return ruleEngine.generateSyntheticRuleHits(allTx);
        }

        Map<Long, RuleHitDTO> ruleStats = new LinkedHashMap<>();
        for (RiskAlertRule rule : allRules) {
            RuleHitDTO dto = new RuleHitDTO(
                    rule.getRuleName(),
                    rule.getRuleType(),
                    0,
                    0.0,
                    false
            );
            ruleStats.put(rule.getId(), dto);
        }

        for (FinanceTransaction tx : allTx) {
            if (tx.getRiskScore() == null || tx.getRiskLevel() == null) continue;
            for (RiskAlertRule rule : allRules) {
                boolean hit = false;
                if ("金额阈值".equals(rule.getRuleType()) && rule.getThreshold() != null) {
                    hit = tx.getAmount() != null && tx.getAmount().doubleValue() > rule.getThreshold().doubleValue();
                } else if ("风险等级".equals(rule.getRuleType()) && rule.getRiskLevel() != null) {
                    String[] levels = rule.getRiskLevel().split(",");
                    for (String lv : levels) {
                        if (lv.trim().equals(tx.getRiskLevel())) { hit = true; break; }
                    }
                }
                if (hit) {
                    RuleHitDTO dto = ruleStats.get(rule.getId());
                    dto.setHitCount(dto.getHitCount() + 1);
                    dto.setTotalRiskAmount(dto.getTotalRiskAmount()
                            + (tx.getAmount() != null ? tx.getAmount().doubleValue() : 0));
                }
            }
        }

        List<RuleHitDTO> results = new ArrayList<>(ruleStats.values());
        results.sort((a, b) -> Integer.compare(b.getHitCount(), a.getHitCount()));

        return results;
    }

    // ======================== 金融风控高级 AI 分析 ========================

    public List<TrendPredictionDTO> predictTransactionTrend(int days) {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();

        // 获取历史交易金额序列
        List<Double> pastAmounts = allTx.stream()
                .filter(tx -> tx.getAmount() != null)
                .map(tx -> tx.getAmount().doubleValue())
                .collect(Collectors.toList());

        // 尝试用 ML 市场趋势预测
        if (!pastAmounts.isEmpty()) {
            JsonNode mlResult = pythonMlClient.marketTrend(pastAmounts.size() > 30
                    ? pastAmounts.subList(pastAmounts.size() - 30, pastAmounts.size())
                    : pastAmounts);
            if (mlResult != null && "success".equals(mlResult.path("status").asText())) {
                JsonNode predictions = mlResult.path("predictions");
                List<TrendPredictionDTO> results = new ArrayList<>();
                LocalDate today = LocalDate.now();

                for (int i = 0; i < Math.min(days, predictions.size()); i++) {
                    double predictedAmount = predictions.get(i).asDouble();
                    double predictedCount = predictedAmount / 1000; // 估算交易笔数

                    LocalDate futureDate = today.plusDays(i + 1);
                    TrendPredictionDTO item = new TrendPredictionDTO();
                    item.setDate(futureDate.toString());
                    item.setDayOfWeek(futureDate.getDayOfWeek().getDisplayName(
                            java.time.format.TextStyle.FULL, java.util.Locale.CHINESE));
                    item.setPredictedCount(Math.max(1, Math.round(predictedCount)));
                    item.setPredictedAmount(Math.round(predictedAmount * 100.0) / 100.0);
                    item.setHighRiskCount(Math.max(0, Math.round(predictedCount * 0.08)));
                    item.setConfidenceRange(Math.round(predictedCount * 0.85) + "-" + Math.round(predictedCount * 1.15));
                    item.setMlGenerated(true);
                    results.add(item);
                }
                return results;
            }
        }

        // Fallback: 基于历史统计和系统日均值按周期外推
        Map<LocalDate, long[]> dailyStats = new TreeMap<>();
        for (FinanceTransaction tx : allTx) {
            if (tx.getCreateTime() == null) continue;
            LocalDate date = tx.getCreateTime().toLocalDate();
            dailyStats.computeIfAbsent(date, k -> new long[]{0, 0});
            dailyStats.get(date)[0]++;
            dailyStats.get(date)[1] += tx.getAmount() != null ? tx.getAmount().longValue() : 0;
        }

        double avgCount = dailyStats.values().stream().mapToLong(a -> a[0]).average().orElse(100);
        double avgAmount = dailyStats.values().stream().mapToLong(a -> a[1]).average().orElse(500000);

        List<TrendPredictionDTO> results = new ArrayList<>();
        LocalDate today = LocalDate.now();
        for (int i = 1; i <= days; i++) {
            LocalDate futureDate = today.plusDays(i);
            int dow = futureDate.getDayOfWeek().getValue();
            double dayFactor = (dow >= 6) ? 0.6 : 1.2;
            // 使用工作日/周末因子代替随机噪声，保证确定性
            double smallVariation = 0.1 * (dow % 3 - 1); // -0.1~0.1 基于星期确定
            double noise = 1.0 + smallVariation;
            double trendFactor = 1.0 + i * 0.005;

            long predictedCount = Math.round(avgCount * dayFactor * noise * trendFactor);
            long predictedAmount = Math.round(avgAmount * dayFactor * noise * trendFactor);
            long highRiskCount = Math.round(predictedCount * 0.08 * (1.0 + (dow % 5) * 0.08));

            TrendPredictionDTO item = new TrendPredictionDTO();
            item.setDate(futureDate.toString());
            item.setDayOfWeek(futureDate.getDayOfWeek().getDisplayName(
                    java.time.format.TextStyle.FULL, java.util.Locale.CHINESE));
            item.setPredictedCount(predictedCount);
            item.setPredictedAmount(predictedAmount);
            item.setHighRiskCount(highRiskCount);
            item.setConfidenceRange((int)(predictedCount * 0.85) + "-" + (int)(predictedCount * 1.15));
            item.setMlGenerated(false);
            results.add(item);
        }
        return results;
    }

    public List<UserBehaviorProfileDTO> analyzeUserBehaviorProfiles() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();

        Map<Long, List<FinanceTransaction>> userTxMap = allTx.stream()
                .filter(tx -> tx.getUserId() != null)
                .collect(Collectors.groupingBy(FinanceTransaction::getUserId));

        List<UserBehaviorProfileDTO> profiles = new ArrayList<>();
        for (Map.Entry<Long, List<FinanceTransaction>> entry : userTxMap.entrySet()) {
            List<FinanceTransaction> userTx = entry.getValue();
            int totalCount = userTx.size();
            double totalAmount = userTx.stream().filter(tx -> tx.getAmount() != null).mapToDouble(tx -> tx.getAmount().doubleValue()).sum();
            double avgAmount = totalAmount / Math.max(1, totalCount);

            // 尝试用 ML 客户分群
            int activeHour = userTx.stream()
                    .filter(tx -> tx.getCreateTime() != null)
                    .collect(Collectors.groupingBy(tx -> tx.getCreateTime().getHour(), Collectors.counting()))
                    .entrySet().stream().max(Map.Entry.comparingByValue())
                    .map(e -> e.getKey()).orElse(12);

            JsonNode segResult = pythonMlClient.customerSegments(
                    avgAmount, totalCount, 0.5, activeHour, 0.3
            );

            String segmentName = null;
            String profileDescription = null;
            if (segResult != null && "success".equals(segResult.path("status").asText())) {
                segmentName = segResult.path("segment_name").asText();
                profileDescription = segResult.path("profile_description").asText();
            }

            // 风险分析
            long highRiskCount = userTx.stream()
                    .filter(tx -> tx.getRiskLevel() != null && ("高".equals(tx.getRiskLevel()) || "严重".equals(tx.getRiskLevel())))
                    .count();
            double riskRatio = totalCount > 0 ? (double) highRiskCount / totalCount : 0;

            String userName = userTx.get(0).getUserName();
            if (userName == null || userName.isBlank()) userName = "用户" + entry.getKey();

            String riskLevel;
            if (riskRatio > 0.3) riskLevel = "高风险";
            else if (riskRatio > 0.15) riskLevel = "中风险";
            else if (riskRatio > 0.05) riskLevel = "低风险";
            else riskLevel = "正常";

            String spendingPattern;
            if (avgAmount > 10000) spendingPattern = "高额消费";
            else if (avgAmount > 3000) spendingPattern = "中等消费";
            else spendingPattern = "日常消费";

            UserBehaviorProfileDTO profile = new UserBehaviorProfileDTO();
            profile.setUserId(entry.getKey());
            profile.setUserName(userName);
            profile.setTotalTransactions(totalCount);
            profile.setTotalAmount(Math.round(totalAmount * 100.0) / 100.0);
            profile.setAvgAmount(Math.round(avgAmount * 100.0) / 100.0);
            profile.setHighRiskCount(highRiskCount);
            profile.setRiskRatio(Math.round(riskRatio * 100));
            profile.setRiskLevel(riskLevel);
            profile.setSpendingPattern(spendingPattern);
            if (segmentName != null) {
                profile.setSegmentName(segmentName);
                profile.setProfileDescription(profileDescription);
            }
            int securityScore = (int) Math.max(0, Math.min(100, 100 - (riskRatio * 100) - (avgAmount > 50000 ? 10 : 0) - (totalCount > 50 ? 5 : 0)));
            profile.setSecurityScore(securityScore);
            profile.setRiskTrend(riskRatio > 0.2 ? "警惕" : riskRatio > 0.1 ? "关注" : "稳定");
            profile.setMlGenerated(segmentName != null);

            profiles.add(profile);
        }

        profiles.sort(Comparator.comparingLong(UserBehaviorProfileDTO::getRiskRatio).reversed());
        return profiles;
    }

    public List<SuspiciousTransactionDTO> detectSuspiciousTransactions() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();
        List<SuspiciousTransactionDTO> suspicious = new ArrayList<>();

        for (FinanceTransaction tx : allTx) {
            double amount = tx.getAmount() != null ? tx.getAmount().doubleValue() : 0;
            int hour = tx.getCreateTime() != null ? tx.getCreateTime().getHour() : 12;
            int dayOfWeek = tx.getCreateTime() != null ? tx.getCreateTime().getDayOfWeek().getValue() : 3;
            int isWeekend = (dayOfWeek == 6 || dayOfWeek == 7) ? 1 : 0;
            int isNight = (hour < 6 || hour >= 23) ? 1 : 0;

            // 调用 ML 欺诈检测
            JsonNode fraudResult = pythonMlClient.fraudDetect(amount, 0, 0, 0, 1.0, isNight, 0);
            if (fraudResult != null && "success".equals(fraudResult.path("status").asText())) {
                double fraudProb = fraudResult.path("fraud_probability").asDouble();
                String alert = fraudResult.path("alert_level").asText();
                String action = fraudResult.path("action_suggestion").asText();

                if (fraudProb > 30) {
                    SuspiciousTransactionDTO item = new SuspiciousTransactionDTO();
                    item.setTransactionId(tx.getId());
                    item.setTransactionNo(tx.getTransactionNo());
                    item.setUserName(tx.getUserName());
                    item.setAmount(amount);
                    item.setType(tx.getTransactionType());
                    item.setFraudProbability(fraudProb);
                    item.setAlertLevel(alert);
                    item.setActionSuggestion(action);
                    item.setTime(tx.getCreateTime() != null ? tx.getCreateTime().toString() : "未知");
                    item.setMlGenerated(true);
                    suspicious.add(item);
                }
            } else {
                // Fallback: 原规则检测
                boolean isSuspicious = false;
                List<String> reasons = new ArrayList<>();
                if (amount > 100000) { isSuspicious = true; reasons.add("单笔金额过大"); }
                if (amount > 50000 && "提现".equals(tx.getTransactionType())) { isSuspicious = true; reasons.add("大额提现"); }
                if (isNight == 1 && amount > 30000) { isSuspicious = true; reasons.add("深夜大额交易"); }

                if (isSuspicious) {
                    double riskScore = 50 + Math.min(50, (int)(amount / 5000));
                    SuspiciousTransactionDTO item = new SuspiciousTransactionDTO();
                    item.setTransactionId(tx.getId());
                    item.setTransactionNo(tx.getTransactionNo());
                    item.setUserName(tx.getUserName());
                    item.setAmount(amount);
                    item.setType(tx.getTransactionType());
                    item.setFraudProbability(Math.round(riskScore * 10.0) / 10.0);
                    item.setAlertLevel(riskScore > 70 ? "高风险" : "中风险");
                    item.setActionSuggestion(riskScore > 70 ? "立即拦截并通知安全团队" : "人工审核");
                    item.setReasons(reasons);
                    item.setTime(tx.getCreateTime() != null ? tx.getCreateTime().toString() : "未知");
                    item.setMlGenerated(false);
                    suspicious.add(item);
                }
            }
        }

        if (suspicious.isEmpty()) {
            // Fallback: 从数据库取最可疑的交易（按金额降序）
            List<FinanceTransaction> highAmount = allTx.stream()
                    .filter(tx -> tx.getAmount() != null && tx.getAmount().compareTo(new java.math.BigDecimal("100000")) > 0)
                    .sorted(Comparator.comparing(FinanceTransaction::getAmount, Comparator.nullsLast(Comparator.reverseOrder())))
                    .limit(3)
                    .collect(Collectors.toList());
            if (!highAmount.isEmpty()) {
                for (FinanceTransaction tx : highAmount) {
                    SuspiciousTransactionDTO item = new SuspiciousTransactionDTO();
                    item.setTransactionId(tx.getId());
                    item.setTransactionNo(tx.getTransactionNo());
                    item.setUserName(tx.getUserName() != null ? tx.getUserName() : "未知");
                    item.setAmount(tx.getAmount().doubleValue());
                    item.setType(tx.getTransactionType());
                    item.setFraudProbability(Math.min(95, tx.getAmount().doubleValue() / 10000));
                    item.setAlertLevel(tx.getAmount().compareTo(new java.math.BigDecimal("500000")) > 0 ? "高风险" : "中风险");
                    item.setActionSuggestion(tx.getAmount().compareTo(new java.math.BigDecimal("500000")) > 0 ? "立即拦截并通知安全团队" : "人工审核");
                    item.setTime(tx.getCreateTime() != null ? tx.getCreateTime().toString() : LocalDateTime.now().toString());
                    item.setMlGenerated(false);
                    suspicious.add(item);
                }
            }
        }

        suspicious.sort(Comparator.comparingDouble(SuspiciousTransactionDTO::getFraudProbability).reversed());
        return suspicious;
    }

    public MultiDimensionalRiskDTO getMultiDimensionalRisk(Long transactionId) {
        FinanceTransaction tx = financeTransactionRepository.findById(transactionId).orElse(null);
        if (tx == null) {
            // 交易不存在时不伪造数据，直接返回明确的 404 错误
            throw new BusinessException(404, "交易不存在");
        }

        double amount = tx.getAmount() != null ? tx.getAmount().doubleValue() : 0;
        String txType = tx.getTransactionType() != null ? tx.getTransactionType() : "转账";
        String txStatus = tx.getStatus() != null ? tx.getStatus() : "正常";
        String sourceAccount = tx.getSourceAccount() != null ? tx.getSourceAccount() : "";
        String targetAccount = tx.getTargetAccount() != null ? tx.getTargetAccount() : "";
        String description = tx.getDescription() != null ? tx.getDescription() : "";

        // 各维度风险评分（委托规则引擎）
        double amountRisk = ruleEngine.scoreAmountRisk(amount);

        int hour = tx.getCreateTime() != null ? tx.getCreateTime().getHour() : 12;
        int dayOfWeek = tx.getCreateTime() != null ? tx.getCreateTime().getDayOfWeek().getValue() : 3;
        boolean isWeekend = (dayOfWeek == 6 || dayOfWeek == 7);
        double timeRisk = ruleEngine.scoreTimeRisk(hour, isWeekend);

        double behaviorRisk = ruleEngine.scoreBehaviorRisk(txType, sourceAccount, targetAccount);
        double statusRisk = ruleEngine.scoreStatusRisk(txStatus);
        double descriptionRisk = ruleEngine.scoreDescriptionRisk(description);

        // ML 财务健康评估 - 使用真实交易数据而非固定值
        double mlHealthScore = 50;
        boolean isMl = false;
        // 获取该用户所有交易的平均金额作为参考
        List<FinanceTransaction> userTx = tx.getUserId() != null ?
            financeTransactionRepository.findByUserId(tx.getUserId()) : List.of();
        double userAvgAmount = userTx.stream()
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .average().orElse(5000);
        double userTotalAmount = userTx.stream()
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        int userTxCount = userTx.size();

        JsonNode healthResult = pythonMlClient.financialHealth(
                userAvgAmount, userAvgAmount * 0.6, userTotalAmount,
                amount, 2, Math.min(10, Math.max(1, userTxCount)), 3,
                0.6, 0.2, 2, 0.3, 0.6
        );

        if (healthResult != null && "success".equals(healthResult.path("status").asText())) {
            mlHealthScore = healthResult.path("overall_score").asDouble(50);
            isMl = true;
        } else {
            // 不依赖ML时，根据用户实际交易数据计算健康分
            double amountRatio = amount / Math.max(1, userAvgAmount);
            mlHealthScore = 100 - Math.min(70, Math.abs(amountRatio - 1) * 20);
            mlHealthScore = Math.max(10, Math.min(95, mlHealthScore));
        }

        // 金融健康分数越低 → 风险越高
        double healthRisk = Math.max(0, 100 - mlHealthScore) * 0.3;

        // 综合评分（包含更多维度）
        double overallRisk = amountRisk * 0.25 + timeRisk * 0.15 + behaviorRisk * 0.2
                           + healthRisk * 0.25 + statusRisk * 0.1 + descriptionRisk * 0.05;

        // 评分归一化到0-100
        overallRisk = Math.min(100, Math.max(0, overallRisk));

        // 风险等级标签
        String riskLabel;
        if (overallRisk >= 80) riskLabel = "极高";
        else if (overallRisk >= 60) riskLabel = "高";
        else if (overallRisk >= 40) riskLabel = "中";
        else if (overallRisk >= 20) riskLabel = "低";
        else riskLabel = "极低";

        MultiDimensionalRiskDTO.RiskDimensions dimensions = new MultiDimensionalRiskDTO.RiskDimensions();
        dimensions.setAmountRisk(Math.round(amountRisk * 10.0) / 10.0);
        dimensions.setTimeRisk(Math.round(timeRisk * 10.0) / 10.0);
        dimensions.setBehaviorRisk(Math.round(behaviorRisk * 10.0) / 10.0);
        dimensions.setFinancialHealthRisk(Math.round(healthRisk * 10.0) / 10.0);
        dimensions.setStatusRisk(Math.round(statusRisk * 10.0) / 10.0);
        dimensions.setDescriptionRisk(Math.round(descriptionRisk * 10.0) / 10.0);

        MultiDimensionalRiskDTO result = new MultiDimensionalRiskDTO();
        result.setTransactionId(transactionId);
        result.setTransactionNo(tx.getTransactionNo());
        result.setRiskLabel(riskLabel);
        result.setOverallRiskScore(Math.round(overallRisk * 10.0) / 10.0);
        result.setDimensions(dimensions);
        result.setFinancialHealthScore(Math.round(mlHealthScore * 10.0) / 10.0);
        result.setUserAvgAmount(Math.round(userAvgAmount * 100.0) / 100.0);
        result.setUserTxCount(userTxCount);
        result.setTransactionAmount(Math.round(amount * 100.0) / 100.0);
        result.setTransactionType(txType);
        result.setTransactionHour(hour);
        result.setWeekend(isWeekend);
        result.setMlGenerated(isMl);
        return result;
    }

    public TransactionNetworkDTO getTransactionNetworkAnalysis() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();
        Map<Long, List<FinanceTransaction>> userTxMap = allTx.stream()
                .filter(tx -> tx.getUserId() != null)
                .collect(Collectors.groupingBy(FinanceTransaction::getUserId));

        // 用户间交易关系
        List<TransactionNetworkDTO.NetworkNode> nodes = new ArrayList<>();
        List<Object> edges = new ArrayList<>();

        for (Map.Entry<Long, List<FinanceTransaction>> entry : userTxMap.entrySet()) {
            TransactionNetworkDTO.NetworkNode node = new TransactionNetworkDTO.NetworkNode();
            node.setUserId(entry.getKey());
            node.setUserName(entry.getValue().get(0).getUserName() != null ? entry.getValue().get(0).getUserName() : "用户" + entry.getKey());
            node.setTransactionCount(entry.getValue().size());
            node.setTotalAmount(entry.getValue().stream().filter(t -> t.getAmount() != null)
                    .mapToDouble(t -> t.getAmount().doubleValue()).sum());
            nodes.add(node);
        }

        TransactionNetworkDTO result = new TransactionNetworkDTO();
        result.setNodes(nodes);
        result.setTotalNodes(nodes.size());
        result.setEdges(edges);
        result.setTotalEdges(edges.size());
        result.setMlGenerated(false);
        return result;
    }

    public FinanceReportDTO generateRiskAssessmentReport() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();
        List<RiskAlertRule> allRules = riskAlertRuleRepository.findAll();

        long transactionCount = allTx.size();
        long highRiskCount = allTx.stream()
                .filter(tx -> tx.getRiskLevel() != null && ("高".equals(tx.getRiskLevel()) || "严重".equals(tx.getRiskLevel())))
                .count();
        long mediumRiskCount = allTx.stream()
                .filter(tx -> tx.getRiskLevel() != null && "中".equals(tx.getRiskLevel()))
                .count();
        long lowRiskCount = allTx.stream()
                .filter(tx -> tx.getRiskLevel() != null && "低".equals(tx.getRiskLevel()))
                .count();

        double totalAmount = allTx.stream().filter(tx -> tx.getAmount() != null)
                .mapToDouble(tx -> tx.getAmount().doubleValue()).sum();
        double highRiskAmount = allTx.stream()
                .filter(tx -> tx.getRiskLevel() != null && ("高".equals(tx.getRiskLevel()) || "严重".equals(tx.getRiskLevel())))
                .filter(tx -> tx.getAmount() != null)
                .mapToDouble(tx -> tx.getAmount().doubleValue()).sum();
        double highRiskRatio = transactionCount > 0 ? (double) highRiskCount / transactionCount * 100 : 0;

        long activeRules = allRules.stream().filter(RiskAlertRule::getEnabled).count();

        // 尝试用 ML 财务健康评估整体风险
        JsonNode healthResult = pythonMlClient.financialHealth(
                totalAmount / Math.max(1, transactionCount),
                totalAmount * 0.6 / Math.max(1, transactionCount),
                totalAmount * 0.2, highRiskAmount, 2, 5, 3,
                0.5, 0.2, 2, 0.3, 0.5
        );

        double mlOverallScore = 50;
        boolean isMl = false;
        if (healthResult != null && "success".equals(healthResult.path("status").asText())) {
            mlOverallScore = healthResult.path("overall_score").asDouble(50);
            isMl = true;
        }

        FinanceReportDTO dto = new FinanceReportDTO();
        dto.setReportTitle("金融风控AI评估报告 - " + LocalDate.now().toString());
        dto.setTotalTransactions(transactionCount);
        dto.setHighRiskCount(highRiskCount);
        dto.setMediumRiskCount(mediumRiskCount);
        dto.setLowRiskCount(lowRiskCount);
        dto.setTotalAmount(Math.round(totalAmount * 100.0) / 100.0);
        dto.setHighRiskAmount(Math.round(highRiskAmount * 100.0) / 100.0);
        dto.setHighRiskRatio(Math.round(highRiskRatio * 10.0) / 10.0);
        dto.setActiveRules(activeRules);
        dto.setOverallHealthScore(Math.round(mlOverallScore * 10.0) / 10.0);
        dto.setMlGenerated(isMl);
        dto.setAnalysisTime(LocalDateTime.now());
        // 构建 reportText（前端 dashReport.reportText 使用）
        StringBuilder reportText = new StringBuilder();
        reportText.append("📊 金融风控评估报告\n");
        reportText.append("总交易：").append(transactionCount).append(" 笔\n");
        reportText.append("高风险：").append(highRiskCount).append(" 笔（").append(String.format("%.1f", highRiskRatio)).append("%）\n");
        reportText.append("中风险：").append(mediumRiskCount).append(" 笔\n");
        reportText.append("总金额：¥").append(String.format("%.2f", totalAmount)).append("\n");
        reportText.append("风险金额：¥").append(String.format("%.2f", highRiskAmount)).append("\n");
        reportText.append("启用规则：").append(activeRules).append(" 条");
        dto.setReportText(reportText.toString());
        return dto;
    }

    public List<RiskAlertDTO> getRealTimeRiskAlerts() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();
        List<RiskAlertDTO> alerts = new ArrayList<>();

        // 用 ML 欺诈检测分析最新交易
        List<FinanceTransaction> recentTx = allTx.stream()
                .sorted(Comparator.comparing(FinanceTransaction::getCreateTime, Comparator.nullsLast(Comparator.reverseOrder())))
                .limit(20)
                .collect(Collectors.toList());

        for (FinanceTransaction tx : recentTx) {
            double amount = tx.getAmount() != null ? tx.getAmount().doubleValue() : 0;
            int hour = tx.getCreateTime() != null ? tx.getCreateTime().getHour() : 12;
            int isNight = (hour < 6 || hour >= 23) ? 1 : 0;

            JsonNode fraudResult = pythonMlClient.fraudDetect(amount, 0, 0, 0, 1.0, isNight, 0);
            if (fraudResult != null && "success".equals(fraudResult.path("status").asText())) {
                double fraudProb = fraudResult.path("fraud_probability").asDouble();
                String alert = fraudResult.path("alert_level").asText();
                if (fraudProb > 50) {
                    RiskAlertDTO item = new RiskAlertDTO();
                    item.setTransactionNo(tx.getTransactionNo());
                    item.setUserName(tx.getUserName());
                    item.setAmount(amount);
                    item.setRiskScore(fraudProb);
                    item.setRiskLevel(alert.contains("高风险") ? "严重" : "高");
                    item.setType(tx.getTransactionType());
                    item.setTime(tx.getCreateTime() != null ? tx.getCreateTime().toString() : "未知");
                    item.setSeverity(alert.contains("高风险") ? "紧急" : "警告");
                    item.setMlGenerated(true);
                    alerts.add(item);
                }
            }
        }

        if (alerts.isEmpty()) {
            // Fallback: 原逻辑
            allTx.stream()
                    .filter(tx -> tx.getRiskLevel() != null && ("高".equals(tx.getRiskLevel()) || "严重".equals(tx.getRiskLevel())))
                    .sorted(Comparator.comparing(FinanceTransaction::getCreateTime, Comparator.nullsLast(Comparator.reverseOrder())))
                    .limit(8)
                    .forEach(tx -> {
                        RiskAlertDTO alert = new RiskAlertDTO();
                        alert.setTransactionNo(tx.getTransactionNo());
                        alert.setUserName(tx.getUserName());
                        alert.setAmount(tx.getAmount() != null ? tx.getAmount().doubleValue() : 0);
                        alert.setRiskScore(tx.getRiskScore());
                        alert.setRiskLevel(tx.getRiskLevel());
                        alert.setType(tx.getTransactionType());
                        alert.setTime(tx.getCreateTime() != null ? tx.getCreateTime().toString() : "未知");
                        alert.setSeverity("严重".equals(tx.getRiskLevel()) ? "紧急" : "警告");
                        alert.setMlGenerated(false);
                        alerts.add(alert);
                    });

            if (alerts.isEmpty()) {
                // Fallback: 从数据库中找最高风险的交易
                List<FinanceTransaction> riskyTx = allTx.stream()
                        .filter(tx -> tx.getRiskScore() != null || tx.getAmount() != null)
                        .sorted(Comparator.comparing(Function.identity(), (a, b) -> {
                            double riskA = a.getRiskScore() != null ? a.getRiskScore() : (a.getAmount() != null ? a.getAmount().doubleValue() / 1000 : 50);
                            double riskB = b.getRiskScore() != null ? b.getRiskScore() : (b.getAmount() != null ? b.getAmount().doubleValue() / 1000 : 50);
                            return Double.compare(riskB, riskA);
                        })).limit(3).collect(Collectors.toList());
                for (int i = 0; i < Math.min(3, riskyTx.size()); i++) {
                    FinanceTransaction tx = riskyTx.get(i);
                    RiskAlertDTO alert = new RiskAlertDTO();
                    alert.setTransactionNo(tx.getTransactionNo() != null ? tx.getTransactionNo() : "TX" + String.format("%010d", tx.getId()));
                    alert.setUserName(tx.getUserName() != null ? tx.getUserName() : "未知");
                    alert.setAmount(tx.getAmount() != null ? tx.getAmount().doubleValue() : 0);
                    double riskScore = tx.getRiskScore() != null ? tx.getRiskScore() : Math.min(99, (tx.getAmount() != null ? tx.getAmount().longValue() / 10000 : 50));
                    alert.setRiskScore(riskScore);
                    alert.setRiskLevel(riskScore > 80 ? "严重" : riskScore > 60 ? "高" : "中");
                    alert.setType(tx.getTransactionType() != null ? tx.getTransactionType() : "转账");
                    alert.setTime(tx.getCreateTime() != null ? tx.getCreateTime().toString() : LocalDateTime.now().toString());
                    alert.setSeverity(riskScore > 80 ? "紧急" : "警告");
                    alert.setMlGenerated(false);
                    alerts.add(alert);
                }
            }
        }

        return alerts;
    }

    public List<RiskTrendDTO> getRiskTrendData() {
        List<FinanceTransaction> allTx = financeTransactionRepository.findAll();

        Map<LocalDate, long[]> trendMap = new TreeMap<>();
        for (FinanceTransaction tx : allTx) {
            if (tx.getCreateTime() == null) continue;
            LocalDate date = tx.getCreateTime().toLocalDate();
            trendMap.computeIfAbsent(date, k -> new long[]{0, 0, 0, 0});
            trendMap.get(date)[0]++;
            String level = tx.getRiskLevel();
            if ("高".equals(level) || "严重".equals(level)) trendMap.get(date)[1]++;
            else if ("中".equals(level)) trendMap.get(date)[2]++;
            else if ("低".equals(level)) trendMap.get(date)[3]++;
        }

        List<RiskTrendDTO> trendData = new ArrayList<>();
        for (var entry : trendMap.entrySet()) {
            RiskTrendDTO item = new RiskTrendDTO();
            item.setDate(entry.getKey().toString());
            item.setTotal(entry.getValue()[0]);
            item.setHighRisk(entry.getValue()[1]);
            item.setMediumRisk(entry.getValue()[2]);
            item.setLowRisk(entry.getValue()[3]);
            double ratio = entry.getValue()[0] > 0 ? (double) entry.getValue()[1] / entry.getValue()[0] * 100 : 0;
            item.setRiskRatio(Math.round(ratio * 10.0) / 10.0);
            item.setMlGenerated(false);
            trendData.add(item);
        }
        return trendData;
    }
}
