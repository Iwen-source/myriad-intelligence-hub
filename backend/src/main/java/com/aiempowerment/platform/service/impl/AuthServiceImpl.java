package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.common.BusinessException;
import com.aiempowerment.platform.model.dto.LoginRequest;
import com.aiempowerment.platform.model.dto.RegisterRequest;
import com.aiempowerment.platform.model.entity.User;
import com.aiempowerment.platform.repository.UserRepository;
import com.aiempowerment.platform.security.JwtTokenProvider;
import com.aiempowerment.platform.service.AuthService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Service
@RequiredArgsConstructor
/**
 * AuthServiceImpl - 认证授权服务实现 - 用户注册登录与JWT令牌管理
 */
public class AuthServiceImpl implements AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;
    private final AuthenticationManager authenticationManager;

    private static final int MAX_LOGIN_ATTEMPTS = 5;
    private static final long LOGIN_LOCK_DURATION_MS = 5 * 60 * 1000L;
    private final Map<String, Integer> loginFailedCounts = new ConcurrentHashMap<>();
    private final Map<String, Long> loginLockedUntil = new ConcurrentHashMap<>();

    @Override
    public Map<String, Object> login(LoginRequest request) {
        String username = request.getUsername();

        // 登录失败锁定：防暴力破解
        Long lockedUntil = loginLockedUntil.get(username);
        if (lockedUntil != null && System.currentTimeMillis() < lockedUntil) {
            throw new BusinessException(429, "登录失败次数过多，请5分钟后再试");
        }

        // 先检查用户是否存在
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new BusinessException(401, "用户名或密码错误"));

        // 验证密码
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            recordLoginFailure(username);
            throw new BusinessException(401, "用户名或密码错误");
        }

        // Spring Security认证
        authenticationManager.authenticate(
                new UsernamePasswordAuthenticationToken(
                        username, request.getPassword()));

        // 登录成功，清除失败计数
        loginFailedCounts.remove(username);
        loginLockedUntil.remove(username);

        // 生成JWT Token（含角色）
        String token = jwtTokenProvider.generateToken(user.getUsername(), user.getRole());

        Map<String, Object> result = new HashMap<>();
        result.put("token", token);
        result.put("tokenType", "Bearer");
        result.put("user", user);
        return result;
    }

    private void recordLoginFailure(String username) {
        int fails = loginFailedCounts.merge(username, 1, Integer::sum);
        if (fails >= MAX_LOGIN_ATTEMPTS) {
            loginLockedUntil.put(username, System.currentTimeMillis() + LOGIN_LOCK_DURATION_MS);
            loginFailedCounts.remove(username);
        }
    }

    @Override
    @Transactional
    public User register(RegisterRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new BusinessException(409, "用户名已存在");
        }

        User user = new User();
        user.setUsername(request.getUsername());
        user.setPassword(passwordEncoder.encode(request.getPassword()));
        user.setNickname(request.getNickname() != null ? request.getNickname() : request.getUsername());
        user.setEmail(request.getEmail());
        // 普通用户角色（管理员由 UserDataInitializer 启动时创建，避免越权/竞态）
        user.setRole("USER");

        return userRepository.save(user);
    }

    @Override
    public User getCurrentUser(String username) {
        return userRepository.findByUsername(username)
                .orElseThrow(() -> new BusinessException(404, "用户不存在"));
    }
}

