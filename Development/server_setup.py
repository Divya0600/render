#!/usr/bin/env python3
"""
Simple Server Setup for Internet-Connected Machine
Direct installation without emoji characters
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def install_package(package):
    """Install a Python package"""
    try:
        print(f"Installing {package}...")
        subprocess.run([sys.executable, "-m", "pip", "install", package], 
                      check=True, capture_output=True, text=True)
        print(f"Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Failed to install {package}: {e}")
        return False

def install_dependencies():
    """Install all required dependencies"""
    print("Installing dependencies...")
    
    # Base packages
    packages = [
        "PyQt5>=5.15.0",
        "requests>=2.25.0", 
        "psutil>=5.8.0",
        "aiofiles>=0.8.0",
        "paramiko>=2.7.0",
        "pywinrm>=0.4.0"
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"Installed {success_count}/{len(packages)} packages successfully")
    return success_count == len(packages)

def create_server_config():
    """Create server configuration"""
    config = {
        "port": 8080,
        "host": "",
        "auto_start_workers": True,
        "database_path": "render_farm.db"
    }
    
    with open("server_config.json", "w") as f:
        import json
        json.dump(config, f, indent=2)
    
    print("Created server_config.json")

def create_startup_script():
    """Create startup script"""
    if platform.system() == "Windows":
        script_content = f'''@echo off
title Render Farm Server
echo Starting Render Farm Server...
cd /d "{os.getcwd()}"
python main_app.py
pause
'''
        with open("start_server.bat", "w") as f:
            f.write(script_content)
        print("Created start_server.bat")
    else:
        script_content = f'''#!/bin/bash
echo "Starting Render Farm Server..."
cd "{os.getcwd()}"
python3 main_app.py
'''
        with open("start_server.sh", "w") as f:
            f.write(script_content)
        os.chmod("start_server.sh", 0o755)
        print("Created start_server.sh")

def main():
    """Main setup process"""
    print("=" * 50)
    print("Render Farm Server Setup")
    print("=" * 50)
    print()
    
    # Check Python version
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        return False
    
    print(f"Python version: {sys.version.split()[0]} - OK")
    print()
    
    # Install dependencies
    print("Step 1: Installing dependencies...")
    if not install_dependencies():
        print("WARNING: Some packages failed to install")
        print("You may need to install them manually")
    print()
    
    # Create configuration
    print("Step 2: Creating configuration...")
    create_server_config()
    print()
    
    # Create startup script
    print("Step 3: Creating startup script...")
    create_startup_script()
    print()
    
    # Final instructions
    print("=" * 50)
    print("SERVER SETUP COMPLETE!")
    print("=" * 50)
    print()
    print("To start the server:")
    if platform.system() == "Windows":
        print("  1. Double-click start_server.bat")
        print("  2. Or run: python main_app.py")
    else:
        print("  1. Run: ./start_server.sh") 
        print("  2. Or run: python3 main_app.py")
    print()
    print("Server will be available at:")
    print("  - Main App: Desktop application")
    print("  - Web Interface: http://localhost:8080")
    print()
    print("To create offline packages for workers:")
    print("  Run: python offline_package_downloader.py")
    print()
    
    return True

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup cancelled by user")
    except Exception as e:
        print(f"\nSetup failed: {e}")
        print("You can try running: python setup_installer.py")