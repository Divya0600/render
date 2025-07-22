@echo off
title Render Farm Quick Start

echo.
echo ========================================
echo   Render Farm Quick Server Setup
echo ========================================
echo.

echo This will install the server on this machine.
echo Make sure you have internet connection.
echo.

set /p confirm="Continue with server setup? (y/n): "
if /i not "%confirm%"=="y" (
    echo Setup cancelled.
    goto end
)

echo.
echo Installing server components...
echo.

python server_setup.py

echo.
echo Setup complete! You can now:
echo 1. Run 'start_server.bat' to launch the server
echo 2. Use main_app.py for the full GUI interface
echo 3. Create offline packages with offline_package_downloader.py
echo.

:end
pause