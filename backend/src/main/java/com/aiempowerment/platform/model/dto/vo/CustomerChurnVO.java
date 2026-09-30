package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 客户流失预测视图对象 - 替换 predictCustomerChurn() 中的 fallback Map
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class CustomerChurnVO {
    private double churnProbability;
    private double churnScore;
    private String riskLevel;
}
