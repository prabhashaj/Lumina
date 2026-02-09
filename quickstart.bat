@echo off
REM Quick Start Script for AI Research Teaching Agent (Windows)
REM This script sets up and runs both backend and frontend

echo ========================================
echo AI Research Teaching Agent - Quick Start
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if Node is installed
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Node.js is not installed. Please install Node.js 18+
    pause
    exit /b 1
)

echo Prerequisites check passed
echo.

REM Backend Setup
echo Setting up Backend...
cd backend

if not exist "venv" (
    echo Creating Python virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install -q -r requirements.txt

if not exist ".env" (
    echo Creating .env file...
    copy .env.example .env
    echo.
    echo WARNING: Please edit backend\.env and add your API keys!
    echo Required: OPENAI_API_KEY, TAVILY_API_KEY
    echo.
)

cd ..

REM Frontend Setup
echo.
echo Setting up Frontend...
cd frontend

if not exist "node_modules" (
    echo Installing Node dependencies...
    call npm install
)

if not exist ".env.local" (
    echo Creating .env.local file...
    copy .env.local.example .env.local
)

cd ..

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. Edit backend\.env and add your API keys
echo 2. Start the backend: cd backend && python main.py
echo 3. In a new terminal, start the frontend: cd frontend && npm run dev
echo 4. Open http://localhost:3000
echo.
echo Happy learning!
echo.
pause
