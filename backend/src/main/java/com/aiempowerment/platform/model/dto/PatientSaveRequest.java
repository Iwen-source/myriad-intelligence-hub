package com.aiempowerment.platform.model.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

/**
 * 患者保存/更新请求 DTO
 */
@Data
public class PatientSaveRequest {

    private String patientId; // null 时为新增

    @NotBlank(message = "患者姓名不能为空")
    @Size(min = 1, max = 50, message = "姓名长度需在1-50字之间")
    private String name;

    private String gender;

    @Min(value = 0, message = "年龄不能为负")
    @Max(value = 150, message = "年龄不能超过150")
    private Integer age;

    @Size(max = 2000, message = "症状描述不能超过2000字")
    private String symptoms;

    private String checkStatus;

    @Size(max = 1000, message = "备注不能超过1000字")
    private String remark;
}
