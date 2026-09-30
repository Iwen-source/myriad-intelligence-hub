package com.aiempowerment.platform.websocket;

import com.aiempowerment.platform.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import java.util.Map;

/**
 * WebSocket 握手鉴权拦截器
 * <p>
 * 浏览器 WebSocket API 无法携带自定义 Header，因此 token 通过查询参数传递：?token=xxx。
 * 握手时校验 JWT，校验失败则拒绝建立连接。
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtHandshakeInterceptor implements HandshakeInterceptor {

    private final JwtTokenProvider jwtTokenProvider;

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                   WebSocketHandler wsHandler, Map<String, Object> attributes) {
        String token = null;
        if (request instanceof ServletServerHttpRequest servletRequest) {
            token = servletRequest.getServletRequest().getParameter("token");
        } else {
            // 兜底：从 URI 查询参数解析
            String query = request.getURI().getQuery();
            if (query != null) {
                for (String kv : query.split("&")) {
                    String[] parts = kv.split("=", 2);
                    if (parts.length == 2 && "token".equals(parts[0])) {
                        token = parts[1];
                    }
                }
            }
        }

        if (token == null || token.isBlank() || !jwtTokenProvider.validateToken(token)) {
            log.warn("[WebSocket] 握手被拒绝：缺少有效 token");
            return false;
        }

        String username = jwtTokenProvider.getUsernameFromToken(token);
        attributes.put("username", username);
        return true;
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                               WebSocketHandler wsHandler, Exception exception) {
        // no-op
    }
}
