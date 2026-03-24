#!/bin/bash
echo "========================================="
echo "   Starting TestHub Platform Services"
echo "========================================="

# Change to script directory
cd "$(dirname "$0")"

echo "[1/3] Starting Frontend (Port 5656)..."
cd frontend
npm run dev -- --port 5656 &
PID_FRONTEND=$!
cd ..

echo "[2/3] Starting Backend (Port 4545)..."
venv_py311/bin/python manage.py runserver 0.0.0.0:4545 &
PID_BACKEND=$!

echo "[3/3] Starting Django-Q2 Worker..."
venv_py311/bin/python manage.py qcluster &
PID_QCLUSTER=$!

echo "========================================="
echo "All services started!"
echo "Press Ctrl+C to stop all services."
echo "========================================="

# Trap Ctrl+C to kill all background processes
trap "echo 'Stopping services...'; kill $PID_FRONTEND $PID_BACKEND $PID_QCLUSTER; exit" EXIT

# Wait for processes
wait
