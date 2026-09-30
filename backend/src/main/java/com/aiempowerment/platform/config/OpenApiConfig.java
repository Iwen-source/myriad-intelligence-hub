package com.aiempowerment.platform.config;

import io.swagger.v3.oas.models.ExternalDocumentation;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Contact;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.info.License;
import io.swagger.v3.oas.models.security.SecurityRequirement;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * OpenAPI 3.0 (Swagger) 配置
 */
@Configuration
public class OpenApiConfig {

    @Bean
    public OpenAPI customOpenAPI() {
        var securityScheme = new SecurityScheme()
                .type(SecurityScheme.Type.HTTP)
                .scheme("bearer")
                .bearerFormat("JWT")
                .description("输入JWT Token（不需要 Bearer 前缀）");

        var components = new io.swagger.v3.oas.models.Components()
                .addSecuritySchemes("bearerAuth", securityScheme);

        return new OpenAPI()
                .info(new Info()
                        .title("万象智枢 (MyriHub) API")
                        .description("万象智枢后端接口文档。涵盖能源管理、医疗诊断、环境监测、金融风控、交通仿真五大AI应用场景。")
                        .version("1.0.0")
                        .contact(new Contact()
                                .name("万象智枢")
                                .email("dev@myrihub.com"))
                        .license(new License()
                                .name("Apache 2.0")
                                .url("https://www.apache.org/licenses/LICENSE-2.0")))
                .externalDocs(new ExternalDocumentation()
                        .description("项目文档")
                        .url("https://github.com/myrihub"))
                .addSecurityItem(new SecurityRequirement().addList("bearerAuth"))
                .components(components);
    }
}
