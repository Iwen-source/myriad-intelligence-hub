package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.FinanceTransaction;
import com.aiempowerment.platform.model.entity.RiskAlertRule;
import com.aiempowerment.platform.repository.FinanceTransactionRepository;
import com.aiempowerment.platform.repository.RiskAlertRuleRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * 初始化 - 金融风控数据（交易记录、风控规则）
 */
@Slf4j
@Component
@Order(4)
@RequiredArgsConstructor
public class FinanceDataInitializer implements CommandLineRunner {

    private final FinanceTransactionRepository financeTransactionRepository;
    private final RiskAlertRuleRepository riskAlertRuleRepository;
    private final Random random = new Random(42);

    @Override
    public void run(String... args) {
        initFinanceData();
    }

    private void initFinanceData() {
        if (financeTransactionRepository.count() > 0) return;
        // 生成 200 条模拟交易，覆盖更多场景
        String[] types = {"转账", "消费", "提现", "充值", "理财", "贷款", "外汇"};
        String[] statuses = {"正常", "正常", "正常", "正常", "可疑", "已拦截"};
        String[] users = {"张三", "李四", "王五", "赵六", "钱七", "孙八", "周九", "吴十", "郑十一", "陈十二"};
        String[] descriptions = {
            "工资代发", "生活缴费", "网络购物", "餐饮消费", "交通出行",
            "医疗支出", "教育费用", "房租缴纳", "投资理财", "转账汇款",
            "跨境支付", "电费缴纳", "水费缴纳", "话费充值", "保险缴费",
            "股票交易", "基金申购", "理财赎回", "信用卡还款", "贷款发放"
        };
        List<FinanceTransaction> transactions = new ArrayList<>();
        for (int i = 0; i < 200; i++) {
            FinanceTransaction tx = new FinanceTransaction();
            tx.setTransactionNo("TXN" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"))
                    + String.format("%04d", i + 1));
            tx.setUserId((long) (random.nextInt(10) + 1));
            tx.setUserName(users[random.nextInt(users.length)]);
            // 模拟真实金额分布：大部分小额，少量大额
            double amount;
            if (random.nextDouble() < 0.7) {
                amount = 100 + random.nextDouble() * 5000;
            } else if (random.nextDouble() < 0.9) {
                amount = 5000 + random.nextDouble() * 50000;
            } else {
                amount = 50000 + random.nextDouble() * 500000;
            }
            tx.setAmount(BigDecimal.valueOf(Math.round(amount * 100.0) / 100.0));
            tx.setTransactionType(types[random.nextInt(types.length)]);
            tx.setSourceAccount("6222****" + String.format("%04d", random.nextInt(9999)));
            tx.setTargetAccount("6222****" + String.format("%04d", random.nextInt(9999)));
            double riskScore = Math.min(100, random.nextDouble() * 120);
            tx.setRiskScore(riskScore);
            tx.setRiskLevel(riskScore < 30 ? "低" : riskScore < 60 ? "中" : riskScore < 80 ? "高" : "严重");
            tx.setStatus(statuses[random.nextInt(statuses.length)]);
            tx.setDescription(descriptions[i % descriptions.length]);
            tx.setCreateTime(LocalDateTime.now().minusHours(random.nextInt(720)).minusMinutes(random.nextInt(60)));
            transactions.add(tx);
        }
        financeTransactionRepository.saveAll(transactions);

        if (riskAlertRuleRepository.count() == 0) {
            List<RiskAlertRule> rules = List.of(
                createRule("大额交易预警", "金额", "amount > 50000", 50000.0, "高", true),
                createRule("频繁交易检测", "频率", "count > 10 in 1h", 10.0, "中", true),
                createRule("异地登录风控", "地域", "login_city != usual_city", 0.0, "高", true),
                createRule("夜间交易限制", "时间", "hour < 6 || hour > 23", 0.0, "中", true),
                createRule("跨境交易审核", "地域", "country != CN", 0.0, "严重", true),
                createRule("可疑账户监控", "账户特征", "risk_score > 60", 60.0, "严重", true),
                createRule("快速转账风控", "行为", "transfer_interval < 30s", 0.0, "高", true),
                createRule("新设备登录验证", "设备", "new_device_login", 0.0, "中", true)
            );
            riskAlertRuleRepository.saveAll(rules);
        }

        log.info("✅ 已初始化金融风控数据: {} 条交易, 8 条规则", transactions.size());
    }

    private RiskAlertRule createRule(String name, String type, String condition, Double threshold, String level, boolean enabled) {
        RiskAlertRule rule = new RiskAlertRule();
        rule.setRuleName(name);
        rule.setRuleType(type);
        rule.setAlertCondition(condition);
        rule.setThreshold(threshold);
        rule.setRiskLevel(level);
        rule.setEnabled(enabled);
        rule.setDescription(name + " - AI智能风控规则");
        return rule;
    }
}