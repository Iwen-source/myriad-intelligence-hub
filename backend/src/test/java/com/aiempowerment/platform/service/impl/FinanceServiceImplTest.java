package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.repository.FinanceTransactionRepository;
import com.aiempowerment.platform.repository.RiskAlertRuleRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class FinanceServiceImplTest {

    @Mock private FinanceTransactionRepository transactionRepository;
    @Mock private RiskAlertRuleRepository ruleRepository;

    private FinanceServiceImpl financeService;

    @BeforeEach
    void setUp() {
        financeService = new FinanceServiceImpl(transactionRepository, ruleRepository);
    }

    private FinanceTransaction createTransaction(Long id, String txnNo, String riskLevel, BigDecimal amount, LocalDateTime time) {
        FinanceTransaction t = new FinanceTransaction();
        t.setId(id);
        t.setTransactionNo(txnNo);
        t.setRiskLevel(riskLevel);
        t.setAmount(amount);
        t.setCreateTime(time);
        t.setUserName("用户" + id);
        return t;
    }

    // ====== Transaction CRUD ======

    @Test
    @DisplayName("findAllTransactions 应返回所有交易")
    void findAllTransactions() {
        when(transactionRepository.findAll()).thenReturn(List.of(
            createTransaction(1L, "TXN001", "低风险", new BigDecimal("100.00"), LocalDateTime.now()),
            createTransaction(2L, "TXN002", "高风险", new BigDecimal("50000.00"), LocalDateTime.now())
        ));
        assertEquals(2, financeService.findAllTransactions().size());
    }

    @Test
    @DisplayName("findTransactionById 存在时返回交易")
    void findTransactionByIdExists() {
        FinanceTransaction t = createTransaction(1L, "TXN001", "低风险", new BigDecimal("100.00"), LocalDateTime.now());
        when(transactionRepository.findById(1L)).thenReturn(Optional.of(t));
        assertNotNull(financeService.findTransactionById(1L));
    }

    @Test
    @DisplayName("findTransactionById 不存在时返回null")
    void findTransactionByIdNotExists() {
        when(transactionRepository.findById(999L)).thenReturn(Optional.empty());
        assertNull(financeService.findTransactionById(999L));
    }

    @Test
    @DisplayName("saveTransaction 应保存并返回")
    void saveTransaction() {
        FinanceTransaction t = createTransaction(null, "TXN003", "中风险", new BigDecimal("5000.00"), LocalDateTime.now());
        when(transactionRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        assertNotNull(financeService.saveTransaction(t));
        verify(transactionRepository).save(t);
    }

    @Test
    @DisplayName("deleteTransaction 应删除")
    void deleteTransaction() {
        financeService.deleteTransaction(1L);
        verify(transactionRepository).deleteById(1L);
    }

    @Test
    @DisplayName("findTransactionByNo 应按编号查询")
    void findByNo() {
        when(transactionRepository.findByTransactionNo("TXN001")).thenReturn(List.of(new FinanceTransaction()));
        assertEquals(1, financeService.findTransactionByNo("TXN001").size());
    }

    @Test
    @DisplayName("findTransactionsByRiskLevel 应按风险等级过滤")
    void findByRiskLevel() {
        when(transactionRepository.findByRiskLevel("高风险")).thenReturn(List.of(new FinanceTransaction()));
        assertEquals(1, financeService.findTransactionsByRiskLevel("高风险").size());
    }

    // ====== RiskAlertRule CRUD ======

    @Test
    @DisplayName("findAllRules 应返回所有规则")
    void findAllRules() {
        RiskAlertRule r = new RiskAlertRule();
        r.setId(1L);
        r.setRuleName("大额交易监控");
        when(ruleRepository.findAll()).thenReturn(List.of(r));
        assertEquals(1, financeService.findAllRules().size());
    }

    @Test
    @DisplayName("saveRule 应保存规则")
    void saveRule() {
        RiskAlertRule r = new RiskAlertRule();
        r.setRuleName("新规则");
        when(ruleRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));
        assertNotNull(financeService.saveRule(r));
    }

    @Test
    @DisplayName("updateRule 存在时只更新非空字段")
    void updateRulePartial() {
        RiskAlertRule existing = new RiskAlertRule();
        existing.setId(1L);
        existing.setRuleName("旧规则");
        existing.setRuleType("金额规则");
        existing.setAlertCondition("amount > 10000");
        existing.setEnabled(true);

        RiskAlertRule update = new RiskAlertRule();
        update.setRuleName("新规则名称");
        // 其他字段不设置 → 应保留原值

        when(ruleRepository.findById(1L)).thenReturn(Optional.of(existing));
        when(ruleRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        RiskAlertRule result = financeService.updateRule(1L, update);

        assertEquals("新规则名称", result.getRuleName());
        assertEquals("金额规则", result.getRuleType()); // 保留原值
        assertTrue(result.getEnabled());
    }

    @Test
    @DisplayName("updateRule 不存在时返回null")
    void updateRuleNotFound() {
        when(ruleRepository.findById(999L)).thenReturn(Optional.empty());
        assertNull(financeService.updateRule(999L, new RiskAlertRule()));
    }

    @Test
    @DisplayName("findEnabledRules 应只返回启用规则")
    void findEnabledRules() {
        when(ruleRepository.findByEnabledTrue()).thenReturn(List.of(new RiskAlertRule()));
        assertEquals(1, financeService.findEnabledRules().size());
    }

    // ====== Dashboard ======

    @Test
    @DisplayName("getDashboard 应返回完整统计")
    void getDashboard() {
        List<FinanceTransaction> txns = Arrays.asList(
            createTransaction(1L, "TXN001", "低风险", new BigDecimal("100.00"), LocalDateTime.now().minusDays(1)),
            createTransaction(2L, "TXN002", "高风险", new BigDecimal("50000.00"), LocalDateTime.now()),
            createTransaction(3L, "TXN003", "中风险", new BigDecimal("8000.00"), LocalDateTime.now().minusHours(5)),
            createTransaction(4L, "TXN004", "高风险", new BigDecimal("100000.00"), LocalDateTime.now())
        );
        when(transactionRepository.findAll()).thenReturn(txns);
        when(ruleRepository.findAll()).thenReturn(List.of());

        Map<String, Object> dashboard = financeService.getDashboard();

        assertEquals(4L, dashboard.get("totalTransactions"));
        assertEquals(3L, dashboard.get("riskTransactionCount"));
        assertTrue(((String)dashboard.get("riskRate")).contains("75"));
        assertNotNull(dashboard.get("riskDistribution"));
        assertNotNull(dashboard.get("recentHighRiskTransactions"));
    }
}
