package com.claudeflow.dto;

import lombok.Data;

/**
 * SSE等待介入事件
 */
@Data
public class InterventionPromptEvent {

    private String taskId;
    private String message;
    private Integer timeoutSeconds;
    private Long timestamp;

    public InterventionPromptEvent() {
        this.timestamp = System.currentTimeMillis();
        if (timeoutSeconds == null) {
            timeoutSeconds = 300;
        }
    }
}