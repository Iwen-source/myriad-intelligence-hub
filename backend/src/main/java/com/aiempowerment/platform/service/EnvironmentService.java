package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.entity.AirQualityRecord;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;

import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

public interface EnvironmentService {
    // 监测点管理
    List<EnvironmentMonitorPoint> findAllPoints();
    EnvironmentMonitorPoint findPointById(Long id);
    EnvironmentMonitorPoint savePoint(EnvironmentMonitorPoint point);
    void deletePoint(Long id);
    List<EnvironmentMonitorPoint> searchPoints(String pointName, String status, String location, String monitorType);

    // 空气质量记录
    List<AirQualityRecord> findAllRecords();
    List<AirQualityRecord> findRecordsByPointId(Long pointId);
    List<AirQualityRecord> findRecordsByPointIdOrderByTimeDesc(Long pointId);
    List<AirQualityRecord> findRecordsByTimeBetween(LocalDateTime start, LocalDateTime end);
    AirQualityRecord findLatestByPointId(Long pointId);
    List<AirQualityRecord> findTop10Latest();
    AirQualityRecord saveAirQualityRecord(AirQualityRecord record);

    // 统计分析
    Map<String, Object> getStatistics();
    Map<String, Object> getSummary();
}
