package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.TrafficFlowRecord;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface TrafficFlowRecordRepository extends JpaRepository<TrafficFlowRecord, Long> {

    List<TrafficFlowRecord> findBySectionId(Long sectionId);

    Page<TrafficFlowRecord> findBySectionId(Long sectionId, Pageable pageable);

    List<TrafficFlowRecord> findBySectionIdAndRecordDate(Long sectionId, LocalDate recordDate);

    List<TrafficFlowRecord> findByRecordDate(LocalDate recordDate);

    List<TrafficFlowRecord> findByRecordDateBetween(LocalDate start, LocalDate end);

    List<TrafficFlowRecord> findTop10BySectionIdOrderByRecordHourDesc(Long sectionId);
}
