package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.Map;

/**
 * 能源趋势视图对象 - 替换 getTrend() 中的 Map<String, Map<String, Double>>
 * 序列化为: { "2026-01-01": {"空调": 123.4, "照明": 56.7}, ... }
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class EnergyTrendVO {
    private Map<String, Map<String, Double>> trendData;
}
