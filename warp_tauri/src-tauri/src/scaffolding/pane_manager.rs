// Pane Manager - Split Pane Terminal Management
//
// Manages multiple terminal panes with layouts.
// Warp/iTerm2 style split panes.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

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
    pub name: Option<String>,
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
}

impl PaneManager {
    pub fn new() -> Self {
        let mut manager = Self {
            tabs: Vec::new(),
            panes: HashMap::new(),
            active_tab: 0,
        };

        // Create initial tab with single pane
        manager.new_tab(None);
        manager
    }

    // ==========================================================================
    // Tab Operations
    // ==========================================================================

    // Create new tab
    pub fn new_tab(&mut self, name: Option<&str>) -> &Tab {
        let pane = self.create_pane();
        let pane_id = pane.id.clone();

        let tab = Tab {
            id: format!("tab_{}", chrono::Utc::now().timestamp_millis()),
            name: name.map(|s| s.to_string()),
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
}
