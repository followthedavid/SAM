//! Sticky Commands - Pinned commands and snippets
//!
//! Provides quick access to frequently used commands:
//! - Pin commands from history
//! - Create custom snippets
//! - Organize with folders/tags
//! - Quick insertion via keyboard shortcut

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

/// Atomic counter for unique ID generation
static ID_COUNTER: AtomicU64 = AtomicU64::new(0);

// =============================================================================
// TYPES
// =============================================================================

/// A sticky command or snippet
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StickyCommand {
    /// Unique ID
    pub id: String,
    /// Display name
    pub name: String,
    /// The command/snippet
    pub command: String,
    /// Description
    pub description: Option<String>,
    /// Folder/category
    pub folder: Option<String>,
    /// Tags for filtering
    pub tags: Vec<String>,
    /// Keyboard shortcut (e.g., "Ctrl+1")
    pub shortcut: Option<String>,
    /// Whether to auto-execute or just insert
    pub auto_execute: bool,
    /// Use count
    pub use_count: u32,
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    /// Last used
    pub last_used: Option<DateTime<Utc>>,
    /// Sort order (lower = higher)
    pub sort_order: i32,
    /// Color for visual organization
    pub color: Option<String>,
    /// Icon (emoji or named)
    pub icon: Option<String>,
}

/// A folder for organizing sticky commands
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StickyFolder {
    /// Folder ID
    pub id: String,
    /// Folder name
    pub name: String,
    /// Icon
    pub icon: Option<String>,
    /// Color
    pub color: Option<String>,
    /// Sort order
    pub sort_order: i32,
    /// Collapsed state
    pub collapsed: bool,
}

// =============================================================================
// STICKY COMMAND MANAGER
// =============================================================================

pub struct StickyManager {
    commands: HashMap<String, StickyCommand>,
    folders: HashMap<String, StickyFolder>,
    /// Maximum number of sticky commands
    max_commands: usize,
    /// Show in terminal UI
    visible: bool,
}

impl StickyManager {
    pub fn new() -> Self {
        let mut manager = Self {
            commands: HashMap::new(),
            folders: HashMap::new(),
            max_commands: 50,
            visible: true,
        };
        manager.create_default_folders();
        manager
    }

    fn create_default_folders(&mut self) {
        let defaults = vec![
            ("git", "Git", "🔀"),
            ("docker", "Docker", "🐳"),
            ("system", "System", "💻"),
            ("custom", "Custom", "⭐"),
        ];

        for (i, (id, name, icon)) in defaults.into_iter().enumerate() {
            self.folders.insert(id.to_string(), StickyFolder {
                id: id.to_string(),
                name: name.to_string(),
                icon: Some(icon.to_string()),
                color: None,
                sort_order: i as i32,
                collapsed: false,
            });
        }
    }

    /// Add a sticky command
    pub fn add(&mut self, name: &str, command: &str) -> String {
        let counter = ID_COUNTER.fetch_add(1, Ordering::SeqCst);
        let id = format!("sticky_{}_{}", chrono::Utc::now().timestamp_millis(), counter);
        let sticky = StickyCommand {
            id: id.clone(),
            name: name.to_string(),
            command: command.to_string(),
            description: None,
            folder: None,
            tags: Vec::new(),
            shortcut: None,
            auto_execute: false,
            use_count: 0,
            created_at: Utc::now(),
            last_used: None,
            sort_order: self.commands.len() as i32,
            color: None,
            icon: None,
        };

        self.commands.insert(id.clone(), sticky);
        id
    }

    /// Add with full options
    pub fn add_full(&mut self, sticky: StickyCommand) -> String {
        let id = sticky.id.clone();
        self.commands.insert(id.clone(), sticky);
        id
    }

    /// Pin a command from history
    pub fn pin_from_history(&mut self, command: &str, name: Option<&str>) -> String {
        let display_name = match name {
            Some(n) => n.to_string(),
            None => command.split_whitespace().take(3).collect::<Vec<_>>().join(" "),
        };
        self.add(&display_name, command)
    }

    /// Remove a sticky command
    pub fn remove(&mut self, id: &str) -> bool {
        self.commands.remove(id).is_some()
    }

    /// Get a sticky command
    pub fn get(&self, id: &str) -> Option<&StickyCommand> {
        self.commands.get(id)
    }

    /// Update a sticky command
    pub fn update(&mut self, id: &str, updates: StickyUpdate) -> bool {
        if let Some(cmd) = self.commands.get_mut(id) {
            if let Some(name) = updates.name {
                cmd.name = name;
            }
            if let Some(command) = updates.command {
                cmd.command = command;
            }
            if let Some(description) = updates.description {
                cmd.description = Some(description);
            }
            if let Some(folder) = updates.folder {
                cmd.folder = Some(folder);
            }
            if let Some(tags) = updates.tags {
                cmd.tags = tags;
            }
            if let Some(shortcut) = updates.shortcut {
                cmd.shortcut = Some(shortcut);
            }
            if let Some(auto_execute) = updates.auto_execute {
                cmd.auto_execute = auto_execute;
            }
            if let Some(color) = updates.color {
                cmd.color = Some(color);
            }
            if let Some(icon) = updates.icon {
                cmd.icon = Some(icon);
            }
            true
        } else {
            false
        }
    }

    /// Record usage of a sticky command
    pub fn record_use(&mut self, id: &str) -> Option<&str> {
        if let Some(cmd) = self.commands.get_mut(id) {
            cmd.use_count += 1;
            cmd.last_used = Some(Utc::now());
            Some(&cmd.command)
        } else {
            None
        }
    }

    /// Get command and record usage
    pub fn use_command(&mut self, id: &str) -> Option<UseResult> {
        if let Some(cmd) = self.commands.get_mut(id) {
            cmd.use_count += 1;
            cmd.last_used = Some(Utc::now());
            Some(UseResult {
                command: cmd.command.clone(),
                auto_execute: cmd.auto_execute,
            })
        } else {
            None
        }
    }

    /// List all sticky commands
    pub fn list(&self) -> Vec<&StickyCommand> {
        let mut commands: Vec<_> = self.commands.values().collect();
        commands.sort_by(|a, b| a.sort_order.cmp(&b.sort_order));
        commands
    }

    /// List by folder
    pub fn list_by_folder(&self, folder: Option<&str>) -> Vec<&StickyCommand> {
        let mut commands: Vec<_> = self.commands.values()
            .filter(|c| c.folder.as_deref() == folder)
            .collect();
        commands.sort_by(|a, b| a.sort_order.cmp(&b.sort_order));
        commands
    }

    /// Search sticky commands
    pub fn search(&self, query: &str) -> Vec<&StickyCommand> {
        let query_lower = query.to_lowercase();
        let mut results: Vec<_> = self.commands.values()
            .filter(|c| {
                c.name.to_lowercase().contains(&query_lower) ||
                c.command.to_lowercase().contains(&query_lower) ||
                c.description.as_ref().map(|d| d.to_lowercase().contains(&query_lower)).unwrap_or(false) ||
                c.tags.iter().any(|t| t.to_lowercase().contains(&query_lower))
            })
            .collect();
        results.sort_by(|a, b| b.use_count.cmp(&a.use_count));
        results
    }

    /// Get by shortcut
    pub fn get_by_shortcut(&self, shortcut: &str) -> Option<&StickyCommand> {
        self.commands.values().find(|c| c.shortcut.as_deref() == Some(shortcut))
    }

    /// Reorder commands
    pub fn reorder(&mut self, id: &str, new_order: i32) {
        if let Some(cmd) = self.commands.get_mut(id) {
            let old_order = cmd.sort_order;
            cmd.sort_order = new_order;

            // Adjust other commands
            for other in self.commands.values_mut() {
                if other.id != id {
                    if new_order <= other.sort_order && other.sort_order < old_order {
                        other.sort_order += 1;
                    } else if old_order < other.sort_order && other.sort_order <= new_order {
                        other.sort_order -= 1;
                    }
                }
            }
        }
    }

    // ==========================================================================
    // Folder Operations
    // ==========================================================================

    /// Add a folder
    pub fn add_folder(&mut self, name: &str) -> String {
        let counter = ID_COUNTER.fetch_add(1, Ordering::SeqCst);
        let id = format!("folder_{}_{}", chrono::Utc::now().timestamp_millis(), counter);
        self.folders.insert(id.clone(), StickyFolder {
            id: id.clone(),
            name: name.to_string(),
            icon: None,
            color: None,
            sort_order: self.folders.len() as i32,
            collapsed: false,
        });
        id
    }

    /// Remove a folder (moves commands to unfiled)
    pub fn remove_folder(&mut self, id: &str) -> bool {
        if self.folders.remove(id).is_some() {
            // Move commands in this folder to unfiled
            for cmd in self.commands.values_mut() {
                if cmd.folder.as_deref() == Some(id) {
                    cmd.folder = None;
                }
            }
            true
        } else {
            false
        }
    }

    /// List folders
    pub fn list_folders(&self) -> Vec<&StickyFolder> {
        let mut folders: Vec<_> = self.folders.values().collect();
        folders.sort_by(|a, b| a.sort_order.cmp(&b.sort_order));
        folders
    }

    /// Toggle folder collapsed state
    pub fn toggle_folder(&mut self, id: &str) -> Option<bool> {
        if let Some(folder) = self.folders.get_mut(id) {
            folder.collapsed = !folder.collapsed;
            Some(folder.collapsed)
        } else {
            None
        }
    }

    // ==========================================================================
    // Visibility
    // ==========================================================================

    /// Toggle visibility
    pub fn toggle_visibility(&mut self) -> bool {
        self.visible = !self.visible;
        self.visible
    }

    /// Check if visible
    pub fn is_visible(&self) -> bool {
        self.visible
    }

    /// Set visibility
    pub fn set_visible(&mut self, visible: bool) {
        self.visible = visible;
    }

    // ==========================================================================
    // Import/Export
    // ==========================================================================

    /// Export to JSON
    pub fn export(&self) -> String {
        let data = ExportData {
            commands: self.commands.values().cloned().collect(),
            folders: self.folders.values().cloned().collect(),
        };
        serde_json::to_string_pretty(&data).unwrap_or_default()
    }

    /// Import from JSON
    pub fn import(&mut self, json: &str) -> Result<usize, String> {
        let data: ExportData = serde_json::from_str(json)
            .map_err(|e| e.to_string())?;

        let count = data.commands.len();

        for folder in data.folders {
            self.folders.insert(folder.id.clone(), folder);
        }
        for cmd in data.commands {
            self.commands.insert(cmd.id.clone(), cmd);
        }

        Ok(count)
    }
}

impl Default for StickyManager {
    fn default() -> Self {
        Self::new()
    }
}

/// Updates for a sticky command
#[derive(Debug, Default)]
pub struct StickyUpdate {
    pub name: Option<String>,
    pub command: Option<String>,
    pub description: Option<String>,
    pub folder: Option<String>,
    pub tags: Option<Vec<String>>,
    pub shortcut: Option<String>,
    pub auto_execute: Option<bool>,
    pub color: Option<String>,
    pub icon: Option<String>,
}

/// Result of using a command
#[derive(Debug, Clone)]
pub struct UseResult {
    pub command: String,
    pub auto_execute: bool,
}

#[derive(Serialize, Deserialize)]
struct ExportData {
    commands: Vec<StickyCommand>,
    folders: Vec<StickyFolder>,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref STICKY_MANAGER: Arc<Mutex<StickyManager>> =
        Arc::new(Mutex::new(StickyManager::new()));
}

/// Get the global sticky manager
pub fn stickies() -> Arc<Mutex<StickyManager>> {
    STICKY_MANAGER.clone()
}

/// Add a sticky command
pub fn add(name: &str, command: &str) -> String {
    STICKY_MANAGER.lock().unwrap().add(name, command)
}

/// Pin from history
pub fn pin(command: &str) -> String {
    STICKY_MANAGER.lock().unwrap().pin_from_history(command, None)
}

/// Use a sticky command
pub fn use_command(id: &str) -> Option<UseResult> {
    STICKY_MANAGER.lock().unwrap().use_command(id)
}

/// Search sticky commands
pub fn search(query: &str) -> Vec<StickyCommand> {
    STICKY_MANAGER.lock().unwrap().search(query).into_iter().cloned().collect()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_sticky() {
        let mut manager = StickyManager::new();
        let id = manager.add("List files", "ls -la");

        let cmd = manager.get(&id).unwrap();
        assert_eq!(cmd.name, "List files");
        assert_eq!(cmd.command, "ls -la");
    }

    #[test]
    fn test_pin_from_history() {
        let mut manager = StickyManager::new();
        let id = manager.pin_from_history("git status", None);

        let cmd = manager.get(&id).unwrap();
        assert_eq!(cmd.command, "git status");
        assert_eq!(cmd.name, "git status");
    }

    #[test]
    fn test_use_command() {
        let mut manager = StickyManager::new();
        let id = manager.add("Test", "echo test");

        let result = manager.use_command(&id).unwrap();
        assert_eq!(result.command, "echo test");

        let cmd = manager.get(&id).unwrap();
        assert_eq!(cmd.use_count, 1);
        assert!(cmd.last_used.is_some());
    }

    #[test]
    fn test_search() {
        let mut manager = StickyManager::new();
        manager.add("Git Status", "git status");
        manager.add("Git Pull", "git pull");
        manager.add("Docker PS", "docker ps");

        let results = manager.search("git");
        assert_eq!(results.len(), 2);
    }

    #[test]
    fn test_folders() {
        let mut manager = StickyManager::new();
        let folder_id = manager.add_folder("My Folder");
        let cmd_id = manager.add("Test", "test");

        manager.update(&cmd_id, StickyUpdate {
            folder: Some(folder_id.clone()),
            ..Default::default()
        });

        let by_folder = manager.list_by_folder(Some(&folder_id));
        assert_eq!(by_folder.len(), 1);
    }

    #[test]
    fn test_shortcut() {
        let mut manager = StickyManager::new();
        let id = manager.add("Quick", "quick command");

        manager.update(&id, StickyUpdate {
            shortcut: Some("Ctrl+1".to_string()),
            ..Default::default()
        });

        let found = manager.get_by_shortcut("Ctrl+1").unwrap();
        assert_eq!(found.id, id);
    }

    #[test]
    fn test_export_import() {
        let mut manager = StickyManager::new();
        manager.add("Test1", "cmd1");
        manager.add("Test2", "cmd2");

        let json = manager.export();

        let mut manager2 = StickyManager::new();
        let count = manager2.import(&json).unwrap();
        assert_eq!(count, 2);
    }
}
