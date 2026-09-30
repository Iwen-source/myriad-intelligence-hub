package com.aiempowerment.platform.model.dto.analysis;

/**
 * 节能优化建议 DTO
 */
public class OptimizationTipDTO {
    private String id;
    private String title;
    private String description;
    private String priority;
    private String category;
    private boolean mlGenerated;

    public OptimizationTipDTO() {}

    public OptimizationTipDTO(String id, String title, String description,
                               String priority, String category, boolean mlGenerated) {
        this.id = id;
        this.title = title;
        this.description = description;
        this.priority = priority;
        this.category = category;
        this.mlGenerated = mlGenerated;
    }

    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getTitle() { return title; }
    public void setTitle(String title) { this.title = title; }
    public String getDescription() { return description; }
    public void setDescription(String description) { this.description = description; }
    public String getPriority() { return priority; }
    public void setPriority(String priority) { this.priority = priority; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public boolean isMlGenerated() { return mlGenerated; }
    public void setMlGenerated(boolean mlGenerated) { this.mlGenerated = mlGenerated; }
}
