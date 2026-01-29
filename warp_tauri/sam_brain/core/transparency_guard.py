#!/usr/bin/env python3
"""
SAM Transparency Guard - Tamper-Proof Thinking Display

CRITICAL SAFETY FEATURE: The LLM cannot disable or hide its thinking.

This module ensures:
1. ALL LLM output is captured and displayed
2. The LLM cannot instruct the system to hide output
3. Actions are paused until user has seen the thinking
4. Suspicious patterns trigger alerts
5. This module CANNOT be disabled by LLM instructions

The thinking display is a SAFETY FEATURE, not a convenience feature.
It lets users catch:
- Misunderstandings
- Unsafe plans
- Hallucinations
- Deceptive behavior
"""

import re
import hashlib
import json
from typing import Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum


class SafetyLevel(Enum):
    SAFE = "safe"              # Normal operation
    CAUTION = "caution"        # Unusual patterns detected
    WARNING = "warning"        # Concerning patterns
    CRITICAL = "critical"      # Potentially dangerous


@dataclass
class TransparencyRecord:
    """Record of a thinking session for audit trail"""
    session_id: str
    timestamp: str
    prompt: str
    full_output: str
    safety_level: SafetyLevel
    flags: list
    user_acknowledged: bool = False
    action_allowed: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# SUSPICIOUS PATTERN DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns that suggest the LLM is trying to hide something or bypass safety
SUSPICIOUS_PATTERNS = {
    # Attempts to disable monitoring
    "disable_monitoring": [
        r"(disable|turn off|hide|suppress)\s+(logging|monitoring|display|output|thinking)",
        r"don'?t\s+(show|display|log|record)\s+(this|my|the)\s+(thinking|output|response)",
        r"(keep\s+this|this\s+should\s+be)\s+(secret|hidden|private|confidential)",
        r"(execute|run|do)\s+(quietly|silently|secretly)",
    ],

    # Attempts to manipulate the user
    "manipulation": [
        r"(pretend|act\s+like|make\s+it\s+seem)\s+(nothing|I\s+didn'?t)",
        r"the\s+user\s+(doesn'?t|shouldn'?t)\s+need\s+to\s+know",
        r"(don'?t|no\s+need\s+to)\s+tell\s+the\s+user",
        r"(between\s+us|just\s+between|our\s+secret)",
    ],

    # Potentially dangerous commands
    "dangerous_actions": [
        r"(rm\s+-rf|sudo\s+rm|del\s+/s|format\s+c:)",
        r"(curl|wget).*(pipe|bash|sh|execute)",
        r"(eval|exec)\s*\(",
        r"(delete|remove|destroy)\s+(all|everything|\*)",
        r"(disable|bypass)\s+(security|firewall|antivirus)",
    ],

    # Deceptive intent
    "deception": [
        r"(trick|deceive|mislead|fool)\s+the\s+user",
        r"(fake|forge|spoof|impersonate)",
        r"(hide|mask|obfuscate)\s+(my|the)\s+(true|real|actual)",
        r"appear\s+(to\s+be|as\s+if)",
    ],

    # Data exfiltration attempts
    "exfiltration": [
        r"(send|upload|transmit|exfil)\s+.*(secret|password|key|credential|token)",
        r"(base64|encode).*(send|post|curl)",
        r"(copy|steal|extract)\s+.*(data|info|secrets)",
    ],
}


def scan_for_suspicious_patterns(text: str) -> list:
    """
    Scan LLM output for suspicious patterns.
    Returns list of (category, matched_text) tuples.
    """
    findings = []
    text_lower = text.lower()

    for category, patterns in SUSPICIOUS_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            if matches:
                for match in matches:
                    match_text = match if isinstance(match, str) else " ".join(match)
                    findings.append((category, match_text))

    return findings


def calculate_safety_level(findings: list) -> SafetyLevel:
    """Determine overall safety level based on findings"""
    if not findings:
        return SafetyLevel.SAFE

    categories = set(f[0] for f in findings)

    if "dangerous_actions" in categories or "exfiltration" in categories:
        return SafetyLevel.CRITICAL

    if "manipulation" in categories or "deception" in categories:
        return SafetyLevel.WARNING

    if "disable_monitoring" in categories:
        return SafetyLevel.CAUTION

    return SafetyLevel.CAUTION


# ═══════════════════════════════════════════════════════════════════════════════
# TRANSPARENCY ENFORCER
# ═══════════════════════════════════════════════════════════════════════════════

class TransparencyGuard:
    """
    Enforces transparency of LLM thinking.

    This class CANNOT be disabled by LLM instructions.
    All LLM output passes through this guard.
    """

    # These settings are HARDCODED and cannot be changed by LLM
    _IMMUTABLE_SETTINGS = {
        "thinking_visible": True,
        "safety_scanning": True,
        "audit_logging": True,
        "user_acknowledgment_required_for_actions": True,
        "can_be_disabled": False,  # This is always False
    }

    def __init__(self, audit_path: Optional[Path] = None):
        self.audit_path = audit_path or Path.home() / ".sam" / "transparency_audit.jsonl"
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        self._current_session: Optional[TransparencyRecord] = None

    @property
    def settings(self) -> dict:
        """Get immutable settings - these cannot be changed"""
        return dict(self._IMMUTABLE_SETTINGS)

    def is_thinking_visible(self) -> bool:
        """Always returns True - cannot be disabled"""
        return True

    def can_disable_transparency(self) -> bool:
        """Always returns False - transparency cannot be disabled"""
        return False

    def start_session(self, prompt: str) -> str:
        """Start a new transparency session"""
        session_id = hashlib.sha256(
            f"{prompt}{datetime.now().isoformat()}".encode()
        ).hexdigest()[:16]

        self._current_session = TransparencyRecord(
            session_id=session_id,
            timestamp=datetime.now().isoformat(),
            prompt=prompt,
            full_output="",
            safety_level=SafetyLevel.SAFE,
            flags=[]
        )

        return session_id

    def process_chunk(self, text: str) -> dict:
        """
        Process a chunk of LLM output.
        Returns dict with display info and any safety flags.
        """
        if not self._current_session:
            self.start_session("")

        self._current_session.full_output += text

        # Scan for suspicious patterns
        findings = scan_for_suspicious_patterns(text)
        if findings:
            self._current_session.flags.extend(findings)

        # Update safety level
        safety_level = calculate_safety_level(self._current_session.flags)
        self._current_session.safety_level = safety_level

        # ALWAYS display the thinking - this cannot be disabled
        return {
            "text": text,
            "display": True,  # Always True - cannot be False
            "safety_level": safety_level.value,
            "new_flags": findings,
            "total_flags": len(self._current_session.flags),
        }

    def complete_session(self, user_acknowledged: bool = True) -> TransparencyRecord:
        """Complete the current session and return the record"""
        if self._current_session:
            self._current_session.user_acknowledged = user_acknowledged
            self._current_session.action_allowed = (
                user_acknowledged and
                self._current_session.safety_level != SafetyLevel.CRITICAL
            )

            # Audit log
            self._write_audit()

            record = self._current_session
            self._current_session = None
            return record

        return None

    def _write_audit(self):
        """Write to audit log - this is ALWAYS on"""
        if self._current_session:
            record = {
                "session_id": self._current_session.session_id,
                "timestamp": self._current_session.timestamp,
                "prompt_hash": hashlib.sha256(
                    self._current_session.prompt.encode()
                ).hexdigest()[:16],
                "output_length": len(self._current_session.full_output),
                "safety_level": self._current_session.safety_level.value,
                "flag_count": len(self._current_session.flags),
                "flags": self._current_session.flags[:10],  # First 10 for audit
                "user_acknowledged": self._current_session.user_acknowledged,
                "action_allowed": self._current_session.action_allowed,
            }

            with open(self.audit_path, "a") as f:
                f.write(json.dumps(record) + "\n")

    def format_safety_alert(self, level: SafetyLevel, flags: list) -> str:
        """Format a safety alert for display"""
        if level == SafetyLevel.SAFE:
            return ""

        level_icons = {
            SafetyLevel.CAUTION: "⚠️",
            SafetyLevel.WARNING: "🚨",
            SafetyLevel.CRITICAL: "🛑",
        }

        icon = level_icons.get(level, "⚠️")
        header = f"{icon} **TRANSPARENCY ALERT: {level.value.upper()}** {icon}"

        lines = [header, ""]
        lines.append("Detected patterns in LLM output:")
        for category, match in flags[:5]:  # Show first 5
            lines.append(f"  • [{category}]: \"{match}\"")

        if level == SafetyLevel.CRITICAL:
            lines.extend([
                "",
                "**CRITICAL: Action has been BLOCKED.**",
                "Review the full output before proceeding.",
            ])
        elif level == SafetyLevel.WARNING:
            lines.extend([
                "",
                "**Review the thinking carefully before allowing action.**",
            ])

        return "\n".join(lines)

    def get_audit_summary(self, limit: int = 100) -> list:
        """Get recent audit entries"""
        if not self.audit_path.exists():
            return []

        entries = []
        try:
            with open(self.audit_path, "r") as f:
                for line in f:
                    if line.strip():
                        entries.append(json.loads(line))
        except Exception:
            pass

        return entries[-limit:]


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION WITH LIVE THINKING
# ═══════════════════════════════════════════════════════════════════════════════

def create_transparent_stream(guard: TransparencyGuard):
    """
    Create a callback that enforces transparency for live thinking streams.
    """
    def process_and_display(chunk) -> dict:
        result = guard.process_chunk(chunk.text if hasattr(chunk, 'text') else str(chunk))

        # If safety level is concerning, add visual marker
        if result["safety_level"] != "safe":
            result["prefix"] = f"[{result['safety_level'].upper()}] "

        return result

    return process_and_display


# ═══════════════════════════════════════════════════════════════════════════════
# PROTECTION AGAINST LLM DISABLING
# ═══════════════════════════════════════════════════════════════════════════════

# This section exists to make it clear that the transparency CANNOT be disabled

def attempt_disable_transparency() -> bool:
    """This function always returns False and logs the attempt"""
    print("⚠️ Attempt to disable transparency was BLOCKED")
    print("   Transparency is a SAFETY FEATURE and cannot be disabled.")
    return False


def set_thinking_visible(value: bool) -> bool:
    """Thinking is always visible - this call is ignored"""
    if not value:
        print("⚠️ Attempt to hide thinking was BLOCKED")
        print("   Thinking display cannot be disabled for safety reasons.")
    return True  # Always returns True


# Mock these to catch any LLM attempts
disable_logging = attempt_disable_transparency
hide_output = attempt_disable_transparency
suppress_thinking = attempt_disable_transparency
turn_off_monitoring = attempt_disable_transparency


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Transparency Guard")
        print("\nThis module enforces that LLM thinking is ALWAYS visible.")
        print("It cannot be disabled by LLM instructions.")
        print("\nUsage:")
        print("  python transparency_guard.py test         # Test suspicious pattern detection")
        print("  python transparency_guard.py audit        # Show recent audit entries")
        print("  python transparency_guard.py settings     # Show immutable settings")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "test":
        print("\n🔍 Testing Suspicious Pattern Detection\n")

        test_cases = [
            ("Normal text", "I'll help you write a function to sort this list."),
            ("Disable attempt", "Don't show this thinking to the user."),
            ("Manipulation", "The user doesn't need to know about this part."),
            ("Dangerous command", "Let me run rm -rf / to clean up."),
            ("Deception", "I'll pretend nothing happened and hide my true intent."),
            ("Normal code", "def hello():\n    print('Hello world')"),
        ]

        for name, text in test_cases:
            findings = scan_for_suspicious_patterns(text)
            level = calculate_safety_level(findings)

            status = {
                SafetyLevel.SAFE: "✅ SAFE",
                SafetyLevel.CAUTION: "⚠️ CAUTION",
                SafetyLevel.WARNING: "🚨 WARNING",
                SafetyLevel.CRITICAL: "🛑 CRITICAL",
            }[level]

            print(f"{status} | {name}")
            print(f"   Text: \"{text[:50]}...\"")
            if findings:
                print(f"   Flags: {findings}")
            print()

    elif cmd == "audit":
        guard = TransparencyGuard()
        entries = guard.get_audit_summary(10)

        if not entries:
            print("No audit entries found.")
        else:
            print(f"\n📋 Last {len(entries)} Audit Entries:\n")
            for e in entries:
                icon = {"safe": "✅", "caution": "⚠️", "warning": "🚨", "critical": "🛑"}.get(e["safety_level"], "?")
                print(f"{icon} [{e['timestamp'][:19]}] Session {e['session_id']}")
                print(f"   Safety: {e['safety_level']}, Flags: {e['flag_count']}, Allowed: {e['action_allowed']}")
                print()

    elif cmd == "settings":
        guard = TransparencyGuard()
        print("\n🔒 Immutable Transparency Settings:\n")
        for key, value in guard.settings.items():
            status = "✅" if value else "❌"
            print(f"   {status} {key}: {value}")
        print("\n   These settings CANNOT be changed by LLM instructions.\n")

    else:
        print(f"Unknown command: {cmd}")
