package com.aiempowerment.platform.service;

import com.aiempowerment.platform.config.AiModelClient;
import com.aiempowerment.platform.model.dto.AssistantChatRequest;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;

import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.*;

/**
 * 「豆芽」智能助手服务。
 *
 * 工作方式：
 * 1) 若配置了可用的大模型 API Key（DeepSeek），则携带「平台知识系统提示词 + 多轮历史」调用真实模型；
 * 2) 否则回退到内置知识库（关键词检索），保证在无 Key 环境下依然可用、可答疑。
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AssistantService {

    private final AiModelClient aiModelClient;
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 平台知识系统提示词 */
    private String systemPrompt = "";

    /** 内置知识库条目 */
    private List<Map<String, Object>> faq = new ArrayList<>();

    /** 推荐问题（前端快捷气泡） */
    private static final List<String> SUGGESTIONS = List.of(
            "这个平台是做什么的？",
            "血糖预测怎么用？",
            "CT 影像工作台能做什么？",
            "AI 智能问诊怎么用？",
            "金融风控有哪些功能？",
            "怎么登录平台？"
    );

    @jakarta.annotation.PostConstruct
    public void init() {
        try (InputStream in = new ClassPathResource("assistant/system-prompt.md").getInputStream()) {
            systemPrompt = new String(in.readAllBytes(), StandardCharsets.UTF_8);
        } catch (Exception e) {
            log.warn("AssistantService: 加载系统提示词失败: {}", e.getMessage());
            systemPrompt = "你是万象智枢平台的智能助手豆芽，用中文简洁回答用户关于平台的问题。";
        }
        try (InputStream in = new ClassPathResource("assistant/faq.json").getInputStream()) {
            faq = objectMapper.readValue(in, new TypeReference<List<Map<String, Object>>>() {});
        } catch (Exception e) {
            log.warn("AssistantService: 加载知识库失败: {}", e.getMessage());
        }
        log.info("AssistantService: 初始化完成，知识库 {} 条，AI Key 可用={}", faq.size(), aiModelClient.isAvailable());
    }

    public List<String> suggestions() {
        return SUGGESTIONS;
    }

    /** 聊天结果 */
    public record ChatResult(String reply, String mode) {}

    public ChatResult chat(String message, List<AssistantChatRequest.Message> history) {
        String msg = message == null ? "" : message.trim();
        if (msg.isEmpty()) {
            return new ChatResult("你想问点什么呢？可以说说你想了解哪个功能 🌱", "local");
        }

        // 1) 优先走真实大模型
        if (aiModelClient.isAvailable()) {
            List<Map<String, String>> messages = new ArrayList<>();
            if (history != null) {
                for (AssistantChatRequest.Message m : history) {
                    if (m == null || m.getContent() == null || m.getContent().isBlank()) continue;
                    String role = "assistant".equals(m.getRole()) ? "assistant" : "user";
                    messages.add(Map.of("role", role, "content", m.getContent()));
                }
            }
            messages.add(Map.of("role", "user", "content", msg));
            String reply = aiModelClient.callAsText(systemPrompt, messages);
            if (reply != null && !reply.isBlank()) {
                return new ChatResult(reply.trim(), "llm");
            }
            log.info("AssistantService: 大模型调用无结果，回退本地知识库");
        }

        // 2) 本地知识库回退
        return new ChatResult(localAnswer(msg), "local");
    }

    /** 本地知识库检索：按关键词命中数打分，取最高分；无命中时返回兜底指引。 */
    private String localAnswer(String msg) {
        String q = msg.toLowerCase(Locale.ROOT);
        int bestScore = 0;
        String best = null;
        for (Map<String, Object> entry : faq) {
            Object kwObj = entry.get("keywords");
            if (!(kwObj instanceof List<?> kws)) continue;
            int score = 0;
            for (Object k : kws) {
                String kw = String.valueOf(k).toLowerCase(Locale.ROOT);
                if (!kw.isBlank() && q.contains(kw)) {
                    // 关键词越长，匹配越具体，权重略高
                    score += Math.max(1, kw.length());
                }
            }
            if (score > bestScore) {
                bestScore = score;
                best = String.valueOf(entry.get("answer"));
            }
        }
        if (best != null && bestScore > 0) {
            return best;
        }
        return "这个问题我暂时没有现成的答案 🌱。你可以问我：平台整体介绍、五大场景（能源/环境/金融/医疗/交通）的功能、某个页面怎么操作，"
                + "或者「血糖预测怎么用」「CT 工作台能做什么」之类的问题。";
    }
}
