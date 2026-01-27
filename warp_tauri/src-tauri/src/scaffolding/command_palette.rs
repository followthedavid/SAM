// Command Palette - Cmd+K Style Fuzzy Search
//
// Fuzzy search across commands, files, workflows, and actions.
// Warp-style command palette with keyboard shortcuts.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::Path;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaletteItem {
    pub id: String,
    pub title: String,
    pub subtitle: Option<String>,
    pub category: ItemCategory,
    pub icon: Option<String>,
    pub shortcut: Option<String>,
    pub action: PaletteAction,
    pub score: f32,  // Search relevance score
    pub frequency: u32,  // Usage frequency for ranking
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum ItemCategory {
    Command,      // Shell commands
    File,         // Files in project
    Workflow,     // Saved workflows
    Action,       // Built-in actions
    Git,          // Git operations
    Recent,       // Recent items
    Setting,      // Settings/preferences
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PaletteAction {
    Execute(String),           // Run shell command
    OpenFile(String),          // Open file in editor
    RunWorkflow(String),       // Run workflow by ID
    Navigate(String),          // Navigate to path
    BuiltIn(BuiltInAction),    // Built-in action
    Custom(String),            // Custom action ID
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum BuiltInAction {
    NewFile,
    NewFolder,
    NewTerminal,
    SplitPane,
    ToggleFullscreen,
    ShowSettings,
    ShowHelp,
    ClearTerminal,
    SearchInFiles,
    GitStatus,
    GitCommit,
    GitPush,
    GitPull,
    GitBranch,
    RunBuild,
    RunTest,
    KillProcess,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub items: Vec<PaletteItem>,
    pub total: usize,
    pub query: String,
    pub categories: Vec<ItemCategory>,
}

// =============================================================================
// FUZZY MATCHER
// =============================================================================

pub struct FuzzyMatcher;

impl FuzzyMatcher {
    // Score a string against a query using fuzzy matching
    pub fn score(query: &str, target: &str) -> Option<f32> {
        if query.is_empty() {
            return Some(1.0);
        }

        let query_lower = query.to_lowercase();
        let target_lower = target.to_lowercase();

        // Exact match
        if target_lower == query_lower {
            return Some(1.0);
        }

        // Starts with
        if target_lower.starts_with(&query_lower) {
            return Some(0.9);
        }

        // Contains
        if target_lower.contains(&query_lower) {
            let position = target_lower.find(&query_lower).unwrap_or(0);
            let score = 0.7 - (position as f32 * 0.01);
            return Some(score.max(0.5));
        }

        // Fuzzy character matching
        let mut query_chars = query_lower.chars().peekable();
        let mut score = 0.0;
        let mut consecutive = 0;
        let mut last_match_idx: Option<usize> = None;

        for (idx, target_char) in target_lower.chars().enumerate() {
            if let Some(&query_char) = query_chars.peek() {
                if target_char == query_char {
                    query_chars.next();

                    // Bonus for consecutive matches
                    if last_match_idx.map(|i| i + 1 == idx).unwrap_or(false) {
                        consecutive += 1;
                        score += 0.1 + (consecutive as f32 * 0.05);
                    } else {
                        consecutive = 0;
                        score += 0.1;
                    }

                    // Bonus for word boundary matches
                    if idx == 0 || target.chars().nth(idx - 1).map(|c| !c.is_alphanumeric()).unwrap_or(true) {
                        score += 0.15;
                    }

                    last_match_idx = Some(idx);
                }
            }
        }

        // All query characters must be found
        if query_chars.peek().is_some() {
            return None;
        }

        // Normalize score by query length
        let normalized = score / query.len() as f32;
        Some(normalized.min(0.6))
    }

    // Match with word boundaries (camelCase, snake_case, etc.)
    pub fn score_word_boundary(query: &str, target: &str) -> Option<f32> {
        // Extract word parts from target
        let words = Self::extract_words(target);
        let query_lower = query.to_lowercase();

        // Check if query matches word initials (e.g., "gs" -> "git status")
        let initials: String = words.iter()
            .filter_map(|w| w.chars().next())
            .collect();

        if initials.to_lowercase().starts_with(&query_lower) {
            return Some(0.85);
        }

        // Check if any word starts with query
        for word in &words {
            if word.to_lowercase().starts_with(&query_lower) {
                return Some(0.8);
            }
        }

        // Fall back to regular fuzzy
        Self::score(query, target)
    }

    fn extract_words(s: &str) -> Vec<&str> {
        let mut words = Vec::new();
        let mut start = 0;

        for (i, c) in s.char_indices() {
            if c == '_' || c == '-' || c == ' ' || c == '/' || c == '.' {
                if start < i {
                    words.push(&s[start..i]);
                }
                start = i + 1;
            } else if c.is_uppercase() && i > 0 {
                if start < i {
                    words.push(&s[start..i]);
                }
                start = i;
            }
        }

        if start < s.len() {
            words.push(&s[start..]);
        }

        words
    }
}

// =============================================================================
// COMMAND PALETTE
// =============================================================================

pub struct CommandPalette {
    items: Vec<PaletteItem>,
    recent_usage: HashMap<String, u32>,
    file_cache: Vec<String>,
    max_results: usize,
}

impl CommandPalette {
    pub fn new() -> Self {
        Self {
            items: Self::get_default_items(),
            recent_usage: HashMap::new(),
            file_cache: Vec::new(),
            max_results: 50,
        }
    }

    // Search all items
    pub fn search(&self, query: &str, categories: Option<Vec<ItemCategory>>) -> SearchResult {
        let mut results: Vec<PaletteItem> = Vec::new();

        for item in &self.items {
            // Filter by category if specified
            if let Some(ref cats) = categories {
                if !cats.contains(&item.category) {
                    continue;
                }
            }

            // Score against title
            if let Some(score) = FuzzyMatcher::score_word_boundary(query, &item.title) {
                let mut result = item.clone();
                result.score = score + (item.frequency as f32 * 0.01).min(0.2);
                results.push(result);
                continue;
            }

            // Score against subtitle
            if let Some(ref subtitle) = item.subtitle {
                if let Some(score) = FuzzyMatcher::score(query, subtitle) {
                    let mut result = item.clone();
                    result.score = score * 0.8 + (item.frequency as f32 * 0.01).min(0.1);
                    results.push(result);
                }
            }
        }

        // Sort by score (descending)
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));

        // Limit results
        results.truncate(self.max_results);

        let total = results.len();
        let categories: Vec<ItemCategory> = results.iter()
            .map(|r| r.category.clone())
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();

        SearchResult {
            items: results,
            total,
            query: query.to_string(),
            categories,
        }
    }

    // Search files only
    pub fn search_files(&self, query: &str, _root: &str) -> SearchResult {
        let mut results = Vec::new();

        // Search cached files
        for file_path in &self.file_cache {
            let file_name = Path::new(file_path)
                .file_name()
                .map(|n| n.to_string_lossy().to_string())
                .unwrap_or_default();

            if let Some(score) = FuzzyMatcher::score(query, &file_name) {
                results.push(PaletteItem {
                    id: file_path.clone(),
                    title: file_name,
                    subtitle: Some(file_path.clone()),
                    category: ItemCategory::File,
                    icon: Some(Self::get_file_icon(file_path)),
                    shortcut: None,
                    action: PaletteAction::OpenFile(file_path.clone()),
                    score,
                    frequency: 0,
                });
            }
        }

        // Also search by path
        for file_path in &self.file_cache {
            if !results.iter().any(|r| r.id == *file_path) {
                if let Some(score) = FuzzyMatcher::score(query, file_path) {
                    let file_name = Path::new(file_path)
                        .file_name()
                        .map(|n| n.to_string_lossy().to_string())
                        .unwrap_or_default();

                    results.push(PaletteItem {
                        id: file_path.clone(),
                        title: file_name,
                        subtitle: Some(file_path.clone()),
                        category: ItemCategory::File,
                        icon: Some(Self::get_file_icon(file_path)),
                        shortcut: None,
                        action: PaletteAction::OpenFile(file_path.clone()),
                        score: score * 0.7,
                        frequency: 0,
                    });
                }
            }
        }

        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(self.max_results);

        let total = results.len();
        SearchResult {
            items: results,
            total,
            query: query.to_string(),
            categories: vec![ItemCategory::File],
        }
    }

    // Update file cache
    pub fn update_files(&mut self, files: Vec<String>) {
        self.file_cache = files;
    }

    // Add custom item
    pub fn add_item(&mut self, item: PaletteItem) {
        self.items.push(item);
    }

    // Record usage (for frequency ranking)
    pub fn record_usage(&mut self, item_id: &str) {
        *self.recent_usage.entry(item_id.to_string()).or_insert(0) += 1;

        // Update frequency in items
        if let Some(item) = self.items.iter_mut().find(|i| i.id == item_id) {
            item.frequency = *self.recent_usage.get(item_id).unwrap_or(&0);
        }
    }

    // Get recent items
    pub fn recent(&self, limit: usize) -> Vec<&PaletteItem> {
        let mut items: Vec<_> = self.items.iter()
            .filter(|i| i.category == ItemCategory::Recent || i.frequency > 0)
            .collect();

        items.sort_by(|a, b| b.frequency.cmp(&a.frequency));
        items.truncate(limit);
        items
    }

    // Get file icon based on extension
    fn get_file_icon(path: &str) -> String {
        let ext = Path::new(path)
            .extension()
            .map(|e| e.to_string_lossy().to_lowercase())
            .unwrap_or_default();

        match ext.as_str() {
            "rs" => "rust",
            "js" | "jsx" => "javascript",
            "ts" | "tsx" => "typescript",
            "py" => "python",
            "go" => "go",
            "java" => "java",
            "rb" => "ruby",
            "md" => "markdown",
            "json" => "json",
            "toml" => "toml",
            "yaml" | "yml" => "yaml",
            "html" => "html",
            "css" | "scss" | "sass" => "css",
            "sh" | "bash" | "zsh" => "shell",
            "sql" => "database",
            "docker" | "dockerfile" => "docker",
            _ => "file",
        }.to_string()
    }

    // Default palette items
    fn get_default_items() -> Vec<PaletteItem> {
        vec![
            // Git commands
            PaletteItem {
                id: "git_status".to_string(),
                title: "Git: Status".to_string(),
                subtitle: Some("Show working tree status".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("git status".to_string()),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "git_commit".to_string(),
                title: "Git: Commit".to_string(),
                subtitle: Some("Commit staged changes".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::BuiltIn(BuiltInAction::GitCommit),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "git_push".to_string(),
                title: "Git: Push".to_string(),
                subtitle: Some("Push to remote".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("git push".to_string()),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "git_pull".to_string(),
                title: "Git: Pull".to_string(),
                subtitle: Some("Pull from remote".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("git pull".to_string()),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "git_log".to_string(),
                title: "Git: Log".to_string(),
                subtitle: Some("Show commit history".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("git log --oneline -20".to_string()),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "git_diff".to_string(),
                title: "Git: Diff".to_string(),
                subtitle: Some("Show changes".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("git diff".to_string()),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "git_branch".to_string(),
                title: "Git: Branches".to_string(),
                subtitle: Some("List branches".to_string()),
                category: ItemCategory::Git,
                icon: Some("git".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("git branch -a".to_string()),
                score: 0.0,
                frequency: 0,
            },

            // Actions
            PaletteItem {
                id: "new_file".to_string(),
                title: "New File".to_string(),
                subtitle: Some("Create a new file".to_string()),
                category: ItemCategory::Action,
                icon: Some("file-plus".to_string()),
                shortcut: Some("Cmd+N".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::NewFile),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "new_folder".to_string(),
                title: "New Folder".to_string(),
                subtitle: Some("Create a new folder".to_string()),
                category: ItemCategory::Action,
                icon: Some("folder-plus".to_string()),
                shortcut: Some("Cmd+Shift+N".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::NewFolder),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "new_terminal".to_string(),
                title: "New Terminal".to_string(),
                subtitle: Some("Open new terminal tab".to_string()),
                category: ItemCategory::Action,
                icon: Some("terminal".to_string()),
                shortcut: Some("Cmd+T".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::NewTerminal),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "split_pane".to_string(),
                title: "Split Pane".to_string(),
                subtitle: Some("Split terminal horizontally".to_string()),
                category: ItemCategory::Action,
                icon: Some("columns".to_string()),
                shortcut: Some("Cmd+D".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::SplitPane),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "clear".to_string(),
                title: "Clear Terminal".to_string(),
                subtitle: Some("Clear terminal output".to_string()),
                category: ItemCategory::Action,
                icon: Some("trash".to_string()),
                shortcut: Some("Cmd+K".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::ClearTerminal),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "search_files".to_string(),
                title: "Search in Files".to_string(),
                subtitle: Some("Search text across files".to_string()),
                category: ItemCategory::Action,
                icon: Some("search".to_string()),
                shortcut: Some("Cmd+Shift+F".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::SearchInFiles),
                score: 0.0,
                frequency: 0,
            },

            // Common commands
            PaletteItem {
                id: "ls".to_string(),
                title: "List Files".to_string(),
                subtitle: Some("ls -la".to_string()),
                category: ItemCategory::Command,
                icon: Some("folder".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("ls -la".to_string()),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "pwd".to_string(),
                title: "Current Directory".to_string(),
                subtitle: Some("pwd".to_string()),
                category: ItemCategory::Command,
                icon: Some("folder".to_string()),
                shortcut: None,
                action: PaletteAction::Execute("pwd".to_string()),
                score: 0.0,
                frequency: 0,
            },

            // Settings
            PaletteItem {
                id: "settings".to_string(),
                title: "Settings".to_string(),
                subtitle: Some("Open preferences".to_string()),
                category: ItemCategory::Setting,
                icon: Some("settings".to_string()),
                shortcut: Some("Cmd+,".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::ShowSettings),
                score: 0.0,
                frequency: 0,
            },
            PaletteItem {
                id: "help".to_string(),
                title: "Help".to_string(),
                subtitle: Some("Show help".to_string()),
                category: ItemCategory::Setting,
                icon: Some("help-circle".to_string()),
                shortcut: Some("Cmd+?".to_string()),
                action: PaletteAction::BuiltIn(BuiltInAction::ShowHelp),
                score: 0.0,
                frequency: 0,
            },
        ]
    }
}

// Global palette
lazy_static::lazy_static! {
    pub static ref COMMAND_PALETTE: std::sync::Mutex<CommandPalette> =
        std::sync::Mutex::new(CommandPalette::new());
}

pub fn palette() -> std::sync::MutexGuard<'static, CommandPalette> {
    COMMAND_PALETTE.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fuzzy_exact_match() {
        assert_eq!(FuzzyMatcher::score("git", "git"), Some(1.0));
    }

    #[test]
    fn test_fuzzy_starts_with() {
        let score = FuzzyMatcher::score("git", "git status").unwrap();
        assert!(score >= 0.9);
    }

    #[test]
    fn test_fuzzy_contains() {
        let score = FuzzyMatcher::score("status", "git status").unwrap();
        assert!(score >= 0.5);
    }

    #[test]
    fn test_fuzzy_no_match() {
        assert!(FuzzyMatcher::score("xyz", "git status").is_none());
    }

    #[test]
    fn test_word_boundary() {
        // "gs" should match "git status" via initials
        let score = FuzzyMatcher::score_word_boundary("gs", "git status").unwrap();
        assert!(score >= 0.8);
    }

    #[test]
    fn test_palette_search() {
        let palette = CommandPalette::new();
        let results = palette.search("git", None);

        assert!(!results.items.is_empty());
        assert!(results.items.iter().all(|i| i.title.to_lowercase().contains("git")));
    }
}
