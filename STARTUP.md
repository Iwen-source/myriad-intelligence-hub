# 🚀 万象智枢 (MyriHub) — 启动指南

## 前置条件

| 工具 | 版本要求 | 检查命令 |
|------|----------|----------|
| JDK | 17+ | `java -version` |
| Maven | 3.6+ | `mvn --version` |
| Node.js | 18+ | `node --version` |
| MySQL | 8.0+ | 必须运行中 |

## 一键启动（交给豆芽）

> 直接对我说「启动系统」就行了，不用记命令。

---

## 手动启动

### 1️⃣ 确保 MySQL 运行

```bash
net start MySQL80        # 如果 MySQL 没启动
```

### 2️⃣ 启动后端（终端 1）

```bash
cd backend
mvn spring-boot:run -DskipTests
```

✅ 看到以下日志即成功：
```
Started AiEmpowermentApplication in 3.6 seconds
已创建管理员账号 admin（初始口令来自环境变量 ADMIN_INIT_PASSWORD）
```

### 3️⃣ 启动前端（终端 2）

```bash
cd frontend
npm run dev
```

✅ 看到以下日志即成功：
```
VITE v5.4.21  ready in 3.0 s
➜  Local:   http://localhost:3000/
```

### 4️⃣ 打开浏览器

访问 **[http://localhost:3000](http://localhost:3000)**

| 账号 | 密码 |
|------|------|
| `admin` | `admin123456` |

---

## 常见问题

| 问题 | 解决 |
|------|------|
| `Port 8088 already in use` | 有旧 Java 进程残留 → `netstat -ano \| findstr :8088` 查 PID，任务管理器杀掉 |
| `Port 3000 already in use` | 有旧 Node 进程残留 → 同上查:3000 杀 PID，或 Vite 会自动跳到 3001 |
| 页面白屏 / 接口 401 | 后端还在启动中，等出现 `Started` 再刷新 |
| MySQL 连接失败 | 检查 MySQL80 服务是否正在运行 |

---

## 访问地址

- 🌐 **前端页面** → `http://localhost:3000`
- 🖥 **后端 API** → `http://localhost:8088/api`
- 📘 **Swagger 文档** → `http://localhost:8088/api/swagger-ui.html`

---

## 项目目录

```
myriad-intelligence-hub
├── backend/          Spring Boot 3.2 后端 (Java 17)
│   └── src/main/java/com/aiempowerment/platform/
│       ├── controller/     12 个 REST 控制器
│       ├── service/        业务逻辑 + AI 分析服务
│       ├── model/          实体 + DTO
│       └── repository/     JPA 数据访问
├── frontend/         Vue 3 前端 (Vite)
│   └── src/
│       ├── views/          页面组件
│       ├── components/     通用组件
│       ├── api/            API 调用
│       └── router/         路由
├── python/           训练脚本 + ML 模型
└── data/             数据集
```
