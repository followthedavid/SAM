# SAM Auto-Fix System

Phase 4.2 Documentation - Automatic Code Issue Detection and Fixing

## Overview

The SAM Auto-Fix System provides autonomous code quality maintenance by detecting and fixing simple, well-understood code issues. It operates under a strict safety-first philosophy: **fix only what is clearly safe, and never touch sensitive files or complex logic.**

### Philosophy

1. **Conservative by default** - Only fix issues with high confidence
2. **Reversible changes** - All fixes create backups before modification
3. **Transparent operation** - Full logging and statistics for all operations
4. **Permission-based** - Per-project control over what can be fixed
5. **Rate-limited** - Prevents runaway autonomous fixing

### Architecture

```
                    +-------------------+
                    | AutoFixController |
                    | (Permission Check)|
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
    +---------v---------+         +---------v---------+
    |   IssueDetector   |         |   AutoFixer       |
    | (Runs Linters)    |         | (Applies Fixes)   |
    +-------------------+         +-------------------+
              |                             |
              |                   +---------v---------+
              |                   |  ExecutionHistory |
              |                   | (Tracks Results)  |
              |                   +-------------------+
              |
    +---------v---------+
    |   AutoFixTracker  |
    | (Statistics/DB)   |
    +-------------------+
```

## Fixable Issue Types

### Fully Automatic (High Confidence)

| Issue Type | Description | Example | Tool |
|------------|-------------|---------|------|
| `TRAILING_WHITESPACE` | Spaces at end of lines | `def foo():   ` -> `def foo():` | Built-in |
| `MISSING_NEWLINE` | No newline at EOF | `pass` -> `pass\n` | Built-in |
| `FORMAT_ERROR` | Code formatting issues | Inconsistent indentation | black/prettier/rustfmt |
| `IMPORT_SORT` | Unsorted imports | Random import order | isort |
| `UNUSED_IMPORT` | Import never used | `import json  # never used` | ruff/eslint |

### Semi-Automatic (Requires Review Threshold)

| Issue Type | Description | Risk Level | Notes |
|------------|-------------|------------|-------|
| `LINT_ERROR` | General linting issues | Medium | Tool-specific |
| `TYPO` | Typos in strings/comments | Low | May change meaning |
| `F_STRING_CONVERSION` | String to f-string | Low | Python 3.6+ only |
| `TYPE_HINT_MISSING` | Missing type hints | Low | May need context |

### Never Automatic (Always Manual)

| Issue Type | Reason |
|------------|--------|
| `HARDCODED_SECRET` | Security-critical, needs human review |
| `SQL_INJECTION_RISK` | Security-critical, complex fixes |
| `SECURITY_VULNERABILITY` | Security-critical, varied remediation |
| `DEPRECATED_API` | May require significant refactoring |

## Per-Language Support

### Python

**Detection Tools:**
- `ruff` - Fast linting with auto-fix support
- `black` - Opinionated formatting
- `isort` - Import sorting
- `autoflake` - Unused import removal

**Fixable Issues:**
```python
# Before
import os
import json  # F401: unused import
import sys

def hello():   # Trailing whitespace
    print( "hello" )  # E201, E202: whitespace

# After
import os
import sys

def hello():
    print("hello")
```

**Configuration:**
- Respects `pyproject.toml` and `.ruff.toml`
- Default line length: 88 (black standard)
- Compatible with Python 3.8+

### JavaScript/TypeScript

**Detection Tools:**
- `eslint` - Configurable linting with auto-fix
- `prettier` - Code formatting

**Fixable Issues:**
```javascript
// Before
const x = 1  // Missing semicolon
let  y = 2   // Extra space
function hello( ) {  // Whitespace in parens
    console.log("hello")
}

// After
const x = 1;
let y = 2;
function hello() {
    console.log("hello");
}
```

**Configuration:**
- Respects `.eslintrc` and `.prettierrc`
- Requires project-level ESLint configuration

### Rust

**Detection Tools:**
- `rustfmt` - Official Rust formatter
- `clippy` - Linting (detection only, limited auto-fix)

**Fixable Issues:**
```rust
// Before
fn main(){
let x=1;
    println!("Hello");
}

// After
fn main() {
    let x = 1;
    println!("Hello");
}
```

**Configuration:**
- Respects `rustfmt.toml`
- Uses Rust edition from `Cargo.toml`

### Swift

**Detection Tools:**
- `swift-format` - Apple's official formatter

**Fixable Issues:**
```swift
// Before
import Foundation
func hello(){
let x=1
    print("Hello")
}

// After
import Foundation

func hello() {
    let x = 1
    print("Hello")
}
```

## Permission System

### AutoFixPermissions Configuration

```python
AutoFixPermissions(
    project_id="sam_brain",

    # Master switch
    enabled=True,

    # What can be fixed
    allowed_fix_types=[
        "unused_import",
        "trailing_whitespace",
        "missing_newline_eof",
        "unsorted_imports",
        "f_string_conversion",
    ],

    # What is NEVER fixed automatically
    blocked_fix_types=[
        "hardcoded_secret",
        "sql_injection_risk",
        "security_vulnerability",
    ],

    # File controls
    allowed_file_patterns=["*.py", "*.js", "*.ts", "*.rs"],
    blocked_file_patterns=[
        "*.env*",           # Environment files
        "*secret*",         # Anything named secret
        "*credential*",     # Credential files
        "node_modules/*",   # Dependencies
        ".git/*",           # Git internals
        "*.lock",           # Lock files
    ],

    # Limits
    max_fixes_per_file=10,       # Per-file limit per hour
    max_fixes_per_hour=50,       # Project-wide limit
    require_review_threshold=5,  # Require review if >5 fixes

    # Quality controls
    min_confidence=0.85,         # 85% confidence minimum
    dry_run=False,               # Set True to detect only
    auto_commit=False,           # Don't auto-commit
)
```

### Enabling/Disabling Auto-Fix

**Per Project:**
```bash
# Enable for a project
python auto_fix_control.py enable sam_brain

# Disable for a project
python auto_fix_control.py disable sam_brain

# Check current status
python auto_fix_control.py permissions sam_brain
```

**Via API:**
```python
from auto_fix_control import api_autofix_permissions_update

# Enable
api_autofix_permissions_update("sam_brain", {"enabled": True})

# Disable
api_autofix_permissions_update("sam_brain", {"enabled": False})

# Change limits
api_autofix_permissions_update("sam_brain", {
    "max_fixes_per_hour": 100,
    "min_confidence": 0.90
})
```

### File Pattern Restrictions

**Always Blocked (cannot be overridden):**
- `.env`, `.env.local`, `.env.production`
- Files containing "secret", "credential", "password" in name
- `.git/` directory contents
- `node_modules/`, `__pycache__/`, `venv/`
- Lock files (`*.lock`, `package-lock.json`, etc.)

**Default Allowed:**
- `*.py` - Python
- `*.js`, `*.jsx` - JavaScript
- `*.ts`, `*.tsx` - TypeScript
- `*.rs` - Rust
- `*.swift` - Swift

## Rate Limiting

### How It Works

Rate limiting prevents SAM from making too many changes too quickly:

```
Project Limit: 50 fixes/hour
File Limit: 10 fixes/file/hour
```

Rate limits reset at the top of each hour.

### Checking Rate Limit Status

```bash
python auto_fix_control.py status sam_brain
```

Output:
```json
{
    "project_id": "sam_brain",
    "rate_limit": {
        "fixes_this_hour": 12,
        "limit": 50,
        "remaining": 38,
        "can_fix": true,
        "resets_at": "2026-01-25T15:00:00"
    }
}
```

### When Rate Limited

When rate limit is exceeded:
1. New fix requests are rejected
2. Issues are queued for next window
3. Notification sent (if proactive_notifier enabled)
4. Manual override available for urgent fixes

## User Guide

### Quick Start

1. **Check available tools:**
   ```bash
   python auto_fix.py tools
   ```

2. **Detect issues in a file:**
   ```bash
   python auto_fix.py detect path/to/file.py
   ```

3. **Preview what would be fixed:**
   ```bash
   python auto_fix.py dry-run path/to/file.py
   ```

4. **Fix issues:**
   ```bash
   python auto_fix.py fix path/to/file.py
   ```

### Detecting Issues

**Single File:**
```python
from auto_fix import detect_issues

issues = detect_issues("/path/to/file.py")
for issue in issues:
    print(f"{issue.file_path}:{issue.line_number}")
    print(f"  Type: {issue.issue_type.name}")
    print(f"  {issue.description}")
    print(f"  Fixable: {issue.auto_fixable}")
```

**Entire Project:**
```python
from auto_fix import IssueDetector

detector = IssueDetector(verbose=True)
issues = detector.detect_project_issues("/path/to/project")
```

### Fixing Issues

**Fix All in File:**
```python
from auto_fix import fix_file

results = fix_file("/path/to/file.py", create_backups=True)
for result in results:
    if result.success:
        print(f"Fixed: {result.changes_made}")
    else:
        print(f"Failed: {result.error}")
```

**Fix Single Issue:**
```python
from auto_fix import AutoFixer

fixer = AutoFixer(create_backups=True)
result = fixer.fix_issue(detected_issue)
```

**Fix with Controller (Recommended):**
```python
from auto_fix_control import get_auto_fix_controller

controller = get_auto_fix_controller()

# Check if fix is allowed
can_fix, reason = controller.can_auto_fix("sam_brain", issue)
if can_fix:
    result = apply_fix(issue)  # Your fix logic
    controller.record_fix("sam_brain", issue, result)
else:
    print(f"Cannot fix: {reason}")
```

### Reviewing Pending Fixes

```bash
# View pending issues across all projects
python auto_fix_control.py pending

# View pending for specific project
python auto_fix_control.py pending sam_brain
```

### Reverting a Fix

If a fix causes problems:

1. **Find the backup:**
   ```bash
   ls ~/.sam/.auto_fix_backups/
   ```

2. **Restore from backup:**
   ```bash
   cp ~/.sam/.auto_fix_backups/file_YYYYMMDD_HHMMSS_hash.py /path/to/file.py
   ```

3. **Record the revert:**
   ```python
   from auto_fix_control import get_auto_fix_controller

   controller = get_auto_fix_controller()
   controller.tracker.track_revert("sam_brain", issue, "Fix broke tests")
   ```

## API Reference

### REST API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/autofix/permissions/{project_id}` | GET | Get project permissions |
| `/api/autofix/permissions/{project_id}` | PUT | Update project permissions |
| `/api/autofix/stats/{project_id}` | GET | Get fix statistics |
| `/api/autofix/run/{project_id}` | POST | Trigger auto-fix scan |
| `/api/autofix/pending` | GET | Get pending issues |
| `/api/autofix/history?file_path=...` | GET | Get file fix history |

### Python API

```python
# Core Functions
from auto_fix import (
    detect_issues,      # Detect issues in file/project
    fix_file,           # Fix all issues in file
    fix_project,        # Fix all issues in project
    get_stats,          # Get execution statistics
)

# Control Functions
from auto_fix_control import (
    get_auto_fix_controller,    # Get controller singleton
    api_autofix_permissions_get,
    api_autofix_permissions_update,
    api_autofix_stats,
    api_autofix_run,
    api_autofix_pending,
    api_autofix_history,
)
```

### CLI Reference

```bash
# Detection
python auto_fix.py detect <path>        # Detect issues
python auto_fix.py dry-run <path>       # Preview fixes

# Fixing
python auto_fix.py fix <path>           # Apply fixes
python auto_fix.py fix <path> --no-backup  # Fix without backup

# Status
python auto_fix.py tools                # Show available tools
python auto_fix.py stats                # Show execution stats

# Control
python auto_fix_control.py status <project>      # Project status
python auto_fix_control.py permissions <project> # Show permissions
python auto_fix_control.py enable <project>      # Enable auto-fix
python auto_fix_control.py disable <project>     # Disable auto-fix
python auto_fix_control.py pending [project]     # Show pending
python auto_fix_control.py history <file_path>   # File history
python auto_fix_control.py run <project> [--dry-run]  # Trigger scan
python auto_fix_control.py cleanup [days]        # Clean old data
```

## Best Practices

### Do's

1. **Always create backups** - Use `create_backups=True`
2. **Start with dry-run** - Preview before applying
3. **Review statistics** - Monitor success rates
4. **Set appropriate confidence** - 0.85 is a good default
5. **Use project-specific permissions** - Different projects have different needs
6. **Run tests after fixes** - Verify fixes don't break anything

### Don'ts

1. **Don't disable backups** - Recovery is essential
2. **Don't set confidence too low** - Leads to bad fixes
3. **Don't override security blocks** - They exist for a reason
4. **Don't auto-commit without review** - Keep auto_commit=False
5. **Don't fix in production directly** - Use staging/development

### Recommended Workflow

```
1. Enable dry_run for new project
2. Run detection, review issues
3. Adjust permissions based on findings
4. Enable fixing with conservative limits
5. Monitor statistics for a week
6. Gradually increase limits if success rate >95%
```

## Troubleshooting

### Common Issues

**Issue: No issues detected**
- Check that linting tools are installed (`python auto_fix.py tools`)
- Verify file type is supported (Python, JS/TS, Rust, Swift)
- Check that file exists and is readable

**Issue: Fix not applied**
- Check permissions with `auto_fix_control.py permissions <project>`
- Verify file is not in blocked patterns
- Check rate limit status
- Review confidence threshold

**Issue: Fix broke code**
- Restore from backup (see Reverting section)
- Record the revert for tracking
- Adjust permissions to prevent similar issues

**Issue: Rate limit exceeded**
- Wait for reset (top of next hour)
- Increase `max_fixes_per_hour` if appropriate
- For urgent fixes, use manual override

### Logging

Enable verbose mode for detailed logging:
```python
detector = IssueDetector(verbose=True)
fixer = AutoFixer(verbose=True)
```

View execution history:
```python
from auto_fix import ExecutionHistory

history = ExecutionHistory()
recent = history.get_recent(limit=20)
for entry in recent:
    print(f"{entry['timestamp']}: {entry['status']} - {entry['changes']}")
```

### Getting Help

1. Check this documentation
2. Review execution history for patterns
3. Check tool-specific documentation (ruff, black, etc.)
4. Review test file for expected behavior

## Storage Locations

Following CLAUDE.md storage rules:

| Data | Location | Notes |
|------|----------|-------|
| Database | `/Volumes/David External/sam_memory/auto_fix.db` | Falls back to `~/.sam/` |
| Backups | `~/.sam/.auto_fix_backups/` | Timestamped backups |
| History | In database | Last 1000 entries |
| Logs | Console/verbose mode | Not persisted |

## Version History

- **v1.0.0** (2026-01-25) - Initial release
  - IssueDetector with Python, JS/TS, Rust, Swift support
  - AutoFixer with backup and restore
  - AutoFixController with permissions and rate limiting
  - Full test coverage
  - API and CLI interfaces

## Related Documentation

- [ROADMAP.md](ROADMAP.md) - Development roadmap
- [FEEDBACK_LEARNING.md](FEEDBACK_LEARNING.md) - How SAM learns from feedback
- [MEMORY_SYSTEM.md](MEMORY_SYSTEM.md) - Memory architecture
