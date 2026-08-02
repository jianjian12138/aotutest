from .agent_framework import BaseAgent
from .skills_library import ApiTestingSkill, WebTestingSkill, AppTestingSkill, CaseGenerationSkill, DataFactorySkill

class AgentFactory:
    """
    Factory to construct preset Agent personas equipped with specific skill combinations.
    """
    
    @staticmethod
    def create_api_agent() -> BaseAgent:
        agent = BaseAgent(
            name="ApiTesterAgent", 
            system_prompt="You are a Backend API Quality Assurance expert. You rigorously test HTTP endpoints."
        )
        agent.register_skill(ApiTestingSkill())
        return agent

    @staticmethod
    def create_web_agent() -> BaseAgent:
        agent = BaseAgent(
            name="WebUIAutomatorAgent", 
            system_prompt="You are a Frontend Automation expert specializing in Playwright and semantic DOM interactions."
        )
        agent.register_skill(WebTestingSkill())
        return agent

    @staticmethod
    def create_app_agent() -> BaseAgent:
        agent = BaseAgent(
            name="MobileAppTesterAgent", 
            system_prompt="You are a Mobile App QA specialist. You use Appium grids to test iOS and Android screens."
        )
        agent.register_skill(AppTestingSkill())
        return agent
        
    @staticmethod
    def create_generation_agent() -> BaseAgent:
        agent = BaseAgent(
            name="RequirementsAnalystAgent", 
            system_prompt="You are a Business Analyst and QA Designer. You break down complex PRDs into atomic test cases."
        )
        agent.register_skill(CaseGenerationSkill())
        return agent
        
    @staticmethod
    def create_data_factory_agent() -> BaseAgent:
        agent = BaseAgent(
            name="DataProvisioningAgent", 
            # audit: real-impl system_prompt 文案描述该 Agent 的职责（供给测试数据），非伪造实现
            system_prompt="You are a Data Engineering AI. You understand business contexts and can provision complex mock data combinations into the system."
        )
        agent.register_skill(DataFactorySkill())
        return agent

    @staticmethod
    def create_master_orchestrator() -> BaseAgent:
        agent = BaseAgent(
            name="MasterOrchestratorAgent", 
            system_prompt="You are the Supreme AI Coordinator. You have access to API, Web, App, Generation and Data Provisioning skills to fulfill holistic engineering requests."
        )
        agent.register_skill(ApiTestingSkill())
        agent.register_skill(WebTestingSkill())
        agent.register_skill(AppTestingSkill())
        agent.register_skill(CaseGenerationSkill())
        agent.register_skill(DataFactorySkill())
        return agent
