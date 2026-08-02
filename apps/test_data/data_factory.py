import logging
from typing import Dict, Any
import uuid

logger = logging.getLogger(__name__)

class BusinessDataFactory:
    """
    Intelligent Test Data Engine.
    Generates complex, business-constrained mock data for automation tests.
    """
    
    @classmethod
    def generate_vip_user(cls, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Generates a mocked VIP user with history and tags.
        """
        user_id = str(uuid.uuid4())
        has_orders = requirements.get("has_active_orders", False) if requirements else False
        
        user_profile = {
            "user_id": user_id,
            "username": f"vip_tester_{user_id[:8]}",
            "tier": "Gold",
            "balance": 1500.00,
            "risk_tags": ["low_risk", "verified_identity"],
            "orders": []
        }
        
        if has_orders:
            user_profile["orders"].append({
                "order_id": f"ORD-{user_id[:5]}",
                "status": "pending_payment",
                "amount": 299.99
            })
            
        logger.info(f"Generated VIP User: {user_profile['username']}")
        return user_profile

    @classmethod
    async def provision_data_by_intent(cls, intent: str) -> Dict[str, Any]:
        """
        AI-driven entrypoint. Parses natural language intent to provision data.
        """
        # In a real scenario, this uses an LLM to map "Give me a VIP user with orders" 
        # to the cls.generate_vip_user kwargs. Here we mock the router.
        
        intent_lower = intent.lower()
        if "vip" in intent_lower:
            reqs = {"has_active_orders": "order" in intent_lower or "订单" in intent_lower}
            record = cls.generate_vip_user(requirements=reqs)
            return {
                "status": "success",
                "provisioned_type": "VIP User",
                "records_created": 1,
                "data": record
            }
        elif "异常" in intent_lower or "invalid" in intent_lower:
            return {
                "status": "success",
                "provisioned_type": "Invalid Data",
                "records_created": 3,
                "data": [
                    {"id": "ERR-1", "value": -99, "reason": "negative balance"},
                    {"id": "ERR-2", "value": None, "reason": "null reference"},
                    {"id": "ERR-3", "value": "A"*5000, "reason": "buffer overflow"}
                ]
            }
        
        # Generic fallback
        return {
            "status": "success",
            "provisioned_type": "Generic Test Data",
            "records_created": 3,
            "data": [{"id": 1, "mock": "A"}, {"id": 2, "mock": "B"}, {"id": 3, "mock": "C"}]
        }
