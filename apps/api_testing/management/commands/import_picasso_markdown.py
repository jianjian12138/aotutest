import os
import re
import json
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.api_testing.models import ApiProject, ApiCollection, ApiRequest

User = get_user_model()

class Command(BaseCommand):
    help = 'Import Picasso project interface documents from Markdown file (Optimized for large files)'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the Markdown file')
        parser.add_argument('--user', type=str, default='admin', help='Username to assign as owner')

    def handle(self, *args, **options):
        file_path = options['file_path']
        username = options['user']

        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"File {file_path} does not exist."))
            return

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            user = User.objects.first()
            if not user:
                self.stdout.write(self.style.ERROR(f"User {username} not found and no users exist."))
                return

        project_name = "毕加索"
        project, created = ApiProject.objects.get_or_create(
            name=project_name,
            defaults={
                'project_type': 'HTTP',
                'status': 'IN_PROGRESS',
                'owner': user,
                'description': '毕加索项目接口文档导入'
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f"Created project: {project_name}"))

        current_collection = None
        current_interface_name = None
        current_interface_buffer = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Group/Collection Level
                if line.startswith('# '):
                    # Save previous interface before switching collection
                    if current_interface_name and current_interface_buffer:
                        self._parse_and_create_request("\n".join(current_interface_buffer), current_interface_name, current_collection, user)
                        current_interface_name = None
                        current_interface_buffer = []

                    collection_name = line[2:].strip()
                    if collection_name and collection_name != "中造快速开发平台":
                        current_collection, _ = ApiCollection.objects.get_or_create(
                            name=collection_name,
                            project=project,
                            defaults={'description': f'Group: {collection_name}'}
                        )
                        self.stdout.write(f"Collection: {collection_name}")
                    else:
                        current_collection = None
                
                # Interface Level
                elif line.startswith('## '):
                    # Save previous interface
                    if current_interface_name and current_interface_buffer:
                        self._parse_and_create_request("\n".join(current_interface_buffer), current_interface_name, current_collection, user)
                    
                    current_interface_name = line[3:].strip()
                    current_interface_buffer = []
                
                else:
                    if current_interface_name:
                        current_interface_buffer.append(line)

            # Save the last interface
            if current_interface_name and current_interface_buffer:
                self._parse_and_create_request("\n".join(current_interface_buffer), current_interface_name, current_collection, user)

        self.stdout.write(self.style.SUCCESS("Import completed!"))

    def _parse_and_create_request(self, content, name, collection, user):
        if not collection:
            return

        url = ""
        method = "GET"
        headers = {}
        params = {}
        body = {}

        # Extract URL
        path_match = re.search(r'\*\*接口地址\*\*:`([^`]+)`', content)
        if path_match:
            url = path_match.group(1).strip()

        # Extract Method
        method_match = re.search(r'\*\*请求方式\*\*:`([^`]+)`', content)
        if method_match:
            method = method_match.group(1).strip().upper()

        # Simple parameter table parsing
        # | 参数名称 | 参数说明 | 请求类型 | 是否必须 | 数据类型 | schema |
        param_table_match = re.search(r'\*\*请求参数\*\*:(.*?)\n\s*\|', content, re.DOTALL)
        if param_table_match:
            # Find where the table actually starts
            table_start = content.find('|', param_table_match.start())
            table_end = content.find('\n\n', table_start)
            if table_end == -1: table_end = len(content)
            
            table_content = content[table_start:table_end]
            for line in table_content.split('\n'):
                if '|' not in line or '---' in line or '参数名称' in line:
                    continue
                cols = [c.strip() for c in line.split('|')]
                if len(cols) < 6:
                    continue
                
                p_name = cols[1].replace('&emsp;', '').strip()
                p_type = cols[3].strip().lower() # 请求类型: body, header, query
                
                if p_type == 'header':
                    headers[p_name] = ""
                elif p_type == 'query':
                    params[p_name] = ""
                elif p_type == 'body' or not p_type:
                    if p_name:
                        body[p_name] = ""

        # Request Example parsing
        example_match = re.search(r'\*\*请求示例\*\*:(.*?)```javascript\n(.*?)\n```', content, re.DOTALL)
        if example_match:
            try:
                example_json_str = example_match.group(2).strip()
                example_json = json.loads(example_json_str)
                if isinstance(example_json, dict):
                    body = {
                        'type': 'json',
                        'data': example_json
                    }
            except:
                pass

        if not isinstance(body, dict) or 'type' not in body:
            body = {'type': 'json', 'data': body} if body else {}

        # Default headers
        if not headers.get('Authorization'):
            headers['Authorization'] = 'Bearer {{token}}'
        if not headers.get('tenant-id'):
            headers['tenant-id'] = '{{tenant_id}}'
        if not headers.get('Content-Type'):
            headers['Content-Type'] = 'application/json'

        header_list = []
        for k, v in headers.items():
            header_list.append({
                'key': k,
                'value': v,
                'enabled': True,
                'description': ''
            })

        ApiRequest.objects.update_or_create(
            name=name,
            collection=collection,
            defaults={
                'method': method,
                'url': url,
                'headers': header_list,
                'params': params,
                'body': body,
                'created_by': user,
                'description': f'Imported from Picasso docs'
            }
        )
        # self.stdout.write(f"  Request: {name}") # Too much output, suppress unless needed
