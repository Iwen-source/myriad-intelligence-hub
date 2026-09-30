package com.aiempowerment.platform.model.dto.analysis;

import java.time.LocalDateTime;
import java.util.Map;

/**
 * 能源设备详细分析 DTO
 */
public class EnergyDeviceAnalysisDTO extends AnalysisMetadata {
    private Map<String, Long> deviceTypeCount;
    private Map<String, Double> deviceTypeConsumption;
    private Map<String, Double> efficiencyScores;
    private Map<String, Double> topConsumptionDevices;
    private double totalConsumption;
    private double totalCost;
    private double carbonEmission;
    private double avgDailyConsumption;
    private boolean carbonMlEstimated;

    public EnergyDeviceAnalysisDTO() {}

    public Map<String, Long> getDeviceTypeCount() { return deviceTypeCount; }
    public void setDeviceTypeCount(Map<String, Long> deviceTypeCount) { this.deviceTypeCount = deviceTypeCount; }
    public Map<String, Double> getDeviceTypeConsumption() { return deviceTypeConsumption; }
    public void setDeviceTypeConsumption(Map<String, Double> deviceTypeConsumption) { this.deviceTypeConsumption = deviceTypeConsumption; }
    public Map<String, Double> getEfficiencyScores() { return efficiencyScores; }
    public void setEfficiencyScores(Map<String, Double> efficiencyScores) { this.efficiencyScores = efficiencyScores; }
    public Map<String, Double> getTopConsumptionDevices() { return topConsumptionDevices; }
    public void setTopConsumptionDevices(Map<String, Double> topConsumptionDevices) { this.topConsumptionDevices = topConsumptionDevices; }
    public double getTotalConsumption() { return totalConsumption; }
    public void setTotalConsumption(double totalConsumption) { this.totalConsumption = totalConsumption; }
    public double getTotalCost() { return totalCost; }
    public void setTotalCost(double totalCost) { this.totalCost = totalCost; }
    public double getCarbonEmission() { return carbonEmission; }
    public void setCarbonEmission(double carbonEmission) { this.carbonEmission = carbonEmission; }
    public double getAvgDailyConsumption() { return avgDailyConsumption; }
    public void setAvgDailyConsumption(double avgDailyConsumption) { this.avgDailyConsumption = avgDailyConsumption; }
    public boolean isCarbonMlEstimated() { return carbonMlEstimated; }
    public void setCarbonMlEstimated(boolean carbonMlEstimated) { this.carbonMlEstimated = carbonMlEstimated; }
}
