package com.claudeflow.service;

import com.claudeflow.dto.TaskDTO;
import com.claudeflow.dto.TaskStatsDTO;
import com.claudeflow.dto.CreateTaskRequest;
import com.claudeflow.entity.TaskEntity;
import com.claudeflow.repository.TaskRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;
import java.util.stream.Collectors;

/**
 * 任务服务
 */
@Service
@RequiredArgsConstructor
public class TaskService {

    private final TaskRepository taskRepository;

    /**
     * 创建任务
     */
    @Transactional
    public TaskDTO createTask(CreateTaskRequest request) {
        TaskEntity task = new TaskEntity();
        task.setId(UUID.randomUUID().toString());
        task.setName(request.getName());
        task.setDomain(request.getDomain());
        task.setDescription(request.getPrompt());
        task.setPriority(request.getPriority());
        task.setStatus("pending");
        task.setPhase("init");
        task.setProgress(0);

        TaskEntity saved = taskRepository.save(task);
        return toDTO(saved);
    }

    /**
     * 获取任务列表
     */
    public List<TaskDTO> getTaskList(String status) {
        List<TaskEntity> tasks;
        if (status != null && !status.isEmpty()) {
            tasks = taskRepository.findByStatus(status);
        } else {
            tasks = taskRepository.findAll();
        }
        return tasks.stream()
                .map(this::toDTO)
                .collect(Collectors.toList());
    }

    /**
     * 获取统计数据
     */
    public TaskStatsDTO getStats() {
        TaskStatsDTO stats = new TaskStatsDTO();
        List<Object[]> counts = taskRepository.countByStatus();

        for (Object[] row : counts) {
            String status = (String) row[0];
            long count = (Long) row[1];

            switch (status) {
                case "running":
                    stats.setRunning(count);
                    break;
                case "completed":
                    stats.setCompleted(count);
                    break;
                case "waiting":
                    stats.setWaiting(count);
                    break;
                case "alert":
                    stats.setAlert(count);
                    break;
            }
        }

        return stats;
    }

    /**
     * 获取任务详情
     */
    public TaskDTO getTaskDetail(String taskId) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));
        return toDTO(task);
    }

    /**
     * 暂停任务
     */
    @Transactional
    public TaskDTO pauseTask(String taskId) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));

        if (!"running".equals(task.getStatus())) {
            throw new RuntimeException("Only running tasks can be paused");
        }

        task.setStatus("paused");
        taskRepository.save(task);
        return toDTO(task);
    }

    /**
     * 恢复任务
     */
    @Transactional
    public TaskDTO resumeTask(String taskId) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));

        if (!"paused".equals(task.getStatus())) {
            throw new RuntimeException("Only paused tasks can be resumed");
        }

        task.setStatus("running");
        taskRepository.save(task);
        return toDTO(task);
    }

    /**
     * 确认介入
     */
    @Transactional
    public TaskDTO confirmIntervention(String taskId, String userInput) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));

        if (!"waiting".equals(task.getStatus())) {
            throw new RuntimeException("Only waiting tasks can be confirmed");
        }

        task.setStatus("running");
        taskRepository.save(task);
        return toDTO(task);
    }

    /**
     * 取消任务
     */
    @Transactional
    public TaskDTO cancelTask(String taskId) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));

        task.setStatus("cancelled");
        taskRepository.save(task);
        return toDTO(task);
    }

    /**
     * 删除任务
     */
    @Transactional
    public void deleteTask(String taskId) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));

        // 如果任务正在运行，先取消Hermes会话
        if ("running".equals(task.getStatus()) && task.getSessionId() != null) {
            // 调用 Hermes 取消会话
        }

        taskRepository.delete(task);
    }

    /**
     * 重新执行任务（重置为pending）
     */
    @Transactional
    public TaskDTO retryTask(String taskId) {
        TaskEntity task = taskRepository.findById(taskId)
                .orElseThrow(() -> new RuntimeException("Task not found: " + taskId));

        // 只有error状态的任务可以重试
        if (!"error".equals(task.getStatus())) {
            throw new RuntimeException("Only error tasks can be retried");
        }

        task.setStatus("pending");
        task.setPhase("init");
        task.setProgress(0);
        task.setSessionId(null);
        taskRepository.save(task);
        return toDTO(task);
    }

    /**
     * Entity转DTO
     */
    private TaskDTO toDTO(TaskEntity entity) {
        TaskDTO dto = new TaskDTO();
        dto.setId(entity.getId());
        dto.setName(entity.getName());
        dto.setDomain(entity.getDomain());
        dto.setStatus(entity.getStatus());
        dto.setPhase(entity.getPhase());
        dto.setProgress(entity.getProgress());
        dto.setSessionId(entity.getSessionId());
        dto.setDescription(entity.getDescription());
        dto.setPriority(entity.getPriority());
        dto.setGmtCreate(entity.getGmtCreate());
        dto.setGmtModified(entity.getGmtModified());
        return dto;
    }
}