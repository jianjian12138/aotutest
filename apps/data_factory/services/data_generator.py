import logging
from faker import Faker
from datetime import datetime

logger = logging.getLogger(__name__)

class TestDataGeneratorService:
    def __init__(self, locale='zh_CN'):
        self.fake = Faker(locale)
        self.en_fake = Faker('en_US')
        
        # Mapping from frontend types to Faker methods or lambdas
        self.TYPE_MAPPING = {
            # Personal
            'gender': lambda: self.fake.random_element(elements=('男', '女')),
            'name': lambda: self.fake.name(),
            'en_name': lambda: self.en_fake.name(),
            'username': lambda: self.fake.user_name(),
            'id_card': lambda: self.fake.ssn(),
            'passport': lambda: self.fake.ssn(), # Simplified
            'job': lambda: self.fake.job(),
            'bio': lambda: self.fake.text(),
            'birthday': lambda: self.fake.date_of_birth().strftime('%Y-%m-%d'),
            
            # Contact
            'phone': lambda: self.fake.phone_number(),
            'phone_number': lambda: self.fake.phone_number(),
            'tel': lambda: self.fake.phone_number(),
            'email': lambda: self.fake.email(),
            'qq': lambda: self.fake.random_int(min=10000, max=999999999),
            'address': lambda: self.fake.address(),
            'zipcode': lambda: self.fake.postcode(),
            'country': lambda: self.fake.country(),
            'province': lambda: self.fake.province(),
            'city': lambda: self.fake.city(),
            
            # Financial
            'bank_card': lambda: self.fake.credit_card_number(),
            'credit_card': lambda: self.fake.credit_card_number(),
            'credit_card_number': lambda: self.fake.credit_card_number(),
            'cvv': lambda: self.fake.credit_card_security_code(),
            'iban': lambda: self.fake.iban(),
            'price': lambda: self.fake.random_int(min=1, max=10000),
            'currency': lambda: self.fake.currency_code(),
            'currency_code': lambda: self.fake.currency_code(),
            
            # DateTime
            'current_date': lambda: datetime.now().strftime('%Y-%m-%d'),
            'current_time': lambda: datetime.now().strftime('%H:%M:%S'),
            'current_datetime': lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'random_date': lambda: self.fake.date(),
            'random_time': lambda: self.fake.time(),
            'timestamp': lambda: self.fake.unix_time(),
            
            # Other
            'text': lambda: self.fake.text(),
            'random_int': lambda: self.fake.random_int(),
            'uuid': lambda: self.fake.uuid4(),
            'ipv4': lambda: self.fake.ipv4(),
            'url': lambda: self.fake.url(),
            'domain_name': lambda: self.fake.domain_name(),
            'ipv4': lambda: self.fake.ipv4(),
            'user_agent': lambda: self.fake.user_agent(),
            'company': lambda: self.fake.company(),
            
            # Case (Mock)
            'case_title': lambda: f"测试用例-{self.fake.word()}-{self.fake.random_int(100, 999)}",
            'precondition': lambda: "用户已登录，且网络正常",
            'test_step': lambda: "1. 点击按钮\n2. 输入文本\n3. 提交表单",
            'expected_result': lambda: "操作成功，显示提示信息",
            
            # Record (Mock)
            'mouse_coords': lambda: f"({self.fake.random_int(0, 1920)}, {self.fake.random_int(0, 1080)})",
            'keyboard_key': lambda: self.fake.random_element(elements=('Enter', 'Esc', 'Space', 'Tab', 'Ctrl', 'Alt')),
            'click_event': lambda: f"Click at ({self.fake.random_int(0, 1920)}, {self.fake.random_int(0, 1080)})",
            
            # Image
            'image_url': lambda: self.fake.image_url(),
            'avatar': lambda: f"https://api.dicebear.com/7.x/avataaars/svg?seed={self.fake.uuid4()}", # Better avatar placeholder
            
            # File
            'file_name': lambda: self.fake.file_name(),
            'file_extension': lambda: self.fake.file_extension(),
            'mime_type': lambda: self.fake.mime_type(),
            
            # AI (Mock)
            'ai_text': lambda: self.fake.paragraph(),
            'ai_image': lambda: self.fake.image_url(),
        }

    def generate_data(self, schema, count=10):
        """
        Generate test data based on schema.
        
        Args:
            schema (list): List of field definitions.
                           Example: [{'name': 'username', 'type': 'name'}, {'name': 'age', 'type': 'random_int', 'min': 18, 'max': 60}]
            count (int): Number of records to generate.
            
        Returns:
            list: List of generated records (dicts).
        """
        results = []
        for _ in range(count):
            row = {}
            for field in schema:
                field_name = field.get('name')
                field_type = field.get('type')
                
                if not field_name or not field_type:
                    continue
                
                # Extract arguments
                kwargs = {k: v for k, v in field.items() if k not in ['name', 'type', 'params']}
                
                try:
                    # 1. Check TYPE_MAPPING first
                    if field_type in self.TYPE_MAPPING:
                        handler = self.TYPE_MAPPING[field_type]
                        if callable(handler):
                            # Check if handler accepts kwargs (simplified check)
                            # For lambdas in mapping, we usually don't pass kwargs unless designed
                            # But for direct Faker method calls, we might need them
                            
                            # Special handling for random_int which needs params
                            if field_type == 'random_int' and kwargs:
                                row[field_name] = self.fake.random_int(**kwargs)
                            elif field_type == 'text' and kwargs:
                                row[field_name] = self.fake.text(max_nb_chars=kwargs.get('max', 200))
                            else:
                                row[field_name] = handler()
                        else:
                            row[field_name] = handler
                            
                    # 2. Fallback to direct Faker method
                    elif hasattr(self.fake, field_type):
                        provider = getattr(self.fake, field_type)
                        if callable(provider):
                            row[field_name] = provider(**kwargs)
                        else:
                            row[field_name] = provider
                    else:
                        # Fallback or error
                        logger.warning(f"Unknown Faker provider: {field_type}")
                        row[field_name] = f"Unknown type: {field_type}"
                except Exception as e:
                    logger.warning(f"Error generating field {field_name} with type {field_type}: {e}")
                    row[field_name] = None
            
            results.append(row)
        return results

    def get_available_providers(self):
        """Return a list of common available providers"""
        # This is a simplified list of common providers
        return [
            {'type': 'name', 'description': '姓名'},
            {'type': 'address', 'description': '地址'},
            {'type': 'email', 'description': '邮箱'},
            {'type': 'phone_number', 'description': '电话号码'},
            {'type': 'company', 'description': '公司名'},
            {'type': 'job', 'description': '职位'},
            {'type': 'text', 'description': '文本'},
            {'type': 'date', 'description': '日期'},
            {'type': 'date_time', 'description': '日期时间'},
            {'type': 'random_int', 'description': '随机整数', 'params': ['min', 'max']},
            {'type': 'uuid4', 'description': 'UUID'},
            {'type': 'ipv4', 'description': 'IPv4地址'},
            {'type': 'url', 'description': 'URL'},
            {'type': 'credit_card_number', 'description': '信用卡号'},
        ]
