package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.MedicalDiagnosisResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MedicalDiagnosisResultRepository extends JpaRepository<MedicalDiagnosisResult, String> {
    List<MedicalDiagnosisResult> findByPatientId(String patientId);
}
