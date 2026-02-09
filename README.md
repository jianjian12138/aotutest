# Testing Platform (智能测试平台)

## 简介
Testing Platform 是一个全方位的智能测试解决方案，集成了 AI 辅助测试、接口自动化、UI 自动化、性能测试、安全测试以及数据工厂等多种能力。平台旨在通过智能化手段提升测试效率，降低测试门槛，实现从需求分析到测试报告的全流程覆盖。

## 核心功能模块

### 1. AI 用例生成 (AI Generation)
*   **需求分析**：基于 AI 模型对需求文档进行深度分析。
*   **用例生成**：自动生成高质量的测试用例。
*   **评审管理**：支持用例评审流程和模板管理。

### 2. 接口测试 (API Testing)
*   **接口管理**：HTTP/HTTPS 接口的定义与维护。
*   **自动化测试**：支持测试场景编排与自动化执行。
*   **定时任务**：支持基于 Crontab 的定时执行策略。
*   **多环境支持**：灵活切换测试环境配置。

### 3. UI 自动化 (UI Automation)
*   **AI 驱动 (Stagehand 模式)**：集成 Stagehand 能力，支持基于自然语言的动作执行 (Act) 和数据提取 (Extract)。
*   **自愈合执行**：不再依赖脆弱的选择器，利用 LLM 视觉与语义理解能力动态定位元素，极大提高脚本稳定性。
*   **元素管理**：智能元素定位与管理，支持 Smart Inspector 侦测。
*   **多端支持**：覆盖 Web 和 App 端测试。

### 4. 自然语言测试 (Natural Language Testing)
*   **Midscene 集成**：通过自然语言指令直接驱动浏览器操作。
*   **智能交互**：降低自动化脚本编写成本，实现"说话即测试"。

### 5. 性能测试 (Performance Test)
*   **压测管理**：支持集合管理与请求编排。
*   **执行报告**：实时监控压测数据与生成详细报告。

### 6. 安全测试 (Strix Security)
*   **漏洞扫描**：自动化扫描系统漏洞。
*   **风险评估**：提供安全风险评估报告。

### 7. 数据工厂 (Data Factory)
*   **RAG 增强 SQL 生成**：集成 SQLBot (Vanna.ai 模式)，基于 RAG 技术实现高准确率的 Text-to-SQL。
*   **智能上下文**：支持表结构自动检索、元数据语义增强与少样本学习 (Few-Shot Learning)。
*   **自我修正**：具备 SQL 执行错误自动分析与修复能力。
*   **数据构造**：自动生成各类测试数据（姓名、地址、证件号等）。

### 8. 知识图谱 (Knowledge Graph)
*   **领域知识库**：构建测试领域的知识网络。
*   **AI 助手**：基于知识图谱的智能问答助手。

### 9. 配置中心 (Configuration)
*   **AI 模型配置**：管理 LLM 模型参数。
*   **CI/CD 集成**：流水线配置与监控。
*   **系统设置**：用户管理、通知配置、MCP 服务集成等。

## 技术栈

### 前端 (Frontend)
*   **框架**：Vue 3 + Vite
*   **UI 组件库**：Element Plus
*   **可视化**：ECharts
*   **编辑器**：Monaco Editor
*   **状态管理**：Pinia

### 后端 (Backend)
*   **框架**：Django + Django REST Framework
*   **任务队列**：Celery
*   **文档**：Drf-spectacular (Swagger/Redoc)
*   **测试引擎**：Playwright, Selenium, Pytest

## 快速开始

### 前端启动
```bash
cd frontend
npm install
npm run dev
```

### 后端启动
```bash
# 确保已安装 Python 依赖
pip install -r requirements.txt

# 迁移数据库
python manage.py migrate

# 启动服务
python manage.py runserver
```

## 目录结构
*   `frontend/`: 前端 Vue 项目源码
*   `apps/`: 后端 Django 应用模块
*   `allure/`: Allure 报告相关配置
*   `scripts/`: 运维与初始化脚本
*   `media/`: 静态媒体文件存储
