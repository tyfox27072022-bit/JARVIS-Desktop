@echo off
setlocal EnableExtensions
cd /d "%~dp0"
echo Installing JARVIS core deps (no C++ compiler)...
python -m pip install --upgrade pip wheel setuptools
python -m pip install "PySide6>=6.8" "pyinstaller>=6.11" "requests>=2.32" "psutil>=6.1" "pyautogui>=0.9.54" "Pillow>=10.0"
echo.
echo Optional llama-cpp-python (safe to fail on Python 3.14):
python -m pip install llama-cpp-python --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
echo.
echo Done. Run MAKE_EXE.bat next.
pause
