package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.dto.vo.CustomerChurnVO;
import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.service.FinanceService;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 金融风控控制器 - AI应用场景模块
 * 🆕 V4: 新增客户流失预测 (真实XGBoost模型)
 */
@Slf4j
@RestController
@RequestMapping("/finance")
@RequiredArgsConstructor
public class FinanceController {

    private final FinanceService financeService;
    private final AIAnalysisService aiAnalysisService;
    private final PythonMlClient pythonMlClient;

    // ===== 交易管理 =====
    @GetMapping("/transactions")
    public ApiResponse<?> getAllTransactions() {
        return ApiResponse.success(financeService.findAllTransactions());
    }

    @GetMapping("/transactions/{id}")
    public ApiResponse<?> getTransaction(@PathVariable Long id) {
        return ApiResponse.success(financeService.findTransactionById(id));
    }

    @PostMapping("/transactions")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> saveTransaction(@RequestBody FinanceTransaction transaction) {
        return ApiResponse.success(financeService.saveTransaction(transaction));
    }

    @DeleteMapping("/transactions/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deleteTransaction(@PathVariable Long id) {
        financeService.deleteTransaction(id);
        return ApiResponse.success("删除成功");
    }

    // ===== 风控规则 =====
    @GetMapping("/rules")
    public ApiResponse<?> getAllRules() {
        return ApiResponse.success(financeService.findAllRules());
    }

    @PostMapping("/rules")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> saveRule(@RequestBody RiskAlertRule rule) {
        return ApiResponse.success(financeService.saveRule(rule));
    }

    @PutMapping("/rules/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> updateRule(@PathVariable Long id, @RequestBody RiskAlertRule rule) {
        return ApiResponse.success(financeService.updateRule(id, rule));
    }

    @DeleteMapping("/rules/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deleteRule(@PathVariable Long id) {
        financeService.deleteRule(id);
        return ApiResponse.success("删除成功");
    }

    // ===== AI分析 =====
    @GetMapping("/analysis/risk/{id}")
    public ApiResponse<?> evaluateTransactionRisk(@PathVariable Long id) {
        return ApiResponse.success(aiAnalysisService.evaluateTransactionRisk(id));
    }

    @GetMapping("/analysis/rule-hits")
    public ApiResponse<?> analyzeRuleHits() {
        return ApiResponse.success(aiAnalysisService.analyzeRuleHits());
    }

    // ===== 新增：高级 AI 金融风控 =====

    /** 交易趋势预测 */
    @GetMapping("/analysis/trend-prediction")
    public ApiResponse<?> predictTransactionTrend(@RequestParam(defaultValue = "7") int days) {
        return ApiResponse.success(aiAnalysisService.predictTransactionTrend(days));
    }

    /** 用户行为画像 */
    @GetMapping("/analysis/user-profiles")
    public ApiResponse<?> analyzeUserBehaviorProfiles() {
        return ApiResponse.success(aiAnalysisService.analyzeUserBehaviorProfiles());
    }

    /** 可疑交易检测 */
    @GetMapping("/analysis/suspicious")
    public ApiResponse<?> detectSuspiciousTransactions() {
        return ApiResponse.success(aiAnalysisService.detectSuspiciousTransactions());
    }

    /** 多维度风险评估 */
    @GetMapping("/analysis/multi-risk/{id}")
    public ApiResponse<?> getMultiDimensionalRisk(@PathVariable Long id) {
        return ApiResponse.success(aiAnalysisService.getMultiDimensionalRisk(id));
    }

    /** 交易网络分析 */
    @GetMapping("/analysis/network")
    public ApiResponse<?> getTransactionNetworkAnalysis() {
        return ApiResponse.success(aiAnalysisService.getTransactionNetworkAnalysis());
    }

    /** AI风险评估报告 */
    @GetMapping("/analysis/report")
    public ApiResponse<?> generateRiskAssessmentReport() {
        return ApiResponse.success(aiAnalysisService.generateRiskAssessmentReport());
    }

    /** 实时风险预警 */
    @GetMapping("/analysis/alerts")
    public ApiResponse<?> getRealTimeRiskAlerts() {
        return ApiResponse.success(aiAnalysisService.getRealTimeRiskAlerts());
    }

    /** 风险趋势数据 */
    @GetMapping("/analysis/risk-trend")
    public ApiResponse<?> getRiskTrendData() {
        return ApiResponse.success(aiAnalysisService.getRiskTrendData());
    }

    // ===== 分页查询 =====
    @GetMapping("/transactions/page")
    public ApiResponse<?> getTransactionsByPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String riskLevel) {
        return ApiResponse.success(financeService.findTransactionsByPage(page, size, riskLevel));
    }

    /** 风险汇总 */
    @GetMapping("/risk-summary")
    public ApiResponse<?> getRiskSummary() {
        return ApiResponse.success(financeService.getRiskSummary());
    }

    // ===== 仪表盘 =====
    @GetMapping("/dashboard")
    public ApiResponse<?> getDashboard() {
        return ApiResponse.success(financeService.getDashboard());
    }

    // ===== 🆕 V4 AI增强: 客户流失预测 (真实XGBoost模型) =====
    @PostMapping("/analysis/customer-churn")
    public ApiResponse<?> predictCustomerChurn(@RequestBody Map<String, Object> customerParams) {
        // Fill defaults
        if (!customerParams.containsKey("avg_balance")) customerParams.put("avg_balance", 10000);
        if (!customerParams.containsKey("monthly_transaction_count")) customerParams.put("monthly_transaction_count", 10);
        if (!customerParams.containsKey("days_since_last_transaction")) customerParams.put("days_since_last_transaction", 5);
        if (!customerParams.containsKey("login_frequency_per_week")) customerParams.put("login_frequency_per_week", 4);

        JsonNode result = pythonMlClient.financeCustomerChurnPredict(customerParams);
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }

        // Fallback
        int daysSinceTx = ((Number) customerParams.getOrDefault("days_since_last_transaction", 5)).intValue();
        int txCount = ((Number) customerParams.getOrDefault("monthly_transaction_count", 10)).intValue();
        double balance = ((Number) customerParams.getOrDefault("avg_balance", 10000)).doubleValue();
        double prob = Math.min(0.9, Math.max(0.01,
                0.1 + Math.log1p(daysSinceTx) * 0.05 - txCount * 0.008 - Math.log1p(balance) * 0.002));
        String riskLevel = prob < 0.2 ? "低风险 🟢" : prob < 0.4 ? "中等风险 🟡"
                : prob < 0.7 ? "高风险 🟠" : "危急 🔴";

        CustomerChurnVO fallback = new CustomerChurnVO(
                Math.round(prob * 10000.0) / 10000.0,
                Math.round(prob * 1000.0) / 10.0,
                riskLevel
        );
        return ApiResponse.success(fallback);
    }
}
