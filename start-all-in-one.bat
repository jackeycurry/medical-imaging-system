@echo off
chcp 65001 >nul
echo ========================================
echo   Medical Records System - All in One
echo ========================================
echo.

cd /d %~dp0

echo Building Docker image (first time only)...
docker build -t medical-system .

echo.
echo Starting container...
docker run -d --name medical-system ^
    -e DASHSCOPE_API_KEY=%DASHSCOPE_API_KEY% ^
    -p 8000:8000 -p 3000:3000 ^
    medical-system

echo.
echo ========================================
echo   Container started!
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:3000
echo ========================================
echo.
echo View logs: docker logs -f medical-system
echo Stop:      docker stop medical-system
pause
