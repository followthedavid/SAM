//! warp_core - Rust backend for Warp_Open Electron app
//! 
//! Phase 5: Drop-in replacement for Phase 4 Node.js modules
//! 
//! Modules:
//! - fs_ops: File operations (read, write, patch, run scripts)
//! - cwd_tracker: Directory context tracking with sandboxing
//! - journal_store: Persistent action journal with undo support

pub mod fs_ops;
pub mod cwd_tracker;
pub mod journal_store;
pub mod osc_parser;
pub mod pty;
pub mod session;

#[cfg(feature = "napi")]
pub mod napi_bridge;

// Re-export key types for convenience
pub use fs_ops::{
    ReadFileOpts, WriteFileOpts, WriteFileResult, 
    ApplyDiffOpts, ApplyDiffResult,
    RunScriptOpts, RunScriptResult,
    read_text_file, write_text_file, apply_unified_diff, run_script, make_id
};

pub use cwd_tracker::{CwdTracker, CdResult};

pub use journal_store::{Journal, JournalEntry, UndoResult};

pub use osc_parser::{OSC133Parser, OSC133Type, BlockEvent};

pub use pty::WarpPty;
