@echo off
title Abaad ERP v4.0 - Setup
color 0A

echo.
echo ========================================
echo    ABAAD 3D PRINT MANAGER v4.0
echo    Setup & Installation
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo.
    echo Please download Python from:
    echo https://www.python.org/downloads/
    echo.
    echo IMPORTANT: Check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b 1
)

echo [OK] Python found
python --version
echo.

:: Create virtual environment
echo [1/3] Creating virtual environment...
if exist "venv" (
    echo      Virtual environment already exists.
) else (
    python -m venv venv
    echo      Virtual environment created.
)
echo.

:: Activate virtual environment
echo [2/3] Activating virtual environment...
call venv\Scripts\activate.bat
echo      Activated.
echo.

:: Install dependencies
echo [3/3] Installing required libraries...
echo.
pip install --upgrade pip
pip install reportlab Pillow pytesseract
echo.

echo ========================================
echo    SETUP COMPLETE!
echo ========================================
echo.
echo To run the application:
echo    Double-click "Launch_App.bat"
echo.
echo Or manually:
echo    1. Open Command Prompt here
echo    2. Run: venv\Scripts\activate
echo    3. Run: python main.py
echo.
pause
