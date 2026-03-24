import sys
import os
import django
import json

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.ui_automation.models import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory, force_authenticate
from apps.ui_automation.views.testcase_views import TestCaseViewSet

User = get_user_model()
u = User.objects.first()
tc = TestCase.objects.last()

if not tc:
    print("No test case found")
    sys.exit()

rf = APIRequestFactory()
r = rf.post(f'/run/', data={"engine": "playwright", "browser": "chrome", "headless": True}, format='json')
force_authenticate(r, user=u)

view = TestCaseViewSet.as_view({'post': 'run'})
try:
    res = view(r, pk=tc.id)
    print(f"Status: {res.status_code}")
    print(f"Response: {res.data}")
except Exception as e:
    import traceback
    traceback.print_exc()
