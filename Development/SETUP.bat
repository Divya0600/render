@echo off
title Render Farm Professional Setup v2.0

echo.
echo ========================================
echo   🎬 Render Farm Professional Setup
echo ========================================
echo.

echo Choose installation method:
echo.
echo [1] Quick Install (Development)
echo [2] Build Professional Installer
echo [3] Exit
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" goto quickinstall
if "%choice%"=="2" goto buildinstaller  
if "%choice%"=="3" goto exit
goto invalid

:quickinstall
echo.
echo 🚀 Starting Quick Installation...
echo.
python setup_installer.py
goto end

:buildinstaller
echo.
echo 🏗️ Building Professional Installer...
echo.
python build_installer.py
goto end

:invalid
echo.
echo ❌ Invalid choice. Please enter 1, 2, or 3.
pause
goto start

:exit
echo.
echo 👋 Goodbye!
goto end

:end
echo.
echo ✅ Setup complete!
pause