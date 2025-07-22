# 🎬 Render Farm Professional Installer

## Quick Start

### Option 1: Development Installer (Immediate Use)
```bash
# Run the installer directly
python setup_installer.py
```

### Option 2: Build Standalone Installer
```bash
# Build professional installer executable
python build_installer.py

# Then run the generated installer
./RenderFarmInstaller/RenderFarmSetup.exe
```

## 🚀 Installation Types

### **Server Installation**
- **Purpose**: Main control and coordination hub
- **Features**: 
  - Job queue management and web interface
  - Worker coordination and monitoring  
  - Automated worker deployment
  - Central render farm control
- **Best for**: Main workstation/server machine

### **Worker Installation**  
- **Purpose**: Dedicated rendering machines
- **Features**:
  - High-performance render processing
  - Automatic job discovery and execution
  - Optimized resource utilization
  - RAM caching and async I/O
- **Best for**: Render farm worker nodes

## 📋 Installation Process

1. **Choose Installation Type**: Server or Worker
2. **Configure Settings**: Install path, server IP (for workers)
3. **Automatic Setup**: Dependencies, configuration, shortcuts
4. **Launch**: Start using immediately

## 🔧 What Gets Installed

### Dependencies
- Python packages (PyQt5, requests, psutil, aiofiles, etc.)
- SSH/WinRM libraries for remote deployment
- Performance optimization libraries

### Components
- Application files and scripts
- Configuration templates
- Desktop shortcuts and start menu entries
- Startup services (optional)

### Configuration
- **Server**: Creates server_config.json with port and database settings
- **Worker**: Creates worker_config.json with server connection details

## 🌐 Network Setup

### Single Machine (Development)
```
1. Install as Server
2. Launch application
3. Submit render jobs
```

### Multi-Machine (Production)
```
1. Install Server on main machine
2. Note server IP address (e.g., 192.168.1.100)
3. Install Workers on render machines
4. Workers automatically connect to server
```

## 🎯 Professional Features

- **GUI Installation**: Windows-style installer with progress tracking
- **Automatic Dependencies**: No manual pip install needed
- **Service Integration**: Auto-start on system boot
- **Desktop Shortcuts**: Easy application access
- **Configuration Management**: Smart default settings
- **Network Discovery**: Automatic worker detection

## 🔍 Post-Installation

### Server Machine
- Launch "Render Farm Server" from desktop
- Access web interface at http://localhost:8080
- Use "Worker Deployment" tab to manage remote workers

### Worker Machine  
- Worker automatically starts and connects to server
- Monitor status in server's "Worker Nodes" tab
- View performance metrics and job processing

## 🛠️ Advanced Options

### Custom Installation Path
- Default: `C:\Program Files\RenderFarm` (Windows)
- Default: `/opt/renderfarm` (Linux)
- Customizable during installation

### Startup Behavior
- **Auto-start service**: Starts with system boot
- **Manual start**: Launch from desktop shortcuts
- **Command line**: Direct script execution

### Configuration Files
- `server_config.json`: Server settings
- `worker_config.json`: Worker settings  
- `worker_machines.json`: Remote worker definitions

## ✅ Verification

After installation:
1. Check desktop shortcuts are created
2. Verify service starts automatically (if enabled)
3. Test server web interface accessibility
4. Confirm worker-server connectivity

## 🆘 Troubleshooting

### Common Issues
- **Permission errors**: Run installer as administrator
- **Network issues**: Check firewall settings (port 8080)
- **Dependencies**: Ensure Python 3.7+ is installed
- **Worker connection**: Verify server IP and port

### Log Files
- Installation log: Displayed during setup
- Application logs: See application directory
- Service logs: System event logs

---
**Professional VFX Render Farm v2.0**  
*Enterprise-grade distributed rendering solution*