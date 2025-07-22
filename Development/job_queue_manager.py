import sqlite3
import json
import uuid
import time
from datetime import datetime
import threading
import os
from collections import OrderedDict

class JobQueueManager:
    def __init__(self, db_path="render_farm.db"):
        self.db_path = db_path
        self.init_database()
        self.lock = threading.Lock()
        
        # Memory cache for faster job operations
        self.job_cache = OrderedDict()
        self.worker_cache = OrderedDict()
        self.cache_max_size = 1000
        self.cache_enabled = True
        
        print("JobQueueManager initialized with memory caching enabled")
    
    def init_database(self):
        """Initialize the SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Jobs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                renderer TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                progress REAL DEFAULT 0.0,
                priority TEXT DEFAULT 'normal',
                job_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                worker_id TEXT,
                error_message TEXT
            )
        """)
        
        # Sub-jobs table (for batches)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sub_jobs (
                id TEXT PRIMARY KEY,
                parent_job_id TEXT NOT NULL,
                batch_number INTEGER NOT NULL,
                frame_range TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                worker_id TEXT,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                error_message TEXT,
                FOREIGN KEY (parent_job_id) REFERENCES jobs (id)
            )
        """)
        
        # Workers table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workers (
                id TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL,
                hostname TEXT,
                status TEXT DEFAULT 'offline',
                current_job_id TEXT,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                capabilities TEXT,
                cpu_count INTEGER,
                memory_gb REAL
            )
        """)
        
        conn.commit()
        conn.close()
    
    def submit_job(self, job_data):
        """Submit a new job to the queue"""
        job_id = str(uuid.uuid4())
        
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO jobs (id, title, renderer, job_data, priority)
                VALUES (?, ?, ?, ?, ?)
            """, (
                job_id,
                job_data['job_title'],
                job_data['renderer'],
                json.dumps(job_data),
                job_data.get('priority', 'normal').lower()
            ))
            
            conn.commit()
            conn.close()
        
        return job_id
    
    def get_all_jobs(self):
        """Get all jobs with their status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title, status, progress, created_at, worker_id, 
                   json_extract(job_data, '$.frame_range') as frame_range,
                   priority
            FROM jobs 
            ORDER BY created_at DESC
        """)
        
        jobs = []
        for row in cursor.fetchall():
            jobs.append({
                'id': row[0],
                'title': row[1],
                'status': row[2],
                'progress': row[3],
                'created_at': row[4],
                'worker_id': row[5],
                'frame_range': row[6],
                'priority': row[7]
            })
        
        conn.close()
        return jobs
    
    def get_next_job(self, worker_id):
        """Get the next job for a worker with memory caching optimization"""
        with self.lock:
            # Try memory cache first for faster retrieval
            if self.cache_enabled:
                cached_job = self._get_job_from_cache(worker_id)
                if cached_job:
                    print(f"Retrieved job from memory cache for worker {worker_id}")
                    return cached_job
            
            # Fallback to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Look for pending sub-jobs first, ordered by priority
            cursor.execute("""
                SELECT sj.id, sj.parent_job_id, sj.frame_range, j.job_data
                FROM sub_jobs sj
                JOIN jobs j ON sj.parent_job_id = j.id
                WHERE sj.status = 'pending'
                ORDER BY 
                    CASE j.priority 
                        WHEN 'critical' THEN 1
                        WHEN 'high' THEN 2
                        WHEN 'normal' THEN 3
                        WHEN 'low' THEN 4
                        ELSE 5
                    END,
                    j.created_at ASC
                LIMIT 5
            """)
            
            results = cursor.fetchall()
            if results:
                # Take first job and cache the rest
                result = results[0]
                sub_job_id, parent_job_id, frame_range, job_data_str = result
                job_data = json.loads(job_data_str)
                
                # Cache remaining jobs for faster access
                if self.cache_enabled and len(results) > 1:
                    self._cache_pending_jobs(results[1:], cursor)
                
                # Mark sub-job as running
                cursor.execute("""
                    UPDATE sub_jobs 
                    SET status = 'running', worker_id = ?, started_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (worker_id, sub_job_id))
                
                # Update parent job status if needed
                cursor.execute("""
                    UPDATE jobs 
                    SET status = 'running', started_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND status = 'pending'
                """, (parent_job_id,))
                
                conn.commit()
                conn.close()
                
                return {
                    'sub_job_id': sub_job_id,
                    'parent_job_id': parent_job_id,
                    'frame_range': frame_range,
                    'job_data': job_data
                }
            
            conn.close()
            return None
    
    def _get_job_from_cache(self, worker_id):
        """Get job from memory cache"""
        try:
            for job_id in list(self.job_cache.keys()):
                job_data = self.job_cache[job_id]
                if job_data.get('status') == 'pending':
                    # Move to end (mark as accessed)
                    self.job_cache.move_to_end(job_id)
                    
                    # Mark as running
                    job_data['status'] = 'running'
                    job_data['worker_id'] = worker_id
                    job_data['started_at'] = datetime.now().isoformat()
                    
                    return job_data
        except Exception as e:
            print(f"Cache retrieval error: {e}")
        
        return None
    
    def _cache_pending_jobs(self, job_results, cursor):
        """Cache pending jobs for faster access"""
        try:
            for result in job_results[:10]:  # Cache up to 10 jobs
                sub_job_id, parent_job_id, frame_range, job_data_str = result
                job_data = json.loads(job_data_str)
                
                cached_job = {
                    'sub_job_id': sub_job_id,
                    'parent_job_id': parent_job_id,
                    'frame_range': frame_range,
                    'job_data': job_data,
                    'status': 'pending',
                    'cached_at': time.time()
                }
                
                # Add to cache with size limit
                if len(self.job_cache) >= self.cache_max_size:
                    # Remove oldest entry
                    self.job_cache.popitem(last=False)
                
                self.job_cache[sub_job_id] = cached_job
                
        except Exception as e:
            print(f"Cache population error: {e}")
    
    def complete_sub_job(self, sub_job_id, success=True, error_message=None, metrics=None):
        """Mark a sub-job as completed with enhanced tracking"""
        with self.lock:
            # Update memory cache first
            if self.cache_enabled and sub_job_id in self.job_cache:
                cached_job = self.job_cache[sub_job_id]
                cached_job['status'] = 'completed' if success else 'failed'
                cached_job['completed_at'] = datetime.now().isoformat()
                cached_job['error_message'] = error_message
                cached_job['metrics'] = metrics or {}
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            status = 'completed' if success else 'failed'
            
            # Store metrics as JSON if provided
            metrics_json = json.dumps(metrics) if metrics else None
            
            cursor.execute("""
                UPDATE sub_jobs 
                SET status = ?, completed_at = CURRENT_TIMESTAMP, error_message = ?
                WHERE id = ?
            """, (status, error_message, sub_job_id))
            
            # Get parent job ID
            cursor.execute("SELECT parent_job_id FROM sub_jobs WHERE id = ?", (sub_job_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                return
                
            parent_job_id = result[0]
            
            # Check if all sub-jobs are completed
            cursor.execute("""
                SELECT COUNT(*) as total, 
                       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed
                FROM sub_jobs 
                WHERE parent_job_id = ?
            """, (parent_job_id,))
            
            total, completed = cursor.fetchone()
            progress = (completed / total) * 100 if total > 0 else 0
            
            # Update parent job progress
            cursor.execute("""
                UPDATE jobs 
                SET progress = ?
                WHERE id = ?
            """, (progress, parent_job_id))
            
            # If all sub-jobs are done, mark parent as completed
            if completed == total:
                cursor.execute("""
                    UPDATE jobs 
                    SET status = 'completed', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (parent_job_id,))
                
                # Log completion with metrics if available
                if metrics:
                    output_info = metrics.get('output_info', {})
                    if output_info.get('directories'):
                        print(f"\n🎬 JOB COMPLETED: {parent_job_id}")
                        print(f"📁 Output locations:")
                        for directory in output_info['directories']:
                            print(f"   └── {directory}")
                        print(f"📊 Total files: {output_info.get('total_files', 0)}")
                        print(f"💾 Total size: {output_info.get('total_size_mb', 0):.1f}MB")
            
            conn.commit()
            conn.close()
            
            # Periodic cache optimization
            if hasattr(self, '_cache_optimization_counter'):
                self._cache_optimization_counter += 1
            else:
                self._cache_optimization_counter = 1
            
            # Optimize cache every 50 job completions
            if self._cache_optimization_counter % 50 == 0:
                self.optimize_cache()
    
    def register_worker(self, worker_id, ip_address, hostname, capabilities):
        """Register a worker node"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO workers 
                (id, ip_address, hostname, status, capabilities, last_heartbeat)
                VALUES (?, ?, ?, 'online', ?, CURRENT_TIMESTAMP)
            """, (worker_id, ip_address, hostname, json.dumps(capabilities)))
            
            conn.commit()
            conn.close()
    
    def worker_heartbeat(self, worker_id, system_metrics=None):
        """Update worker heartbeat with optional system metrics"""
        with self.lock:
            # Update memory cache
            if self.cache_enabled:
                self.worker_cache[worker_id] = {
                    'last_heartbeat': datetime.now().isoformat(),
                    'status': 'online',
                    'system_metrics': system_metrics or {},
                    'updated_at': time.time()
                }
                
                # Trim cache if too large
                if len(self.worker_cache) > self.cache_max_size:
                    # Remove oldest entries
                    for _ in range(len(self.worker_cache) - self.cache_max_size):
                        self.worker_cache.popitem(last=False)
            
            # Update database (async-like by reducing frequency)
            if not hasattr(self, '_last_db_heartbeat'):
                self._last_db_heartbeat = {}
            
            current_time = time.time()
            last_update = self._last_db_heartbeat.get(worker_id, 0)
            
            # Only update database every 30 seconds to reduce I/O
            if current_time - last_update > 30:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE workers 
                    SET last_heartbeat = CURRENT_TIMESTAMP, status = 'online'
                    WHERE id = ?
                """, (worker_id,))
                
                conn.commit()
                conn.close()
                
                self._last_db_heartbeat[worker_id] = current_time
    
    def get_online_workers(self):
        """Get count of online workers with memory cache optimization"""
        if self.cache_enabled and self.worker_cache:
            # Count from memory cache first
            current_time = time.time()
            online_count = 0
            
            for worker_id, worker_data in self.worker_cache.items():
                last_update = worker_data.get('updated_at', 0)
                if current_time - last_update < 60:  # Within last minute
                    online_count += 1
            
            if online_count > 0:
                return online_count
        
        # Fallback to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT COUNT(*) 
            FROM workers 
            WHERE status = 'online' 
            AND datetime(last_heartbeat) > datetime('now', '-30 seconds')
        """)
        
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_all_workers(self):
        """Get all workers with their status"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, ip_address, hostname, status, current_job_id, 
                   last_heartbeat, cpu_count,
                   CASE 
                       WHEN datetime(last_heartbeat) > datetime('now', '-30 seconds') THEN 'Online'
                       ELSE 'Offline'
                   END as actual_status
            FROM workers 
            ORDER BY last_heartbeat DESC
        """)
        
        workers = []
        for row in cursor.fetchall():
            workers.append({
                'id': row[0],
                'ip_address': row[1],
                'hostname': row[2],
                'status': row[7],  # Use actual_status (online/offline based on heartbeat)
                'current_job_id': row[4] or 'None',
                'last_heartbeat': row[5],
                'cpu_count': row[6] or 0
            })
        
        conn.close()
        return workers
    
    def pause_all_jobs(self):
        """Pause all running jobs"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE jobs SET status = 'paused' WHERE status = 'running'")
            cursor.execute("UPDATE sub_jobs SET status = 'paused' WHERE status = 'running'")
            
            conn.commit()
            conn.close()
    
    def resume_all_jobs(self):
        """Resume all paused jobs"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE jobs SET status = 'running' WHERE status = 'paused'")
            cursor.execute("UPDATE sub_jobs SET status = 'pending' WHERE status = 'paused'")
            
            conn.commit()
            conn.close()
    
    def pause_job(self, job_id):
        """Pause a specific job"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE jobs SET status = 'paused' WHERE id = ?", (job_id,))
            cursor.execute("UPDATE sub_jobs SET status = 'paused' WHERE parent_job_id = ? AND status = 'running'", (job_id,))
            
            conn.commit()
            conn.close()
    
    def resume_job(self, job_id):
        """Resume a specific job"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE jobs SET status = 'running' WHERE id = ?", (job_id,))
            cursor.execute("UPDATE sub_jobs SET status = 'pending' WHERE parent_job_id = ? AND status = 'paused'", (job_id,))
            
            conn.commit()
            conn.close()
    
    def cancel_job(self, job_id):
        """Cancel a specific job"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE jobs SET status = 'cancelled' WHERE id = ?", (job_id,))
            cursor.execute("UPDATE sub_jobs SET status = 'cancelled' WHERE parent_job_id = ?", (job_id,))
            
            conn.commit()
            conn.close()
    
    def remove_worker(self, worker_id):
        """Remove a worker from the database"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM workers WHERE id = ?", (worker_id,))
            
            conn.commit()
            conn.close()
    
    def stop_worker(self, worker_id):
        """Mark worker as stopped"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("UPDATE workers SET status = 'stopped' WHERE id = ?", (worker_id,))
            
            conn.commit()
            conn.close()
    
    def clear_completed_jobs(self):
        """Clear completed jobs from the database and cache"""
        with self.lock:
            # Clear from memory cache
            if self.cache_enabled:
                completed_jobs = [job_id for job_id, job_data in self.job_cache.items() 
                                if job_data.get('status') == 'completed']
                for job_id in completed_jobs:
                    del self.job_cache[job_id]
                
                print(f"Cleared {len(completed_jobs)} completed jobs from cache")
            
            # Clear from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sub_jobs WHERE parent_job_id IN (SELECT id FROM jobs WHERE status = 'completed')")
            cursor.execute("DELETE FROM jobs WHERE status = 'completed'")
            
            conn.commit()
            conn.close()
    
    def get_cache_stats(self):
        """Get memory cache statistics"""
        if not self.cache_enabled:
            return {'cache_enabled': False}
        
        job_cache_size = len(self.job_cache)
        worker_cache_size = len(self.worker_cache)
        
        # Calculate memory usage (rough estimate)
        job_memory_kb = sum(len(str(job_data)) for job_data in self.job_cache.values()) / 1024
        worker_memory_kb = sum(len(str(worker_data)) for worker_data in self.worker_cache.values()) / 1024
        
        return {
            'cache_enabled': True,
            'job_cache_entries': job_cache_size,
            'worker_cache_entries': worker_cache_size,
            'job_cache_memory_kb': round(job_memory_kb, 2),
            'worker_cache_memory_kb': round(worker_memory_kb, 2),
            'total_memory_mb': round((job_memory_kb + worker_memory_kb) / 1024, 2)
        }
    
    def optimize_cache(self):
        """Optimize memory cache by removing stale entries"""
        if not self.cache_enabled:
            return
        
        current_time = time.time()
        stale_threshold = 300  # 5 minutes
        
        # Clean stale job cache entries
        stale_jobs = [job_id for job_id, job_data in self.job_cache.items() 
                     if current_time - job_data.get('cached_at', 0) > stale_threshold]
        
        for job_id in stale_jobs:
            del self.job_cache[job_id]
        
        # Clean stale worker cache entries
        stale_workers = [worker_id for worker_id, worker_data in self.worker_cache.items() 
                        if current_time - worker_data.get('updated_at', 0) > stale_threshold]
        
        for worker_id in stale_workers:
            del self.worker_cache[worker_id]
        
        if stale_jobs or stale_workers:
            print(f"Cache optimization: removed {len(stale_jobs)} stale jobs, {len(stale_workers)} stale workers")