package com.claudeflow.dto;

import lombok.Data;

/**
 * SSE进度更新事件
 */
@Data
public class ProgressUpdateEvent {

    private String taskId;
    private String phase;
    private Integer progress;
    private Integer currentStep;
    private Integer totalSteps;
    private Long timestamp;

    public ProgressUpdateEvent() {
        this.timestamp = System.currentTimeMillis();
    }
}