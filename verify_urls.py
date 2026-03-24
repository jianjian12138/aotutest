import os
import django
from django.urls import resolve, reverse
from rest_framework.test import APIRequestFactory

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.reports.views import TestReportViewSet

print("Checking TestReportViewSet actions:")
view = TestReportViewSet()
for attr in dir(view):
    method = getattr(view, attr)
    if hasattr(method, 'detail'):
        print(f"  Action: {attr}, detail={method.detail}, url_path={getattr(method, 'url_path', 'None')}")

print("\nTrying to reverse export URL:")
try:
    url = reverse('reports-export', kwargs={'pk': 10})
    print(f"  Reversed URL (basename='reports'): {url}")
except Exception as e:
    print(f"  Failed to reverse 'reports-export': {e}")

try:
    url = reverse('testreport-export', kwargs={'pk': 10})
    print(f"  Reversed URL (basename='testreport'): {url}")
except Exception as e:
    print(f"  Failed to reverse 'testreport-export': {e}")
