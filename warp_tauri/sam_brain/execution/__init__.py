"""
SAM Execution System

This module provides safe command execution, auto-fix capabilities,
and escalation handling for SAM's autonomous actions.

Modules:
- auto_fix: Automatic code issue detection and fixing
- auto_fix_control: Permission and rate limiting for auto-fix
- command_classifier: Command safety classification
- command_proposer: Command proposal generation
- escalation_handler: Claude escalation logic
- escalation_learner: Learning from escalations
- execution_history: Execution logging and rollback
- safe_executor: Sandboxed command execution

Usage:
    from execution import (
        AutoFixer, IssueDetector, detect_issues, fix_file,
        AutoFixController, get_auto_fix_controller,
        CommandClassifier, RiskLevel, CommandType,
        CommandProposer, ProposalFormatter,
        process_request, escalate_to_claude, EscalationReason,
        EscalationLearner,
        RollbackManager, ExecutionLogger, ExecutionResult,
        SafeExecutor, create_safe_context, ExecutionStatus,
    )
"""

__version__ = "1.0.0"

# auto_fix.py exports
from execution.auto_fix import (
    AutoFixableIssue,
    DetectedIssue,
    FixResult,
    AutoFixProposal,
    ToolChecker,
    IssueDetector,
    ExecutionHistory,
    AutoFixer,
    detect_issues,
    fix_file,
    fix_project,
    get_stats,
)

# auto_fix_control.py exports
from execution.auto_fix_control import (
    AutoFixPermissions,
    RateLimitStatus,
    AutoFixStats,
    AutoFixTracker,
    AutoFixController,
    FixResultStatus,
    get_auto_fix_controller,
    notify_auto_fixes_available,
    notify_auto_fixes_completed,
    notify_auto_fix_failed,
    api_autofix_permissions_get,
    api_autofix_permissions_update,
    api_autofix_stats,
    api_autofix_run,
    api_autofix_pending,
    api_autofix_history,
)

# command_classifier.py exports
from execution.command_classifier import (
    CommandType,
    RiskLevel,
    ClassificationResult,
    CommandClassifier,
    classify_command,
    is_safe_command,
    get_command_dangers,
)

# command_proposer.py exports
from execution.command_proposer import (
    CommandProposal,
    ExecutionResult as ProposerExecutionResult,
    CommandProposer,
    ProposalFormatter,
    ProposalHistory,
    propose_fix,
    propose_task,
    format_proposal,
)

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

# execution_history.py exports
from execution.execution_history import (
    CheckpointStatus,
    ExecutionStatus as HistoryExecutionStatus,
    ExecutionResult as HistoryExecutionResult,
    CommandLog,
    Checkpoint,
    CheckpointInfo,
    RollbackResult,
    ExecutionStats,
    RollbackManager,
    ExecutionLogger,
    get_rollback_manager,
    get_execution_logger,
    api_execution_history,
    api_execution_stats,
    api_execution_rollback,
    api_execution_checkpoints,
    api_checkpoint_details,
    api_create_checkpoint,
    api_cleanup_checkpoints,
    api_export_executions,
)

# safe_executor.py exports
from execution.safe_executor import (
    ExecutionStatus,
    ExecutionResult,
    FileOperationResult,
    ExecutionContext,
    RollbackInfo,
    FileOperation,
    SafeExecutor,
    check_with_classifier,
    create_safe_context,
    get_executor,
    safe_execute,
)

__all__ = [
    # auto_fix
    "AutoFixableIssue",
    "DetectedIssue",
    "FixResult",
    "AutoFixProposal",
    "ToolChecker",
    "IssueDetector",
    "ExecutionHistory",
    "AutoFixer",
    "detect_issues",
    "fix_file",
    "fix_project",
    "get_stats",
    # auto_fix_control
    "AutoFixPermissions",
    "RateLimitStatus",
    "AutoFixStats",
    "AutoFixTracker",
    "AutoFixController",
    "FixResultStatus",
    "get_auto_fix_controller",
    "notify_auto_fixes_available",
    "notify_auto_fixes_completed",
    "notify_auto_fix_failed",
    "api_autofix_permissions_get",
    "api_autofix_permissions_update",
    "api_autofix_stats",
    "api_autofix_run",
    "api_autofix_pending",
    "api_autofix_history",
    # command_classifier
    "CommandType",
    "RiskLevel",
    "ClassificationResult",
    "CommandClassifier",
    "classify_command",
    "is_safe_command",
    "get_command_dangers",
    # command_proposer
    "CommandProposal",
    "ProposerExecutionResult",
    "CommandProposer",
    "ProposalFormatter",
    "ProposalHistory",
    "propose_fix",
    "propose_task",
    "format_proposal",
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
    # execution_history
    "CheckpointStatus",
    "HistoryExecutionStatus",
    "HistoryExecutionResult",
    "CommandLog",
    "Checkpoint",
    "CheckpointInfo",
    "RollbackResult",
    "ExecutionStats",
    "RollbackManager",
    "ExecutionLogger",
    "get_rollback_manager",
    "get_execution_logger",
    "api_execution_history",
    "api_execution_stats",
    "api_execution_rollback",
    "api_execution_checkpoints",
    "api_checkpoint_details",
    "api_create_checkpoint",
    "api_cleanup_checkpoints",
    "api_export_executions",
    # safe_executor
    "ExecutionStatus",
    "ExecutionResult",
    "FileOperationResult",
    "ExecutionContext",
    "RollbackInfo",
    "FileOperation",
    "SafeExecutor",
    "check_with_classifier",
    "create_safe_context",
    "get_executor",
    "safe_execute",
]
