import sys
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.scheduler.models import ScheduledTask
from apps.scheduler.tasks import execute_scheduled_task

print("Triggering REAL Scheduled Tasks to Generate Execution Reports...")

try:
    tasks = ScheduledTask.objects.filter(name__icontains="System Task:")
    if not tasks.exists():
        print("[ERROR] No scheduled tasks found to execute.")
        sys.exit(1)

    for task in tasks:
        print(f"\n-> Executing Task: {task.name} (ID: {task.id})")
        print("This will natively run the bound TestSuite and automatically fire the Feishu webhook upon completion.")
        execute_scheduled_task(task.id)
        print(f"<- Completed executing {task.name}!")

    print("\n[SUCCESS] Authentic Test Executions completed! Check 'Test Reports' in the UI!")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[ERROR] Failed to execute tasks: {str(e)}")
