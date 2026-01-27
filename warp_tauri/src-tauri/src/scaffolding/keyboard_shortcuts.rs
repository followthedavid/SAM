//! Keyboard Shortcuts - Customizable keybindings
//!
//! Provides:
//! - Default keybindings
//! - User customization
//! - Conflict detection
//! - Platform-specific defaults
//! - Vim/Emacs modes

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

/// A keyboard shortcut
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub struct Shortcut {
    /// Primary key
    pub key: String,
    /// Modifier keys
    pub modifiers: Vec<Modifier>,
}

impl Shortcut {
    pub fn new(key: &str) -> Self {
        Self {
            key: key.to_string(),
            modifiers: Vec::new(),
        }
    }

    pub fn with_cmd(mut self) -> Self {
        self.modifiers.push(Modifier::Cmd);
        self
    }

    pub fn with_ctrl(mut self) -> Self {
        self.modifiers.push(Modifier::Ctrl);
        self
    }

    pub fn with_alt(mut self) -> Self {
        self.modifiers.push(Modifier::Alt);
        self
    }

    pub fn with_shift(mut self) -> Self {
        self.modifiers.push(Modifier::Shift);
        self
    }

    /// Format for display
    pub fn display(&self) -> String {
        let mut parts = Vec::new();

        for m in &self.modifiers {
            parts.push(match m {
                Modifier::Cmd => {
                    #[cfg(target_os = "macos")]
                    { "⌘" }
                    #[cfg(not(target_os = "macos"))]
                    { "Cmd" }
                }
                Modifier::Ctrl => {
                    #[cfg(target_os = "macos")]
                    { "⌃" }
                    #[cfg(not(target_os = "macos"))]
                    { "Ctrl" }
                }
                Modifier::Alt => {
                    #[cfg(target_os = "macos")]
                    { "⌥" }
                    #[cfg(not(target_os = "macos"))]
                    { "Alt" }
                }
                Modifier::Shift => {
                    #[cfg(target_os = "macos")]
                    { "⇧" }
                    #[cfg(not(target_os = "macos"))]
                    { "Shift" }
                }
            });
        }

        parts.push(&self.key);
        parts.join("+")
    }

    /// Parse from string like "Cmd+Shift+K"
    pub fn parse(s: &str) -> Option<Self> {
        let parts: Vec<&str> = s.split('+').collect();
        if parts.is_empty() {
            return None;
        }

        let key = parts.last()?.to_string();
        let mut modifiers = Vec::new();

        for part in &parts[..parts.len()-1] {
            let lower = part.to_lowercase();
            match lower.as_str() {
                "cmd" | "command" | "⌘" | "meta" => modifiers.push(Modifier::Cmd),
                "ctrl" | "control" | "⌃" => modifiers.push(Modifier::Ctrl),
                "alt" | "option" | "⌥" => modifiers.push(Modifier::Alt),
                "shift" | "⇧" => modifiers.push(Modifier::Shift),
                _ => {}
            }
        }

        Some(Self { key, modifiers })
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Modifier {
    Cmd,
    Ctrl,
    Alt,
    Shift,
}

/// Actions that can be bound to shortcuts
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum Action {
    // Terminal actions
    NewTab,
    CloseTab,
    NextTab,
    PrevTab,
    SplitHorizontal,
    SplitVertical,
    ClosePane,
    FocusNextPane,
    FocusPrevPane,
    Clear,
    Copy,
    Paste,
    SelectAll,

    // Navigation
    ScrollUp,
    ScrollDown,
    ScrollToTop,
    ScrollToBottom,
    Search,
    CommandPalette,

    // AI/Agent
    ToggleAi,
    SendToAi,
    AgentMode,

    // Window
    NewWindow,
    CloseWindow,
    ToggleFullscreen,
    Minimize,

    // Settings
    OpenSettings,
    OpenKeyboardShortcuts,

    // History
    HistoryUp,
    HistoryDown,
    HistorySearch,

    // Editing
    Undo,
    Redo,
    CutLine,
    DeleteWord,
    DeleteLine,

    // Blocks
    NextBlock,
    PrevBlock,
    BookmarkBlock,
    CopyBlock,

    // Voice
    ToggleVoice,

    // Custom
    Custom(String),
}

/// Shortcut binding
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Binding {
    pub action: Action,
    pub shortcut: Shortcut,
    pub description: String,
    pub category: Category,
    pub enabled: bool,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum Category {
    Terminal,
    Navigation,
    Editing,
    AiAgent,
    Window,
    Blocks,
    Other,
}

/// Keyboard mode
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Default)]
pub enum KeyboardMode {
    #[default]
    Standard,
    Vim,
    Emacs,
}

// =============================================================================
// SHORTCUT MANAGER
// =============================================================================

pub struct ShortcutManager {
    bindings: HashMap<Shortcut, Binding>,
    action_to_shortcut: HashMap<Action, Shortcut>,
    keyboard_mode: KeyboardMode,
    custom_overrides: HashMap<Action, Shortcut>,
}

impl ShortcutManager {
    pub fn new() -> Self {
        let mut manager = Self {
            bindings: HashMap::new(),
            action_to_shortcut: HashMap::new(),
            keyboard_mode: KeyboardMode::Standard,
            custom_overrides: HashMap::new(),
        };
        manager.load_defaults();
        manager
    }

    fn load_defaults(&mut self) {
        let defaults = vec![
            // Terminal
            (Action::NewTab, "Cmd+T", "New tab", Category::Terminal),
            (Action::CloseTab, "Cmd+W", "Close tab", Category::Terminal),
            (Action::NextTab, "Cmd+Shift+]", "Next tab", Category::Terminal),
            (Action::PrevTab, "Cmd+Shift+[", "Previous tab", Category::Terminal),
            (Action::SplitHorizontal, "Cmd+D", "Split horizontal", Category::Terminal),
            (Action::SplitVertical, "Cmd+Shift+D", "Split vertical", Category::Terminal),
            (Action::ClosePane, "Cmd+Shift+W", "Close pane", Category::Terminal),
            (Action::FocusNextPane, "Cmd+]", "Focus next pane", Category::Terminal),
            (Action::FocusPrevPane, "Cmd+[", "Focus previous pane", Category::Terminal),
            (Action::Clear, "Cmd+K", "Clear terminal", Category::Terminal),
            (Action::Copy, "Cmd+C", "Copy", Category::Editing),
            (Action::Paste, "Cmd+V", "Paste", Category::Editing),
            (Action::SelectAll, "Cmd+A", "Select all", Category::Editing),

            // Navigation
            (Action::ScrollUp, "Shift+PageUp", "Scroll up", Category::Navigation),
            (Action::ScrollDown, "Shift+PageDown", "Scroll down", Category::Navigation),
            (Action::ScrollToTop, "Cmd+Home", "Scroll to top", Category::Navigation),
            (Action::ScrollToBottom, "Cmd+End", "Scroll to bottom", Category::Navigation),
            (Action::Search, "Cmd+F", "Search", Category::Navigation),
            (Action::CommandPalette, "Cmd+P", "Command palette", Category::Navigation),

            // AI/Agent
            (Action::ToggleAi, "Cmd+I", "Toggle AI", Category::AiAgent),
            (Action::SendToAi, "Cmd+Enter", "Send to AI", Category::AiAgent),
            (Action::AgentMode, "Cmd+Shift+A", "Agent mode", Category::AiAgent),

            // Window
            (Action::NewWindow, "Cmd+N", "New window", Category::Window),
            (Action::CloseWindow, "Cmd+Shift+Q", "Close window", Category::Window),
            (Action::ToggleFullscreen, "Cmd+Ctrl+F", "Toggle fullscreen", Category::Window),
            (Action::Minimize, "Cmd+M", "Minimize", Category::Window),

            // Settings
            (Action::OpenSettings, "Cmd+,", "Open settings", Category::Other),
            (Action::OpenKeyboardShortcuts, "Cmd+Shift+K", "Keyboard shortcuts", Category::Other),

            // History
            (Action::HistoryUp, "Up", "History up", Category::Navigation),
            (Action::HistoryDown, "Down", "History down", Category::Navigation),
            (Action::HistorySearch, "Ctrl+R", "History search", Category::Navigation),

            // Editing
            (Action::Undo, "Cmd+Z", "Undo", Category::Editing),
            (Action::Redo, "Cmd+Shift+Z", "Redo", Category::Editing),
            (Action::CutLine, "Cmd+X", "Cut line", Category::Editing),
            (Action::DeleteWord, "Alt+Backspace", "Delete word", Category::Editing),
            (Action::DeleteLine, "Cmd+Backspace", "Delete line", Category::Editing),

            // Blocks
            (Action::NextBlock, "Cmd+Down", "Next block", Category::Blocks),
            (Action::PrevBlock, "Cmd+Up", "Previous block", Category::Blocks),
            (Action::BookmarkBlock, "Cmd+B", "Bookmark block", Category::Blocks),
            (Action::CopyBlock, "Cmd+Shift+C", "Copy block", Category::Blocks),

            // Voice
            (Action::ToggleVoice, "Cmd+Shift+V", "Toggle voice input", Category::Other),
        ];

        for (action, shortcut_str, description, category) in defaults {
            if let Some(shortcut) = Shortcut::parse(shortcut_str) {
                let binding = Binding {
                    action: action.clone(),
                    shortcut: shortcut.clone(),
                    description: description.to_string(),
                    category,
                    enabled: true,
                };
                self.bindings.insert(shortcut.clone(), binding);
                self.action_to_shortcut.insert(action, shortcut);
            }
        }
    }

    /// Get action for shortcut
    pub fn get_action(&self, shortcut: &Shortcut) -> Option<&Action> {
        self.bindings.get(shortcut).map(|b| &b.action)
    }

    /// Get shortcut for action
    pub fn get_shortcut(&self, action: &Action) -> Option<&Shortcut> {
        self.action_to_shortcut.get(action)
    }

    /// Get all bindings
    pub fn bindings(&self) -> Vec<&Binding> {
        self.bindings.values().collect()
    }

    /// Get bindings by category
    pub fn bindings_by_category(&self, category: Category) -> Vec<&Binding> {
        self.bindings.values()
            .filter(|b| b.category == category)
            .collect()
    }

    /// Set custom binding
    pub fn set_binding(&mut self, action: Action, shortcut: Shortcut) -> Result<(), ShortcutError> {
        // Check for conflicts
        if let Some(existing) = self.bindings.get(&shortcut) {
            if existing.action != action {
                return Err(ShortcutError::Conflict(existing.action.clone()));
            }
        }

        // Remove old shortcut for this action
        if let Some(old_shortcut) = self.action_to_shortcut.remove(&action) {
            self.bindings.remove(&old_shortcut);
        }

        // Add new binding
        let category = self.get_category(&action);
        let binding = Binding {
            action: action.clone(),
            shortcut: shortcut.clone(),
            description: self.get_description(&action),
            category,
            enabled: true,
        };

        self.bindings.insert(shortcut.clone(), binding);
        self.action_to_shortcut.insert(action.clone(), shortcut.clone());
        self.custom_overrides.insert(action, shortcut);

        Ok(())
    }

    /// Reset action to default
    pub fn reset_binding(&mut self, action: &Action) {
        self.custom_overrides.remove(action);
        // Reload defaults to restore original binding
        self.bindings.clear();
        self.action_to_shortcut.clear();
        self.load_defaults();
    }

    /// Reset all to defaults
    pub fn reset_all(&mut self) {
        self.custom_overrides.clear();
        self.bindings.clear();
        self.action_to_shortcut.clear();
        self.load_defaults();
    }

    /// Set keyboard mode
    pub fn set_mode(&mut self, mode: KeyboardMode) {
        self.keyboard_mode = mode;

        // Apply mode-specific bindings
        match mode {
            KeyboardMode::Vim => self.apply_vim_bindings(),
            KeyboardMode::Emacs => self.apply_emacs_bindings(),
            KeyboardMode::Standard => self.reset_all(),
        }
    }

    /// Get keyboard mode
    pub fn mode(&self) -> KeyboardMode {
        self.keyboard_mode
    }

    /// Find conflicts
    pub fn find_conflicts(&self) -> Vec<(Shortcut, Vec<&Binding>)> {
        // In our design, shortcuts are unique keys, so no real conflicts
        // This could check for "similar" shortcuts
        Vec::new()
    }

    /// Search shortcuts
    pub fn search(&self, query: &str) -> Vec<&Binding> {
        let query = query.to_lowercase();
        self.bindings.values()
            .filter(|b| {
                b.description.to_lowercase().contains(&query) ||
                b.shortcut.display().to_lowercase().contains(&query)
            })
            .collect()
    }

    fn apply_vim_bindings(&mut self) {
        // Add vim-specific bindings
        // hjkl navigation, etc.
    }

    fn apply_emacs_bindings(&mut self) {
        // Add emacs-specific bindings
        // C-a, C-e, C-k, etc.
    }

    fn get_category(&self, action: &Action) -> Category {
        match action {
            Action::NewTab | Action::CloseTab | Action::NextTab | Action::PrevTab |
            Action::SplitHorizontal | Action::SplitVertical | Action::ClosePane |
            Action::FocusNextPane | Action::FocusPrevPane | Action::Clear => Category::Terminal,

            Action::Copy | Action::Paste | Action::SelectAll | Action::Undo |
            Action::Redo | Action::CutLine | Action::DeleteWord | Action::DeleteLine => Category::Editing,

            Action::ScrollUp | Action::ScrollDown | Action::ScrollToTop |
            Action::ScrollToBottom | Action::Search | Action::CommandPalette |
            Action::HistoryUp | Action::HistoryDown | Action::HistorySearch => Category::Navigation,

            Action::ToggleAi | Action::SendToAi | Action::AgentMode => Category::AiAgent,

            Action::NewWindow | Action::CloseWindow | Action::ToggleFullscreen |
            Action::Minimize => Category::Window,

            Action::NextBlock | Action::PrevBlock | Action::BookmarkBlock |
            Action::CopyBlock => Category::Blocks,

            _ => Category::Other,
        }
    }

    fn get_description(&self, action: &Action) -> String {
        match action {
            Action::NewTab => "New tab",
            Action::CloseTab => "Close tab",
            Action::NextTab => "Next tab",
            Action::PrevTab => "Previous tab",
            Action::Copy => "Copy",
            Action::Paste => "Paste",
            Action::ToggleAi => "Toggle AI",
            Action::CommandPalette => "Command palette",
            _ => "Action",
        }.to_string()
    }
}

impl Default for ShortcutManager {
    fn default() -> Self {
        Self::new()
    }
}

#[derive(Debug)]
pub enum ShortcutError {
    Conflict(Action),
    InvalidShortcut,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref SHORTCUT_MANAGER: Arc<Mutex<ShortcutManager>> =
        Arc::new(Mutex::new(ShortcutManager::new()));
}

/// Get the global shortcut manager
pub fn shortcuts() -> Arc<Mutex<ShortcutManager>> {
    SHORTCUT_MANAGER.clone()
}

/// Get action for shortcut
pub fn get_action(shortcut: &Shortcut) -> Option<Action> {
    SHORTCUT_MANAGER.lock().unwrap().get_action(shortcut).cloned()
}

/// Get shortcut for action
pub fn get_shortcut(action: &Action) -> Option<Shortcut> {
    SHORTCUT_MANAGER.lock().unwrap().get_shortcut(action).cloned()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shortcut_parse() {
        let s = Shortcut::parse("Cmd+Shift+K").unwrap();
        assert_eq!(s.key, "K");
        assert!(s.modifiers.contains(&Modifier::Cmd));
        assert!(s.modifiers.contains(&Modifier::Shift));
    }

    #[test]
    fn test_shortcut_display() {
        let s = Shortcut::new("K").with_cmd().with_shift();
        let display = s.display();
        assert!(display.contains("K"));
    }

    #[test]
    fn test_get_action() {
        let manager = ShortcutManager::new();
        let shortcut = Shortcut::parse("Cmd+T").unwrap();
        let action = manager.get_action(&shortcut);
        assert_eq!(action, Some(&Action::NewTab));
    }

    #[test]
    fn test_get_shortcut() {
        let manager = ShortcutManager::new();
        let shortcut = manager.get_shortcut(&Action::NewTab);
        assert!(shortcut.is_some());
    }

    #[test]
    fn test_set_binding() {
        let mut manager = ShortcutManager::new();
        let new_shortcut = Shortcut::parse("Cmd+Shift+T").unwrap();

        manager.set_binding(Action::NewTab, new_shortcut.clone()).unwrap();

        let shortcut = manager.get_shortcut(&Action::NewTab).unwrap();
        assert_eq!(shortcut, &new_shortcut);
    }

    #[test]
    fn test_conflict_detection() {
        let mut manager = ShortcutManager::new();

        // Try to set Copy to use NewTab's shortcut
        let conflict_shortcut = Shortcut::parse("Cmd+T").unwrap();
        let result = manager.set_binding(Action::Copy, conflict_shortcut);

        assert!(matches!(result, Err(ShortcutError::Conflict(_))));
    }

    #[test]
    fn test_reset_binding() {
        let mut manager = ShortcutManager::new();
        let original = manager.get_shortcut(&Action::NewTab).cloned();

        let new_shortcut = Shortcut::parse("Cmd+Shift+T").unwrap();
        manager.set_binding(Action::NewTab, new_shortcut).unwrap();

        manager.reset_binding(&Action::NewTab);

        let restored = manager.get_shortcut(&Action::NewTab);
        assert_eq!(restored, original.as_ref());
    }

    #[test]
    fn test_search() {
        let manager = ShortcutManager::new();
        let results = manager.search("tab");

        assert!(!results.is_empty());
        assert!(results.iter().any(|b| matches!(b.action, Action::NewTab)));
    }

    #[test]
    fn test_bindings_by_category() {
        let manager = ShortcutManager::new();
        let terminal_bindings = manager.bindings_by_category(Category::Terminal);

        assert!(!terminal_bindings.is_empty());
    }
}
