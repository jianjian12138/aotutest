# Testing Platform (智能测试平台)

## 简介
Testing Platform 是一个全方位的智能测试解决方案，集成了 AI 辅助测试、接口自动化、UI 自动化、性能测试、安全测试以及数据工厂等多种能力。平台旨在通过智能化手段提升测试效率，降低测试门槛，实现从需求分析到测试报告的全流程覆盖。

## 核心功能模块

### 🌟 V2 AI 核心级特性 (V2 AI Core Features)
*   **AI 智能错误根因诊断 (RCA Engine)**：在接口测试与 UI 测试中深度集成 LLM。测试失败时可一键召唤 AI Copilot，智能解析异常日志、网络请求和上下文，直接输出精准的崩溃原因与修复代码。
*   **AI 元素智能自愈 (UI Locator Self-Healing)**：终结 UI 测试中“定位器频繁失效”的痛点。AI 自动捕捉失效 DOM 树上下文，逆向推导并生成抗干扰的 Playwright/Selenium 替代选择器，实现“一键采纳，自我修复”。
*   **AI 数据探索员 (Text-to-SQL Agent)**：数据工厂全面进化！引入自然语言到 SQL 的转化模型。用户只需用中文描述“查出某项目的用例执行失败率”，Agent 即可自动抓取元数据进行推理并返回分析图表。
*   **多智能体需求转测闭环 (Multi-Agent Verification)**：破除业务壁垒，将 PRD 需求文档直接编译为可执行策略！上传产品需求文档，内置 Orchestrator 智能体将打散文字，自动化排布 API 接口和依赖关系，零代码转化为开箱即用的测试套件。
*   **十万级测试用例秒级渲染**：引入全局动态虚拟滚动 (`vue-virtual-scroller`) 架构。突破浏览器 DOM 渲染极限，全面支持展示十万级以上的密集型 API 测试回归网格并彻底消除 OOM 崩溃。

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

### 🌟 V3 智能化测试集成 (V3 Intelligent Testing Integration)
*   **智能化测试全家桶 (Unified Intelligent Suite)**：将四大 AI 核心模块（自主探索 Agent、精准测试与风险预测、多模态视觉回归、云原生执行池）统一集成至“智能化测试”导航下，实现 AI 赋能的一站式体验。
*   **自主探索 Agent (Autonomous Crawler)**：基于 DOM 语义与 CoT 思维链，AI 能够自主探索业务流程，自动生成高覆盖率的操作路径，告别手动编写繁琐的爬虫脚本。
*   **精准测试与风险预测 (Predictive QA)**：深度扫描 Git Commit 变更，利用 AST 静态分析技术建立“代码-接口-用例”映射图谱，精准推荐受影响的回归测试范围。
*   **多模态视觉回归 (Visual AI Regression)**：引入 AI 视觉比对，智能识别页面布局中的“微小但致命”的 UI 偏离，自动过滤反爬虫干扰，让 UI 自动化拥有“人类般的眼睛”。
*   **云原生执行池 (K8s Runner Pool)**：支持基于 Kubernetes 的弹性伸缩执行引擎，海量测试任务并行时自动拉起 Pod 集群，任务结束即销毁，极致资源利用率。

### 🎨 交互式专业首页 (Interactive Professional Home)
*   **Professional Space 主题**：采用深邃星象背景与极简品牌设计，彻底消除视觉杂乱，展现企业级软件的高级质感。
*   **反重力实时交互 (Anti-Gravity Drag)**：首页模块支持物理感应式拖拽。你可以随意“摘取”行星模块在屏幕中飞舞，释放后图标会带着灵动的弹簧效果自动吸附回原始轨道。
*   **绝对水平对齐**：通过精密的 CSS 动画抵消逻辑，确保所有功能模块的标签在 360 度旋转过程中始终保持水平正立，阅读体验无可挑剔。

### 4. 智能测试 (Intelligent Testing)
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
