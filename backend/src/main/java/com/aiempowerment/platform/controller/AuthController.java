package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.dto.LoginRequest;
import com.aiempowerment.platform.model.dto.RegisterRequest;
import com.aiempowerment.platform.service.AuthService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.security.Principal;

/**
 * 认证控制器 - 登录/注册
 */
@RestController
@RequestMapping("/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @PostMapping("/login")
    public ApiResponse<?> login(@Valid @RequestBody LoginRequest request) {
        return ApiResponse.success("登录成功", authService.login(request));
    }

    @PostMapping("/register")
    public ApiResponse<?> register(@Valid @RequestBody RegisterRequest request) {
        return ApiResponse.success("注册成功", authService.register(request));
    }

    @GetMapping("/me")
    public ApiResponse<?> getCurrentUser(Principal principal) {
        if (principal == null) {
            return ApiResponse.error(401, "未登录或登录已过期");
        }
        return ApiResponse.success(authService.getCurrentUser(principal.getName()));
    }
}
