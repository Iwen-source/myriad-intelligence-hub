package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.config.AiModelClient;
import com.aiempowerment.platform.model.entity.AirQualityRecord;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import com.aiempowerment.platform.repository.AirQualityRecordRepository;
import com.aiempowerment.platform.repository.EnvironmentMonitorPointRepository;
import com.aiempowerment.platform.service.PythonMlClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import java.time.LocalDateTime;
import java.util.*;
import com.aiempowerment.platform.model.dto.analysis.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class EnvironmentAnalysisServiceTest {

    @Mock private AirQualityRecordRepository airQualityRepository;
    @Mock private EnvironmentMonitorPointRepository envPointRepository;
    @Mock private AiModelClient aiModelClient;
    @Mock private PythonMlClient pythonMlClient;

    private EnvironmentAnalysisService service;

    @BeforeEach
    void setUp() {
        service = new EnvironmentAnalysisService(airQualityRepository, envPointRepository, aiModelClient, pythonMlClient);
    }

    private AirQualityRecord createRecord(Long id, Long pointId, Integer aqi, Double pm25, Double pm10,
            Double o3, Double no2, Double temperature, Double humidity, LocalDateTime time) {
        AirQualityRecord r = new AirQualityRecord();
        r.setId(id);
        r.setPointId(pointId);
        r.setAqi(aqi);
        r.setPm25(pm25);
        r.setPm10(pm10);
        r.setO3(o3);
        r.setNo2(no2);
        r.setTemperature(temperature);
        r.setHumidity(humidity);
        r.setRecordTime(time);
        return r;
    }

    private EnvironmentMonitorPoint createPoint(Long id, String name) {
        EnvironmentMonitorPoint p = new EnvironmentMonitorPoint();
        p.setId(id);
        p.setPointName(name);
        return p;
    }

    // ====== predictAirQuality ======

    @Test
    @DisplayName("predictAirQuality 应返回指定天数的预测")
    void predictAirQuality_shouldReturnDaysCount() {
        List<AirQualityRecord> records = new ArrayList<>();
        for (int i = 0; i < 20; i++) {
            records.add(createRecord((long)i, 1L, 50 + i, 30.0 + i, 60.0 + i,
                0.05, 0.02, 22.0, 55.0, LocalDateTime.now().minusHours(i)));
        }
        when(airQualityRepository.findAll()).thenReturn(records);

        List<AirQualityPredictionDTO> result = service.predictAirQuality(7);

        assertNotNull(result);
        assertEquals(7, result.size(), "应返回7天预测");
        assertTrue(result.get(0).getDate() != null, "应包含日期");
        assertTrue(result.get(0).getPredictedAqi() > 0, "应包含预测值");
    }

    @Test
    @DisplayName("predictAirQuality 空数据时返回基本预测")
    void predictAirQuality_emptyData() {
        when(airQualityRepository.findAll()).thenReturn(List.of());

        List<AirQualityPredictionDTO> result = service.predictAirQuality(3);

        assertNotNull(result);
        assertEquals(3, result.size());
    }

    // ====== getPollutionAlerts ======

    @Test
    @DisplayName("getPollutionAlerts 应包含超标报警")
    void getPollutionAlerts_shouldReturnAlerts() {
        List<AirQualityRecord> records = List.of(
            createRecord(1L, 1L, 180, 80.0, 150.0, 0.08, 0.03, 25.0, 50.0, LocalDateTime.now()),
            createRecord(2L, 1L, 250, 120.0, 200.0, 0.1, 0.04, 24.0, 45.0, LocalDateTime.now()),
            createRecord(3L, 2L, 60, 25.0, 50.0, 0.04, 0.01, 22.0, 60.0, LocalDateTime.now())
        );
        when(airQualityRepository.findAll()).thenReturn(records);

        List<PollutionAlertDTO> result = service.getPollutionAlerts();

        assertFalse(result.isEmpty());
    }

    @Test
    @DisplayName("getPollutionAlerts 无污染时返回正常信息")
    void getPollutionAlerts_cleanAir() {
        when(airQualityRepository.findAll()).thenReturn(List.of(
            createRecord(1L, 1L, 30, 10.0, 20.0, 0.02, 0.005, 22.0, 55.0, LocalDateTime.now())
        ));

        List<PollutionAlertDTO> result = service.getPollutionAlerts();

        assertNotNull(result);
    }

    // ====== getEnvironmentHealthIndex ======

    @Test
    @DisplayName("getEnvironmentHealthIndex 应返回健康指数")
    void getEnvironmentHealthIndex_shouldReturnHealthIndex() {
        when(airQualityRepository.findAll()).thenReturn(List.of(
            createRecord(1L, 1L, 80, 35.0, 70.0, 0.06, 0.025, 25.0, 50.0, LocalDateTime.now())
        ));

        Map<String, Object> result = service.getEnvironmentHealthIndex();

        assertNotNull(result);
        assertTrue(result.containsKey("aqi") || result.containsKey("healthIndex"));
        assertTrue(result.containsKey("level") || result.containsKey("aqiLevel"));
    }

    // ====== getSeasonalTrendAnalysis ======

    @Test
    @DisplayName("getSeasonalTrendAnalysis 应返回季节分析")
    void getSeasonalTrendAnalysis_shouldReturnSeasonal() {
        List<AirQualityRecord> records = new ArrayList<>();
        for (int i = 0; i < 120; i++) {
            records.add(createRecord((long)i, 1L, 50 + i % 40, 25.0 + i % 30,
                50.0 + i % 50, 0.05, 0.02, 22.0, 55.0,
                LocalDateTime.of(2026, (i % 12) + 1, 15, 10, 0)));
        }
        when(airQualityRepository.findAll()).thenReturn(records);

        Map<String, Object> result = service.getSeasonalTrendAnalysis();

        assertNotNull(result);
    }

    // ====== getHealthImpactAssessment ======

    @Test
    @DisplayName("getHealthImpactAssessment 应返回健康影响评估")
    void getHealthImpactAssessment_shouldReturnAssessment() {
        when(airQualityRepository.findAll()).thenReturn(List.of(
            createRecord(1L, 1L, 120, 55.0, 100.0, 0.07, 0.03, 25.0, 45.0, LocalDateTime.now()),
            createRecord(2L, 1L, 150, 70.0, 130.0, 0.09, 0.035, 24.0, 40.0, LocalDateTime.now())
        ));

        Map<String, Object> result = service.getHealthImpactAssessment();

        assertNotNull(result);
    }

    // ====== getCrossPointCorrelation ======

    @Test
    @DisplayName("getCrossPointCorrelation 多监测点返回关联分析")
    void getCrossPointCorrelation_multiplePoints() {
        List<AirQualityRecord> records = new ArrayList<>();
        for (long p = 1; p <= 4; p++) {
            for (int i = 0; i < 10; i++) {
                records.add(createRecord(p * 100 + i, p, 50 + i, 25.0, 50.0,
                    0.05, 0.02, 22.0, 55.0, LocalDateTime.now().minusHours(i)));
            }
        }
        when(airQualityRepository.findAll()).thenReturn(records);

        List<Map<String, Object>> result = service.getCrossPointCorrelation();

        assertNotNull(result);
    }

    // ====== getPollutantBreakdown ======

    @Test
    @DisplayName("getPollutantBreakdown 应返回污染物分析")
    void getPollutantBreakdown_shouldReturnBreakdown() {
        // Service uses findByPointId internally
        when(airQualityRepository.findByPointId(1L)).thenReturn(List.of(
            createRecord(1L, 1L, 80, 35.0, 70.0, 0.06, 0.025, 23.0, 50.0, LocalDateTime.now())
        ));

        Map<String, Object> result = service.getPollutantBreakdown(1L);

        assertNotNull(result);
        assertTrue(result.containsKey("pollutants") || result.containsKey("aqi"), "应包含污染物列表或AQI");
    }

    @Test
    @DisplayName("getPollutantBreakdown 无数据时返回错误信息")
    void getPollutantBreakdown_noData() {
        when(airQualityRepository.findByPointId(1L)).thenReturn(List.of());

        Map<String, Object> result = service.getPollutantBreakdown(1L);

        assertNotNull(result);
        assertTrue(result.containsKey("error"), "无数据时应包含错误信息");
    }

    // ====== getSmartRecommendations ======

    @Test
    @DisplayName("getSmartRecommendations 应返回建议")
    void getSmartRecommendations_shouldReturnRecommendations() {
        // Service uses findTop10ByOrderByRecordTimeDesc internally
        when(airQualityRepository.findTop10ByOrderByRecordTimeDesc()).thenReturn(List.of(
            createRecord(1L, 1L, 120, 55.0, 100.0, 0.07, 0.03, 25.0, 35.0, LocalDateTime.now()),
            createRecord(2L, 1L, 150, 70.0, 130.0, 0.09, 0.035, 24.0, 30.0, LocalDateTime.now())
        ));
        when(envPointRepository.findAll()).thenReturn(List.of(createPoint(1L, "监测站A")));

        List<Map<String, Object>> result = service.getSmartRecommendations();

        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    // ====== getEnvironmentAiReport ======

    @Test
    @DisplayName("getEnvironmentAiReport 应生成报告")
    void getEnvironmentAiReport_shouldGenerate() {
        when(airQualityRepository.findAll()).thenReturn(List.of(
            createRecord(1L, 1L, 80, 35.0, 70.0, 0.06, 0.025, 23.0, 50.0, LocalDateTime.now())
        ));

        Map<String, Object> result = service.getEnvironmentAiReport();

        assertNotNull(result);
    }

    // ====== getEnvironmentalAnomalyDetection ======

    @Test
    @DisplayName("getEnvironmentalAnomalyDetection 应检测异常")
    void getEnvironmentalAnomalyDetection_shouldDetect() {
        when(airQualityRepository.findAll()).thenReturn(List.of(
            createRecord(1L, 1L, 250, 120.0, 200.0, 0.15, 0.05, 25.0, 50.0, LocalDateTime.now()),
            createRecord(2L, 1L, 60, 25.0, 50.0, 0.04, 0.01, 22.0, 55.0, LocalDateTime.now())
        ));

        List<Map<String, Object>> result = service.getEnvironmentalAnomalyDetection();

        assertFalse(result.isEmpty());
    }
}

