#!/usr/bin/env python3
"""
SAM Watch - Monitor files and auto-suggest improvements

Features:
- Watches for file changes
- Detects errors on save
- Suggests fixes via SAM
- Optional auto-fix mode
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class SAMWatcher(FileSystemEventHandler):
    def __init__(self, project_path: str, auto_fix: bool = False):
        self.project_path = project_path
        self.auto_fix = auto_fix
        self.last_event = {}
        self.debounce_seconds = 2

    def should_process(self, path: str) -> bool:
        """Check if file should be processed."""
        # Skip non-code files
        if not any(path.endswith(ext) for ext in ['.py', '.js', '.ts', '.rs', '.json']):
            return False
        # Skip hidden/generated
        if '/.git/' in path or '/node_modules/' in path or '/__pycache__/' in path:
            return False
        # Debounce
        now = time.time()
        if path in self.last_event and (now - self.last_event[path]) < self.debounce_seconds:
            return False
        self.last_event[path] = now
        return True

    def on_modified(self, event):
        if event.is_directory:
            return

        path = event.src_path
        if not self.should_process(path):
            return

        print(f"\n[SAM Watch] File changed: {Path(path).name}")
        self.analyze_file(path)

    def analyze_file(self, filepath: str):
        """Analyze file for issues."""
        path = Path(filepath)

        # Python files: run syntax check
        if path.suffix == '.py':
            result = subprocess.run(
                ['python3', '-m', 'py_compile', filepath],
                capture_output=True, text=True
            )
            if result.returncode != 0:
                error = result.stderr
                print(f"[SAM Watch] ❌ Syntax error detected:")
                print(f"  {error[:200]}")

                if self.auto_fix:
                    self.suggest_fix(filepath, error)
                else:
                    print(f"  Run: sam \"fix syntax error in {path.name}\"")
                return

            # Run basic lint
            result = subprocess.run(
                ['python3', '-m', 'pyflakes', filepath],
                capture_output=True, text=True
            )
            if result.stdout:
                print(f"[SAM Watch] ⚠️ Lint warnings:")
                for line in result.stdout.strip().split('\n')[:3]:
                    print(f"  {line}")

        # TypeScript/JavaScript: check syntax
        elif path.suffix in ['.ts', '.js']:
            if path.suffix == '.ts':
                result = subprocess.run(
                    ['npx', 'tsc', '--noEmit', filepath],
                    capture_output=True, text=True, timeout=30
                )
            else:
                result = subprocess.run(
                    ['node', '--check', filepath],
                    capture_output=True, text=True, timeout=10
                )
            if result.returncode != 0:
                print(f"[SAM Watch] ❌ Error in {path.name}:")
                print(f"  {result.stderr[:200]}")

        # JSON: validate
        elif path.suffix == '.json':
            import json
            try:
                json.load(open(filepath))
            except json.JSONDecodeError as e:
                print(f"[SAM Watch] ❌ Invalid JSON: {e}")

        print(f"[SAM Watch] ✓ {path.name} OK")

    def suggest_fix(self, filepath: str, error: str):
        """Use SAM to suggest a fix."""
        print("[SAM Watch] Attempting auto-fix...")
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / 'sam_agent.py'),
             '--auto', f'fix this error in {filepath}: {error[:100]}'],
            capture_output=True, text=True, timeout=120
        )
        print(result.stdout)

def watch(path: str = ".", auto_fix: bool = False):
    """Start watching a directory."""
    path = os.path.expanduser(path)
    print(f"[SAM Watch] Monitoring: {path}")
    print(f"[SAM Watch] Auto-fix: {'enabled' if auto_fix else 'disabled'}")
    print("[SAM Watch] Press Ctrl+C to stop\n")

    handler = SAMWatcher(path, auto_fix)
    observer = Observer()
    observer.schedule(handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n[SAM Watch] Stopped")
    observer.join()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SAM Watch - File monitoring with auto-suggestions")
    parser.add_argument("path", nargs="?", default=".", help="Directory to watch")
    parser.add_argument("--auto-fix", action="store_true", help="Automatically attempt fixes")
    args = parser.parse_args()

    # Check for watchdog
    try:
        from watchdog.observers import Observer
    except ImportError:
        print("Installing watchdog...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'watchdog', '-q'])
        from watchdog.observers import Observer

    watch(args.path, args.auto_fix)

if __name__ == "__main__":
    main()
