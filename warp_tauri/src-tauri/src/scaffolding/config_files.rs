// Config Files - Project configuration and agent instructions
//
// Supports multiple config file formats:
// - .sam.md / SAM.md - SAM-specific instructions
// - CLAUDE.md - Claude Code compatible instructions
// - .cursorrules - Cursor IDE rules
// - WARP.md - Warp terminal agent instructions
// - .ai-instructions - Generic AI instructions

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::Mutex;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectConfig {
    /// Project root directory
    pub root: PathBuf,

    /// Merged instructions from all config files
    pub instructions: String,

    /// Individual config files found
    pub config_files: Vec<ConfigFile>,

    /// Parsed rules and settings
    pub rules: ProjectRules,

    /// Custom environment variables
    pub env: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConfigFile {
    pub path: PathBuf,
    pub format: ConfigFormat,
    pub content: String,
    pub priority: u32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum ConfigFormat {
    SamMd,        // .sam.md, SAM.md
    ClaudeMd,     // CLAUDE.md, .claude.md
    CursorRules,  // .cursorrules
    WarpMd,       // WARP.md, .warp.md
    AiInstructions, // .ai-instructions
    Generic,      // Other markdown/text files
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProjectRules {
    /// Files/patterns to always include in context
    pub always_include: Vec<String>,

    /// Files/patterns to never include
    pub never_include: Vec<String>,

    /// Preferred coding style
    pub coding_style: Option<CodingStyle>,

    /// Custom commands/aliases
    pub commands: HashMap<String, String>,

    /// Agent behavior settings
    pub agent_settings: AgentSettings,

    /// Technology stack hints
    pub tech_stack: Vec<String>,

    /// Testing requirements
    pub testing: TestingRules,
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CodingStyle {
    pub language: Option<String>,
    pub indent: Option<String>,
    pub max_line_length: Option<u32>,
    pub prefer_const: Option<bool>,
    pub use_semicolons: Option<bool>,
    pub quote_style: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentSettings {
    /// Autonomy level: "full", "selective", "approval_required"
    pub autonomy: String,

    /// Whether to auto-commit changes
    pub auto_commit: bool,

    /// Whether to run tests before committing
    pub test_before_commit: bool,

    /// Max files to edit in one transaction
    pub max_files_per_edit: u32,

    /// Preferred model for this project
    pub preferred_model: Option<String>,
}

impl Default for AgentSettings {
    fn default() -> Self {
        Self {
            autonomy: "selective".to_string(),
            auto_commit: false,
            test_before_commit: true,
            max_files_per_edit: 10,
            preferred_model: None,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct TestingRules {
    /// Test command to run
    pub test_command: Option<String>,

    /// Required test coverage percentage
    pub min_coverage: Option<u32>,

    /// Test file patterns
    pub test_patterns: Vec<String>,
}

// =============================================================================
// CONFIG FILE PARSER
// =============================================================================

pub struct ConfigParser;

impl ConfigParser {
    /// Discover and load all config files from a directory
    pub fn load_project_config(root: &Path) -> Result<ProjectConfig, String> {
        let config_files = Self::discover_config_files(root)?;

        let mut merged_instructions = String::new();
        let mut rules = ProjectRules::default();
        let mut env = HashMap::new();

        // Process files in priority order (lower priority first, higher overwrites)
        let mut sorted_files = config_files.clone();
        sorted_files.sort_by_key(|f| f.priority);

        for file in &sorted_files {
            // Append instructions
            if !merged_instructions.is_empty() {
                merged_instructions.push_str("\n\n---\n\n");
            }
            merged_instructions.push_str(&format!("# From {}\n\n", file.path.display()));
            merged_instructions.push_str(&file.content);

            // Parse rules from content
            Self::parse_rules_from_content(&file.content, &mut rules);
            Self::parse_env_from_content(&file.content, &mut env);
        }

        Ok(ProjectConfig {
            root: root.to_path_buf(),
            instructions: merged_instructions,
            config_files,
            rules,
            env,
        })
    }

    /// Discover config files in directory
    fn discover_config_files(root: &Path) -> Result<Vec<ConfigFile>, String> {
        let mut files = Vec::new();

        // Config file patterns with priorities (higher = more specific)
        let patterns = [
            (".sam.md", ConfigFormat::SamMd, 100),
            ("SAM.md", ConfigFormat::SamMd, 100),
            ("CLAUDE.md", ConfigFormat::ClaudeMd, 90),
            (".claude.md", ConfigFormat::ClaudeMd, 90),
            (".cursorrules", ConfigFormat::CursorRules, 80),
            ("WARP.md", ConfigFormat::WarpMd, 70),
            (".warp.md", ConfigFormat::WarpMd, 70),
            (".ai-instructions", ConfigFormat::AiInstructions, 60),
            ("AI_INSTRUCTIONS.md", ConfigFormat::AiInstructions, 60),
            ("AGENTS.md", ConfigFormat::Generic, 50),
            ("CONTRIBUTING.md", ConfigFormat::Generic, 30),
        ];

        for (filename, format, priority) in patterns {
            let path = root.join(filename);
            if path.exists() {
                if let Ok(content) = std::fs::read_to_string(&path) {
                    files.push(ConfigFile {
                        path,
                        format,
                        content,
                        priority,
                    });
                }
            }
        }

        // Also check .claude/ directory for additional files
        let claude_dir = root.join(".claude");
        if claude_dir.exists() && claude_dir.is_dir() {
            if let Ok(entries) = std::fs::read_dir(&claude_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if path.extension().map(|e| e == "md").unwrap_or(false) {
                        if let Ok(content) = std::fs::read_to_string(&path) {
                            files.push(ConfigFile {
                                path,
                                format: ConfigFormat::ClaudeMd,
                                content,
                                priority: 85,
                            });
                        }
                    }
                }
            }
        }

        Ok(files)
    }

    /// Parse rules from markdown content
    fn parse_rules_from_content(content: &str, rules: &mut ProjectRules) {
        // Parse always/never include patterns
        if let Some(section) = extract_section(content, "Always Include") {
            for line in section.lines() {
                let trimmed = line.trim().trim_start_matches('-').trim();
                if !trimmed.is_empty() && !trimmed.starts_with('#') {
                    rules.always_include.push(trimmed.to_string());
                }
            }
        }

        if let Some(section) = extract_section(content, "Never Include") {
            for line in section.lines() {
                let trimmed = line.trim().trim_start_matches('-').trim();
                if !trimmed.is_empty() && !trimmed.starts_with('#') {
                    rules.never_include.push(trimmed.to_string());
                }
            }
        }

        // Parse tech stack
        if let Some(section) = extract_section(content, "Tech Stack") {
            for line in section.lines() {
                let trimmed = line.trim().trim_start_matches('-').trim();
                if !trimmed.is_empty() && !trimmed.starts_with('#') {
                    rules.tech_stack.push(trimmed.to_string());
                }
            }
        }

        // Parse commands
        if let Some(section) = extract_section(content, "Commands") {
            for line in section.lines() {
                if let Some((name, cmd)) = line.split_once(':') {
                    let name = name.trim().trim_start_matches('-').trim();
                    let cmd = cmd.trim().trim_matches('`');
                    if !name.is_empty() && !cmd.is_empty() {
                        rules.commands.insert(name.to_string(), cmd.to_string());
                    }
                }
            }
        }

        // Parse testing rules
        if let Some(section) = extract_section(content, "Testing") {
            for line in section.lines() {
                let lower = line.to_lowercase();
                if lower.contains("test command") || lower.contains("run tests") {
                    if let Some(cmd) = extract_code_block(line) {
                        rules.testing.test_command = Some(cmd);
                    }
                }
                if lower.contains("coverage") {
                    if let Some(pct) = extract_number(line) {
                        rules.testing.min_coverage = Some(pct);
                    }
                }
            }
        }

        // Parse agent settings
        if let Some(section) = extract_section(content, "Agent Settings") {
            for line in section.lines() {
                let lower = line.to_lowercase();
                if lower.contains("autonomy") {
                    if lower.contains("full") {
                        rules.agent_settings.autonomy = "full".to_string();
                    } else if lower.contains("none") || lower.contains("approval") {
                        rules.agent_settings.autonomy = "approval_required".to_string();
                    }
                }
                if lower.contains("auto-commit") || lower.contains("auto commit") {
                    rules.agent_settings.auto_commit = lower.contains("yes") || lower.contains("true");
                }
            }
        }
    }

    /// Parse environment variables from content
    fn parse_env_from_content(content: &str, env: &mut HashMap<String, String>) {
        if let Some(section) = extract_section(content, "Environment") {
            for line in section.lines() {
                if let Some((key, value)) = line.split_once('=') {
                    let key = key.trim().trim_start_matches('-').trim();
                    let value = value.trim().trim_matches('"').trim_matches('\'');
                    if !key.is_empty() {
                        env.insert(key.to_string(), value.to_string());
                    }
                }
            }
        }
    }

    /// Create a default config file
    pub fn create_default_config(root: &Path, format: ConfigFormat) -> Result<PathBuf, String> {
        let (filename, content) = match format {
            ConfigFormat::SamMd => ("SAM.md", DEFAULT_SAM_MD),
            ConfigFormat::ClaudeMd => ("CLAUDE.md", DEFAULT_CLAUDE_MD),
            ConfigFormat::CursorRules => (".cursorrules", DEFAULT_CURSORRULES),
            ConfigFormat::WarpMd => ("WARP.md", DEFAULT_WARP_MD),
            _ => return Err("Unsupported format for default config".to_string()),
        };

        let path = root.join(filename);
        std::fs::write(&path, content)
            .map_err(|e| format!("Failed to write {}: {}", filename, e))?;

        Ok(path)
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn extract_section(content: &str, header: &str) -> Option<String> {
    let header_patterns = [
        format!("# {}", header),
        format!("## {}", header),
        format!("### {}", header),
    ];

    for pattern in &header_patterns {
        if let Some(start) = content.find(pattern) {
            let section_start = start + pattern.len();
            let section_content = &content[section_start..];

            // Find next header
            let end = section_content.find("\n#")
                .unwrap_or(section_content.len());

            return Some(section_content[..end].trim().to_string());
        }
    }

    None
}

fn extract_code_block(line: &str) -> Option<String> {
    if let Some(start) = line.find('`') {
        if let Some(end) = line[start + 1..].find('`') {
            return Some(line[start + 1..start + 1 + end].to_string());
        }
    }
    None
}

fn extract_number(line: &str) -> Option<u32> {
    let re = regex::Regex::new(r"\d+").ok()?;
    re.find(line)
        .and_then(|m| m.as_str().parse().ok())
}

// =============================================================================
// DEFAULT TEMPLATES
// =============================================================================

const DEFAULT_SAM_MD: &str = r#"# SAM Project Configuration

## Tech Stack
- Rust
- TypeScript
- Vue 3

## Agent Settings
- Autonomy: selective
- Auto-commit: no
- Test before commit: yes

## Always Include
- src/main.rs
- package.json
- Cargo.toml

## Never Include
- node_modules/
- target/
- .git/

## Commands
- build: `cargo build`
- test: `cargo test`
- dev: `npm run tauri:dev`

## Testing
- Test command: `cargo test`
- Coverage: 80%
"#;

const DEFAULT_CLAUDE_MD: &str = r#"# CLAUDE.md

This file provides context to Claude Code about this project.

## Project Overview
Describe your project here.

## Tech Stack
- List your technologies

## Important Files
- Key files to always consider

## Coding Style
- Prefer const over let
- Use TypeScript strict mode
- Write tests for new features

## Commands
- build: `npm run build`
- test: `npm test`
"#;

const DEFAULT_CURSORRULES: &str = r#"# Cursor Rules

## Code Style
- Use 2 space indentation
- Prefer arrow functions
- Use async/await over promises

## Project Context
This project uses...

## Testing
Always write tests for new features.
"#;

const DEFAULT_WARP_MD: &str = r#"# WARP.md

Agent instructions for Warp terminal.

## Workflows
Define common workflows here.

## Commands
- deploy: Deploy to production
- sync: Sync with remote

## Agent Behavior
- Ask before destructive operations
- Run tests before commits
"#;

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref PROJECT_CONFIGS: Mutex<HashMap<PathBuf, ProjectConfig>> = Mutex::new(HashMap::new());
}

/// Load project config (cached)
pub fn load_config(root: &Path) -> Result<ProjectConfig, String> {
    let mut cache = PROJECT_CONFIGS.lock().unwrap();

    if let Some(config) = cache.get(root) {
        return Ok(config.clone());
    }

    let config = ConfigParser::load_project_config(root)?;
    cache.insert(root.to_path_buf(), config.clone());
    Ok(config)
}

/// Reload project config (invalidate cache)
pub fn reload_config(root: &Path) -> Result<ProjectConfig, String> {
    let mut cache = PROJECT_CONFIGS.lock().unwrap();
    cache.remove(root);
    drop(cache);
    load_config(root)
}

/// Get merged instructions for a project
pub fn get_instructions(root: &Path) -> Result<String, String> {
    load_config(root).map(|c| c.instructions)
}

/// Get project rules
pub fn get_rules(root: &Path) -> Result<ProjectRules, String> {
    load_config(root).map(|c| c.rules)
}

/// Create default config file
pub fn create_config(root: &Path, format: ConfigFormat) -> Result<PathBuf, String> {
    ConfigParser::create_default_config(root, format)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_section() {
        let content = r#"
# Header

Some text

## Tech Stack
- Rust
- TypeScript

## Other
More stuff
"#;

        let section = extract_section(content, "Tech Stack");
        assert!(section.is_some());
        let s = section.unwrap();
        assert!(s.contains("Rust"));
        assert!(s.contains("TypeScript"));
        assert!(!s.contains("More stuff"));
    }

    #[test]
    fn test_extract_code_block() {
        assert_eq!(extract_code_block("Run `cargo test` to test"), Some("cargo test".to_string()));
        assert_eq!(extract_code_block("No code here"), None);
    }

    #[test]
    fn test_extract_number() {
        assert_eq!(extract_number("Coverage: 80%"), Some(80));
        assert_eq!(extract_number("No number"), None);
    }

    #[test]
    fn test_default_templates() {
        assert!(DEFAULT_SAM_MD.contains("Tech Stack"));
        assert!(DEFAULT_CLAUDE_MD.contains("CLAUDE.md"));
        assert!(DEFAULT_CURSORRULES.contains("Cursor Rules"));
    }
}
