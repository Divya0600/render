#!/usr/bin/env python3

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import urllib.parse
import threading
import sys
import signal
from job_queue_manager import JobQueueManager

class RenderFarmAPIHandler(BaseHTTPRequestHandler):
    # Class variable to share queue manager across all handler instances
    queue_manager = None
    
    @classmethod
    def set_queue_manager(cls, queue_manager):
        cls.queue_manager = queue_manager
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests"""
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def send_cors_headers(self):
        """Send CORS headers"""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
    
    def do_GET(self):
        """Handle GET requests"""
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        query_params = urllib.parse.parse_qs(parsed_path.query)
        
        print(f"GET {path} from {self.client_address[0]}")
        
        if path == '/api/jobs/next':
            worker_id = query_params.get('worker_id', [None])[0]
            if worker_id:
                job = self.queue_manager.get_next_job(worker_id)
                if job:
                    print(f"Assigned job {job['sub_job_id']} to worker {worker_id}")
                    self.send_json_response(job)
                else:
                    # No jobs available
                    self.send_json_response(None, 204)
            else:
                self.send_error_response(400, "Missing worker_id parameter")
                
        elif path == '/api/status':
            # Enhanced status endpoint with cache information
            cache_stats = self.queue_manager.get_cache_stats() if hasattr(self.queue_manager, 'get_cache_stats') else {}
            
            status = {
                'status': 'online',
                'online_workers': self.queue_manager.get_online_workers(),
                'total_jobs': len(self.queue_manager.get_all_jobs()),
                'server_time': self.get_server_timestamp(),
                'cache_stats': cache_stats,
                'version': '2.0-optimized'
            }
            self.send_json_response(status)
            
        elif path == '/':
            # Simple root endpoint
            self.send_html_response("""
            <html>
            <head><title>Render Farm API Server</title></head>
            <body>
                <h1>🎬 Render Farm API Server</h1>
                <p>Status: <strong>Online</strong></p>
                <p>Workers Online: <strong>{}</strong></p>
                <p>Total Jobs: <strong>{}</strong></p>
                <h2>API Endpoints:</h2>
                <ul>
                    <li>GET /api/status - Server status</li>
                    <li>GET /api/jobs/next?worker_id=XXX - Get next job for worker</li>
                    <li>POST /api/workers/register - Register worker</li>
                    <li>POST /api/workers/heartbeat - Worker heartbeat</li>
                    <li>POST /api/jobs/complete - Report job completion</li>
                </ul>
            </body>
            </html>
            """.format(
                self.queue_manager.get_online_workers(),
                len(self.queue_manager.get_all_jobs())
            ))
        else:
            self.send_error_response(404, "Endpoint not found")
    
    def do_POST(self):
        """Handle POST requests"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 0:
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                self.send_error_response(400, "Invalid JSON in request body")
                return
        else:
            data = {}
        
        path = self.path
        print(f"POST {path} from {self.client_address[0]}")
        
        if path == '/api/workers/register':
            try:
                worker_id = data['worker_id']
                ip_address = data['ip_address']
                hostname = data['hostname']
                capabilities = data['capabilities']
                
                self.queue_manager.register_worker(worker_id, ip_address, hostname, capabilities)
                print(f"✅ Registered worker: {worker_id} ({hostname} - {ip_address})")
                self.send_json_response({'status': 'registered', 'worker_id': worker_id})
                
            except KeyError as e:
                self.send_error_response(400, f"Missing required field: {e}")
            except Exception as e:
                self.send_error_response(500, f"Registration failed: {str(e)}")
            
        elif path == '/api/workers/heartbeat':
            try:
                worker_id = data['worker_id']
                system_metrics = data.get('system_metrics', {})
                current_jobs = data.get('current_jobs', [])
                worker_status = data.get('status', 'unknown')
                
                # Enhanced heartbeat with system metrics
                self.queue_manager.worker_heartbeat(worker_id, system_metrics)
                
                # Log performance metrics periodically
                if system_metrics and hasattr(self, '_heartbeat_counter'):
                    self._heartbeat_counter += 1
                else:
                    self._heartbeat_counter = 1
                
                # Log detailed metrics every 10 heartbeats to avoid spam
                if self._heartbeat_counter % 10 == 0:
                    cpu = system_metrics.get('cpu_percent', 0)
                    memory = system_metrics.get('memory_percent', 0)
                    jobs_count = len(current_jobs)
                    print(f"📊 Worker {worker_id}: CPU {cpu:.1f}%, RAM {memory:.1f}%, Jobs: {jobs_count}")
                
                response = {
                    'status': 'ok',
                    'server_time': self.get_server_timestamp(),
                    'cache_stats': self.queue_manager.get_cache_stats() if hasattr(self.queue_manager, 'get_cache_stats') else {}
                }
                self.send_json_response(response)
                
            except KeyError:
                self.send_error_response(400, "Missing worker_id")
            except Exception as e:
                self.send_error_response(500, f"Heartbeat failed: {str(e)}")
            
        elif path == '/api/jobs/complete':
            try:
                sub_job_id = data['sub_job_id']
                worker_id = data['worker_id']
                success = data['success']
                error_message = data.get('error_message')
                metrics = data.get('metrics', {})
                
                # Enhanced job completion with metrics
                self.queue_manager.complete_sub_job(sub_job_id, success, error_message, metrics)
                
                if success:
                    render_time = metrics.get('render_time', 0)
                    output_info = metrics.get('output_info', {})
                    frames_count = output_info.get('total_files', 0)
                    
                    print(f"✅ Job {sub_job_id} completed by {worker_id} in {render_time:.1f}s")
                    
                    # Log output locations if available
                    if output_info.get('directories'):
                        print(f"📁 Output saved to: {', '.join(output_info['directories'])}")
                        print(f"🎞️  {frames_count} frames ({output_info.get('total_size_mb', 0):.1f}MB)")
                else:
                    print(f"❌ Job {sub_job_id} failed on worker {worker_id}: {error_message}")
                
                self.send_json_response({'status': 'updated'})
                
            except KeyError as e:
                self.send_error_response(400, f"Missing required field: {e}")
            except Exception as e:
                self.send_error_response(500, f"Job completion update failed: {str(e)}")
            
        else:
            self.send_error_response(404, "Endpoint not found")
    
    def send_json_response(self, data, status_code=200):
        """Send JSON response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_cors_headers()
        self.end_headers()
        if data is not None:
            response_json = json.dumps(data, indent=2)
            self.wfile.write(response_json.encode('utf-8'))
    
    def send_html_response(self, html, status_code=200):
        """Send HTML response"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'text/html')
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(html.encode('utf-8'))
    
    def send_error_response(self, status_code, message):
        """Send error response"""
        error_data = {'error': message, 'status_code': status_code}
        self.send_json_response(error_data, status_code)
    
    def get_server_timestamp(self):
        """Get current server timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def log_message(self, format, *args):
        """Override to customize logging"""
        # Only log errors, not every request
        if 'POST' in format or 'GET' in format:
            return  # Skip normal request logging
        return super().log_message(format, *args)

class RenderFarmServer:
    def __init__(self, port=8080, host=''):
        self.port = port
        self.host = host
        self.httpd = None
        self.queue_manager = JobQueueManager()
        
        # Set the queue manager for the handler class
        RenderFarmAPIHandler.set_queue_manager(self.queue_manager)
        
    def start(self):
        """Start the server"""
        server_address = (self.host, self.port)
        
        try:
            self.httpd = HTTPServer(server_address, RenderFarmAPIHandler)
            
            print("="*60)
            print("🎬 Render Farm API Server")
            print("="*60)
            print(f"Server running on http://localhost:{self.port}")
            print(f"Server accessible at http://{self.get_local_ip()}:{self.port}")
            print()
            print("Available endpoints:")
            print(f"  • Status: http://localhost:{self.port}/api/status")
            print(f"  • Web UI: http://localhost:{self.port}/")
            print()
            print("Press Ctrl+C to stop the server")
            print("="*60)
            
            # Set up signal handlers for graceful shutdown
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
            
            self.httpd.serve_forever()
            
        except OSError as e:
            if e.errno == 48:  # Address already in use
                print(f"❌ Error: Port {self.port} is already in use")
                print(f"Please check if another server is running or use a different port:")
                print(f"python server.py --port 8081")
            else:
                print(f"❌ Server error: {e}")
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """Stop the server"""
        print("\n🛑 Shutting down server...")
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
        print("✅ Server stopped")
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stop()
        sys.exit(0)
    
    def get_local_ip(self):
        """Get local IP address"""
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "localhost"

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Render Farm API Server')
    parser.add_argument('--port', type=int, default=8080,
                       help='Port to run the server on (default: 8080)')
    parser.add_argument('--host', default='',
                       help='Host to bind to (default: all interfaces)')
    
    args = parser.parse_args()
    
    server = RenderFarmServer(port=args.port, host=args.host)
    
    try:
        server.start()
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()