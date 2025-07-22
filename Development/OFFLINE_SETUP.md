# 🔌 Offline Installation Guide

## For Windows Machines Without Internet

### Step 1: Create Offline Package (On Internet-Connected Machine)

```cmd
# Run this on a machine WITH internet
create_offline_package.bat
```

Or manually:
```cmd
python offline_package_downloader.py
```

This creates an `offline_packages` folder containing:
- All Python packages as wheel files
- Offline installer script
- Setup files

### Step 2: Transfer to Target Machine

1. Copy the entire `offline_packages` folder to your worker machine
2. Use USB drive, network share, or any file transfer method

### Step 3: Install on Offline Machine

```cmd
# On the worker machine (no internet needed)
cd offline_packages
python install_offline.py
```

### Step 4: Run Setup

```cmd
# After offline packages are installed
python setup_installer.py
```

## What Gets Downloaded

### Base Packages (All Installations)
- PyQt5 - GUI framework
- requests - HTTP client
- psutil - System monitoring  
- aiofiles - Async file operations

### Server Packages (Server Only)
- paramiko - SSH for worker deployment
- pywinrm - Windows remote management

### Windows Packages (Windows Only)  
- pywin32 - Windows API access
- winshell - Windows shortcuts

## Portable Python Option

For machines without Python:

1. Download Python Embeddable Package:
   - Go to python.org/downloads
   - Get "Windows embeddable package (64-bit)"
   - Extract to `offline_packages/python/`

2. Download get-pip.py:
   - Get from bootstrap.pypa.io/get-pip.py
   - Save to `offline_packages/get-pip.py`

The installer will automatically detect and use portable Python.

## File Structure

```
offline_packages/
├── wheels/              # Python packages
├── python/              # Portable Python (optional)
├── get-pip.py          # pip installer (optional)
├── install_offline.py  # Offline installer
├── setup_installer.py  # Main setup
├── worker_node.py      # Worker application
├── manifest.json       # Package info
└── README.txt         # Instructions
```

## Troubleshooting

### "No module named pip"
- Install portable Python with get-pip.py
- Or install Python normally on target machine

### "Failed to install packages"  
- Check wheel files are present in wheels/ folder
- Verify Python version compatibility
- Try running as administrator

### "Import errors after installation"
- Restart command prompt/terminal
- Check Python PATH environment variable
- Try `python -m pip list` to verify installations

## Verification

After successful installation:
```cmd
python -c "import PyQt5; print('PyQt5 OK')"
python -c "import requests; print('Requests OK')"  
python -c "import psutil; print('Psutil OK')"
```

## Quick Commands

```cmd
# Create offline package (internet machine)
create_offline_package.bat

# Install offline (target machine)  
cd offline_packages
python install_offline.py
python setup_installer.py

# Choose "Worker" installation
# Enter server IP address
# Complete installation
```

---
**Perfect for air-gapped networks and secure environments!**