#!/usr/bin/env python3
"""
SAM Privacy Guard - Guardian, Not Censor

Philosophy:
- SAM is a GUARDIAN, not a blocker
- Scans outgoing messages for PII and sensitive data
- WARNS the user, but respects their final decision
- Can encrypt/redact sensitive content if user chooses
- Protects you from yourself, doesn't control you

"I'll tell you what I see. You decide what to do."
"""

import re
import hashlib
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

# Storage for user decisions (remember "allow" choices)
DECISIONS_PATH = Path.home() / ".sam" / "privacy_decisions.json"


@dataclass
class SensitiveMatch:
    """A detected piece of sensitive information"""
    category: str       # Type of sensitive data
    value: str          # The actual matched value
    start: int          # Start position in text
    end: int            # End position in text
    severity: str       # "high", "medium", "low"
    description: str    # Human-readable description


@dataclass
class ScanResult:
    """Result of scanning text for sensitive data"""
    has_sensitive: bool
    matches: list       # List of SensitiveMatch
    warnings: list      # List of warning messages
    can_proceed: bool   # User previously allowed this type


# PII detection patterns
PII_PATTERNS = {
    # High severity - definitely sensitive
    "ssn": {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "severity": "high",
        "description": "Social Security Number detected"
    },
    "credit_card": {
        "pattern": r"\b(?:\d{4}[-\s]?){3}\d{4}\b",
        "severity": "high",
        "description": "Credit card number detected"
    },
    "api_key": {
        "pattern": r"\b(?:sk-|pk_|api[_-]?key[=:\s]+)[a-zA-Z0-9_-]{20,}\b",
        "severity": "high",
        "description": "API key detected"
    },
    "password_field": {
        "pattern": r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]{8,}",
        "severity": "high",
        "description": "Password value detected"
    },
    "private_key": {
        "pattern": r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----",
        "severity": "high",
        "description": "Private key detected"
    },
    "jwt_token": {
        "pattern": r"\beyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b",
        "severity": "high",
        "description": "JWT token detected"
    },

    # Medium severity - contextually sensitive
    "email": {
        "pattern": r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b",
        "severity": "medium",
        "description": "Email address detected"
    },
    "phone": {
        "pattern": r"\b(?:\+1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b",
        "severity": "medium",
        "description": "Phone number detected"
    },
    "ip_address": {
        "pattern": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        "severity": "medium",
        "description": "IP address detected"
    },
    "aws_key": {
        "pattern": r"\bAKIA[0-9A-Z]{16}\b",
        "severity": "high",
        "description": "AWS Access Key ID detected"
    },
    "stripe_key": {
        "pattern": r"\b(?:sk_live_|pk_live_|sk_test_|pk_test_)[a-zA-Z0-9]+\b",
        "severity": "high",
        "description": "Stripe API key detected"
    },

    # Low severity - potentially sensitive in context
    "street_address": {
        "pattern": r"\b\d{1,5}\s+[A-Za-z]+\s+(?:St|Street|Ave|Avenue|Blvd|Boulevard|Dr|Drive|Ln|Lane|Rd|Road|Ct|Court)\b",
        "severity": "low",
        "description": "Street address detected"
    },
    "date_of_birth": {
        "pattern": r"\b(?:DOB|birth(?:date|day)?)[:\s]+\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        "severity": "low",
        "description": "Date of birth detected"
    },
}


class PrivacyGuard:
    """
    SAM's Privacy Guardian

    Scans outgoing messages for sensitive data and warns the user.
    Does NOT block - advises and respects user decisions.
    """

    def __init__(self):
        self.decisions_path = DECISIONS_PATH
        self.decisions_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_decisions()

    def _load_decisions(self):
        """Load remembered user decisions"""
        if self.decisions_path.exists():
            try:
                self.decisions = json.loads(self.decisions_path.read_text())
            except Exception:
                self.decisions = {"allowed_hashes": [], "blocked_categories": []}
        else:
            self.decisions = {"allowed_hashes": [], "blocked_categories": []}

    def _save_decisions(self):
        """Save user decisions"""
        self.decisions_path.write_text(json.dumps(self.decisions, indent=2))

    def _hash_content(self, content: str) -> str:
        """Create a hash of content for remembering decisions"""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def scan(self, text: str, destination: str = "unknown") -> ScanResult:
        """
        Scan text for sensitive information.

        Args:
            text: The text to scan
            destination: Where this text is being sent (claude, chatgpt, etc.)

        Returns:
            ScanResult with findings and warnings
        """
        matches = []
        warnings = []

        for category, config in PII_PATTERNS.items():
            pattern = re.compile(config["pattern"], re.IGNORECASE)
            for match in pattern.finditer(text):
                sensitive = SensitiveMatch(
                    category=category,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    severity=config["severity"],
                    description=config["description"]
                )
                matches.append(sensitive)

        # Generate warnings
        high_severity = [m for m in matches if m.severity == "high"]
        medium_severity = [m for m in matches if m.severity == "medium"]
        low_severity = [m for m in matches if m.severity == "low"]

        if high_severity:
            warnings.append(f"HIGH RISK: {len(high_severity)} highly sensitive item(s) detected!")
            for m in high_severity:
                warnings.append(f"  - {m.description}: {self._mask_value(m.value)}")

        if medium_severity:
            warnings.append(f"CAUTION: {len(medium_severity)} potentially sensitive item(s) detected")
            for m in medium_severity:
                warnings.append(f"  - {m.description}: {self._mask_value(m.value)}")

        if low_severity and not high_severity:  # Only show low if no high
            warnings.append(f"INFO: {len(low_severity)} low-risk item(s) detected")

        # Check if user previously allowed this exact content
        content_hash = self._hash_content(text)
        previously_allowed = content_hash in self.decisions.get("allowed_hashes", [])

        return ScanResult(
            has_sensitive=len(matches) > 0,
            matches=matches,
            warnings=warnings,
            can_proceed=previously_allowed or len(high_severity) == 0
        )

    def _mask_value(self, value: str) -> str:
        """Mask a sensitive value for display (show first/last chars only)"""
        if len(value) <= 4:
            return "*" * len(value)
        return f"{value[:2]}{'*' * (len(value) - 4)}{value[-2:]}"

    def redact(self, text: str, matches: list) -> str:
        """
        Redact sensitive values from text.

        Replaces detected sensitive values with [REDACTED_TYPE].
        """
        # Sort matches by position (reverse) to avoid index shifting
        sorted_matches = sorted(matches, key=lambda m: m.start, reverse=True)

        result = text
        for match in sorted_matches:
            redacted = f"[REDACTED_{match.category.upper()}]"
            result = result[:match.start] + redacted + result[match.end:]

        return result

    def remember_decision(self, text: str, allowed: bool):
        """
        Remember user's decision about this content.

        Args:
            text: The original text
            allowed: Whether user chose to allow sending
        """
        content_hash = self._hash_content(text)

        if allowed:
            if content_hash not in self.decisions["allowed_hashes"]:
                self.decisions["allowed_hashes"].append(content_hash)
                # Keep only last 1000 decisions
                self.decisions["allowed_hashes"] = self.decisions["allowed_hashes"][-1000:]
        else:
            # Remove from allowed if user changed mind
            if content_hash in self.decisions["allowed_hashes"]:
                self.decisions["allowed_hashes"].remove(content_hash)

        self._save_decisions()

    def format_warning(self, scan_result: ScanResult, destination: str = "LLM") -> str:
        """
        Format a user-friendly warning message.

        This is the guardian speaking - informative, not preachy.
        """
        if not scan_result.has_sensitive:
            return ""

        lines = [
            "=" * 50,
            "SAM PRIVACY GUARDIAN",
            "=" * 50,
            "",
            f"Before sending to {destination}, I noticed:",
            ""
        ]
        lines.extend(scan_result.warnings)
        lines.extend([
            "",
            "My role is to INFORM you, not control you.",
            "",
            "Options:",
            "  1. SEND ANYWAY - I trust you know what you're doing",
            "  2. REDACT - Replace sensitive values with [REDACTED]",
            "  3. CANCEL - Don't send this message",
            "",
            "What would you like to do?",
            "=" * 50
        ])

        return "\n".join(lines)


def guard_outgoing(text: str, destination: str = "claude") -> dict:
    """
    Main entry point for checking outgoing messages.

    Returns dict with:
        - safe: bool - Whether it's safe to proceed without warning
        - scan_result: The detailed scan result
        - warning: Formatted warning string (if any)
        - redacted: Redacted version of text (if sensitive content found)
    """
    guard = PrivacyGuard()
    result = guard.scan(text, destination)

    response = {
        "safe": not result.has_sensitive,
        "scan_result": {
            "has_sensitive": result.has_sensitive,
            "match_count": len(result.matches),
            "categories": list(set(m.category for m in result.matches)),
            "high_severity_count": len([m for m in result.matches if m.severity == "high"]),
            "previously_allowed": result.can_proceed
        },
        "warning": "",
        "redacted": text
    }

    if result.has_sensitive:
        response["warning"] = guard.format_warning(result, destination)
        response["redacted"] = guard.redact(text, result.matches)

    return response


def allow_and_send(text: str):
    """User chose to send despite warning - remember this"""
    guard = PrivacyGuard()
    guard.remember_decision(text, allowed=True)


def clear_decisions():
    """Clear all remembered decisions"""
    if DECISIONS_PATH.exists():
        DECISIONS_PATH.unlink()


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Privacy Guard")
        print("\nUsage:")
        print("  python privacy_guard.py scan <text>")
        print("  python privacy_guard.py demo")
        print("  python privacy_guard.py clear")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "demo":
        # Demo with test data
        test_cases = [
            "My email is test@example.com and phone is 555-123-4567",
            "API key: sk-1234567890abcdefghijklmnop",
            "My SSN is 123-45-6789",
            "Normal text with no sensitive info",
            "Password: supersecret123!",
            "Credit card: 4111-1111-1111-1111",
        ]

        guard = PrivacyGuard()

        for text in test_cases:
            print("\n" + "=" * 60)
            print(f"Input: {text[:50]}...")
            result = guard_outgoing(text)
            if result["safe"]:
                print("Result: SAFE")
            else:
                print(f"Result: WARNING - {result['scan_result']['match_count']} issue(s)")
                print(f"Categories: {result['scan_result']['categories']}")
                print(f"Redacted: {result['redacted']}")

    elif cmd == "scan":
        text = " ".join(sys.argv[2:])
        result = guard_outgoing(text)
        if result["warning"]:
            print(result["warning"])
        else:
            print("No sensitive information detected.")

    elif cmd == "clear":
        clear_decisions()
        print("Cleared all remembered decisions.")

    else:
        print(f"Unknown command: {cmd}")
