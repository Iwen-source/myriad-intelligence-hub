package com.aiempowerment.platform.model.dto.analysis;

import java.time.LocalDate;

/**
 * 空气质量预测 DTO
 */
public class AirQualityPredictionDTO {
    private LocalDate date;
    private String dayOfWeek;
    private int predictedAqi;
    private String level;
    private String levelColor;
    private boolean mlGenerated;

    public AirQualityPredictionDTO() {}

    public AirQualityPredictionDTO(LocalDate date, String dayOfWeek, int predictedAqi,
                                    String level, String levelColor, boolean mlGenerated) {
        this.date = date;
        this.dayOfWeek = dayOfWeek;
        this.predictedAqi = predictedAqi;
        this.level = level;
        this.levelColor = levelColor;
        this.mlGenerated = mlGenerated;
    }

    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }
    public String getDayOfWeek() { return dayOfWeek; }
    public void setDayOfWeek(String dayOfWeek) { this.dayOfWeek = dayOfWeek; }
    public int getPredictedAqi() { return predictedAqi; }
    public void setPredictedAqi(int predictedAqi) { this.predictedAqi = predictedAqi; }
    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }
    public String getLevelColor() { return levelColor; }
    public void setLevelColor(String levelColor) { this.levelColor = levelColor; }
    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
}
