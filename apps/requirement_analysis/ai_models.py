# -*- coding: utf-8 -*-
"""
AI模型配置和服务
"""

from django.db import models
from django.contrib.auth import get_user_model
import json
import httpx
import asyncio
from typing import Dict, Any, List
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class AIModelConfig(models.Model):
    """AI模型配置模型"""
    MODEL_CHOICES = [
        ('deepseek', 'DeepSeek'),
        ('qwen', '通义千问'),
        ('siliconflow', '硅基流动'),
        ('other', '其他'),
    ]
    
    ROLE_CHOICES = [
        ('writer', '测试用例编写专家'),
        ('reviewer', '测试评审专家'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='配置名称')
    model_type = models.CharField(max_length=20, choices=MODEL_CHOICES, verbose_name='模型类型')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='角色')
    api_key = models.CharField(max_length=200, verbose_name='API Key')
    base_url = models.URLField(verbose_name='API Base URL')
    model_name = models.CharField(max_length=100, verbose_name='模型名称')
    max_tokens = models.IntegerField(default=4096, verbose_name='最大Token数')
    temperature = models.FloatField(default=0.7, verbose_name='温度参数')
    top_p = models.FloatField(default=0.9, verbose_name='Top P参数')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'ai_model_config'
        verbose_name = 'AI模型配置'
        verbose_name_plural = 'AI模型配置'
        unique_together = ('model_type', 'role')  # 每种角色只能有一个活跃配置
    
    def __str__(self):
        return f"{self.get_model_type_display()} - {self.get_role_display()}"


class PromptConfig(models.Model):
    """提示词配置模型"""
    PROMPT_CHOICES = [
        ('writer', '用例编写提示词'),
        ('reviewer', '用例评审提示词'),
    ]
    
    name = models.CharField(max_length=100, verbose_name='配置名称')
    prompt_type = models.CharField(max_length=20, choices=PROMPT_CHOICES, verbose_name='提示词类型')
    content = models.TextField(verbose_name='提示词内容')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        db_table = 'prompt_config'
        verbose_name = '提示词配置'
        verbose_name_plural = '提示词配置'
        unique_together = ('prompt_type', 'is_active')  # 每种类型只能有一个活跃提示词
    
    def __str__(self):
        return f"{self.get_prompt_type_display()} - {self.name}"


class TestCaseGenerationTask(models.Model):
    """测试用例生成任务模型"""
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('generating', '生成中'),
        ('reviewing', '评审中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    task_id = models.CharField(max_length=50, unique=True, verbose_name='任务ID')
    title = models.CharField(max_length=200, verbose_name='任务标题')
    requirement_text = models.TextField(verbose_name='需求描述')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='状态')
    progress = models.IntegerField(default=0, verbose_name='进度百分比')
    
    # 配置参数
    writer_model_config = models.ForeignKey(
        AIModelConfig, on_delete=models.SET_NULL, null=True, 
        related_name='writer_tasks', verbose_name='编写模型配置'
    )
    reviewer_model_config = models.ForeignKey(
        AIModelConfig, on_delete=models.SET_NULL, null=True,
        related_name='reviewer_tasks', verbose_name='评审模型配置'
    )
    writer_prompt_config = models.ForeignKey(
        PromptConfig, on_delete=models.SET_NULL, null=True,
        related_name='writer_tasks', verbose_name='编写提示词配置'
    )
    reviewer_prompt_config = models.ForeignKey(
        PromptConfig, on_delete=models.SET_NULL, null=True,
        related_name='reviewer_tasks', verbose_name='评审提示词配置'
    )
    
    # 生成结果
    generated_test_cases = models.TextField(blank=True, verbose_name='生成的测试用例')
    review_feedback = models.TextField(blank=True, verbose_name='评审反馈')
    final_test_cases = models.TextField(blank=True, verbose_name='最终测试用例')
    
    # 元数据
    generation_log = models.TextField(blank=True, verbose_name='生成日志')
    error_message = models.TextField(blank=True, verbose_name='错误信息')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='创建者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name='完成时间')
    
    class Meta:
        db_table = 'testcase_generation_task'
        verbose_name = '测试用例生成任务'
        verbose_name_plural = '测试用例生成任务'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"


class AIModelService:
    """AI模型服务类"""
    
    @staticmethod
    async def call_openai_compatible_api(config: AIModelConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用OpenAI兼容格式的API"""
        headers = {
            'Authorization': f'Bearer {config.api_key}',
            'Content-Type': 'application/json'
        }
        
        data = {
            'model': config.model_name,
            'messages': messages,
            'max_tokens': config.max_tokens,
            'temperature': config.temperature,
            'top_p': config.top_p,
            'stream': False
        }
        
        # 确保base_url不以/结尾
        base_url = config.base_url.rstrip('/')
        # 如果用户没有输入完整的v1/chat/completions路径，尝试智能补全
        if not base_url.endswith('/chat/completions'):
            if base_url.endswith('/v1'):
                url = f"{base_url}/chat/completions"
            else:
                # 默认假设是根路径，尝试添加 v1/chat/completions
                # 但对于某些API（如DeepSeek），base_url可能已经是 https://api.deepseek.com
                url = f"{base_url}/v1/chat/completions"
        else:
            url = base_url
            
        try:
            # Increase timeout to 120s for long generation tasks
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json=data
                )
                
                if response.status_code != 200:
                    error_detail = response.text
                    logger.error(f"API调用返回错误: Status={response.status_code}, Body={error_detail}")
                    
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            provider_name = config.get_model_type_display()
            error_msg = f"{provider_name} API返回错误 {e.response.status_code}: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.TimeoutException as e:
            provider_name = config.get_model_type_display()
            logger.error(f"{provider_name} API请求超时: {repr(e)}")
            raise Exception(f"{provider_name} API请求超时，请稍后再试或检查网络连接")
        except Exception as e:
            provider_name = config.get_model_type_display()
            # Use repr(e) to capture the full exception type and message, especially if str(e) is empty
            logger.error(f"{provider_name} API调用失败: {repr(e)}")
            raise Exception(f"{provider_name} API调用失败: {str(e) or repr(e)}")
    
    @staticmethod
    async def call_deepseek_api(config: AIModelConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用DeepSeek API (兼容OpenAI格式)"""
        return await AIModelService.call_openai_compatible_api(config, messages)
    
    @staticmethod
    async def call_qwen_api(config: AIModelConfig, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """调用千问API (兼容OpenAI格式)"""
        return await AIModelService.call_openai_compatible_api(config, messages)
    
    @staticmethod
    async def generate_test_cases(task: TestCaseGenerationTask) -> str:
        """生成测试用例"""
        writer_prompt = task.writer_prompt_config.content
        user_message = f"请根据以下需求生成测试用例：\n\n{task.requirement_text}"
        
        messages = [
            {"role": "system", "content": writer_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 所有支持的模型都使用兼容OpenAI的接口
        response = await AIModelService.call_openai_compatible_api(task.writer_model_config, messages)
        
        return response['choices'][0]['message']['content']
    
    @staticmethod
    async def review_test_cases(task: TestCaseGenerationTask, test_cases: str) -> str:
        """评审测试用例"""
        reviewer_prompt = task.reviewer_prompt_config.content
        user_message = f"请评审以下测试用例：\n\n{test_cases}"
        
        messages = [
            {"role": "system", "content": reviewer_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # 所有支持的模型都使用兼容OpenAI的接口
        response = await AIModelService.call_openai_compatible_api(task.reviewer_model_config, messages)
        
        return response['choices'][0]['message']['content']