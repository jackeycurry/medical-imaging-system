@echo off
chcp 65001 >nul
echo ========================================
echo   Stopping Docker containers...
echo ========================================
cd /d %~dp0
docker-compose down
echo Done.
pause
