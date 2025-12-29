//! journalStore - persistent JSON journal for AI actions with undo support
//! Stores to: ~/.warp_open/warp_history.json

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use serde_json::Value as JsonValue;
use std::path::PathBuf;
use tokio::fs;
use tokio::sync::Mutex;

use crate::fs_ops::make_id;

/// Location of the journal store
fn get_store_path() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| "/tmp".to_string());
    PathBuf::from(home)
        .join(".warp_open")
        .join("warp_history.json")
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JournalEntry {
    pub id: String,
    pub timestamp: DateTime<Utc>,
    #[serde(rename = "type")]
    pub entry_type: String,
    pub summary: String,
    #[serde(default)]
    pub payload: JsonValue,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct JournalStore {
    entries: Vec<JournalEntry>,
}

impl Default for JournalStore {
    fn default() -> Self {
        Self {
            entries: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UndoResult {
    pub ok: bool,
    pub undone: Option<JournalEntry>,
    pub error: Option<String>,
}

/// Journal manager with thread-safe access
pub struct Journal {
    store_path: PathBuf,
    // Mutex for safe concurrent access in async context
    _lock: Mutex<()>,
}

impl Journal {
    pub fn new() -> Self {
        Self {
            store_path: get_store_path(),
            _lock: Mutex::new(()),
        }
    }

    /// Create a new Journal with a custom path (useful for testing)
    pub fn new_with_path(path: PathBuf) -> Self {
        Self {
            store_path: path,
            _lock: Mutex::new(()),
        }
    }

    /// Ensure store directory and file exist
    async fn ensure_store(&self) -> Result<()> {
        if let Some(parent) = self.store_path.parent() {
            fs::create_dir_all(parent)
                .await
                .context("Failed to create journal directory")?;
        }

        if !self.store_path.exists() {
            let empty_store = JournalStore::default();
            let json = serde_json::to_string_pretty(&empty_store)?;
            fs::write(&self.store_path, json)
                .await
                .context("Failed to initialize journal store")?;
        }

        Ok(())
    }

    /// Load the journal store from disk
    async fn load_store(&self) -> Result<JournalStore> {
        self.ensure_store().await?;

        let content = fs::read_to_string(&self.store_path)
            .await
            .context("Failed to read journal store")?;

        let store: JournalStore = serde_json::from_str(&content)
            .context("Failed to parse journal store")?;

        Ok(store)
    }

    /// Save the journal store to disk
    async fn save_store(&self, store: &JournalStore) -> Result<()> {
        self.ensure_store().await?;

        let json = serde_json::to_string_pretty(store)
            .context("Failed to serialize journal store")?;

        fs::write(&self.store_path, json)
            .await
            .context("Failed to write journal store")?;

        Ok(())
    }

    /// Log a new action to the journal
    pub async fn log_action(
        &self,
        entry_type: impl Into<String>,
        summary: impl Into<String>,
        payload: Option<JsonValue>,
    ) -> Result<JournalEntry> {
        let _guard = self._lock.lock().await;

        let mut store = self.load_store().await?;

        let entry = JournalEntry {
            id: make_id("action"),
            timestamp: Utc::now(),
            entry_type: entry_type.into(),
            summary: summary.into(),
            payload: payload.unwrap_or(JsonValue::Null),
        };

        // Insert at front (newest first)
        store.entries.insert(0, entry.clone());

        self.save_store(&store).await?;

        Ok(entry)
    }

    /// Get journal entries with pagination
    pub async fn get_entries(&self, offset: usize, limit: usize) -> Result<Vec<JournalEntry>> {
        let _guard = self._lock.lock().await;

        let store = self.load_store().await?;
        let end = (offset + limit).min(store.entries.len());

        Ok(store.entries[offset..end].to_vec())
    }

    /// Undo the last action by removing it from the journal
    pub async fn undo_last(&self) -> UndoResult {
        let _guard = self._lock.lock().await;

        let mut store = match self.load_store().await {
            Ok(s) => s,
            Err(e) => {
                return UndoResult {
                    ok: false,
                    undone: None,
                    error: Some(e.to_string()),
                }
            }
        };

        if store.entries.is_empty() {
            return UndoResult {
                ok: false,
                undone: None,
                error: Some("no-actions".to_string()),
            };
        }

        let last = store.entries.remove(0);

        if let Err(e) = self.save_store(&store).await {
            return UndoResult {
                ok: false,
                undone: None,
                error: Some(e.to_string()),
            };
        }

        UndoResult {
            ok: true,
            undone: Some(last),
            error: None,
        }
    }

    /// Get the path to the journal store file
    pub fn get_store_path(&self) -> String {
        self.store_path.display().to_string()
    }
}

impl Default for Journal {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[tokio::test]
    async fn test_journal_log_and_get() {
        let temp_dir = env::temp_dir();
        let test_path = temp_dir.join(format!("warp_journal_test_{}.json", uuid::Uuid::new_v4()));
        let journal = Journal::new_with_path(test_path.clone());

        let entry = journal
            .log_action("test", "Test action", None)
            .await
            .unwrap();

        assert_eq!(entry.entry_type, "test");
        assert_eq!(entry.summary, "Test action");

        let entries = journal.get_entries(0, 10).await.unwrap();
        assert!(!entries.is_empty());
        assert_eq!(entries[0].id, entry.id);
        
        // Cleanup
        let _ = std::fs::remove_file(test_path);
    }

    #[tokio::test]
    async fn test_journal_undo() {
        let temp_dir = env::temp_dir();
        let test_path = temp_dir.join(format!("warp_journal_undo_{}.json", uuid::Uuid::new_v4()));
        let journal = Journal::new_with_path(test_path.clone());

        journal
            .log_action("test1", "Action 1", None)
            .await
            .unwrap();

        journal
            .log_action("test2", "Action 2", None)
            .await
            .unwrap();

        let undo_result = journal.undo_last().await;
        assert!(undo_result.ok);
        assert_eq!(undo_result.undone.unwrap().summary, "Action 2");

        let entries = journal.get_entries(0, 10).await.unwrap();
        assert_eq!(entries[0].summary, "Action 1");
        
        // Cleanup
        let _ = std::fs::remove_file(test_path);
    }
}
