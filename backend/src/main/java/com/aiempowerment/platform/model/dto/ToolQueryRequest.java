package com.aiempowerment.platform.model.dto;

import lombok.AllArgsConstructor;
import lombok.Data;
import lombok.NoArgsConstructor;

/**
 * 工具查询DTO
 */
@Data
@NoArgsConstructor
@AllArgsConstructor
public class ToolQueryRequest {

    private String keyword;
    private Long toolId;
}
