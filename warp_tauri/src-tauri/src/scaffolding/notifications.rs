//! Desktop Notifications - Alert users about terminal events
//!
//! Provides notifications for:
//! - Long-running command completion
//! - Command failures
//! - Agent task completion/needs review
//! - Password/input prompts
//! - Custom triggers

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use chrono::{DateTime, Utc, Timelike};

// =============================================================================
// NOTIFICATION TYPES
// =============================================================================

/// Types of notifications
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum NotificationType {
    /// Command took longer than threshold
    LongRunningCommand,
    /// Command completed
    CommandComplete,
    /// Command failed
    CommandFailed,
    /// Agent finished task
    AgentComplete,
    /// Agent needs user review/approval
    AgentNeedsReview,
    /// Password or input required
    InputRequired,
    /// SSH connection event
    SshEvent,
    /// Custom user-defined trigger
    Custom,
}

/// Notification priority/urgency
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
pub enum NotificationPriority {
    Low,
    #[default]
    Normal,
    High,
    Critical,
}

/// A notification to display
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Notification {
    /// Unique ID
    pub id: String,
    /// Notification type
    pub notification_type: NotificationType,
    /// Title
    pub title: String,
    /// Body text
    pub body: String,
    /// Priority
    pub priority: NotificationPriority,
    /// When created
    pub created_at: DateTime<Utc>,
    /// Whether notification has been shown
    pub shown: bool,
    /// Whether notification has been dismissed
    pub dismissed: bool,
    /// Associated command (if any)
    pub command: Option<String>,
    /// Exit code (if command related)
    pub exit_code: Option<i32>,
    /// Duration in ms (if timed)
    pub duration_ms: Option<u64>,
    /// Custom actions
    pub actions: Vec<NotificationAction>,
    /// Metadata
    pub metadata: HashMap<String, String>,
}

/// Action button on notification
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationAction {
    pub id: String,
    pub label: String,
    pub action_type: ActionType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ActionType {
    /// Dismiss the notification
    Dismiss,
    /// Focus the terminal window
    Focus,
    /// Run a command
    RunCommand(String),
    /// Open URL
    OpenUrl(String),
    /// Copy to clipboard
    Copy(String),
    /// Custom callback ID
    Custom(String),
}

// =============================================================================
// NOTIFICATION RULES
// =============================================================================

/// Rule for triggering notifications
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationRule {
    /// Rule ID
    pub id: String,
    /// Whether rule is enabled
    pub enabled: bool,
    /// When to trigger
    pub trigger: NotificationTrigger,
    /// Notification settings
    pub settings: NotificationSettings,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum NotificationTrigger {
    /// Command takes longer than N seconds
    LongRunning { threshold_secs: u64 },
    /// Command matches pattern
    CommandPattern { regex: String },
    /// Exit code matches
    ExitCode { codes: Vec<i32> },
    /// Output contains pattern
    OutputPattern { regex: String },
    /// Agent state change
    AgentState { states: Vec<String> },
    /// Always trigger
    Always,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationSettings {
    pub notification_type: NotificationType,
    pub priority: NotificationPriority,
    pub title_template: String,
    pub body_template: String,
    pub sound: Option<String>,
    pub badge: bool,
    pub actions: Vec<NotificationAction>,
}

// =============================================================================
// NOTIFICATION CONFIG
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NotificationConfig {
    /// Whether notifications are enabled
    pub enabled: bool,
    /// Whether to show when app is focused
    pub show_when_focused: bool,
    /// Long-running command threshold (seconds)
    pub long_running_threshold: u64,
    /// Whether to play sounds
    pub sounds_enabled: bool,
    /// Whether to show badge count
    pub badge_enabled: bool,
    /// Do not disturb mode
    pub do_not_disturb: bool,
    /// Quiet hours
    pub quiet_hours: Option<QuietHours>,
    /// Custom rules
    pub rules: Vec<NotificationRule>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuietHours {
    pub start_hour: u8,
    pub end_hour: u8,
}

impl Default for NotificationConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            show_when_focused: false,
            long_running_threshold: 30, // 30 seconds
            sounds_enabled: true,
            badge_enabled: true,
            do_not_disturb: false,
            quiet_hours: None,
            rules: vec![
                // Default rule: notify on long-running commands
                NotificationRule {
                    id: "long_running".to_string(),
                    enabled: true,
                    trigger: NotificationTrigger::LongRunning { threshold_secs: 30 },
                    settings: NotificationSettings {
                        notification_type: NotificationType::LongRunningCommand,
                        priority: NotificationPriority::Normal,
                        title_template: "Command Complete".to_string(),
                        body_template: "{{command}} finished in {{duration}}".to_string(),
                        sound: Some("default".to_string()),
                        badge: true,
                        actions: vec![
                            NotificationAction {
                                id: "focus".to_string(),
                                label: "Show".to_string(),
                                action_type: ActionType::Focus,
                            },
                        ],
                    },
                },
                // Default rule: notify on command failure
                NotificationRule {
                    id: "command_failed".to_string(),
                    enabled: true,
                    trigger: NotificationTrigger::ExitCode { codes: vec![-1] }, // Non-zero (handled specially)
                    settings: NotificationSettings {
                        notification_type: NotificationType::CommandFailed,
                        priority: NotificationPriority::High,
                        title_template: "Command Failed".to_string(),
                        body_template: "{{command}} exited with code {{exit_code}}".to_string(),
                        sound: Some("error".to_string()),
                        badge: true,
                        actions: vec![],
                    },
                },
            ],
        }
    }
}

// =============================================================================
// NOTIFICATION MANAGER
// =============================================================================

/// Tracks running commands for notification purposes
struct TrackedCommand {
    command: String,
    started_at: Instant,
    notified_long_running: bool,
}

pub struct NotificationManager {
    config: NotificationConfig,
    notifications: Vec<Notification>,
    tracked_commands: HashMap<String, TrackedCommand>,
    handlers: Vec<Box<dyn Fn(&Notification) -> bool + Send + Sync>>,
    unread_count: usize,
}

impl NotificationManager {
    pub fn new() -> Self {
        Self::with_config(NotificationConfig::default())
    }

    pub fn with_config(config: NotificationConfig) -> Self {
        Self {
            config,
            notifications: Vec::new(),
            tracked_commands: HashMap::new(),
            handlers: Vec::new(),
            unread_count: 0,
        }
    }

    /// Check if notifications should be shown
    fn should_notify(&self) -> bool {
        if !self.config.enabled || self.config.do_not_disturb {
            return false;
        }

        // Check quiet hours
        if let Some(ref quiet) = self.config.quiet_hours {
            let now = chrono::Local::now();
            let hour = now.hour() as u8;
            if quiet.start_hour <= quiet.end_hour {
                if hour >= quiet.start_hour && hour < quiet.end_hour {
                    return false;
                }
            } else {
                // Wraps midnight
                if hour >= quiet.start_hour || hour < quiet.end_hour {
                    return false;
                }
            }
        }

        true
    }

    /// Track a command starting
    pub fn command_started(&mut self, id: &str, command: &str) {
        self.tracked_commands.insert(id.to_string(), TrackedCommand {
            command: command.to_string(),
            started_at: Instant::now(),
            notified_long_running: false,
        });
    }

    /// Track a command completing
    pub fn command_completed(&mut self, id: &str, exit_code: i32) -> Option<Notification> {
        let tracked = self.tracked_commands.remove(id)?;
        let duration = tracked.started_at.elapsed();
        let duration_ms = duration.as_millis() as u64;

        if !self.should_notify() {
            return None;
        }

        // Check rules
        for rule in &self.config.rules {
            if !rule.enabled {
                continue;
            }

            let matches = match &rule.trigger {
                NotificationTrigger::LongRunning { threshold_secs } => {
                    duration.as_secs() >= *threshold_secs
                }
                NotificationTrigger::ExitCode { codes } => {
                    // Special case: -1 means any non-zero
                    codes.contains(&exit_code) || (codes.contains(&-1) && exit_code != 0)
                }
                NotificationTrigger::CommandPattern { regex } => {
                    regex::Regex::new(regex)
                        .map(|r| r.is_match(&tracked.command))
                        .unwrap_or(false)
                }
                NotificationTrigger::Always => true,
                _ => false,
            };

            if matches {
                let notification = self.create_notification(
                    &rule.settings,
                    &tracked.command,
                    Some(exit_code),
                    Some(duration_ms),
                );
                self.send_notification(notification.clone());
                return Some(notification);
            }
        }

        None
    }

    /// Check tracked commands for long-running threshold
    pub fn check_long_running(&mut self) -> Vec<Notification> {
        if !self.should_notify() {
            return Vec::new();
        }

        let mut notifications = Vec::new();
        let threshold = Duration::from_secs(self.config.long_running_threshold);

        // Collect notifications to send
        let mut to_notify: Vec<(String, Notification)> = Vec::new();

        for (id, tracked) in self.tracked_commands.iter_mut() {
            if !tracked.notified_long_running && tracked.started_at.elapsed() >= threshold {
                tracked.notified_long_running = true;

                let notification = Notification {
                    id: format!("longrun_{}", id),
                    notification_type: NotificationType::LongRunningCommand,
                    title: "Long-Running Command".to_string(),
                    body: format!(
                        "'{}' is still running ({}s)",
                        truncate_command(&tracked.command, 40),
                        tracked.started_at.elapsed().as_secs()
                    ),
                    priority: NotificationPriority::Normal,
                    created_at: Utc::now(),
                    shown: false,
                    dismissed: false,
                    command: Some(tracked.command.clone()),
                    exit_code: None,
                    duration_ms: Some(tracked.started_at.elapsed().as_millis() as u64),
                    actions: vec![
                        NotificationAction {
                            id: "focus".to_string(),
                            label: "Show".to_string(),
                            action_type: ActionType::Focus,
                        },
                    ],
                    metadata: HashMap::new(),
                };

                to_notify.push((id.clone(), notification));
            }
        }

        // Now send notifications (after releasing mutable borrow)
        for (_, notification) in to_notify {
            self.send_notification(notification.clone());
            notifications.push(notification);
        }

        notifications
    }

    /// Notify about agent events
    pub fn agent_event(&mut self, event_type: &str, task_name: &str, details: &str) -> Option<Notification> {
        if !self.should_notify() {
            return None;
        }

        let (notification_type, priority, title) = match event_type {
            "complete" => (
                NotificationType::AgentComplete,
                NotificationPriority::Normal,
                "Agent Task Complete",
            ),
            "needs_review" | "approval_required" => (
                NotificationType::AgentNeedsReview,
                NotificationPriority::High,
                "Agent Needs Review",
            ),
            "error" => (
                NotificationType::CommandFailed,
                NotificationPriority::High,
                "Agent Error",
            ),
            _ => return None,
        };

        let notification = Notification {
            id: format!("agent_{}_{}", event_type, Utc::now().timestamp_millis()),
            notification_type,
            title: title.to_string(),
            body: format!("{}: {}", task_name, details),
            priority,
            created_at: Utc::now(),
            shown: false,
            dismissed: false,
            command: None,
            exit_code: None,
            duration_ms: None,
            actions: vec![
                NotificationAction {
                    id: "focus".to_string(),
                    label: "Review".to_string(),
                    action_type: ActionType::Focus,
                },
            ],
            metadata: HashMap::new(),
        };

        self.send_notification(notification.clone());
        Some(notification)
    }

    /// Send a custom notification
    pub fn notify(&mut self, title: &str, body: &str, priority: NotificationPriority) -> Notification {
        let notification = Notification {
            id: format!("custom_{}", Utc::now().timestamp_millis()),
            notification_type: NotificationType::Custom,
            title: title.to_string(),
            body: body.to_string(),
            priority,
            created_at: Utc::now(),
            shown: false,
            dismissed: false,
            command: None,
            exit_code: None,
            duration_ms: None,
            actions: vec![],
            metadata: HashMap::new(),
        };

        self.send_notification(notification.clone());
        notification
    }

    /// Get all notifications
    pub fn get_all(&self) -> &[Notification] {
        &self.notifications
    }

    /// Get unread count
    pub fn unread_count(&self) -> usize {
        self.unread_count
    }

    /// Mark notification as read
    pub fn mark_read(&mut self, id: &str) -> bool {
        if let Some(n) = self.notifications.iter_mut().find(|n| n.id == id) {
            if !n.dismissed {
                n.dismissed = true;
                if self.unread_count > 0 {
                    self.unread_count -= 1;
                }
                return true;
            }
        }
        false
    }

    /// Mark all as read
    pub fn mark_all_read(&mut self) {
        for n in &mut self.notifications {
            n.dismissed = true;
        }
        self.unread_count = 0;
    }

    /// Clear all notifications
    pub fn clear_all(&mut self) {
        self.notifications.clear();
        self.unread_count = 0;
    }

    /// Add notification handler
    pub fn on_notification<F>(&mut self, handler: F)
    where
        F: Fn(&Notification) -> bool + Send + Sync + 'static,
    {
        self.handlers.push(Box::new(handler));
    }

    /// Update config
    pub fn update_config(&mut self, config: NotificationConfig) {
        self.config = config;
    }

    /// Get config
    pub fn config(&self) -> &NotificationConfig {
        &self.config
    }

    // Private helpers

    fn create_notification(
        &self,
        settings: &NotificationSettings,
        command: &str,
        exit_code: Option<i32>,
        duration_ms: Option<u64>,
    ) -> Notification {
        // Template substitution
        let title = settings.title_template
            .replace("{{command}}", &truncate_command(command, 30))
            .replace("{{exit_code}}", &exit_code.map(|c| c.to_string()).unwrap_or_default())
            .replace("{{duration}}", &format_duration(duration_ms));

        let body = settings.body_template
            .replace("{{command}}", &truncate_command(command, 60))
            .replace("{{exit_code}}", &exit_code.map(|c| c.to_string()).unwrap_or_default())
            .replace("{{duration}}", &format_duration(duration_ms));

        Notification {
            id: format!("{}_{}", settings.notification_type as u8, Utc::now().timestamp_millis()),
            notification_type: settings.notification_type,
            title,
            body,
            priority: settings.priority,
            created_at: Utc::now(),
            shown: false,
            dismissed: false,
            command: Some(command.to_string()),
            exit_code,
            duration_ms,
            actions: settings.actions.clone(),
            metadata: HashMap::new(),
        }
    }

    fn send_notification(&mut self, mut notification: Notification) {
        // Call handlers
        for handler in &self.handlers {
            if handler(&notification) {
                notification.shown = true;
            }
        }

        // Send to OS notification system
        #[cfg(target_os = "macos")]
        self.send_macos_notification(&notification);

        #[cfg(target_os = "linux")]
        self.send_linux_notification(&notification);

        self.unread_count += 1;
        self.notifications.push(notification);

        // Limit history
        if self.notifications.len() > 100 {
            self.notifications.remove(0);
        }
    }

    #[cfg(target_os = "macos")]
    fn send_macos_notification(&self, notification: &Notification) {
        // Use osascript for native notifications
        let script = format!(
            r#"display notification "{}" with title "{}""#,
            notification.body.replace('"', r#"\""#),
            notification.title.replace('"', r#"\""#)
        );

        let _ = std::process::Command::new("osascript")
            .args(["-e", &script])
            .spawn();
    }

    #[cfg(target_os = "linux")]
    fn send_linux_notification(&self, notification: &Notification) {
        // Use notify-send
        let urgency = match notification.priority {
            NotificationPriority::Low => "low",
            NotificationPriority::Normal => "normal",
            NotificationPriority::High | NotificationPriority::Critical => "critical",
        };

        let _ = std::process::Command::new("notify-send")
            .args([
                "-u", urgency,
                &notification.title,
                &notification.body,
            ])
            .spawn();
    }
}

impl Default for NotificationManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn truncate_command(cmd: &str, max_len: usize) -> String {
    if cmd.len() <= max_len {
        cmd.to_string()
    } else {
        format!("{}...", &cmd[..max_len.saturating_sub(3)])
    }
}

fn format_duration(ms: Option<u64>) -> String {
    match ms {
        Some(ms) if ms < 1000 => format!("{}ms", ms),
        Some(ms) if ms < 60_000 => format!("{:.1}s", ms as f64 / 1000.0),
        Some(ms) if ms < 3_600_000 => format!("{}m {}s", ms / 60_000, (ms % 60_000) / 1000),
        Some(ms) => format!("{}h {}m", ms / 3_600_000, (ms % 3_600_000) / 60_000),
        None => "unknown".to_string(),
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref NOTIFICATION_MANAGER: Arc<Mutex<NotificationManager>> =
        Arc::new(Mutex::new(NotificationManager::new()));
}

/// Get the global notification manager
pub fn notifications() -> Arc<Mutex<NotificationManager>> {
    NOTIFICATION_MANAGER.clone()
}

/// Track command start
pub fn command_started(id: &str, command: &str) {
    NOTIFICATION_MANAGER.lock().unwrap().command_started(id, command);
}

/// Track command completion
pub fn command_completed(id: &str, exit_code: i32) -> Option<Notification> {
    NOTIFICATION_MANAGER.lock().unwrap().command_completed(id, exit_code)
}

/// Check for long-running commands
pub fn check_long_running() -> Vec<Notification> {
    NOTIFICATION_MANAGER.lock().unwrap().check_long_running()
}

/// Send agent event notification
pub fn agent_event(event_type: &str, task_name: &str, details: &str) -> Option<Notification> {
    NOTIFICATION_MANAGER.lock().unwrap().agent_event(event_type, task_name, details)
}

/// Send custom notification
pub fn notify(title: &str, body: &str, priority: NotificationPriority) -> Notification {
    NOTIFICATION_MANAGER.lock().unwrap().notify(title, body, priority)
}

/// Get unread count
pub fn unread_count() -> usize {
    NOTIFICATION_MANAGER.lock().unwrap().unread_count()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_notification_manager_new() {
        let manager = NotificationManager::new();
        assert!(manager.config.enabled);
        assert_eq!(manager.unread_count, 0);
    }

    #[test]
    fn test_command_tracking() {
        let mut manager = NotificationManager::new();

        manager.command_started("cmd1", "sleep 1");
        assert!(manager.tracked_commands.contains_key("cmd1"));

        manager.command_completed("cmd1", 0);
        assert!(!manager.tracked_commands.contains_key("cmd1"));
    }

    #[test]
    fn test_custom_notification() {
        let mut manager = NotificationManager::new();

        let notification = manager.notify(
            "Test Title",
            "Test Body",
            NotificationPriority::Normal,
        );

        assert_eq!(notification.title, "Test Title");
        assert_eq!(notification.body, "Test Body");
        assert_eq!(manager.unread_count(), 1);
    }

    #[test]
    fn test_mark_read() {
        let mut manager = NotificationManager::new();

        let notification = manager.notify("Test", "Body", NotificationPriority::Normal);
        assert_eq!(manager.unread_count(), 1);

        manager.mark_read(&notification.id);
        assert_eq!(manager.unread_count(), 0);
    }

    #[test]
    fn test_format_duration() {
        assert_eq!(format_duration(Some(500)), "500ms");
        assert_eq!(format_duration(Some(1500)), "1.5s");
        assert_eq!(format_duration(Some(65000)), "1m 5s");
        assert_eq!(format_duration(Some(3700000)), "1h 1m");
    }

    #[test]
    fn test_truncate_command() {
        assert_eq!(truncate_command("short", 10), "short");
        assert_eq!(truncate_command("this is a very long command", 15), "this is a ve...");
    }

    #[test]
    fn test_do_not_disturb() {
        let mut manager = NotificationManager::new();
        manager.config.do_not_disturb = true;

        manager.command_started("cmd1", "test");
        let result = manager.command_completed("cmd1", 0);

        assert!(result.is_none()); // No notification in DND mode
    }

    #[test]
    fn test_agent_event() {
        let mut manager = NotificationManager::new();

        let notification = manager.agent_event(
            "complete",
            "Build Task",
            "Successfully built project",
        );

        assert!(notification.is_some());
        let n = notification.unwrap();
        assert_eq!(n.notification_type, NotificationType::AgentComplete);
    }

    #[test]
    fn test_notification_limit() {
        let mut manager = NotificationManager::new();

        // Add 105 notifications
        for i in 0..105 {
            manager.notify(&format!("Test {}", i), "Body", NotificationPriority::Normal);
        }

        // Should be capped at 100
        assert!(manager.notifications.len() <= 100);
    }
}
