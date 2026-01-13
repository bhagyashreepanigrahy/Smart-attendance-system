@echo off
title Flask Server Emergency Restart
echo ========================================
echo 🚨 EMERGENCY FLASK SERVER RESTART 🚨
echo ========================================
echo.

echo 🔪 Step 1: Killing ALL Python processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
echo ✅ Python processes killed

echo.
echo 🧹 Step 2: Clearing Python cache...
if exist "__pycache__" (
    rmdir /s /q "__pycache__"
    echo ✅ Removed __pycache__ directory
)
del /s /q *.pyc >nul 2>&1
echo ✅ Cache cleared

echo.
echo ⏳ Step 3: Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo.
echo 🚀 Step 4: Starting Flask server...
echo 📍 Current directory: %CD%
echo 🌐 Server will be at: http://localhost:5000
echo.

start "Flask Server - FRESH START" cmd /k "echo Flask Server Starting... && python app.py"

echo.
echo ✅ SERVER RESTARTED WITH FRESH MODULES!
echo 🌐 Visit: http://localhost:5000/online_attendance
echo ⏰ Wait 5-10 seconds for server to fully load
echo.
echo 🎯 The error should now be FIXED!
echo.
pause