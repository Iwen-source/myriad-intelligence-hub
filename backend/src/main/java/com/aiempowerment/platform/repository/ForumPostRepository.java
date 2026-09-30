package com.aiempowerment.platform.repository;

import com.aiempowerment.platform.model.entity.ForumPost;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface ForumPostRepository extends JpaRepository<ForumPost, Long> {

    List<ForumPost> findByCategory(String category);

    Page<ForumPost> findByCategory(String category, Pageable pageable);

    Page<ForumPost> findByTitleContaining(String keyword, Pageable pageable);

    List<ForumPost> findByCategoryOrderByCreateTimeDesc(String category);

    List<ForumPost> findByTitleContaining(String keyword);

    List<ForumPost> findByAuthor(String author);

    long countByCategory(String category);
}
