package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.AirQualityRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

@Repository
public interface AirQualityRecordRepository extends JpaRepository<AirQualityRecord, Long> {

    List<AirQualityRecord> findByPointId(Long pointId);

    List<AirQualityRecord> findByPointIdOrderByRecordTimeDesc(Long pointId);

    List<AirQualityRecord> findByRecordTimeBetween(LocalDateTime start, LocalDateTime end);

    Optional<AirQualityRecord> findTopByPointIdOrderByRecordTimeDesc(Long pointId);

    List<AirQualityRecord> findTop10ByOrderByRecordTimeDesc();
}
