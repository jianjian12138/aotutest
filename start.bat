@echo off
echo =========================================
echo    Starting TestHub Platform Services
echo =========================================

:: Ensure we are in the project root
cd /d "%~dp0"

echo [1/3] Starting Frontend (Port 5656)...
start "TestHub Frontend" cmd /k "cd frontend && npm run dev -- --port 5656"

echo [2/3] Starting Backend (Port 4545)...
start "TestHub Backend" cmd /k "venv_py311\Scripts\python manage.py runserver 0.0.0.0:4545"

echo [3/3] Starting Django-Q2 Worker...
start "TestHub Task Worker" cmd /k "venv_py311\Scripts\python manage.py qcluster"

echo.
echo All services are launching in separate windows!
echo Please check the new terminal windows for logs.
echo =========================================
pause
