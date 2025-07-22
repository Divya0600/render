#!/usr/bin/env python3
"""
Simple, Modern Render Farm Installer
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import sys
import platform
import subprocess
import threading
import json
import shutil
from pathlib import Path

class RenderFarmInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Render Farm Setup")
        self.root.geometry("700x550")
        self.root.resizable(False, False)
        self.root.configure(bg="#ffffff")
        
        # Center window
        self.center_window()
        
        # Variables
        self.install_type = tk.StringVar(value="server")
        self.install_path = tk.StringVar(value=self.get_default_install_path())
        self.create_shortcuts = tk.BooleanVar(value=True)
        self.start_service = tk.BooleanVar(value=True)
        self.server_ip = tk.StringVar(value="localhost")
        self.server_port = tk.StringVar(value="8080")
        
        # State
        self.current_step = 0
        self.installation_complete = False
        
        self.create_ui()
    
    def center_window(self):
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.root.winfo_screenheight() // 2) - (550 // 2)
        self.root.geometry(f"700x550+{x}+{y}")
    
    def get_default_install_path(self):
        if platform.system() == "Windows":
            # Use user directory instead of Program Files to avoid permission issues
            user_dir = Path.home()
            return str(user_dir / "RenderFarm")
        else:
            return "/opt/renderfarm"
    
    def create_ui(self):
        # Main container
        main_frame = tk.Frame(self.root, bg="#ffffff")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = tk.Frame(main_frame, bg="#f8f9fa", height=80)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        
        title_label = tk.Label(header_frame, text="Render Farm Setup", 
                              font=("Arial", 20, "bold"), bg="#f8f9fa", fg="#212529")
        title_label.pack(pady=20)
        
        # Content area
        self.content_frame = tk.Frame(main_frame, bg="#ffffff")
        self.content_frame.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Bottom frame for buttons
        bottom_frame = tk.Frame(main_frame, bg="#f8f9fa", height=70)
        bottom_frame.pack(fill="x", side="bottom")
        bottom_frame.pack_propagate(False)
        
        button_frame = tk.Frame(bottom_frame, bg="#f8f9fa")
        button_frame.pack(side="right", padx=20, pady=15)
        
        self.back_button = tk.Button(button_frame, text="Back", command=self.go_back,
                                    width=10, height=1, font=("Arial", 10),
                                    state="disabled")
        self.back_button.pack(side="left", padx=(0, 10))
        
        self.next_button = tk.Button(button_frame, text="Next", command=self.go_next,
                                    width=10, height=1, font=("Arial", 10, "bold"),
                                    bg="#0066cc", fg="white")
        self.next_button.pack(side="left")
        
        # Show first step
        self.show_step()
    
    def show_step(self):
        # Clear content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        if self.current_step == 0:
            self.show_welcome()
        elif self.current_step == 1:
            self.show_installation_type()
        elif self.current_step == 2:
            self.show_configuration()
        elif self.current_step == 3:
            self.show_installation()
        elif self.current_step == 4:
            self.show_complete()
        
        self.update_buttons()
    
    def show_welcome(self):
        tk.Label(self.content_frame, text="Welcome to Render Farm Setup", 
                font=("Arial", 16, "bold"), bg="#ffffff").pack(pady=(0, 20))
        
        tk.Label(self.content_frame, 
                text="This will install the Professional VFX Render Farm on your computer.",
                font=("Arial", 11), bg="#ffffff").pack(pady=(0, 20))
        
        features_text = """Features:
• Distribute rendering across multiple machines
• Real-time progress monitoring
• Central worker management
• Optimized resource usage"""
        
        tk.Label(self.content_frame, text=features_text, 
                font=("Arial", 10), bg="#ffffff", justify="left").pack(pady=(0, 20))
        
        req_frame = tk.LabelFrame(self.content_frame, text="Requirements", 
                                 font=("Arial", 10, "bold"))
        req_frame.pack(fill="x", pady=20)
        
        tk.Label(req_frame, text="• Python 3.7+\n• Windows 10+ or Linux\n• 4GB RAM\n• Network access",
                font=("Arial", 9), justify="left").pack(padx=10, pady=10)
    
    def show_installation_type(self):
        tk.Label(self.content_frame, text="Choose Installation Type", 
                font=("Arial", 16, "bold"), bg="#ffffff").pack(pady=(0, 30))
        
        # Server option
        server_frame = tk.LabelFrame(self.content_frame, text="Server Installation", 
                                    font=("Arial", 12, "bold"), padx=20, pady=15)
        server_frame.pack(fill="x", pady=10)
        
        tk.Radiobutton(server_frame, text="Install as Render Farm Server", 
                      variable=self.install_type, value="server", 
                      font=("Arial", 11, "bold"), bg="#ffffff").pack(anchor="w")
        
        tk.Label(server_frame, text="• Job queue management\n• Web interface\n• Worker coordination",
                justify="left", fg="#666", bg="#ffffff").pack(anchor="w", pady=(5, 0))
        
        # Worker option
        worker_frame = tk.LabelFrame(self.content_frame, text="Worker Installation", 
                                    font=("Arial", 12, "bold"), padx=20, pady=15)
        worker_frame.pack(fill="x", pady=10)
        
        tk.Radiobutton(worker_frame, text="Install as Render Farm Worker", 
                      variable=self.install_type, value="worker", 
                      font=("Arial", 11, "bold"), bg="#ffffff").pack(anchor="w")
        
        tk.Label(worker_frame, text="• Process render jobs\n• Auto-connect to server\n• High performance",
                justify="left", fg="#666", bg="#ffffff").pack(anchor="w", pady=(5, 0))
    
    def show_configuration(self):
        tk.Label(self.content_frame, text="Configuration", 
                font=("Arial", 16, "bold"), bg="#ffffff").pack(pady=(0, 20))
        
        # Installation path
        path_frame = tk.Frame(self.content_frame, bg="#ffffff")
        path_frame.pack(fill="x", pady=10)
        
        tk.Label(path_frame, text="Installation Directory:", 
                font=("Arial", 10, "bold"), bg="#ffffff").pack(anchor="w")
        
        path_entry_frame = tk.Frame(path_frame, bg="#ffffff")
        path_entry_frame.pack(fill="x", pady=5)
        
        path_entry = tk.Entry(path_entry_frame, textvariable=self.install_path, 
                             font=("Arial", 10), width=50)
        path_entry.pack(side="left", fill="x", expand=True)
        
        tk.Button(path_entry_frame, text="Browse", command=self.browse_path,
                 width=8).pack(side="right", padx=(10, 0))
        
        # Options
        options_frame = tk.Frame(self.content_frame, bg="#ffffff")
        options_frame.pack(fill="x", pady=20)
        
        tk.Checkbutton(options_frame, text="Create desktop shortcuts", 
                      variable=self.create_shortcuts, bg="#ffffff").pack(anchor="w")
        
        tk.Checkbutton(options_frame, text="Start service automatically", 
                      variable=self.start_service, bg="#ffffff").pack(anchor="w")
        
        # Worker-specific config
        if self.install_type.get() == "worker":
            server_frame = tk.LabelFrame(self.content_frame, text="Server Connection", 
                                        font=("Arial", 10, "bold"))
            server_frame.pack(fill="x", pady=20)
            
            server_row = tk.Frame(server_frame, bg="#ffffff")
            server_row.pack(fill="x", padx=10, pady=10)
            
            tk.Label(server_row, text="Server IP:", bg="#ffffff").pack(side="left")
            tk.Entry(server_row, textvariable=self.server_ip, width=15).pack(side="left", padx=(10, 20))
            
            tk.Label(server_row, text="Port:", bg="#ffffff").pack(side="left")
            tk.Entry(server_row, textvariable=self.server_port, width=8).pack(side="left", padx=(10, 0))
    
    def show_installation(self):
        tk.Label(self.content_frame, text="Installing...", 
                font=("Arial", 16, "bold"), bg="#ffffff").pack(pady=(0, 20))
        
        # Progress bar
        self.progress = ttk.Progressbar(self.content_frame, mode='determinate', length=400)
        self.progress.pack(pady=20)
        
        # Status label
        self.status_label = tk.Label(self.content_frame, text="Starting installation...", 
                                    font=("Arial", 10), bg="#ffffff")
        self.status_label.pack(pady=10)
        
        # Log area
        log_frame = tk.Frame(self.content_frame, bg="#ffffff")
        log_frame.pack(fill="both", expand=True, pady=20)
        
        self.log_text = tk.Text(log_frame, height=10, font=("Courier", 9))
        scrollbar = tk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Start installation
        threading.Thread(target=self.run_installation, daemon=True).start()
    
    def show_complete(self):
        tk.Label(self.content_frame, text="Installation Complete!", 
                font=("Arial", 18, "bold"), fg="#28a745", bg="#ffffff").pack(pady=(0, 20))
        
        install_path = Path(self.install_path.get())
        
        if self.install_type.get() == "server":
            message = f"""Server Ready!

Installed to: {install_path}
Web Interface: http://localhost:8080

Click "Launch Server" to start immediately."""
        else:
            if self.start_service.get():
                # Check if service was actually installed by looking at the log
                log_content = self.log_text.get("1.0", "end-1c")
                if "Service started successfully" in log_content:
                    message = f""" Worker Service Running!

 Service: RenderFarmWorker (Started)
 Server: {self.server_ip.get()}:{self.server_port.get()}
 Auto-start: Enabled

The worker is now processing jobs automatically."""
                else:
                    message = f""" Worker Installed!

 Service requires Administrator privileges
 Server: {self.server_ip.get()}:{self.server_port.get()}
 Desktop shortcut created

Run installer as Administrator for automatic service setup."""
            else:
                message = f""" Worker Installed!

Server: {self.server_ip.get()}:{self.server_port.get()}

Click "Launch Worker" to start processing jobs."""
        
        tk.Label(self.content_frame, text=message, 
                font=("Arial", 12), justify="center", bg="#ffffff").pack(pady=(0, 30))
        
        # Button frame - centered and larger
        button_frame = tk.Frame(self.content_frame, bg="#ffffff")
        button_frame.pack(pady=30)
        
        # Launch button - larger and more prominent
        if self.install_type.get() == "server" or not self.start_service.get():
            launch_text = "Launch Server" if self.install_type.get() == "server" else "Launch Worker"
            tk.Button(button_frame, text=launch_text, 
                     command=self.launch_app, font=("Arial", 12, "bold"),
                     bg="#28a745", fg="white", width=18, height=3).pack(pady=(0, 15))
        
        # Finish button - always visible and prominent
        tk.Button(button_frame, text="Finish", 
                 command=self.root.quit, font=("Arial", 12, "bold"),
                 bg="#0066cc", fg="white", width=18, height=2).pack(pady=(0, 10))
        
        # Open folder button - smaller, less prominent
        tk.Button(button_frame, text="📁 Open Install Folder", 
                 command=self.open_install_folder, font=("Arial", 10),
                 bg="#6c757d", fg="white", width=18, height=1).pack()
    
    def install_worker_service(self, install_path):
        """Install worker as Windows service"""
        try:
            service_name = "RenderFarmWorker"
            
            # Check if running as admin
            try:
                import ctypes
                is_admin = ctypes.windll.shell32.IsUserAnAdmin()
                if not is_admin:
                    self.log_message(" Administrator privileges required for Windows service")
                    self.log_message("  Installing as manual start instead")
                    self.log_message("  Use 'Run as Administrator' for automatic service installation")
                    return
            except:
                self.log_message(" Could not check admin privileges")
            
            # Check if service already exists and remove it
            check_cmd = f'sc query {service_name}'
            check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                self.log_message(f" Found existing {service_name} service - removing it")
                
                # Stop the service first
                stop_cmd = f'sc stop {service_name}'
                subprocess.run(stop_cmd, shell=True, capture_output=True, text=True)
                self.log_message(" Stopped existing service")
                
                # Delete the service
                delete_cmd = f'sc delete {service_name}'
                delete_result = subprocess.run(delete_cmd, shell=True, capture_output=True, text=True)
                
                if delete_result.returncode == 0:
                    self.log_message(" Removed existing service")
                    # Wait a moment for service deletion to complete
                    import time
                    time.sleep(2)
                else:
                    self.log_message(" Could not remove existing service - continuing anyway")
            
            # Create service script
            service_script = f'''@echo off
cd /d "{install_path}"
python worker_node.py --server http://{self.server_ip.get()}:{self.server_port.get()}'''
            
            service_bat = install_path / "worker_service.bat"
            with open(service_bat, 'w') as f:
                f.write(service_script)
            
            self.log_message(" Created service script")
            
            # Create Windows service with batch file wrapper  
            create_cmd = f'sc create {service_name} binPath= "\\"{service_bat}\\"" start= auto DisplayName= "Render Farm Worker" depend= Tcpip'
            
            result = subprocess.run(create_cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log_message(" Windows service created successfully")
                
                # Set service description
                desc_cmd = f'sc description {service_name} "Render Farm Worker - Distributed rendering node"'
                subprocess.run(desc_cmd, shell=True, capture_output=True, text=True)
                
                # Start the service
                start_cmd = f"sc start {service_name}"
                start_result = subprocess.run(start_cmd, shell=True, capture_output=True, text=True)
                
                if start_result.returncode == 0:
                    self.log_message(" Service started successfully - Worker is now running!")
                    self.log_message(" Service will restart automatically on system boot")
                else:
                    self.log_message(" Service created but failed to start immediately")
                    self.log_message("  You can start it with: sc start RenderFarmWorker")
                    
            else:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip()
                if "Access is denied" in error_msg:
                    self.log_message("✗ Service creation failed: Administrator privileges required")
                    self.log_message("  Please run installer as Administrator for automatic service setup")
                else:
                    self.log_message(f"✗ Service creation failed: {error_msg}")
                self.log_message("  Installing as manual start instead")
                
        except Exception as e:
            self.log_message(f" Service installation error: {e}")
            self.log_message("  Worker installed for manual start only")
    
    def open_install_folder(self):
        install_path = Path(self.install_path.get())
        if platform.system() == "Windows":
            os.startfile(install_path)
        elif platform.system() == "Darwin":
            subprocess.run(["open", str(install_path)])
        else:
            subprocess.run(["xdg-open", str(install_path)])
    
    def browse_path(self):
        path = filedialog.askdirectory(initialdir=self.install_path.get())
        if path:
            self.install_path.set(path)
    
    def go_back(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step()
    
    def go_next(self):
        if self.current_step == 4:
            self.root.quit()
        elif self.current_step == 3:
            if self.installation_complete:
                self.current_step += 1
                self.show_step()
            else:
                pass  # Wait for installation to complete
        elif self.current_step == 2:
            if self.validate_config():
                self.current_step += 1
                self.show_step()
        else:
            self.current_step += 1
            self.show_step()
    
    def update_buttons(self):
        # Back button
        self.back_button.config(state="normal" if self.current_step > 0 else "disabled")
        
        # Next button
        if self.current_step == 4:
            self.next_button.config(text="Finish")
        elif self.current_step == 3:
            if self.installation_complete:
                self.next_button.config(text="Next", state="normal", bg="#28a745")
            else:
                self.next_button.config(text="Installing...", state="disabled", bg="#ffc107")
        else:
            self.next_button.config(text="Next", state="normal", bg="#0066cc")
    
    def validate_config(self):
        if not self.install_path.get().strip():
            messagebox.showerror("Error", "Please select an installation directory")
            return False
        return True
    
    def run_installation(self):
        try:
            self.log_message("Starting Render Farm installation...")
            self.update_progress(5, "Validating installation path...")
            
            # Create install directory
            install_path = Path(self.install_path.get())
            self.log_message(f"Installing to: {install_path}")
            
            try:
                install_path.mkdir(parents=True, exist_ok=True)
                self.log_message(f" Created directory: {install_path}")
            except Exception as e:
                raise Exception(f"Failed to create directory: {e}")
            
            self.update_progress(15, "Preparing file list...")
            
            # Get source directory - files are in the same directory as installer
            source_path = Path(__file__).parent
            if getattr(sys, 'frozen', False):
                # Running as EXE - files are embedded in the temporary directory  
                source_path = Path(sys._MEIPASS)
                self.log_message(f"EXE mode - using embedded files from: {source_path}")
            else:
                self.log_message(f"Development mode - using current directory: {source_path}")
            
            # Core files needed for both server and worker
            core_files = [
                "requirements.txt", 
                "worker_node.py", 
                "job_queue_manager.py",
                "config.json", 
                "app_config.json"
            ]
            
            server_files = [
                "main_app.py", 
                "server.py", 
                "distributed_renderers.py",
                "unified_app.py", 
                "server_config.json", 
                "worker_machines.json",
                "worker_deployment_manager.py"
            ]
            
            if self.install_type.get() == "server":
                files_to_copy = core_files + server_files
                self.log_message("Installing SERVER components...")
            else:
                files_to_copy = core_files
                self.log_message("Installing WORKER components...")
            
            self.update_progress(25, "Copying application files...")
            
            copied_files = 0
            missing_files = []
            
            for i, file in enumerate(files_to_copy):
                progress = 25 + (i * 40 // len(files_to_copy))
                self.update_progress(progress, f"Copying {file}...")
                
                src = source_path / file
                dst = install_path / file
                
                if src.exists():
                    try:
                        shutil.copy2(src, dst)
                        self.log_message(f" Copied {file}")
                        copied_files += 1
                    except Exception as e:
                        self.log_message(f"✗ Failed to copy {file}: {e}")
                        missing_files.append(f"{file} (copy error)")
                else:
                    self.log_message(f"✗ Missing source file: {file}")
                    missing_files.append(f"{file} (not found)")
            
            self.log_message(f"Copied {copied_files} files successfully")
            if missing_files:
                self.log_message(f"Missing files: {', '.join(missing_files)}")
            
            self.update_progress(70, "Installing Python dependencies...")
            
            # Skip pip installation when running as EXE (dependencies should already be available)
            if getattr(sys, 'frozen', False):
                self.log_message(" Running as EXE - dependencies already included")
            else:
                # Try to install Python dependencies (development mode only)
                try:
                    result = subprocess.run([
                        sys.executable, "-m", "pip", "install", "-r", 
                        str(install_path / "requirements.txt")
                    ], capture_output=True, text=True, timeout=60)
                    
                    if result.returncode == 0:
                        self.log_message(" Python dependencies installed")
                    else:
                        self.log_message(f" Dependency installation warning: {result.stderr}")
                except Exception as e:
                    self.log_message(f" Could not install dependencies: {e}")
            
            self.update_progress(85, "Creating configuration files...")
            
            # Create config
            self.create_config(install_path)
            
            self.update_progress(90, "Creating shortcuts and launchers...")
            
            # Create shortcuts
            if self.create_shortcuts.get():
                self.create_shortcuts_func(install_path)
            
            # Create Windows service for worker if requested
            if self.install_type.get() == "worker" and self.start_service.get():
                self.update_progress(95, "Installing Windows service...")
                self.install_worker_service(install_path)
            
            self.update_progress(100, "Installation complete!")
            self.log_message("=" * 50)
            self.log_message(" INSTALLATION COMPLETED SUCCESSFULLY")
            self.log_message(f" Files installed to: {install_path}")
            
            if self.install_type.get() == "server":
                self.log_message(" Server components ready")
                self.log_message(" Launch with Start_RenderFarm.bat")
            else:
                self.log_message(" Worker components ready") 
                self.log_message(" Launch with Start_Worker.bat")
            
            self.log_message("=" * 50)
            
            self.installation_complete = True
            self.update_buttons()
            
        except Exception as e:
            error_msg = f"Installation failed: {str(e)}"
            self.log_message(f"ERROR: {error_msg}")
            self.update_progress(0, "Installation failed!")
            messagebox.showerror("Installation Error", error_msg)
    
    def update_progress(self, value, status):
        self.progress['value'] = value
        self.status_label.config(text=status)
        self.root.update()
    
    def log_message(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.root.update()
    
    def create_config(self, install_path):
        if self.install_type.get() == "worker":
            # Make sure server URL is properly formatted
            server_url = self.server_ip.get()
            # Add http:// prefix if not already present
            if not server_url.startswith(("http://", "https://")):
                server_url = f"http://{server_url}"
            
            # Make sure the port is added to the URL
            if ":" not in server_url.split("/")[-1]:
                server_url = f"{server_url}:{self.server_port.get()}"
                
            config = {
                "server_url": server_url,
                "worker_id": f"worker_{platform.node()}",
                "auto_start": True
            }
            
            self.log_message(f"Creating worker config with server URL: {server_url}")
            with open(install_path / "worker_config.json", 'w') as f:
                json.dump(config, f, indent=2)
        else:
            config = {
                "port": int(self.server_port.get()),
                "host": "0.0.0.0",
                "database_path": str(install_path / "render_farm.db")
            }
            with open(install_path / "server_config.json", 'w') as f:
                json.dump(config, f, indent=2)
                
    def create_shortcuts_func(self, install_path):
        if platform.system() == "Windows":
            if self.install_type.get() == "server":
                script_content = f'''@echo off
title Render Farm Server
cd /d "{install_path}"
echo Starting Render Farm Server...
start "Render Farm API Server" python server.py
timeout /t 3
echo Starting Management GUI...
start "Render Farm GUI" python main_app.py
echo.
echo Server and GUI started successfully!
echo Server API: http://localhost:8080
echo Close this window when done
pause'''
                launcher_path = install_path / "Start_RenderFarm.bat"
                with open(launcher_path, 'w') as f:
                    f.write(script_content)
                self.log_message(f"Created launcher: {launcher_path}")
                
                # Try to create desktop shortcut
                try:
                    desktop = Path("C:/Users/Public/Desktop")
                    if desktop.exists():
                        desktop_shortcut = desktop / "Render Farm Server.bat"
                        with open(desktop_shortcut, 'w') as f:
                            f.write(script_content)
                        self.log_message(f" Created desktop shortcut: {desktop_shortcut}")
                except Exception as e:
                    self.log_message(f" Could not create desktop shortcut: {e}")
                    
            else:
                # Make sure server URL is properly formatted
                server_url = self.server_ip.get()
                # Add http:// prefix if not already present
                if not server_url.startswith(("http://", "https://")):
                    server_url = f"http://{server_url}"
                
                # Make sure the port is added to the URL
                if ":" not in server_url.split("/")[-1]:
                    server_url = f"{server_url}:{self.server_port.get()}"
                
                # Create two versions: visible and background
                # Visible version (for testing/debugging)
                script_content = f'''@echo off
title Render Farm Worker  
cd /d "{install_path}"
echo Connecting to server: {server_url}
python worker_node.py --server {server_url}
pause'''
                
                # Background version (production - runs minimized)
                background_script = f'''@echo off
cd /d "{install_path}"
start /min "" python worker_node.py --server {server_url}'''
                
                # Create both launchers
                launcher_path = install_path / "Start_Worker.bat"
                with open(launcher_path, 'w') as f:
                    f.write(script_content)
                self.log_message(f" Created launcher: {launcher_path}")
                
                # Create background launcher
                background_path = install_path / "Start_Worker_Background.bat"
                with open(background_path, 'w') as f:
                    f.write(background_script)
                self.log_message(f" Created background launcher: {background_path}")
                
                # Try to create desktop shortcuts
                try:
                    desktop = Path("C:/Users/Public/Desktop")
                    if desktop.exists():
                        # Create background shortcut (main one)
                        desktop_shortcut = desktop / "Render Farm Worker (Background).bat"
                        with open(desktop_shortcut, 'w') as f:
                            f.write(background_script)
                        self.log_message(f" Created background desktop shortcut: {desktop_shortcut}")
                        
                        # Create visible shortcut (for debugging)
                        desktop_debug = desktop / "Render Farm Worker (Debug).bat" 
                        with open(desktop_debug, 'w') as f:
                            f.write(script_content)
                        self.log_message(f" Created debug desktop shortcut: {desktop_debug}")
                        
                        # Add to Windows Startup folder for auto-start on boot
                        startup_folder = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
                        if startup_folder.exists():
                            startup_shortcut = startup_folder / "Render Farm Worker.bat"
                            with open(startup_shortcut, 'w') as f:
                                f.write(background_script)
                            self.log_message(f" Added to Windows Startup: {startup_shortcut}")
                            self.log_message(" Worker will start automatically on system boot!")
                        else:
                            self.log_message(" Could not find Windows Startup folder")
                except Exception as e:
                    self.log_message(f" Could not create desktop shortcut: {e}")
        else:
            # Linux shortcuts
            if self.install_type.get() == "server":
                script_content = f'''#!/bin/bash
cd "{install_path}"
python3 main_app.py'''
                launcher_path = install_path / "start_server.sh"
                with open(launcher_path, 'w') as f:
                    f.write(script_content)
                launcher_path.chmod(0o755)
                self.log_message(f" Created launcher: {launcher_path}")
            else:
                script_content = f'''#!/bin/bash
cd "{install_path}"
python3 worker_node.py'''
                launcher_path = install_path / "start_worker.sh"
                with open(launcher_path, 'w') as f:
                    f.write(script_content)
                launcher_path.chmod(0o755)
                self.log_message(f" Created launcher: {launcher_path}")
    
    def launch_app(self):
        install_path = Path(self.install_path.get())
        if self.install_type.get() == "server":
            script = install_path / "Start_RenderFarm.bat"
        else:
            script = install_path / "Start_Worker.bat"
        
        if script.exists():
            subprocess.Popen([str(script)], shell=True)
    
    def run(self):
        self.root.mainloop()

def main():
    installer = RenderFarmInstaller()
    installer.run()

if __name__ == "__main__":
    main()