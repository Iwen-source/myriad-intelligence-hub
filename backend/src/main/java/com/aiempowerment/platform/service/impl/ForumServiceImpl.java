package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.ForumPost;
import com.aiempowerment.platform.repository.ForumPostRepository;
import com.aiempowerment.platform.service.ForumService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
/**
 * ForumServiceImpl - 论坛互动服务实现 - 帖子、评论等社区功能管理
 */
public class ForumServiceImpl implements ForumService {

    private final ForumPostRepository forumPostRepository;

    // ==================== 帖子管理 ====================

    @Override
    public List<ForumPost> findAllPosts() {
        return forumPostRepository.findAll();
    }

    @Override
    public ForumPost findPostById(Long id) {
        return forumPostRepository.findById(id).orElse(null);
    }

    @Override
    @Transactional
    public ForumPost savePost(ForumPost post) {
        return forumPostRepository.save(post);
    }

    @Override
    @Transactional
    public void deletePost(Long id) {
        forumPostRepository.deleteById(id);
    }

    @Override
    public List<ForumPost> findByCategory(String category) {
        return forumPostRepository.findByCategory(category);
    }

    @Override
    public List<ForumPost> findByCategoryOrderByCreateTimeDesc(String category) {
        return forumPostRepository.findByCategoryOrderByCreateTimeDesc(category);
    }

    @Override
    public List<ForumPost> searchByTitle(String keyword) {
        return forumPostRepository.findByTitleContaining(keyword);
    }

    @Override
    public List<ForumPost> findByAuthor(String author) {
        return forumPostRepository.findByAuthor(author);
    }

    // ==================== 帖子操作 ====================

    @Override
    @Transactional
    public ForumPost createPost(ForumPost post) {
        post.setViewCount(post.getViewCount() != null ? post.getViewCount() : 0);
        post.setLikeCount(post.getLikeCount() != null ? post.getLikeCount() : 0);
        post.setCommentCount(post.getCommentCount() != null ? post.getCommentCount() : 0);
        post.setIsPinned(post.getIsPinned() != null ? post.getIsPinned() : false);
        return forumPostRepository.save(post);
    }

    @Override
    @Transactional
    public ForumPost updatePost(Long id, ForumPost post) {
        ForumPost existing = forumPostRepository.findById(id).orElse(null);
        if (existing != null) {
            if (post.getTitle() != null) existing.setTitle(post.getTitle());
            if (post.getContent() != null) existing.setContent(post.getContent());
            if (post.getCategory() != null) existing.setCategory(post.getCategory());
            if (post.getIsPinned() != null) existing.setIsPinned(post.getIsPinned());
            return forumPostRepository.save(existing);
        }
        return null;
    }

    @Override
    @Transactional
    public ForumPost likePost(Long id) {
        ForumPost post = forumPostRepository.findById(id).orElse(null);
        if (post != null) {
            post.setLikeCount(post.getLikeCount() == null ? 1 : post.getLikeCount() + 1);
            return forumPostRepository.save(post);
        }
        return null;
    }

    @Override
    @Transactional
    public ForumPost incrementViewCount(Long id) {
        ForumPost post = forumPostRepository.findById(id).orElse(null);
        if (post != null) {
            post.setViewCount(post.getViewCount() == null ? 1 : post.getViewCount() + 1);
            return forumPostRepository.save(post);
        }
        return null;
    }

    // ==================== 统计 ====================

    @Override
    public Map<String, Object> getCategoryStats() {
        List<ForumPost> allPosts = forumPostRepository.findAll();

        // 总帖子数
        int totalPosts = allPosts.size();

        // 按分类统计帖子数量
        Map<String, Long> categoryCount = allPosts.stream()
                .filter(p -> p.getCategory() != null)
                .collect(Collectors.groupingBy(
                        ForumPost::getCategory,
                        LinkedHashMap::new,
                        Collectors.counting()
                ));

        // 使用repository的countByCategory方法补充验证
        Map<String, Long> verifiedCategoryCount = new LinkedHashMap<>();
        for (String category : categoryCount.keySet()) {
            verifiedCategoryCount.put(category, forumPostRepository.countByCategory(category));
        }

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalPosts", totalPosts);
        result.put("categoryCount", verifiedCategoryCount);
        return result;
    }

    // ==================== 分页查询实现 ====================

    @Override
    public Page<ForumPost> findPostsByPage(int page, int size, String category) {
        Pageable pageable = PageRequest.of(page, size);
        if (category != null && !category.trim().isEmpty()) {
            return forumPostRepository.findByCategory(category, pageable);
        }
        return forumPostRepository.findAll(pageable);
    }

    @Override
    public Page<ForumPost> searchPosts(String keyword, int page, int size) {
        Pageable pageable = PageRequest.of(page, size);
        if (keyword != null && !keyword.trim().isEmpty()) {
            return forumPostRepository.findByTitleContaining(keyword, pageable);
        }
        return forumPostRepository.findAll(pageable);
    }

    // ==================== AI智能分析实现 ====================

    @Override
    public List<Map<String, Object>> getHotTopics() {
        List<ForumPost> allPosts = forumPostRepository.findAll();

        return allPosts.stream()
                .filter(p -> p.getLikeCount() != null || p.getCommentCount() != null || p.getViewCount() != null)
                .map(p -> {
                    Map<String, Object> item = new LinkedHashMap<>();
                    item.put("id", p.getId());
                    item.put("title", p.getTitle());
                    item.put("category", p.getCategory());
                    item.put("likes", p.getLikeCount() != null ? p.getLikeCount() : 0);
                    item.put("comments", p.getCommentCount() != null ? p.getCommentCount() : 0);
                    item.put("views", p.getViewCount() != null ? p.getViewCount() : 0);
                    // 热度分 = 点赞*3 + 评论*2 + 浏览*0.1
                    double score = (p.getLikeCount() != null ? p.getLikeCount() * 3 : 0)
                            + (p.getCommentCount() != null ? p.getCommentCount() * 2 : 0)
                            + (p.getViewCount() != null ? p.getViewCount() * 0.1 : 0);
                    item.put("score", Math.round(score * 10.0) / 10.0);
                    return item;
                })
                .sorted((a, b) -> Double.compare((Double) b.get("score"), (Double) a.get("score")))
                .limit(10)
                .collect(Collectors.toList());
    }

    @Override
    public List<Map<String, Object>> getRecommendations(Integer limit) {
        List<ForumPost> allPosts = forumPostRepository.findAll();

        // 按分类分组，每类取热度最高的前N个
        Map<String, List<ForumPost>> byCategory = allPosts.stream()
                .filter(p -> p.getCategory() != null)
                .collect(Collectors.groupingBy(ForumPost::getCategory));

        int perCategory = Math.max(1, (limit != null ? limit : 6) / Math.max(1, byCategory.size()));
        List<Map<String, Object>> result = new ArrayList<>();

        for (String category : new String[]{"ai", "tech", "project"}) {
            List<ForumPost> catPosts = byCategory.getOrDefault(category, Collections.emptyList());
            catPosts.sort((a, b) -> {
                double scoreA = (a.getLikeCount() != null ? a.getLikeCount() * 3 : 0)
                        + (a.getCommentCount() != null ? a.getCommentCount() * 2 : 0)
                        + (a.getViewCount() != null ? a.getViewCount() * 0.1 : 0);
                double scoreB = (b.getLikeCount() != null ? b.getLikeCount() * 3 : 0)
                        + (b.getCommentCount() != null ? b.getCommentCount() * 2 : 0)
                        + (b.getViewCount() != null ? b.getViewCount() * 0.1 : 0);
                return Double.compare(scoreB, scoreA);
            });

            for (int i = 0; i < Math.min(perCategory, catPosts.size()); i++) {
                ForumPost p = catPosts.get(i);
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("id", p.getId());
                item.put("title", p.getTitle());
                item.put("category", p.getCategory());
                item.put("content", p.getContent());
                item.put("likes", p.getLikeCount() != null ? p.getLikeCount() : 0);
                item.put("comments", p.getCommentCount() != null ? p.getCommentCount() : 0);
                item.put("views", p.getViewCount() != null ? p.getViewCount() : 0);
                double score = (p.getLikeCount() != null ? p.getLikeCount() * 3 : 0)
                        + (p.getCommentCount() != null ? p.getCommentCount() * 2 : 0)
                        + (p.getViewCount() != null ? p.getViewCount() * 0.1 : 0);
                item.put("score", Math.round(score * 10.0) / 10.0);
                result.add(item);
            }
        }

        // 按分数排序后取limit
        result.sort((a, b) -> Double.compare((Double) b.get("score"), (Double) a.get("score")));
        if (limit != null && limit < result.size()) {
            return result.subList(0, limit);
        }
        return result;
    }

    @Override
    public List<Map<String, Object>> getTrends() {
        List<ForumPost> allPosts = forumPostRepository.findAll();
        LocalDate today = LocalDate.now();
        LocalDate thirtyDaysAgo = today.minusDays(29);

        // 按日期+分类统计
        Map<String, Map<String, Long>> dateCategoryCount = new LinkedHashMap<>();
        for (int i = 0; i < 30; i++) {
            LocalDate date = thirtyDaysAgo.plusDays(i);
            dateCategoryCount.put(date.toString(), new LinkedHashMap<>());
        }

        for (ForumPost post : allPosts) {
            if (post.getCreateTime() == null) continue;
            LocalDate postDate = post.getCreateTime().toLocalDate();
            if (postDate.isBefore(thirtyDaysAgo) || postDate.isAfter(today)) continue;
            String dateKey = postDate.toString();
            String cat = post.getCategory() != null ? post.getCategory() : "unknown";
            dateCategoryCount.computeIfAbsent(dateKey, k -> new LinkedHashMap<>());
            dateCategoryCount.get(dateKey).merge(cat, 1L, Long::sum);
        }

        // 对没有帖子的日期也填充0
        List<Map<String, Object>> result = new ArrayList<>();
        for (Map.Entry<String, Map<String, Long>> entry : dateCategoryCount.entrySet()) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("date", entry.getKey());
            item.put("ai", entry.getValue().getOrDefault("ai", 0L));
            item.put("tech", entry.getValue().getOrDefault("tech", 0L));
            item.put("project", entry.getValue().getOrDefault("project", 0L));
            item.put("total", entry.getValue().values().stream().mapToLong(Long::longValue).sum());
            result.add(item);
        }

        return result;
    }

    @Override
    public Map<String, Object> getActivityStats() {
        List<ForumPost> allPosts = forumPostRepository.findAll();

        int totalPosts = allPosts.size();
        int totalLikes = allPosts.stream()
                .filter(p -> p.getLikeCount() != null)
                .mapToInt(ForumPost::getLikeCount)
                .sum();
        int totalComments = allPosts.stream()
                .filter(p -> p.getCommentCount() != null)
                .mapToInt(ForumPost::getCommentCount)
                .sum();
        int totalViews = allPosts.stream()
                .filter(p -> p.getViewCount() != null)
                .mapToInt(ForumPost::getViewCount)
                .sum();

        // 平均互动率 = (点赞+评论) / 浏览 * 100
        double interactionRate = totalViews > 0
                ? Math.round(((double) (totalLikes + totalComments) / totalViews) * 100.0 * 100.0) / 100.0
                : 0.0;

        // 日均发帖量（基于最近30天）
        LocalDateTime thirtyDaysAgo = LocalDateTime.now().minusDays(30);
        long recentPosts = allPosts.stream()
                .filter(p -> p.getCreateTime() != null && p.getCreateTime().isAfter(thirtyDaysAgo))
                .count();
        double dailyPosts = Math.round((double) recentPosts / 30.0 * 10.0) / 10.0;

        // 各分类活跃度
        Map<String, Long> categoryActive = allPosts.stream()
                .filter(p -> p.getCategory() != null)
                .collect(Collectors.groupingBy(ForumPost::getCategory, Collectors.counting()));

        // AI活跃指数（综合评分）
        double activityScore = Math.min(100, Math.round(
                (totalPosts * 0.3 + totalLikes * 0.1 + totalComments * 0.2 + totalViews * 0.01)
        ));

        Map<String, Object> result = new LinkedHashMap<>();
        result.put("totalPosts", totalPosts);
        result.put("totalLikes", totalLikes);
        result.put("totalComments", totalComments);
        result.put("totalViews", totalViews);
        result.put("interactionRate", interactionRate + "%");
        result.put("dailyPosts", dailyPosts);
        result.put("categoryActivity", categoryActive);
        result.put("activityScore", activityScore);

        return result;
    }
}