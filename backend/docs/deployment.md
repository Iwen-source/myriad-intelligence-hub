# 部署文档 — AI赋能万象应用平台

---

## 目录

- [环境要求](#环境要求)
- [开发环境部署](#开发环境部署)
- [生产环境部署](#生产环境部署)
- [Docker 部署](#docker-部署)
- [环境变量配置](#环境变量配置)
- [Nginx 配置](#nginx-配置)
- [数据库初始化](#数据库初始化)
- [监控与日志](#监控与日志)
- [常见问题](#常见问题)

---

## 环境要求

### 最低配置（开发环境）

| 资源 | 要求 |
|------|------|
| CPU | 2核 |
| 内存 | 4GB |
| 磁盘 | 20GB |
| JDK | 17+ |
| MySQL | 8.0+ |
| Node.js | 18+ |

### 推荐配置（生产环境）

| 资源 | 要求 |
|------|------|
| CPU | 4核+ |
| 内存 | 8GB+ |
| 磁盘 | 50GB+ |
| JDK | 17 (GraalVM 或 OpenJDK) |
| MySQL | 8.0+ (主从或集群) |
| Nginx | 最新稳定版 |

---

## 开发环境部署

### 1. 后端启动

```bash
cd backend

# 编译
mvn clean install -DskipTests

# 开发模式启动（热重载）
mvn spring-boot:run -Dspring-boot.run.profiles=dev

# 或打包后启动
java -jar target/ai-empowerment-platform.jar \
  --spring.profiles.active=dev
```

后端默认端口：`8080`

### 2. 前端启动

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端默认端口：`5173`

### 3. API 文档

```bash
# 后端启动后
http://localhost:8080/swagger-ui/index.html
http://localhost:8080/v3/api-docs
```

---

## 生产环境部署

### 后端部署

#### Step 1: 打包

```bash
cd backend
mvn clean package -DskipTests -Pproduction
```

#### Step 2: 配置环境变量

```bash
# Linux/macOS
export DB_USERNAME=prod_user
export DB_PASSWORD=your_secure_password
export JWT_SECRET=your_jwt_secret_key_256bits
export JWT_EXPIRATION=86400000
export DEEPSEEK_API_KEY=sk-your-api-key
export DEEPSEEK_API_URL=https://api.deepseek.com
export DEEPSEEK_MODEL=deepseek-chat

# Windows PowerShell
$env:DB_USERNAME="prod_user"
$env:DB_PASSWORD="your_secure_password"
```

#### Step 3: 启动

```bash
# 直接启动
java -jar target/ai-empowerment-platform.jar \
  --spring.profiles.active=prod \
  --server.port=8080

# 推荐：使用 systemd 管理（Linux）
cat > /etc/systemd/system/ai-platform.service << 'EOF'
[Unit]
Description=AI Empowerment Platform
After=network.target mysql.service

[Service]
Type=simple
User=deploy
WorkingDirectory=/opt/ai-platform
EnvironmentFile=/opt/ai-platform/.env
ExecStart=/usr/bin/java -jar /opt/ai-platform/backend.jar --spring.profiles.active=prod
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable ai-platform
systemctl start ai-platform
```

#### Step 4: 验证

```bash
# 健康检查
curl http://localhost:8080/actuator/health

# 预期响应
{"status":"UP"}
```

### 前端部署

#### Step 1: 构建

```bash
cd frontend

# 设置API地址（修改 .env.production）
echo "VITE_API_BASE_URL=https://api.your-domain.com" > .env.production

# 构建
npm run build
```

构建产物在 `frontend/dist/` 目录。

#### Step 2: Nginx 部署

```nginx
# 将 dist/ 部署到 /var/www/ai-platform/
cp -r dist/* /var/www/ai-platform/
```

详见 [Nginx 配置](#nginx-配置) 章节。

---

## Docker 部署

### Docker Compose

创建 `docker-compose.yml`：

```yaml
version: '3.8'

services:
  mysql:
    image: mysql:8.0
    container_name: ai-mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: ai_empowerment
      MYSQL_CHARACTER_SET_SERVER: utf8mb4
      MYSQL_COLLATION_SERVER: utf8mb4_unicode_ci
    ports:
      - "3306:3306"
    volumes:
      - mysql-data:/var/lib/mysql
      - ./backend/scripts/schema.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ./backend/scripts/data.sql:/docker-entrypoint-initdb.d/02-data.sql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: ai-backend
    environment:
      - DB_USERNAME=root
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_URL=jdbc:mysql://mysql:3306/ai_empowerment?useUnicode=true&characterEncoding=utf-8&serverTimezone=Asia/Shanghai
      - JWT_SECRET=${JWT_SECRET}
      - JWT_EXPIRATION=${JWT_EXPIRATION}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DEEPSEEK_API_URL=${DEEPSEEK_API_URL}
    ports:
      - "8080:8080"
    depends_on:
      mysql:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: ai-frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  mysql-data:
```

### Dockerfile

**backend/Dockerfile**:

```dockerfile
FROM maven:3.9-eclipse-temurin-17 AS builder
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn clean package -DskipTests

FROM eclipse-temurin:17-jre
WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar", "--spring.profiles.active=prod"]
```

**frontend/Dockerfile**:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### 启动

```bash
# 复制环境变量
cp backend/.env.example .env
# 编辑 .env 填入配置

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止
docker-compose down
```

---

## 环境变量配置

### 完整环境变量列表

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `DB_USERNAME` | 是 | `root` | 数据库用户名 |
| `DB_PASSWORD` | 是 | 无 | 数据库密码 |
| `DB_URL` | 否 | `jdbc:mysql://localhost:3306/ai_empowerment?...` | 数据库连接URL |
| `JWT_SECRET` | 是 | 无 | JWT签名密钥（建议256位以上） |
| `JWT_EXPIRATION` | 否 | `86400000` | JWT过期时间(ms) |
| `DEEPSEEK_API_KEY` | 否 | 无 | DeepSeek API密钥 |
| `DEEPSEEK_API_URL` | 否 | `https://api.deepseek.com` | DeepSeek API地址 |
| `DEEPSEEK_MODEL` | 否 | `deepseek-chat` | DeepSeek模型名 |
| `SERVER_PORT` | 否 | `8080` | 后端端口 |

### .env 文件模板

```bash
# ===== 数据库配置 =====
DB_USERNAME=root
DB_PASSWORD=your_secure_password_here

# ===== JWT配置 =====
JWT_SECRET=your_jwt_secret_key_must_be_at_least_256_bits_long
JWT_EXPIRATION=86400000

# ===== DeepSeek AI 配置 =====
DEEPSEEK_API_KEY=sk-your-api-key-here
DEEPSEEK_API_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# ===== 服务器配置 =====
SERVER_PORT=8080
```

---

## Nginx 配置

### 前端 + API 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /var/www/ai-platform;
    index index.html;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml text/javascript image/svg+xml;
    gzip_min_length 1024;
    gzip_comp_level 6;

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8080/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # AI场景超时配置
        proxy_connect_timeout 60s;
        proxy_read_timeout 60s;
        proxy_send_timeout 60s;
    }

    # Swagger 文档
    location /swagger-ui/ {
        proxy_pass http://127.0.0.1:8080/swagger-ui/;
    }

    location /v3/api-docs {
        proxy_pass http://127.0.0.1:8080/v3/api-docs;
    }

    # SPA 路由
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### HTTPS 配置（推荐）

```bash
# 使用 Certbot 获取 SSL 证书
certbot --nginx -d your-domain.com

# 或手动配置
server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # ... 同上配置
}
```

---

## 数据库初始化

### 手动方式

```bash
# 登录MySQL
mysql -u root -p

# 创建数据库
CREATE DATABASE IF NOT EXISTS ai_empowerment
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE ai_empowerment;

# 导入表结构
SOURCE /path/to/backend/scripts/schema.sql;

# 导入初始数据
SOURCE /path/to/backend/scripts/data.sql;
```

### Spring Boot 自动方式

在 `application.yml` 中配置：

```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: update   # 自动创建/更新表结构
    show-sql: true       # 开发环境开启
```

生产环境建议使用 `validate` 模式：

```yaml
spring:
  jpa:
    hibernate:
      ddl-auto: validate
```

---

## 监控与日志

### Actuator 端点

项目已集成 Spring Boot Actuator：

```yaml
management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,logfile
  endpoint:
    health:
      show-details: when-authorized
```

访问：`http://localhost:8080/actuator/health`

### 日志配置

默认日志在 `logs/` 目录：

```yaml
logging:
  file:
    path: logs/
    name: logs/ai-platform.log
  level:
    com.aiempowerment: DEBUG
    org.springframework: WARN
```

### 性能指标

```bash
# JVM 指标
curl http://localhost:8080/actuator/metrics/jvm.memory.used

# HTTP 请求
curl http://localhost:8080/actuator/metrics/http.server.requests
```

---

## 常见问题

### Q: 启动报 MySQL 连接拒绝

**原因**: MySQL 未启动或连接配置错误

**解决**:
```bash
# 检查MySQL状态
systemctl status mysql

# 测试连接
mysql -u root -p -e "SELECT 1"

# 检查环境变量
echo $DB_USERNAME $DB_PASSWORD
```

### Q: JWT 密钥错误

**原因**: JWT 密钥为空或太短

**解决**: 设置一个至少256位的密钥（32+字符）

### Q: 前端 API 请求超时

**原因**: AI场景请求耗时较长，默认超时5秒太短

**解决**: 前端已调整为30秒超时，确认 `.env.production` 中配置正确

### Q: 数据库表未创建

**原因**: `ddl-auto` 配置为 `none` 或 `validate`

**解决**:
```bash
# 手动导入
mysql -u root -p ai_empowerment < backend/scripts/schema.sql
```

### Q: Swagger 页面 404

**原因**: 未添加 springdoc 依赖或未重启后端

**解决**:
```bash
# 确认依赖
mvn dependency:list | grep springdoc

# 确认访问路径
# 正确路径: http://localhost:8080/swagger-ui/index.html
```
