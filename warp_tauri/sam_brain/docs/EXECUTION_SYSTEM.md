# SAM Execution System

**Version:** 1.0.0
**Updated:** 2026-01-25
**Phase:** 4.1 (Supervised Code Execution)

## Overview

The SAM Execution System provides a secure framework for SAM to propose and execute commands autonomously while maintaining human oversight. It implements a defense-in-depth approach with multiple layers of validation, approval workflows, and rollback capabilities.

### Security Philosophy

1. **Defense in Depth**: Multiple layers of validation (classification, permissions, sandboxing)
2. **Fail Secure**: Deny by default, allow by exception
3. **Auditability**: Complete audit trail of all actions and decisions
4. **Reversibility**: Automatic backups enable rollback of changes
5. **Human Oversight**: Dangerous operations require explicit approval

### Architecture Diagram

```
+------------------+     +-------------------+     +------------------+
|   SAM Brain      |---->| Command Classifier|---->| Risk Assessment  |
|   (Proposal)     |     | (command_classifier.py)|  (SAFE/MOD/DANG)  |
+------------------+     +-------------------+     +------------------+
                                                           |
                                                           v
+------------------+     +-------------------+     +------------------+
|   API Response   |<----| Approval Queue    |<----| Permission Check |
|   (Execute/Wait) |     | (approval_queue.py)    | (project_permissions.py)
+------------------+     +-------------------+     +------------------+
         |                       |
         | (if approved)         | (status tracking)
         v                       v
+------------------+     +-------------------+     +------------------+
|   Safe Executor  |---->| Execution History |---->| Rollback Manager |
| (safe_executor.py)|    | (execution_history.py) | (backup/restore) |
+------------------+     +-------------------+     +------------------+
```

---

## Components

### 1. ApprovalQueue (`approval_queue.py`)

The ApprovalQueue manages the lifecycle of proposed actions, from submission through approval/rejection to execution.

**Key Features:**
- SQLite-backed persistent storage
- Thread-safe operations
- Automatic expiration of stale requests
- Full audit trail
- JSON API support

**Storage Location:** `~/.sam/approval_queue.db`

#### Data Model

```python
@dataclass
class ApprovalItem:
    id: str                    # UUID
    command: str               # The proposed command
    command_type: CommandType  # SHELL, FILE_EDIT, FILE_CREATE, FILE_DELETE, GIT
    risk_level: RiskLevel      # SAFE, MODERATE, DANGEROUS, BLOCKED
    reasoning: str             # Why SAM wants to execute this
    created_at: datetime       # When proposed
    expires_at: datetime       # Auto-reject deadline (default: 24h)
    status: ApprovalStatus     # PENDING, APPROVED, REJECTED, EXECUTED, EXPIRED, FAILED
    project_id: str            # Optional project context
    rollback_info: Dict        # Information for rollback
```

#### Usage

```python
from approval_queue import ApprovalQueue, CommandType

queue = ApprovalQueue()

# Add a new approval request
item_id = queue.add(
    command="rm -rf /tmp/build",
    command_type=CommandType.SHELL,
    reasoning="Cleaning up temporary build directory",
    project_id="sam_brain"
)

# List pending items
pending = queue.list_pending()

# Approve or reject
queue.approve(item_id)
queue.reject(item_id, reason="Too risky")

# Mark execution result
queue.mark_executed(item_id, result="Success")
queue.mark_failed(item_id, error="Permission denied")
```

---

### 2. CommandClassifier (`command_classifier.py`)

The CommandClassifier analyzes shell commands to determine their risk level and type.

**Risk Levels:**
- **SAFE**: Can auto-execute without approval (read-only, non-destructive)
- **MODERATE**: Needs approval but not blocked (file writes, commits)
- **DANGEROUS**: Requires extra approval with warnings (destructive operations)
- **BLOCKED**: Never allowed (system destruction, remote code execution)

#### Safe Whitelist Categories

```
lint_format:   black, ruff, prettier, eslint, rustfmt
test:          pytest, cargo test, npm test, jest
build:         cargo build, npm run build, make
info:          git status, ls, cat, pwd, env
package_info:  pip show, npm list, brew list
```

#### Dangerous Patterns Detected

- Recursive deletion (`rm -rf`)
- Privilege escalation (`sudo`, `su`)
- Remote code execution (`curl | bash`)
- Destructive git operations (`push --force`, `reset --hard`)
- Database destruction (`DROP TABLE`, `TRUNCATE`)
- System directory writes (`> /etc/`, `> /usr/`)
- Fork bombs, disk formatting

#### Usage

```python
from command_classifier import CommandClassifier, RiskLevel

classifier = CommandClassifier()

# Basic classification
cmd_type, risk_level = classifier.classify("rm -rf /tmp/build")
# Returns: (CommandType.FILE_DELETE, RiskLevel.DANGEROUS)

# Detailed analysis
result = classifier.classify_detailed("git push --force origin main")
print(result.dangers)        # ["Force push - can overwrite remote history"]
print(result.reasoning)      # "Dangerous pattern: Force push..."
print(result.has_chaining)   # False
print(result.env_vars_used)  # []

# Quick check
if classifier.is_safe("pytest tests/"):
    # Can auto-execute
    pass
```

---

### 3. SafeExecutor (`safe_executor.py`)

The SafeExecutor provides sandboxed command execution with resource limits, path validation, and environment sanitization.

**Safety Features:**
- Resource limits (memory, CPU time, execution timeout)
- Path validation and whitelisting
- Environment variable filtering (removes API keys, secrets)
- Automatic backup creation for file modifications
- Dry-run mode for previewing actions
- Process group isolation for clean termination

#### Configuration

```python
# Default limits
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MEMORY_LIMIT_MB = 512
DEFAULT_CPU_TIME_LIMIT = 60

# Allowed project directories
ALLOWED_PROJECT_ROOTS = [
    Path.home() / "ReverseLab",
    Path.home() / "Projects",
    Path("/Volumes/David External"),
    Path("/Volumes/Plex/SSOT"),
    Path("/tmp"),
]

# Sensitive environment variables (removed from subprocess)
SENSITIVE_ENV_VARS = {
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GITHUB_TOKEN",
    "AWS_SECRET_ACCESS_KEY", "DATABASE_URL", "SECRET_KEY",
    # ... and more
}
```

#### Usage

```python
from safe_executor import SafeExecutor, create_safe_context, ExecutionStatus

executor = SafeExecutor()

# Create execution context
context = create_safe_context(
    project_id="sam_brain",
    working_directory="/Users/david/ReverseLab/SAM/warp_tauri/sam_brain",
    dry_run=False
)

# Execute command
result = executor.execute(
    command="pytest tests/",
    working_dir="/Users/david/ReverseLab/SAM/warp_tauri/sam_brain",
    timeout=60,
    context=context
)

if result.status == ExecutionStatus.SUCCESS:
    print(result.stdout)
elif result.status == ExecutionStatus.BLOCKED:
    print(f"Blocked: {result.blocked_reason}")
elif result.status == ExecutionStatus.TIMEOUT:
    print("Command timed out")
```

---

### 4. ProjectPermissions (`project_permissions.py`)

Per-project permission configuration controlling what SAM can execute.

#### Permission Presets

| Preset | Safe Auto-Execute | Moderate w/Approval | Block Dangerous | Use Case |
|--------|-------------------|---------------------|-----------------|----------|
| STRICT | No | Yes | Yes | Production, sensitive projects |
| NORMAL | Yes | Yes | Yes | Standard development |
| PERMISSIVE | Yes | Yes | No | Trusted projects |
| DEVELOPMENT | Yes | Yes | No (+ git ops) | Active development |

#### Configuration Options

```python
@dataclass
class ProjectPermissions:
    project_id: str
    allow_safe_auto_execute: bool = True      # Run safe commands without approval
    allow_moderate_with_approval: bool = True  # Allow moderate with approval
    block_dangerous: bool = True               # Always block dangerous
    allowed_commands: List[str] = []           # Extra whitelisted commands
    blocked_commands: List[str] = []           # Extra blocked commands
    allowed_paths: List[str] = []              # Paths SAM can modify
    blocked_paths: List[str] = []              # Paths SAM cannot touch
    max_timeout: int = 120                     # Max execution time
    require_dry_run_first: bool = False        # Preview before execute
    auto_rollback_on_error: bool = True        # Rollback on failure
    notification_level: NotificationLevel      # When to notify
```

#### Usage

```python
from project_permissions import PermissionManager, PermissionPreset

manager = PermissionManager()

# Check if command is allowed
can_exec, reason = manager.can_execute("sam_brain", "git push origin main")
print(f"Allowed: {can_exec}, Reason: {reason}")

# Apply a preset
manager.apply_preset("sam_brain", PermissionPreset.DEVELOPMENT)

# Custom configuration
perms = manager.get_permissions("sam_brain")
perms.allowed_commands.append("docker build")
manager.set_permissions("sam_brain", perms)

# Check path access
can_modify, reason = manager.can_modify_path(
    "sam_brain",
    "/Users/david/ReverseLab/SAM/warp_tauri/sam_brain/test.py"
)
```

---

### 5. ExecutionHistory (`execution_history.py`)

Provides checkpoint creation, command logging, and rollback capabilities.

#### Components

1. **RollbackManager**: Creates checkpoints and restores files
2. **ExecutionLogger**: Tracks all command executions with statistics

#### Checkpoint Flow

```
1. Create Checkpoint    ->  2. Backup Files        ->  3. Execute Commands
   (named save point)       (gzip compressed)          (logged to checkpoint)
         |                        |                          |
         v                        v                          v
   checkpoint_id            backup/                    If error: Rollback
   created                  {checkpoint_id}/           Restore all files
```

#### Usage

```python
from execution_history import RollbackManager, ExecutionLogger, ExecutionResult

# Checkpoint management
manager = RollbackManager()

# Create checkpoint before risky changes
checkpoint_id = manager.create_checkpoint(
    project_id="sam_brain",
    description="Before major refactor"
)

# Backup files that will be modified
manager.add_file_backup(checkpoint_id, "/path/to/important_file.py")
manager.add_file_backup(checkpoint_id, "/path/to/config.json")

# Log commands as they execute
result = ExecutionResult(success=True, output="Changes applied")
manager.add_command_log(checkpoint_id, "git commit -m 'refactor'", result)

# If something goes wrong
rollback_result = manager.rollback(checkpoint_id)
if rollback_result.success:
    print(f"Restored {len(rollback_result.files_restored)} files")

# Execution logging
logger = ExecutionLogger()

# Log an execution
exec_id = logger.log_execution(
    approval_id="abc123",
    command="git push origin main",
    result=result,
    duration_ms=1500,
    project_id="sam_brain"
)

# Get statistics
stats = logger.get_execution_stats()
print(f"Success rate: {stats.successful / stats.total_executions * 100}%")
```

---

## Risk Levels Explained

### SAFE

**Definition:** Read-only operations with no side effects.

**Examples:**
- `ls -la`, `pwd`, `cat file.txt`
- `git status`, `git log`, `git diff`
- `pip list`, `npm list`
- `pytest tests/` (testing)
- `black --check .` (lint check only)

**Behavior:** Can auto-execute if `allow_safe_auto_execute=True`

### MODERATE

**Definition:** May modify files but changes are recoverable.

**Examples:**
- `git add .`, `git commit -m "message"`
- `pip install requests`
- `mkdir new_dir`, `touch file.txt`
- `cp source.txt dest.txt`
- `black src/` (formatting with changes)

**Behavior:** Requires approval unless `allow_moderate_with_approval=False`

### DANGEROUS

**Definition:** Destructive operations that are hard to reverse.

**Examples:**
- `rm -rf directory/`
- `git push --force`
- `git reset --hard HEAD~5`
- `git clean -fd`
- `sudo anything`
- `chmod 777 file`

**Behavior:** Blocked by default, requires explicit approval with `block_dangerous=False`

### BLOCKED

**Definition:** Never allowed under any circumstances.

**Examples:**
- `rm -rf /` (root deletion)
- `curl | bash` (remote code execution)
- `DROP DATABASE production`
- `dd if=/dev/zero of=/dev/sda`
- Fork bombs
- Writing to system directories

**Behavior:** Always rejected, cannot be overridden by permissions

---

## User Guide

### Reviewing Approvals

#### CLI

```bash
# List pending approvals
python approval_queue.py list

# View specific approval
python approval_queue.py get --id <item-id>

# Approve an item
python approval_queue.py approve --id <item-id>

# Reject with reason
python approval_queue.py reject --id <item-id> --reason "Too risky"

# View history
python approval_queue.py history --limit 50
```

#### API

```python
# GET /api/approval/queue
response = api_approval_queue(project_id="sam_brain")
# Returns: {"pending_count": 3, "items": [...], "stats": {...}}

# POST /api/approval/approve/{item_id}
response = api_approval_approve("abc123")

# POST /api/approval/reject/{item_id}
response = api_approval_reject("abc123", reason="Not safe")
```

### Setting Permissions

#### CLI

```bash
# Show all projects
python project_permissions.py show

# Show specific project
python project_permissions.py show sam_brain

# Apply preset
python project_permissions.py set sam_brain --preset normal

# Allow specific command
python project_permissions.py allow sam_brain --command "docker build"

# Block path
python project_permissions.py block sam_brain --path "~/.ssh"

# Check command
python project_permissions.py check sam_brain "git push origin main"
```

### Managing Rollback

#### CLI

```bash
# List checkpoints
python execution_history.py checkpoint list sam_brain

# View checkpoint details
python execution_history.py checkpoint details <checkpoint-id>

# Rollback to checkpoint
python execution_history.py checkpoint rollback <checkpoint-id>

# Cleanup old checkpoints (older than 7 days)
python execution_history.py checkpoint cleanup --days 7
```

---

## API Reference

### ApprovalQueue Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/approval/queue` | GET | List pending approvals |
| `/api/approval/queue/{project_id}` | GET | List pending for project |
| `/api/approval/approve/{item_id}` | POST | Approve an item |
| `/api/approval/reject/{item_id}` | POST | Reject an item |
| `/api/approval/history` | GET | Get approval history |
| `/api/approval/{item_id}` | GET | Get specific item |
| `/api/approval/stats` | GET | Get queue statistics |

#### Request/Response Formats

**List Pending:**
```json
GET /api/approval/queue

Response:
{
  "success": true,
  "pending_count": 2,
  "items": [
    {
      "id": "abc-123",
      "command": "git push origin main",
      "command_type": "git",
      "risk_level": "moderate",
      "reasoning": "Push changes to remote",
      "created_at": "2026-01-25T10:30:00",
      "expires_at": "2026-01-26T10:30:00",
      "status": "pending"
    }
  ],
  "stats": {
    "total": 50,
    "pending": 2,
    "approval_rate": 0.92
  }
}
```

**Approve:**
```json
POST /api/approval/approve/abc-123

Response:
{
  "success": true,
  "item_id": "abc-123",
  "command": "git push origin main",
  "status": "approved",
  "approved_by": "david"
}
```

### Permission Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/permissions/{project_id}` | GET | Get project permissions |
| `/api/permissions/{project_id}` | PUT | Set project permissions |
| `/api/permissions/defaults` | GET | Get default permissions |
| `/api/permissions/defaults` | PUT | Set default permissions |
| `/api/permissions/{project_id}/check` | POST | Check command permission |
| `/api/permissions/audit` | GET | Get audit log |

### Execution Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/execution/history` | GET | Get execution history |
| `/api/execution/stats` | GET | Get execution statistics |
| `/api/execution/checkpoints/{project_id}` | GET | List checkpoints |
| `/api/execution/checkpoint/{id}` | GET | Get checkpoint details |
| `/api/execution/checkpoint` | POST | Create checkpoint |
| `/api/execution/rollback/{id}` | POST | Rollback to checkpoint |
| `/api/execution/cleanup` | POST | Cleanup old checkpoints |

---

## CLI Reference

### approval_queue.py

```
Commands:
  list              List pending approvals
  add               Add approval request (for testing)
  approve           Approve pending item
  reject            Reject pending item
  history           View approval history
  stats             View queue statistics
  get               Get specific item details
  expire            Expire old items
  clear             Clear old completed items

Options:
  --id              Item UUID
  --cmd             Command to add
  --type            Command type (shell, file_edit, etc.)
  --reason          Reasoning or rejection reason
  --project         Project ID filter
  --limit           Limit for history
  --days            Days for clear operation
  --json            Output as JSON
```

### project_permissions.py

```
Commands:
  show [project_id]        Show permissions
  set <project_id>         Set permission preset
  allow <project_id>       Allow command or path
  block <project_id>       Block command or path
  check <project_id> <cmd> Check if command allowed
  audit [project_id]       Show audit log
  defaults show/set        Manage default permissions

Options:
  --preset          Permission preset (strict/normal/permissive/development)
  --command         Command to allow/block
  --path            Path to allow/block
  --limit           Limit for audit log
```

### execution_history.py

```
Commands:
  checkpoint create <project_id> <description>
  checkpoint list <project_id>
  checkpoint details <checkpoint_id>
  checkpoint rollback <checkpoint_id>
  checkpoint backup <checkpoint_id> <file_path>
  checkpoint cleanup --days N

  executions list [--limit N] [--project ID]
  executions stats
  executions export <start_date> <end_date> [-o file]
```

---

## Security Considerations

### What SAM Cannot Do

1. **System Destruction**: Delete root, format disks, modify system files
2. **Remote Code Execution**: Pipe untrusted content to shell
3. **Privilege Escalation**: Use sudo, su, or doas
4. **Credential Theft**: Access SSH keys, API tokens, or secrets
5. **Process Manipulation**: Kill system processes, fork bomb
6. **Network Attacks**: Open listeners, scan networks
7. **Database Destruction**: DROP DATABASE, TRUNCATE without WHERE

### Audit Procedures

#### Daily Review

1. Check pending approvals: `python approval_queue.py list`
2. Review recent executions: `python execution_history.py executions list --limit 20`
3. Check for anomalies in audit log: `python project_permissions.py audit --limit 50`

#### Weekly Maintenance

1. Clean up old checkpoints: `python execution_history.py checkpoint cleanup --days 7`
2. Clear old approval history: `python approval_queue.py clear --days 30`
3. Export execution log for analysis: `python execution_history.py executions export <dates> -o weekly_report.json`

#### Security Audit Checklist

- [ ] Review blocked commands in logs
- [ ] Check for permission escalation attempts
- [ ] Verify checkpoint backups are being created
- [ ] Confirm sensitive paths are blocked
- [ ] Test rollback functionality
- [ ] Review project permission configurations

---

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SAM_APPROVAL_TIMEOUT` | Default approval timeout (hours) | 24 |
| `SAM_EXECUTION_TIMEOUT` | Default execution timeout (seconds) | 30 |
| `SAM_MEMORY_LIMIT_MB` | Max memory for subprocesses | 512 |
| `SAM_BACKUP_DIR` | Backup storage location | `~/.sam/backups` |
| `SAM_LOG_LEVEL` | Logging verbosity | INFO |

### File Locations

| File | Purpose |
|------|---------|
| `~/.sam/approval_queue.db` | Approval queue database |
| `~/.sam/permissions.db` | Permission settings |
| `~/.sam/execution_history.db` | Execution logs |
| `~/.sam/backups/` | File backups for rollback |
| `~/.sam/execution_log.jsonl` | Detailed execution log |

---

## Troubleshooting

### Common Issues

#### "Command blocked by pattern"

**Cause:** Command matches a dangerous pattern.

**Solution:** Review the command. If it's safe for your use case:
1. Add to `allowed_commands` in project permissions
2. Use a different approach that's less risky
3. If truly needed, manually execute outside SAM

#### "Path not in allowed list"

**Cause:** Working directory or file path is outside allowed roots.

**Solution:**
1. Add path to `ALLOWED_PROJECT_ROOTS` in safe_executor.py
2. Or add to `allowed_paths` in project permissions

#### "Approval expired"

**Cause:** Approval request wasn't reviewed within timeout period.

**Solution:**
1. Increase `timeout_hours` when adding requests
2. Review pending approvals more frequently
3. Set up notifications for pending items

#### "Rollback failed"

**Cause:** Backup file missing or corrupted.

**Solution:**
1. Check `~/.sam/backups/` for backup files
2. Verify checkpoint was created before changes
3. For critical files, maintain separate version control

### Debug Mode

Enable verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Or via environment
export SAM_LOG_LEVEL=DEBUG
```

### Support

For issues with the execution system:
1. Check the audit log for related entries
2. Review the execution log at `~/.sam/execution_log.jsonl`
3. Verify permissions configuration
4. Test with dry-run mode first

---

## Related Documentation

- **SSOT Master Context**: `/Volumes/Plex/SSOT/CLAUDE_READ_FIRST.md`
- **SAM Brain CLAUDE.md**: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/CLAUDE.md`
- **Roadmap**: `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/docs/ROADMAP.md`
