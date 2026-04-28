package com.claudeflow.sse;

import com.claudeflow.dto.ProgressUpdateEvent;
import com.claudeflow.dto.ToolCallEvent;
import com.claudeflow.dto.InterventionPromptEvent;
import lombok.extern.slf4j.Slf4j;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Controller;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.IOException;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * SSE事件推送控制器
 */
@Slf4j
@Controller
public class SseController {

    private final List<SseEmitter> emitters = new CopyOnWriteArrayList<>();

    private static final long SSE_TIMEOUT = 30 * 60 * 1000L; // 30分钟

    /**
     * SSE事件流端点
     */
    @org.springframework.web.bind.annotation.GetMapping("/api/events/stream")
    public SseEmitter stream() {
        SseEmitter emitter = new SseEmitter(SSE_TIMEOUT);

        emitter.onCompletion(() -> {
            log.info("SSE emitter completed");
            emitters.remove(emitter);
        });

        emitter.onTimeout(() -> {
            log.info("SSE emitter timeout");
            emitters.remove(emitter);
        });

        emitter.onError(e -> {
            log.error("SSE emitter error", e);
            emitters.remove(emitter);
        });

        emitters.add(emitter);

        // 发送初始连接成功消息
        try {
            emitter.send(SseEmitter.event()
                    .name("connected")
                    .data("{\"status\":\"connected\"}"));
        } catch (IOException e) {
            log.error("Failed to send initial message", e);
        }

        return emitter;
    }

    /**
     * 发送进度更新事件
     */
    public void sendProgressUpdate(ProgressUpdateEvent event) {
        broadcast("progress_update", event);
    }

    /**
     * 发送工具调用事件
     */
    public void sendToolCall(ToolCallEvent event) {
        broadcast("tool_call", event);
    }

    /**
     * 发送等待介入事件
     */
    public void sendInterventionPrompt(InterventionPromptEvent event) {
        broadcast("intervention_prompt", event);
    }

    /**
     * 心跳机制（30秒）
     */
    @Scheduled(fixedRate = 30000)
    public void heartbeat() {
        broadcast("heartbeat", "{\"timestamp\":" + System.currentTimeMillis() + "}");
    }

    /**
     * 广播事件
     */
    private void broadcast(String eventName, Object data) {
        for (SseEmitter emitter : emitters) {
            try {
                emitter.send(SseEmitter.event()
                        .name(eventName)
                        .data(data));
            } catch (IOException e) {
                log.error("Failed to send SSE event", e);
                emitters.remove(emitter);
            }
        }
    }
}