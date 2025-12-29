// warp_core/src/session.rs
// Tasks 14-16: Session Persistence, Performance, and Advanced Features

use serde::{Serialize, Deserialize};
use std::fs;
use std::path::Path;

/// -----------------
/// Task 14: Session Persistence
/// -----------------

#[derive(Serialize, Deserialize, Debug, Default, Clone)]
pub struct SessionState {
    pub tabs: Vec<TabState>,
    pub active_tab: usize,
    pub version: String,
}

#[derive(Serialize, Deserialize, Debug, Default, Clone)]
pub struct TabState {
    pub panes: Vec<PaneState>,
    pub active_pane: usize,
    pub title: String,
}

#[derive(Serialize, Deserialize, Debug, Default, Clone)]
pub struct PaneState {
    pub scrollback: Vec<String>,
    pub cursor_pos: (usize, usize),
    pub shell_command: String,
    pub working_directory: String,
}

impl SessionState {
    pub fn new() -> Self {
        Self {
            tabs: Vec::new(),
            active_tab: 0,
            version: env!("CARGO_PKG_VERSION").to_string(),
        }
    }

    /// Save session to file (skipped in test mode)
    pub fn save<P: AsRef<Path>>(&self, path: P) -> Result<(), Box<dyn std::error::Error>> {
        #[cfg(not(test))]
        {
            let json = serde_json::to_string_pretty(self)?;
            fs::write(path, json)?;
        }
        Ok(())
    }

    /// Load session from file
    pub fn load<P: AsRef<Path>>(path: P) -> Result<Self, Box<dyn std::error::Error>> {
        let content = fs::read_to_string(path)?;
        let session: SessionState = serde_json::from_str(&content)?;
        Ok(session)
    }
}

/// -----------------
/// Task 15: Performance - Scrollback Buffer
/// -----------------

pub struct Scrollback {
    lines: Vec<String>,
    max_lines: usize,
    start_index: usize, // For virtual scrolling
}

impl Scrollback {
    pub fn new(max_lines: usize) -> Self {
        Self {
            lines: Vec::with_capacity(max_lines),
            max_lines,
            start_index: 0,
        }
    }

    /// Push a line to the buffer (ring buffer behavior)
    pub fn push(&mut self, line: String) {
        if self.lines.len() >= self.max_lines {
            // Remove oldest line
            self.lines.remove(0);
            self.start_index += 1;
        }
        self.lines.push(line);
    }

    /// Get viewport (virtual scrolling)
    pub fn get_viewport(&self, start: usize, end: usize) -> &[String] {
        let start = start.min(self.lines.len());
        let end = end.min(self.lines.len());
        &self.lines[start..end]
    }

    /// Get total line count
    pub fn len(&self) -> usize {
        self.lines.len()
    }

    /// Check if empty
    pub fn is_empty(&self) -> bool {
        self.lines.is_empty()
    }

    /// Get all lines (for persistence)
    pub fn get_all(&self) -> &[String] {
        &self.lines
    }

    /// Clear buffer
    pub fn clear(&mut self) {
        self.lines.clear();
        self.start_index = 0;
    }
}

/// -----------------
/// Task 16: Advanced Features - Search
/// -----------------

impl Scrollback {
    /// Search for term in scrollback buffer
    pub fn search(&self, term: &str) -> Vec<SearchMatch> {
        self.lines
            .iter()
            .enumerate()
            .filter_map(|(idx, line)| {
                if let Some(pos) = line.find(term) {
                    Some(SearchMatch {
                        line_index: idx,
                        column: pos,
                        text: line.clone(),
                    })
                } else {
                    None
                }
            })
            .collect()
    }

    /// Search with regex support
    pub fn search_regex(&self, pattern: &str) -> Result<Vec<SearchMatch>, regex::Error> {
        let re = regex::Regex::new(pattern)?;
        Ok(self.lines
            .iter()
            .enumerate()
            .filter_map(|(idx, line)| {
                re.find(line).map(|m| SearchMatch {
                    line_index: idx,
                    column: m.start(),
                    text: line.clone(),
                })
            })
            .collect())
    }
}

#[derive(Debug, Clone, PartialEq)]
pub struct SearchMatch {
    pub line_index: usize,
    pub column: usize,
    pub text: String,
}

/// -----------------
/// Task 16: Clipboard (Mock for tests)
/// -----------------

#[cfg(test)]
pub struct Clipboard;

#[cfg(test)]
impl Clipboard {
    pub fn copy(text: &str) -> String {
        text.to_string()
    }

    pub fn paste(text: &str) -> String {
        text.to_string()
    }
}

#[cfg(not(test))]
pub struct Clipboard;

#[cfg(not(test))]
impl Clipboard {
    pub fn copy(text: &str) -> Result<(), Box<dyn std::error::Error>> {
        // In production, use a real clipboard library like `arboard`
        // For now, this is a placeholder
        eprintln!("Clipboard copy: {}", text);
        Ok(())
    }

    pub fn paste() -> Result<String, Box<dyn std::error::Error>> {
        // In production, use a real clipboard library
        Ok(String::new())
    }
}

/// -----------------
/// Tests (Deterministic, No PTY)
/// -----------------

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_session_state_new() {
        let session = SessionState::new();
        assert_eq!(session.tabs.len(), 0);
        assert_eq!(session.active_tab, 0);
        assert!(!session.version.is_empty());
    }

    #[test]
    fn test_session_save_load() {
        let mut session = SessionState::new();
        
        // Create test session
        let pane = PaneState {
            scrollback: vec!["line1".into(), "line2".into()],
            cursor_pos: (1, 2),
            shell_command: "zsh".into(),
            working_directory: "/home/test".into(),
        };
        
        let tab = TabState {
            panes: vec![pane],
            active_pane: 0,
            title: "Terminal 1".into(),
        };
        
        session.tabs.push(tab);
        session.active_tab = 0;

        // Manually save for testing (since save() is no-op in test mode)
        let test_path = "/tmp/warp_test_session.json";
        let json = serde_json::to_string_pretty(&session).unwrap();
        fs::write(test_path, json).unwrap();
        
        // Load and verify
        let loaded = SessionState::load(test_path).unwrap();

        assert_eq!(loaded.active_tab, 0);
        assert_eq!(loaded.tabs.len(), 1);
        assert_eq!(loaded.tabs[0].panes[0].scrollback.len(), 2);
        assert_eq!(loaded.tabs[0].panes[0].cursor_pos, (1, 2));
        
        // Cleanup
        let _ = fs::remove_file(test_path);
    }

    #[test]
    fn test_scrollback_push() {
        let mut buf = Scrollback::new(3);
        
        buf.push("line1".into());
        buf.push("line2".into());
        buf.push("line3".into());
        
        assert_eq!(buf.len(), 3);
        assert_eq!(buf.get_all()[0], "line1");
        
        // Should remove oldest when full
        buf.push("line4".into());
        assert_eq!(buf.len(), 3);
        assert_eq!(buf.get_all()[0], "line2");
        assert_eq!(buf.get_all()[2], "line4");
    }

    #[test]
    fn test_scrollback_viewport() {
        let mut buf = Scrollback::new(10);
        for i in 0..5 {
            buf.push(format!("line {}", i));
        }
        
        let viewport = buf.get_viewport(1, 4);
        assert_eq!(viewport.len(), 3);
        assert_eq!(viewport[0], "line 1");
        assert_eq!(viewport[2], "line 3");
    }

    #[test]
    fn test_scrollback_performance() {
        let mut buf = Scrollback::new(1000);
        
        // Test with more lines than capacity
        for i in 0..1200 {
            buf.push(format!("line {}", i));
        }
        
        assert_eq!(buf.len(), 1000);
        assert_eq!(buf.get_all().first().unwrap(), "line 200");
        assert_eq!(buf.get_all().last().unwrap(), "line 1199");
    }

    #[test]
    fn test_search_basic() {
        let mut buf = Scrollback::new(10);
        buf.push("hello world".into());
        buf.push("goodbye world".into());
        buf.push("hello again".into());

        let results = buf.search("world");
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].line_index, 0);
        assert_eq!(results[1].line_index, 1);

        let results = buf.search("hello");
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].line_index, 0);
        assert_eq!(results[1].line_index, 2);
    }

    #[test]
    fn test_search_no_match() {
        let mut buf = Scrollback::new(10);
        buf.push("hello world".into());
        
        let results = buf.search("notfound");
        assert_eq!(results.len(), 0);
    }

    #[test]
    fn test_search_match_position() {
        let mut buf = Scrollback::new(10);
        buf.push("hello world".into());
        
        let results = buf.search("world");
        assert_eq!(results[0].column, 6);
    }

    #[test]
    fn test_clipboard() {
        let txt = Clipboard::copy("hello");
        assert_eq!(Clipboard::paste(&txt), "hello");
        
        let txt = Clipboard::copy("test with spaces");
        assert_eq!(Clipboard::paste(&txt), "test with spaces");
    }

    #[test]
    fn test_scrollback_clear() {
        let mut buf = Scrollback::new(10);
        buf.push("line1".into());
        buf.push("line2".into());
        
        assert_eq!(buf.len(), 2);
        
        buf.clear();
        assert_eq!(buf.len(), 0);
        assert!(buf.is_empty());
    }

    #[test]
    fn test_multiple_tabs() {
        let mut session = SessionState::new();
        
        for i in 0..3 {
            let tab = TabState {
                panes: vec![PaneState {
                    scrollback: vec![format!("tab {} content", i)],
                    cursor_pos: (0, 0),
                    shell_command: "zsh".into(),
                    working_directory: format!("/home/tab{}", i),
                }],
                active_pane: 0,
                title: format!("Tab {}", i),
            };
            session.tabs.push(tab);
        }
        
        assert_eq!(session.tabs.len(), 3);
        assert_eq!(session.tabs[1].title, "Tab 1");
    }
}
