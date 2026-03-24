import os
import re

directory = r'd:\TEST\apps'

replacements = [
    (r'from apps\.users\.models import', 'from apps.core_platform.models import'),
    (r'from apps\.projects\.models import', 'from apps.core_platform.models import'),
    (r'from apps\.versions\.models import', 'from apps.core_platform.models import'),
    (r'from apps\.configuration\.models import', 'from apps.core_platform.models import'),
    
    (r'from apps\.users\.serializers import', 'from apps.core_platform.serializers.users import'),
    (r'from apps\.projects\.serializers import', 'from apps.core_platform.serializers.projects import'),
    (r'from apps\.versions\.serializers import', 'from apps.core_platform.serializers.versions import'),
    (r'from apps\.configuration\.serializers import', 'from apps.core_platform.serializers.configuration import'),

    (r'from apps\.users import views', 'from apps.core_platform.views import users as views'),
    (r'from apps\.projects import views', 'from apps.core_platform.views import projects as views'),
    (r'from apps\.versions import views', 'from apps.core_platform.views import versions as views'),
    (r'from apps\.configuration import views', 'from apps.core_platform.views import configuration as views'),
    
    (r'import apps\.users\.models', 'import apps.core_platform.models'),
    (r'import apps\.projects\.models', 'import apps.core_platform.models'),
    (r'import apps\.versions\.models', 'import apps.core_platform.models'),
    (r'import apps\.configuration\.models', 'import apps.core_platform.models'),
]

def update_file(filepath):
    # Skip core_platform to avoid double-processing if it was already fixed
    if 'core_platform' in filepath:
        return
        
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content = content
        for pattern, replacement in replacements:
            new_content = re.sub(pattern, replacement, new_content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated globally: {filepath}")
    except Exception as e:
        print(f"Error in {filepath}: {e}")

for root, dirs, files in os.walk(directory):
    for file in files:
        if file.endswith('.py'):
            update_file(os.path.join(root, file))
