"""
操作记录工具
用于记录用户在API测试模块中的各种操作
"""
from .models import OperationLog


def log_operation(operation_type, resource_type, resource_id, resource_name, user, description=None):
    """
    记录用户操作

    Args:
        operation_type: 操作类型 (create, edit, delete, execute, run, save)
        resource_type: 资源类型 (project, collection, request, suite, environment, task, execution)
        resource_id: 资源ID
        resource_name: 资源名称
        user: 操作用户
        description: 操作描述(可选,如果不提供会自动生成)
    """
    if description is None:
        # 自动生成描述
        operation_text = dict(OperationLog.OPERATION_TYPE_CHOICES).get(operation_type, operation_type)
        resource_text = dict(OperationLog.RESOURCE_TYPE_CHOICES).get(resource_type, resource_type)
        description = f"{operation_text}{resource_text}「{resource_name}」"

    try:
        OperationLog.objects.create(
            operation_type=operation_type,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_name=resource_name,
            description=description,
            user=user
        )
    except Exception as e:
        # 记录操作日志失败不应影响主要业务逻辑
        print(f"记录操作日志失败: {str(e)}")
