package com.aiempowerment.platform.model.dto.analysis;

/**
 * 金融风控评估报告 DTO
 */
public class FinanceReportDTO extends AnalysisMetadata {
    private String reportTitle;
    private long totalTransactions;
    private long highRiskCount;
    private long mediumRiskCount;
    private long lowRiskCount;
    private double totalAmount;
    private double highRiskAmount;
    private double highRiskRatio;
    private long activeRules;
    private double overallHealthScore;
    private String reportText;

    public FinanceReportDTO() {}

    public String getReportTitle() { return reportTitle; }
    public void setReportTitle(String reportTitle) { this.reportTitle = reportTitle; }
    public long getTotalTransactions() { return totalTransactions; }
    public void setTotalTransactions(long totalTransactions) { this.totalTransactions = totalTransactions; }
    public long getHighRiskCount() { return highRiskCount; }
    public void setHighRiskCount(long highRiskCount) { this.highRiskCount = highRiskCount; }
    public long getMediumRiskCount() { return mediumRiskCount; }
    public void setMediumRiskCount(long mediumRiskCount) { this.mediumRiskCount = mediumRiskCount; }
    public long getLowRiskCount() { return lowRiskCount; }
    public void setLowRiskCount(long lowRiskCount) { this.lowRiskCount = lowRiskCount; }
    public double getTotalAmount() { return totalAmount; }
    public void setTotalAmount(double totalAmount) { this.totalAmount = totalAmount; }
    public double getHighRiskAmount() { return highRiskAmount; }
    public void setHighRiskAmount(double highRiskAmount) { this.highRiskAmount = highRiskAmount; }
    public double getHighRiskRatio() { return highRiskRatio; }
    public void setHighRiskRatio(double highRiskRatio) { this.highRiskRatio = highRiskRatio; }
    public long getActiveRules() { return activeRules; }
    public void setActiveRules(long activeRules) { this.activeRules = activeRules; }
    public double getOverallHealthScore() { return overallHealthScore; }
    public void setOverallHealthScore(double overallHealthScore) { this.overallHealthScore = overallHealthScore; }
    public String getReportText() { return reportText; }
    public void setReportText(String reportText) { this.reportText = reportText; }
}
