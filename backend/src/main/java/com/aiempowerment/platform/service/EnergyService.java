package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.entity.EnergyDevice;
import com.aiempowerment.platform.model.entity.EnergyConsumptionRecord;
import com.aiempowerment.platform.model.entity.DeviceMaintenanceRecord;

import java.time.LocalDate;
import java.util.List;

public interface EnergyService {
    // 设备管理
    List<EnergyDevice> findAllDevices();
    EnergyDevice findDeviceById(String deviceId);
    EnergyDevice saveDevice(EnergyDevice device);
    void deleteDevice(String deviceId);
    List<EnergyDevice> searchDevices(String deviceType, String status, String location);

    // 能耗记录
    List<EnergyConsumptionRecord> findAllConsumptionRecords();
    List<EnergyConsumptionRecord> findConsumptionByDevice(String deviceId);
    List<EnergyConsumptionRecord> findConsumptionByDateRange(LocalDate start, LocalDate end);
    EnergyConsumptionRecord saveConsumptionRecord(EnergyConsumptionRecord record);

    // 维护记录
    List<DeviceMaintenanceRecord> findAllMaintenanceRecords();
    List<DeviceMaintenanceRecord> findMaintenanceByDevice(String deviceId);
    DeviceMaintenanceRecord saveMaintenanceRecord(DeviceMaintenanceRecord record);
}
