// Multi-File Atomic Edit - Transaction-style Editing
//
// Edit multiple files as a single atomic operation.
// Either all edits succeed, or all are rolled back.
// Claude Code style with full undo support.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MultiEditTransaction {
    pub id: String,
    pub description: Option<String>,
    pub edits: Vec<FileEdit>,
    pub created_at: i64,
    pub status: TransactionStatus,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum TransactionStatus {
    Pending,
    InProgress,
    Completed,
    RolledBack,
    Failed(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FileEdit {
    pub file_path: String,
    pub edit_type: EditType,
    pub backup_path: Option<String>,
    pub applied: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum EditType {
    Replace { old_content: String, new_content: String },
    ReplaceAll { old_content: String, new_content: String },
    ReplaceLine { line_number: usize, new_content: String },
    InsertAfter { line_number: usize, content: String },
    InsertBefore { line_number: usize, content: String },
    DeleteLines { start: usize, end: usize },
    Append { content: String },
    Prepend { content: String },
    Create { content: String },
    Delete,
    Rename { new_path: String },
    RegexReplace { pattern: String, replacement: String, all: bool },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TransactionResult {
    pub success: bool,
    pub transaction_id: String,
    pub files_modified: usize,
    pub files_created: usize,
    pub files_deleted: usize,
    pub errors: Vec<String>,
    pub can_rollback: bool,
}

// =============================================================================
// MULTI EDIT ENGINE
// =============================================================================

pub struct MultiEditEngine {
    backup_dir: PathBuf,
    transactions: HashMap<String, MultiEditTransaction>,
    max_transactions: usize,
}

impl MultiEditEngine {
    pub fn new() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let backup_dir = PathBuf::from(format!("{}/.sam/multi_edit_backups", home));
        let _ = fs::create_dir_all(&backup_dir);

        Self {
            backup_dir,
            transactions: HashMap::new(),
            max_transactions: 50,
        }
    }

    // Create a new transaction
    pub fn begin(&mut self, description: Option<&str>) -> String {
        let id = format!("txn_{}", chrono::Utc::now().timestamp_millis());

        let transaction = MultiEditTransaction {
            id: id.clone(),
            description: description.map(|s| s.to_string()),
            edits: Vec::new(),
            created_at: chrono::Utc::now().timestamp(),
            status: TransactionStatus::Pending,
        };

        self.transactions.insert(id.clone(), transaction);
        self.cleanup_old_transactions();

        id
    }

    // Add an edit to the transaction
    pub fn add_edit(&mut self, transaction_id: &str, file_path: &str, edit_type: EditType) -> Result<(), String> {
        let transaction = self.transactions.get_mut(transaction_id)
            .ok_or_else(|| "Transaction not found".to_string())?;

        match &transaction.status {
            TransactionStatus::Pending => {}
            _ => return Err("Transaction already executed or rolled back".to_string()),
        }

        transaction.edits.push(FileEdit {
            file_path: file_path.to_string(),
            edit_type,
            backup_path: None,
            applied: false,
        });

        Ok(())
    }

    // Execute the transaction atomically
    pub fn commit(&mut self, transaction_id: &str) -> TransactionResult {
        // Check if transaction exists and set to InProgress
        {
            let transaction = match self.transactions.get_mut(transaction_id) {
                Some(t) => t,
                None => return TransactionResult {
                    success: false,
                    transaction_id: transaction_id.to_string(),
                    files_modified: 0,
                    files_created: 0,
                    files_deleted: 0,
                    errors: vec!["Transaction not found".to_string()],
                    can_rollback: false,
                },
            };
            transaction.status = TransactionStatus::InProgress;
        }

        let mut files_modified = 0;
        let mut files_created = 0;
        let mut files_deleted = 0;
        let mut errors = Vec::new();
        let mut applied_indices = Vec::new();
        let mut backup_paths: Vec<(usize, String)> = Vec::new();

        // Phase 1: Backup all files that will be modified
        let edit_count = self.transactions.get(transaction_id)
            .map(|t| t.edits.len())
            .unwrap_or(0);

        for i in 0..edit_count {
            let (file_path, file_exists) = {
                let transaction = self.transactions.get(transaction_id).unwrap();
                let edit = &transaction.edits[i];
                let path = Path::new(&edit.file_path);
                (edit.file_path.clone(), path.exists())
            };

            if file_exists {
                let path = Path::new(&file_path);
                let backup_path = self.backup_dir.join(format!(
                    "{}_{}_{}",
                    transaction_id,
                    i,
                    path.file_name().unwrap_or_default().to_string_lossy()
                ));

                if let Err(e) = fs::copy(&path, &backup_path) {
                    errors.push(format!("Failed to backup {}: {}", file_path, e));
                    self.rollback_partial(transaction_id, &applied_indices);
                    if let Some(t) = self.transactions.get_mut(transaction_id) {
                        t.status = TransactionStatus::Failed(errors.join("; "));
                    }
                    return TransactionResult {
                        success: false,
                        transaction_id: transaction_id.to_string(),
                        files_modified: 0,
                        files_created: 0,
                        files_deleted: 0,
                        errors,
                        can_rollback: false,
                    };
                }

                backup_paths.push((i, backup_path.to_string_lossy().to_string()));
            }
        }

        // Store backup paths
        for (i, backup_path) in backup_paths {
            if let Some(t) = self.transactions.get_mut(transaction_id) {
                t.edits[i].backup_path = Some(backup_path);
            }
        }

        // Phase 2: Apply all edits
        for i in 0..edit_count {
            let edit = {
                let transaction = self.transactions.get(transaction_id).unwrap();
                transaction.edits[i].clone()
            };

            match Self::apply_edit_static(&edit) {
                Ok(result) => {
                    if let Some(t) = self.transactions.get_mut(transaction_id) {
                        t.edits[i].applied = true;
                    }
                    applied_indices.push(i);

                    match result {
                        ApplyResult::Modified => files_modified += 1,
                        ApplyResult::Created => files_created += 1,
                        ApplyResult::Deleted => files_deleted += 1,
                    }
                }
                Err(e) => {
                    let file_path = {
                        self.transactions.get(transaction_id)
                            .map(|t| t.edits[i].file_path.clone())
                            .unwrap_or_default()
                    };
                    errors.push(format!("{}: {}", file_path, e));
                    self.rollback_partial(transaction_id, &applied_indices);
                    if let Some(t) = self.transactions.get_mut(transaction_id) {
                        t.status = TransactionStatus::Failed(errors.join("; "));
                    }
                    return TransactionResult {
                        success: false,
                        transaction_id: transaction_id.to_string(),
                        files_modified: 0,
                        files_created: 0,
                        files_deleted: 0,
                        errors,
                        can_rollback: false,
                    };
                }
            }
        }

        if let Some(t) = self.transactions.get_mut(transaction_id) {
            t.status = TransactionStatus::Completed;
        }

        TransactionResult {
            success: true,
            transaction_id: transaction_id.to_string(),
            files_modified,
            files_created,
            files_deleted,
            errors,
            can_rollback: true,
        }
    }

    // Apply a single edit (static method to avoid borrow issues)
    fn apply_edit_static(edit: &FileEdit) -> Result<ApplyResult, String> {
        let path = Path::new(&edit.file_path);

        match &edit.edit_type {
            EditType::Replace { old_content, new_content } => {
                let content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let count = content.matches(old_content).count();
                if count == 0 {
                    return Err("Content not found".to_string());
                }
                if count > 1 {
                    return Err(format!("Content found {} times (must be unique)", count));
                }

                let new_file_content = content.replacen(old_content, new_content, 1);
                fs::write(path, new_file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::ReplaceAll { old_content, new_content } => {
                let content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let new_file_content = content.replace(old_content, new_content);
                fs::write(path, new_file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::ReplaceLine { line_number, new_content } => {
                let content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let mut lines: Vec<&str> = content.lines().collect();
                let idx = line_number.saturating_sub(1);

                if idx >= lines.len() {
                    return Err(format!("Line {} doesn't exist (file has {} lines)", line_number, lines.len()));
                }

                lines[idx] = new_content;
                let new_file_content = lines.join("\n");
                fs::write(path, new_file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::InsertAfter { line_number, content } => {
                let file_content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let mut lines: Vec<&str> = file_content.lines().collect();
                let idx = *line_number; // Insert after this line (0 = beginning)

                if idx > lines.len() {
                    return Err(format!("Line {} doesn't exist", line_number));
                }

                let insert_lines: Vec<&str> = content.lines().collect();
                for (i, line) in insert_lines.into_iter().enumerate() {
                    lines.insert(idx + i, line);
                }

                let new_file_content = lines.join("\n");
                fs::write(path, new_file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::InsertBefore { line_number, content } => {
                let file_content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let mut lines: Vec<&str> = file_content.lines().collect();
                let idx = line_number.saturating_sub(1);

                if idx > lines.len() {
                    return Err(format!("Line {} doesn't exist", line_number));
                }

                let insert_lines: Vec<&str> = content.lines().collect();
                for (i, line) in insert_lines.into_iter().enumerate() {
                    lines.insert(idx + i, line);
                }

                let new_file_content = lines.join("\n");
                fs::write(path, new_file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::DeleteLines { start, end } => {
                let file_content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let lines: Vec<&str> = file_content.lines().collect();
                let start_idx = start.saturating_sub(1);
                let end_idx = (*end).min(lines.len());

                if start_idx >= lines.len() {
                    return Err(format!("Start line {} doesn't exist", start));
                }

                let new_lines: Vec<&str> = lines.iter()
                    .enumerate()
                    .filter(|(i, _)| *i < start_idx || *i >= end_idx)
                    .map(|(_, line)| *line)
                    .collect();

                let new_file_content = new_lines.join("\n");
                fs::write(path, new_file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::Append { content } => {
                let mut file_content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                if !file_content.ends_with('\n') && !file_content.is_empty() {
                    file_content.push('\n');
                }
                file_content.push_str(content);

                fs::write(path, file_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::Prepend { content } => {
                let file_content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let new_content = if content.ends_with('\n') {
                    format!("{}{}", content, file_content)
                } else {
                    format!("{}\n{}", content, file_content)
                };

                fs::write(path, new_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::Create { content } => {
                if path.exists() {
                    return Err("File already exists".to_string());
                }

                if let Some(parent) = path.parent() {
                    fs::create_dir_all(parent)
                        .map_err(|e| format!("Failed to create directory: {}", e))?;
                }

                fs::write(path, content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Created)
            }

            EditType::Delete => {
                if !path.exists() {
                    return Err("File doesn't exist".to_string());
                }

                fs::remove_file(path)
                    .map_err(|e| format!("Delete error: {}", e))?;

                Ok(ApplyResult::Deleted)
            }

            EditType::Rename { new_path } => {
                if !path.exists() {
                    return Err("Source file doesn't exist".to_string());
                }

                let new_path = Path::new(new_path);
                if new_path.exists() {
                    return Err("Destination already exists".to_string());
                }

                if let Some(parent) = new_path.parent() {
                    fs::create_dir_all(parent)
                        .map_err(|e| format!("Failed to create directory: {}", e))?;
                }

                fs::rename(path, new_path)
                    .map_err(|e| format!("Rename error: {}", e))?;

                Ok(ApplyResult::Modified)
            }

            EditType::RegexReplace { pattern, replacement, all } => {
                let content = fs::read_to_string(path)
                    .map_err(|e| format!("Read error: {}", e))?;

                let re = regex::Regex::new(pattern)
                    .map_err(|e| format!("Invalid regex: {}", e))?;

                let new_content = if *all {
                    re.replace_all(&content, replacement.as_str()).to_string()
                } else {
                    re.replace(&content, replacement.as_str()).to_string()
                };

                fs::write(path, new_content)
                    .map_err(|e| format!("Write error: {}", e))?;

                Ok(ApplyResult::Modified)
            }
        }
    }

    // Rollback partial transaction (for error recovery)
    fn rollback_partial(&self, transaction_id: &str, applied_indices: &[usize]) {
        if let Some(transaction) = self.transactions.get(transaction_id) {
            for &i in applied_indices.iter().rev() {
                if let Some(edit) = transaction.edits.get(i) {
                    if let Some(backup_path) = &edit.backup_path {
                        let _ = fs::copy(backup_path, &edit.file_path);
                    } else if let EditType::Create { .. } = &edit.edit_type {
                        // Delete created file
                        let _ = fs::remove_file(&edit.file_path);
                    }
                }
            }
        }
    }

    // Rollback entire transaction
    pub fn rollback(&mut self, transaction_id: &str) -> Result<(), String> {
        let transaction = self.transactions.get_mut(transaction_id)
            .ok_or_else(|| "Transaction not found".to_string())?;

        match &transaction.status {
            TransactionStatus::Completed => {}
            _ => return Err("Can only rollback completed transactions".to_string()),
        }

        // Restore all backups in reverse order
        for edit in transaction.edits.iter().rev() {
            if edit.applied {
                if let Some(backup_path) = &edit.backup_path {
                    fs::copy(backup_path, &edit.file_path)
                        .map_err(|e| format!("Rollback failed for {}: {}", edit.file_path, e))?;
                } else if let EditType::Create { .. } = &edit.edit_type {
                    // Delete created file
                    let _ = fs::remove_file(&edit.file_path);
                }
            }
        }

        transaction.status = TransactionStatus::RolledBack;
        Ok(())
    }

    // Get transaction status
    pub fn status(&self, transaction_id: &str) -> Option<&TransactionStatus> {
        self.transactions.get(transaction_id).map(|t| &t.status)
    }

    // List recent transactions
    pub fn list_transactions(&self) -> Vec<&MultiEditTransaction> {
        let mut txns: Vec<_> = self.transactions.values().collect();
        txns.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        txns
    }

    // Cleanup old transactions and backups
    fn cleanup_old_transactions(&mut self) {
        if self.transactions.len() > self.max_transactions {
            let mut txns: Vec<_> = self.transactions.iter().collect();
            txns.sort_by(|a, b| a.1.created_at.cmp(&b.1.created_at));

            // Remove oldest transactions
            let to_remove: Vec<_> = txns.iter()
                .take(self.transactions.len() - self.max_transactions)
                .map(|(id, _)| id.to_string())
                .collect();

            for id in to_remove {
                // Clean up backup files
                if let Some(txn) = self.transactions.get(&id) {
                    for edit in &txn.edits {
                        if let Some(backup) = &edit.backup_path {
                            let _ = fs::remove_file(backup);
                        }
                    }
                }
                self.transactions.remove(&id);
            }
        }
    }
}

enum ApplyResult {
    Modified,
    Created,
    Deleted,
}

// =============================================================================
// BUILDER API (Fluent interface)
// =============================================================================

pub struct TransactionBuilder<'a> {
    engine: &'a mut MultiEditEngine,
    transaction_id: String,
}

impl<'a> TransactionBuilder<'a> {
    pub fn new(engine: &'a mut MultiEditEngine, description: Option<&str>) -> Self {
        let transaction_id = engine.begin(description);
        Self { engine, transaction_id }
    }

    pub fn replace(self, file: &str, old: &str, new: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::Replace {
            old_content: old.to_string(),
            new_content: new.to_string(),
        });
        self
    }

    pub fn replace_all(self, file: &str, old: &str, new: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::ReplaceAll {
            old_content: old.to_string(),
            new_content: new.to_string(),
        });
        self
    }

    pub fn replace_line(self, file: &str, line: usize, content: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::ReplaceLine {
            line_number: line,
            new_content: content.to_string(),
        });
        self
    }

    pub fn insert_after(self, file: &str, line: usize, content: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::InsertAfter {
            line_number: line,
            content: content.to_string(),
        });
        self
    }

    pub fn delete_lines(self, file: &str, start: usize, end: usize) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::DeleteLines { start, end });
        self
    }

    pub fn create(self, file: &str, content: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::Create {
            content: content.to_string(),
        });
        self
    }

    pub fn delete(self, file: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::Delete);
        self
    }

    pub fn rename(self, file: &str, new_path: &str) -> Self {
        let _ = self.engine.add_edit(&self.transaction_id, file, EditType::Rename {
            new_path: new_path.to_string(),
        });
        self
    }

    pub fn commit(self) -> TransactionResult {
        self.engine.commit(&self.transaction_id)
    }

    pub fn id(&self) -> &str {
        &self.transaction_id
    }
}

// Global engine
lazy_static::lazy_static! {
    pub static ref MULTI_EDIT: std::sync::Mutex<MultiEditEngine> =
        std::sync::Mutex::new(MultiEditEngine::new());
}

pub fn multi_edit() -> std::sync::MutexGuard<'static, MultiEditEngine> {
    MULTI_EDIT.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_transaction_builder() {
        let mut engine = MultiEditEngine::new();

        // This would fail without actual files, but tests the API
        let txn_id = engine.begin(Some("Test transaction"));
        assert!(!txn_id.is_empty());
        assert!(matches!(engine.status(&txn_id), Some(TransactionStatus::Pending)));
    }
}
