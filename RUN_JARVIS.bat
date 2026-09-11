@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  JARVIS
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo Python not found — installing Python 3.12...
  winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo Could not install Python automatically.
    echo Install it from https://www.python.org/downloads/ and tick "Add python.exe to PATH"
    pause
    exit /b 1
  )
  where python >nul 2>&1
  if errorlevel 1 (
    echo Close this window, open a new one, and double-click RUN_JARVIS.bat again.
    pause
    exit /b 1
  )
)

python --version
echo Installing packages...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install "PySide6>=6.8" "requests>=2.32" "psutil>=6.1" "pyautogui>=0.9.54" "Pillow>=10.0" "discord.py>=2.4"
if errorlevel 1 (
  echo Package install failed.
  pause
  exit /b 1
)

echo.
echo Starting JARVIS...
python -m jarvis.main
echo.
echo JARVIS closed.
pause
