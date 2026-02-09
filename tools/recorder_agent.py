import os
import sys
import json
import subprocess
import requests
import argparse
import time

def run_codegen(url=None, channel=None):
    """
    运行 Playwright Codegen 并捕获输出
    """
    output_file = "recorded_script.py"
    
    def execute_cmd(use_channel=None):
        cmd = ["playwright", "codegen"]
        if url:
            cmd.append(url)
        if use_channel:
            cmd.extend(["--channel", use_channel])
        cmd.extend(["-o", output_file])
        
        print(f"Starting recorder: {' '.join(cmd)}")
        print("请在弹出的浏览器中进行操作。关闭浏览器或终端以结束录制。")
        return subprocess.run(cmd, check=True)

    try:
        execute_cmd(channel)
    except subprocess.CalledProcessError as e:
        print(f"Error running codegen: {e}")
        
        # Windows下自动重试 Edge
        if not channel and sys.platform == 'win32':
            print("\n⚠️ 检测到 Chromium 启动失败 (可能是缺失 DLL 依赖)。")
            print("🔄 正在尝试使用系统 Microsoft Edge 浏览器重试...")
            try:
                execute_cmd("msedge")
            except subprocess.CalledProcessError as e2:
                print(f"❌ Edge 启动也失败了: {e2}")
                return None
        else:
            print("\n--- Troubleshooting ---")
            print("If you see 'Failed to load Chrome DLL' or similar browser launch errors, try running:")
            print("    playwright install chromium")
            print("    # Or if you need system dependencies:")
            print("    playwright install-deps")
            return None
    except FileNotFoundError:
        print("Error: 'playwright' command not found. Please ensure it is installed:")
        print("    pip install playwright")
        print("    playwright install")
        return None
        
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            code = f.read()
        # 清理
        os.remove(output_file)
        return code
    return None

def upload_record(server_url, token, project_id, code, name):
    """
    上传录制代码到服务器
    """
    api_url = f"{server_url.rstrip('/')}/api/ui/testcases/upload_record/"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "project_id": project_id,
        "code": code,
        "name": name
    }
    
    try:
        response = requests.post(api_url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 录制上传成功! 用例ID: {data.get('case_id')}")
            print(f"包含步骤数: {data.get('steps_count')}")
        else:
            print(f"❌ 上传失败: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ 连接服务器失败: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="UI Automation Recorder Agent")
    parser.add_argument("--server", required=True, help="Server URL (e.g. http://localhost:8000)")
    parser.add_argument("--token", required=True, help="User API Token")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--url", help="Target URL to start recording")
    parser.add_argument("--channel", help="Browser channel (e.g. msedge, chrome)")
    parser.add_argument("--name", default=f"录制用例_{int(time.time())}", help="Test Case Name")
    
    args = parser.parse_args()
    
    # 1. Start Recording
    code = run_codegen(args.url, args.channel)
    
    if code:
        print("\n--- Captured Code ---")
        print(code)
        print("---------------------\n")
        
        # 2. Upload
        upload_record(args.server, args.token, args.project, code, args.name)
    else:
        print("No code captured.")
