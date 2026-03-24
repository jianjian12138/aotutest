import sys
import os
import django
import time
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from django.urls import get_resolver

User = get_user_model()
admin_user = User.objects.filter(is_superuser=True).first()
if not admin_user:
    admin_user = User.objects.first()

client = APIClient()
if admin_user:
    client.force_authenticate(user=admin_user)

print(f"Starting Compressive Platform Test with user: {admin_user.username if admin_user else 'Anonymous'}")

# List of essential module endpoints to test via GET
# We will cover Core, Test, API, UI, Perf, Sec, etc.
endpoints_to_test = [
    # Core & Auth
    "/api/auth/user/",
    "/api/projects/",
    "/api/users/",
    
    # API Testing
    "/api/api-projects/",
    "/api/api-collections/",
    "/api/api-requests/",
    "/api/api-test-cases/",
    
    # UI Automation
    "/api/ui-automation/projects/",
    "/api/ui-automation/elements/",
    "/api/ui-automation/test-cases/",
    "/api/ui-automation/dashboard/stats/",
    "/api/ui-automation/devices/",
    
    # Performance
    "/api/performance-testing/projects/",
    "/api/performance-testing/collections/",
    
    # Security
    "/api/strix-security/projects/",
    "/api/strix-security/configs/",
    
    # Assistant / AI
    "/api/assistant/conversations/",
    "/api/ai-cases/",
    
    # Data Factory
    "/api/data-factory/vanna-configs/",
    
    # CI/CD
    "/api/cicd/pipelines/",
    
    # Notifications
    "/api/notifications/configs/",
    
    # Scheduler
    "/api/scheduler/jobs/",
]

results = []

print("Running Full Platform Exploration...")

for ep in endpoints_to_test:
    start_time = time.time()
    try:
        response = client.get(ep, {'page_size': 10})
        duration = time.time() - start_time
        status = response.status_code
        is_success = status in [200, 201, 204]
        
        detail = ""
        if status == 200:
            data = getattr(response, 'data', {})
            if isinstance(data, dict) and 'count' in data:
                detail = f"Records found: {data['count']}"
            elif isinstance(data, list):
                detail = f"Records found: {len(data)}"
            else:
                detail = "Success"
        else:
            detail = str(getattr(response, 'data', 'Error'))[:100]
            
        results.append({
            "endpoint": ep,
            "status": status,
            "success": is_success,
            "duration": f"{duration:.3f}s",
            "detail": detail
        })
    except Exception as e:
        duration = time.time() - start_time
        results.append({
            "endpoint": ep,
            "status": "ERROR",
            "success": False,
            "duration": f"{duration:.3f}s",
            "detail": str(e)
        })

# Now perform some basic CRUD checks
print("Running Core Functional Workflows (CRUD)...")

crud_workflows = []

# 1. Create a Project
project_id = None
try:
    s = time.time()
    res = client.post("/api/projects/", {
        "name": f"Full_Volume_Test_Project_{int(s)}",
        "description": "Created by full volume automation script"
    })
    if res.status_code in [201, 200]:
        project_id = res.data.get("id")
        crud_workflows.append({"name": "Core: Create Project", "status": "Pass", "detail": f"Project ID: {project_id}"})
    else:
        crud_workflows.append({"name": "Core: Create Project", "status": "Fail", "detail": str(res.data)[:100]})
except Exception as e:
    crud_workflows.append({"name": "Core: Create Project", "status": "Fail", "detail": str(e)})

# 2. If Project created, attempt creating an API Project bound to it
if project_id:
    # Get unified subprojects API
    try:
        res = client.post("/api/api-projects/", {
            "name": f"API_Target_{project_id}",
            "base_url": "http://127.0.0.1:8000"
        })
        if res.status_code in [201, 200]:
            crud_workflows.append({"name": "API Testing: Create API Sub-Project", "status": "Pass", "detail": f"ID: {res.data.get('id')}"})
        else:
            crud_workflows.append({"name": "API Testing: Create API Sub-Project", "status": "Fail", "detail": str(res.data)[:100]})
    except Exception as e:
         crud_workflows.append({"name": "API Testing: Create API Sub-Project", "status": "Fail", "detail": str(e)})

    # UI Automation Sub-Project
    try:
        res = client.post("/api/ui-automation/projects/", {
            "name": f"UI_Target_{project_id}",
            "base_url": "http://127.0.0.1:3000"
        })
        if res.status_code in [201, 200]:
            crud_workflows.append({"name": "UI Automation: Create UI Sub-Project", "status": "Pass", "detail": f"ID: {res.data.get('id')}"})
        else:
            crud_workflows.append({"name": "UI Automation: Create UI Sub-Project", "status": "Fail", "detail": str(res.data)[:100]})
    except Exception as e:
         crud_workflows.append({"name": "UI Automation: Create UI Sub-Project", "status": "Fail", "detail": str(e)})

# Generate HTML Report
print("Generating HTML Report...")
html = f"""
<html>
<head>
    <title>Platform Full-Volume Test Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; background: #fdfdfd; color: #333; }}
        h1 {{ border-bottom: 2px solid #0056b3; padding-bottom: 10px; color: #0056b3; }}
        h2 {{ margin-top: 30px; color: #444; }}
        .summary {{ background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px; }}
        table {{ width: 100%; border-collapse: collapse; background: #fff; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f8f9fa; font-weight: 600; }}
        tr:hover {{ background-color: #f1f5f9; }}
        .Pass {{ color: #10b981; font-weight: bold; }}
        .Fail {{ color: #ef4444; font-weight: bold; }}
        .status-badge {{ padding: 4px 8px; border-radius: 4px; font-size: 0.85em; }}
        .bg-Pass {{ background-color: #d1fae5; color: #065f46; }}
        .bg-Fail {{ background-color: #fee2e2; color: #991b1b; }}
    </style>
</head>
<body>
    <h1>Platform Full-Volume Test Report</h1>
    <div class="summary">
        <p><strong>Execution Time:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
        <p><strong>Total Endpoints Scanned:</strong> {len(results)}</p>
        <p><strong>Functional Workflows Verified:</strong> {len(crud_workflows)}</p>
    </div>

    <h2>1. Module Health (Breadth API Discovery)</h2>
    <table>
        <tr>
            <th>Endpoint Module</th>
            <th>HTTP Status</th>
            <th>Duration</th>
            <th>Details</th>
        </tr>
"""

for r in results:
    s_class = "Pass" if r['success'] else "Fail"
    html += f"""
        <tr>
            <td><code>{r['endpoint']}</code></td>
            <td><span class="status-badge bg-{s_class}">{r['status']}</span></td>
            <td>{r['duration']}</td>
            <td>{r['detail']}</td>
        </tr>
    """

html += """
    </table>
    
    <h2>2. Functional Workflows (Depth Testing)</h2>
    <table>
        <tr>
            <th>Workflow Action</th>
            <th>Status</th>
            <th>Details</th>
        </tr>
"""

if not crud_workflows:
    html += "<tr><td colspan='3'>No workflows executed.</td></tr>"
for w in crud_workflows:
    html += f"""
        <tr>
            <td>{w['name']}</td>
            <td><span class="status-badge bg-{w['status']}">{w['status']}</span></td>
            <td>{w['detail']}</td>
        </tr>
    """

html += """
    </table>
</body>
</html>
"""

report_path = "d:/TEST/comprehensive_test_report.html"
with open(report_path, "w", encoding="utf-8") as f:
    f.write(html)

print(f"Report successfully generated at: {report_path}")
