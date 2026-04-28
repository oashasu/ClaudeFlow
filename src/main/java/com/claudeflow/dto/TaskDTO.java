package com.claudeflow.dto;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 任务DTO
 */
@Data
public class TaskDTO {

    private String id;
    private String name;
    private String domain;
    private String status;
    private String phase;
    private Integer progress;
    private String sessionId;
    private String description;
    private String priority;
    private LocalDateTime gmtCreate;
    private LocalDateTime gmtModified;
}