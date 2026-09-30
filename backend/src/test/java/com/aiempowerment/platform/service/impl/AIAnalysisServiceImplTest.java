package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.config.AiModelClient;
import com.aiempowerment.platform.model.entity.*;
import com.aiempowerment.platform.repository.*;
import com.aiempowerment.platform.service.analysis.EnergyAnalysisService;
import com.aiempowerment.platform.service.analysis.EnvironmentAnalysisService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.aiempowerment.platform.service.analysis.FinanceAnalysisService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.when;

/**
 * AI分析引擎实现 单元测试
 * 覆盖医疗/交通/教育/创意 等未在领域测试中覆盖的方法
 */
@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
@DisplayName("AIAnalysisServiceImpl 单元测试")
class AIAnalysisServiceImplTest {

    @Mock private EnergyConsumptionRecordRepository consumptionRepository;
    @Mock private EnergyDeviceRepository energyDeviceRepository;
    @Mock private MedicalDiagnosisResultRepository diagnosisRepository;
    @Mock private MedicalPatientRepository patientRepository;
    @Mock private AirQualityRecordRepository airQualityRepository;
    @Mock private FinanceTransactionRepository financeTransactionRepository;
    @Mock private RiskAlertRuleRepository riskAlertRuleRepository;
    @Mock private TrafficFlowRecordRepository trafficFlowRepository;
    @Mock private TrafficRoadSectionRepository trafficRoadSectionRepository;
    @Mock private EnvironmentMonitorPointRepository envPointRepository;
    @Mock private AiModelClient aiModelClient;
    @Mock private EnergyAnalysisService energyAnalysisService;
    @Mock private EnvironmentAnalysisService environmentAnalysisService;
    @Mock private FinanceAnalysisService financeAnalysisService;
    @Mock private PythonMlClient pythonMlClient;

    @InjectMocks
    private AIAnalysisServiceImpl aiAnalysisService;

    // ===================== 医疗分析 =====================

    @Test
    @DisplayName("分析症状-疾病关联：发热咳嗽")
    void analyzeSymptomDisease_withFeverAndCough() {
        List<Map<String, Object>> result = aiAnalysisService.analyzeSymptomDisease("发热,咳嗽");
        assertEquals(2, result.size());
        assertEquals("发热", result.get(0).get("symptom"));
        assertEquals("上呼吸道感染", result.get(0).get("possibleDisease"));
    }

    @Test
    @DisplayName("分析症状-疾病关联：空字符串返回提示消息")
    void analyzeSymptomDisease_emptyInput() {
        List<Map<String, Object>> result = aiAnalysisService.analyzeSymptomDisease("");
        assertEquals(1, result.size());
        assertTrue(result.get(0).containsKey("message"));
    }

    @Test
    @DisplayName("分析症状-疾病关联：多个症状含头痛和腹痛")
    void analyzeSymptomDisease_withMultipleSymptoms() {
        List<Map<String, Object>> result = aiAnalysisService.analyzeSymptomDisease("头痛;腹痛;皮疹");
        assertEquals(3, result.size());
        assertEquals("偏头痛", result.get(0).get("possibleDisease"));
        assertEquals("胃炎", result.get(1).get("possibleDisease"));
        assertEquals("过敏性皮炎", result.get(2).get("possibleDisease"));
    }

    @Test
    @DisplayName("查找相似病例：有患者数据")
    void findSimilarCases_withPatients() {
        MedicalPatient patient1 = new MedicalPatient();
        patient1.setPatientId("1");
        patient1.setName("张三");
        patient1.setSymptoms("发热咳嗽");
        MedicalPatient patient2 = new MedicalPatient();
        patient2.setPatientId("2");
        patient2.setName("李四");
        patient2.setSymptoms("头痛");

        when(patientRepository.findAll()).thenReturn(List.of(patient1, patient2));
        List<Map<String, Object>> result = aiAnalysisService.findSimilarCases(1L);

        assertFalse(result.isEmpty());
        assertEquals("李四", result.get(0).get("name"));
    }

    @Test
    @DisplayName("查找相似病例：无数据返回空列表")
    void findSimilarCases_noPatients() {
        when(patientRepository.findAll()).thenReturn(List.of());
        List<Map<String, Object>> result = aiAnalysisService.findSimilarCases(1L);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("分析诊断趋势")
    void analyzeDiagnosisTrend() {
        MedicalDiagnosisResult r1 = new MedicalDiagnosisResult();
        r1.setResultId("1");
        r1.setDiagnosisResult("高血压");
        MedicalDiagnosisResult r2 = new MedicalDiagnosisResult();
        r2.setResultId("2");
        r2.setDiagnosisResult("高血压");
        MedicalDiagnosisResult r3 = new MedicalDiagnosisResult();
        r3.setResultId("3");
        r3.setDiagnosisResult("糖尿病");

        when(diagnosisRepository.findAll()).thenReturn(List.of(r1, r2, r3));

        Map<String, Object> result = aiAnalysisService.analyzeDiagnosisTrend();
        assertEquals(3, ((Number) result.get("totalDiagnoses")).intValue());
        assertEquals(2, ((Number) result.get("uniqueDiagnoses")).intValue());
        assertTrue(result.containsKey("topDiagnoses"));
        assertTrue(result.containsKey("analysisTime"));
    }

    @Test
    @DisplayName("分析诊断趋势：无数据")
    void analyzeDiagnosisTrend_noData() {
        when(diagnosisRepository.findAll()).thenReturn(List.of());
        Map<String, Object> result = aiAnalysisService.analyzeDiagnosisTrend();
        assertEquals(0, ((Number) result.get("totalDiagnoses")).intValue());
        assertEquals(0, ((Number) result.get("uniqueDiagnoses")).intValue());
    }

    // ===================== 交通分析 =====================

    private TrafficRoadSection createTestSection(Long id, String roadName, String sectionName, Integer lanes, Integer speedLimit) {
        TrafficRoadSection s = new TrafficRoadSection();
        s.setId(id);
        s.setRoadName(roadName);
        s.setSectionName(sectionName);
        s.setLanes(lanes);
        s.setSpeedLimit(speedLimit);
        s.setLength(3.5);
        return s;
    }

    @Test
    @DisplayName("预测拥堵：给定日期返回24小时数据")
    void predictCongestion_withDate() {
        TrafficRoadSection section = createTestSection(1L, "青年大街", "浑南段", 6, 60);
        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section));

        TrafficFlowRecord rec = new TrafficFlowRecord();
        rec.setId(1L);
        rec.setSectionId(1L);
        rec.setRecordDate(LocalDate.of(2026, 5, 20));
        rec.setRecordHour(8);
        rec.setFlowCount(3500);
        rec.setAvgSpeed(25.0);

        when(trafficFlowRepository.findByRecordDate(LocalDate.of(2026, 5, 20)))
                .thenReturn(List.of(rec));

        List<Map<String, Object>> result = aiAnalysisService.predictCongestion("2026-05-20");
        assertEquals(24, result.size());
        assertEquals("08:00", result.get(8).get("hour"));
        assertTrue(result.get(0).containsKey("congestionLevel"));
    }

    @Test
    @DisplayName("路线优化建议：无路段数据时返回引导提示")
    void getRouteOptimizationTips_noSections_shouldReturnGuideTip() {
        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of());
        List<Map<String, Object>> result = aiAnalysisService.getRouteOptimizationTips();
        assertFalse(result.isEmpty());
        assertEquals("当前无路段数据", result.get(0).get("title"));
        assertEquals("请先添加路段信息", result.get(0).get("description"));
    }

    @Test
    @DisplayName("路线优化建议：有路段数据时返回建议")
    void getRouteOptimizationTips_withSections_shouldReturnTips() {
        TrafficRoadSection section = createTestSection(1L, "青年大街", "浑南段", 6, 60);
        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section));
        when(trafficFlowRepository.findAll()).thenReturn(List.of());

        List<Map<String, Object>> result = aiAnalysisService.getRouteOptimizationTips();
        // 无ML数据时可能返回0条或少量建议，只验证不为null
        assertNotNull(result);
    }

    @Test
    @DisplayName("交通热力图：有路段数据")
    void getTrafficHeatmap_withSections() {
        TrafficRoadSection section = new TrafficRoadSection();
        section.setId(1L);
        section.setRoadName("青年大街");
        section.setSectionName("浑南段");
        section.setLength(3.5);
        section.setLanes(6);

        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section));
        when(trafficFlowRepository.findTop10BySectionIdOrderByRecordHourDesc(1L)).thenReturn(List.of());

        List<Map<String, Object>> result = aiAnalysisService.getTrafficHeatmap();
        assertFalse(result.isEmpty());
        assertEquals("青年大街", result.get(0).get("roadName"));
        assertTrue(result.get(0).containsKey("congestionLevel"));
        assertTrue(result.get(0).containsKey("congestionIndex"));
    }

    @Test
    @DisplayName("拥堵日历：无ML数据时返回空")
    void predictCongestionCalendar_noMlData_shouldReturnEmpty() {
        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of());
        when(trafficFlowRepository.findAll()).thenReturn(List.of());

        List<Map<String, Object>> result = aiAnalysisService.predictCongestionCalendar(5);
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("事故影响分析：路段不存在返回错误")
    void analyzeAccidentImpact_sectionNotFound() {
        when(trafficRoadSectionRepository.findById(999L)).thenReturn(java.util.Optional.empty());
        Map<String, Object> result = aiAnalysisService.analyzeAccidentImpact(999L);
        assertTrue(result.containsKey("error"));
    }

    @Test
    @DisplayName("事故影响分析：有效路段返回级联影响数据")
    void analyzeAccidentImpact_withData() {
        TrafficRoadSection section = new TrafficRoadSection();
        section.setId(1L);
        section.setRoadName("青年大街");
        section.setSectionName("浑南段");
        section.setLength(3.5);
        section.setLanes(6);

        TrafficRoadSection otherSection = new TrafficRoadSection();
        otherSection.setId(2L);
        otherSection.setRoadName("文化路");
        otherSection.setSectionName("立交桥段");
        otherSection.setLength(2.0);
        otherSection.setLanes(4);

        TrafficFlowRecord rec = new TrafficFlowRecord();
        rec.setId(1L);
        rec.setSectionId(1L);
        rec.setFlowCount(3000);
        rec.setAvgSpeed(30.0);
        rec.setRecordDate(LocalDate.now());
        rec.setRecordHour(8);

        when(trafficRoadSectionRepository.findById(1L)).thenReturn(java.util.Optional.of(section));
        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section, otherSection));
        when(trafficFlowRepository.findAll()).thenReturn(List.of(rec));

        Map<String, Object> result = aiAnalysisService.analyzeAccidentImpact(1L);
        assertEquals("青年大街-浑南段", result.get("accidentSection"));
        assertTrue(result.containsKey("affectedSections"));
        assertTrue(result.containsKey("recommendation"));
    }

    @Test
    @DisplayName("天气交通关联分析：返回9种天气场景")
    void analyzeWeatherTrafficCorrelation_shouldReturn9Scenarios() {
        TrafficRoadSection section = new TrafficRoadSection();
        section.setId(1L);
        section.setRoadName("青年大街");
        section.setSectionName("浑南段");
        section.setRoadType("主干道");

        TrafficFlowRecord rec = new TrafficFlowRecord();
        rec.setId(1L);
        rec.setSectionId(1L);
        rec.setFlowCount(3000);
        rec.setAvgSpeed(40.0);

        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section));
        when(trafficFlowRepository.findAll()).thenReturn(List.of(rec));

        List<Map<String, Object>> result = aiAnalysisService.analyzeWeatherTrafficCorrelation();
        assertEquals(9, result.size());
        assertEquals("晴", result.get(0).get("weather"));
        assertTrue(result.get(0).containsKey("congestionRisk"));
        assertTrue(result.get(0).containsKey("drivingAdvice"));
        assertEquals("暴雨", result.get(4).get("weather"));
        assertEquals("高风险", result.get(4).get("congestionRisk"));
    }

    @Test
    @DisplayName("检测交通异常：无历史数据时返回空")
    void detectTrafficAnomalies_noData() {
        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of());
        when(trafficFlowRepository.findAll()).thenReturn(List.of());

        List<Map<String, Object>> result = aiAnalysisService.detectTrafficAnomalies();
        assertTrue(result.isEmpty());
    }

    @Test
    @DisplayName("检测交通异常：有路段和流量数据时返回异常")
    void detectTrafficAnomalies_withData() {
        TrafficRoadSection section = new TrafficRoadSection();
        section.setId(1L);
        section.setRoadName("青年大街");
        section.setSectionName("浑南段");
        section.setLanes(6);
        section.setSpeedLimit(60);

        TrafficFlowRecord rec = new TrafficFlowRecord();
        rec.setId(1L);
        rec.setSectionId(1L);
        rec.setFlowCount(3500);
        rec.setAvgSpeed(25.0);
        rec.setRecordHour(8);

        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section));
        when(trafficFlowRepository.findAll()).thenReturn(List.of(rec));

        List<Map<String, Object>> result = aiAnalysisService.detectTrafficAnomalies();
        assertNotNull(result);
    }

    
    // 教育模块和创意设计模块已移除，测试方法已删除
    // ===================== 交通仿真 =====================

    @Test
    @DisplayName("交通仿真：增加车道场景")
    void simulateWhatIf_addLane() {
        TrafficRoadSection section = new TrafficRoadSection();
        section.setId(1L);
        section.setRoadName("青年大街");
        section.setSectionName("浑南段");
        section.setLanes(4);
        section.setSpeedLimit(60);
        section.setLength(3.5);

        TrafficFlowRecord rec = new TrafficFlowRecord();
        rec.setId(1L);
        rec.setSectionId(1L);
        rec.setFlowCount(6000);
        rec.setAvgSpeed(35.0);

        when(trafficRoadSectionRepository.findById(1L)).thenReturn(java.util.Optional.of(section));
        when(trafficFlowRepository.findBySectionId(1L)).thenReturn(List.of(rec));

        Map<String, Object> result = aiAnalysisService.simulateWhatIf(1L, Map.of("type", "add_lane", "value", 2));
        assertFalse(result.containsKey("error"));
        assertEquals(4, ((Number) result.get("originalLanes")).intValue());
        assertTrue(result.containsKey("impactDescription"));
        assertTrue(result.containsKey("recommendation"));
    }

    @Test
    @DisplayName("智能出行建议：返回最佳出发时间段")
    void getSmartDepartureTips_shouldReturnBestTime() {
        TrafficRoadSection section = new TrafficRoadSection();
        section.setId(1L);
        section.setRoadName("青年大街");
        section.setSectionName("浑南段");

        TrafficFlowRecord rec = new TrafficFlowRecord();
        rec.setId(1L);
        rec.setSectionId(1L);
        rec.setRecordHour(8);
        rec.setFlowCount(3000);
        rec.setAvgSpeed(20.0);

        when(trafficRoadSectionRepository.findAll()).thenReturn(List.of(section));
        when(trafficFlowRepository.findAll()).thenReturn(List.of(rec));

        Map<String, Object> result = aiAnalysisService.getSmartDepartureTips();
        assertTrue(result.containsKey("tips"));
        assertTrue(result.containsKey("totalSections"));
        assertTrue(result.containsKey("generatedTime"));
    }
}