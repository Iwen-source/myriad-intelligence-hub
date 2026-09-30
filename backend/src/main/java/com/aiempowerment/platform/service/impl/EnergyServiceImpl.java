package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.EnergyDevice;
import com.aiempowerment.platform.model.entity.EnergyConsumptionRecord;
import com.aiempowerment.platform.model.entity.DeviceMaintenanceRecord;
import com.aiempowerment.platform.repository.EnergyDeviceRepository;
import com.aiempowerment.platform.repository.EnergyConsumptionRecordRepository;
import com.aiempowerment.platform.repository.DeviceMaintenanceRecordRepository;
import com.aiempowerment.platform.service.EnergyService;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.util.List;

@Service
@RequiredArgsConstructor
/**
 * EnergyServiceImpl - 能源管理服务实现 - 设备与能耗数据的CRUD及统计分析
 */
public class EnergyServiceImpl implements EnergyService {

    private final EnergyDeviceRepository deviceRepository;
    private final EnergyConsumptionRecordRepository consumptionRepository;
    private final DeviceMaintenanceRecordRepository maintenanceRepository;

    @Override
    @Cacheable(value = "energyDevices", key = "'all'")
    public List<EnergyDevice> findAllDevices() {
        return deviceRepository.findAll();
    }

    @Override
    @Cacheable(value = "energyDevices", key = "#deviceId")
    public EnergyDevice findDeviceById(String deviceId) {
        return deviceRepository.findById(deviceId).orElse(null);
    }

    @Override
    @Transactional
    @CacheEvict(value = "energyDevices", allEntries = true)
    public EnergyDevice saveDevice(EnergyDevice device) {
        return deviceRepository.save(device);
    }

    @Override
    @Transactional
    @CacheEvict(value = "energyDevices", allEntries = true)
    public void deleteDevice(String deviceId) {
        deviceRepository.deleteById(deviceId);
    }

    @Override
    public List<EnergyDevice> searchDevices(String deviceType, String status, String location) {
        if (status != null && !status.isEmpty()) {
            return deviceRepository.findByStatus(status);
        }
        if (location != null && !location.isEmpty()) {
            return deviceRepository.findByLocationContaining(location);
        }
        if (deviceType != null && !deviceType.isEmpty()) {
            return deviceRepository.findByDeviceTypeContaining(deviceType);
        }
        return deviceRepository.findAll();
    }

    @Override
    public List<EnergyConsumptionRecord> findAllConsumptionRecords() {
        return consumptionRepository.findAll();
    }

    @Override
    public List<EnergyConsumptionRecord> findConsumptionByDevice(String deviceId) {
        return consumptionRepository.findByDeviceId(deviceId);
    }

    @Override
    public List<EnergyConsumptionRecord> findConsumptionByDateRange(LocalDate start, LocalDate end) {
        return consumptionRepository.findByConsumptionDateBetween(start, end);
    }

    @Override
    @Transactional
    @CacheEvict(value = "energyConsumption", allEntries = true)
    public EnergyConsumptionRecord saveConsumptionRecord(EnergyConsumptionRecord record) {
        return consumptionRepository.save(record);
    }

    @Override
    public List<DeviceMaintenanceRecord> findAllMaintenanceRecords() {
        return maintenanceRepository.findAll();
    }

    @Override
    public List<DeviceMaintenanceRecord> findMaintenanceByDevice(String deviceId) {
        return maintenanceRepository.findByDeviceId(deviceId);
    }

    @Override
    @Transactional
    public DeviceMaintenanceRecord saveMaintenanceRecord(DeviceMaintenanceRecord record) {
        return maintenanceRepository.save(record);
    }
}

