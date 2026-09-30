package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.dto.ConsultRequest;
import com.aiempowerment.platform.model.dto.PatientSaveRequest;
import com.aiempowerment.platform.model.entity.MedicalDiagnosisResult;
import com.aiempowerment.platform.model.entity.MedicalPatient;
import com.aiempowerment.platform.service.AIAnalysisService;
import com.aiempowerment.platform.service.MedicalService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.aiempowerment.platform.service.impl.MedicalAiDoctorService;
import com.aiempowerment.platform.service.impl.MedicalAiModelService;
import com.fasterxml.jackson.databind.JsonNode;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

import jakarta.servlet.http.HttpServletRequest;

/**
 * 医疗诊断控制器 — AI赋能云医院场景
 *
 * 创新功能：
 * 1. AI问诊 — 输入病情细节，输出结构化诊断报告
 * 2. 疾病知识库 — 20+种疾病的详细百科
 * 3. 患者健康档案 — 全周期健康管理
 */
@RestController
@RequestMapping("/medical")
@RequiredArgsConstructor
public class MedicalController {

    private final MedicalService medicalService;
    private final AIAnalysisService aiAnalysisService;
    private final MedicalAiDoctorService aiDoctorService;
    private final MedicalAiModelService aiModelService;
    private final PythonMlClient pythonMlClient;

    // ======================== 患者管理 ========================

    @GetMapping("/patients")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> listPatients(@RequestParam(required = false) String status,
                                       @RequestParam(required = false) String keyword) {
        if (status != null && !status.isEmpty()) {
            return ApiResponse.success(medicalService.findPatientsByStatus(status));
        }
        if (keyword != null && !keyword.isEmpty()) {
            return ApiResponse.success(medicalService.searchPatients(keyword));
        }
        return ApiResponse.success(medicalService.findAllPatients());
    }

    @GetMapping("/patients/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> getPatient(@PathVariable String id) {
        return ApiResponse.success(medicalService.findPatientById(id));
    }

    @PostMapping("/patients")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> savePatient(@Valid @RequestBody PatientSaveRequest request) {
        // DTO → Entity
        MedicalPatient patient = new MedicalPatient();
        patient.setPatientId(request.getPatientId());
        patient.setName(request.getName());
        patient.setGender(request.getGender());
        patient.setAge(request.getAge());
        patient.setSymptoms(request.getSymptoms());
        patient.setCheckStatus(request.getCheckStatus());
        return ApiResponse.success(medicalService.savePatient(patient));
    }

    @DeleteMapping("/patients/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deletePatient(@PathVariable String id) {
        medicalService.deletePatient(id);
        return ApiResponse.success("删除成功");
    }

    // ======================== 诊断记录 ========================

    @GetMapping("/diagnosis")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> listDiagnosis(@RequestParam(required = false) String patientId) {
        if (patientId != null) {
            return ApiResponse.success(medicalService.findDiagnosisByPatient(patientId));
        }
        return ApiResponse.success(medicalService.findAllDiagnosisResults());
    }

    @PostMapping("/diagnosis")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> saveDiagnosis(@RequestBody MedicalDiagnosisResult result) {
        return ApiResponse.success(medicalService.saveDiagnosisResult(result));
    }

    @DeleteMapping("/diagnosis/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deleteDiagnosis(@PathVariable String id) {
        medicalService.deleteDiagnosisResult(id);
        return ApiResponse.success("删除成功");
    }

    // ======================== 🏆 核心创新：AI问诊（规则引擎版） ========================

    /**
     * AI问诊 — 基于医学知识库的规则引擎诊断
     * 输入患者详细病情，返回结构化诊断报告
     */
    @PostMapping("/ai-doctor/consult")
    public ApiResponse<?> aiConsult(@Valid @RequestBody ConsultRequest request) {
        return ApiResponse.success(aiDoctorService.consult(
                request.getName(),
                request.getAge(),
                request.getGender(),
                request.getSymptoms(),
                request.getDurationDays(),
                request.getHistory(),
                request.getMedications()));
    }

    // ======================== 🏆🏆🏆 真正的AI大模型问诊 ========================

    @PostMapping("/ai-model/consult")
    public ApiResponse<?> aiModelConsult(@Valid @RequestBody ConsultRequest request) {
        return ApiResponse.success(aiModelService.consult(
                request.getName(),
                request.getAge(),
                request.getGender(),
                request.getSymptoms(),
                request.getDurationDays(),
                request.getHistory(),
                request.getMedications()));
    }

    // ======================== 疾病知识库 ========================

    /** 疾病库概览 */
    @GetMapping("/disease-library/overview")
    public ApiResponse<?> diseaseLibraryOverview() {
        return ApiResponse.success(aiDoctorService.getDiseaseLibraryOverview());
    }

    /** 搜索疾病库 */
    @GetMapping("/disease-library/search")
    public ApiResponse<?> searchDiseaseLibrary(@RequestParam(required = false) String keyword) {
        return ApiResponse.success(aiDoctorService.searchDiseaseLibrary(keyword));
    }

    /** 疾病详情 */
    @GetMapping("/disease-library/{name}")
    public ApiResponse<?> diseaseDetail(@PathVariable String name) {
        Map<String, Object> detail = aiDoctorService.getDiseaseDetail(name);
        if (detail == null) {
            return ApiResponse.error(404, "未找到该疾病信息");
        }
        return ApiResponse.success(detail);
    }

    // ======================== 患者健康档案 ========================

    /** 患者健康档案（全生命周期） */
    @GetMapping("/patients/{id}/health-profile")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> patientHealthProfile(@PathVariable String id) {
        return ApiResponse.success(medicalService.getPatientHealthProfile(id));
    }

    // ======================== AI分析 ========================

    @PostMapping("/analysis/symptom")
    public ApiResponse<?> analyzeSymptom(@RequestBody Map<String, String> body) {
        String symptoms = body.get("symptoms");
        return ApiResponse.success(aiAnalysisService.analyzeSymptomDisease(symptoms));
    }

    @GetMapping("/analysis/similar/{patientId}")
    public ApiResponse<?> findSimilarCases(@PathVariable Long patientId) {
        return ApiResponse.success(aiAnalysisService.findSimilarCases(patientId));
    }

    @GetMapping("/analysis/trend")
    public ApiResponse<?> analyzeTrend() {
        return ApiResponse.success(aiAnalysisService.analyzeDiagnosisTrend());
    }

    // ======================== V3 真实数据模型端点 ========================

    /**
     * 🩺 糖尿病风险预测 — 基于真实 PIMA 数据
     */
    /**
     * 🩺 糖尿病风险预测 — 基于真实 PIMA 数据
     * 前端字段使用snake_case格式，与Python后端一致
     */
    @PostMapping("/v3/diabetes-risk")
    public ApiResponse<?> diabetesRiskPredict(@RequestBody Map<String, Object> params) {
        double pregnancies = getDouble(params, "pregnancies", 0);
        double glucose = getDouble(params, "glucose", 100);
        // 前端使用snake_case字段名 → 需要匹配Python后端而非Java camelCase
        double bloodPressure = getDouble(params, "blood_pressure",
            getDouble(params, "bloodPressure", 72));
        double skinThickness = getDouble(params, "skin_thickness",
            getDouble(params, "skinThickness", 20));
        double insulin = getDouble(params, "insulin", 79);
        double bmi = getDouble(params, "bmi", 25);
        double diabetesPedigree = getDouble(params, "diabetes_pedigree",
            getDouble(params, "diabetesPedigree", 0.47));
        double age = getDouble(params, "age", 30);

        JsonNode result = pythonMlClient.diabetesRiskPredict(
            pregnancies, glucose, bloodPressure, skinThickness,
            insulin, bmi, diabetesPedigree, age
        );
        if (result == null) {
            return ApiResponse.error(500, "糖尿病风险模型调用失败");
        }
        return ApiResponse.success(result);
    }

    /**
     * 🩺 血糖时序预测 — 基于真实 CGM 数据
     * 支持两种输入格式:
     *   格式A: {readings: [12个血糖值], predictMinutes: 30}
     *   格式B: {current_glucose, prediction_minutes, postprandial_hours, avg_glucose_3d, hba1c}
     */
    @SuppressWarnings("unchecked")
    @PostMapping("/v3/glucose-forecast")
    public ApiResponse<?> glucoseForecastPredict(@RequestBody Map<String, Object> params) {
        // 格式A: 尝试读取 readings 数组
        List<Double> readings = null;
        Object readingsObj = params.get("readings");
        if (readingsObj instanceof List) {
            readings = (List<Double>) readingsObj;
        }

        // 如果 readings 不足12个，检查是否使用前端的简化格式（格式B）
        if (readings == null || readings.size() < 12) {
            Object currentGlucoseObj = params.get("current_glucose");
            if (currentGlucoseObj != null) {
                // 前端简化格式：将当前血糖等字段传递给Python，由Python生成合成读数
                double currentGlucose = ((Number) currentGlucoseObj).doubleValue();
                int predictionMinutes = getInt(params, "prediction_minutes", 30);
                double postprandialHours = getDouble(params, "postprandial_hours", 0);
                double avgGlucose3d = getDouble(params, "avg_glucose_3d", currentGlucose);
                double hba1c = getDouble(params, "hba1c", 6.5);

                // 构造包含前端字段的请求体，传递到Python
                Map<String, Object> forwardedParams = new HashMap<>(params);
                // 确保Python能正确解析 prediction_minutes
                forwardedParams.put("prediction_minutes", predictionMinutes);
                if (!forwardedParams.containsKey("predict_minutes")) {
                    forwardedParams.put("predict_minutes", predictionMinutes);
                }

                JsonNode result = pythonMlClient.proxyGlucoseForecast(forwardedParams);
                if (result == null) {
                    return ApiResponse.error(500, "血糖预测模型调用失败");
                }
                return ApiResponse.success(result);
            }

            return ApiResponse.error(400, "至少需要12个历史血糖读数");
        }

        // 格式A: 有readings数组，调用Python
        int predictMinutes = getInt(params, "predictMinutes",
            getInt(params, "predict_minutes", 30));

        JsonNode result = pythonMlClient.glucoseForecastPredict(readings, predictMinutes);
        if (result == null) {
            return ApiResponse.error(500, "血糖预测模型调用失败");
        }
        return ApiResponse.success(result);
    }

    private double getDouble(Map<String, Object> map, String key, double defaultValue) {
        Object val = map.get(key);
        if (val instanceof Number) return ((Number) val).doubleValue();
        return defaultValue;
    }

    private int getInt(Map<String, Object> map, String key, int defaultValue) {
        Object val = map.get(key);
        if (val instanceof Number) return ((Number) val).intValue();
        return defaultValue;
    }

    /**
     * 胰岛素-血糖相关性分析 — 基于 PIMA 真实数据
     * 返回：皮尔逊相关系数、p值、散点数据、统计概要
     */
    @GetMapping("/v3/insulin-glucose-correlation")
    public ApiResponse<?> insulinGlucoseCorrelation() {
        JsonNode result = pythonMlClient.insulinGlucoseCorrelation();
        if (result == null) {
            return ApiResponse.error(500, "相关性分析调用失败");
        }
        return ApiResponse.success(result);
    }

    /**
     * 获取真实 CGM 血糖监测数据（9位患者）
     * 返回患者列表及血糖时间序列
     */
    @GetMapping("/v3/glucose-patients")
    public ApiResponse<?> glucosePatients() {
        JsonNode result = pythonMlClient.glucosePatients();
        if (result == null) {
            return ApiResponse.error(500, "血糖数据获取失败");
        }
        return ApiResponse.success(result);
    }

    /**
     * 获取指定患者的完整血糖时序数据
     * @param patientId 患者编号 (01-09)
     */
    @GetMapping("/v3/glucose-patient/{patientId}")
    public ApiResponse<?> glucosePatientDetail(@PathVariable String patientId) {
        JsonNode result = pythonMlClient.glucosePatientDetail(patientId);
        if (result == null) {
            return ApiResponse.error(500, "患者血糖数据获取失败");
        }
        return ApiResponse.success(result);
    }

    // ======================== CT 影像工作站 (替换旧脑部CT) ========================

    /**
     * CT 影像工作台 — 通用代理到 Python ML Server
     * 替换旧 brain-ct 检测, 提供完整的 CT 影像分析功能
     */
    @RequestMapping("/ct/**")
    public ResponseEntity<?> ctWorkstationProxy(HttpServletRequest request,
                                                  @RequestBody(required = false) String body) {
        // 提取 /ct/ 之后的路径
        String fullPath = request.getRequestURI();
        String ctPath = fullPath.substring(fullPath.indexOf("/ct"));
        String method = request.getMethod();

        JsonNode result = pythonMlClient.ctWorkstationProxy(ctPath, method, body);
        if (result == null) {
            return ResponseEntity.status(500).body(
                Map.of("status", "error", "message", "CT 工作站调用失败")
            );
        }
        return ResponseEntity.ok(result);
    }
}
