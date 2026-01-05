// Autonomy Controls - Agent behavior and approval settings
//
// Provides fine-grained control over agent autonomy:
// - Approval levels (none, selective, full)
// - Dispatch mode (Ctrl+Shift+I style full autonomy)
// - Tool-specific permissions
// - User authorization policies

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::Mutex;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum AutonomyLevel {
    /// No autonomy - require approval for everything
    None,
    /// Selective - approve destructive operations only
    Selective,
    /// High - approve only high-risk operations
    High,
    /// Full - no approvals required (dispatch mode)
    Full,
}

impl Default for AutonomyLevel {
    fn default() -> Self {
        Self::Selective
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutonomyConfig {
    /// Current autonomy level
    pub level: AutonomyLevel,

    /// Dispatch mode active (temporary full autonomy)
    pub dispatch_mode: bool,

    /// Dispatch mode timeout in seconds (0 = no timeout)
    pub dispatch_timeout_secs: u64,

    /// Dispatch mode start time (for timeout calculation)
    pub dispatch_started: Option<u64>,

    /// Tool-specific overrides
    pub tool_permissions: HashMap<String, ToolPermission>,

    /// Paths that are always protected
    pub protected_paths: HashSet<String>,

    /// Paths that are always allowed
    pub allowed_paths: HashSet<String>,

    /// Maximum files to modify without approval
    pub max_files_without_approval: u32,

    /// Require approval for git operations
    pub approve_git_operations: bool,

    /// Require approval for external commands
    pub approve_external_commands: bool,
}

impl Default for AutonomyConfig {
    fn default() -> Self {
        let mut protected = HashSet::new();
        protected.insert(".git".to_string());
        protected.insert(".env".to_string());
        protected.insert("credentials".to_string());
        protected.insert("secrets".to_string());
        protected.insert("/etc".to_string());
        protected.insert("/usr".to_string());
        protected.insert("/bin".to_string());

        Self {
            level: AutonomyLevel::Selective,
            dispatch_mode: false,
            dispatch_timeout_secs: 300, // 5 minutes
            dispatch_started: None,
            tool_permissions: HashMap::new(),
            protected_paths: protected,
            allowed_paths: HashSet::new(),
            max_files_without_approval: 5,
            approve_git_operations: true,
            approve_external_commands: true,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum ToolPermission {
    /// Always allow this tool
    Allow,
    /// Always require approval
    RequireApproval,
    /// Use default autonomy level
    Default,
    /// Never allow this tool
    Deny,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApprovalRequest {
    pub id: String,
    pub tool: String,
    pub action: String,
    pub details: String,
    pub risk_level: RiskLevel,
    pub timestamp: u64,
    pub auto_approve_after_secs: Option<u64>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, PartialOrd, Ord)]
pub enum RiskLevel {
    Low,
    Medium,
    High,
    Critical,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApprovalResponse {
    pub request_id: String,
    pub approved: bool,
    pub reason: Option<String>,
    pub remember_choice: bool,
}

// =============================================================================
// AUTONOMY CONTROLLER
// =============================================================================

pub struct AutonomyController {
    config: AutonomyConfig,
    pending_approvals: HashMap<String, ApprovalRequest>,
    approval_history: Vec<(ApprovalRequest, ApprovalResponse)>,
    remembered_choices: HashMap<String, bool>, // action_key -> approved
}

impl AutonomyController {
    pub fn new(config: AutonomyConfig) -> Self {
        Self {
            config,
            pending_approvals: HashMap::new(),
            approval_history: Vec::new(),
            remembered_choices: HashMap::new(),
        }
    }

    /// Check if an action requires approval
    pub fn requires_approval(&self, tool: &str, action: &str, paths: &[String]) -> Option<ApprovalRequest> {
        // Dispatch mode overrides everything (except protected paths)
        if self.is_dispatch_mode_active() {
            // Still check protected paths
            if self.involves_protected_path(paths) {
                return Some(self.create_approval_request(
                    tool, action, paths, RiskLevel::Critical,
                    "Protected path access in dispatch mode"
                ));
            }
            return None;
        }

        // Check tool-specific permissions
        if let Some(permission) = self.config.tool_permissions.get(tool) {
            match permission {
                ToolPermission::Allow => return None,
                ToolPermission::Deny => {
                    return Some(self.create_approval_request(
                        tool, action, paths, RiskLevel::Critical,
                        "Tool is denied by policy"
                    ));
                }
                ToolPermission::RequireApproval => {
                    return Some(self.create_approval_request(
                        tool, action, paths, RiskLevel::Medium,
                        "Tool requires approval by policy"
                    ));
                }
                ToolPermission::Default => {} // Fall through to level-based check
            }
        }

        // Check remembered choices
        let action_key = format!("{}:{}", tool, action);
        if let Some(&remembered) = self.remembered_choices.get(&action_key) {
            if remembered {
                return None;
            }
        }

        // Check based on autonomy level
        match self.config.level {
            AutonomyLevel::None => {
                Some(self.create_approval_request(
                    tool, action, paths, RiskLevel::Low,
                    "All actions require approval"
                ))
            }

            AutonomyLevel::Selective => {
                let risk = self.assess_risk(tool, action, paths);
                if risk >= RiskLevel::Medium {
                    Some(self.create_approval_request(tool, action, paths, risk, "Selective approval"))
                } else {
                    None
                }
            }

            AutonomyLevel::High => {
                let risk = self.assess_risk(tool, action, paths);
                if risk >= RiskLevel::High {
                    Some(self.create_approval_request(tool, action, paths, risk, "High-risk approval"))
                } else {
                    None
                }
            }

            AutonomyLevel::Full => {
                // Still protect critical paths
                if self.involves_protected_path(paths) {
                    Some(self.create_approval_request(
                        tool, action, paths, RiskLevel::Critical,
                        "Protected path access"
                    ))
                } else {
                    None
                }
            }
        }
    }

    /// Assess risk level of an action
    fn assess_risk(&self, tool: &str, action: &str, paths: &[String]) -> RiskLevel {
        // Critical: system paths, credentials
        if self.involves_protected_path(paths) {
            return RiskLevel::Critical;
        }

        // High: git push, delete, external commands
        let high_risk_tools = ["git_push", "delete_file", "rm", "execute_shell"];
        let high_risk_actions = ["push", "delete", "remove", "drop", "force"];

        if high_risk_tools.contains(&tool) {
            return RiskLevel::High;
        }

        if high_risk_actions.iter().any(|a| action.to_lowercase().contains(a)) {
            return RiskLevel::High;
        }

        // Medium: file writes, git commits
        let medium_risk_tools = ["write_file", "edit_file", "git_commit", "git_merge"];
        let medium_risk_actions = ["write", "edit", "commit", "merge", "create"];

        if medium_risk_tools.contains(&tool) {
            return RiskLevel::Medium;
        }

        if medium_risk_actions.iter().any(|a| action.to_lowercase().contains(a)) {
            return RiskLevel::Medium;
        }

        // Check file count
        if paths.len() > self.config.max_files_without_approval as usize {
            return RiskLevel::Medium;
        }

        RiskLevel::Low
    }

    fn involves_protected_path(&self, paths: &[String]) -> bool {
        for path in paths {
            for protected in &self.config.protected_paths {
                if path.contains(protected) {
                    return true;
                }
            }
        }
        false
    }

    fn create_approval_request(
        &self,
        tool: &str,
        action: &str,
        paths: &[String],
        risk: RiskLevel,
        reason: &str,
    ) -> ApprovalRequest {
        ApprovalRequest {
            id: uuid::Uuid::new_v4().to_string(),
            tool: tool.to_string(),
            action: action.to_string(),
            details: format!("{}: {:?}", reason, paths),
            risk_level: risk,
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            auto_approve_after_secs: None,
        }
    }

    /// Enter dispatch mode (full autonomy with timeout)
    pub fn enter_dispatch_mode(&mut self) {
        self.config.dispatch_mode = true;
        self.config.dispatch_started = Some(
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs()
        );
    }

    /// Exit dispatch mode
    pub fn exit_dispatch_mode(&mut self) {
        self.config.dispatch_mode = false;
        self.config.dispatch_started = None;
    }

    /// Check if dispatch mode is currently active
    pub fn is_dispatch_mode_active(&self) -> bool {
        if !self.config.dispatch_mode {
            return false;
        }

        // Check timeout
        if self.config.dispatch_timeout_secs > 0 {
            if let Some(started) = self.config.dispatch_started {
                let now = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs();

                if now - started > self.config.dispatch_timeout_secs {
                    return false;
                }
            }
        }

        true
    }

    /// Submit approval for a pending request
    pub fn submit_approval(&mut self, response: ApprovalResponse) -> Result<(), String> {
        let request = self.pending_approvals.remove(&response.request_id)
            .ok_or_else(|| format!("Approval request {} not found", response.request_id))?;

        // Remember choice if requested
        if response.remember_choice {
            let action_key = format!("{}:{}", request.tool, request.action);
            self.remembered_choices.insert(action_key, response.approved);
        }

        self.approval_history.push((request, response));
        Ok(())
    }

    /// Get pending approvals
    pub fn get_pending_approvals(&self) -> Vec<&ApprovalRequest> {
        self.pending_approvals.values().collect()
    }

    /// Set autonomy level
    pub fn set_level(&mut self, level: AutonomyLevel) {
        self.config.level = level;
    }

    /// Get current autonomy level
    pub fn get_level(&self) -> AutonomyLevel {
        if self.is_dispatch_mode_active() {
            AutonomyLevel::Full
        } else {
            self.config.level
        }
    }

    /// Set tool permission
    pub fn set_tool_permission(&mut self, tool: &str, permission: ToolPermission) {
        self.config.tool_permissions.insert(tool.to_string(), permission);
    }

    /// Add protected path
    pub fn add_protected_path(&mut self, path: &str) {
        self.config.protected_paths.insert(path.to_string());
    }

    /// Remove protected path
    pub fn remove_protected_path(&mut self, path: &str) {
        self.config.protected_paths.remove(path);
    }

    /// Get config
    pub fn get_config(&self) -> &AutonomyConfig {
        &self.config
    }

    /// Clear remembered choices
    pub fn clear_remembered_choices(&mut self) {
        self.remembered_choices.clear();
    }

    /// Get stats
    pub fn stats(&self) -> AutonomyStats {
        AutonomyStats {
            level: self.config.level,
            dispatch_active: self.is_dispatch_mode_active(),
            pending_count: self.pending_approvals.len(),
            remembered_count: self.remembered_choices.len(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AutonomyStats {
    pub level: AutonomyLevel,
    pub dispatch_active: bool,
    pub pending_count: usize,
    pub remembered_count: usize,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref AUTONOMY: Mutex<AutonomyController> = Mutex::new(AutonomyController::new(AutonomyConfig::default()));
}

pub fn autonomy() -> std::sync::MutexGuard<'static, AutonomyController> {
    AUTONOMY.lock().unwrap()
}

/// Check if action requires approval
pub fn requires_approval(tool: &str, action: &str, paths: &[String]) -> Option<ApprovalRequest> {
    autonomy().requires_approval(tool, action, paths)
}

/// Enter dispatch mode
pub fn dispatch_mode_on() {
    autonomy().enter_dispatch_mode();
}

/// Exit dispatch mode
pub fn dispatch_mode_off() {
    autonomy().exit_dispatch_mode();
}

/// Check dispatch mode status
pub fn is_dispatch_mode() -> bool {
    autonomy().is_dispatch_mode_active()
}

/// Set autonomy level
pub fn set_level(level: AutonomyLevel) {
    autonomy().set_level(level);
}

/// Get current level
pub fn get_level() -> AutonomyLevel {
    autonomy().get_level()
}

/// Submit approval response
pub fn approve(response: ApprovalResponse) -> Result<(), String> {
    autonomy().submit_approval(response)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = AutonomyConfig::default();
        assert_eq!(config.level, AutonomyLevel::Selective);
        assert!(!config.dispatch_mode);
        assert!(config.protected_paths.contains(".env"));
    }

    #[test]
    fn test_dispatch_mode() {
        let mut controller = AutonomyController::new(AutonomyConfig::default());

        assert!(!controller.is_dispatch_mode_active());

        controller.enter_dispatch_mode();
        assert!(controller.is_dispatch_mode_active());
        assert_eq!(controller.get_level(), AutonomyLevel::Full);

        controller.exit_dispatch_mode();
        assert!(!controller.is_dispatch_mode_active());
    }

    #[test]
    fn test_risk_assessment() {
        let controller = AutonomyController::new(AutonomyConfig::default());

        // High risk
        assert_eq!(
            controller.assess_risk("delete_file", "delete", &["file.txt".to_string()]),
            RiskLevel::High
        );

        // Medium risk
        assert_eq!(
            controller.assess_risk("write_file", "write", &["file.txt".to_string()]),
            RiskLevel::Medium
        );

        // Low risk
        assert_eq!(
            controller.assess_risk("read_file", "read", &["file.txt".to_string()]),
            RiskLevel::Low
        );

        // Critical (protected path)
        assert_eq!(
            controller.assess_risk("read_file", "read", &[".env".to_string()]),
            RiskLevel::Critical
        );
    }

    #[test]
    fn test_requires_approval() {
        let mut controller = AutonomyController::new(AutonomyConfig::default());

        // Selective mode - low risk should not require approval
        let result = controller.requires_approval("read_file", "read", &["test.txt".to_string()]);
        assert!(result.is_none());

        // Selective mode - medium risk should require approval
        let result = controller.requires_approval("write_file", "write", &["test.txt".to_string()]);
        assert!(result.is_some());

        // None mode - everything requires approval
        controller.set_level(AutonomyLevel::None);
        let result = controller.requires_approval("read_file", "read", &["test.txt".to_string()]);
        assert!(result.is_some());
    }

    #[test]
    fn test_tool_permissions() {
        let mut controller = AutonomyController::new(AutonomyConfig::default());

        // Allow specific tool
        controller.set_tool_permission("my_safe_tool", ToolPermission::Allow);
        let result = controller.requires_approval("my_safe_tool", "anything", &[]);
        assert!(result.is_none());

        // Deny specific tool
        controller.set_tool_permission("my_dangerous_tool", ToolPermission::Deny);
        let result = controller.requires_approval("my_dangerous_tool", "anything", &[]);
        assert!(result.is_some());
    }
}
