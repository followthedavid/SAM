// Safe Executor for SAM
//
// Wraps tool execution with:
// - Persistent state tracking
// - File backup before modifications
// - Protected file checks
// - Checkpoint/resume capability
// - Watchdog integration

use std::process::Command;
use std::path::Path;
use serde::{Deserialize, Serialize};

use crate::scaffolding::persistence::{
    PersistentTask, TaskStatus, FileBackup, ProtectedFiles, ensure_dirs
};
use crate::scaffolding::lean_agent::{TaskPhase, DefaultActions, LeanState, OutputParser};

/// Result of a safe execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionResult {
    pub success: bool,
    pub output: String,
    pub backup_path: Option<String>,
    pub blocked_reason: Option<String>,
}

/// Safe executor that protects against self-destruction
pub struct SafeExecutor {
    task: PersistentTask,
    protected: ProtectedFiles,
    lean_state: LeanState,
}

impl SafeExecutor {
    /// Create a new safe executor for a task
    pub fn new(task_id: &str, description: &str, work_dir: &str) -> Self {
        let _ = ensure_dirs();

        // Try to resume existing task, or create new one
        let task = PersistentTask::resume_from_checkpoint(task_id)
            .unwrap_or_else(|_| PersistentTask::new(task_id, description, work_dir));

        let protected = ProtectedFiles::load()
            .unwrap_or_else(|_| ProtectedFiles::new());

        let lean_state = LeanState::new(description.to_string(), work_dir.to_string());

        Self { task, protected, lean_state }
    }

    /// Resume an existing task
    pub fn resume(task_id: &str) -> Result<Self, String> {
        let task = PersistentTask::resume_from_checkpoint(task_id)
            .map_err(|e| format!("Failed to resume task: {}", e))?;

        let protected = ProtectedFiles::load()
            .unwrap_or_else(|_| ProtectedFiles::new());

        let lean_state = LeanState::new(task.description.clone(), task.work_dir.clone());

        Ok(Self { task, protected, lean_state })
    }

    /// Get current phase
    pub fn current_phase(&self) -> &str {
        &self.task.phase
    }

    /// Get task status
    pub fn status(&self) -> TaskStatus {
        self.task.status
    }

    /// Execute a shell command safely
    pub fn execute_shell(&mut self, command: &str) -> ExecutionResult {
        // Log the attempt
        eprintln!("[SafeExecutor] Executing: {}", command);

        // Check for dangerous patterns
        if self.is_dangerous_command(command) {
            let reason = format!("Blocked dangerous command: {}", command);
            eprintln!("[SafeExecutor] {}", reason);
            return ExecutionResult {
                success: false,
                output: String::new(),
                backup_path: None,
                blocked_reason: Some(reason),
            };
        }

        // Execute the command
        let output = Command::new("sh")
            .arg("-c")
            .arg(command)
            .output();

        match output {
            Ok(out) => {
                let stdout = String::from_utf8_lossy(&out.stdout).to_string();
                let stderr = String::from_utf8_lossy(&out.stderr).to_string();
                let combined = if stderr.is_empty() {
                    stdout.clone()
                } else {
                    format!("{}\n{}", stdout, stderr)
                };

                let success = out.status.success();

                // Record the command
                self.task.record_command(command, &combined, success);

                ExecutionResult {
                    success,
                    output: combined,
                    backup_path: None,
                    blocked_reason: None,
                }
            }
            Err(e) => {
                let error = format!("Command failed: {}", e);
                self.task.record_command(command, &error, false);

                ExecutionResult {
                    success: false,
                    output: error,
                    backup_path: None,
                    blocked_reason: None,
                }
            }
        }
    }

    /// Write a file safely (with backup)
    pub fn write_file(&mut self, path: &str, content: &str) -> ExecutionResult {
        // Check if protected
        if self.protected.is_protected(path) {
            let reason = format!("Cannot modify protected path: {}", path);
            eprintln!("[SafeExecutor] {}", reason);
            return ExecutionResult {
                success: false,
                output: String::new(),
                backup_path: None,
                blocked_reason: Some(reason),
            };
        }

        // Backup existing file
        let backup_path = if Path::new(path).exists() {
            match FileBackup::backup(path) {
                Ok(bp) => {
                    eprintln!("[SafeExecutor] Backed up {} to {}", path, bp);
                    Some(bp)
                }
                Err(e) => {
                    eprintln!("[SafeExecutor] Backup failed: {}", e);
                    None
                }
            }
        } else {
            None
        };

        // Write the file
        match std::fs::write(path, content) {
            Ok(_) => {
                if Path::new(path).exists() {
                    self.task.mark_file_modified(path);
                } else {
                    self.task.mark_file_created(path);
                }

                ExecutionResult {
                    success: true,
                    output: format!("Wrote {} bytes to {}", content.len(), path),
                    backup_path,
                    blocked_reason: None,
                }
            }
            Err(e) => ExecutionResult {
                success: false,
                output: format!("Failed to write: {}", e),
                backup_path,
                blocked_reason: None,
            },
        }
    }

    /// Read a file safely
    pub fn read_file(&self, path: &str) -> ExecutionResult {
        match std::fs::read_to_string(path) {
            Ok(content) => ExecutionResult {
                success: true,
                output: content,
                backup_path: None,
                blocked_reason: None,
            },
            Err(e) => ExecutionResult {
                success: false,
                output: format!("Failed to read: {}", e),
                backup_path: None,
                blocked_reason: None,
            },
        }
    }

    /// Advance to next phase
    pub fn advance_phase(&mut self) {
        let current = match self.task.phase.as_str() {
            "Extract" => TaskPhase::Extract,
            "Unpack" => TaskPhase::Unpack,
            "Analyze" => TaskPhase::Analyze,
            "Identify" => TaskPhase::Identify,
            "Research" => TaskPhase::Research,
            "InstallTools" => TaskPhase::InstallTools,
            "Implement" => TaskPhase::Implement,
            "Test" => TaskPhase::Test,
            "QualityCheck" => TaskPhase::QualityCheck,
            "Verify" => TaskPhase::Verify,
            _ => TaskPhase::Complete,
        };

        if let Some(next) = current.next() {
            let phase_name = format!("{:?}", next);
            self.task.advance_phase(&phase_name);
            self.lean_state.advance();
            eprintln!("[SafeExecutor] Advanced to phase: {}", phase_name);
        }
    }

    /// Get default action for current phase
    pub fn get_default_action(&self) -> Option<String> {
        let phase = match self.task.phase.as_str() {
            "Extract" => TaskPhase::Extract,
            "Unpack" => TaskPhase::Unpack,
            "Analyze" => TaskPhase::Analyze,
            "Identify" => TaskPhase::Identify,
            "Research" => TaskPhase::Research,
            "InstallTools" => TaskPhase::InstallTools,
            "Implement" => TaskPhase::Implement,
            "Test" => TaskPhase::Test,
            "QualityCheck" => TaskPhase::QualityCheck,
            "Verify" => TaskPhase::Verify,
            _ => return None,
        };

        DefaultActions::for_phase(&phase, &self.lean_state)
    }

    /// Add a finding
    pub fn add_finding(&mut self, finding: &str) {
        self.task.add_finding(finding);
        self.lean_state.add_finding(finding.to_string());
    }

    /// Mark task as completed
    pub fn complete(&mut self) {
        self.task.complete();
    }

    /// Mark task as failed
    pub fn fail(&mut self, error: &str) {
        self.task.fail(error);
    }

    /// Checkpoint current state
    pub fn checkpoint(&self) {
        let _ = self.task.checkpoint();
    }

    /// Check if command is dangerous
    fn is_dangerous_command(&self, command: &str) -> bool {
        let dangerous_patterns = [
            "rm -rf /",
            "rm -rf ~",
            "rm -rf $HOME",
            "> /dev/sda",
            "mkfs",
            "dd if=/dev/zero",
            ":(){ :|:& };:",  // Fork bomb
            "chmod -R 777 /",
            "chown -R",
        ];

        for pattern in dangerous_patterns {
            if command.contains(pattern) {
                return true;
            }
        }

        // Check for rm/mv/cp on protected paths
        if command.starts_with("rm ") || command.starts_with("mv ") {
            for word in command.split_whitespace() {
                if self.protected.is_protected(word) {
                    return true;
                }
            }
        }

        false
    }

    /// Parse LLM response and extract command
    pub fn parse_response(&self, response: &str) -> Option<String> {
        OutputParser::extract_command(response)
    }

    /// Get task summary
    pub fn summary(&self) -> serde_json::Value {
        serde_json::json!({
            "id": self.task.id,
            "description": self.task.description,
            "phase": self.task.phase,
            "phase_index": self.task.phase_index,
            "total_phases": self.task.total_phases,
            "status": format!("{:?}", self.task.status),
            "commands_executed": self.task.executed_commands.len(),
            "findings": self.task.findings.len(),
            "files_created": self.task.files_created.len(),
            "files_modified": self.task.files_modified.len(),
        })
    }
}

/// Run a task autonomously with the safe executor
pub async fn run_autonomous_task(
    task_id: &str,
    description: &str,
    work_dir: &str,
    max_iterations: u32,
) -> Result<String, String> {
    let mut executor = SafeExecutor::new(task_id, description, work_dir);

    eprintln!("[Autonomous] Starting task: {}", description);
    eprintln!("[Autonomous] Work dir: {}", work_dir);

    for iteration in 0..max_iterations {
        eprintln!("[Autonomous] Iteration {} - Phase: {}", iteration, executor.current_phase());

        if executor.status() == TaskStatus::Completed {
            eprintln!("[Autonomous] Task completed successfully");
            return Ok(format!("Task completed in {} iterations", iteration));
        }

        if executor.status() == TaskStatus::Failed {
            return Err("Task failed".to_string());
        }

        // Get default action for current phase
        let action = match executor.get_default_action() {
            Some(a) => a,
            None => {
                executor.complete();
                return Ok("Task completed (no more actions)".to_string());
            }
        };

        eprintln!("[Autonomous] Executing: {}", action);

        // Execute the action
        let result = executor.execute_shell(&action);

        if result.success {
            eprintln!("[Autonomous] Success: {}", result.output.lines().take(3).collect::<Vec<_>>().join("\n"));
            executor.add_finding(&format!("Phase {} completed", executor.current_phase()));
            executor.advance_phase();
        } else if let Some(reason) = result.blocked_reason {
            eprintln!("[Autonomous] Blocked: {}", reason);
            executor.fail(&reason);
            return Err(reason);
        } else {
            eprintln!("[Autonomous] Failed: {}", result.output);
            // Don't fail immediately - try to recover by advancing
            executor.advance_phase();
        }

        executor.checkpoint();

        // Small delay to prevent overwhelming
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
    }

    Err(format!("Max iterations ({}) exceeded", max_iterations))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_dangerous_command_detection() {
        let executor = SafeExecutor::new("test", "Test", "/tmp");
        assert!(executor.is_dangerous_command("rm -rf /"));
        assert!(executor.is_dangerous_command(":(){ :|:& };:"));
        assert!(!executor.is_dangerous_command("ls -la"));
        assert!(!executor.is_dangerous_command("cat /tmp/test.txt"));
    }
}
