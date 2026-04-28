package com.claudeflow.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

/**
 * 应用配置
 */
@Configuration
public class AppConfig {

    /**
     * RestTemplate Bean
     * 用于调用外部 API（Hermes, Runtime）
     */
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}