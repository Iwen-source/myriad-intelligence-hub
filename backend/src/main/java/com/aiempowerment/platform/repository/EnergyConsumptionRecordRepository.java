package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.EnergyConsumptionRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;

@Repository
public interface EnergyConsumptionRecordRepository extends JpaRepository<EnergyConsumptionRecord, String> {
    List<EnergyConsumptionRecord> findByDeviceId(String deviceId);
    List<EnergyConsumptionRecord> findByConsumptionDateBetween(LocalDate start, LocalDate end);

    List<EnergyConsumptionRecord> findTop3ByDeviceIdOrderByConsumptionDateDesc(String deviceId);

    @Query("SELECT e.consumptionDate, SUM(e.consumptionValue) FROM EnergyConsumptionRecord e GROUP BY e.consumptionDate ORDER BY e.consumptionDate")
    List<Object[]> findConsumptionStatsByDay();

    @Query("SELECT e.deviceId, SUM(e.consumptionValue) FROM EnergyConsumptionRecord e GROUP BY e.deviceId")
    List<Object[]> findConsumptionSumByDevice();
}
