import os
import uuid
import logging
import base64
from datetime import datetime
from typing import List, Dict, Any
from django.conf import settings
from apps.requirement_analysis.models import AIModelConfig, AIModelService
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class VisualAIAnalyzer:
    """
    V3.3 Visual AI Engine:
    Handles screenshot-based semantic comparison using LLM Vision.
    """
    
    def __init__(self, storage_dir: str = None):
        self.storage_dir = storage_dir or os.path.join(settings.MEDIA_ROOT, 'visual_regression')
        os.makedirs(self.storage_dir, exist_ok=True)

    async def compare_screenshots(self, base_image_path: str, current_image_base64: str) -> Dict[str, Any]:
        """
        Calls LLM Vision to compare two screenshots semantically.
        """
        config = await sync_to_async(AIModelConfig.objects.filter(is_active=True).first)()
        if not config:
            return {"status": "ERROR", "reason": "No active AI config"}

        # Read base image
        try:
            with open(base_image_path, "rb") as f:
                base_image_base64 = base64.b64encode(f.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to read base image: {e}")
            return {"status": "ERROR", "reason": "Base image not found"}

        prompt = """
        Compare these two screenshots of a web application.
        Image 1: Baseline (Golden Standard)
        Image 2: Current Build
        
        Identify any visual regressions, layout shifts, or rendering errors.
        Ignore minor pixel noise but report significant UI changes.
        Output ONLY a JSON object: {"diff_found": true|false, "explanation": "string", "risk_level": "Low|Medium|High"}
        """
        
        messages = [
            {"role": "system", "content": "You are a professional UI/UX Quality Assurance expert."},
            {
                "role": "user", 
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base_image_base64}"}},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{current_image_base64}"}}
                ]
            }
        ]
        
        try:
            response = await AIModelService.call_openai_compatible_api(config, messages)
            content = response['choices'][0]['message']['content']
            
            import json, re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(content)
        except Exception as e:
            logger.error(f"Visual AI Analysis failed: {e}")
            return {"status": "ERROR", "reason": str(e)}

    def save_screenshot(self, image_data_base64: str, name: str) -> str:
        """
        Saves a base64 image to the storage directory.
        """
        filename = f"{name}_{uuid.uuid4().hex[:8]}.png"
        file_path = os.path.join(self.storage_dir, filename)
        
        try:
            with open(file_path, "wb") as f:
                f.write(base64.b64decode(image_data_base64))
            return file_path
        except Exception as e:
            logger.error(f"Failed to save screenshot: {e}")
            return ""
