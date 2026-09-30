package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.dto.LoginRequest;
import com.aiempowerment.platform.model.dto.RegisterRequest;
import com.aiempowerment.platform.model.entity.User;

import java.util.Map;

public interface AuthService {
    Map<String, Object> login(LoginRequest request);
    User register(RegisterRequest request);
    User getCurrentUser(String username);
}
