package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 事故风险预测视图对象 - 替换 predictAccidentRisk() 中的 fallback Map
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class AccidentRiskVO {
    private double riskProbability;
    private double riskScore;
    private String riskLevel;
    private String recommendations;
}
