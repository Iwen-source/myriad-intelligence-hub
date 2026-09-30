package com.aiempowerment.platform.service.analysis;

import com.aiempowerment.platform.model.dto.analysis.*;
import com.aiempowerment.platform.model.entity.EnergyConsumptionRecord;
import com.aiempowerment.platform.model.entity.EnergyDevice;
import com.aiempowerment.platform.repository.EnergyConsumptionRecordRepository;
import com.aiempowerment.platform.repository.EnergyDeviceRepository;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

/**
 * 能源分析AI分析服务
 * <p>
 * Python ML Server 可用时调用真实模型，不可用时使用基于统计的确定性 fallback（无随机数）。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class EnergyAnalysisService {

    private final EnergyConsumptionRecordRepository consumptionRepository;
    private final EnergyDeviceRepository energyDeviceRepository;
    private final PythonMlClient pythonMlClient;

    // ======================== 能源分析核心方法 ========================

    public List<EnergyPredictionDTO> predictEnergyConsumption(int days) {
        List<Object[]> rawData = consumptionRepository.findConsumptionStatsByDay();
        Map<LocalDate, Double> dailyStats = new LinkedHashMap<>();
        for (Object[] row : rawData) {
            if (row[0] instanceof LocalDate date && row[1] instanceof Number val) {
                dailyStats.put(date, val.doubleValue());
            }
        }

        List<EnergyPredictionDTO> predictions = new ArrayList<>();
        double baseAvg = dailyStats.values().stream().mapToDouble(d -> d).average().orElse(100);

        LocalDate today = LocalDate.now();
        for (int i = 1; i <= days; i++) {
            LocalDate futureDate = today.plusDays(i);
            double dayOfWeek = futureDate.getDayOfWeek().getValue();
            double dayFactor = (dayOfWeek >= 6) ? 0.85 : 1.05;
            // 确定性统计基线：平滑增长趋势 + 工作日/周末因子 + 固定相位季节波动。
            // 注意：这是可复现的统计外推，并非 ML 推理，故 mlEnhanced 恒为 false。
            // 真实 ML 负荷预测走 EnergyController#loadForecast（LSTM: energy_load_lstm.pth）。
            double seasonal = 0.95 + Math.sin(i * 1.7) * 0.05;
            double trend = 1.02;
            double predicted = baseAvg * Math.pow(trend, i) * dayFactor * seasonal;

            predictions.add(new EnergyPredictionDTO(
                    futureDate,
                    futureDate.getDayOfWeek().toString(),
                    Math.round(predicted * 100.0) / 100.0,
                    Math.round(predicted * 0.85 * 100.0) / 100.0,
                    Math.round(predicted * 1.15 * 100.0) / 100.0,
                    false
            ));
        }

        return predictions;
    }

    public List<DeviceAnomalyDTO> detectDeviceAnomalies() {
        List<EnergyDevice> devices = energyDeviceRepository.findAll();
        List<DeviceAnomalyDTO> anomalies = new ArrayList<>();

        for (EnergyDevice device : devices) {
            List<EnergyConsumptionRecord> records = consumptionRepository
                    .findTop3ByDeviceIdOrderByConsumptionDateDesc(device.getDeviceId());

            if ("待维护".equals(device.getStatus()) || "已停机".equals(device.getStatus())) {
                anomalies.add(new DeviceAnomalyDTO(
                        device.getDeviceId(), device.getDeviceName(),
                        "STATUS_ANOMALY",
                        "已停机".equals(device.getStatus()) ? "critical" : "high",
                        "设备当前状态为: " + device.getStatus(),
                        "建议立即安排维护人员检查设备",
                        LocalDateTime.now().toString(), false
                ));
            }

            if (records.size() >= 3) {
                double avg = records.stream().mapToDouble(r -> r.getConsumptionValue().doubleValue()).average().orElse(0);
                double latest = records.get(0).getConsumptionValue().doubleValue();
                if (latest > avg * 1.5) {
                    anomalies.add(new DeviceAnomalyDTO(
                            device.getDeviceId(), device.getDeviceName(),
                            "CONSUMPTION_SPIKE",
                            latest > avg * 2.0 ? "critical" : "high",
                            String.format("能耗突增: 当前 %.1f kWh, 历史均值 %.1f kWh, 增幅 %.0f%%",
                                    latest, avg, (latest / avg - 1) * 100),
                            "检查设备运行参数和负载情况",
                            records.get(0).getConsumptionDate().toString(), false
                    ));
                }
            }
        }

        // 没有异常时返回明确信息（而非生成一条模拟异常）
        if (anomalies.isEmpty()) {
            anomalies.add(new DeviceAnomalyDTO(
                    null, null, "INFO", "normal",
                    "所有设备运行状态正常，未检测到异常",
                    "建议定期执行预防性维护",
                    LocalDateTime.now().toString(), false
            ));
        }

        return anomalies;
    }

    public List<OptimizationTipDTO> getEnergyOptimizationTips() {
        List<EnergyDevice> devices = energyDeviceRepository.findAll();
        List<OptimizationTipDTO> tips = new ArrayList<>();

        long runningDevices = devices.stream().filter(d -> "运行中".equals(d.getStatus())).count();
        long maintenanceDevices = devices.stream().filter(d -> "待维护".equals(d.getStatus()) || "已停机".equals(d.getStatus())).count();
        double totalConsumption = consumptionRepository.findAll().stream()
                .mapToDouble(r -> r.getConsumptionValue().doubleValue()).sum();

        if (maintenanceDevices > 0) {
            tips.add(newTip("tip-1", "设备维护提醒",
                    maintenanceDevices + " 台设备需要维护，及时维护可提升运行效率 5-10%",
                    "高", "效率", false));
        }

        if (totalConsumption > 10000) {
            tips.add(newTip("tip-2", "错峰用电策略",
                    "总能耗较高（" + String.format("%.0f", totalConsumption) + " kWh），将高能耗设备安排在低谷时段运行可降低用电成本约 15-25%",
                    "高", "经济", false));
        }

        tips.add(newTip("tip-3", "智能温控", "根据室内外温差 AI 自动调节空调温度，节能效果显著", "中", "节能", false));
        tips.add(newTip("tip-4", "无功补偿", "安装无功补偿装置，提高功率因数至 0.95 以上", "低", "经济", false));
        tips.add(newTip("tip-5", "能耗监测", "实时监控各设备能耗，及时发现异常能耗点", "高", "管理", false));

        if (runningDevices > 5) {
            tips.add(newTip("tip-6", "变频改造",
                    "对 " + runningDevices + " 台运行设备中的风机、水泵进行变频改造，节能率可达 20-40%",
                    "中", "技术", false));
        }

        return tips;
    }

    // ======================== 能源增强分析 ========================

    public EnergyDeviceAnalysisDTO getEnergyDeviceAnalysis() {
        List<EnergyDevice> devices = energyDeviceRepository.findAll();
        List<EnergyConsumptionRecord> allRecords = consumptionRepository.findAll();

        Map<String, Long> deviceTypeCount = devices.stream()
                .filter(d -> d.getDeviceType() != null)
                .collect(Collectors.groupingBy(EnergyDevice::getDeviceType, Collectors.counting()));

        Map<String, Double> deviceTypeConsumption = new HashMap<>();
        for (EnergyConsumptionRecord record : allRecords) {
            devices.stream()
                    .filter(d -> d.getDeviceId().equals(record.getDeviceId()))
                    .findFirst()
                    .ifPresent(device -> {
                        String type = device.getDeviceType();
                        deviceTypeConsumption.merge(type, record.getConsumptionValue().doubleValue(), Double::sum);
                    });
        }

        Map<String, Double> efficiencyScores = new LinkedHashMap<>();
        for (EnergyDevice device : devices) {
            List<EnergyConsumptionRecord> devRecords = consumptionRepository.findByDeviceId(device.getDeviceId());
            double devAvg = devRecords.stream().mapToDouble(r -> r.getConsumptionValue().doubleValue()).average().orElse(0);
            double ratedPower = switch (device.getDeviceType() != null ? device.getDeviceType() : "") {
                case "空调" -> 150.0;
                case "照明" -> 50.0;
                case "服务器" -> 300.0;
                case "电梯" -> 100.0;
                case "水泵" -> 80.0;
                default -> 120.0;
            };
            double efficiency = devAvg > 0 ? Math.min(100, Math.round((ratedPower / devAvg) * 100 * 10.0) / 10.0) : 60.0;
            efficiencyScores.put(device.getDeviceName() != null ? device.getDeviceName() : "未知设备", efficiency);
        }

        Map<String, Double> deviceRank = new LinkedHashMap<>();
        Map<String, Double> deviceConsumption = new HashMap<>();
        for (EnergyConsumptionRecord record : allRecords) {
            devices.stream()
                    .filter(d -> d.getDeviceId().equals(record.getDeviceId()))
                    .findFirst()
                    .ifPresent(device ->
                            deviceConsumption.merge(device.getDeviceName() != null ? device.getDeviceName() : "未知",
                                    record.getConsumptionValue().doubleValue(), Double::sum));
        }
        deviceConsumption.entrySet().stream()
                .sorted(Map.Entry.<String, Double>comparingByValue().reversed())
                .limit(5)
                .forEach(e -> deviceRank.put(e.getKey(), Math.round(e.getValue() * 100.0) / 100.0));

        double totalConsumption = allRecords.stream().mapToDouble(r -> r.getConsumptionValue().doubleValue()).sum();
        double totalCost = totalConsumption * 0.8;

        int season = LocalDate.now().getMonthValue() / 4 + 1;
        JsonNode carbonResult = pythonMlClient.carbonEstimate(totalConsumption, 0, 0, 0, 1, 0.8, season);
        double carbonEmission;
        boolean carbonMl = false;
        if (carbonResult != null && "success".equals(carbonResult.path("status").asText())) {
            carbonEmission = carbonResult.path("daily_estimate").asDouble();
            carbonMl = true;
        } else {
            carbonEmission = totalConsumption * 0.785;
        }

        EnergyDeviceAnalysisDTO dto = new EnergyDeviceAnalysisDTO();
        dto.setDeviceTypeCount(deviceTypeCount);
        dto.setDeviceTypeConsumption(deviceTypeConsumption);
        dto.setEfficiencyScores(efficiencyScores);
        dto.setTopConsumptionDevices(deviceRank);
        dto.setTotalConsumption(Math.round(totalConsumption * 100.0) / 100.0);
        dto.setTotalCost(Math.round(totalCost * 100.0) / 100.0);
        dto.setCarbonEmission(Math.round(carbonEmission * 100.0) / 100.0);
        dto.setAvgDailyConsumption(allRecords.isEmpty() ? 0 :
                Math.round((totalConsumption / allRecords.size()) * 100.0) / 100.0);
        dto.setCarbonMlEstimated(carbonMl);
        dto.setMlGenerated(carbonMl);
        return dto;
    }

    public EnergySummaryReportDTO getEnergySummaryReport() {
        List<EnergyDevice> devices = energyDeviceRepository.findAll();
        List<EnergyConsumptionRecord> allRecords = consumptionRepository.findAll();

        double totalConsumption = allRecords.stream().mapToDouble(r -> r.getConsumptionValue().doubleValue()).sum();
        double totalCost = totalConsumption * 0.8;

        long normalDevices = devices.stream().filter(d -> "运行中".equals(d.getStatus())).count();
        long abnormalDevices = devices.stream().filter(d -> "待维护".equals(d.getStatus()) || "已停机".equals(d.getStatus())).count();

        Map<String, Double> weekDistribution = new LinkedHashMap<>();
        for (EnergyConsumptionRecord record : allRecords) {
            if (record.getConsumptionDate() != null) {
                String key = record.getConsumptionDate().getDayOfWeek().toString();
                weekDistribution.merge(key, record.getConsumptionValue().doubleValue(), Double::sum);
            }
        }

        int season = LocalDate.now().getMonthValue() / 4 + 1;
        JsonNode carbonResult = pythonMlClient.carbonEstimate(totalConsumption, 0, 0, 0, 1, 0.8, season);
        double carbonEmission;
        boolean isMl = false;
        if (carbonResult != null && "success".equals(carbonResult.path("status").asText())) {
            carbonEmission = carbonResult.path("daily_estimate").asDouble();
            isMl = true;
        } else {
            carbonEmission = totalConsumption * 0.785;
        }

        StringBuilder reportText = new StringBuilder();
        reportText.append("【能源AI分析报告】").append("\n");
        reportText.append("📊 总能耗 ").append(String.format("%.1f", totalConsumption)).append(" kWh，")
                .append("电费 ¥").append(String.format("%.2f", totalCost)).append("。").append("\n");
        reportText.append("🔌 设备 ").append(devices.size()).append(" 台（运行 ").append(normalDevices)
                .append("，异常 ").append(abnormalDevices).append("）。").append("\n");
        reportText.append("🌱 碳排放 ").append(String.format("%.1f", carbonEmission)).append(" kg CO2");
        if (isMl) {
            reportText.append("（ML 模型估算）");
        }
        reportText.append("。").append("\n");
        reportText.append("⚡ 日均能耗 ").append(allRecords.isEmpty() ? 0 :
                String.format("%.1f", totalConsumption / allRecords.size())).append(" kWh");

        EnergySummaryReportDTO dto = new EnergySummaryReportDTO();
        dto.setReportTitle("能源AI分析报告 - " + LocalDate.now().toString());
        dto.setSummary(reportText.toString());
        dto.setTotalConsumption(Math.round(totalConsumption * 100.0) / 100.0);
        dto.setTotalCost(Math.round(totalCost * 100.0) / 100.0);
        dto.setCarbonEmission(Math.round(carbonEmission * 100.0) / 100.0);
        dto.setNormalDevices(normalDevices);
        dto.setAbnormalDevices(abnormalDevices);
        dto.setWeekDistribution(weekDistribution);
        dto.setMlGenerated(isMl);
        return dto;
    }

    // ======================== 私有工具方法 ========================

    private OptimizationTipDTO newTip(String id, String title, String description,
                                       String priority, String category, boolean mlGenerated) {
        return new OptimizationTipDTO(id, title, description, priority, category, mlGenerated);
    }
}
