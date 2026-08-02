import os
import json
import subprocess
import shutil
import tempfile
import logging
import time
from django.utils import timezone
from .models import PerformanceTestExecution, PerformanceTestSuiteRequest

logger = logging.getLogger(__name__)

class LocustService:
    @staticmethod
    def execute_test_suite(test_suite, execution, concurrency, duration, worker_count=0):
        """
        Execute a performance test suite using Locust.
        
        Args:
            test_suite: PerformanceTestSuite instance
            execution: PerformanceTestExecution instance
            concurrency: Number of users
            duration: Duration in seconds
            worker_count: Number of worker processes (0 for standalone)
        """
        try:
            # 1. Prepare Locust script
            locust_script = LocustService._generate_locust_script(test_suite)
            
            # 2. Check environment
            LocustService._check_environment()
            
            # 3. Create temp directory
            temp_dir = tempfile.mkdtemp()
            script_path = os.path.join(temp_dir, 'locustfile.py')
            results_path = os.path.join(temp_dir, 'results.json')
            report_path = os.path.join(temp_dir, 'report.html')
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(locust_script)
            
            # 4. Build command
            cmd = [
                'locust',
                '-f', script_path,
                '--headless',
                '-u', str(concurrency),
                '-r', str(concurrency // 2 if concurrency > 1 else 1),
                '--run-time', f'{duration}s',
                '--json',
                '--html', report_path
            ]
            
            # Distributed mode configuration
            master_process = None
            worker_processes = []
            
            if worker_count > 0:
                # Master
                cmd.extend(['--master', '--expect-workers', str(worker_count)])
                
                # Start Master
                logger.info(f"Starting Locust Master: {' '.join(cmd)}")
                master_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir
                )
                
                # Start Workers
                worker_cmd = ['locust', '-f', script_path, '--worker']
                for i in range(worker_count):
                    logger.info(f"Starting Locust Worker {i+1}")
                    p = subprocess.Popen(
                        worker_cmd,
                        stdout=subprocess.PIPE, # Or None to inherit
                        stderr=subprocess.PIPE,
                        cwd=temp_dir
                    )
                    worker_processes.append(p)
                
                # Wait for Master to finish
                stdout, stderr = master_process.communicate()
                
                # Kill workers
                for p in worker_processes:
                    if p.poll() is None:
                        p.terminate()
            else:
                # Standalone
                cmd.extend(['--out', results_path.replace('.json', '')]) # --out prefix for json/html/csv
                
                logger.info(f"Starting Locust Standalone: {' '.join(cmd)}")
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=temp_dir
                )
                stdout, stderr = process.communicate()
            
            # 5. Process Results
            # Note: In distributed mode, results might be saved differently or need --csv/--json on master
            # Ensure --json and --html are passed to master to generate reports at the end
            
            # Check if report exists
            if os.path.exists(report_path):
                with open(report_path, 'r', encoding='utf-8') as f:
                    execution.report_html = f.read()
            
            # Check for JSON results (Locust generates [prefix]_stats.json)
            # Standalone: results_path + "_stats.json"
            # Distributed: master generates it if configured
            
            results_path # For standalone --json defaults to stdout or if --out is specified...
            # With --json, locust prints to stdout, BUT if --out is specified, it saves to files.
            # Standalone cmd has '--out'
            # Distributed master cmd also needs '--out' or '--json' behavior.
            
            # Let's adjust cmd construction above slightly to be robust.
            
            # Parse metrics
            stats_path = results_path + "_stats.json" # Default suffix when using --out
            if not os.path.exists(stats_path) and os.path.exists(results_path):
                 stats_path = results_path
            
            if os.path.exists(stats_path):
                with open(stats_path, 'r') as f:
                    stats = json.load(f)
                    # Locust JSON output is a list of dicts or a dict depending on version.
                    # Usually it's a list of stats per endpoint + 'Total'
                    
                    if isinstance(stats, list):
                        total_stats = next((item for item in stats if item.get('name') == 'Total'), {})
                        execution.total_requests = total_stats.get('num_requests', 0)
                        execution.passed_requests = total_stats.get('num_requests', 0) - total_stats.get('num_failures', 0)
                        execution.failed_requests = total_stats.get('num_failures', 0)
                        execution.response_time_avg = total_stats.get('avg_response_time', 0)
                        execution.response_time_min = total_stats.get('min_response_time', 0)
                        execution.response_time_max = total_stats.get('max_response_time', 0)
                        execution.rps = total_stats.get('current_rps', 0) or (execution.total_requests / duration)
            
            execution.status = 'COMPLETED'
            execution.end_time = timezone.now()
            execution.locust_logs = f"Stdout:\n{stdout}\n\nStderr:\n{stderr}"
            execution.save()
            
            # Cleanup
            shutil.rmtree(temp_dir, ignore_errors=True)
            
        except Exception as e:
            logger.error(f"Locust execution failed: {e}")
            execution.status = 'FAILED'
            execution.end_time = timezone.now()
            execution.locust_logs = str(e)
            execution.save()
            raise e

    @staticmethod
    def _check_environment():
        try:
            subprocess.run(['locust', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise EnvironmentError("Locust is not installed or not in PATH. Please install it with 'pip install locust'.")

    @staticmethod
    def _generate_locust_script(test_suite):
        requests = PerformanceTestSuiteRequest.objects.filter(
            test_suite=test_suite,
            enabled=True
        ).order_by('order')
        
        script = [
            "import json",
            "import time",
            "import re",
            "from locust import HttpUser, task, between, events",
            "from faker import Faker",
            "",
            "fake = Faker('zh_CN')",
            "",
            "def resolve_vars(text):",
            "    if not isinstance(text, str): return text",
            "    # Resolve dynamic variables",
            "    def repl(match):",
            "        var_name = match.group(1).strip()",
            "        if var_name == '$timestamp': return str(int(time.time() * 1000))",
            "        if var_name.startswith('$faker.'):",
            "            method_name = var_name[7:]",
            "            if hasattr(fake, method_name):",
            "                try:",
            "                    return str(getattr(fake, method_name)())",
            "                except: pass",
            "        return match.group(0)",
            "    return re.sub(r'\\{\\{\\s*([^}]+)\\s*\\}\\}', repl, text)",
            "",
            "def resolve_dict(d):",
            "    if isinstance(d, dict):",
            "        return {k: resolve_dict(v) for k, v in d.items()}",
            "    elif isinstance(d, list):",
            "        return [resolve_dict(i) for i in d]",
            "    elif isinstance(d, str):",
            "        return resolve_vars(d)",
            "    return d",
            "",
            "class WebsiteUser(HttpUser):",
            "    wait_time = between(1, 5) # Default wait time, can be overridden per task",
            ""
        ]
        
        for idx, req_link in enumerate(requests):
            req = req_link.request
            method = req.method.lower()
            url = req.url
            headers = req.headers or {}
            params = req.params or {}
            body = req.body or {}
            assertions = req.assertions or []
            
            # Escape strings for script generation
            url_str = url.replace("'", "\\'")
            
            task_def = [
                f"    @task({req_link.weight})",
                f"    def task_{idx}(self):",
                f"        url = resolve_vars('{url_str}')",
                f"        headers = resolve_dict({json.dumps(headers)})",
                f"        params = resolve_dict({json.dumps(params)})",
            ]
            
            # format headers properly
            task_def.append("        # Format headers map")
            task_def.append("        final_headers = {}")
            task_def.append("        if isinstance(headers, list):")
            task_def.append("            for h in headers:")
            task_def.append("                if isinstance(h, dict) and h.get('enabled', True) and h.get('key'):")
            task_def.append("                    final_headers[h['key']] = h.get('value', '')")
            task_def.append("        else: final_headers = headers")
            
            task_def.append("        # Format params map")
            task_def.append("        final_params = {}")
            task_def.append("        if isinstance(params, list):")
            task_def.append("            for p in params:")
            task_def.append("                if isinstance(p, dict) and p.get('enabled', True) and p.get('key'):")
            task_def.append("                    final_params[p['key']] = p.get('value', '')")
            task_def.append("        else: final_params = params")
            
            req_kwargs = "url=url, headers=final_headers, params=final_params"
            
            if method in ['post', 'put', 'patch'] and body:
                if body.get('type') == 'json':
                    task_def.append(f"        req_body = resolve_dict({json.dumps(body.get('data', {}))})")
                    req_kwargs += ", json=req_body"
                else:
                    task_def.append(f"        req_body = resolve_vars({json.dumps(body.get('data', ''))})")
                    req_kwargs += ", data=req_body"
            
            task_def.append(f"        with self.client.{method}({req_kwargs}, catch_response=True) as response:")
            task_def.append("            try:")
            
            # Generate assertions
            if assertions:
                for a_idx, assertion in enumerate(assertions):
                    a_type = assertion.get('type')
                    expected = assertion.get('expected')
                    
                    if a_type == 'status_code':
                        task_def.append(f"                if str(response.status_code) != '{expected}':")
                        task_def.append(f"                    response.failure(f'Status {{response.status_code}} != {expected}')")
                        task_def.append(f"                    return")
                        
                    elif a_type == 'contains':
                        task_def.append(f"                if '{expected}' not in response.text:")
                        task_def.append(f"                    response.failure('Text not found in response')")
                        task_def.append(f"                    return")
                        
                    elif a_type == 'json_path':
                        json_path = assertion.get('json_path', '')
                        expected_val = assertion.get('expected')
                        task_def.append("                try:")
                        task_def.append("                    resp_json = response.json()")
                        task_def.append(f"                    from jsonpath_ng import parse")
                        task_def.append(f"                    matches = parse('{json_path}').find(resp_json)")
                        task_def.append(f"                    actual = matches[0].value if matches else None")
                        task_def.append(f"                    if str(actual) != str('{expected_val}'):")
                        task_def.append(f"                        response.failure(f'JSONPath {json_path} value {{actual}} != {expected_val}')")
                        task_def.append(f"                        return")
                        task_def.append("                except Exception as e:")
                        task_def.append("                    response.failure(f'JSON parsing/path failed: {e}')")
                        task_def.append("                    return")
                        
            task_def.append("                response.success()")
            task_def.append("            except Exception as assertion_err:")
            task_def.append("                response.failure(str(assertion_err))")
                
            script.extend(task_def)
            script.append("")
            
        return "\n".join(script)
