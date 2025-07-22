import os
import sys
import time
import json
import socket
import requests
import subprocess
import threading
import argparse
import platform
import glob
import psutil
import hashlib
import logging
import asyncio
import aiofiles
import weakref
from datetime import datetime
from pathlib import Path
from multiprocessing import shared_memory
from collections import OrderedDict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ProductionRenderWorker:
    def __init__(self, server_url, worker_id=None, config_path="worker_config.json"):
        self.server_url = server_url.rstrip('/')
        self.worker_id = worker_id or f"worker_{socket.gethostname()}"
        self.hostname = socket.gethostname()
        self.ip_address = self.get_local_ip()
        self.running = False
        self.current_jobs = {}
        self.config = self.load_config(config_path)
        
        # Performance monitoring
        self.metrics_collector = SystemMetricsCollector()
        self.render_history = []
        
        # Enhanced performance features
        # Aggressive RAM usage for high-end systems
        available_ram_gb = psutil.virtual_memory().total / (1024**3)
        
        # For 64GB+ systems, use much more RAM for caching
        if available_ram_gb >= 32:
            cache_size_gb = min(int(available_ram_gb * 0.5), 32)  # Use 50% of RAM, up to 32GB
            logger.info(f"🚀 High-end system detected: {available_ram_gb:.1f}GB RAM, using {cache_size_gb}GB cache")
        else:
            cache_size_gb = min(int(available_ram_gb * 0.3), 8)  # Standard systems
        
        self.asset_cache = AssetCache(max_size_gb=cache_size_gb)
        # Larger buffer pool for high-end systems
        if available_ram_gb >= 32:
            buffer_size_mb = 2048  # 2GB buffers for high-end systems
            max_buffers = 16       # More buffers available
            logger.info(f"🔥 High-end buffer pool: {max_buffers} x {buffer_size_mb}MB buffers")
        else:
            buffer_size_mb = 512
            max_buffers = 8
            
        self.render_buffer_pool = RenderBufferPool(buffer_size_mb=buffer_size_mb, max_buffers=max_buffers)
        self.async_file_manager = AsyncFileManager()
        self.memory_job_cache = {}
        
        # Output tracking
        self.output_locations = {}
        self.render_stats = {
            'jobs_completed': 0,
            'frames_rendered': 0,
            'total_render_time': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # Setup directories
        self.temp_dir = Path(self.config.get('temp_directory', 'temp_renders'))
        self.temp_dir.mkdir(exist_ok=True)
        self.log_dir = Path(self.config.get('log_directory', 'logs'))
        self.log_dir.mkdir(exist_ok=True)
        
        # Worker capabilities with enhanced detection
        self.capabilities = self.detect_capabilities()
        
        logger.info(f"Production worker initialized: {self.worker_id}")
        logger.info(f"Hostname: {self.hostname}, IP: {self.ip_address}")
        logger.info(f"Capabilities: {self.capabilities}")
    
    def load_config(self, config_path):
        """Load worker configuration"""
        default_config = {
            "max_concurrent_jobs": self.detect_optimal_concurrency(),
            "heartbeat_interval": 10,
            "metrics_interval": 30,
            "retry_attempts": 3,
            "timeout_per_frame": 1800,  # 30 minutes per frame
            "temp_directory": "temp_renders",
            "log_directory": "logs",
            "resource_limits": {
                "max_memory_percent": 85,
                "max_cpu_percent": 95
            },
            "renderers": {
                "nuke": {
                    "timeout_multiplier": 1.0,
                    "memory_per_thread_gb": 2.0
                },
                "silhouette": {
                    "timeout_multiplier": 1.5,
                    "memory_per_thread_gb": 1.5
                },
                "fusion": {
                    "timeout_multiplier": 2.0,
                    "memory_per_thread_gb": 3.0
                }
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                default_config.update(user_config)
        except Exception as e:
            logger.warning(f"Failed to load config: {e}, using defaults")
        
        return default_config
    
    def detect_optimal_concurrency(self):
        """Enhanced concurrency detection using actual memory patterns"""
        cpu_count = os.cpu_count()
        memory_gb = psutil.virtual_memory().total / (1024**3)
        
        # Use default memory per job since config not available during init
        memory_per_job_gb = 2.0  # Default value, will be updated later
        
        # For high-end systems (32GB+), use more aggressive settings
        if memory_gb >= 32:
            # Use 85% of available memory for high-end systems
            memory_limit = max(int((memory_gb * 0.85) // memory_per_job_gb), 1)
            # Use 85% of CPU cores for maximum performance
            cpu_limit = max(int(cpu_count * 0.85), 2)
            # Allow up to 20 concurrent jobs on high-end systems
            max_concurrent = 20
            logger.info(f"🔥 High-end mode: Using 85% RAM, 85% CPU cores")
        else:
            # Standard settings for lower-end systems
            memory_limit = max(int((memory_gb * 0.8) // memory_per_job_gb), 1)
            cpu_limit = max(int(cpu_count * 0.75), 1)
            max_concurrent = 12
        
        optimal_jobs = min(memory_limit, cpu_limit, max_concurrent)
        
        logger.info(f"🚀 Enhanced concurrency: {optimal_jobs} jobs (Memory: {memory_gb:.1f}GB using 80%, CPUs: {cpu_count} using 75%)")
        return optimal_jobs
    
    def detect_capabilities(self):
        """Enhanced capability detection"""
        capabilities = {
            'platform': platform.system(),
            'hostname': self.hostname,
            'cpu_count': os.cpu_count(),
            'memory_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'disk_space_gb': round(psutil.disk_usage('.').free / (1024**3), 2),
            'renderers': self.detect_renderers(),
            'network_speed': self.test_network_speed(),
            'max_concurrent_jobs': self.config.get('max_concurrent_jobs', 1)
        }
        
        # GPU detection
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                capabilities['gpu'] = {
                    'count': len(gpus),
                    'memory_gb': sum(gpu.memoryTotal for gpu in gpus) / 1024,
                    'names': [gpu.name for gpu in gpus]
                }
        except ImportError:
            pass
        
        return capabilities
    
    def detect_renderers(self):
        """Detect and validate renderer installations"""
        renderers = {}
        
        renderer_configs = {
            'nuke': {
                'patterns': [
                    'C:\\Program Files\\Nuke*\\Nuke*.exe',
                    '/usr/local/Nuke*/Nuke*',
                    '/Applications/Nuke*/Nuke*.app/Contents/MacOS/Nuke*'
                ],
                'version_flag': '--version'
            },
            'silhouette': {
                'patterns': [
                    'C:\\Program Files\\SilhouetteFX\\Silhouette*\\silhouette.exe',
                    '/Applications/Silhouette*.app/Contents/MacOS/Silhouette*'
                ],
                'version_flag': '--version'
            },
            'fusion': {
                'patterns': [
                    'C:\\Program Files\\Blackmagic Design\\Fusion*\\Fusion.exe',
                    'C:\\Program Files\\Blackmagic Design\\Fusion*\\FusionRenderNode.exe',
                    '/Applications/Fusion*.app/Contents/MacOS/Fusion*'
                ],
                'version_flag': '--version'
            }
        }
        
        for renderer_name, config in renderer_configs.items():
            for pattern in config['patterns']:
                matches = glob.glob(pattern)
                if matches:
                    executable = matches[0]
                    version = self.get_renderer_version(executable, config['version_flag'])
                    renderers[renderer_name] = {
                        'path': executable,
                        'version': version,
                        'validated': True
                    }
                    logger.info(f"Found {renderer_name}: {executable} (v{version})")
                    break
        
        return renderers
    
    def get_renderer_version(self, executable, version_flag):
        """Get renderer version"""
        try:
            result = subprocess.run([executable, version_flag], 
                                  capture_output=True, text=True, timeout=10)
            return result.stdout.strip()[:50]  # First 50 chars
        except:
            return "unknown"
    
    def validate_renderer(self, executable):
        """Validate renderer can execute"""
        try:
            result = subprocess.run([executable, '--help'], 
                                  capture_output=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def test_network_speed(self):
        """Basic network speed test"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.server_url}/api/status", timeout=5)
            latency = (time.time() - start_time) * 1000
            return {"latency_ms": round(latency, 2), "status": "ok"}
        except:
            return {"latency_ms": 9999, "status": "error"}
    
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
    
    def register_with_server(self):
        """Register with enhanced retry and validation"""
        max_retries = self.config.get('retry_attempts', 3)
        
        for attempt in range(max_retries):
            try:
                payload = {
                    'worker_id': self.worker_id,
                    'ip_address': self.ip_address,
                    'hostname': self.hostname,
                    'capabilities': self.capabilities
                }
                
                # Add API key if configured
                headers = {}
                api_key = self.config.get('api_key')
                if api_key:
                    headers['X-API-Key'] = api_key
                
                response = requests.post(
                    f"{self.server_url}/api/workers/register",
                    json=payload,
                    headers=headers,
                    timeout=15
                )
                
                if response.status_code == 200:
                    logger.info("Successfully registered with server")
                    return True
                else:
                    logger.error(f"Registration failed: HTTP {response.status_code}")
                    
            except requests.RequestException as e:
                logger.error(f"Registration attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
        
        return False
    
    def send_heartbeat(self):
        """Enhanced heartbeat with system metrics"""
        try:
            system_metrics = self.metrics_collector.get_current_metrics()
            
            payload = {
                'worker_id': self.worker_id,
                'system_metrics': system_metrics,
                'current_jobs': list(self.current_jobs.keys()),
                'status': 'busy' if self.current_jobs else 'idle'
            }
            
            headers = {}
            api_key = self.config.get('api_key')
            if api_key:
                headers['X-API-Key'] = api_key
            
            response = requests.post(
                f"{self.server_url}/api/workers/heartbeat",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            logger.error(f"Heartbeat failed: {e}")
            return False
    
    def get_next_job(self):
        """Get next job with enhanced error handling and memory optimization"""
        # Check if we can take more jobs
        max_concurrent = self.config.get('max_concurrent_jobs', 1)
        if len(self.current_jobs) >= max_concurrent:
            return None
        
        # Check system resources
        if not self.check_resource_availability():
            logger.warning("System resources low, not requesting new jobs")
            return None
        
        # Check memory cache first for faster job retrieval
        if hasattr(self, 'memory_job_cache') and self.memory_job_cache:
            for job_id, job_data in list(self.memory_job_cache.items()):
                if job_data.get('status') == 'pending':
                    job_data['status'] = 'running'
                    job_data['worker_id'] = self.worker_id
                    cached_job = self.memory_job_cache.pop(job_id)
                    logger.debug(f"Retrieved job from memory cache: {job_id}")
                    return cached_job
        
        try:
            headers = {}
            api_key = self.config.get('api_key')
            if api_key:
                headers['X-API-Key'] = api_key
            
            response = requests.get(
                f"{self.server_url}/api/jobs/next",
                params={'worker_id': self.worker_id},
                headers=headers,
                timeout=15
            )
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 204:
                return None  # No jobs available
            else:
                logger.error(f"Failed to get job: HTTP {response.status_code}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"Failed to get next job: {e}")
            return None
    
    def check_resource_availability(self):
        """Check if system has resources for new job"""
        metrics = self.metrics_collector.get_current_metrics()
        limits = self.config.get('resource_limits', {})
        
        if metrics['memory_percent'] > limits.get('max_memory_percent', 85):
            return False
        
        if metrics['cpu_percent'] > limits.get('max_cpu_percent', 95):
            return False
        
        # Check disk space (need at least 5GB free)
        if metrics['disk_free_gb'] < 5:
            return False
        
        return True
    
    def report_job_completion(self, sub_job_id, success, error_message=None, metrics=None):
        """Report job completion with detailed metrics"""
        try:
            payload = {
                'sub_job_id': sub_job_id,
                'worker_id': self.worker_id,
                'success': success,
                'error_message': error_message,
                'metrics': metrics or {}
            }
            
            headers = {}
            api_key = self.config.get('api_key')
            if api_key:
                headers['X-API-Key'] = api_key
            
            response = requests.post(
                f"{self.server_url}/api/jobs/complete",
                json=payload,
                headers=headers,
                timeout=15
            )
            
            return response.status_code == 200
            
        except requests.RequestException as e:
            logger.error(f"Failed to report job completion: {e}")
            return False
    
    def execute_render_job(self, job):
        """Execute job with comprehensive error handling and RAM optimization"""
        sub_job_id = job['sub_job_id']
        frame_range = job['frame_range']
        job_data = job['job_data']
        retry_count = job.get('retry_count', 0)
        
        logger.info(f"Starting optimized job {sub_job_id}: frames {frame_range} (retry {retry_count})")
        
        # Get render buffer from pool
        render_buffer = None
        if hasattr(self, 'render_buffer_pool'):
            render_buffer = self.render_buffer_pool.get_buffer(sub_job_id)
        
        # Preload project file into cache
        project_file = job_data.get('processed_file_path', job_data['file_path'])
        if hasattr(self, 'asset_cache') and os.path.exists(project_file):
            try:
                cached_data = self.asset_cache.get_file(project_file)
                logger.debug(f"Project file cached: {len(cached_data)} bytes")
            except Exception as e:
                logger.warning(f"Failed to cache project file: {e}")
        
        # Add to current jobs with enhanced tracking
        self.current_jobs[sub_job_id] = {
            'start_time': time.time(),
            'frame_range': frame_range,
            'job_data': job_data,
            'render_buffer': render_buffer,
            'memory_allocated': render_buffer.size if render_buffer else 0
        }
        
        try:
            renderer = job_data['renderer']
            executable = job_data['executable_path']
            project_file = job_data.get('processed_file_path', job_data['file_path'])
            
            # Validate renderer availability
            if renderer not in self.capabilities['renderers']:
                raise Exception(f"Renderer {renderer} not available on this worker")
            
            # Validate executable
            renderer_info = self.capabilities['renderers'][renderer]
            if not renderer_info.get('validated', False):
                raise Exception(f"Renderer {renderer} failed validation")
            
            # Execute render based on type
            if renderer == 'nuke':
                success, error, metrics = self.render_nuke_production(
                    executable, project_file, frame_range, job_data, sub_job_id
                )
            elif renderer == 'silhouette':
                success, error, metrics = self.render_silhouette_production(
                    executable, project_file, frame_range, job_data, sub_job_id
                )
            elif renderer == 'fusion':
                success, error, metrics = self.render_fusion_production(
                    executable, project_file, frame_range, job_data, sub_job_id
                )
            else:
                raise Exception(f"Unknown renderer: {renderer}")
            
            # Store render history
            self.render_history.append({
                'sub_job_id': sub_job_id,
                'success': success,
                'duration': metrics.get('render_time', 0),
                'timestamp': datetime.now().isoformat()
            })
            
            # Report completion with enhanced metrics
            self.report_job_completion(sub_job_id, success, error, metrics)
            
            if success:
                output_info = metrics.get('output_info', {})
                render_time = metrics.get('render_time', 0)
                frames_count = output_info.get('total_files', 0)
                total_size = output_info.get('total_size_mb', 0)
                
                logger.info(f" Job {sub_job_id} completed in {render_time:.1f}s")
                logger.info(f" Rendered {frames_count} frames ({total_size:.1f}MB)")
                
                # Log output directories
                for output_dir in output_info.get('directories', []):
                    logger.info(f" Output saved to: {output_dir}")
            else:
                logger.error(f" Job {sub_job_id} failed: {error}")
                
        except Exception as e:
            error_msg = f"Job execution failed: {str(e)}"
            logger.error(error_msg)
            self.report_job_completion(sub_job_id, False, error_msg)
        
        finally:
            # Clean up resources
            if sub_job_id in self.current_jobs:
                job_info = self.current_jobs[sub_job_id]
                
                # Return render buffer to pool
                if hasattr(self, 'render_buffer_pool') and job_info.get('render_buffer'):
                    self.render_buffer_pool.return_buffer(sub_job_id)
                
                # Remove from current jobs
                del self.current_jobs[sub_job_id]
                
                # Log performance summary
                if hasattr(self, 'render_stats'):
                    cache_stats = self.asset_cache.get_stats() if hasattr(self, 'asset_cache') else {}
                    logger.info(f" Performance Summary - Jobs: {self.render_stats['jobs_completed']}, "
                              f"Cache Hit Rate: {cache_stats.get('hit_ratio', 0):.1f}%, "
                              f"Memory Usage: {cache_stats.get('cache_size_gb', 0):.2f}GB")
    
    def render_nuke_production(self, executable, project_file, frame_range, job_data, batch_id):
        """Production Nuke render with UNC path support"""
        start_time = time.time()
        
        try:
            logger.info(f"=== RENDER DEBUG INFO ===")
            logger.info(f"Executable: {executable}")
            logger.info(f"Project file: {project_file}")
            logger.info(f"Frame range: {frame_range}")
            logger.info(f"Working directory: {os.getcwd()}")
            logger.info(f"Batch ID: {batch_id}")
            
            # Check if executable exists
            if not os.path.exists(executable):
                logger.error(f" Executable not found: {executable}")
                return False, f"Executable not found: {executable}", {'render_time': 0}
            else:
                logger.info(f" Executable exists: {executable}")
            
            # Check if project file exists
            if not os.path.exists(project_file):
                logger.error(f" Project file not found: {project_file}")
                return False, f"Project file not found: {project_file}", {'render_time': 0}
            else:
                logger.info(f" Project file exists: {project_file}")
                logger.info(f"Project file size: {os.path.getsize(project_file)} bytes")
            
            # Parse frame range
            if '-' in frame_range:
                start_frame, end_frame = frame_range.split('-')
            else:
                start_frame = end_frame = frame_range
            
            logger.info(f"Parsed frames: {start_frame} to {end_frame}")
            
            # Build command with proper absolute paths
            cmd = [
                os.path.abspath(executable),
                '-i', '-f', '-x', '-m', '3',
                '-F', f"{start_frame}-{end_frame}",
                '-m', '14', '-V',
                '--', os.path.abspath(project_file)
            ]
            
            # Add extra arguments
            extra_args = job_data.get('extra_args', '')
            if extra_args:
                cmd_with_args = cmd[:-2] + extra_args.split() + cmd[-2:]
                cmd = cmd_with_args
                logger.info(f"Added extra args: {extra_args}")
            
            logger.info(f"Full command: {' '.join(cmd)}")
            
            # Set working directory - avoid UNC paths for Windows CMD
            work_dir = os.path.dirname(os.path.abspath(project_file))
            if work_dir.startswith('\\\\'):
                # UNC path - use local directory to avoid CMD issues
                safe_work_dir = "C:\\"
                logger.info(f"UNC path detected, using safe working directory: {safe_work_dir}")
            else:
                safe_work_dir = work_dir
                logger.info(f"Working directory: {safe_work_dir}")
            
            # Create batch file for Windows with UNC path handling
            batch_file = None
            if platform.system() == 'Windows':
                batch_file = self.temp_dir / f"nuke_{batch_id}.cmd"
                logger.info(f"Creating batch file: {batch_file}")
                
                # Create batch content with UNC path support
                batch_content = []
                batch_content.append("@echo off")
                
                # Use safe local directory as working directory
                batch_content.append(f'cd /d "{safe_work_dir}"')
                batch_content.append("echo Current directory: %CD%")
                batch_content.append("echo Starting Nuke render...")
                
                # Use absolute paths for the command (including UNC paths)
                nuke_cmd = f'"{cmd[0]}" -i -f -x -m 3 -F {start_frame}-{end_frame} -m 14 -V -- "{cmd[-1]}"'
                batch_content.append(nuke_cmd)
                batch_content.append("echo Nuke render completed with exit code: %ERRORLEVEL%")
                
                with open(batch_file, 'w') as f:
                    f.write('\n'.join(batch_content))
                
                logger.info(f"Batch file contents:")
                for line in batch_content:
                    logger.info(f"  {line}")
                
                # Execute batch file
                cmd = ["cmd", "/c", str(batch_file.absolute())]
                shell = False
            else:
                shell = False
            
            logger.info(f"Executing command: {' '.join(cmd)}")
            logger.info(f"Shell mode: {shell}")
            logger.info(f"Safe working directory: {safe_work_dir}")
            
            # Calculate timeout
            frame_count = int(end_frame) - int(start_frame) + 1 if '-' in frame_range else 1
            timeout = frame_count * self.config.get('timeout_per_frame', 1800)
            logger.info(f"Timeout: {timeout}s for {frame_count} frames")
            
            # Monitor execution with safe working directory
            with subprocess.Popen(
                cmd, 
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=safe_work_dir
            ) as process:
                
                logger.info(f"Process started with PID: {process.pid}")
                
                # Monitor process with resource tracking
                stdout, stderr = self.monitor_process(process, timeout, batch_id)
            
            render_time = time.time() - start_time
            
            logger.info(f"Process completed with return code: {process.returncode}")
            logger.info(f"STDOUT: {stdout[:500]}...")  # First 500 chars
            logger.info(f"STDERR: {stderr[:500]}...")  # First 500 chars
            
            # Clean up batch file
            if platform.system() == 'Windows' and batch_file and batch_file.exists():
                batch_file.unlink()
                logger.info("Batch file cleaned up")
            
            # Analyze results
            if process.returncode == 0:
                output_info = self.detect_output_files(project_file, frame_range, job_data)
                
                # Enhanced metrics with output information
                metrics = {
                    'render_time': render_time,
                    'output_info': output_info,
                    'memory_peak': self.get_peak_memory_usage(batch_id),
                    'frames_rendered': frame_count,
                    'cache_stats': self.asset_cache.get_stats() if hasattr(self, 'asset_cache') else {}
                }
                
                # Store output location for this job
                if hasattr(self, 'output_locations'):
                    self.output_locations[batch_id] = output_info
                
                # Update render stats
                if hasattr(self, 'render_stats'):
                    self.render_stats['jobs_completed'] += 1
                    self.render_stats['frames_rendered'] += frame_count
                    self.render_stats['total_render_time'] += render_time
                
                logger.info(f"✅ Nuke render successful! {output_info.get('total_files', 0)} files rendered")
                return True, None, metrics
            else:
                error_msg = f"Nuke render failed (exit {process.returncode}): {stderr}"
                logger.error(f"❌ Render failed: {error_msg}")
                return False, error_msg, {'render_time': render_time}
                
        except subprocess.TimeoutExpired:
            error_msg = f"Render timed out after {timeout}s"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, {'render_time': time.time() - start_time}
        except Exception as e:
            error_msg = f"Render execution error: {str(e)}"
            logger.error(f"❌ {error_msg}")
            logger.exception("Full traceback:")
            
            # Return buffer to pool if it was allocated
            if hasattr(self, 'render_buffer_pool'):
                self.render_buffer_pool.return_buffer(batch_id)
            
            return False, error_msg, {'render_time': time.time() - start_time}
    
    def render_silhouette_production(self, executable, project_file, frame_range, job_data, batch_id):
        """Production Silhouette render with monitoring"""
        start_time = time.time()
        
        try:
            # Build command
            cmd = [executable, '-range', frame_range, project_file]
            
            # Add extra arguments
            extra_args = job_data.get('extra_args', '')
            if extra_args:
                cmd.extend(extra_args.split())
            
            logger.info(f"Executing Silhouette: {' '.join(cmd)}")
            
            # Calculate timeout
            frame_count = len(frame_range.split('-')) if '-' in frame_range else 1
            timeout = frame_count * self.config.get('timeout_per_frame', 1800)
            
            # Execute with monitoring
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(project_file)
            ) as process:
                
                stdout, stderr = self.monitor_process(process, timeout, batch_id)
            
            render_time = time.time() - start_time
            
            if process.returncode == 0:
                metrics = {
                    'render_time': render_time,
                    'memory_peak': self.get_peak_memory_usage(batch_id)
                }
                return True, None, metrics
            else:
                error_msg = f"Silhouette render failed (exit {process.returncode}): {stderr}"
                return False, error_msg, {'render_time': render_time}
                
        except subprocess.TimeoutExpired:
            return False, f"Render timed out after {timeout}s", {'render_time': time.time() - start_time}
        except Exception as e:
            return False, f"Render execution error: {str(e)}", {'render_time': time.time() - start_time}
    
    def render_fusion_production(self, executable, project_file, frame_range, job_data, batch_id):
        """Production Fusion render with monitoring"""
        start_time = time.time()
        
        try:
            # Parse frame range
            if '-' in frame_range:
                start_frame, end_frame = frame_range.split('-')
            else:
                start_frame = end_frame = frame_range
            
            # Build command
            cmd = [
                executable, project_file,
                '/render', '/start', start_frame, '/end', end_frame
            ]
            
            # Add extra arguments
            extra_args = job_data.get('extra_args', '')
            if extra_args:
                cmd.extend(extra_args.split())
            
            logger.info(f"Executing Fusion: {' '.join(cmd)}")
            
            # Calculate timeout
            frame_count = int(end_frame) - int(start_frame) + 1 if '-' in frame_range else 1
            timeout = frame_count * self.config.get('timeout_per_frame', 1800)
            
            # Execute with monitoring
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(project_file)
            ) as process:
                
                stdout, stderr = self.monitor_process(process, timeout, batch_id)
            
            render_time = time.time() - start_time
            
            if process.returncode == 0:
                metrics = {
                    'render_time': render_time,
                    'memory_peak': self.get_peak_memory_usage(batch_id)
                }
                return True, None, metrics
            else:
                error_msg = f"Fusion render failed (exit {process.returncode}): {stderr}"
                return False, error_msg, {'render_time': render_time}
                
        except subprocess.TimeoutExpired:
            return False, f"Render timed out after {timeout}s", {'render_time': time.time() - start_time}
        except Exception as e:
            return False, f"Render execution error: {str(e)}", {'render_time': time.time() - start_time}
    
    def monitor_process(self, process, timeout, job_id):
        """Monitor process execution with resource tracking"""
        start_time = time.time()
        stdout_lines = []
        stderr_lines = []
        peak_memory = 0
        
        try:
            # Get process for monitoring
            ps_process = psutil.Process(process.pid)
            
            while process.poll() is None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    process.terminate()
                    time.sleep(5)
                    if process.poll() is None:
                        process.kill()
                    raise subprocess.TimeoutExpired(process.args, timeout)
                
                # Monitor memory usage
                try:
                    memory_info = ps_process.memory_info()
                    peak_memory = max(peak_memory, memory_info.rss / 1024 / 1024)  # MB
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                time.sleep(1)
            
            # Get final output
            stdout, stderr = process.communicate()
            
            # Store peak memory for this job
            self.store_peak_memory(job_id, peak_memory)
            
            return stdout, stderr
            
        except Exception as e:
            logger.error(f"Process monitoring error: {e}")
            return "", str(e)
    
    def store_peak_memory(self, job_id, peak_memory_mb):
        """Store peak memory usage for job"""
        self._peak_memory_cache = getattr(self, '_peak_memory_cache', {})
        self._peak_memory_cache[job_id] = peak_memory_mb
    
    def get_peak_memory_usage(self, job_id):
        """Get stored peak memory usage"""
        cache = getattr(self, '_peak_memory_cache', {})
        return cache.get(job_id, 0)
    
    def detect_output_files(self, project_file, frame_range, job_data=None):
        """Enhanced output file detection with comprehensive reporting"""
        output_files = []
        output_directories = set()
        
        try:
            # Parse project file to find actual Write nodes
            if project_file.endswith('.nk'):
                output_info = self.parse_nuke_write_nodes(project_file)
            elif project_file.endswith('.sfx'):
                output_info = self.parse_silhouette_outputs(project_file)
            elif project_file.endswith('.comp'):
                output_info = self.parse_fusion_outputs(project_file)
            else:
                output_info = []
            
            # Look for rendered files based on write nodes
            for write_info in output_info:
                output_pattern = write_info.get('file_path', '')
                if output_pattern:
                    rendered_files = self.find_rendered_frames(output_pattern, frame_range)
                    output_files.extend(rendered_files)
                    
                    if rendered_files:
                        output_dir = os.path.dirname(rendered_files[0])
                        output_directories.add(output_dir)
            
            # Fallback: search common output locations
            if not output_files:
                fallback_dirs = [
                    os.path.dirname(project_file),
                    os.path.join(os.path.dirname(project_file), 'renders'),
                    os.path.join(os.path.dirname(project_file), 'output'),
                    os.path.join(os.path.dirname(project_file), 'comp')
                ]
                
                for search_dir in fallback_dirs:
                    if os.path.exists(search_dir):
                        pattern_files = self.find_rendered_frames_in_dir(search_dir, frame_range)
                        if pattern_files:
                            output_files.extend(pattern_files)
                            output_directories.add(search_dir)
            
            # Log detailed output information
            if output_files:
                logger.info(f"✅ RENDER OUTPUT DETECTED:")
                for output_dir in sorted(output_directories):
                    dir_files = [f for f in output_files if f.startswith(output_dir)]
                    logger.info(f"📁 Output Directory: {output_dir}")
                    logger.info(f"   📄 Files: {len(dir_files)} frames")
                    
                    # Show sample files
                    for i, file_path in enumerate(sorted(dir_files)[:3]):
                        file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                        logger.info(f"   ├─ {os.path.basename(file_path)} ({file_size/1024/1024:.1f}MB)")
                    
                    if len(dir_files) > 3:
                        logger.info(f"   └─ ... and {len(dir_files)-3} more files")
                
                # Summary
                total_size = sum(os.path.getsize(f) for f in output_files if os.path.exists(f))
                logger.info(f"🎬 RENDER COMPLETE: {len(output_files)} frames, {total_size/1024/1024:.1f}MB total")
                
                # Store output locations for reporting
                return {
                    'files': output_files[:50],  # Limit for performance
                    'directories': list(output_directories),
                    'total_files': len(output_files),
                    'total_size_mb': total_size / 1024 / 1024,
                    'frame_range': frame_range
                }
            else:
                logger.warning(f"⚠️  No output files found for frames {frame_range}")
                return {'files': [], 'directories': [], 'total_files': 0, 'total_size_mb': 0}
                
        except Exception as e:
            logger.error(f"Error detecting output files: {e}")
            return {'files': [], 'directories': [], 'total_files': 0, 'total_size_mb': 0, 'error': str(e)}
    
    def parse_nuke_write_nodes(self, nuke_file):
        """Parse Nuke script to find Write node output paths"""
        write_nodes = []
        try:
            with open(nuke_file, 'r') as f:
                content = f.read()
            
            # Find Write nodes with file paths
            import re
            write_pattern = r'Write \{[^}]*?file "([^"]+)"[^}]*?\}'
            matches = re.findall(write_pattern, content, re.DOTALL)
            
            for file_path in matches:
                # Handle sequence notation (%04d, ####, etc.)
                write_nodes.append({
                    'type': 'write',
                    'file_path': file_path
                })
                
        except Exception as e:
            logger.debug(f"Failed to parse Nuke write nodes: {e}")
        
        return write_nodes
    
    def parse_silhouette_outputs(self, sfx_file):
        """Parse Silhouette project for output paths"""
        # Simplified - would need proper SFX parsing
        return []
    
    def parse_fusion_outputs(self, comp_file):
        """Parse Fusion composition for output paths"""
        # Simplified - would need proper Fusion parsing
        return []
    
    def find_rendered_frames(self, file_pattern, frame_range):
        """Find rendered frames based on file pattern and frame range"""
        rendered_files = []
        
        try:
            # Parse frame range
            if '-' in frame_range:
                start_frame, end_frame = map(int, frame_range.split('-'))
                frame_numbers = list(range(start_frame, end_frame + 1))
            else:
                frame_numbers = [int(frame_range)]
            
            # Handle different sequence notations
            base_dir = os.path.dirname(file_pattern)
            base_name = os.path.basename(file_pattern)
            
            for frame_num in frame_numbers:
                # Try different frame padding patterns
                patterns_to_try = [
                    base_name.replace('%04d', f'{frame_num:04d}'),
                    base_name.replace('####', f'{frame_num:04d}'),
                    base_name.replace('%d', str(frame_num)),
                    base_name.replace('#', str(frame_num)),
                    f"{base_name}.{frame_num:04d}.exr",
                    f"{base_name}.{frame_num:04d}.png",
                    f"{base_name}.{frame_num:04d}.jpg",
                    f"{base_name}_{frame_num:04d}.exr"
                ]
                
                for pattern in patterns_to_try:
                    full_path = os.path.join(base_dir, pattern)
                    if os.path.exists(full_path):
                        rendered_files.append(full_path)
                        break
                        
        except Exception as e:
            logger.debug(f"Error finding frames for pattern {file_pattern}: {e}")
        
        return rendered_files
    
    def find_rendered_frames_in_dir(self, search_dir, frame_range):
        """Search directory for rendered frames"""
        rendered_files = []
        
        try:
            # Parse frame range
            if '-' in frame_range:
                start_frame, end_frame = map(int, frame_range.split('-'))
                frame_numbers = list(range(start_frame, end_frame + 1))
            else:
                frame_numbers = [int(frame_range)]
            
            # Common render file extensions
            extensions = ['.exr', '.png', '.jpg', '.jpeg', '.tif', '.tiff', '.dpx']
            
            for ext in extensions:
                for frame_num in frame_numbers:
                    # Try common naming patterns
                    patterns = [
                        f"*{frame_num:04d}{ext}",
                        f"*_{frame_num:04d}{ext}",
                        f"*.{frame_num:04d}{ext}",
                        f"*{frame_num}{ext}"
                    ]
                    
                    for pattern in patterns:
                        matches = list(Path(search_dir).glob(pattern))
                        rendered_files.extend([str(f) for f in matches])
                        
        except Exception as e:
            logger.debug(f"Error searching directory {search_dir}: {e}")
        
        return list(set(rendered_files))  # Remove duplicates
    
    def start(self):
        """Start worker with enhanced resilience"""
        logger.info(f"Starting production worker {self.worker_id}")
        
        # Register with retry logic
        if not self.register_with_server():
            logger.error("Failed to register with server. Exiting.")
            return
        
        self.running = True
        
        # Start background threads
        self.start_background_threads()
        
        logger.info("✅ Worker online and ready for production")
        
        # Main work loop with error recovery
        consecutive_failures = 0
        max_failures = 10
        
        while self.running:
            try:
                job = self.get_next_job()
                
                if job:
                    consecutive_failures = 0
                    # Execute in separate thread for better resource management
                    job_thread = threading.Thread(
                        target=self.execute_render_job,
                        args=(job,),
                        name=f"RenderJob-{job['sub_job_id']}"
                    )
                    job_thread.start()
                    
                    # Dynamic polling based on system capability
                    available_ram_gb = psutil.virtual_memory().total / (1024**3)
                    if available_ram_gb >= 32:
                        # High-end systems can handle faster polling
                        time.sleep(5)  # Faster for high-end systems
                    else:
                        # Standard polling for regular systems
                        time.sleep(10)
                else:
                    # No jobs available - wait based on system capability
                    available_ram_gb = psutil.virtual_memory().total / (1024**3)
                    if available_ram_gb >= 32:
                        time.sleep(15)  # Faster polling when no jobs (high-end)
                    else:
                        time.sleep(30)  # Standard wait (regular systems)
                    
            except KeyboardInterrupt:
                logger.info("Received shutdown signal")
                self.running = False
                break
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Worker error ({consecutive_failures}/{max_failures}): {e}")
                
                if consecutive_failures >= max_failures:
                    logger.error("Too many consecutive failures, shutting down")
                    self.running = False
                else:
                    time.sleep(min(60, consecutive_failures * 10))  # Exponential backoff
        
        logger.info("🛑 Worker shutdown complete")
    
    def start_background_threads(self):
        """Start background monitoring threads"""
        # Heartbeat thread
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        
        # Metrics collection thread
        metrics_thread = threading.Thread(target=self.metrics_loop, daemon=True)
        metrics_thread.start()
        
        # Cleanup thread
        cleanup_thread = threading.Thread(target=self.cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def heartbeat_loop(self):
        """Enhanced heartbeat loop with reconnection"""
        consecutive_failures = 0
        max_failures = 6
        # Dynamic heartbeat based on system capability
        available_ram_gb = psutil.virtual_memory().total / (1024**3)
        if available_ram_gb >= 32:
            interval = self.config.get('heartbeat_interval', 20)  # Faster heartbeat for high-end systems
        else:
            interval = self.config.get('heartbeat_interval', 45)  # Standard heartbeat
        
        while self.running:
            try:
                if self.send_heartbeat():
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures >= max_failures:
                        logger.error("Lost connection to server, attempting re-registration")
                        if self.register_with_server():
                            consecutive_failures = 0
                        else:
                            logger.error("Re-registration failed, shutting down")
                            self.running = False
                            break
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                time.sleep(interval)
    
    def metrics_loop(self):
        """Periodic metrics collection and cleanup"""
        interval = self.config.get('metrics_interval', 60)  # Reduced metrics collection frequency
        
        while self.running:
            try:
                # Collect and log performance metrics
                metrics = self.metrics_collector.get_current_metrics()
                logger.debug(f"System metrics: CPU {metrics['cpu_percent']:.1f}%, "
                           f"Memory {metrics['memory_percent']:.1f}%, "
                           f"Disk {metrics['disk_free_gb']:.1f}GB free")
                
                time.sleep(interval)
                
            except Exception as e:
                logger.error(f"Metrics collection error: {e}")
                time.sleep(interval)
    
    def cleanup_loop(self):
        """Periodic cleanup of temp files and logs"""
        while self.running:
            try:
                # Clean up old temp files (older than 24 hours)
                cutoff_time = time.time() - 86400
                for temp_file in self.temp_dir.glob("*"):
                    if temp_file.stat().st_mtime < cutoff_time:
                        try:
                            temp_file.unlink()
                        except:
                            pass
                
                # Trim render history (keep last 100 entries)
                if len(self.render_history) > 100:
                    self.render_history = self.render_history[-100:]
                
                time.sleep(3600)  # Run every hour
                
            except Exception as e:
                logger.error(f"Cleanup error: {e}")
                time.sleep(3600)
    
    def stop(self):
        """Enhanced graceful shutdown with resource cleanup"""
        logger.info("Initiating enhanced graceful shutdown...")
        self.running = False
        
        # Wait for current jobs to complete (with timeout)
        shutdown_timeout = 300  # 5 minutes
        start_time = time.time()
        
        while self.current_jobs and (time.time() - start_time) < shutdown_timeout:
            logger.info(f"Waiting for {len(self.current_jobs)} jobs to complete...")
            time.sleep(10)
        
        if self.current_jobs:
            logger.warning(f"Shutdown timeout reached, {len(self.current_jobs)} jobs still running")
        
        # Clean up resources
        try:
            if hasattr(self, 'render_buffer_pool'):
                self.render_buffer_pool.cleanup()
                logger.info("Render buffer pool cleaned up")
                
            if hasattr(self, 'asset_cache'):
                cache_stats = self.asset_cache.get_stats()
                logger.info(f"Asset cache stats - Files: {cache_stats['cached_files']}, "
                          f"Size: {cache_stats['cache_size_gb']:.2f}GB, "
                          f"Hit Rate: {cache_stats['hit_ratio']:.1f}%")
                
            if hasattr(self, 'render_stats'):
                logger.info(f"Final render stats: {self.render_stats}")
                
        except Exception as e:
            logger.error(f"Error during resource cleanup: {e}")
        
        logger.info("Enhanced worker stopped")

class AssetCache:
    """LRU Cache for frequently accessed assets to maximize RAM usage"""
    
    def __init__(self, max_size_gb=4):
        self.cache = OrderedDict()
        self.max_size_bytes = max_size_gb * 1024**3
        self.current_size = 0
        self.access_times = {}
        self.hit_count = 0
        self.miss_count = 0
        self.lock = threading.RLock()
        
        logger.info(f"Asset cache initialized: {max_size_gb}GB capacity")
    
    def get_file(self, file_path):
        """Get file from cache or load and cache it"""
        with self.lock:
            if file_path in self.cache:
                # Move to end (most recently used)
                self.cache.move_to_end(file_path)
                self.access_times[file_path] = time.time()
                self.hit_count += 1
                logger.debug(f"Cache HIT: {file_path}")
                return self.cache[file_path]
            
            # Cache miss - load file
            try:
                with open(file_path, 'rb') as f:
                    data = f.read()
                
                self._add_to_cache(file_path, data)
                self.miss_count += 1
                logger.debug(f"Cache MISS: {file_path} ({len(data)} bytes)")
                return data
                
            except Exception as e:
                logger.error(f"Failed to load file {file_path}: {e}")
                raise
    
    def _add_to_cache(self, file_path, data):
        """Add file to cache with LRU eviction"""
        file_size = len(data)
        
        # Skip if file is too large for cache
        if file_size > self.max_size_bytes * 0.5:
            logger.warning(f"File too large for cache: {file_path} ({file_size} bytes)")
            return
        
        # Evict old files if needed
        while self.current_size + file_size > self.max_size_bytes and self.cache:
            self._evict_lru()
        
        self.cache[file_path] = data
        self.current_size += file_size
        self.access_times[file_path] = time.time()
        
        logger.debug(f"Cached: {file_path} ({file_size} bytes, {len(self.cache)} files, {self.current_size/1024**3:.2f}GB)")
    
    def _evict_lru(self):
        """Evict least recently used item"""
        if not self.cache:
            return
            
        # Remove oldest item (first in OrderedDict)
        oldest_path, oldest_data = self.cache.popitem(last=False)
        file_size = len(oldest_data)
        self.current_size -= file_size
        
        if oldest_path in self.access_times:
            del self.access_times[oldest_path]
        
        logger.debug(f"Evicted: {oldest_path} ({file_size} bytes)")
    
    def get_stats(self):
        """Get cache statistics"""
        with self.lock:
            total_requests = self.hit_count + self.miss_count
            hit_ratio = (self.hit_count / total_requests * 100) if total_requests > 0 else 0
            
            return {
                'hit_count': self.hit_count,
                'miss_count': self.miss_count,
                'hit_ratio': hit_ratio,
                'cached_files': len(self.cache),
                'cache_size_gb': self.current_size / 1024**3,
                'cache_usage_percent': (self.current_size / self.max_size_bytes) * 100
            }


class RenderBufferPool:
    """Shared memory pool for render operations"""
    
    def __init__(self, buffer_size_mb=512, max_buffers=8):
        self.buffer_size = buffer_size_mb * 1024 * 1024
        self.max_buffers = max_buffers
        self.available_buffers = []
        self.in_use_buffers = {}
        self.lock = threading.Lock()
        
        logger.info(f"Render buffer pool initialized: {max_buffers} x {buffer_size_mb}MB buffers")
    
    def get_buffer(self, job_id):
        """Get a render buffer from pool"""
        with self.lock:
            if self.available_buffers:
                buffer = self.available_buffers.pop()
                logger.debug(f"Reusing buffer for job {job_id}")
            elif len(self.in_use_buffers) < self.max_buffers:
                try:
                    buffer = shared_memory.SharedMemory(
                        create=True, size=self.buffer_size
                    )
                    logger.debug(f"Created new buffer for job {job_id}")
                except Exception as e:
                    logger.warning(f"Failed to create shared memory buffer: {e}")
                    return None
            else:
                logger.warning(f"No buffers available for job {job_id}")
                return None
            
            self.in_use_buffers[job_id] = buffer
            return buffer
    
    def return_buffer(self, job_id):
        """Return buffer to pool"""
        with self.lock:
            if job_id in self.in_use_buffers:
                buffer = self.in_use_buffers.pop(job_id)
                self.available_buffers.append(buffer)
                logger.debug(f"Buffer returned from job {job_id}")
    
    def cleanup(self):
        """Clean up all buffers"""
        with self.lock:
            for buffer in self.available_buffers + list(self.in_use_buffers.values()):
                try:
                    buffer.close()
                    buffer.unlink()
                except:
                    pass
            self.available_buffers.clear()
            self.in_use_buffers.clear()


class AsyncFileManager:
    """Async file operations and preloading"""
    
    def __init__(self):
        self.preloaded_assets = {}
        self.preload_lock = asyncio.Lock()
        
    async def preload_assets(self, asset_list):
        """Preload assets into RAM in background"""
        tasks = []
        for asset_path in asset_list:
            if asset_path not in self.preloaded_assets:
                task = asyncio.create_task(self._load_asset(asset_path))
                tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info(f"Preloaded {len(tasks)} assets")
    
    async def _load_asset(self, asset_path):
        """Load single asset asynchronously"""
        try:
            async with aiofiles.open(asset_path, 'rb') as f:
                data = await f.read()
                async with self.preload_lock:
                    self.preloaded_assets[asset_path] = data
                logger.debug(f"Preloaded: {asset_path}")
        except Exception as e:
            logger.error(f"Failed to preload {asset_path}: {e}")
    
    def get_preloaded(self, asset_path):
        """Get preloaded asset data"""
        return self.preloaded_assets.get(asset_path)


class SystemMetricsCollector:
    """Collect system performance metrics"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_current_metrics(self):
        """Get current system metrics"""
        try:
            # CPU metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()
            
            # Memory metrics
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Disk metrics
            disk = psutil.disk_usage('.')
            disk_free_gb = disk.free / (1024**3)
            disk_percent = disk.percent
            
            # Network metrics
            network = psutil.net_io_counters()
            
            return {
                'cpu_percent': cpu_percent,
                'cpu_count': cpu_count,
                'memory_percent': memory_percent,
                'memory_available_gb': round(memory_available_gb, 2),
                'disk_free_gb': round(disk_free_gb, 2),
                'disk_percent': disk_percent,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Metrics collection failed: {e}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_free_gb': 0,
                'error': str(e)
            }

def main():
    parser = argparse.ArgumentParser(description='Production Render Farm Worker Node')
    parser.add_argument('--server', required=True,
                       help='Server URL (e.g., http://192.168.1.100:8080)')
    parser.add_argument('--worker-id',
                       help='Worker ID (auto-generated if not provided)')
    parser.add_argument('--config', default='worker_config.json',
                       help='Configuration file path')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    
    args = parser.parse_args()
    
    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))
    
    logger.info("="*60)
    logger.info("🎬 Production Render Farm Worker Node")
    logger.info("="*60)
    
    # Check dependencies
    try:
        import psutil
    except ImportError:
        logger.error("psutil not installed. Run: pip install psutil")
        sys.exit(1)
    
    worker = ProductionRenderWorker(args.server, args.worker_id, args.config)
    
    try:
        worker.start()
    except KeyboardInterrupt:
        worker.stop()
    except Exception as e:
        logger.error(f"Fatal worker error: {e}")
        worker.stop()
        sys.exit(1)

if __name__ == '__main__':
    main()