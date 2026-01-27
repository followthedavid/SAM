// Auto-Complete Engine - Context-aware suggestions
//
// Provides intelligent auto-completion for:
// - Commands (shell, git, npm, cargo)
// - File paths
// - Code snippets
// - Natural language prompts

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Suggestion {
    pub text: String,
    pub display: String,
    pub description: Option<String>,
    pub kind: SuggestionKind,
    pub score: f32,
    pub source: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum SuggestionKind {
    Command,
    FilePath,
    Directory,
    GitBranch,
    GitCommand,
    NpmScript,
    CargoCommand,
    CodeSnippet,
    HistoryEntry,
    Template,
    Skill,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CompletionContext {
    pub input: String,
    pub cursor_position: usize,
    pub working_dir: PathBuf,
    pub history: Vec<String>,
    pub project_type: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoCompleteConfig {
    pub max_suggestions: usize,
    pub min_score: f32,
    pub enable_fuzzy: bool,
    pub enable_history: bool,
    pub enable_files: bool,
    pub enable_commands: bool,
    pub enable_snippets: bool,
}

impl Default for AutoCompleteConfig {
    fn default() -> Self {
        Self {
            max_suggestions: 10,
            min_score: 0.3,
            enable_fuzzy: true,
            enable_history: true,
            enable_files: true,
            enable_commands: true,
            enable_snippets: true,
        }
    }
}

// =============================================================================
// AUTO-COMPLETE ENGINE
// =============================================================================

pub struct AutoCompleteEngine {
    config: AutoCompleteConfig,
    command_cache: HashMap<String, Vec<String>>,
    snippet_library: Vec<CodeSnippet>,
    history: Vec<String>,
}

#[derive(Debug, Clone)]
#[allow(dead_code)]
struct CodeSnippet {
    trigger: String,
    content: String,
    description: String,
    language: Option<String>,
}

impl AutoCompleteEngine {
    pub fn new(config: AutoCompleteConfig) -> Self {
        let mut engine = Self {
            config,
            command_cache: HashMap::new(),
            snippet_library: Vec::new(),
            history: Vec::new(),
        };
        engine.init_commands();
        engine.init_snippets();
        engine
    }

    /// Get completions for input
    pub fn complete(&self, ctx: &CompletionContext) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();
        let input = ctx.input.trim();

        if input.is_empty() {
            return self.get_default_suggestions(ctx);
        }

        // Determine completion type based on input
        let word = self.get_current_word(input, ctx.cursor_position);

        // Command completions
        if self.config.enable_commands && !input.contains(' ') {
            suggestions.extend(self.complete_commands(&word));
        }

        // File path completions
        if self.config.enable_files && (word.starts_with('.') || word.starts_with('/') || word.starts_with('~')) {
            suggestions.extend(self.complete_paths(&word, &ctx.working_dir));
        }

        // Git completions
        if input.starts_with("git ") {
            suggestions.extend(self.complete_git(&word, &ctx.working_dir));
        }

        // NPM completions
        if input.starts_with("npm ") || input.starts_with("pnpm ") || input.starts_with("yarn ") {
            suggestions.extend(self.complete_npm(&word, &ctx.working_dir));
        }

        // Cargo completions
        if input.starts_with("cargo ") {
            suggestions.extend(self.complete_cargo(&word));
        }

        // History completions
        if self.config.enable_history {
            suggestions.extend(self.complete_history(&word, &ctx.history));
        }

        // Snippet completions
        if self.config.enable_snippets {
            suggestions.extend(self.complete_snippets(&word));
        }

        // Skill completions (slash commands)
        if word.starts_with('/') {
            suggestions.extend(self.complete_skills(&word));
        }

        // Sort by score and limit
        suggestions.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap());
        suggestions.truncate(self.config.max_suggestions);

        suggestions
    }

    fn get_current_word(&self, input: &str, cursor: usize) -> String {
        let chars: Vec<char> = input.chars().collect();
        let cursor = cursor.min(chars.len());

        // Find word boundaries
        let mut start = cursor;
        while start > 0 && !chars[start - 1].is_whitespace() {
            start -= 1;
        }

        chars[start..cursor].iter().collect()
    }

    fn get_default_suggestions(&self, ctx: &CompletionContext) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // Recent history
        for (i, cmd) in ctx.history.iter().rev().take(5).enumerate() {
            suggestions.push(Suggestion {
                text: cmd.clone(),
                display: cmd.clone(),
                description: Some("Recent command".to_string()),
                kind: SuggestionKind::HistoryEntry,
                score: 0.9 - (i as f32 * 0.1),
                source: "history".to_string(),
            });
        }

        // Common commands
        for cmd in ["git status", "ls", "cd", "cat", "grep"] {
            suggestions.push(Suggestion {
                text: cmd.to_string(),
                display: cmd.to_string(),
                description: None,
                kind: SuggestionKind::Command,
                score: 0.5,
                source: "common".to_string(),
            });
        }

        suggestions
    }

    fn complete_commands(&self, prefix: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        for (category, commands) in &self.command_cache {
            for cmd in commands {
                if self.matches(cmd, prefix) {
                    suggestions.push(Suggestion {
                        text: cmd.clone(),
                        display: cmd.clone(),
                        description: Some(category.clone()),
                        kind: SuggestionKind::Command,
                        score: self.score(cmd, prefix),
                        source: category.clone(),
                    });
                }
            }
        }

        suggestions
    }

    fn complete_paths(&self, prefix: &str, working_dir: &Path) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // Expand ~ to home directory
        let path_str = if prefix.starts_with('~') {
            std::env::var("HOME")
                .map(|h| prefix.replacen('~', &h, 1))
                .unwrap_or_else(|_| prefix.to_string())
        } else if prefix.starts_with('.') || !prefix.starts_with('/') {
            working_dir.join(prefix).display().to_string()
        } else {
            prefix.to_string()
        };

        let path = Path::new(&path_str);
        let (dir, file_prefix) = if path.is_dir() {
            (path.to_path_buf(), String::new())
        } else {
            (
                path.parent().unwrap_or(Path::new(".")).to_path_buf(),
                path.file_name()
                    .map(|s| s.to_string_lossy().to_string())
                    .unwrap_or_default(),
            )
        };

        if let Ok(entries) = std::fs::read_dir(&dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if file_prefix.is_empty() || self.matches(&name, &file_prefix) {
                    let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
                    let display_path = if prefix.starts_with('~') {
                        if let Ok(home) = std::env::var("HOME") {
                            format!("~/{}", entry.path().strip_prefix(&home).unwrap_or(&entry.path()).display())
                        } else {
                            entry.path().display().to_string()
                        }
                    } else {
                        entry.path().display().to_string()
                    };

                    suggestions.push(Suggestion {
                        text: if is_dir { format!("{}/", display_path) } else { display_path.clone() },
                        display: name.clone(),
                        description: Some(if is_dir { "Directory".to_string() } else { "File".to_string() }),
                        kind: if is_dir { SuggestionKind::Directory } else { SuggestionKind::FilePath },
                        score: self.score(&name, &file_prefix),
                        source: "filesystem".to_string(),
                    });
                }
            }
        }

        suggestions
    }

    fn complete_git(&self, word: &str, working_dir: &Path) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // Git subcommands
        let git_commands = [
            ("status", "Show working tree status"),
            ("add", "Add file contents to index"),
            ("commit", "Record changes to repository"),
            ("push", "Update remote refs"),
            ("pull", "Fetch and integrate with remote"),
            ("checkout", "Switch branches or restore files"),
            ("branch", "List, create, or delete branches"),
            ("merge", "Join development histories"),
            ("rebase", "Reapply commits on top of another base"),
            ("log", "Show commit logs"),
            ("diff", "Show changes between commits"),
            ("stash", "Stash changes in a dirty working directory"),
            ("reset", "Reset current HEAD to specified state"),
        ];

        for (cmd, desc) in git_commands {
            if self.matches(cmd, word) {
                suggestions.push(Suggestion {
                    text: format!("git {}", cmd),
                    display: cmd.to_string(),
                    description: Some(desc.to_string()),
                    kind: SuggestionKind::GitCommand,
                    score: self.score(cmd, word),
                    source: "git".to_string(),
                });
            }
        }

        // Git branches
        if let Ok(output) = std::process::Command::new("git")
            .args(["branch", "--list"])
            .current_dir(working_dir)
            .output()
        {
            let branches = String::from_utf8_lossy(&output.stdout);
            for branch in branches.lines() {
                let branch = branch.trim().trim_start_matches("* ");
                if self.matches(branch, word) {
                    suggestions.push(Suggestion {
                        text: branch.to_string(),
                        display: branch.to_string(),
                        description: Some("Branch".to_string()),
                        kind: SuggestionKind::GitBranch,
                        score: self.score(branch, word),
                        source: "git".to_string(),
                    });
                }
            }
        }

        suggestions
    }

    fn complete_npm(&self, word: &str, working_dir: &Path) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // NPM subcommands
        let npm_commands = [
            ("install", "Install a package"),
            ("run", "Run a script"),
            ("test", "Run tests"),
            ("build", "Build the project"),
            ("start", "Start the project"),
            ("dev", "Run in development mode"),
        ];

        for (cmd, desc) in npm_commands {
            if self.matches(cmd, word) {
                suggestions.push(Suggestion {
                    text: format!("npm {}", cmd),
                    display: cmd.to_string(),
                    description: Some(desc.to_string()),
                    kind: SuggestionKind::NpmScript,
                    score: self.score(cmd, word),
                    source: "npm".to_string(),
                });
            }
        }

        // NPM scripts from package.json
        let package_json = working_dir.join("package.json");
        if package_json.exists() {
            if let Ok(content) = std::fs::read_to_string(&package_json) {
                if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(scripts) = json["scripts"].as_object() {
                        for script_name in scripts.keys() {
                            if self.matches(script_name, word) {
                                suggestions.push(Suggestion {
                                    text: format!("npm run {}", script_name),
                                    display: script_name.clone(),
                                    description: Some("npm script".to_string()),
                                    kind: SuggestionKind::NpmScript,
                                    score: self.score(script_name, word) + 0.1,
                                    source: "package.json".to_string(),
                                });
                            }
                        }
                    }
                }
            }
        }

        suggestions
    }

    fn complete_cargo(&self, word: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        let cargo_commands = [
            ("build", "Compile the current package"),
            ("run", "Run the current package"),
            ("test", "Run the tests"),
            ("check", "Check the current package"),
            ("clippy", "Run Clippy lints"),
            ("fmt", "Format the current package"),
            ("doc", "Build documentation"),
            ("clean", "Remove build artifacts"),
            ("update", "Update dependencies"),
            ("add", "Add a dependency"),
        ];

        for (cmd, desc) in cargo_commands {
            if self.matches(cmd, word) {
                suggestions.push(Suggestion {
                    text: format!("cargo {}", cmd),
                    display: cmd.to_string(),
                    description: Some(desc.to_string()),
                    kind: SuggestionKind::CargoCommand,
                    score: self.score(cmd, word),
                    source: "cargo".to_string(),
                });
            }
        }

        suggestions
    }

    fn complete_history(&self, word: &str, history: &[String]) -> Vec<Suggestion> {
        history
            .iter()
            .rev()
            .filter(|cmd| self.matches(cmd, word))
            .take(5)
            .enumerate()
            .map(|(i, cmd)| Suggestion {
                text: cmd.clone(),
                display: cmd.clone(),
                description: Some("History".to_string()),
                kind: SuggestionKind::HistoryEntry,
                score: self.score(cmd, word) + 0.2 - (i as f32 * 0.05),
                source: "history".to_string(),
            })
            .collect()
    }

    fn complete_snippets(&self, word: &str) -> Vec<Suggestion> {
        self.snippet_library
            .iter()
            .filter(|s| self.matches(&s.trigger, word))
            .map(|s| Suggestion {
                text: s.content.clone(),
                display: s.trigger.clone(),
                description: Some(s.description.clone()),
                kind: SuggestionKind::CodeSnippet,
                score: self.score(&s.trigger, word),
                source: "snippets".to_string(),
            })
            .collect()
    }

    fn complete_skills(&self, word: &str) -> Vec<Suggestion> {
        use crate::scaffolding::skills::list_skills;

        list_skills()
            .iter()
            .filter(|s| self.matches(&format!("/{}", s.id), word))
            .map(|s| Suggestion {
                text: format!("/{}", s.id),
                display: format!("/{}", s.id),
                description: Some(s.description.clone()),
                kind: SuggestionKind::Skill,
                score: self.score(&s.id, &word[1..]),
                source: "skills".to_string(),
            })
            .collect()
    }

    fn matches(&self, text: &str, pattern: &str) -> bool {
        if pattern.is_empty() {
            return true;
        }

        if self.config.enable_fuzzy {
            self.fuzzy_match(text, pattern)
        } else {
            text.to_lowercase().starts_with(&pattern.to_lowercase())
        }
    }

    fn fuzzy_match(&self, text: &str, pattern: &str) -> bool {
        let text = text.to_lowercase();
        let pattern = pattern.to_lowercase();

        let mut pattern_chars = pattern.chars().peekable();
        for c in text.chars() {
            if pattern_chars.peek() == Some(&c) {
                pattern_chars.next();
            }
            if pattern_chars.peek().is_none() {
                return true;
            }
        }

        pattern_chars.peek().is_none()
    }

    fn score(&self, text: &str, pattern: &str) -> f32 {
        if pattern.is_empty() {
            return 0.5;
        }

        let text_lower = text.to_lowercase();
        let pattern_lower = pattern.to_lowercase();

        // Exact match
        if text_lower == pattern_lower {
            return 1.0;
        }

        // Prefix match
        if text_lower.starts_with(&pattern_lower) {
            return 0.9 - (text.len() as f32 - pattern.len() as f32) * 0.01;
        }

        // Contains match
        if text_lower.contains(&pattern_lower) {
            return 0.7;
        }

        // Fuzzy match
        if self.fuzzy_match(text, pattern) {
            return 0.5;
        }

        0.0
    }

    fn init_commands(&mut self) {
        self.command_cache.insert("shell".to_string(), vec![
            "ls".to_string(), "cd".to_string(), "pwd".to_string(),
            "cat".to_string(), "grep".to_string(), "find".to_string(),
            "mkdir".to_string(), "rm".to_string(), "cp".to_string(),
            "mv".to_string(), "chmod".to_string(), "echo".to_string(),
        ]);

        self.command_cache.insert("git".to_string(), vec![
            "git".to_string(),
        ]);

        self.command_cache.insert("npm".to_string(), vec![
            "npm".to_string(), "npx".to_string(), "pnpm".to_string(), "yarn".to_string(),
        ]);

        self.command_cache.insert("cargo".to_string(), vec![
            "cargo".to_string(), "rustc".to_string(), "rustup".to_string(),
        ]);
    }

    fn init_snippets(&mut self) {
        self.snippet_library = vec![
            CodeSnippet {
                trigger: "fn".to_string(),
                content: "fn name() {\n    \n}".to_string(),
                description: "Rust function".to_string(),
                language: Some("rust".to_string()),
            },
            CodeSnippet {
                trigger: "impl".to_string(),
                content: "impl Type {\n    \n}".to_string(),
                description: "Rust impl block".to_string(),
                language: Some("rust".to_string()),
            },
            CodeSnippet {
                trigger: "async".to_string(),
                content: "async fn name() -> Result<(), Error> {\n    \n}".to_string(),
                description: "Async function".to_string(),
                language: Some("rust".to_string()),
            },
        ];
    }

    /// Add to history
    pub fn add_to_history(&mut self, command: &str) {
        if !command.trim().is_empty() {
            self.history.push(command.to_string());
            if self.history.len() > 1000 {
                self.history.remove(0);
            }
        }
    }

    /// Get stats
    pub fn stats(&self) -> AutoCompleteStats {
        AutoCompleteStats {
            history_size: self.history.len(),
            max_suggestions: self.config.max_suggestions,
            snippets_loaded: self.snippet_library.len(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutoCompleteStats {
    pub history_size: usize,
    pub max_suggestions: usize,
    pub snippets_loaded: usize,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref AUTOCOMPLETE: Mutex<AutoCompleteEngine> = Mutex::new(AutoCompleteEngine::new(AutoCompleteConfig::default()));
}

pub fn autocomplete() -> std::sync::MutexGuard<'static, AutoCompleteEngine> {
    AUTOCOMPLETE.lock().unwrap()
}

/// Get completions
pub fn complete(ctx: &CompletionContext) -> Vec<Suggestion> {
    autocomplete().complete(ctx)
}

/// Add command to history
pub fn add_history(command: &str) {
    autocomplete().add_to_history(command);
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fuzzy_match() {
        let engine = AutoCompleteEngine::new(AutoCompleteConfig::default());
        assert!(engine.fuzzy_match("cargo", "crg"));
        assert!(engine.fuzzy_match("status", "st"));
        assert!(!engine.fuzzy_match("git", "xyz"));
    }

    #[test]
    fn test_score() {
        let engine = AutoCompleteEngine::new(AutoCompleteConfig::default());
        assert!(engine.score("git", "git") > engine.score("github", "git"));
        assert!(engine.score("status", "st") > engine.score("status", "at"));
    }

    #[test]
    fn test_complete_commands() {
        let engine = AutoCompleteEngine::new(AutoCompleteConfig::default());
        let suggestions = engine.complete_commands("gi");
        assert!(suggestions.iter().any(|s| s.text == "git"));
    }
}
