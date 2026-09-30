package com.aiempowerment.platform.config;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 统一的 AI 大模型调用客户端
 *
 * 封装对 DeepSeek（或其他 OpenAI 兼容 API）的调用。
 * 如果 API Key 未配置或调用失败，返回 null，调用方应回退到模拟分析。
 */
@Slf4j
@Component
public class AiModelClient {

    /** 常见的占位符/示例值标记（小写匹配）。命中即视为「未配置真实 Key」。 */
    private static final String[] PLACEHOLDER_MARKERS = {
            "placeholder", "change_me", "your-deepseek", "your-key", "sk-your", "replace"
    };

    private final RestTemplate restTemplate = buildRestTemplate();
    private final ObjectMapper objectMapper = new ObjectMapper();

    /** 构造带超时的 RestTemplate，避免远程 API 不可达时请求无限挂起 */
    private static RestTemplate buildRestTemplate() {
        org.springframework.http.client.SimpleClientHttpRequestFactory factory =
                new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(30000);
        return new RestTemplate(factory);
    }

    @Value("${aimodel.api-url:https://api.deepseek.com/v1/chat/completions}")
    private String apiUrl;

    @Value("${aimodel.api-key:}")
    private String apiKey;

    @Value("${aimodel.model:deepseek-chat}")
    private String modelName;

    /** 检查是否有可用的 API Key（识别占位符/示例值，避免用无效 Key 发起真实调用） */
    public boolean isAvailable() {
        if (apiKey == null || apiKey.isBlank()) return false;
        String key = apiKey.trim().toLowerCase();
        for (String marker : PLACEHOLDER_MARKERS) {
            if (key.contains(marker)) return false;
        }
        return true;
    }

    /**
     * 调用 AI 模型，返回解析后的 JSON 响应
     *
     * @param systemPrompt 系统提示词
     * @param userMessage  用户消息
     * @return 解析后的 JSON 对象，调用失败或未配置时返回 null
     */
    public JsonNode call(String systemPrompt, String userMessage) {
        if (!isAvailable()) {
            log.info("AiModelClient: API Key 未配置，跳过真实 AI 调用");
            return null;
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);

            Map<String, Object> requestBody = new LinkedHashMap<>();
            requestBody.put("model", modelName);
            requestBody.put("messages", List.of(
                    Map.of("role", "system", "content", systemPrompt),
                    Map.of("role", "user", "content", userMessage)
            ));
            requestBody.put("temperature", 0.3);
            requestBody.put("max_tokens", 2048);

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
            String response = restTemplate.postForObject(apiUrl, request, String.class);
            if (response == null) {
                log.warn("AiModelClient: API 返回空响应");
                return null;
            }
            JsonNode root = objectMapper.readTree(response);
            return root.path("choices").get(0).path("message").path("content");
        } catch (Exception e) {
            log.warn("AiModelClient: API 调用失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 调用 AI 模型并解析为指定类型的 Map
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> callAsMap(String systemPrompt, String userMessage) {
        JsonNode node = call(systemPrompt, userMessage);
        if (node == null) return null;
        try {
            // DeepSeek 有时返回 JSON 字符串（TextNode），需要二次解析
            if (node.isTextual()) {
                String text = node.asText().trim();
                // 清理可能的 markdown 代码块标记
                if (text.startsWith("```json")) {
                    text = text.substring(7);
                    int end = text.lastIndexOf("```");
                    if (end > 0) text = text.substring(0, end);
                } else if (text.startsWith("```")) {
                    text = text.substring(3);
                    int end = text.lastIndexOf("```");
                    if (end > 0) text = text.substring(0, end);
                }
                return objectMapper.readValue(text.trim(), LinkedHashMap.class);
            }
            return objectMapper.convertValue(node, Map.class);
        } catch (Exception e) {
            log.warn("AiModelClient: JSON 解析失败: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 调用 AI 模型返回纯文本响应
     */
    public String callAsText(String systemPrompt, String userMessage) {
        JsonNode node = call(systemPrompt, userMessage);
        if (node == null) return null;
        return node.asText();
    }

    /**
     * 多轮对话：携带系统提示词 + 历史消息调用 AI 模型，返回纯文本响应。
     *
     * @param systemPrompt 系统提示词
     * @param history      历史消息（role=user/assistant, content），按时间正序；可为 null
     * @return 模型回复文本；未配置 Key 或调用失败时返回 null
     */
    public String callAsText(String systemPrompt, List<Map<String, String>> history) {
        if (!isAvailable()) {
            log.info("AiModelClient: API Key 未配置，跳过真实 AI 调用");
            return null;
        }
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            headers.setBearerAuth(apiKey);

            List<Map<String, String>> messages = new java.util.ArrayList<>();
            messages.add(Map.of("role", "system", "content", systemPrompt == null ? "" : systemPrompt));
            if (history != null) {
                for (Map<String, String> m : history) {
                    if (m == null) continue;
                    String role = m.getOrDefault("role", "user");
                    if (!"assistant".equals(role)) role = "user";
                    String content = m.getOrDefault("content", "");
                    if (content == null || content.isBlank()) continue;
                    messages.add(Map.of("role", role, "content", content));
                }
            }

            Map<String, Object> requestBody = new LinkedHashMap<>();
            requestBody.put("model", modelName);
            requestBody.put("messages", messages);
            requestBody.put("temperature", 0.4);
            requestBody.put("max_tokens", 1024);

            HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
            String response = restTemplate.postForObject(apiUrl, request, String.class);
            if (response == null) {
                log.warn("AiModelClient: API 返回空响应");
                return null;
            }
            JsonNode root = objectMapper.readTree(response);
            return root.path("choices").get(0).path("message").path("content").asText();
        } catch (Exception e) {
            log.warn("AiModelClient: API 调用失败: {}", e.getMessage());
            return null;
        }
    }
}
