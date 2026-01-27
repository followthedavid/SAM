//! Link Detection - Clickable URLs in terminal output
//!
//! Provides URL and path detection:
//! - HTTP/HTTPS URLs
//! - File paths
//! - Email addresses
//! - IP addresses
//! - Custom patterns (issue numbers, etc.)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use regex::Regex;

// =============================================================================
// TYPES
// =============================================================================

/// Type of detected link
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum LinkType {
    /// Web URL (http/https)
    Url,
    /// File path
    FilePath,
    /// Email address
    Email,
    /// IP address (with optional port)
    IpAddress,
    /// Git repository
    GitRepo,
    /// Issue/PR reference (e.g., #123, GH-123)
    IssueRef,
    /// Custom pattern
    Custom(String),
}

/// A detected link in text
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DetectedLink {
    /// Link type
    pub link_type: LinkType,
    /// The matched text
    pub text: String,
    /// Start position in original text
    pub start: usize,
    /// End position in original text
    pub end: usize,
    /// Resolved URL (may differ from text)
    pub url: String,
    /// Whether link is valid/reachable
    pub valid: Option<bool>,
}

/// Custom pattern for link detection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CustomPattern {
    /// Pattern name
    pub name: String,
    /// Regex pattern
    pub pattern: String,
    /// URL template (use $0 for full match, $1-$9 for groups)
    pub url_template: String,
    /// Whether enabled
    pub enabled: bool,
}

/// Configuration for link detection
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LinkConfig {
    /// Enable URL detection
    pub detect_urls: bool,
    /// Enable file path detection
    pub detect_paths: bool,
    /// Enable email detection
    pub detect_emails: bool,
    /// Enable IP detection
    pub detect_ips: bool,
    /// Enable git repo detection
    pub detect_git: bool,
    /// Enable issue reference detection
    pub detect_issues: bool,
    /// Custom patterns
    pub custom_patterns: Vec<CustomPattern>,
    /// Issue URL template (for issue references)
    pub issue_url_template: Option<String>,
}

impl Default for LinkConfig {
    fn default() -> Self {
        Self {
            detect_urls: true,
            detect_paths: true,
            detect_emails: true,
            detect_ips: true,
            detect_git: true,
            detect_issues: true,
            custom_patterns: Vec::new(),
            issue_url_template: None,
        }
    }
}

// =============================================================================
// LINK DETECTOR
// =============================================================================

pub struct LinkDetector {
    config: LinkConfig,
    url_regex: Regex,
    path_regex: Regex,
    email_regex: Regex,
    ip_regex: Regex,
    git_regex: Regex,
    issue_regex: Regex,
    custom_regexes: HashMap<String, Regex>,
}

impl LinkDetector {
    pub fn new() -> Self {
        Self::with_config(LinkConfig::default())
    }

    pub fn with_config(config: LinkConfig) -> Self {
        let mut detector = Self {
            url_regex: Regex::new(r#"https?://[^\s\]\)>"'`]+"#).unwrap(),
            path_regex: Regex::new(r"(?:^|[\s\(\[])(/[^\s\]\)]+|~[^\s\]\)]+|\./[^\s\]\)]+|\.\./[^\s\]\)]+)").unwrap(),
            email_regex: Regex::new(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}").unwrap(),
            ip_regex: Regex::new(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(:\d+)?\b").unwrap(),
            git_regex: Regex::new(r"git@[^\s]+:[^\s]+\.git|https://(?:github|gitlab|bitbucket)[^\s]+\.git").unwrap(),
            issue_regex: Regex::new(r"(?:#|GH-|JIRA-|ISSUE-)(\d+)").unwrap(),
            custom_regexes: HashMap::new(),
            config,
        };
        detector.compile_custom_patterns();
        detector
    }

    fn compile_custom_patterns(&mut self) {
        self.custom_regexes.clear();
        for pattern in &self.config.custom_patterns {
            if pattern.enabled {
                if let Ok(regex) = Regex::new(&pattern.pattern) {
                    self.custom_regexes.insert(pattern.name.clone(), regex);
                }
            }
        }
    }

    /// Detect all links in text
    pub fn detect(&self, text: &str) -> Vec<DetectedLink> {
        let mut links = Vec::new();

        if self.config.detect_urls {
            links.extend(self.detect_urls(text));
        }

        if self.config.detect_paths {
            links.extend(self.detect_paths(text));
        }

        if self.config.detect_emails {
            links.extend(self.detect_emails(text));
        }

        if self.config.detect_ips {
            links.extend(self.detect_ips(text));
        }

        if self.config.detect_git {
            links.extend(self.detect_git(text));
        }

        if self.config.detect_issues {
            links.extend(self.detect_issues(text));
        }

        // Custom patterns
        for pattern in &self.config.custom_patterns {
            if pattern.enabled {
                links.extend(self.detect_custom(text, pattern));
            }
        }

        // Sort by position and remove overlaps
        links.sort_by_key(|l| l.start);
        self.remove_overlaps(links)
    }

    /// Detect URLs
    fn detect_urls(&self, text: &str) -> Vec<DetectedLink> {
        self.url_regex.find_iter(text).map(|m| {
            let matched = m.as_str().to_string();
            // Clean up trailing punctuation
            let cleaned = matched.trim_end_matches(|c| c == '.' || c == ',' || c == ')' || c == ']');
            DetectedLink {
                link_type: LinkType::Url,
                text: cleaned.to_string(),
                start: m.start(),
                end: m.start() + cleaned.len(),
                url: cleaned.to_string(),
                valid: None,
            }
        }).collect()
    }

    /// Detect file paths
    fn detect_paths(&self, text: &str) -> Vec<DetectedLink> {
        self.path_regex.captures_iter(text).filter_map(|cap| {
            cap.get(1).map(|m| {
                let path = m.as_str().to_string();
                let expanded = self.expand_path(&path);
                DetectedLink {
                    link_type: LinkType::FilePath,
                    text: path.clone(),
                    start: m.start(),
                    end: m.end(),
                    url: format!("file://{}", expanded),
                    valid: None,
                }
            })
        }).collect()
    }

    /// Detect email addresses
    fn detect_emails(&self, text: &str) -> Vec<DetectedLink> {
        self.email_regex.find_iter(text).map(|m| {
            let email = m.as_str().to_string();
            DetectedLink {
                link_type: LinkType::Email,
                text: email.clone(),
                start: m.start(),
                end: m.end(),
                url: format!("mailto:{}", email),
                valid: None,
            }
        }).collect()
    }

    /// Detect IP addresses
    fn detect_ips(&self, text: &str) -> Vec<DetectedLink> {
        self.ip_regex.captures_iter(text).map(|cap| {
            let full_match = cap.get(0).unwrap();
            let ip = cap.get(1).unwrap().as_str();
            let port = cap.get(2).map(|m| m.as_str()).unwrap_or("");
            let url = if port.is_empty() {
                format!("http://{}", ip)
            } else {
                format!("http://{}{}", ip, port)
            };
            DetectedLink {
                link_type: LinkType::IpAddress,
                text: full_match.as_str().to_string(),
                start: full_match.start(),
                end: full_match.end(),
                url,
                valid: None,
            }
        }).collect()
    }

    /// Detect git repositories
    fn detect_git(&self, text: &str) -> Vec<DetectedLink> {
        self.git_regex.find_iter(text).map(|m| {
            let repo = m.as_str().to_string();
            let url = self.git_to_web_url(&repo);
            DetectedLink {
                link_type: LinkType::GitRepo,
                text: repo,
                start: m.start(),
                end: m.end(),
                url,
                valid: None,
            }
        }).collect()
    }

    /// Detect issue references
    fn detect_issues(&self, text: &str) -> Vec<DetectedLink> {
        self.issue_regex.captures_iter(text).filter_map(|cap| {
            let full_match = cap.get(0)?;
            let number = cap.get(1)?.as_str();

            let url = if let Some(ref template) = self.config.issue_url_template {
                template.replace("{number}", number)
            } else {
                // Default to GitHub issues if we can detect the repo
                format!("https://github.com/issues/{}", number)
            };

            Some(DetectedLink {
                link_type: LinkType::IssueRef,
                text: full_match.as_str().to_string(),
                start: full_match.start(),
                end: full_match.end(),
                url,
                valid: None,
            })
        }).collect()
    }

    /// Detect custom patterns
    fn detect_custom(&self, text: &str, pattern: &CustomPattern) -> Vec<DetectedLink> {
        let regex = match self.custom_regexes.get(&pattern.name) {
            Some(r) => r,
            None => return Vec::new(),
        };

        regex.captures_iter(text).filter_map(|cap| {
            let full_match = cap.get(0)?;
            let mut url = pattern.url_template.clone();

            // Replace $0 with full match
            url = url.replace("$0", full_match.as_str());

            // Replace $1-$9 with capture groups
            for i in 1..=9 {
                if let Some(group) = cap.get(i) {
                    url = url.replace(&format!("${}", i), group.as_str());
                }
            }

            Some(DetectedLink {
                link_type: LinkType::Custom(pattern.name.clone()),
                text: full_match.as_str().to_string(),
                start: full_match.start(),
                end: full_match.end(),
                url,
                valid: None,
            })
        }).collect()
    }

    /// Remove overlapping links (keep longest)
    fn remove_overlaps(&self, links: Vec<DetectedLink>) -> Vec<DetectedLink> {
        let mut result = Vec::new();
        let mut last_end = 0;

        for link in links {
            if link.start >= last_end {
                last_end = link.end;
                result.push(link);
            } else if link.end - link.start > result.last().map(|l| l.end - l.start).unwrap_or(0) {
                // Replace shorter link with longer one
                result.pop();
                last_end = link.end;
                result.push(link);
            }
        }

        result
    }

    /// Expand path (~ to home, resolve relative)
    fn expand_path(&self, path: &str) -> String {
        if path.starts_with('~') {
            if let Some(home) = std::env::var("HOME").ok() {
                return path.replacen('~', &home, 1);
            }
        }
        path.to_string()
    }

    /// Convert git URL to web URL
    fn git_to_web_url(&self, git_url: &str) -> String {
        if git_url.starts_with("git@github.com:") {
            let path = git_url.trim_start_matches("git@github.com:").trim_end_matches(".git");
            format!("https://github.com/{}", path)
        } else if git_url.starts_with("git@gitlab.com:") {
            let path = git_url.trim_start_matches("git@gitlab.com:").trim_end_matches(".git");
            format!("https://gitlab.com/{}", path)
        } else if git_url.starts_with("git@bitbucket.org:") {
            let path = git_url.trim_start_matches("git@bitbucket.org:").trim_end_matches(".git");
            format!("https://bitbucket.org/{}", path)
        } else if git_url.ends_with(".git") {
            git_url.trim_end_matches(".git").to_string()
        } else {
            git_url.to_string()
        }
    }

    /// Update config
    pub fn set_config(&mut self, config: LinkConfig) {
        self.config = config;
        self.compile_custom_patterns();
    }

    /// Get config
    pub fn config(&self) -> &LinkConfig {
        &self.config
    }

    /// Add custom pattern
    pub fn add_pattern(&mut self, pattern: CustomPattern) {
        self.config.custom_patterns.push(pattern);
        self.compile_custom_patterns();
    }

    /// Remove custom pattern
    pub fn remove_pattern(&mut self, name: &str) -> bool {
        let original_len = self.config.custom_patterns.len();
        self.config.custom_patterns.retain(|p| p.name != name);
        let removed = self.config.custom_patterns.len() < original_len;
        if removed {
            self.compile_custom_patterns();
        }
        removed
    }

    /// Set issue URL template
    pub fn set_issue_template(&mut self, template: &str) {
        self.config.issue_url_template = Some(template.to_string());
    }
}

impl Default for LinkDetector {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref LINK_DETECTOR: std::sync::Mutex<LinkDetector> =
        std::sync::Mutex::new(LinkDetector::new());
}

/// Detect links in text
pub fn detect(text: &str) -> Vec<DetectedLink> {
    LINK_DETECTOR.lock().unwrap().detect(text)
}

/// Add a custom pattern
pub fn add_pattern(name: &str, pattern: &str, url_template: &str) {
    LINK_DETECTOR.lock().unwrap().add_pattern(CustomPattern {
        name: name.to_string(),
        pattern: pattern.to_string(),
        url_template: url_template.to_string(),
        enabled: true,
    });
}

/// Set issue URL template
pub fn set_issue_template(template: &str) {
    LINK_DETECTOR.lock().unwrap().set_issue_template(template);
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_urls() {
        let detector = LinkDetector::new();
        let links = detector.detect("Check out https://example.com for more info");

        assert_eq!(links.len(), 1);
        assert_eq!(links[0].link_type, LinkType::Url);
        assert_eq!(links[0].url, "https://example.com");
    }

    #[test]
    fn test_detect_urls_with_paths() {
        let detector = LinkDetector::new();
        let links = detector.detect("Visit https://github.com/user/repo/issues/123");

        assert_eq!(links.len(), 1);
        assert!(links[0].url.contains("github.com"));
    }

    #[test]
    fn test_detect_emails() {
        let detector = LinkDetector::new();
        let links = detector.detect("Contact us at hello@example.com");

        assert_eq!(links.len(), 1);
        assert_eq!(links[0].link_type, LinkType::Email);
        assert_eq!(links[0].url, "mailto:hello@example.com");
    }

    #[test]
    fn test_detect_paths() {
        let detector = LinkDetector::new();
        let links = detector.detect("Edit the file /etc/hosts or ~/config");

        assert_eq!(links.len(), 2);
        assert!(links.iter().all(|l| l.link_type == LinkType::FilePath));
    }

    #[test]
    fn test_detect_ip() {
        let detector = LinkDetector::new();
        let links = detector.detect("Server at 192.168.1.1:8080");

        assert_eq!(links.len(), 1);
        assert_eq!(links[0].link_type, LinkType::IpAddress);
        assert!(links[0].url.contains("192.168.1.1:8080"));
    }

    #[test]
    fn test_detect_git() {
        let detector = LinkDetector::new();
        let links = detector.detect("Clone git@github.com:user/repo.git");

        assert_eq!(links.len(), 1);
        assert_eq!(links[0].link_type, LinkType::GitRepo);
        assert_eq!(links[0].url, "https://github.com/user/repo");
    }

    #[test]
    fn test_detect_issues() {
        let detector = LinkDetector::new();
        let links = detector.detect("Fixed in #123 and GH-456");

        assert_eq!(links.len(), 2);
        assert!(links.iter().all(|l| l.link_type == LinkType::IssueRef));
    }

    #[test]
    fn test_custom_pattern() {
        let mut detector = LinkDetector::new();
        detector.add_pattern(CustomPattern {
            name: "jira".to_string(),
            pattern: r"PROJ-(\d+)".to_string(),
            url_template: "https://jira.example.com/browse/PROJ-$1".to_string(),
            enabled: true,
        });

        let links = detector.detect("See PROJ-123 for details");

        assert_eq!(links.len(), 1);
        assert_eq!(links[0].url, "https://jira.example.com/browse/PROJ-123");
    }

    #[test]
    fn test_no_overlaps() {
        let detector = LinkDetector::new();
        let links = detector.detect("https://example.com/path");

        // Should not have overlapping URL and path
        assert_eq!(links.len(), 1);
    }

    #[test]
    fn test_disabled_detection() {
        let mut config = LinkConfig::default();
        config.detect_emails = false;

        let detector = LinkDetector::with_config(config);
        let links = detector.detect("Email: test@example.com");

        assert_eq!(links.len(), 0);
    }
}
