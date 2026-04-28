package com.claudeflow.controller;

import com.claudeflow.client.RuntimeClient;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

/**
 * Runtime REST 控制器
 *
 * A35: 消费 Python Runtime API 的 HTTP 入口。
 * 与 TaskController 边界区分：
 *
 * - TaskController (/api/tasks): 旧任务流 CRUD，操作 TaskEntity（数据库）
 * - RuntimeController (/api/runtime-consume): Runtime API 消费代理，不持久化状态
 *
 * 边界约定：
 * - 不复制 Python runtime 状态机
 * - 只代理调用 + DTO 转换
 * - 状态真相源在 Python runtime，Java 只做聚合展示
 */
@RestController
@RequestMapping("/api/runtime-consume")
@RequiredArgsConstructor
public class RuntimeController {

    private final RuntimeClient runtimeClient;

    /**
     * 获取 Runtime 总览状态
     * 代理 Python: GET /api/runtime/status
     */
    @GetMapping("/status")
    public ResponseEntity<RuntimeClient.RuntimeStatusResponse> getStatus() {
        RuntimeClient.RuntimeStatusResponse status = runtimeClient.getStatus();
        if (status == null) {
            return ResponseEntity.internalServerError().build();
        }
        return ResponseEntity.ok(status);
    }

    /**
     * 获取 Runtime Sessions 列表
     * 代理 Python: GET /api/runtime/sessions
     */
    @GetMapping("/sessions")
    public ResponseEntity<List<RuntimeClient.RuntimeSessionDTO>> getSessions() {
        List<RuntimeClient.RuntimeSessionDTO> sessions = runtimeClient.getSessions();
        return ResponseEntity.ok(sessions);
    }

    /**
     * 获取 Runtime Plan
     * 代理 Python: GET /api/runtime/plan
     */
    @GetMapping("/plan")
    public ResponseEntity<RuntimeClient.RuntimePlanResponse> getPlan(
        @RequestParam(defaultValue = "claude") String executorType
    ) {
        RuntimeClient.RuntimePlanResponse plan = runtimeClient.getPlan(executorType);
        if (plan == null) {
            return ResponseEntity.internalServerError().build();
        }
        return ResponseEntity.ok(plan);
    }

    /**
     * 解释任务状态
     * 代理 Python: GET /api/runtime/explain/{task_id}
     */
    @GetMapping("/explain/{taskId}")
    public ResponseEntity<RuntimeClient.RuntimeExplainResponse> explainTask(
        @PathVariable String taskId
    ) {
        RuntimeClient.RuntimeExplainResponse explain = runtimeClient.explainTask(taskId);
        if (explain == null) {
            return ResponseEntity.notFound().build();
        }
        return ResponseEntity.ok(explain);
    }

    /**
     * 查询审计记录
     * 代理 Python: GET /api/runtime/action-audit
     */
    @GetMapping("/audit")
    public ResponseEntity<List<RuntimeClient.RuntimeAuditRecordDTO>> getAuditRecords(
        @RequestParam(required = false) String actionType,
        @RequestParam(required = false) String targetTaskId,
        @RequestParam(defaultValue = "50") int limit
    ) {
        List<RuntimeClient.RuntimeAuditRecordDTO> records =
            runtimeClient.getAuditRecords(actionType, targetTaskId, limit);
        return ResponseEntity.ok(records);
    }
}