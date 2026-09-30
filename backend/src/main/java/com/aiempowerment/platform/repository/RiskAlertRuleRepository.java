package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.RiskAlertRule;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface RiskAlertRuleRepository extends JpaRepository<RiskAlertRule, Long> {

    List<RiskAlertRule> findByRuleType(String ruleType);

    List<RiskAlertRule> findByEnabledTrue();

    List<RiskAlertRule> findByRiskLevel(String riskLevel);
}
