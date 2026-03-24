import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.filter(is_superuser=True).first() or User.objects.first()
if not user:
    print("NO USERS FOUND")
    exit(1)

c = Client()
c.force_login(user)

try:
    resp = c.get('/api/testcases/')
    print('STATUS:', resp.status_code)
    try:
        data = resp.json()
        print('SUCCESS:', len(data.get('results', data)) if isinstance(data, dict) else len(data), 'records found.')
    except Exception:
        print('BODY ERR:', resp.content.decode('utf-8')[:1000])
except Exception as e:
    import traceback
    traceback.print_exc()
