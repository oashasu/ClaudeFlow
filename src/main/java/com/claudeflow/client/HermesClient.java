package com.claudeflow.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.Map;

/**
 * Hermes服务客户端
 * 调用Python Hermes服务的API
 */
@Slf4j
@Component
public class HermesClient {

    @Value("${hermes.url:http://localhost:8000}")
    private String hermesUrl;

    private final RestTemplate restTemplate = new RestTemplate();

    /**
     * 启动CLI会话
     *
     * @param prompt 任务描述
     * @return session_id
     */
    public String startSession(String prompt) {
        try {
            String url = hermesUrl + "/api/session/start";

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, String> body = new HashMap<>();
            body.put("prompt", prompt);
            HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);

            ResponseEntity<Map> response = restTemplate.postForEntity(url, request, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                String sessionId = (String) response.getBody().get("session_id");
                log.info("Hermes session started: {}", sessionId);
                return sessionId;
            }

            log.error("Hermes start session failed: {}", response.getStatusCode());
            return null;

        } catch (Exception e) {
            log.error("Failed to call Hermes API: {}", e.getMessage());
            return null;
        }
    }

    /**
     * 取消会话
     *
     * @param sessionId 会话ID
     */
    public void cancelSession(String sessionId) {
        try {
            String url = hermesUrl + "/api/session/" + sessionId + "/cancel";
            restTemplate.postForEntity(url, null, Map.class);
            log.info("Hermes session cancelled: {}", sessionId);
        } catch (Exception e) {
            log.error("Failed to cancel Hermes session: {}", e.getMessage());
        }
    }

    /**
     * 干预会话
     *
     * @param sessionId 会话ID
     * @param prompt    干预内容
     */
    public void interveneSession(String sessionId, String prompt) {
        try {
            String url = hermesUrl + "/api/session/" + sessionId + "/intervene";

            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            Map<String, String> body = new HashMap<>();
            body.put("prompt", prompt);
            HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);

            restTemplate.postForEntity(url, request, Map.class);
            log.info("Hermes session intervened: {}", sessionId);
        } catch (Exception e) {
            log.error("Failed to intervene Hermes session: {}", e.getMessage());
        }
    }

    /**
     * 检查会话状态
     *
     * @param sessionId 会话ID
     * @return 状态字符串
     */
    public String getSessionStatus(String sessionId) {
        try {
            String url = hermesUrl + "/api/session/" + sessionId + "/status";
            ResponseEntity<Map> response = restTemplate.getForEntity(url, Map.class);

            if (response.getStatusCode() == HttpStatus.OK && response.getBody() != null) {
                return (String) response.getBody().get("status");
            }
            return "unknown";
        } catch (Exception e) {
            log.error("Failed to get Hermes session status: {}", e.getMessage());
            return "error";
        }
    }
}