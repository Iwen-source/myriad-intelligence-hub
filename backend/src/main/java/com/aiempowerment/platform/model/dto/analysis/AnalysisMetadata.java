package com.aiempowerment.platform.model.dto.analysis;

import java.time.LocalDateTime;

/**
 * 分析元数据 — 所有分析 DTO 的公共基类
 */
public class AnalysisMetadata {
    private boolean mlGenerated = false;
    private LocalDateTime analysisTime = LocalDateTime.now();

    public AnalysisMetadata() {}

    public AnalysisMetadata(boolean mlGenerated) {
        this.mlGenerated = mlGenerated;
        this.analysisTime = LocalDateTime.now();
    }

    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
    public LocalDateTime getAnalysisTime() { return analysisTime; }
    public void setAnalysisTime(LocalDateTime analysisTime) { this.analysisTime = analysisTime; }
}
