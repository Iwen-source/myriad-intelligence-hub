package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.model.dto.ConsultRequest;
import com.aiempowerment.platform.model.dto.PatientSaveRequest;
import jakarta.validation.Validation;
import jakarta.validation.Validator;
import jakarta.validation.ValidatorFactory;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * DTO Validation 单元测试
 */
class MedicalControllerTest {

    private static Validator validator;

    @BeforeAll
    static void setUp() {
        try (ValidatorFactory factory = Validation.buildDefaultValidatorFactory()) {
            validator = factory.getValidator();
        }
    }

    @Test
    void testConsultRequestValidationPasses() {
        ConsultRequest request = new ConsultRequest();
        request.setName("张三");
        request.setAge(30);
        request.setGender("男");
        request.setSymptoms("发热咳嗽三天");
        request.setDurationDays(3);
        request.setHistory("无");
        request.setMedications("布洛芬");

        var violations = validator.validate(request);
        assertTrue(violations.isEmpty(), "合法请求应无校验错误");
    }

    @Test
    void testConsultRequestFailsWhenSymptomsEmpty() {
        ConsultRequest request = new ConsultRequest();
        request.setSymptoms("");

        var violations = validator.validate(request);
        assertFalse(violations.isEmpty(), "症状为空时应校验失败");
        assertTrue(violations.stream()
                .anyMatch(v -> v.getMessage().contains("不能为空")));
    }

    @Test
    void testPatientSaveRequestValidationPasses() {
        PatientSaveRequest request = new PatientSaveRequest();
        request.setName("李四");
        request.setGender("女");
        request.setAge(25);

        var violations = validator.validate(request);
        assertTrue(violations.isEmpty(), "合法患者数据应无校验错误");
    }

    @Test
    void testPatientSaveRequestFailsWhenNameEmpty() {
        PatientSaveRequest request = new PatientSaveRequest();
        request.setName("");

        var violations = validator.validate(request);
        assertFalse(violations.isEmpty(), "姓名为空时应校验失败");
    }
}
