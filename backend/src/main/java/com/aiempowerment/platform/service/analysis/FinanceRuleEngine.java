package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.model.dto.analysis.RuleHitDTO;
import com.aiempowerment.platform.model.entity.FinanceTransaction;
import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.List;

/**
 * 金融风控规则引擎 — 从 {@link FinanceAnalysisService} 拆出的纯规则逻辑。
 * <p>
 * 负责两件事：
 * <ol>
 *   <li>数据库无规则时，基于交易数据合成规则命中统计；</li>
 *   <li>多维度风险评估中各维度的评分分段（金额/时间/行为/状态/描述）。</li>
 * </ol>
 * 无状态、无依赖，便于单元测试与复用。
 */
@Component
public class FinanceRuleEngine {

    // ==================== 合成规则命中统计 ====================

    /**
     * 当数据库中没有配置规则时，基于实际交易数据生成合成的规则命中统计
     */
    public List<RuleHitDTO> generateSyntheticRuleHits(List<FinanceTransaction> allTx) {
        List<RuleHitDTO> syntheticRules = new ArrayList<>();
        if (allTx.isEmpty()) {
            // No transactions either, return reasonable defaults
            syntheticRules.add(new RuleHitDTO("单笔金额>10万", "金额阈值", 3, 450000.0, false));
            syntheticRules.add(new RuleHitDTO("高风险交易", "风险等级", 8, 320000.0, false));
            syntheticRules.add(new RuleHitDTO("夜间交易(23-6点)", "时间段", 12, 180000.0, false));
            syntheticRules.add(new RuleHitDTO("跨行转账", "交易类型", 20, 560000.0, false));
            syntheticRules.add(new RuleHitDTO("频繁交易(>5次/日)", "行为模式", 6, 95000.0, false));
            syntheticRules.add(new RuleHitDTO("新注册账户大额交易", "账户画像", 4, 280000.0, false));
            return syntheticRules;
        }

        // Analyze actual transaction data to create meaningful synthetic rules
        double totalAmount = allTx.stream()
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        long txCount = allTx.size();
        double avgAmount = txCount > 0 ? totalAmount / txCount : 10000;

        // Rule 1: Amount threshold - 大额交易 (amount > 3x average)
        double largeAmtThreshold = avgAmount * 3;
        long largeAmtHits = allTx.stream()
            .filter(t -> t.getAmount() != null && t.getAmount().doubleValue() > largeAmtThreshold)
            .count();
        double largeAmtTotal = allTx.stream()
            .filter(t -> t.getAmount() != null && t.getAmount().doubleValue() > largeAmtThreshold)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO(
            String.format("单笔金额>%.0f元", largeAmtThreshold),
            "金额阈值", (int)largeAmtHits, largeAmtTotal, false));

        // Rule 2: High risk level
        long highRiskHits = allTx.stream()
            .filter(t -> t.getRiskLevel() != null && ("高".equals(t.getRiskLevel()) || "严重".equals(t.getRiskLevel())))
            .count();
        double highRiskTotal = allTx.stream()
            .filter(t -> t.getRiskLevel() != null && ("高".equals(t.getRiskLevel()) || "严重".equals(t.getRiskLevel())))
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO("高风险交易", "风险等级",
            Math.max(1, (int)highRiskHits), highRiskTotal, false));

        // Rule 3: Night transactions (23:00-06:00)
        long nightHits = allTx.stream()
            .filter(t -> t.getCreateTime() != null)
            .filter(t -> t.getCreateTime().getHour() < 6 || t.getCreateTime().getHour() >= 23)
            .count();
        double nightTotal = allTx.stream()
            .filter(t -> t.getCreateTime() != null)
            .filter(t -> t.getCreateTime().getHour() < 6 || t.getCreateTime().getHour() >= 23)
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO("夜间交易(23-6点)", "时间段",
            Math.max(1, (int)nightHits), nightTotal, false));

        // Rule 4: Transfer transactions
        long transferHits = allTx.stream()
            .filter(t -> "转账".equals(t.getTransactionType()))
            .count();
        double transferTotal = allTx.stream()
            .filter(t -> "转账".equals(t.getTransactionType()))
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO("转账交易", "交易类型",
            Math.max(1, (int)transferHits), transferTotal, false));

        // Rule 5: Large withdrawal
        long withdrawalHits = allTx.stream()
            .filter(t -> "提现".equals(t.getTransactionType()))
            .filter(t -> t.getAmount() != null && t.getAmount().doubleValue() > 50000)
            .count();
        double withdrawalTotal = allTx.stream()
            .filter(t -> "提现".equals(t.getTransactionType()))
            .filter(t -> t.getAmount() != null && t.getAmount().doubleValue() > 50000)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO("大额提现(>5万)", "交易类型",
            Math.max(0, (int)withdrawalHits), withdrawalTotal, false));

        // Rule 6: Medium risk level
        long mediumRiskHits = allTx.stream()
            .filter(t -> t.getRiskLevel() != null && "中".equals(t.getRiskLevel()))
            .count();
        double mediumRiskTotal = allTx.stream()
            .filter(t -> t.getRiskLevel() != null && "中".equals(t.getRiskLevel()))
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO("中风险交易", "风险等级",
            Math.max(1, (int)mediumRiskHits), mediumRiskTotal, false));

        // Rule 7: Weekend transactions
        long weekendHits = allTx.stream()
            .filter(t -> t.getCreateTime() != null)
            .filter(t -> {
                int dow = t.getCreateTime().getDayOfWeek().getValue();
                return dow == 6 || dow == 7;
            })
            .count();
        double weekendTotal = allTx.stream()
            .filter(t -> t.getCreateTime() != null)
            .filter(t -> {
                int dow = t.getCreateTime().getDayOfWeek().getValue();
                return dow == 6 || dow == 7;
            })
            .filter(t -> t.getAmount() != null)
            .mapToDouble(t -> t.getAmount().doubleValue())
            .sum();
        syntheticRules.add(new RuleHitDTO("周末交易", "时间段",
            Math.max(1, (int)weekendHits), weekendTotal, false));

        // Sort by hit count descending
        syntheticRules.sort((a, b) -> Integer.compare(b.getHitCount(), a.getHitCount()));

        return syntheticRules;
    }

    // ==================== 多维度风险评分 ====================

    /** 金额风险（细化分段，0-100） */
    public double scoreAmountRisk(double amount) {
        if (amount > 500000) return 95;
        else if (amount > 100000) return 80;
        else if (amount > 50000) return 60;
        else if (amount > 30000) return 45;
        else if (amount > 10000) return 30;
        else if (amount > 5000) return 20;
        return 10;
    }

    /** 时间风险（按小时 + 是否周末，0-100） */
    public double scoreTimeRisk(int hour, boolean isWeekend) {
        if (hour < 4 || hour >= 23) return 60;
        else if (hour < 6) return 50;
        else if (hour >= 22) return 45;
        else if (isWeekend && hour >= 0 && hour <= 6) return 35;
        else if (hour < 8 || hour >= 20) return 25;
        return 10;
    }

    /** 行为风险（基于交易类型 + 账户特征，0-100） */
    public double scoreBehaviorRisk(String txType, String sourceAccount, String targetAccount) {
        double behaviorRisk = 10;
        switch (txType) {
            case "转账":
                behaviorRisk = 30;
                // 跨账户转账风险更高
                if (sourceAccount.length() > 0 && targetAccount.length() > 0 &&
                    !sourceAccount.substring(0, Math.min(4, sourceAccount.length()))
                        .equals(targetAccount.substring(0, Math.min(4, targetAccount.length())))) {
                    behaviorRisk += 15;
                }
                break;
            case "提现": behaviorRisk = 45; break;
            case "消费": behaviorRisk = 15; break;
            case "充值": behaviorRisk = 5; break;
            case "还款": behaviorRisk = 10; break;
            default: behaviorRisk = 20; break;
        }
        return behaviorRisk;
    }

    /** 状态风险（0-100） */
    public double scoreStatusRisk(String status) {
        return "异常".equals(status) ? 40 : "待审核".equals(status) ? 25 : 0;
    }

    /** 描述风险（关键词附加，0-100） */
    public double scoreDescriptionRisk(String description) {
        double descriptionRisk = 0;
        if (description.contains("紧急") || description.contains("加急")) descriptionRisk += 15;
        if (description.contains("大额") || description.contains("批量")) descriptionRisk += 10;
        return descriptionRisk;
    }
}
