package com.claudeflow.scheduler;

import com.claudeflow.repository.CheckpointRepository;
import com.claudeflow.repository.PhaseStepRepository;
import com.claudeflow.repository.TaskRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.Arrays;
import java.util.List;

/**
 * 数据清理定时任务
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class CleanupScheduler {

    private final TaskRepository taskRepository;
    private final CheckpointRepository checkpointRepository;
    private final PhaseStepRepository phaseStepRepository;

    private static final int RETENTION_DAYS = 7;

    /**
     * 每日03:00执行清理
     */
    @Scheduled(cron = "0 0 3 * * ?")
    @Transactional
    public void cleanupOldTasks() {
        log.info("Starting cleanup task...");

        LocalDateTime threshold = LocalDateTime.now().minusDays(RETENTION_DAYS);
        List<String> statusesToClean = Arrays.asList("completed", "cancelled", "archived");

        // 查询需要清理的任务
        List<String> taskIds = taskRepository.findForCleanup(statusesToClean, threshold)
                .stream()
                .map(task -> task.getId())
                .toList();

        if (taskIds.isEmpty()) {
            log.info("No tasks to cleanup");
            return;
        }

        // 删除关联数据
        for (String taskId : taskIds) {
            checkpointRepository.deleteByTaskId(taskId);
            phaseStepRepository.deleteByTaskId(taskId);
        }

        // 删除任务
        taskRepository.deleteByStatusInAndGmtModifiedBefore(statusesToClean, threshold);

        log.info("Cleanup completed. Removed {} tasks", taskIds.size());
    }
}