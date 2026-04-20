package com.claudeflow.service;

import java.util.List;

/**
 * CLI Driver服务接口
 * 定义Web控制台与CLI Driver的交互契约
 */
public interface CliDriverService {

    /**
     * 启动新会话
     * @param prompt 用户输入的提示词
     * @return 会话ID
     */
    String startSession(String prompt);

    /**
     * 监控事件流
     * @param sessionId 会话ID
     * @return 事件列表
     */
    List<CliEvent> monitorEvents(String sessionId);

    /**
     * 用户干预
     * @param sessionId 会话ID
     * @param prompt 用户输入
     */
    void intervene(String sessionId, String prompt);

    /**
     * 取消会话
     * @param sessionId 会话ID
     */
    void cancel(String sessionId);

    /**
     * 获取会话状态
     * @param sessionId 会话ID
     * @return 状态（running/paused/cancelled/completed）
     */
    String getSessionStatus(String sessionId);
}