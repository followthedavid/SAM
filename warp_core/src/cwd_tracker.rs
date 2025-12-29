//! cwdTracker - lightweight directory context tracker
//! - Keeps a current working directory per "session"
//! - Enforces simple sandboxing: optionally restrict cd to a project root

use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use tokio::fs;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CdResult {
    pub ok: bool,
    pub cwd: Option<String>,
    pub error: Option<String>,
}

/// Directory context tracker with optional project root sandboxing
pub struct CwdTracker {
    cwd: PathBuf,
    project_root: Option<PathBuf>,
}

impl CwdTracker {
    /// Create a new CwdTracker
    /// - initial: starting directory (defaults to current dir)
    /// - project_root: optional root to restrict navigation
    pub fn new(initial: Option<PathBuf>, project_root: Option<PathBuf>) -> Self {
        let cwd = initial
            .or_else(|| std::env::current_dir().ok())
            .unwrap_or_else(|| PathBuf::from("/"));

        let cwd = cwd.canonicalize().unwrap_or(cwd);
        let project_root = project_root.and_then(|p| p.canonicalize().ok());

        Self { cwd, project_root }
    }

    /// Get current working directory
    pub fn get_cwd(&self) -> PathBuf {
        self.cwd.clone()
    }

    /// Get current working directory as string
    pub fn get_cwd_string(&self) -> String {
        self.cwd.display().to_string()
    }

    /// Change directory with validation and optional sandboxing
    pub async fn cd(&mut self, target_path: impl AsRef<Path>) -> CdResult {
        let target = target_path.as_ref();
        
        // Resolve relative to current cwd
        let resolved = if target.is_absolute() {
            target.to_path_buf()
        } else {
            self.cwd.join(target)
        };

        // Canonicalize to get real path
        let resolved = match resolved.canonicalize() {
            Ok(p) => p,
            Err(e) => {
                return CdResult {
                    ok: false,
                    cwd: None,
                    error: Some(format!("Path resolution failed: {}", e)),
                };
            }
        };

        // Verify it exists and is a directory
        match fs::metadata(&resolved).await {
            Ok(metadata) => {
                if !metadata.is_dir() {
                    return CdResult {
                        ok: false,
                        cwd: None,
                        error: Some("Not a directory".to_string()),
                    };
                }
            }
            Err(e) => {
                return CdResult {
                    ok: false,
                    cwd: None,
                    error: Some(format!("Cannot access directory: {}", e)),
                };
            }
        }

        // Check project root restriction if set
        if let Some(ref root) = self.project_root {
            if !resolved.starts_with(root) {
                return CdResult {
                    ok: false,
                    cwd: None,
                    error: Some("cd outside project root denied".to_string()),
                };
            }
        }

        // Success - update cwd
        self.cwd = resolved.clone();

        CdResult {
            ok: true,
            cwd: Some(resolved.display().to_string()),
            error: None,
        }
    }

    /// Get project root if set
    pub fn get_project_root(&self) -> Option<String> {
        self.project_root
            .as_ref()
            .map(|p| p.display().to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_cwd_tracker_basic() {
        let temp_dir = std::env::temp_dir();
        let tracker = CwdTracker::new(Some(temp_dir.clone()), None);

        assert_eq!(
            tracker.get_cwd().canonicalize().unwrap(),
            temp_dir.canonicalize().unwrap()
        );
    }

    #[tokio::test]
    async fn test_cd_to_parent() {
        let temp_dir = std::env::temp_dir();
        let mut tracker = CwdTracker::new(Some(temp_dir.clone()), None);

        let result = tracker.cd("..").await;
        assert!(result.ok);
    }

    #[tokio::test]
    async fn test_sandbox_restriction() {
        let temp_dir = std::env::temp_dir();
        let mut tracker = CwdTracker::new(Some(temp_dir.clone()), Some(temp_dir.clone()));

        // Try to cd outside project root
        let result = tracker.cd("..").await;
        assert!(!result.ok);
        assert!(result.error.unwrap().contains("outside project root"));
    }
}
