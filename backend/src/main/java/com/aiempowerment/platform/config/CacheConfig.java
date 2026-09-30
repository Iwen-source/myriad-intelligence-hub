package com.aiempowerment.platform.config;

import org.springframework.cache.CacheManager;
import org.springframework.cache.annotation.EnableCaching;
import org.springframework.cache.concurrent.ConcurrentMapCache;
import org.springframework.cache.support.SimpleCacheManager;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.Primary;
import org.springframework.context.annotation.Profile;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;

import java.time.Duration;
import java.util.Set;

/**
 * 缓存配置 — 支持本地缓存（默认）和 Redis（启用 spring.profiles.active=redis）
 * <p>
 * 本地缓存：无需 Redis，适合开发测试
 * Redis 缓存：生产环境使用，需配置 spring.redis.* 属性
 * <p>
 * 使用方式：在方法上添加 @Cacheable(value = "cacheName", key = "#param")
 */
@Configuration
@EnableCaching
public class CacheConfig {

    /** 默认使用本地缓存（ConcurrentMap），无需额外依赖 */
    @Bean
    @Primary
    public CacheManager localCacheManager() {
        SimpleCacheManager cacheManager = new SimpleCacheManager();
        cacheManager.setCaches(Set.of(
            new ConcurrentMapCache("energyDevices"),
            new ConcurrentMapCache("energyConsumption"),
            new ConcurrentMapCache("envMonitorPoints"),
            new ConcurrentMapCache("airQualityRecords"),
            new ConcurrentMapCache("financeTransactions"),
            new ConcurrentMapCache("trafficSections"),
            new ConcurrentMapCache("trafficFlow"),
            new ConcurrentMapCache("forumPosts"),
            new ConcurrentMapCache("aiAnalysisResults")
        ));
        return cacheManager;
    }

    /** Redis 缓存管理器（profile=redis 时启用） */
    @Bean
    @Profile("redis")
    public CacheManager redisCacheManager(LettuceConnectionFactory connectionFactory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
            .entryTtl(Duration.ofMinutes(10))          // 默认10分钟过期
            .serializeValuesWith(
                RedisSerializationContext.SerializationPair
                    .fromSerializer(new GenericJackson2JsonRedisSerializer())
            )
            .disableCachingNullValues();                // 不缓存 null 值

        return RedisCacheManager.builder(connectionFactory)
            .cacheDefaults(config)
            .withCacheConfiguration("energyDevices",
                RedisCacheConfiguration.defaultCacheConfig().entryTtl(Duration.ofMinutes(5)))
            .withCacheConfiguration("aiAnalysisResults",
                RedisCacheConfiguration.defaultCacheConfig().entryTtl(Duration.ofMinutes(30)))
            .build();
    }
}