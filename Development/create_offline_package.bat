@echo off
title Create Offline Package for Render Farm

echo.
echo ===============================================
echo   🎬 Render Farm Offline Package Creator
echo ===============================================
echo.

echo This will create an offline installation package
echo for machines without internet access.
echo.

echo Requirements:
echo - Internet connection (for downloading packages)
echo - Python with pip installed
echo.

set /p confirm="Continue? (y/n): "
if /i not "%confirm%"=="y" (
    echo Cancelled.
    goto end
)

echo.
echo 📦 Creating offline package...
echo.

python offline_package_downloader.py

echo.
echo ✅ Offline package creation complete!
echo.
echo 📋 Next steps:
echo 1. Copy the 'offline_packages' folder to your target machine
echo 2. On target machine, run: cd offline_packages
echo 3. Then run: python install_offline.py
echo 4. Finally run: python setup_installer.py
echo.

:end
pause