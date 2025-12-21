@echo off
title Abaad 3D Print Manager v4.0
color 0B

:: Change to script directory
cd /d "%~dp0"

:: Check if venv exists
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [!] Virtual environment not found!
    echo     Please run SETUP.bat first.
    echo.
    pause
    exit /b 1
)

:: Run with virtual environment
echo Starting Abaad 3D Print Manager v4.0...
echo.
venv\Scripts\python.exe main.py

:: If error, show message
if errorlevel 1 (
    echo.
    echo [ERROR] Application crashed or closed with error.
    echo.
    pause
)
