
import subprocess
import sys

def check_screenshot(device_id):
    print(f"Checking screenshot for {device_id}...")
    
    # Method 1: exec-out
    print("Trying exec-out...")
    try:
        cmd = ['adb', '-s', device_id, 'exec-out', 'screencap', '-p']
        result = subprocess.run(cmd, capture_output=True)
        print(f"exec-out return code: {result.returncode}")
        print(f"exec-out stdout len: {len(result.stdout)}")
        print(f"exec-out stderr: {result.stderr}")
        if len(result.stdout) > 0:
            print(f"Header: {result.stdout[:10]}")
    except Exception as e:
        print(f"exec-out failed: {e}")

    # Method 2: shell
    print("\nTrying shell...")
    try:
        cmd = ['adb', '-s', device_id, 'shell', 'screencap', '-p']
        result = subprocess.run(cmd, capture_output=True)
        print(f"shell return code: {result.returncode}")
        print(f"shell stdout len: {len(result.stdout)}")
        if len(result.stdout) > 0:
            print(f"Header: {result.stdout[:10]}")
            
            # Check for CRLF corruption
            if b'\r\n' in result.stdout[:20]:
                print("Detected CRLF in header")
            if b'\r\r\n' in result.stdout[:20]:
                print("Detected CRCRLF in header")
                
    except Exception as e:
        print(f"shell failed: {e}")

if __name__ == "__main__":
    check_screenshot("127.0.0.1:7555")
