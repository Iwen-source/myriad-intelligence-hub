package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 极端天气分类视图对象 - 替换 classifyExtremeWeather() 中的 fallback Map
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ExtremeWeatherVO {
    private String severityLevel;
    private double confidence;
    private String advisory;
}
