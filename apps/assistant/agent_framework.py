from abc import ABC, abstractmethod
import json
import logging
import asyncio
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class BaseSkill(ABC):
    """
    Abstract Base Class for an Agent Skill.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the skill to be exposed to the LLM (e.g. 'execute_api_request')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what the skill does, helping the LLM decide when to use it."""
        pass

    @abstractmethod
    async def run(self, **kwargs) -> Any:
        """The core execution logic of the skill."""
        pass


class BaseAgent:
    """
    The Base Agent that holds a set of skills and a specific persona.
    """
    def __init__(self, name: str, system_prompt: str, llm_config_id: int = None):
        self.name = name
        self.system_prompt = system_prompt
        self.llm_config_id = llm_config_id
        self.skills: Dict[str, BaseSkill] = {}
        logger.info(f"Agent '{self.name}' initialized.")

    def register_skill(self, skill: BaseSkill):
        self.skills[skill.name] = skill
        logger.info(f"Registered skill '{skill.name}' to Agent '{self.name}'.")

    async def execute(self, prompt: str, project=None, user=None) -> Dict[str, Any]:
        """
        Executes a prompt by evaluating skills and running the necessary tools.
        """
        logger.info(f"Agent '{self.name}' processing prompt: {prompt}")
        
        # 1. Prepare available skills metadata for the LLM
        skills_info = []
        for name, skill in self.skills.items():
            skills_info.append(f"- Name: {name}, Description: {skill.description}")
        
        system_instruction = f"{self.system_prompt}\nAvailable Skills:\n" + "\n".join(skills_info)
        system_instruction += "\nBased on the user's prompt, select the skill to execute and extract the necessary arguments. Respond with JSON strictly formatted as: {\"skill\": \"skill_name\", \"kwargs\": {\"key\": \"value\"}}"
        
        # 2. Integrate Real LLM (AIModel)
        from asgiref.sync import sync_to_async
        from apps.requirement_analysis.models import AIModelConfig
        import json
        
        selected_skill = None
        skill_kwargs = {}
        llm_response_text = ""
        
        try:
            dify_config = None
            if self.llm_config_id:
                # Use specific bound LLM config
                dify_config = await sync_to_async(AIModelConfig.objects.get)(id=self.llm_config_id)
            else:
                # Fallback to default active LLM config
                dify_config = await sync_to_async(AIModelConfig.objects.filter(is_active=True).first)()
                
            if dify_config and hasattr(dify_config, 'base_url') and dify_config.api_key:
                # Use OpenAI compatible Real LLM
                from apps.requirement_analysis.models import AIModelService
                
                messages = [
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt}
                ]
                
                resp_json = await AIModelService.call_openai_compatible_api(dify_config, messages)
                
                if 'choices' in resp_json and len(resp_json['choices']) > 0:
                    llm_response_text = resp_json['choices'][0]['message'].get('content', '')
                else:
                    llm_response_text = json.dumps(resp_json)
                    
                # Extract JSON from LLM answer
                import re
                json_match = re.search(r'\{.*\}', llm_response_text.replace('\n', ''), re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    selected_skill = parsed.get("skill")
                    skill_kwargs = parsed.get("kwargs", {})
            else:
                # Fallback purely to mock mapping logic
                if "click" in prompt.lower() or "tap" in prompt.lower():
                    llm_response_text = json.dumps({"skill": "click_element", "kwargs": {"selector": "#submit-btn"}})
                elif "type" in prompt.lower() or "input" in prompt.lower():
                    llm_response_text = json.dumps({"skill": "type_text", "kwargs": {"selector": "#username", "text": "admin"}})
                else:
                    raise Exception("No active DifyConfig found and no mock mapping applied.")
        except Exception as e:
            # Fallback to simulated mapping if Dify is not configured or fails
            logger.warning(f"LLM API Call failed ({e}). Falling back to local keyword routing.")
            llm_response_text = f"Simulated Fallback. Reason: {e}"
            prompt_lower = prompt.lower()
            for name in self.skills.keys():
                if "api" in prompt_lower and "api" in name.lower():
                    selected_skill, skill_kwargs = name, {"method": "GET", "url": "http://api.mock.test/v1/health"}
                elif ("web" in prompt_lower or "ui" in prompt_lower) and "web" in name.lower():
                    selected_skill, skill_kwargs = name, {"action": "navigate_and_test", "target": prompt}
                elif ("app" in prompt_lower or "mobile" in prompt_lower) and "app" in name.lower():
                    selected_skill, skill_kwargs = name, {"device": "android", "action": "test_flow"}
                elif ("generate" in prompt_lower or "用例" in prompt_lower) and "case" in name.lower():
                    selected_skill, skill_kwargs = name, {"requirement": prompt, "project": project, "user": user}

        executed_skills = []
        final_answer = "Default Response"
        
        if selected_skill and selected_skill in self.skills:
            skill_obj = self.skills[selected_skill]
            logger.info(f"Agent '{self.name}' invoking selected skill: {selected_skill} with args {skill_kwargs}")
            try:
                # Inject contextual context that might be required by specific skills
                if 'project' not in skill_kwargs and project:
                    skill_kwargs['project'] = project
                if 'user' not in skill_kwargs and user:
                    skill_kwargs['user'] = user

                res = await skill_obj.run(**skill_kwargs)
                executed_skills.append({
                    "skill": selected_skill,
                    "status": "success",
                    "output": res
                })
                final_answer = f"Agent successfully executed {selected_skill}. Execution results collected."
            except Exception as e:
                executed_skills.append({
                    "skill": selected_skill,
                    "status": "error",
                    "output": str(e)
                })
                final_answer = f"Error during execution of {selected_skill}: {e}"
        else:
             final_answer = f"Agent '{self.name}' could not map the prompt to any registered skills. Raw LLM response: {llm_response_text}"
                
        return {
            "prompt": prompt,
            "system_instruction": system_instruction,
            "raw_llm_response": llm_response_text,
            "selected_skill": selected_skill,
            "skill_kwargs": skill_kwargs,
            "executed_skills": executed_skills,
            "final_answer": final_answer
        }

    async def execute_stream(self, prompt: str, project=None, user=None):
        """
        Stream the execution progress using yield statements.
        Implements a Multi-Agent Supervisor Pipeline (Coordinator -> Workers).
        """
        logger.info(f"Agent '{self.name}' processing stream prompt...")
        
        # ========================================
        # Phase 1: Supervisor Coordination
        # ========================================
        yield {"type": "agent_switch", "agent_role": "交响乐指挥家 (Supervisor)"}
        yield {"type": "metadata", "status": "planning", "message": f"[{self.name}] 正在拆解意图，分配专属领域专家..."}
        
        skills_info = []
        for name, skill in self.skills.items():
            skills_info.append(f"- Name: {name}, Description: {skill.description}")
        
        from asgiref.sync import sync_to_async
        from apps.requirement_analysis.models import AIModelConfig, AIModelService
        import json, re
        
        dify_config = None
        if self.llm_config_id:
            dify_config = await sync_to_async(AIModelConfig.objects.get)(id=self.llm_config_id)
        else:
            dify_config = await sync_to_async(AIModelConfig.objects.filter(is_active=True).first)()
            
        if not dify_config or not dify_config.api_key:
            yield {"type": "error", "message": "No Active LLM Config Found"}
            return
            
        # Call Supervisor LLM
        supervisor_sys = (
            "You are a Task Supervisor. The user will provide a testing/QA prompt.\n"
            "Decide the exact multi-agent workflow sequence needed.\n"
            "Roles available: [\"需求分析专家\", \"测试点提取专家\", \"架构评审专家\", \"用例编写专家\", \"通用执行专家\"]\n"
            "Return ONLY a JSON array of roles in execution order. Example: [\"需求分析专家\", \"用例编写专家\"]"
        )
        try:
            sup_resp = await AIModelService.call_openai_compatible_api(dify_config, [
                {"role": "system", "content": supervisor_sys},
                {"role": "user", "content": prompt}
            ])
            sup_text = sup_resp['choices'][0]['message'].get('content', '["通用执行专家"]')
            match = re.search(r'\[.*?\]', sup_text.replace('\n', ''))
            experts = json.loads(match.group(0)) if match else ["通用执行专家"]
        except Exception as e:
            experts = ["通用执行专家"]
            
        yield {"type": "metadata", "status": "planning", "message": f"任务调度规划完毕，执行管线：{' -> '.join(experts)}"}
        
        # ========================================
        # Phase 2: Worker Agents Execution Loop
        # ========================================
        global_context = []
        
        for idx, expert in enumerate(experts):
            yield {"type": "agent_switch", "agent_role": expert}
            yield {"type": "metadata", "status": "thinking", "message": f"{expert} 开始接管并处理环节 {idx+1}/{len(experts)}..."}
            
            # Construct Worker Instruction
            context_str = "\n".join(global_context) if global_context else "No prior context."
            sys_instruct = (
                f"{self.system_prompt}\n\n"
                f"You are now acting specifically as: {expert}. Focus only on your domain.\n"
                f"Prior Pipeline Output:\n{context_str}\n\n"
                f"Available Skills:\n" + "\n".join(skills_info) + "\n"
                "To trigger a tool, output JSON containing {\"skill\": \"skill_name\", \"kwargs\": {}}. Otherwise output standard text."
            )
            
            messages = [
                {"role": "system", "content": sys_instruct},
                {"role": "user", "content": prompt}
            ]
            
            llm_response_text = ""
            try:
                async for chunk in AIModelService.call_openai_compatible_api_stream(dify_config, messages):
                    llm_response_text += chunk
                    yield {"type": "text_chunk", "content": chunk}
            except Exception as e:
                yield {"type": "error", "message": f"{expert} failed: {e}"}
                continue
                
            global_context.append(f"[{expert} Output]: {llm_response_text}")
            
            # Extract JSON from Worker's answer to see if they called a skill
            json_match = re.search(r'\{.*\}', llm_response_text.replace('\n', ''), re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(0))
                    selected_skill = parsed.get("skill")
                    skill_kwargs = parsed.get("kwargs", {})
                    
                    if selected_skill and selected_skill in self.skills:
                        yield {"type": "metadata", "status": "executing", "message": f"{expert} 调用技能: {selected_skill}..."}
                        skill_obj = self.skills[selected_skill]
                        
                        if 'project' not in skill_kwargs and project:
                            skill_kwargs['project'] = project
                        if 'user' not in skill_kwargs and user:
                            skill_kwargs['user'] = user

                        res = await skill_obj.run(**skill_kwargs)
                        yield {"type": "metadata", "status": "success", "message": f"技能 {selected_skill} 执行完毕。"}
                        yield {"type": "skill_result", "skill": selected_skill, "result": res}
                        
                        global_context.append(f"[{expert} Skill {selected_skill} Result]: {res}")
                except Exception as e:
                    yield {"type": "error", "message": f"技能尝试失败: {str(e)}"}
                    
        yield {"type": "agent_switch", "agent_role": "交响乐指挥家 (Supervisor)"}
        yield {"type": "metadata", "status": "success", "message": "全流水线处理完毕。"}
