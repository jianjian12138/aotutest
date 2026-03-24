from rest_framework import generics, permissions, status, viewsets
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from django.http import HttpResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from .models import TestCaseModule, TestCase, TestCaseStep, TestCaseAttachment, TestCaseComment
from .serializers import (
    TestCaseModuleSerializer, TestCaseSerializer, TestCaseCreateSerializer, TestCaseUpdateSerializer
)
from apps.core_platform.models import Project

class TestCaseModuleViewSet(viewsets.ModelViewSet):
    """测试用例模块视图集"""
    queryset = TestCaseModule.objects.all()
    serializer_class = TestCaseModuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['order', 'created_at']
    ordering = ['order', 'created_at']
    filterset_fields = ['project', 'parent']
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        queryset = TestCaseModule.objects.filter(project__in=accessible_projects)
        
        # 默认只返回顶级模块（如果没有显式请求特定父模块）
        parent_id = self.request.query_params.get('parent')
        get_all = self.request.query_params.get('get_all')
        if parent_id is None and not get_all:
            return queryset.filter(parent__isnull=True)
        return queryset
        
    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取模块树"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def batch_update_order(self, request):
        """批量更新模块排序"""
        items = request.data.get('items', [])
        if not items:
            return Response({'error': '未提供排序数据'}, status=status.HTTP_400_BAD_REQUEST)

        updated_modules = []
        for index, item_id in enumerate(items):
            try:
                module = TestCaseModule.objects.get(id=item_id)
                module.order = index
                module.save()
                updated_modules.append(module)
            except TestCaseModule.DoesNotExist:
                continue

        serializer = self.get_serializer(updated_modules, many=True)
        return Response(serializer.data)


class TestCaseListCreateView(generics.ListCreateAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['priority', 'status', 'test_type', 'project', 'module']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TestCaseCreateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        # 只显示用户有权限访问的项目的测试用例
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestCase.objects.select_related(
            'author', 'assignee', 'project', 'module'
        ).prefetch_related(
            'versions', 'step_details', 'attachments', 'comments'
        ).filter(project__in=accessible_projects)
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
    
    def perform_create(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        # 获取用户有权限的项目
        accessible_projects = self.get_user_accessible_projects(user)
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            try:
                project = accessible_projects.get(id=project_id)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，使用第一个可访问的项目
                project = accessible_projects.first()
                if not project:
                    # 如果用户没有任何项目，创建默认项目
                    project = Project.objects.create(
                        name="默认项目",
                        owner=user,
                        description='系统自动创建的默认项目'
                    )
        else:
            # 没有指定项目，使用第一个可访问的项目
            project = accessible_projects.first()
            if not project:
                # 如果用户没有任何项目，创建默认项目
                project = Project.objects.create(
                    name="默认项目",
                    owner=user,
                    description='系统自动创建的默认项目'
                )
        
        serializer.save(author=user, project=project)

class TestCaseDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = TestCase.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return TestCaseUpdateSerializer
        return TestCaseSerializer
    
    def get_queryset(self):
        user = self.request.user
        accessible_projects = Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return TestCase.objects.select_related(
            'author', 'assignee', 'project', 'module'
        ).prefetch_related(
            'versions', 'step_details', 'attachments', 'comments'
        ).filter(project__in=accessible_projects)
    
    def get_user_accessible_projects(self, user):
        """获取用户有权限访问的项目"""
        return Project.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
    
    def perform_update(self, serializer):
        user = self.request.user
        project_id = self.request.data.get('project_id')
        
        if project_id:
            # 检查指定的项目是否存在且用户有权限
            accessible_projects = self.get_user_accessible_projects(user)
            try:
                project = accessible_projects.get(id=project_id)
                serializer.save(project=project)
            except Project.DoesNotExist:
                # 如果指定项目不存在或无权限，保持原项目不变
                serializer.save()
        else:
            # 没有指定项目，保持原项目不变
            serializer.save()

class ImportTestCaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        file = request.FILES.get('file')
        file_type = request.data.get('file_type', 'excel')
        project_id = request.data.get('project_id')
        
        if not file:
            return Response({'error': 'No file uploaded'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if project_id:
                project = Project.objects.get(id=project_id)
                # Check permission
                if not (request.user == project.owner or request.user in project.members.all()):
                    return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
            else:
                # Default to first accessible project
                project = Project.objects.filter(
                    models.Q(owner=request.user) | models.Q(members=request.user)
                ).distinct().first()
                if not project:
                    return Response({'error': 'No accessible project found'}, status=status.HTTP_400_BAD_REQUEST)
            
            count = ImportService.import_cases(file, file_type, project, request.user)
            return Response({'message': f'Successfully imported {count} test cases'})
            
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class ExportTestCaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        project_id = request.query_params.get('project_id')
        file_type = request.query_params.get('file_type', 'excel')
        
        queryset = TestCase.objects.filter(
            models.Q(project__owner=request.user) | models.Q(project__members=request.user)
        ).distinct()
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        try:
            if file_type == 'excel':
                wb = ExportService.export_cases(queryset, file_type)
                response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="test_cases.xlsx"'
                wb.save(response)
                return response
            elif file_type == 'json':
                data = ExportService.export_cases(queryset, file_type)
                response = HttpResponse(data, content_type='application/json')
                response['Content-Disposition'] = 'attachment; filename="test_cases.json"'
                return response
            elif file_type == 'yaml':
                data = ExportService.export_cases(queryset, file_type)
                response = HttpResponse(data, content_type='application/x-yaml')
                response['Content-Disposition'] = 'attachment; filename="test_cases.yaml"'
                return response
            else:
                return Response({'error': 'Unsupported file type'}, status=status.HTTP_400_BAD_REQUEST)
                
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
