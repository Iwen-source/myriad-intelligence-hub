package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.model.dto.analysis.EnergyPredictionDTO;
import com.aiempowerment.platform.model.dto.analysis.OptimizationTipDTO;
import com.aiempowerment.platform.model.entity.EnergyDevice;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.EnergyService;
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

import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.MOCK)
@AutoConfigureMockMvc(addFilters = false)
@ActiveProfiles("test")
@DisplayName("EnergyController 集成测试")
class EnergyControllerIntegrationTest {

    @Autowired
    private MockMvc mockMvc;

    @MockBean
    private EnergyService energyService;

    @MockBean
    private AIAnalysisService aiAnalysisService;

    private EnergyDevice createDevice(String deviceId, String name, String status) {
        EnergyDevice d = new EnergyDevice();
        d.setDeviceId(deviceId);
        d.setDeviceName(name);
        d.setStatus(status);
        d.setDeviceType("空调");
        d.setLocation("大厅");
        d.setPower("5kW");
        d.setStartDate(LocalDate.now());
        return d;
    }

    @Test
    @DisplayName("GET /energy/devices 返回设备列表")
    void listDevices_shouldReturnList() throws Exception {
        when(energyService.searchDevices(null, null, null)).thenReturn(List.of(
                createDevice("DEV001", "空调A", "运行中"),
                createDevice("DEV002", "照明B", "运行中")
        ));

        mockMvc.perform(get("/energy/devices"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /energy/devices/DEV001 返回单个设备")
    void getDevice_shouldReturnSingle() throws Exception {
        when(energyService.findDeviceById("DEV001")).thenReturn(createDevice("DEV001", "空调A", "运行中"));

        mockMvc.perform(get("/energy/devices/DEV001"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.deviceName").value("空调A"));
    }

    @Test
    @DisplayName("GET /energy/analysis/predict 返回能耗预测")
    void predictEnergy_shouldReturnPrediction() throws Exception {
        EnergyPredictionDTO p1 = new EnergyPredictionDTO(LocalDate.of(2026, 5, 21), "Thursday", 120.5, 100.0, 140.0, false);
        EnergyPredictionDTO p2 = new EnergyPredictionDTO(LocalDate.of(2026, 5, 22), "Friday", 130.2, 110.0, 150.0, false);
        when(aiAnalysisService.predictEnergyConsumption(7)).thenReturn(List.of(p1, p2));

        mockMvc.perform(get("/energy/analysis/prediction?days=7"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /energy/analysis/tips 返回优化建议")
    void getTips_shouldReturnList() throws Exception {
        OptimizationTipDTO t1 = new OptimizationTipDTO("1", "节能建议1", "减少待机能耗", "高", "能耗", false);
        OptimizationTipDTO t2 = new OptimizationTipDTO("2", "节能建议2", "优化运行时段", "中", "调度", false);
        when(aiAnalysisService.getEnergyOptimizationTips()).thenReturn(List.of(t1, t2));

        mockMvc.perform(get("/energy/analysis/optimization"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.length()").value(2));
    }

    @Test
    @DisplayName("GET /energy/analysis/anomalies 返回异常检测")
    void detectAnomalies_shouldReturnList() throws Exception {
        when(aiAnalysisService.detectDeviceAnomalies()).thenReturn(List.of());

        mockMvc.perform(get("/energy/analysis/anomalies"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data").isArray());
    }
}

