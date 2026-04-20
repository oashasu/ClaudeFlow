package com.claudeflow.dto;

import lombok.Data;
import java.time.LocalDateTime;

/**
 * Checkpoint DTO
 */
@Data
public class CheckpointDTO {

    private String id;
    private String taskId;
    private String phase;
    private Integer stepIndex;
    private String summary;
    private LocalDateTime gmtCreate;

    /**
     * 是否当前checkpoint
     */
    private boolean isCurrent;
}