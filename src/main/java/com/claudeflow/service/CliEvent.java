package com.claudeflow.service;

import java.time.Instant;
import java.util.Map;

/**
 * CLI事件模型
 */
public class CliEvent {

    private String type;
    private String tool;
    private Map<String, Object> input;
    private String checkpointId;
    private String phase;
    private Integer step;
    private String summary;
    private String status;
    private Long totalCost;
    private Integer durationSeconds;
    private Instant timestamp;

    // tool_use事件构造器
    public static CliEvent toolUse(String tool, Map<String, Object> input) {
        CliEvent event = new CliEvent();
        event.type = "tool_use";
        event.tool = tool;
        event.input = input;
        event.timestamp = Instant.now();
        return event;
    }

    // checkpoint事件构造器
    public static CliEvent checkpoint(String checkpointId, String phase, Integer step, String summary) {
        CliEvent event = new CliEvent();
        event.type = "checkpoint";
        event.checkpointId = checkpointId;
        event.phase = phase;
        event.step = step;
        event.summary = summary;
        event.timestamp = Instant.now();
        return event;
    }

    // result事件构造器
    public static CliEvent result(String status, Long totalCost, Integer durationSeconds) {
        CliEvent event = new CliEvent();
        event.type = "result";
        event.status = status;
        event.totalCost = totalCost;
        event.durationSeconds = durationSeconds;
        event.timestamp = Instant.now();
        return event;
    }

    // Getters
    public String getType() { return type; }
    public String getTool() { return tool; }
    public Map<String, Object> getInput() { return input; }
    public String getCheckpointId() { return checkpointId; }
    public String getPhase() { return phase; }
    public Integer getStep() { return step; }
    public String getSummary() { return summary; }
    public String getStatus() { return status; }
    public Long getTotalCost() { return totalCost; }
    public Integer getDurationSeconds() { return durationSeconds; }
    public Instant getTimestamp() { return timestamp; }
}