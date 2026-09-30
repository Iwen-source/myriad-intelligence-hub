package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDate;

/**
 * 能源设备实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "energy_devices")
public class EnergyDevice {

    @Id
    @Column(name = "device_id", length = 10)
    private String deviceId;

    @Column(name = "device_name", nullable = false, length = 50)
    private String deviceName;

    @Column(name = "device_type", nullable = false, length = 50)
    private String deviceType;

    @Column(nullable = false, length = 50)
    private String location;

    @Column(nullable = false, length = 20)
    private String power;

    @Column(name = "start_date", nullable = false)
    private LocalDate startDate;

    @Column(nullable = false, length = 20)
    private String status;
}
