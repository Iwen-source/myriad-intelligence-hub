package com.aiempowerment.platform.service.analysis;

import java.util.List;
import java.util.Map;

/**
 * 医疗AI分析接口 - 症状分析、病例匹配、诊断趋势
 */
public interface MedicalAnalysisInterface {

    /** 症状-疾病关联分析 */
    List<Map<String, Object>> analyzeSymptomDisease(String symptoms);

    /** 相似病例推荐 */
    List<Map<String, Object>> findSimilarCases(Long patientId);

    /** 诊断趋势分析 */
    Map<String, Object> analyzeDiagnosisTrend();
}