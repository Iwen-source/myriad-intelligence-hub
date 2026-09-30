package com.aiempowerment.platform.model.dto.analysis;

import lombok.Data;

/**
 * 多维度风险评估 DTO
 * <p>
 * 由 {@code getMultiDimensionalRisk} 返回。dimensions 为各维度风险分（0-100）。
 */
@Data
public class MultiDimensionalRiskDTO {
    private Long transactionId;
    private String transactionNo;
    private String riskLabel;
    private double overallRiskScore;
    private RiskDimensions dimensions;
    private double financialHealthScore;
    private double userAvgAmount;
    private int userTxCount;
    private double transactionAmount;
    private String transactionType;
    private int transactionHour;
    private boolean isWeekend;
    private boolean mlGenerated;

    @Data
    public static class RiskDimensions {
        private double amountRisk;
        private double timeRisk;
        private double behaviorRisk;
        private double financialHealthRisk;
        private double statusRisk;
        private double descriptionRisk;
    }
}
