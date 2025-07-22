#!/usr/bin/env python3
"""
Unified Render Farm Application
Can run as Server, Worker, or Both
"""

import sys
import os
import json
import subprocess
import threading
import socket
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QRadioButton,
                             QLineEdit, QTextEdit, QGroupBox, QGridLayout,
                             QTabWidget, QMessageBox, QSystemTrayIcon, QMenu)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QPixmap

# Import our components
try:
    from job_queue_manager import JobQueueManager
    from worker_node import ProductionRenderWorker
    PRODUCTION_MODE = True
except ImportError:
    from job_queue_manager import JobQueueManager as JobQueueManager
    from worker_node import RenderWorker as ProductionRenderWorker
    PRODUCTION_MODE = False

class ServerThread(QThread):
    status_signal = pyqtSignal(str)
    
    def __init__(self, port=8080):
        super().__init__()
        self.port = port
        self.running = False
    
    def run(self):
        try:
            from http.server import HTTPServer
            if PRODUCTION_MODE:
                from server import RenderFarmAPIHandler
            else:
                from server import RenderFarmAPIHandler
            
            server_address = ('', self.port)
            httpd = HTTPServer(server_address, RenderFarmAPIHandler)
            
            self.status_signal.emit(f"✅ Server started on port {self.port}")
            self.running = True
            
            while self.running:
                httpd.handle_request()
                
        except Exception as e:
            self.status_signal.emit(f"❌ Server error: {e}")
    
    def stop(self):
        self.running = False

class WorkerThread(QThread):
    status_signal = pyqtSignal(str)
    
    def __init__(self, server_url, worker_id=None):
        super().__init__()
        self.server_url = server_url
        self.worker_id = worker_id
        self.worker = None
    
    def run(self):
        try:
            self.worker = ProductionRenderWorker(self.server_url, self.worker_id)
            self.status_signal.emit("✅ Worker connected")
            self.worker.start()
        except Exception as e:
            self.status_signal.emit(f"❌ Worker error: {e}")
    
    def stop(self):
        if self.worker:
            self.worker.stop()

class RenderFarmApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎬 Render Farm Control Center")
        self.setGeometry(100, 100, 800, 600)
        
        # Threads
        self.server_thread = None
        self.worker_thread = None
        self.gui_process = None
        
        # Config
        self.config_file = "app_config.json"
        self.config = self.load_config()
        
        self.init_ui()
        self.setup_system_tray()
    
    def load_config(self):
        default_config = {
            "mode": "server",
            "server_port": 8080,
            "server_url": "http://localhost:8080",
            "worker_name": socket.gethostname(),
            "auto_start": False
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except:
            pass
        
        return default_config
    
    def save_config(self):
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Failed to save config: {e}")
    
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Header
        header = QLabel("🎬 Render Farm Control Center")
        header.setStyleSheet("font-size: 20px; font-weight: bold; margin: 10px;")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Tabs
        tabs = QTabWidget()
        
        # Configuration Tab
        config_tab = self.create_config_tab()
        tabs.addTab(config_tab, "Configuration")
        
        # Control Tab
        control_tab = self.create_control_tab()
        tabs.addTab(control_tab, "Control")
        
        # Status Tab
        status_tab = self.create_status_tab()
        tabs.addTab(status_tab, "Status")
        
        layout.addWidget(tabs)
        
        # Load saved config
        self.load_ui_from_config()
    
    def create_config_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Mode selection
        mode_group = QGroupBox("Application Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.server_radio = QRadioButton("Server Mode (Control machine)")
        self.worker_radio = QRadioButton("Worker Mode (Render machine)")
        self.both_radio = QRadioButton("Both (Testing/Development)")
        
        mode_layout.addWidget(self.server_radio)
        mode_layout.addWidget(self.worker_radio)
        mode_layout.addWidget(self.both_radio)
        layout.addWidget(mode_group)
        
        # Server settings
        server_group = QGroupBox("Server Settings")
        server_layout = QGridLayout(server_group)
        
        server_layout.addWidget(QLabel("Port:"), 0, 0)
        self.port_edit = QLineEdit("8080")
        server_layout.addWidget(self.port_edit, 0, 1)
        
        layout.addWidget(server_group)
        
        # Worker settings
        worker_group = QGroupBox("Worker Settings")
        worker_layout = QGridLayout(worker_group)
        
        worker_layout.addWidget(QLabel("Server URL:"), 0, 0)
        self.server_url_edit = QLineEdit("http://192.168.1.100:8080")
        worker_layout.addWidget(self.server_url_edit, 0, 1)
        
        worker_layout.addWidget(QLabel("Worker Name:"), 1, 0)
        self.worker_name_edit = QLineEdit(socket.gethostname())
        worker_layout.addWidget(self.worker_name_edit, 1, 1)
        
        layout.addWidget(worker_group)
        
        # Auto-detect IP
        ip_label = QLabel(f"Local IP: {self.get_local_ip()}")
        ip_label.setStyleSheet("background: #E8F5E8; padding: 10px; border-radius: 5px;")
        layout.addWidget(ip_label)
        
        # Save button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_ui_config)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        return widget
    
    def create_control_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Quick start buttons
        quick_group = QGroupBox("Quick Start")
        quick_layout = QHBoxLayout(quick_group)
        
        self.start_server_btn = QPushButton("Start Server")
        self.start_server_btn.clicked.connect(self.start_server)
        quick_layout.addWidget(self.start_server_btn)
        
        self.start_worker_btn = QPushButton("Start Worker")
        self.start_worker_btn.clicked.connect(self.start_worker)
        quick_layout.addWidget(self.start_worker_btn)
        
        self.start_gui_btn = QPushButton("Open Render GUI")
        self.start_gui_btn.clicked.connect(self.start_gui)
        quick_layout.addWidget(self.start_gui_btn)
        
        layout.addWidget(quick_group)
        
        # Control buttons
        control_group = QGroupBox("Control")
        control_layout = QHBoxLayout(control_group)
        
        self.stop_all_btn = QPushButton("Stop All")
        self.stop_all_btn.clicked.connect(self.stop_all)
        control_layout.addWidget(self.stop_all_btn)
        
        self.restart_btn = QPushButton("Restart")
        self.restart_btn.clicked.connect(self.restart_all)
        control_layout.addWidget(self.restart_btn)
        
        layout.addWidget(control_group)
        
        layout.addStretch()
        return widget
    
    def create_status_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Status display
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(400)
        layout.addWidget(self.status_text)
        
        # Clear button
        clear_btn = QPushButton("Clear Log")
        clear_btn.clicked.connect(self.status_text.clear)
        layout.addWidget(clear_btn)
        
        return widget
    
    def setup_system_tray(self):
        """Setup system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon()
            
            # Create icon (using text as icon for simplicity)
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.blue)
            self.tray_icon.setIcon(QIcon(pixmap))
            
            # Tray menu
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction("Show")
            show_action.triggered.connect(self.show)
            
            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(self.close)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.show()
    
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"
    
    def load_ui_from_config(self):
        """Load UI state from config"""
        mode = self.config.get("mode", "server")
        if mode == "server":
            self.server_radio.setChecked(True)
        elif mode == "worker":
            self.worker_radio.setChecked(True)
        else:
            self.both_radio.setChecked(True)
        
        self.port_edit.setText(str(self.config.get("server_port", 8080)))
        self.server_url_edit.setText(self.config.get("server_url", ""))
        self.worker_name_edit.setText(self.config.get("worker_name", ""))
    
    def save_ui_config(self):
        """Save UI state to config"""
        if self.server_radio.isChecked():
            self.config["mode"] = "server"
        elif self.worker_radio.isChecked():
            self.config["mode"] = "worker"
        else:
            self.config["mode"] = "both"
        
        self.config["server_port"] = int(self.port_edit.text())
        self.config["server_url"] = self.server_url_edit.text()
        self.config["worker_name"] = self.worker_name_edit.text()
        
        self.save_config()
        QMessageBox.information(self, "Success", "Configuration saved!")
    
    def log_status(self, message):
        """Add message to status log"""
        timestamp = QTimer().remainingTime()
        self.status_text.append(f"[{timestamp}] {message}")
    
    def start_server(self):
        """Start render server"""
        if self.server_thread and self.server_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Server already running")
            return
        
        port = int(self.port_edit.text())
        self.server_thread = ServerThread(port)
        self.server_thread.status_signal.connect(self.log_status)
        self.server_thread.start()
        
        self.log_status(f"Starting server on port {port}...")
    
    def start_worker(self):
        """Start render worker"""
        if self.worker_thread and self.worker_thread.isRunning():
            QMessageBox.warning(self, "Warning", "Worker already running")
            return
        
        server_url = self.server_url_edit.text()
        worker_name = self.worker_name_edit.text()
        
        if not server_url:
            QMessageBox.warning(self, "Warning", "Please enter server URL")
            return
        
        self.worker_thread = WorkerThread(server_url, worker_name)
        self.worker_thread.status_signal.connect(self.log_status)
        self.worker_thread.start()
        
        self.log_status(f"Starting worker: {worker_name}")
    
    def start_gui(self):
        """Start render GUI"""
        if self.gui_process and self.gui_process.poll() is None:
            QMessageBox.warning(self, "Warning", "GUI already running")
            return
        
        try:
            # Try to start the main GUI
            if PRODUCTION_MODE:
                self.gui_process = subprocess.Popen([sys.executable, 'main_app.py'])
            else:
                self.gui_process = subprocess.Popen([sys.executable, 'main_app.py'])
            self.log_status("✅ Render GUI started")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to start GUI: {e}")
    
    def stop_all(self):
        """Stop all services"""
        # Stop server
        if self.server_thread and self.server_thread.isRunning():
            self.server_thread.stop()
            self.server_thread.wait(5000)
            self.log_status("🛑 Server stopped")
        
        # Stop worker
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.stop()
            self.worker_thread.wait(5000)
            self.log_status("🛑 Worker stopped")
        
        # Stop GUI
        if self.gui_process and self.gui_process.poll() is None:
            self.gui_process.terminate()
            self.log_status("🛑 GUI stopped")
    
    def restart_all(self):
        """Restart all services"""
        self.stop_all()
        QTimer.singleShot(2000, self.auto_start_services)  # Wait 2 seconds
    
    def auto_start_services(self):
        """Auto-start based on configuration"""
        mode = self.config.get("mode", "server")
        
        if mode in ["server", "both"]:
            self.start_server()
            QTimer.singleShot(3000, self.start_gui)  # Start GUI after server
        
        if mode in ["worker", "both"]:
            self.start_worker()
    
    def closeEvent(self, event):
        """Handle application close"""
        reply = QMessageBox.question(
            self, "Confirm Exit",
            "Stop all services and exit?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.stop_all()
            event.accept()
        else:
            event.ignore()

def create_executable():
    """Instructions for creating executable"""
    setup_script = '''
# Create executable with PyInstaller
# 1. Install PyInstaller: pip install pyinstaller
# 2. Run: pyinstaller --onefile --windowed --name "RenderFarm" render_farm_app.py
# 3. Executable will be in dist/ folder

# For icon: --icon=icon.ico
# For console: remove --windowed
'''
    return setup_script

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Render Farm")
    
    # Handle command line args
    if len(sys.argv) > 1:
        if sys.argv[1] == "--server":
            # Run as server only
            from server import main as server_main
            server_main()
            return
        elif sys.argv[1] == "--worker":
            # Run as worker only
            server_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8080"
            worker = ProductionRenderWorker(server_url)
            worker.start()
            return
    
    # Run GUI application
    window = RenderFarmApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
