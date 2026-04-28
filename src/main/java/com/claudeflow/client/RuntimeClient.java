package com.claudeflow.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.*;
import java.util.stream.Collectors;

/**
 * Runtime API 客户端
 *
 * A35: 消费 Python Runtime API 的契约层。
 * 与 HermesClient 区分：HermesClient 调用 session 级 API，
 * RuntimeClient 调用 runtime 级 API（plan/status/sessions/dispatch）。
 *
 * 边界约定：
 * - 不复制 Python runtime 状态机逻辑
 * - 只做 DTO 转换，不重写核心判定
 * - 字段契约与 examples/runtime-*.schema.json 对齐
 */
@Slf4j
@Component
public class RuntimeClient {

    @Value("${runtime.url:http://localhost:8000}")
    private String runtimeUrl;

    private final RestTemplate restTemplate;

    public RuntimeClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    /**
     * 获取 Runtime Status
     * 对应 Python: GET /api/runtime/status
     */
    public RuntimeStatusResponse getStatus() {
        try {
            String url = runtimeUrl + "/api/runtime/status";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                return RuntimeStatusResponse.fromMap(body);
            }
            log.error("Runtime status request failed: {}", response.getStatusCode());
            return null;
        } catch (Exception e) {
            log.error("Failed to call Runtime API: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 获取 Runtime Sessions
     * 对应 Python: GET /api/runtime/sessions
     */
    public List<RuntimeSessionDTO> getSessions() {
        try {
            String url = runtimeUrl + "/api/runtime/sessions";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                List<Map<String, Object>> sessions = (List<Map<String, Object>>) body.get("sessions");
                if (sessions == null) {
                    return Collections.emptyList();
                }
                return sessions.stream()
                    .map(RuntimeSessionDTO::fromMap)
                    .collect(Collectors.toList());
            }
            return Collections.emptyList();
        } catch (Exception e) {
            log.error("Failed to get Runtime sessions: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    /**
     * 获取 Runtime Plan
     * 对应 Python: GET /api/runtime/plan
     */
    public RuntimePlanResponse getPlan(String executorType) {
        try {
            String url = runtimeUrl + "/api/runtime/plan?executor_type=" + executorType;
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return RuntimePlanResponse.fromMap(response.getBody());
            }
            return null;
        } catch (Exception e) {
            log.error("Failed to get Runtime plan: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 解释任务状态
     * 对应 Python: GET /api/runtime/explain/{task_id}
     */
    public RuntimeExplainResponse explainTask(String taskId) {
        try {
            String url = runtimeUrl + "/api/runtime/explain/" + taskId;
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return RuntimeExplainResponse.fromMap(response.getBody());
            }
            return null;
        } catch (Exception e) {
            log.error("Failed to explain task {}: {}", taskId, e.getMessage());
            return null;
        }
    }

    /**
     * 查询审计记录
     * 对应 Python: GET /api/runtime/action-audit
     */
    public List<RuntimeAuditRecordDTO> getAuditRecords(String actionType, String targetTaskId, int limit) {
        try {
            StringBuilder urlBuilder = new StringBuilder(runtimeUrl + "/api/runtime/action-audit?limit=" + limit);
            if (actionType != null && !actionType.isEmpty()) {
                urlBuilder.append("&action_type=").append(actionType);
            }
            if (targetTaskId != null && !targetTaskId.isEmpty()) {
                urlBuilder.append("&target_task_id=").append(targetTaskId);
            }

            ResponseEntity<Map> response = restTemplate.getForEntity(urlBuilder.toString(), Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                Map<String, Object> body = response.getBody();
                List<Map<String, Object>> records = (List<Map<String, Object>>) body.get("records");
                if (records == null) {
                    return Collections.emptyList();
                }
                return records.stream()
                    .map(RuntimeAuditRecordDTO::fromMap)
                    .collect(Collectors.toList());
            }
            return Collections.emptyList();
        } catch (Exception e) {
            log.error("Failed to get audit records: {}", e.getMessage());
            return Collections.emptyList();
        }
    }

    // ── DTO 内类（与 Python runtime schema 对齐）────────────────

    /**
     * Runtime Status DTO
     * 对应 schema: examples/runtime-status.schema.json
     */
    public static class RuntimeStatusResponse {
        private final String repoPath;
        private final int activeAgents;
        private final int queuedTasks;
        private final int completedTasks;
        private final int failedTasks;
        private final boolean interventionRequired;
        private final List<String> runningTasks;

        public RuntimeStatusResponse(
            String repoPath, int activeAgents, int queuedTasks,
            int completedTasks, int failedTasks, boolean interventionRequired,
            List<String> runningTasks
        ) {
            this.repoPath = repoPath;
            this.activeAgents = activeAgents;
            this.queuedTasks = queuedTasks;
            this.completedTasks = completedTasks;
            this.failedTasks = failedTasks;
            this.interventionRequired = interventionRequired;
            this.runningTasks = runningTasks;
        }

        public static RuntimeStatusResponse fromMap(Map<String, Object> map) {
            List<String> runningTasksRaw = (List<String>) map.get("running_tasks");
            List<String> runningTasks = runningTasksRaw != null ? runningTasksRaw : Collections.emptyList();

            return new RuntimeStatusResponse(
                (String) map.get("repo_path"),
                ((Number) map.getOrDefault("active_agents", 0)).intValue(),
                ((Number) map.getOrDefault("queued_tasks", 0)).intValue(),
                ((Number) map.getOrDefault("completed_tasks", 0)).intValue(),
                ((Number) map.getOrDefault("failed_tasks", 0)).intValue(),
                (Boolean) map.getOrDefault("intervention_required", false),
                runningTasks
            );
        }

        public String getRepoPath() { return repoPath; }
        public int getActiveAgents() { return activeAgents; }
        public int getQueuedTasks() { return queuedTasks; }
        public int getCompletedTasks() { return completedTasks; }
        public int getFailedTasks() { return failedTasks; }
        public boolean isInterventionRequired() { return interventionRequired; }
        public List<String> getRunningTasks() { return runningTasks; }
    }

    /**
     * Runtime Session DTO
     * 对应 schema: examples/runtime-sessions.schema.json
     */
    public static class RuntimeSessionDTO {
        private final String taskId;
        private final String sessionId;
        private final String status;
        private final String priority;

        public RuntimeSessionDTO(String taskId, String sessionId, String status, String priority) {
            this.taskId = taskId;
            this.sessionId = sessionId;
            this.status = status;
            this.priority = priority;
        }

        public static RuntimeSessionDTO fromMap(Map<String, Object> map) {
            return new RuntimeSessionDTO(
                (String) map.get("task_id"),
                (String) map.get("session_id"),
                (String) map.get("status"),
                (String) map.get("priority")
            );
        }

        public String getTaskId() { return taskId; }
        public String getSessionId() { return sessionId; }
        public String getStatus() { return status; }
        public String getPriority() { return priority; }
    }

    /**
     * Runtime Plan DTO
     * 对应 Python runtime plan 输出
     */
    public static class RuntimePlanResponse {
        private final List<RunnableTaskDTO> runnable;
        private final List<Object> blocked;
        private final List<Object> running;

        public RuntimePlanResponse(List<RunnableTaskDTO> runnable, List<Object> blocked, List<Object> running) {
            this.runnable = runnable;
            this.blocked = blocked;
            this.running = running;
        }

        public static RuntimePlanResponse fromMap(Map<String, Object> map) {
            List<Map<String, Object>> runnableList = (List<Map<String, Object>>) map.get("runnable");
            List<RunnableTaskDTO> runnable = runnableList == null ? Collections.emptyList() :
                runnableList.stream().map(RunnableTaskDTO::fromMap).collect(Collectors.toList());

            List<Object> blockedRaw = (List<Object>) map.get("blocked");
            List<Object> blocked = blockedRaw != null ? blockedRaw : Collections.emptyList();

            List<Object> runningRaw = (List<Object>) map.get("running");
            List<Object> running = runningRaw != null ? runningRaw : Collections.emptyList();

            return new RuntimePlanResponse(runnable, blocked, running);
        }

        public List<RunnableTaskDTO> getRunnable() { return runnable; }
        public List<Object> getBlocked() { return blocked; }
        public List<Object> getRunning() { return running; }
    }

    public static class RunnableTaskDTO {
        private final String taskId;
        private final String priority;
        private final String executorType;
        private final String phaseId;

        public RunnableTaskDTO(String taskId, String priority, String executorType, String phaseId) {
            this.taskId = taskId;
            this.priority = priority;
            this.executorType = executorType;
            this.phaseId = phaseId;
        }

        public static RunnableTaskDTO fromMap(Map<String, Object> map) {
            return new RunnableTaskDTO(
                (String) map.get("task_id"),
                (String) map.get("priority"),
                (String) map.get("executor_type"),
                (String) map.get("phase_id")
            );
        }

        public String getTaskId() { return taskId; }
        public String getPriority() { return priority; }
        public String getExecutorType() { return executorType; }
        public String getPhaseId() { return phaseId; }
    }

    /**
     * Runtime Explain DTO
     */
    public static class RuntimeExplainResponse {
        private final String taskId;
        private final String state;
        private final String priority;
        private final String reasonCode;
        private final String reason;
        private final List<Object> dependencies;

        public RuntimeExplainResponse(String taskId, String state, String priority,
            String reasonCode, String reason, List<Object> dependencies) {
            this.taskId = taskId;
            this.state = state;
            this.priority = priority;
            this.reasonCode = reasonCode;
            this.reason = reason;
            this.dependencies = dependencies;
        }

        public static RuntimeExplainResponse fromMap(Map<String, Object> map) {
            List<Object> depsRaw = (List<Object>) map.get("dependencies");
            List<Object> dependencies = depsRaw != null ? depsRaw : Collections.emptyList();

            return new RuntimeExplainResponse(
                (String) map.get("task_id"),
                (String) map.get("state"),
                (String) map.get("priority"),
                (String) map.get("reason_code"),
                (String) map.get("reason"),
                dependencies
            );
        }

        public String getTaskId() { return taskId; }
        public String getState() { return state; }
        public String getPriority() { return priority; }
        public String getReasonCode() { return reasonCode; }
        public String getReason() { return reason; }
        public List<Object> getDependencies() { return dependencies; }
    }

    /**
     * Runtime Audit Record DTO
     * 对应 Python ActionAuditRecord
     */
    public static class RuntimeAuditRecordDTO {
        private final String actionId;
        private final String actionType;
        private final String targetTaskId;
        private final String targetSessionId;
        private final boolean success;
        private final String message;
        private final String timestamp;

        public RuntimeAuditRecordDTO(String actionId, String actionType, String targetTaskId,
            String targetSessionId, boolean success, String message, String timestamp) {
            this.actionId = actionId;
            this.actionType = actionType;
            this.targetTaskId = targetTaskId;
            this.targetSessionId = targetSessionId;
            this.success = success;
            this.message = message;
            this.timestamp = timestamp;
        }

        public static RuntimeAuditRecordDTO fromMap(Map<String, Object> map) {
            return new RuntimeAuditRecordDTO(
                (String) map.get("action_id"),
                (String) map.get("action_type"),
                (String) map.get("target_task_id"),
                (String) map.get("target_session_id"),
                (Boolean) map.getOrDefault("success", false),
                (String) map.get("message"),
                (String) map.get("timestamp")
            );
        }

        public String getActionId() { return actionId; }
        public String getActionType() { return actionType; }
        public String getTargetTaskId() { return targetTaskId; }
        public String getTargetSessionId() { return targetSessionId; }
        public boolean isSuccess() { return success; }
        public String getMessage() { return message; }
        public String getTimestamp() { return timestamp; }
    }
}