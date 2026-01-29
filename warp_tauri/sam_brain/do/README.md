# do/ - Execution

## What This Does
Safely executes commands and actions. This is how SAM affects the real world.

## Why It Exists
SAM needs to run commands, modify files, and take actions - but SAFELY.
This package provides classification, sandboxing, and approval workflows.

## When To Use
- Running any shell command
- Classifying command safety
- Getting user approval for risky actions
- Auditing what SAM has done

## How To Use
```python
from sam.do import run
result = run.execute("ls -la")

from sam.do import classify
risk = classify.assess("rm -rf /")
# Returns: {'safe': False, 'risk': 'CRITICAL', 'reason': 'Recursive delete'}

from sam.do import approve
if not classify.is_safe(cmd):
    approved = approve.request(cmd, reason="Needs to delete old logs")
    if approved:
        run.execute(cmd)
```

## Key Files
- `run.py` - Safe command execution with sandboxing
- `classify.py` - Risk classification for commands
- `propose.py` - Suggest commands for user approval
- `approve.py` - Approval queue and workflow
- `history.py` - Audit trail of all executed commands
- `fix.py` - Auto-fix common errors

## Safety Levels
| Level | Examples | Action |
|-------|----------|--------|
| SAFE | ls, pwd, cat | Execute immediately |
| MODERATE | git commit, npm install | Log and execute |
| RISKY | pip install, chmod | Require approval |
| DANGEROUS | rm -rf, sudo | Block or require explicit approval |

## Dependencies
- **Requires:** Nothing (leaf node)
- **Required by:** core/ (for action execution)

## What Was Here Before
This consolidates:
- `execution/safe_executor.py` (933 lines)
- `execution/command_classifier.py` (986 lines)
- `execution/command_proposer.py` (1,344 lines)
- `execution/auto_fix.py` (1,851 lines)
- `approval_queue.py` (1,015 lines)
