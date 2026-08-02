import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class APIContractHealer:
    """
    Intelligent failure retry logic & Schema Validation.
    If the API structure changes (e.g. non-breaking fields added),
    it avoids failing the test natively.
    """
    @classmethod
    def validate_schema_soft(cls, expected_schema: Dict[str, Any], actual_response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Soft JSON schema validation comparing dictionary keys natively. 
        Returns {"valid": bool, "missing_keys": list, "extra_keys": list}
        """
        expected_keys = set(expected_schema.keys())
        actual_keys = set(actual_response.keys())
        
        missing_keys = list(expected_keys - actual_keys)
        extra_keys = list(actual_keys - expected_keys)
        
        # In a soft validation, extra keys do not break the API contract.
        is_valid = len(missing_keys) == 0
        
        return {
            "valid": is_valid,
            "missing_keys": missing_keys,
            "extra_keys": extra_keys,
            "message": "Validation Passed" if is_valid else f"Contract Breached. Missing required keys: {missing_keys}"
        }
    
    @classmethod
    async def diagnose_and_heal(cls, failed_request: Dict, error_msg: str) -> Dict[str, Any]:
        """
        Simulates an LLM call to auto-diagnose an API failure and suggest retries.
        """
        logger.info(f"Initiating self-healing for: {failed_request.get('url')}")
        
        healed_request = failed_request.copy()
        healed_action = "None"
        
        if "timeout" in error_msg.lower():
            healed_action = "Increased timeout to 30s and injected fallback retry loop"
            healed_request['timeout'] = 30
        elif "401" in error_msg or "authorization" in error_msg.lower():
            healed_action = "Refetched dynamic Bearer token from auth service"
            healed_request['headers'] = {"Authorization": "Bearer HEALED_TOKEN_XYZ"}
        elif "missing required keys" in error_msg.lower():
            healed_action = "LLM analyzed new endpoints. Detected v2 migration. Rewrote assertion schema."
            # Mocks the LLM noticing a version upgrade and fixing the test data expectations
            healed_request['url'] = healed_request.get('url', '').replace('/v1/', '/v2/')
            
        return {
            "healed": True if healed_action != "None" else False,
            "action_taken": healed_action,
            "suggested_request": healed_request
        }
