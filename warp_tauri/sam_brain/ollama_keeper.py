#!/usr/bin/env python3
"""
Ollama Keeper - Keeps models warm and ready for instant responses.

Periodically pings Ollama to keep models loaded in memory.
Also handles auto-restart if Ollama dies.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from pathlib import Path

# Configuration
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELS_TO_KEEP_WARM = [
    "qwen2.5-coder:1.5b",  # Primary coding model
    "tinydolphin:1.1b",    # Fast routing model
]
PING_INTERVAL = 300  # 5 minutes
KEEP_ALIVE = "30m"   # Keep model loaded for 30 minutes after each ping

LOG_FILE = Path(__file__).parent / "ollama_keeper.log"


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def is_ollama_running() -> bool:
    """Check if Ollama is responding."""
    try:
        result = subprocess.run(
            ["curl", "-s", "-m", "5", f"{OLLAMA_URL}/api/tags"],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except:
        return False


def start_ollama():
    """Start Ollama if not running."""
    log("Starting Ollama...")
    subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True
    )
    time.sleep(5)


def warm_model(model: str) -> bool:
    """Send a minimal request to keep model loaded."""
    try:
        import urllib.request
        import urllib.error

        data = json.dumps({
            "model": model,
            "prompt": "ready",
            "stream": False,
            "keep_alive": KEEP_ALIVE,
            "options": {"num_predict": 1}
        }).encode()

        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status == 200
    except Exception as e:
        log(f"Failed to warm {model}: {e}")
        return False


def get_loaded_models() -> list:
    """Get list of currently loaded models."""
    try:
        import urllib.request
        with urllib.request.urlopen(f"{OLLAMA_URL}/api/ps", timeout=5) as resp:
            data = json.loads(resp.read())
            return [m["name"] for m in data.get("models", [])]
    except:
        return []


def keeper_loop():
    """Main keeper loop."""
    log("Ollama Keeper started")
    log(f"Keeping warm: {', '.join(MODELS_TO_KEEP_WARM)}")
    log(f"Ping interval: {PING_INTERVAL}s")

    while True:
        try:
            # Check if Ollama is running
            if not is_ollama_running():
                log("Ollama not responding, attempting restart...")
                start_ollama()
                time.sleep(10)

                if not is_ollama_running():
                    log("Failed to start Ollama, waiting...")
                    time.sleep(60)
                    continue

            # Get currently loaded models
            loaded = get_loaded_models()

            # Warm each model
            for model in MODELS_TO_KEEP_WARM:
                if model in loaded:
                    # Just ping to extend keep_alive
                    warm_model(model)
                else:
                    log(f"Loading {model}...")
                    if warm_model(model):
                        log(f"✓ {model} loaded")
                    else:
                        log(f"✗ {model} failed to load")

            time.sleep(PING_INTERVAL)

        except KeyboardInterrupt:
            log("Keeper stopped")
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(60)


def status():
    """Show current status."""
    print("Ollama Keeper Status")
    print("-" * 40)

    if is_ollama_running():
        print("Ollama: ✓ Running")
        loaded = get_loaded_models()
        print(f"Loaded models: {', '.join(loaded) if loaded else 'None'}")

        print("\nTarget models:")
        for model in MODELS_TO_KEEP_WARM:
            status = "✓ Loaded" if model in loaded else "○ Not loaded"
            print(f"  {model}: {status}")
    else:
        print("Ollama: ✗ Not running")


def warm_now():
    """Warm all models immediately."""
    if not is_ollama_running():
        print("Ollama not running, starting...")
        start_ollama()

    print("Warming models...")
    for model in MODELS_TO_KEEP_WARM:
        print(f"  {model}...", end=" ", flush=True)
        if warm_model(model):
            print("✓")
        else:
            print("✗")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "status":
            status()
        elif cmd == "warm":
            warm_now()
        elif cmd == "start":
            keeper_loop()
        else:
            print(f"Usage: {sys.argv[0]} [status|warm|start]")
    else:
        # Default: show status
        status()
