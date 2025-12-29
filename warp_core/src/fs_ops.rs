//! fsOps - abstraction layer for file & script operations
//! - read_text_file, write_text_file, apply_unified_diff, run_script
//! - returns normalized results matching Phase 4 JS API

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Stdio;
use tokio::fs;
use tokio::process::Command;
use tokio::time::{timeout, Duration};

#[derive(Debug, Serialize, Deserialize)]
pub struct ReadFileOpts {
    pub max_bytes: usize,
}

impl Default for ReadFileOpts {
    fn default() -> Self {
        Self {
            max_bytes: 64 * 1024,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WriteFileOpts {
    pub ensure_dir: bool,
    pub mode: Option<u32>,
}

impl Default for WriteFileOpts {
    fn default() -> Self {
        Self {
            ensure_dir: true,
            mode: None,
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct WriteFileResult {
    pub ok: bool,
    pub path: String,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApplyDiffOpts {
    pub dry_run: bool,
}

impl Default for ApplyDiffOpts {
    fn default() -> Self {
        Self { dry_run: false }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct ApplyDiffResult {
    pub applied: bool,
    pub reason: Option<String>,
    pub file: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RunScriptOpts {
    pub cwd: Option<String>,
    pub timeout_ms: Option<u64>,
}

impl Default for RunScriptOpts {
    fn default() -> Self {
        Self {
            cwd: None,
            timeout_ms: Some(60_000),
        }
    }
}

#[derive(Debug, Serialize, Deserialize)]
pub struct RunScriptResult {
    pub code: Option<i32>,
    pub signal: Option<String>,
    pub stdout: String,
    pub stderr: String,
    pub error: Option<String>,
}

/// Generate a unique ID with prefix (matching JS makeId)
pub fn make_id(prefix: &str) -> String {
    format!("{}-{}", prefix, uuid::Uuid::new_v4())
}

/// Read a text file with optional truncation for large files
pub async fn read_text_file(file_path: impl AsRef<Path>, opts: ReadFileOpts) -> Result<String> {
    let path = file_path.as_ref();
    let content = fs::read_to_string(path)
        .await
        .context(format!("Failed to read file: {:?}", path))?;

    if content.len() > opts.max_bytes {
        let half = opts.max_bytes / 2;
        let start = &content[..half];
        let end = &content[content.len() - half..];
        Ok(format!("{}\n...TRUNCATED...\n{}", start, end))
    } else {
        Ok(content)
    }
}

/// Write a text file with optional directory creation and permissions
pub async fn write_text_file(
    file_path: impl AsRef<Path>,
    content: &str,
    opts: WriteFileOpts,
) -> Result<WriteFileResult> {
    let path = file_path.as_ref();

    if opts.ensure_dir {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .await
                .context("Failed to create parent directory")?;
        }
    }

    fs::write(path, content)
        .await
        .context(format!("Failed to write file: {:?}", path))?;

    #[cfg(unix)]
    if let Some(mode) = opts.mode {
        use std::os::unix::fs::PermissionsExt;
        let permissions = std::fs::Permissions::from_mode(mode);
        std::fs::set_permissions(path, permissions)
            .context("Failed to set file permissions")?;
    }

    Ok(WriteFileResult {
        ok: true,
        path: path.display().to_string(),
    })
}

/// Apply a unified diff with simple replacement marker support
/// Matches JS behavior: if diff contains "===REPLACE===" marker, 
/// treat content after marker as full file replacement
pub async fn apply_unified_diff(
    file_path: impl AsRef<Path>,
    unified_diff: &str,
    opts: ApplyDiffOpts,
) -> Result<ApplyDiffResult> {
    const REPLACE_MARKER: &str = "===REPLACE===";

    if let Some(marker_pos) = unified_diff.find(REPLACE_MARKER) {
        let new_content = &unified_diff[marker_pos + REPLACE_MARKER.len()..];

        if opts.dry_run {
            return Ok(ApplyDiffResult {
                applied: true,
                reason: Some("dry-run: replace detected".to_string()),
                file: None,
            });
        }

        let path = file_path.as_ref();
        write_text_file(path, new_content, WriteFileOpts::default()).await?;

        return Ok(ApplyDiffResult {
            applied: true,
            reason: None,
            file: Some(path.display().to_string()),
        });
    }

    // No marker found - return unsupported
    Ok(ApplyDiffResult {
        applied: false,
        reason: Some("unsupported-diff-format".to_string()),
        file: None,
    })
}

/// Run a shell script/command with timeout
pub async fn run_script(
    command: &str,
    args: Vec<String>,
    opts: RunScriptOpts,
) -> Result<RunScriptResult> {
    let cwd = opts
        .cwd
        .as_ref()
        .map(PathBuf::from)
        .unwrap_or_else(|| std::env::current_dir().unwrap_or_default());

    let timeout_duration = Duration::from_millis(opts.timeout_ms.unwrap_or(60_000));

    let mut cmd = Command::new(command);
    cmd.args(&args)
        .current_dir(cwd)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    match cmd.spawn() {
        Ok(child) => {
            // Use async block to handle timeout without moving child
            let result = timeout(timeout_duration, async {
                let output = child.wait_with_output().await?;
                Ok::<_, std::io::Error>(output)
            }).await;

            match result {
                Ok(Ok(output)) => Ok(RunScriptResult {
                    code: output.status.code(),
                    signal: None,
                    stdout: String::from_utf8_lossy(&output.stdout).to_string(),
                    stderr: String::from_utf8_lossy(&output.stderr).to_string(),
                    error: None,
                }),
                Ok(Err(e)) => Ok(RunScriptResult {
                    code: None,
                    signal: None,
                    stdout: String::new(),
                    stderr: String::new(),
                    error: Some(e.to_string()),
                }),
                Err(_) => {
                    // Timeout exceeded
                    Ok(RunScriptResult {
                        code: None,
                        signal: Some("SIGKILL".to_string()),
                        stdout: String::new(),
                        stderr: String::new(),
                        error: Some("Timeout exceeded".to_string()),
                    })
                }
            }
        }
        Err(e) => Ok(RunScriptResult {
            code: None,
            signal: None,
            stdout: String::new(),
            stderr: String::new(),
            error: Some(e.to_string()),
        }),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_make_id() {
        let id = make_id("test");
        assert!(id.starts_with("test-"));
    }

    #[tokio::test]
    async fn test_write_and_read() {
        let temp_dir = std::env::temp_dir();
        let test_file = temp_dir.join("warp_core_test.txt");
        let content = "Hello Warp Core!";

        let result = write_text_file(&test_file, content, WriteFileOpts::default())
            .await
            .unwrap();
        assert!(result.ok);

        let read_content = read_text_file(&test_file, ReadFileOpts::default())
            .await
            .unwrap();
        assert_eq!(read_content, content);

        let _ = fs::remove_file(&test_file).await;
    }
}
