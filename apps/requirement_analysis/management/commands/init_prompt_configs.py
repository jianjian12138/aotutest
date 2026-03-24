from django.core.management.base import BaseCommand
from apps.core_platform.models import User
from apps.requirement_analysis.models import PromptConfig

class Command(BaseCommand):
    help = 'Initialize prompt configurations for test case writing and reviewing'

    def handle(self, *args, **options):
        # 获取默认用户（通常是admin）
        user = User.objects.filter(is_superuser=True).first()
        if not user:
            user = User.objects.order_by('-date_joined').first()
            if not user:
                self.stdout.write(self.style.ERROR('No users found. Please create a user first.'))
                return

        self.stdout.write(f'Initializing prompt configurations for user: {user.username}')

        # 用例编写提示词
        writer_prompts = [
            {
                'name': '基础用例编写提示词',
                'content': '''你是一位专业的测试用例编写专家，请根据以下需求描述生成详细的测试用例。

要求：
1. 覆盖所有功能点和边界情况
2. 测试用例格式清晰，包含：用例编号、用例标题、优先级、前置条件、测试步骤、预期结果
3. 用例设计符合等价类划分、边界值分析等测试方法
4. 确保用例可执行、可验证
5. 考虑异常情况和错误处理

需求描述：{requirement_text}''',
                'is_active': True
            },
            {
                'name': '详细场景用例编写提示词',
                'content': '''作为高级测试工程师，请为以下需求生成全面的测试用例集，重点关注业务场景的完整性。

生成规则：
1. 首先分析需求，识别核心业务流程和关键功能点
2. 为每个核心流程生成至少3个不同场景的测试用例
3. 包含正常场景、异常场景和边界场景
4. 用例需包含：场景描述、测试步骤、预期结果、风险等级
5. 确保测试覆盖所有业务规则和约束条件

需求描述：{requirement_text}''',
                'is_active': False
            },
            {
                'name': '敏捷用例编写提示词',
                'content': '''你是敏捷测试团队的成员，请根据以下用户故事生成简洁高效的测试用例。

生成要求：
1. 采用Given-When-Then格式编写用例
2. 重点关注用户价值和业务结果
3. 优先覆盖核心功能和高频场景
4. 每个用户故事至少生成5个测试用例
5. 用例应易于理解和执行，适合快速迭代环境

用户故事：{requirement_text}''',
                'is_active': False
            }
        ]

        # 用例评审提示词
        reviewer_prompts = [
            {
                'name': '全面评审提示词',
                'content': '''你是一位资深测试评审专家，请对以下测试用例进行全面评审。

评审要点：
1. 用例完整性：是否覆盖所有需求点和边界情况
2. 用例正确性：测试步骤和预期结果是否正确
3. 用例可执行性：是否具备可操作性和可验证性
4. 用例覆盖度：是否包含正常、异常和边界场景
5. 用例质量：是否符合测试设计原则
6. 用例清晰度：描述是否清晰易懂，格式是否规范

请提供详细的评审意见，包括优点、不足和改进建议。

测试用例：{test_cases}''',
                'is_active': True
            },
            {
                'name': '风险导向评审提示词',
                'content': '''作为风险分析专家，请从风险角度评审以下测试用例。

评审重点：
1. 识别高风险功能点是否有充分的测试覆盖
2. 检查是否遗漏了关键的异常场景
3. 评估测试用例对业务价值的保障程度
4. 分析测试用例的优先级分配是否合理
5. 检查是否存在冗余或不必要的测试用例

请提供风险评估报告，包括风险等级、影响范围和改进建议。

测试用例：{test_cases}''',
                'is_active': False
            },
            {
                'name': '效率优化评审提示词',
                'content': '''你是测试效率优化专家，请评审以下测试用例并提出优化建议。

评审要点：
1. 测试用例的执行效率：是否存在可优化的步骤
2. 测试用例的可维护性：是否易于更新和管理
3. 测试用例的复用性：是否可以通过参数化等方式复用
4. 测试数据的设计：是否合理且易于准备
5. 测试用例的组织：是否便于执行和报告

请提供具体的优化建议，包括改进方案和预期效果。

测试用例：{test_cases}''',
                'is_active': False
            }
        ]

        try:
            # 创建用例编写提示词
            self.stdout.write('\nCreating test case writing prompts:')
            self.stdout.write('-' * 50)
            for i, prompt_data in enumerate(writer_prompts):
                prompt, created = PromptConfig.objects.update_or_create(
                    name=prompt_data['name'],
                    prompt_type='writer',
                    defaults={
                        'content': prompt_data['content'],
                        'is_active': prompt_data['is_active'],
                        'created_by': user
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created: {prompt.name}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Updated: {prompt.name}'))

            # 创建用例评审提示词
            self.stdout.write('\nCreating test case reviewing prompts:')
            self.stdout.write('-' * 50)
            for i, prompt_data in enumerate(reviewer_prompts):
                prompt, created = PromptConfig.objects.update_or_create(
                    name=prompt_data['name'],
                    prompt_type='reviewer',
                    defaults={
                        'content': prompt_data['content'],
                        'is_active': prompt_data['is_active'],
                        'created_by': user
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created: {prompt.name}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Updated: {prompt.name}'))

            self.stdout.write('\n' + self.style.SUCCESS('Successfully initialized prompt configurations'))
            self.stdout.write(f'Total created/updated: {len(writer_prompts) + len(reviewer_prompts)} prompts')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error initializing prompt configurations: {e}'))