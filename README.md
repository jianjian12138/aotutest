# testing 智能测试管理平台

<div align="center">

**基于 AI 驱动的全栈测试管理平台**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 📖 项目简介

testing 是一个功能强大的智能测试管理平台，集成了 **AI 需求分析**、**测试用例管理**、**API 测试**、**UI 自动化测试** 等多个模块，旨在提升测试效率和质量。平台采用 Django + Vue3 技术栈，提供现代化的用户界面和丰富的功能特性。

## ✨ 核心特性

### 🤖 AI 智能化能力
- **AI 需求分析**: 自动解析需求文档（PDF/Word/TXT），智能提取业务需求
- **智能测试用例生成**: 基于需求自动生成测试用例，支持多种测试类型
- **智能助手**: 集成 Dify AI 助手，提供测试咨询和问题解答
- **多模型支持**: 支持 DeepSeek、通义千问、硅基流动等多种 AI 模型
- **AI 智能模式**: 基于 Browser-use 的智能浏览器自动化，AI 理解页面并自动完成测试

### 🔐 安全机制
- **JWT 认证**: 采用企业级 JWT 双 Token 安全机制
- **自动刷新**: Access Token 过期前自动刷新，无感续期
- **Token 黑名单**: 登出时自动将 Token 加入黑名单，防止重放攻击
- **请求队列**: Token 刷新期间请求自动排队等待，确保请求不丢失

### ⚙️ 统一配置中心
- **环境检测**: 自动检测系统浏览器和 Playwright 环境
- **驱动管理**: 一键安装和更新浏览器驱动
- **AI 模型配置**: 统一管理多种 AI 模型的 API 配置
- **连接测试**: 支持 AI 模型连接测试和验证

### 📋 测试用例管理
- **完整的用例生命周期管理**: 创建、编辑、版本控制、归档
- **灵活的用例组织**: 支持项目、版本、标签等多维度分类
- **详细的用例步骤**: 支持步骤化用例设计，包含前置条件、操作步骤、预期结果
- **附件和评论**: 支持用例附件上传和团队协作评论

### 🔍 测试用例评审
- **评审流程管理**: 支持多人评审、评审模板、检查清单
- **评审状态跟踪**: 待评审、评审中、已通过、已拒绝等状态管理
- **评审意见记录**: 支持整体意见、用例意见、步骤意见等多层级反馈
- **评审模板**: 可自定义评审检查清单和默认评审人

### 🌐 API 测试
- **项目和集合管理**: 支持 HTTP/WebSocket 协议，树形结构组织 API
- **请求管理**: 支持 GET/POST/PUT/DELETE/PATCH 等多种 HTTP 方法
- **环境变量**: 全局和局部环境变量管理，支持变量替换
- **测试套件**: 批量执行 API 请求，支持断言和执行顺序配置
- **请求历史**: 完整的请求执行历史记录和结果追踪
- **定时任务**: 支持定时执行测试套件，邮件/Webhook 通知
- **测试报告**: 自动生成 Allure 测试报告

### 🖥️ UI 自动化测试
- **双引擎支持**: 支持 Selenium 和 Playwright 两种自动化引擎
- **元素管理**: 元素库管理，支持多种定位策略（ID、XPath、CSS 等）
- **页面对象模式**: 支持 POM 设计模式，提高脚本可维护性
- **测试脚本**: 可视化脚本编辑器，支持步骤录制和回放
- **测试套件**: 批量执行测试脚本，支持多浏览器（Chrome/Firefox/Edge）
- **执行记录**: 详细的执行日志、截图、视频录制
- **定时任务**: 支持 Cron 表达式、固定间隔、单次执行
- **AI 智能模式**:
  - 基于 Browser-use 框架的智能浏览器自动化
  - AI 理解页面结构并自动完成测试任务
  - 支持文本模式（基于 DOM 解析）和视觉模式（基于截图识别）
  - 支持多种 AI 模型：OpenAI、Anthropic、Google Gemini、DeepSeek、硅基流动等
  - 智能任务规划和步骤自动生成

### 📊 测试执行与报告
- **测试计划**: 创建测试计划，关联项目、版本和测试用例
- **测试执行**: 手动和自动化测试执行，实时记录测试结果
- **执行历史**: 完整的执行历史追踪和结果对比
- **测试报告**: 多维度数据统计和可视化图表
- **Allure 集成**: 支持生成专业的 Allure 测试报告

### 👥 项目与团队管理
- **项目管理**: 多项目支持，项目成员和角色管理
- **版本管理**: 版本规划和测试用例关联
- **权限控制**: 基于项目的成员角色权限管理
- **用户配置**: 个性化用户设置和偏好配置

## 🏗️ 技术架构

### 后端技术栈
- **框架**: Django 4.2 + Django REST Framework
- **数据库**: MySQL 8.0+ (PyMySQL)
- **API 文档**: drf-spectacular (Swagger/ReDoc)
- **安全认证**: JWT (rest_framework_simplejwt) + Token 黑名单
- **AI 集成**:
  - browser-use: AI 驱动的浏览器自动化
  - langchain-openai: LLM 集成框架
  - 多模型支持：OpenAI、Anthropic、Google Gemini、DeepSeek、硅基流动等
- **自动化测试**: Selenium, Playwright, Allure
- **HTTP 客户端**: httpx (异步 HTTP)
- **定时任务**: Django APScheduler

### 前端技术栈
- **框架**: Vue 3.3 + Composition API
- **构建工具**: Vite 4.4
- **UI 组件**: Element Plus 2.3
- **状态管理**: Pinia 2.1
- **路由**: Vue Router 4.2
- **HTTP 客户端**: Axios 1.5
- **数据可视化**: ECharts 5.4
- **代码编辑器**: Monaco Editor
- **其他**: vuedraggable (拖拽), xlsx (Excel), dayjs (日期)

## 📁 项目结构

```
testing_platform/
├── apps/                           # Django 应用模块
│   ├── users/                      # 用户管理
│   ├── projects/                   # 项目管理
│   ├── testcases/                  # 测试用例管理
│   ├── testsuites/                 # 测试套件管理
│   ├── executions/                 # 测试执行管理
│   ├── reports/                    # 测试报告
│   ├── reviews/                    # 用例评审管理
│   ├── versions/                   # 版本管理
│   ├── requirement_analysis/       # AI 需求分析
│   ├── assistant/                  # 智能助手
│   ├── api_testing/                # API 测试
│   └── ui_automation/              # UI 自动化测试
├── backend/                        # Django 项目配置
│   ├── settings.py                 # 项目设置
│   ├── urls.py                     # URL 路由
│   └── middleware.py               # 中间件
├── frontend/                       # Vue3 前端
│   ├── src/
│   │   ├── api/                    # API 接口
│   │   ├── components/             # 公共组件
│   │   ├── views/                  # 页面视图
│   │   │   ├── auth/               # 登录注册
│   │   │   ├── projects/           # 项目管理
│   │   │   ├── testcases/          # 测试用例
│   │   │   ├── reviews/            # 用例评审
│   │   │   ├── requirement-analysis/  # 需求分析
│   │   │   ├── assistant/          # 智能助手
│   │   │   ├── api-testing/        # API 测试
│   │   │   ├── ui-automation/      # UI 自动化
│   │   │   │   ├── ai/             # AI 智能模式
│   │   │   │   ├── config/         # 配置管理
│   │   │   │   └── suites/         # 测试套件
│   │   │   └── configuration/      # 统一配置中心
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── router/                 # 路由配置
│   │   ├── utils/                  # 工具函数
│   │   └── assets/                 # 静态资源
│   └── package.json
├── media/                          # 媒体文件（上传文件、截图等）
├── logs/                           # 日志文件
├── allure/                         # Allure 测试报告
├── requirements.txt                # Python 依赖
└── manage.py                       # Django 管理脚本
```

## 🚀 快速开始

### 环境要求

- **Python**: 3.11+
- **Node.js**: 18+
- **MySQL**: 8.0+
- **浏览器驱动**: ChromeDriver / GeckoDriver (用于 UI 自动化)

### 后端部署

1. **克隆项目**
```bash
git clone <repository-url>
cd testing_platform
```

2. **创建虚拟环境**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置环境变量**

创建 `.env` 文件：
```env
# 数据库配置
DB_NAME=testing
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=3306

# Django 配置
SECRET_KEY=your-secret-key-here
DEBUG=True

# 邮件配置（可选）
EMAIL_HOST=smtp.163.com
EMAIL_PORT=465
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_email_password
DEFAULT_FROM_EMAIL=your_email@gmail.com
```

5. **初始化数据库**
```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE testing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
EXIT;

# 创建 migrations 目录（如果不存在）
mkdir -p apps/testcases/migrations
echo "# This file is intentionally left empty" > apps/testcases/migrations/__init__.py

# 执行迁移
python manage.py makemigrations
python manage.py migrate

# 创建超级用户
python manage.py createsuperuser
```

6. **初始化UI自动化测试定位策略**
```bash
# 根目录执行
python manage.py init_locator_strategies
```

7. **启动服务**
```bash
# 启动 Django 开发服务器
python manage.py runserver 0.0.0.0:4545
```

### 前端部署

1. **安装依赖**
```bash
cd frontend
npm install
```

2. **启动开发服务器**
```bash
npm run dev
```

3. **构建生产版本**
```bash
npm run build
```

### 访问应用

- **前端**: http://localhost:5656
- **后端 API**: http://localhost:4545
- **API 文档**: http://localhost:4545/api/docs/
- **Admin 后台**: http://localhost:4545/admin/

## 📖 详细使用说明

### 1. 系统登录与注册

#### 1.1 登录
1. 打开浏览器访问前端地址：http://localhost:5656
2. 在登录页面输入用户名和密码
3. 点击"登录"按钮进入系统

#### 1.2 注册
1. 在登录页面点击"没有账号？立即注册"
2. 填写注册信息：用户名、邮箱、密码
3. 点击"注册"按钮完成注册
4. 使用新注册的账号登录系统

### 2. 系统功能概述

testing智能测试管理平台包含以下核心功能模块：

| 模块名称 | 主要功能 | 访问路径 |
|---------|---------|---------|
| 首页 | 系统概览、功能入口 | /home |
| AI用例生成 | AI需求分析、测试用例自动生成 | /ai-generation/requirement-analysis |
| 接口测试 | API项目管理、接口测试执行 | /api-testing/dashboard |
| UI自动化测试 | UI项目管理、自动化脚本编写 | /ui-automation/dashboard |
| 数据工厂 | SQL生成、数据查询 | /data-factory/dashboard |
| 性能测试 | 性能测试项目管理、执行 | /performance-test/dashboard |
| WHartTest | WHartTest集成功能 | /wharttest/dashboard |
| 配置中心 | AI模型配置、系统配置 | /configuration/ai-model |

### 3. 各功能模块使用说明

#### 3.1 AI用例生成模块

**功能说明**：该模块利用AI技术自动分析需求文档并生成测试用例。

**使用步骤**：
1. 进入"AI用例生成"页面
2. 点击"上传需求文档"按钮，选择PDF/Word/TXT格式的需求文档
3. 选择AI模型和配置
4. 点击"开始分析"按钮
5. 等待分析完成，查看生成的测试用例
6. 可对生成的测试用例进行编辑、保存或导出

#### 3.2 接口测试模块

**功能说明**：用于管理和执行API测试，支持HTTP/WebSocket协议。

**使用步骤**：
1. 进入"接口测试"模块
2. **创建项目**：
   - 点击"新建项目"按钮
   - 填写项目名称、描述等信息
   - 点击"保存"按钮
3. **创建接口集合**：
   - 在项目中点击"新建集合"
   - 填写集合名称和描述
4. **创建API请求**：
   - 在集合中点击"新建请求"
   - 选择请求方法（GET/POST/PUT等）
   - 填写URL、请求头、请求体等信息
   - 点击"发送"按钮测试请求
5. **创建测试套件**：
   - 点击"新建测试套件"
   - 添加需要执行的API请求
   - 配置断言和执行顺序
6. **执行测试**：
   - 选择测试套件
   - 点击"执行"按钮
   - 查看执行结果和报告

#### 3.3 UI自动化测试模块

**功能说明**：用于编写和执行UI自动化测试脚本，支持Selenium和Playwright引擎。

**使用步骤**：
1. 进入"UI自动化测试"模块
2. **创建项目**：
   - 点击"新建项目"按钮
   - 填写项目信息并保存
3. **元素管理**：
   - 进入"元素管理"页面
   - 点击"新建元素"按钮
   - 填写元素名称、定位方式和定位表达式
4. **编写测试脚本**：
   - 进入"脚本管理"页面
   - 点击"新建脚本"
   - 使用可视化编辑器编写测试步骤
   - 保存脚本
5. **执行测试**：
   - 选择测试脚本
   - 点击"执行"按钮
   - 选择浏览器环境
   - 查看执行结果和截图

#### 3.4 数据工厂模块

**功能说明**：用于生成测试数据和执行SQL查询。

**使用步骤**：
1. 进入"数据工厂"模块
2. **SQL生成**：
   - 进入"SQL生成"页面
   - 输入自然语言描述的查询需求
   - 点击"生成SQL"按钮
   - 查看生成的SQL语句
3. **执行查询**：
   - 在"SQL生成"页面点击"执行查询"
   - 查看查询结果
4. **保存查询**：
   - 点击"保存查询"按钮
   - 填写查询名称和描述

#### 3.5 性能测试模块

**功能说明**：用于进行性能测试，模拟多用户并发访问。

**使用步骤**：
1. 进入"性能测试"模块
2. **创建项目**：
   - 点击"新建项目"按钮
   - 填写项目信息并保存
3. **创建集合**：
   - 在项目中点击"新建集合"
   - 填写集合信息
4. **创建请求**：
   - 在集合中点击"新建请求"
   - 配置请求参数
5. **创建测试套件**：
   - 点击"新建测试套件"
   - 添加请求并配置并发数、持续时间等参数
6. **执行性能测试**：
   - 选择测试套件
   - 点击"执行"按钮
   - 查看实时性能指标和报告

#### 3.6 WHartTest模块

**功能说明**：集成WHartTest功能，用于执行WHartTest测试任务。

**使用步骤**：
1. 进入"WHartTest"模块
2. **配置管理**：
   - 进入"配置管理"页面
   - 点击"新建配置"按钮
   - 填写WHartTest服务地址和API密钥
3. **项目管理**：
   - 进入"项目管理"页面
   - 点击"新建项目"按钮
   - 关联WHartTest配置
4. **执行测试**：
   - 进入"执行管理"页面
   - 点击"新建执行"按钮
   - 配置执行参数
   - 点击"执行"按钮
5. **查看结果**：
   - 在"执行管理"页面查看执行状态
   - 点击执行记录查看详细结果

### 4. 配置中心

**功能说明**：用于配置系统各项参数，包括AI模型、UI自动化环境等。

**使用步骤**：
1. 进入"配置中心"模块
2. **AI模型配置**：
   - 进入"AI模型配置"页面
   - 点击"新建配置"按钮
   - 选择AI提供商和模型
   - 填写API密钥和其他参数
   - 点击"测试连接"验证配置
   - 点击"保存"按钮
3. **UI环境配置**：
   - 进入"UI环境配置"页面
   - 检查浏览器和驱动状态
   - 点击"安装驱动"按钮安装所需驱动

### 5. 个人设置

**功能说明**：用于管理用户个人信息和偏好设置。

**使用步骤**：
1. 点击右上角用户头像
2. 选择"个人设置"
3. 编辑个人信息
4. 修改密码
5. 保存设置

### 6. 系统管理（管理员）

**功能说明**：用于管理系统用户、角色和权限。

**使用步骤**：
1. 进入"系统管理"模块
2. **用户管理**：
   - 查看用户列表
   - 点击"新建用户"按钮创建新用户
   - 编辑或删除现有用户
3. **角色管理**：
   - 查看角色列表
   - 点击"新建角色"按钮创建新角色
   - 配置角色权限
4. **权限管理**：
   - 查看权限列表
   - 配置权限分配

## 🔧 常见问题解决

### 1. 登录失败
- **原因**：用户名或密码错误
- **解决方法**：检查用户名和密码是否正确，或点击"忘记密码"重置密码

### 2. API请求执行失败
- **原因**：URL错误、请求参数不正确、服务器未响应
- **解决方法**：检查URL和请求参数，确保服务器正常运行

### 3. UI自动化测试执行失败
- **原因**：浏览器驱动版本不匹配、元素定位表达式错误
- **解决方法**：更新浏览器驱动，检查并修正元素定位表达式

### 4. AI模型连接失败
- **原因**：API密钥错误、网络连接问题
- **解决方法**：检查API密钥是否正确，确保网络连接正常

### 5. 上传文件失败
- **原因**：文件格式不支持、文件过大
- **解决方法**：检查文件格式是否符合要求，减小文件大小

## 📊 最佳实践

1. **项目管理**：
   - 为每个测试项目创建独立的项目空间
   - 合理划分测试集合和模块
   - 定期备份测试用例和脚本

2. **测试用例管理**：
   - 使用清晰的命名规则
   - 包含完整的测试步骤和预期结果
   - 定期评审和更新测试用例

3. **自动化测试**：
   - 优先自动化核心业务流程
   - 使用页面对象模式(POM)设计测试脚本
   - 定期维护和更新自动化脚本

4. **AI模型使用**：
   - 根据需求选择合适的AI模型
   - 合理设置模型参数
   - 对生成的内容进行人工审核

5. **报告管理**：
   - 定期生成和分析测试报告
   - 分享报告给相关团队成员
   - 基于报告结果持续改进测试流程

