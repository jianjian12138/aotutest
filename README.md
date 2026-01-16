# TestHub 智能测试管理平台

<div align="center">

**基于 AI 驱动的全栈测试管理平台**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2-green.svg)](https://www.djangoproject.com/)
[![Vue](https://img.shields.io/badge/Vue-3.3-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

## 📖 项目简介

TestHub 是一个功能强大的智能测试管理平台，集成了 **AI 需求分析**、**测试用例管理**、**API 测试**、**UI 自动化测试** 等多个模块，旨在提升测试效率和质量。平台采用 Django + Vue3 技术栈，提供现代化的用户界面和丰富的功能特性。

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
testhub_platform/
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
cd testhub_platform
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
DB_NAME=testhub
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
CREATE DATABASE testhub CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
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

TestHub智能测试管理平台包含以下核心功能模块：

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

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

如有问题或建议，欢迎通过 Issue 反馈。

---

<div align="center">
Made with ❤️ by 大刚（公众号：测试开发实战）
</div>

## � 详细使用说明

### 1. 系统登录与注册

#### 1.1 首次登录
1. 启动前端服务后，访问 `http://localhost:5173`
2. 点击 **注册账号**，填写用户名、邮箱和密码
3. 注册成功后自动跳转登录页面
4. 输入注册的账号密码，点击 **登录**
5. 首次登录后，系统会引导您完善个人信息

#### 1.2 管理员登录
- 系统默认管理员账号由初始化脚本创建
- 使用超级管理员账号登录后，可以进入 **系统管理** 模块

#### 1.3 忘记密码
1. 在登录页面点击 **忘记密码**
2. 输入注册邮箱，系统会发送重置密码链接
3. 点击邮件中的链接重置密码

### 2. 系统功能概述

登录成功后，您将看到系统主界面，包含以下核心功能模块：

- **仪表盘**: 展示系统概览、最近动态和统计数据
- **AI 需求分析**: 上传需求文档，AI 自动生成测试用例
- **测试用例管理**: 管理测试用例的完整生命周期
- **测试用例评审**: 对测试用例进行评审和优化
- **API 测试**: 管理和执行 API 测试
- **UI 自动化测试**: 创建和执行 UI 自动化测试，支持 AI 智能模式
- **测试执行**: 管理测试计划和执行记录
- **配置中心**: 管理系统配置和 AI 模型
- **个人设置**: 管理个人信息和偏好
- **系统管理**: 仅管理员可见，管理用户、角色和权限

### 3. 各功能模块使用说明

#### 3.1 仪表盘
- **功能**: 查看系统概览、最近动态和关键指标
- **使用流程**:
  1. 登录后自动进入仪表盘
  2. 查看测试用例统计、执行情况和最近活动
  3. 点击快捷入口进入各功能模块

#### 3.2 AI 需求分析
- **功能**: 上传需求文档，AI 自动解析并生成测试用例
- **使用流程**:
  1. 进入 **AI 需求分析** 模块
  2. 点击 **上传文档**，支持 PDF/Word/TXT 格式
  3. 选择 AI 模型和配置
  4. 点击 **开始分析**，等待 AI 处理
  5. 查看分析结果，提取的业务需求和生成的测试用例
  6. 编辑和调整生成的测试用例
  7. 点击 **保存** 将用例导入到测试用例库

#### 3.3 测试用例管理
- **功能**: 管理测试用例的创建、编辑、版本控制和归档
- **使用流程**:
  1. 进入 **测试用例管理** 模块
  2. **创建用例**:
     - 点击 **新建用例**
     - 填写用例基本信息（名称、描述、优先级等）
     - 添加测试步骤（前置条件、操作步骤、预期结果）
     - 上传附件（可选）
     - 点击 **保存**
  3. **组织用例**:
     - 按项目、版本、标签分类管理
     - 使用搜索和筛选功能快速定位用例
  4. **编辑用例**:
     - 点击用例名称进入详情页
     - 修改用例信息和步骤
     - 保存版本记录
  5. **导出用例**:
     - 选择要导出的用例
     - 点击 **导出**，支持 Excel、CSV 格式

#### 3.4 测试用例评审
- **功能**: 对测试用例进行评审，确保质量
- **使用流程**:
  1. 进入 **测试用例评审** 模块
  2. **创建评审任务**:
     - 点击 **新建评审**
     - 选择要评审的测试用例
     - 分配评审人员
     - 设置评审截止时间
  3. **执行评审**:
     - 评审人员进入评审任务
     - 查看测试用例详情
     - 添加评审意见和建议
     - 标记评审结果（通过/拒绝/需要修改）
  4. **查看评审结果**:
     - 用例作者查看评审意见
     - 根据意见修改用例
     - 重新提交评审

#### 3.5 API 测试
- **功能**: 创建和执行 API 测试，支持 HTTP/WebSocket 协议
- **使用流程**:
  1. 进入 **API 测试** 模块
  2. **创建 API 项目**:
     - 点击 **新建项目**
     - 填写项目名称和描述
  3. **创建 API 集合**:
     - 在项目下点击 **新建集合**
     - 组织 API 请求的树形结构
  4. **创建 API 请求**:
     - 选择请求方法（GET/POST/PUT/DELETE 等）
     - 填写 URL、请求头、请求体
     - 添加查询参数和路径参数
     - 配置断言规则
  5. **执行 API 请求**:
     - 点击 **发送** 执行单个请求
     - 查看响应结果、状态码和响应时间
  6. **创建测试套件**:
     - 选择多个 API 请求组成测试套件
     - 设置执行顺序和环境变量
  7. **执行测试套件**:
     - 点击 **运行** 执行整个套件
     - 查看执行报告和结果统计
  8. **设置定时任务**:
     - 配置测试套件的定时执行规则
     - 设置通知方式（邮件/Webhook）

#### 3.6 UI 自动化测试
- **功能**: 创建和执行 UI 自动化测试，支持传统模式和 AI 智能模式
- **使用流程**:
  1. 进入 **UI 自动化测试** 模块
  2. **创建 UI 项目**:
     - 点击 **新建项目**
     - 填写项目名称和描述
  3. **元素管理**:
     - 创建元素组，管理测试元素
     - 支持多种定位策略（ID、XPath、CSS 等）
  4. **页面对象管理**:
     - 创建页面对象，封装页面元素和操作
     - 支持页面对象继承和复用
  5. **创建测试脚本**:
     - **传统模式**: 手动编写测试步骤，调用页面对象方法
     - **AI 智能模式**:
       - 选择 AI 模型和模式（文本/视觉）
       - 输入测试任务描述
       - AI 自动生成测试步骤
       - 调整和优化生成的步骤
  6. **执行测试**:
     - 选择浏览器（Chrome/Firefox/Edge）
     - 选择运行模式（有头/无头）
     - 点击 **运行** 执行测试
  7. **查看执行结果**:
     - 查看详细执行日志
     - 查看测试截图和视频
     - 分析失败原因
  8. **创建测试套件**:
     - 组合多个测试用例
     - 配置执行顺序和环境
  9. **设置定时任务**:
     - 配置测试套件的定时执行
     - 设置通知方式

#### 3.7 测试执行
- **功能**: 管理测试计划和执行记录
- **使用流程**:
  1. 进入 **测试执行** 模块
  2. **创建测试计划**:
     - 点击 **新建计划**
     - 填写计划名称、描述和时间范围
     - 关联测试用例和执行人员
  3. **执行测试**:
     - 进入测试计划详情
     - 分配测试任务给团队成员
     - 执行测试并记录结果
  4. **查看执行报告**:
     - 查看测试覆盖率和通过率
     - 生成测试报告（支持 Allure 格式）
     - 导出和分享测试报告

### 4. 配置中心

- **功能**: 管理系统配置和 AI 模型
- **使用流程**:
  1. 进入 **配置中心** 模块
  2. **环境检测**:
     - 查看系统已安装的浏览器
     - 检测 Playwright 环境
  3. **驱动管理**:
     - 一键安装或更新浏览器驱动
  4. **AI 模型配置**:
     - 点击 **添加模型**
     - 选择 AI 提供商（OpenAI、DeepSeek、通义千问等）
     - 填写 API 密钥、模型名称和参数
     - 点击 **测试连接** 验证配置
     - 设置模型角色（测试用例编写器、Browser Use 等）
  5. **系统配置**:
     - 管理系统级配置项
     - 保存配置后立即生效

### 5. 个人设置

- **功能**: 管理个人信息和偏好设置
- **使用流程**:
  1. 点击右上角头像，选择 **个人设置**
  2. **基本信息**:
     - 修改用户名、邮箱和联系方式
     - 上传头像
  3. **密码设置**:
     - 修改登录密码
     - 设置密码强度
  4. **偏好设置**:
     - 设置默认浏览器
     - 调整界面主题
     - 配置通知偏好
  5. **安全设置**:
     - 查看登录日志
     - 管理 API 密钥

### 6. 系统管理（管理员）

- **功能**: 管理用户、角色和权限
- **使用流程**:
  1. 进入 **系统管理** 模块
  2. **用户管理**:
     - 查看和管理系统用户
     - 创建新用户，分配角色
     - 禁用或启用用户账号
  3. **角色管理**:
     - 创建和管理角色
     - 分配权限给角色
  4. **权限管理**:
     - 查看和管理系统权限
     - 配置权限组
  5. **系统日志**:
     - 查看系统操作日志
     - 审计用户行为
  6. **系统监控**:
     - 查看系统运行状态
     - 监控资源使用情况

## 🔧 常见问题解决

### 1. 服务访问异常
- **问题**: 登录页面显示 "服务访问异常" 或 "重连失败"
- **解决方法**:
  1. 检查后端服务是否正常运行
  2. 检查前端配置中的 API 地址是否正确
  3. 检查网络连接和防火墙设置

### 2. AI 模型连接失败
- **问题**: AI 模型测试连接失败
- **解决方法**:
  1. 检查 API 密钥是否正确
  2. 检查网络连接是否正常
  3. 检查 AI 模型服务是否可用
  4. 检查模型配置中的基础 URL 是否正确

### 3. UI 自动化测试执行失败
- **问题**: UI 自动化测试无法执行
- **解决方法**:
  1. 检查浏览器驱动是否正确安装
  2. 检查浏览器版本与驱动版本是否匹配
  3. 检查测试脚本中的元素定位是否正确
  4. 查看执行日志，分析具体错误原因

### 4. API 测试响应异常
- **问题**: API 请求返回错误状态码
- **解决方法**:
  1. 检查 API URL 和请求参数是否正确
  2. 检查请求头和认证信息
  3. 检查 API 服务是否正常运行
  4. 查看响应详情，分析错误原因

## 📊 最佳实践

### 1. 测试用例管理
- 遵循 "金字塔" 原则：单元测试 > API 测试 > UI 测试
- 每个测试用例应独立可执行
- 测试用例应包含清晰的前置条件、操作步骤和预期结果
- 定期评审和更新测试用例

### 2. AI 模型使用
- 为不同场景选择合适的 AI 模型
- 定期更新 AI 模型配置和参数
- 结合人工审核，优化 AI 生成的测试用例

### 3. 自动化测试
- 优先自动化稳定的功能
- 保持测试脚本的可维护性
- 定期运行自动化测试，及时发现问题
- 结合 CI/CD 流程，实现持续测试

### 4. 团队协作
- 明确团队成员角色和职责
- 建立规范的测试流程和标准
- 定期召开测试评审会议
- 分享测试经验和最佳实践

## �📚 核心功能模块说明

### 1. AI 需求分析模块 (`requirement_analysis`)

**功能**:
- 上传需求文档（PDF/Word/TXT）
- AI 自动解析需求文档内容
- 提取业务需求和功能点
- 基于需求自动生成测试用例
- 支持多种 AI 模型配置

**数据模型**:
- `RequirementDocument`: 需求文档
- `RequirementAnalysis`: 需求分析记录
- `BusinessRequirement`: 业务需求
- `GeneratedTestCase`: 生成的测试用例
- `AnalysisTask`: 分析任务
- `AIModelConfig`: AI 模型配置

### 2. 智能助手模块 (`assistant`)

**功能**:
- 集成 Dify AI 助手
- 多会话管理
- 聊天历史记录
- 测试咨询和问题解答

**数据模型**:
- `DifyConfig`: Dify API 配置
- `AssistantSession`: 助手会话
- `ChatMessage`: 聊天消息

### 3. API 测试模块 (`api_testing`)

**功能**:
- API 项目和集合管理
- HTTP/WebSocket 请求管理
- 环境变量管理
- 测试套件和自动化执行
- 请求历史和结果追踪
- 定时任务和通知
- Allure 报告生成

**数据模型**:
- `ApiProject`: API 项目
- `ApiCollection`: API 集合
- `ApiRequest`: API 请求
- `Environment`: 环境变量
- `TestSuite`: 测试套件
- `RequestHistory`: 请求历史
- `ApiScheduledTask`: 定时任务
- `ApiNotificationConfig`: 通知配置

### 4. UI 自动化测试模块 (`ui_automation`)

**功能**:
- 元素库管理（支持多种定位策略）
- 页面对象模式（POM）
- 测试脚本编辑和执行
- 测试套件批量执行
- 多浏览器支持
- 执行截图和视频录制
- 定时任务调度
- **AI 智能测试模式**:
  - 基于 Browser-use 框架的智能浏览器自动化
  - AI 自动理解页面结构并生成测试步骤
  - 支持文本模式（基于 DOM 解析）和视觉模式（基于截图识别）
  - 智能任务规划和执行
  - 执行过程实时日志记录

**核心组件**:
- `ai_base.py`: Browser-use 基础框架和补丁
- `ai_agent.py`: AI Agent 实现（BrowserAgent 类）
- `ai_models.py`: 多 AI 模型统一接口

**数据模型**:
- `UiProject`: UI 项目
- `Element`: 元素
- `ElementGroup`: 元素分组
- `PageObject`: 页面对象
- `TestScript`: 测试脚本
- `TestCase`: 测试用例
- `TestSuite`: 测试套件
- `TestExecution`: 测试执行
- `UiScheduledTask`: 定时任务
- `AICase`: AI 智能用例
- `AIIntelligentModeConfig`: AI 智能模式配置

### 5. 统一配置中心模块 (`configuration`)

**功能**:
- **环境检测**: 自动检测系统已安装的浏览器
- **驱动管理**: 一键安装 Playwright 浏览器驱动
- **AI 模型配置**:
  - 支持多种 AI 提供商：OpenAI、Azure OpenAI、Anthropic、Google Gemini、DeepSeek、硅基流动
  - 按角色配置：测试用例编写器、测试用例评审员、Browser Use 文本/视觉模式
  - API 密钥、基础 URL、模型名称、参数配置
  - 连接测试功能

**API 路由**:
- `/api/ui-automation/config/environment/`: 环境配置
- `/api/ui-automation/config/ai-mode/`: AI 智能模式配置

### 6. 测试用例评审模块 (`reviews`)

**功能**:
- 创建评审任务
- 分配评审人员
- 评审意见记录
- 评审模板管理
- 评审状态跟踪

**数据模型**:
- `TestCaseReview`: 测试用例评审
- `ReviewAssignment`: 评审分配
- `TestCaseReviewComment`: 评审意见
- `ReviewTemplate`: 评审模板

### 7. 测试执行模块 (`executions`)

**功能**:
- 测试计划管理
- 测试执行记录
- 执行历史追踪
- 执行结果统计

**数据模型**:
- `TestPlan`: 测试计划
- `TestRun`: 测试执行
- `TestRunCase`: 测试执行用例
- `TestRunCaseHistory`: 执行历史

## 🔧 配置说明

### JWT 安全配置

项目采用企业级 JWT 双 Token 安全机制：

**后端配置** (`backend/settings.py`):
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),  # Access Token 30分钟
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),     # Refresh Token 7天
    'ROTATE_REFRESH_TOKENS': True,                   # 刷新时轮换 Refresh Token
    'BLACKLIST_AFTER_ROTATION': True,                # 旧 Refresh Token 加入黑名单
    'UPDATE_LAST_LOGIN': True,
    'ALGORITHM': 'HS256',
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**安全特性**:
- 双 Token 机制：短期 Access Token + 长期 Refresh Token
- 自动刷新：Token 过期前 5 分钟自动刷新，无感续期
- Token 黑名单：登出时将 Refresh Token 加入黑名单，防止重放攻击
- 请求队列：Token 刷新期间的请求自动排队等待
- 防循环机制：logout 函数包含防循环调用保护

**前端 Token 管理**:
- Token 存储在 localStorage
- 请求拦截器自动添加 Bearer Token
- 响应拦截器处理 401 错误并自动刷新 Token

### AI 智能模式配置

在统一配置中心可以配置多种 AI 模型：

**支持的 AI 提供商**:
- **OpenAI**: GPT-4、GPT-3.5 等模型
- **Azure OpenAI**: Azure 托管的 OpenAI 服务
- **Anthropic**: Claude 系列模型
- **Google Gemini**: Gemini Pro、Gemini Flash
- **DeepSeek**: DeepSeek 系列模型
- **硅基流动**: 聚合多种 AI 模型

**配置角色**:
- `testcase_writer`: 测试用例编写
- `testcase_reviewer`: 测试用例评审
- `browser_use_text`: Browser Use 文本模式（DOM 解析）
- `browser_use_vision`: Browser Use 视觉模式（截图识别）

**配置参数**:
- API Key: API 访问密钥
- Base URL: API 端点地址（可选）
- Model Name: 模型名称
- Temperature: 温度参数（控制随机性）
- Max Tokens: 最大生成 Token 数

**连接测试**:
配置完成后可使用"测试连接"功能验证配置是否正确。

### AI 需求分析配置

在系统配置中心可以配置多种 AI 模型：

- **DeepSeek**: 用于需求分析和用例生成
- **通义千问**: 备选 AI 模型
- **硅基流动**: 备选 AI 模型
- **自定义模型**: 支持配置自定义 API

### Dify 助手配置

配置 Dify API 以启用智能助手功能：

- API URL: Dify API 端点
- API Key: Dify API 密钥

### UI 自动化配置

- **执行引擎**: Selenium / Playwright
- **浏览器**: Chrome / Firefox / Edge
- **WebDriver**: 自动下载或手动配置驱动路径
- **运行模式**: 有头模式 / 无头模式
- **AI 智能模式**:
  - 文本模式：基于 DOM 解析，快速高效
  - 视觉模式：基于截图识别，适合复杂页面

### 通知配置

- **邮件通知**: SMTP 配置
- **Webhook 通知**: 企业微信、钉钉等

## 📊 数据库设计

项目使用 MySQL 数据库，主要表结构包括：

- **用户相关**: `users`, `user_profiles`
- **项目管理**: `projects`, `project_members`, `versions`
- **测试用例**: `testcases`, `testcase_steps`, `testcase_attachments`, `testcase_comments`
- **测试套件**: `testsuites`, `testsuite_cases`
- **测试执行**: `test_plans`, `test_runs`, `test_run_cases`
- **用例评审**: `testcase_reviews`, `review_assignments`, `review_comments`
- **需求分析**: `requirement_documents`, `requirement_analyses`, `business_requirements`, `generated_test_cases`
- **AI 配置**: `ai_model_configs`, `prompt_configs` - AI 模型和提示词配置
- **智能助手**: `dify_configs`, `assistant_sessions`, `chat_messages`
- **API 测试**: `api_projects`, `api_collections`, `api_requests`, `api_environments`, `test_suites`, `request_history`, `api_scheduled_tasks`
- **UI 自动化**: `ui_projects`, `ui_elements`, `element_groups`, `ui_page_objects`, `ui_test_scripts`, `ui_test_cases`, `ui_test_suites`, `ui_test_executions`, `ui_scheduled_tasks`, `ai_cases`, `ai_intelligent_mode_configs`
- **JWT 安全**: `blacklisted_token`, `outstanding_token` - Token 黑名单管理

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request 来帮助改进项目！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 📧 联系方式

如有问题或建议，欢迎通过 Issue 反馈。

---

<div align="center">
Made with ❤️ by 大刚（公众号：测试开发实战）
</div>