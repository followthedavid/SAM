//! Block Sharing for warp_core
//!
//! Enables sharing terminal output blocks via links, similar to Warp's
//! block sharing feature. Supports local file export and URL-based sharing.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use chrono::{DateTime, Utc};
use base64::{Engine as _, engine::general_purpose::STANDARD as BASE64};

/// A shareable terminal block
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SharedBlock {
    /// Unique identifier for the block
    pub id: String,
    /// The command that was executed
    pub command: String,
    /// The output of the command
    pub output: String,
    /// Exit code of the command
    pub exit_code: Option<i32>,
    /// Working directory when command was run
    pub cwd: String,
    /// Timestamp when command was executed
    pub timestamp: DateTime<Utc>,
    /// Duration in milliseconds
    pub duration_ms: Option<u64>,
    /// Optional title/description
    pub title: Option<String>,
    /// Environment variables (filtered for safety)
    pub env_snapshot: Option<HashMap<String, String>>,
    /// Shell type used
    pub shell: Option<String>,
    /// Whether output was truncated
    pub truncated: bool,
    /// Sharing metadata
    pub share_info: ShareInfo,
}

/// Sharing metadata
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ShareInfo {
    /// When the block was shared
    pub shared_at: DateTime<Utc>,
    /// Expiration time (optional)
    pub expires_at: Option<DateTime<Utc>>,
    /// Access level
    pub access: ShareAccess,
    /// View count
    pub view_count: u64,
    /// Whether secrets were redacted
    pub secrets_redacted: bool,
}

/// Access level for shared blocks
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum ShareAccess {
    /// Anyone with the link can view
    Public,
    /// Only specific users can view
    Private,
    /// Requires password
    Protected { password_hash: String },
}

/// Export format for shared blocks
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum ExportFormat {
    /// Plain text
    Text,
    /// Markdown with syntax highlighting hints
    Markdown,
    /// HTML with styling
    Html,
    /// JSON for programmatic access
    Json,
    /// ANSI-preserved output
    Ansi,
    /// PNG image (rendered terminal)
    Image,
}

/// Block sharing manager
pub struct BlockSharing {
    /// Storage backend
    storage: BlockStorage,
    /// Maximum output size before truncation
    max_output_size: usize,
    /// Secret redactor (optional)
    redactor: Option<crate::secret_redactor::SecretRedactor>,
}

/// Storage backend for shared blocks
#[derive(Clone, Debug)]
pub enum BlockStorage {
    /// Local file storage
    LocalFile { path: std::path::PathBuf },
    /// In-memory storage (for testing)
    Memory { blocks: HashMap<String, SharedBlock> },
    /// Remote API storage
    Remote { api_url: String, api_key: Option<String> },
}

impl BlockSharing {
    /// Create with local file storage
    pub fn new_local(storage_path: impl Into<std::path::PathBuf>) -> Self {
        Self {
            storage: BlockStorage::LocalFile { path: storage_path.into() },
            max_output_size: 1_000_000, // 1MB default
            redactor: None,
        }
    }

    /// Create with in-memory storage (for testing)
    pub fn new_memory() -> Self {
        Self {
            storage: BlockStorage::Memory { blocks: HashMap::new() },
            max_output_size: 1_000_000,
            redactor: None,
        }
    }

    /// Set secret redactor
    pub fn with_redactor(mut self, redactor: crate::secret_redactor::SecretRedactor) -> Self {
        self.redactor = Some(redactor);
        self
    }

    /// Set maximum output size
    pub fn with_max_size(mut self, size: usize) -> Self {
        self.max_output_size = size;
        self
    }

    /// Share a terminal block
    pub fn share_block(
        &mut self,
        command: &str,
        output: &str,
        exit_code: Option<i32>,
        cwd: &str,
        timestamp: DateTime<Utc>,
        duration_ms: Option<u64>,
    ) -> Result<SharedBlock, ShareError> {
        let id = generate_share_id();

        // Truncate if needed
        let (processed_output, truncated) = if output.len() > self.max_output_size {
            (
                format!(
                    "{}...\n\n[Output truncated - {} bytes total]",
                    &output[..self.max_output_size],
                    output.len()
                ),
                true,
            )
        } else {
            (output.to_string(), false)
        };

        // Redact secrets if redactor is configured
        let (final_output, secrets_redacted) = if let Some(ref redactor) = self.redactor {
            let result = redactor.redact_with_info(&processed_output);
            (result.redacted_text, !result.redactions.is_empty())
        } else {
            (processed_output, false)
        };

        let block = SharedBlock {
            id: id.clone(),
            command: command.to_string(),
            output: final_output,
            exit_code,
            cwd: cwd.to_string(),
            timestamp,
            duration_ms,
            title: None,
            env_snapshot: None,
            shell: None,
            truncated,
            share_info: ShareInfo {
                shared_at: Utc::now(),
                expires_at: None,
                access: ShareAccess::Public,
                view_count: 0,
                secrets_redacted,
            },
        };

        self.store_block(&block)?;
        Ok(block)
    }

    /// Get a shared block by ID
    pub fn get_block(&self, id: &str) -> Result<Option<SharedBlock>, ShareError> {
        match &self.storage {
            BlockStorage::LocalFile { path } => {
                let file_path = path.join(format!("{}.json", id));
                if file_path.exists() {
                    let content = std::fs::read_to_string(&file_path)
                        .map_err(|e| ShareError::StorageError(e.to_string()))?;
                    let block: SharedBlock = serde_json::from_str(&content)
                        .map_err(|e| ShareError::ParseError(e.to_string()))?;
                    Ok(Some(block))
                } else {
                    Ok(None)
                }
            }
            BlockStorage::Memory { blocks } => Ok(blocks.get(id).cloned()),
            BlockStorage::Remote { .. } => {
                Err(ShareError::NotImplemented("Remote storage get".to_string()))
            }
        }
    }

    /// Delete a shared block
    pub fn delete_block(&mut self, id: &str) -> Result<bool, ShareError> {
        match &mut self.storage {
            BlockStorage::LocalFile { path } => {
                let file_path = path.join(format!("{}.json", id));
                if file_path.exists() {
                    std::fs::remove_file(&file_path)
                        .map_err(|e| ShareError::StorageError(e.to_string()))?;
                    Ok(true)
                } else {
                    Ok(false)
                }
            }
            BlockStorage::Memory { blocks } => Ok(blocks.remove(id).is_some()),
            BlockStorage::Remote { .. } => {
                Err(ShareError::NotImplemented("Remote storage delete".to_string()))
            }
        }
    }

    /// Export a block to a specific format
    pub fn export_block(&self, block: &SharedBlock, format: ExportFormat) -> Result<String, ShareError> {
        match format {
            ExportFormat::Text => Ok(self.export_text(block)),
            ExportFormat::Markdown => Ok(self.export_markdown(block)),
            ExportFormat::Html => Ok(self.export_html(block)),
            ExportFormat::Json => serde_json::to_string_pretty(block)
                .map_err(|e| ShareError::ParseError(e.to_string())),
            ExportFormat::Ansi => Ok(self.export_ansi(block)),
            ExportFormat::Image => Err(ShareError::NotImplemented("Image export".to_string())),
        }
    }

    /// Generate a shareable URL (placeholder - actual implementation depends on backend)
    pub fn generate_share_url(&self, block: &SharedBlock, base_url: &str) -> String {
        format!("{}/share/{}", base_url, block.id)
    }

    /// Generate an embeddable snippet
    pub fn generate_embed_code(&self, block: &SharedBlock, base_url: &str) -> String {
        let url = self.generate_share_url(block, base_url);
        format!(
            r#"<iframe src="{}/embed" width="100%" height="400" frameborder="0"></iframe>"#,
            url
        )
    }

    // Private methods

    fn store_block(&mut self, block: &SharedBlock) -> Result<(), ShareError> {
        match &mut self.storage {
            BlockStorage::LocalFile { path } => {
                std::fs::create_dir_all(&*path)
                    .map_err(|e| ShareError::StorageError(e.to_string()))?;
                let file_path = path.join(format!("{}.json", block.id));
                let content = serde_json::to_string_pretty(block)
                    .map_err(|e| ShareError::ParseError(e.to_string()))?;
                std::fs::write(file_path, content)
                    .map_err(|e| ShareError::StorageError(e.to_string()))?;
                Ok(())
            }
            BlockStorage::Memory { blocks } => {
                blocks.insert(block.id.clone(), block.clone());
                Ok(())
            }
            BlockStorage::Remote { .. } => {
                Err(ShareError::NotImplemented("Remote storage".to_string()))
            }
        }
    }

    fn export_text(&self, block: &SharedBlock) -> String {
        let mut output = String::new();

        if let Some(ref title) = block.title {
            output.push_str(&format!("# {}\n\n", title));
        }

        output.push_str(&format!("$ {}\n", block.command));
        output.push_str(&block.output);

        if let Some(code) = block.exit_code {
            output.push_str(&format!("\n[Exit code: {}]", code));
        }

        output
    }

    fn export_markdown(&self, block: &SharedBlock) -> String {
        let mut output = String::new();

        if let Some(ref title) = block.title {
            output.push_str(&format!("# {}\n\n", title));
        }

        output.push_str("```bash\n");
        output.push_str(&format!("$ {}\n", block.command));
        output.push_str("```\n\n");

        output.push_str("**Output:**\n\n");
        output.push_str("```\n");
        output.push_str(&block.output);
        output.push_str("\n```\n");

        if let Some(code) = block.exit_code {
            let status = if code == 0 { "✓" } else { "✗" };
            output.push_str(&format!("\n{} Exit code: {}\n", status, code));
        }

        if let Some(ms) = block.duration_ms {
            output.push_str(&format!("⏱ Duration: {}ms\n", ms));
        }

        output
    }

    fn export_html(&self, block: &SharedBlock) -> String {
        let title = block.title.as_deref().unwrap_or("Shared Terminal Block");
        let exit_class = match block.exit_code {
            Some(0) => "success",
            Some(_) => "error",
            None => "unknown",
        };

        format!(
            r#"<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 20px; background: #1e1e1e; color: #d4d4d4; }}
        .terminal {{ background: #0d1117; border-radius: 8px; padding: 16px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 14px; }}
        .command {{ color: #58a6ff; margin-bottom: 8px; }}
        .prompt {{ color: #7ee787; }}
        .output {{ white-space: pre-wrap; color: #c9d1d9; }}
        .meta {{ margin-top: 12px; font-size: 12px; color: #8b949e; }}
        .success {{ color: #7ee787; }}
        .error {{ color: #f85149; }}
    </style>
</head>
<body>
    <div class="terminal">
        <div class="command"><span class="prompt">$</span> {command}</div>
        <div class="output">{output}</div>
        <div class="meta {exit_class}">
            Exit: {exit_code} | {cwd}
        </div>
    </div>
</body>
</html>"#,
            title = html_escape(title),
            command = html_escape(&block.command),
            output = html_escape(&block.output),
            exit_class = exit_class,
            exit_code = block.exit_code.map(|c| c.to_string()).unwrap_or_else(|| "?".to_string()),
            cwd = html_escape(&block.cwd),
        )
    }

    fn export_ansi(&self, block: &SharedBlock) -> String {
        // Return output with ANSI codes preserved
        format!(
            "\x1b[32m$\x1b[0m {}\n{}",
            block.command,
            block.output
        )
    }
}

/// Generate a unique share ID
fn generate_share_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();

    let random: u32 = rand::random();

    // Create a short, URL-safe ID
    let combined = format!("{:x}{:x}", timestamp, random);
    BASE64.encode(&combined.as_bytes()[..12.min(combined.len())])
        .replace('+', "-")
        .replace('/', "_")
        .trim_end_matches('=')
        .to_string()
}

/// Simple HTML escaping
fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
        .replace('\'', "&#x27;")
}

/// Errors that can occur during sharing
#[derive(Debug)]
pub enum ShareError {
    StorageError(String),
    ParseError(String),
    NotImplemented(String),
    Expired,
    AccessDenied,
}

impl std::fmt::Display for ShareError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ShareError::StorageError(msg) => write!(f, "Storage error: {}", msg),
            ShareError::ParseError(msg) => write!(f, "Parse error: {}", msg),
            ShareError::NotImplemented(msg) => write!(f, "Not implemented: {}", msg),
            ShareError::Expired => write!(f, "Share link has expired"),
            ShareError::AccessDenied => write!(f, "Access denied"),
        }
    }
}

impl std::error::Error for ShareError {}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_share_block() {
        let mut sharing = BlockSharing::new_memory();

        let block = sharing.share_block(
            "ls -la",
            "total 0\ndrwxr-xr-x  2 user user 64 Jan 1 00:00 .\n",
            Some(0),
            "/home/user",
            Utc::now(),
            Some(50),
        ).unwrap();

        assert!(!block.id.is_empty());
        assert_eq!(block.command, "ls -la");
        assert_eq!(block.exit_code, Some(0));
    }

    #[test]
    fn test_get_block() {
        let mut sharing = BlockSharing::new_memory();

        let block = sharing.share_block(
            "echo hello",
            "hello\n",
            Some(0),
            "/tmp",
            Utc::now(),
            None,
        ).unwrap();

        let retrieved = sharing.get_block(&block.id).unwrap();
        assert!(retrieved.is_some());
        assert_eq!(retrieved.unwrap().command, "echo hello");
    }

    #[test]
    fn test_export_markdown() {
        let mut sharing = BlockSharing::new_memory();

        let block = sharing.share_block(
            "date",
            "Wed Jan 22 10:00:00 UTC 2025\n",
            Some(0),
            "/home",
            Utc::now(),
            Some(10),
        ).unwrap();

        let md = sharing.export_block(&block, ExportFormat::Markdown).unwrap();
        assert!(md.contains("```bash"));
        assert!(md.contains("$ date"));
        assert!(md.contains("Exit code: 0"));
    }

    #[test]
    fn test_truncation() {
        let mut sharing = BlockSharing::new_memory().with_max_size(100);

        let long_output = "x".repeat(200);
        let block = sharing.share_block(
            "cat bigfile",
            &long_output,
            Some(0),
            "/tmp",
            Utc::now(),
            None,
        ).unwrap();

        assert!(block.truncated);
        assert!(block.output.contains("[Output truncated"));
    }

    #[test]
    fn test_share_id_generation() {
        let id1 = generate_share_id();
        let id2 = generate_share_id();

        assert!(!id1.is_empty());
        assert!(!id2.is_empty());
        assert_ne!(id1, id2);

        // Check URL-safe
        assert!(!id1.contains('+'));
        assert!(!id1.contains('/'));
    }
}
