@echo off
title Render Farm Worker Service Installer
echo Installing Render Farm Worker as Windows Service...
echo.

REM Get current directory
set INSTALL_DIR=%~dp0

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Get server IP from user
set /p SERVER_IP="Enter Server IP (default: localhost): "
if "%SERVER_IP%"=="" set SERVER_IP=localhost

set /p SERVER_PORT="Enter Server Port (default: 8080): "
if "%SERVER_PORT%"=="" set SERVER_PORT=8080

echo.
echo Creating service for server: %SERVER_IP%:%SERVER_PORT%
echo Install directory: %INSTALL_DIR%

REM Create service wrapper script
echo @echo off > "%INSTALL_DIR%worker_service.bat"
echo cd /d "%INSTALL_DIR%" >> "%INSTALL_DIR%worker_service.bat"
echo python worker_node.py --server http://%SERVER_IP%:%SERVER_PORT% >> "%INSTALL_DIR%worker_service.bat"

REM Create the service
sc create RenderFarmWorker binPath= "\"%INSTALL_DIR%worker_service.bat\"" start= auto DisplayName= "Render Farm Worker"

if %errorLevel% equ 0 (
    echo.
    echo ✓ Service created successfully!
    echo.
    echo Starting service...
    sc start RenderFarmWorker
    
    if %errorLevel% equ 0 (
        echo ✓ Service started successfully!
        echo.
        echo The Render Farm Worker will now:
        echo - Start automatically when Windows boots
        echo - Run in the background
        echo - Connect to %SERVER_IP%:%SERVER_PORT%
        echo.
        echo To manage the service:
        echo - Stop: sc stop RenderFarmWorker
        echo - Start: sc start RenderFarmWorker  
        echo - Remove: sc delete RenderFarmWorker
    ) else (
        echo ⚠ Service created but failed to start
        echo You can start it manually: sc start RenderFarmWorker
    )
) else (
    echo ✗ Failed to create service
    echo Make sure you're running as Administrator
)

echo.
echo Service installation complete!
pause