package com.claudeflow.dto;

import lombok.Data;

/**
 * 创建任务请求DTO
 */
@Data
public class CreateTaskRequest {

    /**
     * 任务名称
     */
    private String name;

    /**
     * 业务领域
     */
    private String domain;

    /**
     * 任务描述（Prompt）
     */
    private String prompt;

    /**
     * 优先级：高/中/低
     */
    private String priority;
}