package com.aiempowerment.platform.model.dto.analysis;

/**
 * 设备异常检测结果 DTO
 */
public class DeviceAnomalyDTO {
    private String deviceId;
    private String deviceName;
    private String type;
    private String severity;
    private String message;
    private String suggestion;
    private String time;
    private boolean mlGenerated;

    public DeviceAnomalyDTO() {}

    public DeviceAnomalyDTO(String deviceId, String deviceName, String type,
                             String severity, String message, String suggestion,
                             String time, boolean mlGenerated) {
        this.deviceId = deviceId;
        this.deviceName = deviceName;
        this.type = type;
        this.severity = severity;
        this.message = message;
        this.suggestion = suggestion;
        this.time = time;
        this.mlGenerated = mlGenerated;
    }

    public String getDeviceId() { return deviceId; }
    public void setDeviceId(String deviceId) { this.deviceId = deviceId; }
    public String getDeviceName() { return deviceName; }
    public void setDeviceName(String deviceName) { this.deviceName = deviceName; }
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public String getSeverity() { return severity; }
    public void setSeverity(String severity) { this.severity = severity; }
    public String getMessage() { return message; }
    public void setMessage(String message) { this.message = message; }
    public String getSuggestion() { return suggestion; }
    public void setSuggestion(String suggestion) { this.suggestion = suggestion; }
    public String getTime() { return time; }
    public void setTime(String time) { this.time = time; }
    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
}
