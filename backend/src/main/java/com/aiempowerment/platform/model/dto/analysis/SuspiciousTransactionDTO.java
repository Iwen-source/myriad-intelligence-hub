package com.aiempowerment.platform.model.dto.analysis;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

import java.util.List;

/**
 * 可疑交易 DTO
 * <p>
 * 由 {@code detectSuspiciousTransactions} 返回。reasons 仅在规则 fallback 命中时存在，标注 NON_NULL。
 */
@Data
public class SuspiciousTransactionDTO {
    private Long transactionId;
    private String transactionNo;
    private String userName;
    private double amount;
    private String type;
    private double fraudProbability;
    private String alertLevel;
    private String actionSuggestion;

    @JsonInclude(JsonInclude.Include.NON_NULL)
    private List<String> reasons;

    private String time;
    private boolean mlGenerated;
}
