package com.aiempowerment.platform.model.dto.analysis;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

/**
 * 用户行为画像 DTO
 * <p>
 * 由 {@code analyzeUserBehaviorProfiles} 返回。segmentName / profileDescription 仅在 ML 分群成功时存在，
 * 因此标注 NON_NULL 以保持与原 Map 版本一致的序列化行为（缺省而非 null）。
 */
@Data
public class UserBehaviorProfileDTO {
    private Long userId;
    private String userName;
    private int totalTransactions;
    private double totalAmount;
    private double avgAmount;
    private long highRiskCount;
    private long riskRatio;
    private String riskLevel;
    private String spendingPattern;

    @JsonInclude(JsonInclude.Include.NON_NULL)
    private String segmentName;

    @JsonInclude(JsonInclude.Include.NON_NULL)
    private String profileDescription;

    private int securityScore;
    private String riskTrend;
    private boolean mlGenerated;
}
