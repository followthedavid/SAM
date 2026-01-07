#!/usr/bin/env python3
"""
SAM Smart Router
- First tries local models
- Sanitizes and routes to external LLMs only when needed
- Manages context to prevent credit burning
"""

import os
import re
import json
import hashlib
from pathlib import Path
from typing import Optional, Dict, Tuple
from dataclasses import dataclass
from enum import Enum

class Provider(Enum):
    LOCAL = "local"           # SAM Brain / Ollama
    CHATGPT = "chatgpt"       # Via browser bridge
    CLAUDE = "claude"         # Via API or browser bridge

@dataclass
class RoutingDecision:
    provider: Provider
    sanitized_prompt: str
    context_summary: str
    estimated_tokens: int
    reason: str

# Patterns that indicate complex tasks needing external LLM
COMPLEX_PATTERNS = [
    r"implement|create|build|write.*function|write.*class",
    r"debug|fix.*bug|why.*not working|error",
    r"refactor|redesign|architect",
    r"explain.*complex|how does.*work",
    r"optimize|improve performance",
    r"security|vulnerability",
]

# Patterns that local models handle well
LOCAL_PATTERNS = [
    r"list|show|display|what.*files",
    r"read|cat|head|tail",
    r"git status|git diff|git log",
    r"run|execute|test",
    r"simple|quick|just",
    r"rename|move|copy",
    r"format|lint|check",
]

# Secrets to strip before sending externally
SECRET_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey|secret|token|password|passwd|pwd)\s*[=:]\s*["\']?[\w\-\.]+["\']?', '[REDACTED_SECRET]'),
    (r'(?i)bearer\s+[\w\-\.]+', 'Bearer [REDACTED]'),
    (r'sk-[a-zA-Z0-9]{20,}', '[OPENAI_KEY_REDACTED]'),
    (r'anthropic-[a-zA-Z0-9]{20,}', '[ANTHROPIC_KEY_REDACTED]'),
    (r'ghp_[a-zA-Z0-9]{36}', '[GITHUB_TOKEN_REDACTED]'),
    (r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*', '[JWT_REDACTED]'),
]

# Path anonymization (pattern, replacement)
PATH_REPLACEMENTS = [
    (r'/Users/\w+/', '/Users/USER/'),
    (r'/home/\w+/', '/home/USER/'),
]


def sanitize_content(content: str) -> str:
    """Remove secrets and anonymize paths."""
    result = content

    # Remove secrets
    for pattern, replacement in SECRET_PATTERNS:
        result = re.sub(pattern, replacement, result)

    # Anonymize paths
    for pattern, replacement in PATH_REPLACEMENTS:
        result = re.sub(pattern, replacement, result)

    return result


def summarize_context(context: str, max_lines: int = 50) -> str:
    """Summarize large context to prevent token waste."""
    lines = context.split('\n')

    if len(lines) <= max_lines:
        return context

    # Take beginning, relevant middle, and end
    summary_parts = [
        "# Context Summary (truncated)",
        "",
        "## Beginning:",
        '\n'.join(lines[:15]),
        "",
        "## Middle (around line {}):".format(len(lines)//2),
        '\n'.join(lines[len(lines)//2 - 5 : len(lines)//2 + 5]),
        "",
        "## End:",
        '\n'.join(lines[-15:]),
        "",
        f"# Total lines: {len(lines)} (showing {max_lines})"
    ]

    return '\n'.join(summary_parts)


def estimate_complexity(prompt: str) -> Tuple[int, str]:
    """
    Estimate task complexity (1-10).
    Returns (score, reason)
    """
    prompt_lower = prompt.lower()

    # Check for complex patterns
    for pattern in COMPLEX_PATTERNS:
        if re.search(pattern, prompt_lower):
            return (8, f"Complex task pattern: {pattern}")

    # Check for local-friendly patterns
    for pattern in LOCAL_PATTERNS:
        if re.search(pattern, prompt_lower):
            return (2, f"Simple task pattern: {pattern}")

    # Check length and detail
    word_count = len(prompt.split())
    if word_count > 100:
        return (6, "Detailed request (many words)")

    if "?" in prompt and word_count < 20:
        return (3, "Simple question")

    return (5, "Medium complexity (default)")


def count_tokens(text: str) -> int:
    """Rough token estimate (words * 1.3)."""
    return int(len(text.split()) * 1.3)


def route_request(
    prompt: str,
    context: Optional[str] = None,
    force_provider: Optional[Provider] = None,
    local_model: str = "dolphin-llama3:8b"
) -> RoutingDecision:
    """
    Decide where to route a request.

    Returns a RoutingDecision with:
    - Which provider to use
    - Sanitized prompt (secrets removed)
    - Summarized context
    - Estimated tokens
    - Reason for decision
    """

    # Force provider if specified
    if force_provider:
        sanitized = sanitize_content(prompt)
        ctx_summary = summarize_context(context) if context else ""
        return RoutingDecision(
            provider=force_provider,
            sanitized_prompt=sanitized,
            context_summary=sanitize_content(ctx_summary),
            estimated_tokens=count_tokens(sanitized + ctx_summary),
            reason=f"Forced to {force_provider.value}"
        )

    # Estimate complexity
    complexity, reason = estimate_complexity(prompt)

    # Prepare content
    sanitized_prompt = sanitize_content(prompt)
    context_summary = ""
    if context:
        context_summary = summarize_context(sanitize_content(context))

    total_tokens = count_tokens(sanitized_prompt + context_summary)

    # Routing logic
    if complexity <= 4:
        # Simple task - local can handle
        return RoutingDecision(
            provider=Provider.LOCAL,
            sanitized_prompt=prompt,  # No sanitization needed for local
            context_summary=context or "",
            estimated_tokens=total_tokens,
            reason=f"Simple task (complexity {complexity}): {reason}"
        )

    elif complexity <= 6:
        # Medium - try local first, but prepare for escalation
        return RoutingDecision(
            provider=Provider.LOCAL,
            sanitized_prompt=prompt,
            context_summary=context or "",
            estimated_tokens=total_tokens,
            reason=f"Medium task (complexity {complexity}): {reason} - trying local first"
        )

    else:
        # Complex - route to external
        # Prefer Claude for coding tasks
        provider = Provider.CLAUDE if "code" in prompt.lower() or "function" in prompt.lower() else Provider.CHATGPT

        return RoutingDecision(
            provider=provider,
            sanitized_prompt=sanitized_prompt,
            context_summary=context_summary,
            estimated_tokens=total_tokens,
            reason=f"Complex task (complexity {complexity}): {reason}"
        )


def format_external_prompt(decision: RoutingDecision, project_name: str = "") -> str:
    """
    Format a clean, focused prompt for external LLMs.
    Prevents overwhelming them with unnecessary context.
    """
    parts = []

    if project_name:
        parts.append(f"Project: {project_name}")
        parts.append("")

    parts.append("Task:")
    parts.append(decision.sanitized_prompt)

    if decision.context_summary:
        parts.append("")
        parts.append("Relevant Context:")
        parts.append(decision.context_summary)

    parts.append("")
    parts.append("Please provide a focused, actionable response.")

    return '\n'.join(parts)


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Smart Router")
        print("================")
        print()
        print("Usage:")
        print("  smart_router.py route '<prompt>'     - Get routing decision")
        print("  smart_router.py sanitize '<text>'    - Sanitize text")
        print("  smart_router.py test                 - Run test cases")
        print()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "route" and len(sys.argv) > 2:
        prompt = sys.argv[2]
        decision = route_request(prompt)
        print(f"Provider: {decision.provider.value}")
        print(f"Reason: {decision.reason}")
        print(f"Estimated tokens: {decision.estimated_tokens}")
        print(f"Sanitized: {decision.sanitized_prompt[:100]}...")

    elif cmd == "sanitize" and len(sys.argv) > 2:
        text = sys.argv[2]
        print(sanitize_content(text))

    elif cmd == "test":
        test_cases = [
            "list all files in the project",
            "implement a user authentication system with OAuth2",
            "git status",
            "explain how the routing algorithm works and suggest improvements",
            "run the tests",
            "debug why the login is failing with error 403",
            "rename foo.py to bar.py",
        ]

        print("Routing Test Cases")
        print("=" * 60)
        for prompt in test_cases:
            decision = route_request(prompt)
            print(f"\nPrompt: {prompt}")
            print(f"  → {decision.provider.value}: {decision.reason}")
