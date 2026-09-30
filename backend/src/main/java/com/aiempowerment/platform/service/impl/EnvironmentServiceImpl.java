package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.AirQualityRecord;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import com.aiempowerment.platform.repository.AirQualityRecordRepository;
import com.aiempowerment.platform.repository.EnvironmentMonitorPointRepository;
import com.aiempowerment.platform.service.EnvironmentService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class EnvironmentServiceImpl implements EnvironmentService {

    private final EnvironmentMonitorPointRepository monitorPointRepository;
    private final AirQualityRecordRepository airQualityRecordRepository;

    // ==================== 监测点管理 ====================

    @Override
    public List<EnvironmentMonitorPoint> findAllPoints() {
        return monitorPointRepository.findAll();
    }

    @Override
    public EnvironmentMonitorPoint findPointById(Long id) {
        return monitorPointRepository.findById(id).orElse(null);
    }

    @Override
    @Transactional
    public EnvironmentMonitorPoint savePoint(EnvironmentMonitorPoint point) {
        return monitorPointRepository.save(point);
    }

    @Override
    @Transactional
    public void deletePoint(Long id) {
        monitorPointRepository.deleteById(id);
    }

    @Override
    public List<EnvironmentMonitorPoint> searchPoints(String pointName, String status, String location, String monitorType) {
        if (pointName != null && !pointName.isEmpty()) {
            return monitorPointRepository.findByPointNameContaining(pointName);
        }
        if (status != null && !status.isEmpty()) {
            return monitorPointRepository.findByStatus(status);
        }
        if (location != null && !location.isEmpty()) {
            return monitorPointRepository.findByLocationContaining(location);
        }
        if (monitorType != null && !monitorType.isEmpty()) {
            return monitorPointRepository.findByMonitorType(monitorType);
        }
        return monitorPointRepository.findAll();
    }

    // ==================== 空气质量记录 ====================

    @Override
    public List<AirQualityRecord> findAllRecords() {
        return airQualityRecordRepository.findAll();
    }

    @Override
    public List<AirQualityRecord> findRecordsByPointId(Long pointId) {
        return airQualityRecordRepository.findByPointId(pointId);
    }

    @Override
    public List<AirQualityRecord> findRecordsByPointIdOrderByTimeDesc(Long pointId) {
        return airQualityRecordRepository.findByPointIdOrderByRecordTimeDesc(pointId);
    }

    @Override
    public List<AirQualityRecord> findRecordsByTimeBetween(LocalDateTime start, LocalDateTime end) {
        return airQualityRecordRepository.findByRecordTimeBetween(start, end);
    }

    @Override
    public AirQualityRecord findLatestByPointId(Long pointId) {
        return airQualityRecordRepository.findTopByPointIdOrderByRecordTimeDesc(pointId).orElse(null);
    }

    @Override
    public List<AirQualityRecord> findTop10Latest() {
        return airQualityRecordRepository.findTop10ByOrderByRecordTimeDesc();
    }

    @Override
    @Transactional
    public AirQualityRecord saveAirQualityRecord(AirQualityRecord record) {
        if (record.getRecordTime() == null) {
            record.setRecordTime(LocalDateTime.now());
        }
        return airQualityRecordRepository.save(record);
    }

    // ==================== 统计分析 ====================

    @Override
    public Map<String, Object> getStatistics() {
        List<EnvironmentMonitorPoint> allPoints = monitorPointRepository.findAll();

        // 监测点总数
        int totalPoints = allPoints.size();

        // 按状态统计
        Map<String, Long> statusCount = allPoints.stream()
                .collect(Collectors.groupingBy(
                        p -> p.getStatus() != null ? p.getStatus() : "未知",
                        LinkedHashMap::new,
                        Collectors.counting()
                ));

        // 按监测类型统计
        Map<String, Long> monitorTypeCount = allPoints.stream()
                .collect(Collectors.groupingBy(
                        p -> p.getMonitorType() != null ? p.getMonitorType() : "未知",
                        LinkedHashMap::new,
                        Collectors.counting()
                ));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalPoints", totalPoints);
        result.put("statusDistribution", statusCount);
        result.put("monitorTypeDistribution", monitorTypeCount);
        return result;
    }

    @Override
    public Map<String, Object> getSummary() {
        List<EnvironmentMonitorPoint> allPoints = monitorPointRepository.findAll();
        List<AirQualityRecord> latestRecords = airQualityRecordRepository.findTop10ByOrderByRecordTimeDesc();

        // 总监测点数
        int totalPoints = allPoints.size();

        // 各AQI等级统计
        Map<String, Long> aqiLevelCount = new LinkedHashMap<>();
        for (AirQualityRecord record : latestRecords) {
            String level = getAqiLevel(record.getAqi());
            aqiLevelCount.merge(level, 1L, Long::sum);
        }

        // 最新更新时间
        LocalDateTime latestUpdateTime = latestRecords.stream()
                .map(AirQualityRecord::getRecordTime)
                .filter(Objects::nonNull)
                .max(Comparator.naturalOrder())
                .orElse(null);

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalPoints", totalPoints);
        result.put("aqiLevelDistribution", aqiLevelCount);
        result.put("latestUpdateTime", latestUpdateTime);
        return result;
    }

    /**
     * 根据AQI值获取等级
     */
    private String getAqiLevel(Integer aqi) {
        if (aqi == null) return "未知";
        if (aqi <= 50) return "优";
        if (aqi <= 100) return "良";
        if (aqi <= 150) return "轻度污染";
        if (aqi <= 200) return "中度污染";
        if (aqi <= 300) return "重度污染";
        return "严重污染";
    }
}
