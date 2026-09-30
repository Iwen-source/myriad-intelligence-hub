package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.common.BusinessException;
import com.aiempowerment.platform.model.dto.LoginRequest;
import com.aiempowerment.platform.model.dto.RegisterRequest;
import com.aiempowerment.platform.model.entity.User;
import com.aiempowerment.platform.repository.UserRepository;
import com.aiempowerment.platform.security.JwtTokenProvider;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.crypto.password.PasswordEncoder;

import java.util.Map;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceImplTest {

    @Mock private UserRepository userRepository;
    @Mock private PasswordEncoder passwordEncoder;
    @Mock private JwtTokenProvider jwtTokenProvider;
    @Mock private AuthenticationManager authenticationManager;

    private AuthServiceImpl authService;

    @BeforeEach
    void setUp() {
        authService = new AuthServiceImpl(userRepository, passwordEncoder, jwtTokenProvider, authenticationManager);
    }

    private User createTestUser() {
        User user = new User();
        user.setId(1L);
        user.setUsername("testuser");
        user.setPassword("$2a$10$encodedpassword");
        user.setNickname("测试用户");
        user.setEmail("test@test.com");
        return user;
    }

    // ====== login ======

    @Test
    @DisplayName("登录成功应返回token和用户信息")
    void loginSuccess() {
        LoginRequest request = new LoginRequest();
        request.setUsername("testuser");
        request.setPassword("password123");

        User user = createTestUser();
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("password123", user.getPassword())).thenReturn(true);
        when(jwtTokenProvider.generateToken("testuser", "USER")).thenReturn("jwt-token-123");

        Map<String, Object> result = authService.login(request);

        assertNotNull(result);
        assertEquals("jwt-token-123", result.get("token"));
        assertEquals("Bearer", result.get("tokenType"));
        assertEquals(user, result.get("user"));
        verify(authenticationManager).authenticate(any());
    }

    @Test
    @DisplayName("登录时用户名不存在应抛异常")
    void loginUserNotFound() {
        LoginRequest request = new LoginRequest();
        request.setUsername("unknown");
        request.setPassword("password123");

        when(userRepository.findByUsername("unknown")).thenReturn(Optional.empty());

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.login(request));
        assertEquals("用户名或密码错误", ex.getMessage());
        verify(authenticationManager, never()).authenticate(any());
    }

    @Test
    @DisplayName("登录时密码错误应抛异常")
    void loginWrongPassword() {
        LoginRequest request = new LoginRequest();
        request.setUsername("testuser");
        request.setPassword("wrongpass");

        User user = createTestUser();
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(user));
        when(passwordEncoder.matches("wrongpass", user.getPassword())).thenReturn(false);

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.login(request));
        assertEquals("用户名或密码错误", ex.getMessage());
        verify(authenticationManager, never()).authenticate(any());
    }

    // ====== register ======

    @Test
    @DisplayName("注册成功应返回用户")
    void registerSuccess() {
        RegisterRequest request = new RegisterRequest();
        request.setUsername("newuser");
        request.setPassword("password123");
        request.setNickname("新用户");
        request.setEmail("new@test.com");

        User savedUser = new User();
        savedUser.setId(2L);
        savedUser.setUsername("newuser");
        savedUser.setPassword("$2a$10$encoded");
        savedUser.setNickname("新用户");
        savedUser.setEmail("new@test.com");

        when(userRepository.existsByUsername("newuser")).thenReturn(false);
        when(passwordEncoder.encode("password123")).thenReturn("$2a$10$encoded");
        when(userRepository.save(any(User.class))).thenReturn(savedUser);

        User result = authService.register(request);

        assertNotNull(result);
        assertEquals("newuser", result.getUsername());
        assertEquals("新用户", result.getNickname());
        verify(userRepository).save(any(User.class));
    }

    @Test
    @DisplayName("注册重复用户名应抛异常")
    void registerDuplicateUsername() {
        RegisterRequest request = new RegisterRequest();
        request.setUsername("existinguser");
        request.setPassword("password123");

        when(userRepository.existsByUsername("existinguser")).thenReturn(true);

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.register(request));
        assertEquals("用户名已存在", ex.getMessage());
        verify(userRepository, never()).save(any());
    }

    @Test
    @DisplayName("注册时未提供nickname应默认使用username")
    void registerDefaultNickname() {
        RegisterRequest request = new RegisterRequest();
        request.setUsername("nonickuser");
        request.setPassword("password123");

        when(userRepository.existsByUsername("nonickuser")).thenReturn(false);
        when(passwordEncoder.encode(anyString())).thenReturn("encoded");
        when(userRepository.save(any(User.class))).thenAnswer(invocation -> invocation.getArgument(0));

        User result = authService.register(request);

        assertEquals("nonickuser", result.getNickname());
    }

    // ====== getCurrentUser ======

    @Test
    @DisplayName("获取当前用户成功")
    void getCurrentUserSuccess() {
        User user = createTestUser();
        when(userRepository.findByUsername("testuser")).thenReturn(Optional.of(user));

        User result = authService.getCurrentUser("testuser");
        assertEquals("testuser", result.getUsername());
    }

    @Test
    @DisplayName("获取不存在的用户应抛异常")
    void getCurrentUserNotFound() {
        when(userRepository.findByUsername("ghost")).thenReturn(Optional.empty());

        BusinessException ex = assertThrows(BusinessException.class, () -> authService.getCurrentUser("ghost"));
        assertEquals("用户不存在", ex.getMessage());
    }
}
