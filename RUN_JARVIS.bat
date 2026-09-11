@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ========================================
echo  JARVIS - Start (no EXE build needed)
echo ========================================
echo Folder: %CD%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found.
  echo Install Python from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH"
  pause
  exit /b 1
)

python --version
echo Installing/checking packages...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install "PySide6>=6.8" "requests>=2.32" "psutil>=6.1" "pyautogui>=0.9.54" "Pillow>=10.0"
if errorlevel 1 (
  echo Package install failed.
  pause
  exit /b 1
)

echo.
echo Starting JARVIS...
echo If the window opens, you do not need MAKE_EXE.bat.
echo.
python -m jarvis.main
echo.
echo JARVIS closed.
pause
