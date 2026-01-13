@echo off
REM Flask Server Restart Script for Windows
REM This script will properly restart your Flask server with fresh module loading

echo 🔄 Restarting Flask Server with Module Reload...
echo.

REM Kill any existing Flask processes
echo Stopping existing Flask processes...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq *app.py*" 2>nul
taskkill /F /IM python.exe /FI "COMMANDLINE eq *app.py*" 2>nul
timeout /t 2 /nobreak >nul

REM Clear Python cache
echo Clearing Python cache files...
if exist "__pycache__" rmdir /s /q "__pycache__"
del /s /q "*.pyc" 2>nul

REM Start the restart script
echo Starting Flask server with module reload...
echo.
python simple_restart.py

echo.
echo Press any key to exit...
pause >nul
