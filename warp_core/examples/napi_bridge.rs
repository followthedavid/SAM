// Example: napi-rs bridge for warp_core
// This shows how to expose Rust functions to Node.js
// 
// To use this:
// 1. Add to Cargo.toml:
//    [dependencies]
//    napi = "2"
//    napi-derive = "2"
//    
//    [lib]
//    crate-type = ["cdylib"]
//
// 2. Build with: napi build --platform --release
// 3. Import in Node: const warpCore = require('./warp_core.node');

#[cfg(feature = "napi")]
use napi::bindgen_prelude::*;
#[cfg(feature = "napi")]
use napi_derive::napi;

use warp_core::*;
use std::path::PathBuf;

#[cfg(feature = "napi")]
#[napi(object)]
pub struct ReadFileOptions {
    pub max_bytes: Option<u32>,
}

#[cfg(feature = "napi")]
#[napi(object)]
pub struct WriteFileOptions {
    pub ensure_dir: Option<bool>,
    pub mode: Option<u32>,
}

#[cfg(feature = "napi")]
#[napi(object)]
pub struct WriteFileResponse {
    pub ok: bool,
    pub path: String,
}

#[cfg(feature = "napi")]
#[napi(object)]
pub struct CdResponse {
    pub ok: bool,
    pub cwd: Option<String>,
    pub error: Option<String>,
}

#[cfg(feature = "napi")]
#[napi(object)]
pub struct JournalEntryJs {
    pub id: String,
    pub timestamp: String,
    pub entry_type: String,
    pub summary: String,
    pub payload: String, // JSON string
}

/// Read a text file with optional max size
#[cfg(feature = "napi")]
#[napi]
pub async fn read_file(path: String, options: Option<ReadFileOptions>) -> Result<String> {
    let opts = ReadFileOpts {
        max_bytes: options
            .and_then(|o| o.max_bytes)
            .unwrap_or(64 * 1024) as usize,
    };

    read_text_file(path, opts)
        .await
        .map_err(|e| Error::from_reason(e.to_string()))
}

/// Write a text file
#[cfg(feature = "napi")]
#[napi]
pub async fn write_file(
    path: String,
    content: String,
    options: Option<WriteFileOptions>,
) -> Result<WriteFileResponse> {
    let opts = WriteFileOpts {
        ensure_dir: options.as_ref().and_then(|o| o.ensure_dir).unwrap_or(true),
        mode: options.and_then(|o| o.mode),
    };

    let result = write_text_file(path, &content, opts)
        .await
        .map_err(|e| Error::from_reason(e.to_string()))?;

    Ok(WriteFileResponse {
        ok: result.ok,
        path: result.path,
    })
}

/// Apply a unified diff to a file
#[cfg(feature = "napi")]
#[napi]
pub async fn apply_diff(path: String, diff: String, dry_run: Option<bool>) -> Result<bool> {
    let opts = ApplyDiffOpts {
        dry_run: dry_run.unwrap_or(false),
    };

    let result = apply_unified_diff(path, &diff, opts)
        .await
        .map_err(|e| Error::from_reason(e.to_string()))?;

    Ok(result.applied)
}

/// Run a shell script/command
#[cfg(feature = "napi")]
#[napi]
pub async fn run_script_cmd(
    command: String,
    args: Vec<String>,
    cwd: Option<String>,
    timeout_ms: Option<u32>,
) -> Result<String> {
    let opts = RunScriptOpts {
        cwd,
        timeout_ms: timeout_ms.map(|t| t as u64),
    };

    let result = run_script(&command, args, opts)
        .await
        .map_err(|e| Error::from_reason(e.to_string()))?;

    // Return JSON string with result
    serde_json::to_string(&result).map_err(|e| Error::from_reason(e.to_string()))
}

/// Change directory
#[cfg(feature = "napi")]
#[napi]
pub async fn change_directory(tracker_id: String, path: String) -> Result<CdResponse> {
    // In a real implementation, you'd maintain a map of tracker instances
    // For this example, we'll create a new one each time
    let mut tracker = CwdTracker::new(None, None);
    let result = tracker.cd(path).await;

    Ok(CdResponse {
        ok: result.ok,
        cwd: result.cwd,
        error: result.error,
    })
}

/// Log an action to the journal
#[cfg(feature = "napi")]
#[napi]
pub async fn log_action(
    entry_type: String,
    summary: String,
    payload: Option<String>,
) -> Result<String> {
    let journal = Journal::new();
    let payload_json = payload
        .map(|p| serde_json::from_str(&p).unwrap_or(serde_json::Value::Null))
        .unwrap_or(serde_json::Value::Null);

    let entry = journal
        .log_action(entry_type, summary, Some(payload_json))
        .await
        .map_err(|e| Error::from_reason(e.to_string()))?;

    serde_json::to_string(&entry).map_err(|e| Error::from_reason(e.to_string()))
}

/// Get journal entries
#[cfg(feature = "napi")]
#[napi]
pub async fn get_journal_entries(offset: Option<u32>, limit: Option<u32>) -> Result<String> {
    let journal = Journal::new();
    let entries = journal
        .get_entries(offset.unwrap_or(0) as usize, limit.unwrap_or(100) as usize)
        .await
        .map_err(|e| Error::from_reason(e.to_string()))?;

    serde_json::to_string(&entries).map_err(|e| Error::from_reason(e.to_string()))
}

/// Undo the last journal entry
#[cfg(feature = "napi")]
#[napi]
pub async fn undo_last_action() -> Result<String> {
    let journal = Journal::new();
    let result = journal.undo_last().await;

    serde_json::to_string(&result).map_err(|e| Error::from_reason(e.to_string()))
}

/// Generate a unique ID
#[cfg(feature = "napi")]
#[napi]
pub fn generate_id(prefix: String) -> String {
    make_id(&prefix)
}

// Example usage in Node.js:
//
// const warpCore = require('./warp_core.node');
//
// // Read file
// const content = await warpCore.readFile('/path/to/file', { maxBytes: 1024 });
//
// // Write file
// await warpCore.writeFile('/path/to/new', 'content', { ensureDir: true });
//
// // Log action
// await warpCore.logAction('file_write', 'Wrote config', JSON.stringify({ file: 'config.json' }));
//
// // Get journal
// const entries = JSON.parse(await warpCore.getJournalEntries(0, 10));
//
// // Undo last
// await warpCore.undoLastAction();
