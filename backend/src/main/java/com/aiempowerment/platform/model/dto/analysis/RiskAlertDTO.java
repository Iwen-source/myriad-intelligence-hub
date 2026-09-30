package com.aiempowerment.platform.model.dto.analysis;

import lombok.Data;

/**
 * 实时风险预警 DTO
 * <p>
 * 由 {@code getRealTimeRiskAlerts} 返回。
 */
@Data
public class RiskAlertDTO {
    private String transactionNo;
    private String userName;
    private double amount;
    private Double riskScore;
    private String riskLevel;
    private String type;
    private String time;
    private String severity;
    private boolean mlGenerated;
}
