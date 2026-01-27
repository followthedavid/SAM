#!/usr/bin/env python3
"""
SAM Proactive Notifier

Runs in the background and pushes recommendations to you WITHOUT being asked.
- macOS notifications for important items
- Optional voice announcements
- Cooldown to prevent spam
- Smart filtering (only notify on changes)
- Feedback awareness (Phase 1.2.8) - tracks corrections and suggests reviews

Usage:
    python3 proactive_notifier.py start   # Start daemon
    python3 proactive_notifier.py stop    # Stop daemon
    python3 proactive_notifier.py status  # Check status
    python3 proactive_notifier.py test    # Test notification
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Set
import urllib.request
import urllib.error

# Configuration
SAM_API = "http://localhost:8765"
CHECK_INTERVAL_SECONDS = 300  # 5 minutes
NOTIFICATION_COOLDOWN_MINUTES = 30  # Don't repeat same notification within this time
VOICE_ENABLED = True  # Speak important notifications
VOICE_COOLDOWN_MINUTES = 60  # Don't speak too often
PID_FILE = Path("/tmp/sam_proactive_notifier.pid")
LOG_FILE = Path("/Volumes/David External/sam_memory/proactive.log")
STATE_FILE = Path("/Volumes/David External/sam_memory/proactive_state.json")

# Notification priorities
PRIORITY_HIGH = ["critical", "urgent", "blocking", "error"]
PRIORITY_MEDIUM = ["stale_project", "auto_approve_ready", "corrections_threshold", "accuracy_drop"]
PRIORITY_LOW = ["suggestion", "optimization", "training_ready"]

# Feedback thresholds (Phase 1.2.8)
CORRECTION_THRESHOLD = 3  # Notify when this many corrections in a day
NEGATIVE_FEEDBACK_THRESHOLD = 5  # Notify when this many negative ratings
UNPROCESSED_TRAINING_THRESHOLD = 5  # Notify when this many items ready for export


def log(message: str, level: str = "INFO"):
    """Log with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] [{level}] {message}"
    print(line)
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except:
        pass


def send_macos_notification(title: str, message: str, sound: bool = True):
    """Send a macOS notification."""
    try:
        sound_param = 'sound name "Ping"' if sound else ""
        script = f'''
        display notification "{message}" with title "{title}" {sound_param}
        '''
        subprocess.run(["osascript", "-e", script], capture_output=True)
        log(f"Notification sent: {title}")
    except Exception as e:
        log(f"Notification failed: {e}", "ERROR")


def speak(text: str):
    """Speak text using SAM's voice or system TTS."""
    if not VOICE_ENABLED:
        return

    try:
        # Try SAM's voice first
        data = json.dumps({"text": text[:500]}).encode()
        req = urllib.request.Request(
            f"{SAM_API}/api/speak",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
        log(f"Spoke via SAM: {text[:50]}...")
    except:
        # Fallback to system say
        try:
            subprocess.run(["say", "-v", "Daniel", text[:200]], capture_output=True)
            log(f"Spoke via system: {text[:50]}...")
        except:
            pass


def fetch_json(endpoint: str) -> Optional[Dict]:
    """Fetch JSON from SAM API."""
    try:
        url = f"{SAM_API}{endpoint}"
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        log(f"API fetch failed ({endpoint}): {e}", "ERROR")
        return None


def load_state() -> Dict:
    """Load persisted state."""
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
    except:
        pass
    return {
        "last_notifications": {},  # notification_id -> timestamp
        "last_voice": None,
        "seen_items": [],
    }


def save_state(state: Dict):
    """Save state to disk."""
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    except Exception as e:
        log(f"State save failed: {e}", "ERROR")


def should_notify(item_id: str, state: Dict) -> bool:
    """Check if we should notify for this item (cooldown check)."""
    last_notified = state.get("last_notifications", {}).get(item_id)
    if last_notified:
        try:
            last_time = datetime.fromisoformat(last_notified)
            if datetime.now() - last_time < timedelta(minutes=NOTIFICATION_COOLDOWN_MINUTES):
                return False
        except:
            pass
    return True


def should_speak(state: Dict) -> bool:
    """Check if voice is allowed (cooldown check)."""
    if not VOICE_ENABLED:
        return False
    last_voice = state.get("last_voice")
    if last_voice:
        try:
            last_time = datetime.fromisoformat(last_voice)
            if datetime.now() - last_time < timedelta(minutes=VOICE_COOLDOWN_MINUTES):
                return False
        except:
            pass
    return True


# ===== Phase 1.2.8: Feedback Awareness =====

def get_feedback_db():
    """Lazy import of FeedbackDB to avoid circular imports."""
    try:
        from feedback_system import get_feedback_db as _get_db
        return _get_db()
    except ImportError as e:
        log(f"Could not import feedback_system: {e}", "WARNING")
        return None


def check_feedback_stats() -> List[Dict]:
    """
    Check feedback statistics and return notification items.

    Returns:
        List of notification items with type, message, and urgency.
    """
    notifications = []

    db = get_feedback_db()
    if not db:
        return notifications

    try:
        data = db.get_feedback_notifications_data()

        # Return all threshold alerts from the feedback system
        for alert in data.get("threshold_alerts", []):
            notifications.append({
                "type": alert["type"],
                "message": alert["message"],
                "urgency": alert["urgency"],
                "source": "feedback_system"
            })

        # Log stats for debugging
        log(f"Feedback stats: {data['daily_corrections']} corrections, "
            f"{data['daily_negative']} negative, "
            f"{data['unprocessed_count']} unprocessed, "
            f"{len(data['declining_domains'])} declining domains")

    except Exception as e:
        log(f"Error checking feedback stats: {e}", "ERROR")

    return notifications


def check_and_notify():
    """Main check loop - fetch SAM status and notify if needed."""
    state = load_state()
    notifications_sent = 0

    # 1. Check proactive suggestions
    proactive = fetch_json("/api/proactive")
    if proactive and proactive.get("success"):
        for item in proactive.get("suggestions", [])[:5]:
            item_id = f"proactive_{item.get('type')}_{item.get('message', '')[:30]}"

            if should_notify(item_id, state):
                urgency = item.get("urgency", "low")
                message = item.get("message", "SAM noticed something")

                if urgency == "high":
                    send_macos_notification("🚨 SAM Alert", message, sound=True)
                    if should_speak(state):
                        speak(f"Hey David, {message}")
                        state["last_voice"] = datetime.now().isoformat()
                elif urgency == "medium":
                    send_macos_notification("🧠 SAM Suggestion", message, sound=False)

                state["last_notifications"][item_id] = datetime.now().isoformat()
                notifications_sent += 1

    # 2. Check for stale projects
    self_status = fetch_json("/api/self")
    if self_status and self_status.get("success"):
        status = self_status.get("status", {})
        proactive_items = status.get("proactive", [])

        for item in proactive_items:
            if item.get("type") == "stale_project":
                item_id = f"stale_{item.get('message', '')[:30]}"
                if should_notify(item_id, state):
                    send_macos_notification(
                        "📁 Project Needs Attention",
                        item.get("message", "A project is stale"),
                        sound=False
                    )
                    state["last_notifications"][item_id] = datetime.now().isoformat()
                    notifications_sent += 1

    # 3. Check resources (warn if low)
    resources = fetch_json("/api/resources")
    if resources and resources.get("success"):
        res = resources.get("resources", {})
        level = res.get("resource_level", "good")
        available = res.get("available_memory_gb", 0)

        if level == "critical":
            item_id = "resource_critical"
            if should_notify(item_id, state):
                send_macos_notification(
                    "⚠️ Memory Critical",
                    f"Only {available:.1f}GB free - SAM may be slow",
                    sound=True
                )
                state["last_notifications"][item_id] = datetime.now().isoformat()
                notifications_sent += 1

    # 4. Check feedback stats (Phase 1.2.8)
    feedback_notifications = check_feedback_stats()
    for item in feedback_notifications:
        item_id = f"feedback_{item.get('type')}_{item.get('message', '')[:30]}"

        if should_notify(item_id, state):
            urgency = item.get("urgency", "low")
            message = item.get("message", "Feedback update")
            notif_type = item.get("type", "")

            # Choose notification style based on type
            if notif_type == "corrections_threshold":
                send_macos_notification(
                    "Corrections Today",
                    message,
                    sound=False
                )
            elif notif_type == "accuracy_drop":
                send_macos_notification(
                    "Accuracy Alert",
                    message,
                    sound=True
                )
            elif notif_type == "training_ready":
                send_macos_notification(
                    "Training Data Ready",
                    message,
                    sound=False
                )
            elif notif_type == "negative_feedback":
                send_macos_notification(
                    "Feedback Alert",
                    message,
                    sound=False
                )
            else:
                send_macos_notification(
                    "SAM Feedback",
                    message,
                    sound=False
                )

            state["last_notifications"][item_id] = datetime.now().isoformat()
            notifications_sent += 1

    # Clean old notifications from state (keep last 100)
    if len(state.get("last_notifications", {})) > 100:
        sorted_items = sorted(
            state["last_notifications"].items(),
            key=lambda x: x[1],
            reverse=True
        )
        state["last_notifications"] = dict(sorted_items[:50])

    save_state(state)

    if notifications_sent > 0:
        log(f"Sent {notifications_sent} notifications")

    return notifications_sent


def daemon_loop():
    """Main daemon loop."""
    log("Proactive notifier started")

    # Initial notification
    send_macos_notification("🧠 SAM Active", "Proactive monitoring enabled", sound=False)

    while True:
        try:
            check_and_notify()
        except Exception as e:
            log(f"Check failed: {e}", "ERROR")

        time.sleep(CHECK_INTERVAL_SECONDS)


def start_daemon():
    """Start the daemon in background."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)  # Check if running
            print(f"Daemon already running (PID {pid})")
            return
        except ProcessLookupError:
            PID_FILE.unlink()  # Stale PID file

    # Fork to background
    if os.fork() > 0:
        print("Daemon started")
        return

    # Detach
    os.setsid()

    # Write PID
    PID_FILE.write_text(str(os.getpid()))

    # Run
    try:
        daemon_loop()
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()


def stop_daemon():
    """Stop the daemon."""
    if not PID_FILE.exists():
        print("Daemon not running")
        return

    pid = int(PID_FILE.read_text().strip())
    try:
        os.kill(pid, 15)  # SIGTERM
        print(f"Daemon stopped (PID {pid})")
        PID_FILE.unlink()
    except ProcessLookupError:
        print("Daemon was not running")
        PID_FILE.unlink()


def status():
    """Check daemon status."""
    if PID_FILE.exists():
        pid = int(PID_FILE.read_text().strip())
        try:
            os.kill(pid, 0)
            print(f"✅ Daemon running (PID {pid})")

            # Show state
            state = load_state()
            print(f"   Notifications tracked: {len(state.get('last_notifications', {}))}")
            if state.get('last_voice'):
                print(f"   Last voice: {state['last_voice']}")
            return
        except ProcessLookupError:
            pass

    print("❌ Daemon not running")


def test_notification():
    """Test notification system."""
    print("Testing macOS notification...")
    send_macos_notification("🧠 SAM Test", "Proactive notifier is working!", sound=True)

    print("Testing voice (if enabled)...")
    if VOICE_ENABLED:
        speak("Hey David, SAM's proactive notifier is working.")

    print("Testing API connection...")
    health = fetch_json("/api/health")
    if health:
        print(f"   API status: {health.get('status', 'unknown')}")
    else:
        print("   API not reachable")

    print("\nRunning one check cycle...")
    count = check_and_notify()
    print(f"   Sent {count} notifications")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "start":
        start_daemon()
    elif cmd == "stop":
        stop_daemon()
    elif cmd == "status":
        status()
    elif cmd == "test":
        test_notification()
    elif cmd == "run":
        # Run in foreground (for debugging)
        daemon_loop()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)
