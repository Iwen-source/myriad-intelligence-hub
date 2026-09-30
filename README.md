# 万象智枢 (MyriHub)

> 基于 **Spring Boot 3.2 + Vue 3 + MySQL** 的前后端分离智能分析平台，覆盖 **能源管理、环境监测、金融风控、医疗诊断、交通仿真** 五大核心AI应用场景。

---

## 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [模块架构](#模块架构)
- [AI分析服务](#ai分析服务)
- [API文档](#api文档)
- [测试](#测试)
- [性能](#性能)
- [部署](#部署)
- [项目结构](#项目结构)

---

## 项目概述

万象智枢是一款前后端分离的智能分析平台，将人工智能技术（大语言模型、预测分析、异常检测等）融入多个业务场景，展示AI在实际应用中的价值。

### 核心场景

| 场景 | 功能 | AI能力 |
|------|------|--------|
| 🔋 **能源管理** | 设备监控、能耗分析、异常检测 | 能耗趋势预测、设备异常检测、节能优化建议 |
| 🌿 **环境监测** | 空气质量监测、污染预警、健康评估 | AQI预测、污染源分析、多因子智能预测 |
| 💰 **金融风控** | 交易管理、风险评分、反欺诈 | 交易风险评估、规则命中分析、用户行为画像 |
| 🏥 **医疗诊断** | 患者管理、病历查询、AI问诊 | 症状-疾病分析、相似病例推荐、诊断趋势分析 |
| 🚦 **交通仿真** | 流量监控、拥堵预测、路线优化 | 拥堵预测、沙盘模拟、级联影响分析 |

---

## 技术栈

### 后端

| 组件 | 版本 | 用途 |
|------|------|------|
| Spring Boot | 3.2.0 | 应用框架 |
| Spring Security | 6.x | 认证授权（JWT） |
| Spring Data JPA | 3.x | ORM 持久化 |
| MySQL | 8.x | 关系型数据库 |
| Lombok | 1.18.30 | 代码简化 |
| SpringDoc OpenAPI | 2.3.0 | API文档 |
| Maven | 3.x | 构建管理 |

### 前端

| 组件 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.x | 前端框架 |
| Element Plus | 2.x | UI组件库 |
| ECharts | 5.x | 数据可视化 |
| Vue Router | 4.x | 前端路由 |
| Pinia | 2.x | 状态管理 |
| Axios | 1.x | HTTP客户端 |

---

## 快速开始

### 前置要求

- JDK 17+
- Maven 3.6+
- Node.js 18+
- MySQL 8.0+
- npm / pnpm

### 1. 克隆项目

```bash
git clone <repository-url>
cd ai-empowerment-platform
```

### 2. 配置数据库

```bash
# 创建MySQL数据库
mysql -u root -p -e "CREATE DATABASE ai_empowerment DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 导入表结构（scripts/目录下）
mysql -u root -p ai_empowerment < backend/scripts/schema.sql
mysql -u root -p ai_empowerment < backend/scripts/data.sql
```

### 3. 配置环境变量

```bash
# 复制环境变量模板
cp backend/.env.example backend/.env
# 编辑 .env 填入实际配置
```

必要环境变量：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `DB_USERNAME` | 数据库用户名 | `root` |
| `DB_PASSWORD` | 数据库密码 | (必填) |
| `JWT_SECRET` | JWT签名密钥 | (必填) |
| `JWT_EXPIRATION` | JWT过期时间(ms) | `86400000` |
| `DEEPSEEK_API_KEY` | DeepSeek API密钥 | (可选) |
| `DEEPSEEK_API_URL` | DeepSeek API地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | DeepSeek模型名 | `deepseek-chat` |

### 4. 启动后端

```bash
cd backend
mvn clean install -DskipTests
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

启动后访问：`http://localhost:8080`

### 5. 启动前端

```bash
cd frontend
npm install
npm run dev
```

启动后访问：`http://localhost:5173`

### 6. 访问API文档

```bash
# 后端启动后
http://localhost:8080/swagger-ui/index.html
http://localhost:8080/v3/api-docs
```

---

## 模块架构

```
┌──────────────────────────────────────────────────────────┐
│                     Web 前端 (Vue 3)                      │
│  ┌──────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐   │
│  │ 路由 │ │ 组件(Ele+)│ │ 状态管理 │ │ ECharts 图表   │   │
│  └──────┘ └──────────┘ └──────────┘ └────────────────┘   │
└──────────────────────┬───────────────────────────────────┘
                       │ REST API (JSON)
┌──────────────────────┴───────────────────────────────────┐
│                Spring Boot 后端                            │
│  ┌──────────────────────────────────────────────┐        │
│  │             Controller 层                     │        │
│  │  Energy / Environment / Finance / Medical    │        │
│  │  Traffic / Education / Creative / Forum      │        │
│  └──────────────────┬───────────────────────────┘        │
│  ┌──────────────────┴───────────────────────────┐        │
│  │            Service 层                         │        │
│  │  ┌────────────────┐  ┌────────────────────┐   │        │
│  │  │  业务ServiceImpl │  │ AI分析服务(分析专区) │   │        │
│  │  │ (CRUD/查询)     │  │ (预测/检测/评估)   │   │        │
│  │  └────────────────┘  └────────────────────┘   │        │
│  └──────────────────┬───────────────────────────┘        │
│  ┌──────────────────┴───────────────────────────┐        │
│  │            Repository (JPA)                   │        │
│  └──────────────────┬───────────────────────────┘        │
└──────────────────────┴───────────────────────────────────┘
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
           MySQL              DeepSeek API
```

---

## AI分析服务

项目核心亮点是统一且丰富的AI分析引擎。所有AI分析功能通过 `AIAnalysisService` 接口统一暴露，内部由各领域分析服务（`*AnalysisService`）实现。

### 服务架构

```
AIAnalysisService (统一接口)
├── EnergyAnalysisService      (能源AI分析)
│   ├── predictEnergyConsumption  → 能耗趋势预测
│   ├── detectDeviceAnomalies     → 设备异常检测
│   ├── getEnergyOptimizationTips → 节能优化建议
│   └── ...
├── EnvironmentAnalysisService (环境AI分析)
│   ├── predictAirQuality         → AQI趋势预测
│   ├── getPollutionAlerts        → 污染预警
│   ├── getEnvironmentHealthIndex → 环境健康指数
│   └── ...
├── FinanceAnalysisService    (金融AI分析)
│   ├── evaluateTransactionRisk   → 交易风险评分
│   ├── detectSuspiciousTransactions → 可疑交易检测
│   └── ...
├── MedicalAiDoctorService     (医疗AI分析)
│   ├── analyzeSymptomDisease     → 症状-疾病分析
│   └── ...
└── Traffic相关方法              (交通AI分析)
```

### AI分析覆盖的方法数

| 服务 | 方法数 | 核心能力 |
|------|--------|----------|
| EnergyAnalysisService | 5 | 预测、检测、优化、报告 |
| EnvironmentAnalysisService | 12 | 预测、预警、健康、成分、趋势、关联 |
| FinanceAnalysisService | 10 | 评估、检测、画像、网络、报告 |
| Medical & Traffic 等 | 15+ | 诊断、仿真、推荐 |
| **总计** | **~50** | |

---

## API文档

项目集成了 **SpringDoc OpenAPI 3 (Swagger)**。

- **Swagger UI**: `http://localhost:8080/swagger-ui/index.html`
- **OpenAPI JSON**: `http://localhost:8080/v3/api-docs`

### 核心API端点

#### 能源管理 (`/energy`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/energy/devices` | 设备列表 |
| GET | `/energy/analysis/tips` | 节能优化建议 |
| GET | `/energy/analysis/predict?days=N` | 能耗预测 |

#### 环境监测 (`/environment`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/environment/analysis/health-index` | 环境健康指数 |
| GET | `/environment/analysis/predict-air?days=N` | AQI预测 |
| GET | `/environment/analysis/alerts` | 污染预警 |

#### 金融风控 (`/finance`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/finance/transactions/page` | 交易分页查询 |
| GET | `/finance/risk-summary` | 风险统计汇总 |
| GET | `/finance/analysis/risk-trend` | 风险趋势分析 |

#### 医疗诊断 (`/medical`)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/medical/ai-doctor/consult` | AI智能问诊 |
| GET | `/medical/cases` | 病例查询 |
| POST | `/medical/ai-doctor/analyze-symptoms` | 症状分析 |

#### 交通仿真 (`/traffic`)

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/traffic/flow-records/page` | 流量分页查询 |
| GET | `/traffic/congestion-stats` | 拥堵统计 |
| GET | `/traffic/analysis/heatmap` | 热力图数据 |

---

## 测试

### 测试概况

| 类别 | 数量 | 覆盖内容 |
|------|------|----------|
| 单元测试 | 90+ | Service逻辑、AI分析引擎、工具类 |
| 集成测试 | 4 | Controller层(@WebMvcTest) |
| **总计** | **101** | |

### 运行测试

```bash
cd backend
mvn test
```

### 测试覆盖模块

- ✅ `AiModelClientTest` — AI模型客户端
- ✅ `CorsConfigTest` — CORS配置
- ✅ `MedicalControllerTest` — 医疗控制器
- ✅ `EnergyAnalysisServiceTest` — 能源AI分析 (10个)
- ✅ `EnvironmentAnalysisServiceTest` — 环境AI分析 (13个)
- ✅ `FinanceAnalysisServiceTest` — 金融AI分析 (12个)
- ✅ `AuthServiceImplTest` — 认证服务
- ✅ `FinanceServiceImplTest` — 金融服务
- ✅ `ForumServiceImplTest` — 论坛服务
- ✅ `MedicalAiDoctorServiceTest` — AI医生
- ✅ `MedicalServiceImplTest` — 医疗服务
- ✅ `TrafficServiceImplTest` — 交通服务

---

## 性能

### JMeter 压测结果

项目提供JMeter压测脚本 `backend/scripts/jmeter/ai-platform-test.jmx`。

#### 测试场景

| 场景 | 并发用户 | 目标TPS | 说明 |
|------|----------|---------|------|
| 基础查询 | 50 | 500+ | 列表查询、分页 |
| AI分析 | 20 | 100+ | 预测、检测、评估 |
| 混合场景 | 50 | 300+ | 综合业务操作 |

#### 建议压测命令

```bash
jmeter -n -t backend/scripts/jmeter/ai-platform-test.jmx \
  -Jhost=localhost -Jport=8080 \
  -l results.jtl -e -o reports/
```

#### 优化项

- 前端API超时已从5秒调整为30秒（适应AI场景）
- 数据库连接池已配置合理大小
- 响应数据压缩已启用（需额外配置）

---

## 部署

详见 [`deployment.md`](./deployment.md)。

### 快速部署

```bash
# 后端
cd backend
mvn clean package -DskipTests
java -jar target/ai-empowerment-platform.jar \
  --spring.profiles.active=prod

# 前端
cd frontend
npm run build
# 将 dist/ 部署到 nginx
```

---

## 项目结构

```
ai-empowerment-platform/
├── backend/                          # Spring Boot 后端
│   ├── src/
│   │   ├── main/
│   │   │   ├── java/com/aiempowerment/platform/
│   │   │   │   ├── common/           # 通用类(ApiResponse,异常处理)
│   │   │   │   ├── config/           # 配置类(Security,CORS,Swagger)
│   │   │   │   ├── controller/       # REST控制器(14个)
│   │   │   │   ├── model/
│   │   │   │   │   ├── dto/          # 数据传输对象
│   │   │   │   │   └── entity/       # 实体类(20个)
│   │   │   │   ├── repository/       # JPA仓库
│   │   │   │   ├── security/         # Spring Security配置
│   │   │   │   └── service/
│   │   │   │       ├── analysis/     # AI分析服务(3个)
│   │   │   │       └── impl/         # 业务实现(12个)
│   │   │   └── resources/
│   │   └── test/
│   └── pom.xml
├── frontend/                         # Vue 3 前端
│   ├── src/
│   │   ├── api/                      # API接口
│   │   ├── components/               # 公共组件
│   │   ├── router/                   # 路由配置
│   │   ├── stores/                   # 状态管理
│   │   └── views/                    # 页面组件
│   └── package.json
└── README.md
```

---

## 设计亮点

1. **统一AI分析接口** — `AIAnalysisService` 提供统一入口，内部按领域委托给独立分析服务
2. **三大分析服务** — 能源、环境、金融各有独立 `*AnalysisService`，职责清晰，便于扩展
3. **12+业务模块** — 覆盖7大场景，14个Controller，20个实体，功能完整
4. **SpringDoc集成** — 自动生成OpenAPI文档，方便前后端联调
5. **环境变量配置** — 敏感信息通过环境变量注入，安全可靠
6. **101个测试用例** — 覆盖主要业务逻辑和AI分析服务

---

## License

MIT License
