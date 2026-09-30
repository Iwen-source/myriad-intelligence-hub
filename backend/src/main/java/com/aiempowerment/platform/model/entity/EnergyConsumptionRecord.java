package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDate;

/**
 * 能耗记录实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "energy_consumption_records")
public class EnergyConsumptionRecord {

    @Id
    @Column(name = "record_id", length = 20)
    private String recordId;

    @Column(name = "device_id", nullable = false, length = 20)
    private String deviceId;

    @Column(name = "consumption_date", nullable = false)
    private LocalDate consumptionDate;

    @Column(name = "consumption_value", nullable = false, precision = 10, scale = 2)
    private BigDecimal consumptionValue;
}
