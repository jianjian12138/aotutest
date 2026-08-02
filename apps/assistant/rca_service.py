import json
import traceback
from django.utils import timezone
from apps.api_testing.models import TestExecution as ApiTestExecution
from apps.ui_automation.models.execution import TestExecution as UiTestExecution
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from asgiref.sync import async_to_sync

class RCAService:
    
    @staticmethod
    def analyze_api_execution(execution_id):
        """分析 API 执行流水线的报错根因"""
        try:
            execution = ApiTestExecution.objects.get(id=execution_id)
            if execution.status != 'FAILED':
                execution.ai_rca_status = 'UNNECESSARY'
                execution.save()
                return
                
            execution.ai_rca_status = 'ANALYZING'
            execution.save()
            
            # Gather Context
            stats = f"总请求: {execution.total_requests}, 失败请求: {execution.failed_requests}"
            results_payload = json.dumps(execution.results, ensure_ascii=False)
            
            prompt = f"""
你是一个资深的 DevOps 和 API 自动化测试专家。请对以下失败的 API 测试执行报告进行 Root Cause Analysis (根因分析)。
测试统计: {stats}

执行详情 (JSON 截取):
{results_payload[:3000]}

请输出 Markdown 格式的分析报告，必须包含以下结构：
### 💥 核心失败原因总结
(用一句话概括)

### 🔍 异常断言与网络状态分析
(解析状态码、响应体及断言差距)

### 🛠️ 修复建议与自愈方案
(给出可落地的代码级或配置级检查步骤)
"""
            model_config = AIModelConfig.objects.filter(is_active=True).first()
            if not model_config:
                execution.ai_rca_status = 'FAILED'
                execution.ai_rca_result = "⚠️ 系统未配置激活的 AI 模型，无法进行根因分析。"
                execution.save()
                return
                
            messages = [{"role": "user", "content": prompt}]
            try:
                response_data = async_to_sync(AIModelService.call_openai_compatible_api)(model_config, messages)
                answer = response_data['choices'][0]['message']['content']
                
                execution.ai_rca_status = 'SUCCESS'
                execution.ai_rca_result = answer
            except Exception as e:
                execution.ai_rca_status = 'FAILED'
                execution.ai_rca_result = f"AI 服务调用失败: {str(e)}"
                
            execution.save()
            
        except Exception as e:
            print(f"RCA API Error: {str(e)}")

    @staticmethod
    def analyze_ui_execution(execution_id):
        """分析 UI Playwright 自动化执行链的崩溃根因"""
        try:
            execution = UiTestExecution.objects.get(id=execution_id)
            if execution.status != 'FAILED':
                execution.ai_rca_status = 'UNNECESSARY'
                execution.save()
                return
                
            execution.ai_rca_status = 'ANALYZING'
            execution.save()
            
            stats = f"总用例: {execution.total_cases}, 失败用例: {execution.failed_cases}, 时长: {execution.duration}s"
            
            prompt = f"""
你是一个资深的 Web UI 自动化测试专家和前端开发。请对以下失败的 Playwright 自动化执行进行根因分析。
统计: {stats}
执行环境浏览器: {execution.environment}
脚本层级错误（泛型推断）: 页面元素加载超时 (Timeout 30000ms exceeded) 或 严格模式下 Locator 定位器匹配到多个 DOM 节点。

请输出 Markdown 格式的详细诊断报告，包含：
### 💥 UI 阻塞/元素失效 抽象分析
(分析可能由于前端页面改版引发的 CSS 类名变动导致的 Locator 击穿)

### 🔍 DOM 树或网络层可能性排查
(排查是接口响应慢导致的异步渲染超时，还是 DOM 自身树形结构更改)

### 🛠️ Playwright 修复建议代码与定位器增强
(给出更高稳定性的 XPath/CSS 写法或使用 text=[文本] 的模糊查找替换方案)
"""
            model_config = AIModelConfig.objects.filter(is_active=True).first()
            if not model_config:
                execution.ai_rca_status = 'FAILED'
                execution.ai_rca_result = "⚠️ 系统未配置激活的 AI 模型，无法进行根因分析。"
                execution.save()
                return
                
            messages = [{"role": "user", "content": prompt}]
            try:
                response_data = async_to_sync(AIModelService.call_openai_compatible_api)(model_config, messages)
                answer = response_data['choices'][0]['message']['content']
                
                execution.ai_rca_status = 'SUCCESS'
                execution.ai_rca_result = answer
            except Exception as e:
                execution.ai_rca_status = 'FAILED'
                execution.ai_rca_result = f"AI 服务调用失败: {str(e)}"
                
            execution.save()
            
        except Exception as e:
            print(f"RCA UI Error: {str(e)}")
