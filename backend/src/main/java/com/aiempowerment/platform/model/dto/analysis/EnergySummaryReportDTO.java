package com.aiempowerment.platform.model.dto.analysis;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * 能源AI摘要报告 DTO
 */
public class EnergySummaryReportDTO extends AnalysisMetadata {
    private String reportTitle;
    private String summary;
    private double totalConsumption;
    private double totalCost;
    private double carbonEmission;
    private long normalDevices;
    private long abnormalDevices;
    private Map<String, Double> weekDistribution;

    public EnergySummaryReportDTO() {}

    public String getReportTitle() { return reportTitle; }
    public void setReportTitle(String reportTitle) { this.reportTitle = reportTitle; }
    public String getSummary() { return summary; }
    public void setSummary(String summary) { this.summary = summary; }
    public double getTotalConsumption() { return totalConsumption; }
    public void setTotalConsumption(double totalConsumption) { this.totalConsumption = totalConsumption; }
    public double getTotalCost() { return totalCost; }
    public void setTotalCost(double totalCost) { this.totalCost = totalCost; }
    public double getCarbonEmission() { return carbonEmission; }
    public void setCarbonEmission(double carbonEmission) { this.carbonEmission = carbonEmission; }
    public long getNormalDevices() { return normalDevices; }
    public void setNormalDevices(long normalDevices) { this.normalDevices = normalDevices; }
    public long getAbnormalDevices() { return abnormalDevices; }
    public void setAbnormalDevices(long abnormalDevices) { this.abnormalDevices = abnormalDevices; }
    public Map<String, Double> getWeekDistribution() { return weekDistribution; }
    public void setWeekDistribution(Map<String, Double> weekDistribution) { this.weekDistribution = weekDistribution; }
}
