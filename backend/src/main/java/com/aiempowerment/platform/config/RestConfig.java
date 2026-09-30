package com.aiempowerment.platform.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.client.RestTemplate;

/**
 * HTTP 客户端配置 — 用于调用 Python ML Server
 */
@Configuration
public class RestConfig {

    @Bean
    public RestTemplate pythonMlRestTemplate() {
        RestTemplate restTemplate = new RestTemplate();
        restTemplate.setRequestFactory(new org.springframework.http.client.SimpleClientHttpRequestFactory() {{
            setConnectTimeout(10000);
            setReadTimeout(30000);
        }});
        return restTemplate;
    }
}
