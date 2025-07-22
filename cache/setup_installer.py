#!/usr/bin/env python3
"""
Professional Render Farm Installer
Creates a Windows-style installer for Server/Worker components
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
import webbrowser

class RenderFarmInstaller:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Render Farm Setup v2.0")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8f9fa")
        
        # Center window
        self.center_window()
        
        # Variables
        self.install_type = tk.StringVar(value="server")
        self.install_path = tk.StringVar(value=self.get_default_install_path())
        self.create_shortcuts = tk.BooleanVar(value=True)
        self.start_service = tk.BooleanVar(value=True)
        self.server_ip = tk.StringVar(value="localhost")
        self.server_port = tk.StringVar(value="8080")
        
        # Installation state
        self.installation_complete = False
        
        self.create_gui()
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f"800x600+{x}+{y}")
    
    def get_default_install_path(self):
        """Get default installation path"""
        if platform.system() == "Windows":
            return "C:\\Program Files\\RenderFarm"
        else:
            return "/opt/renderfarm"
    
    def create_gui(self):
        """Create the installer GUI"""
        # Modern header
        self.create_modern_header()
        
        # Horizontal progress indicator
        self.create_progress_indicator()
        
        # Main content area
        self.create_main_content()
        
        # Bottom navigation bar
        self.create_bottom_navigation()
    
    def create_modern_header(self):
        """Create modern header"""
        header = tk.Frame(self.root, bg="#ffffff", height=80, relief="solid", bd=1)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        # Title container
        title_container = tk.Frame(header, bg="#ffffff")
        title_container.pack(fill="both", expand=True, padx=30, pady=20)
        
        title_label = tk.Label(title_container, text="Render Farm Setup", 
                              font=("Segoe UI", 18, "bold"), fg="#212529", bg="#ffffff")
        title_label.pack(side="left")
        
        # Version info
        version_label = tk.Label(title_container, text="v2.0", 
                                font=("Segoe UI", 12), fg="#6c757d", bg="#ffffff")
        version_label.pack(side="right", anchor="e")
    
    def create_progress_indicator(self):
        """Create horizontal progress indicator"""
        progress_frame = tk.Frame(self.root, bg="#f8f9fa", height=60, relief="solid", bd=1)
        progress_frame.pack(fill="x")
        progress_frame.pack_propagate(False)
        
        # Progress container
        progress_container = tk.Frame(progress_frame, bg="#f8f9fa")
        progress_container.pack(expand=True, fill="both", pady=20)
        
        # Progress steps
        self.progress_steps = []
        steps = ["Welcome", "Type", "Configuration", "Installation", "Complete"]
        
        steps_container = tk.Frame(progress_container, bg="#f8f9fa")
        steps_container.pack(expand=True)
        
        for i, step in enumerate(steps):
            # Step frame
            step_frame = tk.Frame(steps_container, bg="#f8f9fa")
            step_frame.pack(side="left", padx=20)
            
            # Progress dot
            dot_frame = tk.Frame(step_frame, bg="#f8f9fa")
            dot_frame.pack()
            
            dot = tk.Label(dot_frame, text="●", font=("Segoe UI", 16), 
                          fg="#dee2e6", bg="#f8f9fa")
            dot.pack()
            
            # Step label
            label = tk.Label(step_frame, text=step, 
                            font=("Segoe UI", 9), fg="#6c757d", bg="#f8f9fa")
            label.pack(pady=(5, 0))
            
            self.progress_steps.append((dot, label))
            
            # Add connector line (except for last step)
            if i < len(steps) - 1:
                line_frame = tk.Frame(steps_container, bg="#f8f9fa", width=40, height=2)
                line_frame.pack(side="left", pady=(8, 0))
                line = tk.Label(line_frame, text="──", font=("Segoe UI", 8), 
                               fg="#dee2e6", bg="#f8f9fa")
                line.pack()
    
    def create_main_content(self):
        """Create main content area"""
        # Create pages list and current page tracker
        self.current_page = 0
        self.pages = []
        
        # Create container for pages
        self.page_container = tk.Frame(self.root, bg="#ffffff")
        self.page_container.pack(fill="both", expand=True, padx=40, pady=30)
        
        # Create all pages
        self.create_welcome_page()
        self.create_install_type_page()
        self.create_config_page()
        self.create_installation_page()
        self.create_complete_page()
    
    def create_bottom_navigation(self):
        """Create bottom navigation bar"""
        # Bottom border line
        border = tk.Frame(self.root, bg="#dee2e6", height=1)
        border.pack(fill="x")
        
        # Navigation frame
        nav_frame = tk.Frame(self.root, bg="#ffffff", height=70)
        nav_frame.pack(fill="x")
        nav_frame.pack_propagate(False)
        
        nav_content = tk.Frame(nav_frame, bg="#ffffff")
        nav_content.pack(fill="both", expand=True, padx=40, pady=20)
        
        # Status label
        self.status_var = tk.StringVar(value="Ready to begin installation")
        status_label = tk.Label(nav_content, textvariable=self.status_var,
                               font=("Segoe UI", 9), fg="#6c757d", bg="#ffffff")
        status_label.pack(side="left", anchor="w")
        
        # Navigation buttons
        button_frame = tk.Frame(nav_content, bg="#ffffff")
        button_frame.pack(side="right", anchor="e")
        
        self.back_btn = tk.Button(button_frame, text="Back", command=self.go_back,
                                 font=("Segoe UI", 10), width=10, height=2,
                                 bg="#6c757d", fg="white", relief="flat", bd=0,
                                 state="disabled")
        self.back_btn.pack(side="left", padx=(0, 15))
        
        self.next_btn = tk.Button(button_frame, text="Next", command=self.go_next,
                                 font=("Segoe UI", 10, "bold"), width=10, height=2,
                                 bg="#0d6efd", fg="white", relief="flat", bd=0)
        self.next_btn.pack(side="left")
        
        # Show first page after all UI is created
        self.show_page(0)
    
    def show_page(self, page_index):
        """Show specific page"""
        # Hide all pages
        for page in self.pages:
            page.pack_forget()
        
        # Show requested page
        if 0 <= page_index < len(self.pages):
            self.current_page = page_index
            self.pages[page_index].pack(fill="both", expand=True)
            self.update_progress_indicators()
            self.update_navigation_buttons()
    
    def update_progress_indicators(self):
        """Update horizontal progress indicators"""
        for i, (dot, label) in enumerate(self.progress_steps):
            if i < self.current_page:
                # Completed step
                dot.config(fg="#198754")
                label.config(fg="#198754", font=("Segoe UI", 9, "bold"))
            elif i == self.current_page:
                # Current step
                dot.config(fg="#0d6efd")
                label.config(fg="#0d6efd", font=("Segoe UI", 9, "bold"))
            else:
                # Future step
                dot.config(fg="#dee2e6")
                label.config(fg="#6c757d", font=("Segoe UI", 9))
    
    def create_welcome_page(self):
        """Create welcome page"""
        page = tk.Frame(self.page_container, bg="#ffffff")
        self.pages.append(page)
        
        # Welcome content with modern layout
        content = tk.Frame(page, bg="#ffffff")
        content.pack(expand=True, fill="both")
        
        # Large welcome title
        title_label = tk.Label(content, text="Welcome to Render Farm Setup", 
                              font=("Segoe UI", 24, "bold"), fg="#212529", bg="#ffffff")
        title_label.pack(pady=(0, 10))
        
        # Subtitle
        subtitle_label = tk.Label(content, text="Professional VFX Render Farm Installation", 
                                 font=("Segoe UI", 12), fg="#6c757d", bg="#ffffff")
        subtitle_label.pack(pady=(0, 30))
        
        # Features section
        features_frame = tk.Frame(content, bg="#ffffff")
        features_frame.pack(fill="x", pady=(0, 30))
        
        features_title = tk.Label(features_frame, text="What you'll get:", 
                                 font=("Segoe UI", 14, "bold"), fg="#212529", bg="#ffffff")
        features_title.pack(anchor="w", pady=(0, 15))
        
        features = [
            "Distribute rendering jobs across multiple machines",
            "Monitor render progress with real-time web interface",
            "Centralized worker node management",
            "Optimized resource utilization and load balancing"
        ]
        
        for feature in features:
            feature_frame = tk.Frame(features_frame, bg="#ffffff")
            feature_frame.pack(fill="x", pady=3)
            
            # Checkmark icon (using Unicode)
            check_label = tk.Label(feature_frame, text="✓", 
                                  font=("Segoe UI", 12, "bold"), fg="#198754", bg="#ffffff")
            check_label.pack(side="left", padx=(0, 10))
            
            feature_label = tk.Label(feature_frame, text=feature, 
                                    font=("Segoe UI", 11), fg="#495057", bg="#ffffff")
            feature_label.pack(side="left", anchor="w")
        
        # System requirements in a modern card
        req_frame = tk.Frame(content, bg="#f8f9fa", relief="solid", bd=1)
        req_frame.pack(fill="x", pady=(20, 0))
        
        req_content = tk.Frame(req_frame, bg="#f8f9fa")
        req_content.pack(fill="both", padx=20, pady=15)
        
        req_title = tk.Label(req_content, text="System Requirements", 
                            font=("Segoe UI", 12, "bold"), fg="#495057", bg="#f8f9fa")
        req_title.pack(anchor="w", pady=(0, 10))
        
        requirements = [
            "Python 3.7 or higher",
            "Windows 10/11 or Linux",
            "4GB RAM minimum", 
            "Network connectivity for distributed rendering"
        ]
        
        for req in requirements:
            req_item = tk.Label(req_content, text=f"• {req}", 
                               font=("Segoe UI", 10), fg="#6c757d", bg="#f8f9fa")
            req_item.pack(anchor="w", pady=2)
    
    def create_install_type_page(self):
        """Create installation type selection page"""
        page = tk.Frame(self.page_container)
        self.pages.append(page)
        
        # Header
        header_label = tk.Label(page, text="Choose Installation Type", 
                               font=("Arial", 16, "bold"))
        header_label.pack(pady=(20, 10))
        
        desc_label = tk.Label(page, text="Select whether this machine will be a Server or Worker node:", 
                             font=("Arial", 11))
        desc_label.pack(pady=(0, 20))
        
        # Installation options
        options_frame = tk.Frame(page)
        options_frame.pack(pady=20, fill="x")
        
        # Server option
        server_frame = tk.LabelFrame(options_frame, text="Server Installation", 
                                    font=("Arial", 12, "bold"), padx=20, pady=15)
        server_frame.pack(fill="x", pady=10)
        
        tk.Radiobutton(server_frame, text="Install as Render Farm Server", 
                      variable=self.install_type, value="server", 
                      font=("Arial", 11, "bold")).pack(anchor="w")
        
        server_desc = tk.Label(server_frame, 
                              text="• Job queue management and web interface\\n"
                                   "• Worker coordination and monitoring\\n"
                                   "• Central render farm control\\n"
                                   "• Best for: Main control machine", 
                              justify="left", fg="#666")
        server_desc.pack(anchor="w", pady=5)
        
        # Worker option
        worker_frame = tk.LabelFrame(options_frame, text="Worker Installation", 
                                    font=("Arial", 12, "bold"), padx=20, pady=15)
        worker_frame.pack(fill="x", pady=10)
        
        tk.Radiobutton(worker_frame, text="Install as Render Worker", 
                      variable=self.install_type, value="worker", 
                      font=("Arial", 11, "bold")).pack(anchor="w")
        
        worker_desc = tk.Label(worker_frame, 
                              text="• Processes render jobs from server\\n"
                                   "• Optimized for high-performance rendering\\n"
                                   "• Automatic job discovery and execution\\n"
                                   "• Best for: Dedicated render machines", 
                              justify="left", fg="#666")
        worker_desc.pack(anchor="w", pady=5)
        
        # System info
        info_frame = tk.LabelFrame(page, text="System Information", padx=10, pady=10)
        info_frame.pack(fill="x", pady=20)
        
        system_info = f"OS: {platform.system()} {platform.release()}\\n"
        system_info += f"Architecture: {platform.machine()}\\n"
        system_info += f"Python: {sys.version.split()[0]}"
        
        tk.Label(info_frame, text=system_info, justify="left", 
                font=("Courier", 9)).pack(anchor="w")
    
    def create_config_page(self):
        """Create configuration page"""
        page = tk.Frame(self.page_container)
        self.pages.append(page)
        
        tk.Label(page, text="Installation Configuration", 
                font=("Arial", 16, "bold")).pack(pady=20)
        
        # Installation path
        path_frame = tk.LabelFrame(page, text="Installation Directory", padx=10, pady=10)
        path_frame.pack(fill="x", pady=10)
        
        path_entry_frame = tk.Frame(path_frame)
        path_entry_frame.pack(fill="x")
        
        tk.Entry(path_entry_frame, textvariable=self.install_path, 
                font=("Arial", 10), width=50).pack(side="left", padx=5)
        tk.Button(path_entry_frame, text="Browse...", 
                 command=self.browse_install_path).pack(side="right")
        
        # Server configuration (for worker installs)
        self.server_frame = tk.LabelFrame(page, text="Server Configuration", 
                                         padx=10, pady=10)
        self.server_frame.pack(fill="x", pady=10)
        
        tk.Label(self.server_frame, text="Server IP Address:").grid(row=0, column=0, sticky="w", padx=5)
        tk.Entry(self.server_frame, textvariable=self.server_ip, width=20).grid(row=0, column=1, padx=5)
        
        tk.Label(self.server_frame, text="Server Port:").grid(row=1, column=0, sticky="w", padx=5)
        tk.Entry(self.server_frame, textvariable=self.server_port, width=20).grid(row=1, column=1, padx=5)
        
        # Options
        options_frame = tk.LabelFrame(page, text="Installation Options", padx=10, pady=10)
        options_frame.pack(fill="x", pady=10)
        
        tk.Checkbutton(options_frame, text="Create desktop shortcuts", 
                      variable=self.create_shortcuts).pack(anchor="w")
        tk.Checkbutton(options_frame, text="Start service automatically", 
                      variable=self.start_service).pack(anchor="w")
        
        # Update server frame visibility
        self.update_config_visibility()
    
    def create_installation_page(self):
        """Create installation progress page"""
        page = tk.Frame(self.page_container)
        self.pages.append(page)
        
        tk.Label(page, text="Installing Render Farm", 
                font=("Arial", 16, "bold")).pack(pady=20)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(page, variable=self.progress_var, 
                                           maximum=100, length=400)
        self.progress_bar.pack(pady=20)
        
        # Progress text
        self.progress_text = tk.StringVar(value="Ready to install...")
        tk.Label(page, textvariable=self.progress_text, 
                font=("Arial", 10)).pack(pady=10)
        
        # Installation log
        log_frame = tk.LabelFrame(page, text="Installation Log", padx=5, pady=5)
        log_frame.pack(fill="both", expand=True, pady=10)
        
        # Create scrolled text widget
        log_container = tk.Frame(log_frame)
        log_container.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(log_container, height=12, font=("Courier", 8))
        scrollbar = tk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Installation complete frame (hidden initially)
        self.complete_frame = tk.Frame(page)
        
        tk.Label(self.complete_frame, text="✅ Installation Complete!", 
                font=("Arial", 14, "bold"), fg="green").pack(pady=10)
        
        complete_text = tk.Label(self.complete_frame, 
                                text="Render Farm has been successfully installed.\\n"
                                     "You can now start using the application.", 
                                justify="center")
        complete_text.pack(pady=5)
        
        # Action buttons for completion
        action_frame = tk.Frame(self.complete_frame)
        action_frame.pack(pady=10)
        
        self.launch_btn = tk.Button(action_frame, text="🚀 Launch Application", 
                                   command=self.launch_application, 
                                   bg="#27ae60", fg="white", font=("Arial", 10, "bold"))
        self.launch_btn.pack(side="left", padx=10)
        
        tk.Button(action_frame, text="📁 Open Install Folder", 
                 command=self.open_install_folder).pack(side="left", padx=10)
    
    def update_config_visibility(self):
        """Update configuration page based on install type"""
        if self.install_type.get() == "worker":
            self.server_frame.pack(fill="x", pady=10)
        else:
            self.server_frame.pack_forget()
    
    def browse_install_path(self):
        """Browse for installation directory"""
        path = filedialog.askdirectory(initialdir=self.install_path.get())
        if path:
            self.install_path.set(path)
    
    def go_back(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.show_page(self.current_page - 1)
    
    def go_next(self):
        """Go to next page or start installation"""
        if self.current_page == 0:  # Welcome page
            self.show_page(1)
        elif self.current_page == 1:  # Type selection page
            self.update_config_visibility()
            self.show_page(2)
        elif self.current_page == 2:  # Configuration page
            if self.validate_configuration():
                self.show_page(3)
                # Start installation in background thread
                threading.Thread(target=self.start_installation, daemon=True).start()
        elif self.current_page == 3:  # Installation page
            if self.installation_complete:
                self.show_page(4)
        elif self.current_page == 4:  # Complete page
            self.root.quit()
    
    def update_navigation_buttons(self):
        """Update navigation button states"""
        # Back button
        if self.current_page == 0:
            self.back_btn.config(state="disabled", bg="#e9ecef", fg="#6c757d")
        else:
            self.back_btn.config(state="normal", bg="#6c757d", fg="white")
        
        # Next button
        if self.current_page == 4:  # Complete page
            self.next_btn.config(text="Finish", command=self.root.quit, 
                               state="normal", bg="#198754", fg="white")
        elif self.current_page == 3:  # Installation page
            if self.installation_complete:
                self.next_btn.config(text="Next", bg="#198754", fg="white", state="normal")
            else:
                self.next_btn.config(state="disabled", text="Installing...", 
                                   bg="#ffc107", fg="#212529")
        else:
            self.next_btn.config(text="Next", state="normal", bg="#0d6efd", fg="white")
    
    def validate_configuration(self):
        """Validate configuration settings"""
        if not self.install_path.get().strip():
            messagebox.showerror("Error", "Please specify an installation directory")
            return False
        
        if self.install_type.get() == "worker":
            if not self.server_ip.get().strip():
                messagebox.showerror("Error", "Please specify the server IP address")
                return False
            
            try:
                port = int(self.server_port.get())
                if port < 1 or port > 65535:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Error", "Please specify a valid port number (1-65535)")
                return False
        
        return True
    
    def log_message(self, message):
        """Add message to installation log"""
        self.log_text.insert(tk.END, f"{message}\\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def update_progress(self, value, text):
        """Update progress bar and text"""
        self.progress_var.set(value)
        self.progress_text.set(text)
        self.root.update_idletasks()
    
    def start_installation(self):
        """Start the installation process"""
        try:
            self.log_message("=== Render Farm Installation Started ===")
            self.log_message(f"Install Type: {self.install_type.get().title()}")
            self.log_message(f"Install Path: {self.install_path.get()}")
            
            # Step 1: Check dependencies
            self.update_progress(10, "Checking system dependencies...")
            self.check_dependencies()
            
            # Step 2: Create installation directory
            self.update_progress(20, "Creating installation directory...")
            self.create_install_directory()
            
            # Step 3: Install Python dependencies
            self.update_progress(30, "Installing Python dependencies...")
            self.install_dependencies()
            
            # Step 4: Copy application files
            self.update_progress(50, "Copying application files...")
            self.copy_application_files()
            
            # Step 5: Create configuration
            self.update_progress(70, "Creating configuration...")
            self.create_configuration()
            
            # Step 6: Create shortcuts and services
            self.update_progress(85, "Setting up shortcuts and services...")
            self.setup_shortcuts_and_services()
            
            # Step 7: Complete
            self.update_progress(100, "Installation complete!")
            self.log_message("=== Installation Completed Successfully ===")
            
            # Show completion UI
            self.complete_frame.pack(fill="x", pady=20)
            self.installation_complete = True
            self.update_navigation_buttons()
            
        except Exception as e:
            self.log_message(f"ERROR: Installation failed: {str(e)}")
            self.update_progress(0, "Installation failed!")
            messagebox.showerror("Installation Error", f"Installation failed:\\n{str(e)}")
    
    def check_dependencies(self):
        """Check system dependencies"""
        self.log_message("Checking Python installation...")
        
        # Check Python version
        if sys.version_info < (3, 7):
            raise Exception("Python 3.7 or higher is required")
        
        self.log_message(f"✓ Python {sys.version.split()[0]} found")
        
        # Check pip
        try:
            import pip
            self.log_message("✓ pip is available")
        except ImportError:
            raise Exception("pip is not installed")
    
    def create_install_directory(self):
        """Create installation directory"""
        install_path = Path(self.install_path.get())
        
        try:
            install_path.mkdir(parents=True, exist_ok=True)
            self.log_message(f"✓ Created directory: {install_path}")
        except Exception as e:
            raise Exception(f"Failed to create install directory: {e}")
    
    def install_dependencies(self):
        """Install Python dependencies"""
        dependencies = [
            "PyQt5>=5.15.0",
            "requests>=2.25.0",
            "psutil>=5.8.0",
            "aiofiles>=0.8.0"
        ]
        
        if self.install_type.get() == "server":
            dependencies.extend([
                "paramiko>=2.7.0",
                "pywinrm>=0.4.0"
            ])
        
        for dep in dependencies:
            self.log_message(f"Installing {dep}...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                             check=True, capture_output=True, text=True)
                self.log_message(f"✓ Installed {dep}")
            except subprocess.CalledProcessError as e:
                self.log_message(f"⚠ Warning: Failed to install {dep}")
    
    def copy_application_files(self):
        """Copy application files to installation directory"""
        install_path = Path(self.install_path.get())
        source_path = Path(__file__).parent
        
        # Core files for both server and worker
        files_to_copy = [
            "requirements.txt",
            "worker_node.py",
            "job_queue_manager.py",
            "config.json",
            "app_config.json",
        ]
        
        if self.install_type.get() == "server":
            files_to_copy.extend([
                "main_app.py",
                "server.py", 
                "distributed_renderers.py",
                "worker_deployment_manager.py",
                "unified_app.py",
                "server_config.json",
                "worker_machines.json"
            ])
        else:
            # Worker-specific files
            files_to_copy.extend([
                "worker_config.json"
            ])
        
        total_files = len(files_to_copy)
        for i, filename in enumerate(files_to_copy):
            progress = 50 + (i * 20 // total_files)  # Progress from 50 to 70
            self.update_progress(progress, f"Copying {filename}...")
            
            src_file = source_path / filename
            if src_file.exists():
                dst_file = install_path / filename
                shutil.copy2(src_file, dst_file)
                self.log_message(f"✓ Copied {filename}")
            else:
                self.log_message(f"⚠ Warning: {filename} not found")
                # Create empty file if it doesn't exist
                dst_file = install_path / filename
                dst_file.touch()
    
    def create_configuration(self):
        """Create configuration files"""
        install_path = Path(self.install_path.get())
        
        if self.install_type.get() == "worker":
            # Create worker config
            worker_config = {
                "server_url": f"http://{self.server_ip.get()}:{self.server_port.get()}",
                "worker_id": f"worker_{platform.node()}",
                "auto_start": True,
                "max_concurrent_jobs": 4
            }
            
            config_file = install_path / "worker_config.json"
            with open(config_file, 'w') as f:
                json.dump(worker_config, f, indent=2)
            
            self.log_message(f"✓ Created worker configuration")
        
        else:  # Server
            # Create server config
            server_config = {
                "port": int(self.server_port.get()),
                "host": "",
                "database_path": str(install_path / "render_farm.db")
            }
            
            config_file = install_path / "server_config.json"
            with open(config_file, 'w') as f:
                json.dump(server_config, f, indent=2)
            
            self.log_message(f"✓ Created server configuration")
    
    def setup_shortcuts_and_services(self):
        """Create shortcuts and services"""
        install_path = Path(self.install_path.get())
        
        # Create launcher scripts
        self.create_launcher_scripts(install_path)
        
        if self.create_shortcuts.get():
            if platform.system() == "Windows":
                self.create_windows_shortcuts(install_path)
            else:
                self.create_linux_shortcuts(install_path)
        
        if self.start_service.get():
            self.create_startup_service(install_path)
    
    def create_launcher_scripts(self, install_path):
        """Create launcher scripts"""
        if self.install_type.get() == "server":
            # Create server launcher
            server_launcher = f"""@echo off
title Render Farm Server
cd /d "{install_path}"
python main_app.py
pause
"""
            launcher_file = install_path / "start_server.bat"
            with open(launcher_file, 'w') as f:
                f.write(server_launcher)
            self.log_message("✓ Created server launcher script")
        else:
            # Create worker launcher  
            worker_launcher = f"""@echo off
title Render Farm Worker
cd /d "{install_path}"
python worker_node.py
pause
"""
            launcher_file = install_path / "start_worker.bat"
            with open(launcher_file, 'w') as f:
                f.write(worker_launcher)
            self.log_message("✓ Created worker launcher script")
    
    def create_windows_shortcuts(self, install_path):
        """Create Windows shortcuts"""
        try:
            import winshell
            from win32com.client import Dispatch
            
            desktop = winshell.desktop()
            
            if self.install_type.get() == "server":
                shortcut_name = "Render Farm Server"
                target = str(install_path / "main_app.py")
            else:
                shortcut_name = "Render Farm Worker"
                target = str(install_path / "worker_node.py")
            
            shell = Dispatch('WScript.Shell')
            shortcut = shell.CreateShortCut(os.path.join(desktop, f"{shortcut_name}.lnk"))
            shortcut.Targetpath = sys.executable
            shortcut.Arguments = f'"{target}"'
            shortcut.WorkingDirectory = str(install_path)
            shortcut.IconLocation = sys.executable
            shortcut.save()
            
            self.log_message(f"✓ Created desktop shortcut: {shortcut_name}")
            
        except ImportError:
            self.log_message("⚠ pywin32 not available, skipping shortcuts")
        except Exception as e:
            self.log_message(f"⚠ Failed to create shortcuts: {e}")
    
    def create_linux_shortcuts(self, install_path):
        """Create Linux desktop shortcuts"""
        try:
            desktop_dir = Path.home() / "Desktop"
            if not desktop_dir.exists():
                desktop_dir = Path.home() / ".local" / "share" / "applications"
                desktop_dir.mkdir(parents=True, exist_ok=True)
            
            if self.install_type.get() == "server":
                shortcut_name = "render-farm-server"
                exec_cmd = f'python3 "{install_path / "main_app.py"}"'
                display_name = "Render Farm Server"
            else:
                shortcut_name = "render-farm-worker"
                exec_cmd = f'python3 "{install_path / "worker_node.py"}"'
                display_name = "Render Farm Worker"
            
            desktop_content = f"""[Desktop Entry]
Name={display_name}
Comment=VFX Render Farm {self.install_type.get().title()}
Exec={exec_cmd}
Icon=applications-multimedia
Terminal=false
Type=Application
Categories=Graphics;Video;
"""
            
            shortcut_file = desktop_dir / f"{shortcut_name}.desktop"
            with open(shortcut_file, 'w') as f:
                f.write(desktop_content)
            
            # Make executable
            shortcut_file.chmod(0o755)
            
            self.log_message(f"✓ Created desktop shortcut: {display_name}")
            
        except Exception as e:
            self.log_message(f"⚠ Failed to create shortcuts: {e}")
    
    def create_startup_service(self, install_path):
        """Create startup service/script"""
        if platform.system() == "Windows":
            self.create_windows_service(install_path)
        else:
            self.create_linux_service(install_path)
    
    def create_windows_service(self, install_path):
        """Create Windows startup script"""
        try:
            startup_folder = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
            
            if self.install_type.get() == "server":
                script_name = "RenderFarmServer.bat"
                script_content = f'''@echo off
cd /d "{install_path}"
python "{install_path / "main_app.py"}"
'''
            else:
                script_name = "RenderFarmWorker.bat"
                script_content = f'''@echo off
cd /d "{install_path}"
python "{install_path / "worker_node.py"}" --server {self.server_ip.get()}:{self.server_port.get()}
'''
            
            script_file = startup_folder / script_name
            with open(script_file, 'w') as f:
                f.write(script_content)
            
            self.log_message(f"✓ Created startup script: {script_name}")
            
        except Exception as e:
            self.log_message(f"⚠ Failed to create startup script: {e}")
    
    def create_linux_service(self, install_path):
        """Create Linux systemd service"""
        self.log_message("ℹ Manual service setup required on Linux")
        self.log_message("  See documentation for systemd service configuration")
    
    def launch_application(self):
        """Launch the installed application"""
        install_path = Path(self.install_path.get())
        
        try:
            if self.install_type.get() == "server":
                script = install_path / "main_app.py"
            else:
                script = install_path / "worker_node.py"
            
            if platform.system() == "Windows":
                subprocess.Popen([sys.executable, str(script)], 
                               cwd=str(install_path))
            else:
                subprocess.Popen([sys.executable, str(script)], 
                               cwd=str(install_path))
            
            self.log_message("✓ Application launched")
            
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch application:\\n{e}")
    
    def open_install_folder(self):
        """Open installation folder"""
        install_path = self.install_path.get()
        
        if platform.system() == "Windows":
            os.startfile(install_path)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", install_path])
        else:  # Linux
            subprocess.run(["xdg-open", install_path])
    def create_complete_page(self):
        """Create installation complete page"""
        page = tk.Frame(self.page_container)
        self.pages.append(page)
        
        # Success content
        success_frame = tk.Frame(page)
        success_frame.pack(expand=True, fill="both", padx=30, pady=40)
        
        # Success icon and title
        success_label = tk.Label(success_frame, text="Installation Complete!", 
                                font=("Arial", 18, "bold"), fg="#27ae60")
        success_label.pack(pady=(0, 20))
        
        # Summary based on installation type
        if self.install_type.get() == "server":
            summary_text = """Server installation completed successfully!
            
Your Render Farm Server is now ready:
• Web interface: http://localhost:8080
• Desktop shortcut created
• Service configured (if selected)

Next steps:
1. Launch the server application
2. Configure worker machines
3. Submit your first render job"""
        else:
            summary_text = f"""Worker installation completed successfully!
            
Your Worker Node is now ready:
• Server connection: {self.server_ip.get()}:{self.server_port.get()}
• Desktop shortcut created
• Service configured (if selected)

The worker will automatically:
1. Connect to the server
2. Register for render jobs
3. Start processing tasks"""
        
        summary_label = tk.Label(success_frame, text=summary_text, 
                                font=("Arial", 10), justify="left")
        summary_label.pack(pady=20)
        
        # Action buttons
        action_frame = tk.Frame(success_frame)
        action_frame.pack(pady=20)
        
        launch_btn = tk.Button(action_frame, text="Launch Application", 
                              command=self.launch_application,
                              bg="#3498db", fg="white", font=("Arial", 10, "bold"),
                              width=15)
        launch_btn.pack(side="left", padx=10)
        
        finish_btn = tk.Button(action_frame, text="Finish", 
                              command=self.root.quit,
                              bg="#95a5a6", fg="white", font=("Arial", 10, "bold"),
                              width=15)
        finish_btn.pack(side="left", padx=10)
    
    def run(self):
        """Run the installer"""
        self.root.mainloop()

def main():
    """Main entry point"""
    # Check if running as admin/root
    if platform.system() == "Windows":
        try:
            import ctypes
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
            if not is_admin:
                print("Note: Running without administrator privileges")
        except:
            pass
    
    installer = RenderFarmInstaller()
    installer.run()

if __name__ == "__main__":
    main()