@echo off
REM aotutest 本地部署启动脚本（Windows）
REM 前端 8787 / 后端 8686；venv 在 E:\evi\aotutest（不在项目目录内）。
REM 注意：gunicorn 在 Windows 不可用（依赖 fcntl），后端用 runserver（同 venv 内）。
REM 前端 vite 已配置 dev server 端口 8787，并将 /api、/media 代理到 http://localhost:8686。

set FIELD_ENCRYPTION_KEY=dtYMyxpT7jz36T2cR1fwSHh3nmbF-rkimaNEO81uBuE=
set DJANGO_SETTINGS_MODULE=backend.settings
set DEBUG=True
set SECRET_KEY=local-deploy-secret-key-not-for-prod-8786

cd /d %~dp0

start "aotutest-backend" E:\evi\aotutest\Scripts\python.exe manage.py runserver 0.0.0.0:8686 --noreload
cd frontend
start "aotutest-frontend" npm run dev

echo.
echo 后端:  http://localhost:8686  (admin: http://localhost:8686/admin/)
echo 前端:  http://localhost:8787
echo 登录账号 admin / admin123456 （已归属 default-org 且开通 AGENT_EVAL）
echo 按任意键关闭本窗口（服务仍在各自窗口运行）...
pause >nul
