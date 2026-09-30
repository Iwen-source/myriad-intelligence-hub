package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 交通流量记录实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "traffic_flow_records")
public class TrafficFlowRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "section_id", nullable = false)
    private Long sectionId;

    @Column(name = "flow_count")
    private Integer flowCount;

    @Column(name = "avg_speed")
    private Double avgSpeed;

    @Column(name = "congestion_level", length = 20)
    private String congestionLevel;

    @Column(name = "avg_travel_time")
    private Double avgTravelTime;

    @Column(name = "record_hour")
    private Integer recordHour;

    @Column(name = "record_date")
    private LocalDate recordDate;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
