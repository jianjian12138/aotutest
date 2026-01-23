import subprocess
import re
import platform

class DeviceManager:
    @staticmethod
    def auto_connect_emulators():
        """尝试自动连接常见的模拟器端口"""
        emulator_ports = [
            ('7555', 'MuMu Emulator'),      # MuMu
            ('62001', 'Nox Emulator'),      # 夜神
            ('21503', 'MEmu Emulator'),     # 逍遥
            ('5555', 'BlueStacks/Default'), # 蓝叠/默认
        ]
        
        connected_emulators = []
        for port, name in emulator_ports:
            try:
                # 检查端口是否开放（简单的socket检查比adb connect快）
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(0.5)
                result = sock.connect_ex(('127.0.0.1', int(port)))
                sock.close()
                
                if result == 0:
                    # 端口开放，尝试ADB连接
                    print(f"Detected open port {port} ({name}), trying adb connect...")
                    cmd = ['adb', 'connect', f'127.0.0.1:{port}']
                    subprocess.run(cmd, capture_output=True, text=True, timeout=3)
                    connected_emulators.append(name)
            except Exception as e:
                # print(f"Error checking emulator {name}: {e}")
                pass
        
        return connected_emulators

    @staticmethod
    def get_android_devices():
        """获取连接的Android设备"""
        # 先尝试自动连接模拟器
        DeviceManager.auto_connect_emulators()
        
        devices = []
        try:
            # 执行adb devices命令
            result = subprocess.run(['adb', 'devices', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2:
                        device_id = parts[0]
                        status = parts[1]
                        # 解析更多信息，如model:Pixel_4
                        model = "Unknown Android"
                        for part in parts:
                            if part.startswith("model:"):
                                model = part.split(":")[1]
                            elif part.startswith("device:"):
                                if model == "Unknown Android":
                                    model = part.split(":")[1]
                        
                        devices.append({
                            'device_id': device_id,
                            'name': model,
                            'platform': 'android',
                            'type': 'emulator' if device_id.startswith('127.0.0.1') or device_id.startswith('emulator') else 'real',
                            'status': 'online' if status == 'device' else 'offline',
                            'version': '' # 获取版本需要额外命令
                        })
                        
                        # 尝试获取Android版本
                        if status == 'device':
                            try:
                                ver_res = subprocess.run(['adb', '-s', device_id, 'shell', 'getprop', 'ro.build.version.release'], capture_output=True, text=True)
                                if ver_res.returncode == 0:
                                    devices[-1]['version'] = ver_res.stdout.strip()
                            except:
                                pass
        except FileNotFoundError:
            print("ADB not found")
        except Exception as e:
            print(f"Error getting android devices: {e}")
            
        return devices

    @staticmethod
    def get_ios_devices():
        """获取连接的iOS设备"""
        devices = []
        try:
            # 检查是否安装了idevice_id
            result = subprocess.run(['idevice_id', '-l'], capture_output=True, text=True)
            if result.returncode == 0:
                ids = result.stdout.strip().split('\n')
                for device_id in ids:
                    if not device_id.strip():
                        continue
                        
                    devices.append({
                        'device_id': device_id.strip(),
                        'name': 'iOS Device', # 获取名称需要idevicename
                        'platform': 'ios',
                        'status': 'online',
                        'version': '' # 获取版本需要ideviceinfo
                    })
                    
                    # 尝试获取更多信息
                    try:
                        name_res = subprocess.run(['idevicename', '-u', device_id], capture_output=True, text=True)
                        if name_res.returncode == 0:
                            devices[-1]['name'] = name_res.stdout.strip()
                            
                        info_res = subprocess.run(['ideviceinfo', '-u', device_id, '-k', 'ProductVersion'], capture_output=True, text=True)
                        if info_res.returncode == 0:
                            devices[-1]['version'] = info_res.stdout.strip()
                    except:
                        pass
        except FileNotFoundError:
            print("libimobiledevice tools not found")
        except Exception as e:
            print(f"Error getting ios devices: {e}")
            
        return devices

    @staticmethod
    def connect_android_remote(ip, port="5555"):
        """连接远程Android设备"""
        try:
            cmd = ['adb', 'connect', f'{ip}:{port}']
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0, result.stdout
        except Exception as e:
            return False, str(e)

    @staticmethod
    def disconnect_android(device_id):
        """断开Android设备"""
        try:
            # 如果是IP:Port格式
            if ':' in device_id:
                cmd = ['adb', 'disconnect', device_id]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0, result.stdout
            return True, "Local device cannot be disconnected via command"
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_screenshot_bytes(device_id):
        """获取设备截图并返回bytes"""
        try:
            # 使用 exec-out 直接获取二进制流，避免 shell 的换行符转换问题
            # 注意：exec-out 在某些旧版本 Android/ADB 上可能不支持，但现代环境通常没问题
            cmd = ['adb', '-s', device_id, 'exec-out', 'screencap', '-p']
            result = subprocess.run(cmd, capture_output=True)
            if result.returncode == 0:
                img_data = result.stdout
                if img_data.startswith(b'\x89PNG\r\n\x1a\n'):
                    return img_data
            
            # Fallback: 如果 exec-out 失败或返回空，尝试旧方法但不做 replace
            print("Warning: exec-out failed or invalid PNG, trying shell...")
            cmd_shell = ['adb', '-s', device_id, 'shell', 'screencap', '-p']
            result_shell = subprocess.run(cmd_shell, capture_output=True)
            if result_shell.returncode == 0:
                img_data = result_shell.stdout
                # 尝试修复 Windows 下的换行符问题
                if b'\r\r\n' in img_data:
                    img_data = img_data.replace(b'\r\r\n', b'\n')
                elif b'\r\n' in img_data:
                    img_data = img_data.replace(b'\r\n', b'\n')
                return img_data
                
            return None
        except Exception as e:
            print(f"Error getting screenshot: {e}")
            return None
