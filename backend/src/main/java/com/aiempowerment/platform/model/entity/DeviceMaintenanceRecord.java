package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDate;

/**
 * 设备维护记录实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "device_maintenance_records")
public class DeviceMaintenanceRecord {

    @Id
    @Column(name = "maintenance_id", length = 20)
    private String maintenanceId;

    @Column(name = "device_id", nullable = false, length = 20)
    private String deviceId;

    @Column(name = "maintenance_date", nullable = false)
    private LocalDate maintenanceDate;

    @Column(name = "maintenance_description", nullable = false, columnDefinition = "TEXT")
    private String maintenanceDescription;
}
