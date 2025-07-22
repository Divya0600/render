#!/usr/bin/env python3
"""
Offline Package Downloader for Render Farm
Downloads all required packages for offline installation
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import json
import shutil

class OfflinePackageDownloader:
    def __init__(self):
        self.packages_dir = Path("offline_packages")
        self.wheels_dir = self.packages_dir / "wheels"
        self.python_dir = self.packages_dir / "python"
        
        # Required packages for different components
        self.base_packages = [
            "PyQt5>=5.15.0",
            "requests>=2.25.0", 
            "psutil>=5.8.0",
            "aiofiles>=0.8.0"
        ]
        
        self.server_packages = [
            "paramiko>=2.7.0",
            "pywinrm>=0.4.0"
        ]
        
        # Windows-specific packages for shortcuts
        self.windows_packages = [
            "pywin32>=227",
            "winshell>=0.6"
        ]
        
        print("🔧 Offline Package Downloader for Render Farm")
        print("=" * 50)
    
    def create_directories(self):
        """Create necessary directories"""
        self.packages_dir.mkdir(exist_ok=True)
        self.wheels_dir.mkdir(exist_ok=True)
        self.python_dir.mkdir(exist_ok=True)
        print(f"✓ Created directories in {self.packages_dir}")
    
    def download_python_packages(self, package_list, target_dir):
        """Download Python packages as wheels"""
        print(f"\n📦 Downloading {len(package_list)} packages...")
        
        for package in package_list:
            print(f"  Downloading {package}...")
            try:
                # Download package and dependencies as wheels
                subprocess.run([
                    sys.executable, "-m", "pip", "download",
                    "--dest", str(target_dir),
                    "--prefer-binary",
                    package
                ], check=True, capture_output=True)
                print(f"  ✓ {package}")
                
            except subprocess.CalledProcessError as e:
                print(f"  ✗ Failed to download {package}: {e}")
    
    def download_portable_python(self):
        """Download portable Python for completely offline installation"""
        print("\n🐍 Portable Python Information:")
        print("For completely offline installation, download:")
        print("1. Python Embeddable Package from python.org")
        print("   - Windows x86-64 embeddable zip file")
        print("   - Extract to offline_packages/python/")
        print("2. get-pip.py from bootstrap.pypa.io")
        print("   - Save to offline_packages/")
        
        # Create instructions file
        instructions = """# Portable Python Setup Instructions

## For Completely Offline Installation:

1. Download Python Embeddable Package:
   - Go to https://python.org/downloads/
   - Download "Windows embeddable package (64-bit)"
   - Extract to: offline_packages/python/
   
2. Download get-pip.py:
   - Go to https://bootstrap.pypa.io/get-pip.py
   - Save as: offline_packages/get-pip.py

3. The installer will automatically use these for offline installation.

## Files included in this package:
- wheels/ : All required Python packages
- python/ : Portable Python (if downloaded)
- get-pip.py : pip installer (if downloaded)
- install_offline.py : Offline installer script
"""
        
        with open(self.packages_dir / "README.txt", "w") as f:
            f.write(instructions)
        
        print(f"✓ Instructions saved to {self.packages_dir / 'README.txt'}")
    
    def create_offline_installer(self):
        """Create offline installer script"""
        offline_installer = '''#!/usr/bin/env python3
"""
Offline Installer for Render Farm
Installs packages from local wheels without internet
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
import shutil

def install_from_wheels(wheels_dir):
    """Install packages from downloaded wheels"""
    print("🔧 Installing packages from offline wheels...")
    
    wheel_files = list(Path(wheels_dir).glob("*.whl"))
    
    if not wheel_files:
        print("❌ No wheel files found!")
        return False
    
    try:
        # Install all wheels
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--no-index",
            "--find-links", str(wheels_dir),
            "--force-reinstall"
        ] + [str(wf) for wf in wheel_files], check=True)
        
        print(f"✅ Installed {len(wheel_files)} packages")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        return False

def setup_portable_python():
    """Setup portable Python if available"""
    python_dir = Path("python")
    
    if python_dir.exists():
        print("🐍 Using portable Python...")
        
        # Add to PATH
        python_exe = python_dir / "python.exe"
        if python_exe.exists():
            os.environ["PATH"] = str(python_dir) + ";" + os.environ["PATH"]
            
            # Install pip if get-pip.py exists
            get_pip = Path("get-pip.py")
            if get_pip.exists():
                print("📦 Installing pip...")
                subprocess.run([str(python_exe), str(get_pip)], check=True)
            
            return str(python_exe)
    
    return sys.executable

def main():
    print("🎬 Render Farm Offline Installer")
    print("=" * 40)
    
    # Setup Python
    python_exe = setup_portable_python()
    
    # Install wheels
    wheels_dir = Path("wheels")
    if wheels_dir.exists():
        success = install_from_wheels(wheels_dir)
        if success:
            print("\\n✅ Offline installation complete!")
            print("\\nYou can now run:")
            print("  python setup_installer.py")
        else:
            print("\\n❌ Offline installation failed!")
            return 1
    else:
        print("❌ Wheels directory not found!")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
        
        installer_file = self.packages_dir / "install_offline.py"
        with open(installer_file, "w") as f:
            f.write(offline_installer)
        
        print(f"✓ Created offline installer: {installer_file}")
    
    def create_package_manifest(self):
        """Create package manifest for tracking"""
        manifest = {
            "version": "2.0",
            "created_for": platform.system(),
            "python_version": sys.version,
            "packages": {
                "base": self.base_packages,
                "server": self.server_packages,
                "windows": self.windows_packages if platform.system() == "Windows" else []
            },
            "usage": {
                "copy_to_target": "Copy entire offline_packages folder to target machine",
                "run": "python offline_packages/install_offline.py",
                "then": "python setup_installer.py"
            }
        }
        
        manifest_file = self.packages_dir / "manifest.json"
        with open(manifest_file, "w") as f:
            json.dump(manifest, f, indent=2)
        
        print(f"✓ Created package manifest: {manifest_file}")
    
    def create_offline_package(self):
        """Create complete offline package"""
        print("🚀 Creating offline installation package...")
        
        # Create directories
        self.create_directories()
        
        # Download base packages
        all_packages = self.base_packages + self.server_packages
        
        # Add Windows packages if on Windows
        if platform.system() == "Windows":
            all_packages.extend(self.windows_packages)
        
        # Download packages
        self.download_python_packages(all_packages, self.wheels_dir)
        
        # Create offline installer
        self.create_offline_installer()
        
        # Create manifest
        self.create_package_manifest()
        
        # Copy main installer files
        main_files = [
            "setup_installer.py",
            "worker_node.py", 
            "job_queue_manager.py",
            "requirements.txt"
        ]
        
        for filename in main_files:
            if Path(filename).exists():
                shutil.copy2(filename, self.packages_dir / filename)
                print(f"✓ Copied {filename}")
        
        # Show portable Python instructions
        self.download_portable_python()
        
        print(f"\n🎯 Offline package created in: {self.packages_dir}")
        print(f"\n📋 Usage Instructions:")
        print(f"1. Copy '{self.packages_dir}' folder to target machine")
        print(f"2. On target machine: cd {self.packages_dir}")
        print(f"3. Run: python install_offline.py")
        print(f"4. Then: python setup_installer.py")
        
        return True

def main():
    """Main entry point"""
    downloader = OfflinePackageDownloader()
    
    print("\nOptions:")
    print("1. Create offline package (internet required)")
    print("2. Exit")
    
    choice = input("\nChoose option (1-2): ").strip()
    
    if choice == "1":
        if downloader.create_offline_package():
            print("\n✅ Offline package creation complete!")
        else:
            print("\n❌ Package creation failed!")
    else:
        print("👋 Goodbye!")

if __name__ == "__main__":
    main()