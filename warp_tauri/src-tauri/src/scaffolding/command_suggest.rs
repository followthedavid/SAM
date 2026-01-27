//! Command Suggestions - Predict next command
//!
//! Provides intelligent command suggestions based on:
//! - Command history patterns
//! - Current directory context
//! - Git state
//! - Recent errors
//! - Workflow patterns

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

/// A command suggestion
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Suggestion {
    /// The suggested command
    pub command: String,
    /// Confidence score (0-1)
    pub score: f32,
    /// Why this was suggested
    pub reason: SuggestionReason,
    /// Whether this is from history
    pub from_history: bool,
    /// Times this pattern occurred
    pub occurrences: u32,
}

/// Reason for suggestion
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SuggestionReason {
    /// Frequently follows previous command
    FollowsPattern,
    /// Common in this directory
    DirectoryPattern,
    /// Common after error
    ErrorRecovery,
    /// Git workflow pattern
    GitWorkflow,
    /// Recently used
    Recent,
    /// Typo correction
    TypoCorrection,
    /// AI-generated
    AiSuggestion,
}

/// Command context for suggestions
#[derive(Debug, Clone, Default)]
pub struct CommandContext {
    /// Previous command
    pub prev_command: Option<String>,
    /// Previous exit code
    pub prev_exit_code: Option<i32>,
    /// Current directory
    pub cwd: String,
    /// Git branch (if in repo)
    pub git_branch: Option<String>,
    /// Git has uncommitted changes
    pub git_dirty: bool,
    /// Current input (partial)
    pub current_input: String,
}

// =============================================================================
// COMMAND SUGGESTER
// =============================================================================

pub struct CommandSuggester {
    /// Command sequences: (prev_cmd, next_cmd) -> count
    sequences: HashMap<(String, String), u32>,
    /// Directory patterns: (dir, cmd) -> count
    dir_patterns: HashMap<(String, String), u32>,
    /// Error recovery patterns: (failed_cmd, recovery_cmd) -> count
    error_patterns: HashMap<(String, String), u32>,
    /// Recent commands
    recent: Vec<String>,
    /// Git workflow patterns
    git_patterns: Vec<(Vec<String>, String)>,
    /// Total commands seen
    total_commands: u64,
}

impl CommandSuggester {
    pub fn new() -> Self {
        let mut suggester = Self {
            sequences: HashMap::new(),
            dir_patterns: HashMap::new(),
            error_patterns: HashMap::new(),
            recent: Vec::new(),
            git_patterns: Vec::new(),
            total_commands: 0,
        };
        suggester.load_git_patterns();
        suggester
    }

    fn load_git_patterns(&mut self) {
        // Common git workflows
        self.git_patterns = vec![
            // After git status
            (vec!["git status".into()], "git add .".into()),
            (vec!["git status".into()], "git diff".into()),

            // After git add
            (vec!["git add".into()], "git commit -m ''".into()),
            (vec!["git add .".into()], "git commit -m ''".into()),

            // After git commit
            (vec!["git commit".into()], "git push".into()),

            // After git pull with conflicts
            (vec!["git pull".into()], "git status".into()),

            // After git checkout
            (vec!["git checkout".into()], "git pull".into()),

            // Branch operations
            (vec!["git branch".into()], "git checkout".into()),
            (vec!["git checkout -b".into()], "git push -u origin".into()),

            // Stash workflow
            (vec!["git stash".into()], "git pull".into()),
            (vec!["git pull".into(), "git stash".into()], "git stash pop".into()),
        ];
    }

    /// Record a command execution
    pub fn record_command(&mut self, command: &str, context: &CommandContext) {
        if command.is_empty() {
            return;
        }

        self.total_commands += 1;
        let cmd = normalize_command(command);

        // Record sequence pattern
        if let Some(ref prev) = context.prev_command {
            let prev_norm = normalize_command(prev);
            let key = (prev_norm, cmd.clone());
            *self.sequences.entry(key).or_insert(0) += 1;
        }

        // Record directory pattern
        let dir_key = (context.cwd.clone(), cmd.clone());
        *self.dir_patterns.entry(dir_key).or_insert(0) += 1;

        // Record error recovery pattern
        if context.prev_exit_code.map(|c| c != 0).unwrap_or(false) {
            if let Some(ref prev) = context.prev_command {
                let prev_norm = normalize_command(prev);
                let key = (prev_norm, cmd.clone());
                *self.error_patterns.entry(key).or_insert(0) += 1;
            }
        }

        // Add to recent
        if self.recent.last().map(|s| s.as_str()) != Some(&cmd) {
            self.recent.push(cmd);
            if self.recent.len() > 100 {
                self.recent.remove(0);
            }
        }
    }

    /// Get suggestions based on context
    pub fn suggest(&self, context: &CommandContext, max_results: usize) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // If there's current input, filter based on prefix
        let filter_prefix = if !context.current_input.is_empty() {
            Some(context.current_input.to_lowercase())
        } else {
            None
        };

        // 1. Sequence-based suggestions
        if let Some(ref prev) = context.prev_command {
            let prev_norm = normalize_command(prev);
            for ((p, next), count) in &self.sequences {
                if p == &prev_norm {
                    if let Some(ref prefix) = filter_prefix {
                        if !next.to_lowercase().starts_with(prefix) {
                            continue;
                        }
                    }
                    suggestions.push(Suggestion {
                        command: next.clone(),
                        score: calculate_score(*count, self.total_commands),
                        reason: SuggestionReason::FollowsPattern,
                        from_history: true,
                        occurrences: *count,
                    });
                }
            }
        }

        // 2. Directory-based suggestions
        for ((dir, cmd), count) in &self.dir_patterns {
            if dir == &context.cwd {
                if let Some(ref prefix) = filter_prefix {
                    if !cmd.to_lowercase().starts_with(prefix) {
                        continue;
                    }
                }
                let existing = suggestions.iter_mut().find(|s| s.command == *cmd);
                if let Some(s) = existing {
                    s.score += calculate_score(*count, self.total_commands) * 0.5;
                } else {
                    suggestions.push(Suggestion {
                        command: cmd.clone(),
                        score: calculate_score(*count, self.total_commands) * 0.8,
                        reason: SuggestionReason::DirectoryPattern,
                        from_history: true,
                        occurrences: *count,
                    });
                }
            }
        }

        // 3. Error recovery suggestions
        if context.prev_exit_code.map(|c| c != 0).unwrap_or(false) {
            if let Some(ref prev) = context.prev_command {
                let prev_norm = normalize_command(prev);
                for ((p, recovery), count) in &self.error_patterns {
                    if p == &prev_norm {
                        if let Some(ref prefix) = filter_prefix {
                            if !recovery.to_lowercase().starts_with(prefix) {
                                continue;
                            }
                        }
                        suggestions.push(Suggestion {
                            command: recovery.clone(),
                            score: calculate_score(*count, self.total_commands) * 2.0, // Boost error recovery
                            reason: SuggestionReason::ErrorRecovery,
                            from_history: true,
                            occurrences: *count,
                        });
                    }
                }
            }
        }

        // 4. Git workflow suggestions
        if context.git_branch.is_some() {
            if let Some(ref prev) = context.prev_command {
                for (pattern, next) in &self.git_patterns {
                    if pattern.iter().any(|p| prev.contains(p)) {
                        if let Some(ref prefix) = filter_prefix {
                            if !next.to_lowercase().starts_with(prefix) {
                                continue;
                            }
                        }
                        suggestions.push(Suggestion {
                            command: next.clone(),
                            score: 0.7,
                            reason: SuggestionReason::GitWorkflow,
                            from_history: false,
                            occurrences: 0,
                        });
                    }
                }
            }
        }

        // 5. Recent commands
        for (i, cmd) in self.recent.iter().rev().enumerate() {
            if let Some(ref prefix) = filter_prefix {
                if !cmd.to_lowercase().starts_with(prefix) {
                    continue;
                }
            }
            if !suggestions.iter().any(|s| &s.command == cmd) {
                suggestions.push(Suggestion {
                    command: cmd.clone(),
                    score: 0.3 / (i + 1) as f32,
                    reason: SuggestionReason::Recent,
                    from_history: true,
                    occurrences: 1,
                });
            }
        }

        // Sort by score and deduplicate
        suggestions.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        suggestions.dedup_by(|a, b| a.command == b.command);
        suggestions.truncate(max_results);

        suggestions
    }

    /// Get typo corrections
    pub fn correct_typo(&self, input: &str) -> Option<Suggestion> {
        let input_lower = input.to_lowercase();

        // Check common typos
        let corrections = [
            ("gti", "git"),
            ("giit", "git"),
            ("sl", "ls"),
            ("cta", "cat"),
            ("mkdri", "mkdir"),
            ("rn", "rm"),
            ("pyhton", "python"),
            ("pytohn", "python"),
            ("nmp", "npm"),
            ("yran", "yarn"),
            ("dcoker", "docker"),
            ("kubeclt", "kubectl"),
        ];

        for (typo, correct) in &corrections {
            if input_lower.starts_with(typo) {
                let corrected = input.replacen(typo, correct, 1);
                return Some(Suggestion {
                    command: corrected,
                    score: 0.9,
                    reason: SuggestionReason::TypoCorrection,
                    from_history: false,
                    occurrences: 0,
                });
            }
        }

        // Check against recent commands using edit distance
        for cmd in self.recent.iter().rev().take(20) {
            if edit_distance(&input_lower, &cmd.to_lowercase()) <= 2 {
                return Some(Suggestion {
                    command: cmd.clone(),
                    score: 0.8,
                    reason: SuggestionReason::TypoCorrection,
                    from_history: true,
                    occurrences: 1,
                });
            }
        }

        None
    }

    /// Clear learned patterns
    pub fn clear(&mut self) {
        self.sequences.clear();
        self.dir_patterns.clear();
        self.error_patterns.clear();
        self.recent.clear();
        self.total_commands = 0;
    }

    /// Get stats
    pub fn stats(&self) -> SuggesterStats {
        SuggesterStats {
            total_commands: self.total_commands,
            unique_sequences: self.sequences.len(),
            dir_patterns: self.dir_patterns.len(),
            error_patterns: self.error_patterns.len(),
            recent_count: self.recent.len(),
        }
    }
}

impl Default for CommandSuggester {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SuggesterStats {
    pub total_commands: u64,
    pub unique_sequences: usize,
    pub dir_patterns: usize,
    pub error_patterns: usize,
    pub recent_count: usize,
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn normalize_command(cmd: &str) -> String {
    // Remove arguments that vary (file paths, etc.) but keep structure
    let parts: Vec<&str> = cmd.split_whitespace().collect();
    if parts.is_empty() {
        return String::new();
    }

    // Keep command and first argument/flag
    let base = parts[0];

    // For common commands, normalize the pattern
    match base {
        "cd" | "cat" | "vim" | "nvim" | "nano" | "code" | "open" => {
            // Keep just the command
            base.to_string()
        }
        "git" => {
            // Keep git + subcommand
            if parts.len() > 1 {
                format!("{} {}", base, parts[1])
            } else {
                base.to_string()
            }
        }
        "npm" | "yarn" | "pnpm" | "cargo" | "docker" | "kubectl" => {
            // Keep command + subcommand
            if parts.len() > 1 {
                format!("{} {}", base, parts[1])
            } else {
                base.to_string()
            }
        }
        _ => {
            // Keep first two parts
            parts.iter().take(2).copied().collect::<Vec<_>>().join(" ")
        }
    }
}

fn calculate_score(count: u32, total: u64) -> f32 {
    if total == 0 {
        return 0.0;
    }
    let freq = count as f64 / total as f64;
    (freq.sqrt() as f32).min(1.0)
}

fn edit_distance(a: &str, b: &str) -> usize {
    let a_chars: Vec<char> = a.chars().collect();
    let b_chars: Vec<char> = b.chars().collect();
    let m = a_chars.len();
    let n = b_chars.len();

    if m == 0 { return n; }
    if n == 0 { return m; }

    let mut dp = vec![vec![0; n + 1]; m + 1];

    for i in 0..=m { dp[i][0] = i; }
    for j in 0..=n { dp[0][j] = j; }

    for i in 1..=m {
        for j in 1..=n {
            let cost = if a_chars[i-1] == b_chars[j-1] { 0 } else { 1 };
            dp[i][j] = (dp[i-1][j] + 1)
                .min(dp[i][j-1] + 1)
                .min(dp[i-1][j-1] + cost);
        }
    }

    dp[m][n]
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref COMMAND_SUGGESTER: Arc<Mutex<CommandSuggester>> =
        Arc::new(Mutex::new(CommandSuggester::new()));
}

/// Get the global suggester
pub fn suggester() -> Arc<Mutex<CommandSuggester>> {
    COMMAND_SUGGESTER.clone()
}

/// Record a command
pub fn record(command: &str, context: &CommandContext) {
    COMMAND_SUGGESTER.lock().unwrap().record_command(command, context);
}

/// Get suggestions
pub fn suggest(context: &CommandContext, max: usize) -> Vec<Suggestion> {
    COMMAND_SUGGESTER.lock().unwrap().suggest(context, max)
}

/// Correct typo
pub fn correct_typo(input: &str) -> Option<Suggestion> {
    COMMAND_SUGGESTER.lock().unwrap().correct_typo(input)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_record_and_suggest() {
        let mut suggester = CommandSuggester::new();

        let ctx = CommandContext {
            prev_command: Some("git status".into()),
            cwd: "/home/user/project".into(),
            ..Default::default()
        };

        // Record pattern multiple times
        for _ in 0..5 {
            suggester.record_command("git add .", &ctx);
        }

        let ctx2 = CommandContext {
            prev_command: Some("git status".into()),
            cwd: "/home/user/project".into(),
            ..Default::default()
        };

        let suggestions = suggester.suggest(&ctx2, 5);
        assert!(!suggestions.is_empty());
        assert!(suggestions.iter().any(|s| s.command.contains("git add")));
    }

    #[test]
    fn test_directory_patterns() {
        let mut suggester = CommandSuggester::new();

        let ctx = CommandContext {
            cwd: "/home/user/rust-project".into(),
            ..Default::default()
        };

        for _ in 0..3 {
            suggester.record_command("cargo build", &ctx);
        }

        let suggestions = suggester.suggest(&ctx, 5);
        assert!(suggestions.iter().any(|s| s.command.contains("cargo")));
    }

    #[test]
    fn test_error_recovery() {
        let mut suggester = CommandSuggester::new();

        // Record: when git push fails, user does git pull
        let fail_ctx = CommandContext {
            prev_command: Some("git push".into()),
            prev_exit_code: Some(1),
            ..Default::default()
        };

        for _ in 0..3 {
            suggester.record_command("git pull", &fail_ctx);
        }

        // Now when git push fails again, should suggest git pull
        let new_ctx = CommandContext {
            prev_command: Some("git push".into()),
            prev_exit_code: Some(1),
            ..Default::default()
        };

        let suggestions = suggester.suggest(&new_ctx, 5);
        let recovery = suggestions.iter().find(|s| matches!(s.reason, SuggestionReason::ErrorRecovery));
        assert!(recovery.is_some());
    }

    #[test]
    fn test_typo_correction() {
        let suggester = CommandSuggester::new();

        let correction = suggester.correct_typo("gti status");
        assert!(correction.is_some());
        assert!(correction.unwrap().command.starts_with("git"));
    }

    #[test]
    fn test_normalize_command() {
        assert_eq!(normalize_command("git commit -m 'message'"), "git commit");
        assert_eq!(normalize_command("cd /some/path"), "cd");
        assert_eq!(normalize_command("npm install package"), "npm install");
    }

    #[test]
    fn test_edit_distance() {
        assert_eq!(edit_distance("kitten", "sitten"), 1);
        assert_eq!(edit_distance("git", "gti"), 2);
        assert_eq!(edit_distance("hello", "hello"), 0);
    }

    #[test]
    fn test_filter_by_prefix() {
        let mut suggester = CommandSuggester::new();

        let ctx = CommandContext::default();
        suggester.record_command("git status", &ctx);
        suggester.record_command("npm install", &ctx);
        suggester.record_command("cargo build", &ctx);

        let filter_ctx = CommandContext {
            current_input: "gi".into(),
            ..Default::default()
        };

        let suggestions = suggester.suggest(&filter_ctx, 10);
        assert!(suggestions.iter().all(|s| s.command.to_lowercase().starts_with("gi")));
    }

    #[test]
    fn test_git_workflow() {
        let suggester = CommandSuggester::new();

        let ctx = CommandContext {
            prev_command: Some("git add .".into()),
            git_branch: Some("main".into()),
            ..Default::default()
        };

        let suggestions = suggester.suggest(&ctx, 5);
        let git_suggestion = suggestions.iter().find(|s| matches!(s.reason, SuggestionReason::GitWorkflow));
        assert!(git_suggestion.is_some());
    }
}
