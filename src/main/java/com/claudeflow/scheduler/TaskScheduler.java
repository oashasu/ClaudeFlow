package com.claudeflow.scheduler;

import com.claudeflow.client.HermesClient;
import com.claudeflow.entity.TaskEntity;
import com.claudeflow.repository.TaskRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * 任务调度器
 * 定时扫描pending任务并启动执行
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class TaskScheduler {

    private final TaskRepository taskRepository;
    private final HermesClient hermesClient;

    /**
     * 每5秒扫描一次pending任务
     */
    @Scheduled(fixedRate = 5000)
    @Transactional
    public void startPendingTasks() {
        List<TaskEntity> pendingTasks = taskRepository.findByStatus("pending");

        for (TaskEntity task : pendingTasks) {
            log.info("Starting pending task: {} - {}", task.getId(), task.getName());

            // 调用Hermes启动CLI会话
            String sessionId = hermesClient.startSession(task.getDescription());

            if (sessionId != null) {
                // 更新任务状态
                task.setStatus("running");
                task.setSessionId(sessionId);
                task.setPhase("planning");
                taskRepository.save(task);

                log.info("Task {} started with session {}", task.getId(), sessionId);
            } else {
                log.error("Failed to start task {}", task.getId());
            }
        }
    }

    /**
     * 每30秒检查运行中任务的状态
     */
    @Scheduled(fixedRate = 30000)
    @Transactional
    public void checkRunningTasks() {
        List<TaskEntity> runningTasks = taskRepository.findByStatus("running");

        for (TaskEntity task : runningTasks) {
            if (task.getSessionId() == null) {
                continue;
            }

            String status = hermesClient.getSessionStatus(task.getSessionId());

            if ("completed".equals(status)) {
                task.setStatus("completed");
                task.setProgress(100);
                taskRepository.save(task);
                log.info("Task {} completed", task.getId());
            } else if ("terminated".equals(status) || "error".equals(status)) {
                task.setStatus("error");
                taskRepository.save(task);
                log.error("Task {} terminated with error", task.getId());
            }
        }
    }
}