# AI赋能万象应用平台 · 完整项目树状结构

**Spring Boot 3.2 + Vue 3 + Element Plus + ECharts + DeepSeek ｜ 总计 100+ 个文件**

---

## 项目根目录

```
ai-empowerment-platform/        项目根目录
```

---

## backend/ — Spring Boot 3.2 后端

```
backend/
├── pom.xml                     Java 17 · Spring Boot 3.2.0 · JJWT 0.12.3 · MySQL · H2 · Lombok · Commons Lang3
├── application.yml             端口8088 · H2 · JWT 24h · DeepSeek API Key
├── application-mysql.yml       MySQL 8 · HikariCP · localhost:3306/ai_application
└── src/java/com/aiempowerment/platform/
    ├── AiEmpowermentApplication.java    @SpringBootApplication · 启动入口类
    │
    ├── config/
    │   ├── CorsConfig.java              CORS跨域 · allowedOriginPatterns=*
    │   ├── SecurityConfig.java          SecurityFilterChain · 无状态Session · JWT Filter · BCryptPasswordEncoder
    │   └── DataInitializer.java         700+行 · 8大模块种子数据 · 默认管理员 admin/123456
    │
    ├── security/
    │   ├── JwtTokenProvider.java        HMAC-SHA256密钥 · generateToken · validateToken · 24h过期
    │   ├── JwtAuthenticationFilter.java OncePerRequestFilter · Bearer Token解析 · SecurityContext设置
    │   └── CustomUserDetailsService.java UserDetailsService · loadUserByUsername
    │
    ├── common/
    │   ├── ApiResponse.java             统一响应格式 · success/error/unauthorized/forbidden/badRequest
    │   ├── BusinessException.java       RuntimeException · 业务异常基类
    │   └── GlobalExceptionHandler.java  @RestControllerAdvice · 全局异常拦截处理
    │
    ├── model/dto/
    │   ├── LoginRequest.java            username + password · JSR303校验
    │   ├── RegisterRequest.java         username + password + nickname + email
    │   └── ToolQueryRequest.java        keyword + category + page + size
    │
    ├── model/entity/                    【20个 JPA @Entity】
    │   │
    │   ├── User.java                    id/username/password/nickname/email/avatar
    │   ├── AiPioneer.java               name/category/era/contribution
    │   ├── AiApplication.java           applicationName/industry/techStack
    │   ├── ForumPost.java               title/content/category/authorId
    │   ├── Tool.java                    name/category/url/description
    │   ├── ToolComment.java             toolId/content/authorId
    │   ├── EducationCourse.java         courseName/subject/difficulty
    │   ├── EducationResource.java       title/type/url/subject
    │   ├── DesignProject.java           projectName/style/tags/status
    │   ├── OperationLog.java            userId/action/module/target
    │   ├── EnergyDevice.java            deviceId/name/type/location/power
    │   ├── EnergyConsumptionRecord.java recordId/deviceId/date/consumption
    │   ├── DeviceMaintenanceRecord.java maintenanceId/deviceId/date/desc
    │   ├── MedicalPatient.java          patientId/name/gender/age/symptoms
    │   ├── MedicalDiagnosisResult.java  resultId/patientId/result/date
    │   ├── EnvironmentMonitorPoint.java pointName/location/lon/lat/type
    │   ├── AirQualityRecord.java        pointId/aqi/pm25/pm10/o3/no2
    │   ├── FinanceTransaction.java      txNo/userId/amount/riskScore
    │   ├── RiskAlertRule.java           ruleName/type/condition/threshold
    │   ├── TrafficRoadSection.java      sectionName/length/lanes/speed
    │   └── TrafficFlowRecord.java       sectionId/time/flowCount/speed
    │
    ├── repository/                      【20个 JpaRepository<Entity, Id>】
    │   ├── UserRepo · AiPioneerRepo · AiApplicationRepo · ForumPostRepo · ToolRepo · ToolCommentRepo
    │   ├── EducationCourseRepo · EducationResourceRepo · DesignProjectRepo · OperationLogRepo
    │   ├── EnergyDeviceRepo · EnergyConsumptionRepo · DeviceMaintenanceRepo · MedicalPatientRepo
    │   ├── MedicalDiagnosisRepo · EnvPointRepo · AirQualityRepo · FinanceTransactionRepo
    │   └── RiskAlertRuleRepo · TrafficRoadSectionRepo · TrafficFlowRepo
    │
    └── service/                         【14个接口 + 14个实现类】
        │
        ├── AIAnalysisService.java       ⭐ 核心：统一AI分析引擎 · 8大领域50+方法
        ├── AuthService.java             → AuthServiceImpl · JWT登录/注册
        ├── AiApplicationService.java    → AiApplicationServiceImpl · CRUD
        ├── AiPioneerService.java        → AiPioneerServiceImpl · CRUD
        ├── EnergyService.java           → EnergyServiceImpl · 设备CRUD + 统计分析
        ├── EnvironmentService.java      → EnvironmentServiceImpl · CRUD + 统计
        ├── FinanceService.java          → FinanceServiceImpl · 交易CRUD + 风控
        ├── TrafficService.java          → TrafficServiceImpl · 路段CRUD + 交通分析
        ├── MedicalService.java          → MedicalServiceImpl · 患者/诊断CRUD
        ├── EducationService.java        → EducationServiceImpl · 课程CRUD
        ├── CreativeService.java         → CreativeServiceImpl · 项目CRUD
        ├── ForumService.java            → ForumServiceImpl · 帖子CRUD
        ├── ToolService.java             → ToolServiceImpl · 工具CRUD
        │
        ├── AIAnalysisServiceImpl.java    规则计算 + 统计分析 + 模拟数据
        ├── MedicalAiDoctorService.java   AI问诊 · 症状分析
        └── MedicalAiModelService.java    DeepSeek API 真实AI大模型调用
```

### controller/ — 15个 @RestController

| Controller | 路由 |
|-----------|------|
| **AuthController.java** | POST /auth/login · POST/register · GET /me |
| PublicController.java | GET /public/navigation |
| DevelopmentController.java | /development/history · /resources · /tech-evolution |
| AiPioneerController.java | CRUD /pioneers |
| AiApplicationController.java | CRUD /ai-applications · GET /industries |
| EnergyController.java | /energy/devices · /consumption · /maintenance · /statistics · /analysis/** |
| MedicalController.java | /medical/patients · /diagnosis · /analysis · /ai-doctor · /ai-model |
| EnvironmentController.java | /environment/points · /data · /summary · /analysis/** |
| FinanceController.java | /finance/transactions · /rules · /dashboard · /analysis/** |
| TrafficController.java | /traffic/sections · /flow · /overview · /analysis/** |
| EducationController.java | /education/courses · /resources · /subjects · /analysis/** |
| CreativeController.java | /creative/projects · /overview · /planar-designs · /analysis/** |
| ForumController.java | /forum/posts · /stats · /analysis/** |
| ToolController.java | /tools · /tools/{id}/comments · /tools/analysis/** |

---

## frontend/ — Vue 3 + Vite 前端

```
frontend/
├── package.json                Vue 3.4 · Element Plus 2.5 · Axios · ECharts 5.5 · Pinia · Vue Router 4
├── vite.config.js              Vite 5 · 端口3000 · /api → localhost:8088 代理
├── index.html
└── src/
    ├── main.js                 🟢 入口：ElementPlus · Pinia · Router · 图标注册
    ├── App.vue                 根组件 · <router-view />
    │
    ├── api/
    │   ├── index.js            Axios实例 · JWT拦截 · 401跳转
    │   ├── auth.js             login · register · getCurrentUser
    │   └── modules.js          ⭐ 全部业务API · 200+行
    │
    ├── router/index.js         18条路由 · 导航守卫 · 动态title · JWT校验
    ├── stores/auth.js          Pinia · token/user · login/register/logout
    │
    └── views/                  【16个页面组件】
        │
        ├── Layout.vue          核心布局：暗色侧边栏 · el-header · el-main · 面包屑
        ├── Home.vue            首页
        │
        ├── auth/
        │   ├── Login.vue       登录页 · 表单校验
        │   └── Register.vue    注册页
        │
        ├── development/        AI发展概述
        │   ├── History.vue     AI时间线 · 历史沿革
        │   ├── Pioneers.vue    AI先驱者 · 人物卡片 · CRUD
        │   ├── Applications.vue AI应用案例 · 行业分类 · CRUD
        │   ├── TechEvolution.vue AI技术演进 · 里程碑
        │   └── Resources.vue   AI学习资源
        │
        ├── scenarios/          ⭐ 核心：AI应用场景
        │   ├── ScenariosIndex.vue  场景概览 · 5大入口
        │   ├── Energy.vue          ⚡能源管理 · CRUD+图表+预测
        │   ├── Medical.vue         🏥医疗诊断 · CRUD+AI问诊
        │   ├── Environment.vue     🌿环境监测 · CRUD+预测+分析
        │   ├── Finance.vue         💰金融风控 · CRUD+风险评估
        │   └── Traffic.vue         🚗交通仿真 · CRUD+拥堵预测+仿真
        │
        ├── Education.vue       📚 AI赋能教育 · 课程·知识图谱·学习路径
        ├── Creative.vue        🎨 AI创意设计 · 项目·平面·3D·风格推荐
        │
        └── forum/
            ├── Forum.vue       论坛交流 · CRUD · AI热点分析
            └── Tools.vue       开发工具 · CRUD · AI推荐
```

---

## 📦 项目依赖全景

### 前端依赖

- Vue 3.4 · Vue Router 4 · Pinia 2
- Element Plus 2.5 · @element-plus/icons-vue
- Axios 1.6 · ECharts 5.5 · vue-echarts 6.6
- Vite 5 · @vitejs/plugin-vue 5

### 后端依赖

- Spring Boot 3.2.0 · Spring Web · Spring Data JPA
- Spring Security · Spring Validation
- MySQL Connector-J · H2 Database (内嵌)
- JJWT 0.12.3 · Lombok · Commons Lang3

### 🔥 AI 能力

- **DeepSeek Chat API** (真实大模型调用)
  - → MedicalAiModelService · AI智能问诊
- **AIAnalysisService** (50+方法)
  - → 规则计算 + 统计分析 + 模拟数据

---

## 项目统计

- **后端**：1 启动类 + 3 配置 + 3 安全 + 3 公共 + 3 DTO + 20 Entity + 20 Repository + 14 Service(14实现) + 15 Controller
- **前端**：1 entry + 1 App + 3 api + 1 router + 1 store + 16 views + 1 vite config + 1 package
- **总计约 120+ 个源文件**

扫描日期: 2026-05-20
