from django.core.management.base import BaseCommand
from apps.core_platform.models import User
from apps.requirement_analysis.models import AIModelConfig

class Command(BaseCommand):
    help = 'Initialize DeepSeek model configuration for all roles'

    def handle(self, *args, **options):
        # 获取默认用户（通常是admin）
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.order_by('-date_joined').first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
                return

        self.stdout.write(f'Initializing DeepSeek model configuration for user: {user.username}')

        # DeepSeek 模型配置参数
        # 安全要求：API Key 一律从环境变量读取，严禁硬编码入库/入仓
        import os
        api_key = os.environ.get('DEEPSEEK_API_KEY', '')
        if not api_key:
            self.stdout.write(self.style.ERROR(
                '未检测到环境变量 DEEPSEEK_API_KEY，已中止初始化。'
                '请先执行: export DEEPSEEK_API_KEY=sk-xxx （或在 .env 中配置）'
            ))
            return

        deepseek_config = {
            'model_type': 'deepseek',
            'api_key': api_key,
            'base_url': 'https://api.deepseek.com',
            'model_name': 'deepseek-chat',
            'max_tokens': 4096,
            'temperature': 0.7,
            'top_p': 0.9,
            'is_active': True,
            'created_by': user
        }

        # 需要配置的角色列表
        roles = [
            {'name': 'DeepSeek - 测试用例编写专家', 'role': 'writer'},
            {'name': 'DeepSeek - 测试评审专家', 'role': 'reviewer'},
            {'name': 'DeepSeek - Browser Use 文本模式', 'role': 'browser_use_text'}
        ]

        try:
            for role_config in roles:
                # 禁用同角色下的其他配置
                AIModelConfig.objects.filter(role=role_config['role']).update(is_active=False)
                
                # 创建或更新DeepSeek配置
                config, created = AIModelConfig.objects.update_or_create(
                    name=role_config['name'],
                    role=role_config['role'],
                    defaults={
                        **deepseek_config
                    }
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created DeepSeek config for role: {role_config["role"]}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Updated DeepSeek config for role: {role_config["role"]}'))

            self.stdout.write(self.style.SUCCESS('Successfully initialized DeepSeek model configuration for all roles'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing DeepSeek config: {e}'))