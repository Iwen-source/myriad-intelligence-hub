package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.FinanceTransaction;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface FinanceTransactionRepository extends JpaRepository<FinanceTransaction, Long> {

    List<FinanceTransaction> findByTransactionNo(String transactionNo);

    List<FinanceTransaction> findByRiskLevel(String riskLevel);

    Page<FinanceTransaction> findByRiskLevel(String riskLevel, Pageable pageable);

    List<FinanceTransaction> findByStatus(String status);

    List<FinanceTransaction> findByCreateTimeBetween(LocalDateTime start, LocalDateTime end);

    List<FinanceTransaction> findByUserId(Long userId);

    List<FinanceTransaction> findByRiskScoreGreaterThanEqual(Double minScore);

    long countByRiskLevel(String riskLevel);

    Page<FinanceTransaction> findAll(Pageable pageable);

    long countByStatus(String status);
}
