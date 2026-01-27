// Pane Manager - Split Pane Terminal Management
//
// Manages multiple terminal panes with layouts.
// Warp/iTerm2 style split panes with tab colors and naming.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// =============================================================================
// TAB COLORS
// =============================================================================

/// Preset tab colors (Warp-style)
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum TabColorPreset {
    Default,
    Red,
    Orange,
    Yellow,
    Green,
    Cyan,
    Blue,
    Purple,
    Pink,
    Gray,
}

impl TabColorPreset {
    /// Get RGB values for preset
    pub fn rgb(&self) -> (u8, u8, u8) {
        match self {
            TabColorPreset::Default => (128, 128, 128),
            TabColorPreset::Red => (239, 68, 68),
            TabColorPreset::Orange => (249, 115, 22),
            TabColorPreset::Yellow => (234, 179, 8),
            TabColorPreset::Green => (34, 197, 94),
            TabColorPreset::Cyan => (6, 182, 212),
            TabColorPreset::Blue => (59, 130, 246),
            TabColorPreset::Purple => (168, 85, 247),
            TabColorPreset::Pink => (236, 72, 153),
            TabColorPreset::Gray => (107, 114, 128),
        }
    }

    /// Get all presets
    pub fn all() -> Vec<TabColorPreset> {
        vec![
            TabColorPreset::Default,
            TabColorPreset::Red,
            TabColorPreset::Orange,
            TabColorPreset::Yellow,
            TabColorPreset::Green,
            TabColorPreset::Cyan,
            TabColorPreset::Blue,
            TabColorPreset::Purple,
            TabColorPreset::Pink,
            TabColorPreset::Gray,
        ]
    }
}

/// Tab color - preset or custom RGB
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TabColor {
    Preset(TabColorPreset),
    Custom { r: u8, g: u8, b: u8 },
}

impl Default for TabColor {
    fn default() -> Self {
        TabColor::Preset(TabColorPreset::Default)
    }
}

impl TabColor {
    /// Get RGB values
    pub fn rgb(&self) -> (u8, u8, u8) {
        match self {
            TabColor::Preset(p) => p.rgb(),
            TabColor::Custom { r, g, b } => (*r, *g, *b),
        }
    }

    /// Create from hex string (e.g., "#FF5733")
    pub fn from_hex(hex: &str) -> Option<Self> {
        let hex = hex.trim_start_matches('#');
        if hex.len() != 6 {
            return None;
        }
        let r = u8::from_str_radix(&hex[0..2], 16).ok()?;
        let g = u8::from_str_radix(&hex[2..4], 16).ok()?;
        let b = u8::from_str_radix(&hex[4..6], 16).ok()?;
        Some(TabColor::Custom { r, g, b })
    }

    /// Convert to hex string
    pub fn to_hex(&self) -> String {
        let (r, g, b) = self.rgb();
        format!("#{:02X}{:02X}{:02X}", r, g, b)
    }
}

/// Tab icon (optional)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum TabIcon {
    /// Emoji icon
    Emoji(String),
    /// Named icon (for icon fonts)
    Named(String),
    /// No icon
    None,
}

impl Default for TabIcon {
    fn default() -> Self {
        TabIcon::None
    }
}

// =============================================================================
// DIRECTORY COLOR RULES
// =============================================================================

/// Rule for auto-assigning tab colors based on directory
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DirectoryColorRule {
    /// Path pattern (supports glob-like matching)
    pub pattern: String,
    /// Color to assign
    pub color: TabColor,
    /// Optional icon
    pub icon: Option<TabIcon>,
}

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Pane {
    pub id: String,
    pub pty_id: Option<String>,  // Associated PTY ID
    pub title: Option<String>,
    pub cwd: String,
    pub active: bool,
    pub created_at: i64,
    /// Running process name
    pub process: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaneLayout {
    pub root: LayoutNode,
    pub active_pane: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LayoutNode {
    Pane(String),  // Pane ID
    Split {
        direction: SplitDirection,
        ratio: f32,  // 0.0 to 1.0 - position of split
        first: Box<LayoutNode>,
        second: Box<LayoutNode>,
    },
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum SplitDirection {
    Horizontal,  // Side by side
    Vertical,    // Top and bottom
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tab {
    pub id: String,
    /// Custom name (if set)
    pub name: Option<String>,
    /// Tab color
    pub color: TabColor,
    /// Tab icon
    pub icon: TabIcon,
    /// Whether tab is pinned (stays at start, can't be closed accidentally)
    pub pinned: bool,
    /// Auto-name based on process/directory
    pub auto_name: bool,
    /// Layout
    pub layout: PaneLayout,
    pub created_at: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PaneSize {
    pub cols: u16,
    pub rows: u16,
}

// =============================================================================
// PANE MANAGER
// =============================================================================

pub struct PaneManager {
    tabs: Vec<Tab>,
    panes: HashMap<String, Pane>,
    active_tab: usize,
    /// Directory-based color rules
    directory_rules: Vec<DirectoryColorRule>,
    /// Default color for new tabs
    default_color: TabColor,
}

impl PaneManager {
    pub fn new() -> Self {
        let mut manager = Self {
            tabs: Vec::new(),
            panes: HashMap::new(),
            active_tab: 0,
            directory_rules: Self::default_directory_rules(),
            default_color: TabColor::default(),
        };

        // Create initial tab with single pane
        manager.new_tab(None);
        manager
    }

    /// Default directory color rules
    fn default_directory_rules() -> Vec<DirectoryColorRule> {
        vec![
            DirectoryColorRule {
                pattern: "*/Projects/*".to_string(),
                color: TabColor::Preset(TabColorPreset::Blue),
                icon: Some(TabIcon::Emoji("📁".to_string())),
            },
            DirectoryColorRule {
                pattern: "*/.git".to_string(),
                color: TabColor::Preset(TabColorPreset::Orange),
                icon: Some(TabIcon::Emoji("🔀".to_string())),
            },
            DirectoryColorRule {
                pattern: "*/node_modules/*".to_string(),
                color: TabColor::Preset(TabColorPreset::Green),
                icon: Some(TabIcon::Emoji("📦".to_string())),
            },
            DirectoryColorRule {
                pattern: "*/.config/*".to_string(),
                color: TabColor::Preset(TabColorPreset::Purple),
                icon: Some(TabIcon::Emoji("⚙️".to_string())),
            },
            DirectoryColorRule {
                pattern: "*/Documents/*".to_string(),
                color: TabColor::Preset(TabColorPreset::Cyan),
                icon: Some(TabIcon::Emoji("📄".to_string())),
            },
            DirectoryColorRule {
                pattern: "*/Downloads/*".to_string(),
                color: TabColor::Preset(TabColorPreset::Yellow),
                icon: Some(TabIcon::Emoji("⬇️".to_string())),
            },
        ]
    }

    // ==========================================================================
    // Tab Operations
    // ==========================================================================

    // Create new tab
    pub fn new_tab(&mut self, name: Option<&str>) -> &Tab {
        let pane = self.create_pane();
        let pane_id = pane.id.clone();
        let cwd = pane.cwd.clone();

        // Determine color based on directory rules
        let (color, icon) = self.color_for_directory(&cwd);

        let tab = Tab {
            id: format!("tab_{}", chrono::Utc::now().timestamp_millis()),
            name: name.map(|s| s.to_string()),
            color,
            icon: icon.unwrap_or_default(),
            pinned: false,
            auto_name: name.is_none(), // Auto-name if no explicit name
            layout: PaneLayout {
                root: LayoutNode::Pane(pane_id.clone()),
                active_pane: Some(pane_id),
            },
            created_at: chrono::Utc::now().timestamp(),
        };

        self.tabs.push(tab);
        self.active_tab = self.tabs.len() - 1;

        &self.tabs[self.active_tab]
    }

    /// Create a new tab with specific color
    pub fn new_tab_with_color(&mut self, name: Option<&str>, color: TabColor) -> &Tab {
        let pane = self.create_pane();
        let pane_id = pane.id.clone();

        let tab = Tab {
            id: format!("tab_{}", chrono::Utc::now().timestamp_millis()),
            name: name.map(|s| s.to_string()),
            color,
            icon: TabIcon::None,
            pinned: false,
            auto_name: name.is_none(),
            layout: PaneLayout {
                root: LayoutNode::Pane(pane_id.clone()),
                active_pane: Some(pane_id),
            },
            created_at: chrono::Utc::now().timestamp(),
        };

        self.tabs.push(tab);
        self.active_tab = self.tabs.len() - 1;

        &self.tabs[self.active_tab]
    }

    // Close tab
    pub fn close_tab(&mut self, tab_id: &str) -> bool {
        if let Some(idx) = self.tabs.iter().position(|t| t.id == tab_id) {
            // Collect pane IDs to remove
            let pane_ids = Self::collect_pane_ids(&self.tabs[idx].layout.root);

            // Remove panes
            for id in pane_ids {
                self.panes.remove(&id);
            }

            // Remove tab
            self.tabs.remove(idx);

            // Adjust active tab
            if self.tabs.is_empty() {
                self.new_tab(None);
            } else if self.active_tab >= self.tabs.len() {
                self.active_tab = self.tabs.len() - 1;
            }

            true
        } else {
            false
        }
    }

    // Switch to tab
    pub fn switch_tab(&mut self, index: usize) -> Option<&Tab> {
        if index < self.tabs.len() {
            self.active_tab = index;
            Some(&self.tabs[self.active_tab])
        } else {
            None
        }
    }

    // Next tab
    pub fn next_tab(&mut self) -> &Tab {
        self.active_tab = (self.active_tab + 1) % self.tabs.len();
        &self.tabs[self.active_tab]
    }

    // Previous tab
    pub fn prev_tab(&mut self) -> &Tab {
        self.active_tab = if self.active_tab == 0 {
            self.tabs.len() - 1
        } else {
            self.active_tab - 1
        };
        &self.tabs[self.active_tab]
    }

    // Rename tab
    pub fn rename_tab(&mut self, tab_id: &str, name: &str) -> bool {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
            tab.name = Some(name.to_string());
            tab.auto_name = false; // Disable auto-naming when explicitly renamed
            true
        } else {
            false
        }
    }

    // ==========================================================================
    // Tab Color and Appearance
    // ==========================================================================

    /// Set tab color
    pub fn set_tab_color(&mut self, tab_id: &str, color: TabColor) -> bool {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
            tab.color = color;
            true
        } else {
            false
        }
    }

    /// Set tab color by preset
    pub fn set_tab_color_preset(&mut self, tab_id: &str, preset: TabColorPreset) -> bool {
        self.set_tab_color(tab_id, TabColor::Preset(preset))
    }

    /// Set tab color by hex
    pub fn set_tab_color_hex(&mut self, tab_id: &str, hex: &str) -> bool {
        if let Some(color) = TabColor::from_hex(hex) {
            self.set_tab_color(tab_id, color)
        } else {
            false
        }
    }

    /// Set tab icon
    pub fn set_tab_icon(&mut self, tab_id: &str, icon: TabIcon) -> bool {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
            tab.icon = icon;
            true
        } else {
            false
        }
    }

    /// Set tab icon by emoji
    pub fn set_tab_emoji(&mut self, tab_id: &str, emoji: &str) -> bool {
        self.set_tab_icon(tab_id, TabIcon::Emoji(emoji.to_string()))
    }

    /// Toggle tab pinned status
    pub fn toggle_pin(&mut self, tab_id: &str) -> Option<bool> {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
            tab.pinned = !tab.pinned;
            Some(tab.pinned)
        } else {
            None
        }
    }

    /// Pin tab
    pub fn pin_tab(&mut self, tab_id: &str) -> bool {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
            tab.pinned = true;
            // Move pinned tabs to the beginning
            self.sort_tabs_by_pinned();
            true
        } else {
            false
        }
    }

    /// Unpin tab
    pub fn unpin_tab(&mut self, tab_id: &str) -> bool {
        if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
            tab.pinned = false;
            true
        } else {
            false
        }
    }

    /// Sort tabs so pinned ones are at the beginning
    fn sort_tabs_by_pinned(&mut self) {
        // Get current active tab ID
        let active_id = self.tabs.get(self.active_tab).map(|t| t.id.clone());

        // Stable sort: pinned tabs first
        self.tabs.sort_by(|a, b| b.pinned.cmp(&a.pinned));

        // Restore active tab index
        if let Some(id) = active_id {
            if let Some(new_idx) = self.tabs.iter().position(|t| t.id == id) {
                self.active_tab = new_idx;
            }
        }
    }

    /// Get color for a directory based on rules
    fn color_for_directory(&self, path: &str) -> (TabColor, Option<TabIcon>) {
        for rule in &self.directory_rules {
            if Self::matches_pattern(path, &rule.pattern) {
                return (rule.color.clone(), rule.icon.clone());
            }
        }
        (self.default_color.clone(), None)
    }

    /// Simple glob-like pattern matching
    fn matches_pattern(path: &str, pattern: &str) -> bool {
        // Simple * matching
        if pattern == "*" {
            return true;
        }

        let parts: Vec<&str> = pattern.split('*').collect();
        if parts.len() == 1 {
            return path == pattern;
        }

        let mut pos = 0;
        for (i, part) in parts.iter().enumerate() {
            if part.is_empty() {
                continue;
            }
            if let Some(found) = path[pos..].find(part) {
                if i == 0 && found != 0 {
                    return false; // First part must match at start
                }
                pos += found + part.len();
            } else {
                return false;
            }
        }

        // Last part must match at end if pattern doesn't end with *
        if !pattern.ends_with('*') {
            if let Some(last) = parts.last() {
                if !last.is_empty() && !path.ends_with(last) {
                    return false;
                }
            }
        }

        true
    }

    /// Add a directory color rule
    pub fn add_directory_rule(&mut self, pattern: &str, color: TabColor, icon: Option<TabIcon>) {
        self.directory_rules.push(DirectoryColorRule {
            pattern: pattern.to_string(),
            color,
            icon,
        });
    }

    /// Remove a directory color rule
    pub fn remove_directory_rule(&mut self, pattern: &str) -> bool {
        let original_len = self.directory_rules.len();
        self.directory_rules.retain(|r| r.pattern != pattern);
        self.directory_rules.len() < original_len
    }

    /// Get all directory rules
    pub fn directory_rules(&self) -> &[DirectoryColorRule] {
        &self.directory_rules
    }

    /// Set default tab color
    pub fn set_default_color(&mut self, color: TabColor) {
        self.default_color = color;
    }

    /// Update tab appearance based on active pane's directory
    pub fn update_tab_from_directory(&mut self, tab_id: &str) -> bool {
        // First collect the info we need
        let tab_info = self.tabs.iter().find(|t| t.id == tab_id).and_then(|tab| {
            if !tab.auto_name {
                return None;
            }
            tab.layout.active_pane.as_ref().and_then(|pane_id| {
                self.panes.get(pane_id).map(|pane| pane.cwd.clone())
            })
        });

        if let Some(cwd) = tab_info {
            let (color, icon) = self.color_for_directory(&cwd);
            let dir_name = std::path::Path::new(&cwd)
                .file_name()
                .map(|n| n.to_string_lossy().to_string());

            if let Some(tab) = self.tabs.iter_mut().find(|t| t.id == tab_id) {
                tab.color = color;
                if let Some(i) = icon {
                    tab.icon = i;
                }
                // Auto-set name to directory name if auto_name is enabled
                if tab.auto_name && tab.name.is_none() {
                    tab.name = dir_name;
                }
                return true;
            }
        }
        false
    }

    /// Get display name for a tab (auto-generated if not set)
    pub fn get_tab_display_name(&self, tab_id: &str) -> Option<String> {
        let tab = self.tabs.iter().find(|t| t.id == tab_id)?;

        // If explicit name is set, use it
        if let Some(ref name) = tab.name {
            return Some(name.clone());
        }

        // Try to get name from active pane's process or directory
        if let Some(pane_id) = &tab.layout.active_pane {
            if let Some(pane) = self.panes.get(pane_id) {
                // Prefer process name
                if let Some(ref process) = pane.process {
                    return Some(process.clone());
                }
                // Fall back to directory name
                return std::path::Path::new(&pane.cwd)
                    .file_name()
                    .map(|n| n.to_string_lossy().to_string());
            }
        }

        // Default to tab index
        self.tabs.iter().position(|t| t.id == tab_id)
            .map(|i| format!("Tab {}", i + 1))
    }

    /// Set pane's running process
    pub fn set_pane_process(&mut self, pane_id: &str, process: Option<&str>) -> bool {
        if let Some(pane) = self.panes.get_mut(pane_id) {
            pane.process = process.map(|s| s.to_string());
            true
        } else {
            false
        }
    }

    // Get active tab
    pub fn active_tab(&self) -> Option<&Tab> {
        self.tabs.get(self.active_tab)
    }

    // List tabs
    pub fn list_tabs(&self) -> &[Tab] {
        &self.tabs
    }

    // ==========================================================================
    // Pane Operations
    // ==========================================================================

    // Create a new pane
    fn create_pane(&mut self) -> Pane {
        let pane = Pane {
            id: format!("pane_{}_{}", chrono::Utc::now().timestamp_millis(), uuid::Uuid::new_v4().to_string().split('-').next().unwrap_or("0")),
            pty_id: None,
            title: None,
            cwd: std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| ".".to_string()),
            active: true,
            created_at: chrono::Utc::now().timestamp(),
            process: None,
        };

        self.panes.insert(pane.id.clone(), pane.clone());
        pane
    }

    // Split current pane
    pub fn split(&mut self, direction: SplitDirection, ratio: f32) -> Option<String> {
        // First, get the active pane ID and current layout
        let (active_pane_id, current_root) = {
            let tab = self.tabs.get(self.active_tab)?;
            (tab.layout.active_pane.clone()?, tab.layout.root.clone())
        };

        // Create new pane (needs mutable borrow of self)
        let new_pane = self.create_pane();
        let new_pane_id = new_pane.id.clone();

        // Now update the tab layout
        if let Some(tab) = self.tabs.get_mut(self.active_tab) {
            tab.layout.root = Self::split_node(
                current_root,
                &active_pane_id,
                &new_pane_id,
                direction,
                ratio,
            );
            tab.layout.active_pane = Some(new_pane_id.clone());
        }

        Some(new_pane_id)
    }

    fn split_node(
        node: LayoutNode,
        target_id: &str,
        new_id: &str,
        direction: SplitDirection,
        ratio: f32,
    ) -> LayoutNode {
        match node {
            LayoutNode::Pane(id) if id == target_id => {
                LayoutNode::Split {
                    direction,
                    ratio,
                    first: Box::new(LayoutNode::Pane(id)),
                    second: Box::new(LayoutNode::Pane(new_id.to_string())),
                }
            }
            LayoutNode::Split { direction: d, ratio: r, first, second } => {
                LayoutNode::Split {
                    direction: d,
                    ratio: r,
                    first: Box::new(Self::split_node(*first, target_id, new_id, direction, ratio)),
                    second: Box::new(Self::split_node(*second, target_id, new_id, direction, ratio)),
                }
            }
            other => other,
        }
    }

    // Close pane
    pub fn close_pane(&mut self, pane_id: &str) -> bool {
        let tab = match self.tabs.get_mut(self.active_tab) {
            Some(t) => t,
            None => return false,
        };

        // Don't close if it's the last pane
        if matches!(&tab.layout.root, LayoutNode::Pane(_)) {
            return false;
        }

        // Find sibling pane
        let sibling_id = Self::find_sibling(&tab.layout.root, pane_id);

        // Remove pane from layout
        tab.layout.root = Self::remove_node(tab.layout.root.clone(), pane_id);

        // Set sibling as active
        if tab.layout.active_pane.as_deref() == Some(pane_id) {
            tab.layout.active_pane = sibling_id;
        }

        // Remove from panes map
        self.panes.remove(pane_id);

        true
    }

    fn find_sibling(node: &LayoutNode, target_id: &str) -> Option<String> {
        match node {
            LayoutNode::Split { first, second, .. } => {
                if matches!(first.as_ref(), LayoutNode::Pane(id) if id == target_id) {
                    Self::first_pane_id(second)
                } else if matches!(second.as_ref(), LayoutNode::Pane(id) if id == target_id) {
                    Self::first_pane_id(first)
                } else {
                    Self::find_sibling(first, target_id)
                        .or_else(|| Self::find_sibling(second, target_id))
                }
            }
            _ => None,
        }
    }

    fn first_pane_id(node: &LayoutNode) -> Option<String> {
        match node {
            LayoutNode::Pane(id) => Some(id.clone()),
            LayoutNode::Split { first, .. } => Self::first_pane_id(first),
        }
    }

    fn remove_node(node: LayoutNode, target_id: &str) -> LayoutNode {
        match node {
            LayoutNode::Split { first, second, direction, ratio } => {
                // If first is the target, return second
                if matches!(first.as_ref(), LayoutNode::Pane(id) if id == target_id) {
                    return *second;
                }
                // If second is the target, return first
                if matches!(second.as_ref(), LayoutNode::Pane(id) if id == target_id) {
                    return *first;
                }
                // Recurse
                LayoutNode::Split {
                    direction,
                    ratio,
                    first: Box::new(Self::remove_node(*first, target_id)),
                    second: Box::new(Self::remove_node(*second, target_id)),
                }
            }
            other => other,
        }
    }

    // Focus pane
    pub fn focus_pane(&mut self, pane_id: &str) -> bool {
        // Update active status in panes
        for pane in self.panes.values_mut() {
            pane.active = pane.id == pane_id;
        }

        // Update active pane in layout
        if let Some(tab) = self.tabs.get_mut(self.active_tab) {
            if self.panes.contains_key(pane_id) {
                tab.layout.active_pane = Some(pane_id.to_string());
                return true;
            }
        }

        false
    }

    // Focus next pane
    pub fn focus_next(&mut self) -> Option<String> {
        let tab = self.tabs.get(self.active_tab)?;
        let pane_ids = Self::collect_pane_ids(&tab.layout.root);
        let active_pane = tab.layout.active_pane.clone();

        if pane_ids.is_empty() {
            return None;
        }

        let current_idx = active_pane
            .as_ref()
            .and_then(|id| pane_ids.iter().position(|p| p == id))
            .unwrap_or(0);

        let next_idx = (current_idx + 1) % pane_ids.len();
        let next_id = pane_ids[next_idx].clone();

        self.focus_pane(&next_id);
        Some(next_id)
    }

    // Focus previous pane
    pub fn focus_prev(&mut self) -> Option<String> {
        let tab = self.tabs.get(self.active_tab)?;
        let pane_ids = Self::collect_pane_ids(&tab.layout.root);
        let active_pane = tab.layout.active_pane.clone();

        if pane_ids.is_empty() {
            return None;
        }

        let current_idx = active_pane
            .as_ref()
            .and_then(|id| pane_ids.iter().position(|p| p == id))
            .unwrap_or(0);

        let prev_idx = if current_idx == 0 {
            pane_ids.len() - 1
        } else {
            current_idx - 1
        };

        let prev_id = pane_ids[prev_idx].clone();
        self.focus_pane(&prev_id);
        Some(prev_id)
    }

    // Get pane by ID
    pub fn get_pane(&self, pane_id: &str) -> Option<&Pane> {
        self.panes.get(pane_id)
    }

    // Get active pane
    pub fn active_pane(&self) -> Option<&Pane> {
        let tab = self.tabs.get(self.active_tab)?;
        let pane_id = tab.layout.active_pane.as_ref()?;
        self.panes.get(pane_id)
    }

    // Set pane PTY
    pub fn set_pane_pty(&mut self, pane_id: &str, pty_id: &str) -> bool {
        if let Some(pane) = self.panes.get_mut(pane_id) {
            pane.pty_id = Some(pty_id.to_string());
            true
        } else {
            false
        }
    }

    // Set pane title
    pub fn set_pane_title(&mut self, pane_id: &str, title: &str) -> bool {
        if let Some(pane) = self.panes.get_mut(pane_id) {
            pane.title = Some(title.to_string());
            true
        } else {
            false
        }
    }

    // Set pane CWD
    pub fn set_pane_cwd(&mut self, pane_id: &str, cwd: &str) -> bool {
        if let Some(pane) = self.panes.get_mut(pane_id) {
            pane.cwd = cwd.to_string();
            true
        } else {
            false
        }
    }

    // Collect all pane IDs in a layout
    fn collect_pane_ids(node: &LayoutNode) -> Vec<String> {
        match node {
            LayoutNode::Pane(id) => vec![id.clone()],
            LayoutNode::Split { first, second, .. } => {
                let mut ids = Self::collect_pane_ids(first);
                ids.extend(Self::collect_pane_ids(second));
                ids
            }
        }
    }

    // ==========================================================================
    // Layout Operations
    // ==========================================================================

    // Get current layout
    pub fn current_layout(&self) -> Option<&PaneLayout> {
        self.tabs.get(self.active_tab).map(|t| &t.layout)
    }

    // Calculate pane sizes based on total size
    pub fn calculate_sizes(&self, total_cols: u16, total_rows: u16) -> HashMap<String, PaneSize> {
        let mut sizes = HashMap::new();

        if let Some(tab) = self.tabs.get(self.active_tab) {
            self.calculate_node_sizes(
                &tab.layout.root,
                0, 0,
                total_cols, total_rows,
                &mut sizes,
            );
        }

        sizes
    }

    fn calculate_node_sizes(
        &self,
        node: &LayoutNode,
        x: u16, y: u16,
        width: u16, height: u16,
        sizes: &mut HashMap<String, PaneSize>,
    ) {
        match node {
            LayoutNode::Pane(id) => {
                sizes.insert(id.clone(), PaneSize {
                    cols: width,
                    rows: height,
                });
            }
            LayoutNode::Split { direction, ratio, first, second } => {
                match direction {
                    SplitDirection::Horizontal => {
                        let first_width = ((width as f32) * ratio) as u16;
                        let second_width = width - first_width;

                        self.calculate_node_sizes(first, x, y, first_width, height, sizes);
                        self.calculate_node_sizes(second, x + first_width, y, second_width, height, sizes);
                    }
                    SplitDirection::Vertical => {
                        let first_height = ((height as f32) * ratio) as u16;
                        let second_height = height - first_height;

                        self.calculate_node_sizes(first, x, y, width, first_height, sizes);
                        self.calculate_node_sizes(second, x, y + first_height, width, second_height, sizes);
                    }
                }
            }
        }
    }

    // Resize split
    pub fn resize_split(&mut self, pane_id: &str, delta: f32) -> bool {
        let tab = match self.tabs.get_mut(self.active_tab) {
            Some(t) => t,
            None => return false,
        };

        let (found, new_root) = Self::resize_node(tab.layout.root.clone(), pane_id, delta);
        if found {
            tab.layout.root = new_root;
            true
        } else {
            false
        }
    }

    fn resize_node(node: LayoutNode, target_id: &str, delta: f32) -> (bool, LayoutNode) {
        match node {
            LayoutNode::Split { direction, ratio, first, second } => {
                // Check if first pane is target
                if matches!(first.as_ref(), LayoutNode::Pane(id) if id == target_id) {
                    let new_ratio = (ratio + delta).clamp(0.1, 0.9);
                    return (true, LayoutNode::Split {
                        direction,
                        ratio: new_ratio,
                        first,
                        second,
                    });
                }

                // Check if second pane is target
                if matches!(second.as_ref(), LayoutNode::Pane(id) if id == target_id) {
                    let new_ratio = (ratio - delta).clamp(0.1, 0.9);
                    return (true, LayoutNode::Split {
                        direction,
                        ratio: new_ratio,
                        first,
                        second,
                    });
                }

                // Recurse
                let (found_first, new_first) = Self::resize_node(*first, target_id, delta);
                if found_first {
                    return (true, LayoutNode::Split {
                        direction,
                        ratio,
                        first: Box::new(new_first),
                        second,
                    });
                }

                let (found_second, new_second) = Self::resize_node(*second, target_id, delta);
                (found_second, LayoutNode::Split {
                    direction,
                    ratio,
                    first: Box::new(new_first),
                    second: Box::new(new_second),
                })
            }
            other => (false, other),
        }
    }
}

// Global pane manager
lazy_static::lazy_static! {
    pub static ref PANE_MANAGER: std::sync::Mutex<PaneManager> =
        std::sync::Mutex::new(PaneManager::new());
}

pub fn panes() -> std::sync::MutexGuard<'static, PaneManager> {
    PANE_MANAGER.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_new_manager() {
        let manager = PaneManager::new();
        assert_eq!(manager.tabs.len(), 1);
        assert!(manager.active_pane().is_some());
    }

    #[test]
    fn test_split_horizontal() {
        let mut manager = PaneManager::new();
        let initial_pane = manager.active_pane().unwrap().id.clone();

        let new_pane = manager.split(SplitDirection::Horizontal, 0.5);
        assert!(new_pane.is_some());
        assert_ne!(new_pane.unwrap(), initial_pane);
    }

    #[test]
    fn test_multiple_tabs() {
        let mut manager = PaneManager::new();

        manager.new_tab(Some("Tab 2"));
        assert_eq!(manager.tabs.len(), 2);
        assert_eq!(manager.active_tab, 1);

        manager.prev_tab();
        assert_eq!(manager.active_tab, 0);
    }

    #[test]
    fn test_calculate_sizes() {
        let mut manager = PaneManager::new();
        manager.split(SplitDirection::Horizontal, 0.5);

        let sizes = manager.calculate_sizes(100, 50);
        assert_eq!(sizes.len(), 2);

        // Each pane should be roughly half width
        for (_id, size) in &sizes {
            assert!(size.cols >= 49 && size.cols <= 51);
            assert_eq!(size.rows, 50);
        }
    }

    #[test]
    fn test_tab_color_preset() {
        let mut manager = PaneManager::new();
        let tab_id = manager.active_tab().unwrap().id.clone();

        assert!(manager.set_tab_color_preset(&tab_id, TabColorPreset::Blue));

        let tab = manager.active_tab().unwrap();
        assert_eq!(tab.color, TabColor::Preset(TabColorPreset::Blue));
    }

    #[test]
    fn test_tab_color_hex() {
        let mut manager = PaneManager::new();
        let tab_id = manager.active_tab().unwrap().id.clone();

        assert!(manager.set_tab_color_hex(&tab_id, "#FF5733"));

        let tab = manager.active_tab().unwrap();
        if let TabColor::Custom { r, g, b } = tab.color {
            assert_eq!(r, 255);
            assert_eq!(g, 87);
            assert_eq!(b, 51);
        } else {
            panic!("Expected custom color");
        }
    }

    #[test]
    fn test_tab_icon_emoji() {
        let mut manager = PaneManager::new();
        let tab_id = manager.active_tab().unwrap().id.clone();

        assert!(manager.set_tab_emoji(&tab_id, "🚀"));

        let tab = manager.active_tab().unwrap();
        assert_eq!(tab.icon, TabIcon::Emoji("🚀".to_string()));
    }

    #[test]
    fn test_pin_tab() {
        let mut manager = PaneManager::new();
        manager.new_tab(Some("Second"));

        let first_tab_id = manager.tabs[0].id.clone();
        let second_tab_id = manager.tabs[1].id.clone();

        // Pin second tab
        assert!(manager.pin_tab(&second_tab_id));

        // Pinned tabs should be first
        assert!(manager.tabs[0].pinned);
        assert_eq!(manager.tabs[0].id, second_tab_id);
        assert!(!manager.tabs[1].pinned);
    }

    #[test]
    fn test_color_from_hex() {
        let color = TabColor::from_hex("#FF0000").unwrap();
        assert_eq!(color.rgb(), (255, 0, 0));

        let color2 = TabColor::from_hex("00FF00").unwrap();
        assert_eq!(color2.rgb(), (0, 255, 0));

        assert!(TabColor::from_hex("invalid").is_none());
    }

    #[test]
    fn test_color_to_hex() {
        let color = TabColor::Preset(TabColorPreset::Red);
        assert_eq!(color.to_hex(), "#EF4444");

        let custom = TabColor::Custom { r: 255, g: 128, b: 0 };
        assert_eq!(custom.to_hex(), "#FF8000");
    }

    #[test]
    fn test_pattern_matching() {
        assert!(PaneManager::matches_pattern("/home/user/Projects/myapp", "*/Projects/*"));
        assert!(PaneManager::matches_pattern("/home/user/.config/app", "*/.config/*"));
        assert!(!PaneManager::matches_pattern("/home/user/Documents", "*/Projects/*"));
    }

    #[test]
    fn test_rename_disables_auto_name() {
        let mut manager = PaneManager::new();
        let tab_id = manager.active_tab().unwrap().id.clone();

        assert!(manager.tabs[0].auto_name); // Default is auto-name

        manager.rename_tab(&tab_id, "My Custom Tab");

        assert!(!manager.tabs[0].auto_name); // Should be disabled after rename
        assert_eq!(manager.tabs[0].name, Some("My Custom Tab".to_string()));
    }

    #[test]
    fn test_tab_display_name() {
        let mut manager = PaneManager::new();
        let tab_id = manager.active_tab().unwrap().id.clone();

        // Should return something (either directory name or Tab 1)
        let name = manager.get_tab_display_name(&tab_id);
        assert!(name.is_some());
    }

    #[test]
    fn test_directory_rules() {
        let mut manager = PaneManager::new();

        // Add custom rule
        manager.add_directory_rule(
            "*/custom/*",
            TabColor::Preset(TabColorPreset::Pink),
            Some(TabIcon::Emoji("💖".to_string()))
        );

        let (color, icon) = manager.color_for_directory("/home/user/custom/project");
        assert_eq!(color, TabColor::Preset(TabColorPreset::Pink));
        assert_eq!(icon, Some(TabIcon::Emoji("💖".to_string())));

        // Remove rule
        assert!(manager.remove_directory_rule("*/custom/*"));
    }
}
