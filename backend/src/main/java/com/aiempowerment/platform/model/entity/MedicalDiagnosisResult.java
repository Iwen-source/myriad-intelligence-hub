package com.aiempowerment.platform.model.entity;

import jakarta.persistence.*;
import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.time.LocalDate;


/**
 * 医疗诊断结果实体
 */
@Data
@Entity
@NoArgsConstructor
@AllArgsConstructor
@Table(name = "medical_diagnosis_results")
public class MedicalDiagnosisResult {

    @Id
    @Column(name = "result_id", length = 10)
    private String resultId;

    @Column(name = "patient_id", nullable = false, length = 10)
    private String patientId;

    @Column(name = "diagnosis_result", nullable = false, columnDefinition = "TEXT")
    private String diagnosisResult;

    @Column(name = "diagnosis_date", nullable = false)
    private LocalDate diagnosisDate;
}
