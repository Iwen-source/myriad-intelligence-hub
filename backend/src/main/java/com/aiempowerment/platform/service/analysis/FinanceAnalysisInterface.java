package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.model.dto.analysis.*;

import java.util.List;

/**
 * 金融AI分析接口 - 交易风险评估、规则分析、可疑交易检测、趋势预测
 * 所有返回值均为类型安全的 DTO
 */
public interface FinanceAnalysisInterface {

    /** 交易风险评分 */
    TransactionRiskDTO evaluateTransactionRisk(Long transactionId);

    /** 风控规则命中分析 */
    List<RuleHitDTO> analyzeRuleHits();

    /** 交易趋势预测（未来N天） */
    List<TrendPredictionDTO> predictTransactionTrend(int days);

    /** 用户行为画像分析 */
    List<UserBehaviorProfileDTO> analyzeUserBehaviorProfiles();

    /** 智能可疑交易检测 */
    List<SuspiciousTransactionDTO> detectSuspiciousTransactions();

    /** 多维度风险评估（雷达图数据） */
    MultiDimensionalRiskDTO getMultiDimensionalRisk(Long transactionId);

    /** 交易关系网络分析 */
    TransactionNetworkDTO getTransactionNetworkAnalysis();

    /** AI风险评估报告 */
    FinanceReportDTO generateRiskAssessmentReport();

    /** 实时风险预警 */
    List<RiskAlertDTO> getRealTimeRiskAlerts();

    /** 风险趋势数据（按天） */
    List<RiskTrendDTO> getRiskTrendData();
}
