@echo off
REM Dispute Resolution System - Windows Shutdown Script
REM This script stops all running services

echo ========================================
echo Stopping Dispute Resolution System
echo ========================================
echo.

echo Stopping processes on port 8000 (Backend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping processes on port 8001 (MCP HTTP Server)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8001') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo Stopping processes on port 3000 (Frontend)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do (
    taskkill /F /PID %%a >nul 2>&1
)

echo.
echo All services stopped.
echo.
pause
