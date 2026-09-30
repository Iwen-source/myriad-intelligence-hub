package com.aiempowerment.platform.model.dto.analysis;

import lombok.Data;

/**
 * 交易趋势预测 DTO（单日预测点）
 * <p>
 * 由 {@code predictTransactionTrend} 返回，字段名与原 Map 版本保持一致以保证前端契约不变。
 */
@Data
public class TrendPredictionDTO {
    private String date;
    private String dayOfWeek;
    private long predictedCount;
    private double predictedAmount;
    private long highRiskCount;
    private String confidenceRange;
    private boolean mlGenerated;
}
