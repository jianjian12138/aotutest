from rest_framework import viewsets

class BaseProjectViewSet(viewsets.ModelViewSet):
    """
    全局基础 ViewSet：负责统一处理项目级别的数据隔离和自动填充审计字段
    """
    
    def get_queryset(self):
        """
        统一实现根据 project_id 过滤数据的逻辑。
        只有当请求查询参数中包含 (project_id=X) 时才进行过滤，实现数据级别的项目隔离。
        要求继承此类的 Model 必须具有 project 字段（ForeignKey）。
        """
        queryset = super().get_queryset()
        
        # 处理 schema generation 等无 request 环境
        if getattr(self, 'swagger_fake_view', False) or not hasattr(self, 'request') or self.request is None:
            return queryset
            
        # 兼容 query_params 和 data (处理 GET/POST)
        project_id = getattr(self.request, 'query_params', {}).get('project_id')
        if not project_id and hasattr(self.request, 'data') and isinstance(self.request.data, dict):
             project_id = self.request.data.get('project_id')
             
        if project_id:
            return queryset.filter(project_id=project_id)
        return queryset

    def perform_create(self, serializer):
        """
        统一实现创建记录时自动绑定 created_by 为当前登录用户
        要求继承此类的 Model 必须具有 created_by 字段
        """
        if hasattr(serializer.Meta.model, 'created_by'):
            serializer.save(created_by=self.request.user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        """
        统一实现更新记录时自动绑定 updated_by 为当前登录用户
        要求继承此类的 Model 必须具有 updated_by 字段
        """
        if hasattr(serializer.Meta.model, 'updated_by'):
            serializer.save(updated_by=self.request.user)
        else:
            serializer.save()
