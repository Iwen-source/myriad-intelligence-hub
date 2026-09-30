package com.aiempowerment.platform.model.dto.analysis;

import lombok.Data;

/**
 * 风险趋势 DTO（单日统计点）
 * <p>
 * 由 {@code getRiskTrendData} 返回。
 */
@Data
public class RiskTrendDTO {
    private String date;
    private long total;
    private long highRisk;
    private long mediumRisk;
    private long lowRisk;
    private double riskRatio;
    private boolean mlGenerated;
}
