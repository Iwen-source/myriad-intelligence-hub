package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDateTime;

/**
 * 交通路段实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "traffic_road_sections")
public class TrafficRoadSection {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "road_name", nullable = false, length = 100)
    private String roadName;

    @Column(name = "section_name", length = 200)
    private String sectionName;

    @Column(name = "road_type", length = 50)
    private String roadType;

    private Double length;

    private Integer lanes;

    @Column(name = "speed_limit")
    private Integer speedLimit;

    @Column(name = "start_point", length = 200)
    private String startPoint;

    @Column(name = "end_point", length = 200)
    private String endPoint;

    @Column(length = 20)
    private String status;

    @Column(name = "create_time")
    private LocalDateTime createTime;

    @PrePersist
    protected void onCreate() {
        createTime = LocalDateTime.now();
    }
}
