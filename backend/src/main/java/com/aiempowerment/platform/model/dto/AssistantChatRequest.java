package com.aiempowerment.platform.model.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.Data;

import java.util.ArrayList;
import java.util.List;

/**
 * 「豆芽」助手聊天请求。
 */
@Data
public class AssistantChatRequest {

    /** 用户本轮消息 */
    @NotBlank(message = "消息不能为空")
    @Size(max = 4000, message = "消息过长")
    private String message;

    /** 历史对话（可选），按时间正序 */
    @Size(max = 40, message = "历史消息过多")
    private List<Message> history = new ArrayList<>();

    @Data
    public static class Message {
        private String role;    // user | assistant
        private String content;
    }
}
