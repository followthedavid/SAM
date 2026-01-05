#!/usr/bin/env python3
"""
SAM Persistent Job Queue
- Survives crashes with local JSON state
- Processes jobs in background
- Auto-queues new work as files transfer
"""

import json
import os
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from enum import Enum

QUEUE_FILE = Path.home() / ".sam_job_queue.json"
LOCK_FILE = Path.home() / ".sam_job_queue.lock"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class JobType(str, Enum):
    QUALITY_ANALYSIS = "quality_analysis"
    VERIFY_AUDIO = "verify_audio"
    BEETS_IMPORT = "beets_import"
    FIX_FEATURED_ARTISTS = "fix_featured_artists"
    WRITE_METADATA = "write_metadata"
    MOVE_FILES = "move_files"
    CATALOG_RESEARCH = "catalog_research"
    FETCH_LYRICS = "fetch_lyrics"
    FETCH_CD_SCANS = "fetch_cd_scans"
    FETCH_ANIMATED_COVERS = "fetch_animated_covers"
    REFRESH_NAVIDROME = "refresh_navidrome"

class JobQueue:
    def __init__(self):
        self.queue_file = QUEUE_FILE
        self.lock_file = LOCK_FILE
        self.load()

    def load(self):
        """Load queue from disk"""
        if self.queue_file.exists():
            try:
                with open(self.queue_file, 'r') as f:
                    data = json.load(f)
                    self.jobs = data.get('jobs', [])
                    self.completed = data.get('completed', [])
                    self.stats = data.get('stats', {})
            except:
                self.jobs = []
                self.completed = []
                self.stats = {}
        else:
            self.jobs = []
            self.completed = []
            self.stats = {}

    def save(self):
        """Persist queue to disk"""
        data = {
            'jobs': self.jobs,
            'completed': self.completed[-100:],  # Keep last 100 completed
            'stats': self.stats,
            'last_updated': datetime.now().isoformat()
        }
        # Atomic write
        temp_file = str(self.queue_file) + '.tmp'
        with open(temp_file, 'w') as f:
            json.dump(data, f, indent=2)
        os.replace(temp_file, self.queue_file)

    def add_job(self, job_type, params=None, priority=5):
        """Add a job to the queue"""
        job = {
            'id': f"{job_type}_{int(time.time()*1000)}",
            'type': job_type,
            'params': params or {},
            'priority': priority,  # 1=highest, 10=lowest
            'status': JobStatus.PENDING,
            'created': datetime.now().isoformat(),
            'attempts': 0,
            'error': None
        }

        # Check for duplicates
        for existing in self.jobs:
            if existing['type'] == job_type and existing['params'] == params:
                if existing['status'] in [JobStatus.PENDING, JobStatus.RUNNING]:
                    return existing['id']  # Already queued

        self.jobs.append(job)
        self.jobs.sort(key=lambda x: x['priority'])
        self.save()
        return job['id']

    def get_next_job(self):
        """Get next pending job"""
        for job in self.jobs:
            if job['status'] == JobStatus.PENDING:
                return job
        return None

    def update_job(self, job_id, status, error=None):
        """Update job status"""
        for job in self.jobs:
            if job['id'] == job_id:
                job['status'] = status
                job['updated'] = datetime.now().isoformat()
                if error:
                    job['error'] = str(error)
                if status == JobStatus.COMPLETED:
                    self.completed.append(job)
                    self.jobs.remove(job)
                self.save()
                return

    def get_status(self):
        """Get queue status summary"""
        pending = sum(1 for j in self.jobs if j['status'] == JobStatus.PENDING)
        running = sum(1 for j in self.jobs if j['status'] == JobStatus.RUNNING)
        failed = sum(1 for j in self.jobs if j['status'] == JobStatus.FAILED)
        completed = len(self.completed)
        return {
            'pending': pending,
            'running': running,
            'failed': failed,
            'completed': completed,
            'total': len(self.jobs)
        }


class JobWorker:
    """Background worker that processes jobs"""

    def __init__(self, queue):
        self.queue = queue
        self.running = False
        self.current_job = None

    def execute_job(self, job):
        """Execute a single job"""
        job_type = job['type']
        params = job['params']

        try:
            if job_type == JobType.QUALITY_ANALYSIS or job_type == 'quality_analysis':
                result = subprocess.run(
                    ['python3', '/Users/davidquinton/ReverseLab/SAM/media/audio_quality_analyzer_v2.py'],
                    capture_output=True, text=True, timeout=86400  # 24 hour timeout
                )
                return result.returncode == 0

            elif job_type == JobType.VERIFY_AUDIO or job_type == 'verify_audio':
                result = subprocess.run(
                    ['python3', '/Users/davidquinton/ReverseLab/SAM/media/verify_audio_v2.py'],
                    capture_output=True, text=True, timeout=43200  # 12 hour timeout
                )
                return result.returncode == 0

            elif job_type == JobType.BEETS_IMPORT:
                path = params.get('path', '/Volumes/Music/_Music Lossless')
                result = subprocess.run(
                    ['beet', 'import', '-q', path],
                    capture_output=True, text=True, timeout=3600
                )
                return result.returncode == 0

            elif job_type == JobType.FIX_FEATURED_ARTISTS:
                result = subprocess.run(
                    ['python3', '/tmp/fix_featured_artists.py'],
                    capture_output=True, text=True, timeout=1800
                )
                return result.returncode == 0

            elif job_type == JobType.WRITE_METADATA:
                result = subprocess.run(
                    ['beet', 'write'],
                    capture_output=True, text=True, timeout=1800
                )
                return result.returncode == 0

            elif job_type == JobType.MOVE_FILES:
                result = subprocess.run(
                    ['beet', 'move'],
                    capture_output=True, text=True, timeout=3600
                )
                return result.returncode == 0

            elif job_type == JobType.CATALOG_RESEARCH:
                result = subprocess.run(
                    ['python3', '/Users/davidquinton/ReverseLab/SAM/media/catalog_researcher.py'],
                    capture_output=True, text=True, timeout=7200
                )
                return result.returncode == 0

            elif job_type == JobType.FETCH_LYRICS:
                result = subprocess.run(
                    ['python3', '/Users/davidquinton/ReverseLab/SAM/media/lyrics/bulk_fetch_lyrics.py', '--workers', '2'],
                    capture_output=True, text=True, timeout=7200
                )
                return result.returncode == 0

            elif job_type == JobType.FETCH_CD_SCANS:
                env = os.environ.copy()
                env['DISCOGS_TOKEN'] = 'ZVyTkhRtDtwJBXkoBDDJmmHcnpLdvuYlYzZCOLte'
                result = subprocess.run(
                    ['python3', '/Users/davidquinton/ReverseLab/SAM/media/discogs/fetch_cd_scans.py'],
                    capture_output=True, text=True, timeout=7200, env=env
                )
                return result.returncode == 0

            elif job_type == JobType.FETCH_ANIMATED_COVERS:
                result = subprocess.run(
                    ['python3', '/Users/davidquinton/ReverseLab/SAM/media/apple_music/bulk_fetch.py'],
                    capture_output=True, text=True, timeout=7200
                )
                return result.returncode == 0

            elif job_type == JobType.REFRESH_NAVIDROME:
                result = subprocess.run(
                    ['docker', 'restart', 'navidrome'],
                    capture_output=True, text=True, timeout=60
                )
                return result.returncode == 0

            else:
                print(f"Unknown job type: {job_type}")
                return False

        except subprocess.TimeoutExpired:
            raise Exception("Job timed out")
        except Exception as e:
            raise e

    def run(self):
        """Main worker loop"""
        self.running = True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Job worker started")

        while self.running:
            job = self.queue.get_next_job()

            if job:
                self.current_job = job
                job_id = job['id']
                job_type = job['type']

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting: {job_type}")
                self.queue.update_job(job_id, JobStatus.RUNNING)

                try:
                    success = self.execute_job(job)
                    if success:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Completed: {job_type}")
                        self.queue.update_job(job_id, JobStatus.COMPLETED)
                    else:
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] Failed: {job_type}")
                        self.queue.update_job(job_id, JobStatus.FAILED, "Non-zero exit code")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error: {job_type} - {e}")
                    self.queue.update_job(job_id, JobStatus.FAILED, str(e))

                self.current_job = None
            else:
                # No pending jobs, wait and check again
                time.sleep(30)

    def stop(self):
        """Stop the worker"""
        self.running = False


def setup_initial_queue():
    """Set up the initial job queue for post-transfer processing"""
    queue = JobQueue()

    # Clear any old jobs
    queue.jobs = []
    queue.save()

    # Add jobs in order of priority (lower = higher priority)
    jobs_to_add = [
        (JobType.BEETS_IMPORT, {}, 1),
        (JobType.FIX_FEATURED_ARTISTS, {}, 2),
        (JobType.WRITE_METADATA, {}, 3),
        (JobType.MOVE_FILES, {}, 4),
        (JobType.CATALOG_RESEARCH, {}, 5),
        (JobType.FETCH_LYRICS, {}, 6),
        (JobType.FETCH_CD_SCANS, {}, 7),
        (JobType.FETCH_ANIMATED_COVERS, {}, 8),
        (JobType.REFRESH_NAVIDROME, {}, 9),
    ]

    for job_type, params, priority in jobs_to_add:
        queue.add_job(job_type, params, priority)

    print(f"Queued {len(jobs_to_add)} jobs")
    print(f"Queue saved to: {queue.queue_file}")
    return queue


def print_status(queue):
    """Print current queue status"""
    status = queue.get_status()
    print("\n" + "=" * 50)
    print("SAM JOB QUEUE STATUS")
    print("=" * 50)
    print(f"Pending:   {status['pending']}")
    print(f"Running:   {status['running']}")
    print(f"Completed: {status['completed']}")
    print(f"Failed:    {status['failed']}")
    print("-" * 50)

    print("\nQueued Jobs:")
    for job in queue.jobs:
        status_icon = {
            JobStatus.PENDING: "⏳",
            JobStatus.RUNNING: "🔄",
            JobStatus.COMPLETED: "✅",
            JobStatus.FAILED: "❌"
        }.get(job['status'], "?")
        print(f"  {status_icon} [{job['priority']}] {job['type']}")

    print("\nRecent Completed:")
    for job in queue.completed[-5:]:
        print(f"  ✅ {job['type']}")


def main():
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python job_queue.py setup    - Initialize queue with all jobs")
        print("  python job_queue.py status   - Show queue status")
        print("  python job_queue.py run      - Start processing jobs")
        print("  python job_queue.py add TYPE - Add a specific job")
        return

    command = sys.argv[1]

    if command == "setup":
        queue = setup_initial_queue()
        print_status(queue)

    elif command == "status":
        queue = JobQueue()
        print_status(queue)

    elif command == "run":
        queue = JobQueue()
        worker = JobWorker(queue)
        try:
            worker.run()
        except KeyboardInterrupt:
            print("\nStopping worker...")
            worker.stop()

    elif command == "add" and len(sys.argv) > 2:
        queue = JobQueue()
        job_type = sys.argv[2]
        queue.add_job(job_type, {}, 5)
        print(f"Added job: {job_type}")
        print_status(queue)

    else:
        print(f"Unknown command: {command}")


if __name__ == '__main__':
    main()
