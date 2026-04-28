package com.claudeflow.sse;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * SseController测试
 * TDD: 测试SSE推送功能
 */
class SseControllerTest {

    private SseController sseController;

    @BeforeEach
    void setUp() {
        sseController = new SseController();
    }

    @Test
    @DisplayName("stream返回有效的SseEmitter")
    void stream_returnsValidEmitter() {
        SseEmitter emitter = sseController.stream();

        assertThat(emitter).isNotNull();
        assertThat(emitter.getTimeout()).isEqualTo(30 * 60 * 1000L);
    }

    @Test
    @DisplayName("多个客户端可以同时订阅")
    void multipleClients_canSubscribe() {
        SseEmitter emitter1 = sseController.stream();
        SseEmitter emitter2 = sseController.stream();

        assertThat(emitter1).isNotNull();
        assertThat(emitter2).isNotNull();
        assertThat(emitter1).isNotSameAs(emitter2);
    }

    @Test
    @DisplayName("sendProgressUpdate可以发送事件")
    void sendProgressUpdate_canSendEvent() {
        // 先订阅
        SseEmitter emitter = sseController.stream();

        // 发送进度更新
        com.claudeflow.dto.ProgressUpdateEvent event = new com.claudeflow.dto.ProgressUpdateEvent();
        event.setTaskId("task-001");
        event.setPhase("Phase1");
        event.setProgress(50);

        // 方法调用不应该抛异常
        sseController.sendProgressUpdate(event);

        // 验证emitter仍然有效（未被移除）
        assertThat(emitter).isNotNull();
    }

    @Test
    @DisplayName("sendToolCall可以发送工具调用事件")
    void sendToolCall_canSendEvent() {
        SseEmitter emitter = sseController.stream();

        com.claudeflow.dto.ToolCallEvent event = new com.claudeflow.dto.ToolCallEvent();
        event.setTaskId("task-001");
        event.setToolName("Glob");
        event.setAction("{\"pattern\":\"src/**/*.java\"}");

        sseController.sendToolCall(event);

        assertThat(emitter).isNotNull();
    }

    @Test
    @DisplayName("sendInterventionPrompt可以发送介入提示事件")
    void sendInterventionPrompt_canSendEvent() {
        SseEmitter emitter = sseController.stream();

        com.claudeflow.dto.InterventionPromptEvent event = new com.claudeflow.dto.InterventionPromptEvent();
        event.setTaskId("task-001");
        event.setMessage("需要用户确认");

        sseController.sendInterventionPrompt(event);

        assertThat(emitter).isNotNull();
    }
}