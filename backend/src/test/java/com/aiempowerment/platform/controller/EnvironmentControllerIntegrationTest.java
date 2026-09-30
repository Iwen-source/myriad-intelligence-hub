package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.model.dto.analysis.AirQualityPredictionDTO;
import com.aiempowerment.platform.model.dto.analysis.PollutionAlertDTO;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.EnvironmentService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

import java.time.LocalDate;
import java.util.List;
import java.util.Map;

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
@DisplayName("EnvironmentController 集成测试")
class EnvironmentControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private EnvironmentService environmentService;

    @MockBean
    private AIAnalysisService aiAnalysisService;

    private EnvironmentMonitorPoint createPoint(Long id, String name) {
        EnvironmentMonitorPoint p = new EnvironmentMonitorPoint();
        p.setId(id);
        p.setPointName(name);
        p.setLocation("沈阳");
        p.setStatus("正常");
        return p;
    }

    @Test
    @DisplayName("GET /environment/points 返回监测点列表")
    void getPoints_shouldReturnList() throws Exception {
        when(environmentService.findAllPoints()).thenReturn(List.of(
                createPoint(1L, "监测站A"),
                createPoint(2L, "监测站B")
        ));

        mockMvc.perform(get("/environment/points"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /environment/points/1 返回单个监测点")
    void getPoint_shouldReturnSingle() throws Exception {
        when(environmentService.findPointById(1L)).thenReturn(createPoint(1L, "监测站A"));

        mockMvc.perform(get("/environment/points/1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.pointName").value("监测站A"));
    }

    @Test
    @DisplayName("GET /environment/analysis/health-index 返回健康指数")
    void getHealthIndex_shouldReturnData() throws Exception {
        when(aiAnalysisService.getEnvironmentHealthIndex()).thenReturn(Map.of(
                "aqi", 80, "level", "良", "healthIndex", 72.5));

        mockMvc.perform(get("/environment/analysis/health-index"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.aqi").value(80));
    }

    @Test
    @DisplayName("GET /environment/analysis/prediction 返回AQI预测")
    void predictAir_shouldReturnPrediction() throws Exception {
        AirQualityPredictionDTO p1 = new AirQualityPredictionDTO(LocalDate.of(2026, 5, 21), "Thursday", 85, "良", "#E8C02C", false);
        AirQualityPredictionDTO p2 = new AirQualityPredictionDTO(LocalDate.of(2026, 5, 22), "Friday", 90, "良", "#E8C02C", false);
        when(aiAnalysisService.predictAirQuality(5)).thenReturn(List.of(p1, p2));

        mockMvc.perform(get("/environment/analysis/prediction?days=5"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /environment/analysis/alerts 返回污染预警")
    void getAlerts_shouldReturnList() throws Exception {
        PollutionAlertDTO alert = new PollutionAlertDTO("橙色预警", "PM2.5浓度超标", "工业区", "减少户外活动", "2026-05-31 10:00", false);
        when(aiAnalysisService.getPollutionAlerts()).thenReturn(List.of(alert));

        mockMvc.perform(get("/environment/analysis/alerts"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data[0].level").value("橙色预警"));
    }

    @Test
    @DisplayName("GET /environment/analysis/seasonal-trend 返回季节趋势")
    void getSeasonalTrend_shouldReturnData() throws Exception {
        when(aiAnalysisService.getSeasonalTrendAnalysis()).thenReturn(Map.of(
                "spring", Map.of("avgAqi", 75),
                "summer", Map.of("avgAqi", 60)
        ));

        mockMvc.perform(get("/environment/analysis/seasonal-trend"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));
    }
}

