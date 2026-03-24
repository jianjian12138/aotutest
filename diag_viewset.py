import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.reports.views import TestReportViewSet
from rest_framework.decorators import action

print(f"File: {TestReportViewSet.__module__}")
view = TestReportViewSet()
print("Methods in TestReportViewSet:")
for attr in dir(TestReportViewSet):
    if not attr.startswith("__"):
        method = getattr(TestReportViewSet, attr)
        if hasattr(method, 'detail'):
            print(f"  ACTION: {attr}, detail={method.detail}, url_path={getattr(method, 'url_path', 'None')}")

print("\nTesting dispatch print:")
from rest_framework.test import APIRequestFactory
factory = APIRequestFactory()
request = factory.get('/')
try:
    # Test if dispatch actually prints
    view.dispatch(request)
except Exception as e:
    print(f"Dispatch failed (expected since no kwargs/etc): {e}")
