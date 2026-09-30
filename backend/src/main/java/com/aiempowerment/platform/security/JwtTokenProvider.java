package com.aiempowerment.platform.security;

import io.jsonwebtoken.*;
import io.jsonwebtoken.io.Decoders;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.Date;

/**
 * JWT Token 提供者
 *
 * 支持两种密钥格式：
 * 1. Base64 编码的密钥（推荐）
 * 2. 明文密钥（自动做 SHA-256 派生）
 */
@Slf4j
@Component
public class JwtTokenProvider {

    private final SecretKey secretKey;
    private final long expiration;

    public JwtTokenProvider(
            @Value("${jwt.secret}") String secret,
            @Value("${jwt.expiration}") long expiration) {
        this.secretKey = deriveSecretKey(secret);
        this.expiration = expiration;
        log.info("JWT 密钥初始化完成（expiration={}ms）", expiration);
    }

    /**
     * 从配置的密钥派生 HMAC-SHA 密钥。
     * 自动检测密钥类型：Base64 格式（至少 32 字节解码后）或明文格式。
     */
    private SecretKey deriveSecretKey(String secret) {
        if (secret == null || secret.isBlank() || "DEV_PLACEHOLDER_CHANGE_ME_IN_PRODUCTION".equals(secret)) {
            log.warn("JWT Secret 未配置或仍为占位符，已生成随机密钥（仅用于开发，重启后令牌失效；生产环境必须设置 JWT_SECRET！）");
            byte[] randomKey = new byte[32];
            new SecureRandom().nextBytes(randomKey);
            return new SecretKeySpec(randomKey, "HmacSHA256");
        }

        // 尝试 Base64 解码
        try {
            byte[] decoded = Base64.getDecoder().decode(secret);
            if (decoded.length >= 32) {
                log.info("JWT 密钥使用 Base64 格式（{} 字节）", decoded.length);
                return Keys.hmacShaKeyFor(decoded);
            }
            // Base64 解码成功但太短，fallthrough 到明文处理
            log.warn("Base64 解码后密钥仅 {} 字节（需 ≥32），改用 SHA-256 派生", decoded.length);
        } catch (IllegalArgumentException e) {
            // 不是 Base64 格式，当作明文处理
            log.info("JWT 密钥使用明文格式，自动做 SHA-256 派生");
        }

        // 明文密钥：SHA-256 哈希派生为 32 字节
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(secret.getBytes(StandardCharsets.UTF_8));
            return new SecretKeySpec(hash, "HmacSHA256");
        } catch (Exception e) {
            throw new RuntimeException("JWT 密钥派生失败", e);
        }
    }

    /**
     * 生成JWT Token（含角色）
     */
    public String generateToken(String username, String role) {
        Date now = new Date();
        Date expiryDate = new Date(now.getTime() + expiration);

        return Jwts.builder()
                .subject(username)
                .claim("role", role)
                .issuedAt(now)
                .expiration(expiryDate)
                .signWith(secretKey)
                .compact();
    }

    /**
     * 从Token中提取角色
     */
    public String getRoleFromToken(String token) {
        try {
            return Jwts.parser()
                    .verifyWith(secretKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload()
                    .get("role", String.class);
        } catch (JwtException e) {
            return null;
        }
    }

    /**
     * 从Token中提取用户名
     */
    public String getUsernameFromToken(String token) {
        return Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token)
                .getPayload()
                .getSubject();
    }

    /**
     * 验证Token有效性
     */
    public boolean validateToken(String token) {
        try {
            Jwts.parser().verifyWith(secretKey).build().parseSignedClaims(token);
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            log.warn("JWT Token验证失败: {}", e.getMessage());
            return false;
        }
    }
}
