package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.MedicalPatient;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface MedicalPatientRepository extends JpaRepository<MedicalPatient, String> {
    List<MedicalPatient> findByCheckStatus(String checkStatus);
    List<MedicalPatient> findByNameContaining(String name);
}
