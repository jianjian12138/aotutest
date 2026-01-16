from django.core.management.base import BaseCommand
from apps.users.models import User
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
        deepseek_config = {
            'model_type': 'deepseek',
            'api_key': 'sk-5e83993f48454833ab32eacd157df42e',
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