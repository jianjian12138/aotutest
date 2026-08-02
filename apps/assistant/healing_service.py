import json
from apps.ui_automation.models.element import Element
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from asgiref.sync import async_to_sync

class SelfHealingService:
    
    @staticmethod
    def suggest_locators(element_id):
        """为失效的UI元素提供智能定位自愈建议"""
        try:
            element = Element.objects.get(id=element_id)
            
            context = f"""
元素名称: {element.name}
类型: {element.get_element_type_display()}
所属页面: {element.page}
当前失效定位策略: {element.locator_strategy.name}
当前失效定位值: {element.locator_value}
元素备注描述: {element.description}
"""
            
            prompt = f"""
你是一个非常资深的 Playwright 自动化测试与前端架构专家。
因为由于前端 Vue/React 页面的更新，测试项目中定义的一个 UI 元素的定位器 (Locator) 或者 CSS 类名已经失效，导致执行期间经常出现 `TimeoutError` 等节点不可见异常。

根据以下是该在我们的 UI 自动化维护平台上原本登记的属性字典语义信息：
{context}

请利用你的 Web 领域测试知识储备，进行智能推演补偿。推荐提供 3 - 5 种极具鲁棒性（防丢防失效能力强）的高可用推测替换定位策略。请在 CSS / XPath / Text 维度中分别尝试突破。

你必须严格以合法的 JSON Array 字符串格式返回数据（便于后端反序列化映射），对象的 Schema 标准如下：
[
  {{ "strategy": "CSS", "value": ".class > input", "description": "采用直接类名与后代组件挂钩" }},
  {{ "strategy": "XPath", "value": "//button[contains(text(),'xx')]", "description": "脱离脆弱的哈希样式名，使用文本锚定" }}
]

请确保 ONLY 输出合法的 JSON 数组，【不要】输出 \`\`\`json 的 Markdown 代码块，不要包含任何自然语言解释说明！
"""
            model_config = AIModelConfig.objects.filter(is_active=True).first()
            if not model_config:
                return {"error": "系统配置中心未激活任何可用的 AI 推理引擎。"}
                
            messages = [{"role": "user", "content": prompt}]
            try:
                # Synchronous wrapper around the HTTP aiohttp pipeline
                response_data = async_to_sync(AIModelService.call_openai_compatible_api)(model_config, messages)
                answer = response_data['choices'][0]['message']['content']
                
                # Sanitize typical MD leakage
                clean_answer = answer.strip()
                if clean_answer.startswith("```json"):
                    clean_answer = clean_answer.replace("```json", "", 1)
                    if clean_answer.endswith("```"):
                        clean_answer = clean_answer[:-3]
                elif clean_answer.startswith("```"):
                    clean_answer = clean_answer.replace("```", "", 1)
                    if clean_answer.endswith("```"):
                        clean_answer = clean_answer[:-3]
                        
                json_result = json.loads(clean_answer.strip())
                return {"status": "SUCCESS", "suggestions": json_result}
                
            except json.JSONDecodeError as jde:
                return {"status": "FAILED", "error": f"大语言模型输出了无效的 JSON 格式: {str(jde)}", "raw_response": locals().get('answer', '')}
            except Exception as e:
                return {"status": "FAILED", "error": f"推理引擎调用异常: {str(e)}"}
                
        except Exception as e:
            return {"status": "FAILED", "error": f"自愈引擎异常: {str(e)}"}
