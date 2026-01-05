// Hooks System - Pre/Post Tool Execution Callbacks
//
// Allows users to register hooks that run before and after tool execution.
// Similar to Claude Code's hooks system for extensibility.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HookTrigger {
    /// Before any tool execution
    PreTool,
    /// After any tool execution
    PostTool,
    /// Before specific tool
    PreToolNamed(String),
    /// After specific tool
    PostToolNamed(String),
    /// Before message processing
    PreMessage,
    /// After message processing
    PostMessage,
    /// On error
    OnError,
    /// On session start
    SessionStart,
    /// On session end
    SessionEnd,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HookAction {
    /// Run a shell command
    Shell(String),
    /// Log to file
    LogToFile(String),
    /// Send notification (macOS)
    Notify(String),
    /// Execute JavaScript (for frontend hooks)
    JavaScript(String),
    /// Block execution with message
    Block(String),
    /// Modify tool args
    ModifyArgs(HashMap<String, String>),
    /// Custom Rust function (by name)
    Custom(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Hook {
    pub id: String,
    pub name: String,
    pub description: String,
    pub trigger: HookTrigger,
    pub action: HookAction,
    pub enabled: bool,
    pub priority: i32,  // Lower = runs first
    pub conditions: Option<HookConditions>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookConditions {
    /// Only run for these tools
    pub tools: Option<Vec<String>>,
    /// Only run in these directories
    pub directories: Option<Vec<String>>,
    /// Only run for files matching pattern
    pub file_patterns: Option<Vec<String>>,
    /// Custom condition expression
    pub expression: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookContext {
    pub tool_name: Option<String>,
    pub tool_args: Option<HashMap<String, serde_json::Value>>,
    pub working_directory: String,
    pub session_id: String,
    pub message: Option<String>,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum HookResult {
    /// Continue with execution
    Continue,
    /// Continue with modified args
    ContinueWithArgs(HashMap<String, serde_json::Value>),
    /// Block execution
    Block(String),
    /// Skip this hook (condition not met)
    Skip,
}

// =============================================================================
// HOOK MANAGER
// =============================================================================

pub struct HookManager {
    hooks: Vec<Hook>,
    custom_handlers: HashMap<String, Box<dyn Fn(&HookContext) -> HookResult + Send + Sync>>,
}

impl HookManager {
    pub fn new() -> Self {
        Self {
            hooks: Vec::new(),
            custom_handlers: HashMap::new(),
        }
    }

    /// Register a hook
    pub fn register(&mut self, hook: Hook) -> String {
        let id = hook.id.clone();
        self.hooks.push(hook);
        self.hooks.sort_by_key(|h| h.priority);
        id
    }

    /// Unregister a hook
    pub fn unregister(&mut self, id: &str) -> bool {
        let len_before = self.hooks.len();
        self.hooks.retain(|h| h.id != id);
        self.hooks.len() < len_before
    }

    /// Enable/disable a hook
    pub fn set_enabled(&mut self, id: &str, enabled: bool) -> bool {
        if let Some(hook) = self.hooks.iter_mut().find(|h| h.id == id) {
            hook.enabled = enabled;
            true
        } else {
            false
        }
    }

    /// Register a custom handler function
    pub fn register_custom_handler<F>(&mut self, name: &str, handler: F)
    where
        F: Fn(&HookContext) -> HookResult + Send + Sync + 'static,
    {
        self.custom_handlers.insert(name.to_string(), Box::new(handler));
    }

    /// Run all hooks for a trigger
    pub fn run_hooks(&self, trigger: &HookTrigger, ctx: &HookContext) -> HookResult {
        let mut final_args = ctx.tool_args.clone();

        for hook in &self.hooks {
            if !hook.enabled {
                continue;
            }

            if !self.trigger_matches(&hook.trigger, trigger) {
                continue;
            }

            if !self.conditions_met(&hook.conditions, ctx) {
                continue;
            }

            let result = self.execute_hook(hook, ctx);

            match result {
                HookResult::Continue => continue,
                HookResult::ContinueWithArgs(args) => {
                    final_args = Some(args);
                }
                HookResult::Block(msg) => return HookResult::Block(msg),
                HookResult::Skip => continue,
            }
        }

        if let Some(args) = final_args {
            if ctx.tool_args.as_ref() != Some(&args) {
                return HookResult::ContinueWithArgs(args);
            }
        }

        HookResult::Continue
    }

    fn trigger_matches(&self, hook_trigger: &HookTrigger, event_trigger: &HookTrigger) -> bool {
        match (hook_trigger, event_trigger) {
            (HookTrigger::PreTool, HookTrigger::PreTool) => true,
            (HookTrigger::PreTool, HookTrigger::PreToolNamed(_)) => true,
            (HookTrigger::PostTool, HookTrigger::PostTool) => true,
            (HookTrigger::PostTool, HookTrigger::PostToolNamed(_)) => true,
            (HookTrigger::PreToolNamed(a), HookTrigger::PreToolNamed(b)) => a == b,
            (HookTrigger::PostToolNamed(a), HookTrigger::PostToolNamed(b)) => a == b,
            (HookTrigger::PreMessage, HookTrigger::PreMessage) => true,
            (HookTrigger::PostMessage, HookTrigger::PostMessage) => true,
            (HookTrigger::OnError, HookTrigger::OnError) => true,
            (HookTrigger::SessionStart, HookTrigger::SessionStart) => true,
            (HookTrigger::SessionEnd, HookTrigger::SessionEnd) => true,
            _ => false,
        }
    }

    fn conditions_met(&self, conditions: &Option<HookConditions>, ctx: &HookContext) -> bool {
        let conditions = match conditions {
            Some(c) => c,
            None => return true,
        };

        // Check tool filter
        if let Some(tools) = &conditions.tools {
            if let Some(tool_name) = &ctx.tool_name {
                if !tools.contains(tool_name) {
                    return false;
                }
            }
        }

        // Check directory filter
        if let Some(dirs) = &conditions.directories {
            if !dirs.iter().any(|d| ctx.working_directory.starts_with(d)) {
                return false;
            }
        }

        // Check file pattern filter
        if let Some(patterns) = &conditions.file_patterns {
            if let Some(args) = &ctx.tool_args {
                if let Some(path) = args.get("path").and_then(|v| v.as_str()) {
                    let matches = patterns.iter().any(|p| {
                        glob::Pattern::new(p)
                            .map(|pat| pat.matches(path))
                            .unwrap_or(false)
                    });
                    if !matches {
                        return false;
                    }
                }
            }
        }

        true
    }

    fn execute_hook(&self, hook: &Hook, ctx: &HookContext) -> HookResult {
        match &hook.action {
            HookAction::Shell(cmd) => {
                let expanded = self.expand_variables(cmd, ctx);
                match std::process::Command::new("sh")
                    .arg("-c")
                    .arg(&expanded)
                    .output()
                {
                    Ok(output) => {
                        if output.status.success() {
                            HookResult::Continue
                        } else {
                            let stderr = String::from_utf8_lossy(&output.stderr);
                            eprintln!("[HOOK {}] Shell command failed: {}", hook.id, stderr);
                            HookResult::Continue // Don't block on hook failure
                        }
                    }
                    Err(e) => {
                        eprintln!("[HOOK {}] Failed to run shell command: {}", hook.id, e);
                        HookResult::Continue
                    }
                }
            }

            HookAction::LogToFile(path) => {
                let expanded = self.expand_variables(path, ctx);
                let log_entry = format!(
                    "[{}] Hook: {} | Tool: {:?} | Dir: {}\n",
                    chrono::Utc::now().format("%Y-%m-%d %H:%M:%S"),
                    hook.name,
                    ctx.tool_name,
                    ctx.working_directory
                );
                if let Err(e) = std::fs::OpenOptions::new()
                    .create(true)
                    .append(true)
                    .open(&expanded)
                    .and_then(|mut f| std::io::Write::write_all(&mut f, log_entry.as_bytes()))
                {
                    eprintln!("[HOOK {}] Failed to log: {}", hook.id, e);
                }
                HookResult::Continue
            }

            HookAction::Notify(message) => {
                let expanded = self.expand_variables(message, ctx);
                #[cfg(target_os = "macos")]
                {
                    let _ = std::process::Command::new("osascript")
                        .arg("-e")
                        .arg(format!("display notification \"{}\" with title \"SAM Hook\"", expanded))
                        .output();
                }
                HookResult::Continue
            }

            HookAction::JavaScript(_js) => {
                // Would need to be handled by frontend via Tauri events
                HookResult::Continue
            }

            HookAction::Block(message) => {
                let expanded = self.expand_variables(message, ctx);
                HookResult::Block(expanded)
            }

            HookAction::ModifyArgs(modifications) => {
                let mut args = ctx.tool_args.clone().unwrap_or_default();
                for (key, value) in modifications {
                    let expanded = self.expand_variables(value, ctx);
                    args.insert(key.clone(), serde_json::Value::String(expanded));
                }
                HookResult::ContinueWithArgs(args)
            }

            HookAction::Custom(name) => {
                if let Some(handler) = self.custom_handlers.get(name) {
                    handler(ctx)
                } else {
                    eprintln!("[HOOK {}] Custom handler '{}' not found", hook.id, name);
                    HookResult::Continue
                }
            }
        }
    }

    fn expand_variables(&self, template: &str, ctx: &HookContext) -> String {
        let mut result = template.to_string();

        result = result.replace("${tool}", ctx.tool_name.as_deref().unwrap_or(""));
        result = result.replace("${cwd}", &ctx.working_directory);
        result = result.replace("${session}", &ctx.session_id);
        result = result.replace("${message}", ctx.message.as_deref().unwrap_or(""));
        result = result.replace("${error}", ctx.error.as_deref().unwrap_or(""));

        if let Some(args) = &ctx.tool_args {
            if let Some(path) = args.get("path").and_then(|v| v.as_str()) {
                result = result.replace("${path}", path);
            }
            if let Some(content) = args.get("content").and_then(|v| v.as_str()) {
                result = result.replace("${content}", content);
            }
        }

        result
    }

    /// List all hooks
    pub fn list(&self) -> &[Hook] {
        &self.hooks
    }

    /// Get a hook by ID
    pub fn get(&self, id: &str) -> Option<&Hook> {
        self.hooks.iter().find(|h| h.id == id)
    }

    /// Load hooks from config file
    pub fn load_from_file(&mut self, path: &str) -> Result<(), String> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| format!("Failed to read hooks file: {}", e))?;

        let hooks: Vec<Hook> = serde_json::from_str(&content)
            .map_err(|e| format!("Failed to parse hooks: {}", e))?;

        for hook in hooks {
            self.register(hook);
        }

        Ok(())
    }

    /// Save hooks to config file
    pub fn save_to_file(&self, path: &str) -> Result<(), String> {
        let content = serde_json::to_string_pretty(&self.hooks)
            .map_err(|e| format!("Failed to serialize hooks: {}", e))?;

        std::fs::write(path, content)
            .map_err(|e| format!("Failed to write hooks file: {}", e))?;

        Ok(())
    }
}

impl Default for HookManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL HOOK MANAGER
// =============================================================================

lazy_static::lazy_static! {
    pub static ref HOOK_MANAGER: Mutex<HookManager> = Mutex::new(HookManager::new());
}

pub fn hooks() -> std::sync::MutexGuard<'static, HookManager> {
    HOOK_MANAGER.lock().unwrap()
}

/// Register a hook
pub fn register_hook(hook: Hook) -> String {
    hooks().register(hook)
}

/// Unregister a hook
pub fn unregister_hook(id: &str) -> bool {
    hooks().unregister(id)
}

/// Run hooks for a trigger
pub fn run_hooks(trigger: &HookTrigger, ctx: &HookContext) -> HookResult {
    hooks().run_hooks(trigger, ctx)
}

// =============================================================================
// BUILT-IN HOOKS
// =============================================================================

/// Create common built-in hooks
pub fn create_builtin_hooks() -> Vec<Hook> {
    vec![
        // Log all tool executions
        Hook {
            id: "builtin_log_tools".to_string(),
            name: "Log Tool Executions".to_string(),
            description: "Log all tool executions to ~/.sam/hooks.log".to_string(),
            trigger: HookTrigger::PostTool,
            action: HookAction::LogToFile("~/.sam/hooks.log".to_string()),
            enabled: false,
            priority: 100,
            conditions: None,
        },

        // Notify on errors
        Hook {
            id: "builtin_error_notify".to_string(),
            name: "Error Notification".to_string(),
            description: "Show macOS notification on errors".to_string(),
            trigger: HookTrigger::OnError,
            action: HookAction::Notify("SAM Error: ${error}".to_string()),
            enabled: false,
            priority: 100,
            conditions: None,
        },

        // Block dangerous commands
        Hook {
            id: "builtin_block_dangerous".to_string(),
            name: "Block Dangerous Commands".to_string(),
            description: "Block rm -rf and similar dangerous commands".to_string(),
            trigger: HookTrigger::PreToolNamed("execute_shell".to_string()),
            action: HookAction::Custom("check_dangerous_command".to_string()),
            enabled: true,
            priority: 1,
            conditions: None,
        },

        // Auto-backup before edits
        Hook {
            id: "builtin_backup_edits".to_string(),
            name: "Backup Before Edit".to_string(),
            description: "Create backup before editing files".to_string(),
            trigger: HookTrigger::PreToolNamed("edit_file".to_string()),
            action: HookAction::Shell("cp \"${path}\" \"${path}.bak\" 2>/dev/null || true".to_string()),
            enabled: false,
            priority: 10,
            conditions: None,
        },
    ]
}

/// Initialize built-in hooks and custom handlers
pub fn init_hooks() {
    let mut mgr = hooks();

    // Register dangerous command checker
    mgr.register_custom_handler("check_dangerous_command", |ctx| {
        if let Some(args) = &ctx.tool_args {
            if let Some(cmd) = args.get("command").and_then(|v| v.as_str()) {
                let dangerous_patterns = [
                    "rm -rf /",
                    "rm -rf ~",
                    "rm -rf /*",
                    "> /dev/sda",
                    "mkfs.",
                    "dd if=/dev/zero",
                    ":(){:|:&};:",  // Fork bomb
                ];

                for pattern in dangerous_patterns {
                    if cmd.contains(pattern) {
                        return HookResult::Block(format!(
                            "Blocked dangerous command pattern: {}",
                            pattern
                        ));
                    }
                }
            }
        }
        HookResult::Continue
    });

    // Register built-in hooks
    for hook in create_builtin_hooks() {
        mgr.register(hook);
    }

    // Try to load user hooks
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    let hooks_file = format!("{}/.sam/hooks.json", home);
    if std::path::Path::new(&hooks_file).exists() {
        if let Err(e) = mgr.load_from_file(&hooks_file) {
            eprintln!("[HOOKS] Failed to load user hooks: {}", e);
        }
    }
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_hook_registration() {
        let mut mgr = HookManager::new();

        let hook = Hook {
            id: "test_hook".to_string(),
            name: "Test Hook".to_string(),
            description: "A test hook".to_string(),
            trigger: HookTrigger::PreTool,
            action: HookAction::Shell("echo test".to_string()),
            enabled: true,
            priority: 10,
            conditions: None,
        };

        mgr.register(hook);
        assert_eq!(mgr.list().len(), 1);
        assert!(mgr.get("test_hook").is_some());
    }

    #[test]
    fn test_hook_unregister() {
        let mut mgr = HookManager::new();

        let hook = Hook {
            id: "test_hook".to_string(),
            name: "Test".to_string(),
            description: "".to_string(),
            trigger: HookTrigger::PreTool,
            action: HookAction::Shell("echo".to_string()),
            enabled: true,
            priority: 10,
            conditions: None,
        };

        mgr.register(hook);
        assert!(mgr.unregister("test_hook"));
        assert!(mgr.list().is_empty());
    }

    #[test]
    fn test_hook_conditions() {
        let mgr = HookManager::new();

        let conditions = HookConditions {
            tools: Some(vec!["read_file".to_string()]),
            directories: None,
            file_patterns: None,
            expression: None,
        };

        let ctx_match = HookContext {
            tool_name: Some("read_file".to_string()),
            tool_args: None,
            working_directory: "/tmp".to_string(),
            session_id: "test".to_string(),
            message: None,
            error: None,
        };

        let ctx_no_match = HookContext {
            tool_name: Some("write_file".to_string()),
            tool_args: None,
            working_directory: "/tmp".to_string(),
            session_id: "test".to_string(),
            message: None,
            error: None,
        };

        assert!(mgr.conditions_met(&Some(conditions.clone()), &ctx_match));
        assert!(!mgr.conditions_met(&Some(conditions), &ctx_no_match));
    }

    #[test]
    fn test_variable_expansion() {
        let mgr = HookManager::new();

        let ctx = HookContext {
            tool_name: Some("read_file".to_string()),
            tool_args: Some(HashMap::from([
                ("path".to_string(), serde_json::Value::String("/test/file.txt".to_string())),
            ])),
            working_directory: "/home/user".to_string(),
            session_id: "session_123".to_string(),
            message: Some("test message".to_string()),
            error: None,
        };

        let template = "Tool: ${tool}, Path: ${path}, CWD: ${cwd}";
        let expanded = mgr.expand_variables(template, &ctx);

        assert!(expanded.contains("read_file"));
        assert!(expanded.contains("/test/file.txt"));
        assert!(expanded.contains("/home/user"));
    }

    #[test]
    fn test_block_action() {
        let mut mgr = HookManager::new();

        let hook = Hook {
            id: "blocker".to_string(),
            name: "Blocker".to_string(),
            description: "".to_string(),
            trigger: HookTrigger::PreTool,
            action: HookAction::Block("Blocked!".to_string()),
            enabled: true,
            priority: 1,
            conditions: None,
        };

        mgr.register(hook);

        let ctx = HookContext {
            tool_name: Some("test".to_string()),
            tool_args: None,
            working_directory: ".".to_string(),
            session_id: "test".to_string(),
            message: None,
            error: None,
        };

        let result = mgr.run_hooks(&HookTrigger::PreTool, &ctx);
        assert!(matches!(result, HookResult::Block(_)));
    }
}
