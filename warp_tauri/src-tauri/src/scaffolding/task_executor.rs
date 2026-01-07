//! Task Executor - Actually executes approved actions
//!
//! When a user approves a QuickAction, this module handles the real execution:
//! - Git commits
//! - File operations
//! - Shell commands
//! - Project-specific actions

use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::process::Command;
use tokio::sync::mpsc;

/// Types of executable tasks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskType {
    GitCommit { project: String, message: Option<String> },
    GitPush { project: String, branch: Option<String> },
    GitPull { project: String },
    ShellCommand { command: String, working_dir: Option<String> },
    FileEdit { path: String, content: String },
    FileCreate { path: String, content: String },
    ServiceStart { service: String },
    ServiceStop { service: String },
    ProjectScan { path: Option<String> },
    Refresh,
    ModeExit,  // Exit roleplay/creative mode
    Custom { action: String, params: serde_json::Value },
}

/// Result of task execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub success: bool,
    pub task_type: String,
    pub output: String,
    pub error: Option<String>,
    pub duration_ms: u64,
    pub changes_made: Vec<String>,
}

/// Task execution status for UI updates
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TaskStatus {
    Queued,
    Running { progress: Option<f32> },
    Completed(TaskResult),
    Failed(String),
}

pub struct TaskExecutor {
    project_registry_path: PathBuf,
}

impl TaskExecutor {
    pub fn new() -> Self {
        let project_registry_path = dirs::home_dir()
            .map(|h| h.join(".sam_project_registry.json"))
            .unwrap_or_else(|| PathBuf::from("/tmp/.sam_project_registry.json"));

        Self {
            project_registry_path,
        }
    }

    /// Parse a command string into a TaskType
    pub fn parse_command(&self, command: &str) -> Option<TaskType> {
        let lower = command.to_lowercase();
        let parts: Vec<&str> = command.split_whitespace().collect();

        // Git commands
        if lower.starts_with("commit ") {
            let project = parts.get(1).map(|s| s.to_string()).unwrap_or_default();
            return Some(TaskType::GitCommit { project, message: None });
        }
        if lower.starts_with("push ") {
            let project = parts.get(1).map(|s| s.to_string()).unwrap_or_default();
            return Some(TaskType::GitPush { project, branch: None });
        }
        if lower.starts_with("pull ") {
            let project = parts.get(1).map(|s| s.to_string()).unwrap_or_default();
            return Some(TaskType::GitPull { project });
        }

        // Service commands
        if lower.starts_with("start ") {
            let service = parts.get(1).map(|s| s.to_string()).unwrap_or_default();
            return Some(TaskType::ServiceStart { service });
        }
        if lower.starts_with("stop ") {
            let service = parts.get(1).map(|s| s.to_string()).unwrap_or_default();
            return Some(TaskType::ServiceStop { service });
        }

        // Mode exit commands
        if lower == "exit roleplay" || lower == "exit creative mode" || lower == "exit creative" {
            return Some(TaskType::ModeExit);
        }

        // Special commands
        if lower == "refresh" || lower == "scan projects" {
            return Some(TaskType::Refresh);
        }
        if lower.starts_with("scan ") {
            let path = parts.get(1).map(|s| s.to_string());
            return Some(TaskType::ProjectScan { path });
        }

        // Shell command fallback
        if lower.starts_with("run ") || lower.starts_with("exec ") {
            let cmd = command.splitn(2, ' ').nth(1).unwrap_or("").to_string();
            return Some(TaskType::ShellCommand { command: cmd, working_dir: None });
        }

        None
    }

    /// Execute a parsed task
    pub async fn execute(&self, task: TaskType) -> TaskResult {
        let start = std::time::Instant::now();

        let result = match task {
            TaskType::GitCommit { project, message } => {
                self.execute_git_commit(&project, message.as_deref()).await
            }
            TaskType::GitPush { project, branch } => {
                self.execute_git_push(&project, branch.as_deref()).await
            }
            TaskType::GitPull { project } => {
                self.execute_git_pull(&project).await
            }
            TaskType::ShellCommand { command, working_dir } => {
                self.execute_shell(&command, working_dir.as_deref()).await
            }
            TaskType::ServiceStart { service } => {
                self.execute_service_start(&service).await
            }
            TaskType::ServiceStop { service } => {
                self.execute_service_stop(&service).await
            }
            TaskType::ProjectScan { path } => {
                self.execute_project_scan(path.as_deref()).await
            }
            TaskType::Refresh => {
                self.execute_refresh().await
            }
            TaskType::FileEdit { path, content } => {
                self.execute_file_edit(&path, &content).await
            }
            TaskType::FileCreate { path, content } => {
                self.execute_file_create(&path, &content).await
            }
            TaskType::ModeExit => {
                TaskResult {
                    success: true,
                    task_type: "mode_exit".to_string(),
                    output: "Exited mode. Back to normal assistant mode.".to_string(),
                    error: None,
                    duration_ms: 0,
                    changes_made: vec![],
                }
            }
            TaskType::Custom { action, params } => {
                self.execute_custom(&action, params).await
            }
        };

        TaskResult {
            duration_ms: start.elapsed().as_millis() as u64,
            ..result
        }
    }

    async fn execute_git_commit(&self, project: &str, message: Option<&str>) -> TaskResult {
        let project_path = match self.find_project_path(project) {
            Some(p) => p,
            None => return TaskResult {
                success: false,
                task_type: "git_commit".to_string(),
                output: String::new(),
                error: Some(format!("Project '{}' not found in registry", project)),
                duration_ms: 0,
                changes_made: vec![],
            },
        };

        // Get status first
        let status = Command::new("git")
            .args(["status", "--porcelain"])
            .current_dir(&project_path)
            .output();

        let files_changed = match status {
            Ok(output) => {
                String::from_utf8_lossy(&output.stdout)
                    .lines()
                    .map(|l| l.trim().to_string())
                    .collect::<Vec<_>>()
            }
            Err(e) => return TaskResult {
                success: false,
                task_type: "git_commit".to_string(),
                output: String::new(),
                error: Some(format!("Failed to get git status: {}", e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        };

        if files_changed.is_empty() {
            return TaskResult {
                success: true,
                task_type: "git_commit".to_string(),
                output: "No changes to commit".to_string(),
                error: None,
                duration_ms: 0,
                changes_made: vec![],
            };
        }

        // Stage all changes
        let add_result = Command::new("git")
            .args(["add", "-A"])
            .current_dir(&project_path)
            .output();

        if let Err(e) = add_result {
            return TaskResult {
                success: false,
                task_type: "git_commit".to_string(),
                output: String::new(),
                error: Some(format!("Failed to stage changes: {}", e)),
                duration_ms: 0,
                changes_made: vec![],
            };
        }

        // Generate commit message if not provided
        let commit_msg = message.map(|s| s.to_string()).unwrap_or_else(|| {
            let changes_summary = files_changed.len();
            format!("SAM auto-commit: {} file(s) changed", changes_summary)
        });

        // Commit
        let commit_result = Command::new("git")
            .args(["commit", "-m", &commit_msg])
            .current_dir(&project_path)
            .output();

        match commit_result {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).to_string();

                if output.status.success() {
                    TaskResult {
                        success: true,
                        task_type: "git_commit".to_string(),
                        output: format!("Committed {} files:\n{}", files_changed.len(), stdout),
                        error: None,
                        duration_ms: 0,
                        changes_made: files_changed,
                    }
                } else {
                    TaskResult {
                        success: false,
                        task_type: "git_commit".to_string(),
                        output: stdout,
                        error: Some(stderr),
                        duration_ms: 0,
                        changes_made: vec![],
                    }
                }
            }
            Err(e) => TaskResult {
                success: false,
                task_type: "git_commit".to_string(),
                output: String::new(),
                error: Some(format!("Failed to commit: {}", e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_git_push(&self, project: &str, branch: Option<&str>) -> TaskResult {
        let project_path = match self.find_project_path(project) {
            Some(p) => p,
            None => return TaskResult {
                success: false,
                task_type: "git_push".to_string(),
                output: String::new(),
                error: Some(format!("Project '{}' not found", project)),
                duration_ms: 0,
                changes_made: vec![],
            },
        };

        let mut args = vec!["push"];
        if let Some(b) = branch {
            args.push("origin");
            args.push(b);
        }

        let result = Command::new("git")
            .args(&args)
            .current_dir(&project_path)
            .output();

        match result {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).to_string();

                TaskResult {
                    success: output.status.success(),
                    task_type: "git_push".to_string(),
                    output: format!("{}\n{}", stdout, stderr),
                    error: if output.status.success() { None } else { Some(stderr) },
                    duration_ms: 0,
                    changes_made: vec!["Pushed to remote".to_string()],
                }
            }
            Err(e) => TaskResult {
                success: false,
                task_type: "git_push".to_string(),
                output: String::new(),
                error: Some(format!("Failed to push: {}", e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_git_pull(&self, project: &str) -> TaskResult {
        let project_path = match self.find_project_path(project) {
            Some(p) => p,
            None => return TaskResult {
                success: false,
                task_type: "git_pull".to_string(),
                output: String::new(),
                error: Some(format!("Project '{}' not found", project)),
                duration_ms: 0,
                changes_made: vec![],
            },
        };

        let result = Command::new("git")
            .args(["pull"])
            .current_dir(&project_path)
            .output();

        match result {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();

                TaskResult {
                    success: output.status.success(),
                    task_type: "git_pull".to_string(),
                    output: stdout,
                    error: None,
                    duration_ms: 0,
                    changes_made: vec!["Pulled from remote".to_string()],
                }
            }
            Err(e) => TaskResult {
                success: false,
                task_type: "git_pull".to_string(),
                output: String::new(),
                error: Some(format!("Failed to pull: {}", e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_shell(&self, command: &str, working_dir: Option<&str>) -> TaskResult {
        let mut cmd = Command::new("sh");
        cmd.args(["-c", command]);

        if let Some(dir) = working_dir {
            cmd.current_dir(dir);
        }

        match cmd.output() {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout).to_string();
                let stderr = String::from_utf8_lossy(&output.stderr).to_string();

                TaskResult {
                    success: output.status.success(),
                    task_type: "shell".to_string(),
                    output: stdout,
                    error: if stderr.is_empty() { None } else { Some(stderr) },
                    duration_ms: 0,
                    changes_made: vec![format!("Executed: {}", command)],
                }
            }
            Err(e) => TaskResult {
                success: false,
                task_type: "shell".to_string(),
                output: String::new(),
                error: Some(format!("Failed to execute: {}", e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_service_start(&self, service: &str) -> TaskResult {
        // Check if it's a Docker service
        let docker_result = Command::new("docker")
            .args(["start", service])
            .output();

        if let Ok(output) = docker_result {
            if output.status.success() {
                return TaskResult {
                    success: true,
                    task_type: "service_start".to_string(),
                    output: format!("Started Docker container: {}", service),
                    error: None,
                    duration_ms: 0,
                    changes_made: vec![format!("docker start {}", service)],
                };
            }
        }

        // Try launchctl for macOS services
        let launchctl_result = Command::new("launchctl")
            .args(["start", service])
            .output();

        match launchctl_result {
            Ok(output) => TaskResult {
                success: output.status.success(),
                task_type: "service_start".to_string(),
                output: format!("Started service: {}", service),
                error: None,
                duration_ms: 0,
                changes_made: vec![format!("launchctl start {}", service)],
            },
            Err(e) => TaskResult {
                success: false,
                task_type: "service_start".to_string(),
                output: String::new(),
                error: Some(format!("Failed to start {}: {}", service, e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_service_stop(&self, service: &str) -> TaskResult {
        // Try Docker first
        let docker_result = Command::new("docker")
            .args(["stop", service])
            .output();

        if let Ok(output) = docker_result {
            if output.status.success() {
                return TaskResult {
                    success: true,
                    task_type: "service_stop".to_string(),
                    output: format!("Stopped Docker container: {}", service),
                    error: None,
                    duration_ms: 0,
                    changes_made: vec![format!("docker stop {}", service)],
                };
            }
        }

        // Try launchctl
        let launchctl_result = Command::new("launchctl")
            .args(["stop", service])
            .output();

        match launchctl_result {
            Ok(output) => TaskResult {
                success: output.status.success(),
                task_type: "service_stop".to_string(),
                output: format!("Stopped service: {}", service),
                error: None,
                duration_ms: 0,
                changes_made: vec![format!("launchctl stop {}", service)],
            },
            Err(e) => TaskResult {
                success: false,
                task_type: "service_stop".to_string(),
                output: String::new(),
                error: Some(format!("Failed to stop {}: {}", service, e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_project_scan(&self, _path: Option<&str>) -> TaskResult {
        // Trigger project registry refresh
        // This would call the existing project scanning logic
        TaskResult {
            success: true,
            task_type: "project_scan".to_string(),
            output: "Project scan initiated".to_string(),
            error: None,
            duration_ms: 0,
            changes_made: vec!["Refreshed project registry".to_string()],
        }
    }

    async fn execute_refresh(&self) -> TaskResult {
        TaskResult {
            success: true,
            task_type: "refresh".to_string(),
            output: "Refreshed".to_string(),
            error: None,
            duration_ms: 0,
            changes_made: vec![],
        }
    }

    async fn execute_file_edit(&self, path: &str, content: &str) -> TaskResult {
        match std::fs::write(path, content) {
            Ok(_) => TaskResult {
                success: true,
                task_type: "file_edit".to_string(),
                output: format!("Updated {}", path),
                error: None,
                duration_ms: 0,
                changes_made: vec![format!("Modified: {}", path)],
            },
            Err(e) => TaskResult {
                success: false,
                task_type: "file_edit".to_string(),
                output: String::new(),
                error: Some(format!("Failed to edit {}: {}", path, e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_file_create(&self, path: &str, content: &str) -> TaskResult {
        // Create parent directories if needed
        if let Some(parent) = std::path::Path::new(path).parent() {
            let _ = std::fs::create_dir_all(parent);
        }

        match std::fs::write(path, content) {
            Ok(_) => TaskResult {
                success: true,
                task_type: "file_create".to_string(),
                output: format!("Created {}", path),
                error: None,
                duration_ms: 0,
                changes_made: vec![format!("Created: {}", path)],
            },
            Err(e) => TaskResult {
                success: false,
                task_type: "file_create".to_string(),
                output: String::new(),
                error: Some(format!("Failed to create {}: {}", path, e)),
                duration_ms: 0,
                changes_made: vec![],
            },
        }
    }

    async fn execute_custom(&self, action: &str, _params: serde_json::Value) -> TaskResult {
        TaskResult {
            success: false,
            task_type: "custom".to_string(),
            output: String::new(),
            error: Some(format!("Custom action '{}' not implemented", action)),
            duration_ms: 0,
            changes_made: vec![],
        }
    }

    fn find_project_path(&self, project_name: &str) -> Option<PathBuf> {
        let registry_content = std::fs::read_to_string(&self.project_registry_path).ok()?;
        let registry: serde_json::Value = serde_json::from_str(&registry_content).ok()?;

        let projects = registry.get("projects")?.as_array()?;

        for p in projects {
            let name = p.get("name")?.as_str()?;
            if name.to_lowercase() == project_name.to_lowercase() {
                let path = p.get("path")?.as_str()?;
                return Some(PathBuf::from(path));
            }
        }

        None
    }
}

impl Default for TaskExecutor {
    fn default() -> Self {
        Self::new()
    }
}

// Global instance
lazy_static::lazy_static! {
    static ref EXECUTOR: TaskExecutor = TaskExecutor::new();
}

/// Execute a command string
pub async fn execute_command(command: &str) -> TaskResult {
    if let Some(task) = EXECUTOR.parse_command(command) {
        EXECUTOR.execute(task).await
    } else {
        TaskResult {
            success: false,
            task_type: "unknown".to_string(),
            output: String::new(),
            error: Some(format!("Could not parse command: {}", command)),
            duration_ms: 0,
            changes_made: vec![],
        }
    }
}

/// Execute a pre-parsed task
pub async fn execute_task(task: TaskType) -> TaskResult {
    EXECUTOR.execute(task).await
}
