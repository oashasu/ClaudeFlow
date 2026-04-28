package com.claudeflow.controller;

import com.claudeflow.client.RuntimeClient;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.http.ResponseEntity;

import java.util.Collections;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.when;

/**
 * RuntimeController 单元测试
 *
 * A35: 验证 Runtime 消费端点代理行为
 */
@ExtendWith(MockitoExtension.class)
class RuntimeControllerTest {

    @Mock
    private RuntimeClient runtimeClient;

    @InjectMocks
    private RuntimeController runtimeController;

    // ── getStatus 测试 ───────────────────────────────

    @Test
    @DisplayName("getStatus 返回代理结果")
    void getStatus_returnsProxiedResult() {
        RuntimeClient.RuntimeStatusResponse mockStatus =
            new RuntimeClient.RuntimeStatusResponse("/tmp", 2, 5, 10, 1, false, Collections.singletonList("t1"));

        when(runtimeClient.getStatus()).thenReturn(mockStatus);

        ResponseEntity<RuntimeClient.RuntimeStatusResponse> response =
            runtimeController.getStatus();

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).isNotNull();
        assertThat(response.getBody().getRepoPath()).isEqualTo("/tmp");
    }

    @Test
    @DisplayName("getStatus client 返回 null 时返回 500")
    void getStatus_nullResult_returns500() {
        when(runtimeClient.getStatus()).thenReturn(null);

        ResponseEntity<RuntimeClient.RuntimeStatusResponse> response =
            runtimeController.getStatus();

        assertThat(response.getStatusCode().is5xxServerError()).isTrue();
    }

    // ── getSessions 测试 ───────────────────────────────

    @Test
    @DisplayName("getSessions 返回 session 列表")
    void getSessions_returnsSessions() {
        RuntimeClient.RuntimeSessionDTO session =
            new RuntimeClient.RuntimeSessionDTO("t1", "s1", "running", "high");

        when(runtimeClient.getSessions()).thenReturn(Collections.singletonList(session));

        ResponseEntity<List<RuntimeClient.RuntimeSessionDTO>> response =
            runtimeController.getSessions();

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).hasSize(1);
        assertThat(response.getBody().get(0).getTaskId()).isEqualTo("t1");
    }

    // ── getPlan 测试 ───────────────────────────────────

    @Test
    @DisplayName("getPlan 返回代理结果")
    void getPlan_returnsProxiedResult() {
        RuntimeClient.RuntimePlanResponse mockPlan =
            new RuntimeClient.RuntimePlanResponse(Collections.emptyList(), Collections.emptyList(), Collections.emptyList());

        when(runtimeClient.getPlan("claude")).thenReturn(mockPlan);

        ResponseEntity<RuntimeClient.RuntimePlanResponse> response =
            runtimeController.getPlan("claude");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).isNotNull();
    }

    // ── explainTask 测试 ────────────────────────────────

    @Test
    @DisplayName("explainTask 返回代理结果")
    void explainTask_returnsProxiedResult() {
        RuntimeClient.RuntimeExplainResponse mockExplain =
            new RuntimeClient.RuntimeExplainResponse("t1", "blocked", "high", "waiting", "等待", Collections.emptyList());

        when(runtimeClient.explainTask("t1")).thenReturn(mockExplain);

        ResponseEntity<RuntimeClient.RuntimeExplainResponse> response =
            runtimeController.explainTask("t1");

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody().getTaskId()).isEqualTo("t1");
    }

    @Test
    @DisplayName("explainTask 未找到返回 404")
    void explainTask_notFound_returns404() {
        when(runtimeClient.explainTask("t1")).thenReturn(null);

        ResponseEntity<RuntimeClient.RuntimeExplainResponse> response =
            runtimeController.explainTask("t1");

        assertThat(response.getStatusCode().is4xxClientError()).isTrue();
    }

    // ── getAuditRecords 测试 ────────────────────────────

    @Test
    @DisplayName("getAuditRecords 返回审计记录")
    void getAuditRecords_returnsRecords() {
        RuntimeClient.RuntimeAuditRecordDTO record =
            new RuntimeClient.RuntimeAuditRecordDTO("a1", "intervene", "t1", "s1", true, "成功", "2026-04-27T14:00:00Z");

        when(runtimeClient.getAuditRecords("intervene", "t1", 50))
            .thenReturn(Collections.singletonList(record));

        ResponseEntity<List<RuntimeClient.RuntimeAuditRecordDTO>> response =
            runtimeController.getAuditRecords("intervene", "t1", 50);

        assertThat(response.getStatusCode().is2xxSuccessful()).isTrue();
        assertThat(response.getBody()).hasSize(1);
        assertThat(response.getBody().get(0).getActionType()).isEqualTo("intervene");
    }
}