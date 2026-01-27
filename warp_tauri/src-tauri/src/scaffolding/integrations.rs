//! Third-party Integrations - Slack, Linear, and other services
//!
//! Provides first-party integrations with external services for:
//! - Sharing terminal output to Slack channels
//! - Creating Linear issues from errors/tasks
//! - Receiving commands from integrations
//! - Syncing workflows with external tools

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// INTEGRATION TYPES
// =============================================================================

/// Available integration types
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum IntegrationType {
    Slack,
    Linear,
    GitHub,
    Jira,
    Discord,
    Teams,
    Notion,
    Custom,
}

/// Base integration configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrationConfig {
    /// Integration type
    pub integration_type: IntegrationType,
    /// Whether integration is enabled
    pub enabled: bool,
    /// Display name
    pub name: String,
    /// OAuth token or API key
    pub auth_token: Option<String>,
    /// Webhook URL (for incoming)
    pub webhook_url: Option<String>,
    /// Additional configuration
    pub settings: HashMap<String, serde_json::Value>,
}

/// Event from an integration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrationEvent {
    /// Source integration
    pub source: IntegrationType,
    /// Event type
    pub event_type: String,
    /// Event payload
    pub payload: serde_json::Value,
    /// When event was received
    pub received_at: DateTime<Utc>,
    /// Raw event ID (for deduplication)
    pub event_id: Option<String>,
}

/// Result of an integration action
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IntegrationResult {
    pub success: bool,
    pub message: Option<String>,
    pub data: Option<serde_json::Value>,
    pub error: Option<String>,
}

// =============================================================================
// INTEGRATION TRAIT
// =============================================================================

pub trait Integration: Send + Sync {
    /// Integration type
    fn integration_type(&self) -> IntegrationType;

    /// Whether integration is connected/authenticated
    fn is_connected(&self) -> bool;

    /// Connect/authenticate
    fn connect(&mut self, config: &IntegrationConfig) -> Result<(), IntegrationError>;

    /// Disconnect
    fn disconnect(&mut self);

    /// Send a message
    fn send_message(&self, channel: &str, message: &str) -> Result<IntegrationResult, IntegrationError>;

    /// Send a block/snippet
    fn send_block(&self, channel: &str, title: &str, content: &str, language: Option<&str>) -> Result<IntegrationResult, IntegrationError>;

    /// Create a task/issue
    fn create_task(&self, title: &str, description: &str, labels: &[&str]) -> Result<IntegrationResult, IntegrationError>;

    /// Handle incoming event
    fn handle_event(&self, event: &IntegrationEvent) -> Result<IntegrationResult, IntegrationError>;
}

// =============================================================================
// SLACK INTEGRATION
// =============================================================================

#[derive(Debug, Clone)]
pub struct SlackIntegration {
    config: Option<IntegrationConfig>,
    connected: bool,
    /// Default channel for messages
    default_channel: String,
    /// Bot user ID
    bot_user_id: Option<String>,
    /// Team ID
    team_id: Option<String>,
}

impl SlackIntegration {
    pub fn new() -> Self {
        Self {
            config: None,
            connected: false,
            default_channel: "#general".to_string(),
            bot_user_id: None,
            team_id: None,
        }
    }

    /// Set default channel
    pub fn with_default_channel(mut self, channel: &str) -> Self {
        self.default_channel = channel.to_string();
        self
    }

    /// Send a threaded reply
    pub fn send_thread_reply(
        &self,
        channel: &str,
        thread_ts: &str,
        message: &str,
    ) -> Result<IntegrationResult, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let _token = self.config.as_ref()
            .and_then(|c| c.auth_token.as_ref())
            .ok_or(IntegrationError::MissingAuth)?;

        // In production, would use reqwest to call Slack API
        // POST https://slack.com/api/chat.postMessage
        let _payload = serde_json::json!({
            "channel": channel,
            "thread_ts": thread_ts,
            "text": message,
        });

        // Placeholder - actual implementation would make HTTP request
        Ok(IntegrationResult {
            success: true,
            message: Some(format!("Reply sent to thread {} in {}", thread_ts, channel)),
            data: Some(serde_json::json!({ "thread_ts": thread_ts })),
            error: None,
        })
    }

    /// Upload a file/snippet
    pub fn upload_file(
        &self,
        channels: &[&str],
        content: &str,
        filename: &str,
        filetype: Option<&str>,
    ) -> Result<IntegrationResult, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let _token = self.config.as_ref()
            .and_then(|c| c.auth_token.as_ref())
            .ok_or(IntegrationError::MissingAuth)?;

        // POST https://slack.com/api/files.upload
        let _payload = serde_json::json!({
            "channels": channels.join(","),
            "content": content,
            "filename": filename,
            "filetype": filetype.unwrap_or("text"),
        });

        Ok(IntegrationResult {
            success: true,
            message: Some(format!("File {} uploaded to {}", filename, channels.join(", "))),
            data: None,
            error: None,
        })
    }

    /// Get channel list
    pub fn list_channels(&self) -> Result<Vec<SlackChannel>, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        // GET https://slack.com/api/conversations.list
        // Placeholder
        Ok(vec![
            SlackChannel {
                id: "C12345".to_string(),
                name: "general".to_string(),
                is_private: false,
            },
            SlackChannel {
                id: "C67890".to_string(),
                name: "random".to_string(),
                is_private: false,
            },
        ])
    }

    /// Parse slash command
    pub fn parse_slash_command(payload: &serde_json::Value) -> Option<SlackSlashCommand> {
        Some(SlackSlashCommand {
            command: payload.get("command")?.as_str()?.to_string(),
            text: payload.get("text")?.as_str()?.to_string(),
            user_id: payload.get("user_id")?.as_str()?.to_string(),
            channel_id: payload.get("channel_id")?.as_str()?.to_string(),
            response_url: payload.get("response_url")?.as_str()?.to_string(),
        })
    }
}

impl Default for SlackIntegration {
    fn default() -> Self {
        Self::new()
    }
}

impl Integration for SlackIntegration {
    fn integration_type(&self) -> IntegrationType {
        IntegrationType::Slack
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    fn connect(&mut self, config: &IntegrationConfig) -> Result<(), IntegrationError> {
        if config.auth_token.is_none() {
            return Err(IntegrationError::MissingAuth);
        }

        // Verify token with auth.test
        // In production, would call Slack API
        self.config = Some(config.clone());
        self.connected = true;
        self.bot_user_id = Some("U12345678".to_string()); // Would come from API

        if let Some(channel) = config.settings.get("default_channel") {
            if let Some(ch) = channel.as_str() {
                self.default_channel = ch.to_string();
            }
        }

        Ok(())
    }

    fn disconnect(&mut self) {
        self.connected = false;
        self.config = None;
        self.bot_user_id = None;
        self.team_id = None;
    }

    fn send_message(&self, channel: &str, message: &str) -> Result<IntegrationResult, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let channel = if channel.is_empty() { &self.default_channel } else { channel };

        let _token = self.config.as_ref()
            .and_then(|c| c.auth_token.as_ref())
            .ok_or(IntegrationError::MissingAuth)?;

        // POST https://slack.com/api/chat.postMessage
        let _payload = serde_json::json!({
            "channel": channel,
            "text": message,
        });

        // Placeholder response
        Ok(IntegrationResult {
            success: true,
            message: Some(format!("Message sent to {}", channel)),
            data: Some(serde_json::json!({
                "channel": channel,
                "ts": format!("{}.123456", Utc::now().timestamp()),
            })),
            error: None,
        })
    }

    fn send_block(&self, channel: &str, title: &str, content: &str, _language: Option<&str>) -> Result<IntegrationResult, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let channel = if channel.is_empty() { &self.default_channel } else { channel };

        // Use Slack blocks for rich formatting
        let _blocks = serde_json::json!([
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": title,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": format!("```{}```", content),
                }
            }
        ]);

        Ok(IntegrationResult {
            success: true,
            message: Some(format!("Block '{}' sent to {}", title, channel)),
            data: None,
            error: None,
        })
    }

    fn create_task(&self, _title: &str, _description: &str, _labels: &[&str]) -> Result<IntegrationResult, IntegrationError> {
        // Slack doesn't have native task creation
        // Could integrate with Slack workflows or forward to Linear
        Err(IntegrationError::NotSupported("Slack doesn't support task creation".to_string()))
    }

    fn handle_event(&self, event: &IntegrationEvent) -> Result<IntegrationResult, IntegrationError> {
        match event.event_type.as_str() {
            "message" => {
                // Handle incoming message
                let text = event.payload.get("text")
                    .and_then(|t| t.as_str())
                    .unwrap_or("");

                // Check for mentions of bot
                if let Some(ref bot_id) = self.bot_user_id {
                    if text.contains(&format!("<@{}>", bot_id)) {
                        // Bot was mentioned - could trigger response
                        return Ok(IntegrationResult {
                            success: true,
                            message: Some("Bot mentioned".to_string()),
                            data: Some(event.payload.clone()),
                            error: None,
                        });
                    }
                }

                Ok(IntegrationResult {
                    success: true,
                    message: None,
                    data: None,
                    error: None,
                })
            }
            "app_mention" => {
                Ok(IntegrationResult {
                    success: true,
                    message: Some("App mentioned".to_string()),
                    data: Some(event.payload.clone()),
                    error: None,
                })
            }
            "slash_command" => {
                if let Some(cmd) = Self::parse_slash_command(&event.payload) {
                    Ok(IntegrationResult {
                        success: true,
                        message: Some(format!("Command: {} {}", cmd.command, cmd.text)),
                        data: Some(serde_json::to_value(&cmd).unwrap()),
                        error: None,
                    })
                } else {
                    Err(IntegrationError::ParseError("Invalid slash command".to_string()))
                }
            }
            _ => Ok(IntegrationResult {
                success: true,
                message: Some(format!("Unhandled event: {}", event.event_type)),
                data: None,
                error: None,
            }),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlackChannel {
    pub id: String,
    pub name: String,
    pub is_private: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SlackSlashCommand {
    pub command: String,
    pub text: String,
    pub user_id: String,
    pub channel_id: String,
    pub response_url: String,
}

// =============================================================================
// LINEAR INTEGRATION
// =============================================================================

#[derive(Debug, Clone)]
pub struct LinearIntegration {
    config: Option<IntegrationConfig>,
    connected: bool,
    /// Default team ID
    default_team_id: Option<String>,
    /// Default project ID
    default_project_id: Option<String>,
    /// Workspace info
    workspace: Option<LinearWorkspace>,
}

impl LinearIntegration {
    pub fn new() -> Self {
        Self {
            config: None,
            connected: false,
            default_team_id: None,
            default_project_id: None,
            workspace: None,
        }
    }

    /// Set default team
    pub fn with_default_team(mut self, team_id: &str) -> Self {
        self.default_team_id = Some(team_id.to_string());
        self
    }

    /// Set default project
    pub fn with_default_project(mut self, project_id: &str) -> Self {
        self.default_project_id = Some(project_id.to_string());
        self
    }

    /// Create an issue with full options
    pub fn create_issue(
        &self,
        title: &str,
        description: &str,
        team_id: Option<&str>,
        project_id: Option<&str>,
        labels: &[&str],
        priority: Option<LinearPriority>,
        assignee_id: Option<&str>,
    ) -> Result<LinearIssue, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let _token = self.config.as_ref()
            .and_then(|c| c.auth_token.as_ref())
            .ok_or(IntegrationError::MissingAuth)?;

        let team = team_id
            .map(|t| t.to_string())
            .or_else(|| self.default_team_id.clone())
            .ok_or_else(|| IntegrationError::MissingConfig("team_id required".to_string()))?;

        // GraphQL mutation
        let _mutation = r#"
            mutation CreateIssue($input: IssueCreateInput!) {
                issueCreate(input: $input) {
                    success
                    issue {
                        id
                        identifier
                        title
                        url
                    }
                }
            }
        "#;

        let _variables = serde_json::json!({
            "input": {
                "teamId": team,
                "projectId": project_id.or(self.default_project_id.as_deref()),
                "title": title,
                "description": description,
                "labelIds": labels,
                "priority": priority.map(|p| p as u8),
                "assigneeId": assignee_id,
            }
        });

        // Placeholder response
        let issue_id = format!("ISS-{}", rand::random::<u32>() % 10000);
        Ok(LinearIssue {
            id: format!("uuid-{}", rand::random::<u32>()),
            identifier: issue_id.clone(),
            title: title.to_string(),
            description: Some(description.to_string()),
            url: format!("https://linear.app/team/issue/{}", issue_id),
            state: LinearIssueState::Todo,
            priority: priority.unwrap_or(LinearPriority::NoPriority),
        })
    }

    /// Update an issue
    pub fn update_issue(
        &self,
        issue_id: &str,
        updates: LinearIssueUpdate,
    ) -> Result<LinearIssue, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let _token = self.config.as_ref()
            .and_then(|c| c.auth_token.as_ref())
            .ok_or(IntegrationError::MissingAuth)?;

        // GraphQL mutation issueUpdate
        // Placeholder
        Ok(LinearIssue {
            id: issue_id.to_string(),
            identifier: "ISS-123".to_string(),
            title: updates.title.unwrap_or_else(|| "Updated".to_string()),
            description: updates.description,
            url: format!("https://linear.app/team/issue/{}", issue_id),
            state: updates.state.unwrap_or(LinearIssueState::InProgress),
            priority: updates.priority.unwrap_or(LinearPriority::Medium),
        })
    }

    /// Add a comment to an issue
    pub fn add_comment(
        &self,
        issue_id: &str,
        body: &str,
    ) -> Result<IntegrationResult, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        let _token = self.config.as_ref()
            .and_then(|c| c.auth_token.as_ref())
            .ok_or(IntegrationError::MissingAuth)?;

        // GraphQL mutation commentCreate
        Ok(IntegrationResult {
            success: true,
            message: Some(format!("Comment added to {}", issue_id)),
            data: Some(serde_json::json!({
                "issue_id": issue_id,
                "body": body,
            })),
            error: None,
        })
    }

    /// List teams
    pub fn list_teams(&self) -> Result<Vec<LinearTeam>, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        // GraphQL query teams
        Ok(vec![
            LinearTeam {
                id: "team-1".to_string(),
                name: "Engineering".to_string(),
                key: "ENG".to_string(),
            },
            LinearTeam {
                id: "team-2".to_string(),
                name: "Product".to_string(),
                key: "PROD".to_string(),
            },
        ])
    }

    /// Search issues
    pub fn search_issues(&self, _query: &str) -> Result<Vec<LinearIssue>, IntegrationError> {
        if !self.connected {
            return Err(IntegrationError::NotConnected);
        }

        // GraphQL query issueSearch
        // Placeholder
        Ok(vec![])
    }
}

impl Default for LinearIntegration {
    fn default() -> Self {
        Self::new()
    }
}

impl Integration for LinearIntegration {
    fn integration_type(&self) -> IntegrationType {
        IntegrationType::Linear
    }

    fn is_connected(&self) -> bool {
        self.connected
    }

    fn connect(&mut self, config: &IntegrationConfig) -> Result<(), IntegrationError> {
        if config.auth_token.is_none() {
            return Err(IntegrationError::MissingAuth);
        }

        // Verify token with viewer query
        self.config = Some(config.clone());
        self.connected = true;

        if let Some(team) = config.settings.get("default_team_id") {
            self.default_team_id = team.as_str().map(|s| s.to_string());
        }

        if let Some(project) = config.settings.get("default_project_id") {
            self.default_project_id = project.as_str().map(|s| s.to_string());
        }

        self.workspace = Some(LinearWorkspace {
            id: "workspace-1".to_string(),
            name: "SAM Workspace".to_string(),
            url_key: "sam".to_string(),
        });

        Ok(())
    }

    fn disconnect(&mut self) {
        self.connected = false;
        self.config = None;
        self.workspace = None;
    }

    fn send_message(&self, issue_id: &str, message: &str) -> Result<IntegrationResult, IntegrationError> {
        // Send as comment on issue
        self.add_comment(issue_id, message)
    }

    fn send_block(&self, issue_id: &str, title: &str, content: &str, language: Option<&str>) -> Result<IntegrationResult, IntegrationError> {
        // Send as formatted comment
        let formatted = if let Some(lang) = language {
            format!("## {}\n\n```{}\n{}\n```", title, lang, content)
        } else {
            format!("## {}\n\n```\n{}\n```", title, content)
        };

        self.add_comment(issue_id, &formatted)
    }

    fn create_task(&self, title: &str, description: &str, labels: &[&str]) -> Result<IntegrationResult, IntegrationError> {
        let issue = self.create_issue(title, description, None, None, labels, None, None)?;

        Ok(IntegrationResult {
            success: true,
            message: Some(format!("Issue created: {}", issue.identifier)),
            data: Some(serde_json::to_value(&issue).unwrap()),
            error: None,
        })
    }

    fn handle_event(&self, event: &IntegrationEvent) -> Result<IntegrationResult, IntegrationError> {
        match event.event_type.as_str() {
            "Issue" => {
                // Issue created/updated webhook
                let action = event.payload.get("action")
                    .and_then(|a| a.as_str())
                    .unwrap_or("unknown");

                Ok(IntegrationResult {
                    success: true,
                    message: Some(format!("Issue {}", action)),
                    data: Some(event.payload.clone()),
                    error: None,
                })
            }
            "Comment" => {
                Ok(IntegrationResult {
                    success: true,
                    message: Some("Comment event".to_string()),
                    data: Some(event.payload.clone()),
                    error: None,
                })
            }
            _ => Ok(IntegrationResult {
                success: true,
                message: Some(format!("Unhandled Linear event: {}", event.event_type)),
                data: None,
                error: None,
            }),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinearWorkspace {
    pub id: String,
    pub name: String,
    pub url_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinearTeam {
    pub id: String,
    pub name: String,
    pub key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinearIssue {
    pub id: String,
    pub identifier: String,
    pub title: String,
    pub description: Option<String>,
    pub url: String,
    pub state: LinearIssueState,
    pub priority: LinearPriority,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum LinearIssueState {
    Backlog,
    Todo,
    InProgress,
    Done,
    Cancelled,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
#[repr(u8)]
pub enum LinearPriority {
    NoPriority = 0,
    Urgent = 1,
    High = 2,
    Medium = 3,
    Low = 4,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LinearIssueUpdate {
    pub title: Option<String>,
    pub description: Option<String>,
    pub state: Option<LinearIssueState>,
    pub priority: Option<LinearPriority>,
    pub assignee_id: Option<String>,
    pub label_ids: Option<Vec<String>>,
}

// =============================================================================
// INTEGRATION MANAGER
// =============================================================================

pub struct IntegrationManager {
    integrations: HashMap<IntegrationType, Box<dyn Integration>>,
    event_handlers: Vec<Box<dyn Fn(&IntegrationEvent) + Send + Sync>>,
}

impl IntegrationManager {
    pub fn new() -> Self {
        let mut manager = Self {
            integrations: HashMap::new(),
            event_handlers: Vec::new(),
        };

        // Register default integrations
        manager.register(Box::new(SlackIntegration::new()));
        manager.register(Box::new(LinearIntegration::new()));

        manager
    }

    /// Register an integration
    pub fn register(&mut self, integration: Box<dyn Integration>) {
        self.integrations.insert(integration.integration_type(), integration);
    }

    /// Get an integration
    pub fn get(&self, integration_type: IntegrationType) -> Option<&dyn Integration> {
        self.integrations.get(&integration_type).map(|i| i.as_ref())
    }

    /// Get mutable integration
    pub fn get_mut(&mut self, integration_type: IntegrationType) -> Option<&mut Box<dyn Integration>> {
        self.integrations.get_mut(&integration_type)
    }

    /// Connect an integration
    pub fn connect(&mut self, config: IntegrationConfig) -> Result<(), IntegrationError> {
        if let Some(integration) = self.integrations.get_mut(&config.integration_type) {
            integration.connect(&config)
        } else {
            Err(IntegrationError::NotFound(format!("{:?}", config.integration_type)))
        }
    }

    /// Disconnect an integration
    pub fn disconnect(&mut self, integration_type: IntegrationType) {
        if let Some(integration) = self.integrations.get_mut(&integration_type) {
            integration.disconnect();
        }
    }

    /// List connected integrations
    pub fn list_connected(&self) -> Vec<IntegrationType> {
        self.integrations
            .iter()
            .filter(|(_, i)| i.is_connected())
            .map(|(t, _)| *t)
            .collect()
    }

    /// Send message via integration
    pub fn send_message(
        &self,
        integration_type: IntegrationType,
        channel: &str,
        message: &str,
    ) -> Result<IntegrationResult, IntegrationError> {
        let integration = self.integrations.get(&integration_type)
            .ok_or_else(|| IntegrationError::NotFound(format!("{:?}", integration_type)))?;

        integration.send_message(channel, message)
    }

    /// Send block via integration
    pub fn send_block(
        &self,
        integration_type: IntegrationType,
        channel: &str,
        title: &str,
        content: &str,
        language: Option<&str>,
    ) -> Result<IntegrationResult, IntegrationError> {
        let integration = self.integrations.get(&integration_type)
            .ok_or_else(|| IntegrationError::NotFound(format!("{:?}", integration_type)))?;

        integration.send_block(channel, title, content, language)
    }

    /// Create task via integration
    pub fn create_task(
        &self,
        integration_type: IntegrationType,
        title: &str,
        description: &str,
        labels: &[&str],
    ) -> Result<IntegrationResult, IntegrationError> {
        let integration = self.integrations.get(&integration_type)
            .ok_or_else(|| IntegrationError::NotFound(format!("{:?}", integration_type)))?;

        integration.create_task(title, description, labels)
    }

    /// Handle incoming event
    pub fn handle_event(&self, event: IntegrationEvent) -> Result<IntegrationResult, IntegrationError> {
        // Notify handlers
        for handler in &self.event_handlers {
            handler(&event);
        }

        // Dispatch to integration
        if let Some(integration) = self.integrations.get(&event.source) {
            integration.handle_event(&event)
        } else {
            Err(IntegrationError::NotFound(format!("{:?}", event.source)))
        }
    }

    /// Register event handler
    pub fn on_event<F>(&mut self, handler: F)
    where
        F: Fn(&IntegrationEvent) + Send + Sync + 'static,
    {
        self.event_handlers.push(Box::new(handler));
    }

    /// Quick share to Slack
    pub fn share_to_slack(&self, channel: &str, title: &str, content: &str) -> Result<IntegrationResult, IntegrationError> {
        self.send_block(IntegrationType::Slack, channel, title, content, Some("bash"))
    }

    /// Quick create Linear issue
    pub fn create_linear_issue(&self, title: &str, description: &str) -> Result<IntegrationResult, IntegrationError> {
        self.create_task(IntegrationType::Linear, title, description, &[])
    }
}

impl Default for IntegrationManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// ERROR TYPE
// =============================================================================

#[derive(Debug)]
pub enum IntegrationError {
    NotConnected,
    MissingAuth,
    MissingConfig(String),
    NotFound(String),
    NotSupported(String),
    NetworkError(String),
    ParseError(String),
    ApiError(String),
}

impl std::fmt::Display for IntegrationError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            IntegrationError::NotConnected => write!(f, "Integration not connected"),
            IntegrationError::MissingAuth => write!(f, "Missing authentication token"),
            IntegrationError::MissingConfig(msg) => write!(f, "Missing config: {}", msg),
            IntegrationError::NotFound(name) => write!(f, "Integration not found: {}", name),
            IntegrationError::NotSupported(msg) => write!(f, "Not supported: {}", msg),
            IntegrationError::NetworkError(msg) => write!(f, "Network error: {}", msg),
            IntegrationError::ParseError(msg) => write!(f, "Parse error: {}", msg),
            IntegrationError::ApiError(msg) => write!(f, "API error: {}", msg),
        }
    }
}

impl std::error::Error for IntegrationError {}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref INTEGRATION_MANAGER: Arc<Mutex<IntegrationManager>> =
        Arc::new(Mutex::new(IntegrationManager::new()));
}

/// Get the global integration manager
pub fn integrations() -> Arc<Mutex<IntegrationManager>> {
    INTEGRATION_MANAGER.clone()
}

/// Quick share to Slack
pub fn share_to_slack(channel: &str, title: &str, content: &str) -> Result<IntegrationResult, IntegrationError> {
    INTEGRATION_MANAGER.lock().unwrap().share_to_slack(channel, title, content)
}

/// Quick create Linear issue
pub fn create_linear_issue(title: &str, description: &str) -> Result<IntegrationResult, IntegrationError> {
    INTEGRATION_MANAGER.lock().unwrap().create_linear_issue(title, description)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_slack_integration_new() {
        let slack = SlackIntegration::new();
        assert!(!slack.is_connected());
        assert_eq!(slack.integration_type(), IntegrationType::Slack);
    }

    #[test]
    fn test_slack_connect() {
        let mut slack = SlackIntegration::new();

        let config = IntegrationConfig {
            integration_type: IntegrationType::Slack,
            enabled: true,
            name: "Test Slack".to_string(),
            auth_token: Some("xoxb-test-token".to_string()),
            webhook_url: None,
            settings: HashMap::new(),
        };

        slack.connect(&config).unwrap();
        assert!(slack.is_connected());
    }

    #[test]
    fn test_slack_requires_auth() {
        let mut slack = SlackIntegration::new();

        let config = IntegrationConfig {
            integration_type: IntegrationType::Slack,
            enabled: true,
            name: "Test".to_string(),
            auth_token: None,
            webhook_url: None,
            settings: HashMap::new(),
        };

        let result = slack.connect(&config);
        assert!(matches!(result, Err(IntegrationError::MissingAuth)));
    }

    #[test]
    fn test_linear_integration_new() {
        let linear = LinearIntegration::new();
        assert!(!linear.is_connected());
        assert_eq!(linear.integration_type(), IntegrationType::Linear);
    }

    #[test]
    fn test_linear_connect() {
        let mut linear = LinearIntegration::new();

        let config = IntegrationConfig {
            integration_type: IntegrationType::Linear,
            enabled: true,
            name: "Test Linear".to_string(),
            auth_token: Some("lin_test_token".to_string()),
            webhook_url: None,
            settings: HashMap::new(),
        };

        linear.connect(&config).unwrap();
        assert!(linear.is_connected());
    }

    #[test]
    fn test_manager_register() {
        let manager = IntegrationManager::new();

        // Should have Slack and Linear by default
        assert!(manager.get(IntegrationType::Slack).is_some());
        assert!(manager.get(IntegrationType::Linear).is_some());
    }

    #[test]
    fn test_manager_list_connected() {
        let mut manager = IntegrationManager::new();

        // Initially none connected
        assert!(manager.list_connected().is_empty());

        // Connect Slack
        let config = IntegrationConfig {
            integration_type: IntegrationType::Slack,
            enabled: true,
            name: "Slack".to_string(),
            auth_token: Some("xoxb-test".to_string()),
            webhook_url: None,
            settings: HashMap::new(),
        };

        manager.connect(config).unwrap();

        let connected = manager.list_connected();
        assert_eq!(connected.len(), 1);
        assert!(connected.contains(&IntegrationType::Slack));
    }

    #[test]
    fn test_slack_send_when_connected() {
        let mut slack = SlackIntegration::new();

        let config = IntegrationConfig {
            integration_type: IntegrationType::Slack,
            enabled: true,
            name: "Slack".to_string(),
            auth_token: Some("xoxb-test".to_string()),
            webhook_url: None,
            settings: HashMap::new(),
        };

        slack.connect(&config).unwrap();

        let result = slack.send_message("#general", "Hello!").unwrap();
        assert!(result.success);
    }

    #[test]
    fn test_linear_create_issue_when_connected() {
        let mut linear = LinearIntegration::new()
            .with_default_team("team-1");

        let config = IntegrationConfig {
            integration_type: IntegrationType::Linear,
            enabled: true,
            name: "Linear".to_string(),
            auth_token: Some("lin_test".to_string()),
            webhook_url: None,
            settings: HashMap::new(),
        };

        linear.connect(&config).unwrap();

        let issue = linear.create_issue(
            "Test Issue",
            "Description",
            None,
            None,
            &[],
            Some(LinearPriority::High),
            None,
        ).unwrap();

        assert!(!issue.id.is_empty());
        assert!(issue.title == "Test Issue");
    }
}
