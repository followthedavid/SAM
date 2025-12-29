# warp_core API Reference

Complete mapping from Phase 4 Node.js to Phase 5 Rust implementation.

## File Operations (`fs_ops`)

### read_text_file

**JavaScript (Phase 4):**
```javascript
const { readTextFile } = require('./fsOps');
const content = await readTextFile('/path/to/file', { maxBytes: 1024 });
```

**Rust (Phase 5):**
```rust
use warp_core::{read_text_file, ReadFileOpts};

let opts = ReadFileOpts { max_bytes: 1024 };
let content = read_text_file("/path/to/file", opts).await?;
```

**Return Type:**
- JS: `Promise<string>`
- Rust: `Result<String, anyhow::Error>`

---

### write_text_file

**JavaScript (Phase 4):**
```javascript
const { writeTextFile } = require('./fsOps');
const result = await writeTextFile('/path/to/file', 'content', { 
    ensureDir: true, 
    mode: 0o755 
});
// Returns: { ok: true, path: '/path/to/file' }
```

**Rust (Phase 5):**
```rust
use warp_core::{write_text_file, WriteFileOpts, WriteFileResult};

let opts = WriteFileOpts {
    ensure_dir: true,
    mode: Some(0o755),
};
let result: WriteFileResult = write_text_file("/path/to/file", "content", opts).await?;
// result.ok == true
// result.path == "/path/to/file"
```

**Return Type:**
- JS: `Promise<{ ok: boolean, path: string }>`
- Rust: `Result<WriteFileResult, anyhow::Error>`

---

### apply_unified_diff

**JavaScript (Phase 4):**
```javascript
const { applyUnifiedDiff } = require('./fsOps');
const diff = "===REPLACE===\nnew content here";
const result = await applyUnifiedDiff('/path/to/file', diff, { dryRun: false });
// Returns: { applied: true, file: '/path/to/file' }
```

**Rust (Phase 5):**
```rust
use warp_core::{apply_unified_diff, ApplyDiffOpts, ApplyDiffResult};

let diff = "===REPLACE===\nnew content here";
let opts = ApplyDiffOpts { dry_run: false };
let result: ApplyDiffResult = apply_unified_diff("/path/to/file", diff, opts).await?;
// result.applied == true
// result.file == Some("/path/to/file")
```

**Return Type:**
- JS: `Promise<{ applied: boolean, reason?: string, file?: string }>`
- Rust: `Result<ApplyDiffResult, anyhow::Error>`

---

### run_script

**JavaScript (Phase 4):**
```javascript
const { runScript } = require('./fsOps');
const result = await runScript('ls', ['-la', '/tmp'], { 
    cwd: '/home/user',
    timeoutMs: 5000 
});
// Returns: { code: 0, stdout: '...', stderr: '', signal: null }
```

**Rust (Phase 5):**
```rust
use warp_core::{run_script, RunScriptOpts, RunScriptResult};

let opts = RunScriptOpts {
    cwd: Some("/home/user".to_string()),
    timeout_ms: Some(5000),
};
let result: RunScriptResult = run_script("ls", vec!["-la".into(), "/tmp".into()], opts).await?;
// result.code == Some(0)
// result.stdout == "..."
// result.stderr == ""
```

**Return Type:**
- JS: `Promise<{ code: number|null, stdout: string, stderr: string, signal?: string, error?: string }>`
- Rust: `Result<RunScriptResult, anyhow::Error>`

---

### make_id

**JavaScript (Phase 4):**
```javascript
const { makeId } = require('./fsOps');
const id = makeId('action');
// Returns: 'action-550e8400-e29b-41d4-a716-446655440000'
```

**Rust (Phase 5):**
```rust
use warp_core::make_id;

let id = make_id("action");
// Returns: "action-550e8400-e29b-41d4-a716-446655440000"
```

**Return Type:**
- JS: `string`
- Rust: `String`

---

## Directory Tracking (`cwd_tracker`)

### CwdTracker Constructor

**JavaScript (Phase 4):**
```javascript
const CwdTracker = require('./cwdTracker');
const tracker = new CwdTracker({ 
    initial: '/home/user',
    projectRoot: '/home/user/project' 
});
```

**Rust (Phase 5):**
```rust
use warp_core::CwdTracker;
use std::path::PathBuf;

let tracker = CwdTracker::new(
    Some(PathBuf::from("/home/user")),
    Some(PathBuf::from("/home/user/project"))
);
```

---

### getCwd / get_cwd_string

**JavaScript (Phase 4):**
```javascript
const cwd = tracker.getCwd();
// Returns: '/home/user'
```

**Rust (Phase 5):**
```rust
let cwd: String = tracker.get_cwd_string();
// Returns: "/home/user"
```

**Return Type:**
- JS: `string`
- Rust: `String`

---

### cd

**JavaScript (Phase 4):**
```javascript
const result = await tracker.cd('../projects');
// Returns: { ok: true, cwd: '/home/projects' }
// Or: { ok: false, error: 'cd outside project root denied' }
```

**Rust (Phase 5):**
```rust
use warp_core::CdResult;

let result: CdResult = tracker.cd("../projects").await;
// result.ok == true
// result.cwd == Some("/home/projects")
// OR
// result.ok == false
// result.error == Some("cd outside project root denied")
```

**Return Type:**
- JS: `Promise<{ ok: boolean, cwd?: string, error?: string }>`
- Rust: `CdResult` (struct with `ok`, `cwd`, `error` fields)

---

## Journal Store (`journal_store`)

### Journal Constructor

**JavaScript (Phase 4):**
```javascript
const { logAction, getEntries, undoLast } = require('./journalStore');
// Module-level functions, no constructor
```

**Rust (Phase 5):**
```rust
use warp_core::Journal;

let journal = Journal::new();
// Creates instance with default store path
```

---

### logAction / log_action

**JavaScript (Phase 4):**
```javascript
const entry = await logAction({ 
    type: 'file_write',
    summary: 'Updated config',
    payload: { file: 'config.json' }
});
// Returns: { id: 'action-...', timestamp: '2024-...', type: 'file_write', ... }
```

**Rust (Phase 5):**
```rust
use warp_core::{Journal, JournalEntry};
use serde_json::json;

let journal = Journal::new();
let payload = json!({ "file": "config.json" });
let entry: JournalEntry = journal
    .log_action("file_write", "Updated config", Some(payload))
    .await?;
// entry.id == "action-..."
// entry.entry_type == "file_write"
```

**Return Type:**
- JS: `Promise<{ id: string, timestamp: string, type: string, summary: string, payload: object }>`
- Rust: `Result<JournalEntry, anyhow::Error>`

---

### getEntries / get_entries

**JavaScript (Phase 4):**
```javascript
const entries = await getEntries({ offset: 0, limit: 10 });
// Returns: [{ id: 'action-...', ... }, ...]
```

**Rust (Phase 5):**
```rust
use warp_core::Journal;

let journal = Journal::new();
let entries: Vec<JournalEntry> = journal.get_entries(0, 10).await?;
```

**Return Type:**
- JS: `Promise<Array<JournalEntry>>`
- Rust: `Result<Vec<JournalEntry>, anyhow::Error>`

---

### undoLast / undo_last

**JavaScript (Phase 4):**
```javascript
const result = await undoLast();
// Returns: { ok: true, undone: { id: 'action-...', ... } }
// Or: { ok: false, error: 'no-actions' }
```

**Rust (Phase 5):**
```rust
use warp_core::{Journal, UndoResult};

let journal = Journal::new();
let result: UndoResult = journal.undo_last().await;
// result.ok == true
// result.undone == Some(JournalEntry { ... })
// OR
// result.ok == false
// result.error == Some("no-actions")
```

**Return Type:**
- JS: `Promise<{ ok: boolean, undone?: JournalEntry, error?: string }>`
- Rust: `UndoResult` (struct with `ok`, `undone`, `error` fields)

---

## Type Definitions

### Structs and Options

#### ReadFileOpts

```rust
pub struct ReadFileOpts {
    pub max_bytes: usize,  // Default: 64 * 1024
}
```

#### WriteFileOpts

```rust
pub struct WriteFileOpts {
    pub ensure_dir: bool,     // Default: true
    pub mode: Option<u32>,    // Unix permissions (e.g., 0o755)
}
```

#### WriteFileResult

```rust
pub struct WriteFileResult {
    pub ok: bool,
    pub path: String,
}
```

#### ApplyDiffOpts

```rust
pub struct ApplyDiffOpts {
    pub dry_run: bool,  // Default: false
}
```

#### ApplyDiffResult

```rust
pub struct ApplyDiffResult {
    pub applied: bool,
    pub reason: Option<String>,
    pub file: Option<String>,
}
```

#### RunScriptOpts

```rust
pub struct RunScriptOpts {
    pub cwd: Option<String>,
    pub timeout_ms: Option<u64>,  // Default: 60_000
}
```

#### RunScriptResult

```rust
pub struct RunScriptResult {
    pub code: Option<i32>,
    pub signal: Option<String>,
    pub stdout: String,
    pub stderr: String,
    pub error: Option<String>,
}
```

#### CdResult

```rust
pub struct CdResult {
    pub ok: bool,
    pub cwd: Option<String>,
    pub error: Option<String>,
}
```

#### JournalEntry

```rust
pub struct JournalEntry {
    pub id: String,
    pub timestamp: DateTime<Utc>,  // ISO 8601
    pub entry_type: String,
    pub summary: String,
    pub payload: serde_json::Value,
}
```

#### UndoResult

```rust
pub struct UndoResult {
    pub ok: bool,
    pub undone: Option<JournalEntry>,
    pub error: Option<String>,
}
```

---

## Error Handling

### JavaScript (Phase 4)

```javascript
try {
    const content = await readTextFile('/path/to/file');
} catch (err) {
    console.error('Error:', err.message);
}
```

### Rust (Phase 5)

```rust
use anyhow::Result;

match read_text_file("/path/to/file", ReadFileOpts::default()).await {
    Ok(content) => println!("Content: {}", content),
    Err(e) => eprintln!("Error: {:?}", e),
}

// Or with ? operator:
async fn example() -> Result<()> {
    let content = read_text_file("/path/to/file", ReadFileOpts::default()).await?;
    Ok(())
}
```

---

## Constants and Defaults

| Constant | JS | Rust |
|----------|----|----|
| Max file size | 64KB | 64KB |
| Script timeout | 60s | 60s |
| Journal path | `~/.warp_open/warp_history.json` | `~/.warp_open/warp_history.json` |
| Ensure parent dir | `true` | `true` |

---

## Migration Checklist

- [ ] Replace `require('./fsOps')` with `use warp_core::fs_ops`
- [ ] Replace `require('./cwdTracker')` with `use warp_core::CwdTracker`
- [ ] Replace `require('./journalStore')` with `use warp_core::Journal`
- [ ] Convert promises to `.await?` calls
- [ ] Convert JS objects to Rust structs
- [ ] Handle `Result<T, E>` return types
- [ ] Update error handling from `try/catch` to `match` or `?`
- [ ] Convert JS `null` to Rust `None`/`Option<T>`
- [ ] Update imports in IPC handlers

---

## See Also

- [README.md](./README.md) - Architecture and integration
- [PHASE5_SUMMARY.md](./PHASE5_SUMMARY.md) - Complete overview
- [QUICKSTART.md](./QUICKSTART.md) - Getting started guide
- [examples/napi_bridge.rs](./examples/napi_bridge.rs) - Node.js integration
