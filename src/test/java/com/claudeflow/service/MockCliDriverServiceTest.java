package com.claudeflow.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * MockCliDriverService测试
 * TDD: 测试Mock实现行为
 */
class MockCliDriverServiceTest {

    @Test
    @DisplayName("startSession创建有效会话")
    void startSession_createsValidSession() {
        MockCliDriverService service = new MockCliDriverService();

        String sessionId = service.startSession("test prompt");

        assertThat(sessionId).isNotNull();
        assertThat(sessionId).matches("[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}");
    }

    @Test
    @DisplayName("monitorEvents返回模拟事件")
    void monitorEvents_returnsMockEvents() {
        MockCliDriverService service = new MockCliDriverService();
        String sessionId = service.startSession("test prompt");

        List<CliEvent> events = service.monitorEvents(sessionId);

        assertThat(events).isNotEmpty();
        assertThat(events.get(0).getType()).isEqualTo("tool_use");
    }

    @Test
    @DisplayName("intervene添加事件到会话")
    void intervene_addsEventToSession() {
        MockCliDriverService service = new MockCliDriverService();
        String sessionId = service.startSession("test prompt");
        int initialEventCount = service.monitorEvents(sessionId).size();

        service.intervene(sessionId, "user intervention");

        List<CliEvent> events = service.monitorEvents(sessionId);
        assertThat(events.size()).isGreaterThan(initialEventCount);
    }

    @Test
    @DisplayName("cancel设置会话状态为cancelled")
    void cancel_setsCancelledStatus() {
        MockCliDriverService service = new MockCliDriverService();
        String sessionId = service.startSession("test prompt");

        service.cancel(sessionId);

        assertThat(service.getSessionStatus(sessionId)).isEqualTo("cancelled");
    }

    @Test
    @DisplayName("不同会话有不同ID")
    void differentSessions_haveDifferentIds() {
        MockCliDriverService service = new MockCliDriverService();

        String id1 = service.startSession("prompt1");
        String id2 = service.startSession("prompt2");

        assertThat(id1).isNotEqualTo(id2);
    }

    @Test
    @DisplayName("不存在的会话返回unknown状态")
    void unknownSession_returnsUnknownStatus() {
        MockCliDriverService service = new MockCliDriverService();

        String status = service.getSessionStatus("non-existent-id");

        assertThat(status).isEqualTo("unknown");
    }

    @Test
    @DisplayName("不存在的会话返回空事件列表")
    void unknownSession_returnsEmptyEvents() {
        MockCliDriverService service = new MockCliDriverService();

        List<CliEvent> events = service.monitorEvents("non-existent-id");

        assertThat(events).isEmpty();
    }
}