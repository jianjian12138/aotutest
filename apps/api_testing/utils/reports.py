from apps.notifications.models import NotificationConfig, NotificationLog
import json
import time
import os
import shutil
import subprocess
import logging
from pathlib import Path
from django.utils import timezone
from django.conf import settings
from ..models import RequestHistory, ApiTestCaseExecution
from apps.core_platform.models import GlobalParameter
def generate_allure_report(execution, is_test_case=False):
    """
    生成Allure报告
    :param execution: ApiTestExecution 或 ApiTestCaseExecution 实例
    :param is_test_case: 是否为单条用例执行
    :return: 报告URL
    """
    try:
        execution_id = execution.id
        prefix = 'case' if is_test_case else 'suite'
        execution_folder = f"{prefix}_{execution_id}"
        
        # 创建工作目录
        results_dir = os.path.join(settings.MEDIA_ROOT, 'allure-results', execution_folder)
        report_output_dir = os.path.join(settings.MEDIA_ROOT, 'allure-reports', execution_folder)
        os.makedirs(results_dir, exist_ok=True)
        os.makedirs(report_output_dir, exist_ok=True)
        
        # 1. 生成Allure结果文件 (JSON)
        _generate_allure_results(execution, results_dir, is_test_case)
        
        # 2. 尝试运行Allure命令行工具生成生成HTML报告
        base_dir = Path(__file__).resolve().parent.parent.parent
        allure_executable = 'allure.bat' if os.name == 'nt' else 'allure'
        allure_cmd = str(base_dir / 'allure' / 'bin' / allure_executable)
        
        if not os.path.exists(allure_cmd):
            # 搜索系统路径
            allure_cmd = shutil.which('allure')
        
        report_generated = False
        if allure_cmd:
            try:
                # 清理旧报告
                if os.path.exists(report_output_dir):
                    shutil.rmtree(report_output_dir)
                os.makedirs(report_output_dir, exist_ok=True)
                
                # 生成报告
                subprocess.run([
                    allure_cmd, 'generate',
                    results_dir,
                    '--clean',
                    '--output', report_output_dir
                ], check=True, capture_output=True, text=True, timeout=30)
                report_generated = True
            except Exception as e:
                logger.warning(f"Allure command failed: {e}")
        
        # 3. 如果Allure工具不可用或失败，复制静态文件或生成回退页面
        if not report_generated:
            static_dir = os.path.join(settings.MEDIA_ROOT, 'allure-static')
            if os.path.exists(static_dir):
                shutil.copytree(static_dir, report_output_dir, dirs_exist_ok=True)
            
            # 生成简单的 index.html 导航
            if not os.path.exists(os.path.join(report_output_dir, 'index.html')):
                suite_name = execution.test_case.name if is_test_case else execution.test_suite.name
                fallback_html = f"<html><body><h1>Allure 报告生成失败</h1><p>测试对象: {suite_name}</p></body></html>"
                with open(os.path.join(report_output_dir, 'index.html'), 'w', encoding='utf-8') as f:
                    f.write(fallback_html)
        
        # 4. 生成 summary.html 供预览 (参考 views.py 逻辑)
        _generate_summary_html(execution, report_output_dir, is_test_case)
        
        return f"/media/allure-reports/{execution_folder}/summary.html"
    except Exception as e:
        logger.error(f"Generate allure report failed: {e}", exc_info=True)
        return ""


def _generate_allure_results(execution, report_dir, is_test_case=False):
    """生成Allure原始结果文件"""
    suite_name = execution.test_case.name if is_test_case else execution.test_suite.name
    project_name = "Unknown"
    
    if is_test_case:
        first_step = execution.test_case.steps.first()
        if first_step and first_step.api_request and first_step.api_request.collection:
            project_name = first_step.api_request.collection.project.name
    else:
        project_name = execution.test_suite.project.name

    # 1. Container file
    container_data = {
        "uuid": str(execution.id),
        "name": suite_name,
        "children": [f"{execution.id}-{i}" for i in range(len(execution.results or []))]
    }
    with open(os.path.join(report_dir, f'{execution.id}-container.json'), 'w', encoding='utf-8') as f:
        json.dump(container_data, f, ensure_ascii=False, indent=2)
    
    # 2. Results files
    if execution.results:
        for i, result in enumerate(execution.results):
            # Check if this is a test case result (nested steps) or a simple request result
            has_steps = result.get('type') == 'test_case'
            status_str = "passed" if (result.get('status') == 'passed' or result.get('passed')) else "failed"
            
            steps_data = []
            if has_steps:
                for step_idx, step in enumerate(result.get('results', [])):
                    steps_data.append({
                        "name": step.get('name', f"Step {step_idx + 1}"),
                        "status": "passed" if step.get('passed', False) else "failed",
                        "stage": "finished",
                        "start": int(time.time() * 1000) - 500,
                        "stop": int(time.time() * 1000),
                        "parameters": [
                            {"name": "method", "value": step.get('method', 'GET')},
                            {"name": "url", "value": step.get('url', '')}
                        ]
                    })
            
            allure_result = {
                "uuid": f"{execution.id}-{i}",
                "name": result.get('name', f'测试点 {i+1}'),
                "status": status_str,
                "stage": "finished",
                "start": int(time.time() * 1000) - 1000,
                "stop": int(time.time() * 1000),
                "description": result.get('description', ''),
                "labels": [
                    {"name": "suite", "value": suite_name},
                    {"name": "project", "value": project_name}
                ],
                "parameters": [
                    {"name": "method", "value": result.get('method', 'GET')},
                    {"name": "url", "value": result.get('url', '')}
                ],
                "steps": steps_data
            }
            
            if result.get('error'):
                allure_result["statusDetails"] = {"message": result.get('error')}
                
            with open(os.path.join(report_dir, f'{execution.id}-{i}-result.json'), 'w', encoding='utf-8') as f:
                json.dump(allure_result, f, ensure_ascii=False, indent=2)


def _generate_summary_html(execution, report_dir, is_test_case=False):
    """生成带Allure链接的概览页面"""
    suite_name = execution.test_case.name if is_test_case else execution.test_suite.name
    status_display = "通过" if (execution.status == 'passed' or execution.status == 'COMPLETED') else "失败"
    status_class = "status-passed" if status_display == "通过" else "status-failed"
    
    # 简化版 HTML 模板 (参考 views.py)
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试报告概览 - {suite_name}</title>
    <style>
        body {{ font-family: 'Segoe UI', sans-serif; margin: 0; padding: 20px; background: #f5f7fa; color: #333; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .status-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; }}
        .status-passed {{ background-color: #67c23a; }}
        .status-failed {{ background-color: #f56c6c; }}
        .allure-report-btn {{ display: inline-block; background: #409eff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; margin-top: 10px; }}
        .result-item {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 10px; border-left: 5px solid #eee; }}
        .passed {{ border-left-color: #67c23a; }}
        .failed {{ border-left-color: #f56c6c; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{suite_name} - 测试报告</h1>
        <div>状态: <span class="status-badge {status_class}">{status_display}</span></div>
        <a href="index.html" target="_blank" class="allure-report-btn">查看完整 Allure 报告</a>
    </div>
    <h2>测试明细</h2>
"""
    for res in (execution.results or []):
        is_passed = res.get('passed', False) or res.get('status') == 'passed'
        res_class = "passed" if is_passed else "failed"
        html_content += f"""
    <div class="result-item {res_class}">
        <strong>{res.get('name', '测试请求')}</strong> - {'通过' if is_passed else '失败'}
        <div>{res.get('url', '')}</div>
        {f'<div style="color:red">错误: {res.get("error")}</div>' if res.get('error') else ""}
    </div>
"""
    html_content += "</body></html>"
    
    with open(os.path.join(report_dir, 'summary.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


