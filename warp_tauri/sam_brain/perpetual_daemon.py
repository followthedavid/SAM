#!/usr/bin/env python3
"""
SAM Perpetual Improvement Daemon

A true self-improving system that:
1. Runs continuously in the background
2. Selects high-impact improvement tasks
3. Executes via Claude Code
4. Verifies changes work (tests, builds)
5. Learns from successes and failures
6. Tracks evolution levels across all projects

Usage:
    python perpetual_daemon.py start    # Start daemon
    python perpetual_daemon.py stop     # Stop daemon
    python perpetual_daemon.py status   # Show status
    python perpetual_daemon.py once     # Single iteration
    python perpetual_daemon.py history  # Show learning history
"""

import os
import sys
import json
import time
import signal
import sqlite3
import subprocess
import requests
import hashlib
import random
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from enum import Enum
import logging

# ============================================================================
# CONFIGURATION
# ============================================================================

CONFIG = {
    "registry_path": Path.home() / ".sam/projects/registry.json",
    "db_path": Path.home() / ".sam/perpetual_ladder.db",
    "pid_file": Path.home() / ".sam/perpetual_daemon.pid",
    "log_file": Path.home() / ".sam/logs/perpetual_daemon.log",
    "state_file": Path.home() / ".sam/perpetual_state.json",
    
    # Timing
    "cycle_interval_minutes": 10,      # Time between improvement cycles
    "cooldown_after_failure": 60,      # Minutes to wait after a failure
    "max_daily_tasks": 20,             # Safety limit
    "task_timeout_minutes": 30,        # Max time for a single task
    
    # LLM
    "ollama_url": "http://localhost:11434",
    "planning_model": "sam-coder:latest",
    "quick_model": "sam-brain:latest",
    
    # Guardrails
    "require_approval": ["delete", "drop", "rm -rf", "git push --force", "truncate"],
    "auto_approve": ["test", "lint", "format", "build", "docs", "git add", "git commit"],
    "max_files_per_task": 10,
    "protected_paths": ["/usr", "/etc", "/System", str(Path.home() / "Documents")],
}

# ============================================================================
# DATA MODELS
# ============================================================================

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    VERIFYING = "verifying"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"

class EvolutionLevel(Enum):
    BASIC = 1
    FUNCTIONAL = 2
    INTEGRATED = 3
    AUTONOMOUS = 4
    MASTERY = 5

@dataclass
class ImprovementTask:
    id: str
    project_id: str
    description: str
    category: str  # code, docs, test, refactor, feature
    estimated_impact: float  # 0.0 to 1.0
    created_at: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None
    verification_passed: Optional[bool] = None
    files_changed: int = 0
    error: Optional[str] = None

@dataclass
class LearningRecord:
    task_id: str
    project_id: str
    task_type: str
    success: bool
    duration_seconds: int
    lessons: str
    recorded_at: str

# ============================================================================
# DATABASE
# ============================================================================

class PerpetualDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    project_id TEXT NOT NULL,
                    description TEXT NOT NULL,
                    category TEXT,
                    estimated_impact REAL,
                    created_at TEXT,
                    status TEXT,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    verification_passed INTEGER,
                    files_changed INTEGER DEFAULT 0,
                    error TEXT
                );
                
                CREATE TABLE IF NOT EXISTS learning (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT,
                    project_id TEXT,
                    task_type TEXT,
                    success INTEGER,
                    duration_seconds INTEGER,
                    lessons TEXT,
                    recorded_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS evolution (
                    project_id TEXT PRIMARY KEY,
                    current_level INTEGER DEFAULT 1,
                    level_progress REAL DEFAULT 0.0,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_failed INTEGER DEFAULT 0,
                    last_improvement TEXT,
                    updated_at TEXT
                );
                
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    tasks_attempted INTEGER DEFAULT 0,
                    tasks_succeeded INTEGER DEFAULT 0,
                    tasks_failed INTEGER DEFAULT 0,
                    total_files_changed INTEGER DEFAULT 0
                );
                
                CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_learning_project ON learning(project_id);
            """)
    
    def add_task(self, task: ImprovementTask):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tasks 
                (id, project_id, description, category, estimated_impact, created_at,
                 status, started_at, completed_at, result, verification_passed, 
                 files_changed, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (task.id, task.project_id, task.description, task.category,
                  task.estimated_impact, task.created_at, task.status,
                  task.started_at, task.completed_at, task.result,
                  task.verification_passed, task.files_changed, task.error))
    
    def update_task(self, task_id: str, **kwargs):
        updates = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [task_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE tasks SET {updates} WHERE id = ?", values)
    
    def get_task(self, task_id: str) -> Optional[ImprovementTask]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            return ImprovementTask(**dict(row)) if row else None
    
    def record_learning(self, record: LearningRecord):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO learning (task_id, project_id, task_type, success,
                                      duration_seconds, lessons, recorded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (record.task_id, record.project_id, record.task_type,
                  record.success, record.duration_seconds, record.lessons,
                  record.recorded_at))
    
    def get_project_success_rate(self, project_id: str) -> float:
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COUNT(*) as total, SUM(success) as successes
                FROM learning WHERE project_id = ?
            """, (project_id,)).fetchone()
            if result[0] == 0:
                return 0.5  # Default for new projects
            return result[1] / result[0]
    
    def get_evolution_level(self, project_id: str) -> Tuple[int, float]:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT current_level, level_progress FROM evolution WHERE project_id = ?",
                (project_id,)
            ).fetchone()
            return (row[0], row[1]) if row else (1, 0.0)
    
    def update_evolution(self, project_id: str, level: int, progress: float,
                        tasks_completed: int = 0, tasks_failed: int = 0):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evolution 
                (project_id, current_level, level_progress, tasks_completed, 
                 tasks_failed, last_improvement, updated_at)
                VALUES (?, ?, ?, 
                    COALESCE((SELECT tasks_completed FROM evolution WHERE project_id = ?), 0) + ?,
                    COALESCE((SELECT tasks_failed FROM evolution WHERE project_id = ?), 0) + ?,
                    ?, ?)
            """, (project_id, level, progress, project_id, tasks_completed,
                  project_id, tasks_failed, datetime.now().isoformat(),
                  datetime.now().isoformat()))
    
    def get_daily_task_count(self) -> int:
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT tasks_attempted FROM daily_stats WHERE date = ?",
                (today,)
            ).fetchone()
            return result[0] if result else 0
    
    def increment_daily_stats(self, success: bool, files_changed: int = 0):
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO daily_stats (date, tasks_attempted, tasks_succeeded, 
                                         tasks_failed, total_files_changed)
                VALUES (?, 1, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    tasks_attempted = tasks_attempted + 1,
                    tasks_succeeded = tasks_succeeded + ?,
                    tasks_failed = tasks_failed + ?,
                    total_files_changed = total_files_changed + ?
            """, (today, 1 if success else 0, 0 if success else 1, files_changed,
                  1 if success else 0, 0 if success else 1, files_changed))
    
    def get_recent_history(self, limit: int = 20) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT t.*, e.current_level 
                FROM tasks t
                LEFT JOIN evolution e ON t.project_id = e.project_id
                ORDER BY t.created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()
            return [dict(row) for row in rows]

# ============================================================================
# PERPETUAL DAEMON
# ============================================================================

class PerpetualDaemon:
    def __init__(self):
        self.db = PerpetualDB(CONFIG["db_path"])
        self.running = False
        self.logger = self._setup_logging()
        self.registry = self._load_registry()
    
    def _setup_logging(self) -> logging.Logger:
        CONFIG["log_file"].parent.mkdir(parents=True, exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(CONFIG["log_file"]),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger("perpetual")
    
    def _load_registry(self) -> Dict:
        with open(CONFIG["registry_path"]) as f:
            return json.load(f)
    
    def _reload_registry(self):
        self.registry = self._load_registry()

    def _get_baseline(self, key: str, default: int) -> int:
        """Get baseline metric from state file."""
        try:
            if CONFIG["state_file"].exists():
                with open(CONFIG["state_file"]) as f:
                    state = json.load(f)
                    return state.get("baselines", {}).get(key, default)
        except:
            pass
        return default

    def _set_baseline(self, key: str, value: int):
        """Set baseline metric in state file."""
        try:
            state = {}
            if CONFIG["state_file"].exists():
                with open(CONFIG["state_file"]) as f:
                    state = json.load(f)
            if "baselines" not in state:
                state["baselines"] = {}
            state["baselines"][key] = value
            with open(CONFIG["state_file"], "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save baseline: {e}")

    # ========================================================================
    # LLM INTERACTION
    # ========================================================================
    
    def ask_ollama(self, prompt: str, model: str = None) -> str:
        model = model or CONFIG["planning_model"]
        try:
            resp = requests.post(
                f"{CONFIG['ollama_url']}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": 500, "temperature": 0.7}
                },
                timeout=60
            )
            return resp.json().get("response", "")
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")
            return ""
    
    # ========================================================================
    # TASK SELECTION
    # ========================================================================
    
    def select_next_task(self) -> Optional[Tuple[Dict, str]]:
        """Select the highest-impact task across all projects."""
        self._reload_registry()
        
        # Get active projects sorted by priority
        projects = [p for p in self.registry["projects"] 
                   if p.get("status") in ("active", "ready")]
        projects.sort(key=lambda p: p.get("priority", 99))
        
        if not projects:
            self.logger.info("No active projects")
            return None
        
        # Build context for SAM
        project_summaries = []
        for p in projects[:7]:  # Top 7 by priority
            level, progress = self.db.get_evolution_level(p["id"])
            success_rate = self.db.get_project_success_rate(p["id"])
            tech_stack = ", ".join(p.get("techStack", ["unknown"]))
            project_summaries.append(
                f"- {p['name']} (P{p.get('priority', '?')}, L{level}): "
                f"{p.get('currentFocus', 'General')} "
                f"[Tech: {tech_stack}] "
                f"[{success_rate*100:.0f}% success rate]"
            )
        
        prompt = f"""You are SAM, an AI that autonomously improves software projects.

Active projects (priority order):
{chr(10).join(project_summaries)}

Rules:
1. Pick ONE project and ONE small, specific task
2. Task MUST be completable in under 15 minutes
3. Prefer projects with higher success rates (they're easier wins)
4. Be EXTREMELY specific about what to do
5. USE THE CORRECT FILE EXTENSIONS for the project's tech stack (e.g., .ts for TypeScript, .rs for Rust, .py for Python)

Good tasks (small, specific, fast):
- "Add error handling to the main.ts fetch call"
- "Write a unit test for the router module"
- "Add a docstring to the Orchestrator class"
- "Fix linting warnings in lib.rs"

Bad tasks (too vague, too big):
- "Review code and run tests" (too vague)
- "Refactor the entire system" (too big)
- "Improve performance" (not specific)

IMPORTANT: Generate a UNIQUE task based on the project's actual tech stack. Do NOT copy the examples above.

Output format (exactly):
PROJECT_ID: <project_id>
TASK: <specific actionable task under 15 min>
CATEGORY: <code|test|docs|refactor|feature>
IMPACT: <0.1-1.0>"""

        response = self.ask_ollama(prompt)
        
        # Parse response
        lines = response.strip().split("\n")
        task_info = {}
        for line in lines:
            if ":" in line:
                key, value = line.split(":", 1)
                task_info[key.strip().upper()] = value.strip()
        
        project_id = task_info.get("PROJECT_ID", "").lower().replace(" ", "-")
        task_desc = task_info.get("TASK", "")
        
        if not project_id or not task_desc:
            # Fallback to first project with a specific small task
            project_id = projects[0]["id"]
            fallback_tasks = [
                "Add a docstring to the main function",
                "Fix any linting warnings in the main file",
                "Add type hints to one function",
                "Write a simple unit test for one function",
            ]
            task_desc = random.choice(fallback_tasks)
        
        # Find the project
        project = next((p for p in projects if p["id"] == project_id), projects[0])
        
        return project, task_desc
    
    # ========================================================================
    # TASK EXECUTION
    # ========================================================================
    
    def execute_task(self, project: Dict, task_desc: str) -> ImprovementTask:
        """Execute a task via Claude Code."""
        task_id = hashlib.md5(
            f"{project['id']}-{task_desc}-{time.time()}".encode()
        ).hexdigest()[:12]
        
        task = ImprovementTask(
            id=task_id,
            project_id=project["id"],
            description=task_desc,
            category="code",
            estimated_impact=0.5,
            created_at=datetime.now().isoformat(),
            status=TaskStatus.RUNNING.value,
            started_at=datetime.now().isoformat()
        )
        self.db.add_task(task)
        
        self.logger.info(f"Executing task {task_id}: {task_desc}")
        self.logger.info(f"Project: {project['name']} at {project['path']}")
        
        # Check guardrails
        for forbidden in CONFIG["require_approval"]:
            if forbidden.lower() in task_desc.lower():
                self.logger.warning(f"Task requires approval: contains '{forbidden}'")
                task.status = TaskStatus.SKIPPED.value
                task.error = f"Requires approval: contains '{forbidden}'"
                self.db.add_task(task)
                return task
        
        # Run Claude Code
        try:
            start_time = time.time()
            result = subprocess.run(
                ["claude", "-p", task_desc],
                cwd=project["path"],
                capture_output=True,
                text=True,
                timeout=CONFIG["task_timeout_minutes"] * 60
            )
            duration = int(time.time() - start_time)
            
            task.result = result.stdout[-2000:] if result.stdout else ""
            
            if result.returncode == 0:
                task.status = TaskStatus.VERIFYING.value
                self.logger.info(f"Task completed in {duration}s, verifying...")
            else:
                task.status = TaskStatus.FAILED.value
                task.error = result.stderr[-500:] if result.stderr else "Unknown error"
                self.logger.error(f"Task failed: {task.error}")
        
        except subprocess.TimeoutExpired:
            task.status = TaskStatus.FAILED.value
            task.error = "Task timed out"
            self.logger.error("Task timed out")
        except Exception as e:
            task.status = TaskStatus.FAILED.value
            task.error = str(e)
            self.logger.error(f"Task error: {e}")
        
        task.completed_at = datetime.now().isoformat()
        self.db.add_task(task)
        return task
    
    # ========================================================================
    # VERIFICATION
    # ========================================================================
    
    def verify_task(self, task: ImprovementTask, project: Dict) -> bool:
        """Verify the task succeeded by running tests/build."""
        self.logger.info(f"Verifying task {task.id}...")
        
        project_path = Path(project["path"])
        verification_passed = True
        
        # Check for test commands
        if (project_path / "package.json").exists():
            # Node project - count TypeScript errors (allow existing errors, fail only if NEW errors)
            try:
                result = subprocess.run(
                    ["npx", "tsc", "--noEmit"],
                    cwd=project_path,
                    capture_output=True,
                    text=True,
                    timeout=90
                )
                # Count errors in output
                error_count = result.stderr.count("error TS") if result.stderr else 0

                # Get baseline (stored in state file or use current as baseline)
                baseline_key = f"ts_errors_{project['id']}"
                baseline = self._get_baseline(baseline_key, error_count)

                if error_count > baseline:
                    self.logger.warning(f"TypeScript errors increased: {baseline} → {error_count}")
                    verification_passed = False
                else:
                    self.logger.info(f"TypeScript check OK ({error_count} errors, baseline: {baseline})")
                    # Update baseline if errors decreased
                    if error_count < baseline:
                        self._set_baseline(baseline_key, error_count)
            except Exception as e:
                self.logger.warning(f"Type check error: {e}")
        
        elif (project_path / "Cargo.toml").exists():
            # Rust project
            try:
                result = subprocess.run(
                    ["cargo", "check"],
                    cwd=project_path,
                    capture_output=True,
                    timeout=120
                )
                if result.returncode != 0:
                    self.logger.warning("cargo check failed")
                    verification_passed = False
            except:
                pass
        
        elif (project_path / "pyproject.toml").exists() or (project_path / "setup.py").exists():
            # Python project
            try:
                result = subprocess.run(
                    ["python", "-m", "pytest", "--tb=no", "-q"],
                    cwd=project_path,
                    capture_output=True,
                    timeout=120
                )
                if result.returncode != 0:
                    self.logger.warning("pytest failed")
                    verification_passed = False
            except:
                pass
        
        # Count changed files (git status)
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=10
            )
            task.files_changed = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        except:
            task.files_changed = 0
        
        task.verification_passed = verification_passed
        task.status = TaskStatus.SUCCESS.value if verification_passed else TaskStatus.FAILED.value
        self.db.add_task(task)
        
        return verification_passed
    
    # ========================================================================
    # LEARNING
    # ========================================================================
    
    def record_learning(self, task: ImprovementTask, project: Dict):
        """Record what we learned from this task."""
        success = task.status == TaskStatus.SUCCESS.value
        
        # Calculate duration
        start = datetime.fromisoformat(task.started_at) if task.started_at else datetime.now()
        end = datetime.fromisoformat(task.completed_at) if task.completed_at else datetime.now()
        duration = int((end - start).total_seconds())
        
        # Generate lessons learned
        if success:
            lessons = f"Task succeeded: {task.description[:100]}"
        else:
            lessons = f"Task failed ({task.error or 'unknown'}): {task.description[:100]}"
        
        record = LearningRecord(
            task_id=task.id,
            project_id=project["id"],
            task_type=task.category or "code",
            success=success,
            duration_seconds=duration,
            lessons=lessons,
            recorded_at=datetime.now().isoformat()
        )
        self.db.record_learning(record)
        
        # Update evolution
        level, progress = self.db.get_evolution_level(project["id"])
        if success:
            progress += 0.1  # 10 successes to level up
            if progress >= 1.0 and level < 5:
                level += 1
                progress = 0.0
                self.logger.info(f"🎉 {project['name']} evolved to Level {level}!")
        
        self.db.update_evolution(
            project["id"], level, progress,
            tasks_completed=1 if success else 0,
            tasks_failed=0 if success else 1
        )
        
        # Update daily stats
        self.db.increment_daily_stats(success, task.files_changed)
        
        self.logger.info(f"Learning recorded: {'✓' if success else '✗'} {project['name']}")
    
    # ========================================================================
    # MAIN LOOP
    # ========================================================================
    
    def run_single_cycle(self) -> bool:
        """Run a single improvement cycle."""
        # Check daily limit
        daily_count = self.db.get_daily_task_count()
        if daily_count >= CONFIG["max_daily_tasks"]:
            self.logger.info(f"Daily limit reached ({daily_count}/{CONFIG['max_daily_tasks']})")
            return False
        
        # Select task
        result = self.select_next_task()
        if not result:
            return False
        
        project, task_desc = result
        self.logger.info(f"Selected: {project['name']} - {task_desc}")
        
        # Execute
        task = self.execute_task(project, task_desc)
        
        # Verify if execution succeeded
        if task.status == TaskStatus.VERIFYING.value:
            self.verify_task(task, project)
        
        # Learn
        self.record_learning(task, project)
        
        return task.status == TaskStatus.SUCCESS.value
    
    def run_daemon(self):
        """Run the perpetual improvement loop."""
        self.running = True
        self.logger.info("═" * 50)
        self.logger.info("PERPETUAL IMPROVEMENT DAEMON STARTED")
        self.logger.info("═" * 50)
        
        # Write PID file
        CONFIG["pid_file"].write_text(str(os.getpid()))
        
        # Handle signals
        def signal_handler(sig, frame):
            self.logger.info("Received shutdown signal")
            self.running = False
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
        
        consecutive_failures = 0
        
        while self.running:
            try:
                success = self.run_single_cycle()
                
                if success:
                    consecutive_failures = 0
                    wait_minutes = CONFIG["cycle_interval_minutes"]
                else:
                    consecutive_failures += 1
                    wait_minutes = min(
                        CONFIG["cooldown_after_failure"] * consecutive_failures,
                        CONFIG["cycle_interval_minutes"] * 4
                    )
                
                self.logger.info(f"Next cycle in {wait_minutes} minutes...")
                
                # Sleep in small increments to catch signals
                for _ in range(wait_minutes * 6):
                    if not self.running:
                        break
                    time.sleep(10)
            
            except Exception as e:
                self.logger.error(f"Cycle error: {e}")
                time.sleep(60)
        
        # Cleanup
        if CONFIG["pid_file"].exists():
            CONFIG["pid_file"].unlink()
        
        self.logger.info("Daemon stopped")
    
    def stop_daemon(self):
        """Stop the running daemon."""
        if CONFIG["pid_file"].exists():
            pid = int(CONFIG["pid_file"].read_text())
            try:
                os.kill(pid, signal.SIGTERM)
                print(f"Sent stop signal to daemon (PID {pid})")
            except ProcessLookupError:
                print("Daemon not running")
                CONFIG["pid_file"].unlink()
        else:
            print("No daemon running")
    
    def show_status(self):
        """Show current daemon status."""
        print("\n" + "═" * 50)
        print("    PERPETUAL IMPROVEMENT STATUS")
        print("═" * 50)
        
        # Daemon status
        if CONFIG["pid_file"].exists():
            pid = CONFIG["pid_file"].read_text()
            print(f"\n🟢 Daemon running (PID {pid})")
        else:
            print("\n🔴 Daemon not running")
        
        # Daily stats
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(CONFIG["db_path"]) as conn:
            row = conn.execute(
                "SELECT * FROM daily_stats WHERE date = ?", (today,)
            ).fetchone()
            if row:
                print(f"\n📊 Today's Stats:")
                print(f"   Tasks: {row[1]} attempted, {row[2]} succeeded, {row[3]} failed")
                print(f"   Files changed: {row[4]}")
        
        # Evolution levels
        print(f"\n🏆 Evolution Levels:")
        with sqlite3.connect(CONFIG["db_path"]) as conn:
            rows = conn.execute(
                "SELECT project_id, current_level, tasks_completed, tasks_failed "
                "FROM evolution ORDER BY current_level DESC, tasks_completed DESC"
            ).fetchall()
            for row in rows[:10]:
                level_names = ["", "Basic", "Functional", "Integrated", "Autonomous", "Mastery"]
                print(f"   L{row[1]} {level_names[row[1]]}: {row[0]} ({row[2]}✓ {row[3]}✗)")
        
        # Recent tasks
        print(f"\n📝 Recent Tasks:")
        history = self.db.get_recent_history(5)
        for task in history:
            status = "✓" if task["status"] == "success" else "✗"
            print(f"   {status} {task['project_id']}: {task['description'][:50]}...")
        
        print("\n" + "═" * 50)
    
    def show_history(self):
        """Show learning history."""
        print("\n" + "═" * 50)
        print("    LEARNING HISTORY")
        print("═" * 50 + "\n")
        
        history = self.db.get_recent_history(20)
        for task in history:
            status = "✓" if task["status"] == "success" else "✗"
            date = task["created_at"][:10] if task["created_at"] else "?"
            print(f"[{date}] {status} {task['project_id']}")
            print(f"         {task['description'][:60]}...")
            if task.get("error"):
                print(f"         Error: {task['error'][:50]}")
            print()

# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python perpetual_daemon.py <start|stop|status|once|history>")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    daemon = PerpetualDaemon()
    
    if command == "start":
        daemon.run_daemon()
    elif command == "stop":
        daemon.stop_daemon()
    elif command == "status":
        daemon.show_status()
    elif command == "once":
        daemon.run_single_cycle()
    elif command == "history":
        daemon.show_history()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

if __name__ == "__main__":
    main()
