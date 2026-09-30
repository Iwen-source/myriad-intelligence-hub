# 数据库设计文档 — AI赋能万象应用平台

> 基于 MySQL 8.0，共 20 张表，覆盖能源、环境、金融、医疗、交通、教育、论坛 7 大场景。

---

## 目录

- [ER图概览](#er图概览)
- [表清单](#表清单)
- [详细表结构](#详细表结构)
- [索引设计](#索引设计)
- [关联关系](#关联关系)
- [设计规范](#设计规范)

---

## ER图概览

```
users ──┬── forum_posts ── forum_comments
        ├── medical_patients ── medical_records
        ├── energy_devices ── energy_consumption_records ── device_maintenance_records
        ├── env_monitor_points ── air_quality_records
        ├── finance_transactions ── risk_alert_rules
        ├── traffic_sections ── traffic_flow_records
        ├── education_courses ── learning_progress
        ├── creative_projects
        └── ai_applications ── application_usage
```

---

## 表清单

| 编号 | 表名 | 中文名 | 所属模块 | 记录数(示例) |
|------|------|--------|----------|-------------|
| 1 | `users` | 用户表 | 公共 | 100+ |
| 2 | `ai_applications` | AI应用表 | AI应用 | 20+ |
| 3 | `application_usage` | 应用使用记录 | AI应用 | - |
| 4 | `energy_devices` | 能源设备表 | 能源管理 | 50+ |
| 5 | `energy_consumption_records` | 能耗记录表 | 能源管理 | 10000+ |
| 6 | `device_maintenance_records` | 设备维护记录 | 能源管理 | 200+ |
| 7 | `env_monitor_points` | 环境监测点 | 环境监测 | 20+ |
| 8 | `air_quality_records` | 空气质量记录 | 环境监测 | 5000+ |
| 9 | `finance_transactions` | 金融交易表 | 金融风控 | 10000+ |
| 10 | `risk_alert_rules` | 风控规则表 | 金融风控 | 30+ |
| 11 | `medical_patients` | 患者表 | 医疗诊断 | 200+ |
| 12 | `medical_records` | 病历记录表 | 医疗诊断 | 500+ |
| 13 | `traffic_sections` | 路段表 | 交通仿真 | 100+ |
| 14 | `traffic_flow_records` | 流量记录表 | 交通仿真 | 5000+ |
| 15 | `education_courses` | 课程表 | 教育AI | 100+ |
| 16 | `learning_progress` | 学习进度表 | 教育AI | 500+ |
| 17 | `creative_projects` | 创意项目表 | 创意设计 | 100+ |
| 18 | `forum_posts` | 论坛帖子表 | 论坛 | 300+ |
| 19 | `forum_comments` | 论坛评论表 | 论坛 | 1000+ |
| 20 | `ai_pioneers` | AI先驱者表 | 展示 | 50+ |

---

## 详细表结构

### 1. 用户表 (`users`)

用户认证与基本信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 用户ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 用户名 |
| password | VARCHAR(255) | NOT NULL | 加密密码(BCrypt) |
| email | VARCHAR(100) | UNIQUE | 邮箱 |
| phone | VARCHAR(20) | | 手机号 |
| avatar | VARCHAR(500) | | 头像URL |
| role | VARCHAR(20) | DEFAULT 'user' | 角色：user/admin |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| created_at | DATETIME | DEFAULT CURRENT_TIMESTAMP | 创建时间 |
| updated_at | DATETIME | DEFAULT CURRENT_TIMESTAMP ON UPDATE | 更新时间 |

### 2. AI应用表 (`ai_applications`)

系统内置的AI应用配置。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 应用ID |
| name | VARCHAR(100) | NOT NULL | 应用名称 |
| type | VARCHAR(50) | NOT NULL | 类型：energy/env/finance/medical/traffic/edu/creative |
| description | TEXT | | 描述 |
| icon | VARCHAR(500) | | 图标URL |
| status | VARCHAR(20) | DEFAULT 'active' | 状态 |
| sort_order | INT | DEFAULT 0 | 排序 |
| created_at | DATETIME | | 创建时间 |

### 3. 应用使用记录 (`application_usage`)

记录用户使用AI应用的行为。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 记录ID |
| user_id | BIGINT | FK → users.id | 用户ID |
| application_id | BIGINT | FK → ai_applications.id | 应用ID |
| action | VARCHAR(50) | | 操作类型 |
| duration_seconds | INT | | 耗时(秒) |
| ip_address | VARCHAR(45) | | 客户端IP |
| created_at | DATETIME | | 创建时间 |

### 4. 能源设备表 (`energy_devices`)

管理的能源设备信息。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| device_id | VARCHAR(50) | PK | 设备编号(字符串主键) |
| device_name | VARCHAR(100) | NOT NULL | 设备名称 |
| device_type | VARCHAR(50) | | 设备类型(空调/照明/电梯等) |
| location | VARCHAR(200) | | 安装位置 |
| power | VARCHAR(50) | | 额定功率 |
| status | VARCHAR(20) | DEFAULT '运行中' | 状态(运行中/待机/待维护/已停机) |
| start_date | DATE | | 启用日期 |
| created_at | DATETIME | | 创建时间 |
| updated_at | DATETIME | | 更新时间 |

### 5. 能耗记录表 (`energy_consumption_records`)

设备能耗数据记录。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| record_id | VARCHAR(50) | PK | 记录ID(字符串主键) |
| device_id | VARCHAR(50) | FK → energy_devices.device_id | 设备编号 |
| consumption_value | DECIMAL(12,2) | NOT NULL | 能耗值(kWh) |
| consumption_date | DATE | NOT NULL | 日期 |
| record_time | DATETIME | | 记录时间 |
| created_at | DATETIME | | 创建时间 |

### 6. 设备维护记录表 (`device_maintenance_records`)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 维护ID |
| device_id | VARCHAR(50) | FK → energy_devices.device_id | 设备编号 |
| maintenance_type | VARCHAR(50) | | 维护类型 |
| description | TEXT | | 描述 |
| cost | DECIMAL(12,2) | | 费用 |
| maintenance_date | DATE | | 维护日期 |
| created_at | DATETIME | | 创建时间 |

### 7. 环境监测点表 (`env_monitor_points`)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 监测点ID |
| point_name | VARCHAR(100) | NOT NULL | 监测点名称 |
| location | VARCHAR(200) | | 位置描述 |
| longitude | DECIMAL(10,6) | | 经度 |
| latitude | DECIMAL(10,6) | | 纬度 |
| monitor_type | VARCHAR(50) | | 监测类型 |
| status | VARCHAR(20) | DEFAULT '正常' | 状态 |
| created_at | DATETIME | | 创建时间 |

### 8. 空气质量记录表 (`air_quality_records`)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 记录ID |
| point_id | BIGINT | FK → env_monitor_points.id | 监测点ID |
| aqi | INT | | AQI指数 |
| pm25 | DOUBLE | | PM2.5浓度(ug/m³) |
| pm10 | DOUBLE | | PM10浓度(ug/m³) |
| o3 | DOUBLE | | O₃浓度(ug/m³) |
| no2 | DOUBLE | | NO₂浓度(ug/m³) |
| so2 | DOUBLE | | SO₂浓度(ug/m³) |
| co | DOUBLE | | CO浓度(mg/m³) |
| temperature | DOUBLE | | 温度(°C) |
| humidity | DOUBLE | | 湿度(%) |
| record_time | DATETIME | | 记录时间 |
| create_time | DATETIME | | 创建时间 |

### 9. 金融交易表 (`finance_transactions`)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 交易ID |
| transaction_no | VARCHAR(50) | UNIQUE | 交易编号 |
| user_name | VARCHAR(50) | | 用户名 |
| amount | DECIMAL(15,2) | NOT NULL | 交易金额 |
| transaction_type | VARCHAR(50) | | 交易类型(转账/消费/提现/充值) |
| risk_score | DOUBLE | | 风险评分(0-100) |
| risk_level | VARCHAR(20) | | 风险等级(低/中/高) |
| status | VARCHAR(20) | | 状态(正常/待处理/已拦截) |
| remark | VARCHAR(500) | | 备注 |
| create_time | DATETIME | | 创建时间 |
| update_time | DATETIME | | 更新时间 |

### 10. 风控规则表 (`risk_alert_rules`)

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | BIGINT | PK, AUTO_INCREMENT | 规则ID |
| rule_name | VARCHAR(100) | NOT NULL | 规则名称 |
| rule_type | VARCHAR(50) | | 规则类型 |
| condition_expr | VARCHAR(500) | | 条件表达式 |
| risk_level | VARCHAR(20) | | 触发风险等级 |
| description | TEXT | | 描述 |
| enabled | TINYINT(1) | DEFAULT 1 | 是否启用 |
| created_at | DATETIME | | 创建时间 |

### 11-20. 其他表

> 医疗、交通、教育、论坛等表结构省略（遵循类似设计模式，均为 id BIGINT PK + 业务字段 + 时间戳）。

---

## 索引设计

### 主键索引

所有表均以 `id` (BIGINT AUTO_INCREMENT) 或业务编号（VARCHAR）作为主键。

### 业务索引

| 表名 | 索引字段 | 索引类型 | 说明 |
|------|----------|----------|------|
| `energy_consumption_records` | `device_id` | INDEX | 按设备查询能耗 |
| `energy_consumption_records` | `consumption_date` | INDEX | 按日期查询 |
| `energy_consumption_records` | `(device_id, consumption_date)` | COMPOSITE | 设备+日期联合查询 |
| `air_quality_records` | `point_id` | INDEX | 按监测点查询 |
| `air_quality_records` | `record_time` | INDEX | 按时间排序查询 |
| `air_quality_records` | `(point_id, record_time)` | COMPOSITE | 监测点+时间联合查询 |
| `finance_transactions` | `risk_level` | INDEX | 按风险等级过滤 |
| `finance_transactions` | `create_time` | INDEX | 按时间排序 |
| `finance_transactions` | `transaction_no` | UNIQUE | 交易编号唯一索引 |
| `traffic_flow_records` | `section_id` | INDEX | 按路段查询 |
| `traffic_flow_records` | `record_time` | INDEX | 按时间查询 |
| `forum_posts` | `user_id` | INDEX | 按用户查询帖子 |
| `forum_posts` | `created_at` | INDEX | 按时间排序 |

### 建议额外索引

对于高频AI分析场景，建议添加以下索引：

```sql
-- 环境监测：跨监测点关联分析
CREATE INDEX idx_aq_point_time ON air_quality_records(point_id, record_time DESC);

-- 能耗分析：设备维度的日期范围查询
CREATE INDEX idx_energy_device_date ON energy_consumption_records(device_id, consumption_date DESC);

-- 金融风控：风险等级+时间联合查询
CREATE INDEX idx_finance_risk_time ON finance_transactions(risk_level, create_time DESC);
```

---

## 关联关系

```
users (1) ──────< (N) forum_posts
users (1) ──────< (N) forum_comments
users (1) ──────< (N) application_usage
users (1) ──────< (N) medical_patients
users (1) ──────< (N) learning_progress

energy_devices (1) ──────< (N) energy_consumption_records
energy_devices (1) ──────< (N) device_maintenance_records

env_monitor_points (1) ────< (N) air_quality_records

forum_posts (1) ──────< (N) forum_comments

ai_applications (1) ──< (N) application_usage
```

---

## 设计规范

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 表名 | 小写+下划线，复数 | `energy_devices` |
| 字段名 | 小写+下划线 | `device_name` |
| 主键 | `id` 或 `{table}_id` | `id`, `device_id` |
| 外键 | 引用表名+字段 | `device_id` |
| 时间字段 | `_at` 后缀 | `created_at` |

### 字段规范

- 所有表包含 `created_at` 和 `updated_at` 时间戳
- 金额字段统一使用 `DECIMAL(15,2)` 
- 状态字段使用 VARCHAR，不使用 TINYINT（可读性更好）
- 逻辑删除字段 `is_deleted` (TINYINT)，默认0

### 字符集

```sql
DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
```

UTF8MB4 支持完整的 Unicode（包括 emoji），推荐用于所有表和字段。
