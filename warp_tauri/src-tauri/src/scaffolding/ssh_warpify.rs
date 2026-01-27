//! SSH Warpify - IDE features for SSH sessions
//!
//! Provides enhanced SSH experience:
//! - Automatic Warpify detection
//! - Remote tmux integration
//! - Feature parity with local terminal
//! - Session persistence

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// TYPES
// =============================================================================

/// An SSH session that can be Warpified
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SshSession {
    /// Session ID
    pub id: String,
    /// Remote host
    pub host: String,
    /// Remote user
    pub user: Option<String>,
    /// Remote port
    pub port: u16,
    /// Connection state
    pub state: SshState,
    /// Whether session is Warpified
    pub warpified: bool,
    /// Warpify capabilities available
    pub capabilities: WarpifyCapabilities,
    /// Remote shell type
    pub shell: Option<String>,
    /// Remote OS
    pub remote_os: Option<String>,
    /// Connection time
    pub connected_at: DateTime<Utc>,
    /// Last activity
    pub last_activity: DateTime<Utc>,
    /// Associated pane ID
    pub pane_id: Option<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum SshState {
    Connecting,
    Connected,
    Warpifying,
    Warpified,
    Disconnected,
    Error,
}

/// Capabilities available when Warpified
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WarpifyCapabilities {
    /// Can use blocks (requires tmux)
    pub blocks: bool,
    /// Can use command palette
    pub command_palette: bool,
    /// Can use history search
    pub history_search: bool,
    /// Can use completion
    pub completion: bool,
    /// Can use AI features
    pub ai_features: bool,
    /// Remote has tmux installed
    pub has_tmux: bool,
    /// Remote shell is compatible
    pub shell_compatible: bool,
}

/// SSH configuration for Warpify
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WarpifyConfig {
    /// Auto-Warpify on connect
    pub auto_warpify: bool,
    /// Install tmux if missing
    pub install_tmux: bool,
    /// Forward agent
    pub forward_agent: bool,
    /// Sync shell config
    pub sync_shell_config: bool,
    /// Prompt pattern to detect successful login
    pub login_patterns: Vec<String>,
}

impl Default for WarpifyConfig {
    fn default() -> Self {
        Self {
            auto_warpify: true,
            install_tmux: false,
            forward_agent: true,
            sync_shell_config: false,
            login_patterns: vec![
                "Last login:".to_string(),
                "Welcome to".to_string(),
                "\\$".to_string(),
                "#".to_string(),
            ],
        }
    }
}

// =============================================================================
// SSH WARPIFY MANAGER
// =============================================================================

pub struct SshWarpifyManager {
    sessions: HashMap<String, SshSession>,
    config: WarpifyConfig,
    event_handlers: Vec<Box<dyn Fn(&SshSession, SshEvent) + Send + Sync>>,
}

#[derive(Debug, Clone)]
pub enum SshEvent {
    Connected,
    Warpified,
    Disconnected,
    Error(String),
    OutputReceived(String),
}

impl SshWarpifyManager {
    pub fn new() -> Self {
        Self::with_config(WarpifyConfig::default())
    }

    pub fn with_config(config: WarpifyConfig) -> Self {
        Self {
            sessions: HashMap::new(),
            config,
            event_handlers: Vec::new(),
        }
    }

    /// Register a new SSH connection
    pub fn register_session(&mut self, host: &str, user: Option<&str>, port: u16) -> SshSession {
        let id = format!("ssh_{}", uuid::Uuid::new_v4().to_string()[..8].to_string());
        let now = Utc::now();

        let session = SshSession {
            id: id.clone(),
            host: host.to_string(),
            user: user.map(String::from),
            port,
            state: SshState::Connecting,
            warpified: false,
            capabilities: WarpifyCapabilities::default(),
            shell: None,
            remote_os: None,
            connected_at: now,
            last_activity: now,
            pane_id: None,
        };

        self.sessions.insert(id, session.clone());
        session
    }

    /// Mark session as connected
    pub fn mark_connected(&mut self, id: &str) -> bool {
        let (session_clone, should_warpify) = if let Some(session) = self.sessions.get_mut(id) {
            session.state = SshState::Connected;
            session.last_activity = Utc::now();
            (Some(session.clone()), self.config.auto_warpify)
        } else {
            return false;
        };

        // Emit event outside the mutable borrow
        if let Some(sc) = session_clone {
            self.emit_event(&sc, SshEvent::Connected);
        }

        // Auto-warpify if enabled
        if should_warpify {
            self.start_warpify(id);
        }

        self.sessions.contains_key(id)
    }

    /// Process output to detect login success
    pub fn process_output(&mut self, id: &str, output: &str) -> bool {
        let should_warpify = if let Some(session) = self.sessions.get_mut(id) {
            session.last_activity = Utc::now();

            // Check for login patterns
            let logged_in = self.config.login_patterns.iter()
                .any(|p| output.contains(p) || regex::Regex::new(p).map(|r| r.is_match(output)).unwrap_or(false));

            if logged_in && session.state == SshState::Connecting {
                session.state = SshState::Connected;
                self.config.auto_warpify
            } else {
                false
            }
        } else {
            false
        };

        if should_warpify {
            self.start_warpify(id);
        }

        should_warpify
    }

    /// Start Warpify process
    pub fn start_warpify(&mut self, id: &str) -> bool {
        // First check if session exists and is in Connected state
        {
            let session = match self.sessions.get_mut(id) {
                Some(s) if s.state == SshState::Connected => s,
                _ => return false,
            };
            session.state = SshState::Warpifying;
        }

        // Detect remote environment (outside the mutable borrow)
        let has_tmux = self.check_remote_tmux(id);
        let shell = self.detect_remote_shell(id);
        let os = self.detect_remote_os(id);

        // Update session with detected info
        let session_clone = if let Some(session) = self.sessions.get_mut(id) {
            session.shell = Some(shell.clone());
            session.remote_os = Some(os.clone());

            session.capabilities = WarpifyCapabilities {
                blocks: has_tmux,
                command_palette: true,
                history_search: true,
                completion: true,
                ai_features: true,
                has_tmux,
                shell_compatible: matches!(shell.as_str(), "bash" | "zsh" | "fish"),
            };

            session.state = SshState::Warpified;
            session.warpified = true;

            Some(session.clone())
        } else {
            None
        };

        if let Some(sc) = session_clone {
            self.emit_event(&sc, SshEvent::Warpified);
            true
        } else {
            false
        }
    }

    /// Manually trigger Warpify
    pub fn warpify(&mut self, id: &str) -> bool {
        self.start_warpify(id)
    }

    /// Disconnect session
    pub fn disconnect(&mut self, id: &str) -> bool {
        let session_clone = if let Some(session) = self.sessions.get_mut(id) {
            session.state = SshState::Disconnected;
            session.warpified = false;
            Some(session.clone())
        } else {
            return false;
        };

        if let Some(sc) = session_clone {
            self.emit_event(&sc, SshEvent::Disconnected);
        }
        true
    }

    /// Remove session
    pub fn remove_session(&mut self, id: &str) -> Option<SshSession> {
        self.sessions.remove(id)
    }

    /// Get session
    pub fn get(&self, id: &str) -> Option<&SshSession> {
        self.sessions.get(id)
    }

    /// Get all sessions
    pub fn all(&self) -> Vec<&SshSession> {
        self.sessions.values().collect()
    }

    /// Get active (connected/warpified) sessions
    pub fn active(&self) -> Vec<&SshSession> {
        self.sessions.values()
            .filter(|s| matches!(s.state, SshState::Connected | SshState::Warpified))
            .collect()
    }

    /// Update config
    pub fn set_config(&mut self, config: WarpifyConfig) {
        self.config = config;
    }

    /// Get config
    pub fn config(&self) -> &WarpifyConfig {
        &self.config
    }

    /// Register event handler
    pub fn on_event<F>(&mut self, handler: F)
    where
        F: Fn(&SshSession, SshEvent) + Send + Sync + 'static,
    {
        self.event_handlers.push(Box::new(handler));
    }

    // Private helpers

    fn check_remote_tmux(&self, _id: &str) -> bool {
        // Would execute: which tmux || command -v tmux
        // Placeholder - assume tmux is available
        true
    }

    fn detect_remote_shell(&self, _id: &str) -> String {
        // Would execute: echo $SHELL
        // Placeholder
        "bash".to_string()
    }

    fn detect_remote_os(&self, _id: &str) -> String {
        // Would execute: uname -s
        // Placeholder
        "Linux".to_string()
    }

    fn emit_event(&self, session: &SshSession, event: SshEvent) {
        for handler in &self.event_handlers {
            handler(session, event.clone());
        }
    }
}

impl Default for SshWarpifyManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// SUBSHELL DETECTION
// =============================================================================

/// Detects subshells and containers that can be Warpified
pub struct SubshellDetector {
    patterns: Vec<SubshellPattern>,
}

#[derive(Clone)]
struct SubshellPattern {
    name: String,
    command_pattern: regex::Regex,
    prompt_pattern: regex::Regex,
}

impl SubshellDetector {
    pub fn new() -> Self {
        let patterns = vec![
            // Docker
            ("Docker", r"docker\s+(?:exec|run)", r"root@[a-f0-9]+"),
            // Kubernetes
            ("K8s Pod", r"kubectl\s+exec", r"[\w-]+@[\w-]+"),
            // SSH within SSH
            ("Nested SSH", r"ssh\s+\S+", r"Last login:|Welcome to"),
            // sudo/su
            ("Elevated", r"(?:sudo\s+-[is]|su\s+-)", r"root@|#\s*$"),
            // nix-shell
            ("Nix Shell", r"nix-shell", r"\[nix-shell:"),
            // virtualenv
            ("Virtualenv", r"(?:source|\.)\s+\S+/activate", r"\([^)]+\)\s*\$"),
        ];

        let compiled: Vec<_> = patterns.into_iter()
            .filter_map(|(name, cmd, prompt)| {
                Some(SubshellPattern {
                    name: name.to_string(),
                    command_pattern: regex::Regex::new(cmd).ok()?,
                    prompt_pattern: regex::Regex::new(prompt).ok()?,
                })
            })
            .collect();

        Self { patterns: compiled }
    }

    /// Detect if command would enter a subshell
    pub fn detect_subshell_command(&self, command: &str) -> Option<String> {
        for pattern in &self.patterns {
            if pattern.command_pattern.is_match(command) {
                return Some(pattern.name.clone());
            }
        }
        None
    }

    /// Detect subshell from prompt/output
    pub fn detect_from_output(&self, output: &str) -> Option<String> {
        for pattern in &self.patterns {
            if pattern.prompt_pattern.is_match(output) {
                return Some(pattern.name.clone());
            }
        }
        None
    }
}

impl Default for SubshellDetector {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref SSH_MANAGER: Arc<Mutex<SshWarpifyManager>> =
        Arc::new(Mutex::new(SshWarpifyManager::new()));

    static ref SUBSHELL_DETECTOR: SubshellDetector = SubshellDetector::new();
}

/// Get the global SSH manager
pub fn ssh_manager() -> Arc<Mutex<SshWarpifyManager>> {
    SSH_MANAGER.clone()
}

/// Register SSH session
pub fn register_ssh(host: &str, user: Option<&str>, port: u16) -> SshSession {
    SSH_MANAGER.lock().unwrap().register_session(host, user, port)
}

/// Warpify a session
pub fn warpify(session_id: &str) -> bool {
    SSH_MANAGER.lock().unwrap().warpify(session_id)
}

/// Detect subshell in command
pub fn detect_subshell(command: &str) -> Option<String> {
    SUBSHELL_DETECTOR.detect_subshell_command(command)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_session() {
        let mut manager = SshWarpifyManager::new();
        let session = manager.register_session("example.com", Some("user"), 22);

        assert_eq!(session.host, "example.com");
        assert_eq!(session.port, 22);
        assert_eq!(session.state, SshState::Connecting);
    }

    #[test]
    fn test_mark_connected() {
        let mut manager = SshWarpifyManager::new();
        manager.config.auto_warpify = false; // Disable for this test

        let session = manager.register_session("example.com", None, 22);
        manager.mark_connected(&session.id);

        let s = manager.get(&session.id).unwrap();
        assert_eq!(s.state, SshState::Connected);
    }

    #[test]
    fn test_warpify() {
        let mut manager = SshWarpifyManager::new();
        manager.config.auto_warpify = false;

        let session = manager.register_session("example.com", None, 22);
        manager.mark_connected(&session.id);
        manager.warpify(&session.id);

        let s = manager.get(&session.id).unwrap();
        assert_eq!(s.state, SshState::Warpified);
        assert!(s.warpified);
        assert!(s.capabilities.command_palette);
    }

    #[test]
    fn test_disconnect() {
        let mut manager = SshWarpifyManager::new();
        let session = manager.register_session("example.com", None, 22);
        manager.disconnect(&session.id);

        let s = manager.get(&session.id).unwrap();
        assert_eq!(s.state, SshState::Disconnected);
    }

    #[test]
    fn test_active_sessions() {
        let mut manager = SshWarpifyManager::new();
        manager.config.auto_warpify = false;

        let s1 = manager.register_session("host1.com", None, 22);
        let s2 = manager.register_session("host2.com", None, 22);

        manager.mark_connected(&s1.id);

        let active = manager.active();
        assert_eq!(active.len(), 1);
        assert_eq!(active[0].host, "host1.com");
    }

    #[test]
    fn test_subshell_detection() {
        let detector = SubshellDetector::new();

        assert_eq!(detector.detect_subshell_command("docker exec -it container bash"), Some("Docker".to_string()));
        assert_eq!(detector.detect_subshell_command("kubectl exec -it pod -- sh"), Some("K8s Pod".to_string()));
        assert_eq!(detector.detect_subshell_command("ssh user@host"), Some("Nested SSH".to_string()));
        assert_eq!(detector.detect_subshell_command("ls -la"), None);
    }

    #[test]
    fn test_process_output_login() {
        let mut manager = SshWarpifyManager::new();
        manager.config.auto_warpify = false;

        let session = manager.register_session("example.com", None, 22);

        // Simulate receiving login output
        let detected = manager.process_output(&session.id, "Last login: Fri Jan 22 12:00:00 2026");

        // State should change to connected
        let s = manager.get(&session.id).unwrap();
        assert_eq!(s.state, SshState::Connected);
    }
}
