@echo off
title Render Farm Worker Service Uninstaller
echo Uninstalling Render Farm Worker Service...
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Stop the service first
echo Stopping service...
sc stop RenderFarmWorker

REM Delete the service
echo Removing service...
sc delete RenderFarmWorker

if %errorLevel% equ 0 (
    echo ✓ Service removed successfully!
    echo.
    echo The Render Farm Worker service has been uninstalled.
    echo You can still run it manually using Start_Worker.bat
) else (
    echo ⚠ Failed to remove service or service was not installed
)

echo.
echo Uninstall complete!
pause