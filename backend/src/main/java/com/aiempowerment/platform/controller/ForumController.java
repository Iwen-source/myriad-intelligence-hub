package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.entity.ForumPost;
import com.aiempowerment.platform.service.ForumService;
import com.aiempowerment.platform.service.PythonMlClient;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.Page;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

import java.util.*;

/**
 * 论坛控制器 - AI应用场景模块
 * 🆕 V4: 新增NLP内容质量评分 + 情感分析 (真实ML模型)
 */
@Slf4j
@RestController
@RequestMapping("/forum")
@RequiredArgsConstructor
public class ForumController {

    private final ForumService forumService;
    private final PythonMlClient pythonMlClient;

    @GetMapping("/posts/{category}")
    public ApiResponse<?> getPostsByCategory(@PathVariable String category) {
        return ApiResponse.success(forumService.findByCategoryOrderByCreateTimeDesc(category));
    }

    @GetMapping("/posts/detail/{id}")
    public ApiResponse<?> getPostDetail(@PathVariable Long id) {
        forumService.incrementViewCount(id);
        return ApiResponse.success(forumService.findPostById(id));
    }

    @PostMapping("/posts")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> createPost(@RequestBody ForumPost post) {
        return ApiResponse.success(forumService.createPost(post));
    }

    @PutMapping("/posts/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> updatePost(@PathVariable Long id, @RequestBody ForumPost post) {
        return ApiResponse.success(forumService.updatePost(id, post));
    }

    @DeleteMapping("/posts/{id}")
    @PreAuthorize("hasRole('ADMIN')")
    public ApiResponse<?> deletePost(@PathVariable Long id) {
        forumService.deletePost(id);
        return ApiResponse.success("删除成功");
    }

    @PostMapping("/posts/{id}/like")
    public ApiResponse<?> likePost(@PathVariable Long id) {
        return ApiResponse.success(forumService.likePost(id));
    }

    @GetMapping("/stats")
    public ApiResponse<?> getStats() {
        return ApiResponse.success(forumService.getCategoryStats());
    }

    // ===== 分页查询 =====
    @GetMapping("/page")
    public ApiResponse<?> getPostsByPage(
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size,
            @RequestParam(required = false) String category) {
        return ApiResponse.success(forumService.findPostsByPage(page, size, category));
    }

    @GetMapping("/search")
    public ApiResponse<?> searchPosts(
            @RequestParam String keyword,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "10") int size) {
        return ApiResponse.success(forumService.searchPosts(keyword, page, size));
    }

    // ==================== AI智能分析端点 ====================

    @GetMapping("/analysis/hot-topics")
    public ApiResponse<?> getHotTopics() {
        return ApiResponse.success(forumService.getHotTopics());
    }

    @GetMapping("/analysis/recommendations")
    public ApiResponse<?> getRecommendations(@RequestParam(defaultValue = "6") Integer limit) {
        return ApiResponse.success(forumService.getRecommendations(limit));
    }

    @GetMapping("/analysis/trends")
    public ApiResponse<?> getTrends() {
        return ApiResponse.success(forumService.getTrends());
    }

    @GetMapping("/analysis/activity")
    public ApiResponse<?> getActivity() {
        return ApiResponse.success(forumService.getActivityStats());
    }

    // ===== 🆕 V4 AI增强: 内容质量评分 (真实NLP模型) =====
    @PostMapping("/analysis/quality-score")
    public ApiResponse<?> analyzeContentQuality(@RequestBody Map<String, String> request) {
        String title = request.getOrDefault("title", "");
        String body = request.getOrDefault("body", "");

        JsonNode result = pythonMlClient.forumAnalyzeContent(title, body);
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }

        // Fallback: heuristic scoring
        String fullText = title + " " + body;
        int wordCount = fullText.split("\\s+").length;
        boolean hasCode = fullText.contains("import") || fullText.contains("def ") || fullText.contains("class ");
        boolean hasQuestion = fullText.contains("?") || fullText.contains("？");
        double score = Math.min(10.0, Math.max(1.0, 3.0 + wordCount / 100.0 + (hasCode ? 1.5 : 0) + (hasQuestion ? 1 : 0)));

        Map<String, Object> fallback = new HashMap<>();
        fallback.put("quality_score", Math.round(score * 10.0) / 10.0);
        fallback.put("category", hasCode ? "技术讨论" : hasQuestion ? "项目求助" : "闲聊灌水");
        fallback.put("word_count", wordCount);
        return ApiResponse.success(fallback);
    }

    // ===== 🆕 V4 AI增强: 用户情感分析 =====
    @PostMapping("/analysis/sentiment")
    public ApiResponse<?> analyzeSentiment(@RequestBody Map<String, Object> request) {
        @SuppressWarnings("unchecked")
        Object textObj = request.get("text");
        List<String> texts = request.get("texts") instanceof List
                ? (List<String>) request.get("texts")
                : java.util.Collections.singletonList(textObj == null ? "" : textObj.toString());

        JsonNode result = pythonMlClient.forumSentimentAnalysis(texts);
        if (result != null && "success".equals(result.path("status").asText())) {
            return ApiResponse.success(result);
        }

        // Fallback
        Map<String, Object> fallback = new HashMap<>();
        List<Map<String, Object>> results = new ArrayList<>();
        for (String text : texts) {
            if (text == null) continue;
            Map<String, Object> item = new HashMap<>();
            item.put("text", text.length() > 100 ? text.substring(0, 100) : text);
            item.put("sentiment", "neutral");
            item.put("score", 0.5);
            results.add(item);
        }
        fallback.put("results", results);
        return ApiResponse.success(fallback);
    }
}
