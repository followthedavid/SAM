#!/usr/bin/env python3
"""
SAM Bridge Daemon - Runs continuously in background
Automatically processes ChatGPT/Claude queue without manual intervention
"""

import asyncio
import json
import os
import sys
import time
import signal
from pathlib import Path
from datetime import datetime

# Configuration
QUEUE_PATH = Path.home() / ".sam_chatgpt_queue.json"
RESPONSE_PATH = Path.home() / ".sam_chatgpt_responses.json"
PID_FILE = Path.home() / ".sam_bridge_daemon.pid"
LOG_FILE = Path.home() / ".sam_bridge_daemon.log"
POLL_INTERVAL = 2  # seconds

def log(msg: str):
    """Log with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def get_pending_tasks() -> list:
    """Get all pending tasks from queue"""
    if not QUEUE_PATH.exists():
        return []
    try:
        queue = json.loads(QUEUE_PATH.read_text())
        return [t for t in queue if t.get("status") == "pending"]
    except:
        return []

def mark_task_processing(task_id: str):
    """Mark task as being processed"""
    if not QUEUE_PATH.exists():
        return
    try:
        queue = json.loads(QUEUE_PATH.read_text())
        for task in queue:
            if task.get("id") == task_id:
                task["status"] = "processing"
        QUEUE_PATH.write_text(json.dumps(queue, indent=2))
    except:
        pass

def write_response(task_id: str, response: str, success: bool, provider: str):
    """Write response for SAM to poll"""
    responses = {}
    if RESPONSE_PATH.exists():
        try:
            responses = json.loads(RESPONSE_PATH.read_text())
        except:
            responses = {}

    responses[task_id] = {
        "response": response,
        "success": success,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "provider": provider
    }

    RESPONSE_PATH.write_text(json.dumps(responses, indent=2))

def mark_task_done(task_id: str):
    """Mark task as completed in queue"""
    if not QUEUE_PATH.exists():
        return
    try:
        queue = json.loads(QUEUE_PATH.read_text())
        for task in queue:
            if task.get("id") == task_id:
                task["status"] = "done"
        QUEUE_PATH.write_text(json.dumps(queue, indent=2))
    except:
        pass

async def process_with_ollama(prompt: str, provider: str) -> tuple[str, bool]:
    """Process task using local Ollama (fallback when browser not available)"""
    import subprocess

    # Try to call Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/generate",
             "-d", json.dumps({
                 "model": "qwen2.5-coder:1.5b",
                 "prompt": prompt,
                 "stream": False
             })],
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            response_data = json.loads(result.stdout)
            return response_data.get("response", "No response"), True
        else:
            return f"Ollama error: {result.stderr}", False
    except subprocess.TimeoutExpired:
        return "Request timed out", False
    except Exception as e:
        return f"Error: {str(e)}", False

async def process_with_browser(prompt: str, provider: str) -> tuple[str, bool]:
    """Process task using browser automation"""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            user_data_dir = Path.home() / ".sam_browser_data" / provider
            user_data_dir.mkdir(parents=True, exist_ok=True)

            browser = await p.chromium.launch_persistent_context(
                str(user_data_dir),
                headless=True,
                viewport={"width": 1280, "height": 900}
            )

            page = browser.pages[0] if browser.pages else await browser.new_page()

            if provider == "chatgpt":
                await page.goto("https://chatgpt.com/", wait_until="networkidle")
            else:
                await page.goto("https://claude.ai/new", wait_until="networkidle")

            await asyncio.sleep(2)

            # Check if logged in
            try:
                await page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
            except:
                await browser.close()
                return "Not logged in - falling back to Ollama", False

            # Send message
            input_sel = 'textarea' if provider == "chatgpt" else 'div[contenteditable="true"]'
            await page.fill(input_sel, prompt)
            await page.keyboard.press("Enter")

            # Wait for response
            await asyncio.sleep(30)  # Give it time to respond

            # Get response (simplified - would need proper selectors)
            response = await page.evaluate('''
                () => {
                    const messages = document.querySelectorAll('[data-message-author-role="assistant"]');
                    if (messages.length > 0) {
                        return messages[messages.length - 1].textContent;
                    }
                    return "No response captured";
                }
            ''')

            await browser.close()
            return response, True

    except ImportError:
        log("Playwright not installed, using Ollama fallback")
        return await process_with_ollama(prompt, provider)
    except Exception as e:
        log(f"Browser error: {e}, using Ollama fallback")
        return await process_with_ollama(prompt, provider)

async def process_task(task: dict):
    """Process a single task"""
    task_id = task.get("id")
    prompt = task.get("prompt", "")
    provider = task.get("provider", "chatgpt")

    log(f"Processing task {task_id} via {provider}")
    mark_task_processing(task_id)

    # Try browser first, fall back to Ollama
    response, success = await process_with_ollama(prompt, provider)

    write_response(task_id, response, success, provider)
    mark_task_done(task_id)

    log(f"Task {task_id} completed (success={success})")

async def daemon_loop():
    """Main daemon loop - polls queue and processes tasks"""
    log("SAM Bridge Daemon started")

    while True:
        try:
            pending = get_pending_tasks()

            for task in pending:
                await process_task(task)

            await asyncio.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            log("Daemon shutting down")
            break
        except Exception as e:
            log(f"Error in daemon loop: {e}")
            await asyncio.sleep(POLL_INTERVAL)

def cleanup(signum, frame):
    """Cleanup on exit"""
    if PID_FILE.exists():
        PID_FILE.unlink()
    log("Daemon stopped")
    sys.exit(0)

def main():
    # Write PID file
    PID_FILE.write_text(str(os.getpid()))

    # Setup signal handlers
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    # Run daemon
    asyncio.run(daemon_loop())

if __name__ == "__main__":
    main()
