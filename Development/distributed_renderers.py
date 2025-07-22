import os
import re
import shutil
import sqlite3
from abc import ABC, abstractmethod

class DistributedRenderer(ABC):
    def __init__(self, queue_manager):
        self.queue_manager = queue_manager
    
    @abstractmethod
    def process_job(self, job_id, job_data):
        """Process a job and create sub-jobs for workers"""
        pass
    
    def parse_frame_range(self, frame_range_str):
        """Parse frame range string into list of frame numbers"""
        frames = []
        parts = frame_range_str.split(',')
        
        for part in parts:
            part = part.strip()
            if '-' in part:
                start, end = map(int, part.split('-'))
                frames.extend(range(start, end + 1))
            else:
                frames.append(int(part))
        
        return sorted(list(set(frames)))  # Remove duplicates and sort
    
    def create_batches(self, frames, batch_size):
        """Split frames into batches"""
        batches = []
        for i in range(0, len(frames), batch_size):
            batch_frames = frames[i:i + batch_size]
            if len(batch_frames) == 1:
                frame_range = str(batch_frames[0])
            else:
                frame_range = f"{batch_frames[0]}-{batch_frames[-1]}"
            batches.append(frame_range)
        
        return batches
    
    def create_sub_jobs(self, job_id, batches):
        """Create sub-jobs in the database"""
        conn = sqlite3.connect(self.queue_manager.db_path)
        cursor = conn.cursor()
        
        for i, batch in enumerate(batches):
            sub_job_id = f"{job_id}_batch_{i+1:03d}"
            cursor.execute("""
                INSERT INTO sub_jobs (id, parent_job_id, batch_number, frame_range)
                VALUES (?, ?, ?, ?)
            """, (sub_job_id, job_id, i+1, batch))
        
        conn.commit()
        conn.close()

class DistributedNukeRenderer(DistributedRenderer):
    def process_job(self, job_id, job_data):
        """Process Nuke job"""
        print(f"Processing Nuke job {job_id}: {job_data['job_title']}")
        
        # Parse frame range
        frames = self.parse_frame_range(job_data['frame_range'])
        batch_size = job_data['batch_size']
        
        print(f"Total frames: {len(frames)}, Batch size: {batch_size}")
        
        # Create batches
        batches = self.create_batches(frames, batch_size)
        print(f"Created {len(batches)} batches: {batches}")
        
        # Create sub-jobs
        self.create_sub_jobs(job_id, batches)
        
        # Handle path translation if enabled
        if job_data.get('enable_path_translation', False):
            self.prepare_nuke_script(job_data)
    
    def prepare_nuke_script(self, job_data):
        """Prepare Nuke script with path translation"""
        original_path = job_data['file_path']
        
        # Create temp directory if it doesn't exist
        temp_dir = os.path.join(os.path.dirname(original_path), 'temp_scripts')
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
        
        # Copy script to temp location
        temp_script = os.path.join(temp_dir, f"processed_{os.path.basename(original_path)}")
        shutil.copy2(original_path, temp_script)
        
        # Translate paths in the script
        try:
            with open(temp_script, 'r') as f:
                content = f.read()
            
            # Replace local paths with network paths
            network_share = job_data.get('network_share', '')
            if network_share:
                content = self.translate_nuke_paths(content, network_share)
            
            with open(temp_script, 'w') as f:
                f.write(content)
            
            # Update job data with temp script path
            job_data['processed_file_path'] = temp_script
            print(f"Created processed script: {temp_script}")
            
        except Exception as e:
            print(f"Warning: Failed to process script paths: {e}")
            # Continue with original script if path translation fails
    
    def translate_nuke_paths(self, content, network_share):
        """Translate paths in Nuke script content"""
        # Pattern to find Read nodes with file paths
        read_patterns = [
            r'Read \{\n.*?\nfile "([^"]+)"',
            r'Read \{\n.*?\nfile ([^\n]+)',
            r'Read \{\n.*?\n file "([^"]+)"',
            r'Read \{\n.*?\n file ([^\n]+)',
        ]
        
        # Pattern to find Write nodes with file paths
        write_patterns = [
            r'Write \{\n.*?\nfile "([^"]+)"',
            r'Write \{\n.*?\nfile ([^\n]+)',
            r'Write \{\n.*?\n file "([^"]+)"',
            r'Write \{\n.*?\n file ([^\n]+)',
            r'Write \{\n file "([^"]+)"',
            r'Write \{\n file ([^\n]+)',
            r'Write \{\nfile "([^"]+)"',
            r'Write \{\nfile ([^\n]+)',
        ]
        
        all_patterns = read_patterns + write_patterns
        
        for pattern in all_patterns:
            matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                original_path = match.strip().replace('"', '')
                if ':/' in original_path:  # Windows absolute path
                    # Convert C:/ to network share
                    new_path = original_path.replace('C:/', network_share + '/')
                    new_path = new_path.replace('D:/', network_share + '/')
                    new_path = new_path.replace('\\', '/')
                    content = content.replace(original_path, new_path)
        
        return content

class DistributedSilhouetteRenderer(DistributedRenderer):
    def process_job(self, job_id, job_data):
        """Process Silhouette job"""
        print(f"Processing Silhouette job {job_id}: {job_data['job_title']}")
        
        # Parse frame range
        frames = self.parse_frame_range(job_data['frame_range'])
        batch_size = job_data['batch_size']
        
        print(f"Total frames: {len(frames)}, Batch size: {batch_size}")
        
        # Create batches
        batches = self.create_batches(frames, batch_size)
        print(f"Created {len(batches)} batches: {batches}")
        
        # Create sub-jobs
        self.create_sub_jobs(job_id, batches)

class DistributedFusionRenderer(DistributedRenderer):
    def process_job(self, job_id, job_data):
        """Process Fusion job"""
        print(f"Processing Fusion job {job_id}: {job_data['job_title']}")
        
        # Parse frame range
        frames = self.parse_frame_range(job_data['frame_range'])
        batch_size = job_data['batch_size']
        
        print(f"Total frames: {len(frames)}, Batch size: {batch_size}")
        
        # Create batches
        batches = self.create_batches(frames, batch_size)
        print(f"Created {len(batches)} batches: {batches}")
        
        # Create sub-jobs
        self.create_sub_jobs(job_id, batches)