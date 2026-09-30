package com.aiempowerment.platform.websocket;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

/**
 * WebSocket 告警推送处理器
 * <p>
 * 支持多种告警类型实时推送：
 * - DEVICE_ALERT: 设备异常告警
 * - TRANSACTION_ALERT: 交易风险预警
 * - ENV_ALERT: 环境超标告警
 * - SYSTEM_NOTIFICATION: 系统通知
 * <p>
 * 客户端连接：ws://localhost:8088/api/ws/alerts
 */
@Component
public class AlertWebSocketHandler extends TextWebSocketHandler {

    private static final Logger log = LoggerFactory.getLogger(AlertWebSocketHandler.class);

    /** 在线会话池 <sessionId, session> */
    private static final Map<String, WebSocketSession> sessions = new ConcurrentHashMap<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        sessions.put(session.getId(), session);
        log.info("[WebSocket] 新客户端连接: {}, 当前在线: {}", session.getId(), sessions.size());

        // 发送欢迎消息
        sendMessage(session, new AlertMessage("SYSTEM_NOTIFICATION", "WebSocket 连接成功",
            "已连接到 AI 赋能平台实时推送服务", System.currentTimeMillis()));
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) {
        // 客户端可发送心跳维持连接
        String payload = message.getPayload();
        if ("ping".equalsIgnoreCase(payload.trim())) {
            sendMessage(session, new AlertMessage("PONG", "pong", "心跳响应", System.currentTimeMillis()));
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        sessions.remove(session.getId());
        log.info("[WebSocket] 客户端断开: {}, 状态: {}, 当前在线: {}", session.getId(), status, sessions.size());
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) {
        log.error("[WebSocket] 传输错误: session={}, error={}", session.getId(), exception.getMessage());
        sessions.remove(session.getId());
    }

    /** 广播告警给所有连接的客户端 */
    public void broadcast(AlertMessage alert) {
        log.info("[WebSocket] 广播告警: type={}, title={}", alert.getType(), alert.getTitle());
        sessions.values().removeIf(session -> !session.isOpen());
        for (WebSocketSession session : sessions.values()) {
            sendMessage(session, alert);
        }
    }

    /** 获取当前在线客户端数 */
    public int getOnlineCount() {
        sessions.values().removeIf(s -> !s.isOpen());
        return sessions.size();
    }

    private void sendMessage(WebSocketSession session, AlertMessage alert) {
        try {
            if (session.isOpen()) {
                session.sendMessage(new TextMessage(alert.toJson()));
            }
        } catch (IOException e) {
            log.error("[WebSocket] 发送消息失败: session={}", session.getId());
        }
    }

    /** 告警消息体 */
    public static class AlertMessage {
        private String type;
        private String title;
        private String content;
        private long timestamp;

        public AlertMessage() {}

        public AlertMessage(String type, String title, String content, long timestamp) {
            this.type = type;
            this.title = title;
            this.content = content;
            this.timestamp = timestamp;
        }

        public String getType() { return type; }
        public void setType(String type) { this.type = type; }
        public String getTitle() { return title; }
        public void setTitle(String title) { this.title = title; }
        public String getContent() { return content; }
        public void setContent(String content) { this.content = content; }
        public long getTimestamp() { return timestamp; }
        public void setTimestamp(long timestamp) { this.timestamp = timestamp; }

        public String toJson() {
            return String.format(
                "{\"type\":\"%s\",\"title\":\"%s\",\"content\":\"%s\",\"timestamp\":%d}",
                type, escapeJson(title), escapeJson(content), timestamp
            );
        }

        private String escapeJson(String s) {
            if (s == null) return "";
            return s.replace("\\", "\\\\")
                    .replace("\"", "\\\"")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\t", "\\t");
        }
    }
}
