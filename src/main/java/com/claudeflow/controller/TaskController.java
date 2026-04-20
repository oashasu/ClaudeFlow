package com.claudeflow.controller;

import com.claudeflow.dto.TaskDTO;
import com.claudeflow.dto.TaskStatsDTO;
import com.claudeflow.service.TaskService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

/**
 * 任务REST控制器
 */
@RestController
@RequestMapping("/api/tasks")
@RequiredArgsConstructor
public class TaskController {

    private final TaskService taskService;

    /**
     * 任务列表
     */
    @GetMapping
    public List<TaskDTO> getTaskList(@RequestParam(required = false) String status) {
        return taskService.getTaskList(status);
    }

    /**
     * 统计数据
     */
    @GetMapping("/stats")
    public TaskStatsDTO getStats() {
        return taskService.getStats();
    }

    /**
     * 任务详情
     */
    @GetMapping("/{id}")
    public TaskDTO getTaskDetail(@PathVariable String id) {
        return taskService.getTaskDetail(id);
    }

    /**
     * 暂停任务
     */
    @PostMapping("/{id}/pause")
    public TaskDTO pauseTask(@PathVariable String id) {
        return taskService.pauseTask(id);
    }

    /**
     * 恢复任务
     */
    @PostMapping("/{id}/resume")
    public TaskDTO resumeTask(@PathVariable String id) {
        return taskService.resumeTask(id);
    }

    /**
     * 确认介入
     */
    @PostMapping("/confirm/{id}")
    public TaskDTO confirmIntervention(
            @PathVariable String id,
            @RequestBody Map<String, String> body) {
        String userInput = body.get("userInput");
        return taskService.confirmIntervention(id, userInput);
    }

    /**
     * 取消任务
     */
    @PostMapping("/cancel/{id}")
    public TaskDTO cancelTask(@PathVariable String id) {
        return taskService.cancelTask(id);
    }
}