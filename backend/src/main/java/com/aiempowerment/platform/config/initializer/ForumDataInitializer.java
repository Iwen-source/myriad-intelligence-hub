package com.aiempowerment.platform.config.initializer;

import com.aiempowerment.platform.model.entity.ForumPost;
import com.aiempowerment.platform.repository.ForumPostRepository;
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
 * 初始化 - 论坛数据（帖子）
 */
@Slf4j
@Component
@Order(6)
@RequiredArgsConstructor
public class ForumDataInitializer implements CommandLineRunner {

    private final ForumPostRepository forumPostRepository;
    private final Random random = new Random(42);

    @Override
    public void run(String... args) {
        initForumData();
    }

    private void initForumData() {
        if (forumPostRepository.count() > 0) return;

        List<ForumPost> posts = new ArrayList<>();
        // AI/技术类帖子 (10篇)
        posts.add(createPost("ai", "Transformer架构优化实践", "本文分享Transformer架构的各种优化方法和技巧，包括注意力机制改进、位置编码优化等。欢迎讨论！", "admin", 420, 45, 18));
        posts.add(createPost("ai", "PyTorch图像分类实战指南", "分享基于PyTorch的图像分类项目实践经验，涵盖数据增强、模型选择、训练技巧等。", "admin", 380, 38, 15));
        posts.add(createPost("ai", "LSTM梯度消失解决方案", "请教LSTM训练中梯度消失的解决方案，已尝试梯度裁剪和权重初始化但仍未解决。", "alice", 156, 22, 8));
        posts.add(createPost("ai", "GPT-4多模态能力分析", "分享OpenAI发布的技术论文，分析其在多模态、推理能力等方面的突破。", "admin", 520, 62, 25));
        posts.add(createPost("ai", "RAG架构在企业知识库中的应用", "基于LangChain实现RAG系统，解决企业文档问答的实践经验，附代码示例。", "bob", 310, 35, 12));
        posts.add(createPost("ai", "LoRA微调实战：用少量数据定制LLM", "详细介绍LoRA低秩适配原理，以及在开源大模型上微调的完整流程。", "carol", 275, 29, 14));
        posts.add(createPost("ai", "强化学习在推荐系统的应用", "结合深度强化学习，探讨推荐系统长期收益优化的前沿方向。", "dave", 198, 18, 7));
        posts.add(createPost("ai", "语义搜索VS关键词搜索：效果对比", "对比ElasticSearch和向量数据库在语义搜索上的性能差异。", "eve", 230, 25, 11));
        posts.add(createPost("ai", "机器学习模型部署最佳实践", "从模型训练完成到生产环境部署，MLOps全流程指南。", "admin", 445, 52, 20));
        posts.add(createPost("ai", "Prompt Engineering高级技巧", "整理多种Prompt模式，包含思维链、少样本学习等高级技术。", "frank", 340, 41, 16));
        // 技术类 (10篇)
        posts.add(createPost("tech", "量子计算新范式探讨", "量子计算利用量子力学原理，能解决传统计算机难题。介绍基本原理、发展历程及应用前景。", "admin", 480, 42, 16));
        posts.add(createPost("tech", "元宇宙技术架构分析", "虚拟与现实交融的数字世界，分析技术架构、现状与挑战。", "admin", 320, 35, 13));
        posts.add(createPost("tech", "脑机接口技术革命", "大脑与设备直接通信，回顾发展历史，探讨伦理问题。", "admin", 450, 48, 22));
        posts.add(createPost("tech", "WebAssembly在浏览器端的性能革命", "WASM如何让C++/Rust代码在浏览器中接近原生性能运行。", "grace", 215, 20, 9));
        posts.add(createPost("tech", "分布式系统CAP理论的工程实践", "从理论到实践，讨论在微服务架构中如何权衡一致性、可用性和分区容忍性。", "admin", 365, 39, 17));
        posts.add(createPost("tech", "Kubernetes集群管理与优化", "大规模K8s集群的运维经验总结，包括节点调度、资源限制和监控告警。", "heidi", 280, 31, 12));
        posts.add(createPost("tech", "边缘计算与5G：实时AI推理", "5G+边缘计算架构如何进行低延迟AI推理，行业应用案例分析。", "ivan", 195, 17, 8));
        posts.add(createPost("tech", "编译原理入门：从AST到机器码", "用通俗易懂的方式讲解编译器的基本工作原理和各个阶段。", "judy", 160, 15, 6));
        posts.add(createPost("tech", "图数据库在社交网络中的应用", "Neo4j实战：用图数据库构建社交关系分析系统。", "karl", 185, 16, 7));
        posts.add(createPost("tech", "区块链共识算法详解", "PoW、PoS、DPoS、PBFT等主流共识算法的原理与对比分析。", "leo", 295, 28, 14));
        // 项目经验类 (10篇)
        posts.add(createPost("project", "AI智能客服系统项目", "基于大语言模型构建的智能客服系统，利用LangChain框架搭建RAG架构，实现知识库问答。", "admin", 550, 72, 28));
        posts.add(createPost("project", "智慧校园IoT平台", "基于Spring Boot + Vue的校园物联网管理平台，覆盖设备管理、数据采集和智能分析。", "admin", 380, 45, 18));
        posts.add(createPost("project", "实时数据管道搭建指南", "Kafka + Flink + ClickHouse构建实时数据管道，处理每秒百万级消息的实践经验。", "mallory", 310, 33, 15));
        posts.add(createPost("project", "微服务架构迁移经验分享", "从单体应用迁移到微服务架构的完整历程，包括服务拆分、数据一致性、服务治理。", "admin", 495, 58, 22));
        posts.add(createPost("project", "基于OpenCV的缺陷检测系统", "工业视觉检测：用传统图像处理和深度学习结合的缺陷识别方案。", "nia", 245, 22, 11));
        posts.add(createPost("project", "Docker容器化部署最佳实践", "编写高效Dockerfile、多阶段构建、镜像瘦身的实战经验总结。", "oliver", 265, 28, 13));
        posts.add(createPost("project", "移动端深度学习推理优化", "在iOS/Android上部署PyTorch/TensorFlow模型的性能优化技巧。", "peggy", 180, 19, 8));
        posts.add(createPost("project", "CI/CD流水线设计与实现", "GitLab CI + Jenkins + ArgoCD 构建从代码提交到生产部署的全自动流水线。", "quinn", 225, 26, 10));
        posts.add(createPost("project", "高并发秒杀系统设计", "从架构层面分析秒杀系统的设计要点，包括限流、降级、缓存、异步处理。", "admin", 400, 50, 20));
        posts.add(createPost("project", "Serverless架构实战指南", "AWS Lambda + API Gateway 构建无服务器应用，FaaS的优缺点分析。", "rachel", 195, 18, 7));

        forumPostRepository.saveAll(posts);
        log.info("✅ 已初始化论坛数据: {} 篇帖子", posts.size());
    }

    private ForumPost createPost(String category, String title, String content, String author,
                                  int views, int likes, int comments) {
        ForumPost post = new ForumPost();
        post.setCategory(category);
        post.setTitle(title);
        post.setContent(content);
        post.setAuthor(author);
        post.setViewCount(views);
        post.setLikeCount(likes);
        post.setCommentCount(comments);
        post.setIsPinned(false);
        post.setCreateTime(LocalDateTime.now().minusHours(random.nextInt(720)));
        return post;
    }
}