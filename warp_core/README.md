# warp_core - Phase 5 Rust Backend

Drop-in Rust replacement for Warp_Open Phase 4 Node.js backend modules.

## Overview

`warp_core` provides high-performance, type-safe implementations of:

- **fs_ops**: File read/write, unified diff patching, script execution
- **cwd_tracker**: Directory context tracking with sandboxing
- **journal_store**: Persistent JSON action journal with undo support

## Architecture

```
┌──────────────────────────────────────────┐
│         Electron Renderer UI             │
│       (HTML + Vanilla JS / React)        │
└──────────────────┬───────────────────────┘
                   │ window.ai2 API
┌──────────────────▼───────────────────────┐
│         Electron Main Process            │
│    (ai2-main.js IPC bridge)              │
└──────────────────┬───────────────────────┘
                   │
         ┌─────────┴──────────┐
         │                    │
    ┌────▼─────┐      ┌──────▼──────┐
    │ Phase 4  │      │  Phase 5    │
    │ Node.js  │  OR  │   Rust      │
    │ Modules  │      │ warp_core   │
    └──────────┘      └─────────────┘
```

## Module Equivalence

### fs_ops.js → fs_ops.rs

| JS Function | Rust Function | Notes |
|-------------|---------------|-------|
| `readTextFile(path, opts)` | `read_text_file(path, opts)` | Async, truncates large files |
| `writeTextFile(path, content, opts)` | `write_text_file(path, content, opts)` | Creates dirs, optional chmod |
| `applyUnifiedDiff(path, diff, opts)` | `apply_unified_diff(path, diff, opts)` | Supports `===REPLACE===` marker |
| `runScript(cmd, args, opts)` | `run_script(cmd, args, opts)` | Timeout support, captures output |
| `makeId(prefix)` | `make_id(prefix)` | UUID v4 generation |

### cwdTracker.js → cwd_tracker.rs

| JS Class/Method | Rust Type/Method | Notes |
|-----------------|------------------|-------|
| `CwdTracker` | `CwdTracker` | Struct with state |
| `getCwd()` | `get_cwd_string()` | Returns current directory |
| `cd(path)` | `cd(path)` | Async, validates and enforces sandbox |

### journalStore.js → journal_store.rs

| JS Function | Rust Method | Notes |
|-------------|-------------|-------|
| `logAction(opts)` | `journal.log_action(type, summary, payload)` | Thread-safe |
| `getEntries(opts)` | `journal.get_entries(offset, limit)` | Pagination support |
| `undoLast()` | `journal.undo_last()` | Removes last entry |

## Usage

### Building

```bash
cd warp_core
cargo build --release
```

### Testing

```bash
cargo test
```

### Integration Options

#### Option 1: Node.js Native Module (napi-rs)

Use `napi-rs` to expose Rust functions directly to Node.js:

```bash
# Add to Cargo.toml
[dependencies]
napi = "2"
napi-derive = "2"

[lib]
crate-type = ["cdylib"]
```

Then create Node bindings:

```rust
#[napi]
pub async fn read_file(path: String, max_bytes: Option<u32>) -> Result<String> {
    let opts = ReadFileOpts {
        max_bytes: max_bytes.unwrap_or(64 * 1024) as usize,
    };
    warp_core::read_text_file(path, opts)
        .await
        .map_err(|e| napi::Error::from_reason(e.to_string()))
}
```

#### Option 2: Tauri/Wry IPC Bridge

Replace Electron IPC handlers with Tauri commands:

```rust
use tauri::command;
use warp_core::*;

#[command]
async fn read_file(path: String, max_bytes: Option<usize>) -> Result<String, String> {
    let opts = ReadFileOpts {
        max_bytes: max_bytes.unwrap_or(64 * 1024),
    };
    read_text_file(path, opts).await.map_err(|e| e.to_string())
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![
            read_file,
            write_file,
            cd,
            log_action,
            // ... etc
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

#### Option 3: Standalone Service (gRPC/HTTP)

Expose warp_core as a microservice using tonic (gRPC) or axum (HTTP):

```rust
use axum::{Router, Json, extract::State};
use std::sync::Arc;

#[tokio::main]
async fn main() {
    let app = Router::new()
        .route("/read_file", post(read_file_handler))
        .route("/write_file", post(write_file_handler));

    axum::Server::bind(&"127.0.0.1:3030".parse().unwrap())
        .serve(app.into_make_service())
        .await
        .unwrap();
}
```

## Type Safety & Error Handling

All Rust functions return `Result<T, E>` types with detailed error context via `anyhow`:

```rust
// Success
Ok(WriteFileResult { ok: true, path: "/path/to/file" })

// Error with context
Err(anyhow::Error("Failed to write file: /path/to/file: Permission denied"))
```

## Performance Benefits

- **Memory efficiency**: Rust's ownership model prevents leaks
- **Zero-cost abstractions**: No runtime overhead
- **Async runtime**: Tokio provides efficient concurrency
- **Type safety**: Compile-time guarantees vs runtime errors

## Future Enhancements

### Phase 5.1: Enhanced Undo
- Store previous file content in journal payload
- Implement real rollback that restores content
- Add transaction support for multi-file operations

### Phase 5.2: Advanced Context Pack
- Git integration (status, log, blame)
- Syntax tree parsing (tree-sitter)
- Dependency graph analysis
- Real-time file watching

### Phase 5.3: Full Unified Diff Support
- Use `diffy` crate for proper patch application
- Preview diffs before applying
- Support for multi-file patches
- Conflict resolution UI

## License

Same as Warp_Open parent project.

## Testing

All modules include unit tests. Run with:

```bash
cargo test
```

Tests verify:
- File read/write operations
- Directory navigation and sandboxing
- Journal persistence and undo
- Script execution and timeouts

## Dependencies

- `tokio`: Async runtime
- `serde`/`serde_json`: Serialization
- `uuid`: Unique ID generation
- `diffy`: Unified diff support (future)
- `anyhow`: Error handling
- `chrono`: Timestamps

## Development

### Code Structure

```
warp_core/
├── Cargo.toml          # Dependencies and metadata
├── README.md           # This file
└── src/
    ├── lib.rs          # Module exports
    ├── fs_ops.rs       # File operations
    ├── cwd_tracker.rs  # Directory tracking
    └── journal_store.rs # Action journal
```

### Adding New Features

1. Implement in appropriate module with tests
2. Export in `lib.rs`
3. Update this README
4. Run `cargo test` and `cargo clippy`
