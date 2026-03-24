# 测试平台功能重构技术设计文档

## 文档信息
- **功能名称**：测试平台功能重构
- **文档版本**：v1.0
- **创建日期**：2025-01-06
- **文档状态**：待评审

## 1. 总体架构设计

### 1.1 架构概述

本次重构采用**统一模型 + 类型区分**的架构模式，通过引入项目类型、任务类型等枚举字段，实现功能模块的统一管理，同时保持不同测试类型的数据隔离和业务差异。

**核心设计原则：**
- **单一数据源**：每个功能模块只有一个统一的数据模型
- **类型驱动**：通过类型字段区分不同测试类型的业务逻辑
- **向后兼容**：通过适配层保持对旧 API 的兼容
- **平滑迁移**：提供数据迁移脚本，支持从旧模型平滑过渡

### 1.2 系统架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Vue 3)                          │
├─────────────────────────────────────────────────────────────────┤
│  统一项目管理  │  统一定时任务  │  统一通知配置  │  统一测试报告  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    API 网关层 (Django REST Framework)           │
├─────────────────────────────────────────────────────────────────┤
│  适配层 (兼容旧 API)  │  统一 API 接口  │  权限控制  │  数据验证 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      业务逻辑层 (Services)                       │
├─────────────────────────────────────────────────────────────────┤
│  项目管理服务  │  任务调度服务  │  通知服务  │  报告生成服务     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据访问层 (Models)                       │
├─────────────────────────────────────────────────────────────────┤
│  统一项目模型  │  统一定时任务模型  │  统一通知配置模型  │  统一报告模型 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        数据存储层 (PostgreSQL)                   │
├─────────────────────────────────────────────────────────────────┤
│  projects  │  scheduler_tasks  │  notification_configs  │  reports │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                        任务队列 (Celery)                         │
├─────────────────────────────────────────────────────────────────┤
│  任务调度器  │  任务执行器  │  通知发送器  │  报告生成器         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 模块划分

重构后的系统将包含以下核心模块：

| 模块名称 | 功能描述 | 对应应用 |
|---------|---------|---------|
| 统一项目管理 | 项目、项目成员、项目环境的统一管理 | apps/projects (增强) |
| 统一定时任务 | 定时任务、调度策略、执行日志的统一管理 | apps/scheduler (重构) |
| 统一通知配置 | 通知配置、通知规则、通知记录的统一管理 | apps/scheduler (新增) |
| 统一测试报告 | 测试报告、报告模板、报告导出的统一管理 | apps/reports (增强) |
| 数据迁移 | 数据从旧模型迁移到新模型的脚本 | apps/migrations (新增) |
| 适配层 | 保持旧 API 兼容的适配器 | apps/adapter (新增) |

## 2. 数据模型设计

### 2.1 统一项目模型

#### 2.1.1 项目模型 (Project)

**表名**: `projects`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 项目名称 |
| description | TEXT | NULL | 项目描述 |
| project_type | VARCHAR(20) | NOT NULL | 项目类型：API/UI/PERFORMANCE/GENERAL |
| status | VARCHAR(20) | NOT NULL | 状态：active/paused/completed/archived |
| base_url | VARCHAR(500) | NULL | 基础URL（UI自动化项目使用） |
| start_date | DATE | NULL | 开始日期 |
| end_date | DATE | NULL | 结束日期 |
| owner_id | BigInteger | FK | 负责人ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
- `idx_project_type`: project_type
- `idx_owner_id`: owner_id
- `idx_status`: status
- `idx_created_at`: created_at

**关系**:
- `owner`: ForeignKey → User
- `members`: ManyToMany → User (through ProjectMember)
- `environments`: OneToMany → ProjectEnvironment
- `test_reports`: OneToMany → TestReport
- `scheduled_tasks`: OneToMany → ScheduledTask

**迁移说明**:
- 将 `api_projects`、`ui_projects`、`performance_projects` 的数据迁移到此表
- 根据 `project_type` 区分原有项目类型
- 保留原有的成员关系和环境配置

#### 2.1.2 项目成员模型 (ProjectMember)

**表名**: `project_members`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| project_id | BigInteger | FK | 项目ID |
| user_id | BigInteger | FK | 用户ID |
| role | VARCHAR(20) | NOT NULL | 角色：owner/admin/developer/tester/viewer |
| joined_at | TIMESTAMP | NOT NULL | 加入时间 |

**索引**:
- `idx_project_user`: (project_id, user_id) UNIQUE
- `idx_user_id`: user_id

#### 2.1.3 项目环境模型 (ProjectEnvironment)

**表名**: `project_environments`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| project_id | BigInteger | FK | 项目ID |
| name | VARCHAR(100) | NOT NULL | 环境名称 |
| base_url | VARCHAR(500) | NOT NULL | 基础URL |
| description | TEXT | NULL | 环境描述 |
| variables | JSONB | NOT NULL | 环境变量 |
| is_default | BOOLEAN | NOT NULL | 是否默认 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

**索引**:
- `idx_project_id`: project_id
- `idx_is_default`: is_default

### 2.2 统一定时任务模型

#### 2.2.1 定时任务模型 (ScheduledTask)

**表名**: `scheduler_tasks`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 任务名称 |
| description | TEXT | NULL | 任务描述 |
| project_id | BigInteger | FK | 项目ID（可为空，用于全局任务） |
| task_type | VARCHAR(20) | NOT NULL | 任务类型：API/UI/PERFORMANCE |
| trigger_type | VARCHAR(20) | NOT NULL | 触发器类型：CRON/INTERVAL/ONCE |
| cron_expression | VARCHAR(100) | NULL | Cron表达式 |
| interval_seconds | INTEGER | NULL | 间隔秒数 |
| execute_at | TIMESTAMP | NULL | 执行时间（单次执行） |
| status | VARCHAR(20) | NOT NULL | 任务状态：ACTIVE/PAUSED/COMPLETED/FAILED |
| last_run_time | TIMESTAMP | NULL | 最后运行时间 |
| next_run_time | TIMESTAMP | NULL | 下次运行时间 |
| total_runs | INTEGER | NOT NULL | 总运行次数 |
| successful_runs | INTEGER | NOT NULL | 成功运行次数 |
| failed_runs | INTEGER | NOT NULL | 失败运行次数 |
| notification_config_id | BigInteger | FK | 通知配置ID |
| notify_on_success | BOOLEAN | NOT NULL | 成功时通知 |
| notify_on_failure | BOOLEAN | NOT NULL | 失败时通知 |
| created_by_id | BigInteger | FK | 创建者ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
- `idx_project_id`: project_id
- `idx_task_type`: task_type
- `idx_status`: status
- `idx_next_run_time`: next_run_time

**关系**:
- `project`: ForeignKey → Project
- `notification_config`: ForeignKey → NotificationConfig
- `execution_logs`: OneToMany → TaskExecutionLog

**迁移说明**:
- 将 `api_scheduled_tasks` 的数据迁移到此表
- 将 `task_type` 设置为 "API"
- 保留原有的调度配置和执行日志

#### 2.2.2 任务执行日志模型 (TaskExecutionLog)

**表名**: `scheduler_execution_logs`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| task_id | BigInteger | FK | 任务ID |
| status | VARCHAR(20) | NOT NULL | 执行状态：PENDING/RUNNING/SUCCESS/FAILED |
| start_time | TIMESTAMP | NOT NULL | 开始时间 |
| end_time | TIMESTAMP | NULL | 结束时间 |
| duration | FLOAT | NULL | 执行时长(秒) |
| result | JSONB | NOT NULL | 执行结果 |
| error_message | TEXT | NULL | 错误信息 |

**索引**:
- `idx_task_id`: task_id
- `idx_status`: status
- `idx_start_time`: start_time

### 2.3 统一通知配置模型

#### 2.3.1 通知配置模型 (NotificationConfig)

**表名**: `notification_configs`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| name | VARCHAR(100) | NOT NULL | 配置名称 |
| config_type | VARCHAR(20) | NOT NULL | 配置类型：webhook_feishu/webhook_wechat/webhook_dingtalk/email |
| webhook_url | VARCHAR(500) | NULL | Webhook URL |
| secret | VARCHAR(200) | NULL | 加签密钥 |
| smtp_server | VARCHAR(200) | NULL | SMTP服务器 |
| smtp_port | INTEGER | NULL | SMTP端口 |
| smtp_user | VARCHAR(100) | NULL | SMTP用户名 |
| smtp_password | VARCHAR(100) | NULL | SMTP密码 |
| email_from | VARCHAR(100) | NULL | 发件人邮箱 |
| use_tls | BOOLEAN | NOT NULL | 使用TLS |
| use_ssl | BOOLEAN | NOT NULL | 使用SSL |
| email_recipients | JSONB | NOT NULL | 默认收件人列表 |
| is_active | BOOLEAN | NOT NULL | 是否启用 |
| description | TEXT | NULL | 描述 |
| project_id | BigInteger | FK | 关联项目ID（为空则为全局配置） |
| created_by_id | BigInteger | FK | 创建者ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| updated_at | TIMESTAMP | NOT NULL | 更新时间 |

**索引**:
- `idx_config_type`: config_type
- `idx_project_id`: project_id
- `idx_is_active`: is_active

**迁移说明**:
- 将 `api_notification_configs` 的数据迁移到此表
- 保留原有的 Webhook 和邮件配置
- 保留原有的关联关系

#### 2.3.2 通知日志模型 (NotificationLog)

**表名**: `notification_logs`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| task_id | BigInteger | FK | 关联任务ID（可为空） |
| task_name | VARCHAR(200) | NOT NULL | 任务名称 |
| notification_type | VARCHAR(50) | NOT NULL | 通知类型 |
| sender_name | VARCHAR(100) | NOT NULL | 发件人姓名 |
| sender_email | VARCHAR(255) | NOT NULL | 发件人邮箱 |
| recipient_info | JSONB | NOT NULL | 收件人信息 |
| webhook_bot_info | JSONB | NULL | Webhook机器人信息 |
| notification_content | TEXT | NOT NULL | 通知内容 |
| status | VARCHAR(20) | NOT NULL | 发送状态：pending/sending/success/failed/cancelled |
| error_message | TEXT | NULL | 错误信息 |
| response_info | JSONB | NULL | 响应信息 |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| sent_at | TIMESTAMP | NULL | 发送时间 |
| retry_count | INTEGER | NOT NULL | 重试次数 |
| is_retried | BOOLEAN | NOT NULL | 是否已重试 |

**索引**:
- `idx_task_id`: task_id
- `idx_notification_type`: notification_type
- `idx_status`: status
- `idx_created_at`: created_at

### 2.4 统一测试报告模型

#### 2.4.1 测试报告模型 (TestReport)

**表名**: `test_reports`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| project_id | BigInteger | FK | 项目ID |
| name | VARCHAR(200) | NOT NULL | 报告名称 |
| report_type | VARCHAR(20) | NOT NULL | 报告类型：execution/summary/trend |
| test_type | VARCHAR(20) | NOT NULL | 测试类型：API/UI/PERFORMANCE |
| execution_id | BigInteger | FK | 关联执行ID（可为空） |
| summary | JSONB | NOT NULL | 报告摘要 |
| content | JSONB | NOT NULL | 报告内容 |
| template_id | BigInteger | FK | 报告模板ID |
| generated_by_id | BigInteger | FK | 生成者ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |
| ai_analysis_result | TEXT | NULL | AI分析结果 |
| ai_suggestions | TEXT | NULL | 修复建议 |
| ai_analyzed_at | TIMESTAMP | NULL | AI分析时间 |

**索引**:
- `idx_project_id`: project_id
- `idx_report_type`: report_type
- `idx_test_type`: test_type
- `idx_execution_id`: execution_id
- `idx_created_at`: created_at

**迁移说明**:
- 保留现有的 `test_reports` 表结构
- 新增 `test_type` 字段用于区分测试类型
- 新增 `template_id` 字段关联报告模板

#### 2.4.2 报告模板模型 (ReportTemplate)

**表名**: `report_templates`

**字段说明**:

| 字段名 | 类型 | 约束 | 说明 |
|-------|------|------|------|
| id | BigInteger | PK | 主键 |
| name | VARCHAR(200) | NOT NULL | 模板名称 |
| description | TEXT | NULL | 模板描述 |
| test_type | VARCHAR(20) | NOT NULL | 测试类型：API/UI/PERFORMANCE |
| template_config | JSONB | NOT NULL | 模板配置 |
| is_default | BOOLEAN | NOT NULL | 是否默认 |
| created_by_id | BigInteger | FK | 创建者ID |
| created_at | TIMESTAMP | NOT NULL | 创建时间 |

**索引**:
- `idx_test_type`: test_type
- `idx_is_default`: is_default

## 3. API 接口设计

### 3.1 统一项目管理 API

#### 3.1.1 项目列表接口

**接口路径**: `GET /api/v1/projects/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| project_type | string | 否 | 项目类型筛选 |
| status | string | 否 | 状态筛选 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "items": [
      {
        "id": 1,
        "name": "电商系统接口测试",
        "description": "电商系统接口自动化测试项目",
        "project_type": "API",
        "status": "active",
        "owner": {
          "id": 1,
          "username": "admin",
          "email": "admin@example.com"
        },
        "members_count": 5,
        "created_at": "2025-01-01T00:00:00Z",
        "updated_at": "2025-01-06T00:00:00Z"
      }
    ]
  }
}
```

#### 3.1.2 创建项目接口

**接口路径**: `POST /api/v1/projects/`

**请求参数**:

```json
{
  "name": "电商系统接口测试",
  "description": "电商系统接口自动化测试项目",
  "project_type": "API",
  "status": "active",
  "base_url": "https://api.example.com",
  "start_date": "2025-01-01",
  "end_date": "2025-12-31"
}
```

**响应示例**:

```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "电商系统接口测试",
    "project_type": "API",
    "status": "active",
    "created_at": "2025-01-06T00:00:00Z"
  }
}
```

#### 3.1.3 项目详情接口

**接口路径**: `GET /api/v1/projects/{id}/`

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "电商系统接口测试",
    "description": "电商系统接口自动化测试项目",
    "project_type": "API",
    "status": "active",
    "base_url": "https://api.example.com",
    "start_date": "2025-01-01",
    "end_date": "2025-12-31",
    "owner": {
      "id": 1,
      "username": "admin",
      "email": "admin@example.com"
    },
    "members": [
      {
        "id": 2,
        "username": "tester1",
        "email": "tester1@example.com",
        "role": "tester",
        "joined_at": "2025-01-01T00:00:00Z"
      }
    ],
    "environments": [
      {
        "id": 1,
        "name": "测试环境",
        "base_url": "https://test-api.example.com",
        "is_default": true,
        "variables": {
          "token": "{{token}}"
        }
      }
    ],
    "statistics": {
      "test_cases_count": 100,
      "test_suites_count": 10,
      "scheduled_tasks_count": 5,
      "reports_count": 50
    },
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2025-01-06T00:00:00Z"
  }
}
```

### 3.2 统一定时任务 API

#### 3.2.1 定时任务列表接口

**接口路径**: `GET /api/v1/scheduler/tasks/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| project_id | int | 否 | 项目ID筛选 |
| task_type | string | 否 | 任务类型筛选 |
| status | string | 否 | 状态筛选 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 50,
    "items": [
      {
        "id": 1,
        "name": "每日接口测试",
        "description": "每天凌晨2点执行接口测试",
        "project": {
          "id": 1,
          "name": "电商系统接口测试"
        },
        "task_type": "API",
        "trigger_type": "CRON",
        "cron_expression": "0 2 * * *",
        "status": "ACTIVE",
        "last_run_time": "2025-01-05T02:00:00Z",
        "next_run_time": "2025-01-06T02:00:00Z",
        "total_runs": 10,
        "successful_runs": 9,
        "failed_runs": 1,
        "created_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### 3.2.2 创建定时任务接口

**接口路径**: `POST /api/v1/scheduler/tasks/`

**请求参数**:

```json
{
  "name": "每日接口测试",
  "description": "每天凌晨2点执行接口测试",
  "project_id": 1,
  "task_type": "API",
  "trigger_type": "CRON",
  "cron_expression": "0 2 * * *",
  "notification_config_id": 1,
  "notify_on_success": false,
  "notify_on_failure": true,
  "test_suite_id": 1
}
```

**响应示例**:

```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "每日接口测试",
    "task_type": "API",
    "status": "ACTIVE",
    "next_run_time": "2025-01-06T02:00:00Z",
    "created_at": "2025-01-06T00:00:00Z"
  }
}
```

#### 3.2.3 任务执行日志接口

**接口路径**: `GET /api/v1/scheduler/tasks/{id}/execution-logs/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| status | string | 否 | 执行状态筛选 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "items": [
      {
        "id": 1,
        "task_id": 1,
        "status": "SUCCESS",
        "start_time": "2025-01-05T02:00:00Z",
        "end_time": "2025-01-05T02:05:00Z",
        "duration": 300.0,
        "result": {
          "total_cases": 100,
          "passed_cases": 98,
          "failed_cases": 2
        },
        "error_message": null
      }
    ]
  }
}
```

### 3.3 统一通知配置 API

#### 3.3.1 通知配置列表接口

**接口路径**: `GET /api/v1/notifications/configs/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| config_type | string | 否 | 配置类型筛选 |
| project_id | int | 否 | 项目ID筛选 |
| is_active | bool | 否 | 是否启用筛选 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 10,
    "items": [
      {
        "id": 1,
        "name": "飞书通知配置",
        "config_type": "webhook_feishu",
        "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
        "is_active": true,
        "project": {
          "id": 1,
          "name": "电商系统接口测试"
        },
        "created_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
```

#### 3.3.2 创建通知配置接口

**接口路径**: `POST /api/v1/notifications/configs/`

**请求参数**:

```json
{
  "name": "飞书通知配置",
  "config_type": "webhook_feishu",
  "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
  "is_active": true,
  "project_id": 1
}
```

**响应示例**:

```json
{
  "code": 201,
  "message": "创建成功",
  "data": {
    "id": 1,
    "name": "飞书通知配置",
    "config_type": "webhook_feishu",
    "is_active": true,
    "created_at": "2025-01-06T00:00:00Z"
  }
}
```

#### 3.3.3 通知日志接口

**接口路径**: `GET /api/v1/notifications/logs/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| task_id | int | 否 | 任务ID筛选 |
| notification_type | string | 否 | 通知类型筛选 |
| status | string | 否 | 发送状态筛选 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 100,
    "items": [
      {
        "id": 1,
        "task_id": 1,
        "task_name": "每日接口测试",
        "notification_type": "task_execution",
        "sender_name": "系统通知",
        "sender_email": "noreply@example.com",
        "status": "success",
        "notification_content": "任务执行成功",
        "created_at": "2025-01-05T02:05:00Z",
        "sent_at": "2025-01-05T02:05:01Z"
      }
    ]
  }
}
```

### 3.4 统一测试报告 API

#### 3.4.1 测试报告列表接口

**接口路径**: `GET /api/v1/reports/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| project_id | int | 否 | 项目ID筛选 |
| test_type | string | 否 | 测试类型筛选 |
| report_type | string | 否 | 报告类型筛选 |
| start_date | string | 否 | 开始日期 |
| end_date | string | 否 | 结束日期 |
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认20 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 50,
    "items": [
      {
        "id": 1,
        "name": "接口测试执行报告",
        "project": {
          "id": 1,
          "name": "电商系统接口测试"
        },
        "report_type": "execution",
        "test_type": "API",
        "summary": {
          "total_cases": 100,
          "passed_cases": 98,
          "failed_cases": 2,
          "pass_rate": 0.98
        },
        "created_at": "2025-01-05T02:05:00Z"
      }
    ]
  }
}
```

#### 3.4.2 测试报告详情接口

**接口路径**: `GET /api/v1/reports/{id}/`

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "id": 1,
    "name": "接口测试执行报告",
    "project": {
      "id": 1,
      "name": "电商系统接口测试"
    },
    "report_type": "execution",
    "test_type": "API",
    "execution": {
      "id": 1,
      "name": "每日接口测试执行"
    },
    "summary": {
      "total_cases": 100,
      "passed_cases": 98,
      "failed_cases": 2,
      "pass_rate": 0.98,
      "duration": 300.0
    },
    "content": {
      "test_cases": [
        {
          "id": 1,
          "name": "用户登录接口测试",
          "status": "passed",
          "duration": 1.5,
          "assertions": [
            {
              "type": "status_code",
              "expected": 200,
              "actual": 200,
              "passed": true
            }
          ]
        }
      ]
    },
    "created_at": "2025-01-05T02:05:00Z"
  }
}
```

#### 3.4.3 导出报告接口

**接口路径**: `GET /api/v1/reports/{id}/export/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| format | string | 是 | 导出格式：pdf/html/excel |

**响应**:
- 返回文件流，Content-Type 根据格式设置

#### 3.4.4 报告模板接口

**接口路径**: `GET /api/v1/reports/templates/`

**请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| test_type | string | 否 | 测试类型筛选 |
| is_default | bool | 否 | 是否默认筛选 |

**响应示例**:

```json
{
  "code": 200,
  "message": "success",
  "data": {
    "total": 3,
    "items": [
      {
        "id": 1,
        "name": "接口测试默认模板",
        "description": "接口测试默认报告模板",
        "test_type": "API",
        "is_default": true,
        "template_config": {
          "style": "default",
          "layout": "standard"
        },
        "created_at": "2025-01-01T00:00:00Z"
      }
    ]
  }
}
```

## 4. 数据迁移方案

### 4.1 迁移策略

采用**分阶段迁移**策略，确保数据安全和系统稳定：

1. **准备阶段**：备份现有数据，创建新表结构
2. **迁移阶段**：将旧表数据迁移到新表
3. **验证阶段**：验证数据完整性和一致性
4. **切换阶段**：切换到新表，保留旧表作为备份
5. **清理阶段**：确认无误后，清理旧表

### 4.2 项目数据迁移

#### 4.2.1 迁移脚本

```python
# apps/projects/migrations/0002_migrate_to_unified_project.py

from django.db import migrations
from django.utils import timezone

def migrate_api_projects(apps, schema_editor):
    """迁移 API 项目数据"""
    ApiProject = apps.get_model('api_testing', 'ApiProject')
    Project = apps.get_model('projects', 'Project')
    ProjectMember = apps.get_model('projects', 'ProjectMember')
    ProjectEnvironment = apps.get_model('projects', 'ProjectEnvironment')

    for api_project in ApiProject.objects.all():
        # 创建统一项目
        project = Project.objects.create(
            name=api_project.name,
            description=api_project.description,
            project_type='API',
            status=api_project.status,
            start_date=api_project.start_date,
            end_date=api_project.end_date,
            owner=api_project.owner,
            created_at=api_project.created_at,
            updated_at=api_project.updated_at
        )

        # 迁移成员
        for member in api_project.members.all():
            ProjectMember.objects.create(
                project=project,
                user=member,
                role='tester',  # 默认角色
                joined_at=timezone.now()
            )

        # 迁移环境
        for env in api_project.environments.all():
            ProjectEnvironment.objects.create(
                project=project,
                name=env.name,
                base_url=env.base_url if hasattr(env, 'base_url') else '',
                description=env.description,
                variables=env.variables,
                is_default=env.is_active,
                created_at=env.created_at
            )

def migrate_ui_projects(apps, schema_editor):
    """迁移 UI 项目数据"""
    UiProject = apps.get_model('ui_automation', 'UiProject')
    Project = apps.get_model('projects', 'Project')
    ProjectMember = apps.get_model('projects', 'ProjectMember')

    for ui_project in UiProject.objects.all():
        # 创建统一项目
        project = Project.objects.create(
            name=ui_project.name,
            description=ui_project.description,
            project_type='UI',
            status=ui_project.status,
            base_url=ui_project.base_url,
            start_date=ui_project.start_date,
            end_date=ui_project.end_date,
            owner=ui_project.owner,
            created_at=ui_project.created_at,
            updated_at=ui_project.updated_at
        )

        # 迁移成员
        for member in ui_project.members.all():
            ProjectMember.objects.create(
                project=project,
                user=member,
                role='tester',
                joined_at=timezone.now()
            )

def migrate_performance_projects(apps, schema_editor):
    """迁移性能测试项目数据"""
    PerformanceProject = apps.get_model('performance_test', 'PerformanceProject')
    Project = apps.get_model('projects', 'Project')
    ProjectMember = apps.get_model('projects', 'ProjectMember')

    for perf_project in PerformanceProject.objects.all():
        # 创建统一项目
        project = Project.objects.create(
            name=perf_project.name,
            description=perf_project.description,
            project_type='PERFORMANCE',
            status=perf_project.status,
            start_date=perf_project.start_date,
            end_date=perf_project.end_date,
            owner=perf_project.owner,
            created_at=perf_project.created_at,
            updated_at=perf_project.updated_at
        )

        # 迁移成员
        for member in perf_project.members.all():
            ProjectMember.objects.create(
                project=project,
                user=member,
                role='tester',
                joined_at=timezone.now()
            )

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0001_initial'),
        ('api_testing', '0001_initial'),
        ('ui_automation', '0001_initial'),
        ('performance_test', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_api_projects),
        migrations.RunPython(migrate_ui_projects),
        migrations.RunPython(migrate_performance_projects),
    ]
```

#### 4.2.2 回滚脚本

```python
# apps/projects/migrations/0003_rollback_unified_project.py

from django.db import migrations

def rollback_migration(apps, schema_editor):
    """回滚迁移"""
    Project = apps.get_model('projects', 'Project')

    # 删除迁移创建的项目
    Project.objects.filter(project_type__in=['API', 'UI', 'PERFORMANCE']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('projects', '0002_migrate_to_unified_project'),
    ]

    operations = [
        migrations.RunPython(rollback_migration),
    ]
```

### 4.3 定时任务数据迁移

#### 4.3.1 迁移脚本

```python
# apps/scheduler/migrations/0002_migrate_api_scheduled_tasks.py

from django.db import migrations

def migrate_scheduled_tasks(apps, schema_editor):
    """迁移 API 定时任务数据"""
    ApiScheduledTask = apps.get_model('api_testing', 'ScheduledTask')
    ScheduledTask = apps.get_model('scheduler', 'ScheduledTask')
    TaskExecutionLog = apps.get_model('scheduler', 'TaskExecutionLog')
    ApiTaskExecutionLog = apps.get_model('api_testing', 'TaskExecutionLog')

    for api_task in ApiScheduledTask.objects.all():
        # 创建统一定时任务
        task = ScheduledTask.objects.create(
            name=api_task.name,
            description=api_task.description,
            project_id=api_task.project.id if api_task.project else None,
            task_type='API',
            trigger_type=api_task.trigger_type,
            cron_expression=api_task.cron_expression,
            interval_seconds=api_task.interval_seconds,
            execute_at=api_task.execute_at,
            status=api_task.status,
            last_run_time=api_task.last_run_time,
            next_run_time=api_task.next_run_time,
            total_runs=api_task.total_runs,
            successful_runs=api_task.successful_runs,
            failed_runs=api_task.failed_runs,
            notify_on_success=api_task.notify_on_success,
            notify_on_failure=api_task.notify_on_failure,
            created_by=api_task.created_by,
            created_at=api_task.created_at,
            updated_at=api_task.updated_at
        )

        # 迁移执行日志
        for api_log in api_task.execution_logs.all():
            TaskExecutionLog.objects.create(
                task=task,
                status=api_log.status,
                start_time=api_log.start_time,
                end_time=api_log.end_time,
                duration=api_log.duration,
                result=api_log.result,
                error_message=api_log.error_message
            )

class Migration(migrations.Migration):
    dependencies = [
        ('scheduler', '0001_initial'),
        ('api_testing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_scheduled_tasks),
    ]
```

### 4.4 通知配置数据迁移

#### 4.4.1 迁移脚本

```python
# apps/scheduler/migrations/0003_migrate_notification_configs.py

from django.db import migrations

def migrate_notification_configs(apps, schema_editor):
    """迁移通知配置数据"""
    ApiNotificationConfig = apps.get_model('api_testing', 'NotificationConfig')
    NotificationConfig = apps.get_model('scheduler', 'NotificationConfig')
    ApiNotificationLog = apps.get_model('api_testing', 'NotificationLog')
    NotificationLog = apps.get_model('scheduler', 'NotificationLog')

    for api_config in ApiNotificationConfig.objects.all():
        # 创建统一通知配置
        config = NotificationConfig.objects.create(
            name=api_config.name,
            config_type=api_config.config_type,
            webhook_url=api_config.webhook_bots.get('webhook_url') if api_config.webhook_bots else None,
            is_active=api_config.is_active,
            description=api_config.description,
            project_id=api_config.project.id if api_config.project else None,
            created_by=api_config.created_by,
            created_at=api_config.created_at,
            updated_at=api_config.updated_at
        )

    # 迁移通知日志
    for api_log in ApiNotificationLog.objects.all():
        NotificationLog.objects.create(
            task_id=api_log.task.id if api_log.task else None,
            task_name=api_log.task_name,
            notification_type=api_log.notification_type,
            sender_name=api_log.sender_name,
            sender_email=api_log.sender_email,
            recipient_info=api_log.recipient_info,
            webhook_bot_info=api_log.webhook_bot_info,
            notification_content=api_log.notification_content,
            status=api_log.status,
            error_message=api_log.error_message,
            response_info=api_log.response_info,
            created_at=api_log.created_at,
            sent_at=api_log.sent_at,
            retry_count=api_log.retry_count,
            is_retried=api_log.is_retried
        )

class Migration(migrations.Migration):
    dependencies = [
        ('scheduler', '0002_migrate_api_scheduled_tasks'),
        ('api_testing', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_notification_configs),
    ]
```

### 4.5 迁移验证

#### 4.5.1 数据完整性验证

```python
# scripts/validate_migration.py

from django.core.management.base import BaseCommand
from apps.projects.models import Project
from apps.api_testing.models import ApiProject
from apps.ui_automation.models import UiProject
from apps.performance_test.models import PerformanceProject

class Command(BaseCommand):
    help = '验证数据迁移的完整性'

    def handle(self, *args, **options):
        # 验证项目迁移
        api_count = ApiProject.objects.count()
        ui_count = UiProject.objects.count()
        perf_count = PerformanceProject.objects.count()
        total_migrated = Project.objects.filter(
            project_type__in=['API', 'UI', 'PERFORMANCE']
        ).count()

        expected_total = api_count + ui_count + perf_count

        self.stdout.write(f'API 项目数量: {api_count}')
        self.stdout.write(f'UI 项目数量: {ui_count}')
        self.stdout.write(f'性能测试项目数量: {perf_count}')
        self.stdout.write(f'迁移后项目总数: {total_migrated}')
        self.stdout.write(f'预期总数: {expected_total}')

        if total_migrated == expected_total:
            self.stdout.write(self.style.SUCCESS('数据迁移验证通过'))
        else:
            self.stdout.write(self.style.ERROR('数据迁移验证失败'))
```

## 5. 兼容性设计

### 5.1 API 适配层

为了保持对旧 API 的兼容，创建适配层将旧 API 请求转发到新 API。

#### 5.1.1 适配器实现

```python
# apps/adapter/adapters/api_project_adapter.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.projects.models import Project
from apps.projects.serializers import ProjectSerializer

class ApiProjectAdapter(viewsets.ModelViewSet):
    """API 项目适配器，保持旧 API 兼容"""

    serializer_class = ProjectSerializer

    def get_queryset(self):
        """只返回 API 类型的项目"""
        return Project.objects.filter(project_type='API')

    def list(self, request, *args, **kwargs):
        """适配旧的项目列表接口"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # 转换为旧格式
        old_format_data = []
        for item in serializer.data:
            old_format_data.append({
                'id': item['id'],
                'name': item['name'],
                'description': item['description'],
                'project_type': item['project_type'],
                'status': item['status'],
                'owner': item['owner'],
                'members': item['members'],
                'created_at': item['created_at'],
                'updated_at': item['updated_at'],
                # 旧 API 特有字段
                'steps_count': 0,  # 需要从关联数据计算
            })

        return Response({
            'code': 200,
            'message': 'success',
            'data': old_format_data
        })

    def create(self, request, *args, **kwargs):
        """适配旧的项目创建接口"""
        data = request.data.copy()
        data['project_type'] = 'API'  # 强制设置为 API 类型

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({
            'code': 201,
            'message': '创建成功',
            'data': serializer.data
        }, status=status.HTTP_201_CREATED)
```

#### 5.1.2 路由配置

```python
# apps/adapter/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.adapter.adapters.api_project_adapter import ApiProjectAdapter

router = DefaultRouter()
router.register(r'api-projects', ApiProjectAdapter, basename='api-project')

urlpatterns = [
    path('api/v1/adapter/', include(router.urls)),
]
```

### 5.2 URL 重定向

对于废弃的 API 端点，使用 HTTP 重定向到新的 API 端点。

```python
# config/urls.py

from django.urls import path
from django.views.generic import RedirectView

urlpatterns = [
    # 旧 API 重定向到新 API
    path('api/v1/api-testing/projects/',
         RedirectView.as_view(url='/api/v1/projects/?project_type=API', permanent=True)),
    path('api/v1/api-testing/scheduled-tasks/',
         RedirectView.as_view(url='/api/v1/scheduler/tasks/?task_type=API', permanent=True)),
    path('api/v1/api-testing/notification-configs/',
         RedirectView.as_view(url='/api/v1/notifications/configs/', permanent=True)),
]
```

## 6. 前端架构设计

### 6.1 组件结构

```
src/
├── views/
│   ├── unified/
│   │   ├── projects/
│   │   │   ├── ProjectList.vue
│   │   │   ├── ProjectDetail.vue
│   │   │   └── ProjectForm.vue
│   │   ├── scheduler/
│   │   │   ├── TaskList.vue
│   │   │   ├── TaskDetail.vue
│   │   │   └── TaskForm.vue
│   │   ├── notifications/
│   │   │   ├── ConfigList.vue
│   │   │   ├── ConfigForm.vue
│   │   │   └── NotificationLog.vue
│   │   └── reports/
│   │       ├── ReportList.vue
│   │       ├── ReportDetail.vue
│   │       └── ReportExport.vue
├── components/
│   ├── unified/
│   │   ├── ProjectTypeSelector.vue
│   │   ├── TaskTypeSelector.vue
│   │   └── NotificationTypeSelector.vue
├── stores/
│   ├── unified/
│   │   ├── projectStore.ts
│   │   ├── taskStore.ts
│   │   ├── notificationStore.ts
│   │   └── reportStore.ts
├── api/
│   ├── unified/
│   │   ├── project.ts
│   │   ├── task.ts
│   │   ├── notification.ts
│   │   └── report.ts
└── utils/
    ├── migration.ts
    └── adapter.ts
```

### 6.2 状态管理

使用 Pinia 进行状态管理，统一管理项目、任务、通知、报告的数据。

```typescript
// src/stores/unified/projectStore.ts

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { projectApi } from '@/api/unified/project'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProject = ref<Project | null>(null)
  const loading = ref(false)

  const apiProjects = computed(() =>
    projects.value.filter(p => p.project_type === 'API')
  )

  const uiProjects = computed(() =>
    projects.value.filter(p => p.project_type === 'UI')
  )

  const performanceProjects = computed(() =>
    projects.value.filter(p => p.project_type === 'PERFORMANCE')
  )

  async function fetchProjects(params?: ProjectQueryParams) {
    loading.value = true
    try {
      const response = await projectApi.list(params)
      projects.value = response.data.items
    } finally {
      loading.value = false
    }
  }

  async function createProject(data: ProjectFormData) {
    const response = await projectApi.create(data)
    projects.value.unshift(response.data)
    return response.data
  }

  return {
    projects,
    currentProject,
    loading,
    apiProjects,
    uiProjects,
    performanceProjects,
    fetchProjects,
    createProject
  }
})
```

### 6.3 API 封装

统一封装 API 调用，提供类型安全的接口。

```typescript
// src/api/unified/project.ts

import request from '@/utils/request'

export interface Project {
  id: number
  name: string
  description: string
  project_type: 'API' | 'UI' | 'PERFORMANCE' | 'GENERAL'
  status: string
  owner: User
  members_count: number
  created_at: string
  updated_at: string
}

export interface ProjectQueryParams {
  project_type?: string
  status?: string
  page?: number
  page_size?: number
}

export const projectApi = {
  list(params?: ProjectQueryParams) {
    return request.get<ProjectListResponse>('/api/v1/projects/', { params })
  },

  create(data: ProjectFormData) {
    return request.post<ProjectResponse>('/api/v1/projects/', data)
  },

  detail(id: number) {
    return request.get<ProjectDetailResponse>(`/api/v1/projects/${id}/`)
  },

  update(id: number, data: Partial<ProjectFormData>) {
    return request.put<ProjectResponse>(`/api/v1/projects/${id}/`, data)
  },

  delete(id: number) {
    return request.delete(`/api/v1/projects/${id}/`)
  }
}
```

## 7. 性能优化

### 7.1 数据库优化

#### 7.1.1 索引优化

为常用查询字段添加索引，提高查询性能：

```sql
-- 项目表索引
CREATE INDEX idx_projects_type_status ON projects(project_type, status);
CREATE INDEX idx_projects_owner_created ON projects(owner_id, created_at DESC);

-- 定时任务表索引
CREATE INDEX idx_scheduler_tasks_project_type ON scheduler_tasks(project_id, task_type);
CREATE INDEX idx_scheduler_tasks_next_run ON scheduler_tasks(next_run_time) WHERE status = 'ACTIVE';

-- 通知配置表索引
CREATE INDEX idx_notification_configs_type_active ON notification_configs(config_type, is_active);

-- 测试报告表索引
CREATE INDEX idx_test_reports_project_type_created ON test_reports(project_id, test_type, created_at DESC);
```

#### 7.1.2 查询优化

使用 `select_related` 和 `prefetch_related` 优化关联查询：

```python
# apps/projects/views.py

class ProjectViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        queryset = Project.objects.select_related('owner').prefetch_related(
            'members__user',
            'environments'
        )
        return queryset
```

### 7.2 缓存策略

使用 Redis 缓存常用数据，减少数据库查询：

```python
# apps/projects/services.py

from django.core.cache import cache

class ProjectService:
    @staticmethod
    def get_project_with_cache(project_id: int):
        cache_key = f'project:{project_id}'
        project = cache.get(cache_key)

        if project is None:
            project = Project.objects.select_related('owner').get(id=project_id)
            cache.set(cache_key, project, timeout=3600)  # 缓存1小时

        return project

    @staticmethod
    def clear_project_cache(project_id: int):
        cache_key = f'project:{project_id}'
        cache.delete(cache_key)
```

### 7.3 异步处理

使用 Celery 异步处理耗时操作：

```python
# apps/reports/tasks.py

from celery import shared_task
from apps.reports.services import ReportGenerator

@shared_task
def generate_report_async(report_id: int):
    """异步生成报告"""
    generator = ReportGenerator()
    generator.generate(report_id)
    return {'report_id': report_id, 'status': 'completed'}
```

## 8. 安全设计

### 8.1 权限控制

基于角色的访问控制（RBAC）：

```python
# apps/projects/permissions.py

from rest_framework import permissions

class ProjectPermission(permissions.BasePermission):
    """项目权限控制"""

    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']:
            return request.user.is_authenticated
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # 项目所有者和管理员可以执行所有操作
        if obj.owner == request.user:
            return True

        # 检查用户角色
        member = obj.members.filter(user=request.user).first()
        if not member:
            return False

        if view.action in ['update', 'partial_update']:
            return member.role in ['admin', 'owner']

        if view.action == 'destroy':
            return member.role == 'owner'

        return True
```

### 8.2 数据加密

敏感数据加密存储：

```python
# apps/utils/encryption.py

from cryptography.fernet import Fernet
import base64

class EncryptionService:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode())

    def encrypt(self, data: str) -> str:
        encrypted = self.cipher.encrypt(data.encode())
        return base64.b64encode(encrypted).decode()

    def decrypt(self, encrypted: str) -> str:
        encrypted_bytes = base64.b64decode(encrypted.encode())
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
```

### 8.3 审计日志

记录关键操作的审计日志：

```python
# apps/audit/models.py

from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    """审计日志"""
    ACTION_CHOICES = [
        ('create', '创建'),
        ('update', '更新'),
        ('delete', '删除'),
        ('export', '导出'),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=50)
    resource_id = models.IntegerField()
    old_value = models.JSONField(null=True)
    new_value = models.JSONField(null=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-created_at']
```

## 9. 测试策略

### 9.1 单元测试

为关键业务逻辑编写单元测试：

```python
# apps/projects/tests/test_services.py

from django.test import TestCase
from apps.projects.services import ProjectService
from apps.projects.models import Project

class ProjectServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')

    def test_create_project(self):
        project = ProjectService.create_project({
            'name': 'Test Project',
            'project_type': 'API',
            'owner': self.user
        })

        self.assertIsNotNone(project.id)
        self.assertEqual(project.name, 'Test Project')
        self.assertEqual(project.project_type, 'API')
```

### 9.2 集成测试

测试 API 接口的集成：

```python
# apps/api/tests/test_views.py

from rest_framework.test import APITestCase
from rest_framework import status

class ProjectAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test')
        self.client.force_authenticate(user=self.user)

    def test_create_project(self):
        data = {
            'name': 'Test Project',
            'project_type': 'API',
            'description': 'Test Description'
        }

        response = self.client.post('/api/v1/projects/', data)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Test Project')
```

### 9.3 迁移测试

测试数据迁移的正确性：

```python
# apps/projects/tests/test_migrations.py

from django.test import TestCase
from django.core.management import call_command
from apps.projects.models import Project
from apps.api_testing.models import ApiProject

class MigrationTest(TestCase):
    def test_project_migration(self):
        # 运行迁移
        call_command('migrate', 'projects', verbosity=0)

        # 验证迁移结果
        api_projects = ApiProject.objects.all()
        migrated_projects = Project.objects.filter(project_type='API')

        self.assertEqual(api_projects.count(), migrated_projects.count())
```

## 10. 部署方案

### 10.1 部署流程

1. **准备阶段**
   - 备份数据库
   - 部署新版本代码
   - 执行数据库迁移

2. **切换阶段**
   - 停止旧服务
   - 启动新服务
   - 验证功能正常

3. **回滚阶段**
   - 如出现问题，执行回滚脚本
   - 恢复数据库备份
   - 启动旧服务

### 10.2 监控告警

部署后监控系统运行状态：

- 监控 API 响应时间
- 监控数据库查询性能
- 监控任务执行情况
- 监控错误日志

### 10.3 回滚方案

准备完整的回滚方案：

```bash
# 回滚脚本
#!/bin/bash

# 停止新服务
systemctl stop test-platform-new

# 恢复数据库
psql -U postgres -d test_platform -f backup.sql

# 启动旧服务
systemctl start test-platform-old

# 验证服务
curl -f http://localhost:8000/api/v1/health || exit 1

echo "回滚完成"
```

## 11. 风险与应对

### 11.1 技术风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 数据迁移失败 | 高 | 中 | 充分测试迁移脚本，提供回滚方案 |
| 性能下降 | 中 | 低 | 优化查询，添加索引，使用缓存 |
| API 兼容性问题 | 高 | 中 | 提供适配层，保持旧 API 可用 |
| 前端兼容性问题 | 中 | 低 | 渐进式重构，保持用户体验 |

### 11.2 业务风险

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|----------|
| 用户不适应新界面 | 中 | 高 | 提供培训文档，保留旧界面入口 |
| 数据丢失 | 高 | 低 | 充分备份，测试迁移脚本 |
| 功能缺失 | 高 | 低 | 详细对比功能清单，确保不遗漏 |

## 12. 附录

### 12.1 术语表

| 术语 | 说明 |
|------|------|
| 统一项目模型 | 整合 API、UI、性能测试项目的统一数据模型 |
| 项目类型 | 项目的分类标识：API/UI/PERFORMANCE/GENERAL |
| 任务类型 | 定时任务的分类标识：API/UI/PERFORMANCE |
| 适配层 | 保持旧 API 兼容的中间层 |
| 数据迁移 | 将旧模型数据迁移到新模型的过程 |

### 12.2 参考文档

- Django REST Framework 文档
- Vue 3 文档
- Element Plus 文档
- Celery 文档
- PostgreSQL 文档

### 12.3 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| v1.0 | 2025-01-06 | 初始版本 | AI Agent |
