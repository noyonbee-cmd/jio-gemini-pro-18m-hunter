@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Jio Gemini 18-Month Hunter Bot
color 0b

echo ================================================================
echo        JIO GEMINI 18-MONTH HUNTER BOT - 1-CLICK LAUNCHER
echo ================================================================
echo.

if exist "venv\Scripts\python.exe" (
    echo [*] Starting Jio Gemini Hunter Bot with live terminal logs...
    echo.
    venv\Scripts\python.exe -u bot.py
    goto :DONE
)

if exist "..\pixel offer\venv\Scripts\python.exe" (
    echo [*] Starting Jio Gemini Hunter Bot using pixel offer environment...
    echo.
    "..\pixel offer\venv\Scripts\python.exe" -u bot.py
    goto :DONE
)

where.exe python >nul 2>nul
if %errorlevel% equ 0 (
    echo [*] Starting Jio Gemini Hunter Bot using system python...
    echo.
    python -u bot.py
    goto :DONE
)

echo [X] Python was not found on your system!
echo Please install Python 3.10+ from https://www.python.org/

:DONE
echo.
echo ================================================================
echo  Bot process terminated.
echo ================================================================
pause
