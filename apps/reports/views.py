from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q, Sum, F, Avg
from django.db.models.functions import TruncDate, Length
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import HttpResponse
from io import BytesIO
import pandas as pd
from .models import TestReport, ReportTemplate
from apps.executions.models import TestPlan, TestRun, TestRunCase
from apps.testcases.models import TestCase
from apps.requirement_analysis.models import RequirementAnalysis, GeneratedTestCase, BusinessRequirement

class TestReportViewSet(viewsets.ModelViewSet):
    """测试报告视图集"""
    queryset = TestReport.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """获取概览数据"""
        project_id = request.query_params.get('project')
        
        # 基础查询集
        plans_qs = TestPlan.objects.filter(is_active=True)
        cases_qs = TestCase.objects.all()
        
        if project_id:
            plans_qs = plans_qs.filter(projects__id=project_id)
            cases_qs = cases_qs.filter(project_id=project_id)
            
        # 统计数据
        total_plans = plans_qs.count()
        total_cases = cases_qs.count()
        
        # 计算测试计划总进度
        # 遍历所有活跃计划，计算其下所有TestRun的进度平均值
        total_progress = 0
        plan_count_for_progress = 0
        
        for plan in plans_qs:
            runs = plan.test_runs.all()
            if runs.exists():
                # 计算该计划下所有Run的平均进度
                run_progresses = [run.progress_stats['progress'] for run in runs]
                plan_progress = sum(run_progresses) / len(run_progresses)
                total_progress += plan_progress
                plan_count_for_progress += 1
        
        avg_plan_progress = round(total_progress / plan_count_for_progress, 1) if plan_count_for_progress > 0 else 0
        
        # 计算整体通过率
        recent_runs = TestRun.objects.filter(test_plan__in=plans_qs).order_by('-created_at')[:10]
        total_executed = 0
        total_passed = 0
        
        for run in recent_runs:
            stats = run.progress_stats
            total_executed += stats['tested']
            total_passed += stats['passed']
            
        pass_rate = round((total_passed / total_executed * 100), 1) if total_executed > 0 else 0
        
        # 统计缺陷总数 (基于 TestRunCase 的 defects 字段)
        all_runs = TestRun.objects.filter(test_plan__in=plans_qs)
        defects_count = 0
        for run in all_runs:
            run_cases_with_defects = run.run_cases.exclude(defects=[])
            for rc in run_cases_with_defects:
                if isinstance(rc.defects, list):
                    defects_count += len(rc.defects)
        
        return Response({
            'active_plans': total_plans,
            'plan_progress': avg_plan_progress,
            'total_cases': total_cases,
            'total_defects': defects_count,
            'pass_rate': pass_rate
        })

    @action(detail=False, methods=['get'])
    def status_distribution(self, request):
        """获取执行状态分布"""
        project_id = request.query_params.get('project')
        version_id = request.query_params.get('version')
        
        runs_qs = TestRun.objects.all()
        if project_id:
            runs_qs = runs_qs.filter(project_id=project_id)
        if version_id:
            runs_qs = runs_qs.filter(version_id=version_id)
            
        distribution = TestRunCase.objects.filter(test_run__in=runs_qs).values('status').annotate(
            count=Count('id')
        )
        
        result = {item['status']: item['count'] for item in distribution}
        for status, _ in TestRunCase.STATUS_CHOICES:
            if status not in result:
                result[status] = 0
                
        return Response(result)

    @action(detail=False, methods=['get'])
    def defect_distribution(self, request):
        """获取缺陷分布 (按优先级)"""
        project_id = request.query_params.get('project')
        qs = TestRunCase.objects.filter(status='failed')
        
        if project_id:
            qs = qs.filter(test_run__project_id=project_id)
            
        distribution = qs.values('priority').annotate(count=Count('id'))
        
        # 映射优先级显示
        priority_map = dict(TestRunCase.PRIORITY_CHOICES)
        result = []
        for item in distribution:
            result.append({
                'name': priority_map.get(item['priority'], item['priority']),
                'value': item['count']
            })
            
        return Response(result)

    @action(detail=False, methods=['get'])
    def failed_cases_top(self, request):
        """获取失败用例TOP榜"""
        project_id = request.query_params.get('project')
        
        qs = TestRunCase.objects.filter(status='failed')
        if project_id:
            qs = qs.filter(test_run__project_id=project_id)
            
        # 按 testcase 分组统计失败次数
        top_failed = qs.values(
            'testcase__id', 'testcase__title'
        ).annotate(
            fail_count=Count('id')
        ).order_by('-fail_count')[:10]
        
        return Response(top_failed)

    @action(detail=False, methods=['get'])
    def execution_trend(self, request):
        """获取每日执行趋势"""
        project_id = request.query_params.get('project')
        days = int(request.query_params.get('days', 7))
        
        # 获取当前时区的今天开始时间
        current_tz = timezone.get_current_timezone()
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # 计算起始日期
        start_date = today - timedelta(days=days - 1)
        
        # 构造起始时间的 datetime 对象 (00:00:00)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        start_datetime = timezone.make_aware(start_datetime, current_tz)
        
        qs = TestRunCase.objects.filter(
            executed_at__gte=start_datetime,
            status__in=['passed', 'failed', 'blocked', 'retest']
        )
        
        if project_id:
            qs = qs.filter(test_run__project_id=project_id)
            
        # 由于数据库聚合(TruncDate)在某些环境下返回None，改为Python内存聚合
        # 获取所有符合条件的记录的执行时间
        executions = qs.values_list('executed_at', flat=True)
        
        # 初始化日期映射
        date_map = {}
        
        for executed_at in executions:
            if executed_at:
                # 转换为本地时间
                local_time = executed_at.astimezone(current_tz)
                date_str = local_time.date().strftime('%Y-%m-%d')
                date_map[date_str] = date_map.get(date_str, 0) + 1
        
        # 补全日期
        result = []
        for i in range(days):
            date = start_date + timedelta(days=i)
            date_str = date.strftime('%Y-%m-%d')
            result.append({
                'date': date_str,
                'count': date_map.get(date_str, 0)
            })
            
        return Response(result)

    @action(detail=False, methods=['get'])
    def ai_efficiency(self, request):
        """获取AI效能分析"""
        project_id = request.query_params.get('project')
        
        cases_qs = TestCase.objects.all()
        generated_qs = GeneratedTestCase.objects.all()
        requirements_qs = BusinessRequirement.objects.all()
        
        if project_id:
            cases_qs = cases_qs.filter(project_id=project_id)
            generated_qs = generated_qs.filter(requirement__analysis__document__project_id=project_id)
            requirements_qs = requirements_qs.filter(analysis__document__project_id=project_id)
            
        # 1. AI生成 vs 人工创建
        ai_count = generated_qs.count()
        adopted_ai_count = generated_qs.filter(status='adopted').count()
        total_cases = cases_qs.count()
        manual_count = max(0, total_cases - adopted_ai_count)
        
        # 2. 生成采纳率
        adoption_rate = round((adopted_ai_count / ai_count * 100), 1) if ai_count > 0 else 0
        
        # 3. 需求覆盖率
        total_reqs = requirements_qs.count()
        covered_reqs = generated_qs.filter(status='adopted').values('requirement').distinct().count()
        coverage_rate = round((covered_reqs / total_reqs * 100), 1) if total_reqs > 0 else 0
        
        # 4. 节省时间估算
        saved_hours = round(ai_count * 15 / 60, 1)
        
        return Response({
            'ai_vs_manual': {
                'ai': ai_count,
                'manual': manual_count
            },
            'adoption_rate': adoption_rate,
            'requirement_coverage': coverage_rate,
            'saved_hours': saved_hours
        })

    @action(detail=False, methods=['get'])
    def team_workload(self, request):
        """获取团队工作量"""
        project_id = request.query_params.get('project')
        
        qs = TestRunCase.objects.filter(
            status__in=['passed', 'failed', 'blocked', 'retest'],
            executed_by__isnull=False
        )
        
        if project_id:
            qs = qs.filter(test_run__project_id=project_id)
            
        # 统计执行数量
        execution_stats = qs.values(
            'executed_by__username'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # 统计发现缺陷数量
        defect_stats = {}
        defect_qs = qs.filter(status__in=['failed', 'blocked'])
        defect_data = defect_qs.values('executed_by__username').annotate(count=Count('id'))
        for item in defect_data:
            defect_stats[item['executed_by__username']] = item['count']
            
        result = []
        for item in execution_stats:
            username = item['executed_by__username']
            result.append({
                'username': username,
                'execution_count': item['count'],
                'defect_count': defect_stats.get(username, 0)
            })
            
        return Response(result)
    
    @action(detail=False, methods=['get'])
    def export_report(self, request):
        """导出测试报告为Excel格式"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"Export report called with params: {request.query_params}")
        
        project_id = request.query_params.get('project')
        days = int(request.query_params.get('days', 7))
        
        # 获取当前时区的今天开始时间
        current_tz = timezone.get_current_timezone()
        local_now = timezone.localtime(timezone.now())
        today = local_now.date()
        
        # 计算起始日期
        start_date = today - timedelta(days=days - 1)
        
        try:
            # 1. 准备数据
            logger.info("Preparing report data...")
            
            # 概览数据
            dashboard_data = self.dashboard(request).data
            logger.info(f"Dashboard data: {dashboard_data}")
            
            # 状态分布数据
            status_data = self.status_distribution(request).data
            logger.info(f"Status distribution: {status_data}")
            
            # 失败用例TOP10
            failed_cases = self.failed_cases_top(request).data
            logger.info(f"Failed cases: {failed_cases}")
            
            # 执行趋势数据
            trend_data = self.execution_trend(request).data
            logger.info(f"Execution trend: {trend_data}")
            
            # AI效能数据
            ai_data = self.ai_efficiency(request).data
            logger.info(f"AI efficiency: {ai_data}")
            
            # 团队工作量数据
            workload_data = self.team_workload(request).data
            logger.info(f"Team workload: {workload_data}")
            
            # 2. 创建Excel文件
            output = BytesIO()
            writer = pd.ExcelWriter(output, engine='xlsxwriter')
            
            # 2.1 概览工作表
            overview_df = pd.DataFrame([dashboard_data])
            overview_df.to_excel(writer, sheet_name='概览', index=False)
            
            # 2.2 状态分布工作表
            status_df = pd.DataFrame([status_data])
            status_df.to_excel(writer, sheet_name='执行状态分布', index=False)
            
            # 2.3 失败用例工作表
            failed_cases_df = pd.DataFrame(failed_cases)
            failed_cases_df.to_excel(writer, sheet_name='失败用例TOP10', index=False)
            
            # 2.4 执行趋势工作表
            trend_df = pd.DataFrame(trend_data)
            trend_df.to_excel(writer, sheet_name='执行趋势', index=False)
            
            # 2.5 AI效能工作表
            ai_efficiency_df = pd.DataFrame([{
                'AI生成用例数': ai_data['ai_vs_manual']['ai'],
                '人工创建用例数': ai_data['ai_vs_manual']['manual'],
                'AI生成采纳率': ai_data['adoption_rate'],
                '需求覆盖率': ai_data['requirement_coverage'],
                '节省工时': ai_data['saved_hours']
            }])
            ai_efficiency_df.to_excel(writer, sheet_name='AI效能', index=False)
            
            # 2.6 团队工作量工作表
            workload_df = pd.DataFrame(workload_data)
            workload_df.to_excel(writer, sheet_name='团队工作量', index=False)
            
            # 保存Excel文件
            writer.close()
            output.seek(0)
            
            # 3. 返回响应
            filename = f"测试报告_{today.strftime('%Y%m%d')}.xlsx"
            response = HttpResponse(
                output.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = f'attachment; filename={filename}'
            
            logger.info(f"Report exported successfully: {filename}")
            return response
        except Exception as e:
            logger.error(f"Error exporting report: {str(e)}", exc_info=True)
            return Response({
                'error': f'导出报告失败: {str(e)}'
            }, status=500)