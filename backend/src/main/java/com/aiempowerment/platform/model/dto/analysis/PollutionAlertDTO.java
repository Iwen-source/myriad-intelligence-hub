package com.aiempowerment.platform.model.dto.analysis;

/**
 * 污染预警 DTO
 */
public class PollutionAlertDTO {
    private String level;
    private String message;
    private String affectedArea;
    private String suggestion;
    private String time;
    private boolean mlGenerated;

    public PollutionAlertDTO() {}

    public PollutionAlertDTO(String level, String message, String affectedArea,
                              String suggestion, String time, boolean mlGenerated) {
        this.level = level;
        this.message = message;
        this.affectedArea = affectedArea;
        this.suggestion = suggestion;
        this.time = time;
        this.mlGenerated = mlGenerated;
    }

    public String getLevel() { return level; }
    public void setLevel(String level) { this.level = level; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getAffectedArea() { return affectedArea; }
    public void setAffectedArea(String affectedArea) { this.affectedArea = affectedArea; }
    public String getSuggestion() { return suggestion; }
    public void setSuggestion(String suggestion) { this.suggestion = suggestion; }
    public String getTime() { return time; }
    public void setTime(String time) { this.time = time; }
    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
}
