package com.aiempowerment.platform.model.dto.analysis;

import lombok.Data;

import java.util.List;

/**
 * 交易网络分析 DTO
 * <p>
 * 由 {@code getTransactionNetworkAnalysis} 返回。edges 目前未生成用户间边，恒为空列表。
 */
@Data
public class TransactionNetworkDTO {
    private List<NetworkNode> nodes;
    private int totalNodes;
    private List<Object> edges;
    private int totalEdges;
    private boolean mlGenerated;

    @Data
    public static class NetworkNode {
        private Long userId;
        private String userName;
        private int transactionCount;
        private double totalAmount;
    }
}
