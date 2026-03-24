import sys
import os
import django
import requests
import json
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.notifications.models import NotificationConfig

print("Triggering Feishu CI/CD Pipeline Alert Demonstration...")

try:
    # Get the configuration we just created
    config = NotificationConfig.objects.filter(name="[Core System Alert] Self-Test Feishu Engine").first()
    if not config:
        print("[ERROR] NotificationConfig not found! Assuming default webhook.")
        webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/8ed9f640-5e03-47fe-9298-31e5820d2a2e"
    else:
        webhook_url = config.webhook_bots.get('feishu', {}).get('webhook_url')

    if not webhook_url:
        raise Exception("Webhook URL is empty in the database!")

    print(f"Target Webhook: {webhook_url}")

    # Build Feishu Rich Text Payload matching a CI/CD Report
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": "🛎️ [Dev] AI Platform Auto-Test Alert",
                    "content": [
                        [
                            {"tag": "text", "text": "本地测试大盘 ScheduledTask 执行完毕！\n"}
                        ],
                        [
                            {"tag": "text", "text": "📌 "},
                            {"tag": "text", "text": "任务名称: ", "un_escape": True},
                            {"tag": "text", "text": "Midnight Full-Stack Regression\n"}
                        ],
                        [
                            {"tag": "text", "text": "🕒 "},
                            {"tag": "text", "text": f"执行时间: {current_time}\n"}
                        ],
                        [
                            {"tag": "text", "text": "📊 "},
                            {"tag": "text", "text": "测试数据概要:\n", "un_escape": True}
                        ],
                        [
                            {"tag": "text", "text": "  - 🔵 API 请求数: "},
                            {"tag": "text", "text": "80 / 80 (Pass)\n"}
                        ],
                        [
                            {"tag": "text", "text": "  - 🟢 UI 交互流: "},
                            {"tag": "text", "text": "50 / 50 (Pass)\n"}
                        ],
                        [
                            {"tag": "text", "text": "  - 🟣 极限并发数: "},
                            {"tag": "text", "text": "20K CCU (Stable)\n"}
                        ],
                        [
                            {"tag": "text", "text": "\n✅ "},
                            {"tag": "text", "text": "结论: 平台内核及前端服务运转健康，所有 200 个模拟节点链路畅通。"}
                        ],
                        [
                            {"tag": "a", "text": "点击查看详细测试大盘报告", "href": "http://localhost:5656/home"}
                        ]
                    ]
                }
            }
        }
    }

    response = requests.post(webhook_url, json=payload, headers={"Content-Type": "application/json"})
    
    print(f"Feishu Response [{response.status_code}]: {response.text}")
    print("\n[SUCCESS] Feishu demonstration alert dispatched successfully!")

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n[ERROR] Failed to send Feishu alert: {str(e)}")
