import os
import sys
import json
import time
import socket
import threading
import subprocess
import platform
import psutil
import logging
from pathlib import Path
from datetime import datetime
import paramiko
import winrm

logger = logging.getLogger(__name__)

class WorkerDeploymentManager:
    """Manages remote worker node deployment and control"""
    
    def __init__(self, server_url="http://localhost:8080"):
        self.server_url = server_url
        self.worker_configs = []
        self.deployed_workers = {}
        self.deployment_lock = threading.Lock()
        
        # Load worker configurations
        self.config_file = "worker_machines.json"
        self.load_worker_configs()
        
        logger.info("Worker Deployment Manager initialized")
    
    def load_worker_configs(self):
        """Load worker machine configurations"""
        default_config = {
            "worker_machines": [
                {
                    "name": "Worker-01",
                    "ip": "192.168.1.101",
                    "username": "admin",
                    "password": "password",
                    "os": "windows",
                    "worker_path": "C:\\RenderFarm\\worker_node.py",
                    "python_path": "python",
                    "enabled": True,
                    "auto_start": True
                },
                {
                    "name": "Worker-02", 
                    "ip": "192.168.1.102",
                    "username": "admin",
                    "password": "password",
                    "os": "windows",
                    "worker_path": "C:\\RenderFarm\\worker_node.py",
                    "python_path": "python",
                    "enabled": True,
                    "auto_start": True
                }
            ],
            "deployment_settings": {
                "connection_timeout": 30,
                "deployment_timeout": 120,
                "retry_attempts": 3,
                "auto_deploy_on_startup": True,
                "health_check_interval": 60
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                self.worker_configs = config.get('worker_machines', [])
                self.deployment_settings = config.get('deployment_settings', default_config['deployment_settings'])
            else:
                # Create default config file
                with open(self.config_file, 'w') as f:
                    json.dump(default_config, f, indent=2)
                self.worker_configs = default_config['worker_machines']
                self.deployment_settings = default_config['deployment_settings']
                logger.info(f"Created default worker config: {self.config_file}")
                
        except Exception as e:
            logger.error(f"Failed to load worker configs: {e}")
            self.worker_configs = []
            self.deployment_settings = default_config['deployment_settings']
    
    def save_worker_configs(self):
        """Save worker configurations to file"""
        try:
            config = {
                "worker_machines": self.worker_configs,
                "deployment_settings": self.deployment_settings
            }
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info("Worker configurations saved")
        except Exception as e:
            logger.error(f"Failed to save worker configs: {e}")
    
    def discover_network_machines(self):
        """Discover machines on the network that could be workers"""
        discovered_machines = []
        
        try:
            # Get local network range
            local_ip = self.get_local_ip()
            network_base = '.'.join(local_ip.split('.')[:-1])
            
            logger.info(f"Scanning network {network_base}.0/24 for potential workers...")
            
            def ping_host(ip):
                try:
                    if platform.system().lower() == 'windows':
                        result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip], 
                                              capture_output=True, text=True)
                    else:
                        result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                              capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        # Try to get hostname
                        try:
                            hostname = socket.gethostbyaddr(ip)[0]
                        except:
                            hostname = f"Machine-{ip.split('.')[-1]}"
                        
                        discovered_machines.append({
                            'ip': ip,
                            'hostname': hostname,
                            'status': 'online',
                            'discovered_at': datetime.now().isoformat()
                        })
                        logger.debug(f"Found machine: {hostname} ({ip})")
                except:
                    pass
            
            # Ping sweep (first 50 IPs for speed)
            threads = []
            for i in range(1, 51):
                ip = f"{network_base}.{i}"
                if ip != local_ip:  # Skip local machine
                    thread = threading.Thread(target=ping_host, args=(ip,))
                    thread.start()
                    threads.append(thread)
            
            # Wait for all pings to complete
            for thread in threads:
                thread.join(timeout=2)
            
            logger.info(f"Network discovery found {len(discovered_machines)} online machines")
            return discovered_machines
            
        except Exception as e:
            logger.error(f"Network discovery failed: {e}")
            return []
    
    def test_worker_connection(self, worker_config):
        """Test connection to a worker machine"""
        try:
            ip = worker_config['ip']
            username = worker_config['username']
            password = worker_config['password']
            os_type = worker_config.get('os', 'windows').lower()
            
            if os_type == 'windows':
                return self._test_windows_connection(ip, username, password)
            else:
                return self._test_ssh_connection(ip, username, password)
                
        except Exception as e:
            logger.error(f"Connection test failed for {worker_config['name']}: {e}")
            return False, str(e)
    
    def _test_windows_connection(self, ip, username, password):
        """Test Windows connection via WinRM"""
        try:
            session = winrm.Session(f'http://{ip}:5985/wsman', auth=(username, password))
            result = session.run_cmd('echo "test"')
            
            if result.status_code == 0:
                return True, "Windows connection successful"
            else:
                return False, f"WinRM error: {result.std_err.decode()}"
                
        except Exception as e:
            # Fallback to simple ping
            if platform.system().lower() == 'windows':
                result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip], 
                                      capture_output=True)
            else:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                      capture_output=True)
            
            if result.returncode == 0:
                return True, f"Machine reachable (WinRM not available: {e})"
            else:
                return False, f"Machine unreachable: {e}"
    
    def _test_ssh_connection(self, ip, username, password):
        """Test SSH connection for Linux/Mac"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=username, password=password, timeout=10)
            
            stdin, stdout, stderr = ssh.exec_command('echo "test"')
            result = stdout.read().decode().strip()
            ssh.close()
            
            if result == "test":
                return True, "SSH connection successful"
            else:
                return False, "SSH command failed"
                
        except Exception as e:
            return False, f"SSH connection failed: {e}"
    
    def deploy_worker_to_machine(self, worker_config):
        """Deploy worker node to a specific machine"""
        worker_name = worker_config['name']
        
        try:
            logger.info(f"Deploying worker to {worker_name} ({worker_config['ip']})...")
            
            # Test connection first
            connected, message = self.test_worker_connection(worker_config)
            if not connected:
                raise Exception(f"Connection failed: {message}")
            
            # Copy worker files if needed
            self._ensure_worker_files(worker_config)
            
            # Start worker process
            success, process_info = self._start_remote_worker(worker_config)
            
            if success:
                with self.deployment_lock:
                    self.deployed_workers[worker_name] = {
                        'config': worker_config,
                        'process_info': process_info,
                        'deployed_at': datetime.now().isoformat(),
                        'status': 'running'
                    }
                
                logger.info(f"✅ Worker {worker_name} deployed successfully")
                return True, "Deployment successful"
            else:
                return False, f"Failed to start worker: {process_info}"
                
        except Exception as e:
            logger.error(f"Deployment failed for {worker_name}: {e}")
            return False, str(e)
    
    def _ensure_worker_files(self, worker_config):
        """Ensure worker files exist on remote machine"""
        os_type = worker_config.get('os', 'windows').lower()
        remote_path = worker_config['worker_path']
        
        # Check if worker file exists
        if os_type == 'windows':
            return self._check_windows_file(worker_config, remote_path)
        else:
            return self._check_ssh_file(worker_config, remote_path)
    
    def _check_windows_file(self, worker_config, file_path):
        """Check if file exists on Windows machine"""
        try:
            ip = worker_config['ip']
            username = worker_config['username'] 
            password = worker_config['password']
            
            session = winrm.Session(f'http://{ip}:5985/wsman', auth=(username, password))
            
            # Check if file exists
            result = session.run_cmd(f'dir "{file_path}"')
            
            if result.status_code == 0:
                logger.debug(f"Worker file exists on {worker_config['name']}")
                return True
            else:
                logger.warning(f"Worker file not found on {worker_config['name']}, may need manual deployment")
                return False
                
        except Exception as e:
            logger.warning(f"Could not verify worker file on {worker_config['name']}: {e}")
            return False
    
    def _check_ssh_file(self, worker_config, file_path):
        """Check if file exists via SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(worker_config['ip'], 
                       username=worker_config['username'], 
                       password=worker_config['password'], 
                       timeout=10)
            
            stdin, stdout, stderr = ssh.exec_command(f'test -f "{file_path}" && echo "exists"')
            result = stdout.read().decode().strip()
            ssh.close()
            
            return result == "exists"
            
        except Exception as e:
            logger.warning(f"Could not verify worker file on {worker_config['name']}: {e}")
            return False
    
    def _start_remote_worker(self, worker_config):
        """Start worker process on remote machine"""
        os_type = worker_config.get('os', 'windows').lower()
        
        if os_type == 'windows':
            return self._start_windows_worker(worker_config)
        else:
            return self._start_ssh_worker(worker_config)
    
    def _start_windows_worker(self, worker_config):
        """Start worker on Windows via WinRM"""
        try:
            ip = worker_config['ip']
            username = worker_config['username']
            password = worker_config['password']
            python_path = worker_config.get('python_path', 'python')
            worker_path = worker_config['worker_path']
            
            session = winrm.Session(f'http://{ip}:5985/wsman', auth=(username, password))
            
            # Build worker command
            worker_cmd = f'{python_path} "{worker_path}" --server {self.server_url} --worker-id {worker_config["name"]}'
            
            # Start worker in background
            start_cmd = f'start "RenderWorker" /min cmd /c "{worker_cmd}"'
            
            logger.info(f"Starting worker with command: {start_cmd}")
            result = session.run_cmd(start_cmd)
            
            if result.status_code == 0:
                return True, {
                    'command': worker_cmd,
                    'started_at': datetime.now().isoformat(),
                    'method': 'winrm'
                }
            else:
                error_msg = result.std_err.decode() if result.std_err else "Unknown error"
                return False, f"Command failed: {error_msg}"
                
        except Exception as e:
            return False, f"Windows worker start failed: {e}"
    
    def _start_ssh_worker(self, worker_config):
        """Start worker via SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(worker_config['ip'], 
                       username=worker_config['username'], 
                       password=worker_config['password'], 
                       timeout=10)
            
            python_path = worker_config.get('python_path', 'python3')
            worker_path = worker_config['worker_path']
            
            # Build worker command
            worker_cmd = f'{python_path} "{worker_path}" --server {self.server_url} --worker-id {worker_config["name"]}'
            
            # Start worker in background (nohup for persistence)
            start_cmd = f'nohup {worker_cmd} > /tmp/render_worker.log 2>&1 &'
            
            logger.info(f"Starting worker with command: {start_cmd}")
            stdin, stdout, stderr = ssh.exec_command(start_cmd)
            
            # Give it a moment to start
            time.sleep(2)
            
            ssh.close()
            
            return True, {
                'command': worker_cmd,
                'started_at': datetime.now().isoformat(),
                'method': 'ssh'
            }
            
        except Exception as e:
            return False, f"SSH worker start failed: {e}"
    
    def stop_worker(self, worker_name):
        """Stop a specific worker"""
        if worker_name not in self.deployed_workers:
            return False, "Worker not found"
        
        try:
            worker_info = self.deployed_workers[worker_name]
            worker_config = worker_info['config']
            
            # Send stop command based on OS
            if worker_config.get('os', 'windows').lower() == 'windows':
                success = self._stop_windows_worker(worker_config)
            else:
                success = self._stop_ssh_worker(worker_config)
            
            if success:
                worker_info['status'] = 'stopped'
                worker_info['stopped_at'] = datetime.now().isoformat()
                logger.info(f"✅ Worker {worker_name} stopped")
                return True, "Worker stopped"
            else:
                return False, "Failed to stop worker"
                
        except Exception as e:
            logger.error(f"Failed to stop worker {worker_name}: {e}")
            return False, str(e)
    
    def _stop_windows_worker(self, worker_config):
        """Stop Windows worker"""
        try:
            session = winrm.Session(f'http://{worker_config["ip"]}:5985/wsman', 
                                   auth=(worker_config['username'], worker_config['password']))
            
            # Kill python processes running worker_node.py
            kill_cmd = 'taskkill /F /IM python.exe /FI "WINDOWTITLE eq RenderWorker*"'
            result = session.run_cmd(kill_cmd)
            
            return result.status_code == 0
            
        except Exception as e:
            logger.error(f"Failed to stop Windows worker: {e}")
            return False
    
    def _stop_ssh_worker(self, worker_config):
        """Stop SSH worker"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(worker_config['ip'], 
                       username=worker_config['username'], 
                       password=worker_config['password'], 
                       timeout=10)
            
            # Kill worker processes
            kill_cmd = 'pkill -f "worker_node.py"'
            stdin, stdout, stderr = ssh.exec_command(kill_cmd)
            ssh.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop SSH worker: {e}")
            return False
    
    def deploy_all_workers(self):
        """Deploy all enabled workers"""
        results = {}
        enabled_workers = [w for w in self.worker_configs if w.get('enabled', True)]
        
        logger.info(f"Deploying {len(enabled_workers)} workers...")
        
        # Deploy workers in parallel
        threads = []
        
        def deploy_worker_thread(worker_config):
            worker_name = worker_config['name']
            success, message = self.deploy_worker_to_machine(worker_config)
            results[worker_name] = {'success': success, 'message': message}
        
        for worker_config in enabled_workers:
            if worker_config.get('auto_start', True):
                thread = threading.Thread(target=deploy_worker_thread, args=(worker_config,))
                thread.start()
                threads.append(thread)
        
        # Wait for all deployments
        for thread in threads:
            thread.join(timeout=self.deployment_settings.get('deployment_timeout', 120))
        
        # Report results
        successful = sum(1 for r in results.values() if r['success'])
        logger.info(f"Worker deployment complete: {successful}/{len(enabled_workers)} successful")
        
        return results
    
    def stop_all_workers(self):
        """Stop all deployed workers"""
        results = {}
        
        for worker_name in list(self.deployed_workers.keys()):
            success, message = self.stop_worker(worker_name)
            results[worker_name] = {'success': success, 'message': message}
        
        return results
    
    def get_worker_status(self):
        """Get status of all workers"""
        status = {
            'total_configured': len(self.worker_configs),
            'total_deployed': len(self.deployed_workers),
            'workers': []
        }
        
        for worker_config in self.worker_configs:
            worker_name = worker_config['name']
            worker_info = {
                'name': worker_name,
                'ip': worker_config['ip'],
                'enabled': worker_config.get('enabled', True),
                'auto_start': worker_config.get('auto_start', True),
                'status': 'not_deployed'
            }
            
            if worker_name in self.deployed_workers:
                deployed_info = self.deployed_workers[worker_name]
                worker_info.update({
                    'status': deployed_info.get('status', 'unknown'),
                    'deployed_at': deployed_info.get('deployed_at'),
                    'method': deployed_info.get('process_info', {}).get('method')
                })
            
            status['workers'].append(worker_info)
        
        return status
    
    def get_local_ip(self):
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def start_health_monitoring(self):
        """Start background health monitoring of workers"""
        def health_monitor():
            while True:
                try:
                    for worker_name, worker_info in self.deployed_workers.items():
                        if worker_info.get('status') == 'running':
                            # Basic connectivity check
                            worker_config = worker_info['config']
                            connected, _ = self.test_worker_connection(worker_config)
                            
                            if not connected:
                                logger.warning(f"Worker {worker_name} appears to be offline")
                                worker_info['status'] = 'offline'
                    
                    time.sleep(self.deployment_settings.get('health_check_interval', 60))
                    
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    time.sleep(30)
        
        monitor_thread = threading.Thread(target=health_monitor, daemon=True)
        monitor_thread.start()
        logger.info("Worker health monitoring started")