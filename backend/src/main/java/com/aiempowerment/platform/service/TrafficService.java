package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.entity.TrafficFlowRecord;
import com.aiempowerment.platform.model.entity.TrafficRoadSection;
import org.springframework.data.domain.Page;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

public interface TrafficService {
    // 路段管理
    List<TrafficRoadSection> findAllSections();
    TrafficRoadSection findSectionById(Long id);
    TrafficRoadSection saveSection(TrafficRoadSection section);
    void deleteSection(Long id);
    List<TrafficRoadSection> searchSections(String roadName, String roadType, String status);

    // 流量数据
    List<TrafficFlowRecord> findAllFlowRecords();
    List<TrafficFlowRecord> findFlowRecordsBySectionId(Long sectionId);
    TrafficFlowRecord saveFlowRecord(TrafficFlowRecord record);
    List<TrafficFlowRecord> findFlowBySectionIdAndDate(Long sectionId, LocalDate date);
    List<TrafficFlowRecord> findFlowByDate(LocalDate date);
    List<TrafficFlowRecord> findFlowByDateBetween(LocalDate start, LocalDate end);

    // 概览数据
    Map<String, Object> getOverview();
    Map<String, Object> getFlowData(LocalDate date);

    // ==================== 分页查询 ====================

    /**
     * 分页查询流量记录
     */
    Page<TrafficFlowRecord> findFlowRecordsByPage(int page, int size, Long sectionId);

    /**
     * 拥堵统计
     */
    Map<String, Object> getCongestionStats();
}
