package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;

/**
 * 环境监测点实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "environment_monitor_points")
public class EnvironmentMonitorPoint {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "point_name", nullable = false, length = 100)
    private String pointName;

    @Column(nullable = false, length = 200)
    private String location;

    private Double longitude;

    private Double latitude;

    @Column(name = "monitor_type", length = 50)
    private String monitorType;

    @Column(length = 20)
    private String status;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
