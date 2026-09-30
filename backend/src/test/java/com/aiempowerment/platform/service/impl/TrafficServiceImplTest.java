package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.TrafficFlowRecord;
import com.aiempowerment.platform.model.entity.TrafficRoadSection;
import com.aiempowerment.platform.repository.TrafficFlowRecordRepository;
import com.aiempowerment.platform.repository.TrafficRoadSectionRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class TrafficServiceImplTest {

    @Mock private TrafficRoadSectionRepository roadSectionRepository;
    @Mock private TrafficFlowRecordRepository flowRecordRepository;

    private TrafficServiceImpl trafficService;

    @BeforeEach
    void setUp() {
        trafficService = new TrafficServiceImpl(roadSectionRepository, flowRecordRepository);
    }

    private TrafficRoadSection createSection(Long id, String name, double length, String status) {
        TrafficRoadSection s = new TrafficRoadSection();
        s.setId(id);
        s.setSectionName(name);
        s.setLength(length);
        s.setStatus(status);
        return s;
    }

    private TrafficFlowRecord createRecord(Long id, Long sectionId, int flowCount, double avgSpeed, LocalDate date) {
        TrafficFlowRecord r = new TrafficFlowRecord();
        r.setId(id);
        r.setSectionId(sectionId);
        r.setFlowCount(flowCount);
        r.setAvgSpeed(avgSpeed);
        r.setRecordDate(date);
        return r;
    }

    @Test
    @DisplayName("findAllSections 应返回所有路段")
    void findAllSections() {
        when(roadSectionRepository.findAll()).thenReturn(List.of(
            createSection(1L, "路段A", 5.0, "畅通"),
            createSection(2L, "路段B", 3.0, "拥堵")
        ));
        assertEquals(2, trafficService.findAllSections().size());
    }

    @Test
    @DisplayName("findAllFlowRecords 应返回所有流量记录")
    void findAllFlowRecords() {
        when(flowRecordRepository.findAll()).thenReturn(List.of(
            createRecord(1L, 1L, 100, 60.0, LocalDate.now())
        ));
        assertEquals(1, trafficService.findAllFlowRecords().size());
    }

    @Test
    @DisplayName("findFlowRecordsBySectionId 应按路段过滤")
    void findBySectionId() {
        when(flowRecordRepository.findBySectionId(1L)).thenReturn(List.of(
            createRecord(2L, 1L, 200, 40.0, LocalDate.now())
        ));
        assertEquals(1, trafficService.findFlowRecordsBySectionId(1L).size());
    }

    @Test
    @DisplayName("getOverview 有数据返回统计")
    void getOverviewWithData() {
        TrafficRoadSection section = createSection(1L, "主干道", 5.0, "畅通");
        List<TrafficFlowRecord> records = Arrays.asList(
            createRecord(1L, 1L, 500, 30.0, LocalDate.now()),
            createRecord(2L, 1L, 800, 20.0, LocalDate.now())
        );

        when(roadSectionRepository.findAll()).thenReturn(List.of(section));
        when(flowRecordRepository.findAll()).thenReturn(records);

        Map<String, Object> overview = trafficService.getOverview();
        assertNotNull(overview);
    }

    @Test
    @DisplayName("findFlowByDate 应按日期过滤")
    void findFlowByDate() {
        LocalDate today = LocalDate.now();
        when(flowRecordRepository.findByRecordDate(today)).thenReturn(List.of(
            createRecord(1L, 1L, 300, 50.0, today)
        ));
        assertEquals(1, trafficService.findFlowByDate(today).size());
    }
}
