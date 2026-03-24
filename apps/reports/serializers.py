import json
from rest_framework import serializers
from .models import TestReport, ReportTemplate

class ReportTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReportTemplate
        fields = '__all__'

class TestReportSerializer(serializers.ModelSerializer):
    project_name = serializers.SerializerMethodField()
    test_type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    total_cases = serializers.SerializerMethodField()
    failed_cases = serializers.SerializerMethodField()
    skipped_cases = serializers.SerializerMethodField()
    pass_rate = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()
    executor_name = serializers.SerializerMethodField()
    test_details = serializers.SerializerMethodField()
    
    class Meta:
        model = TestReport
        fields = [
            'id', 'project', 'project_name', 'name', 'report_type',
            'execution', 'api_test_execution', 'api_test_suite_execution', 'ui_test_execution', 'allure_url', 'summary', 'content',
            'ai_analysis_result', 'ai_suggestions', 'ai_analyzed_at',
            'generated_by', 'executor_name', 'created_at',
            'test_type', 'status', 'total_cases', 'failed_cases',
            'skipped_cases', 'pass_rate', 'duration', 'test_details'
        ]
        read_only_fields = ('created_at',)
    
    def get_executor_name(self, obj):
        return obj.generated_by.username if obj.generated_by else '-'

    def get_test_details(self, obj):
        """Map content/summary results to unified test_details format"""
        if obj.report_type in ['api_execution', 'ui_execution']:
            content = obj.content or {}
            results = content.get('results', [])
            mapped_details = []
            
            for item in results:
                # Handle both single case results (list of request results) 
                # and suite results (list of case results)
                is_suite_item = item.get('type') == 'test_case'
                
                if is_suite_item:
                    # Suite item (Case result in a suite)
                    mapped_details.append({
                        'name': item.get('name', 'Test Case'),
                        'status': (item.get('status') or 'FAILED').upper(),
                        'duration': item.get('execution_time', 0),
                        'error_message': item.get('error', ''),
                        'item_type': 'test_case',
                        'passed_count': item.get('passed_count', 0),
                        'failed_count': item.get('failed_count', 0),
                        'total_count': item.get('total_count', 0),
                        'steps': self._map_api_steps(item.get('results', []))
                    })
                else:
                    mapped_details.append({
                        'name': item.get('name', 'Test Case/Request'),
                        'status': 'PASSED' if item.get('passed', False) or str(item.get('status', '')).lower() == 'passed' else 'FAILED',
                        'duration': item.get('response_time', item.get('execution_time', 0)) / 1000,
                        'error_message': item.get('error', ''),
                        'item_type': 'test_request',
                        'request_data': json.dumps(item.get('request_data', {}), indent=2, ensure_ascii=False) if item.get('request_data') else '',
                        'response_data': json.dumps(item.get('response_data', {}), indent=2, ensure_ascii=False) if item.get('response_data') else ''
                    })
            return mapped_details
        return []

    def _map_api_steps(self, steps):
        """Helper to map nested API steps in a suite report"""
        mapped = []
        for step in steps:
            mapped.append({
                'name': step.get('name', 'API Step'),
                'status': 'PASSED' if step.get('passed', False) else 'FAILED',
                'duration': step.get('response_time', 0) / 1000,
                'error_message': step.get('error', '')
            })
        return mapped
    
    def get_project_name(self, obj):
        return obj.project.name if obj.project else '-'
    
    def get_test_type(self, obj):
        if obj.report_type == 'api_execution':
            return 'API'
        if obj.report_type == 'ui_execution':
            return 'UI'
        return 'GENERAL'
    
    def get_status(self, obj):
        summary = obj.summary or {}
        s = summary.get('status', '')
        if s == 'passed':
            return 'PASSED'
        elif s == 'failed':
            return 'FAILED'
        return s.upper() if s else '-'
    
    def get_total_cases(self, obj):
        summary = obj.summary or {}
        return summary.get('total_steps', summary.get('total', 0))
    
    def get_failed_cases(self, obj):
        summary = obj.summary or {}
        return summary.get('failed_steps', summary.get('failed', 0))
    
    def get_skipped_cases(self, obj):
        return 0
    
    def get_pass_rate(self, obj):
        summary = obj.summary or {}
        total = summary.get('total_steps', summary.get('total', 0))
        passed = summary.get('passed_steps', summary.get('passed', 0))
        if total > 0:
            return round(passed / total * 100, 1)
        return 0
    
    def get_duration(self, obj):
        summary = obj.summary or {}
        ms = summary.get('execution_time', 0)
        return round(ms / 1000, 2) if ms else 0
