package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import org.springframework.data.domain.Page;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public interface FinanceService {
    // 交易管理
    List<FinanceTransaction> findAllTransactions();
    FinanceTransaction findTransactionById(Long id);
    FinanceTransaction saveTransaction(FinanceTransaction transaction);
    void deleteTransaction(Long id);
    List<FinanceTransaction> findTransactionByNo(String transactionNo);
    List<FinanceTransaction> findTransactionsByRiskLevel(String riskLevel);
    List<FinanceTransaction> findTransactionsByStatus(String status);
    List<FinanceTransaction> findTransactionsByUserId(Long userId);
    List<FinanceTransaction> findTransactionsByRiskScoreGreaterThanEqual(Double minScore);
    List<FinanceTransaction> findTransactionsByCreateTimeBetween(LocalDateTime start, LocalDateTime end);

    // 风控规则管理
    List<RiskAlertRule> findAllRules();
    RiskAlertRule findRuleById(Long id);
    RiskAlertRule saveRule(RiskAlertRule rule);
    RiskAlertRule updateRule(Long id, RiskAlertRule rule);
    void deleteRule(Long id);
    List<RiskAlertRule> findRulesByType(String ruleType);
    List<RiskAlertRule> findEnabledRules();
    List<RiskAlertRule> findRulesByRiskLevel(String riskLevel);

    // 仪表盘
    Map<String, Object> getDashboard();

    // ==================== 分页查询 ====================

    /**
     * 分页查询交易
     */
    Page<FinanceTransaction> findTransactionsByPage(int page, int size, String riskLevel);

    /**
     * 风险汇总统计
     */
    Map<String, Object> getRiskSummary();
}
