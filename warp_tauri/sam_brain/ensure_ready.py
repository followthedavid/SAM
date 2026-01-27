#!/usr/bin/env python3
"""
SAM Readiness Checker & Auto-Starter

Run this once on app startup to ensure everything is ready.
Can also be run as a health-check daemon.

Usage:
    python ensure_ready.py          # One-time check & start
    python ensure_ready.py --daemon # Run continuously as health monitor
    python ensure_ready.py --status # Just show status

Exit codes:
    0 = Everything ready
    1 = Failed to get ready (after retries)
"""

import subprocess
import requests
import time
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Configuration
OLLAMA_URL = "http://localhost:11434"
PRIMARY_MODEL = "sam-trained:latest"
FALLBACK_MODELS = ["sam-roleplay-unrestricted:latest", "dolphin-llama3:8b"]
HEALTH_CHECK_INTERVAL = 60  # seconds
MAX_STARTUP_RETRIES = 3
WARM_TIMEOUT = 120  # seconds

STATUS_FILE = Path.home() / ".sam" / "readiness_status.json"
STATUS_FILE.parent.mkdir(parents=True, exist_ok=True)


def log(msg: str, level: str = "INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def save_status(status: dict):
    """Save status to file for other processes to read."""
    status["updated_at"] = datetime.now().isoformat()
    with open(STATUS_FILE, "w") as f:
        json.dump(status, f, indent=2)


def load_status() -> dict:
    """Load status from file."""
    if STATUS_FILE.exists():
        with open(STATUS_FILE) as f:
            return json.load(f)
    return {}


def is_ollama_running() -> bool:
    """Check if Ollama server is responding."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except:
        return False


def start_ollama() -> bool:
    """Start Ollama if not running."""
    log("Starting Ollama...")
    try:
        # On macOS, ollama serve runs in background
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait for it to be ready
        for i in range(30):
            time.sleep(1)
            if is_ollama_running():
                log("Ollama started successfully")
                return True

        log("Ollama failed to start in time", "ERROR")
        return False
    except Exception as e:
        log(f"Failed to start Ollama: {e}", "ERROR")
        return False


def get_loaded_model() -> str:
    """Get currently loaded model (if any)."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/ps", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            if models:
                return models[0].get("name", "")
    except:
        pass
    return ""


def warm_model(model: str) -> bool:
    """Load and warm a model."""
    log(f"Warming model: {model}")
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": "Hello",
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": 1}
            },
            timeout=WARM_TIMEOUT
        )

        if resp.status_code == 200:
            log(f"Model {model} is warm and ready")
            return True
        else:
            log(f"Model warm failed: {resp.status_code}", "WARN")
            return False
    except requests.Timeout:
        log(f"Model warm timed out (>{WARM_TIMEOUT}s)", "WARN")
        return False
    except Exception as e:
        log(f"Model warm error: {e}", "ERROR")
        return False


def ensure_model_ready() -> tuple[bool, str]:
    """Ensure a model is loaded and ready. Returns (success, model_name)."""
    # Check what's currently loaded
    current = get_loaded_model()
    if current:
        log(f"Model already loaded: {current}")
        return True, current

    # Try primary model
    if warm_model(PRIMARY_MODEL):
        return True, PRIMARY_MODEL

    # Try fallbacks
    for model in FALLBACK_MODELS:
        log(f"Trying fallback model: {model}")
        if warm_model(model):
            return True, model

    return False, ""


def check_model_exists(model: str) -> bool:
    """Check if a model is installed."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            models = [m["name"] for m in data.get("models", [])]
            return model in models or model.split(":")[0] in [m.split(":")[0] for m in models]
    except:
        pass
    return False


def ensure_ready() -> dict:
    """
    Main function: Ensure SAM is ready to use.
    Returns status dict.
    """
    status = {
        "ready": False,
        "ollama_running": False,
        "model_loaded": "",
        "errors": []
    }

    # Step 1: Check MLX availability (Ollama decommissioned 2026-01-18)
    log("Checking MLX availability...")
    try:
        from cognitive.mlx_cognitive import MLXCognitiveEngine
        status["ollama_running"] = True  # Legacy field - now means "inference available"
        log("MLX cognitive engine available")
    except ImportError as e:
        log(f"MLX not available: {e}", "WARN")
        status["ollama_running"] = False
        status["errors"].append(f"MLX not available: {e}")

    # Step 2: Ensure model is ready
    log("Checking model...")
    success, model = ensure_model_ready()
    if success:
        status["model_loaded"] = model
        status["ready"] = True
        log(f"✅ SAM is ready (model: {model})")
    else:
        status["errors"].append("Failed to load any model")
        log("❌ SAM is NOT ready - no model could be loaded", "ERROR")

    save_status(status)
    return status


def run_daemon():
    """Run as health-monitoring daemon."""
    log("Starting SAM readiness daemon...")

    while True:
        status = ensure_ready()

        if not status["ready"]:
            log("System not ready, will retry...", "WARN")

        time.sleep(HEALTH_CHECK_INTERVAL)


def show_status():
    """Show current status."""
    status = load_status()

    if not status:
        print("No status available. Run 'ensure_ready.py' first.")
        return

    print("\n" + "=" * 40)
    print("  SAM READINESS STATUS")
    print("=" * 40)
    print(f"  Ready: {'✅ YES' if status.get('ready') else '❌ NO'}")
    print(f"  Ollama: {'Running' if status.get('ollama_running') else 'Not running'}")
    print(f"  Model: {status.get('model_loaded', 'None')}")

    if status.get("errors"):
        print(f"  Errors: {', '.join(status['errors'])}")

    print(f"  Updated: {status.get('updated_at', 'Unknown')}")
    print("=" * 40 + "\n")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]

        if arg == "--daemon":
            run_daemon()
        elif arg == "--status":
            show_status()
        elif arg == "--help":
            print(__doc__)
        else:
            print(f"Unknown argument: {arg}")
            print("Use --help for usage")
            sys.exit(1)
    else:
        # One-time check
        status = ensure_ready()
        sys.exit(0 if status["ready"] else 1)


if __name__ == "__main__":
    main()
