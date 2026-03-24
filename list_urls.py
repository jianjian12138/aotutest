import os
import django
from django.urls import get_resolver

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def list_urls(lis, prefix=''):
    for entry in lis:
        if hasattr(entry, 'url_patterns'):
            list_urls(entry.url_patterns, prefix + str(entry.pattern))
        else:
            print(f"{prefix}{str(entry.pattern)}")

resolver = get_resolver()
list_urls(resolver.url_patterns)
