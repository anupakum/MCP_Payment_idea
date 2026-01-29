@echo off
REM Dispute Resolution System - Windows Startup Script
REM This script starts the backend (FastAPI) and frontend (Next.js) servers

echo ========================================
echo Starting Dispute Resolution System
echo ========================================
echo.

REM Check if virtual environment exists
if not exist ".venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at .venv
    echo Please create a virtual environment first:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate
    echo   pip install -r requirements.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo Activating Python virtual environment...
call .venv\Scripts\activate.bat

REM Start MCP HTTP Server on port 8001
echo.
echo ========================================
echo Starting MCP HTTP Server on port 8001
echo ========================================
start "MCP HTTP Server" cmd /k "call .venv\Scripts\activate.bat && python -m mcp.http_server"
timeout /t 3 /nobreak >nul

REM Start FastAPI backend
echo.
echo ========================================
echo Starting FastAPI Backend on port 8000
echo ========================================
start "FastAPI Backend" cmd /k "call .venv\Scripts\activate.bat && python -m mcp.main"

REM Wait for backend to start
echo Waiting for backend to initialize...
timeout /t 5 /nobreak >nul

REM Start Next.js frontend
echo.
echo ========================================
echo Starting Next.js Frontend on port 3000
echo ========================================
start "Next.js Frontend" cmd /k "cd web && npm run dev"

echo.
echo ========================================
echo All services started!
echo ========================================
echo.
echo MCP HTTP Server: http://localhost:8001
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:3000
echo.
echo Press any key to exit this window (services will keep running)
pause >nul
