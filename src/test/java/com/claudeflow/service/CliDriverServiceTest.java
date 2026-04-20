package com.claudeflow.service;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * CliDriverService接口测试
 * TDD: 测试定义接口契约
 */
class CliDriverServiceTest {

    @Test
    @DisplayName("startSession返回有效的sessionId")
    void startSession_returnsValidSessionId() {
        CliDriverService service = new MockCliDriverService();

        String sessionId = service.startSession("test prompt");

        assertThat(sessionId).isNotNull();
        assertThat(sessionId).isNotEmpty();
    }

    @Test
    @DisplayName("monitorEvents返回事件列表")
    void monitorEvents_returnsEventList() {
        CliDriverService service = new MockCliDriverService();
        String sessionId = service.startSession("test prompt");

        List<CliEvent> events = service.monitorEvents(sessionId);

        assertThat(events).isNotNull();
    }

    @Test
    @DisplayName("intervene调用成功")
    void intervene_succeeds() {
        CliDriverService service = new MockCliDriverService();
        String sessionId = service.startSession("test prompt");

        service.intervene(sessionId, "user input");

        // 验证intervene成功执行（无异常）
        assertThat(service.monitorEvents(sessionId)).isNotEmpty();
    }

    @Test
    @DisplayName("cancel终止会话")
    void cancel_terminatesSession() {
        CliDriverService service = new MockCliDriverService();
        String sessionId = service.startSession("test prompt");

        service.cancel(sessionId);

        // 验证会话被取消
        assertThat(service.getSessionStatus(sessionId)).isEqualTo("cancelled");
    }

    @Test
    @DisplayName("每个startSession返回唯一sessionId")
    void startSession_returnsUniqueIds() {
        CliDriverService service = new MockCliDriverService();

        String id1 = service.startSession("prompt1");
        String id2 = service.startSession("prompt2");

        assertThat(id1).isNotEqualTo(id2);
    }
}