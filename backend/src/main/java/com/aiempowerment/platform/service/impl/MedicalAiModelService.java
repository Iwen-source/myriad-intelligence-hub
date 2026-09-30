package com.aiempowerment.platform.service.impl;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;
import lombok.extern.slf4j.Slf4j;

import java.time.LocalDate;
import java.util.*;

@Service
@Slf4j
public class MedicalAiModelService {

    @Value("${aimodel.api-url:https://api.deepseek.com/v1/chat/completions}")
    private String apiUrl;

    @Value("${aimodel.api-key:}")
    private String apiKey;

    @Value("${aimodel.model:deepseek-chat}")
    private String modelName;

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

    /** 判断是否配置了可用的真实 API Key（识别占位符/示例值） */
    private boolean isApiKeyConfigured() {
        if (apiKey == null || apiKey.isBlank()) return false;
        String key = apiKey.trim().toLowerCase();
        for (String marker : PLACEHOLDER_MARKERS) {
            if (key.contains(marker)) return false;
        }
        return true;
    }

    /**
     * AI问诊 — 使用大模型进行真正的AI诊断
     */
    public Map<String, Object> consult(String patientName, Integer age, String gender,
                                        String symptoms, Integer durationDays,
                                        String history, String medications) {
        // Build the system prompt (professional medical diagnosis role)
        String systemPrompt = buildSystemPrompt();
        // Build the user message with patient info
        String userMessage = buildUserMessage(patientName, age, gender, symptoms, durationDays, history, medications);

        // Call API
        try {
            String response = callAiApi(systemPrompt, userMessage);
            return parseResponse(response, patientName, symptoms);
        } catch (Exception e) {
            log.error("AI model API call failed: {}", e.getMessage());
            return buildFallbackResponse(patientName, symptoms, e.getMessage());
        }
    }

    private String buildSystemPrompt() {
        return "你是豆芽诊所的一名资深全科医生，名叫\"豆芽医生\"。你的工作是根据患者描述的症状进行初步诊断。" +
               "你擅长分析病因、判断严重程度、推荐非处方药、提供护理建议和就医指导。\n\n" +
               "【工作规则】\n" +
               "1. 只做初步诊断分析，不做绝对确诊\n" +
               "2. 只推荐非处方常用药（OTC），不推荐处方药\n" +
               "3. 危急情况（胸痛持续15分钟以上、大出血、呼吸困难、意识模糊等）必须明确提醒立即就医\n" +
               "4. 语言简洁通俗，少用专业术语\n" +
               "5. 回答必须有清晰的五步结构\n\n" +
               "【必须输出的JSON格式】\n" +
               "请严格按照以下JSON格式回复（不要包含markdown标记）：\n" +
               "{\n" +
               "  \"analysis\": {\n" +
               "    \"possibleDiseases\": [{\"name\": \"疾病名称\", \"probability\": \"高/中/低\", \"reason\": \"判断依据\"}],\n" +
               "    \"analysis\": \"病因综合分析\"\n" +
               "  },\n" +
               "  \"severity\": {\n" +
               "    \"level\": \"轻/中/重/紧急\",\n" +
               "    \"description\": \"严重程度解释\"\n" +
               "  },\n" +
               "  \"medications\": [\n" +
               "    {\"name\": \"药品名\", \"usage\": \"用法用量\", \"note\": \"注意事项\"}\n" +
               "  ],\n" +
               "  \"care\": {\n" +
               "    \"diet\": \"饮食建议\",\n" +
               "    \"rest\": \"作息建议\",\n" +
               "    \"nursing\": \"护理建议\"\n" +
               "  },\n" +
               "  \"whenToSeeDoctor\": \"就医指征和时间\",\n" +
               "  \"summary\": \"诊断总结（100字以内）\"\n" +
               "}";
    }

    private String buildUserMessage(String name, Integer age, String gender,
                                     String symptoms, Integer durationDays,
                                     String history, String medications) {
        StringBuilder sb = new StringBuilder();
        sb.append("【患者信息】\n");
        if (name != null && !name.isEmpty()) sb.append("姓名：").append(name).append("\n");
        if (age != null) sb.append("年龄：").append(age).append("岁\n");
        if (gender != null && !gender.isEmpty()) sb.append("性别：").append(gender).append("\n");
        sb.append("【症状描述】").append(symptoms != null ? symptoms : "未提供").append("\n");
        if (durationDays != null) sb.append("【病程】约").append(durationDays).append("天\n");
        if (history != null && !history.isEmpty()) sb.append("【既往病史】").append(history).append("\n");
        if (medications != null && !medications.isEmpty()) sb.append("【已用药物】").append(medications).append("\n");
        return sb.toString();
    }

    private String callAiApi(String systemPrompt, String userMessage) throws Exception {
        // If no API key configured, use fallback
        if (!isApiKeyConfigured()) {
            log.warn("AI model API key not configured, using fallback diagnosis");
            throw new RuntimeException("API key not configured");
        }

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
        requestBody.put("response_format", Map.of("type", "json_object"));

        HttpEntity<Map<String, Object>> request = new HttpEntity<>(requestBody, headers);
        String response = restTemplate.postForObject(apiUrl, request, String.class);
        if (response == null) throw new RuntimeException("Empty response from API");

        JsonNode root = objectMapper.readTree(response);
        String content = root.path("choices").get(0).path("message").path("content").asText();
        return content;
    }

    private Map<String, Object> parseResponse(String jsonContent, String patientName, String symptoms) {
        try {
            JsonNode root = objectMapper.readTree(jsonContent);
            Map<String, Object> result = new LinkedHashMap<>();

            result.put("patientName", patientName != null ? patientName : "未知");
            result.put("symptoms", symptoms);
            result.put("consultTime", LocalDate.now().toString());
            result.put("disclaimer", "⚠️ 本诊断结果由AI辅助生成，仅供参考。请以线下医生的专业诊断为准。如症状严重，请立即就医。");
            // 统一 AI 来源标注：本路径为远程大模型（DeepSeek）真实推理
            result.put("isMlGenerated", true);
            result.put("source", "deepseek-llm");

            // Analysis
            if (root.has("analysis")) {
                JsonNode analysis = root.get("analysis");
                result.put("possibleDiseases", analysis.has("possibleDiseases") ?
                    objectMapper.convertValue(analysis.get("possibleDiseases"), List.class) : List.of());
                result.put("analysisText", analysis.has("analysis") ?
                    analysis.get("analysis").asText() : "");
            }

            // Severity
            if (root.has("severity")) {
                result.put("severity", root.get("severity"));
            }

            // Medications
            if (root.has("medications")) {
                result.put("medications", objectMapper.convertValue(root.get("medications"), List.class));
            }

            // Care
            if (root.has("care")) {
                result.put("care", objectMapper.convertValue(root.get("care"), Map.class));
            }

            // When to see doctor
            if (root.has("whenToSeeDoctor")) {
                result.put("whenToSeeDoctor", root.get("whenToSeeDoctor").asText());
            }

            // Summary
            if (root.has("summary")) {
                result.put("summary", root.get("summary").asText());
            }

            return result;

        } catch (Exception e) {
            log.error("Failed to parse AI response JSON: {}", e.getMessage());
            return buildFallbackResponse(patientName, symptoms, "解析AI响应失败");
        }
    }

    /**
     * 智能本地回退诊断 — 基于症状关键词的规则引擎匹配
     * 当远程AI模型不可用时，使用内置医学知识库生成有意义的诊断
     */
    private Map<String, Object> buildFallbackResponse(String patientName, String symptoms, String reason) {
        log.info("Using local fallback diagnosis engine (reason: {})", reason);

        // Symptom → Disease keyword map (aligned with MedicalAiDoctorService knowledge)
        Map<String, String[]> symptomDiseaseMap = Map.ofEntries(
            Map.entry("发热", new String[]{"上呼吸道感染", "流行性感冒"}),
            Map.entry("咳嗽", new String[]{"急性支气管炎", "上呼吸道感染"}),
            Map.entry("咳痰", new String[]{"急性支气管炎", "肺炎"}),
            Map.entry("流鼻涕", new String[]{"上呼吸道感染", "过敏性鼻炎"}),
            Map.entry("打喷嚏", new String[]{"过敏性鼻炎", "上呼吸道感染"}),
            Map.entry("鼻塞", new String[]{"上呼吸道感染", "过敏性鼻炎"}),
            Map.entry("咽喉痛", new String[]{"上呼吸道感染"}),
            Map.entry("头痛", new String[]{"偏头痛", "原发性高血压"}),
            Map.entry("头晕", new String[]{"脑供血不足", "原发性高血压"}),
            Map.entry("胸痛", new String[]{"冠心病", "肺炎"}),
            Map.entry("胸闷", new String[]{"冠心病", "焦虑症"}),
            Map.entry("心悸", new String[]{"甲状腺功能亢进症", "焦虑症"}),
            Map.entry("腹痛", new String[]{"急性胃肠炎", "胃溃疡"}),
            Map.entry("腹泻", new String[]{"急性胃肠炎"}),
            Map.entry("恶心", new String[]{"急性胃肠炎", "慢性胃炎"}),
            Map.entry("呕吐", new String[]{"急性胃肠炎"}),
            Map.entry("胃痛", new String[]{"胃溃疡", "慢性胃炎"}),
            Map.entry("反酸", new String[]{"慢性胃炎", "胃溃疡"}),
            Map.entry("多饮", new String[]{"2型糖尿病"}),
            Map.entry("多尿", new String[]{"2型糖尿病"}),
            Map.entry("体重下降", new String[]{"甲状腺功能亢进症", "2型糖尿病"}),
            Map.entry("怕热", new String[]{"甲状腺功能亢进症"}),
            Map.entry("手抖", new String[]{"甲状腺功能亢进症", "焦虑症"}),
            Map.entry("失眠", new String[]{"焦虑症"}),
            Map.entry("焦虑", new String[]{"广泛性焦虑障碍"}),
            Map.entry("皮疹", new String[]{"湿疹", "过敏性皮炎"}),
            Map.entry("瘙痒", new String[]{"湿疹"}),
            Map.entry("颈痛", new String[]{"颈椎病"}),
            Map.entry("腰痛", new String[]{"腰椎间盘突出症"}),
            Map.entry("腿麻", new String[]{"腰椎间盘突出症"}),
            Map.entry("尿频", new String[]{"尿路感染"}),
            Map.entry("尿急", new String[]{"尿路感染"}),
            Map.entry("尿痛", new String[]{"尿路感染"}),
            Map.entry("乏力", new String[]{"流行性感冒", "脑供血不足"}),
            Map.entry("记忆力减退", new String[]{"脑供血不足", "焦虑症"})
        );

        // Disease severity map
        Map<String, String> diseaseSeverity = Map.ofEntries(
            Map.entry("上呼吸道感染", "轻"), Map.entry("流行性感冒", "中"),
            Map.entry("急性支气管炎", "中"), Map.entry("肺炎", "重"),
            Map.entry("原发性高血压", "中"), Map.entry("冠心病", "重"),
            Map.entry("偏头痛", "中"), Map.entry("脑供血不足", "中"),
            Map.entry("急性胃肠炎", "轻"), Map.entry("慢性胃炎", "中"),
            Map.entry("胃溃疡", "重"), Map.entry("2型糖尿病", "中"),
            Map.entry("甲状腺功能亢进症", "中"), Map.entry("焦虑症", "中"),
            Map.entry("广泛性焦虑障碍", "中"), Map.entry("湿疹", "轻"),
            Map.entry("尿路感染", "中"), Map.entry("颈椎病", "中"),
            Map.entry("腰椎间盘突出症", "中"), Map.entry("过敏性鼻炎", "轻"),
            Map.entry("过敏性皮炎", "轻"), Map.entry("支气管炎", "中")
        );

        // Disease → Medications
        Map<String, List<Map<String, String>>> diseaseMeds = new LinkedHashMap<>();
        diseaseMeds.put("上呼吸道感染", List.of(
            Map.of("name", "对乙酰氨基酚片", "usage", "500mg 每日3次（发热时服用）", "note", "每日不超过2000mg"),
            Map.of("name", "复方氨酚烷胺胶囊", "usage", "1粒 每日2次", "note", "嗜睡，避免驾驶")
        ));
        diseaseMeds.put("流行性感冒", List.of(
            Map.of("name", "布洛芬缓释胶囊", "usage", "300mg 每日2次（退热）", "note", "饭后服用"),
            Map.of("name", "连花清瘟颗粒", "usage", "1袋 每日3次", "note", "温水冲服")
        ));
        diseaseMeds.put("急性支气管炎", List.of(
            Map.of("name", "氨溴索片", "usage", "30mg 每日3次", "note", "祛痰药"),
            Map.of("name", "右美沙芬糖浆", "usage", "10ml 每日3次", "note", "干咳时使用")
        ));
        diseaseMeds.put("肺炎", List.of(
            Map.of("name", "阿莫西林胶囊", "usage", "500mg 每日3次", "note", "需确认无过敏史，建议就医"),
            Map.of("name", "氨溴索片", "usage", "30mg 每日3次", "note", "祛痰")
        ));
        diseaseMeds.put("急性胃肠炎", List.of(
            Map.of("name", "蒙脱石散", "usage", "3g 每日3次（空腹）", "note", "止泻"),
            Map.of("name", "口服补液盐", "usage", "按说明冲服", "note", "预防脱水最重要")
        ));
        diseaseMeds.put("慢性胃炎", List.of(
            Map.of("name", "奥美拉唑肠溶胶囊", "usage", "20mg 每日1次（空腹）", "note", "抑酸")
        ));
        diseaseMeds.put("胃溃疡", List.of(
            Map.of("name", "奥美拉唑", "usage", "20mg 每日2次", "note", "建议就医规范治疗")
        ));
        diseaseMeds.put("偏头痛", List.of(
            Map.of("name", "布洛芬缓释胶囊", "usage", "300mg（发作时）", "note", "痛前服用效果更佳")
        ));
        diseaseMeds.put("原发性高血压", List.of(
            Map.of("name", "硝苯地平控释片", "usage", "30mg 每日1次", "note", "需长期规律服药，定期监测血压")
        ));
        diseaseMeds.put("焦虑症", List.of(
            Map.of("name", "舍曲林片", "usage", "50mg 每日1次（早晨服）", "note", "需医生处方的抗抑郁药物")
        ));
        diseaseMeds.put("湿疹", List.of(
            Map.of("name", "糠酸莫米松乳膏", "usage", "外用 每日1次", "note", "连续使用不超过2周"),
            Map.of("name", "氯雷他定片", "usage", "10mg 每日1次", "note", "止痒抗过敏")
        ));

        // ----- Symptom analysis -----
        String symLower = (symptoms != null) ? symptoms.toLowerCase() : "";
        List<String> matchedDiseases = new ArrayList<>();
        for (var entry : symptomDiseaseMap.entrySet()) {
            if (symLower.contains(entry.getKey())) {
                for (String disease : entry.getValue()) {
                    if (!matchedDiseases.contains(disease)) {
                        matchedDiseases.add(disease);
                    }
                }
            }
        }

        // Pick primary diagnosis
        String primaryDisease = matchedDiseases.isEmpty() ? "上呼吸道感染" : matchedDiseases.get(0);
        String severity = diseaseSeverity.getOrDefault(primaryDisease, "中");
        List<Map<String, String>> meds = diseaseMeds.getOrDefault(primaryDisease, List.of(
            Map.of("name", "建议就医", "usage", "遵医嘱", "note", "药不对症可能延误病情")
        ));

        // Build possible diseases list
        List<Map<String, Object>> possibleDiseases = new ArrayList<>();
        for (int i = 0; i < Math.min(3, matchedDiseases.size()); i++) {
            String d = matchedDiseases.get(i);
            Map<String, Object> pd = new LinkedHashMap<>();
            pd.put("name", d);
            pd.put("probability", i == 0 ? "高" : i == 1 ? "中" : "低");
            pd.put("reason", i == 0 ? "症状与" + d + "的典型表现高度匹配" :
                                 "部分症状提示" + d + "的可能性");
            possibleDiseases.add(pd);
        }
        if (possibleDiseases.isEmpty()) {
            Map<String, Object> pd = new LinkedHashMap<>();
            pd.put("name", "待进一步检查");
            pd.put("probability", "低");
            pd.put("reason", "症状描述不够具体，建议补充更多信息");
            possibleDiseases.add(pd);
        }

        String severityDescription;
        switch (severity) {
            case "轻": severityDescription = "症状较轻，通常可自行缓解或门诊治疗"; break;
            case "重": severityDescription = "症状较重，建议尽快就医，避免延误治疗"; break;
            case "紧急": severityDescription = "❗ 可能存在紧急情况，请立即就医"; break;
            default: severityDescription = "需要关注，建议根据症状变化及时就医"; break;
        }

        String analysisText = String.format(
            "根据您描述的症状「%s」，结合内置医学知识库分析，初步判断为「%s」。%s。",
            symptoms != null ? symptoms : "未提供",
            primaryDisease,
            "重".equals(severity) ? "这是一种需要重视的疾病，建议尽早就医" : "这是一种常见的可自行观察处理的疾病"
        );

        // ----- Build result -----
        Map<String, Object> fallback = new LinkedHashMap<>();
        fallback.put("patientName", patientName != null ? patientName : "未知");
        fallback.put("symptoms", symptoms);
        fallback.put("consultTime", LocalDate.now().toString());
        fallback.put("disclaimer", "⚠️ 本诊断结果由AI辅助生成（本地模式），仅供参考，请以线下医生的专业诊断为准。如症状严重，请立即就医。");
        fallback.put("isLocalFallback", true);

        fallback.put("analysis", Map.of(
            "possibleDiseases", possibleDiseases,
            "analysis", analysisText
        ));
        fallback.put("possibleDiseases", possibleDiseases);
        fallback.put("analysisText", analysisText);

        fallback.put("severity", Map.of(
            "level", severity,
            "description", severityDescription
        ));

        fallback.put("medications", meds);

        fallback.put("care", Map.of(
            "diet", "清淡饮食，多喝温水，避免辛辣刺激",
            "rest", "保证充足睡眠，避免劳累",
            "nursing", "密切观察症状变化，如加重及时就医"
        ));

        String whenToSeeDoctor;
        if ("重".equals(severity) || "紧急".equals(severity)) {
            whenToSeeDoctor = "❗ 症状较重，建议立即就医。请前往医院相关科室就诊。";
        } else if ("轻".equals(severity)) {
            whenToSeeDoctor = "症状较轻，可先观察3天。如无改善或加重，请及时就医。";
        } else {
            whenToSeeDoctor = "建议关注症状变化，5-7天无好转请前往医院就诊。";
        }
        fallback.put("whenToSeeDoctor", whenToSeeDoctor);

        fallback.put("summary", String.format(
            "AI（本地模式）初步分析：根据您描述的症状，判断可能为「%s」。%s。%s",
            primaryDisease,
            "重".equals(severity) ? "请尽快就医" : "请按建议用药和护理",
            "如症状持续不缓解，请及时就医"
        ));

        fallback.put("isFallback", true);
        // 统一 AI 来源标注：远程大模型不可用时回退到本地知识库规则，非模型输出
        fallback.put("isMlGenerated", false);
        fallback.put("source", "local-kb-rules");

        return fallback;
    }
}
