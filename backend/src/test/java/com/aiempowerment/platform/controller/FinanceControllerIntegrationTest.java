package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.FinanceService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
@DisplayName("FinanceController 集成测试")
class FinanceControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private FinanceService financeService;

    @MockBean
    private AIAnalysisService aiAnalysisService;

    private FinanceTransaction createTx(Long id, String txnNo, String riskLevel) {
        FinanceTransaction t = new FinanceTransaction();
        t.setId(id);
        t.setTransactionNo(txnNo);
        t.setRiskLevel(riskLevel);
        t.setAmount(new BigDecimal("10000"));
        t.setUserName("用户" + id);
        t.setStatus("正常");
        return t;
    }

    @Test
    @DisplayName("GET /finance/transactions 返回交易列表")
    void getAllTransactions_shouldReturnList() throws Exception {
        when(financeService.findAllTransactions()).thenReturn(List.of(
                createTx(1L, "TXN001", "低风险"),
                createTx(2L, "TXN002", "高风险")
        ));

        mockMvc.perform(get("/finance/transactions"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /finance/transactions/1 返回单笔交易")
    void getTransaction_shouldReturnSingle() throws Exception {
        when(financeService.findTransactionById(1L)).thenReturn(createTx(1L, "TXN001", "低风险"));

        mockMvc.perform(get("/finance/transactions/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.transactionNo").value("TXN001"));
    }

    @Test
    @DisplayName("GET /finance/rules 返回规则列表")
    void getAllRules_shouldReturnList() throws Exception {
        RiskAlertRule rule = new RiskAlertRule();
        rule.setId(1L);
        rule.setRuleName("大额交易规则");
        when(financeService.findAllRules()).thenReturn(List.of(rule));

        mockMvc.perform(get("/finance/rules"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(1));
    }

    @Test
    @DisplayName("GET /finance/risk-summary 返回风险统计")
    void getRiskSummary_shouldReturnSummary() throws Exception {
        when(financeService.getRiskSummary()).thenReturn(Map.of("high", 10, "medium", 20, "low", 100));

        mockMvc.perform(get("/finance/risk-summary"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.high").value(10));
    }

    @Test
    @DisplayName("GET /finance/analysis/rule-hits 返回规则命中分析")
    void analyzeRuleHits_shouldReturnList() throws Exception {
        when(aiAnalysisService.analyzeRuleHits()).thenReturn(List.of());

        mockMvc.perform(get("/finance/analysis/rule-hits"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data").isArray());
    }
}
