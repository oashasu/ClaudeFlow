package com.claudeflow.controller;

import com.claudeflow.dto.TaskDTO;
import com.claudeflow.dto.TaskStatsDTO;
import com.claudeflow.entity.TaskEntity;
import com.claudeflow.repository.TaskRepository;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Arrays;
import java.util.List;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.*;

/**
 * TaskController测试
 * TDD: 测试REST API契约
 */
@ExtendWith(MockitoExtension.class)
class TaskControllerTest {

    @Mock
    private TaskRepository taskRepository;

    @InjectMocks
    private com.claudeflow.service.TaskService taskService;

    private TaskController taskController;

    @BeforeEach
    void setUp() {
        taskController = new TaskController(taskService);
    }

    @Test
    @DisplayName("getTaskList返回所有任务")
    void getTaskList_returnsAllTasks() {
        TaskEntity task1 = createTask("task-001", "测试任务1", "running");
        TaskEntity task2 = createTask("task-002", "测试任务2", "completed");
        when(taskRepository.findAll()).thenReturn(Arrays.asList(task1, task2));

        List<TaskDTO> result = taskController.getTaskList(null);

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getId()).isEqualTo("task-001");
        verify(taskRepository).findAll();
    }

    @Test
    @DisplayName("getTaskList按状态过滤")
    void getTaskList_filtersByStatus() {
        TaskEntity task1 = createTask("task-001", "测试任务1", "running");
        when(taskRepository.findByStatus("running")).thenReturn(Arrays.asList(task1));

        List<TaskDTO> result = taskController.getTaskList("running");

        assertThat(result).hasSize(1);
        assertThat(result.get(0).getStatus()).isEqualTo("running");
        verify(taskRepository).findByStatus("running");
        verify(taskRepository, never()).findAll();
    }

    @Test
    @DisplayName("getStats返回统计数据")
    void getStats_returnsStatistics() {
        when(taskRepository.countByStatus()).thenReturn(Arrays.asList(
                new Object[]{"running", 3L},
                new Object[]{"completed", 5L},
                new Object[]{"waiting", 2L},
                new Object[]{"alert", 1L}
        ));

        TaskStatsDTO stats = taskController.getStats();

        assertThat(stats.getRunning()).isEqualTo(3);
        assertThat(stats.getCompleted()).isEqualTo(5);
        assertThat(stats.getWaiting()).isEqualTo(2);
        assertThat(stats.getAlert()).isEqualTo(1);
    }

    @Test
    @DisplayName("getTaskDetail返回任务详情")
    void getTaskDetail_returnsTaskDetail() {
        TaskEntity task = createTask("task-001", "测试任务", "running");
        task.setPhase("Phase2");
        task.setProgress(50);
        when(taskRepository.findById("task-001")).thenReturn(Optional.of(task));

        TaskDTO result = taskController.getTaskDetail("task-001");

        assertThat(result.getId()).isEqualTo("task-001");
        assertThat(result.getPhase()).isEqualTo("Phase2");
        assertThat(result.getProgress()).isEqualTo(50);
    }

    @Test
    @DisplayName("getTaskDetail不存在时抛出异常")
    void getTaskDetail_notFound_throwsException() {
        when(taskRepository.findById("non-existent")).thenReturn(Optional.empty());

        assertThatThrownBy(() -> taskController.getTaskDetail("non-existent"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("Task not found");
    }

    @Test
    @DisplayName("pauseTask暂停运行任务")
    void pauseTask_pausesRunningTask() {
        TaskEntity task = createTask("task-001", "测试任务", "running");
        when(taskRepository.findById("task-001")).thenReturn(Optional.of(task));

        TaskDTO result = taskController.pauseTask("task-001");

        assertThat(result.getStatus()).isEqualTo("paused");
        verify(taskRepository).save(task);
    }

    @Test
    @DisplayName("pauseTask非运行状态时抛出异常")
    void pauseTask_notRunning_throwsException() {
        TaskEntity task = createTask("task-001", "测试任务", "completed");
        when(taskRepository.findById("task-001")).thenReturn(Optional.of(task));

        assertThatThrownBy(() -> taskController.pauseTask("task-001"))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("Only running tasks can be paused");
    }

    @Test
    @DisplayName("resumeTask恢复暂停任务")
    void resumeTask_resumesPausedTask() {
        TaskEntity task = createTask("task-001", "测试任务", "paused");
        when(taskRepository.findById("task-001")).thenReturn(Optional.of(task));

        TaskDTO result = taskController.resumeTask("task-001");

        assertThat(result.getStatus()).isEqualTo("running");
        verify(taskRepository).save(task);
    }

    @Test
    @DisplayName("cancelTask取消任务")
    void cancelTask_cancelsTask() {
        TaskEntity task = createTask("task-001", "测试任务", "running");
        when(taskRepository.findById("task-001")).thenReturn(Optional.of(task));

        TaskDTO result = taskController.cancelTask("task-001");

        assertThat(result.getStatus()).isEqualTo("cancelled");
        verify(taskRepository).save(task);
    }

    private TaskEntity createTask(String id, String name, String status) {
        TaskEntity task = new TaskEntity();
        task.setId(id);
        task.setName(name);
        task.setStatus(status);
        task.setDomain("test-domain");
        task.setDescription("test description");
        return task;
    }
}