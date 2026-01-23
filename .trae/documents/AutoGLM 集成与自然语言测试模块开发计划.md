# 自然语言测试模块（AutoGLM集成）开发计划

## 1. 后端核心引擎实现
### 创建 Mobile AI Agent
- 新建 `apps/ui_automation/ai_mobile.py`
- 实现 `BasePhoneAgent` 类，封装 `AutoGLM` 调用逻辑（ADB 截图、指令下发、模型交互）。
- 集成 `AIExecutionRecord` 用于记录执行日志和截图。

### 扩展 API 接口
- 修改 `apps/ui_automation/views.py`
- 新增 `run_mobile_ai_task` API 接口，处理移动端自然语言指令。
- 对接 `DeviceManager` 获取当前连接的设备。

## 2. 前端架构与路由重构
### 调整菜单结构
- 修改 `frontend/src/router/index.js`
- 将 `/ai-intelligent-mode` 重命名为 `/natural-language-testing`。
- 拆分路由为：
  - `web-testing`: Web智能测试（原功能）
  - `app-testing`: App智能测试（新功能）
  - `cases`: 智能用例管理
  - `history`: 执行历史记录

### 更新侧边栏
- 确保侧边栏菜单名称更新为“自然语言测试模块”。

## 3. 移动端 AI 界面开发
### 新增 App 智能测试页面
- 创建 `frontend/src/views/ui-automation/ai/MobileAITesting.vue`
- 实现设备选择下拉框（集成 ADB 设备列表）。
- 实现聊天/指令输入界面。
- 实现实时执行日志和手机屏幕截图预览。

## 4. 配置中心适配
### 模型配置更新
- 检查 `apps/requirement_analysis/models.py` 和前端 `AIModelConfig.vue`。
- 确保用户可以在配置中心添加 `AutoGLM` 模型配置（Base URL, Model Name）。
