package com.aiempowerment.platform.model.dto;

import jakarta.validation.constraints.*;
import lombok.Data;

/**
 * AI问诊请求 DTO
 */
@Data
public class ConsultRequest {

    private String name;

    @Min(value = 0, message = "年龄不能为负")
    @Max(value = 150, message = "年龄不能超过150")
    private Integer age;

    private String gender;

    @NotBlank(message = "症状描述不能为空")
    @Size(min = 2, max = 2000, message = "症状描述长度需在2-2000字之间")
    private String symptoms;

    @Min(value = 0, message = "病程天数不能为负")
    private Integer durationDays;

    @Size(max = 2000, message = "既往病史描述不能超过2000字")
    private String history;

    @Size(max = 1000, message = "用药情况描述不能超过1000字")
    private String medications;
}
