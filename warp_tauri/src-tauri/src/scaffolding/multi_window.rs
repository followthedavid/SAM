//! Multi-Window Support - Multiple terminal windows
//!
//! Provides support for:
//! - Creating multiple windows
//! - Window state persistence
//! - Cross-window communication
//! - Window layout management

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};

// =============================================================================
// TYPES
// =============================================================================

/// A terminal window
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Window {
    /// Unique window ID
    pub id: String,
    /// Window title
    pub title: String,
    /// Window position
    pub position: WindowPosition,
    /// Window size
    pub size: WindowSize,
    /// Whether window is focused
    pub focused: bool,
    /// Whether window is fullscreen
    pub fullscreen: bool,
    /// Whether window is minimized
    pub minimized: bool,
    /// Window state
    pub state: WindowState,
    /// Creation time
    pub created_at: DateTime<Utc>,
    /// Last focused time
    pub last_focused: DateTime<Utc>,
    /// Associated tab IDs
    pub tabs: Vec<String>,
    /// Active tab index
    pub active_tab: usize,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, Default)]
pub struct WindowPosition {
    pub x: i32,
    pub y: i32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize)]
pub struct WindowSize {
    pub width: u32,
    pub height: u32,
}

impl Default for WindowSize {
    fn default() -> Self {
        Self {
            width: 1200,
            height: 800,
        }
    }
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum WindowState {
    Normal,
    Maximized,
    Minimized,
    Fullscreen,
    Hidden,
}

/// Window creation options
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct WindowOptions {
    pub title: Option<String>,
    pub position: Option<WindowPosition>,
    pub size: Option<WindowSize>,
    pub fullscreen: bool,
    pub transparent: bool,
    pub decorations: bool,
    pub always_on_top: bool,
}

/// Layout configuration that can be saved/restored
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SavedLayout {
    pub name: String,
    pub windows: Vec<WindowLayout>,
    pub created_at: DateTime<Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WindowLayout {
    pub position: WindowPosition,
    pub size: WindowSize,
    pub state: WindowState,
    pub tabs: usize,
}

// =============================================================================
// WINDOW MANAGER
// =============================================================================

pub struct WindowManager {
    windows: HashMap<String, Window>,
    active_window: Option<String>,
    saved_layouts: Vec<SavedLayout>,
    event_handlers: Vec<Box<dyn Fn(&Window, WindowEvent) + Send + Sync>>,
    next_window_num: u32,
}

#[derive(Debug, Clone, Copy)]
pub enum WindowEvent {
    Created,
    Closed,
    Focused,
    Unfocused,
    Moved,
    Resized,
    StateChanged,
}

impl WindowManager {
    pub fn new() -> Self {
        Self {
            windows: HashMap::new(),
            active_window: None,
            saved_layouts: Vec::new(),
            event_handlers: Vec::new(),
            next_window_num: 1,
        }
    }

    /// Create a new window
    pub fn create_window(&mut self, options: WindowOptions) -> Window {
        let id = format!("win_{}", uuid::Uuid::new_v4().to_string()[..8].to_string());
        let title = options.title.unwrap_or_else(|| format!("Terminal {}", self.next_window_num));
        self.next_window_num += 1;

        let now = Utc::now();
        let window = Window {
            id: id.clone(),
            title,
            position: options.position.unwrap_or_default(),
            size: options.size.unwrap_or_default(),
            focused: true,
            fullscreen: options.fullscreen,
            minimized: false,
            state: if options.fullscreen { WindowState::Fullscreen } else { WindowState::Normal },
            created_at: now,
            last_focused: now,
            tabs: Vec::new(),
            active_tab: 0,
        };

        // Unfocus previous active window
        if let Some(ref prev_id) = self.active_window {
            if let Some(prev) = self.windows.get_mut(prev_id) {
                prev.focused = false;
            }
        }

        self.windows.insert(id.clone(), window.clone());
        self.active_window = Some(id);
        self.emit_event(&window, WindowEvent::Created);

        window
    }

    /// Close a window
    pub fn close_window(&mut self, id: &str) -> bool {
        if let Some(window) = self.windows.remove(id) {
            self.emit_event(&window, WindowEvent::Closed);

            // Update active window if needed
            if self.active_window.as_deref() == Some(id) {
                self.active_window = self.windows.keys().next().cloned();
                if let Some(ref new_active) = self.active_window {
                    if let Some(w) = self.windows.get_mut(new_active) {
                        w.focused = true;
                        w.last_focused = Utc::now();
                    }
                }
            }

            true
        } else {
            false
        }
    }

    /// Focus a window
    pub fn focus_window(&mut self, id: &str) -> bool {
        // Unfocus current
        if let Some(ref current) = self.active_window {
            if current != id {
                if let Some(w) = self.windows.get_mut(current) {
                    w.focused = false;
                    let wc = w.clone();
                    self.emit_event(&wc, WindowEvent::Unfocused);
                }
            }
        }

        // Focus new
        if let Some(window) = self.windows.get_mut(id) {
            window.focused = true;
            window.last_focused = Utc::now();
            if window.minimized {
                window.minimized = false;
                window.state = WindowState::Normal;
            }
            let wc = window.clone();
            self.active_window = Some(id.to_string());
            self.emit_event(&wc, WindowEvent::Focused);
            true
        } else {
            false
        }
    }

    /// Get active window
    pub fn active_window(&self) -> Option<&Window> {
        self.active_window.as_ref().and_then(|id| self.windows.get(id))
    }

    /// Get window by ID
    pub fn get(&self, id: &str) -> Option<&Window> {
        self.windows.get(id)
    }

    /// Get mutable window by ID
    pub fn get_mut(&mut self, id: &str) -> Option<&mut Window> {
        self.windows.get_mut(id)
    }

    /// Get all windows
    pub fn all(&self) -> Vec<&Window> {
        self.windows.values().collect()
    }

    /// Get window count
    pub fn count(&self) -> usize {
        self.windows.len()
    }

    /// Move window
    pub fn move_window(&mut self, id: &str, position: WindowPosition) {
        if let Some(window) = self.windows.get_mut(id) {
            window.position = position;
            let wc = window.clone();
            self.emit_event(&wc, WindowEvent::Moved);
        }
    }

    /// Resize window
    pub fn resize_window(&mut self, id: &str, size: WindowSize) {
        if let Some(window) = self.windows.get_mut(id) {
            window.size = size;
            let wc = window.clone();
            self.emit_event(&wc, WindowEvent::Resized);
        }
    }

    /// Set window state
    pub fn set_state(&mut self, id: &str, state: WindowState) {
        if let Some(window) = self.windows.get_mut(id) {
            window.state = state;
            window.minimized = state == WindowState::Minimized;
            window.fullscreen = state == WindowState::Fullscreen;
            let wc = window.clone();
            self.emit_event(&wc, WindowEvent::StateChanged);
        }
    }

    /// Toggle fullscreen
    pub fn toggle_fullscreen(&mut self, id: &str) -> bool {
        let result = if let Some(window) = self.windows.get_mut(id) {
            window.fullscreen = !window.fullscreen;
            window.state = if window.fullscreen {
                WindowState::Fullscreen
            } else {
                WindowState::Normal
            };
            Some((window.clone(), window.fullscreen))
        } else {
            None
        };

        if let Some((wc, is_fullscreen)) = result {
            self.emit_event(&wc, WindowEvent::StateChanged);
            return is_fullscreen;
        }
        false
    }

    /// Minimize window
    pub fn minimize(&mut self, id: &str) {
        self.set_state(id, WindowState::Minimized);
    }

    /// Maximize window
    pub fn maximize(&mut self, id: &str) {
        self.set_state(id, WindowState::Maximized);
    }

    /// Cycle through windows
    pub fn cycle_windows(&mut self) -> Option<&Window> {
        let ids: Vec<_> = self.windows.keys().cloned().collect();
        if ids.is_empty() {
            return None;
        }

        let current_idx = self.active_window
            .as_ref()
            .and_then(|id| ids.iter().position(|i| i == id))
            .unwrap_or(0);

        let next_idx = (current_idx + 1) % ids.len();
        self.focus_window(&ids[next_idx]);
        self.active_window()
    }

    /// Save current layout
    pub fn save_layout(&mut self, name: &str) -> SavedLayout {
        let windows: Vec<WindowLayout> = self.windows.values()
            .map(|w| WindowLayout {
                position: w.position,
                size: w.size,
                state: w.state,
                tabs: w.tabs.len().max(1),
            })
            .collect();

        let layout = SavedLayout {
            name: name.to_string(),
            windows,
            created_at: Utc::now(),
        };

        self.saved_layouts.push(layout.clone());
        layout
    }

    /// Restore a saved layout
    pub fn restore_layout(&mut self, name: &str) -> bool {
        let layout = match self.saved_layouts.iter().find(|l| l.name == name) {
            Some(l) => l.clone(),
            None => return false,
        };

        // Close all current windows
        let ids: Vec<_> = self.windows.keys().cloned().collect();
        for id in ids {
            self.close_window(&id);
        }

        // Create new windows from layout
        for wl in &layout.windows {
            self.create_window(WindowOptions {
                position: Some(wl.position),
                size: Some(wl.size),
                fullscreen: wl.state == WindowState::Fullscreen,
                ..Default::default()
            });
        }

        true
    }

    /// Get saved layouts
    pub fn saved_layouts(&self) -> &[SavedLayout] {
        &self.saved_layouts
    }

    /// Delete saved layout
    pub fn delete_layout(&mut self, name: &str) -> bool {
        if let Some(idx) = self.saved_layouts.iter().position(|l| l.name == name) {
            self.saved_layouts.remove(idx);
            true
        } else {
            false
        }
    }

    /// Register event handler
    pub fn on_window_event<F>(&mut self, handler: F)
    where
        F: Fn(&Window, WindowEvent) + Send + Sync + 'static,
    {
        self.event_handlers.push(Box::new(handler));
    }

    fn emit_event(&self, window: &Window, event: WindowEvent) {
        for handler in &self.event_handlers {
            handler(window, event);
        }
    }
}

impl Default for WindowManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref WINDOW_MANAGER: Arc<Mutex<WindowManager>> =
        Arc::new(Mutex::new(WindowManager::new()));
}

/// Get the global window manager
pub fn windows() -> Arc<Mutex<WindowManager>> {
    WINDOW_MANAGER.clone()
}

/// Create a new window
pub fn create_window(options: WindowOptions) -> Window {
    WINDOW_MANAGER.lock().unwrap().create_window(options)
}

/// Close a window
pub fn close_window(id: &str) -> bool {
    WINDOW_MANAGER.lock().unwrap().close_window(id)
}

/// Focus a window
pub fn focus_window(id: &str) -> bool {
    WINDOW_MANAGER.lock().unwrap().focus_window(id)
}

/// Get window count
pub fn window_count() -> usize {
    WINDOW_MANAGER.lock().unwrap().count()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_window() {
        let mut manager = WindowManager::new();
        let window = manager.create_window(WindowOptions::default());

        assert!(!window.id.is_empty());
        assert!(manager.active_window().is_some());
        assert_eq!(manager.count(), 1);
    }

    #[test]
    fn test_close_window() {
        let mut manager = WindowManager::new();
        let window = manager.create_window(WindowOptions::default());

        assert!(manager.close_window(&window.id));
        assert_eq!(manager.count(), 0);
    }

    #[test]
    fn test_focus_window() {
        let mut manager = WindowManager::new();
        let w1 = manager.create_window(WindowOptions::default());
        let w2 = manager.create_window(WindowOptions::default());

        // w2 should be active
        assert_eq!(manager.active_window().unwrap().id, w2.id);

        // Focus w1
        manager.focus_window(&w1.id);
        assert_eq!(manager.active_window().unwrap().id, w1.id);
    }

    #[test]
    fn test_cycle_windows() {
        let mut manager = WindowManager::new();
        manager.create_window(WindowOptions::default());
        manager.create_window(WindowOptions::default());
        manager.create_window(WindowOptions::default());

        let initial = manager.active_window().unwrap().id.clone();
        manager.cycle_windows();
        let after_cycle = manager.active_window().unwrap().id.clone();

        assert_ne!(initial, after_cycle);
    }

    #[test]
    fn test_save_restore_layout() {
        let mut manager = WindowManager::new();
        manager.create_window(WindowOptions {
            size: Some(WindowSize { width: 800, height: 600 }),
            ..Default::default()
        });
        manager.create_window(WindowOptions {
            size: Some(WindowSize { width: 1000, height: 700 }),
            ..Default::default()
        });

        manager.save_layout("test_layout");
        assert_eq!(manager.saved_layouts().len(), 1);

        manager.restore_layout("test_layout");
        assert_eq!(manager.count(), 2);
    }

    #[test]
    fn test_toggle_fullscreen() {
        let mut manager = WindowManager::new();
        let window = manager.create_window(WindowOptions::default());

        assert!(!window.fullscreen);

        let fs = manager.toggle_fullscreen(&window.id);
        assert!(fs);

        let fs = manager.toggle_fullscreen(&window.id);
        assert!(!fs);
    }

    #[test]
    fn test_move_resize() {
        let mut manager = WindowManager::new();
        let window = manager.create_window(WindowOptions::default());

        manager.move_window(&window.id, WindowPosition { x: 100, y: 200 });
        manager.resize_window(&window.id, WindowSize { width: 500, height: 400 });

        let w = manager.get(&window.id).unwrap();
        assert_eq!(w.position.x, 100);
        assert_eq!(w.size.width, 500);
    }
}
