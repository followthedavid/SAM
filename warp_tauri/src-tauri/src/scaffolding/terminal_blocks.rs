//! Terminal Blocks - Structured command/output grouping
//!
//! Implements Warp-style blocks that group:
//! - Command input
//! - Command output
//! - Exit code and metadata
//! - Navigation and sharing capabilities

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// BLOCK TYPES
// =============================================================================

/// A terminal block representing a command and its output
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Block {
    /// Unique block ID
    pub id: String,
    /// Block sequence number in session
    pub sequence: u64,
    /// The command that was entered
    pub command: String,
    /// The output produced
    pub output: String,
    /// Exit code (None if still running or signal killed)
    pub exit_code: Option<i32>,
    /// Current working directory when run
    pub cwd: String,
    /// Git branch (if in repo)
    pub git_branch: Option<String>,
    /// When command started
    pub started_at: DateTime<Utc>,
    /// When command completed
    pub completed_at: Option<DateTime<Utc>>,
    /// Duration in milliseconds
    pub duration_ms: Option<u64>,
    /// Block state
    pub state: BlockState,
    /// Environment snapshot (filtered)
    pub env: Option<HashMap<String, String>>,
    /// Shell used
    pub shell: Option<String>,
    /// User who ran command
    pub user: Option<String>,
    /// Hostname
    pub hostname: Option<String>,
    /// Whether output was truncated
    pub truncated: bool,
    /// Tags/labels for organization
    pub tags: Vec<String>,
    /// Whether block is bookmarked
    pub bookmarked: bool,
    /// Whether block is collapsed
    pub collapsed: bool,
    /// Whether block is hidden
    pub hidden: bool,
    /// Annotations/notes
    pub notes: Option<String>,
    /// Sharing info
    pub share_id: Option<String>,
}

/// Block state
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum BlockState {
    /// Command is running
    Running,
    /// Command succeeded (exit 0)
    Success,
    /// Command failed (non-zero exit)
    Failed,
    /// Command was killed by signal
    Killed,
    /// Command timed out
    Timeout,
    /// Unknown/error state
    Unknown,
}

impl BlockState {
    pub fn from_exit_code(code: Option<i32>) -> Self {
        match code {
            Some(0) => BlockState::Success,
            Some(c) if c > 128 => BlockState::Killed, // Signal: 128 + signal_num
            Some(_) => BlockState::Failed,
            None => BlockState::Running,
        }
    }
}

/// Block filter criteria
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct BlockFilter {
    /// Filter by state
    pub states: Option<Vec<BlockState>>,
    /// Filter by command pattern
    pub command_pattern: Option<String>,
    /// Filter by output pattern
    pub output_pattern: Option<String>,
    /// Filter by directory
    pub cwd: Option<String>,
    /// Filter by git branch
    pub git_branch: Option<String>,
    /// Filter by tags
    pub tags: Option<Vec<String>>,
    /// Only bookmarked
    pub bookmarked_only: bool,
    /// Only failures
    pub failures_only: bool,
    /// Date range start
    pub after: Option<DateTime<Utc>>,
    /// Date range end
    pub before: Option<DateTime<Utc>>,
    /// Exclude hidden blocks
    pub exclude_hidden: bool,
}

// =============================================================================
// BLOCK MANAGER
// =============================================================================

pub struct BlockManager {
    /// All blocks in current session
    blocks: Vec<Block>,
    /// Next sequence number
    next_sequence: u64,
    /// Currently running block ID
    current_block: Option<String>,
    /// Maximum output size per block before truncation
    max_output_size: usize,
    /// Maximum blocks to keep in memory
    max_blocks: usize,
    /// Block event handlers
    handlers: Vec<Box<dyn Fn(&Block, BlockEvent) + Send + Sync>>,
}

#[derive(Debug, Clone, Copy)]
pub enum BlockEvent {
    Created,
    Updated,
    Completed,
    Bookmarked,
    Hidden,
    Deleted,
}

impl BlockManager {
    pub fn new() -> Self {
        Self {
            blocks: Vec::new(),
            next_sequence: 1,
            current_block: None,
            max_output_size: 1_000_000, // 1MB
            max_blocks: 1000,
            handlers: Vec::new(),
        }
    }

    /// Start a new block for a command
    pub fn start_block(&mut self, command: &str, cwd: &str) -> Block {
        let id = format!("blk_{}", uuid::Uuid::new_v4().to_string()[..8].to_string());
        let sequence = self.next_sequence;
        self.next_sequence += 1;

        let block = Block {
            id: id.clone(),
            sequence,
            command: command.to_string(),
            output: String::new(),
            exit_code: None,
            cwd: cwd.to_string(),
            git_branch: detect_git_branch(cwd),
            started_at: Utc::now(),
            completed_at: None,
            duration_ms: None,
            state: BlockState::Running,
            env: None,
            shell: std::env::var("SHELL").ok(),
            user: std::env::var("USER").ok(),
            hostname: std::env::var("HOSTNAME").ok(),
            truncated: false,
            tags: Vec::new(),
            bookmarked: false,
            collapsed: false,
            hidden: false,
            notes: None,
            share_id: None,
        };

        self.current_block = Some(id.clone());
        self.blocks.push(block.clone());
        self.emit_event(&block, BlockEvent::Created);

        // Trim old blocks if needed
        if self.blocks.len() > self.max_blocks {
            self.blocks.remove(0);
        }

        block
    }

    /// Append output to current block
    pub fn append_output(&mut self, output: &str) {
        let id = match &self.current_block {
            Some(id) => id.clone(),
            None => return,
        };

        if let Some(block) = self.blocks.iter_mut().find(|b| b.id == id) {
            if block.output.len() + output.len() > self.max_output_size {
                block.truncated = true;
                let remaining = self.max_output_size.saturating_sub(block.output.len());
                if remaining > 0 {
                    block.output.push_str(&output[..remaining.min(output.len())]);
                }
            } else {
                block.output.push_str(output);
            }
            let block_clone = block.clone();
            self.emit_event(&block_clone, BlockEvent::Updated);
        }
    }

    /// Complete the current block
    pub fn complete_block(&mut self, exit_code: i32) -> Option<Block> {
        let id = self.current_block.take()?;

        if let Some(block) = self.blocks.iter_mut().find(|b| b.id == id) {
            block.exit_code = Some(exit_code);
            block.completed_at = Some(Utc::now());
            block.state = BlockState::from_exit_code(Some(exit_code));

            if let Some(started) = block.started_at.timestamp_millis().checked_sub(0) {
                let ended = block.completed_at.unwrap().timestamp_millis();
                block.duration_ms = Some((ended - started) as u64);
            }

            let block_clone = block.clone();
            self.emit_event(&block_clone, BlockEvent::Completed);
            return Some(block_clone);
        }

        None
    }

    /// Get block by ID
    pub fn get(&self, id: &str) -> Option<&Block> {
        self.blocks.iter().find(|b| b.id == id)
    }

    /// Get mutable block by ID
    pub fn get_mut(&mut self, id: &str) -> Option<&mut Block> {
        self.blocks.iter_mut().find(|b| b.id == id)
    }

    /// Get block by sequence number
    pub fn get_by_sequence(&self, sequence: u64) -> Option<&Block> {
        self.blocks.iter().find(|b| b.sequence == sequence)
    }

    /// Get all blocks
    pub fn all(&self) -> &[Block] {
        &self.blocks
    }

    /// Get blocks matching filter
    pub fn filter(&self, filter: &BlockFilter) -> Vec<&Block> {
        self.blocks.iter().filter(|b| {
            // State filter
            if let Some(ref states) = filter.states {
                if !states.contains(&b.state) {
                    return false;
                }
            }

            // Command pattern
            if let Some(ref pattern) = filter.command_pattern {
                if let Ok(re) = regex::Regex::new(pattern) {
                    if !re.is_match(&b.command) {
                        return false;
                    }
                }
            }

            // Output pattern
            if let Some(ref pattern) = filter.output_pattern {
                if let Ok(re) = regex::Regex::new(pattern) {
                    if !re.is_match(&b.output) {
                        return false;
                    }
                }
            }

            // CWD filter
            if let Some(ref cwd) = filter.cwd {
                if !b.cwd.contains(cwd) {
                    return false;
                }
            }

            // Git branch filter
            if let Some(ref branch) = filter.git_branch {
                if b.git_branch.as_ref() != Some(branch) {
                    return false;
                }
            }

            // Tags filter
            if let Some(ref tags) = filter.tags {
                if !tags.iter().all(|t| b.tags.contains(t)) {
                    return false;
                }
            }

            // Bookmarked only
            if filter.bookmarked_only && !b.bookmarked {
                return false;
            }

            // Failures only
            if filter.failures_only && b.state != BlockState::Failed {
                return false;
            }

            // Date range
            if let Some(after) = filter.after {
                if b.started_at < after {
                    return false;
                }
            }
            if let Some(before) = filter.before {
                if b.started_at > before {
                    return false;
                }
            }

            // Hidden filter
            if filter.exclude_hidden && b.hidden {
                return false;
            }

            true
        }).collect()
    }

    /// Get current running block
    pub fn current(&self) -> Option<&Block> {
        self.current_block.as_ref().and_then(|id| self.get(id))
    }

    /// Navigate to previous block
    pub fn previous(&self, from_id: &str) -> Option<&Block> {
        let idx = self.blocks.iter().position(|b| b.id == from_id)?;
        if idx > 0 {
            Some(&self.blocks[idx - 1])
        } else {
            None
        }
    }

    /// Navigate to next block
    pub fn next(&self, from_id: &str) -> Option<&Block> {
        let idx = self.blocks.iter().position(|b| b.id == from_id)?;
        if idx + 1 < self.blocks.len() {
            Some(&self.blocks[idx + 1])
        } else {
            None
        }
    }

    /// Toggle bookmark
    pub fn toggle_bookmark(&mut self, id: &str) -> bool {
        let result = if let Some(block) = self.blocks.iter_mut().find(|b| b.id == id) {
            block.bookmarked = !block.bookmarked;
            Some((block.clone(), block.bookmarked))
        } else {
            None
        };

        if let Some((block, bookmarked)) = result {
            self.emit_event(&block, BlockEvent::Bookmarked);
            return bookmarked;
        }
        false
    }

    /// Toggle hidden
    pub fn toggle_hidden(&mut self, id: &str) -> bool {
        let result = if let Some(block) = self.blocks.iter_mut().find(|b| b.id == id) {
            block.hidden = !block.hidden;
            Some((block.clone(), block.hidden))
        } else {
            None
        };

        if let Some((block, hidden)) = result {
            self.emit_event(&block, BlockEvent::Hidden);
            return hidden;
        }
        false
    }

    /// Toggle collapsed
    pub fn toggle_collapsed(&mut self, id: &str) -> bool {
        if let Some(block) = self.get_mut(id) {
            block.collapsed = !block.collapsed;
            return block.collapsed;
        }
        false
    }

    /// Add tags to block
    pub fn add_tags(&mut self, id: &str, tags: &[&str]) {
        if let Some(block) = self.get_mut(id) {
            for tag in tags {
                if !block.tags.contains(&tag.to_string()) {
                    block.tags.push(tag.to_string());
                }
            }
        }
    }

    /// Add note to block
    pub fn add_note(&mut self, id: &str, note: &str) {
        if let Some(block) = self.get_mut(id) {
            block.notes = Some(note.to_string());
        }
    }

    /// Delete a block
    pub fn delete(&mut self, id: &str) -> bool {
        if let Some(idx) = self.blocks.iter().position(|b| b.id == id) {
            let block = self.blocks.remove(idx);
            self.emit_event(&block, BlockEvent::Deleted);
            true
        } else {
            false
        }
    }

    /// Clear all blocks
    pub fn clear(&mut self) {
        self.blocks.clear();
        self.next_sequence = 1;
        self.current_block = None;
    }

    /// Get bookmarked blocks
    pub fn bookmarked(&self) -> Vec<&Block> {
        self.blocks.iter().filter(|b| b.bookmarked).collect()
    }

    /// Get failed blocks
    pub fn failed(&self) -> Vec<&Block> {
        self.blocks.iter().filter(|b| b.state == BlockState::Failed).collect()
    }

    /// Search blocks
    pub fn search(&self, query: &str) -> Vec<&Block> {
        let query_lower = query.to_lowercase();
        self.blocks.iter().filter(|b| {
            b.command.to_lowercase().contains(&query_lower) ||
            b.output.to_lowercase().contains(&query_lower) ||
            b.notes.as_ref().map(|n| n.to_lowercase().contains(&query_lower)).unwrap_or(false) ||
            b.tags.iter().any(|t| t.to_lowercase().contains(&query_lower))
        }).collect()
    }

    /// Register event handler
    pub fn on_block<F>(&mut self, handler: F)
    where
        F: Fn(&Block, BlockEvent) + Send + Sync + 'static,
    {
        self.handlers.push(Box::new(handler));
    }

    /// Export block to text
    pub fn export_text(&self, id: &str) -> Option<String> {
        let block = self.get(id)?;
        Some(format!(
            "$ {}\n{}\n[Exit: {}]",
            block.command,
            block.output,
            block.exit_code.map(|c| c.to_string()).unwrap_or_else(|| "?".to_string())
        ))
    }

    /// Export block to markdown
    pub fn export_markdown(&self, id: &str) -> Option<String> {
        let block = self.get(id)?;
        let status = if block.state == BlockState::Success { "ok" } else { "err" };
        Some(format!(
            "```bash\n$ {}\n```\n\n```\n{}\n```\n\n*Exit: {} | Duration: {}ms | Status: {}*",
            block.command,
            block.output,
            block.exit_code.map(|c| c.to_string()).unwrap_or_else(|| "?".to_string()),
            block.duration_ms.unwrap_or(0),
            status
        ))
    }

    // Private

    fn emit_event(&self, block: &Block, event: BlockEvent) {
        for handler in &self.handlers {
            handler(block, event);
        }
    }
}

impl Default for BlockManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn detect_git_branch(cwd: &str) -> Option<String> {
    let output = std::process::Command::new("git")
        .args(["rev-parse", "--abbrev-ref", "HEAD"])
        .current_dir(cwd)
        .output()
        .ok()?;

    if output.status.success() {
        Some(String::from_utf8_lossy(&output.stdout).trim().to_string())
    } else {
        None
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref BLOCK_MANAGER: Arc<Mutex<BlockManager>> =
        Arc::new(Mutex::new(BlockManager::new()));
}

/// Get the global block manager
pub fn blocks() -> Arc<Mutex<BlockManager>> {
    BLOCK_MANAGER.clone()
}

/// Start a new block
pub fn start_block(command: &str, cwd: &str) -> Block {
    BLOCK_MANAGER.lock().unwrap().start_block(command, cwd)
}

/// Append output to current block
pub fn append_output(output: &str) {
    BLOCK_MANAGER.lock().unwrap().append_output(output);
}

/// Complete current block
pub fn complete_block(exit_code: i32) -> Option<Block> {
    BLOCK_MANAGER.lock().unwrap().complete_block(exit_code)
}

/// Get all blocks
pub fn all_blocks() -> Vec<Block> {
    BLOCK_MANAGER.lock().unwrap().all().to_vec()
}

/// Search blocks
pub fn search_blocks(query: &str) -> Vec<Block> {
    BLOCK_MANAGER.lock().unwrap().search(query).into_iter().cloned().collect()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_block_manager_new() {
        let manager = BlockManager::new();
        assert!(manager.blocks.is_empty());
        assert_eq!(manager.next_sequence, 1);
    }

    #[test]
    fn test_start_block() {
        let mut manager = BlockManager::new();
        let block = manager.start_block("ls -la", "/home/user");

        assert_eq!(block.command, "ls -la");
        assert_eq!(block.cwd, "/home/user");
        assert_eq!(block.sequence, 1);
        assert_eq!(block.state, BlockState::Running);
    }

    #[test]
    fn test_append_output() {
        let mut manager = BlockManager::new();
        manager.start_block("echo test", "/tmp");

        manager.append_output("test\n");
        manager.append_output("more output\n");

        let block = manager.current().unwrap();
        assert_eq!(block.output, "test\nmore output\n");
    }

    #[test]
    fn test_complete_block() {
        let mut manager = BlockManager::new();
        manager.start_block("ls", "/tmp");
        manager.append_output("file.txt\n");

        let block = manager.complete_block(0).unwrap();
        assert_eq!(block.exit_code, Some(0));
        assert_eq!(block.state, BlockState::Success);
        assert!(block.completed_at.is_some());
    }

    #[test]
    fn test_block_state_from_exit_code() {
        assert_eq!(BlockState::from_exit_code(Some(0)), BlockState::Success);
        assert_eq!(BlockState::from_exit_code(Some(1)), BlockState::Failed);
        assert_eq!(BlockState::from_exit_code(Some(137)), BlockState::Killed); // SIGKILL
        assert_eq!(BlockState::from_exit_code(None), BlockState::Running);
    }

    #[test]
    fn test_bookmark() {
        let mut manager = BlockManager::new();
        let block = manager.start_block("test", "/tmp");
        manager.complete_block(0);

        assert!(!manager.get(&block.id).unwrap().bookmarked);

        manager.toggle_bookmark(&block.id);
        assert!(manager.get(&block.id).unwrap().bookmarked);

        manager.toggle_bookmark(&block.id);
        assert!(!manager.get(&block.id).unwrap().bookmarked);
    }

    #[test]
    fn test_filter() {
        let mut manager = BlockManager::new();

        manager.start_block("ls -la", "/home");
        manager.complete_block(0);

        manager.start_block("cat /etc/passwd", "/home");
        manager.complete_block(1);

        manager.start_block("echo test", "/tmp");
        manager.complete_block(0);

        // Filter by state
        let filter = BlockFilter {
            states: Some(vec![BlockState::Failed]),
            ..Default::default()
        };
        let results = manager.filter(&filter);
        assert_eq!(results.len(), 1);
        assert!(results[0].command.contains("cat"));
    }

    #[test]
    fn test_search() {
        let mut manager = BlockManager::new();

        manager.start_block("ls -la", "/tmp");
        manager.append_output("file.txt\ndir/\n");
        manager.complete_block(0);

        manager.start_block("echo hello", "/tmp");
        manager.append_output("hello\n");
        manager.complete_block(0);

        let results = manager.search("hello");
        assert_eq!(results.len(), 1);
        assert!(results[0].command.contains("echo"));
    }

    #[test]
    fn test_navigation() {
        let mut manager = BlockManager::new();

        let b1 = manager.start_block("cmd1", "/tmp");
        manager.complete_block(0);

        let b2 = manager.start_block("cmd2", "/tmp");
        manager.complete_block(0);

        let b3 = manager.start_block("cmd3", "/tmp");
        manager.complete_block(0);

        assert!(manager.previous(&b1.id).is_none());
        assert_eq!(manager.next(&b1.id).unwrap().id, b2.id);
        assert_eq!(manager.previous(&b3.id).unwrap().id, b2.id);
        assert!(manager.next(&b3.id).is_none());
    }

    #[test]
    fn test_tags() {
        let mut manager = BlockManager::new();
        let block = manager.start_block("test", "/tmp");
        manager.complete_block(0);

        manager.add_tags(&block.id, &["important", "build"]);

        let b = manager.get(&block.id).unwrap();
        assert!(b.tags.contains(&"important".to_string()));
        assert!(b.tags.contains(&"build".to_string()));
    }

    #[test]
    fn test_export_markdown() {
        let mut manager = BlockManager::new();
        let block = manager.start_block("echo test", "/tmp");
        manager.append_output("test\n");
        manager.complete_block(0);

        let md = manager.export_markdown(&block.id).unwrap();
        assert!(md.contains("```bash"));
        assert!(md.contains("$ echo test"));
        assert!(md.contains("Exit: 0"));
    }
}
