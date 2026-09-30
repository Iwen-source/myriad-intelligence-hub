package com.aiempowerment.platform.model.dto.analysis;

import java.util.List;

/**
 * 交易风险评分 DTO
 */
public class TransactionRiskDTO {
    private Long transactionId;
    private String transactionNo;
    private double riskScore;
    private String riskLevel;
    private List<String> riskFactors;
    private double anomalyScore;
    private boolean anomaly;
    private boolean mlGenerated;

    public TransactionRiskDTO() {}

    public Long getTransactionId() { return transactionId; }
    public void setTransactionId(Long transactionId) { this.transactionId = transactionId; }
    public String getTransactionNo() { return transactionNo; }
    public void setTransactionNo(String transactionNo) { this.transactionNo = transactionNo; }
    public double getRiskScore() { return riskScore; }
    public void setRiskScore(double riskScore) { this.riskScore = riskScore; }
    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }
    public List<String> getRiskFactors() { return riskFactors; }
    public void setRiskFactors(List<String> riskFactors) { this.riskFactors = riskFactors; }
    public double getAnomalyScore() { return anomalyScore; }
    public void setAnomalyScore(double anomalyScore) { this.anomalyScore = anomalyScore; }
    public boolean isAnomaly() { return anomaly; }
    public void setAnomaly(boolean anomaly) { this.anomaly = anomaly; }
    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
}
