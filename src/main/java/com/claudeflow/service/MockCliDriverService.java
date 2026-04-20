package com.claudeflow.service;

import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Mock CLI Driver服务实现
 * 用于Web控制台开发和测试
 */
@Service
@Profile("test")
public class MockCliDriverService implements CliDriverService {

    private final Map<String, MockSession> sessions = new ConcurrentHashMap<>();

    @Override
    public String startSession(String prompt) {
        String sessionId = UUID.randomUUID().toString();
        MockSession session = new MockSession(prompt);
        sessions.put(sessionId, session);
        // 添加模拟的初始事件
        session.addEvent(CliEvent.toolUse("Glob", Map.of("pattern", "src/**/*.java")));
        session.addEvent(CliEvent.checkpoint("cp_001", "Phase1", 1, "初始化完成"));
        return sessionId;
    }

    @Override
    public List<CliEvent> monitorEvents(String sessionId) {
        MockSession session = sessions.get(sessionId);
        if (session == null) {
            return Collections.emptyList();
        }
        return session.getEvents();
    }

    @Override
    public void intervene(String sessionId, String prompt) {
        MockSession session = sessions.get(sessionId);
        if (session != null) {
            session.addEvent(CliEvent.toolUse("Read", Map.of("file", prompt)));
            session.setStatus("running");
        }
    }

    @Override
    public void cancel(String sessionId) {
        MockSession session = sessions.get(sessionId);
        if (session != null) {
            session.setStatus("cancelled");
        }
    }

    @Override
    public String getSessionStatus(String sessionId) {
        MockSession session = sessions.get(sessionId);
        return session != null ? session.getStatus() : "unknown";
    }

    /**
     * Mock会话内部类
     */
    private static class MockSession {
        private final String prompt;
        private final List<CliEvent> events = new ArrayList<>();
        private String status = "running";

        MockSession(String prompt) {
            this.prompt = prompt;
        }

        void addEvent(CliEvent event) {
            events.add(event);
        }

        List<CliEvent> getEvents() {
            return new ArrayList<>(events);
        }

        String getStatus() {
            return status;
        }

        void setStatus(String status) {
            this.status = status;
        }
    }
}