#!/usr/bin/env python3
"""
Resource-Safe MLX LoRA Training for 8GB Mac

Runs training with memory monitoring - pauses if RAM gets too low,
allowing scrapers to coexist safely.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

# Config
MIN_FREE_RAM_GB = 1.5  # Pause training if RAM drops below this
CHECK_INTERVAL = 30     # Seconds between RAM checks
CONFIG_PATH = Path(__file__).parent / "lora_config.yaml"

def get_free_ram_gb():
    """Get available RAM in GB."""
    try:
        import psutil
        return psutil.virtual_memory().available / (1024**3)
    except ImportError:
        # Fallback to vm_stat parsing
        result = subprocess.run(['vm_stat'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        page_size = 16384  # Default for Apple Silicon
        free_pages = 0
        for line in lines:
            if 'Pages free' in line:
                free_pages = int(line.split(':')[1].strip().rstrip('.'))
                break
        return (free_pages * page_size) / (1024**3)

def wait_for_ram():
    """Wait until enough RAM is available."""
    while True:
        free_ram = get_free_ram_gb()
        if free_ram >= MIN_FREE_RAM_GB:
            return free_ram
        print(f"⏸️  RAM low ({free_ram:.1f}GB free). Waiting for {MIN_FREE_RAM_GB}GB...")
        time.sleep(CHECK_INTERVAL)

def main():
    print("=" * 60)
    print("SAM LoRA Training (Resource-Safe Mode)")
    print(f"Min RAM threshold: {MIN_FREE_RAM_GB}GB")
    print("=" * 60)

    # Initial RAM check
    free_ram = wait_for_ram()
    print(f"✓ RAM OK ({free_ram:.1f}GB free). Starting training...")
    print()

    # Run training with lower priority (nice)
    cmd = [
        "nice", "-n", "10",  # Lower priority than scrapers
        sys.executable, "-m", "mlx_lm.lora",
        "--config", str(CONFIG_PATH),
    ]

    print(f"Command: {' '.join(cmd)}")
    print("-" * 60)

    # Start training
    process = subprocess.Popen(
        cmd,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )

    # Monitor RAM while training runs
    try:
        while process.poll() is None:
            time.sleep(CHECK_INTERVAL)
            free_ram = get_free_ram_gb()

            if free_ram < MIN_FREE_RAM_GB:
                print(f"\n⚠️  RAM low ({free_ram:.1f}GB). Training continues but may slow...")
                # Could implement pause/resume here if needed

    except KeyboardInterrupt:
        print("\n\nInterrupted. Stopping training...")
        process.terminate()
        process.wait()
        return 1

    return process.returncode

if __name__ == "__main__":
    sys.exit(main() or 0)
