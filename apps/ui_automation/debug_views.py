
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from django.conf import settings
import os
import json
import logging
from datetime import datetime
from .models import UiProject, TestCase

logger = logging.getLogger(__name__)

class DebugFileViewSet(viewsets.ViewSet):
    """调试文件管理视图"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """列出所有项目的调试数据文件"""
        debug_root = os.path.join(settings.MEDIA_ROOT, 'debug_data')
        if not os.path.exists(debug_root):
            return Response([])
        
        results = []
        try:
            for project_id in os.listdir(debug_root):
                project_dir = os.path.join(debug_root, project_id)
                if not os.path.isdir(project_dir): continue
                
                # 尝试获取项目名称
                try:
                    project_name = UiProject.objects.get(id=project_id).name
                except:
                    project_name = f"Project {project_id}"
                
                for case_id in os.listdir(project_dir):
                    case_dir = os.path.join(project_dir, case_id)
                    if not os.path.isdir(case_dir): continue
                    
                    # 尝试获取用例名称
                    try:
                        case = TestCase.objects.get(id=case_id)
                        case_name = case.name
                    except:
                        case_name = f"Case {case_id}"
                    
                    for filename in os.listdir(case_dir):
                        file_path = os.path.join(case_dir, filename)
                        try:
                            stat = os.stat(file_path)
                            
                            # 解析文件名获取步骤信息
                            # 格式: step_{number}_{timing}_{timestamp}.{ext}
                            step_info = "Unknown"
                            parts = filename.split('_')
                            if len(parts) >= 3:
                                step_num = parts[1]
                                timing = parts[2]
                                step_info = f"Step {step_num} ({timing})"

                            url = f"{settings.MEDIA_URL}debug_data/{project_id}/{case_id}/{filename}"
                            results.append({
                                'id': f"{project_id}_{case_id}_{filename}",
                                'project_name': project_name,
                                'case_name': case_name,
                                'filename': filename,
                                'step_info': step_info,
                                'url': url,
                                'size': stat.st_size,
                                'modified_time': stat.st_mtime,
                                'created_at': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                'type': 'image' if filename.endswith('.png') else 'json'
                            })
                        except Exception as e:
                            logger.error(f"Error processing file {filename}: {e}")
                            continue
        except Exception as e:
            logger.error(f"Error listing debug files: {e}")
            return Response({'error': str(e)}, status=500)
        
        # 按修改时间倒序排列
        results.sort(key=lambda x: x['modified_time'], reverse=True)
        return Response(results)

    @action(detail=False, methods=['get'])
    def content(self, request):
        """读取JSON文件内容"""
        url = request.query_params.get('url')
        if not url:
            return Response({'error': 'URL required'}, status=400)
            
        # 安全检查: 确保URL以 MEDIA_URL/debug_data 开头
        expected_prefix = settings.MEDIA_URL + 'debug_data/'
        # 处理可能的斜杠差异
        url = url.replace('\\', '/')
        if not url.startswith(expected_prefix):
             # 尝试处理相对路径的情况
             if url.startswith('/media/debug_data/'):
                 pass
             else:
                 return Response({'error': 'Invalid URL'}, status=403)
            
        relative_path = url.replace(settings.MEDIA_URL, '')
        if relative_path.startswith('/'): relative_path = relative_path[1:]
        
        file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
        
        if not os.path.exists(file_path):
            return Response({'error': 'File not found'}, status=404)
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = json.load(f)
            return Response(content)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
