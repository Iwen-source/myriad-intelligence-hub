package com.aiempowerment.platform.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

/**
 * 注册请求DTO
 */
@Data
public class RegisterRequest {

    @NotBlank(message = "用户名不能为空")
    @Size(min = 2, max = 50, message = "用户名长度2-50个字符")
    private String username;

    @NotBlank(message = "密码不能为空")
    @Size(min = 4, max = 50, message = "密码长度4-50个字符")
    private String password;

    private String nickname;

    private String email;
}
