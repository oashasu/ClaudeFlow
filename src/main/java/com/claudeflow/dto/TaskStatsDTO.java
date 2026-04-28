package com.claudeflow.dto;

import lombok.Data;

/**
 * 任务统计DTO
 */
@Data
public class TaskStatsDTO {

    private long running;
    private long completed;
    private long waiting;
    private long alert;

    /**
     * 计算总数
     */
    public long getTotal() {
        return running + completed + waiting + alert;
    }
}