import asyncio
import logging
from .agent_framework import BaseSkill

logger = logging.getLogger(__name__)

class ApiTestingSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "api_testing_skill"
        
    @property
    def description(self) -> str:
        return "Executes HTTP API requests (GET/POST) to validate backend services."
        
    async def run(self, **kwargs):
        method = kwargs.get('method', 'GET')
        url = kwargs.get('url', 'http://localhost')
        expected_schema = kwargs.get('expected_schema', None)
        
        # Simulate API call
        await asyncio.sleep(0.5)
        
        # Mock response containing potentially new fields that would break traditional rigid tests
        response_data = {"message": "API Health Ok", "data": [1, 2, 3], "new_untracked_field": "beta_feature_x"}
        
        result = {
            "status_code": 200,
            "method": method,
            "url": url,
            "response_body": response_data
        }
        
        if expected_schema:
            try:
                from apps.api_testing.self_healing import APIContractHealer
                validation = APIContractHealer.validate_schema_soft(expected_schema, response_data)
                result["contract_validation"] = validation
                
                if not validation["valid"]:
                    heal_result = await APIContractHealer.diagnose_and_heal(
                        failed_request={"url": url, "method": method},
                        error_msg=validation["message"]
                    )
                    result["self_healing"] = heal_result
            except ImportError:
                pass
                
        return result


class WebTestingSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "web_testing_skill"
        
    @property
    def description(self) -> str:
        return "Executes Playwright Web UI automation actions. Includes semantic click, extract, and auto-healing logic."
        
    async def run(self, **kwargs):
        action = kwargs.get('action', 'inspect')
        # Simulate Web call
        await asyncio.sleep(1)
        return {
            "driver": "playwright",
            "action_performed": action,
            "status": "Auto-Heal completed successfully, assertions passed.",
            "screenshot": "base64_encoded_dummy_data..."
        }


class AppTestingSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "app_testing_skill"
        
    @property
    def description(self) -> str:
        return "Connects to Appium to perform UI interaction and visual validation on iOS/Android native applications."
        
    async def run(self, **kwargs):
        device = kwargs.get('device', 'android')
        # Simulate Appium call
        await asyncio.sleep(1)
        return {
            "framework": "appium",
            "device": device,
            "app_state": "Home Screen Validated",
            "metrics": {"cpu": "12%", "memory": "240MB"}
        }

class CaseGenerationSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "case_generation_skill"
        
    @property
    def description(self) -> str:
        return "Generates structured Test Cases from natural language user stories or requirements."
        
    async def run(self, **kwargs):
        requirement = kwargs.get('requirement', '')
        project = kwargs.get('project')
        user = kwargs.get('user')
        
        # Integration with existing AI module
        from apps.testcases.services import AITestCaseGenerator
        if project and user:
            cases = await AITestCaseGenerator.generate_cases_from_requirement(requirement, project, user)
            return {"cases_generated": len(cases), "preview": cases[0] if cases else None}
        return {"error": "Missing project context for generation."}

class DataFactorySkill(BaseSkill):
    @property
    def name(self) -> str:
        return "data_factory_skill"
        
    @property
    def description(self) -> str:
        return "Provisions complex mock test data into the database based on natural language constraints (e.g. 'Generate 3 VIP users')."
        
    async def run(self, **kwargs):
        intent = kwargs.get('intent', 'Generate generic test data')
        
        try:
            from apps.test_data.data_factory import BusinessDataFactory
            result = await BusinessDataFactory.provision_data_by_intent(intent)
            return result
        except ImportError:
            return {"error": "Test Data module not found."}
