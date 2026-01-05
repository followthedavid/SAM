// Background Tasks - Async task execution with status tracking
//
// Like Claude Code's background agents:
// 1. Start long-running tasks in background
// 2. Track progress and status
// 3. Notify on completion
// 4. Allow cancellation

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BackgroundTask {
    pub id: String,
    pub name: String,
    pub description: String,
    pub task_type: TaskType,
    pub status: TaskStatus,
    pub progress: TaskProgress,
    pub created_at: u64,
    pub started_at: Option<u64>,
    pub completed_at: Option<u64>,
    pub result: Option<TaskResult>,
    pub cancellation_requested: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TaskType {
    CodeIndexing,
    FileSearch,
    Refactor,
    Build,
    Test,
    LLMGeneration,
    FileOperation,
    Custom(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TaskStatus {
    Queued,
    Running,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TaskProgress {
    pub current: u32,
    pub total: u32,
    pub message: String,
    pub percent: f32,
}

impl TaskProgress {
    pub fn new(total: u32) -> Self {
        Self {
            current: 0,
            total,
            message: String::new(),
            percent: 0.0,
        }
    }

    pub fn update(&mut self, current: u32, message: &str) {
        self.current = current;
        self.message = message.to_string();
        self.percent = if self.total > 0 {
            (current as f32 / self.total as f32) * 100.0
        } else {
            0.0
        };
    }

    pub fn complete(&mut self) {
        self.current = self.total;
        self.percent = 100.0;
        self.message = "Completed".to_string();
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskResult {
    pub success: bool,
    pub output: String,
    pub artifacts: Vec<String>,  // File paths or other outputs
    pub duration_ms: u64,
}

// =============================================================================
// TASK MANAGER
// =============================================================================

pub struct TaskManager {
    tasks: HashMap<String, BackgroundTask>,
    task_handles: HashMap<String, Arc<Mutex<bool>>>,  // Cancellation tokens
    max_concurrent: usize,
    running_count: usize,
}

impl TaskManager {
    pub fn new() -> Self {
        Self {
            tasks: HashMap::new(),
            task_handles: HashMap::new(),
            max_concurrent: 4,  // Max 4 concurrent background tasks
            running_count: 0,
        }
    }

    /// Create a new background task
    pub fn create_task(&mut self, name: &str, description: &str, task_type: TaskType) -> String {
        let id = uuid::Uuid::new_v4().to_string();

        let task = BackgroundTask {
            id: id.clone(),
            name: name.to_string(),
            description: description.to_string(),
            task_type,
            status: TaskStatus::Queued,
            progress: TaskProgress::default(),
            created_at: now_timestamp(),
            started_at: None,
            completed_at: None,
            result: None,
            cancellation_requested: false,
        };

        self.tasks.insert(id.clone(), task);
        self.task_handles.insert(id.clone(), Arc::new(Mutex::new(false)));

        id
    }

    /// Start a task
    pub fn start_task(&mut self, task_id: &str) -> Result<(), String> {
        if self.running_count >= self.max_concurrent {
            return Err("Maximum concurrent tasks reached".to_string());
        }

        let task = self.tasks.get_mut(task_id)
            .ok_or("Task not found")?;

        if task.status != TaskStatus::Queued {
            return Err("Task is not in queued state".to_string());
        }

        task.status = TaskStatus::Running;
        task.started_at = Some(now_timestamp());
        self.running_count += 1;

        Ok(())
    }

    /// Update task progress
    pub fn update_progress(&mut self, task_id: &str, current: u32, message: &str) {
        if let Some(task) = self.tasks.get_mut(task_id) {
            task.progress.update(current, message);
        }
    }

    /// Set task total for progress tracking
    pub fn set_total(&mut self, task_id: &str, total: u32) {
        if let Some(task) = self.tasks.get_mut(task_id) {
            task.progress.total = total;
        }
    }

    /// Complete a task successfully
    pub fn complete_task(&mut self, task_id: &str, output: String, artifacts: Vec<String>) {
        if let Some(task) = self.tasks.get_mut(task_id) {
            let duration_ms = task.started_at
                .map(|start| now_timestamp() - start)
                .unwrap_or(0) * 1000;

            task.status = TaskStatus::Completed;
            task.completed_at = Some(now_timestamp());
            task.progress.complete();
            task.result = Some(TaskResult {
                success: true,
                output,
                artifacts,
                duration_ms,
            });

            self.running_count = self.running_count.saturating_sub(1);
        }
    }

    /// Fail a task
    pub fn fail_task(&mut self, task_id: &str, error: String) {
        if let Some(task) = self.tasks.get_mut(task_id) {
            let duration_ms = task.started_at
                .map(|start| now_timestamp() - start)
                .unwrap_or(0) * 1000;

            task.status = TaskStatus::Failed;
            task.completed_at = Some(now_timestamp());
            task.result = Some(TaskResult {
                success: false,
                output: error,
                artifacts: vec![],
                duration_ms,
            });

            self.running_count = self.running_count.saturating_sub(1);
        }
    }

    /// Request task cancellation
    pub fn cancel_task(&mut self, task_id: &str) -> Result<(), String> {
        let task = self.tasks.get_mut(task_id)
            .ok_or("Task not found")?;

        if task.status != TaskStatus::Running && task.status != TaskStatus::Queued {
            return Err("Task cannot be cancelled".to_string());
        }

        task.cancellation_requested = true;

        // Set cancellation token
        if let Some(token) = self.task_handles.get(task_id) {
            if let Ok(mut cancel) = token.lock() {
                *cancel = true;
            }
        }

        // If queued, immediately mark as cancelled
        if task.status == TaskStatus::Queued {
            task.status = TaskStatus::Cancelled;
            task.completed_at = Some(now_timestamp());
        }

        Ok(())
    }

    /// Mark task as cancelled (called by task executor)
    pub fn mark_cancelled(&mut self, task_id: &str) {
        if let Some(task) = self.tasks.get_mut(task_id) {
            task.status = TaskStatus::Cancelled;
            task.completed_at = Some(now_timestamp());
            self.running_count = self.running_count.saturating_sub(1);
        }
    }

    /// Check if cancellation was requested
    pub fn is_cancellation_requested(&self, task_id: &str) -> bool {
        self.task_handles.get(task_id)
            .and_then(|token| token.lock().ok())
            .map(|cancel| *cancel)
            .unwrap_or(false)
    }

    /// Get cancellation token for a task
    pub fn get_cancellation_token(&self, task_id: &str) -> Option<Arc<Mutex<bool>>> {
        self.task_handles.get(task_id).cloned()
    }

    /// Get a task by ID
    pub fn get_task(&self, task_id: &str) -> Option<&BackgroundTask> {
        self.tasks.get(task_id)
    }

    /// Get all tasks
    pub fn get_all_tasks(&self) -> Vec<&BackgroundTask> {
        self.tasks.values().collect()
    }

    /// Get running tasks
    pub fn get_running_tasks(&self) -> Vec<&BackgroundTask> {
        self.tasks.values()
            .filter(|t| t.status == TaskStatus::Running)
            .collect()
    }

    /// Get recent tasks (last N)
    pub fn get_recent_tasks(&self, limit: usize) -> Vec<&BackgroundTask> {
        let mut tasks: Vec<_> = self.tasks.values().collect();
        tasks.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        tasks.into_iter().take(limit).collect()
    }

    /// Clean up old completed tasks
    pub fn cleanup_old_tasks(&mut self, max_age_seconds: u64) {
        let cutoff = now_timestamp().saturating_sub(max_age_seconds);

        self.tasks.retain(|id, task| {
            let keep = task.status == TaskStatus::Running
                || task.status == TaskStatus::Queued
                || task.completed_at.unwrap_or(u64::MAX) > cutoff;

            if !keep {
                self.task_handles.remove(id);
            }
            keep
        });
    }

    /// Get task summary
    pub fn get_summary(&self) -> TaskSummary {
        let mut summary = TaskSummary::default();

        for task in self.tasks.values() {
            match task.status {
                TaskStatus::Queued => summary.queued += 1,
                TaskStatus::Running => summary.running += 1,
                TaskStatus::Completed => summary.completed += 1,
                TaskStatus::Failed => summary.failed += 1,
                TaskStatus::Cancelled => summary.cancelled += 1,
            }
        }

        summary.total = self.tasks.len();
        summary
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TaskSummary {
    pub total: usize,
    pub queued: usize,
    pub running: usize,
    pub completed: usize,
    pub failed: usize,
    pub cancelled: usize,
}

// =============================================================================
// GLOBAL TASK MANAGER
// =============================================================================

lazy_static::lazy_static! {
    static ref TASK_MANAGER: Mutex<TaskManager> = Mutex::new(TaskManager::new());
}

pub fn task_manager() -> std::sync::MutexGuard<'static, TaskManager> {
    TASK_MANAGER.lock().unwrap()
}

// =============================================================================
// CONVENIENCE API
// =============================================================================

/// Create and start a background task
pub fn spawn_task<F>(
    name: &str,
    description: &str,
    task_type: TaskType,
    work: F,
) -> String
where
    F: FnOnce(TaskHandle) -> Result<(String, Vec<String>), String> + Send + 'static,
{
    let task_id = {
        let mut mgr = task_manager();
        let id = mgr.create_task(name, description, task_type);
        let _ = mgr.start_task(&id);
        id
    };

    let task_id_clone = task_id.clone();
    let cancel_token = task_manager().get_cancellation_token(&task_id);

    std::thread::spawn(move || {
        let handle = TaskHandle {
            task_id: task_id_clone.clone(),
            cancel_token,
        };

        match work(handle) {
            Ok((output, artifacts)) => {
                task_manager().complete_task(&task_id_clone, output, artifacts);
            }
            Err(e) => {
                if task_manager().is_cancellation_requested(&task_id_clone) {
                    task_manager().mark_cancelled(&task_id_clone);
                } else {
                    task_manager().fail_task(&task_id_clone, e);
                }
            }
        }
    });

    task_id
}

/// Handle passed to background task for progress updates and cancellation checks
#[derive(Clone)]
pub struct TaskHandle {
    pub task_id: String,
    cancel_token: Option<Arc<Mutex<bool>>>,
}

impl TaskHandle {
    /// Update progress
    pub fn update_progress(&self, current: u32, message: &str) {
        task_manager().update_progress(&self.task_id, current, message);
    }

    /// Set total for progress
    pub fn set_total(&self, total: u32) {
        task_manager().set_total(&self.task_id, total);
    }

    /// Check if cancellation was requested
    pub fn is_cancelled(&self) -> bool {
        self.cancel_token.as_ref()
            .and_then(|t| t.lock().ok())
            .map(|c| *c)
            .unwrap_or(false)
    }

    /// Return error if cancelled
    pub fn check_cancelled(&self) -> Result<(), String> {
        if self.is_cancelled() {
            Err("Task cancelled".to_string())
        } else {
            Ok(())
        }
    }
}

// =============================================================================
// PUBLIC API
// =============================================================================

/// Get all tasks
pub fn get_all_tasks() -> Vec<BackgroundTask> {
    task_manager().get_all_tasks().into_iter().cloned().collect()
}

/// Get running tasks
pub fn get_running_tasks() -> Vec<BackgroundTask> {
    task_manager().get_running_tasks().into_iter().cloned().collect()
}

/// Get a specific task
pub fn get_task(task_id: &str) -> Option<BackgroundTask> {
    task_manager().get_task(task_id).cloned()
}

/// Cancel a task
pub fn cancel_task(task_id: &str) -> Result<(), String> {
    task_manager().cancel_task(task_id)
}

/// Get task summary
pub fn get_task_summary() -> TaskSummary {
    task_manager().get_summary()
}

/// Format task for display
pub fn format_task(task: &BackgroundTask) -> String {
    let status_icon = match task.status {
        TaskStatus::Queued => "⏳",
        TaskStatus::Running => "🔄",
        TaskStatus::Completed => "✅",
        TaskStatus::Failed => "❌",
        TaskStatus::Cancelled => "🚫",
    };

    let mut output = format!("{} **{}** - {}\n", status_icon, task.name, task.description);

    if task.status == TaskStatus::Running {
        output.push_str(&format!(
            "   Progress: {:.1}% - {}\n",
            task.progress.percent,
            task.progress.message
        ));
    }

    if let Some(result) = &task.result {
        if result.success {
            output.push_str(&format!("   Completed in {}ms\n", result.duration_ms));
        } else {
            output.push_str(&format!("   Error: {}\n", result.output));
        }
    }

    output
}

/// Format all running tasks
pub fn format_running_tasks() -> String {
    let tasks = get_running_tasks();

    if tasks.is_empty() {
        return "No background tasks running.".to_string();
    }

    let mut output = String::from("## Background Tasks\n\n");

    for task in tasks {
        output.push_str(&format_task(&task));
        output.push('\n');
    }

    output
}

// =============================================================================
// HELPERS
// =============================================================================

fn now_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_task_lifecycle() {
        let mut mgr = TaskManager::new();

        let id = mgr.create_task("Test Task", "A test", TaskType::Custom("test".to_string()));
        assert_eq!(mgr.get_task(&id).unwrap().status, TaskStatus::Queued);

        mgr.start_task(&id).unwrap();
        assert_eq!(mgr.get_task(&id).unwrap().status, TaskStatus::Running);

        mgr.update_progress(&id, 50, "Halfway there");
        assert_eq!(mgr.get_task(&id).unwrap().progress.current, 50);

        mgr.complete_task(&id, "Done".to_string(), vec![]);
        assert_eq!(mgr.get_task(&id).unwrap().status, TaskStatus::Completed);
    }

    #[test]
    fn test_task_cancellation() {
        let mut mgr = TaskManager::new();

        let id = mgr.create_task("Cancel Test", "Test cancellation", TaskType::Custom("test".to_string()));
        mgr.start_task(&id).unwrap();

        mgr.cancel_task(&id).unwrap();
        assert!(mgr.is_cancellation_requested(&id));

        mgr.mark_cancelled(&id);
        assert_eq!(mgr.get_task(&id).unwrap().status, TaskStatus::Cancelled);
    }

    #[test]
    fn test_spawn_task() {
        let task_id = spawn_task(
            "Spawn Test",
            "Test spawning",
            TaskType::Custom("test".to_string()),
            |handle| {
                handle.set_total(10);
                for i in 0..10 {
                    handle.check_cancelled()?;
                    handle.update_progress(i + 1, &format!("Step {}", i + 1));
                    std::thread::sleep(std::time::Duration::from_millis(10));
                }
                Ok(("Success".to_string(), vec![]))
            },
        );

        // Wait for task to complete
        std::thread::sleep(std::time::Duration::from_millis(200));

        let task = get_task(&task_id).unwrap();
        assert_eq!(task.status, TaskStatus::Completed);
    }

    #[test]
    fn test_task_summary() {
        let mut mgr = TaskManager::new();

        mgr.create_task("Task 1", "First", TaskType::Build);
        let id2 = mgr.create_task("Task 2", "Second", TaskType::Test);
        mgr.start_task(&id2).unwrap();

        let summary = mgr.get_summary();
        assert_eq!(summary.queued, 1);
        assert_eq!(summary.running, 1);
        assert_eq!(summary.total, 2);
    }
}
