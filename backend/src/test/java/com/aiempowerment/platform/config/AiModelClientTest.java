package com.aiempowerment.platform.config;

import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.*;

/**
 * AiModelClient 单元测试
 * 验证环境变量回退逻辑和 API 状态判断
 */
class AiModelClientTest {

    private AiModelClient createClientWithKey(String apiKey) {
        AiModelClient client = new AiModelClient();
        ReflectionTestUtils.setField(client, "apiKey", apiKey);
        return client;
    }

    @Test
    void testIsAvailableReturnsFalseWhenKeyIsNull() {
        AiModelClient client = new AiModelClient();
        assertFalse(client.isAvailable(), "空API Key时 should not be available");
    }

    @Test
    void testIsAvailableReturnsFalseWhenKeyIsBlank() {
        AiModelClient client = createClientWithKey("");
        assertFalse(client.isAvailable(), "空API Key时 should not be available");
    }

    @Test
    void testIsAvailableReturnsFalseWhenKeyIsPlaceholder() {
        AiModelClient client = createClientWithKey("sk-your-real-api-key-here");
        assertFalse(client.isAvailable(), "占位符API Key时 should not be available");
    }

    @Test
    void testIsAvailableReturnsFalseWhenKeyStartsWithReplace() {
        AiModelClient client = createClientWithKey("REPLACE_WITH_YOUR_KEY");
        assertFalse(client.isAvailable(), "含REPLACE的API Key时 should not be available");
    }

    @Test
    void testIsAvailableReturnsTrueForValidKey() {
        AiModelClient client = createClientWithKey("sk-valid-key-12345");
        assertTrue(client.isAvailable(), "正常API Key时 should be available");
    }

    @Test
    void testCallReturnsNullWhenNotAvailable() {
        AiModelClient client = createClientWithKey("");
        assertNull(client.call("test", "hello"));
    }
}
