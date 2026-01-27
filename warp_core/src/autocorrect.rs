//! Command Autocorrect for warp_core
//!
//! Suggests corrections for mistyped commands, similar to Warp's
//! command autocorrect feature. Uses Levenshtein distance and
//! common typo patterns.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Command autocorrect engine
pub struct Autocorrect {
    /// Known valid commands
    known_commands: HashSet<String>,
    /// Command aliases (shortcut -> full command)
    aliases: HashMap<String, String>,
    /// Common typo patterns
    typo_patterns: Vec<TypoPattern>,
    /// History of corrections (for learning)
    correction_history: Vec<CorrectionEntry>,
    /// Maximum edit distance for suggestions
    max_distance: usize,
    /// Whether autocorrect is enabled
    enabled: bool,
}

/// A typo pattern for quick corrections
#[derive(Clone, Debug)]
struct TypoPattern {
    /// The typo regex or pattern
    typo: String,
    /// The correction
    correction: String,
}

/// A correction history entry
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CorrectionEntry {
    pub original: String,
    pub corrected: String,
    pub accepted: bool,
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// A suggested correction
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Suggestion {
    /// The suggested correction
    pub command: String,
    /// Confidence score (0.0 - 1.0)
    pub confidence: f64,
    /// Reason for suggestion
    pub reason: SuggestionReason,
    /// Edit distance from original
    pub distance: usize,
}

/// Reason for a suggestion
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum SuggestionReason {
    /// Similar to a known command
    SimilarCommand,
    /// Common typo pattern
    CommonTypo,
    /// Alias expansion
    Alias,
    /// Historical correction
    Historical,
    /// Missing sudo
    MissingSudo,
    /// Wrong flag format
    FlagFormat,
}

impl Default for Autocorrect {
    fn default() -> Self {
        Self::new()
    }
}

impl Autocorrect {
    /// Create a new autocorrect engine with default commands
    pub fn new() -> Self {
        let mut ac = Self {
            known_commands: HashSet::new(),
            aliases: HashMap::new(),
            typo_patterns: Vec::new(),
            correction_history: Vec::new(),
            max_distance: 2,
            enabled: true,
        };

        // Add common Unix commands
        ac.add_common_commands();
        ac.add_common_typos();
        ac.add_common_aliases();

        ac
    }

    /// Enable or disable autocorrect
    pub fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled;
    }

    /// Add a known command
    pub fn add_command(&mut self, cmd: &str) {
        self.known_commands.insert(cmd.to_string());
    }

    /// Add multiple commands
    pub fn add_commands(&mut self, cmds: &[&str]) {
        for cmd in cmds {
            self.known_commands.insert(cmd.to_string());
        }
    }

    /// Add an alias
    pub fn add_alias(&mut self, alias: &str, command: &str) {
        self.aliases.insert(alias.to_string(), command.to_string());
    }

    /// Get suggestions for a command
    pub fn suggest(&self, input: &str) -> Vec<Suggestion> {
        if !self.enabled || input.is_empty() {
            return vec![];
        }

        let mut suggestions = Vec::new();
        let parts: Vec<&str> = input.split_whitespace().collect();

        if parts.is_empty() {
            return vec![];
        }

        let cmd = parts[0];
        let args = &parts[1..];

        // If command is already valid, no suggestions needed
        if self.known_commands.contains(cmd) {
            // But check for flag format issues
            suggestions.extend(self.check_flag_issues(input));
            return suggestions;
        }

        // Check for common typos first (fast path)
        if let Some(correction) = self.check_common_typos(cmd) {
            suggestions.push(Suggestion {
                command: self.rebuild_command(&correction, args),
                confidence: 0.95,
                reason: SuggestionReason::CommonTypo,
                distance: 1,
            });
        }

        // Check aliases
        if let Some(expanded) = self.aliases.get(cmd) {
            suggestions.push(Suggestion {
                command: self.rebuild_command(expanded, args),
                confidence: 0.9,
                reason: SuggestionReason::Alias,
                distance: 0,
            });
        }

        // Find similar commands using edit distance
        for known_cmd in &self.known_commands {
            let dist = levenshtein_distance(cmd, known_cmd);
            if dist > 0 && dist <= self.max_distance {
                let confidence = 1.0 - (dist as f64 / cmd.len().max(known_cmd.len()) as f64);
                suggestions.push(Suggestion {
                    command: self.rebuild_command(known_cmd, args),
                    confidence,
                    reason: SuggestionReason::SimilarCommand,
                    distance: dist,
                });
            }
        }

        // Check historical corrections
        for entry in &self.correction_history {
            if entry.accepted && entry.original == cmd {
                suggestions.push(Suggestion {
                    command: self.rebuild_command(&entry.corrected, args),
                    confidence: 0.85,
                    reason: SuggestionReason::Historical,
                    distance: levenshtein_distance(cmd, &entry.corrected),
                });
            }
        }

        // Check for missing sudo (permission denied patterns)
        if self.might_need_sudo(cmd) {
            suggestions.push(Suggestion {
                command: format!("sudo {}", input),
                confidence: 0.7,
                reason: SuggestionReason::MissingSudo,
                distance: 0,
            });
        }

        // Sort by confidence
        suggestions.sort_by(|a, b| b.confidence.partial_cmp(&a.confidence).unwrap());

        // Deduplicate
        let mut seen = HashSet::new();
        suggestions.retain(|s| seen.insert(s.command.clone()));

        // Return top suggestions
        suggestions.truncate(5);
        suggestions
    }

    /// Record a correction (for learning)
    pub fn record_correction(&mut self, original: &str, corrected: &str, accepted: bool) {
        self.correction_history.push(CorrectionEntry {
            original: original.to_string(),
            corrected: corrected.to_string(),
            accepted,
            timestamp: chrono::Utc::now(),
        });

        // Keep history bounded
        if self.correction_history.len() > 1000 {
            self.correction_history.remove(0);
        }
    }

    /// Get the best suggestion if confidence is high enough
    pub fn get_best_suggestion(&self, input: &str, min_confidence: f64) -> Option<Suggestion> {
        self.suggest(input)
            .into_iter()
            .find(|s| s.confidence >= min_confidence)
    }

    /// Suggest correction after "command not found" error
    pub fn suggest_after_error(&self, command: &str, error: &str) -> Vec<Suggestion> {
        let mut suggestions = self.suggest(command);

        // Add sudo suggestion if permission error
        if error.contains("permission denied") || error.contains("Permission denied") {
            suggestions.insert(0, Suggestion {
                command: format!("sudo {}", command),
                confidence: 0.9,
                reason: SuggestionReason::MissingSudo,
                distance: 0,
            });
        }

        suggestions
    }

    // Private methods

    fn add_common_commands(&mut self) {
        let commands = [
            // File operations
            "ls", "cd", "pwd", "mkdir", "rmdir", "rm", "cp", "mv", "touch", "cat",
            "head", "tail", "less", "more", "find", "grep", "sed", "awk", "sort",
            "uniq", "wc", "diff", "chmod", "chown", "ln",
            // Text processing
            "echo", "printf", "cut", "tr", "xargs", "tee",
            // System
            "ps", "top", "htop", "kill", "killall", "bg", "fg", "jobs", "nohup",
            "sudo", "su", "whoami", "id", "uname", "hostname", "uptime", "df", "du",
            "free", "mount", "umount",
            // Network
            "ping", "curl", "wget", "ssh", "scp", "rsync", "netstat", "ss", "ip",
            "ifconfig", "dig", "nslookup", "traceroute", "nc", "telnet",
            // Package managers
            "apt", "apt-get", "yum", "dnf", "pacman", "brew", "npm", "yarn", "pip",
            "pip3", "gem", "cargo", "go",
            // Git
            "git",
            // Docker
            "docker", "docker-compose", "kubectl", "helm",
            // Editors
            "vim", "vi", "nano", "emacs", "code",
            // Archives
            "tar", "gzip", "gunzip", "zip", "unzip", "bzip2",
            // Misc
            "man", "which", "whereis", "type", "alias", "history", "clear", "exit",
            "source", "export", "env", "set", "unset", "date", "cal", "bc",
        ];

        for cmd in commands {
            self.known_commands.insert(cmd.to_string());
        }
    }

    fn add_common_typos(&mut self) {
        let typos = [
            // Very common typos
            ("sl", "ls"),
            ("l", "ls"),
            ("ll", "ls -la"),
            ("la", "ls -la"),
            ("xs", "cd"),
            ("cd..", "cd .."),
            ("cd~", "cd ~"),
            ("grpe", "grep"),
            ("greop", "grep"),
            ("gerp", "grep"),
            ("gti", "git"),
            ("got", "git"),
            ("gi", "git"),
            ("tit", "git"),
            ("gitp", "git"),
            ("dokcer", "docker"),
            ("dcoker", "docker"),
            ("doker", "docker"),
            ("suod", "sudo"),
            ("sduo", "sudo"),
            ("sudp", "sudo"),
            ("mkdri", "mkdir"),
            ("mkdr", "mkdir"),
            ("mdkir", "mkdir"),
            ("cta", "cat"),
            ("act", "cat"),
            ("caT", "cat"),
            ("ehco", "echo"),
            ("ecoh", "echo"),
            ("ceho", "echo"),
            ("pign", "ping"),
            ("pnig", "ping"),
            ("sssh", "ssh"),
            ("shh", "ssh"),
            ("pytohn", "python"),
            ("pyhton", "python"),
            ("pytho", "python"),
            ("pyton", "python"),
            ("ndoe", "node"),
            ("noed", "node"),
            ("claer", "clear"),
            ("cealr", "clear"),
            ("clera", "clear"),
            ("exti", "exit"),
            ("eixt", "exit"),
            ("exut", "exit"),
            ("crul", "curl"),
            ("ucrl", "curl"),
            ("weget", "wget"),
            ("wgte", "wget"),
            ("tial", "tail"),
            ("tali", "tail"),
            ("haed", "head"),
            ("ehad", "head"),
            ("heda", "head"),
            ("killl", "kill"),
            ("kll", "kill"),
            ("killal", "killall"),
            ("rmr", "rm -r"),
            ("rm-rf", "rm -rf"),
            ("chmdo", "chmod"),
            ("chomd", "chmod"),
            ("chonw", "chown"),
            ("chwon", "chown"),
        ];

        for (typo, correction) in typos {
            self.typo_patterns.push(TypoPattern {
                typo: typo.to_string(),
                correction: correction.to_string(),
            });
        }
    }

    fn add_common_aliases(&mut self) {
        let aliases = [
            ("g", "git"),
            ("d", "docker"),
            ("dc", "docker-compose"),
            ("k", "kubectl"),
            ("py", "python"),
            ("py3", "python3"),
            ("n", "npm"),
            ("y", "yarn"),
            ("c", "cargo"),
            ("v", "vim"),
            ("nv", "nvim"),
            ("tf", "terraform"),
        ];

        for (alias, cmd) in aliases {
            self.aliases.insert(alias.to_string(), cmd.to_string());
        }
    }

    fn check_common_typos(&self, cmd: &str) -> Option<String> {
        for pattern in &self.typo_patterns {
            if pattern.typo == cmd {
                return Some(pattern.correction.clone());
            }
        }
        None
    }

    fn check_flag_issues(&self, input: &str) -> Vec<Suggestion> {
        let mut suggestions = Vec::new();

        // Check for common flag mistakes
        if input.contains("--help ") || input.ends_with("--help") {
            // --help is usually correct, no suggestion
        } else if input.contains(" -help") && !input.contains(" --help") {
            // Some commands use -help instead of --help
            let corrected = input.replace(" -help", " --help");
            suggestions.push(Suggestion {
                command: corrected,
                confidence: 0.7,
                reason: SuggestionReason::FlagFormat,
                distance: 1,
            });
        }

        // Check for missing space after flag
        let flag_pattern = regex::Regex::new(r"-(\w)(\S)").ok();
        if let Some(re) = flag_pattern {
            if re.is_match(input) && !input.contains("=-") {
                // Might be missing space, but this is often intentional (-rf, etc.)
                // Only suggest if it's unusual
            }
        }

        suggestions
    }

    fn might_need_sudo(&self, cmd: &str) -> bool {
        let sudo_commands = [
            "apt", "apt-get", "yum", "dnf", "pacman",
            "systemctl", "service",
            "mount", "umount",
            "fdisk", "mkfs",
            "iptables", "ufw",
            "useradd", "usermod", "userdel",
            "groupadd", "groupmod", "groupdel",
        ];
        sudo_commands.contains(&cmd)
    }

    fn rebuild_command(&self, cmd: &str, args: &[&str]) -> String {
        if args.is_empty() {
            cmd.to_string()
        } else {
            format!("{} {}", cmd, args.join(" "))
        }
    }
}

/// Calculate Levenshtein edit distance between two strings
fn levenshtein_distance(s1: &str, s2: &str) -> usize {
    let len1 = s1.len();
    let len2 = s2.len();

    if len1 == 0 {
        return len2;
    }
    if len2 == 0 {
        return len1;
    }

    let s1_chars: Vec<char> = s1.chars().collect();
    let s2_chars: Vec<char> = s2.chars().collect();

    let mut matrix = vec![vec![0usize; len2 + 1]; len1 + 1];

    for i in 0..=len1 {
        matrix[i][0] = i;
    }
    for j in 0..=len2 {
        matrix[0][j] = j;
    }

    for i in 1..=len1 {
        for j in 1..=len2 {
            let cost = if s1_chars[i - 1] == s2_chars[j - 1] { 0 } else { 1 };
            matrix[i][j] = (matrix[i - 1][j] + 1)
                .min(matrix[i][j - 1] + 1)
                .min(matrix[i - 1][j - 1] + cost);
        }
    }

    matrix[len1][len2]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_typo() {
        let ac = Autocorrect::new();
        let suggestions = ac.suggest("sl");

        assert!(!suggestions.is_empty());
        assert_eq!(suggestions[0].command, "ls");
        assert!(suggestions[0].confidence > 0.9);
    }

    #[test]
    fn test_git_typo() {
        let ac = Autocorrect::new();
        let suggestions = ac.suggest("gti status");

        assert!(!suggestions.is_empty());
        assert_eq!(suggestions[0].command, "git status");
    }

    #[test]
    fn test_similar_command() {
        let ac = Autocorrect::new();
        let suggestions = ac.suggest("caat file.txt");

        assert!(!suggestions.is_empty());
        // Should suggest 'cat file.txt'
        assert!(suggestions.iter().any(|s| s.command.starts_with("cat")));
    }

    #[test]
    fn test_valid_command_no_suggestions() {
        let ac = Autocorrect::new();
        let suggestions = ac.suggest("ls -la");

        // Should be empty or only contain flag suggestions
        assert!(suggestions.is_empty() ||
                suggestions.iter().all(|s| s.reason == SuggestionReason::FlagFormat));
    }

    #[test]
    fn test_levenshtein() {
        assert_eq!(levenshtein_distance("cat", "cat"), 0);
        assert_eq!(levenshtein_distance("cat", "cta"), 2);
        assert_eq!(levenshtein_distance("cat", "cut"), 1);
        assert_eq!(levenshtein_distance("", "abc"), 3);
        assert_eq!(levenshtein_distance("abc", ""), 3);
    }

    #[test]
    fn test_alias() {
        let ac = Autocorrect::new();
        let suggestions = ac.suggest("g status");

        assert!(!suggestions.is_empty());
        assert!(suggestions.iter().any(|s| s.command == "git status"));
    }

    #[test]
    fn test_sudo_suggestion() {
        let ac = Autocorrect::new();
        let suggestions = ac.suggest("apt update");

        assert!(suggestions.iter().any(|s|
            s.command == "sudo apt update" &&
            s.reason == SuggestionReason::MissingSudo
        ));
    }

    #[test]
    fn test_record_correction() {
        let mut ac = Autocorrect::new();
        ac.record_correction("mykustomcmd", "mycustomcmd", true);

        // Later, the same typo should get a historical suggestion
        let suggestions = ac.suggest("mykustomcmd");
        assert!(suggestions.iter().any(|s|
            s.command == "mycustomcmd" &&
            s.reason == SuggestionReason::Historical
        ));
    }

    #[test]
    fn test_disabled() {
        let mut ac = Autocorrect::new();
        ac.set_enabled(false);

        let suggestions = ac.suggest("sl");
        assert!(suggestions.is_empty());
    }
}
