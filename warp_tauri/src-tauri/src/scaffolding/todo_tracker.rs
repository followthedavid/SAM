// Todo Tracker - Claude Code Style Task Tracking
//
// Track tasks within a session with status updates.
// Persistent storage with session grouping.

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::PathBuf;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TodoStatus {
    Pending,
    InProgress,
    Completed,
    Blocked,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Todo {
    pub id: String,
    pub content: String,
    pub active_form: String,  // Present continuous form ("Running tests")
    pub status: TodoStatus,
    pub priority: u8,         // 1 = highest, 5 = lowest
    pub created_at: i64,
    pub updated_at: i64,
    pub completed_at: Option<i64>,
    pub parent_id: Option<String>,  // For subtasks
    pub tags: Vec<String>,
    pub notes: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TodoSession {
    pub id: String,
    pub name: Option<String>,
    pub created_at: i64,
    pub todos: Vec<Todo>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TodoStats {
    pub total: usize,
    pub pending: usize,
    pub in_progress: usize,
    pub completed: usize,
    pub blocked: usize,
    pub cancelled: usize,
    pub completion_rate: f32,
}

// =============================================================================
// TODO TRACKER
// =============================================================================

pub struct TodoTracker {
    current_session: TodoSession,
    sessions: Vec<TodoSession>,
    storage_path: PathBuf,
    max_sessions: usize,
}

impl TodoTracker {
    pub fn new() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let storage_path = PathBuf::from(format!("{}/.sam/todos.json", home));

        let mut tracker = Self {
            current_session: TodoSession {
                id: format!("session_{}", chrono::Utc::now().timestamp_millis()),
                name: None,
                created_at: chrono::Utc::now().timestamp(),
                todos: Vec::new(),
            },
            sessions: Vec::new(),
            storage_path,
            max_sessions: 50,
        };

        tracker.load();
        tracker
    }

    fn load(&mut self) {
        if let Ok(data) = fs::read_to_string(&self.storage_path) {
            if let Ok(stored) = serde_json::from_str::<StoredTodos>(&data) {
                self.sessions = stored.sessions;
                // Resume last session if recent (within 1 hour)
                if let Some(last) = self.sessions.last() {
                    let now = chrono::Utc::now().timestamp();
                    if now - last.created_at < 3600 {
                        self.current_session = last.clone();
                        self.sessions.pop();
                    }
                }
            }
        }
    }

    pub fn save(&self) {
        // Add current session to history
        let mut sessions = self.sessions.clone();
        if !self.current_session.todos.is_empty() {
            sessions.push(self.current_session.clone());
        }

        // Keep only last N sessions
        if sessions.len() > self.max_sessions {
            sessions = sessions.split_off(sessions.len() - self.max_sessions);
        }

        let stored = StoredTodos { sessions };

        if let Some(parent) = self.storage_path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Ok(data) = serde_json::to_string_pretty(&stored) {
            let _ = fs::write(&self.storage_path, data);
        }
    }

    // ==========================================================================
    // CRUD Operations
    // ==========================================================================

    // Add a new todo
    pub fn add(&mut self, content: &str, active_form: &str) -> Todo {
        let todo = Todo {
            id: format!("todo_{}", chrono::Utc::now().timestamp_millis()),
            content: content.to_string(),
            active_form: active_form.to_string(),
            status: TodoStatus::Pending,
            priority: 3,
            created_at: chrono::Utc::now().timestamp(),
            updated_at: chrono::Utc::now().timestamp(),
            completed_at: None,
            parent_id: None,
            tags: Vec::new(),
            notes: None,
        };

        self.current_session.todos.push(todo.clone());
        self.save();
        todo
    }

    // Add multiple todos at once
    pub fn add_many(&mut self, todos: Vec<(String, String)>) -> Vec<Todo> {
        let mut created = Vec::new();

        for (content, active_form) in todos {
            let todo = Todo {
                id: format!("todo_{}_{}", chrono::Utc::now().timestamp_millis(), created.len()),
                content,
                active_form,
                status: TodoStatus::Pending,
                priority: 3,
                created_at: chrono::Utc::now().timestamp(),
                updated_at: chrono::Utc::now().timestamp(),
                completed_at: None,
                parent_id: None,
                tags: Vec::new(),
                notes: None,
            };
            self.current_session.todos.push(todo.clone());
            created.push(todo);
        }

        self.save();
        created
    }

    // Update todo status
    pub fn set_status(&mut self, id: &str, status: TodoStatus) -> Result<(), String> {
        let todo = self.current_session.todos.iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| "Todo not found".to_string())?;

        todo.status = status.clone();
        todo.updated_at = chrono::Utc::now().timestamp();

        if status == TodoStatus::Completed {
            todo.completed_at = Some(chrono::Utc::now().timestamp());
        }

        self.save();
        Ok(())
    }

    // Mark as in progress
    pub fn start(&mut self, id: &str) -> Result<(), String> {
        self.set_status(id, TodoStatus::InProgress)
    }

    // Mark as completed
    pub fn complete(&mut self, id: &str) -> Result<(), String> {
        self.set_status(id, TodoStatus::Completed)
    }

    // Mark as blocked
    pub fn block(&mut self, id: &str, reason: Option<&str>) -> Result<(), String> {
        let todo = self.current_session.todos.iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| "Todo not found".to_string())?;

        todo.status = TodoStatus::Blocked;
        todo.updated_at = chrono::Utc::now().timestamp();
        if let Some(r) = reason {
            todo.notes = Some(r.to_string());
        }

        self.save();
        Ok(())
    }

    // Cancel a todo
    pub fn cancel(&mut self, id: &str) -> Result<(), String> {
        self.set_status(id, TodoStatus::Cancelled)
    }

    // Update todo content
    pub fn update(&mut self, id: &str, content: &str, active_form: &str) -> Result<(), String> {
        let todo = self.current_session.todos.iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| "Todo not found".to_string())?;

        todo.content = content.to_string();
        todo.active_form = active_form.to_string();
        todo.updated_at = chrono::Utc::now().timestamp();

        self.save();
        Ok(())
    }

    // Remove a todo
    pub fn remove(&mut self, id: &str) -> bool {
        let len_before = self.current_session.todos.len();
        self.current_session.todos.retain(|t| t.id != id);
        let removed = self.current_session.todos.len() < len_before;
        if removed {
            self.save();
        }
        removed
    }

    // Clear all todos
    pub fn clear(&mut self) {
        self.current_session.todos.clear();
        self.save();
    }

    // Clear completed todos
    pub fn clear_completed(&mut self) {
        self.current_session.todos.retain(|t| t.status != TodoStatus::Completed);
        self.save();
    }

    // ==========================================================================
    // Query Operations
    // ==========================================================================

    // Get all todos in current session
    pub fn list(&self) -> &[Todo] {
        &self.current_session.todos
    }

    // Get todos by status
    pub fn by_status(&self, status: TodoStatus) -> Vec<&Todo> {
        self.current_session.todos.iter()
            .filter(|t| t.status == status)
            .collect()
    }

    // Get pending todos
    pub fn pending(&self) -> Vec<&Todo> {
        self.by_status(TodoStatus::Pending)
    }

    // Get in-progress todo (should only be one)
    pub fn in_progress(&self) -> Option<&Todo> {
        self.current_session.todos.iter()
            .find(|t| t.status == TodoStatus::InProgress)
    }

    // Get completed todos
    pub fn completed(&self) -> Vec<&Todo> {
        self.by_status(TodoStatus::Completed)
    }

    // Get todo by ID
    pub fn get(&self, id: &str) -> Option<&Todo> {
        self.current_session.todos.iter().find(|t| t.id == id)
    }

    // Get stats
    pub fn stats(&self) -> TodoStats {
        let total = self.current_session.todos.len();
        let pending = self.current_session.todos.iter().filter(|t| t.status == TodoStatus::Pending).count();
        let in_progress = self.current_session.todos.iter().filter(|t| t.status == TodoStatus::InProgress).count();
        let completed = self.current_session.todos.iter().filter(|t| t.status == TodoStatus::Completed).count();
        let blocked = self.current_session.todos.iter().filter(|t| t.status == TodoStatus::Blocked).count();
        let cancelled = self.current_session.todos.iter().filter(|t| t.status == TodoStatus::Cancelled).count();

        let completion_rate = if total > 0 {
            completed as f32 / total as f32
        } else {
            0.0
        };

        TodoStats {
            total,
            pending,
            in_progress,
            completed,
            blocked,
            cancelled,
            completion_rate,
        }
    }

    // ==========================================================================
    // Session Operations
    // ==========================================================================

    // Start a new session
    pub fn new_session(&mut self, name: Option<&str>) {
        // Save current session if it has todos
        if !self.current_session.todos.is_empty() {
            self.sessions.push(self.current_session.clone());
        }

        self.current_session = TodoSession {
            id: format!("session_{}", chrono::Utc::now().timestamp_millis()),
            name: name.map(|s| s.to_string()),
            created_at: chrono::Utc::now().timestamp(),
            todos: Vec::new(),
        };

        self.save();
    }

    // Name current session
    pub fn name_session(&mut self, name: &str) {
        self.current_session.name = Some(name.to_string());
        self.save();
    }

    // Get session history
    pub fn session_history(&self) -> &[TodoSession] {
        &self.sessions
    }

    // Load a previous session
    pub fn load_session(&mut self, session_id: &str) -> Result<(), String> {
        let idx = self.sessions.iter()
            .position(|s| s.id == session_id)
            .ok_or_else(|| "Session not found".to_string())?;

        // Save current if not empty
        if !self.current_session.todos.is_empty() {
            self.sessions.push(self.current_session.clone());
        }

        self.current_session = self.sessions.remove(idx);
        self.save();
        Ok(())
    }

    // ==========================================================================
    // Priority Operations
    // ==========================================================================

    // Set priority (1-5)
    pub fn set_priority(&mut self, id: &str, priority: u8) -> Result<(), String> {
        let priority = priority.clamp(1, 5);

        let todo = self.current_session.todos.iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| "Todo not found".to_string())?;

        todo.priority = priority;
        todo.updated_at = chrono::Utc::now().timestamp();

        self.save();
        Ok(())
    }

    // Reorder todos
    pub fn reorder(&mut self, ids: Vec<String>) {
        let mut new_todos = Vec::new();

        for id in ids {
            if let Some(idx) = self.current_session.todos.iter().position(|t| t.id == id) {
                new_todos.push(self.current_session.todos.remove(idx));
            }
        }

        // Add any remaining todos
        new_todos.append(&mut self.current_session.todos);
        self.current_session.todos = new_todos;

        self.save();
    }

    // ==========================================================================
    // Tag Operations
    // ==========================================================================

    // Add tag to todo
    pub fn add_tag(&mut self, id: &str, tag: &str) -> Result<(), String> {
        let todo = self.current_session.todos.iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| "Todo not found".to_string())?;

        if !todo.tags.contains(&tag.to_string()) {
            todo.tags.push(tag.to_string());
            todo.updated_at = chrono::Utc::now().timestamp();
            self.save();
        }

        Ok(())
    }

    // Remove tag from todo
    pub fn remove_tag(&mut self, id: &str, tag: &str) -> Result<(), String> {
        let todo = self.current_session.todos.iter_mut()
            .find(|t| t.id == id)
            .ok_or_else(|| "Todo not found".to_string())?;

        todo.tags.retain(|t| t != tag);
        todo.updated_at = chrono::Utc::now().timestamp();

        self.save();
        Ok(())
    }

    // Get todos by tag
    pub fn by_tag(&self, tag: &str) -> Vec<&Todo> {
        self.current_session.todos.iter()
            .filter(|t| t.tags.contains(&tag.to_string()))
            .collect()
    }

    // ==========================================================================
    // Subtask Operations
    // ==========================================================================

    // Add subtask
    pub fn add_subtask(&mut self, parent_id: &str, content: &str, active_form: &str) -> Result<Todo, String> {
        // Verify parent exists
        if !self.current_session.todos.iter().any(|t| t.id == parent_id) {
            return Err("Parent todo not found".to_string());
        }

        let todo = Todo {
            id: format!("todo_{}", chrono::Utc::now().timestamp_millis()),
            content: content.to_string(),
            active_form: active_form.to_string(),
            status: TodoStatus::Pending,
            priority: 3,
            created_at: chrono::Utc::now().timestamp(),
            updated_at: chrono::Utc::now().timestamp(),
            completed_at: None,
            parent_id: Some(parent_id.to_string()),
            tags: Vec::new(),
            notes: None,
        };

        self.current_session.todos.push(todo.clone());
        self.save();
        Ok(todo)
    }

    // Get subtasks
    pub fn subtasks(&self, parent_id: &str) -> Vec<&Todo> {
        self.current_session.todos.iter()
            .filter(|t| t.parent_id.as_deref() == Some(parent_id))
            .collect()
    }
}

#[derive(Serialize, Deserialize)]
struct StoredTodos {
    sessions: Vec<TodoSession>,
}

// Global tracker
lazy_static::lazy_static! {
    pub static ref TODO_TRACKER: std::sync::Mutex<TodoTracker> =
        std::sync::Mutex::new(TodoTracker::new());
}

pub fn todos() -> std::sync::MutexGuard<'static, TodoTracker> {
    TODO_TRACKER.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_todo() {
        let mut tracker = TodoTracker::new();
        let todo = tracker.add("Test task", "Testing task");

        assert!(!todo.id.is_empty());
        assert_eq!(todo.content, "Test task");
        assert_eq!(todo.status, TodoStatus::Pending);
    }

    #[test]
    fn test_status_transitions() {
        let mut tracker = TodoTracker::new();
        let todo = tracker.add("Test task", "Testing");

        tracker.start(&todo.id).unwrap();
        assert_eq!(tracker.get(&todo.id).unwrap().status, TodoStatus::InProgress);

        tracker.complete(&todo.id).unwrap();
        assert_eq!(tracker.get(&todo.id).unwrap().status, TodoStatus::Completed);
        assert!(tracker.get(&todo.id).unwrap().completed_at.is_some());
    }

    #[test]
    fn test_stats() {
        let mut tracker = TodoTracker::new();
        tracker.clear();  // Clear any persistent state from other tests

        tracker.add("Task 1", "Testing 1");
        tracker.add("Task 2", "Testing 2");
        let todo3 = tracker.add("Task 3", "Testing 3");
        tracker.complete(&todo3.id).unwrap();

        let stats = tracker.stats();
        assert_eq!(stats.total, 3);
        assert_eq!(stats.pending, 2);
        assert_eq!(stats.completed, 1);
    }
}
