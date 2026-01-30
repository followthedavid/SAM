"""
SAM Execution System

This module provides escalation handling for SAM's autonomous actions.

Active Modules:
- escalation_handler: Claude escalation logic
- escalation_learner: Learning from escalations

Archived to /Volumes/#1/SAM/dead_code_archive/sam_brain_additional/ (2026-01-29):
- auto_fix.py: Automatic code issue detection and fixing (test-only usage)
- auto_fix_control.py: Permission and rate limiting for auto-fix (test-only usage)
- command_classifier.py: Command safety classification (test-only usage)
- execution_history.py: Execution logging and rollback (test-only usage)
- safe_executor.py: Sandboxed command execution (test-only usage)

Usage:
    from execution import (
        process_request, escalate_to_claude, EscalationReason,
        EscalationLearner,
    )
"""

__version__ = "1.1.0"

# escalation_handler.py exports
from execution.escalation_handler import (
    EscalationReason,
    SAMResponse,
    get_cognitive,
    evaluate_confidence,
    should_auto_escalate,
    escalate_to_claude,
    process_request,
)

# escalation_learner.py exports
from execution.escalation_learner import (
    Escalation,
    TaskPattern,
    EscalationDB,
    EscalationLearner,
)

__all__ = [
    # escalation_handler
    "EscalationReason",
    "SAMResponse",
    "get_cognitive",
    "evaluate_confidence",
    "should_auto_escalate",
    "escalate_to_claude",
    "process_request",
    # escalation_learner
    "Escalation",
    "TaskPattern",
    "EscalationDB",
    "EscalationLearner",
]
