package com.aiempowerment.platform.service.impl;

import com.aiempowerment.platform.model.entity.ForumPost;
import com.aiempowerment.platform.repository.ForumPostRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.*;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ForumServiceImplTest {

    @Mock private ForumPostRepository postRepository;

    private ForumServiceImpl forumService;

    @BeforeEach
    void setUp() {
        forumService = new ForumServiceImpl(postRepository);
    }

    private ForumPost createPost(Long id, String title, String content, String category, String author, int views) {
        ForumPost p = new ForumPost();
        p.setId(id);
        p.setTitle(title);
        p.setContent(content);
        p.setCategory(category);
        p.setAuthor(author);
        p.setViewCount(views);
        p.setCreateTime(LocalDateTime.now());
        return p;
    }

    @Test
    @DisplayName("findAllPosts 应返回所有帖子")
    void findAllPosts() {
        when(postRepository.findAll()).thenReturn(List.of(
            createPost(1L, "帖子1", "内容1", "技术", "张三", 10),
            createPost(2L, "帖子2", "内容2", "闲聊", "李四", 5)
        ));
        assertEquals(2, forumService.findAllPosts().size());
    }

    @Test
    @DisplayName("findPostById 存在时返回帖子")
    void findPostByIdExists() {
        ForumPost post = createPost(1L, "帖子1", "内容", "分类", "张三", 10);
        when(postRepository.findById(1L)).thenReturn(Optional.of(post));
        assertNotNull(forumService.findPostById(1L));
    }

    @Test
    @DisplayName("findPostById 不存在时返回null")
    void findPostByIdNotExists() {
        when(postRepository.findById(999L)).thenReturn(Optional.empty());
        assertNull(forumService.findPostById(999L));
    }

    @Test
    @DisplayName("savePost 应保存并返回")
    void savePost() {
        ForumPost post = createPost(null, "新帖子", "新内容", "技术", "张三", 0);
        when(postRepository.save(any())).thenAnswer(inv -> {
            ForumPost saved = inv.getArgument(0);
            saved.setId(3L);
            return saved;
        });
        ForumPost result = forumService.savePost(post);
        assertNotNull(result);
        assertEquals(3L, result.getId());
    }

    @Test
    @DisplayName("findByCategory 应按分类过滤")
    void findByCategory() {
        when(postRepository.findByCategory("技术")).thenReturn(List.of(
            createPost(1L, "技术帖", "内容", "技术", "张三", 10)
        ));
        assertEquals(1, forumService.findByCategory("技术").size());
    }

    @Test
    @DisplayName("getHotTopics 应返回热度排行")
    void getHotTopics() {
        when(postRepository.findAll()).thenReturn(Arrays.asList(
            createPost(1L, "帖子A", "内容A", "技术", "张三", 200),
            createPost(2L, "帖子B", "内容B", "闲聊", "李四", 50),
            createPost(3L, "帖子C", "内容C", "技术", "王五", 100)
        ));
        List<Map<String, Object>> topics = forumService.getHotTopics();
        assertFalse(topics.isEmpty());
    }

    @Test
    @DisplayName("getCategoryStats 应返回分类统计")
    void getCategoryStats() {
        when(postRepository.findAll()).thenReturn(Arrays.asList(
            createPost(1L, "帖子A", "内容", "技术", "张三", 10),
            createPost(2L, "帖子B", "内容", "闲聊", "李四", 5),
            createPost(3L, "帖子C", "内容", "技术", "王五", 20)
        ));
        Map<String, Object> stats = forumService.getCategoryStats();
        assertNotNull(stats);
    }

    @Test
    @DisplayName("incrementViewCount 应增加浏览量")
    void incrementViewCount() {
        ForumPost post = createPost(1L, "帖子", "内容", "分类", "张三", 50);
        when(postRepository.findById(1L)).thenReturn(Optional.of(post));
        when(postRepository.save(any())).thenAnswer(inv -> inv.getArgument(0));

        forumService.incrementViewCount(1L);
        assertEquals(51, post.getViewCount());
        verify(postRepository).save(post);
    }
}
