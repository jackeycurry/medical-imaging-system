@echo off
chcp 65001 >nul
echo ========================================
echo   Medical Records System - Startup
echo ========================================
echo.

echo [1/2] Starting Backend Server (port 8084)...
start "Backend-Server" cmd /k "call conda activate medical_image_find && cd /d D:\Project\test\second\medical-system-backend-fastapi\medical-system-backend-fastapi\medical-system-backend-fastapi && python main.py"

echo.
echo [2/2] Starting Frontend Server (port 3000)...
start "Frontend-Server" cmd /k "cd /d D:\Project\test\second\medical-system-backend-fastapi\medical-system-backend-fastapi\frontend && npm run dev"

echo.
echo ========================================
echo   Starting services...
echo   Backend:   http://localhost:8084
echo   Frontend:  http://localhost:3000
echo ========================================
echo.
echo X-ray analysis uses Qwen-VL (Alibaba Cloud DashScope)
echo Set DASHSCOPE_API_KEY environment variable before starting.
echo.
echo Close this window to stop
pause
