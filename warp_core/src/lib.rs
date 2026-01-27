//! warp_core - Rust backend for Warp_Open / SAM Terminal
//!
//! Phase 6: Full Warp Feature Parity
//!
//! Modules:
//! - fs_ops: File operations (read, write, patch, run scripts)
//! - cwd_tracker: Directory context tracking with sandboxing
//! - journal_store: Persistent action journal with undo support
//! - osc_parser: OSC 133 block boundary detection
//! - pty: Pseudoterminal management
//! - session: Session persistence and scrollback
//! - secret_redactor: Automatic secret detection and masking
//! - workflows: Parameterized YAML workflow execution
//! - completions: Command completion specifications
//! - shell_hooks: Shell integration (precmd/preexec)
//! - block_sharing: Share terminal output blocks via links
//! - autocorrect: Command typo correction suggestions
//! - launch_configs: Terminal launch configurations

pub mod fs_ops;
pub mod cwd_tracker;
pub mod journal_store;
pub mod osc_parser;
pub mod pty;
pub mod session;
pub mod secret_redactor;
pub mod workflows;
pub mod completions;
pub mod shell_hooks;
pub mod block_sharing;
pub mod autocorrect;
pub mod launch_configs;

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

pub use secret_redactor::{SecretRedactor, SecretPattern, SecretCategory, RedactionResult};

pub use workflows::{Workflow, WorkflowArg, WorkflowEngine};

pub use completions::{CompletionSpec, CompletionEngine, Suggestion};

pub use shell_hooks::{ShellHooks, ShellType};

pub use block_sharing::{BlockSharing, SharedBlock, ShareAccess, ExportFormat};

pub use autocorrect::{Autocorrect, Suggestion as AutocorrectSuggestion, SuggestionReason};

pub use launch_configs::{LaunchConfig, LaunchConfigManager, LaunchConfigBuilder};
