package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

/**
 * 医疗患者实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "medical_patients")
public class MedicalPatient {

    @Id
    @Column(name = "patient_id", length = 10)
    private String patientId;

    @Column(nullable = false, length = 50)
    private String name;

    @Column(nullable = false)
    private Integer age;

    @Column(nullable = false, length = 10)
    private String gender;

    @Column(nullable = false, columnDefinition = "TEXT")
    private String symptoms;

    @Column(name = "check_status", nullable = false, length = 20)
    private String checkStatus;
}
