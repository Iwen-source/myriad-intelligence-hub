package com.aiempowerment.platform.service.impl;

import org.junit.jupiter.api.*;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

/**
 * MedicalAiDoctorService 集成测试 — 验证AI问诊引擎输出
 */
@SpringBootTest
@ActiveProfiles("test")
@TestMethodOrder(MethodOrderer.OrderAnnotation.class)
class MedicalAiDoctorServiceTest {

    @Autowired
    private MedicalAiDoctorService doctorService;

    @Test
    @Order(1)
    @DisplayName("发热咳嗽应推荐呼吸内科")
    void consultFeverShouldSuggestRespiratory() {
        Map<String, Object> result = doctorService.consult("张三", 28, "男",
                "发热38.5度，伴有咳嗽、头痛", 2, "无", "无");
        assertNotNull(result);
        String dept = result.get("recommendedDepartment").toString();
        assertTrue(dept.contains("呼吸内科"), "发热咳嗽应推荐呼吸内科，实际: " + dept);
    }

    @Test
    @Order(2)
    @DisplayName("腹痛应推荐消化内科")
    void consultStomachAcheShouldSuggestDigestive() {
        Map<String, Object> result = doctorService.consult("李四", 35, "女",
                "饭后腹部胀痛，反酸，偶尔腹泻", 7, "胃炎病史", "奥美拉唑");
        assertNotNull(result);
        String dept = result.get("recommendedDepartment").toString();
        assertTrue(dept.contains("消化内科"), "腹痛应推荐消化内科，实际: " + dept);
    }

    @Test
    @Order(3)
    @DisplayName("头痛应推荐神经内科或心理科")
    void consultHeadacheShouldSuggestNeurology() {
        Map<String, Object> result = doctorService.consult("王五", 30, "男",
                "头痛，伴有头晕、失眠", 7, "无", "布洛芬");
        assertNotNull(result);
        String dept = result.get("recommendedDepartment").toString();
        assertTrue(dept.contains("神经内科") || dept.contains("心理科"),
                "头痛应推荐神经内科或心理科，实际: " + dept);
    }

    @Test
    @Order(4)
    @DisplayName("严重症状应包含就医提醒")
    void severeSymptomsShouldWarn() {
        Map<String, Object> result = doctorService.consult("老赵", 55, "男",
                "剧烈胸痛，放射至左臂，伴有出冷汗", 0, "高血压", "硝酸甘油");
        assertNotNull(result);
        String advice = result.get("whenToSeeDoctor").toString();
        assertTrue(advice.contains("立即") || advice.contains("急诊") || advice.contains("紧急"),
                "剧烈胸痛应包含就医提醒，实际: " + advice);
    }

    @Test
    @Order(5)
    @DisplayName("诊断结果应包含结构化字段")
    void consultResultHasStructuredFields() {
        Map<String, Object> result = doctorService.consult("小刘", 25, "女",
                "全身皮疹，瘙痒，接触花粉后加重", 3, "过敏史", "氯雷他定");
        assertNotNull(result);
        assertTrue(result.containsKey("recommendedDepartment"));
        assertTrue(result.containsKey("possibleDiagnoses"));
        assertTrue(result.containsKey("primaryDiagnosis"));
        assertTrue(result.containsKey("treatment"));
        assertTrue(result.containsKey("summary"));
    }

    @Test
    @Order(6)
    @DisplayName("不同症状应产生不同诊断结论")
    void differentSymptomsDifferentDiagnosis() {
        Map<String, Object> r1 = doctorService.consult("患者A", 30, "男",
                "发热，咳嗽，咳痰", 3, "无", "感冒药");
        Map<String, Object> r2 = doctorService.consult("患者B", 30, "男",
                "腹痛，腹泻，恶心", 1, "无", "无");

        assertNotNull(r1.get("primaryDiagnosis"));
        assertNotNull(r2.get("primaryDiagnosis"));
        assertNotEquals(r1.get("primaryDiagnosis"), r2.get("primaryDiagnosis"),
                "不同症状的主要诊断不应相同");
    }
}
