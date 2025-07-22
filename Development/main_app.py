import sys
import socket
import os
import json
import threading
import time
import platform
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QGridLayout, QLabel, QLineEdit, 
                             QPushButton, QCheckBox, QRadioButton, QComboBox,
                             QGroupBox, QTabWidget, QTextEdit, QFileDialog,
                             QMenuBar, QAction, QSpinBox, QFrame, QMessageBox,
                             QTableWidget, QTableWidgetItem, QProgressBar)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer, QThread
from PyQt5.QtGui import QFont, QIcon, QPalette, QColor

# Import our render farm components
from job_queue_manager import JobQueueManager
from distributed_renderers import DistributedNukeRenderer, DistributedSilhouetteRenderer, DistributedFusionRenderer
from worker_deployment_manager import WorkerDeploymentManager

class JobMonitorThread(QThread):
    update_signal = pyqtSignal(list)
    
    def __init__(self, queue_manager):
        super().__init__()
        self.queue_manager = queue_manager
        self.running = True
        
    def run(self):
        while self.running:
            jobs = self.queue_manager.get_all_jobs()
            self.update_signal.emit(jobs)
            time.sleep(2)  # Update every 2 seconds
            
    def stop(self):
        self.running = False

class RenderLauncherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🚀 Render Launcher v0.2 - Distributed")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(1000, 700)
        
        # Initialize job queue manager and worker deployment
        self.queue_manager = JobQueueManager()
        self.worker_deployment = WorkerDeploymentManager()
        
        # Auto-deploy workers if enabled
        self.auto_deploy_workers_on_startup()
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #e1e1e1;
                border: 1px solid #adadad;
                border-radius: 3px;
                padding: 5px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #d4edda;
            }
            QPushButton:pressed {
                background-color: #c3e6cb;
            }
            QLineEdit, QComboBox, QSpinBox {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
            }
            QTabWidget::pane {
                border: 1px solid #cccccc;
            }
            QTabBar::tab {
                background-color: #e1e1e1;
                border: 1px solid #cccccc;
                padding: 8px 12px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTableWidget {
                background-color: white;
                gridline-color: #cccccc;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        
        self.init_ui()
        self.start_monitoring()
        
    def init_ui(self):
        # Create menu bar
        self.create_menu_bar()
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        
        # Header with worker status
        header_layout = QHBoxLayout()
        header_layout.addStretch()
        
        # Worker status
        self.worker_status_label = QLabel("🔴 Workers: 0/30 online")
        self.worker_status_label.setStyleSheet("font-size: 12px; font-weight: bold; padding: 5px;")
        header_layout.addWidget(self.worker_status_label)
        
        version_label = QLabel("Render Launcher v0.2")
        version_label.setStyleSheet("font-size: 10px; color: #666666; padding: 5px;")
        header_layout.addWidget(version_label)
        
        main_layout.addLayout(header_layout)
        
        # Server Details Group
        server_group = self.create_server_details_group()
        main_layout.addWidget(server_group)
        
        # Tabs
        self.tab_widget = QTabWidget()
        
        # Launch Options Tab
        launch_tab = self.create_launch_options_tab()
        self.tab_widget.addTab(launch_tab, "Launch Options")
        
        # Job Monitor Tab
        job_monitor_tab = self.create_job_monitor_tab()
        self.tab_widget.addTab(job_monitor_tab, "Job Monitor")
        
        # Worker Nodes Tab
        worker_nodes_tab = self.create_worker_nodes_tab()
        self.tab_widget.addTab(worker_nodes_tab, "Worker Nodes")
        
        # Worker Deployment Tab
        deployment_tab = self.create_worker_deployment_tab()
        self.tab_widget.addTab(deployment_tab, "Worker Deployment")
        
        main_layout.addWidget(self.tab_widget)
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_all_btn = QPushButton("Clear All")
        submit_btn = QPushButton("Submit Job")
        submit_btn.setStyleSheet("QPushButton { background-color: #007bff; color: white; font-weight: bold; }")
        
        clear_all_btn.clicked.connect(self.clear_all_fields)
        submit_btn.clicked.connect(self.submit_job)
        
        button_layout.addWidget(clear_all_btn)
        button_layout.addWidget(submit_btn)
        
        main_layout.addLayout(button_layout)
        
        # Footer
        footer_layout = QHBoxLayout()
        footer_label = QLabel("Licensed to ARONFX")
        footer_label.setStyleSheet("font-size: 10px; color: #666666;")
        footer_layout.addWidget(footer_label)
        footer_layout.addStretch()
        
        logo_label = QLabel("ARONFX")
        logo_label.setStyleSheet("font-size: 10px; color: #ff6600; font-weight: bold;")
        footer_layout.addWidget(logo_label)
        
        main_layout.addLayout(footer_layout)
        
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        file_menu.addAction('New Project', self.new_project)
        file_menu.addAction('Open Project', self.open_project)
        file_menu.addAction('Save Project', self.save_project)
        file_menu.addSeparator()
        file_menu.addAction('Exit', self.close)
        
        # Jobs menu
        jobs_menu = menubar.addMenu('Jobs')
        jobs_menu.addAction('Pause All Jobs', self.pause_all_jobs)
        jobs_menu.addAction('Resume All Jobs', self.resume_all_jobs)
        jobs_menu.addAction('Clear Completed', self.clear_completed_jobs)
        
        # Workers menu
        workers_menu = menubar.addMenu('Workers')
        workers_menu.addAction('Start All Workers', self.start_all_workers)
        workers_menu.addAction('Stop All Workers', self.stop_all_workers)
        workers_menu.addAction('Refresh Status', self.refresh_worker_status)
        
        # Settings menu
        settings_menu = menubar.addMenu('Settings')
        settings_menu.addAction('Configure Workers', self.configure_workers)
        settings_menu.addAction('Network Settings', self.network_settings)
        settings_menu.addAction('Shared Paths', self.configure_shared_paths)
        
        # Worker Deployment menu
        deploy_menu = menubar.addMenu('Worker Deployment')
        deploy_menu.addAction('Deploy All Workers', self.deploy_all_workers)
        deploy_menu.addAction('Stop All Workers', self.stop_all_workers)
        deploy_menu.addAction('Discover Network Machines', self.discover_network_machines)
        deploy_menu.addAction('Test Worker Connections', self.test_all_worker_connections)
        deploy_menu.addAction('Refresh Worker Status', self.refresh_deployment_status)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        help_menu.addAction('About', self.show_about)
        help_menu.addAction('Worker Setup Guide', self.show_worker_setup)
        
    def create_server_details_group(self):
        group = QGroupBox("Render Farm Details")
        layout = QGridLayout(group)
        
        # Queue Server
        queue_checkbox = QCheckBox("Queue Server")
        queue_checkbox.setChecked(True)
        self.queue_server_edit = QLineEdit("localhost:8080")
        
        # Shared Storage
        storage_checkbox = QCheckBox("Shared Storage")
        storage_checkbox.setChecked(True)
        self.shared_storage_edit = QLineEdit("//192.168.1.100/renderfarm")
        
        layout.addWidget(queue_checkbox, 0, 0)
        layout.addWidget(self.queue_server_edit, 0, 1)
        layout.addWidget(storage_checkbox, 1, 0)
        layout.addWidget(self.shared_storage_edit, 1, 1)
        
        return group
        
    def create_launch_options_tab(self):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Renderer Selection
        renderer_layout = QHBoxLayout()
        renderer_layout.addStretch()
        
        self.nuke_radio = QRadioButton("Nuke")
        self.silhouette_radio = QRadioButton("Silhouette")
        self.fusion_radio = QRadioButton("Fusion")
        self.nuke_radio.setChecked(True)
        
        # Connect radio buttons to update executable path
        self.nuke_radio.toggled.connect(self.update_executable_path)
        self.silhouette_radio.toggled.connect(self.update_executable_path)
        self.fusion_radio.toggled.connect(self.update_executable_path)
        
        renderer_layout.addWidget(self.nuke_radio)
        renderer_layout.addWidget(self.silhouette_radio)
        renderer_layout.addWidget(self.fusion_radio)
        renderer_layout.addStretch()
        
        layout.addLayout(renderer_layout)
        
        # Executable Path
        exec_layout = QHBoxLayout()
        self.exec_checkbox = QCheckBox("Executable Path")
        self.exec_checkbox.setChecked(True)
        self.exec_path_edit = QLineEdit("C:\\Program Files\\Nuke10.0v1\\Nuke11.0.exe")
        exec_browse_btn = QPushButton("Browse")
        exec_browse_btn.clicked.connect(self.browse_executable)
        
        exec_layout.addWidget(self.exec_checkbox)
        exec_layout.addWidget(self.exec_path_edit)
        exec_layout.addWidget(exec_browse_btn)
        
        layout.addLayout(exec_layout)
        
        # Main form fields
        form_layout = QGridLayout()
        
        # File Path
        form_layout.addWidget(QLabel("Project File"), 0, 0)
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select project file (.nk, .comp, .sfx)")
        file_browse_btn = QPushButton("Browse")
        file_browse_btn.clicked.connect(self.browse_file_path)
        
        file_layout = QHBoxLayout()
        file_layout.addWidget(self.file_path_edit)
        file_layout.addWidget(file_browse_btn)
        form_layout.addLayout(file_layout, 0, 1)
        
        # Job Title
        form_layout.addWidget(QLabel("Job Title"), 1, 0)
        self.job_title_edit = QLineEdit()
        self.job_title_edit.setPlaceholderText("Enter descriptive job name")
        form_layout.addWidget(self.job_title_edit, 1, 1)
        
        # Frame Range
        form_layout.addWidget(QLabel("Frame Range"), 2, 0)
        frame_layout = QHBoxLayout()
        self.frame_range_edit = QLineEdit()
        self.frame_range_edit.setPlaceholderText("1-100 or 1-50,60-100")
        frame_range_note = QLabel("( Add - or , in between frame range. ex:- [1-20,22,35] )")
        frame_range_note.setStyleSheet("color: #666666; font-size: 10px;")
        frame_layout.addWidget(self.frame_range_edit)
        frame_layout.addWidget(frame_range_note)
        form_layout.addLayout(frame_layout, 2, 1)
        
        # Batch Size
        form_layout.addWidget(QLabel("Batch Size"), 3, 0)
        batch_layout = QHBoxLayout()
        self.batch_size_spin = QSpinBox()
        self.batch_size_spin.setMinimum(1)
        self.batch_size_spin.setMaximum(1000)
        self.batch_size_spin.setValue(10)
        batch_note = QLabel("(Frames per worker)")
        batch_note.setStyleSheet("color: #666666; font-size: 10px;")
        batch_layout.addWidget(self.batch_size_spin)
        batch_layout.addWidget(batch_note)
        batch_layout.addStretch()
        form_layout.addLayout(batch_layout, 3, 1)
        
        # Priority
        form_layout.addWidget(QLabel("Priority"), 4, 0)
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["Low", "Normal", "High", "Critical"])
        self.priority_combo.setCurrentText("Normal")
        form_layout.addWidget(self.priority_combo, 4, 1)
        
        # Worker Pool
        form_layout.addWidget(QLabel("Worker Pool"), 5, 0)
        render_layout = QHBoxLayout()
        self.all_workers_checkbox = QCheckBox("All Workers")
        self.all_workers_checkbox.setChecked(True)
        self.specific_pool_label = QLabel("Specific Pool:")
        self.specific_pool_combo = QComboBox()
        self.specific_pool_combo.addItems(["Pool_A", "Pool_B", "Pool_C"])
        self.specific_pool_combo.setEnabled(False)
        
        self.all_workers_checkbox.stateChanged.connect(self.toggle_worker_pool)
        
        render_layout.addWidget(self.all_workers_checkbox)
        render_layout.addWidget(self.specific_pool_label)
        render_layout.addWidget(self.specific_pool_combo)
        render_layout.addStretch()
        form_layout.addLayout(render_layout, 5, 1)
        
        # Extra Arguments
        form_layout.addWidget(QLabel("Extra Arguments"), 6, 0)
        self.extra_args_edit = QLineEdit()
        self.extra_args_edit.setPlaceholderText("Additional command line arguments")
        form_layout.addWidget(self.extra_args_edit, 6, 1)
        
        layout.addLayout(form_layout)
        
        # Path Management Group
        paths_group = QGroupBox("Path Management")
        paths_layout = QGridLayout(paths_group)
        
        # Enable path translation
        self.enable_path_translation = QCheckBox("Enable Automatic Path Translation")
        self.enable_path_translation.setChecked(True)
        paths_layout.addWidget(self.enable_path_translation, 0, 0, 1, 2)
        
        # Network Share
        paths_layout.addWidget(QLabel("Network Share"), 1, 0)
        self.network_share_edit = QLineEdit("//192.168.1.100/projects")
        paths_layout.addWidget(self.network_share_edit, 1, 1)
        
        # Output path translation
        self.output_path_translate = QCheckBox("Translate output paths")
        self.output_path_translate.setChecked(True)
        paths_layout.addWidget(self.output_path_translate, 2, 0, 1, 2)
        
        layout.addWidget(paths_group)
        
        return tab_widget
        
    def create_job_monitor_tab(self):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        pause_job_btn = QPushButton("Pause Job")
        resume_job_btn = QPushButton("Resume Job")
        cancel_job_btn = QPushButton("Cancel Job")
        clear_completed_btn = QPushButton("Clear Completed")
        
        refresh_btn.clicked.connect(self.refresh_jobs)
        pause_job_btn.clicked.connect(self.pause_selected_job)
        resume_job_btn.clicked.connect(self.resume_selected_job)
        cancel_job_btn.clicked.connect(self.cancel_selected_job)
        clear_completed_btn.clicked.connect(self.clear_completed_jobs)
        
        controls_layout.addWidget(refresh_btn)
        controls_layout.addWidget(pause_job_btn)
        controls_layout.addWidget(resume_job_btn)
        controls_layout.addWidget(cancel_job_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(clear_completed_btn)
        
        layout.addLayout(controls_layout)
        
        # Job table
        self.job_table = QTableWidget()
        self.job_table.setColumnCount(8)
        self.job_table.setHorizontalHeaderLabels([
            "Job ID", "Title", "Status", "Progress", "Start Time", 
            "Worker", "Frames", "Priority"
        ])
        self.job_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.job_table)
        
        # Job details
        details_group = QGroupBox("Job Details")
        details_layout = QVBoxLayout(details_group)
        self.job_details_text = QTextEdit()
        self.job_details_text.setMaximumHeight(100)
        details_layout.addWidget(self.job_details_text)
        
        layout.addWidget(details_group)
        
        return tab_widget
        
    def create_worker_nodes_tab(self):
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        add_worker_btn = QPushButton("Add Worker")
        remove_worker_btn = QPushButton("Remove Worker")
        start_worker_btn = QPushButton("Start Worker")
        stop_worker_btn = QPushButton("Stop Worker")
        refresh_workers_btn = QPushButton("Refresh")
        
        add_worker_btn.clicked.connect(self.add_worker)
        remove_worker_btn.clicked.connect(self.remove_worker)
        start_worker_btn.clicked.connect(self.start_selected_worker)
        stop_worker_btn.clicked.connect(self.stop_selected_worker)
        refresh_workers_btn.clicked.connect(self.refresh_workers)
        
        controls_layout.addWidget(add_worker_btn)
        controls_layout.addWidget(remove_worker_btn)
        controls_layout.addWidget(start_worker_btn)
        controls_layout.addWidget(stop_worker_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(refresh_workers_btn)
        
        layout.addLayout(controls_layout)
        
        # Worker table
        self.worker_table = QTableWidget()
        self.worker_table.setColumnCount(6)
        self.worker_table.setHorizontalHeaderLabels([
            "Worker ID", "IP Address", "Status", "Current Job", 
            "CPU Usage", "Last Seen"
        ])
        self.worker_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        # Initialize empty worker table - will be populated with real workers
        self.populate_default_workers()
        
        layout.addWidget(self.worker_table)
        
        return tab_widget
    
    def create_worker_deployment_tab(self):
        """Create worker deployment management tab"""
        tab_widget = QWidget()
        layout = QVBoxLayout(tab_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        deploy_all_btn = QPushButton("🚀 Deploy All Workers")
        deploy_all_btn.setStyleSheet("QPushButton { background-color: #28a745; color: white; font-weight: bold; }")
        deploy_all_btn.clicked.connect(self.deploy_all_workers)
        
        stop_all_btn = QPushButton("🛑 Stop All Workers")
        stop_all_btn.setStyleSheet("QPushButton { background-color: #dc3545; color: white; font-weight: bold; }")
        stop_all_btn.clicked.connect(self.stop_all_workers)
        
        discover_btn = QPushButton("🔍 Discover Network")
        discover_btn.clicked.connect(self.discover_network_machines)
        
        test_connections_btn = QPushButton("🧪 Test Connections")
        test_connections_btn.clicked.connect(self.test_all_worker_connections)
        
        refresh_deployment_btn = QPushButton("🔄 Refresh Status")
        refresh_deployment_btn.clicked.connect(self.refresh_deployment_status)
        
        controls_layout.addWidget(deploy_all_btn)
        controls_layout.addWidget(stop_all_btn)
        controls_layout.addWidget(discover_btn)
        controls_layout.addWidget(test_connections_btn)
        controls_layout.addStretch()
        controls_layout.addWidget(refresh_deployment_btn)
        
        layout.addLayout(controls_layout)
        
        # Deployment status display
        status_group = QGroupBox("Deployment Status")
        status_layout = QVBoxLayout(status_group)
        
        self.deployment_status_text = QTextEdit()
        self.deployment_status_text.setMaximumHeight(100)
        self.deployment_status_text.setReadOnly(True)
        status_layout.addWidget(self.deployment_status_text)
        
        layout.addWidget(status_group)
        
        # Worker deployment table
        self.deployment_table = QTableWidget()
        self.deployment_table.setColumnCount(8)
        self.deployment_table.setHorizontalHeaderLabels([
            "Worker Name", "IP Address", "OS", "Status", "Connection", 
            "Auto Start", "Deployed At", "Actions"
        ])
        self.deployment_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        layout.addWidget(self.deployment_table)
        
        # Worker configuration
        config_group = QGroupBox("Worker Configuration")
        config_layout = QGridLayout(config_group)
        
        config_layout.addWidget(QLabel("Config File:"), 0, 0)
        self.config_file_label = QLabel("worker_machines.json")
        self.config_file_label.setStyleSheet("color: #666666; font-family: monospace;")
        config_layout.addWidget(self.config_file_label, 0, 1)
        
        edit_config_btn = QPushButton("📝 Edit Config")
        edit_config_btn.clicked.connect(self.edit_worker_config)
        config_layout.addWidget(edit_config_btn, 0, 2)
        
        reload_config_btn = QPushButton("🔄 Reload Config")
        reload_config_btn.clicked.connect(self.reload_worker_config)
        config_layout.addWidget(reload_config_btn, 0, 3)
        
        layout.addWidget(config_group)
        
        # Initialize deployment table
        self.refresh_deployment_status()
        
        return tab_widget
        
    def populate_default_workers(self):
        """Initialize empty worker table - will be populated with real workers"""
        self.worker_table.setRowCount(0)
        print("Worker table initialized - will show real workers when they connect")
    
    def start_monitoring(self):
        """Start background monitoring threads"""
        self.monitor_thread = JobMonitorThread(self.queue_manager)
        self.monitor_thread.update_signal.connect(self.update_job_table)
        self.monitor_thread.start()
        
        # Timer for worker status updates
        self.worker_timer = QTimer()
        self.worker_timer.timeout.connect(self.update_worker_status)
        self.worker_timer.start(5000)  # Every 5 seconds
    
    def update_executable_path(self):
        """Update executable path based on selected renderer"""
        if self.nuke_radio.isChecked():
            self.exec_path_edit.setText("C:\\Program Files\\Nuke10.0v1\\Nuke11.0.exe")
        elif self.silhouette_radio.isChecked():
            self.exec_path_edit.setText("C:\\Program Files\\SilhouetteFX\\Silhouette v6\\silhouette.exe")
        elif self.fusion_radio.isChecked():
            self.exec_path_edit.setText("C:\\Program Files\\Blackmagic Design\\Fusion 16\\Fusion.exe")
    
    def toggle_worker_pool(self, state):
        """Toggle between all workers and specific pool"""
        is_all_workers = state == Qt.Checked
        self.specific_pool_combo.setEnabled(not is_all_workers)
        
    def browse_executable(self):
        """Browse for executable file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Executable", 
            "", 
            "Executable Files (*.exe);;All Files (*.*)"
        )
        if file_path:
            self.exec_path_edit.setText(file_path)
            
    def browse_file_path(self):
        """Browse for project file"""
        renderer = self.get_selected_renderer()
        if renderer == "nuke":
            filter_str = "Nuke Scripts (*.nk);;All Files (*.*)"
        elif renderer == "silhouette":
            filter_str = "Silhouette Projects (*.sfx);;All Files (*.*)"
        elif renderer == "fusion":
            filter_str = "Fusion Compositions (*.comp);;All Files (*.*)"
        else:
            filter_str = "All Files (*.*)"
            
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Project File", 
            "", 
            filter_str
        )
        if file_path:
            self.file_path_edit.setText(file_path)
            if not self.job_title_edit.text():
                # Auto-fill job title from filename
                filename = os.path.splitext(os.path.basename(file_path))[0]
                self.job_title_edit.setText(filename)
    
    def get_selected_renderer(self):
        """Get currently selected renderer"""
        if self.nuke_radio.isChecked():
            return "nuke"
        elif self.silhouette_radio.isChecked():
            return "silhouette"
        elif self.fusion_radio.isChecked():
            return "fusion"
        return "nuke"
    
    def clear_all_fields(self):
        """Clear all input fields"""
        self.file_path_edit.clear()
        self.job_title_edit.clear()
        self.frame_range_edit.clear()
        self.batch_size_spin.setValue(10)
        self.extra_args_edit.clear()
        self.all_workers_checkbox.setChecked(True)
        self.enable_path_translation.setChecked(True)
        self.output_path_translate.setChecked(True)
        self.priority_combo.setCurrentText("Normal")
        
    def submit_job(self):
        """Submit render job to the distributed queue"""
        # Validate inputs
        if not self.file_path_edit.text():
            QMessageBox.warning(self, "Error", "Please select a project file")
            return
            
        if not self.job_title_edit.text():
            QMessageBox.warning(self, "Error", "Please enter a job title")
            return
            
        if not self.frame_range_edit.text():
            QMessageBox.warning(self, "Error", "Please enter a frame range")
            return
        
        # Collect job data
        job_data = {
            'renderer': self.get_selected_renderer(),
            'executable_path': self.exec_path_edit.text(),
            'file_path': self.file_path_edit.text(),
            'job_title': self.job_title_edit.text(),
            'frame_range': self.frame_range_edit.text(),
            'batch_size': self.batch_size_spin.value(),
            'priority': self.priority_combo.currentText(),
            'all_workers': self.all_workers_checkbox.isChecked(),
            'specific_pool': self.specific_pool_combo.currentText(),
            'extra_args': self.extra_args_edit.text(),
            'enable_path_translation': self.enable_path_translation.isChecked(),
            'network_share': self.network_share_edit.text(),
            'output_path_translate': self.output_path_translate.isChecked(),
            'queue_server': self.queue_server_edit.text(),
            'shared_storage': self.shared_storage_edit.text()
        }
        
        try:
            # Submit job to queue
            job_id = self.queue_manager.submit_job(job_data)
            
            # Process and distribute the job
            self.process_render_job(job_id, job_data)
            
            QMessageBox.information(self, "Success", f"Job '{job_data['job_title']}' submitted successfully!\nJob ID: {job_id}")
            
            # Switch to job monitor tab
            self.tab_widget.setCurrentIndex(1)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to submit job:\n{str(e)}")
    
    def process_render_job(self, job_id, job_data):
        """Process and distribute the render job"""
        renderer_type = job_data['renderer']
        
        # Create appropriate renderer
        if renderer_type == 'nuke':
            renderer = DistributedNukeRenderer(self.queue_manager)
        elif renderer_type == 'silhouette':
            renderer = DistributedSilhouetteRenderer(self.queue_manager)
        elif renderer_type == 'fusion':
            renderer = DistributedFusionRenderer(self.queue_manager)
        else:
            raise ValueError(f"Unknown renderer type: {renderer_type}")
        
        # Process the job (this will create sub-jobs for workers)
        renderer.process_job(job_id, job_data)
    
    def update_job_table(self, jobs):
        """Update the job monitor table"""
        self.job_table.setRowCount(len(jobs))
        
        for i, job in enumerate(jobs):
            self.job_table.setItem(i, 0, QTableWidgetItem(str(job['id'])))
            self.job_table.setItem(i, 1, QTableWidgetItem(job['title']))
            self.job_table.setItem(i, 2, QTableWidgetItem(job['status']))
            self.job_table.setItem(i, 3, QTableWidgetItem(f"{job['progress']:.1f}%"))
            self.job_table.setItem(i, 4, QTableWidgetItem(job['created_at']))
            self.job_table.setItem(i, 5, QTableWidgetItem(job.get('worker_id', 'N/A')))
            self.job_table.setItem(i, 6, QTableWidgetItem(job.get('frame_range', 'N/A')))
            self.job_table.setItem(i, 7, QTableWidgetItem(job.get('priority', 'Normal')))
    
    def update_worker_status(self):
        """Update worker status display and worker table"""
        online_workers = self.queue_manager.get_online_workers()
        total_workers = 30  # Target number
        
        if online_workers >= 20:
            color = "🟢"
        elif online_workers >= 10:
            color = "🟡"
        else:
            color = "🔴"
            
        self.worker_status_label.setText(f"{color} Workers: {online_workers}/{total_workers} online")
        
        # Update worker table with real workers
        self.update_worker_table()
    
    def update_worker_table(self):
        """Update worker table with real workers from database"""
        try:
            workers = self.queue_manager.get_all_workers()
            self.worker_table.setRowCount(len(workers))
            
            for i, worker in enumerate(workers):
                # Worker ID (full text)
                id_item = QTableWidgetItem(worker['id'])
                self.worker_table.setItem(i, 0, id_item)
                
                # IP Address
                ip_item = QTableWidgetItem(worker['ip_address'])
                self.worker_table.setItem(i, 1, ip_item)
                
                # Status with color coding
                status_item = QTableWidgetItem(worker['status'])
                if worker['status'].lower() == 'online':
                    status_item.setBackground(QColor(144, 238, 144))  # Light green
                    status_item.setForeground(QColor(0, 100, 0))     # Dark green text
                else:
                    status_item.setBackground(QColor(255, 182, 193))  # Light red
                    status_item.setForeground(QColor(139, 0, 0))     # Dark red text
                self.worker_table.setItem(i, 2, status_item)
                
                # Current Job
                job_item = QTableWidgetItem(worker.get('current_job_id', 'None'))
                self.worker_table.setItem(i, 3, job_item)
                
                # CPU Usage/Cores
                cpu_item = QTableWidgetItem(f"{worker.get('cpu_count', 0)} cores")
                self.worker_table.setItem(i, 4, cpu_item)
                
                # Last Seen
                last_seen = worker.get('last_heartbeat', 'Never')
                if last_seen != 'Never':
                    # Format timestamp to be more readable
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(last_seen.replace('Z', '+00:00'))
                        last_seen = dt.strftime('%H:%M:%S')
                    except:
                        pass
                time_item = QTableWidgetItem(last_seen)
                self.worker_table.setItem(i, 5, time_item)
            
            # Auto-resize columns to fit content
            self.worker_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"Error updating worker table: {e}")
    
    # Job control methods
    def refresh_jobs(self):
        jobs = self.queue_manager.get_all_jobs()
        self.update_job_table(jobs)
    
    def pause_selected_job(self):
        row = self.job_table.currentRow()
        if row >= 0:
            job_id = self.job_table.item(row, 0).text()
            self.queue_manager.pause_job(job_id)
            self.refresh_jobs()

    def resume_selected_job(self):
        row = self.job_table.currentRow()
        if row >= 0:
            job_id = self.job_table.item(row, 0).text()
            self.queue_manager.resume_job(job_id)
            self.refresh_jobs()

    def cancel_selected_job(self):
        row = self.job_table.currentRow()
        if row >= 0:
            job_id = self.job_table.item(row, 0).text()
            self.queue_manager.cancel_job(job_id)
            self.refresh_jobs()

    def remove_worker(self):
        row = self.worker_table.currentRow()
        if row >= 0:
            worker_id = self.worker_table.item(row, 0).text()
            self.queue_manager.remove_worker(worker_id)
            self.refresh_workers()

    def stop_selected_worker(self):
        row = self.worker_table.currentRow()
        if row >= 0:
            worker_id = self.worker_table.item(row, 0).text()
            self.queue_manager.stop_worker(worker_id)
            self.refresh_workers()

    def clear_completed_jobs(self):
        self.queue_manager.clear_completed_jobs()
        self.refresh_jobs()
        QMessageBox.information(self, "Success", "Completed jobs cleared")
        
    # Worker control methods
    def add_worker(self):
        from PyQt5.QtWidgets import QInputDialog
        worker_id, ok = QInputDialog.getText(self, 'Add Worker', 'Enter Worker ID:')
        if ok and worker_id:
            # Add worker manually to database
            self.queue_manager.register_worker(
                worker_id, "manual", socket.gethostname(), {"manual": True}
            )
            self.refresh_workers()

    def remove_worker(self):
        row = self.worker_table.currentRow()
        if row >= 0:
            worker_id = self.worker_table.item(row, 0).text()
            reply = QMessageBox.question(self, "Confirm", f"Remove worker {worker_id}?")
            if reply == QMessageBox.Yes:
                self.queue_manager.remove_worker(worker_id)
                self.refresh_workers()

    def start_selected_worker(self):
        QMessageBox.information(self, "Info", "Workers start automatically when worker_node.py runs")

    def stop_selected_worker(self):
        row = self.worker_table.currentRow()
        if row >= 0:
            worker_id = self.worker_table.item(row, 0).text()
            self.queue_manager.stop_worker(worker_id)
            self.refresh_workers()
            QMessageBox.information(self, "Info", f"Stop signal sent to {worker_id}")
    
    def refresh_workers(self):
        """Refresh worker table"""
        self.update_worker_table()
        print("Worker table refreshed")
    
    # Menu action methods
    def new_project(self):
        self.clear_all_fields()
    
    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    project_data = json.load(f)
                self.load_project_data(project_data)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project:\n{str(e)}")
    
    def save_project(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "JSON Files (*.json);;All Files (*.*)"
        )
        if file_path:
            try:
                project_data = self.get_project_data()
                with open(file_path, 'w') as f:
                    json.dump(project_data, f, indent=2)
                QMessageBox.information(self, "Success", "Project saved successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project:\n{str(e)}")
    
    def get_project_data(self):
        """Get current project settings as dictionary"""
        return {
            'renderer': self.get_selected_renderer(),
            'executable_path': self.exec_path_edit.text(),
            'file_path': self.file_path_edit.text(),
            'job_title': self.job_title_edit.text(),
            'frame_range': self.frame_range_edit.text(),
            'batch_size': self.batch_size_spin.value(),
            'priority': self.priority_combo.currentText(),
            'all_workers': self.all_workers_checkbox.isChecked(),
            'specific_pool': self.specific_pool_combo.currentText(),
            'extra_args': self.extra_args_edit.text(),
            'enable_path_translation': self.enable_path_translation.isChecked(),
            'network_share': self.network_share_edit.text(),
            'output_path_translate': self.output_path_translate.isChecked(),
            'queue_server': self.queue_server_edit.text(),
            'shared_storage': self.shared_storage_edit.text()
        }
    
    def load_project_data(self, data):
        """Load project settings from dictionary"""
        if data.get('renderer') == 'nuke':
            self.nuke_radio.setChecked(True)
        elif data.get('renderer') == 'silhouette':
            self.silhouette_radio.setChecked(True)
        elif data.get('renderer') == 'fusion':
            self.fusion_radio.setChecked(True)
            
        self.exec_path_edit.setText(data.get('executable_path', ''))
        self.file_path_edit.setText(data.get('file_path', ''))
        self.job_title_edit.setText(data.get('job_title', ''))
        self.frame_range_edit.setText(data.get('frame_range', ''))
        self.batch_size_spin.setValue(data.get('batch_size', 10))
        self.priority_combo.setCurrentText(data.get('priority', 'Normal'))
        self.all_workers_checkbox.setChecked(data.get('all_workers', True))
        self.specific_pool_combo.setCurrentText(data.get('specific_pool', ''))
        self.extra_args_edit.setText(data.get('extra_args', ''))
        self.enable_path_translation.setChecked(data.get('enable_path_translation', True))
        self.network_share_edit.setText(data.get('network_share', ''))
        self.output_path_translate.setChecked(data.get('output_path_translate', True))
        self.queue_server_edit.setText(data.get('queue_server', 'localhost:8080'))
        self.shared_storage_edit.setText(data.get('shared_storage', ''))
    
    def pause_all_jobs(self):
        self.queue_manager.pause_all_jobs()
        self.refresh_jobs()
    
    def resume_all_jobs(self):
        self.queue_manager.resume_all_jobs()
        self.refresh_jobs()
    
    def start_all_workers(self):
        QMessageBox.information(self, "Info", "Start all workers command sent")
    
    def stop_all_workers(self):
        QMessageBox.information(self, "Info", "Stop all workers command sent")
    
    def refresh_worker_status(self):
        self.update_worker_status()
        self.refresh_workers()
    
    def configure_workers(self):
        QMessageBox.information(self, "Info", "Worker configuration dialog (to be implemented)")
    
    def network_settings(self):
        QMessageBox.information(self, "Info", "Network settings dialog (to be implemented)")
    
    def configure_shared_paths(self):
        QMessageBox.information(self, "Info", "Shared paths configuration (to be implemented)")
    
    def show_about(self):
        QMessageBox.about(self, "About Render Launcher", 
                         "Render Launcher v0.2\n\n"
                         "Distributed Render Farm Management System\n"
                         "Built with PyQt5\n\n"
                         "Licensed to RotoMaker")
    
    def show_worker_setup(self):
        setup_text = """
Worker Setup Guide:

🚀 AUTOMATED DEPLOYMENT (Recommended):
1. Configure worker machines in 'Worker Deployment' tab
2. Click 'Deploy All Workers' to automatically start all workers
3. Monitor deployment status in real-time

📋 MANUAL DEPLOYMENT:
1. Copy worker_node.py to each render machine
2. Install required dependencies:
   pip install requests psutil aiofiles

3. Run worker on each machine:
   python worker_node.py --server http://192.168.1.100:8080

4. Workers will automatically register and start processing jobs

5. Monitor workers from the 'Worker Nodes' tab

🔧 CONFIGURATION:
- Edit worker_machines.json to add/remove worker machines
- Set up SSH/WinRM access for automated deployment
- Use 'Discover Network' to find available machines
        """
        QMessageBox.information(self, "Worker Setup Guide", setup_text)
    
    def closeEvent(self, event):
        """Enhanced clean shutdown with worker management"""
        reply = QMessageBox.question(self, 'Shutdown Confirmation', 
                                   'Do you want to stop all deployed workers before closing?',
                                   QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        
        if reply == QMessageBox.Cancel:
            event.ignore()
            return
        elif reply == QMessageBox.Yes:
            # Stop all workers
            if hasattr(self, 'worker_deployment'):
                try:
                    results = self.worker_deployment.stop_all_workers()
                    stopped_count = sum(1 for r in results.values() if r['success'])
                    QMessageBox.information(self, 'Workers Stopped', 
                                          f'Stopped {stopped_count} workers successfully')
                except Exception as e:
                    QMessageBox.warning(self, 'Warning', f'Error stopping workers: {e}')
        
        # Clean shutdown
        if hasattr(self, 'monitor_thread'):
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        if hasattr(self, 'worker_timer'):
            self.worker_timer.stop()
        event.accept()
    
    # Worker Deployment Methods
    def auto_deploy_workers_on_startup(self):
        """Auto-deploy workers on application startup if enabled"""
        try:
            if hasattr(self.worker_deployment, 'deployment_settings'):
                auto_deploy = self.worker_deployment.deployment_settings.get('auto_deploy_on_startup', False)
                if auto_deploy:
                    # Deploy in background thread to avoid blocking UI
                    deploy_thread = threading.Thread(target=self._background_deploy, daemon=True)
                    deploy_thread.start()
        except Exception as e:
            print(f"Auto-deployment error: {e}")
    
    def _background_deploy(self):
        """Background worker deployment"""
        try:
            time.sleep(2)  # Give UI time to load
            results = self.worker_deployment.deploy_all_workers()
            
            # Update UI in main thread
            successful = sum(1 for r in results.values() if r['success'])
            QTimer.singleShot(0, lambda: self.update_deployment_status(
                f"Auto-deployment completed: {successful}/{len(results)} workers started"
            ))
        except Exception as e:
            QTimer.singleShot(0, lambda: self.update_deployment_status(
                f"Auto-deployment failed: {e}"
            ))
    
    def deploy_all_workers(self):
        """Deploy all configured workers"""
        try:
            self.update_deployment_status("Starting deployment of all workers...")
            
            # Deploy in background thread
            def deploy_thread():
                try:
                    results = self.worker_deployment.deploy_all_workers()
                    successful = sum(1 for r in results.values() if r['success'])
                    
                    # Update UI
                    QTimer.singleShot(0, lambda: self.deployment_complete(results, successful))
                except Exception as e:
                    QTimer.singleShot(0, lambda: self.update_deployment_status(f"Deployment error: {e}"))
            
            threading.Thread(target=deploy_thread, daemon=True).start()
            
        except Exception as e:
            self.update_deployment_status(f"Failed to start deployment: {e}")
    
    def deployment_complete(self, results, successful):
        """Handle deployment completion"""
        total = len(results)
        self.update_deployment_status(f"Deployment complete: {successful}/{total} workers started successfully")
        
        # Show detailed results
        if successful < total:
            failed_workers = [name for name, result in results.items() if not result['success']]
            QMessageBox.warning(self, "Deployment Issues", 
                              f"Failed to deploy workers: {', '.join(failed_workers)}")
        else:
            QMessageBox.information(self, "Deployment Success", 
                                  f"All {successful} workers deployed successfully!")
        
        # Refresh status
        self.refresh_deployment_status()
    
    def stop_all_workers(self):
        """Stop all deployed workers"""
        try:
            reply = QMessageBox.question(self, 'Confirm Stop', 
                                       'Are you sure you want to stop all workers?',
                                       QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                self.update_deployment_status("Stopping all workers...")
                
                def stop_thread():
                    try:
                        results = self.worker_deployment.stop_all_workers()
                        stopped = sum(1 for r in results.values() if r['success'])
                        
                        QTimer.singleShot(0, lambda: self.workers_stopped(results, stopped))
                    except Exception as e:
                        QTimer.singleShot(0, lambda: self.update_deployment_status(f"Stop error: {e}"))
                
                threading.Thread(target=stop_thread, daemon=True).start()
                
        except Exception as e:
            self.update_deployment_status(f"Failed to stop workers: {e}")
    
    def workers_stopped(self, results, stopped):
        """Handle worker stop completion"""
        total = len(results)
        self.update_deployment_status(f"Workers stopped: {stopped}/{total} stopped successfully")
        QMessageBox.information(self, "Workers Stopped", f"Stopped {stopped} workers")
        self.refresh_deployment_status()
    
    def discover_network_machines(self):
        """Discover machines on network"""
        try:
            self.update_deployment_status("Discovering network machines...")
            
            def discover_thread():
                try:
                    machines = self.worker_deployment.discover_network_machines()
                    QTimer.singleShot(0, lambda: self.show_discovered_machines(machines))
                except Exception as e:
                    QTimer.singleShot(0, lambda: self.update_deployment_status(f"Discovery error: {e}"))
            
            threading.Thread(target=discover_thread, daemon=True).start()
            
        except Exception as e:
            self.update_deployment_status(f"Failed to start discovery: {e}")
    
    def show_discovered_machines(self, machines):
        """Show discovered machines"""
        self.update_deployment_status(f"Network discovery found {len(machines)} online machines")
        
        if machines:
            machine_list = "\n".join([f"• {m['hostname']} ({m['ip']})" for m in machines])
            QMessageBox.information(self, "Discovered Machines", 
                                  f"Found {len(machines)} online machines:\n\n{machine_list}")
        else:
            QMessageBox.information(self, "No Machines Found", 
                                  "No machines discovered on the network")
    
    def test_all_worker_connections(self):
        """Test connections to all configured workers"""
        try:
            self.update_deployment_status("Testing worker connections...")
            
            def test_thread():
                try:
                    results = {}
                    for worker_config in self.worker_deployment.worker_configs:
                        worker_name = worker_config['name']
                        connected, message = self.worker_deployment.test_worker_connection(worker_config)
                        results[worker_name] = {'connected': connected, 'message': message}
                    
                    QTimer.singleShot(0, lambda: self.show_connection_results(results))
                except Exception as e:
                    QTimer.singleShot(0, lambda: self.update_deployment_status(f"Connection test error: {e}"))
            
            threading.Thread(target=test_thread, daemon=True).start()
            
        except Exception as e:
            self.update_deployment_status(f"Failed to test connections: {e}")
    
    def show_connection_results(self, results):
        """Show connection test results"""
        connected_count = sum(1 for r in results.values() if r['connected'])
        total_count = len(results)
        
        self.update_deployment_status(f"Connection test complete: {connected_count}/{total_count} workers reachable")
        
        if results:
            result_text = "\n".join([
                f"{'✅' if r['connected'] else '❌'} {name}: {r['message']}"
                for name, r in results.items()
            ])
            QMessageBox.information(self, "Connection Test Results", result_text)
    
    def refresh_deployment_status(self):
        """Refresh worker deployment status"""
        try:
            status = self.worker_deployment.get_worker_status()
            
            # Update deployment table
            self.deployment_table.setRowCount(len(status['workers']))
            
            for i, worker in enumerate(status['workers']):
                self.deployment_table.setItem(i, 0, QTableWidgetItem(worker['name']))
                self.deployment_table.setItem(i, 1, QTableWidgetItem(worker['ip']))
                self.deployment_table.setItem(i, 2, QTableWidgetItem(worker.get('os', 'windows').title()))
                
                # Status with color coding
                status_item = QTableWidgetItem(worker['status'].replace('_', ' ').title())
                if worker['status'] == 'running':
                    status_item.setBackground(QColor(144, 238, 144))  # Light green
                elif worker['status'] == 'not_deployed':
                    status_item.setBackground(QColor(255, 255, 200))  # Light yellow
                else:
                    status_item.setBackground(QColor(255, 182, 193))  # Light red
                self.deployment_table.setItem(i, 3, status_item)
                
                # Connection status (placeholder)
                self.deployment_table.setItem(i, 4, QTableWidgetItem("Unknown"))
                
                # Auto start
                auto_start = "Yes" if worker.get('auto_start', True) else "No"
                self.deployment_table.setItem(i, 5, QTableWidgetItem(auto_start))
                
                # Deployed at
                deployed_at = worker.get('deployed_at', 'Never')
                if deployed_at != 'Never':
                    try:
                        dt = datetime.fromisoformat(deployed_at.replace('Z', '+00:00'))
                        deployed_at = dt.strftime('%H:%M:%S')
                    except:
                        pass
                self.deployment_table.setItem(i, 6, QTableWidgetItem(deployed_at))
                
                # Actions (placeholder)
                self.deployment_table.setItem(i, 7, QTableWidgetItem("Manual"))
            
            # Auto-resize columns
            self.deployment_table.resizeColumnsToContents()
            
            # Update status summary
            summary = f"Workers: {status['total_deployed']}/{status['total_configured']} deployed"
            self.update_deployment_status(summary)
            
        except Exception as e:
            self.update_deployment_status(f"Status refresh error: {e}")
    
    def update_deployment_status(self, message):
        """Update deployment status display"""
        if hasattr(self, 'deployment_status_text'):
            timestamp = datetime.now().strftime('%H:%M:%S')
            self.deployment_status_text.append(f"[{timestamp}] {message}")
            
            # Keep only last 50 messages
            content = self.deployment_status_text.toPlainText()
            lines = content.split('\n')
            if len(lines) > 50:
                self.deployment_status_text.setPlainText('\n'.join(lines[-50:]))
            
            # Scroll to bottom
            cursor = self.deployment_status_text.textCursor()
            cursor.movePosition(cursor.End)
            self.deployment_status_text.setTextCursor(cursor)
    
    def edit_worker_config(self):
        """Open worker configuration for editing"""
        config_file = "worker_machines.json"
        if os.path.exists(config_file):
            if platform.system() == 'Windows':
                os.startfile(config_file)
            else:
                import subprocess
                subprocess.call(['xdg-open', config_file])
        else:
            QMessageBox.information(self, "Config File", 
                                  f"Configuration file {config_file} will be created when you deploy workers")
    
    def reload_worker_config(self):
        """Reload worker configuration from file"""
        try:
            self.worker_deployment.load_worker_configs()
            self.refresh_deployment_status()
            QMessageBox.information(self, "Config Reloaded", "Worker configuration reloaded successfully")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reload configuration: {e}")

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = RenderLauncherApp()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()