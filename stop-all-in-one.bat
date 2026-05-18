@echo off
chcp 65001 >nul
echo Stopping container...
docker stop medical-system
docker rm medical-system
echo Done.
pause
