// Parallel Agents - Execute multiple agents simultaneously
//
// Enables Cursor-style parallel agent execution:
// - Up to 8 concurrent agents
// - Git worktree isolation per agent
// - Result aggregation and conflict resolution
// - Side-by-side comparison of solutions

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tokio::sync::mpsc;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelTask {
    pub id: String,
    pub prompt: String,
    pub model: Option<String>,
    pub working_dir: PathBuf,
    pub use_worktree: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentResult {
    pub agent_id: String,
    pub task_id: String,
    pub status: AgentStatus,
    pub output: String,
    pub files_modified: Vec<String>,
    pub execution_time_ms: u64,
    pub tokens_used: u32,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum AgentStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelExecutionResult {
    pub task_id: String,
    pub total_agents: u32,
    pub completed: u32,
    pub failed: u32,
    pub results: Vec<AgentResult>,
    pub best_result: Option<String>, // agent_id of best result
    pub conflicts: Vec<FileConflict>,
    pub total_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileConflict {
    pub file_path: String,
    pub agent_ids: Vec<String>,
    pub resolution: Option<ConflictResolution>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ConflictResolution {
    UseAgent(String),      // Use specific agent's version
    Merge,                 // Attempt to merge
    Manual,                // Requires manual resolution
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelConfig {
    pub max_concurrent: u32,
    pub use_worktrees: bool,
    pub timeout_per_agent_ms: u64,
    pub auto_select_best: bool,
    pub cleanup_worktrees: bool,
}

impl Default for ParallelConfig {
    fn default() -> Self {
        Self {
            max_concurrent: 4,
            use_worktrees: true,
            timeout_per_agent_ms: 300000, // 5 minutes
            auto_select_best: true,
            cleanup_worktrees: true,
        }
    }
}

// =============================================================================
// PARALLEL EXECUTOR
// =============================================================================

pub struct ParallelExecutor {
    config: ParallelConfig,
    running_agents: Arc<Mutex<HashMap<String, AgentHandle>>>,
    worktree_manager: WorktreeManager,
}

struct AgentHandle {
    task_id: String,
    cancel_tx: mpsc::Sender<()>,
    status: AgentStatus,
}

impl ParallelExecutor {
    pub fn new(config: ParallelConfig) -> Self {
        Self {
            config,
            running_agents: Arc::new(Mutex::new(HashMap::new())),
            worktree_manager: WorktreeManager::new(),
        }
    }

    /// Execute multiple tasks in parallel
    pub async fn execute_parallel(
        &mut self,
        tasks: Vec<ParallelTask>,
        on_progress: impl Fn(String, AgentStatus) + Send + Sync + 'static,
    ) -> Result<ParallelExecutionResult, String> {
        let start = std::time::Instant::now();
        let task_id = uuid::Uuid::new_v4().to_string();

        // Limit concurrent agents
        let max_concurrent = self.config.max_concurrent.min(8) as usize;
        let tasks_to_run = tasks.into_iter().take(max_concurrent).collect::<Vec<_>>();
        let total_agents = tasks_to_run.len() as u32;

        // Prepare worktrees if enabled
        let worktrees = if self.config.use_worktrees {
            self.prepare_worktrees(&tasks_to_run).await?
        } else {
            HashMap::new()
        };

        // Create channels for results
        let (result_tx, mut result_rx) = mpsc::channel::<AgentResult>(max_concurrent);

        // Spawn agents
        let mut handles = Vec::new();
        for task in tasks_to_run {
            let agent_id = uuid::Uuid::new_v4().to_string();
            let tx = result_tx.clone();
            let worktree_path = worktrees.get(&task.id).cloned();
            let timeout = self.config.timeout_per_agent_ms;

            let (cancel_tx, cancel_rx) = mpsc::channel(1);

            // Register agent
            {
                let mut agents = self.running_agents.lock().unwrap();
                agents.insert(agent_id.clone(), AgentHandle {
                    task_id: task.id.clone(),
                    cancel_tx,
                    status: AgentStatus::Pending,
                });
            }

            let agent_id_clone = agent_id.clone();
            let handle = tokio::spawn(async move {
                let result = Self::run_agent(
                    agent_id_clone,
                    task,
                    worktree_path,
                    timeout,
                    cancel_rx,
                ).await;
                let _ = tx.send(result).await;
            });

            handles.push((agent_id, handle));
        }

        // Drop the sender so receiver knows when all are done
        drop(result_tx);

        // Collect results
        let mut results = Vec::new();
        let on_progress = Arc::new(on_progress);

        while let Some(result) = result_rx.recv().await {
            on_progress(result.agent_id.clone(), result.status);
            results.push(result);
        }

        // Wait for all handles
        for (_, handle) in handles {
            let _ = handle.await;
        }

        // Detect conflicts
        let conflicts = self.detect_conflicts(&results);

        // Select best result
        let best_result = if self.config.auto_select_best {
            self.select_best_result(&results)
        } else {
            None
        };

        // Cleanup worktrees
        if self.config.cleanup_worktrees {
            for (_, path) in worktrees {
                self.worktree_manager.remove_worktree(&path).await.ok();
            }
        }

        let completed = results.iter().filter(|r| r.status == AgentStatus::Completed).count() as u32;
        let failed = results.iter().filter(|r| r.status == AgentStatus::Failed).count() as u32;

        Ok(ParallelExecutionResult {
            task_id,
            total_agents,
            completed,
            failed,
            results,
            best_result,
            conflicts,
            total_time_ms: start.elapsed().as_millis() as u64,
        })
    }

    /// Run a single agent
    async fn run_agent(
        agent_id: String,
        task: ParallelTask,
        worktree_path: Option<PathBuf>,
        timeout_ms: u64,
        mut cancel_rx: mpsc::Receiver<()>,
    ) -> AgentResult {
        let start = std::time::Instant::now();
        let working_dir = worktree_path.unwrap_or(task.working_dir);

        // Create timeout future
        let timeout = tokio::time::sleep(std::time::Duration::from_millis(timeout_ms));

        tokio::select! {
            // Agent execution
            result = Self::execute_agent_task(&task.prompt, &working_dir, task.model.as_deref()) => {
                match result {
                    Ok((output, files)) => AgentResult {
                        agent_id,
                        task_id: task.id,
                        status: AgentStatus::Completed,
                        output,
                        files_modified: files,
                        execution_time_ms: start.elapsed().as_millis() as u64,
                        tokens_used: 0,
                        error: None,
                    },
                    Err(e) => AgentResult {
                        agent_id,
                        task_id: task.id,
                        status: AgentStatus::Failed,
                        output: String::new(),
                        files_modified: vec![],
                        execution_time_ms: start.elapsed().as_millis() as u64,
                        tokens_used: 0,
                        error: Some(e),
                    },
                }
            }

            // Timeout
            _ = timeout => {
                AgentResult {
                    agent_id,
                    task_id: task.id,
                    status: AgentStatus::Failed,
                    output: String::new(),
                    files_modified: vec![],
                    execution_time_ms: start.elapsed().as_millis() as u64,
                    tokens_used: 0,
                    error: Some("Agent timed out".to_string()),
                }
            }

            // Cancellation
            _ = cancel_rx.recv() => {
                AgentResult {
                    agent_id,
                    task_id: task.id,
                    status: AgentStatus::Cancelled,
                    output: String::new(),
                    files_modified: vec![],
                    execution_time_ms: start.elapsed().as_millis() as u64,
                    tokens_used: 0,
                    error: Some("Agent cancelled".to_string()),
                }
            }
        }
    }

    /// Execute agent task (simplified - would call unified_agent in production)
    async fn execute_agent_task(
        prompt: &str,
        _working_dir: &PathBuf,
        model: Option<&str>,
    ) -> Result<(String, Vec<String>), String> {
        // In production, this would call the unified agent
        // For now, we use a direct Ollama call

        use crate::ollama::query_ollama;

        let model_name = model.unwrap_or("qwen2.5-coder:1.5b");

        // Build a simple atomic prompt
        let full_prompt = format!(
            "You are a coding assistant. Complete this task:\n\n{}\n\nProvide a direct, actionable response.",
            prompt
        );

        let response = query_ollama(
            full_prompt,
            Some(model_name.to_string()),
        ).await.map_err(|e| format!("Ollama error: {}", e))?;

        Ok((response, vec![]))
    }

    /// Prepare git worktrees for isolated execution
    async fn prepare_worktrees(&mut self, tasks: &[ParallelTask]) -> Result<HashMap<String, PathBuf>, String> {
        let mut worktrees = HashMap::new();

        for task in tasks {
            if task.use_worktree {
                let worktree_path = self.worktree_manager
                    .create_worktree(&task.working_dir, &task.id)
                    .await?;
                worktrees.insert(task.id.clone(), worktree_path);
            }
        }

        Ok(worktrees)
    }

    /// Detect file conflicts between agent results
    fn detect_conflicts(&self, results: &[AgentResult]) -> Vec<FileConflict> {
        let mut file_to_agents: HashMap<String, Vec<String>> = HashMap::new();

        for result in results {
            if result.status == AgentStatus::Completed {
                for file in &result.files_modified {
                    file_to_agents
                        .entry(file.clone())
                        .or_default()
                        .push(result.agent_id.clone());
                }
            }
        }

        file_to_agents
            .into_iter()
            .filter(|(_, agents)| agents.len() > 1)
            .map(|(file_path, agent_ids)| FileConflict {
                file_path,
                agent_ids,
                resolution: None,
            })
            .collect()
    }

    /// Select the best result based on heuristics
    fn select_best_result(&self, results: &[AgentResult]) -> Option<String> {
        results
            .iter()
            .filter(|r| r.status == AgentStatus::Completed && r.error.is_none())
            .min_by_key(|r| {
                // Prefer: fewer files modified, faster execution, more output
                let file_penalty = r.files_modified.len() as i64 * 10;
                let time_penalty = (r.execution_time_ms / 1000) as i64;
                let output_bonus = -(r.output.len() as i64 / 100);
                file_penalty + time_penalty + output_bonus
            })
            .map(|r| r.agent_id.clone())
    }

    /// Cancel a running agent
    pub fn cancel_agent(&self, agent_id: &str) -> Result<(), String> {
        let agents = self.running_agents.lock().unwrap();
        if let Some(handle) = agents.get(agent_id) {
            let _ = handle.cancel_tx.try_send(());
            Ok(())
        } else {
            Err(format!("Agent {} not found", agent_id))
        }
    }

    /// Cancel all running agents
    pub fn cancel_all(&self) {
        let agents = self.running_agents.lock().unwrap();
        for (_, handle) in agents.iter() {
            let _ = handle.cancel_tx.try_send(());
        }
    }

    /// Get status of running agents
    pub fn get_status(&self) -> Vec<(String, AgentStatus)> {
        let agents = self.running_agents.lock().unwrap();
        agents.iter()
            .map(|(id, h)| (id.clone(), h.status))
            .collect()
    }

    /// Get stats
    pub fn stats(&self) -> ParallelStats {
        let agents = self.running_agents.lock().unwrap();
        ParallelStats {
            running_agents: agents.len(),
            max_concurrent: self.config.max_concurrent as usize,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ParallelStats {
    pub running_agents: usize,
    pub max_concurrent: usize,
}

// =============================================================================
// WORKTREE MANAGER
// =============================================================================

struct WorktreeManager {
    base_dir: PathBuf,
}

impl WorktreeManager {
    fn new() -> Self {
        Self {
            base_dir: std::env::temp_dir().join("sam_worktrees"),
        }
    }

    /// Create a git worktree for isolated execution
    async fn create_worktree(&self, repo_path: &PathBuf, task_id: &str) -> Result<PathBuf, String> {
        let worktree_path = self.base_dir.join(task_id);

        // Ensure base directory exists
        std::fs::create_dir_all(&self.base_dir)
            .map_err(|e| format!("Failed to create worktree base dir: {}", e))?;

        // Create worktree
        let output = tokio::process::Command::new("git")
            .args(["worktree", "add", "-d"])
            .arg(&worktree_path)
            .arg("HEAD")
            .current_dir(repo_path)
            .output()
            .await
            .map_err(|e| format!("Failed to create worktree: {}", e))?;

        if !output.status.success() {
            // Fallback: just copy the directory
            self.copy_directory(repo_path, &worktree_path).await?;
        }

        Ok(worktree_path)
    }

    /// Remove a git worktree
    async fn remove_worktree(&self, worktree_path: &PathBuf) -> Result<(), String> {
        // Try git worktree remove first
        let _ = tokio::process::Command::new("git")
            .args(["worktree", "remove", "--force"])
            .arg(worktree_path)
            .output()
            .await;

        // Also remove directory if it still exists
        if worktree_path.exists() {
            std::fs::remove_dir_all(worktree_path)
                .map_err(|e| format!("Failed to remove worktree directory: {}", e))?;
        }

        Ok(())
    }

    /// Copy directory as fallback when git worktree fails
    async fn copy_directory(&self, src: &PathBuf, dst: &PathBuf) -> Result<(), String> {
        std::fs::create_dir_all(dst)
            .map_err(|e| format!("Failed to create destination: {}", e))?;

        // Use system cp for efficiency
        let output = tokio::process::Command::new("cp")
            .args(["-r"])
            .arg(src)
            .arg(dst)
            .output()
            .await
            .map_err(|e| format!("Failed to copy directory: {}", e))?;

        if !output.status.success() {
            return Err("Copy failed".to_string());
        }

        Ok(())
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref PARALLEL_EXECUTOR: Mutex<ParallelExecutor> = Mutex::new(ParallelExecutor::new(ParallelConfig::default()));
}

pub fn executor() -> std::sync::MutexGuard<'static, ParallelExecutor> {
    PARALLEL_EXECUTOR.lock().unwrap()
}

/// Execute tasks in parallel
pub async fn execute_parallel(
    tasks: Vec<ParallelTask>,
    on_progress: impl Fn(String, AgentStatus) + Send + Sync + 'static,
) -> Result<ParallelExecutionResult, String> {
    let mut exec = executor();
    exec.execute_parallel(tasks, on_progress).await
}

/// Create a parallel task
pub fn create_task(prompt: &str, working_dir: &PathBuf) -> ParallelTask {
    ParallelTask {
        id: uuid::Uuid::new_v4().to_string(),
        prompt: prompt.to_string(),
        model: None,
        working_dir: working_dir.clone(),
        use_worktree: true,
    }
}

/// Cancel all running agents
pub fn cancel_all() {
    executor().cancel_all();
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default() {
        let config = ParallelConfig::default();
        assert_eq!(config.max_concurrent, 4);
        assert!(config.use_worktrees);
    }

    #[test]
    fn test_create_task() {
        let task = create_task("test prompt", &PathBuf::from("/tmp"));
        assert_eq!(task.prompt, "test prompt");
        assert!(task.use_worktree);
    }

    #[test]
    fn test_detect_conflicts() {
        let executor = ParallelExecutor::new(ParallelConfig::default());

        let results = vec![
            AgentResult {
                agent_id: "a1".to_string(),
                task_id: "t1".to_string(),
                status: AgentStatus::Completed,
                output: "".to_string(),
                files_modified: vec!["file1.rs".to_string(), "file2.rs".to_string()],
                execution_time_ms: 100,
                tokens_used: 0,
                error: None,
            },
            AgentResult {
                agent_id: "a2".to_string(),
                task_id: "t2".to_string(),
                status: AgentStatus::Completed,
                output: "".to_string(),
                files_modified: vec!["file1.rs".to_string(), "file3.rs".to_string()],
                execution_time_ms: 100,
                tokens_used: 0,
                error: None,
            },
        ];

        let conflicts = executor.detect_conflicts(&results);
        assert_eq!(conflicts.len(), 1);
        assert_eq!(conflicts[0].file_path, "file1.rs");
        assert_eq!(conflicts[0].agent_ids.len(), 2);
    }

    #[test]
    fn test_select_best_result() {
        let executor = ParallelExecutor::new(ParallelConfig::default());

        let results = vec![
            AgentResult {
                agent_id: "slow".to_string(),
                task_id: "t1".to_string(),
                status: AgentStatus::Completed,
                output: "short".to_string(),
                files_modified: vec!["a.rs".to_string(), "b.rs".to_string(), "c.rs".to_string()],
                execution_time_ms: 10000,
                tokens_used: 0,
                error: None,
            },
            AgentResult {
                agent_id: "fast".to_string(),
                task_id: "t1".to_string(),
                status: AgentStatus::Completed,
                output: "longer output with more content".to_string(),
                files_modified: vec!["a.rs".to_string()],
                execution_time_ms: 1000,
                tokens_used: 0,
                error: None,
            },
        ];

        let best = executor.select_best_result(&results);
        assert_eq!(best, Some("fast".to_string()));
    }
}
