package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;

/**
 * 空气质量记录实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "air_quality_records")
public class AirQualityRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "point_id", nullable = false)
    private Long pointId;

    private Integer aqi;

    private Double pm25;

    private Double pm10;

    private Double o3;

    private Double no2;

    private Double so2;

    private Double co;

    private Double temperature;

    private Double humidity;

    @Column(name = "record_time")
    private LocalDateTime recordTime;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
