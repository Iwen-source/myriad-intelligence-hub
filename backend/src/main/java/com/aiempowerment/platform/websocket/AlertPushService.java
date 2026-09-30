package com.aiempowerment.platform.websocket;

import com.aiempowerment.platform.websocket.AlertWebSocketHandler.AlertMessage;
import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.Random;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ThreadLocalRandom;
import java.util.concurrent.TimeUnit;

/**
 * WebSocket 告警推送服务
 * <p>
 * 支持：
 * 1. 启动后定时模拟推送各种告警（演示目的）
 * 2. 业务代码中手动调用推送方法
 */
@Service
public class AlertPushService {

    private static final Logger log = LoggerFactory.getLogger(AlertPushService.class);

    @Autowired
    private AlertWebSocketHandler alertWebSocketHandler;

    private ScheduledExecutorService scheduler;

    @PostConstruct
    public void init() {
        scheduler = Executors.newScheduledThreadPool(2, r -> {
            Thread t = new Thread(r, "alert-push-" + System.currentTimeMillis() % 10000);
            t.setDaemon(true);
            return t;
        });

        // 启动后60秒开始首次模拟告警，之后每次完成后延迟120-300秒再推送
        long initialDelay = 60000 + ThreadLocalRandom.current().nextInt(60000);
        scheduler.schedule(this::simulateRandomAlert, initialDelay, TimeUnit.MILLISECONDS);
    }

    @PreDestroy
    public void shutdown() {
        if (scheduler != null && !scheduler.isShutdown()) {
            scheduler.shutdown();
        }
    }

    /** 推送设备告警 */
    public void pushDeviceAlert(String deviceId, String deviceName, String severity, String message) {
        alertWebSocketHandler.broadcast(new AlertMessage(
            "DEVICE_ALERT",
            String.format("[%s] 设备告警: %s", severity, deviceName),
            message + " (设备: " + deviceId + ")",
            System.currentTimeMillis()
        ));
    }

    /** 推送交易风险预警 */
    public void pushTransactionAlert(String transactionNo, double riskScore, String riskLevel) {
        alertWebSocketHandler.broadcast(new AlertMessage(
            "TRANSACTION_ALERT",
            String.format("[风险%s] 交易预警", riskLevel),
            String.format("交易 %s 风险评分: %.1f", transactionNo, riskScore),
            System.currentTimeMillis()
        ));
    }

    /** 推送环境超标告警 */
    public void pushEnvironmentAlert(String pointName, String pollutant, double value, double threshold) {
        alertWebSocketHandler.broadcast(new AlertMessage(
            "ENV_ALERT",
            String.format("环境超标: %s - %s", pointName, pollutant),
            String.format("%s 监测值: %.1f (阈值: %.1f)", pollutant, value, threshold),
            System.currentTimeMillis()
        ));
    }

    /** 推送系统通知 */
    public void pushNotification(String title, String content) {
        alertWebSocketHandler.broadcast(new AlertMessage(
            "SYSTEM_NOTIFICATION", title, content, System.currentTimeMillis()
        ));
    }

    /** 模拟随机告警（演示/测试用） */
    private void simulateRandomAlert() {
        try {
            Random rnd = new Random();
            int type = rnd.nextInt(4);
            switch (type) {
                case 0 -> pushDeviceAlert(
                    "DEV-" + (100 + rnd.nextInt(900)),
                    new String[]{"光伏发电板A组", "风力发电机1号", "储能系统B", "中央空调"}[rnd.nextInt(4)],
                    new String[]{"低", "中", "高"}[rnd.nextInt(3)],
                    new String[]{"运行温度异常偏高", "振动幅度超出正常范围", "功率输出不稳定", "通信连接中断"}[rnd.nextInt(4)]
                );
                case 1 -> pushTransactionAlert(
                    "TXN" + LocalDateTime.now().toString().substring(0, 10).replace("-", "") + String.format("%04d", rnd.nextInt(9999)),
                    50 + rnd.nextDouble() * 50,
                    new String[]{"低", "中", "高"}[rnd.nextInt(3)]
                );
                case 2 -> pushEnvironmentAlert(
                    new String[]{"工业区监测站", "市中心监测站", "交通枢纽监测站"}[rnd.nextInt(3)],
                    new String[]{"PM2.5", "NO2", "O3"}[rnd.nextInt(3)],
                    80 + rnd.nextDouble() * 60,
                    100
                );
                default -> pushNotification(
                    "系统通知",
                    new String[]{"数据备份已完成", "模型训练任务完成", "系统资源使用率正常"}[rnd.nextInt(3)]
                );
            }
        } catch (Exception e) {
            log.warn("[AlertPush] 模拟告警失败: {}", e.getMessage());
        }

        // 安排下一次模拟（90-240秒后）
        long nextDelay = 90000 + ThreadLocalRandom.current().nextInt(150000);
        scheduler.schedule(this::simulateRandomAlert, nextDelay, TimeUnit.MILLISECONDS);
    }

    /** WebSocket 控制器端点：手动推送告警（用于测试或手动触发） */
    public void manualPush(String type, String title, String content) {
        alertWebSocketHandler.broadcast(new AlertMessage(type, title, content, System.currentTimeMillis()));
    }
}
