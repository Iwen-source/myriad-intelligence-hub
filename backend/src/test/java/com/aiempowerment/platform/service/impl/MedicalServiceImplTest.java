package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.MedicalDiagnosisResult;
import com.aiempowerment.platform.model.entity.MedicalPatient;
import com.aiempowerment.platform.repository.MedicalDiagnosisResultRepository;
import com.aiempowerment.platform.repository.MedicalPatientRepository;
import com.aiempowerment.platform.service.MedicalService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class MedicalServiceImplTest {

    @Mock private MedicalPatientRepository patientRepository;
    @Mock private MedicalDiagnosisResultRepository diagnosisRepository;

    private MedicalService medicalService;

    @BeforeEach
    void setUp() {
        medicalService = new MedicalServiceImpl(patientRepository, diagnosisRepository);
    }

    private MedicalPatient createPatient(String id, String name, String symptoms, String status) {
        MedicalPatient p = new MedicalPatient();
        p.setPatientId(id);
        p.setName(name);
        p.setSymptoms(symptoms);
        p.setCheckStatus(status);
        return p;
    }

    private MedicalDiagnosisResult createDiagnosis(String id, String patientId, String result) {
        MedicalDiagnosisResult d = new MedicalDiagnosisResult();
        d.setResultId(id);
        d.setPatientId(patientId);
        d.setDiagnosisResult(result);
        d.setDiagnosisDate(LocalDate.now());
        return d;
    }

    // ====== Patient CRUD ======

    @Test
    @DisplayName("findAllPatients 应返回所有患者")
    void findAllPatients() {
        List<MedicalPatient> patients = Arrays.asList(
            createPatient("P001", "张三", "发热", "待检查"),
            createPatient("P002", "李四", "头痛", "已诊断")
        );
        when(patientRepository.findAll()).thenReturn(patients);

        List<MedicalPatient> result = medicalService.findAllPatients();
        assertEquals(2, result.size());
    }

    @Test
    @DisplayName("findPatientById 存在时应返回患者")
    void findPatientByIdExists() {
        MedicalPatient patient = createPatient("P001", "张三", "发热", "待检查");
        when(patientRepository.findById("P001")).thenReturn(Optional.of(patient));

        MedicalPatient result = medicalService.findPatientById("P001");
        assertNotNull(result);
        assertEquals("张三", result.getName());
    }

    @Test
    @DisplayName("findPatientById 不存在时应返回null")
    void findPatientByIdNotExists() {
        when(patientRepository.findById("P999")).thenReturn(Optional.empty());
        assertNull(medicalService.findPatientById("P999"));
    }

    @Test
    @DisplayName("savePatient 应生成自增患者编号")
    void savePatientAutoGenerateId() {
        MedicalPatient newPatient = new MedicalPatient();
        newPatient.setName("新患者");
        newPatient.setSymptoms("咳嗽");

        when(patientRepository.findAll()).thenReturn(Arrays.asList(
            createPatient("P001", "A", "症状1", "已诊断"),
            createPatient("P003", "B", "症状2", "待检查")
        ));
        when(patientRepository.save(any(MedicalPatient.class)))
            .thenAnswer(inv -> inv.getArgument(0));

        MedicalPatient result = medicalService.savePatient(newPatient);
        assertEquals("P004", result.getPatientId());
    }

    @Test
    @DisplayName("savePatient 已有编号不应覆盖")
    void savePatientKeepExistingId() {
        MedicalPatient patient = createPatient("P999", "已有患者", "症状", "待检查");
        when(patientRepository.save(any(MedicalPatient.class)))
            .thenAnswer(inv -> inv.getArgument(0));

        MedicalPatient result = medicalService.savePatient(patient);
        assertEquals("P999", result.getPatientId());
        verify(patientRepository, never()).findAll();
    }

    @Test
    @DisplayName("deletePatient 应同时删除关联诊断")
    void deletePatientCascadeDiagnosis() {
        List<MedicalDiagnosisResult> related = Arrays.asList(
            createDiagnosis("D001", "P001", "感冒"),
            createDiagnosis("D002", "P001", "流感")
        );
        when(diagnosisRepository.findByPatientId("P001")).thenReturn(related);

        medicalService.deletePatient("P001");

        verify(diagnosisRepository).deleteAll(related);
        verify(patientRepository).deleteById("P001");
    }

    @Test
    @DisplayName("deletePatient 无关联诊断时只删患者")
    void deletePatientNoDiagnosis() {
        when(diagnosisRepository.findByPatientId("P002")).thenReturn(List.of());

        medicalService.deletePatient("P002");

        verify(diagnosisRepository, never()).deleteAll(any());
        verify(patientRepository).deleteById("P002");
    }

    // ====== Search & Filter ======

    @Test
    @DisplayName("findPatientsByStatus 应按状态过滤")
    void findPatientsByStatus() {
        MedicalPatient p1 = createPatient("P001", "张三", "发热", "待检查");
        MedicalPatient p2 = createPatient("P002", "李四", "头痛", "已诊断");
        when(patientRepository.findByCheckStatus("待检查")).thenReturn(List.of(p1));

        List<MedicalPatient> result = medicalService.findPatientsByStatus("待检查");
        assertEquals(1, result.size());
        assertEquals("张三", result.get(0).getName());
    }

    @Test
    @DisplayName("searchPatients 应按关键字搜索姓名、症状、编号")
    void searchPatientsByKeyword() {
        List<MedicalPatient> all = Arrays.asList(
            createPatient("P001", "张三", "发热伴咳嗽", "待检查"),
            createPatient("P002", "李四", "头痛头晕", "已诊断"),
            createPatient("P003", "王五", "发热", "已诊断")
        );
        when(patientRepository.findAll()).thenReturn(all);

        List<MedicalPatient> result = medicalService.searchPatients("发热");
        assertEquals(2, result.size());
    }

    @Test
    @DisplayName("searchPatients 空关键字应返回全部")
    void searchPatientsEmptyKeyword() {
        List<MedicalPatient> all = List.of(createPatient("P001", "A", "S1", "待检查"));
        when(patientRepository.findAll()).thenReturn(all);

        assertEquals(1, medicalService.searchPatients("").size());
        assertEquals(1, medicalService.searchPatients(null).size());
    }

    // ====== Diagnosis ======

    @Test
    @DisplayName("findDiagnosisByPatient 应返回患者诊断列表")
    void findDiagnosisByPatient() {
        List<MedicalDiagnosisResult> list = List.of(createDiagnosis("D001", "P001", "感冒"));
        when(diagnosisRepository.findByPatientId("P001")).thenReturn(list);

        List<MedicalDiagnosisResult> result = medicalService.findDiagnosisByPatient("P001");
        assertEquals(1, result.size());
    }

    @Test
    @DisplayName("saveDiagnosisResult 应保存并返回")
    void saveDiagnosisResult() {
        MedicalDiagnosisResult d = createDiagnosis("D001", "P001", "诊断结果");
        when(diagnosisRepository.save(any())).thenReturn(d);

        MedicalDiagnosisResult result = medicalService.saveDiagnosisResult(d);
        assertEquals("D001", result.getResultId());
    }

    // ====== Health Profile ======

    @Test
    @DisplayName("getPatientHealthProfile 患者不存在应返回错误map")
    void healthProfilePatientNotFound() {
        when(patientRepository.findById("P999")).thenReturn(Optional.empty());

        Map<String, Object> profile = medicalService.getPatientHealthProfile("P999");
        assertTrue(profile.containsKey("error"));
        assertEquals("患者不存在", profile.get("error"));
    }

    @Test
    @DisplayName("getPatientHealthProfile 存在时应返回完整档案")
    void healthProfileComplete() {
        MedicalPatient patient = createPatient("P001", "张三", "发热", "待检查");
        MedicalDiagnosisResult d1 = createDiagnosis("D001", "P001", "上呼吸道感染");
        MedicalDiagnosisResult d2 = createDiagnosis("D002", "P001", "支气管炎");

        when(patientRepository.findById("P001")).thenReturn(Optional.of(patient));
        when(diagnosisRepository.findByPatientId("P001")).thenReturn(Arrays.asList(d1, d2));

        Map<String, Object> profile = medicalService.getPatientHealthProfile("P001");

        assertEquals(patient, profile.get("patient"));
        assertEquals(2, profile.get("totalVisits"));
        assertNotNull(profile.get("timeline"));
        assertNotNull(profile.get("firstVisitDate"));
        assertNotNull(profile.get("lastVisitDate"));
    }
}
