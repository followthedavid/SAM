// External AI Bridge - Claude API and OpenAI API Integration
//
// Provides direct API access to:
// - Anthropic Claude (claude-3-5-sonnet, claude-3-opus)
// - OpenAI ChatGPT (gpt-4, gpt-4-turbo, gpt-3.5-turbo)
//
// API keys are loaded from environment or config file

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::PathBuf;

// =============================================================================
// CONFIGURATION
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AIConfig {
    pub claude_api_key: Option<String>,
    pub openai_api_key: Option<String>,
    pub default_claude_model: String,
    pub default_openai_model: String,
    pub max_tokens: u32,
    pub temperature: f32,
}

impl Default for AIConfig {
    fn default() -> Self {
        Self {
            claude_api_key: None,
            openai_api_key: None,
            default_claude_model: "claude-sonnet-4-20250514".to_string(),
            default_openai_model: "gpt-4-turbo-preview".to_string(),
            max_tokens: 4096,
            temperature: 0.7,
        }
    }
}

impl AIConfig {
    /// Load config from file or environment
    pub fn load() -> Self {
        let mut config = Self::default();

        // Try environment variables first
        if let Ok(key) = std::env::var("ANTHROPIC_API_KEY") {
            config.claude_api_key = Some(key);
        }
        if let Ok(key) = std::env::var("OPENAI_API_KEY") {
            config.openai_api_key = Some(key);
        }

        // Try config file
        let config_path = dirs::home_dir()
            .map(|h| h.join(".sam_ai_config.json"))
            .unwrap_or_else(|| PathBuf::from("/tmp/.sam_ai_config.json"));

        if config_path.exists() {
            if let Ok(contents) = std::fs::read_to_string(&config_path) {
                if let Ok(file_config) = serde_json::from_str::<AIConfig>(&contents) {
                    // File config takes precedence if env vars not set
                    if config.claude_api_key.is_none() {
                        config.claude_api_key = file_config.claude_api_key;
                    }
                    if config.openai_api_key.is_none() {
                        config.openai_api_key = file_config.openai_api_key;
                    }
                    config.default_claude_model = file_config.default_claude_model;
                    config.default_openai_model = file_config.default_openai_model;
                    config.max_tokens = file_config.max_tokens;
                    config.temperature = file_config.temperature;
                }
            }
        }

        config
    }

    /// Save config to file
    pub fn save(&self) -> Result<(), String> {
        let config_path = dirs::home_dir()
            .map(|h| h.join(".sam_ai_config.json"))
            .unwrap_or_else(|| PathBuf::from("/tmp/.sam_ai_config.json"));

        std::fs::write(
            &config_path,
            serde_json::to_string_pretty(self).map_err(|e| e.to_string())?,
        )
        .map_err(|e| e.to_string())
    }

    pub fn has_claude(&self) -> bool {
        self.claude_api_key.is_some()
    }

    pub fn has_openai(&self) -> bool {
        self.openai_api_key.is_some()
    }
}

// =============================================================================
// MESSAGE TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChatMessage {
    pub role: String,  // "user", "assistant", "system"
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AIResponse {
    pub content: String,
    pub model: String,
    pub tokens_used: u32,
    pub finish_reason: String,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AIError {
    pub message: String,
    pub error_type: String,
    pub retryable: bool,
}

// =============================================================================
// CLAUDE API
// =============================================================================

pub struct ClaudeClient {
    api_key: String,
    model: String,
    max_tokens: u32,
    temperature: f32,
}

impl ClaudeClient {
    pub fn new(config: &AIConfig) -> Result<Self, AIError> {
        let api_key = config.claude_api_key.clone().ok_or_else(|| AIError {
            message: "Claude API key not configured. Set ANTHROPIC_API_KEY environment variable or add to ~/.sam_ai_config.json".to_string(),
            error_type: "config_error".to_string(),
            retryable: false,
        })?;

        Ok(Self {
            api_key,
            model: config.default_claude_model.clone(),
            max_tokens: config.max_tokens,
            temperature: config.temperature,
        })
    }

    pub fn with_model(mut self, model: &str) -> Self {
        self.model = model.to_string();
        self
    }

    pub async fn chat(&self, messages: &[ChatMessage]) -> Result<AIResponse, AIError> {
        let start = std::time::Instant::now();

        // Convert messages to Claude format
        let claude_messages: Vec<Value> = messages
            .iter()
            .filter(|m| m.role != "system")
            .map(|m| {
                json!({
                    "role": m.role,
                    "content": m.content
                })
            })
            .collect();

        // Extract system message if present
        let system = messages
            .iter()
            .find(|m| m.role == "system")
            .map(|m| m.content.clone());

        let mut request_body = json!({
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": claude_messages,
            "temperature": self.temperature,
        });

        if let Some(sys) = system {
            request_body["system"] = json!(sys);
        }

        let client = reqwest::Client::new();
        let response = client
            .post("https://api.anthropic.com/v1/messages")
            .header("Content-Type", "application/json")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", "2023-06-01")
            .json(&request_body)
            .send()
            .await
            .map_err(|e| AIError {
                message: format!("Request failed: {}", e),
                error_type: "network_error".to_string(),
                retryable: true,
            })?;

        let status = response.status();
        let body: Value = response.json().await.map_err(|e| AIError {
            message: format!("Failed to parse response: {}", e),
            error_type: "parse_error".to_string(),
            retryable: false,
        })?;

        if !status.is_success() {
            return Err(AIError {
                message: body["error"]["message"]
                    .as_str()
                    .unwrap_or("Unknown error")
                    .to_string(),
                error_type: body["error"]["type"]
                    .as_str()
                    .unwrap_or("api_error")
                    .to_string(),
                retryable: status.as_u16() == 429 || status.as_u16() >= 500,
            });
        }

        let content = body["content"]
            .as_array()
            .and_then(|arr| arr.first())
            .and_then(|c| c["text"].as_str())
            .unwrap_or("")
            .to_string();

        let input_tokens = body["usage"]["input_tokens"].as_u64().unwrap_or(0) as u32;
        let output_tokens = body["usage"]["output_tokens"].as_u64().unwrap_or(0) as u32;

        Ok(AIResponse {
            content,
            model: self.model.clone(),
            tokens_used: input_tokens + output_tokens,
            finish_reason: body["stop_reason"]
                .as_str()
                .unwrap_or("end_turn")
                .to_string(),
            latency_ms: start.elapsed().as_millis() as u64,
        })
    }

    /// Simple completion without conversation history
    pub async fn complete(&self, prompt: &str) -> Result<AIResponse, AIError> {
        self.chat(&[ChatMessage {
            role: "user".to_string(),
            content: prompt.to_string(),
        }])
        .await
    }

    /// Completion with system prompt
    pub async fn complete_with_system(
        &self,
        system: &str,
        prompt: &str,
    ) -> Result<AIResponse, AIError> {
        self.chat(&[
            ChatMessage {
                role: "system".to_string(),
                content: system.to_string(),
            },
            ChatMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            },
        ])
        .await
    }
}

// =============================================================================
// OPENAI API
// =============================================================================

pub struct OpenAIClient {
    api_key: String,
    model: String,
    max_tokens: u32,
    temperature: f32,
}

impl OpenAIClient {
    pub fn new(config: &AIConfig) -> Result<Self, AIError> {
        let api_key = config.openai_api_key.clone().ok_or_else(|| AIError {
            message: "OpenAI API key not configured. Set OPENAI_API_KEY environment variable or add to ~/.sam_ai_config.json".to_string(),
            error_type: "config_error".to_string(),
            retryable: false,
        })?;

        Ok(Self {
            api_key,
            model: config.default_openai_model.clone(),
            max_tokens: config.max_tokens,
            temperature: config.temperature,
        })
    }

    pub fn with_model(mut self, model: &str) -> Self {
        self.model = model.to_string();
        self
    }

    pub async fn chat(&self, messages: &[ChatMessage]) -> Result<AIResponse, AIError> {
        let start = std::time::Instant::now();

        let openai_messages: Vec<Value> = messages
            .iter()
            .map(|m| {
                json!({
                    "role": m.role,
                    "content": m.content
                })
            })
            .collect();

        let request_body = json!({
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": openai_messages,
            "temperature": self.temperature,
        });

        let client = reqwest::Client::new();
        let response = client
            .post("https://api.openai.com/v1/chat/completions")
            .header("Content-Type", "application/json")
            .header("Authorization", format!("Bearer {}", self.api_key))
            .json(&request_body)
            .send()
            .await
            .map_err(|e| AIError {
                message: format!("Request failed: {}", e),
                error_type: "network_error".to_string(),
                retryable: true,
            })?;

        let status = response.status();
        let body: Value = response.json().await.map_err(|e| AIError {
            message: format!("Failed to parse response: {}", e),
            error_type: "parse_error".to_string(),
            retryable: false,
        })?;

        if !status.is_success() {
            return Err(AIError {
                message: body["error"]["message"]
                    .as_str()
                    .unwrap_or("Unknown error")
                    .to_string(),
                error_type: body["error"]["type"]
                    .as_str()
                    .unwrap_or("api_error")
                    .to_string(),
                retryable: status.as_u16() == 429 || status.as_u16() >= 500,
            });
        }

        let content = body["choices"]
            .as_array()
            .and_then(|arr| arr.first())
            .and_then(|c| c["message"]["content"].as_str())
            .unwrap_or("")
            .to_string();

        let tokens = body["usage"]["total_tokens"].as_u64().unwrap_or(0) as u32;
        let finish_reason = body["choices"]
            .as_array()
            .and_then(|arr| arr.first())
            .and_then(|c| c["finish_reason"].as_str())
            .unwrap_or("stop")
            .to_string();

        Ok(AIResponse {
            content,
            model: self.model.clone(),
            tokens_used: tokens,
            finish_reason,
            latency_ms: start.elapsed().as_millis() as u64,
        })
    }

    /// Simple completion without conversation history
    pub async fn complete(&self, prompt: &str) -> Result<AIResponse, AIError> {
        self.chat(&[ChatMessage {
            role: "user".to_string(),
            content: prompt.to_string(),
        }])
        .await
    }

    /// Completion with system prompt
    pub async fn complete_with_system(
        &self,
        system: &str,
        prompt: &str,
    ) -> Result<AIResponse, AIError> {
        self.chat(&[
            ChatMessage {
                role: "system".to_string(),
                content: system.to_string(),
            },
            ChatMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            },
        ])
        .await
    }
}

// =============================================================================
// UNIFIED INTERFACE
// =============================================================================

pub enum AIProvider {
    Claude,
    OpenAI,
    Auto,  // Try Claude first, fallback to OpenAI
}

pub struct UnifiedAI {
    config: AIConfig,
}

impl UnifiedAI {
    pub fn new() -> Self {
        Self {
            config: AIConfig::load(),
        }
    }

    pub fn with_config(config: AIConfig) -> Self {
        Self { config }
    }

    /// Get availability status
    pub fn status(&self) -> Value {
        json!({
            "claude_available": self.config.has_claude(),
            "openai_available": self.config.has_openai(),
            "claude_model": self.config.default_claude_model,
            "openai_model": self.config.default_openai_model,
        })
    }

    /// Chat with automatic provider selection
    pub async fn chat(
        &self,
        messages: &[ChatMessage],
        provider: AIProvider,
    ) -> Result<AIResponse, AIError> {
        match provider {
            AIProvider::Claude => {
                let client = ClaudeClient::new(&self.config)?;
                client.chat(messages).await
            }
            AIProvider::OpenAI => {
                let client = OpenAIClient::new(&self.config)?;
                client.chat(messages).await
            }
            AIProvider::Auto => {
                // Try Claude first
                if self.config.has_claude() {
                    match ClaudeClient::new(&self.config) {
                        Ok(client) => match client.chat(messages).await {
                            Ok(response) => return Ok(response),
                            Err(e) if e.retryable => {
                                eprintln!("[UnifiedAI] Claude failed, trying OpenAI: {}", e.message);
                            }
                            Err(e) => return Err(e),
                        },
                        Err(e) => {
                            eprintln!("[UnifiedAI] Claude not available: {}", e.message);
                        }
                    }
                }

                // Fallback to OpenAI
                if self.config.has_openai() {
                    let client = OpenAIClient::new(&self.config)?;
                    return client.chat(messages).await;
                }

                Err(AIError {
                    message: "No AI providers configured. Set ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable.".to_string(),
                    error_type: "config_error".to_string(),
                    retryable: false,
                })
            }
        }
    }

    /// Simple completion
    pub async fn complete(&self, prompt: &str, provider: AIProvider) -> Result<AIResponse, AIError> {
        self.chat(
            &[ChatMessage {
                role: "user".to_string(),
                content: prompt.to_string(),
            }],
            provider,
        )
        .await
    }

    /// Code-focused completion with system prompt
    pub async fn code_complete(
        &self,
        prompt: &str,
        provider: AIProvider,
    ) -> Result<AIResponse, AIError> {
        let system = r#"You are an expert software engineer. Provide clear, concise code solutions.
When showing code, use appropriate markdown code blocks with language identifiers.
Focus on practical, working solutions."#;

        self.chat(
            &[
                ChatMessage {
                    role: "system".to_string(),
                    content: system.to_string(),
                },
                ChatMessage {
                    role: "user".to_string(),
                    content: prompt.to_string(),
                },
            ],
            provider,
        )
        .await
    }
}

// =============================================================================
// TAURI COMMANDS
// =============================================================================

/// Check AI provider availability
pub fn check_ai_status() -> Value {
    let ai = UnifiedAI::new();
    ai.status()
}

/// Call Claude API
pub async fn call_claude(prompt: &str, system: Option<&str>) -> Result<AIResponse, AIError> {
    let config = AIConfig::load();
    let client = ClaudeClient::new(&config)?;

    if let Some(sys) = system {
        client.complete_with_system(sys, prompt).await
    } else {
        client.complete(prompt).await
    }
}

/// Call OpenAI API
pub async fn call_openai(prompt: &str, system: Option<&str>) -> Result<AIResponse, AIError> {
    let config = AIConfig::load();
    let client = OpenAIClient::new(&config)?;

    if let Some(sys) = system {
        client.complete_with_system(sys, prompt).await
    } else {
        client.complete(prompt).await
    }
}

/// Auto-select best available provider
pub async fn call_ai(prompt: &str, system: Option<&str>) -> Result<AIResponse, AIError> {
    let ai = UnifiedAI::new();

    let mut messages = Vec::new();
    if let Some(sys) = system {
        messages.push(ChatMessage {
            role: "system".to_string(),
            content: sys.to_string(),
        });
    }
    messages.push(ChatMessage {
        role: "user".to_string(),
        content: prompt.to_string(),
    });

    ai.chat(&messages, AIProvider::Auto).await
}

/// Set API key
pub fn set_api_key(provider: &str, key: &str) -> Result<(), String> {
    let mut config = AIConfig::load();

    match provider.to_lowercase().as_str() {
        "claude" | "anthropic" => config.claude_api_key = Some(key.to_string()),
        "openai" | "chatgpt" => config.openai_api_key = Some(key.to_string()),
        _ => return Err(format!("Unknown provider: {}", provider)),
    }

    config.save()
}

// =============================================================================
// BROWSER BRIDGE FALLBACK
// =============================================================================

/// Queue a request for the browser bridge (fallback when no API keys)
pub fn queue_browser_bridge(prompt: &str, provider: &str) -> Result<String, String> {
    let queue_file = dirs::home_dir()
        .map(|h| h.join(".sam_chatgpt_queue.json"))
        .unwrap_or_else(|| std::path::PathBuf::from("/tmp/.sam_chatgpt_queue.json"));

    // Generate task ID
    let task_id = format!(
        "task_{}",
        std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_millis()
    );

    // Load existing queue
    let mut queue: Vec<serde_json::Value> = if queue_file.exists() {
        std::fs::read_to_string(&queue_file)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        Vec::new()
    };

    // Add new task
    queue.push(serde_json::json!({
        "id": task_id,
        "prompt": prompt,
        "provider": provider,
        "status": "pending",
        "created_at": chrono::Utc::now().to_rfc3339(),
    }));

    // Save queue
    std::fs::write(&queue_file, serde_json::to_string_pretty(&queue).unwrap())
        .map_err(|e| format!("Failed to write queue: {}", e))?;

    eprintln!("[BRIDGE] Queued task {} for {}", task_id, provider);
    Ok(task_id)
}

/// Check for browser bridge response
pub fn check_bridge_response(task_id: &str) -> Option<String> {
    let response_file = dirs::home_dir()
        .map(|h| h.join(".sam_chatgpt_responses.json"))
        .unwrap_or_else(|| std::path::PathBuf::from("/tmp/.sam_chatgpt_responses.json"));

    if !response_file.exists() {
        return None;
    }

    let responses: serde_json::Value = std::fs::read_to_string(&response_file)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();

    responses
        .get(task_id)
        .and_then(|r| r.get("response"))
        .and_then(|s| s.as_str())
        .map(|s| s.to_string())
}

/// Call browser bridge directly (spawns Node process)
pub fn call_browser_bridge_sync(prompt: &str, provider: &str) -> Result<String, String> {
    let bridge_path = std::env::current_dir()
        .unwrap_or_default()
        .join("ai_bridge.cjs");

    // Fallback path
    let bridge_path = if bridge_path.exists() {
        bridge_path
    } else {
        dirs::home_dir()
            .map(|h| h.join("ReverseLab/SAM/warp_tauri/ai_bridge.cjs"))
            .unwrap_or(bridge_path)
    };

    if !bridge_path.exists() {
        return Err("Bridge script not found. Run bridge daemon manually.".to_string());
    }

    let provider_arg = if provider == "claude" { "--claude" } else { "" };

    let output = std::process::Command::new("node")
        .arg(&bridge_path)
        .arg("send")
        .arg(prompt)
        .arg(provider_arg)
        .output()
        .map_err(|e| format!("Failed to run bridge: {}", e))?;

    if output.status.success() {
        let result: serde_json::Value = serde_json::from_slice(&output.stdout)
            .map_err(|e| format!("Failed to parse bridge output: {}", e))?;

        if result.get("success").and_then(|v| v.as_bool()).unwrap_or(false) {
            result
                .get("response")
                .and_then(|s| s.as_str())
                .map(|s| s.to_string())
                .ok_or_else(|| "No response in output".to_string())
        } else {
            Err(result
                .get("error")
                .and_then(|s| s.as_str())
                .unwrap_or("Bridge failed")
                .to_string())
        }
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

/// Auto-select best method: API if available, else browser bridge
pub async fn call_ai_with_fallback(prompt: &str, system: Option<&str>) -> Result<String, String> {
    let ai = UnifiedAI::new();

    // Try API first if available
    if ai.config.has_claude() || ai.config.has_openai() {
        match call_ai(prompt, system).await {
            Ok(response) => return Ok(response.content),
            Err(e) => {
                eprintln!("[AI] API call failed, trying browser bridge: {}", e.message);
            }
        }
    }

    // Fallback to browser bridge
    eprintln!("[AI] No API keys configured, using browser bridge");
    let full_prompt = if let Some(sys) = system {
        format!("{}\n\n{}", sys, prompt)
    } else {
        prompt.to_string()
    };

    call_browser_bridge_sync(&full_prompt, "chatgpt")
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default() {
        let config = AIConfig::default();
        assert!(config.claude_api_key.is_none());
        assert!(config.openai_api_key.is_none());
        assert_eq!(config.max_tokens, 4096);
    }

    #[test]
    fn test_unified_ai_status() {
        let ai = UnifiedAI::new();
        let status = ai.status();
        assert!(status.get("claude_available").is_some());
        assert!(status.get("openai_available").is_some());
    }

    #[tokio::test]
    async fn test_claude_without_key() {
        let config = AIConfig::default();
        let result = ClaudeClient::new(&config);
        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_openai_without_key() {
        let config = AIConfig::default();
        let result = OpenAIClient::new(&config);
        assert!(result.is_err());
    }
}
