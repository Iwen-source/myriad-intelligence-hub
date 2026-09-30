package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.AirQualityRecord;
import com.aiempowerment.platform.model.entity.EnvironmentMonitorPoint;
import com.aiempowerment.platform.repository.AirQualityRecordRepository;
import com.aiempowerment.platform.repository.EnvironmentMonitorPointRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * 初始化 - 环境监测数据（监测点、空气质量记录）
 */
@Slf4j
@Component
@Order(3)
@RequiredArgsConstructor
public class EnvironmentDataInitializer implements CommandLineRunner {

    private final EnvironmentMonitorPointRepository envPointRepository;
    private final AirQualityRecordRepository airQualityRepository;
    private final Random random = new Random(42);

    @Override
    public void run(String... args) {
        initEnvironmentData();
    }

    private void initEnvironmentData() {
        if (envPointRepository.count() > 0) return;
        String[] pointNames = {
            "市中心监测站", "工业区监测站", "居民区监测站", "公园监测站", "交通枢纽监测站",
            "开发区监测站", "大学城监测站", "滨河湿地站", "商业中心站", "物流园区站",
            "科技园区站", "体育中心站", "高铁站前站", "森林公园站", "港口监测站"
        };
        String[] locations = {
            "市中心解放路", "城北工业园", "城南居民区", "中央公园", "高铁站前",
            "高新区科技路", "大学城学府路", "浑河沿岸", "太原街商业区", "浑南物流园",
            "浑南科技城", "奥体中心", "沈阳南站", "国家森林公园", "营口港办事处"
        };
        String[] types = {
            "空气质量", "空气质量", "空气质量", "水质/空气质量", "噪声/空气质量",
            "空气质量", "空气质量", "水质", "噪声/空气质量", "空气质量",
            "空气质量", "空气质量", "噪声/空气质量", "空气质量", "空气质量/水质"
        };

        List<EnvironmentMonitorPoint> pointList = new ArrayList<>();
        for (int i = 0; i < pointNames.length; i++) {
            EnvironmentMonitorPoint p = new EnvironmentMonitorPoint();
            p.setPointName(pointNames[i]);
            p.setLocation(locations[i]);
            p.setLongitude(123.3 + random.nextDouble() * 0.3);
            p.setLatitude(41.7 + random.nextDouble() * 0.15);
            p.setMonitorType(types[i]);
            p.setStatus(i < 10 ? "正常" : (i < 13 ? "正常" : "维护中"));
            pointList.add(p);
        }
        envPointRepository.saveAll(pointList);

        // 为每个监测点生成最近 7 天每小时的数据
        List<AirQualityRecord> allRecords = new ArrayList<>();
        for (EnvironmentMonitorPoint point : pointList) {
            long pointId = point.getId();
            for (int day = 0; day < 7; day++) {
                for (int h = 0; h < 24; h++) {
                    AirQualityRecord record = new AirQualityRecord();
                    record.setPointId(pointId);
                    // 早晚高峰 AQI 偏高，夜间偏低
                    double hourFactor = 1.0;
                    if (h >= 8 && h <= 10) hourFactor = 1.3;
                    else if (h >= 17 && h <= 19) hourFactor = 1.4;
                    else if (h >= 23 || h <= 4) hourFactor = 0.7;
                    record.setAqi((int) Math.round((30 + random.nextDouble() * 150) * hourFactor));
                    record.setPm25((10 + random.nextDouble() * 100) * hourFactor);
                    record.setPm10((20 + random.nextDouble() * 150) * hourFactor);
                    record.setO3(5 + random.nextDouble() * 50);
                    record.setNo2((10 + random.nextDouble() * 40) * hourFactor);
                    record.setSo2((2 + random.nextDouble() * 20) * hourFactor);
                    record.setCo((0.1 + random.nextDouble() * 1.5) * hourFactor);
                    record.setTemperature(15 + random.nextDouble() * 20);
                    record.setHumidity(30 + random.nextDouble() * 60);
                    record.setRecordTime(LocalDateTime.now().minusDays(day).minusHours(h));
                    allRecords.add(record);
                }
            }
        }
        airQualityRepository.saveAll(allRecords);

        log.info("✅ 已初始化环境监测数据: {} 个监测点, {} 条空气质量记录",
            pointNames.length, allRecords.size());
    }
}