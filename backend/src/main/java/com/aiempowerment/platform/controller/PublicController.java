package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import org.springframework.web.bind.annotation.*;

import java.security.SecureRandom;
import java.util.*;

/**
 * 公共数据控制器 - 不需要认证的公共接口
 */
@RestController
@RequestMapping("/public")
public class PublicController {

    /**
     * 网站导航信息 - 对应原项目的MainHomeFrame
     */
    @GetMapping("/navigation")
    public ApiResponse<?> getNavigation() {
        List<Map<String, Object>> modules = Arrays.asList(
                createModule("ai-development", "AI发展概述", "了解人工智能的发展历程、关键技术和先驱人物",
                        "/development/history", "el-icon-reading"),
                createModule("ai-scenarios", "AI应用场景", "探索AI在教育、能源、环境、金融、医疗等领域的应用",
                        "/scenarios", "el-icon-monitor"),
                createModule("ai-report", "AI分析报告", "基于AI的智能分析和预测报告",
                        "/energy/analysis/summary-report", "el-icon-data-analysis"),
                createModule("ai-finance", "金融风控", "交易风险评估、反欺诈检测和风险预警",
                        "/finance/risk-summary", "el-icon-coin"),
                createModule("tech-forum", "技术论坛", "与开发者交流AI算法、开发工具和前沿技术",
                        "/forum/posts/ai", "el-icon-chat-dot-round")
        );
        return ApiResponse.success(modules);
    }

    /**
     * 健康检查 — 用于 Docker healthcheck 和负载均衡探活
     */
    @GetMapping("/health")
    public ApiResponse<?> health() {
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("status", "UP");
        info.put("timestamp", java.time.LocalDateTime.now().toString());
        info.put("service", "ai-empowerment-platform");
        info.put("version", "1.0.0");
        return ApiResponse.success(info);
    }

    /**
     * 验证码生成
     */
    @GetMapping("/captcha")
    public ApiResponse<?> getCaptcha() {
        String captcha = generateCaptcha();
        Map<String, String> result = new HashMap<>();
        result.put("captcha", captcha);
        return ApiResponse.success(result);
    }

    private static final SecureRandom SECURE_RANDOM = new SecureRandom();

    private String generateCaptcha() {
        String chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 4; i++) {
            sb.append(chars.charAt(SECURE_RANDOM.nextInt(chars.length())));
        }
        return sb.toString();
    }

    private Map<String, Object> createModule(String key, String title, String description, String path, String icon) {
        Map<String, Object> item = new LinkedHashMap<>();
        item.put("key", key);
        item.put("title", title);
        item.put("description", description);
        item.put("path", path);
        item.put("icon", icon);
        return item;
    }
}
