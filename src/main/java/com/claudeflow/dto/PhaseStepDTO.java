package com.claudeflow.dto;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * 阶段步骤DTO
 */
@Data
public class PhaseStepDTO {

    private String id;
    private String taskId;
    private String phase;
    private Integer stepIndex;
    private String stepName;
    private String status;
    private LocalDateTime gmtCreate;
    private LocalDateTime gmtModified;
}