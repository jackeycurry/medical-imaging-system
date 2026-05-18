@echo off
chcp 65001 >nul
echo ========================================
echo   Medical Records System - Docker
echo ========================================
echo.

cd /d %~dp0

echo Building and starting containers...
docker-compose up -d --build

echo.
echo ========================================
echo   Services started!
echo   Backend:   http://localhost:8000
echo   Frontend:  http://localhost:3000
echo ========================================
echo.
echo View logs: docker-compose logs -f
echo Stop:      docker-compose down
pause
