package com.aiempowerment.platform.service;

import com.aiempowerment.platform.service.analysis.*;
import com.aiempowerment.platform.model.dto.analysis.*;

import java.util.concurrent.CompletableFuture;
import java.util.List;
import java.util.Map;

/**
 * AI智能分析服务 - 统一的分析引擎接口
 * <p>
 * 继承多个领域特定接口，所有返回值使用类型安全的 DTO。
 * （教育模块和创意设计模块已移除）
 */
public interface AIAnalysisService extends
        EnergyAnalysisInterface,
        EnvironmentAnalysisInterface,
        FinanceAnalysisInterface,
        TrafficAnalysisInterface,
        MedicalAnalysisInterface {

    // ===== 异步 AI 分析（@Async 支持，返回 CompletableFuture） =====

    /** 异步生成能源AI摘要报告 */
    CompletableFuture<EnergySummaryReportDTO> asyncGenerateEnergyReport();

    /** 异步检测环境异常波动 */
    CompletableFuture<List<Map<String, Object>>> asyncDetectEnvironmentAnomalies();

    /** 异步生成风险评估报告 */
    CompletableFuture<FinanceReportDTO> asyncGenerateRiskReport();

    /** 异步进行多因子AQI预测 */
    CompletableFuture<List<Map<String, Object>>> asyncMultiFactorPrediction();

    /** 异步检测可疑交易 */
    CompletableFuture<List<SuspiciousTransactionDTO>> asyncDetectSuspiciousTransactions();
}
