//! Full-Screen App Support - Vim, Emacs, and other TUI apps
//!
//! Handles alternate screen buffer applications:
//! - Vim/Neovim
//! - Emacs
//! - Less/More
//! - Top/Htop
//! - tmux
//! - Other TUI applications

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

/// Known full-screen application
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FullScreenApp {
    /// Application name
    pub name: String,
    /// Commands that launch this app
    pub commands: Vec<String>,
    /// Whether app uses alternate screen
    pub uses_alt_screen: bool,
    /// Whether app handles mouse events
    pub handles_mouse: bool,
    /// Whether app uses vim keybindings
    pub vim_keybindings: bool,
    /// Recommended padding
    pub padding: AppPadding,
    /// Exit key sequences
    pub exit_sequences: Vec<String>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
pub struct AppPadding {
    pub top: u16,
    pub bottom: u16,
    pub left: u16,
    pub right: u16,
}

/// Current app state
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppState {
    /// Whether in alternate screen
    pub in_alt_screen: bool,
    /// Detected application
    pub detected_app: Option<String>,
    /// Mouse forwarding enabled
    pub mouse_forwarding: bool,
    /// Keyboard mode
    pub keyboard_mode: KeyboardMode,
    /// Current padding
    pub padding: AppPadding,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Default)]
pub enum KeyboardMode {
    #[default]
    Normal,
    Vim,
    Emacs,
    Application, // Full application keyboard mode
}

/// Configuration for full-screen app handling
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FullScreenConfig {
    /// Auto-detect apps
    pub auto_detect: bool,
    /// Forward mouse events to apps
    pub forward_mouse: bool,
    /// Default padding for apps
    pub default_padding: AppPadding,
    /// Disable SAM features when in app
    pub disable_sam_features: bool,
    /// Show app indicator
    pub show_indicator: bool,
}

impl Default for FullScreenConfig {
    fn default() -> Self {
        Self {
            auto_detect: true,
            forward_mouse: true,
            default_padding: AppPadding::default(),
            disable_sam_features: true,
            show_indicator: true,
        }
    }
}

// =============================================================================
// FULLSCREEN APP MANAGER
// =============================================================================

pub struct FullScreenManager {
    config: FullScreenConfig,
    known_apps: HashMap<String, FullScreenApp>,
    state: AppState,
    pane_states: HashMap<String, AppState>,
}

impl FullScreenManager {
    pub fn new() -> Self {
        let mut manager = Self {
            config: FullScreenConfig::default(),
            known_apps: HashMap::new(),
            state: AppState {
                in_alt_screen: false,
                detected_app: None,
                mouse_forwarding: false,
                keyboard_mode: KeyboardMode::Normal,
                padding: AppPadding::default(),
            },
            pane_states: HashMap::new(),
        };
        manager.load_known_apps();
        manager
    }

    fn load_known_apps(&mut self) {
        let apps = vec![
            FullScreenApp {
                name: "vim".to_string(),
                commands: vec!["vim".into(), "vi".into()],
                uses_alt_screen: true,
                handles_mouse: true,
                vim_keybindings: true,
                padding: AppPadding::default(),
                exit_sequences: vec![":q".into(), ":wq".into(), ":qa".into(), "ZZ".into(), "ZQ".into()],
            },
            FullScreenApp {
                name: "neovim".to_string(),
                commands: vec!["nvim".into()],
                uses_alt_screen: true,
                handles_mouse: true,
                vim_keybindings: true,
                padding: AppPadding::default(),
                exit_sequences: vec![":q".into(), ":wq".into()],
            },
            FullScreenApp {
                name: "emacs".to_string(),
                commands: vec!["emacs".into()],
                uses_alt_screen: true,
                handles_mouse: true,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["C-x C-c".into()],
            },
            FullScreenApp {
                name: "nano".to_string(),
                commands: vec!["nano".into()],
                uses_alt_screen: true,
                handles_mouse: false,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["C-x".into()],
            },
            FullScreenApp {
                name: "less".to_string(),
                commands: vec!["less".into()],
                uses_alt_screen: true,
                handles_mouse: false,
                vim_keybindings: true,
                padding: AppPadding::default(),
                exit_sequences: vec!["q".into()],
            },
            FullScreenApp {
                name: "more".to_string(),
                commands: vec!["more".into()],
                uses_alt_screen: true,
                handles_mouse: false,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["q".into()],
            },
            FullScreenApp {
                name: "htop".to_string(),
                commands: vec!["htop".into()],
                uses_alt_screen: true,
                handles_mouse: true,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["q".into(), "F10".into()],
            },
            FullScreenApp {
                name: "top".to_string(),
                commands: vec!["top".into()],
                uses_alt_screen: true,
                handles_mouse: false,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["q".into()],
            },
            FullScreenApp {
                name: "tmux".to_string(),
                commands: vec!["tmux".into()],
                uses_alt_screen: true,
                handles_mouse: true,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["C-b d".into()],
            },
            FullScreenApp {
                name: "screen".to_string(),
                commands: vec!["screen".into()],
                uses_alt_screen: true,
                handles_mouse: false,
                vim_keybindings: false,
                padding: AppPadding::default(),
                exit_sequences: vec!["C-a d".into()],
            },
            FullScreenApp {
                name: "man".to_string(),
                commands: vec!["man".into()],
                uses_alt_screen: true,
                handles_mouse: false,
                vim_keybindings: true,
                padding: AppPadding::default(),
                exit_sequences: vec!["q".into()],
            },
            FullScreenApp {
                name: "lazygit".to_string(),
                commands: vec!["lazygit".into()],
                uses_alt_screen: true,
                handles_mouse: true,
                vim_keybindings: true,
                padding: AppPadding::default(),
                exit_sequences: vec!["q".into()],
            },
        ];

        for app in apps {
            for cmd in &app.commands {
                self.known_apps.insert(cmd.clone(), app.clone());
            }
        }
    }

    /// Detect app from command
    pub fn detect_app(&self, command: &str) -> Option<&FullScreenApp> {
        // Extract base command
        let parts: Vec<&str> = command.split_whitespace().collect();
        let base_cmd = parts.first()?;

        // Remove path if present
        let cmd_name = base_cmd.rsplit('/').next()?;

        self.known_apps.get(cmd_name)
    }

    /// Handle entering alternate screen
    pub fn enter_alt_screen(&mut self, pane_id: Option<&str>, command: Option<&str>) {
        let app = command.and_then(|c| self.detect_app(c));

        let state = AppState {
            in_alt_screen: true,
            detected_app: app.map(|a| a.name.clone()),
            mouse_forwarding: app.map(|a| a.handles_mouse && self.config.forward_mouse).unwrap_or(false),
            keyboard_mode: if app.map(|a| a.vim_keybindings).unwrap_or(false) {
                KeyboardMode::Vim
            } else {
                KeyboardMode::Application
            },
            padding: app.map(|a| a.padding).unwrap_or(self.config.default_padding),
        };

        if let Some(id) = pane_id {
            self.pane_states.insert(id.to_string(), state.clone());
        }
        self.state = state;
    }

    /// Handle leaving alternate screen
    pub fn leave_alt_screen(&mut self, pane_id: Option<&str>) {
        let default_state = AppState {
            in_alt_screen: false,
            detected_app: None,
            mouse_forwarding: false,
            keyboard_mode: KeyboardMode::Normal,
            padding: AppPadding::default(),
        };

        if let Some(id) = pane_id {
            self.pane_states.insert(id.to_string(), default_state.clone());
        }
        self.state = default_state;
    }

    /// Check if currently in full-screen app
    pub fn in_fullscreen(&self) -> bool {
        self.state.in_alt_screen
    }

    /// Check if pane is in full-screen app
    pub fn pane_in_fullscreen(&self, pane_id: &str) -> bool {
        self.pane_states.get(pane_id).map(|s| s.in_alt_screen).unwrap_or(false)
    }

    /// Get current state
    pub fn state(&self) -> &AppState {
        &self.state
    }

    /// Get pane state
    pub fn pane_state(&self, pane_id: &str) -> Option<&AppState> {
        self.pane_states.get(pane_id)
    }

    /// Get detected app name
    pub fn detected_app(&self) -> Option<&str> {
        self.state.detected_app.as_deref()
    }

    /// Should forward mouse events
    pub fn should_forward_mouse(&self) -> bool {
        self.state.mouse_forwarding
    }

    /// Get keyboard mode
    pub fn keyboard_mode(&self) -> KeyboardMode {
        self.state.keyboard_mode
    }

    /// Add custom app
    pub fn add_app(&mut self, app: FullScreenApp) {
        for cmd in &app.commands {
            self.known_apps.insert(cmd.clone(), app.clone());
        }
    }

    /// Get known apps
    pub fn known_apps(&self) -> Vec<&FullScreenApp> {
        let mut seen = std::collections::HashSet::new();
        self.known_apps.values()
            .filter(|a| seen.insert(&a.name))
            .collect()
    }

    /// Update config
    pub fn set_config(&mut self, config: FullScreenConfig) {
        self.config = config;
    }

    /// Get config
    pub fn config(&self) -> &FullScreenConfig {
        &self.config
    }

    /// Process escape sequence to detect alt screen
    pub fn process_escape(&mut self, sequence: &str, pane_id: Option<&str>) {
        // CSI ?1049h = enter alternate screen
        // CSI ?1049l = leave alternate screen
        // CSI ?47h/l, CSI ?1047h/l also used

        if sequence.contains("?1049h") || sequence.contains("?47h") || sequence.contains("?1047h") {
            self.enter_alt_screen(pane_id, None);
        } else if sequence.contains("?1049l") || sequence.contains("?47l") || sequence.contains("?1047l") {
            self.leave_alt_screen(pane_id);
        }
    }
}

impl Default for FullScreenManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref FULLSCREEN_MANAGER: Arc<Mutex<FullScreenManager>> =
        Arc::new(Mutex::new(FullScreenManager::new()));
}

/// Get the global fullscreen manager
pub fn fullscreen() -> Arc<Mutex<FullScreenManager>> {
    FULLSCREEN_MANAGER.clone()
}

/// Check if in fullscreen app
pub fn in_fullscreen() -> bool {
    FULLSCREEN_MANAGER.lock().unwrap().in_fullscreen()
}

/// Enter alt screen
pub fn enter_alt_screen(pane_id: Option<&str>, command: Option<&str>) {
    FULLSCREEN_MANAGER.lock().unwrap().enter_alt_screen(pane_id, command);
}

/// Leave alt screen
pub fn leave_alt_screen(pane_id: Option<&str>) {
    FULLSCREEN_MANAGER.lock().unwrap().leave_alt_screen(pane_id);
}

/// Detect app from command
pub fn detect_app(command: &str) -> Option<String> {
    FULLSCREEN_MANAGER.lock().unwrap().detect_app(command).map(|a| a.name.clone())
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_vim() {
        let manager = FullScreenManager::new();

        let app = manager.detect_app("vim file.txt");
        assert!(app.is_some());
        assert_eq!(app.unwrap().name, "vim");

        let app = manager.detect_app("/usr/bin/vim file.txt");
        assert!(app.is_some());
    }

    #[test]
    fn test_detect_neovim() {
        let manager = FullScreenManager::new();
        let app = manager.detect_app("nvim .");
        assert!(app.is_some());
        assert_eq!(app.unwrap().name, "neovim");
    }

    #[test]
    fn test_detect_unknown() {
        let manager = FullScreenManager::new();
        let app = manager.detect_app("ls -la");
        assert!(app.is_none());
    }

    #[test]
    fn test_enter_alt_screen() {
        let mut manager = FullScreenManager::new();

        assert!(!manager.in_fullscreen());

        manager.enter_alt_screen(None, Some("vim file.txt"));
        assert!(manager.in_fullscreen());
        assert_eq!(manager.detected_app(), Some("vim"));
        assert_eq!(manager.keyboard_mode(), KeyboardMode::Vim);
    }

    #[test]
    fn test_leave_alt_screen() {
        let mut manager = FullScreenManager::new();

        manager.enter_alt_screen(None, Some("vim"));
        assert!(manager.in_fullscreen());

        manager.leave_alt_screen(None);
        assert!(!manager.in_fullscreen());
        assert!(manager.detected_app().is_none());
    }

    #[test]
    fn test_pane_state() {
        let mut manager = FullScreenManager::new();

        manager.enter_alt_screen(Some("pane1"), Some("vim"));
        manager.enter_alt_screen(Some("pane2"), Some("htop"));

        assert!(manager.pane_in_fullscreen("pane1"));
        assert!(manager.pane_in_fullscreen("pane2"));

        manager.leave_alt_screen(Some("pane1"));
        assert!(!manager.pane_in_fullscreen("pane1"));
        assert!(manager.pane_in_fullscreen("pane2"));
    }

    #[test]
    fn test_mouse_forwarding() {
        let mut manager = FullScreenManager::new();

        // vim handles mouse
        manager.enter_alt_screen(None, Some("vim"));
        assert!(manager.should_forward_mouse());

        manager.leave_alt_screen(None);

        // less doesn't handle mouse
        manager.enter_alt_screen(None, Some("less"));
        assert!(!manager.should_forward_mouse());
    }

    #[test]
    fn test_escape_sequence_detection() {
        let mut manager = FullScreenManager::new();

        manager.process_escape("\x1b[?1049h", None);
        assert!(manager.in_fullscreen());

        manager.process_escape("\x1b[?1049l", None);
        assert!(!manager.in_fullscreen());
    }
}
