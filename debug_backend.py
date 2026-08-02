import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

try:
    from apps.executions.views import K8sRunnerViewSet
    from apps.executions.k8s_service import K8sExecutionManager
    print("Imports successful!")
    runners = K8sExecutionManager.list_runners()
    print(f"Runners: {runners}")
except Exception as e:
    import traceback
    traceback.print_exc()
