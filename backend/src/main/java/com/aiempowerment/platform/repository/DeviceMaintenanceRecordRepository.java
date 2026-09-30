package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.DeviceMaintenanceRecord;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface DeviceMaintenanceRecordRepository extends JpaRepository<DeviceMaintenanceRecord, String> {
    List<DeviceMaintenanceRecord> findByDeviceId(String deviceId);
}
