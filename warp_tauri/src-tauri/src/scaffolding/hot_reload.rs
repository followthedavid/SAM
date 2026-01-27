// Hot-Reload Indexer - Real-time codebase indexing
//
// Watches filesystem for changes and updates embeddings/index:
// - File watcher integration (notify crate)
// - Incremental re-indexing
// - Background update thread
// - Debouncing for batch updates

use serde::{Deserialize, Serialize};
use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};
use tokio::sync::mpsc;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexEvent {
    pub path: PathBuf,
    pub event_type: IndexEventType,
    pub timestamp: u64,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum IndexEventType {
    Created,
    Modified,
    Deleted,
    Renamed,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexStats {
    pub total_files: usize,
    pub indexed_files: usize,
    pub pending_updates: usize,
    pub last_update: Option<u64>,
    pub index_size_bytes: usize,
    pub watching_dirs: usize,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HotReloadConfig {
    pub debounce_ms: u64,
    pub batch_size: usize,
    pub exclude_patterns: Vec<String>,
    pub include_extensions: Vec<String>,
    pub max_file_size_bytes: usize,
    pub auto_start: bool,
}

impl Default for HotReloadConfig {
    fn default() -> Self {
        Self {
            debounce_ms: 500,
            batch_size: 50,
            exclude_patterns: vec![
                "node_modules".to_string(),
                "target".to_string(),
                ".git".to_string(),
                "dist".to_string(),
                "build".to_string(),
                "__pycache__".to_string(),
                ".venv".to_string(),
            ],
            include_extensions: vec![
                "rs".to_string(), "ts".to_string(), "tsx".to_string(),
                "js".to_string(), "jsx".to_string(), "py".to_string(),
                "go".to_string(), "java".to_string(), "c".to_string(),
                "cpp".to_string(), "h".to_string(), "hpp".to_string(),
                "vue".to_string(), "svelte".to_string(), "md".to_string(),
                "json".to_string(), "yaml".to_string(), "toml".to_string(),
            ],
            max_file_size_bytes: 1024 * 1024, // 1MB
            auto_start: true,
        }
    }
}

// =============================================================================
// HOT-RELOAD INDEXER
// =============================================================================

pub struct HotReloadIndexer {
    config: HotReloadConfig,
    watched_dirs: HashSet<PathBuf>,
    pending_updates: Arc<Mutex<Vec<IndexEvent>>>,
    last_batch_time: Arc<Mutex<Instant>>,
    running: Arc<Mutex<bool>>,
    event_tx: Option<mpsc::Sender<IndexEvent>>,
}

impl HotReloadIndexer {
    pub fn new(config: HotReloadConfig) -> Self {
        Self {
            config,
            watched_dirs: HashSet::new(),
            pending_updates: Arc::new(Mutex::new(Vec::new())),
            last_batch_time: Arc::new(Mutex::new(Instant::now())),
            running: Arc::new(Mutex::new(false)),
            event_tx: None,
        }
    }

    /// Start watching a directory
    pub fn watch(&mut self, path: &Path) -> Result<(), String> {
        if !path.exists() {
            return Err(format!("Path does not exist: {}", path.display()));
        }

        self.watched_dirs.insert(path.to_path_buf());

        // Start the watcher if auto_start is enabled
        if self.config.auto_start && !*self.running.lock().unwrap() {
            self.start_watcher()?;
        }

        Ok(())
    }

    /// Stop watching a directory
    pub fn unwatch(&mut self, path: &Path) {
        self.watched_dirs.remove(path);
    }

    /// Start the file watcher
    pub fn start_watcher(&mut self) -> Result<(), String> {
        if *self.running.lock().unwrap() {
            return Ok(()); // Already running
        }

        *self.running.lock().unwrap() = true;

        let (tx, mut rx) = mpsc::channel::<IndexEvent>(1000);
        self.event_tx = Some(tx.clone());

        let pending = self.pending_updates.clone();
        let last_batch = self.last_batch_time.clone();
        let running = self.running.clone();
        let debounce_ms = self.config.debounce_ms;
        let batch_size = self.config.batch_size;

        // Spawn the event processor
        tokio::spawn(async move {
            let mut pending_batch = Vec::new();

            loop {
                if !*running.lock().unwrap() {
                    break;
                }

                tokio::select! {
                    Some(event) = rx.recv() => {
                        pending_batch.push(event);

                        // Process batch if size reached or debounce expired
                        let should_process = pending_batch.len() >= batch_size || {
                            let elapsed = last_batch.lock().unwrap().elapsed();
                            elapsed.as_millis() as u64 >= debounce_ms && !pending_batch.is_empty()
                        };

                        if should_process {
                            // Move to pending and process
                            {
                                let mut p = pending.lock().unwrap();
                                p.extend(pending_batch.drain(..));
                            }
                            *last_batch.lock().unwrap() = Instant::now();

                            // Trigger index update
                            Self::process_pending_updates(&pending).await;
                        }
                    }

                    _ = tokio::time::sleep(Duration::from_millis(debounce_ms)) => {
                        if !pending_batch.is_empty() {
                            {
                                let mut p = pending.lock().unwrap();
                                p.extend(pending_batch.drain(..));
                            }
                            Self::process_pending_updates(&pending).await;
                        }
                    }
                }
            }
        });

        // File watcher using polling (cross-platform, no notify dependency)
        let watched = self.watched_dirs.clone();
        let exclude_patterns = self.config.exclude_patterns.clone();
        let include_extensions = self.config.include_extensions.clone();
        let max_size = self.config.max_file_size_bytes;
        let tx_clone = tx;
        let running_clone = self.running.clone();

        std::thread::spawn(move || {
            let mut file_mtimes: std::collections::HashMap<PathBuf, std::time::SystemTime> = std::collections::HashMap::new();

            // Initial scan
            for dir in &watched {
                let entries = walkdir::WalkDir::new(dir).into_iter().filter_map(|e| e.ok());
                for entry in entries {
                    if entry.file_type().is_file() {
                        if let Ok(meta) = entry.metadata() {
                            if let Ok(mtime) = meta.modified() {
                                file_mtimes.insert(entry.path().to_path_buf(), mtime);
                            }
                        }
                    }
                }
            }

            // Poll for changes
            while *running_clone.lock().unwrap() {
                std::thread::sleep(Duration::from_millis(1000)); // Poll every second

                for dir in &watched {
                    let entries = walkdir::WalkDir::new(dir).into_iter().filter_map(|e| e.ok());
                    for entry in entries {
                        let path = entry.path().to_path_buf();

                        if !entry.file_type().is_file() {
                            continue;
                        }

                        // Filter by extension
                        let ext = path.extension()
                            .and_then(|e| e.to_str())
                            .unwrap_or("");

                        if !include_extensions.is_empty() && !include_extensions.contains(&ext.to_string()) {
                            continue;
                        }

                        // Filter by exclude patterns
                        let path_str = path.display().to_string();
                        if exclude_patterns.iter().any(|p| path_str.contains(p)) {
                            continue;
                        }

                        // Filter by size
                        if let Ok(meta) = std::fs::metadata(&path) {
                            if meta.len() as usize > max_size {
                                continue;
                            }
                        }

                        // Check for modifications
                        if let Ok(meta) = entry.metadata() {
                            if let Ok(mtime) = meta.modified() {
                                let event_type = match file_mtimes.get(&path) {
                                    Some(&old_mtime) if old_mtime != mtime => {
                                        file_mtimes.insert(path.clone(), mtime);
                                        Some(IndexEventType::Modified)
                                    }
                                    None => {
                                        file_mtimes.insert(path.clone(), mtime);
                                        Some(IndexEventType::Created)
                                    }
                                    _ => None,
                                };

                                if let Some(et) = event_type {
                                    let index_event = IndexEvent {
                                        path: path.clone(),
                                        event_type: et,
                                        timestamp: std::time::SystemTime::now()
                                            .duration_since(std::time::UNIX_EPOCH)
                                            .unwrap()
                                            .as_secs(),
                                    };

                                    // Send to processor (blocking send for thread)
                                    let tx = tx_clone.clone();
                                    let _ = tx.blocking_send(index_event);
                                }
                            }
                        }
                    }
                }
            }
        });

        Ok(())
    }

    /// Stop the file watcher
    pub fn stop(&mut self) {
        *self.running.lock().unwrap() = false;
        self.event_tx = None;
    }

    /// Process pending updates
    async fn process_pending_updates(pending: &Arc<Mutex<Vec<IndexEvent>>>) {
        let events = {
            let mut p = pending.lock().unwrap();
            std::mem::take(&mut *p)
        };

        if events.is_empty() {
            return;
        }

        // Group by event type
        let mut created: Vec<PathBuf> = Vec::new();
        let mut modified: Vec<PathBuf> = Vec::new();
        let mut _deleted: Vec<PathBuf> = Vec::new();

        for event in events {
            match event.event_type {
                IndexEventType::Created => created.push(event.path),
                IndexEventType::Modified => modified.push(event.path),
                IndexEventType::Deleted => _deleted.push(event.path),
                IndexEventType::Renamed => {
                    // Treat as delete + create
                    _deleted.push(event.path.clone());
                    created.push(event.path);
                }
            }
        }

        // Update the embedding engine
        use crate::scaffolding::embedding_engine::embeddings;

        let mut engine = embeddings();

        // Note: embedding engine doesn't have remove_file yet, skip deletes
        // In a full implementation, we'd track and remove deleted files

        // Index created and modified files
        let to_index: Vec<_> = created.into_iter().chain(modified).collect();
        for path in to_index {
            if path.exists() {
                let path_str = path.display().to_string();
                if let Err(e) = engine.index_file(&path_str) {
                    eprintln!("Failed to index {}: {}", path_str, e);
                }
            }
        }
    }

    /// Force a full re-index of watched directories
    pub async fn reindex_all(&self) -> Result<IndexStats, String> {
        use crate::scaffolding::embedding_engine::embeddings;

        let mut engine = embeddings();
        let mut total_files = 0;
        let mut indexed_files = 0;
        let mut total_size = 0;

        // Default extensions to index
        let extensions = ["rs", "ts", "tsx", "js", "jsx", "py", "go", "java", "c", "cpp", "h", "hpp", "md", "json", "yaml", "toml"];
        let ext_refs: Vec<&str> = extensions.iter().map(|s| *s).collect();

        for dir in &self.watched_dirs {
            let dir_str = dir.display().to_string();
            let result = engine.index_directory(&dir_str, &ext_refs)?;
            total_files += result.total_files;
            indexed_files += result.total_chunks;
            total_size += result.index_size_bytes;
        }

        Ok(IndexStats {
            total_files,
            indexed_files,
            pending_updates: self.pending_updates.lock().unwrap().len(),
            last_update: Some(std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs()),
            index_size_bytes: total_size,
            watching_dirs: self.watched_dirs.len(),
        })
    }

    /// Get current stats
    pub fn stats(&self) -> IndexStats {
        use crate::scaffolding::embedding_engine::embeddings;

        let engine = embeddings();
        let engine_stats = engine.stats();

        IndexStats {
            total_files: engine_stats.total_files,
            indexed_files: engine_stats.total_chunks,
            pending_updates: self.pending_updates.lock().unwrap().len(),
            last_update: Some(engine_stats.indexed_at as u64),
            index_size_bytes: engine_stats.index_size_bytes,
            watching_dirs: self.watched_dirs.len(),
        }
    }

    /// Check if watcher is running
    pub fn is_running(&self) -> bool {
        *self.running.lock().unwrap()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref HOT_RELOAD: Mutex<HotReloadIndexer> = Mutex::new(HotReloadIndexer::new(HotReloadConfig::default()));
}

pub fn hot_reload() -> std::sync::MutexGuard<'static, HotReloadIndexer> {
    HOT_RELOAD.lock().unwrap()
}

/// Start watching a directory
pub fn watch(path: &Path) -> Result<(), String> {
    hot_reload().watch(path)
}

/// Stop watching a directory
pub fn unwatch(path: &Path) {
    hot_reload().unwatch(path)
}

/// Start the watcher
pub fn start() -> Result<(), String> {
    hot_reload().start_watcher()
}

/// Stop the watcher
pub fn stop() {
    hot_reload().stop()
}

/// Force re-index
pub async fn reindex() -> Result<IndexStats, String> {
    hot_reload().reindex_all().await
}

/// Get stats
pub fn stats() -> IndexStats {
    hot_reload().stats()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default() {
        let config = HotReloadConfig::default();
        assert_eq!(config.debounce_ms, 500);
        assert!(config.exclude_patterns.contains(&"node_modules".to_string()));
    }

    #[test]
    fn test_indexer_creation() {
        let indexer = HotReloadIndexer::new(HotReloadConfig::default());
        assert!(!indexer.is_running());
    }
}
