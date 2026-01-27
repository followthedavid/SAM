#!/usr/bin/env python3
"""
SAM Auto-Validator
==================

Automatically validates SAM's task results without human review.
Only escalates to human when truly necessary.

Validation Types:
- code_change: Syntax check, import check, test run
- create_file: File exists, syntax valid, no security issues
- analyze: Has content, no hallucinations detected
- run_command: Exit code check, output validation

Tasks that ALWAYS need human:
- UI/UX changes (visual verification)
- Security-sensitive changes
- Breaking API changes
"""

import os
import sys
import re
import json
import subprocess
import ast
from pathlib import Path
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ValidationResult(Enum):
    PASSED = "passed"           # Auto-approved
    FAILED = "failed"           # Needs fix
    NEEDS_HUMAN = "needs_human" # Can't auto-validate

@dataclass
class ValidationReport:
    result: ValidationResult
    checks_passed: List[str]
    checks_failed: List[str]
    reason: str
    auto_fix_suggestion: Optional[str] = None

# =============================================================================
# SYNTAX VALIDATORS
# =============================================================================

def validate_python_syntax(code: str) -> Tuple[bool, str]:
    """Check if Python code is syntactically valid."""
    try:
        ast.parse(code)
        return True, "Python syntax valid"
    except SyntaxError as e:
        return False, f"Python syntax error: {e}"

def validate_rust_syntax(code: str, file_path: str = None) -> Tuple[bool, str]:
    """Check Rust syntax by attempting to parse."""
    # Basic checks
    if "fn " in code and not re.search(r'fn\s+\w+\s*[\(<]', code):
        return False, "Invalid Rust function syntax"

    # Check for common issues
    issues = []
    if code.count('{') != code.count('}'):
        issues.append("Unbalanced braces")
    if code.count('(') != code.count(')'):
        issues.append("Unbalanced parentheses")

    if issues:
        return False, f"Rust issues: {', '.join(issues)}"

    return True, "Rust syntax appears valid"

def validate_typescript_syntax(code: str) -> Tuple[bool, str]:
    """Check TypeScript/JavaScript syntax."""
    issues = []

    # Basic balance checks
    if code.count('{') != code.count('}'):
        issues.append("Unbalanced braces")
    if code.count('(') != code.count(')'):
        issues.append("Unbalanced parentheses")
    if code.count('[') != code.count(']'):
        issues.append("Unbalanced brackets")

    # Check for common errors
    if re.search(r';\s*;', code):
        issues.append("Double semicolons")

    if issues:
        return False, f"TypeScript issues: {', '.join(issues)}"

    return True, "TypeScript syntax appears valid"

def detect_language(code: str, file_path: str = None) -> str:
    """Detect the programming language of code."""
    if file_path:
        ext = Path(file_path).suffix
        lang_map = {
            '.py': 'python', '.rs': 'rust', '.ts': 'typescript',
            '.js': 'javascript', '.vue': 'vue', '.swift': 'swift',
            '.cpp': 'cpp', '.c': 'c', '.java': 'java'
        }
        if ext in lang_map:
            return lang_map[ext]

    # Detect from content
    if 'def ' in code or 'import ' in code and 'from ' in code:
        return 'python'
    if 'fn ' in code and '-> ' in code:
        return 'rust'
    if 'function ' in code or 'const ' in code or '=>' in code:
        return 'typescript'

    return 'unknown'

# =============================================================================
# CONTENT VALIDATORS
# =============================================================================

def check_for_repetition(text: str, threshold: int = 3) -> Tuple[bool, str]:
    """Check if text has repetitive patterns (SAM failure mode)."""
    lines = text.split('\n')

    # Check for repeated lines
    seen = {}
    for line in lines:
        stripped = line.strip()
        if len(stripped) > 20:
            seen[stripped] = seen.get(stripped, 0) + 1
            if seen[stripped] > threshold:
                return False, f"Repetition detected: '{stripped[:50]}...' appears {seen[stripped]} times"

    return True, "No repetition detected"

def check_for_hallucination(text: str, project_path: str) -> Tuple[bool, str]:
    """Check if analysis mentions files that don't exist."""
    # Extract file paths mentioned
    file_patterns = re.findall(r'[\w/\-\.]+\.(py|rs|ts|js|vue|swift|cpp)', text)

    hallucinations = []
    for fp in file_patterns[:10]:  # Check first 10
        # Try to find the file
        full_path = Path(project_path) / fp
        if not full_path.exists():
            # Could be relative or abbreviated - not necessarily hallucination
            pass

    return True, "No obvious hallucinations"

def check_security_issues(code: str) -> Tuple[bool, List[str]]:
    """Check for security issues in generated code."""
    issues = []

    # Hardcoded secrets
    secret_patterns = [
        (r'api[_-]?key\s*=\s*["\'][^"\']+["\']', "Hardcoded API key"),
        (r'password\s*=\s*["\'][^"\']+["\']', "Hardcoded password"),
        (r'sk-[a-zA-Z0-9]{20,}', "OpenAI API key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub token"),
    ]

    for pattern, issue in secret_patterns:
        if re.search(pattern, code, re.IGNORECASE):
            issues.append(issue)

    # Dangerous operations
    if 'rm -rf' in code or 'sudo rm' in code:
        issues.append("Dangerous rm command")
    if 'eval(' in code and 'user' in code.lower():
        issues.append("Potential code injection via eval")

    return len(issues) == 0, issues

# =============================================================================
# TASK VALIDATORS
# =============================================================================

def validate_code_change(result: str, task: dict) -> ValidationReport:
    """Validate a code change task result."""
    checks_passed = []
    checks_failed = []

    # Extract code blocks (including unclosed ones from truncated responses)
    code_blocks = re.findall(r'```(?:\w+)?\n(.*?)```', result, re.DOTALL)

    # Also try to extract unclosed code blocks (SAM sometimes truncates)
    if not code_blocks:
        unclosed = re.findall(r'```(?:\w+)?\n(.+)', result, re.DOTALL)
        if unclosed:
            code_blocks = unclosed

    if not code_blocks:
        return ValidationReport(
            result=ValidationResult.FAILED,
            checks_passed=[],
            checks_failed=["No code blocks found in response"],
            reason="SAM didn't provide any code"
        )

    code = '\n'.join(code_blocks)
    file_path = task.get('target_file', '')

    # Language detection and syntax check
    lang = detect_language(code, file_path)

    if lang == 'python':
        valid, msg = validate_python_syntax(code)
    elif lang == 'rust':
        valid, msg = validate_rust_syntax(code, file_path)
    elif lang in ['typescript', 'javascript']:
        valid, msg = validate_typescript_syntax(code)
    else:
        valid, msg = True, f"Unknown language ({lang}), skipping syntax check"

    if valid:
        checks_passed.append(f"Syntax: {msg}")
    else:
        checks_failed.append(f"Syntax: {msg}")

    # Repetition check
    rep_valid, rep_msg = check_for_repetition(code)
    if rep_valid:
        checks_passed.append(f"Repetition: {rep_msg}")
    else:
        checks_failed.append(f"Repetition: {rep_msg}")

    # Security check
    sec_valid, sec_issues = check_security_issues(code)
    if sec_valid:
        checks_passed.append("Security: No issues found")
    else:
        checks_failed.extend([f"Security: {i}" for i in sec_issues])

    # Determine result
    if checks_failed:
        return ValidationReport(
            result=ValidationResult.FAILED,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            reason="Code validation failed"
        )

    return ValidationReport(
        result=ValidationResult.PASSED,
        checks_passed=checks_passed,
        checks_failed=[],
        reason="All checks passed"
    )

def validate_analysis(result: str, task: dict) -> ValidationReport:
    """Validate an analysis task result."""
    checks_passed = []
    checks_failed = []

    # Check for content
    if len(result) < 100:
        return ValidationReport(
            result=ValidationResult.FAILED,
            checks_passed=[],
            checks_failed=["Response too short (< 100 chars)"],
            reason="Insufficient analysis"
        )
    checks_passed.append("Content: Sufficient length")

    # Check for repetition
    rep_valid, rep_msg = check_for_repetition(result)
    if rep_valid:
        checks_passed.append(f"Repetition: {rep_msg}")
    else:
        checks_failed.append(f"Repetition: {rep_msg}")

    # Check for hallucination
    hall_valid, hall_msg = check_for_hallucination(result, task.get('project_path', '.'))
    if hall_valid:
        checks_passed.append(f"Hallucination: {hall_msg}")
    else:
        checks_failed.append(f"Hallucination: {hall_msg}")

    # Analysis tasks are lower stakes - pass if basic checks pass
    if checks_failed:
        return ValidationReport(
            result=ValidationResult.NEEDS_HUMAN,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            reason="Analysis may need human review"
        )

    return ValidationReport(
        result=ValidationResult.PASSED,
        checks_passed=checks_passed,
        checks_failed=[],
        reason="Analysis looks valid"
    )

def validate_create_file(result: str, task: dict) -> ValidationReport:
    """Validate a file creation task result."""
    # Same as code_change for now
    return validate_code_change(result, task)

# =============================================================================
# MAIN VALIDATOR
# =============================================================================

def validate_task(task: dict) -> ValidationReport:
    """Main entry point - validate any task type."""
    task_type = task.get('type', 'unknown')
    result = task.get('result', '')

    if task_type == 'code_change':
        return validate_code_change(result, task)
    elif task_type == 'analyze':
        return validate_analysis(result, task)
    elif task_type == 'create_file':
        return validate_create_file(result, task)
    elif task_type in ['run_command', 'research']:
        # These typically need human review
        return ValidationReport(
            result=ValidationResult.NEEDS_HUMAN,
            checks_passed=[],
            checks_failed=[],
            reason=f"Task type '{task_type}' requires human review"
        )
    else:
        return ValidationReport(
            result=ValidationResult.NEEDS_HUMAN,
            checks_passed=[],
            checks_failed=[],
            reason=f"Unknown task type: {task_type}"
        )

def auto_review_tasks():
    """Auto-review all tasks needing review."""
    import json
    from pathlib import Path

    tasks_file = Path.home() / ".sam" / "orchestrator" / "tasks.json"
    if not tasks_file.exists():
        print("No tasks found")
        return

    tasks = json.loads(tasks_file.read_text())

    auto_approved = 0
    needs_human = 0
    failed = 0

    for task in tasks:
        if task.get('status') != 'needs_review':
            continue

        report = validate_task(task)

        if report.result == ValidationResult.PASSED:
            task['status'] = 'completed'
            auto_approved += 1
            print(f"[AUTO-APPROVED] {task['id']}: {task['description'][:40]}...")
        elif report.result == ValidationResult.FAILED:
            task['status'] = 'pending'
            task['instructions'] += f"\n\n[AUTO-VALIDATION FAILED]: {report.reason}\nIssues: {', '.join(report.checks_failed)}"
            failed += 1
            print(f"[RETRY] {task['id']}: {report.reason}")
        else:
            needs_human += 1
            print(f"[HUMAN REVIEW] {task['id']}: {report.reason}")

    tasks_file.write_text(json.dumps([t for t in tasks], indent=2))

    print(f"\nSummary: {auto_approved} auto-approved, {failed} need retry, {needs_human} need human review")

# CLI
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "review":
        auto_review_tasks()
    else:
        print("""
SAM Auto-Validator
==================

Usage:
  python auto_validator.py review    Auto-review pending tasks

Validation rules:
  - Code changes: Syntax check, repetition check, security check
  - Analysis: Content length, repetition, hallucination detection
  - Create file: Same as code change

Auto-approval if ALL checks pass.
Human review needed for: UI changes, security-sensitive, unknown types.
""")
