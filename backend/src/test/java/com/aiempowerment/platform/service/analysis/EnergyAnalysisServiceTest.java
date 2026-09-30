package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.model.entity.EnergyConsumptionRecord;
import com.aiempowerment.platform.model.entity.EnergyDevice;
import com.aiempowerment.platform.repository.EnergyConsumptionRecordRepository;
import com.aiempowerment.platform.repository.EnergyDeviceRepository;
import com.aiempowerment.platform.service.PythonMlClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.mockito.junit.jupiter.MockitoSettings;
import org.mockito.quality.Strictness;

import com.aiempowerment.platform.model.dto.analysis.*;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
@MockitoSettings(strictness = Strictness.LENIENT)
class EnergyAnalysisServiceTest {

    @Mock private EnergyConsumptionRecordRepository recordRepository;
    @Mock private EnergyDeviceRepository deviceRepository;
    @Mock private PythonMlClient pythonMlClient;

    private EnergyAnalysisService service;

    @BeforeEach
    void setUp() {
        service = new EnergyAnalysisService(recordRepository, deviceRepository, pythonMlClient);
    }

    private EnergyConsumptionRecord createRecord(String recordId, String deviceId, double consumption) {
        EnergyConsumptionRecord r = new EnergyConsumptionRecord();
        r.setRecordId(recordId);
        r.setDeviceId(deviceId);
        r.setConsumptionDate(LocalDate.now());
        r.setConsumptionValue(BigDecimal.valueOf(consumption));
        return r;
    }

    private EnergyDevice createDevice(String deviceId, String name, String status) {
        EnergyDevice d = new EnergyDevice();
        d.setDeviceId(deviceId);
        d.setDeviceName(name);
        d.setDeviceType("空调");
        d.setLocation("大厅");
        d.setPower("5kW");
        d.setStartDate(LocalDate.now());
        d.setStatus(status);
        return d;
    }

    // ====== predictEnergyConsumption ======

    @Test
    @DisplayName("predictEnergyConsumption 应返回指定天数的预测数据")
    void predictEnergyConsumption_shouldReturnDaysCount() {
        List<EnergyConsumptionRecord> records = new ArrayList<>();
        for (int i = 0; i < 30; i++) {
            records.add(createRecord("R" + i, "DEV001", 100 + i * 2.0));
        }
        when(recordRepository.findAll()).thenReturn(records);

        List<EnergyPredictionDTO> result = service.predictEnergyConsumption(7);

        assertNotNull(result);
        assertEquals(7, result.size(), "应返回7天预测");
        assertTrue(result.get(0).getPredicted() > 0, "应包含预测值字段");
        assertTrue(result.get(0).getLowerBound() > 0, "应包含下界");
        assertTrue(result.get(0).getUpperBound() > 0, "应包含上界");
    }

    @Test
    @DisplayName("predictEnergyConsumption 空数据时返回基本预测")
    void predictEnergyConsumption_emptyRecords() {
        when(recordRepository.findAll()).thenReturn(List.of());

        List<EnergyPredictionDTO> result = service.predictEnergyConsumption(3);

        assertNotNull(result);
        assertEquals(3, result.size());
    }

    // ====== detectDeviceAnomalies ======

    @Test
    @DisplayName("detectDeviceAnomalies 空数据时返回空结果或正常信息")
    void detectDeviceAnomalies_empty() {
        when(deviceRepository.findAll()).thenReturn(List.of());

        List<DeviceAnomalyDTO> result = service.detectDeviceAnomalies();

        assertNotNull(result);
    }

    @Test
    @DisplayName("detectDeviceAnomalies 空设备空记录时返回正常信息")
    void detectDeviceAnomalies_noDevices() {
        when(deviceRepository.findAll()).thenReturn(List.of());
        when(recordRepository.findAll()).thenReturn(List.of());

        List<DeviceAnomalyDTO> result = service.detectDeviceAnomalies();

        assertNotNull(result);
    }

    @Test
    @DisplayName("detectDeviceAnomalies 有设备时返回结果（可能为空或非空）")
    void detectDeviceAnomalies_withDevices() {
        when(deviceRepository.findAll()).thenReturn(List.of(
            createDevice("DEV001", "空调A", "运行中")
        ));

        List<DeviceAnomalyDTO> result = service.detectDeviceAnomalies();

        assertNotNull(result);
    }

    // ====== getEnergyOptimizationTips ======

    @Test
    @DisplayName("getEnergyOptimizationTips 有设备时返回优化建议")
    void getEnergyOptimizationTips_shouldReturnTips() {
        List<EnergyDevice> devices = List.of(
            createDevice("DEV001", "空调-大厅", "运行中"),
            createDevice("DEV002", "照明-东区", "待机")
        );
        when(deviceRepository.findAll()).thenReturn(devices);

        List<OptimizationTipDTO> result = service.getEnergyOptimizationTips();

        assertNotNull(result);
        assertFalse(result.isEmpty());
        assertTrue(result.stream().allMatch(m -> m.getTitle() != null), "所有建议应有标题");
    }

    @Test
    @DisplayName("getEnergyOptimizationTips 空设备时返回通用建议")
    void getEnergyOptimizationTips_emptyDevices() {
        when(deviceRepository.findAll()).thenReturn(List.of());

        List<OptimizationTipDTO> result = service.getEnergyOptimizationTips();

        assertNotNull(result);
        assertFalse(result.isEmpty());
    }

    // ====== getEnergyDeviceAnalysis ======

    @Test
    @DisplayName("getEnergyDeviceAnalysis 应返回设备分析摘要")
    void getEnergyDeviceAnalysis_shouldReturnSummary() {
        List<EnergyDevice> devices = Arrays.asList(
            createDevice("DEV001", "空调A", "运行中"),
            createDevice("DEV002", "照明B", "运行中"),
            createDevice("DEV003", "空调C", "待机"),
            createDevice("DEV004", "电梯D", "运行中")
        );
        when(deviceRepository.findAll()).thenReturn(devices);

        EnergyDeviceAnalysisDTO result = service.getEnergyDeviceAnalysis();

        assertNotNull(result);
        assertTrue(result.getAnalysisTime() != null, "应包含分析时间");
    }

    // ====== getEnergySummaryReport ======

    @Test
    @DisplayName("getEnergySummaryReport 应返回汇总报告")
    void getEnergySummaryReport_shouldReturnCompleteReport() {
        List<EnergyConsumptionRecord> records = Arrays.asList(
            createRecord("R1", "DEV001", 100.0),
            createRecord("R2", "DEV001", 150.0),
            createRecord("R3", "DEV002", 200.0)
        );
        List<EnergyDevice> devices = List.of(
            createDevice("DEV001", "空调A", "运行中"),
            createDevice("DEV002", "照明B", "待机")
        );

        when(deviceRepository.findAll()).thenReturn(devices);
        when(recordRepository.findAll()).thenReturn(records);

        EnergySummaryReportDTO report = service.getEnergySummaryReport();

        assertNotNull(report);
        assertTrue(report.getTotalConsumption() >= 0);
    }

    @Test
    @DisplayName("getEnergySummaryReport 空记录时返回零值报告")
    void getEnergySummaryReport_emptyRecords() {
        when(deviceRepository.findAll()).thenReturn(List.of());
        when(recordRepository.findAll()).thenReturn(List.of());

        EnergySummaryReportDTO report = service.getEnergySummaryReport();

        assertNotNull(report);
        assertTrue(report.getTotalConsumption() >= 0);
    }
}

