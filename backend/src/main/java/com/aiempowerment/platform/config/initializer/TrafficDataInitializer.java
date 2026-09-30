package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.TrafficFlowRecord;
import com.aiempowerment.platform.model.entity.TrafficRoadSection;
import com.aiempowerment.platform.repository.TrafficFlowRecordRepository;
import com.aiempowerment.platform.repository.TrafficRoadSectionRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.CommandLineRunner;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;
import java.util.Random;

/**
 * 初始化 - 交通数据（路段、流量记录）
 */
@Slf4j
@Component
@Order(5)
@RequiredArgsConstructor
public class TrafficDataInitializer implements CommandLineRunner {

    private final TrafficRoadSectionRepository trafficRoadSectionRepository;
    private final TrafficFlowRecordRepository trafficFlowRepository;
    private final Random random = new Random(42);

    @Override
    public void run(String... args) {
        initTrafficData();
    }

    private void initTrafficData() {
        if (trafficRoadSectionRepository.count() > 0) return;
        List<TrafficRoadSection> sections = List.of(
            createSection("青年大街", "南湖公园-文化路", "主干道", 8.2, 8, 60),
            createSection("南北快速干道", "市府广场-北陵公园", "快速路", 12.5, 6, 80),
            createSection("浑南大道", "奥体中心-长青桥", "主干道", 6.8, 8, 60),
            createSection("文化路", "三好街-南湖公园", "主干道", 4.5, 6, 50),
            createSection("和平大街", "中山广场-太原街", "支路", 3.2, 4, 40),
            createSection("二环路", "全线", "快速路", 18.0, 6, 70),
            createSection("胜利大街", "沈阳站-南五马路", "主干道", 5.1, 6, 50),
            createSection("南京街", "中华路-砂阳路", "主干道", 4.8, 6, 50),
            createSection("三好街", "文艺路-南湖公园", "支路", 2.5, 4, 35),
            createSection("北陵大街", "北陵公园-泰山路", "主干道", 3.6, 6, 55),
            createSection("黄河大街", "皇姑区-北行", "主干道", 5.2, 6, 50),
            createSection("长青街", "长青桥-浑南", "快速路", 7.5, 6, 70),
            createSection("东西快速干道", "全线", "快速路", 15.0, 6, 75),
            createSection("五爱街", "五爱市场-文艺路", "支路", 2.8, 4, 35),
            createSection("富民街", "富民桥-浑南", "主干道", 4.2, 6, 50)
        );
        trafficRoadSectionRepository.saveAll(sections);

        // 流量数据 - 最近30天（批量保存）
        List<TrafficFlowRecord> allRecords = new ArrayList<>();
        for (TrafficRoadSection section : sections) {
            for (int day = 0; day < 30; day++) {
                for (int hour = 0; hour < 24; hour++) {
                    TrafficFlowRecord record = new TrafficFlowRecord();
                    record.setSectionId(section.getId());
                    // 早晚高峰车流量更大
                    int baseFlow;
                    if (hour >= 7 && hour <= 9) baseFlow = 5000 + random.nextInt(2000);
                    else if (hour >= 17 && hour <= 19) baseFlow = 6000 + random.nextInt(2000);
                    else if (hour >= 22 || hour <= 5) baseFlow = 500 + random.nextInt(500);
                    else baseFlow = 2000 + random.nextInt(2000);
                    // 周末流量变化
                    LocalDate date = LocalDate.now().minusDays(day);
                    boolean isWeekend = date.getDayOfWeek().getValue() >= 6;
                    if (isWeekend) {
                        if (hour >= 10 && hour <= 16) baseFlow = (int)(baseFlow * 1.2);
                        else if (hour >= 7 && hour <= 9) baseFlow = (int)(baseFlow * 0.5);
                        else baseFlow = (int)(baseFlow * 0.85);
                    }
                    record.setFlowCount(baseFlow);
                    double speed = Math.max(5, 20 + random.nextDouble() * 40);
                    // 流量越大速度越慢
                    if (baseFlow > 6000) speed = speed * 0.6;
                    else if (baseFlow > 4000) speed = speed * 0.8;
                    record.setAvgSpeed(speed);
                    record.setCongestionLevel(speed < 25 ? "严重" : speed < 35 ? "中度" : speed < 50 ? "轻度" : "畅通");
                    record.setAvgTravelTime(Math.max(2, 5 + random.nextDouble() * 15));
                    record.setRecordHour(hour);
                    record.setRecordDate(date);
                    allRecords.add(record);
                }
            }
        }
        trafficFlowRepository.saveAll(allRecords);

        log.info("✅ 已初始化交通数据: {} 个路段, {} 条流量记录", sections.size(), allRecords.size());
    }

    private TrafficRoadSection createSection(String name, String section, String type, double length, int lanes, int speed) {
        TrafficRoadSection s = new TrafficRoadSection();
        s.setRoadName(name);
        s.setSectionName(section);
        s.setRoadType(type);
        s.setLength(length);
        s.setLanes(lanes);
        s.setSpeedLimit(speed);
        s.setStartPoint(section.split("-")[0]);
        s.setEndPoint(section.contains("-") ? section.split("-")[1] : section);
        s.setStatus("畅通");
        return s;
    }
}