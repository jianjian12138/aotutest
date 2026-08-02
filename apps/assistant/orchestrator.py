import json
import logging
from apps.requirement_analysis.models import RequirementDocument, GeneratedTestCase
from apps.api_testing.models import ApiProject, ApiTestCase, ApiTestCaseStep
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from django.contrib.auth import get_user_model
from django.db import transaction
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)
User = get_user_model()

# Critic 允许的 HTTP 方法白名单
_ALLOWED_METHODS = {'GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'}

class MultiAgentOrchestrator:
    """
    V2.4 多 Agent 协同测试架构
    The master pipeline tracking three native node deployments:
    Manager: 解析 PRD 拆解大块需求。
    Executor: 将抽象测试记录转化为具体的 ApiTestCase/UiAutomationTestCase 节点体系。
    结构校验器: 纠正格式并将报告提纯投递给终端。
    """
    
    @staticmethod
    def _get_active_model():
        model = AIModelConfig.objects.filter(is_active=True).first()
        if not model:
            raise Exception("No active AI model found within the environment config.")
        return model

    @staticmethod
    def _critic_review(cases_data):
        """
        结构校验器 / structural validator（真实评审，非 Dummy）：
        对 Executor 产出的用例做结构与约束校验，过滤不可执行的节点，
        返回 (valid_cases, rejected, critique_text)。
        """
        if not isinstance(cases_data, list):
            return [], [{'reason': 'Executor 输出不是 JSON 数组'}], '输入格式非法'
        valid, rejected, seen = [], [], set()
        for idx, case in enumerate(cases_data):
            if not isinstance(case, dict):
                rejected.append({'index': idx, 'reason': '用例节点不是对象'})
                continue
            name = case.get('name')
            if not isinstance(name, str) or not name.strip():
                rejected.append({'index': idx, 'reason': '缺少 name'})
                continue
            if name in seen:
                rejected.append({'index': idx, 'name': name, 'reason': '重名用例'})
                continue
            seen.add(name)
            steps = case.get('steps')
            if not isinstance(steps, list) or not steps:
                rejected.append({'index': idx, 'name': name, 'reason': 'steps 为空或非数组'})
                continue
            step_ok = True
            for s in steps:
                if not isinstance(s, dict):
                    step_ok = False
                    break
                if str(s.get('method', '')).upper() not in _ALLOWED_METHODS:
                    step_ok = False
                    break
                if not s.get('url'):
                    step_ok = False
                    break
                assertions = s.get('assertions', [])
                if assertions is not None and not isinstance(assertions, list):
                    step_ok = False
                    break
            if not step_ok:
                rejected.append({'index': idx, 'name': name,
                                'reason': '存在非法 step（method/url/assertions 不合法）'})
                continue
            valid.append(case)
        critique = (
            f'结构校验完成：通过 {len(valid)} / 拒绝 {len(rejected)}。'
            + (' 被拒原因：' + '; '.join(r.get('reason', '') for r in rejected)
               if rejected else ' 全部用例结构合规。')
        )
        return valid, rejected, critique

    @staticmethod
    def compile_api_test_cases(document_id, project_id, user_id):
        """Executor Agent (执行编译器): Extract deep JSON execution tree directly binding to ORM Models"""
        try:
            document = RequirementDocument.objects.get(id=document_id)
            project = ApiProject.objects.get(id=project_id)
            user = User.objects.get(id=user_id)
            
            # 使用 Executor 专属零样本 Prompt 解析长文本推演并直接构造 RESTful Node
            prompt = f'''
你是一个资深的高级自动化测试执行 Agent (Executor Node)。
你的任务是：读取上游 Planner 抛给你的原始长文本商业产品需求文档 (PRD)，并以此直接反向编译出一整套具备**连包调用**和**自动化执行**属性的 HTTP 接口自动验证流。

【接收到的原始需求文档】
{document.extracted_text[:5000]}

指令：
完全无视人类语义沟通方式。不要回复诸如“好的，这是生成的用例”。
你必须输出且仅输出一枚完美的 JSON 数组字符串，内部每一个节点都代表一个完整的 `ApiTestCase` 连级测试，每个用例内部包含数个 `steps` 代表具体的网络动作。
数据结构 Schema Mandatory Format:
[
  {{
    "name": "高优冒烟用例：...",
    "description": "用于覆盖PRD的核心节点说明...",
    "steps": [
      {{
         "name": "预置环境动作",
         "method": "POST",
         "url": "http://127.0.0.1:4545/api/v1/mock/login",
         "body": {{"username": "autotest", "password": "v2_agent"}},
         "assertions": [{{"target": "status_code", "operator": "equals", "value": "200"}}]
      }},
      {{
         "name": "拉取权限表测黑洞注入",
         "method": "GET",
         "url": "http://127.0.0.1:4545/api/v1/engine/permissions",
         "params": {{"inject": "true"}},
         "body": {{}}
      }}
    ]
  }}
]
请尽你所能根据给出的 PRD 逻辑，覆盖更多复杂的操作分支。
'''
            model = MultiAgentOrchestrator._get_active_model()
            messages = [{"role": "user", "content": prompt}]
            response_data = async_to_sync(AIModelService.call_openai_compatible_api)(model, messages)
            content = response_data['choices'][0]['message']['content'].strip()
            
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            cases_data = json.loads(content.strip())
            
            # 结构校验器 / structural validator（真实评审）：过滤非法用例，仅持久化通过校验的节点
            valid_cases, rejected, critique = MultiAgentOrchestrator._critic_review(cases_data)
            created_nodes = []
            with transaction.atomic():
                for case_json in valid_cases:
                    # Compile execution models natively against PostgreSQL/SQLite
                    tc = ApiTestCase.objects.create(
                        project=project,
                        name=case_json.get('name', 'Agentic Compiled Node'),
                        description=case_json.get('description', 'Auto-generated by V2 Multi-Agent Exec.'),
                        created_by=user,
                        status='ready',
                        priority='high'
                    )

                    step_num = 1
                    for step_json in case_json.get('steps', []):
                        ApiTestCaseStep.objects.create(
                            test_case=tc,
                            step_number=step_num,
                            name=step_json.get('name', f'Step {step_num}'),
                            method=step_json.get('method', 'GET').upper(),
                            url=step_json.get('url', '/'),
                            params=step_json.get('params', {}),
                            body=step_json.get('body', {}),
                            assertions=step_json.get('assertions', [])
                        )
                        step_num += 1
                    created_nodes.append(tc.name)

            status_ = "SUCCESS" if created_nodes else "PARTIAL"
            return {
                "status": status_,
                "message": f"Multi-Agent 编译 {len(created_nodes)} 条可执行用例（结构校验拦截 {len(rejected)} 条）。",
                "compiled_cases": created_nodes,
                "critic": critique,
                "rejected": rejected,
            }
            
        except Exception as e:
            logger.error(f"Multi-Agent Core Engine Failure Blocked Compilation Loop: {str(e)}")
            return {"status": "FAILED", "error": str(e)}
