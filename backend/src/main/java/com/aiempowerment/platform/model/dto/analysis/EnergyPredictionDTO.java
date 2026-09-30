package com.aiempowerment.platform.model.dto.analysis;

import java.time.LocalDate;

/**
 * 能耗预测结果 DTO
 */
public class EnergyPredictionDTO {
    private LocalDate date;
    private String dayOfWeek;
    private double predicted;
    private double lowerBound;
    private double upperBound;
    private boolean mlEnhanced;

    public EnergyPredictionDTO() {}

    public EnergyPredictionDTO(LocalDate date, String dayOfWeek, double predicted,
                                double lowerBound, double upperBound, boolean mlEnhanced) {
        this.date = date;
        this.dayOfWeek = dayOfWeek;
        this.predicted = predicted;
        this.lowerBound = lowerBound;
        this.upperBound = upperBound;
        this.mlEnhanced = mlEnhanced;
    }

    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }
    public String getDayOfWeek() { return dayOfWeek; }
    public void setDayOfWeek(String dayOfWeek) { this.dayOfWeek = dayOfWeek; }
    public double getPredicted() { return predicted; }
    public void setPredicted(double predicted) { this.predicted = predicted; }
    public double getLowerBound() { return lowerBound; }
    public void setLowerBound(double lowerBound) { this.lowerBound = lowerBound; }
    public double getUpperBound() { return upperBound; }
    public void setUpperBound(double upperBound) { this.upperBound = upperBound; }
    public boolean isMlEnhanced() { return mlEnhanced; }
    public void setMlEnhanced(boolean mlEnhanced) { this.mlEnhanced = mlEnhanced; }
}
