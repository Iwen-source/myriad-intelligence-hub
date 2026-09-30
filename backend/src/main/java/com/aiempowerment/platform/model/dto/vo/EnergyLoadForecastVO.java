package com.aiempowerment.platform.model.dto.vo;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.util.List;

/**
 * 负荷预测视图对象 - 替换 loadForecast() 中的 fallback Map
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class EnergyLoadForecastVO {
    private String source;
    private List<Object> predictions;
    private int peakLoad;
    private String trend;
}
