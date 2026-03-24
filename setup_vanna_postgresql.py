import os
import django
import sys
from django.utils import timezone

# 设置 Django 环境
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.core_platform.models import User
from apps.data_factory.models import VannaConfig

def configure_postgresql():
    print("🚀 开始向【配置中心】及【数据工厂】注入用户提供的真实 PostgreSQL 数据库信源...")

    # 获取默认管理员用户
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        admin_user = User.objects.first()

    db_connection = {
        "host": "192.168.2.172",
        "port": 5432,
        "database": "ruoyi-vue-pro",
        "username": "postgres",
        "password": "postgres",
        "ssl": False
    }

    # 删除旧的测试库
    VannaConfig.objects.filter(name="测试环境-RuoYi-PostgreSQL").delete()

    config = VannaConfig.objects.create(
        name="测试环境-RuoYi-PostgreSQL",
        description="系统平台业务测试基础支撑库",
        provider="openai",  # Dashboard default UI requires AI model definitions alongside the DB config
        model="gpt-3.5-turbo",
        api_key="sk-placeholder-" + str(timezone.now().timestamp()),
        db_type="postgresql",
        db_connection=db_connection,
        is_active=True,
        created_by=admin_user
    )

    print(f"✅ 成功写入数据库配置项: {config.name}")
    print(f"   └─ IP地址: {db_connection['host']}")
    print(f"   └─ 端口:   {db_connection['port']}")
    print(f"   └─ 数据库名:{db_connection['database']}")
    print(f"   └─ 用户名: {db_connection['username']}")
    print("\n🎉 VannaConfig 数据工厂连接点配置完成！请前往平台上查收。")

if __name__ == "__main__":
    configure_postgresql()
