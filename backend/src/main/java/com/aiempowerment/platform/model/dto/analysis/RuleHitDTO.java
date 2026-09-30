package com.aiempowerment.platform.model.dto.analysis;

/**
 * 风控规则命中分析 DTO
 */
public class RuleHitDTO {
    private String ruleName;
    private String ruleType;
    private int hitCount;
    private double totalRiskAmount;
    private boolean mlGenerated;
    private String effectiveness; // "高效" / "有效" / "低效"

    public RuleHitDTO() {}

    public RuleHitDTO(String ruleName, String ruleType, int hitCount, double totalRiskAmount, boolean mlGenerated) {
        this.ruleName = ruleName;
        this.ruleType = ruleType;
        this.hitCount = hitCount;
        this.totalRiskAmount = totalRiskAmount;
        this.mlGenerated = mlGenerated;
        this.effectiveness = calculateEffectiveness(hitCount, totalRiskAmount);
    }

    private static String calculateEffectiveness(int hitCount, double totalRiskAmount) {
        if (hitCount > 10 && totalRiskAmount > 100000) return "高效";
        if (hitCount > 3 || totalRiskAmount > 50000) return "有效";
        return "低效";
    }

    public String getRuleName() { return ruleName; }
    public void setRuleName(String ruleName) { this.ruleName = ruleName; }
    public String getRuleType() { return ruleType; }
    public void setRuleType(String ruleType) { this.ruleType = ruleType; }
    public int getHitCount() { return hitCount; }
    public void setHitCount(int hitCount) { this.hitCount = hitCount; }
    public double getTotalRiskAmount() { return totalRiskAmount; }
    public void setTotalRiskAmount(double totalRiskAmount) { this.totalRiskAmount = totalRiskAmount; this.effectiveness = calculateEffectiveness(this.hitCount, this.totalRiskAmount); }
    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
    public String getEffectiveness() { return effectiveness; }
    public void setEffectiveness(String effectiveness) { this.effectiveness = effectiveness; }
}
