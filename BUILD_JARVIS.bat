@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not defined JARVIS_BUILD_WRAPPED (
  set JARVIS_BUILD_WRAPPED=1
  cmd /k "%~f0"
  exit /b
)

echo ========================================
echo  JARVIS - Build Windows Desktop App
echo  Output: dist\JARVIS\JARVIS.exe
echo ========================================
echo.

> build_log.txt echo JARVIS build log
>> build_log.txt echo Started: %DATE% %TIME%

where python >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python not found.
  echo Install Python 3.11 or 3.12 from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH", then run this again.
  >> build_log.txt echo ERROR: Python not found
  goto :end
)

python --version
python --version >> build_log.txt 2>&1

echo.
echo [1/4] pip...
python -m pip install --upgrade pip wheel setuptools >> build_log.txt 2>&1

echo.
echo [2/4] Desktop packages...
python -m pip install "PySide6>=6.8" "pyinstaller>=6.11" "requests>=2.32" "psutil>=6.1" "pyautogui>=0.9.54" "Pillow>=10.0" "discord.py>=2.4" >> build_log.txt 2>&1
if errorlevel 1 (
  echo ERROR: packages failed. Open build_log.txt
  goto :end
)

echo.
echo [3/4] Optional local AI wheel...
python -m pip install llama-cpp-python --only-binary=:all: --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu >> build_log.txt 2>&1
if errorlevel 1 (
  echo Note: no llama-cpp wheel - CLI backend will be used. OK.
)

echo.
echo [4/4] PyInstaller JARVIS.exe...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist JARVIS.spec del /q JARVIS.spec

python -m PyInstaller --noconfirm --clean --windowed --onedir --name JARVIS ^
  --paths . ^
  --add-data "config;config" ^
  --hidden-import jarvis ^
  --hidden-import jarvis.main ^
  --hidden-import jarvis.ai.brain ^
  --hidden-import jarvis.ai.agent ^
  --hidden-import jarvis.ai.local_engine ^
  --hidden-import jarvis.ai.cli_engine ^
  --hidden-import jarvis.ai.model_manager ^
  --hidden-import jarvis.ai.model_catalog ^
  --hidden-import jarvis.ai.hardware ^
  --hidden-import jarvis.ai.tools ^
  --hidden-import jarvis.ai.cloud_optional ^
  --hidden-import jarvis.ai.intent ^
  --hidden-import jarvis.memory.store ^
  --hidden-import jarvis.pc.controller ^
  --hidden-import jarvis.pc.organize ^
  --hidden-import jarvis.vault.library ^
  --hidden-import jarvis.web.search ^
  --hidden-import jarvis.voice.engine ^
  --hidden-import jarvis.coding.workspace ^
  --hidden-import jarvis.discord.bot ^
  --hidden-import jarvis.discord.support ^
  --hidden-import jarvis.phone.api ^
  --hidden-import jarvis.security.audit ^
  --hidden-import jarvis.updates.improve ^
  --hidden-import jarvis.config ^
  --hidden-import jarvis.paths ^
  --collect-all PySide6 ^
  --collect-all shiboken6 ^
  jarvis\main.py >> build_log.txt 2>&1

if errorlevel 1 (
  echo ERROR: PyInstaller failed. Open build_log.txt
  goto :end
)

if not exist "dist\JARVIS\JARVIS.exe" (
  echo ERROR: dist\JARVIS\JARVIS.exe was not created.
  goto :end
)

if not exist "dist\JARVIS\config" mkdir "dist\JARVIS\config"
copy /Y "config\settings.json" "dist\JARVIS\config\settings.json" >nul
if not exist "dist\JARVIS\vault\scripts" mkdir "dist\JARVIS\vault\scripts"
if not exist "dist\JARVIS\data\models" mkdir "dist\JARVIS\data\models"
if not exist "dist\JARVIS\data\bin" mkdir "dist\JARVIS\data\bin"
if not exist "dist\JARVIS\workspace" mkdir "dist\JARVIS\workspace"

echo Creating Desktop shortcut...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$exe = Join-Path '%CD%' 'dist\JARVIS\JARVIS.exe'; $desk = [Environment]::GetFolderPath('Desktop'); $s = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desk 'JARVIS.lnk')); $s.TargetPath = $exe; $s.WorkingDirectory = Split-Path $exe; $s.WindowStyle = 1; $s.Description = 'JARVIS'; $s.Save(); Write-Host 'Shortcut:' (Join-Path $desk 'JARVIS.lnk')"

echo.
echo ========================================
echo  BUILD SUCCESSFUL
echo  dist\JARVIS\JARVIS.exe
echo  Desktop shortcut: JARVIS
echo ========================================
>> build_log.txt echo BUILD SUCCESSFUL
explorer "dist\JARVIS"

:end
echo.
pause
