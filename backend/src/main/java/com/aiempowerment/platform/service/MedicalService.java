package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.entity.MedicalPatient;
import com.aiempowerment.platform.model.entity.MedicalDiagnosisResult;

import java.util.List;

import java.util.Map;

public interface MedicalService {
    List<MedicalPatient> findAllPatients();
    MedicalPatient findPatientById(String patientId);
    MedicalPatient savePatient(MedicalPatient patient);
    void deletePatient(String patientId);
    List<MedicalPatient> findPatientsByStatus(String status);
    /** 关键词搜索患者（姓名、症状） */
    List<MedicalPatient> searchPatients(String keyword);

    List<MedicalDiagnosisResult> findAllDiagnosisResults();
    List<MedicalDiagnosisResult> findDiagnosisByPatient(String patientId);
    MedicalDiagnosisResult saveDiagnosisResult(MedicalDiagnosisResult result);
    void deleteDiagnosisResult(String resultId);

    /** 获取患者健康档案（含诊断时间线） */
    Map<String, Object> getPatientHealthProfile(String patientId);
}
