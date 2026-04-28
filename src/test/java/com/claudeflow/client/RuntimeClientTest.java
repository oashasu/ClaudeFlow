package com.claudeflow.client;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.*;
import org.springframework.web.client.RestTemplate;

import java.util.*;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.when;

/**
 * RuntimeClient 单元测试
 *
 * A35: 验证 Runtime API 消费契约
 */
@ExtendWith(MockitoExtension.class)
class RuntimeClientTest {

    @Mock
    private RestTemplate restTemplate;

    private RuntimeClient runtimeClient;

    @BeforeEach
    void setUp() {
        runtimeClient = new RuntimeClient(restTemplate);
    }

    // ── RuntimeStatus 测试 ───────────────────────────────

    @Test
    @DisplayName("getStatus 返回有效 RuntimeStatus")
    void getStatus_validResponse_returnsStatus() {
        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("repo_path", "/tmp/repo");
        mockResponse.put("active_agents", 2);
        mockResponse.put("queued_tasks", 5);
        mockResponse.put("completed_tasks", 10);
        mockResponse.put("failed_tasks", 1);
        mockResponse.put("intervention_required", true);
        mockResponse.put("running_tasks", Arrays.asList("t1", "t2"));

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        RuntimeClient.RuntimeStatusResponse status = runtimeClient.getStatus();

        assertThat(status).isNotNull();
        assertThat(status.getRepoPath()).isEqualTo("/tmp/repo");
        assertThat(status.getActiveAgents()).isEqualTo(2);
        assertThat(status.getQueuedTasks()).isEqualTo(5);
        assertThat(status.isInterventionRequired()).isTrue();
        assertThat(status.getRunningTasks()).containsExactly("t1", "t2");
    }

    @Test
    @DisplayName("getStatus 缺少可选字段时使用默认值")
    void getStatus_missingOptionalFields_usesDefaults() {
        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("repo_path", "/tmp");
        // 缺少 active_agents, queued_tasks 等

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        RuntimeClient.RuntimeStatusResponse status = runtimeClient.getStatus();

        assertThat(status).isNotNull();
        assertThat(status.getRepoPath()).isEqualTo("/tmp");
        assertThat(status.getActiveAgents()).isEqualTo(0);
        assertThat(status.isInterventionRequired()).isFalse();
        assertThat(status.getRunningTasks()).isEmpty();
    }

    // ── RuntimeSessions 测试 ─────────────────────────────

    @Test
    @DisplayName("getSessions 返回 session 列表")
    void getSessions_validResponse_returnsSessions() {
        Map<String, Object> session1 = new HashMap<>();
        session1.put("task_id", "t1");
        session1.put("session_id", "s1");
        session1.put("status", "running");
        session1.put("priority", "high");

        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("sessions", Collections.singletonList(session1));

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        List<RuntimeClient.RuntimeSessionDTO> sessions = runtimeClient.getSessions();

        assertThat(sessions).hasSize(1);
        assertThat(sessions.get(0).getTaskId()).isEqualTo("t1");
        assertThat(sessions.get(0).getSessionId()).isEqualTo("s1");
        assertThat(sessions.get(0).getStatus()).isEqualTo("running");
        assertThat(sessions.get(0).getPriority()).isEqualTo("high");
    }

    @Test
    @DisplayName("getSessions 空响应返回空列表")
    void getSessions_emptyResponse_returnsEmptyList() {
        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("sessions", null);

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        List<RuntimeClient.RuntimeSessionDTO> sessions = runtimeClient.getSessions();

        assertThat(sessions).isEmpty();
    }

    // ── RuntimePlan 测试 ─────────────────────────────────

    @Test
    @DisplayName("getPlan 返回有效 RuntimePlan")
    void getPlan_validResponse_returnsPlan() {
        Map<String, Object> runnableTask = new HashMap<>();
        runnableTask.put("task_id", "t1");
        runnableTask.put("priority", "high");
        runnableTask.put("executor_type", "claude");
        runnableTask.put("phase_id", "phase-1");

        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("runnable", Collections.singletonList(runnableTask));
        mockResponse.put("blocked", Collections.emptyList());
        mockResponse.put("running", Collections.emptyList());

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        RuntimeClient.RuntimePlanResponse plan = runtimeClient.getPlan("claude");

        assertThat(plan).isNotNull();
        assertThat(plan.getRunnable()).hasSize(1);
        assertThat(plan.getRunnable().get(0).getTaskId()).isEqualTo("t1");
        assertThat(plan.getRunnable().get(0).getExecutorType()).isEqualTo("claude");
        assertThat(plan.getRunnable().get(0).getPhaseId()).isEqualTo("phase-1");
    }

    // ── RuntimeExplain 测试 ───────────────────────────────

    @Test
    @DisplayName("explainTask 返回有效 Explain")
    void explainTask_validResponse_returnsExplain() {
        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("task_id", "t1");
        mockResponse.put("state", "blocked");
        mockResponse.put("priority", "high");
        mockResponse.put("reason_code", "waiting");
        mockResponse.put("reason", "等待依赖完成");
        mockResponse.put("dependencies", Collections.singletonList("t0"));

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        RuntimeClient.RuntimeExplainResponse explain = runtimeClient.explainTask("t1");

        assertThat(explain).isNotNull();
        assertThat(explain.getTaskId()).isEqualTo("t1");
        assertThat(explain.getState()).isEqualTo("blocked");
        assertThat(explain.getReasonCode()).isEqualTo("waiting");
        assertThat(explain.getDependencies()).containsExactly("t0");
    }

    // ── AuditRecords 测试 ────────────────────────────────

    @Test
    @DisplayName("getAuditRecords 返回审计记录列表")
    void getAuditRecords_validResponse_returnsRecords() {
        Map<String, Object> record = new HashMap<>();
        record.put("action_id", "a1");
        record.put("action_type", "intervene");
        record.put("target_task_id", "t1");
        record.put("target_session_id", "s1");
        record.put("success", true);
        record.put("message", "干预成功");
        record.put("timestamp", "2026-04-27T14:00:00Z");

        Map<String, Object> mockResponse = new HashMap<>();
        mockResponse.put("records", Collections.singletonList(record));
        mockResponse.put("total", 1);

        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenReturn(new ResponseEntity<>(mockResponse, HttpStatus.OK));

        List<RuntimeClient.RuntimeAuditRecordDTO> records =
            runtimeClient.getAuditRecords("intervene", "t1", 50);

        assertThat(records).hasSize(1);
        assertThat(records.get(0).getActionId()).isEqualTo("a1");
        assertThat(records.get(0).getActionType()).isEqualTo("intervene");
        assertThat(records.get(0).isSuccess()).isTrue();
    }

    // ── 错误处理测试 ──────────────────────────────────────

    @Test
    @DisplayName("API 调用失败返回 null 或空列表")
    void apiCall_failure_returnsNull() {
        when(restTemplate.getForEntity(any(String.class), eq(Map.class)))
            .thenThrow(new RuntimeException("Connection refused"));

        RuntimeClient.RuntimeStatusResponse status = runtimeClient.getStatus();
        assertThat(status).isNull();

        List<RuntimeClient.RuntimeSessionDTO> sessions = runtimeClient.getSessions();
        assertThat(sessions).isEmpty();
    }
}