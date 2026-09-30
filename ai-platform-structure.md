# AI赋能万象应用平台 — 完整项目结构

**Spring Boot 3.2 + Vue 3 + Element Plus + ECharts + DeepSeek API**

---

## 前端 Vue 3 应用层 (Frontend)

### 前端入口

- 🟢 **main.js (入口)** — ElementPlus + Pinia + Router
- **App.vue** — `<router-view />`
- **index.html** — Vite 挂载点
- **vite.config.js** — 端口3000 / /api → :8088
- **package.json** — Vue 3.4 / Element Plus

### 📡 API 层

- **api/index.js** — Axios实例 + 拦截器
- **api/auth.js** — login/register/me
- **api/modules.js** — ⭐ 全部业务API(200+行)

### 前端路由与状态管理

- **router/index.js** (路由+守卫)
- **stores/auth.js** (Pinia)

### 📄 页面视图 (16个Vue组件)

- **auth/** — Login.vue · Register.vue
- **development/ (5个)** — History · Pioneers · Applications · TechEvolution · Resources
- **核心布局** — Layout.vue · Home.vue
- **⭐ scenarios/ (6个场景)** — ScenariosIndex · Energy · Medical · Environment · Finance · Traffic
- **其他模块 (4个)** — Education.vue · Creative.vue · Forum.vue · Tools.vue

### 🧩 前端核心功能

- 暗色侧边栏导航 · 面包屑 · 用户头像下拉
- JWT拦截器 · 401自动跳转登录 · 路由守卫
- ECharts 图表 · CRUD 表格 · 表单校验

### 🔄 前端数据流

- 视图(Vue) → stores(Pinia) → api(axios) → /api/* → 后端
- 后端返回 → ApiResponse → 更新store → 视图响应式渲染
- 全局拦截器: 请求注入 Bearer Token · 响应401跳转登录

---

## 🌐 API 网关桥接

**Vite Proxy: localhost:3000/api → localhost:8088/api**

JWT Bearer Token 认证 | CORS 跨域允许 | JSON 数据交互

---

## 后端 Spring Boot 3.2 应用层 (Backend)

### 🟢 启动入口

**AiEmpowermentApplication.java** (Spring Boot 3.2 启动类 / Java 17)
- @SpringBootApplication | Maven: spring-boot-starter-parent 3.2.0

---

### ⚙️ 配置层 (config)

| 文件 | 说明 |
|------|------|
| CorsConfig.java | 跨域 |
| SecurityConfig.java | 安全 |
| DataInitializer.java | 数据初始化 |

- **Security**: 关闭CSRF · 无状态Session · /auth /public /h2-console 放行 · JWT Filter
- **DataInit**: 🟡 700+行种子数据 · 7大模块初始化 · 默认admin/admin123456

### 🛡️ 安全层 (security)

| 文件 | 说明 |
|------|------|
| JwtTokenProvider.java | JWT令牌提供 |
| JwtAuthenticationFilter.java | JWT认证过滤器 |
| CustomUserDetailsService.java | 用户详情服务 |

- JWT: HMAC-SHA256 · 24h过期 · BASE64密钥 · Bearer头传递

### 🎯 控制器层 — 15个 @RestController (@RequiredArgsConstructor 注入Service)

| 控制器 | 路由 |
|--------|------|
| AuthController | /auth/** |
| PublicController | /public/** |
| DevelopmentController | /development/** |
| AiPioneerController | /pioneers |
| AiApplicationController | /ai-applications |
| EnergyController | /energy/** |
| MedicalController | /medical/** |
| EnvironmentController | /environment/** |
| FinanceController | /finance/** |
| TrafficController | /traffic/** |
| EducationController | /education/** |
| CreativeController | /creative/** |
| ForumController | /forum/** |
| ToolController | /tools/** |

每个Controller通过 @RequiredArgsConstructor 注入对应 Service

### 📦 公共基础 (common)

| 文件 | 说明 |
|------|------|
| ApiResponse.java | 统一响应 |
| BusinessException.java | 业务异常 |
| GlobalExceptionHandler.java | 全局异常处理 |

- ApiResponse: 200/400/401/403/404/500 统一格式
- ApiResponse\<T\> { code, message, data }

### 📨 DTO (数据传输对象)

- LoginRequest.java
- RegisterRequest.java
- ToolQueryRequest.java

### 📦 实体层 — 20个 JPA @Entity

| 实体 | 说明 |
|------|------|
| User | 用户 |
| AiApplication | AI应用案例 |
| AiPioneer | AI先驱者 |
| ForumPost | 论坛帖子 |
| Tool | 开发工具 |
| ToolComment | 工具评论 |
| EducationCourse | 教育课程 |
| EducationResource | 教育资源 |
| DesignProject | 设计项目 |
| OperationLog | 操作日志 |
| EnergyDevice | 能源设备 |
| EnergyConsumptionRecord | 能耗记录 |
| DeviceMaintenanceRecord | 设备维护记录 |
| MedicalPatient | 医疗患者 |
| MedicalDiagnosisResult | 诊断结果 |
| EnvironmentMonitorPoint | 环境监测点 |
| AirQualityRecord | 空气质量记录 |
| FinanceTransaction | 金融交易 |
| RiskAlertRule | 风控规则 |
| TrafficRoadSection | 道路路段 |
| TrafficFlowRecord | 交通流量 |

每个Entity映射一张表 · @Data · @NoArgsConstructor · JPA自动建表 (ddl-auto: update)

### 📡 Repository 接口层

20个 JpaRepository 接口 (继承 JpaRepository\<Entity, IdType\>)

- UserRepo · AiAppRepo · AiPioneerRepo · ForumPostRepo · ToolRepo · ToolCommentRepo · EducationCourseRepo
- EducationResourceRepo · DesignProjectRepo · OperationLogRepo · EnergyDeviceRepo · EnergyConsumptionRepo
- DeviceMaintenanceRepo · MedicalPatientRepo · MedicalDiagnosisRepo · EnvPointRepo · AirQualityRepo
- FinanceTransactionRepo · RiskAlertRuleRepo · TrafficRoadSectionRepo · TrafficFlowRepo

### 🎯 业务服务接口 — 14个 Service 接口 (interface)

| 服务接口 | 说明 |
|---------|------|
| ⭐ AIAnalysisService | 统一AI分析引擎 |
| AuthService | 认证服务 |
| AiAppService | 应用服务 |
| AiPioneerService | 先驱者服务 |
| CreativeService | 创意设计服务 |
| EducationService | 教育服务 |
| EnergyService | 能源服务 |
| EnvService | 环境服务 |
| FinanceService | 金融风控服务 |
| ForumService | 论坛服务 |
| MedicalService | 医疗服务 |
| ToolService | 工具服务 |
| TrafficService | 交通服务 |

### 实现层 — 14个 @Service 实现类 (implements + @RequiredArgsConstructor注入Repository)

| 实现类 | 说明 |
|--------|------|
| ⭐ AIAnalysisServiceImpl | 规则引擎+随机模拟 |
| AuthServiceImpl | JWT登录/注册 |
| AiAppServiceImpl | CRUD |
| AiPioneerServiceImpl | CRUD |
| CreativeServiceImpl | CRUD+分析 |
| EducationServiceImpl | CRUD+分析 |
| EnergyServiceImpl | CRUD+分析 |
| EnvServiceImpl | CRUD+分析 |
| FinanceServiceImpl | CRUD+风控 |
| TrafficServiceImpl | CRUD+分析 |
| ForumServiceImpl | CRUD |
| ToolServiceImpl | CRUD |
| MedicalServiceImpl | CRUD |
| **MedicalAiDoctorService** | AI问诊 · 症状分析 |
| **MedicalAiModelService** | 🟡 调DeepSeek |

### 🗄️ 数据持久层

| 环境 | 配置 |
|------|------|
| **开发环境: H2 嵌入式数据库** | jdbc:h2:~/ai_platform_db · MODE=MySQL兼容 · Web Console |
| **⛔ 生产环境: MySQL** | localhost:3306/ai_application · HikariPool · characterEncoding=utf-8 |
| **🚀 AI外部接口** | DeepSeek Chat API · https://api.deepseek.com/v1 |

---

## 图例

| 颜色 | 含义 |
|------|------|
| 🟦 入口/配置 | 入口/配置 |
| 🟧 控制器/服务 | 控制器/服务 |
| 🟩 实体/数据 | 实体/数据 |
| 🟨 前端页面 | 前端页面 |
| ⬜ 工具/公共 | 工具/公共 |
| 🟥 安全/AI集成 | 安全/AI集成 |

数据源: 扫描日期 2026-05-20
