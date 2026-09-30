package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.common.BusinessException;
import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.repository.FinanceTransactionRepository;
import com.aiempowerment.platform.repository.RiskAlertRuleRepository;
import com.aiempowerment.platform.service.PythonMlClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;
import com.aiempowerment.platform.model.dto.analysis.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class FinanceAnalysisServiceTest {

    @Mock private FinanceTransactionRepository financeTransactionRepository;
    @Mock private RiskAlertRuleRepository riskAlertRuleRepository;
    @Mock private PythonMlClient pythonMlClient;

    private FinanceAnalysisService service;

    @BeforeEach
    void setUp() {
        service = new FinanceAnalysisService(financeTransactionRepository, riskAlertRuleRepository, pythonMlClient, new FinanceRuleEngine());
    }

    private FinanceTransaction createTx(Long id, String txnNo, String riskLevel, String status,
            BigDecimal amount, Double riskScore, LocalDateTime time) {
        FinanceTransaction t = new FinanceTransaction();
        t.setId(id);
        t.setTransactionNo(txnNo);
        t.setRiskLevel(riskLevel);
        t.setStatus(status);
        t.setAmount(amount);
        t.setRiskScore(riskScore);
        t.setCreateTime(time);
        t.setUserName("用户" + id);
        return t;
    }

    // ====== evaluateTransactionRisk ======

    @Test
    @DisplayName("evaluateTransactionRisk 存在时返回风险评估")
    void evaluateTransactionRisk_exists() {
        when(financeTransactionRepository.findById(1L)).thenReturn(Optional.of(
            createTx(1L, "TXN001", "低风险", "正常", new BigDecimal("50000.00"), 30.0, LocalDateTime.now())));
        when(riskAlertRuleRepository.findAll()).thenReturn(List.of());

        TransactionRiskDTO result = service.evaluateTransactionRisk(1L);

        assertNotNull(result);
    }

    @Test
    @DisplayName("evaluateTransactionRisk 不存在时返回错误信息")
    void evaluateTransactionRisk_notExists() {
        when(financeTransactionRepository.findById(999L)).thenReturn(Optional.empty());

        TransactionRiskDTO result = service.evaluateTransactionRisk(999L);

        assertNotNull(result); assertTrue(result.getRiskLevel() != null || result.getRiskScore() >= 0);
    }

    // ====== analyzeRuleHits ======

    @Test
    @DisplayName("analyzeRuleHits 应返回规则命中统计")
    void analyzeRuleHits_shouldReturnStats() {
        when(riskAlertRuleRepository.findAll()).thenReturn(List.of(new RiskAlertRule(), new RiskAlertRule()));
        when(financeTransactionRepository.findAll()).thenReturn(List.of(
            createTx(1L, "T1", "高风险", "已拦截", new BigDecimal("100000"), 95.0, LocalDateTime.now()),
            createTx(2L, "T2", "中风险", "待处理", new BigDecimal("5000"), 50.0, LocalDateTime.now())
        ));

        List<RuleHitDTO> result = service.analyzeRuleHits();

        assertNotNull(result);
    }

    // ====== predictTransactionTrend ======

    @Test
    @DisplayName("predictTransactionTrend 应返回趋势预测列表")
    void predictTransactionTrend_shouldReturnTrends() {
        List<FinanceTransaction> txns = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            txns.add(createTx((long)i, "T" + i, "低风险", "正常",
                new BigDecimal("1000"), 20.0, LocalDateTime.now().minusDays(i)));
        }
        when(financeTransactionRepository.findAll()).thenReturn(txns);

        List<TrendPredictionDTO> result = service.predictTransactionTrend(5);

        assertNotNull(result);
        assertEquals(5, result.size());
        assertNotNull(result.get(0).getDate());
        assertNotNull(result.get(0).getConfidenceRange());
    }

    // ====== analyzeUserBehaviorProfiles ======

    @Test
    @DisplayName("analyzeUserBehaviorProfiles 有交易时返回用户画像")
    void analyzeUserBehaviorProfiles_withTransactions() {
        when(financeTransactionRepository.findAll()).thenReturn(List.of(
            createTx(1L, "T1", "低风险", "正常", new BigDecimal("100"), 10.0, LocalDateTime.now()),
            createTx(2L, "T2", "低风险", "正常", new BigDecimal("200"), 10.0, LocalDateTime.now())
        ));

        List<UserBehaviorProfileDTO> result = service.analyzeUserBehaviorProfiles();

        assertNotNull(result);
    }

    // ====== detectSuspiciousTransactions ======

    @Test
    @DisplayName("detectSuspiciousTransactions 应检测可疑交易")
    void detectSuspiciousTransactions_shouldFind() {
        when(financeTransactionRepository.findAll()).thenReturn(List.of(
            createTx(1L, "T1", "低风险", "正常", new BigDecimal("100"), 10.0, LocalDateTime.now()),
            createTx(2L, "T2", "高风险", "已拦截", new BigDecimal("200000"), 95.0, LocalDateTime.now())
        ));

        List<SuspiciousTransactionDTO> result = service.detectSuspiciousTransactions();

        assertNotNull(result);
    }

    // ====== getRiskTrendData ======

    @Test
    @DisplayName("getRiskTrendData 应返回风险趋势")
    void getRiskTrendData_shouldReturnTrend() {
        List<FinanceTransaction> txns = new ArrayList<>();
        for (int i = 0; i < 14; i++) {
            txns.add(createTx((long)i, "T" + i, i % 3 == 0 ? "高风险" : "低风险", "正常",
                new BigDecimal("1000"), 20.0 + i * 3.0, LocalDateTime.now().minusDays(i)));
        }
        when(financeTransactionRepository.findAll()).thenReturn(txns);

        List<RiskTrendDTO> result = service.getRiskTrendData();

        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    // ====== getRealTimeRiskAlerts ======

    @Test
    @DisplayName("getRealTimeRiskAlerts 应返回告警列表")
    void getRealTimeRiskAlerts_shouldReturnAlerts() {
        when(financeTransactionRepository.findAll()).thenReturn(List.of(
            createTx(1L, "T1", "高风险", "待处理", new BigDecimal("100000"), 95.0, LocalDateTime.now())
        ));

        List<RiskAlertDTO> result = service.getRealTimeRiskAlerts();

        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    // ====== getMultiDimensionalRisk ======

    @Test
    @DisplayName("getMultiDimensionalRisk 存在时返回多维分析")
    void getMultiDimensionalRisk_exists() {
        FinanceTransaction tx = createTx(1L, "T1", "高风险", "待处理",
            new BigDecimal("50000"), 85.0, LocalDateTime.now());
        when(financeTransactionRepository.findById(1L)).thenReturn(Optional.of(tx));
        when(financeTransactionRepository.findAll()).thenReturn(List.of(tx));

        MultiDimensionalRiskDTO result = service.getMultiDimensionalRisk(1L);

        assertNotNull(result);
    }

    @Test
    @DisplayName("getMultiDimensionalRisk 不存在时应抛出业务异常（不伪造数据）")
    void getMultiDimensionalRisk_notExists() {
        when(financeTransactionRepository.findById(999L)).thenReturn(Optional.empty());

        BusinessException ex = assertThrows(BusinessException.class, () -> service.getMultiDimensionalRisk(999L));

        assertEquals("交易不存在", ex.getMessage());
        assertEquals(404, ex.getCode());
    }

    // ====== getTransactionNetworkAnalysis ======

    @Test
    @DisplayName("getTransactionNetworkAnalysis 应返回网络分析")
    void getTransactionNetworkAnalysis_shouldReturnAnalysis() {
        when(financeTransactionRepository.findAll()).thenReturn(List.of(
            createTx(1L, "T1", "低风险", "正常", new BigDecimal("100"), 10.0, LocalDateTime.now()),
            createTx(2L, "T2", "高风险", "已拦截", new BigDecimal("200000"), 95.0, LocalDateTime.now())
        ));

        TransactionNetworkDTO result = service.getTransactionNetworkAnalysis();

        assertNotNull(result);
    }

    // ====== generateRiskAssessmentReport ======

    @Test
    @DisplayName("generateRiskAssessmentReport 应生成报告")
    void generateRiskAssessmentReport_shouldGenerate() {
        when(financeTransactionRepository.findAll()).thenReturn(List.of(
            createTx(1L, "T1", "高风险", "已拦截", new BigDecimal("100000"), 95.0, LocalDateTime.now()),
            createTx(2L, "T2", "低风险", "正常", new BigDecimal("100"), 10.0, LocalDateTime.now())
        ));
        when(riskAlertRuleRepository.findAll()).thenReturn(List.of());

        FinanceReportDTO result = service.generateRiskAssessmentReport();

        assertNotNull(result);
    }
}

