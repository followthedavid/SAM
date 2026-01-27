//! Syntax Highlighting - CLI command and output highlighting
//!
//! Provides syntax highlighting for:
//! - Shell commands (bash, zsh, fish)
//! - Command output
//! - File paths
//! - Error messages
//! - Common CLI patterns

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// =============================================================================
// TYPES
// =============================================================================

/// Highlighting theme
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Theme {
    pub name: String,
    pub colors: ThemeColors,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ThemeColors {
    /// Commands (ls, git, etc.)
    pub command: String,
    /// Subcommands (git commit, npm install)
    pub subcommand: String,
    /// Flags (--help, -la)
    pub flag: String,
    /// Arguments/values
    pub argument: String,
    /// Strings (quoted text)
    pub string: String,
    /// Numbers
    pub number: String,
    /// Paths
    pub path: String,
    /// Variables ($HOME, ${VAR})
    pub variable: String,
    /// Operators (|, &&, ||, ;)
    pub operator: String,
    /// Redirections (>, >>, <)
    pub redirect: String,
    /// Comments (#...)
    pub comment: String,
    /// Errors
    pub error: String,
    /// Success indicators
    pub success: String,
    /// Warnings
    pub warning: String,
    /// Default text
    pub default: String,
    /// Background
    pub background: String,
}

impl Default for ThemeColors {
    fn default() -> Self {
        Self {
            command: "#58a6ff".to_string(),    // Blue
            subcommand: "#79c0ff".to_string(), // Light blue
            flag: "#a5d6ff".to_string(),       // Cyan
            argument: "#c9d1d9".to_string(),   // Light gray
            string: "#a5d6a7".to_string(),     // Green
            number: "#ffab70".to_string(),     // Orange
            path: "#d2a8ff".to_string(),       // Purple
            variable: "#ffa657".to_string(),   // Orange
            operator: "#ff7b72".to_string(),   // Red
            redirect: "#ff7b72".to_string(),   // Red
            comment: "#8b949e".to_string(),    // Gray
            error: "#f85149".to_string(),      // Bright red
            success: "#7ee787".to_string(),    // Green
            warning: "#d29922".to_string(),    // Yellow
            default: "#c9d1d9".to_string(),    // Light gray
            background: "#0d1117".to_string(), // Dark
        }
    }
}

/// A highlighted span
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HighlightSpan {
    pub start: usize,
    pub end: usize,
    pub token_type: TokenType,
    pub text: String,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq)]
pub enum TokenType {
    Command,
    Subcommand,
    Flag,
    Argument,
    String,
    Number,
    Path,
    Variable,
    Operator,
    Redirect,
    Comment,
    Error,
    Success,
    Warning,
    Default,
}

/// Highlighted command result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HighlightedCommand {
    pub raw: String,
    pub spans: Vec<HighlightSpan>,
    pub html: String,
    pub ansi: String,
}

// =============================================================================
// SYNTAX HIGHLIGHTER
// =============================================================================

pub struct SyntaxHighlighter {
    theme: Theme,
    known_commands: Vec<&'static str>,
    subcommand_map: HashMap<&'static str, Vec<&'static str>>,
}

impl SyntaxHighlighter {
    pub fn new() -> Self {
        Self::with_theme(Theme {
            name: "default".to_string(),
            colors: ThemeColors::default(),
        })
    }

    pub fn with_theme(theme: Theme) -> Self {
        let mut highlighter = Self {
            theme,
            known_commands: Vec::new(),
            subcommand_map: HashMap::new(),
        };
        highlighter.load_defaults();
        highlighter
    }

    fn load_defaults(&mut self) {
        // Common commands
        self.known_commands = vec![
            // Core utils
            "ls", "cd", "pwd", "cp", "mv", "rm", "mkdir", "rmdir", "touch",
            "cat", "head", "tail", "less", "more", "grep", "find", "sed", "awk",
            "sort", "uniq", "wc", "diff", "chmod", "chown", "ln", "file",
            // Network
            "curl", "wget", "ssh", "scp", "rsync", "ping", "netstat", "ifconfig",
            "ip", "dig", "nslookup", "nc", "telnet",
            // Process
            "ps", "top", "htop", "kill", "killall", "pkill", "pgrep", "jobs",
            "bg", "fg", "nohup", "nice", "renice",
            // Package managers
            "npm", "yarn", "pnpm", "bun", "pip", "pip3", "cargo", "go", "brew",
            "apt", "apt-get", "yum", "dnf", "pacman", "gem", "composer",
            // Dev tools
            "git", "docker", "kubectl", "terraform", "make", "cmake", "ninja",
            "node", "python", "python3", "ruby", "java", "rustc", "gcc", "clang",
            // Editors
            "vim", "nvim", "nano", "emacs", "code", "subl",
            // Shell
            "echo", "printf", "read", "source", "export", "env", "set", "unset",
            "alias", "which", "type", "whereis", "history", "clear",
            // System
            "sudo", "su", "date", "cal", "df", "du", "free", "uname", "hostname",
            "whoami", "id", "groups", "passwd", "uptime", "shutdown", "reboot",
            // Archive
            "tar", "zip", "unzip", "gzip", "gunzip", "bzip2", "xz",
            // Text
            "cut", "paste", "join", "tr", "tee", "xargs",
        ];

        // Subcommand mappings
        self.subcommand_map.insert("git", vec![
            "add", "commit", "push", "pull", "fetch", "clone", "checkout", "branch",
            "merge", "rebase", "reset", "stash", "log", "diff", "status", "init",
            "remote", "tag", "cherry-pick", "bisect", "blame", "show",
        ]);

        self.subcommand_map.insert("docker", vec![
            "run", "build", "pull", "push", "ps", "images", "exec", "logs",
            "stop", "start", "restart", "rm", "rmi", "network", "volume", "compose",
        ]);

        self.subcommand_map.insert("npm", vec![
            "install", "uninstall", "run", "start", "test", "build", "publish",
            "init", "update", "audit", "outdated", "list", "link", "pack",
        ]);

        self.subcommand_map.insert("kubectl", vec![
            "get", "apply", "delete", "describe", "logs", "exec", "port-forward",
            "create", "edit", "patch", "scale", "rollout", "config", "cluster-info",
        ]);

        self.subcommand_map.insert("cargo", vec![
            "build", "run", "test", "check", "clippy", "fmt", "doc", "publish",
            "new", "init", "add", "remove", "update", "search", "install",
        ]);
    }

    /// Highlight a command
    pub fn highlight_command(&self, command: &str) -> HighlightedCommand {
        let mut spans = Vec::new();
        let mut pos = 0;

        let tokens = tokenize_command(command);

        for (i, token) in tokens.iter().enumerate() {
            let token_type = self.classify_token(token, i, &tokens);
            let start = command[pos..].find(token).map(|p| pos + p).unwrap_or(pos);
            let end = start + token.len();

            spans.push(HighlightSpan {
                start,
                end,
                token_type,
                text: token.clone(),
            });

            pos = end;
        }

        let html = self.to_html(&spans);
        let ansi = self.to_ansi(&spans);

        HighlightedCommand {
            raw: command.to_string(),
            spans,
            html,
            ansi,
        }
    }

    /// Highlight output (error detection, paths, etc.)
    pub fn highlight_output(&self, output: &str) -> Vec<HighlightSpan> {
        let mut spans = Vec::new();
        let mut pos = 0;

        for line in output.lines() {
            let line_start = output[pos..].find(line).map(|p| pos + p).unwrap_or(pos);
            let line_end = line_start + line.len();

            let token_type = if line.to_lowercase().contains("error") ||
                line.to_lowercase().contains("failed") ||
                line.to_lowercase().contains("fatal") {
                TokenType::Error
            } else if line.to_lowercase().contains("warning") ||
                line.to_lowercase().contains("warn") {
                TokenType::Warning
            } else if line.to_lowercase().contains("success") ||
                line.contains("ok") ||
                line.contains("passed") {
                TokenType::Success
            } else if line.starts_with('/') || line.contains("./") {
                TokenType::Path
            } else {
                TokenType::Default
            };

            spans.push(HighlightSpan {
                start: line_start,
                end: line_end,
                token_type,
                text: line.to_string(),
            });

            pos = line_end + 1; // +1 for newline
        }

        spans
    }

    fn classify_token(&self, token: &str, index: usize, tokens: &[String]) -> TokenType {
        // Comment
        if token.starts_with('#') {
            return TokenType::Comment;
        }

        // Operators
        if matches!(token, "|" | "||" | "&&" | ";" | "&") {
            return TokenType::Operator;
        }

        // Redirections
        if matches!(token, ">" | ">>" | "<" | "<<" | "2>" | "2>>" | "&>" | "|&") {
            return TokenType::Redirect;
        }

        // Variables
        if token.starts_with('$') || token.starts_with("${") {
            return TokenType::Variable;
        }

        // Strings
        if (token.starts_with('"') && token.ends_with('"')) ||
           (token.starts_with('\'') && token.ends_with('\'')) {
            return TokenType::String;
        }

        // Flags
        if token.starts_with('-') {
            return TokenType::Flag;
        }

        // Numbers
        if token.chars().all(|c| c.is_ascii_digit() || c == '.') && !token.is_empty() {
            return TokenType::Number;
        }

        // Paths (starting with / or ./ or ../ or ~)
        if token.starts_with('/') || token.starts_with("./") ||
           token.starts_with("../") || token.starts_with('~') ||
           token.contains('/') {
            return TokenType::Path;
        }

        // Command (first token or after operator)
        if index == 0 || (index > 0 && matches!(tokens[index - 1].as_str(), "|" | "||" | "&&" | ";")) {
            if self.known_commands.contains(&token) {
                return TokenType::Command;
            }
            // Treat unknown first word as command too
            return TokenType::Command;
        }

        // Subcommand (second token after known command)
        if index == 1 {
            let prev = &tokens[0];
            if let Some(subs) = self.subcommand_map.get(prev.as_str()) {
                if subs.contains(&token) {
                    return TokenType::Subcommand;
                }
            }
        }

        TokenType::Argument
    }

    fn get_color(&self, token_type: TokenType) -> &str {
        match token_type {
            TokenType::Command => &self.theme.colors.command,
            TokenType::Subcommand => &self.theme.colors.subcommand,
            TokenType::Flag => &self.theme.colors.flag,
            TokenType::Argument => &self.theme.colors.argument,
            TokenType::String => &self.theme.colors.string,
            TokenType::Number => &self.theme.colors.number,
            TokenType::Path => &self.theme.colors.path,
            TokenType::Variable => &self.theme.colors.variable,
            TokenType::Operator => &self.theme.colors.operator,
            TokenType::Redirect => &self.theme.colors.redirect,
            TokenType::Comment => &self.theme.colors.comment,
            TokenType::Error => &self.theme.colors.error,
            TokenType::Success => &self.theme.colors.success,
            TokenType::Warning => &self.theme.colors.warning,
            TokenType::Default => &self.theme.colors.default,
        }
    }

    fn to_html(&self, spans: &[HighlightSpan]) -> String {
        let mut html = String::new();
        for span in spans {
            let color = self.get_color(span.token_type);
            html.push_str(&format!(
                r#"<span style="color: {}">{}</span>"#,
                color,
                html_escape(&span.text)
            ));
            html.push(' ');
        }
        html.trim_end().to_string()
    }

    fn to_ansi(&self, spans: &[HighlightSpan]) -> String {
        let mut ansi = String::new();
        for span in spans {
            let color = self.get_color(span.token_type);
            if let Some(code) = hex_to_ansi(color) {
                ansi.push_str(&format!("\x1b[{}m{}\x1b[0m ", code, span.text));
            } else {
                ansi.push_str(&span.text);
                ansi.push(' ');
            }
        }
        ansi.trim_end().to_string()
    }

    /// Set theme
    pub fn set_theme(&mut self, theme: Theme) {
        self.theme = theme;
    }

    /// Get current theme
    pub fn theme(&self) -> &Theme {
        &self.theme
    }
}

impl Default for SyntaxHighlighter {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn tokenize_command(command: &str) -> Vec<String> {
    let mut tokens = Vec::new();
    let mut current = String::new();
    let mut in_string = false;
    let mut string_char = '"';

    for c in command.chars() {
        if in_string {
            current.push(c);
            if c == string_char {
                in_string = false;
            }
        } else if c == '"' || c == '\'' {
            if !current.is_empty() {
                tokens.push(std::mem::take(&mut current));
            }
            in_string = true;
            string_char = c;
            current.push(c);
        } else if c.is_whitespace() {
            if !current.is_empty() {
                tokens.push(std::mem::take(&mut current));
            }
        } else if matches!(c, '|' | '&' | ';' | '>' | '<') {
            if !current.is_empty() {
                tokens.push(std::mem::take(&mut current));
            }
            // Handle multi-char operators
            current.push(c);
            // Check for ||, &&, >>, etc.
        } else {
            current.push(c);
        }
    }

    if !current.is_empty() {
        tokens.push(current);
    }

    tokens
}

fn html_escape(s: &str) -> String {
    s.replace('&', "&amp;")
        .replace('<', "&lt;")
        .replace('>', "&gt;")
        .replace('"', "&quot;")
}

fn hex_to_ansi(hex: &str) -> Option<String> {
    let hex = hex.trim_start_matches('#');
    if hex.len() != 6 {
        return None;
    }

    let r = u8::from_str_radix(&hex[0..2], 16).ok()?;
    let g = u8::from_str_radix(&hex[2..4], 16).ok()?;
    let b = u8::from_str_radix(&hex[4..6], 16).ok()?;

    Some(format!("38;2;{};{};{}", r, g, b))
}

// =============================================================================
// PREDEFINED THEMES
// =============================================================================

pub fn dark_theme() -> Theme {
    Theme {
        name: "dark".to_string(),
        colors: ThemeColors::default(),
    }
}

pub fn light_theme() -> Theme {
    Theme {
        name: "light".to_string(),
        colors: ThemeColors {
            command: "#0366d6".to_string(),
            subcommand: "#005cc5".to_string(),
            flag: "#6f42c1".to_string(),
            argument: "#24292e".to_string(),
            string: "#22863a".to_string(),
            number: "#e36209".to_string(),
            path: "#6f42c1".to_string(),
            variable: "#e36209".to_string(),
            operator: "#d73a49".to_string(),
            redirect: "#d73a49".to_string(),
            comment: "#6a737d".to_string(),
            error: "#cb2431".to_string(),
            success: "#28a745".to_string(),
            warning: "#dbab09".to_string(),
            default: "#24292e".to_string(),
            background: "#ffffff".to_string(),
        },
    }
}

pub fn monokai_theme() -> Theme {
    Theme {
        name: "monokai".to_string(),
        colors: ThemeColors {
            command: "#66d9ef".to_string(),
            subcommand: "#a6e22e".to_string(),
            flag: "#fd971f".to_string(),
            argument: "#f8f8f2".to_string(),
            string: "#e6db74".to_string(),
            number: "#ae81ff".to_string(),
            path: "#f92672".to_string(),
            variable: "#fd971f".to_string(),
            operator: "#f92672".to_string(),
            redirect: "#f92672".to_string(),
            comment: "#75715e".to_string(),
            error: "#f92672".to_string(),
            success: "#a6e22e".to_string(),
            warning: "#e6db74".to_string(),
            default: "#f8f8f2".to_string(),
            background: "#272822".to_string(),
        },
    }
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tokenize_command() {
        let tokens = tokenize_command("git commit -m 'test message'");
        assert_eq!(tokens[0], "git");
        assert_eq!(tokens[1], "commit");
        assert_eq!(tokens[2], "-m");
        assert!(tokens[3].contains("test message"));
    }

    #[test]
    fn test_classify_command() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("git push origin main");

        assert_eq!(result.spans[0].token_type, TokenType::Command);
        assert_eq!(result.spans[1].token_type, TokenType::Subcommand);
    }

    #[test]
    fn test_classify_flags() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("ls -la --color=auto");

        assert_eq!(result.spans[0].token_type, TokenType::Command);
        assert_eq!(result.spans[1].token_type, TokenType::Flag);
        assert_eq!(result.spans[2].token_type, TokenType::Flag);
    }

    #[test]
    fn test_classify_paths() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("cat /etc/passwd");

        assert_eq!(result.spans[1].token_type, TokenType::Path);
    }

    #[test]
    fn test_classify_variables() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("echo $HOME");

        assert_eq!(result.spans[1].token_type, TokenType::Variable);
    }

    #[test]
    fn test_classify_operators() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("cmd1 | cmd2");

        assert!(result.spans.iter().any(|s| s.token_type == TokenType::Operator));
    }

    #[test]
    fn test_html_output() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("ls -la");

        assert!(result.html.contains("<span"));
        assert!(result.html.contains("style="));
    }

    #[test]
    fn test_ansi_output() {
        let highlighter = SyntaxHighlighter::new();
        let result = highlighter.highlight_command("ls -la");

        assert!(result.ansi.contains("\x1b["));
    }

    #[test]
    fn test_output_highlighting() {
        let highlighter = SyntaxHighlighter::new();
        let output = "File not found\nError: something failed\nSuccess!\n";
        let spans = highlighter.highlight_output(output);

        assert!(spans.iter().any(|s| s.token_type == TokenType::Error));
        assert!(spans.iter().any(|s| s.token_type == TokenType::Success));
    }

    #[test]
    fn test_themes() {
        let dark = dark_theme();
        assert_eq!(dark.name, "dark");

        let light = light_theme();
        assert_eq!(light.name, "light");

        let monokai = monokai_theme();
        assert_eq!(monokai.name, "monokai");
    }
}
