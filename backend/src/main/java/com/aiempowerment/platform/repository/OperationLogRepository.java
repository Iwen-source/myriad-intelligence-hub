package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.OperationLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface OperationLogRepository extends JpaRepository<OperationLog, Long> {

    List<OperationLog> findByUserId(Long userId);

    List<OperationLog> findByModule(String module);

    List<OperationLog> findByUsername(String username);

    List<OperationLog> findByCreateTimeBetween(LocalDateTime start, LocalDateTime end);
}
