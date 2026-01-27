//! Warp Bridge - Integration bridge to warp_core features
//!
//! Connects SAM to warp_core's:
//! - Secret redaction
//! - Command completions
//! - Block sharing
//! - Autocorrect

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// Re-export types from warp_core for convenience
// Note: In actual implementation, would use: use warp_core::{...};
// For now, we define compatible types

// =============================================================================
// SECRET REDACTION BRIDGE
// =============================================================================

/// Secret category for redaction
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum SecretCategory {
    CloudProvider,
    VersionControl,
    Authentication,
    Database,
    Cryptographic,
    Generic,
    Network,
}

/// Result of redaction
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RedactionResult {
    pub redacted_text: String,
    pub original_length: usize,
    pub secrets_found: usize,
    pub categories: Vec<SecretCategory>,
}

/// Secret redactor configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RedactorConfig {
    pub enabled: bool,
    pub redact_ips: bool,
    pub replacement: String,
    pub disabled_categories: Vec<SecretCategory>,
}

impl Default for RedactorConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            redact_ips: false,
            replacement: "••••••••".to_string(),
            disabled_categories: Vec::new(),
        }
    }
}

/// Secret redactor bridge
pub struct SecretRedactorBridge {
    config: RedactorConfig,
    patterns: Vec<SecretPattern>,
}

#[derive(Clone)]
struct SecretPattern {
    name: String,
    regex: regex::Regex,
    category: SecretCategory,
}

impl SecretRedactorBridge {
    pub fn new() -> Self {
        Self::with_config(RedactorConfig::default())
    }

    pub fn with_config(config: RedactorConfig) -> Self {
        let patterns = Self::build_patterns();
        Self { config, patterns }
    }

    fn build_patterns() -> Vec<SecretPattern> {
        let pattern_defs = vec![
            // AWS
            ("AWS Access Key", r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}", SecretCategory::CloudProvider),
            // GitHub
            ("GitHub Token", r"ghp_[A-Za-z0-9]{36,}", SecretCategory::VersionControl),
            ("GitHub OAuth", r"gho_[A-Za-z0-9]{36,}", SecretCategory::VersionControl),
            // JWT
            ("JWT Token", r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*", SecretCategory::Authentication),
            // Bearer
            ("Bearer Token", r"(?i)bearer\s+[A-Za-z0-9_.~+/-]+=*", SecretCategory::Authentication),
            // Database URLs
            ("Database URL", r"(?:postgres|mysql|mongodb|redis)(?:ql)?://[^:]+:[^@]+@[^\s]+", SecretCategory::Database),
            // Private Keys
            ("Private Key", r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----", SecretCategory::Cryptographic),
            // API Keys
            ("OpenAI Key", r"sk-[A-Za-z0-9]{48}", SecretCategory::Generic),
            ("Anthropic Key", r"sk-ant-[A-Za-z0-9_-]{40,}", SecretCategory::Generic),
            ("Stripe Key", r"(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{24,}", SecretCategory::Generic),
            ("Slack Token", r"xox[baprs]-[A-Za-z0-9-]{10,}", SecretCategory::Generic),
            // Generic
            ("Generic API Key", r#"(?i)(?:api[_-]?key|apikey)\s*[=:]\s*['"]?[A-Za-z0-9_-]{20,}['"]?"#, SecretCategory::Generic),
            ("Generic Secret", r#"(?i)(?:secret|password|passwd|pwd)\s*[=:]\s*['"]?[^\s'"]{8,}['"]?"#, SecretCategory::Generic),
            // IP Address
            ("IPv4 Address", r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b", SecretCategory::Network),
        ];

        pattern_defs
            .into_iter()
            .filter_map(|(name, pattern, category)| {
                regex::Regex::new(pattern).ok().map(|regex| SecretPattern {
                    name: name.to_string(),
                    regex,
                    category,
                })
            })
            .collect()
    }

    /// Redact secrets from text
    pub fn redact(&self, text: &str) -> String {
        self.redact_with_info(text).redacted_text
    }

    /// Redact with full information
    pub fn redact_with_info(&self, text: &str) -> RedactionResult {
        if !self.config.enabled {
            return RedactionResult {
                redacted_text: text.to_string(),
                original_length: text.len(),
                secrets_found: 0,
                categories: Vec::new(),
            };
        }

        let mut result = text.to_string();
        let mut secrets_found = 0;
        let mut categories = Vec::new();
        let mut offset: i64 = 0;

        for pattern in &self.patterns {
            // Skip disabled categories
            if self.config.disabled_categories.contains(&pattern.category) {
                continue;
            }

            // Skip IP addresses if not enabled
            if pattern.category == SecretCategory::Network && !self.config.redact_ips {
                continue;
            }

            for mat in pattern.regex.find_iter(text) {
                secrets_found += 1;
                if !categories.contains(&pattern.category) {
                    categories.push(pattern.category.clone());
                }

                let start = (mat.start() as i64 + offset) as usize;
                let end = (mat.end() as i64 + offset) as usize;
                let replacement = &self.config.replacement;

                result.replace_range(start..end, replacement);
                offset += replacement.len() as i64 - (mat.end() - mat.start()) as i64;
            }
        }

        RedactionResult {
            redacted_text: result,
            original_length: text.len(),
            secrets_found,
            categories,
        }
    }

    /// Check if text contains secrets
    pub fn contains_secrets(&self, text: &str) -> bool {
        if !self.config.enabled {
            return false;
        }
        self.patterns.iter().any(|p| {
            if self.config.disabled_categories.contains(&p.category) {
                return false;
            }
            if p.category == SecretCategory::Network && !self.config.redact_ips {
                return false;
            }
            p.regex.is_match(text)
        })
    }

    /// Update configuration
    pub fn set_config(&mut self, config: RedactorConfig) {
        self.config = config;
    }

    /// Get current config
    pub fn config(&self) -> &RedactorConfig {
        &self.config
    }
}

impl Default for SecretRedactorBridge {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// COMPLETION BRIDGE
// =============================================================================

/// Completion suggestion
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Completion {
    pub text: String,
    pub display: Option<String>,
    pub description: Option<String>,
    pub completion_type: CompletionType,
    pub priority: i32,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum CompletionType {
    Command,
    Subcommand,
    Flag,
    Argument,
    File,
    Directory,
    Variable,
}

/// Command completion spec (simplified)
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CommandSpec {
    pub name: String,
    pub description: Option<String>,
    pub subcommands: Vec<String>,
    pub flags: Vec<FlagSpec>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FlagSpec {
    pub names: Vec<String>,
    pub description: Option<String>,
    pub takes_arg: bool,
}

/// Completion engine bridge
pub struct CompletionBridge {
    specs: HashMap<String, CommandSpec>,
    history: Vec<String>,
}

impl CompletionBridge {
    pub fn new() -> Self {
        let mut bridge = Self {
            specs: HashMap::new(),
            history: Vec::new(),
        };
        bridge.load_builtin_specs();
        bridge
    }

    fn load_builtin_specs(&mut self) {
        // Git
        self.specs.insert("git".to_string(), CommandSpec {
            name: "git".to_string(),
            description: Some("Distributed version control".to_string()),
            subcommands: vec![
                "add", "commit", "push", "pull", "fetch", "clone", "checkout",
                "branch", "merge", "rebase", "reset", "stash", "log", "diff",
                "status", "init", "remote", "tag", "cherry-pick",
            ].into_iter().map(String::from).collect(),
            flags: vec![
                FlagSpec { names: vec!["-v".into(), "--version".into()], description: Some("Show version".into()), takes_arg: false },
                FlagSpec { names: vec!["-h".into(), "--help".into()], description: Some("Show help".into()), takes_arg: false },
                FlagSpec { names: vec!["-C".into()], description: Some("Run in directory".into()), takes_arg: true },
            ],
        });

        // Docker
        self.specs.insert("docker".to_string(), CommandSpec {
            name: "docker".to_string(),
            description: Some("Container management".to_string()),
            subcommands: vec![
                "run", "build", "pull", "push", "ps", "images", "exec", "logs",
                "stop", "start", "restart", "rm", "rmi", "network", "volume",
                "compose", "inspect", "top", "stats",
            ].into_iter().map(String::from).collect(),
            flags: vec![
                FlagSpec { names: vec!["-v".into(), "--version".into()], description: Some("Show version".into()), takes_arg: false },
                FlagSpec { names: vec!["-D".into(), "--debug".into()], description: Some("Debug mode".into()), takes_arg: false },
            ],
        });

        // npm
        self.specs.insert("npm".to_string(), CommandSpec {
            name: "npm".to_string(),
            description: Some("Node package manager".to_string()),
            subcommands: vec![
                "install", "uninstall", "run", "start", "test", "build",
                "publish", "init", "update", "audit", "outdated", "list",
                "link", "pack", "cache", "ci", "exec", "version",
            ].into_iter().map(String::from).collect(),
            flags: vec![
                FlagSpec { names: vec!["-g".into(), "--global".into()], description: Some("Install globally".into()), takes_arg: false },
                FlagSpec { names: vec!["-D".into(), "--save-dev".into()], description: Some("Save as dev dependency".into()), takes_arg: false },
            ],
        });

        // cargo
        self.specs.insert("cargo".to_string(), CommandSpec {
            name: "cargo".to_string(),
            description: Some("Rust package manager".to_string()),
            subcommands: vec![
                "build", "run", "test", "check", "clippy", "fmt", "doc",
                "publish", "new", "init", "add", "remove", "update", "search",
                "install", "bench", "clean",
            ].into_iter().map(String::from).collect(),
            flags: vec![
                FlagSpec { names: vec!["--release".into()], description: Some("Build in release mode".into()), takes_arg: false },
                FlagSpec { names: vec!["--all-features".into()], description: Some("Enable all features".into()), takes_arg: false },
            ],
        });

        // kubectl
        self.specs.insert("kubectl".to_string(), CommandSpec {
            name: "kubectl".to_string(),
            description: Some("Kubernetes CLI".to_string()),
            subcommands: vec![
                "get", "apply", "delete", "describe", "logs", "exec",
                "port-forward", "create", "edit", "patch", "scale",
                "rollout", "config", "cluster-info", "top",
            ].into_iter().map(String::from).collect(),
            flags: vec![
                FlagSpec { names: vec!["-n".into(), "--namespace".into()], description: Some("Namespace".into()), takes_arg: true },
                FlagSpec { names: vec!["-o".into(), "--output".into()], description: Some("Output format".into()), takes_arg: true },
            ],
        });

        // Common commands
        for cmd in &["ls", "cd", "pwd", "cat", "grep", "find", "rm", "cp", "mv", "mkdir"] {
            self.specs.insert(cmd.to_string(), CommandSpec {
                name: cmd.to_string(),
                description: None,
                subcommands: Vec::new(),
                flags: Vec::new(),
            });
        }
    }

    /// Get completions for input
    pub fn complete(&self, input: &str, cursor: usize) -> Vec<Completion> {
        let input = &input[..cursor.min(input.len())];
        let parts: Vec<&str> = input.split_whitespace().collect();

        if parts.is_empty() || (parts.len() == 1 && !input.ends_with(' ')) {
            // Complete command names
            let prefix = parts.first().copied().unwrap_or("");
            return self.complete_commands(prefix);
        }

        let command = parts[0];

        if let Some(spec) = self.specs.get(command) {
            self.complete_for_command(spec, &parts[1..], input)
        } else {
            // Unknown command - offer file completions
            self.complete_files(parts.last().copied().unwrap_or(""))
        }
    }

    fn complete_commands(&self, prefix: &str) -> Vec<Completion> {
        self.specs
            .values()
            .filter(|s| s.name.starts_with(prefix))
            .map(|s| Completion {
                text: s.name.clone(),
                display: None,
                description: s.description.clone(),
                completion_type: CompletionType::Command,
                priority: 100,
            })
            .collect()
    }

    fn complete_for_command(&self, spec: &CommandSpec, args: &[&str], input: &str) -> Vec<Completion> {
        let mut completions = Vec::new();
        let current = args.last().copied().unwrap_or("");
        let completing_new = input.ends_with(' ');
        let prefix = if completing_new { "" } else { current };

        // Subcommands
        if args.len() <= 1 {
            for sub in &spec.subcommands {
                if sub.starts_with(prefix) {
                    completions.push(Completion {
                        text: sub.clone(),
                        display: None,
                        description: None,
                        completion_type: CompletionType::Subcommand,
                        priority: 90,
                    });
                }
            }
        }

        // Flags
        if prefix.starts_with('-') || completing_new {
            for flag in &spec.flags {
                for name in &flag.names {
                    if name.starts_with(prefix) {
                        completions.push(Completion {
                            text: name.clone(),
                            display: Some(flag.names.join(", ")),
                            description: flag.description.clone(),
                            completion_type: CompletionType::Flag,
                            priority: 80,
                        });
                    }
                }
            }
        }

        // Files as fallback
        if completions.is_empty() {
            completions.extend(self.complete_files(prefix));
        }

        completions
    }

    fn complete_files(&self, prefix: &str) -> Vec<Completion> {
        let mut completions = Vec::new();

        let dir = if prefix.contains('/') {
            std::path::Path::new(prefix).parent().unwrap_or(std::path::Path::new("."))
        } else {
            std::path::Path::new(".")
        };

        if let Ok(entries) = std::fs::read_dir(dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                let full_path = if prefix.contains('/') {
                    format!("{}/{}", dir.display(), name)
                } else {
                    name.clone()
                };

                let file_prefix = if prefix.contains('/') {
                    prefix.rsplit('/').next().unwrap_or("")
                } else {
                    prefix
                };

                if name.starts_with(file_prefix) {
                    let is_dir = entry.file_type().map(|t| t.is_dir()).unwrap_or(false);
                    completions.push(Completion {
                        text: if is_dir { format!("{}/", full_path) } else { full_path },
                        display: Some(name),
                        description: None,
                        completion_type: if is_dir { CompletionType::Directory } else { CompletionType::File },
                        priority: 70,
                    });
                }
            }
        }

        completions
    }

    /// Add command to history
    pub fn add_history(&mut self, command: &str) {
        if !command.is_empty() && self.history.last().map(|s| s.as_str()) != Some(command) {
            self.history.push(command.to_string());
            if self.history.len() > 1000 {
                self.history.remove(0);
            }
        }
    }

    /// Get history-based suggestions
    pub fn history_suggestions(&self, prefix: &str) -> Vec<Completion> {
        self.history
            .iter()
            .rev()
            .filter(|h| h.starts_with(prefix))
            .take(5)
            .map(|h| Completion {
                text: h.clone(),
                display: None,
                description: Some("from history".to_string()),
                completion_type: CompletionType::Command,
                priority: 110,
            })
            .collect()
    }

    /// Add custom command spec
    pub fn add_spec(&mut self, spec: CommandSpec) {
        self.specs.insert(spec.name.clone(), spec);
    }

    /// Get number of loaded specs
    pub fn spec_count(&self) -> usize {
        self.specs.len()
    }
}

impl Default for CompletionBridge {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCES
// =============================================================================

lazy_static::lazy_static! {
    static ref SECRET_REDACTOR: Arc<Mutex<SecretRedactorBridge>> =
        Arc::new(Mutex::new(SecretRedactorBridge::new()));

    static ref COMPLETION_ENGINE: Arc<Mutex<CompletionBridge>> =
        Arc::new(Mutex::new(CompletionBridge::new()));
}

/// Get the global secret redactor
pub fn redactor() -> Arc<Mutex<SecretRedactorBridge>> {
    SECRET_REDACTOR.clone()
}

/// Redact secrets from text
pub fn redact(text: &str) -> String {
    SECRET_REDACTOR.lock().unwrap().redact(text)
}

/// Redact with info
pub fn redact_with_info(text: &str) -> RedactionResult {
    SECRET_REDACTOR.lock().unwrap().redact_with_info(text)
}

/// Check for secrets
pub fn contains_secrets(text: &str) -> bool {
    SECRET_REDACTOR.lock().unwrap().contains_secrets(text)
}

/// Get completions
pub fn complete(input: &str, cursor: usize) -> Vec<Completion> {
    COMPLETION_ENGINE.lock().unwrap().complete(input, cursor)
}

/// Add to history
pub fn add_to_history(command: &str) {
    COMPLETION_ENGINE.lock().unwrap().add_history(command);
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_redact_github_token() {
        let redactor = SecretRedactorBridge::new();
        let text = "export TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
        assert!(!result.contains("ghp_"));
    }

    #[test]
    fn test_redact_jwt() {
        let redactor = SecretRedactorBridge::new();
        let text = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
    }

    #[test]
    fn test_no_false_positives() {
        let redactor = SecretRedactorBridge::new();
        let text = "ls -la /home/user";
        let result = redactor.redact(text);
        assert_eq!(result, text);
    }

    #[test]
    fn test_disabled_redactor() {
        let mut redactor = SecretRedactorBridge::new();
        redactor.set_config(RedactorConfig {
            enabled: false,
            ..Default::default()
        });
        let text = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
        let result = redactor.redact(text);
        assert_eq!(result, text);
    }

    #[test]
    fn test_complete_commands() {
        let bridge = CompletionBridge::new();
        let completions = bridge.complete("gi", 2);
        assert!(completions.iter().any(|c| c.text == "git"));
    }

    #[test]
    fn test_complete_subcommands() {
        let bridge = CompletionBridge::new();
        let completions = bridge.complete("git co", 6);
        assert!(completions.iter().any(|c| c.text == "commit" || c.text == "checkout"));
    }

    #[test]
    fn test_complete_flags() {
        let bridge = CompletionBridge::new();
        let completions = bridge.complete("git --", 6);
        assert!(completions.iter().any(|c| c.completion_type == CompletionType::Flag));
    }

    #[test]
    fn test_history() {
        let mut bridge = CompletionBridge::new();
        bridge.add_history("git status");
        bridge.add_history("git commit -m 'test'");

        let suggestions = bridge.history_suggestions("git");
        assert!(!suggestions.is_empty());
    }

    #[test]
    fn test_contains_secrets() {
        let redactor = SecretRedactorBridge::new();
        assert!(redactor.contains_secrets("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"));
        assert!(!redactor.contains_secrets("hello world"));
    }

    #[test]
    fn test_redact_with_info() {
        let redactor = SecretRedactorBridge::new();
        let result = redactor.redact_with_info("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx");
        assert!(result.secrets_found > 0);
        assert!(!result.categories.is_empty());
    }
}
