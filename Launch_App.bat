@echo off
title Abaad ERP v4.0 - 3D Print Manager
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
echo.
echo  =============================================
echo     ABAAD ERP v4.0 - 3D Print Manager
echo  =============================================
echo.
echo  Starting application...
echo.
venv\Scripts\python.exe main.py

:: If error, show message
if errorlevel 1 (
    echo.
    echo [ERROR] Application crashed or closed with error.
    echo.
    pause
)
