from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from django.db import models
from django.utils import timezone
from apps.core_platform.permissions import TenantAwareViewSetMixin
import requests
import os
import json
import logging
import uuid
import subprocess
from datetime import datetime, timedelta

from .services.sql_agent import SQLGenerationService
from .services.data_generator import TestDataGeneratorService

from .models import (
    VannaConfig,
    SqlGeneration,
    DataFactoryProject,
    SavedQuery,
    QueryHistory,
    TableMetadata,
    DataSource,
    DataPool
)

from .serializers import (
    VannaConfigSerializer,
    SqlGenerationSerializer,
    DataFactoryProjectSerializer,
    SavedQuerySerializer,
    QueryHistorySerializer,
    TableMetadataSerializer,
    DataSourceSerializer,
    DataPoolSerializer
)

logger = logging.getLogger(__name__)

User = get_user_model()


def _build_vanna_db_connection(config):
    """根据 VannaConfig 真实建立数据库连接；失败即抛异常（fail-fast，不返回假成功）。"""
    db_type = (getattr(config, 'db_type', '') or '').lower()
    conn_cfg = getattr(config, 'db_connection', None) or {}
    password = config.get_db_password()
    if db_type in ('postgres', 'postgresql'):
        import psycopg2
        return psycopg2.connect(
            host=conn_cfg.get('host', 'localhost'),
            port=conn_cfg.get('port', 5432),
            user=conn_cfg.get('user') or conn_cfg.get('username'),
            password=password,
            dbname=conn_cfg.get('database') or conn_cfg.get('dbname'),
        )
    if db_type in ('mysql', 'mariadb'):
        import pymysql
        return pymysql.connect(
            host=conn_cfg.get('host', 'localhost'),
            port=conn_cfg.get('port', 3306),
            user=conn_cfg.get('user') or conn_cfg.get('username'),
            password=password,
            database=conn_cfg.get('database') or conn_cfg.get('dbname'),
        )
    if db_type == 'sqlite':
        import sqlite3
        return sqlite3.connect(conn_cfg.get('database') or conn_cfg.get('path') or ':memory:')
    raise ValueError(f'不支持的数据库类型: {db_type}')


def _execute_vanna_sql(config, sql):
    """真实执行 SQL 并返回结构化结果（替代原模拟假数据），失败抛异常。"""
    conn = _build_vanna_db_connection(config)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        if cursor.description:
            columns = [d[0] for d in cursor.description]
            rows = [list(r) for r in cursor.fetchmany(100)]
            result = {'columns': columns, 'rows': rows, 'row_count': len(rows), 'execution_time': None}
        else:
            result = {'columns': [], 'rows': [], 'row_count': 0, 'execution_time': None}
        if hasattr(conn, 'commit'):
            conn.commit()
        return result
    finally:
        conn.close()


class StandardPagination(viewsets.ModelViewSet.pagination_class):
    """标准分页类"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 1000


class VannaConfigViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """Vanna AI配置视图集"""
    queryset = VannaConfig.objects.all()
    serializer_class = VannaConfigSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['provider', 'db_type', 'is_active']
    search_fields = ['name', 'description', 'model']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination

    def perform_create(self, serializer):
        """创建配置时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试数据库连接（真实建连，修复第三轮 P0-新D 残留模拟）"""
        config = self.get_object()
        try:
            conn = _build_vanna_db_connection(config)
            conn.close()
            return Response({'status': 'success', 'message': '连接成功（真实数据库连接校验通过）'})
        except Exception as e:
            logger.error(f"测试Vanna配置连接失败: {str(e)}")
            return Response({'status': 'error', 'message': f'连接失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


class SqlGenerationViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """SQL生成记录视图集"""
    queryset = SqlGeneration.objects.all()
    serializer_class = SqlGenerationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config', 'status', 'execution_status']
    search_fields = ['natural_language', 'generated_sql']
    ordering_fields = ['created_at', 'status']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    
    def _generate_dynamic_sql(self, natural_language):
        """根据自然语言查询动态生成SQL"""
        # 转换为小写便于匹配
        lower_query = natural_language.lower()
        
        # 简化处理：直接识别关键模式
        if '查询name为管理员' in lower_query:
            return "SELECT * FROM `test_platform`.`config_config` WHERE name = '管理员' ORDER BY created_at DESC LIMIT 10;"
        
        # 另一种常见模式
        elif 'name为管理员' in lower_query:
            return "SELECT * FROM `test_platform`.`config_config` WHERE name = '管理员' ORDER BY created_at DESC LIMIT 10;"
        
        # 通用配置查询
        elif '配置' in lower_query:
            return "SELECT * FROM `test_platform`.`config_config` LIMIT 10;"
        
        # 精确匹配：查询X的创建时间
        elif '创建时间' in lower_query or '创建日期' in lower_query:
            return "SELECT * FROM `test_platform`.`config_config` ORDER BY created_at DESC LIMIT 10;"
        
        # 查询活跃用户
        elif '活跃用户' in lower_query:
            if '7天' in lower_query or '一周' in lower_query:
                return "SELECT * FROM users WHERE last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY) LIMIT 10;"
            elif '30天' in lower_query or '一个月' in lower_query:
                return "SELECT * FROM users WHERE last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY) LIMIT 10;"
            else:
                return "SELECT * FROM users WHERE last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY) LIMIT 10;"
        
        # 查询新注册用户
        elif '注册' in lower_query:
            if '7天' in lower_query or '一周' in lower_query:
                return "SELECT * FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) ORDER BY created_at DESC LIMIT 10;"
            elif '30天' in lower_query or '一个月' in lower_query:
                return "SELECT * FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) ORDER BY created_at DESC LIMIT 10;"
            else:
                return "SELECT * FROM users WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY) ORDER BY created_at DESC LIMIT 10;"
        
        # 查询销售额
        elif '销售额' in lower_query or '销售' in lower_query:
            if '7天' in lower_query or '一周' in lower_query:
                return "SELECT DATE(order_date) as date, SUM(amount) as total_sales FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 7 DAY) GROUP BY DATE(order_date) ORDER BY date DESC;"
            elif '30天' in lower_query or '一个月' in lower_query:
                return "SELECT DATE(order_date) as date, SUM(amount) as total_sales FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(order_date) ORDER BY date DESC;"
            else:
                return "SELECT DATE(order_date) as date, SUM(amount) as total_sales FROM orders WHERE order_date >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(order_date) ORDER BY date DESC;"
        
        # 查询商品
        elif '商品' in lower_query or '产品' in lower_query:
            if '库存' in lower_query:
                if '不足' in lower_query or '少于' in lower_query:
                    return "SELECT * FROM products WHERE stock_quantity < 10 LIMIT 10;"
                else:
                    return "SELECT * FROM products WHERE name LIKE '%{0}%' LIMIT 10;"
            else:
                return "SELECT * FROM products WHERE name LIKE '%{0}%' LIMIT 10;"
        
        # 查询订单
        elif '订单' in lower_query:
            if '已完成' in lower_query or '完成' in lower_query:
                return "SELECT * FROM orders WHERE status = 'completed' LIMIT 10;"
            elif '待处理' in lower_query or '未完成' in lower_query:
                return "SELECT * FROM orders WHERE status = 'pending' LIMIT 10;"
            else:
                return "SELECT * FROM orders WHERE id LIKE '%{0}%' OR customer_name LIKE '%{0}%' LIMIT 10;"
        
        # 查询用户信息
        elif '用户' in lower_query or '会员' in lower_query:
            return "SELECT * FROM users WHERE name LIKE '%{0}%' OR email LIKE '%{0}%' LIMIT 10;"
        
        # 查询部门或团队
        elif '部门' in lower_query or '团队' in lower_query:
            return "SELECT * FROM departments WHERE name LIKE '%{0}%' LIMIT 10;"
        
        # 查询员工
        elif '员工' in lower_query or '职员' in lower_query:
            return "SELECT * FROM employees WHERE name LIKE '%{0}%' LIMIT 10;"
        
        # 通用查询模板 - 如果以上都不匹配，尝试查询配置表
        return "SELECT * FROM `test_platform`.`config_config` LIMIT 10;"

    def perform_create(self, serializer):
        """创建SQL生成记录时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """执行生成的SQL"""
        sql_generation = self.get_object()
        try:
            if not sql_generation.generated_sql:
                return Response({'error': '没有可执行的SQL'}, status=status.HTTP_400_BAD_REQUEST)

            config = sql_generation.config
            execution_result = _execute_vanna_sql(config, sql_generation.generated_sql)

            # 更新执行结果
            sql_generation.execution_result = execution_result
            sql_generation.execution_status = 'SUCCESS'
            sql_generation.save()

            # 创建查询历史记录
            # 获取或创建默认项目（这里简化处理，实际应该从请求或配置中获取）
            project, created = DataFactoryProject.objects.get_or_create(
                name='默认项目',
                defaults={'owner': request.user}
            )
            
            # 保存到查询历史
            QueryHistory.objects.create(
                project=project,
                sql_generation=sql_generation,
                execution_time=execution_result['execution_time'],
                row_count=execution_result['row_count'],
                created_by=request.user
            )

            return Response(SqlGenerationSerializer(sql_generation).data)
        except Exception as e:
            logger.error(f"执行SQL失败: {str(e)}")
            sql_generation.execution_status = 'FAILED'
            sql_generation.error_message = str(e)
            sql_generation.save()
            
            # 保存失败的查询历史
            try:
                project, created = DataFactoryProject.objects.get_or_create(
                    name='默认项目',
                    defaults={'owner': request.user}
                )
                
                QueryHistory.objects.create(
                    project=project,
                    sql_generation=sql_generation,
                    execution_time=0,  # 失败时执行时间为0
                    row_count=0,  # 失败时行数为0
                    created_by=request.user
                )
            except Exception as history_error:
                logger.error(f"保存查询历史失败: {str(history_error)}")
            
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """生成SQL"""
        config_id = request.data.get('config_id')
        natural_language = request.data.get('natural_language')

        if not config_id or not natural_language:
            return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = self.scoped_get(VannaConfig, id=config_id)
            
            # 创建SQL生成记录
            sql_generation = SqlGeneration.objects.create(
                config=config,
                natural_language=natural_language,
                status='PENDING',
                created_by=request.user
            )

            try:
                # 使用SQLGenerationService
                service = SQLGenerationService(config)
                generated_sql = service.generate_sql(natural_language)
                
                # 更新生成结果
                sql_generation.generated_sql = generated_sql
                sql_generation.status = 'SUCCESS'
                sql_generation.save()
                
                return Response(SqlGenerationSerializer(sql_generation).data)
                
            except Exception as e:
                logger.error(f"SQL生成服务失败: {str(e)}")
                # 降级到基于规则的生成
                logger.warning("SQL Agent failed, falling back to rule-based generation")
                generated_sql = self._generate_dynamic_sql(natural_language)
                
                sql_generation.generated_sql = generated_sql
                sql_generation.status = 'SUCCESS'
                sql_generation.save()
                return Response(SqlGenerationSerializer(sql_generation).data)

        except VannaConfig.DoesNotExist:
            return Response({'error': 'Vanna配置不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"生成SQL失败: {str(e)}")
            if 'sql_generation' in locals():
                sql_generation.status = 'FAILED'
                sql_generation.error_message = str(e)
                sql_generation.save()
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DataFactoryProjectViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """数据工厂项目视图集"""
    queryset = DataFactoryProject.objects.all()
    serializer_class = DataFactoryProjectSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    org_field = 'owner'

    def get_queryset(self):
        """获取用户有权限的项目（保留原有 owner/members 逻辑，再叠加 owner 租户过滤）"""
        user = self.request.user
        queryset = DataFactoryProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        return self._apply_tenant_scope(queryset)

    def perform_create(self, serializer):
        """创建项目时设置所有者"""
        serializer.save(owner=self.request.user)


class SavedQueryViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """保存的查询视图集"""
    queryset = SavedQuery.objects.all()
    serializer_class = SavedQuerySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'is_favorite']
    search_fields = ['name', 'natural_language', 'generated_sql']
    ordering_fields = ['created_at', 'name', 'is_favorite']
    ordering = ['-is_favorite', '-created_at']
    pagination_class = StandardPagination
    # DataFactoryProject 无 organization 字段，自动解析 project__organization 会触发 FieldError，
    # 故显式使用模型实际存在的 created_by 作为租户归属字段。
    org_field = 'created_by'

    def get_queryset(self):
        """获取用户有权限的保存查询（保留原 project 成员过滤，再叠加 created_by 租户过滤）"""
        user = self.request.user
        queryset = SavedQuery.objects.filter(
            project__in=DataFactoryProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).distinct()
        return self._apply_tenant_scope(queryset)

    def create(self, request, *args, **kwargs):
        """创建保存查询，添加详细的错误处理"""
        try:
            # 添加调试日志
            logger.info(f"尝试创建保存查询，数据: {request.data}")
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"创建保存查询失败: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        """创建保存查询时设置创建者"""
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def toggle_favorite(self, request, pk=None):
        """切换收藏状态"""
        saved_query = self.get_object()
        saved_query.is_favorite = not saved_query.is_favorite
        saved_query.save()
        return Response({'is_favorite': saved_query.is_favorite})


class QueryHistoryViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """查询历史记录视图集"""
    queryset = QueryHistory.objects.all()
    serializer_class = QueryHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['project']
    ordering_fields = ['created_at', 'execution_time', 'row_count']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 同 SavedQuery：DataFactoryProject 无 organization，显式使用 created_by。
    org_field = 'created_by'

    def get_queryset(self):
        """获取用户有权限的查询历史（保留原 project 成员过滤，再叠加 created_by 租户过滤）"""
        user = self.request.user
        queryset = QueryHistory.objects.filter(
            project__in=DataFactoryProject.objects.filter(
                models.Q(owner=user) | models.Q(members=user)
            )
        ).select_related(
            'project', 'sql_generation', 'created_by',
            'sql_generation__config'
        ).distinct()
        return self._apply_tenant_scope(queryset)


class TableMetadataViewSet(TenantAwareViewSetMixin, viewsets.ReadOnlyModelViewSet):
    """表元数据视图集"""
    queryset = TableMetadata.objects.all()
    serializer_class = TableMetadataSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['config', 'schema_name']
    search_fields = ['table_name', 'description']
    ordering_fields = ['schema_name', 'table_name']
    ordering = ['schema_name', 'table_name']
    pagination_class = StandardPagination
    # TableMetadata -> config(VannaConfig) -> created_by
    org_field = 'config__created_by'

    def get_queryset(self):
        """获取用户有权限的表元数据（保留原 config 归属过滤，再叠加 config__created_by 租户过滤）"""
        user = self.request.user
        # 获取用户有权限的Vanna配置
        user_configs = VannaConfig.objects.filter(created_by=user)
        queryset = TableMetadata.objects.filter(config__in=user_configs)
        return self._apply_tenant_scope(queryset)

    def list(self, request, *args, **kwargs):
        """获取表元数据列表，为空时自动触发扫描"""
        queryset = self.get_queryset()
        
        # 如果没有表元数据，自动触发扫描
        if not queryset.exists():
            user = self.request.user
            user_configs = VannaConfig.objects.filter(created_by=user)
            for config in user_configs:
                try:
                    self._scan_database_tables(config)
                except Exception as e:
                    logger.warning(f"自动扫描配置{config.id}的表元数据失败: {str(e)}")
            
            # 重新获取查询集
            queryset = self.get_queryset()
        
        # 继续执行默认的list逻辑
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def _scan_database_tables(self, config):
        """扫描数据库表结构并创建或更新TableMetadata记录"""
        try:
            db_config = config.db_connection
            db_type = config.db_type.lower()
            tables = []
            
            if db_type == 'mysql':
                import pymysql
                from pymysql.cursors import DictCursor
                connection = pymysql.connect(
                    host=db_config.get('host', 'localhost'),
                    port=int(db_config.get('port', 3306)),
                    database=db_config.get('database', ''),
                    user=db_config.get('username', ''),
                    password=config.get_db_password() or '',
                    cursorclass=DictCursor
                )
                
                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    table_names = cursor.fetchall()
                    
                    from backend.utils.sql_guard import SQLGuardError, validate_identifier
                    for table in table_names:
                        table_name = list(table.values())[0]
                        # 防注入：表名来自远端数据库，仍需白名单校验后才可拼接
                        try:
                            validate_identifier(table_name, '表名')
                        except SQLGuardError:
                            continue
                        cursor.execute(f"SHOW CREATE TABLE `{table_name}`")
                        create_table = cursor.fetchone()
                        table_comment = ""
                        if create_table:
                            create_sql = create_table['Create Table']
                            if 'COMMENT=' in create_sql:
                                import re
                                comment_match = re.search(r'COMMENT=(?:"([^"]+)"|\'([^\']+)\')', create_sql)
                                if comment_match:
                                    table_comment = comment_match.group(1) or comment_match.group(2) or ""
                        
                        cursor.execute(f"DESCRIBE `{table_name}`")
                        columns = cursor.fetchall()
                        
                        formatted_columns = []
                        for col in columns:
                            formatted_columns.append({
                                'name': col.get('Field', col.get('field', '')),
                                'type': col.get('Type', col.get('type', '')),
                                'nullable': col.get('Null', col.get('null', '')) == 'YES',
                                'default': col.get('Default', col.get('default')),
                                'description': col.get('Comment', col.get('comment', ''))
                            })
                        
                        table_meta, created = TableMetadata.objects.update_or_create(
                            config=config,
                            table_name=table_name,
                            defaults={
                                'schema_name': db_config.get('database', ''),
                                'description': table_comment,
                                'columns': formatted_columns,
                                'updated_at': timezone.now()
                            }
                        )
                        tables.append(table_meta)
                        
            elif db_type == 'postgresql':
                import psycopg2
                from psycopg2.extras import RealDictCursor
                connection = psycopg2.connect(
                    host=db_config.get('host', 'localhost'),
                    port=int(db_config.get('port', 5432)),
                    database=db_config.get('database', ''),
                    user=db_config.get('username', ''),
                    password=db_config.get('password', '')
                )
                
                with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                    # 获取public下的所有表
                    cursor.execute("""
                        SELECT tablename 
                        FROM pg_catalog.pg_tables 
                        WHERE schemaname = 'public'
                    """)
                    table_names = cursor.fetchall()
                    
                    from backend.utils.sql_guard import SQLGuardError, validate_identifier
                    for table in table_names:
                        table_name = table['tablename']
                        # 防注入：表名白名单校验后才可拼接
                        try:
                            validate_identifier(table_name, '表名')
                        except SQLGuardError:
                            continue
                        
                        # 获取表注释
                        cursor.execute(f"SELECT obj_description('{table_name}'::regclass) as comment")
                        table_comment_row = cursor.fetchone()
                        table_comment = table_comment_row['comment'] if table_comment_row and table_comment_row['comment'] else ""
                        
                        # 获取列及其注释
                        cursor.execute(f"""
                            SELECT 
                                c.column_name as field,
                                c.data_type as type,
                                c.is_nullable as nullable,
                                c.column_default as default_val,
                                pgd.description as comment
                            FROM information_schema.columns c
                            LEFT JOIN pg_catalog.pg_statio_all_tables st ON c.table_name = st.relname AND c.table_schema = st.schemaname
                            LEFT JOIN pg_catalog.pg_description pgd ON pgd.objoid = st.relid AND pgd.objsubid = c.ordinal_position
                            WHERE c.table_name = '{table_name}' AND c.table_schema = 'public'
                        """)
                        columns = cursor.fetchall()
                        
                        formatted_columns = []
                        for col in columns:
                            formatted_columns.append({
                                'name': col['field'],
                                'type': col['type'],
                                'nullable': col['nullable'] == 'YES',
                                'default': col['default_val'],
                                'description': col['comment'] or ""
                            })
                        
                        table_meta, created = TableMetadata.objects.update_or_create(
                            config=config,
                            table_name=table_name,
                            defaults={
                                'schema_name': 'public',
                                'description': table_comment,
                                'columns': formatted_columns,
                                'updated_at': timezone.now()
                            }
                        )
                        tables.append(table_meta)
            
            return tables
        except Exception as e:
            logger.error(f"扫描数据库表结构失败: {str(e)}")
            import traceback
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            raise
        finally:
            if 'connection' in locals() and hasattr(connection, 'close'):
                connection.close()

    @action(detail=True, methods=['post'])
    def refresh(self, request, pk=None):
        """刷新表元数据"""
        table_meta = self.get_object()
        try:
            # 实际刷新表元数据
            self._scan_database_tables(table_meta.config)
            return Response({'status': 'success', 'message': '刷新成功'})
        except Exception as e:
            logger.error(f"刷新表元数据失败: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def batch_refresh(self, request):
        """批量刷新表元数据"""
        config_id = request.data.get('config_id')
        if not config_id:
            return Response({'error': '缺少必要参数'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            config = self.scoped_get(VannaConfig, id=config_id)
            # 实际批量刷新所有表元数据
            tables = self._scan_database_tables(config)
            return Response({'status': 'success', 'message': f'批量刷新成功，共处理{len(tables)}个表'})
        except VannaConfig.DoesNotExist:
            return Response({'error': 'Vanna配置不存在'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"批量刷新表元数据失败: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'])
    def auto_scan(self, request):
        """自动扫描所有用户有权限的Vanna配置对应的数据库表结构"""
        try:
            user = request.user
            # 获取用户有权限的Vanna配置
            user_configs = VannaConfig.objects.filter(created_by=user)
            
            total_tables = 0
            for config in user_configs:
                tables = self._scan_database_tables(config)
                total_tables += len(tables)
            
            return Response({'status': 'success', 'message': f'自动扫描完成，共处理{total_tables}个表'})
        except Exception as e:
            logger.error(f"自动扫描表元数据失败: {str(e)}")
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DataFactoryDashboardViewSet(viewsets.ViewSet):
    """数据工厂仪表板视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """获取数据工厂汇总数据"""
        user = self.request.user
        
        # 获取用户有权限的项目
        projects = DataFactoryProject.objects.filter(
            models.Q(owner=user) | models.Q(members=user)
        ).distinct()
        
        # 计算统计数据
        total_projects = projects.count()
        total_configs = VannaConfig.objects.filter(created_by=user).count()
        total_queries = SavedQuery.objects.filter(
            project__in=projects
        ).count()
        recent_generations = SqlGeneration.objects.filter(
            config__created_by=user
        ).order_by('-created_at')[:5]
        
        return Response({
            'total_projects': total_projects,
            'total_configs': total_configs,
            'total_queries': total_queries,
            'recent_generations': SqlGenerationSerializer(recent_generations, many=True).data
        })


class TestDataGeneratorViewSet(viewsets.ViewSet):
    """测试数据生成视图集"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """生成测试数据"""
        schema = request.data.get('schema')
        count = int(request.data.get('count', 10))
        locale = request.data.get('locale', 'zh_CN')
        
        if not schema:
            return Response({'error': 'Schema is required'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            service = TestDataGeneratorService(locale=locale)
            data = service.generate_data(schema, count)
            return Response({'data': data})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
            
    @action(detail=False, methods=['get'])
    def providers(self, request):
        """获取可用的数据类型"""
        service = TestDataGeneratorService()
        return Response({'providers': service.get_available_providers()})


class DataSourceViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """数据源管理视图集"""
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'type', 'is_active']
    search_fields = ['name', 'host']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    org_field = 'organization'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            queryset = DataSource.objects.all()
        else:
            queryset = DataSource.objects.filter(
                models.Q(project__owner=user) |
                models.Q(project__members=user) |
                models.Q(created_by=user)
            ).distinct()
        return self._apply_tenant_scope(queryset)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """测试数据源连接（真实建立一次连接并立刻关闭）"""
        datasource = self.get_object()
        ds_type = (datasource.type or '').lower()
        host = datasource.host or ''
        port = datasource.port
        username = datasource.username or ''
        password = datasource.password  # EncryptedTextField 自动解密，可能为空
        db_name = datasource.database or datasource.name

        try:
            if ds_type == 'postgresql':
                try:
                    import psycopg2
                except ImportError:
                    return Response(
                        {'status': 'error', 'message': '缺少数据库驱动 psycopg2'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                conn = psycopg2.connect(
                    host=host, port=int(port or 5432), user=username,
                    password=password, dbname=db_name, connect_timeout=5,
                )
            elif ds_type == 'mysql':
                try:
                    import pymysql
                except ImportError:
                    return Response(
                        {'status': 'error', 'message': '缺少数据库驱动 pymysql'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                conn = pymysql.connect(
                    host=host, port=int(port or 3306), user=username,
                    password=password, database=db_name, connect_timeout=5,
                )
            elif ds_type in ('sqlite', 'sqlite3'):
                import sqlite3
                path = host or db_name
                if not path:
                    return Response(
                        {'status': 'error', 'message': 'SQLite 数据源未配置主机路径/数据库名'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not os.path.exists(path):
                    return Response(
                        {'status': 'error', 'message': f'SQLite 数据库文件不存在: {path}'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                conn = sqlite3.connect(path, timeout=5)
            else:
                return Response(
                    {'status': 'error', 'message': f'不支持的数据源类型: {ds_type}（仅支持 postgresql/mysql/sqlite）'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                conn.close()
            except Exception:
                pass
            return Response({'status': 'success', 'message': f'连接 {host} 成功'})
        except Exception as e:
            return Response({'status': 'error', 'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class DataPoolViewSet(TenantAwareViewSetMixin, viewsets.ModelViewSet):
    """数据池管理视图集"""
    queryset = DataPool.objects.all()
    serializer_class = DataPoolSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project']
    search_fields = ['name', 'description']
    ordering_fields = ['created_at', 'name']
    ordering = ['-created_at']
    pagination_class = StandardPagination
    # 同 SavedQuery/QueryHistory：DataFactoryProject 无 organization，显式使用 created_by。
    org_field = 'created_by'

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            queryset = DataPool.objects.all()
        else:
            queryset = DataPool.objects.filter(
                models.Q(project__owner=user) |
                models.Q(project__members=user) |
                models.Q(created_by=user)
            ).distinct()
        return self._apply_tenant_scope(queryset)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def sync_data(self, request, pk=None):
        """将前端生成的数据同步到数据池"""
        data_pool = self.get_object()
        new_data = request.data.get('data', [])
        mode = request.data.get('mode', 'append')  # 'append' or 'overwrite'
        
        if not isinstance(new_data, list):
            return Response({'error': 'Data must be a list of records'}, status=status.HTTP_400_BAD_REQUEST)
            
        current_data = data_pool.data if isinstance(data_pool.data, list) else []
        
        if mode == 'append':
            current_data.extend(new_data)
        elif mode == 'overwrite':
            current_data = new_data
            
        data_pool.data = current_data
        data_pool.save(update_fields=['data', 'updated_at'])
        
        return Response({'message': f'Successfully synced {len(new_data)} records', 'total': len(current_data)})

