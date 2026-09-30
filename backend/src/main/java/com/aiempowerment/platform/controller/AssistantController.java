package com.aiempowerment.platform.controller;

import com.aiempowerment.platform.common.ApiResponse;
import com.aiempowerment.platform.model.dto.AssistantChatRequest;
import com.aiempowerment.platform.service.AssistantService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 「豆芽」智能助手控制器 —— 公共接口（无需登录），用于首页问答与全站答疑。
 */
@RestController
@RequestMapping("/public/assistant")
@RequiredArgsConstructor
public class AssistantController {

    private final AssistantService assistantService;

    /** 推荐问题 */
    @GetMapping("/suggestions")
    public ApiResponse<?> suggestions() {
        return ApiResponse.success(assistantService.suggestions());
    }

    /** 对话 */
    @PostMapping("/chat")
    public ApiResponse<?> chat(@Valid @RequestBody AssistantChatRequest request) {
        AssistantService.ChatResult result =
                assistantService.chat(request.getMessage(), request.getHistory());
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("reply", result.reply());
        data.put("mode", result.mode());
        data.put("assistant", "豆芽");
        return ApiResponse.success(data);
    }
}
