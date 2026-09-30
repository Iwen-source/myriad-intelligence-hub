package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 设备故障预测视图对象 - 替换 predictDeviceFailure() 中的 fallback Map
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class DeviceFailurePredictionVO {
    private double failureProbability;
    private String riskLevel;
    private String recommendations;
}
