package com.claudeflow.websocket;

import com.claudeflow.dto.ProgressUpdateEvent;
import com.claudeflow.dto.ToolCallEvent;
import com.claudeflow.dto.InterventionPromptEvent;
import com.claudeflow.sse.SseController;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * WebSocket处理器（接收Python端消息）
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class PythonWebSocketHandler extends TextWebSocketHandler {

    private final SseController sseController;
    private final ObjectMapper objectMapper;

    private final CopyOnWriteArrayList<WebSocketSession> sessions = new CopyOnWriteArrayList<>();

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        log.info("Python WebSocket connected: {}", session.getId());
        sessions.add(session);
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        log.debug("Received message from Python: {}", payload);

        try {
            Map<String, Object> data = objectMapper.readValue(payload, Map.class);
            String eventType = (String) data.get("event");

            switch (eventType) {
                case "progress_update":
                    ProgressUpdateEvent progressEvent = objectMapper.convertValue(
                            data.get("data"), ProgressUpdateEvent.class);
                    sseController.sendProgressUpdate(progressEvent);
                    break;

                case "tool_call":
                    ToolCallEvent toolEvent = objectMapper.convertValue(
                            data.get("data"), ToolCallEvent.class);
                    sseController.sendToolCall(toolEvent);
                    break;

                case "intervention_prompt":
                    InterventionPromptEvent interventionEvent = objectMapper.convertValue(
                            data.get("data"), InterventionPromptEvent.class);
                    sseController.sendInterventionPrompt(interventionEvent);
                    break;

                default:
                    log.warn("Unknown event type: {}", eventType);
            }
        } catch (Exception e) {
            log.error("Failed to process WebSocket message", e);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        log.info("Python WebSocket disconnected: {}", session.getId());
        sessions.remove(session);
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable exception) throws Exception {
        log.error("WebSocket transport error", exception);
        sessions.remove(session);
    }
}