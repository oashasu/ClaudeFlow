package com.claudeflow.dto;

import lombok.Data;

/**
 * SSE工具调用事件
 */
@Data
public class ToolCallEvent {

    private String taskId;
    private String toolName;
    private String action;
    private Long timestamp;

    public ToolCallEvent() {
        this.timestamp = System.currentTimeMillis();
    }
}