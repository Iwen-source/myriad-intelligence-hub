package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.EnergyConsumptionRecord;
import com.aiempowerment.platform.model.entity.EnergyDevice;
import com.aiempowerment.platform.model.entity.DeviceMaintenanceRecord;
import com.aiempowerment.platform.repository.EnergyConsumptionRecordRepository;
import com.aiempowerment.platform.repository.EnergyDeviceRepository;
import com.aiempowerment.platform.repository.DeviceMaintenanceRecordRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * 初始化 - 能源管理数据（设备、能耗记录、维护记录）
 * <p>
 * 设备数据从静态种子方法加载（而非内联硬编码），更易维护和扩展。
 */
@Slf4j
@Component
@Order(2)
@RequiredArgsConstructor
public class EnergyDataInitializer implements CommandLineRunner {

    private final EnergyDeviceRepository energyDeviceRepository;
    private final EnergyConsumptionRecordRepository energyConsumptionRepository;
    private final DeviceMaintenanceRecordRepository deviceMaintenanceRepository;
    private final Random random = new Random(42);

    @Override
    public void run(String... args) {
        initEnergyData();
    }

    private void initEnergyData() {
        if (energyDeviceRepository.count() > 0) return;

        List<EnergyDeviceSeed> seeds = loadDeviceSeeds();
        List<EnergyDevice> devices = new ArrayList<>();
        for (EnergyDeviceSeed s : seeds) {
            devices.add(buildDevice(s));
        }
        energyDeviceRepository.saveAll(devices);

        List<EnergyConsumptionRecord> allConsumptionRecords = new ArrayList<>();
        List<DeviceMaintenanceRecord> allMaintenanceRecords = new ArrayList<>();

        for (EnergyDevice device : devices) {
            generateConsumptionRecords(device, allConsumptionRecords);
            generateMaintenanceRecords(device, allMaintenanceRecords);
        }

        energyConsumptionRepository.saveAll(allConsumptionRecords);
        deviceMaintenanceRepository.saveAll(allMaintenanceRecords);

        log.info("✅ 已初始化能源管理数据: {} 个设备, {} 条能耗记录, {} 条维护记录",
                seeds.size(), allConsumptionRecords.size(), allMaintenanceRecords.size());
    }

    // ======================== 设备种子数据 ========================

    private List<EnergyDeviceSeed> loadDeviceSeeds() {
        String[][] data = getDeviceDataRows();
        String[] statuses = getDeviceStatuses();
        List<EnergyDeviceSeed> seeds = new ArrayList<>();
        for (int i = 0; i < data.length; i++) {
            seeds.add(new EnergyDeviceSeed(
                    data[i][0], data[i][1], data[i][2], data[i][3],
                    data[i][4], LocalDate.parse(data[i][5]), statuses[i]
            ));
        }
        return seeds;
    }

    /** 30 个设备的静态数据，可按行增删 */
    private String[][] getDeviceDataRows() {
        return new String[][]{
                {"SUN-001", "光伏发电板A组", "太阳能", "厂房屋顶", "500kW", "2025-01-01"},
                {"SUN-002", "光伏发电板B组", "太阳能", "办公楼顶", "300kW", "2025-03-15"},
                {"SUN-003", "光伏发电板C组", "太阳能", "停车场顶棚", "200kW", "2025-04-01"},
                {"SUN-004", "光伏板D组-仓储区", "太阳能", "仓库屋顶", "350kW", "2025-02-01"},
                {"SUN-005", "光伏发电板E组", "太阳能", "研发楼顶", "150kW", "2025-05-01"},
                {"WIND-001", "风力发电机1号", "风能", "厂区北侧", "2MW", "2024-06-01"},
                {"WIND-002", "风力发电机2号", "风能", "厂区南侧", "2MW", "2024-06-01"},
                {"WIND-003", "风力发电机3号", "风能", "厂区东侧", "1.5MW", "2024-08-01"},
                {"WIND-004", "风力发电机4号", "风能", "厂区西侧", "1.5MW", "2024-08-01"},
                {"WIND-005", "风力发电机5号", "风能", "厂区西北角", "2MW", "2024-10-01"},
                {"BAT-001", "储能系统A", "储能", "配电房", "1MWh", "2025-01-01"},
                {"BAT-002", "储能系统B", "储能", "配电房2", "500kWh", "2025-02-01"},
                {"BAT-003", "储能系统C", "储能", "园区储能站", "2MWh", "2024-12-01"},
                {"GRID-001", "市电接入柜", "市电", "配电房", "1000kVA", "2024-01-01"},
                {"GRID-002", "备用市电接入", "市电", "应急配电室", "500kVA", "2024-01-01"},
                {"HVAC-001", "中央空调系统", "暖通", "办公楼", "500kW", "2024-01-01"},
                {"HVAC-002", "生产车间空调", "暖通", "生产车间", "800kW", "2024-03-01"},
                {"HVAC-003", "数据中心空调", "暖通", "机房楼", "1200kW", "2024-06-01"},
                {"PUMP-001", "循环水泵1号", "水处理", "水泵房", "75kW", "2024-01-01"},
                {"PUMP-002", "循环水泵2号", "水处理", "水泵房", "75kW", "2024-01-01"},
                {"PUMP-003", "污水处理泵", "水处理", "污水处理站", "150kW", "2024-05-01"},
                {"LIGHT-001", "园区路灯系统", "照明", "园区道路", "30kW", "2024-01-01"},
                {"LIGHT-002", "办公楼照明", "照明", "办公楼各层", "50kW", "2024-01-01"},
                {"LIGHT-003", "生产车间照明", "照明", "车间内部", "80kW", "2024-03-01"},
                {"ELEV-001", "客梯1号", "电梯", "办公楼", "15kW", "2024-01-01"},
                {"ELEV-002", "客梯2号", "电梯", "办公楼", "15kW", "2024-06-01"},
                {"ELEV-003", "货梯1号", "电梯", "生产车间", "25kW", "2024-01-01"},
                {"PROD-001", "生产线A主电机", "生产设备", "车间A区", "200kW", "2024-01-01"},
                {"PROD-002", "生产线B主电机", "生产设备", "车间B区", "200kW", "2024-02-01"},
                {"PROD-003", "压缩机系统", "生产设备", "压缩空气站", "350kW", "2024-01-01"}
        };
    }

    private String[] getDeviceStatuses() {
        return new String[]{
                "运行中", "运行中", "运行中", "运行中", "运行中",
                "运行中", "运行中", "运行中", "检修中", "运行中",
                "运行中", "运行中", "运行中", "运行中", "运行中",
                "运行中", "运行中", "运行中", "运行中", "运行中",
                "运行中", "运行中", "运行中", "检修中", "运行中",
                "运行中", "运行中", "运行中", "运行中", "运行中"
        };
    }

    // ======================== 设备生成 ========================

    private EnergyDevice buildDevice(EnergyDeviceSeed s) {
        EnergyDevice d = new EnergyDevice();
        d.setDeviceId(s.deviceId());
        d.setDeviceName(s.deviceName());
        d.setDeviceType(s.deviceType());
        d.setLocation(s.location());
        d.setPower(s.power());
        d.setStartDate(s.startDate());
        d.setStatus(s.status());
        return d;
    }

    // ======================== 能耗记录生成 ========================

    private void generateConsumptionRecords(EnergyDevice device, List<EnergyConsumptionRecord> records) {
        for (int day = 0; day < 90; day++) {
            EnergyConsumptionRecord record = new EnergyConsumptionRecord();
            record.setRecordId("R" + device.getDeviceId().replace("-", "") + String.format("%02d", day));
            record.setDeviceId(device.getDeviceId());
            LocalDate date = LocalDate.now().minusDays(day);
            record.setConsumptionDate(date);
            record.setConsumptionValue(BigDecimal.valueOf(computeBaseConsumption(device, date)));
            records.add(record);
        }
    }

    private double computeBaseConsumption(EnergyDevice device, LocalDate date) {
        double base = switch (device.getDeviceType()) {
            case "太阳能" -> 100 + random.nextDouble() * 200;
            case "风能" -> 200 + random.nextDouble() * 400;
            case "储能" -> 50 + random.nextDouble() * 100;
            case "暖通" -> 300 + random.nextDouble() * 200;
            case "照明" -> 30 + random.nextDouble() * 70;
            case "电梯" -> 15 + random.nextDouble() * 25;
            case "生产设备" -> 200 + random.nextDouble() * 300;
            case "水处理" -> 50 + random.nextDouble() * 100;
            default -> 400 + random.nextDouble() * 300;
        };
        // 周末能耗略低
        if (date.getDayOfWeek().getValue() >= 6) {
            base *= 0.7;
        }
        return base;
    }

    // ======================== 维护记录生成 ========================

    private void generateMaintenanceRecords(EnergyDevice device, List<DeviceMaintenanceRecord> records) {
        int count = 2 + random.nextInt(3);
        String[] descriptions = {
                device.getDeviceName() + " - 定期检修",
                device.getDeviceName() + " - 传感器校准与维护",
                device.getDeviceName() + " - 年度大修",
                device.getDeviceName() + " - 紧急故障维修"
        };
        for (int m = 0; m < count; m++) {
            DeviceMaintenanceRecord maintenance = new DeviceMaintenanceRecord();
            maintenance.setMaintenanceId("M" + device.getDeviceId().replace("-", "") + String.format("%02d", m + 1));
            maintenance.setDeviceId(device.getDeviceId());
            maintenance.setMaintenanceDate(LocalDate.now().minusDays(random.nextInt(90) + m * 30));
            maintenance.setMaintenanceDescription(descriptions[m % descriptions.length]);
            records.add(maintenance);
        }
    }

    // ======================== 内部记录类 ========================

    private record EnergyDeviceSeed(String deviceId, String deviceName, String deviceType,
                                     String location, String power, LocalDate startDate, String status) {}
}
