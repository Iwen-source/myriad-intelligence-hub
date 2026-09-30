package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.User;
import com.aiempowerment.platform.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

/**
 * 初始化 - 默认管理员用户
 */
@Slf4j
@Component
@Order(1)
@RequiredArgsConstructor
public class UserDataInitializer implements CommandLineRunner {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Override
    public void run(String... args) {
        initUsers();
    }

    private void initUsers() {
        // 仅在 admin 不存在时创建；已存在则绝不重置密码（避免改密后重启即失效）
        if (userRepository.findByUsername("admin").isEmpty()) {
            User admin = new User();
            admin.setUsername("admin");
            admin.setNickname("管理员");
            admin.setEmail("admin@aiempowerment.com");
            admin.setRole("ADMIN");
            String initPwd = System.getenv().getOrDefault("ADMIN_INIT_PASSWORD", "admin123456");
            admin.setPassword(passwordEncoder.encode(initPwd));
            userRepository.save(admin);
            log.info("已创建管理员账号 admin（初始口令来自环境变量 ADMIN_INIT_PASSWORD，请登录后立即修改）");
        }

        // 创建测试用户（如果不存在）
        if (userRepository.findByUsername("testuser").isEmpty()) {
            User testUser = new User();
            testUser.setUsername("testuser");
            testUser.setPassword(passwordEncoder.encode("test123"));
            testUser.setNickname("测试用户");
            testUser.setRole("USER");
            userRepository.save(testUser);
            log.info("已创建测试用户 testuser");
        }
    }
}
