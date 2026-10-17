@echo off
chcp 65001 >nul
setlocal
title Jio Gemini Hunter - One-Command Terminal Setup
color 0B

echo ========================================================================
echo    ⚡ JIO GEMINI 18-MONTH HUNTER: ONE-COMMAND SETUP ⚡
echo ========================================================================
echo.

:: Check for Python installation
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not added to your PATH!
    echo Please install Python 3.10+ from https://www.python.org/
    pause
    exit /b 1
)

:: Create Virtual Environment if missing
if not exist "venv" (
    echo [INFO] Creating Python virtual environment (venv)...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
)

:: Install / Update Dependencies
echo [INFO] Verifying requirements...
venv\Scripts\python.exe -m pip install -q -r requirements.txt pillow

:: Run setup wizard
venv\Scripts\python.exe setup.py %*

echo.
pause
