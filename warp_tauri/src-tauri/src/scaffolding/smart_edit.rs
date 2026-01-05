// Smart Edit - Claude Code Style File Editing
//
// Supports:
// - Exact string replacement (like Claude's Edit tool)
// - Line-based editing
// - Pattern-based (regex) editing
// - Safe atomic writes with backup

use serde::{Deserialize, Serialize};
use std::fs;
use std::path::Path;

// =============================================================================
// EDIT OPERATIONS
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EditOperation {
    pub file_path: String,
    pub edit_type: EditType,
    pub old_content: Option<String>,
    pub new_content: String,
    pub line_number: Option<usize>,
    pub replace_all: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum EditType {
    /// Replace exact string match (Claude Code style)
    ExactReplace,
    /// Replace line at specific number
    ReplaceLine,
    /// Insert after line
    InsertAfter,
    /// Insert before line
    InsertBefore,
    /// Delete lines
    DeleteLines,
    /// Regex replacement
    RegexReplace,
    /// Append to end of file
    Append,
    /// Prepend to start of file
    Prepend,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EditResult {
    pub success: bool,
    pub file_path: String,
    pub backup_path: Option<String>,
    pub changes_made: usize,
    pub message: String,
    pub diff: Option<String>,
}

// =============================================================================
// SMART EDITOR
// =============================================================================

pub struct SmartEditor;

impl SmartEditor {
    /// Claude Code style exact replacement
    /// Fails if old_content is not unique (or not found)
    pub fn exact_replace(
        file_path: &str,
        old_content: &str,
        new_content: &str,
        replace_all: bool,
    ) -> EditResult {
        // Read file
        let content = match fs::read_to_string(file_path) {
            Ok(c) => c,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: None,
                    changes_made: 0,
                    message: format!("Failed to read file: {}", e),
                    diff: None,
                };
            }
        };

        // Count occurrences
        let count = content.matches(old_content).count();

        if count == 0 {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: "old_content not found in file".to_string(),
                diff: None,
            };
        }

        if count > 1 && !replace_all {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: format!(
                    "old_content found {} times. Use replace_all=true or provide more context",
                    count
                ),
                diff: None,
            };
        }

        // Create backup
        let backup_path = Self::create_backup(file_path);

        // Perform replacement
        let new_file_content = if replace_all {
            content.replace(old_content, new_content)
        } else {
            content.replacen(old_content, new_content, 1)
        };

        // Write file
        if let Err(e) = fs::write(file_path, &new_file_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path,
                changes_made: 0,
                message: format!("Failed to write file: {}", e),
                diff: None,
            };
        }

        // Generate diff
        let diff = Self::generate_diff(&content, &new_file_content);

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path,
            changes_made: if replace_all { count } else { 1 },
            message: format!("Replaced {} occurrence(s)", if replace_all { count } else { 1 }),
            diff: Some(diff),
        }
    }

    /// Replace specific line
    pub fn replace_line(file_path: &str, line_number: usize, new_content: &str) -> EditResult {
        let content = match fs::read_to_string(file_path) {
            Ok(c) => c,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: None,
                    changes_made: 0,
                    message: format!("Failed to read file: {}", e),
                    diff: None,
                };
            }
        };

        let mut lines: Vec<&str> = content.lines().collect();

        if line_number == 0 || line_number > lines.len() {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: format!("Line {} out of range (file has {} lines)", line_number, lines.len()),
                diff: None,
            };
        }

        let backup_path = Self::create_backup(file_path);

        let old_line = lines[line_number - 1];
        lines[line_number - 1] = new_content;

        let new_file_content = lines.join("\n");

        if let Err(e) = fs::write(file_path, &new_file_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path,
                changes_made: 0,
                message: format!("Failed to write file: {}", e),
                diff: None,
            };
        }

        let diff = format!("-{}: {}\n+{}: {}", line_number, old_line, line_number, new_content);

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path,
            changes_made: 1,
            message: format!("Replaced line {}", line_number),
            diff: Some(diff),
        }
    }

    /// Insert content after a specific line
    pub fn insert_after(file_path: &str, line_number: usize, new_content: &str) -> EditResult {
        let content = match fs::read_to_string(file_path) {
            Ok(c) => c,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: None,
                    changes_made: 0,
                    message: format!("Failed to read file: {}", e),
                    diff: None,
                };
            }
        };

        let mut lines: Vec<&str> = content.lines().collect();

        if line_number > lines.len() {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: format!("Line {} out of range (file has {} lines)", line_number, lines.len()),
                diff: None,
            };
        }

        let backup_path = Self::create_backup(file_path);

        // Insert new lines
        let new_lines: Vec<&str> = new_content.lines().collect();
        let insert_pos = line_number; // After line N means index N
        for (i, new_line) in new_lines.iter().enumerate() {
            lines.insert(insert_pos + i, new_line);
        }

        let new_file_content = lines.join("\n");

        if let Err(e) = fs::write(file_path, &new_file_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path,
                changes_made: 0,
                message: format!("Failed to write file: {}", e),
                diff: None,
            };
        }

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path,
            changes_made: new_lines.len(),
            message: format!("Inserted {} line(s) after line {}", new_lines.len(), line_number),
            diff: Some(format!("+{} line(s) after line {}", new_lines.len(), line_number)),
        }
    }

    /// Delete lines in range
    pub fn delete_lines(file_path: &str, start: usize, end: usize) -> EditResult {
        let content = match fs::read_to_string(file_path) {
            Ok(c) => c,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: None,
                    changes_made: 0,
                    message: format!("Failed to read file: {}", e),
                    diff: None,
                };
            }
        };

        let lines: Vec<&str> = content.lines().collect();

        if start == 0 || end > lines.len() || start > end {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: format!("Invalid line range {}-{} (file has {} lines)", start, end, lines.len()),
                diff: None,
            };
        }

        let backup_path = Self::create_backup(file_path);

        let deleted: Vec<&str> = lines[start - 1..end].to_vec();
        let mut new_lines: Vec<&str> = lines[..start - 1].to_vec();
        new_lines.extend(&lines[end..]);

        let new_file_content = new_lines.join("\n");

        if let Err(e) = fs::write(file_path, &new_file_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path,
                changes_made: 0,
                message: format!("Failed to write file: {}", e),
                diff: None,
            };
        }

        let diff = deleted.iter()
            .enumerate()
            .map(|(i, line)| format!("-{}: {}", start + i, line))
            .collect::<Vec<_>>()
            .join("\n");

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path,
            changes_made: deleted.len(),
            message: format!("Deleted {} line(s)", deleted.len()),
            diff: Some(diff),
        }
    }

    /// Regex-based replacement
    pub fn regex_replace(
        file_path: &str,
        pattern: &str,
        replacement: &str,
        replace_all: bool,
    ) -> EditResult {
        let content = match fs::read_to_string(file_path) {
            Ok(c) => c,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: None,
                    changes_made: 0,
                    message: format!("Failed to read file: {}", e),
                    diff: None,
                };
            }
        };

        let re = match regex::Regex::new(pattern) {
            Ok(r) => r,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: None,
                    changes_made: 0,
                    message: format!("Invalid regex: {}", e),
                    diff: None,
                };
            }
        };

        let count = re.find_iter(&content).count();

        if count == 0 {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: "Pattern not found in file".to_string(),
                diff: None,
            };
        }

        let backup_path = Self::create_backup(file_path);

        let new_file_content = if replace_all {
            re.replace_all(&content, replacement).to_string()
        } else {
            re.replace(&content, replacement).to_string()
        };

        if let Err(e) = fs::write(file_path, &new_file_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path,
                changes_made: 0,
                message: format!("Failed to write file: {}", e),
                diff: None,
            };
        }

        let diff = Self::generate_diff(&content, &new_file_content);

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path,
            changes_made: if replace_all { count } else { 1 },
            message: format!("Replaced {} match(es)", if replace_all { count } else { 1 }),
            diff: Some(diff),
        }
    }

    /// Append to end of file
    pub fn append(file_path: &str, content: &str) -> EditResult {
        let existing = fs::read_to_string(file_path).unwrap_or_default();
        let backup_path = Self::create_backup(file_path);

        let new_content = if existing.ends_with('\n') || existing.is_empty() {
            format!("{}{}", existing, content)
        } else {
            format!("{}\n{}", existing, content)
        };

        if let Err(e) = fs::write(file_path, &new_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path,
                changes_made: 0,
                message: format!("Failed to write file: {}", e),
                diff: None,
            };
        }

        let lines_added = content.lines().count();

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path,
            changes_made: lines_added,
            message: format!("Appended {} line(s)", lines_added),
            diff: Some(format!("+{} line(s) at end", lines_added)),
        }
    }

    /// Create a new file (fails if exists)
    pub fn create_file(file_path: &str, content: &str) -> EditResult {
        if Path::new(file_path).exists() {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: "File already exists. Use edit to modify.".to_string(),
                diff: None,
            };
        }

        // Create parent directories
        if let Some(parent) = Path::new(file_path).parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Err(e) = fs::write(file_path, content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: format!("Failed to create file: {}", e),
                diff: None,
            };
        }

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path: None,
            changes_made: content.lines().count(),
            message: "File created".to_string(),
            diff: None,
        }
    }

    /// Undo last edit (restore from backup)
    pub fn undo(file_path: &str) -> EditResult {
        let backup_path = Self::get_backup_path(file_path);

        if !Path::new(&backup_path).exists() {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: None,
                changes_made: 0,
                message: "No backup found for this file".to_string(),
                diff: None,
            };
        }

        let backup_content = match fs::read_to_string(&backup_path) {
            Ok(c) => c,
            Err(e) => {
                return EditResult {
                    success: false,
                    file_path: file_path.to_string(),
                    backup_path: Some(backup_path),
                    changes_made: 0,
                    message: format!("Failed to read backup: {}", e),
                    diff: None,
                };
            }
        };

        if let Err(e) = fs::write(file_path, &backup_content) {
            return EditResult {
                success: false,
                file_path: file_path.to_string(),
                backup_path: Some(backup_path),
                changes_made: 0,
                message: format!("Failed to restore: {}", e),
                diff: None,
            };
        }

        // Remove backup after successful restore
        let _ = fs::remove_file(&backup_path);

        EditResult {
            success: true,
            file_path: file_path.to_string(),
            backup_path: None,
            changes_made: 1,
            message: "Restored from backup".to_string(),
            diff: None,
        }
    }

    // Helper: Create backup
    fn create_backup(file_path: &str) -> Option<String> {
        let backup_path = Self::get_backup_path(file_path);

        if let Some(parent) = Path::new(&backup_path).parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Ok(content) = fs::read_to_string(file_path) {
            if fs::write(&backup_path, content).is_ok() {
                return Some(backup_path);
            }
        }

        None
    }

    fn get_backup_path(file_path: &str) -> String {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let file_name = Path::new(file_path)
            .file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| "unknown".to_string());

        format!("{}/.sam/backups/{}.bak", home, file_name)
    }

    // Helper: Generate simple diff
    fn generate_diff(old: &str, new: &str) -> String {
        let old_lines: Vec<&str> = old.lines().collect();
        let new_lines: Vec<&str> = new.lines().collect();

        let mut diff = Vec::new();
        let mut i = 0;
        let mut j = 0;

        while i < old_lines.len() || j < new_lines.len() {
            if i < old_lines.len() && j < new_lines.len() {
                if old_lines[i] == new_lines[j] {
                    i += 1;
                    j += 1;
                } else {
                    diff.push(format!("-{}: {}", i + 1, old_lines[i]));
                    diff.push(format!("+{}: {}", j + 1, new_lines[j]));
                    i += 1;
                    j += 1;
                }
            } else if i < old_lines.len() {
                diff.push(format!("-{}: {}", i + 1, old_lines[i]));
                i += 1;
            } else {
                diff.push(format!("+{}: {}", j + 1, new_lines[j]));
                j += 1;
            }
        }

        diff.join("\n")
    }
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn test_exact_replace() {
        let path = "/tmp/test_edit.txt";
        fs::write(path, "hello world\nfoo bar\nhello again").unwrap();

        let result = SmartEditor::exact_replace(path, "foo bar", "baz qux", false);
        assert!(result.success);
        assert_eq!(result.changes_made, 1);

        let content = fs::read_to_string(path).unwrap();
        assert!(content.contains("baz qux"));
        assert!(!content.contains("foo bar"));

        fs::remove_file(path).ok();
    }

    #[test]
    fn test_replace_line() {
        let path = "/tmp/test_edit2.txt";
        fs::write(path, "line 1\noriginal line 2\nline 3").unwrap();

        let result = SmartEditor::replace_line(path, 2, "replaced second line");
        assert!(result.success);

        let content = fs::read_to_string(path).unwrap();
        assert!(content.contains("replaced second line"));
        assert!(!content.contains("original line 2"));

        fs::remove_file(path).ok();
    }
}
