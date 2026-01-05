// Guaranteed Success Layer for Small Models
//
// The key insight: Small models (1-8B params) CANNOT think, reason, or make decisions.
// But they CAN:
// - Fill in templates
// - Pick from a small list (< 5 options)
// - Execute predefined commands
// - Parse simple patterns
//
// Rule: NEVER ask a small model to decide WHAT to do.
// Instead: Tell it what to do and ask it to confirm or fill in ONE parameter.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A guaranteed-to-work action for small models
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AtomicAction {
    pub id: String,
    pub description: String,
    pub command_template: String,
    pub required_params: Vec<String>,
    pub validation: ValidationRule,
    pub fallback: Option<String>,
}

/// How to validate the command output
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ValidationRule {
    /// Command must exit 0
    ExitZero,
    /// Output must contain this string
    OutputContains(String),
    /// Output must match this regex
    OutputMatches(String),
    /// Output must not be empty
    NonEmpty,
    /// Always succeeds (for side-effect commands)
    Always,
}

/// The prompt that guarantees success
#[derive(Debug, Clone)]
pub struct GuaranteedPrompt {
    /// What the model sees
    pub prompt: String,
    /// Expected response format (model fills in blanks)
    pub expected_format: String,
    /// Default response if model fails to respond correctly
    pub fallback_response: String,
    /// Max tokens to generate (keep small!)
    pub max_tokens: u32,
}

/// The core scaffolding that makes small models work
pub struct GuaranteedSuccess {
    /// Actions the model can take
    actions: HashMap<String, AtomicAction>,
    /// Current context (kept minimal)
    context: Vec<String>,
    /// Max context items (rolling window)
    max_context: usize,
}

impl GuaranteedSuccess {
    pub fn new() -> Self {
        let mut actions = HashMap::new();

        // Define all possible actions upfront
        actions.insert("list_files".to_string(), AtomicAction {
            id: "list_files".to_string(),
            description: "List files in a directory".to_string(),
            command_template: "ls -la {path}".to_string(),
            required_params: vec!["path".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: Some("ls -la .".to_string()),
        });

        actions.insert("read_file".to_string(), AtomicAction {
            id: "read_file".to_string(),
            description: "Read contents of a file".to_string(),
            command_template: "cat {path}".to_string(),
            required_params: vec!["path".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: None,
        });

        actions.insert("find_files".to_string(), AtomicAction {
            id: "find_files".to_string(),
            description: "Find files matching a pattern".to_string(),
            command_template: "find {dir} -name '{pattern}' 2>/dev/null | head -20".to_string(),
            required_params: vec!["dir".to_string(), "pattern".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: Some("find . -name '*.py' 2>/dev/null | head -20".to_string()),
        });

        actions.insert("search_content".to_string(), AtomicAction {
            id: "search_content".to_string(),
            description: "Search for text in files".to_string(),
            command_template: "grep -r '{pattern}' {dir} 2>/dev/null | head -20".to_string(),
            required_params: vec!["pattern".to_string(), "dir".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: None,
        });

        actions.insert("run_command".to_string(), AtomicAction {
            id: "run_command".to_string(),
            description: "Run a shell command".to_string(),
            command_template: "{command}".to_string(),
            required_params: vec!["command".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: None,
        });

        actions.insert("write_file".to_string(), AtomicAction {
            id: "write_file".to_string(),
            description: "Write content to a file".to_string(),
            command_template: "WRITE_FILE".to_string(), // Special handling
            required_params: vec!["path".to_string(), "content".to_string()],
            validation: ValidationRule::Always,
            fallback: None,
        });

        actions.insert("extract_archive".to_string(), AtomicAction {
            id: "extract_archive".to_string(),
            description: "Extract an archive file".to_string(),
            command_template: "unar -o {dest} '{archive}'".to_string(),
            required_params: vec!["archive".to_string(), "dest".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: None,
        });

        actions.insert("install_package".to_string(), AtomicAction {
            id: "install_package".to_string(),
            description: "Install a package".to_string(),
            command_template: "{manager} install {package}".to_string(),
            required_params: vec!["manager".to_string(), "package".to_string()],
            validation: ValidationRule::ExitZero,
            fallback: None,
        });

        actions.insert("done".to_string(), AtomicAction {
            id: "done".to_string(),
            description: "Task is complete".to_string(),
            command_template: "echo 'Task complete'".to_string(),
            required_params: vec![],
            validation: ValidationRule::Always,
            fallback: Some("echo 'Task complete'".to_string()),
        });

        Self {
            actions,
            context: Vec::new(),
            max_context: 5,
        }
    }

    /// Build a prompt that the small model CANNOT fail
    pub fn build_prompt(&self, task: &str, last_output: Option<&str>) -> GuaranteedPrompt {
        // Build action list for the model
        let action_list: Vec<String> = self.actions.values()
            .map(|a| format!("- {}: {}", a.id, a.description))
            .collect();

        // Build minimal context
        let context_str = if self.context.is_empty() {
            "None yet".to_string()
        } else {
            self.context.iter()
                .rev()
                .take(3)
                .collect::<Vec<_>>()
                .into_iter()
                .rev()
                .cloned()
                .collect::<Vec<_>>()
                .join("\n")
        };

        let last_output_str = last_output
            .map(|o| {
                let truncated: String = o.chars().take(500).collect();
                format!("\nLast command output:\n{}", truncated)
            })
            .unwrap_or_default();

        let prompt = format!(r#"TASK: {task}

AVAILABLE ACTIONS:
{actions}

CONTEXT:
{context}
{last_output}

INSTRUCTIONS:
Pick ONE action and fill in the parameters.
If task is complete, pick "done".

Respond with ONLY this format:
ACTION: <action_id>
PARAMS: <param1>=<value1>, <param2>=<value2>

Example:
ACTION: list_files
PARAMS: path=/tmp

Your response:"#,
            task = task,
            actions = action_list.join("\n"),
            context = context_str,
            last_output = last_output_str,
        );

        GuaranteedPrompt {
            prompt,
            expected_format: "ACTION: <id>\nPARAMS: <key>=<value>".to_string(),
            fallback_response: "ACTION: list_files\nPARAMS: path=.".to_string(),
            max_tokens: 50, // Keep it SHORT
        }
    }

    /// Parse the model's response (with aggressive fallbacks)
    pub fn parse_response(&self, response: &str) -> ParsedAction {
        let response = response.trim();

        // Try to extract ACTION line
        let action_id = response.lines()
            .find(|l| l.to_uppercase().starts_with("ACTION:"))
            .and_then(|l| l.split(':').nth(1))
            .map(|s| s.trim().to_lowercase())
            .unwrap_or_else(|| "list_files".to_string());

        // Try to extract PARAMS line
        let params_line = response.lines()
            .find(|l| l.to_uppercase().starts_with("PARAMS:") || l.to_uppercase().starts_with("PARAM:"))
            .and_then(|l| l.split(':').nth(1))
            .unwrap_or("");

        // Parse params
        let mut params = HashMap::new();
        for part in params_line.split(',') {
            let part = part.trim();
            if let Some(eq_pos) = part.find('=') {
                let key = part[..eq_pos].trim().to_string();
                let value = part[eq_pos + 1..].trim().trim_matches('"').trim_matches('\'').to_string();
                if !key.is_empty() && !value.is_empty() {
                    params.insert(key, value);
                }
            }
        }

        // Look up the action
        if let Some(action) = self.actions.get(&action_id) {
            ParsedAction {
                action: action.clone(),
                params,
                raw_response: response.to_string(),
            }
        } else {
            // Fallback to list_files
            ParsedAction {
                action: self.actions.get("list_files").unwrap().clone(),
                params: {
                    let mut m = HashMap::new();
                    m.insert("path".to_string(), ".".to_string());
                    m
                },
                raw_response: response.to_string(),
            }
        }
    }

    /// Build the actual command to execute
    pub fn build_command(&self, parsed: &ParsedAction) -> String {
        let mut command = parsed.action.command_template.clone();

        // Fill in parameters
        for (key, value) in &parsed.params {
            command = command.replace(&format!("{{{}}}", key), value);
        }

        // Check if any placeholders remain
        if command.contains('{') && command.contains('}') {
            // Use fallback if available
            if let Some(fallback) = &parsed.action.fallback {
                return fallback.clone();
            }
        }

        command
    }

    /// Validate command output
    pub fn validate_output(&self, action: &AtomicAction, exit_code: i32, output: &str) -> bool {
        match &action.validation {
            ValidationRule::ExitZero => exit_code == 0,
            ValidationRule::OutputContains(s) => output.contains(s),
            ValidationRule::OutputMatches(pattern) => {
                regex::Regex::new(pattern)
                    .map(|r| r.is_match(output))
                    .unwrap_or(false)
            }
            ValidationRule::NonEmpty => !output.trim().is_empty(),
            ValidationRule::Always => true,
        }
    }

    /// Add to rolling context
    pub fn add_context(&mut self, entry: String) {
        self.context.push(entry);
        while self.context.len() > self.max_context {
            self.context.remove(0);
        }
    }

    /// Check if task appears complete
    pub fn is_complete(&self, action_id: &str) -> bool {
        action_id == "done"
    }

    /// Get action by ID
    pub fn get_action(&self, id: &str) -> Option<&AtomicAction> {
        self.actions.get(id)
    }

    /// Add a custom action
    pub fn add_action(&mut self, action: AtomicAction) {
        self.actions.insert(action.id.clone(), action);
    }
}

/// Result of parsing model response
#[derive(Debug, Clone)]
pub struct ParsedAction {
    pub action: AtomicAction,
    pub params: HashMap<String, String>,
    pub raw_response: String,
}

impl ParsedAction {
    pub fn is_done(&self) -> bool {
        self.action.id == "done"
    }

    pub fn get_param(&self, key: &str) -> Option<&String> {
        self.params.get(key)
    }
}

/// Phase-specific prompts for even more guidance
pub struct PhasePrompts;

impl PhasePrompts {
    /// Get a hyper-specific prompt for a phase
    pub fn for_phase(phase: &str, work_dir: &str, archive: Option<&str>) -> GuaranteedPrompt {
        match phase {
            "Extract" => {
                let archive = archive.unwrap_or("archive.rar");
                GuaranteedPrompt {
                    prompt: format!(
                        "Extract the archive.\n\nRespond with:\nACTION: extract_archive\nPARAMS: archive={}, dest={}",
                        archive, work_dir
                    ),
                    expected_format: "ACTION: extract_archive\nPARAMS: archive=..., dest=...".to_string(),
                    fallback_response: format!("ACTION: extract_archive\nPARAMS: archive={}, dest={}", archive, work_dir),
                    max_tokens: 30,
                }
            }
            "Analyze" => {
                GuaranteedPrompt {
                    prompt: format!(
                        "Find all .dylib and .app files in {}.\n\nRespond with:\nACTION: find_files\nPARAMS: dir={}, pattern=*.dylib",
                        work_dir, work_dir
                    ),
                    expected_format: "ACTION: find_files\nPARAMS: dir=..., pattern=...".to_string(),
                    fallback_response: format!("ACTION: find_files\nPARAMS: dir={}, pattern=*.dylib", work_dir),
                    max_tokens: 30,
                }
            }
            "Complete" => {
                GuaranteedPrompt {
                    prompt: "Task is complete.\n\nRespond with:\nACTION: done\nPARAMS:".to_string(),
                    expected_format: "ACTION: done\nPARAMS:".to_string(),
                    fallback_response: "ACTION: done\nPARAMS:".to_string(),
                    max_tokens: 15,
                }
            }
            _ => {
                // Default exploration prompt
                GuaranteedPrompt {
                    prompt: format!(
                        "List files in {} to see what we have.\n\nRespond with:\nACTION: list_files\nPARAMS: path={}",
                        work_dir, work_dir
                    ),
                    expected_format: "ACTION: list_files\nPARAMS: path=...".to_string(),
                    fallback_response: format!("ACTION: list_files\nPARAMS: path={}", work_dir),
                    max_tokens: 25,
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_response() {
        let gs = GuaranteedSuccess::new();

        // Good response
        let parsed = gs.parse_response("ACTION: list_files\nPARAMS: path=/tmp");
        assert_eq!(parsed.action.id, "list_files");
        assert_eq!(parsed.params.get("path"), Some(&"/tmp".to_string()));

        // Messy response
        let parsed = gs.parse_response("I think we should list the files...\nAction: find_files\nParams: dir=/home, pattern=*.py");
        assert_eq!(parsed.action.id, "find_files");
        assert_eq!(parsed.params.get("dir"), Some(&"/home".to_string()));

        // Garbage response - should fallback
        let parsed = gs.parse_response("I don't understand what you want me to do");
        assert_eq!(parsed.action.id, "list_files");
    }

    #[test]
    fn test_build_command() {
        let gs = GuaranteedSuccess::new();
        let parsed = gs.parse_response("ACTION: find_files\nPARAMS: dir=/tmp, pattern=*.txt");
        let cmd = gs.build_command(&parsed);
        assert_eq!(cmd, "find /tmp -name '*.txt' 2>/dev/null | head -20");
    }
}
