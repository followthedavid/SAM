//! Voice Input - Speech-to-text for terminal commands
//!
//! Provides voice input capabilities:
//! - Push-to-talk activation
//! - Voice transcription (Wispr Flow, Whisper, or system)
//! - Voice command mode
//! - Dictation mode

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// TYPES
// =============================================================================

/// Voice input provider
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Default)]
pub enum VoiceProvider {
    /// System speech recognition
    #[default]
    System,
    /// Wispr Flow integration
    WisprFlow,
    /// OpenAI Whisper API
    WhisperApi,
    /// Local Whisper model
    WhisperLocal,
}

/// Voice input state
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Default)]
pub enum VoiceState {
    #[default]
    Idle,
    Listening,
    Processing,
    Error,
}

/// Voice input mode
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Default)]
pub enum VoiceMode {
    /// Dictation - insert text at cursor
    #[default]
    Dictation,
    /// Command - execute as command
    Command,
    /// AI - send to AI assistant
    AiAssistant,
}

/// Voice transcription result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Transcription {
    /// Transcribed text
    pub text: String,
    /// Confidence score (0-1)
    pub confidence: f32,
    /// Language detected
    pub language: Option<String>,
    /// Duration in milliseconds
    pub duration_ms: u64,
    /// Provider used
    pub provider: VoiceProvider,
    /// Timestamp
    pub timestamp: DateTime<Utc>,
}

/// Voice input configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceConfig {
    /// Whether voice input is enabled
    pub enabled: bool,
    /// Voice provider
    pub provider: VoiceProvider,
    /// Hotkey for push-to-talk
    pub hotkey: String,
    /// Input mode
    pub mode: VoiceMode,
    /// Whisper API key (if using Whisper API)
    pub whisper_api_key: Option<String>,
    /// Wispr Flow API key
    pub wispr_api_key: Option<String>,
    /// Language hint
    pub language: Option<String>,
    /// Show live transcription
    pub show_live: bool,
    /// Auto-submit on silence
    pub auto_submit: bool,
    /// Silence threshold in ms
    pub silence_threshold_ms: u32,
}

impl Default for VoiceConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            provider: VoiceProvider::System,
            hotkey: "Ctrl+Shift+V".to_string(),
            mode: VoiceMode::Dictation,
            whisper_api_key: None,
            wispr_api_key: None,
            language: Some("en".to_string()),
            show_live: true,
            auto_submit: false,
            silence_threshold_ms: 1500,
        }
    }
}

// =============================================================================
// VOICE INPUT MANAGER
// =============================================================================

pub struct VoiceInputManager {
    config: VoiceConfig,
    state: VoiceState,
    current_transcription: Option<String>,
    history: Vec<Transcription>,
    handlers: Vec<Box<dyn Fn(&Transcription) + Send + Sync>>,
}

impl VoiceInputManager {
    pub fn new() -> Self {
        Self::with_config(VoiceConfig::default())
    }

    pub fn with_config(config: VoiceConfig) -> Self {
        Self {
            config,
            state: VoiceState::Idle,
            current_transcription: None,
            history: Vec::new(),
            handlers: Vec::new(),
        }
    }

    /// Start listening
    pub fn start_listening(&mut self) -> bool {
        if !self.config.enabled {
            return false;
        }

        if self.state != VoiceState::Idle {
            return false;
        }

        self.state = VoiceState::Listening;
        self.current_transcription = None;

        // Start recording based on provider
        match self.config.provider {
            VoiceProvider::System => self.start_system_recording(),
            VoiceProvider::WisprFlow => self.start_wispr_recording(),
            VoiceProvider::WhisperApi => self.start_whisper_recording(),
            VoiceProvider::WhisperLocal => self.start_local_whisper(),
        }

        true
    }

    /// Stop listening and process
    pub fn stop_listening(&mut self) -> Option<Transcription> {
        if self.state != VoiceState::Listening {
            return None;
        }

        self.state = VoiceState::Processing;

        // Process recording
        let transcription = match self.config.provider {
            VoiceProvider::System => self.process_system_recording(),
            VoiceProvider::WisprFlow => self.process_wispr_recording(),
            VoiceProvider::WhisperApi => self.process_whisper_recording(),
            VoiceProvider::WhisperLocal => self.process_local_whisper(),
        };

        self.state = VoiceState::Idle;

        if let Some(ref t) = transcription {
            self.history.push(t.clone());
            for handler in &self.handlers {
                handler(t);
            }

            // Limit history
            if self.history.len() > 100 {
                self.history.remove(0);
            }
        }

        transcription
    }

    /// Cancel listening
    pub fn cancel(&mut self) {
        self.state = VoiceState::Idle;
        self.current_transcription = None;
    }

    /// Get current state
    pub fn state(&self) -> VoiceState {
        self.state
    }

    /// Check if listening
    pub fn is_listening(&self) -> bool {
        self.state == VoiceState::Listening
    }

    /// Get live transcription (partial)
    pub fn live_transcription(&self) -> Option<&str> {
        self.current_transcription.as_deref()
    }

    /// Update live transcription
    pub fn update_live(&mut self, text: &str) {
        if self.state == VoiceState::Listening {
            self.current_transcription = Some(text.to_string());
        }
    }

    /// Get transcription history
    pub fn history(&self) -> &[Transcription] {
        &self.history
    }

    /// Clear history
    pub fn clear_history(&mut self) {
        self.history.clear();
    }

    /// Register transcription handler
    pub fn on_transcription<F>(&mut self, handler: F)
    where
        F: Fn(&Transcription) + Send + Sync + 'static,
    {
        self.handlers.push(Box::new(handler));
    }

    /// Update config
    pub fn set_config(&mut self, config: VoiceConfig) {
        self.config = config;
    }

    /// Get config
    pub fn config(&self) -> &VoiceConfig {
        &self.config
    }

    /// Set voice mode
    pub fn set_mode(&mut self, mode: VoiceMode) {
        self.config.mode = mode;
    }

    /// Get voice mode
    pub fn mode(&self) -> VoiceMode {
        self.config.mode
    }

    // Provider-specific implementations (placeholders)

    fn start_system_recording(&self) {
        // Would use platform-specific speech API
        // macOS: NSSpeechRecognizer
        // Linux: libpocketsphinx or similar
        #[cfg(target_os = "macos")]
        {
            // Use AVFoundation or SFSpeechRecognizer
        }
    }

    fn start_wispr_recording(&self) {
        // Would start Wispr Flow recording
        // Wispr handles audio capture internally
    }

    fn start_whisper_recording(&self) {
        // Would start audio capture for Whisper API
    }

    fn start_local_whisper(&self) {
        // Would start local Whisper model
    }

    fn process_system_recording(&mut self) -> Option<Transcription> {
        // Placeholder - would return actual transcription
        Some(Transcription {
            text: "example transcription".to_string(),
            confidence: 0.95,
            language: Some("en".to_string()),
            duration_ms: 1500,
            provider: VoiceProvider::System,
            timestamp: Utc::now(),
        })
    }

    fn process_wispr_recording(&mut self) -> Option<Transcription> {
        // Would call Wispr Flow API
        None
    }

    fn process_whisper_recording(&mut self) -> Option<Transcription> {
        // Would call OpenAI Whisper API
        None
    }

    fn process_local_whisper(&mut self) -> Option<Transcription> {
        // Would run local Whisper model
        None
    }
}

impl Default for VoiceInputManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// VOICE COMMANDS
// =============================================================================

/// Parse voice input for special commands
pub fn parse_voice_command(text: &str) -> Option<VoiceCommand> {
    let lower = text.to_lowercase();

    // Navigation commands
    if lower.contains("go to") || lower.starts_with("cd ") {
        let dir = text.split_whitespace().skip(2).collect::<Vec<_>>().join(" ");
        return Some(VoiceCommand::Navigate(dir));
    }

    // Run command
    if lower.starts_with("run ") || lower.starts_with("execute ") {
        let cmd = text.split_whitespace().skip(1).collect::<Vec<_>>().join(" ");
        return Some(VoiceCommand::Execute(cmd));
    }

    // Search
    if lower.starts_with("search for ") || lower.starts_with("find ") {
        let query = text.split_whitespace().skip(2).collect::<Vec<_>>().join(" ");
        return Some(VoiceCommand::Search(query));
    }

    // File operations
    if lower.starts_with("open ") {
        let file = text.split_whitespace().skip(1).collect::<Vec<_>>().join(" ");
        return Some(VoiceCommand::Open(file));
    }

    // AI commands
    if lower.starts_with("ask ") || lower.starts_with("hey sam") {
        let query = if lower.starts_with("ask ") {
            text.split_whitespace().skip(1).collect::<Vec<_>>().join(" ")
        } else {
            text.replace("hey sam", "").trim().to_string()
        };
        return Some(VoiceCommand::AskAi(query));
    }

    // Cancel
    if lower == "cancel" || lower == "stop" || lower == "nevermind" {
        return Some(VoiceCommand::Cancel);
    }

    // Clear
    if lower == "clear" || lower == "clear screen" {
        return Some(VoiceCommand::Clear);
    }

    None
}

#[derive(Debug, Clone)]
pub enum VoiceCommand {
    Navigate(String),
    Execute(String),
    Search(String),
    Open(String),
    AskAi(String),
    Cancel,
    Clear,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref VOICE_MANAGER: Arc<Mutex<VoiceInputManager>> =
        Arc::new(Mutex::new(VoiceInputManager::new()));
}

/// Get the global voice manager
pub fn voice() -> Arc<Mutex<VoiceInputManager>> {
    VOICE_MANAGER.clone()
}

/// Start listening
pub fn start_listening() -> bool {
    VOICE_MANAGER.lock().unwrap().start_listening()
}

/// Stop listening
pub fn stop_listening() -> Option<Transcription> {
    VOICE_MANAGER.lock().unwrap().stop_listening()
}

/// Check if listening
pub fn is_listening() -> bool {
    VOICE_MANAGER.lock().unwrap().is_listening()
}

/// Cancel listening
pub fn cancel() {
    VOICE_MANAGER.lock().unwrap().cancel();
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_voice_manager_new() {
        let manager = VoiceInputManager::new();
        assert!(!manager.config.enabled);
        assert_eq!(manager.state(), VoiceState::Idle);
    }

    #[test]
    fn test_start_listening_disabled() {
        let mut manager = VoiceInputManager::new();
        assert!(!manager.start_listening()); // Should fail when disabled
    }

    #[test]
    fn test_start_listening_enabled() {
        let mut manager = VoiceInputManager::new();
        manager.config.enabled = true;

        assert!(manager.start_listening());
        assert_eq!(manager.state(), VoiceState::Listening);
    }

    #[test]
    fn test_cancel() {
        let mut manager = VoiceInputManager::new();
        manager.config.enabled = true;
        manager.start_listening();

        manager.cancel();
        assert_eq!(manager.state(), VoiceState::Idle);
    }

    #[test]
    fn test_parse_voice_command_navigate() {
        let cmd = parse_voice_command("go to home directory");
        assert!(matches!(cmd, Some(VoiceCommand::Navigate(_))));
    }

    #[test]
    fn test_parse_voice_command_execute() {
        let cmd = parse_voice_command("run git status");
        assert!(matches!(cmd, Some(VoiceCommand::Execute(c)) if c == "git status"));
    }

    #[test]
    fn test_parse_voice_command_search() {
        let cmd = parse_voice_command("search for config files");
        assert!(matches!(cmd, Some(VoiceCommand::Search(_))));
    }

    #[test]
    fn test_parse_voice_command_ai() {
        let cmd = parse_voice_command("hey sam what is this error");
        assert!(matches!(cmd, Some(VoiceCommand::AskAi(_))));
    }

    #[test]
    fn test_parse_voice_command_cancel() {
        let cmd = parse_voice_command("cancel");
        assert!(matches!(cmd, Some(VoiceCommand::Cancel)));
    }

    #[test]
    fn test_live_transcription() {
        let mut manager = VoiceInputManager::new();
        manager.config.enabled = true;
        manager.start_listening();

        manager.update_live("hello");
        assert_eq!(manager.live_transcription(), Some("hello"));
    }
}
