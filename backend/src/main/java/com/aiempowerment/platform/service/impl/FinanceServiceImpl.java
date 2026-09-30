package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.repository.FinanceTransactionRepository;
import com.aiempowerment.platform.repository.RiskAlertRuleRepository;
import com.aiempowerment.platform.service.FinanceService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
/**
 * FinanceServiceImpl - 金融风控服务实现 - 交易记录查询与风险统计
 */
public class FinanceServiceImpl implements FinanceService {

    private final FinanceTransactionRepository transactionRepository;
    private final RiskAlertRuleRepository ruleRepository;

    // ==================== 交易管理 ====================

    @Override
    public List<FinanceTransaction> findAllTransactions() {
        return transactionRepository.findAll();
    }

    @Override
    public FinanceTransaction findTransactionById(Long id) {
        return transactionRepository.findById(id).orElse(null);
    }

    @Override
    @Transactional
    public FinanceTransaction saveTransaction(FinanceTransaction transaction) {
        return transactionRepository.save(transaction);
    }

    @Override
    @Transactional
    public void deleteTransaction(Long id) {
        transactionRepository.deleteById(id);
    }

    @Override
    public List<FinanceTransaction> findTransactionByNo(String transactionNo) {
        return transactionRepository.findByTransactionNo(transactionNo);
    }

    @Override
    public List<FinanceTransaction> findTransactionsByRiskLevel(String riskLevel) {
        return transactionRepository.findByRiskLevel(riskLevel);
    }

    @Override
    public List<FinanceTransaction> findTransactionsByStatus(String status) {
        return transactionRepository.findByStatus(status);
    }

    @Override
    public List<FinanceTransaction> findTransactionsByUserId(Long userId) {
        return transactionRepository.findByUserId(userId);
    }

    @Override
    public List<FinanceTransaction> findTransactionsByRiskScoreGreaterThanEqual(Double minScore) {
        return transactionRepository.findByRiskScoreGreaterThanEqual(minScore);
    }

    @Override
    public List<FinanceTransaction> findTransactionsByCreateTimeBetween(LocalDateTime start, LocalDateTime end) {
        return transactionRepository.findByCreateTimeBetween(start, end);
    }

    // ==================== 风控规则管理 ====================

    @Override
    public List<RiskAlertRule> findAllRules() {
        return ruleRepository.findAll();
    }

    @Override
    public RiskAlertRule findRuleById(Long id) {
        return ruleRepository.findById(id).orElse(null);
    }

    @Override
    @Transactional
    public RiskAlertRule saveRule(RiskAlertRule rule) {
        return ruleRepository.save(rule);
    }

    @Override
    @Transactional
    public RiskAlertRule updateRule(Long id, RiskAlertRule rule) {
        RiskAlertRule existing = ruleRepository.findById(id).orElse(null);
        if (existing != null) {
            if (rule.getRuleName() != null) existing.setRuleName(rule.getRuleName());
            if (rule.getRuleType() != null) existing.setRuleType(rule.getRuleType());
            if (rule.getAlertCondition() != null) existing.setAlertCondition(rule.getAlertCondition());
            if (rule.getThreshold() != null) existing.setThreshold(rule.getThreshold());
            if (rule.getRiskLevel() != null) existing.setRiskLevel(rule.getRiskLevel());
            if (rule.getEnabled() != null) existing.setEnabled(rule.getEnabled());
            if (rule.getDescription() != null) existing.setDescription(rule.getDescription());
            return ruleRepository.save(existing);
        }
        return null;
    }

    @Override
    @Transactional
    public void deleteRule(Long id) {
        ruleRepository.deleteById(id);
    }

    @Override
    public List<RiskAlertRule> findRulesByType(String ruleType) {
        return ruleRepository.findByRuleType(ruleType);
    }

    @Override
    public List<RiskAlertRule> findEnabledRules() {
        return ruleRepository.findByEnabledTrue();
    }

    @Override
    public List<RiskAlertRule> findRulesByRiskLevel(String riskLevel) {
        return ruleRepository.findByRiskLevel(riskLevel);
    }

    // ==================== 仪表盘 ====================

    @Override
    public Map<String, Object> getDashboard() {
        List<FinanceTransaction> allTransactions = transactionRepository.findAll();

        // 总交易数
        long totalTransactions = allTransactions.size();

        // 风险交易数（riskLevel不为null且不为"低风险"）
        long riskTransactionCount = allTransactions.stream()
                .filter(t -> t.getRiskLevel() != null && !"低风险".equals(t.getRiskLevel()))
                .count();

        // 风险率
        double riskRate = totalTransactions > 0
                ? (double) riskTransactionCount / totalTransactions * 100
                : 0;

        // 今日新增风险（今日创建的高风险交易数）
        LocalDateTime todayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime todayEnd = LocalDateTime.of(LocalDate.now(), LocalTime.MAX);
        long todayRiskCount = allTransactions.stream()
                .filter(t -> t.getCreateTime() != null
                        && t.getCreateTime().isAfter(todayStart)
                        && t.getCreateTime().isBefore(todayEnd)
                        && t.getRiskLevel() != null
                        && !"低风险".equals(t.getRiskLevel()))
                .count();

        // 风险分布（按风险等级分组）
        Map<String, Long> riskDistribution = allTransactions.stream()
                .filter(t -> t.getRiskLevel() != null)
                .collect(Collectors.groupingBy(
                        FinanceTransaction::getRiskLevel,
                        LinkedHashMap::new,
                        Collectors.counting()
                ));

        // 近期高风险交易（最近10条风险等级为高风险的交易）
        List<Map<String, Object>> recentHighRiskTransactions = allTransactions.stream()
                .filter(t -> "高风险".equals(t.getRiskLevel()))
                .sorted(Comparator.comparing(FinanceTransaction::getCreateTime, Comparator.nullsLast(Comparator.reverseOrder())))
                .limit(10)
                .map(t -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("id", t.getId());
                    item.put("transactionNo", t.getTransactionNo());
                    item.put("userName", t.getUserName());
                    item.put("amount", t.getAmount());
                    item.put("riskScore", t.getRiskScore());
                    item.put("createTime", t.getCreateTime());
                    return item;
                })
                .toList();

        // 规则命中统计
        List<Map<String, Object>> ruleHitStats = ruleRepository.findAll().stream()
                .map(rule -> {
                    long hitCount = transactionRepository.countByRiskLevel(rule.getRiskLevel());
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("ruleId", rule.getId());
                    item.put("ruleName", rule.getRuleName());
                    item.put("ruleType", rule.getRuleType());
                    item.put("riskLevel", rule.getRiskLevel());
                    item.put("enabled", rule.getEnabled());
                    item.put("hitCount", hitCount);
                    return item;
                })
                .toList();

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalTransactions", totalTransactions);
        result.put("riskTransactionCount", riskTransactionCount);
        result.put("riskRate", String.format("%.2f%%", riskRate));
        result.put("todayRiskCount", todayRiskCount);
        result.put("riskDistribution", riskDistribution);
        result.put("recentHighRiskTransactions", recentHighRiskTransactions);
        result.put("ruleHitStats", ruleHitStats);
        return result;
    }

    // ==================== 分页查询 ====================

    @Override
    public Page<FinanceTransaction> findTransactionsByPage(int page, int size, String riskLevel) {
        PageRequest pageRequest = PageRequest.of(page, size, Sort.by(Sort.Direction.DESC, "createTime"));
        if (riskLevel != null && !riskLevel.isEmpty()) {
            return transactionRepository.findByRiskLevel(riskLevel, pageRequest);
        }
        return transactionRepository.findAll(pageRequest);
    }

    @Override
    public Map<String, Object> getRiskSummary() {
        List<FinanceTransaction> allTx = transactionRepository.findAll();

        long totalCount = allTx.size();
        long highCount = allTx.stream()
                .filter(tx -> tx.getRiskLevel() != null && ("高".equals(tx.getRiskLevel()) || "严重".equals(tx.getRiskLevel())))
                .count();
        long mediumCount = allTx.stream()
                .filter(tx -> "中".equals(tx.getRiskLevel()))
                .count();
        long lowCount = allTx.stream()
                .filter(tx -> "低".equals(tx.getRiskLevel()))
                .count();

        double totalAmount = allTx.stream()
                .filter(tx -> tx.getAmount() != null)
                .mapToDouble(tx -> tx.getAmount().doubleValue())
                .sum();
        double highRiskAmount = allTx.stream()
                .filter(tx -> tx.getRiskLevel() != null && ("高".equals(tx.getRiskLevel()) || "严重".equals(tx.getRiskLevel())))
                .filter(tx -> tx.getAmount() != null)
                .mapToDouble(tx -> tx.getAmount().doubleValue())
                .sum();

        double highRiskRatio = totalCount > 0 ? (double) highCount / totalCount * 100 : 0;

        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("totalCount", totalCount);
        summary.put("highRiskCount", highCount);
        summary.put("mediumRiskCount", mediumCount);
        summary.put("lowRiskCount", lowCount);
        summary.put("totalAmount", Math.round(totalAmount * 100.0) / 100.0);
        summary.put("highRiskAmount", Math.round(highRiskAmount * 100.0) / 100.0);
        summary.put("highRiskRatio", Math.round(highRiskRatio * 10.0) / 10.0);
        summary.put("safeCount", totalCount - highCount - mediumCount - lowCount);
        summary.put("summaryTime", LocalDateTime.now().toString());
        return summary;
    }
}
