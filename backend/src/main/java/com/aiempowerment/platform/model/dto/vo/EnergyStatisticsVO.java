package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 能源统计视图对象 - 替换 getStatistics() 中的 Map<String,Object>
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class EnergyStatisticsVO {
    private Map<String, Double> typeConsumption;
    private int totalDevices;
    private double totalConsumption;
}
