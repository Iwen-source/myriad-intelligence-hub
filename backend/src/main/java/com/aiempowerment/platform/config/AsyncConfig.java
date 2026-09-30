package com.aiempowerment.platform.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

/**
 * 异步执行配置 — AI分析等耗时操作使用独立线程池
 * <p>
 * 使用方法：在需要异步执行的方法上添加 @Async("aiAnalysisExecutor")
 */
@Configuration
@EnableAsync
public class AsyncConfig {

    @Bean("aiAnalysisExecutor")
    public Executor aiAnalysisExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        // 核心线程数：处理常规AI分析请求
        executor.setCorePoolSize(4);
        // 最大线程数：应对突发流量
        executor.setMaxPoolSize(8);
        // 队列容量：等待执行的任务数
        executor.setQueueCapacity(100);
        // 线程名前缀：便于日志追踪
        executor.setThreadNamePrefix("ai-analysis-");
        // 当线程池关闭时，等待任务完成（优雅关闭）
        executor.setWaitForTasksToCompleteOnShutdown(true);
        executor.setAwaitTerminationSeconds(30);
        executor.initialize();
        return executor;
    }
}