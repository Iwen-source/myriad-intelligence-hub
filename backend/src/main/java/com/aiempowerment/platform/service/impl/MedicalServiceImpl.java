package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.MedicalPatient;
import com.aiempowerment.platform.model.entity.MedicalDiagnosisResult;
import com.aiempowerment.platform.repository.MedicalPatientRepository;
import com.aiempowerment.platform.repository.MedicalDiagnosisResultRepository;
import com.aiempowerment.platform.service.MedicalService;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
/**
 * MedicalServiceImpl - 医疗信息服务实现 - 患者与病历数据查询管理
 */
public class MedicalServiceImpl implements MedicalService {

    private final MedicalPatientRepository patientRepository;
    private final MedicalDiagnosisResultRepository diagnosisRepository;

    @Override
    public List<MedicalPatient> findAllPatients() {
        return patientRepository.findAll();
    }

    @Override
    public MedicalPatient findPatientById(String patientId) {
        return patientRepository.findById(patientId).orElse(null);
    }

    @Override
    @Transactional
    public MedicalPatient savePatient(MedicalPatient patient) {
        // 自动生成患者编号（synchronized 串行化 max+1，避免并发下主键冲突导致静默覆盖）
        if (patient.getPatientId() == null || patient.getPatientId().isEmpty()) {
            patient.setPatientId(generatePatientId());
        }
        return patientRepository.save(patient);
    }

    private synchronized String generatePatientId() {
        List<MedicalPatient> all = patientRepository.findAll();
        int maxNum = 0;
        for (MedicalPatient p : all) {
            String pid = p.getPatientId();
            if (pid != null && pid.startsWith("P")) {
                try {
                    int num = Integer.parseInt(pid.substring(1));
                    if (num > maxNum) maxNum = num;
                } catch (NumberFormatException ignored) {}
            }
        }
        return String.format("P%03d", maxNum + 1);
    }

    @Override
    @Transactional
    public void deletePatient(String patientId) {
        // 删除患者时同时删除关联诊断记录
        List<MedicalDiagnosisResult> related = diagnosisRepository.findByPatientId(patientId);
        if (related != null && !related.isEmpty()) {
            diagnosisRepository.deleteAll(related);
        }
        patientRepository.deleteById(patientId);
    }

    @Override
    public List<MedicalPatient> findPatientsByStatus(String status) {
        return patientRepository.findByCheckStatus(status);
    }

    @Override
    public List<MedicalPatient> searchPatients(String keyword) {
        if (keyword == null || keyword.isBlank()) return findAllPatients();
        List<MedicalPatient> all = patientRepository.findAll();
        String kw = keyword.toLowerCase();
        return all.stream()
            .filter(p -> (p.getName() != null && p.getName().toLowerCase().contains(kw)) ||
                         (p.getSymptoms() != null && p.getSymptoms().toLowerCase().contains(kw)) ||
                         (p.getPatientId() != null && p.getPatientId().toLowerCase().contains(kw)))
            .collect(Collectors.toList());
    }

    @Override
    public List<MedicalDiagnosisResult> findAllDiagnosisResults() {
        return diagnosisRepository.findAll();
    }

    @Override
    public List<MedicalDiagnosisResult> findDiagnosisByPatient(String patientId) {
        return diagnosisRepository.findByPatientId(patientId);
    }

    @Override
    @Transactional
    public MedicalDiagnosisResult saveDiagnosisResult(MedicalDiagnosisResult result) {
        // 自动生成诊断编号（synchronized 串行化 max+1，避免并发下主键冲突导致静默覆盖）
        if (result.getResultId() == null || result.getResultId().isEmpty()) {
            result.setResultId(generateDiagnosisId());
        }
        return diagnosisRepository.save(result);
    }

    private synchronized String generateDiagnosisId() {
        List<MedicalDiagnosisResult> all = diagnosisRepository.findAll();
        int maxNum = 0;
        for (MedicalDiagnosisResult d : all) {
            String rid = d.getResultId();
            if (rid != null && rid.startsWith("D")) {
                try {
                    int num = Integer.parseInt(rid.substring(1));
                    if (num > maxNum) maxNum = num;
                } catch (NumberFormatException ignored) {}
            }
        }
        return String.format("D%04d", maxNum + 1);
    }

    @Override
    @Transactional
    public void deleteDiagnosisResult(String resultId) {
        diagnosisRepository.deleteById(resultId);
    }

    @Override
    public Map<String, Object> getPatientHealthProfile(String patientId) {
        MedicalPatient patient = patientRepository.findById(patientId).orElse(null);
        if (patient == null) return Map.of("error", "患者不存在");

        List<MedicalDiagnosisResult> allDiagnosis = diagnosisRepository.findByPatientId(patientId);
        List<Map<String, Object>> timeline = allDiagnosis.stream()
            .sorted((a, b) -> {
                if (a.getDiagnosisDate() == null) return 1;
                if (b.getDiagnosisDate() == null) return -1;
                return b.getDiagnosisDate().compareTo(a.getDiagnosisDate());
            })
            .map(d -> {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("diagnosisId", d.getResultId());
                item.put("date", d.getDiagnosisDate() != null ? d.getDiagnosisDate().toString() : "未知");
                item.put("disease", d.getDiagnosisResult() != null ?
                    (d.getDiagnosisResult().length() > 30 ?
                        d.getDiagnosisResult().substring(0, 30) + "..." : d.getDiagnosisResult()) : "未知");
                item.put("fullResult", d.getDiagnosisResult());
                return item;
            })
            .collect(Collectors.toList());

        // 诊断次数统计
        Map<String, Long> diagnosisCount = allDiagnosis.stream()
            .filter(d -> d.getDiagnosisResult() != null)
            .collect(Collectors.groupingBy(d -> {
                String r = d.getDiagnosisResult();
                return r.length() > 10 ? r.substring(0, 10) : r;
            }, Collectors.counting()));

        Map<String, Object> profile = new LinkedHashMap<>();
        profile.put("patient", patient);
        profile.put("totalVisits", allDiagnosis.size());
        profile.put("timeline", timeline);
        profile.put("diagnosisSummary", diagnosisCount);
        profile.put("firstVisitDate", allDiagnosis.stream()
            .filter(d -> d.getDiagnosisDate() != null)
            .map(MedicalDiagnosisResult::getDiagnosisDate)
            .min(Comparator.naturalOrder())
            .map(Object::toString).orElse("无记录"));
        profile.put("lastVisitDate", allDiagnosis.stream()
            .filter(d -> d.getDiagnosisDate() != null)
            .map(MedicalDiagnosisResult::getDiagnosisDate)
            .max(Comparator.naturalOrder())
            .map(Object::toString).orElse("无记录"));

        return profile;
    }
}

