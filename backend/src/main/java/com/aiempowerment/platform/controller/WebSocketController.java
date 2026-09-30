package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.websocket.AlertPushService;
import com.aiempowerment.platform.websocket.AlertWebSocketHandler;
import lombok.RequiredArgsConstructor;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

/**
 * WebSocket 管理控制器
 * <p>
 * 提供手动推送告警和管理 WebSocket 连接的 REST 接口
 */
@RestController
@RequestMapping("/ws")
@RequiredArgsConstructor
public class WebSocketController {

    private final AlertPushService alertPushService;
    private final AlertWebSocketHandler alertWebSocketHandler;

    /** 获取 WebSocket 在线统计 */
    @GetMapping("/status")
    public ApiResponse<?> status() {
        return ApiResponse.success(Map.of(
            "onlineCount", alertWebSocketHandler.getOnlineCount(),
            "service", "WebSocket Alert Push Service",
            "endpoint", "ws://localhost:8088/api/ws/alerts"
        ));
    }

    /** 手动推送告警（管理员） */
    @PostMapping("/push")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> pushAlert(@RequestBody Map<String, String> request) {
        String type = request.getOrDefault("type", "SYSTEM_NOTIFICATION");
        String title = request.getOrDefault("title", "手动推送");
        String content = request.getOrDefault("content", "管理员手动推送的通知");
        alertPushService.manualPush(type, title, content);
        return ApiResponse.success(Map.of(
            "pushed", true,
            "type", type,
            "title", title
        ));
    }

    /** 模拟推送设备告警（管理员） */
    @PostMapping("/simulate/device-alert")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> simulateDeviceAlert(@RequestBody Map<String, String> request) {
        alertPushService.pushDeviceAlert(
            request.getOrDefault("deviceId", "DEV-001"),
            request.getOrDefault("deviceName", "测试设备"),
            request.getOrDefault("severity", "低"),
            request.getOrDefault("message", "模拟设备告警")
        );
        return ApiResponse.success(Map.of("pushed", true, "type", "DEVICE_ALERT"));
    }

    /** 模拟推送交易预警（管理员） */
    @PostMapping("/simulate/transaction-alert")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> simulateTransactionAlert(@RequestBody Map<String, String> request) {
        alertPushService.pushTransactionAlert(
            request.getOrDefault("transactionNo", "TXN-test"),
            parseDoubleOrDefault(request.get("riskScore"), 85.5),
            request.getOrDefault("riskLevel", "高")
        );
        return ApiResponse.success(Map.of("pushed", true, "type", "TRANSACTION_ALERT"));
    }

    /** 安全解析数值：非法/缺失时回退默认值，避免非法输入触发 500 */
    private static double parseDoubleOrDefault(String value, double fallback) {
        if (value == null || value.isBlank()) {
            return fallback;
        }
        try {
            return Double.parseDouble(value.trim());
        } catch (NumberFormatException e) {
            return fallback;
        }
    }
}
