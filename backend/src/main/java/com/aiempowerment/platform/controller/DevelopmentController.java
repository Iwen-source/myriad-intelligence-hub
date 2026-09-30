package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * AI发展概述控制器 - 仅保留 AI 分析接口（学习路径推荐、趋势分析、技能差距分析）
 */
@Slf4j
@RestController
@RequestMapping("/development")
@RequiredArgsConstructor
public class DevelopmentController {

    private final PythonMlClient pythonMlClient;

    // ===== AI增强: 个性化学习路径推荐 =====
    @PostMapping("/ai/recommend-path")
    public ApiResponse<?> recommendLearningPath(@RequestBody Map<String, Object> request) {
        @SuppressWarnings("unchecked")
        Map<String, Double> skillLevels = request.get("skill_levels") instanceof Map
                ? (Map<String, Double>) request.get("skill_levels") : new HashMap<>();

        JsonNode result = pythonMlClient.devRecommendLearningPath(skillLevels);
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }

        // Fallback recommendations
        List<Map<String, Object>> fallbackRecs = List.of(
                Map.of("path_name", "全栈开发工程师", "category", "开发", "difficulty", 3,
                       "duration_months", 6, "match_score", 75.0,
                       "skills_to_learn", List.of("Vue.js/React", "Docker", "CI/CD")),
                Map.of("path_name", "后端开发工程师", "category", "开发", "difficulty", 3,
                       "duration_months", 5, "match_score", 72.0,
                       "skills_to_learn", List.of("微服务", "Docker", "消息队列")),
                Map.of("path_name", "AI/ML 工程师", "category", "AI", "difficulty", 4,
                       "duration_months", 8, "match_score", 60.0,
                       "skills_to_learn", List.of("深度学习", "NLP", "MLOps"))
        );
        Map<String, Object> fallback = new HashMap<>();
        fallback.put("recommendations", fallbackRecs);
        fallback.put("user_skill_summary", Map.of("skills_provided", skillLevels.size()));
        return ApiResponse.success(fallback);
    }

    // ===== AI增强: 趋势分析 =====
    @GetMapping("/ai/trend-analysis")
    public ApiResponse<?> trendAnalysis() {
        JsonNode result = pythonMlClient.devTrendAnalysis();
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }
        Map<String, Object> fallback = new HashMap<>();
        fallback.put("categories", List.of("计算机视觉", "自然语言处理", "强化学习", "AI基础设施"));
        fallback.put("technology_stages", Map.of(0, "新兴", 1, "增长", 2, "成熟", 3, "前沿"));
        return ApiResponse.success(fallback);
    }

    // ===== AI增强: 技能差距分析 =====
    @PostMapping("/ai/skill-gap-analysis")
    public ApiResponse<?> analyzeSkillGap(@RequestBody Map<String, Object> request) {
        // 注意：Jackson 反序列化后的数值是 Integer/Long/Double，不能直接强转为 Map<String, Double>，
        // 否则取值时拆箱会抛 ClassCastException。统一按 Map<String, Object> 处理并用 Number 安全取值。
        @SuppressWarnings("unchecked")
        Map<String, Object> currentSkills = request.get("current_skills") instanceof Map
                ? (Map<String, Object>) request.get("current_skills") : new HashMap<>();
        String targetRole = request.getOrDefault("target_role", "全栈开发工程师").toString();

        Map<String, Object> result = new HashMap<>();
        result.put("target_role", targetRole);
        result.put("current_skills", currentSkills);

        List<Map<String, Object>> gaps = new ArrayList<>();
        Map<String, List<String>> roleRequirements = Map.of(
                "全栈开发工程师", List.of("Vue.js/React", "Node.js", "Spring Boot", "Docker", "数据库", "Git", "CI/CD"),
                "后端开发工程师", List.of("Java", "Spring Boot", "MySQL", "Redis", "微服务", "Docker", "Git"),
                "AI/ML 工程师", List.of("Python", "机器学习", "深度学习", "NLP", "PyTorch", "模型部署", "MLOps"),
                "数据科学家", List.of("Python", "SQL", "统计学", "数据可视化", "机器学习", "特征工程", "Spark"),
                "DevOps 工程师", List.of("Linux", "Docker", "Kubernetes", "CI/CD", "Terraform", "AWS/GCP", "监控系统")
        );

        List<String> required = roleRequirements.getOrDefault(targetRole, List.of());
        for (String skill : required) {
            Object rawLevel = currentSkills.get(skill);
            double currentLevel = rawLevel instanceof Number ? ((Number) rawLevel).doubleValue() : 0.0;
            if (currentLevel < 3.0) {
                Map<String, Object> gap = new HashMap<>();
                gap.put("skill", skill);
                gap.put("current_level", currentLevel);
                gap.put("target_level", 3.0);
                gap.put("gap", Math.max(0, 3.0 - currentLevel));
                gaps.add(gap);
            }
        }
        gaps.sort((a, b) -> Double.compare((Double) b.get("gap"), (Double) a.get("gap")));
        result.put("skill_gaps", gaps);
        result.put("total_gaps", gaps.size());
        result.put("mastery_percentage", required.isEmpty() ? 0 :
                Math.round((required.size() - gaps.size()) * 100.0 / required.size()));
        return ApiResponse.success(result);
    }
}
