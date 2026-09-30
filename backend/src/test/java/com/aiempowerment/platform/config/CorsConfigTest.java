package com.aiempowerment.platform.config;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import org.springframework.web.filter.CorsFilter;

import static org.junit.jupiter.api.Assertions.*;

/**
 * CorsConfig 单元测试
 */
class CorsConfigTest {

    @Test
    void testCorsConfigCreatesFilter() {
        CorsConfig config = new CorsConfig();
        ReflectionTestUtils.setField(config, "allowedOriginsStr",
                "http://localhost:5173,http://test.com");

        CorsFilter filter = config.corsFilter();
        assertNotNull(filter, "CorsFilter 不应为 null");
    }

    @Test
    void testCorsConfigWithWildcard() {
        CorsConfig config = new CorsConfig();
        ReflectionTestUtils.setField(config, "allowedOriginsStr", "*");

        CorsFilter filter = config.corsFilter();
        assertNotNull(filter, "通配符 CORS 配置不应为 null");
    }
}
