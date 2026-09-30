package com.aiempowerment.platform.service;

import com.aiempowerment.platform.model.entity.ForumPost;
import org.springframework.data.domain.Page;

import java.util.List;
import java.util.Map;

public interface ForumService {
    // 帖子管理
    List<ForumPost> findAllPosts();
    ForumPost findPostById(Long id);
    ForumPost savePost(ForumPost post);
    void deletePost(Long id);
    List<ForumPost> findByCategory(String category);
    List<ForumPost> findByCategoryOrderByCreateTimeDesc(String category);
    List<ForumPost> searchByTitle(String keyword);
    List<ForumPost> findByAuthor(String author);

    // 帖子操作
    ForumPost createPost(ForumPost post);
    ForumPost updatePost(Long id, ForumPost post);
    ForumPost likePost(Long id);
    ForumPost incrementViewCount(Long id);

    // 统计
    Map<String, Object> getCategoryStats();

    // ==================== 分页查询 ====================

    /**
     * 分页查询帖子
     */
    Page<ForumPost> findPostsByPage(int page, int size, String category);

    /**
     * 按关键词搜索帖子
     */
    Page<ForumPost> searchPosts(String keyword, int page, int size);

    // ==================== AI智能分析 ====================

    /**
     * AI热门话题分析 - 基于点赞数、评论数、浏览量加权计算热门话题排行
     */
    List<Map<String, Object>> getHotTopics();

    /**
     * AI帖子推荐 - 基于分类和热度混合排序
     */
    List<Map<String, Object>> getRecommendations(Integer limit);

    /**
     * AI话题趋势 - 各分类帖子数量的时间趋势（按天统计最近30天）
     */
    List<Map<String, Object>> getTrends();

    /**
     * AI活跃分析 - 论坛活跃度统计
     */
    Map<String, Object> getActivityStats();
}
