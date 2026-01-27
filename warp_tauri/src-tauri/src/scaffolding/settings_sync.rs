//! Settings Sync - Cloud synchronization of preferences and configuration
//!
//! Provides cross-device sync of:
//! - User preferences (themes, keybindings, etc.)
//! - Workflows and custom commands
//! - AI configuration (model preferences, reasoning levels)
//! - Terminal profiles and shell configurations
//! - Sync conflict resolution

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::sync::{Arc, Mutex};
use chrono::{DateTime, Utc};
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

// =============================================================================
// SYNC TYPES
// =============================================================================

/// Categories of settings that can be synced
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum SyncCategory {
    /// UI preferences (theme, font, colors)
    Appearance,
    /// Keyboard shortcuts
    Keybindings,
    /// AI model preferences and reasoning levels
    AiConfig,
    /// Custom workflows and commands
    Workflows,
    /// Terminal profiles
    Profiles,
    /// Shell configurations
    Shell,
    /// Privacy and security settings
    Privacy,
    /// Extension/plugin settings
    Extensions,
    /// All settings
    All,
}

/// Single sync-able setting
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncSetting {
    /// Unique key for this setting
    pub key: String,
    /// Setting value (JSON-compatible)
    pub value: serde_json::Value,
    /// Category for grouping
    pub category: SyncCategory,
    /// Last modified timestamp
    pub modified_at: DateTime<Utc>,
    /// Hash of the value for conflict detection
    pub hash: String,
    /// Device that last modified this
    pub modified_by: Option<String>,
}

/// Snapshot of all settings at a point in time
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SettingsSnapshot {
    /// Snapshot version
    pub version: u32,
    /// When snapshot was created
    pub created_at: DateTime<Utc>,
    /// Device ID that created this snapshot
    pub device_id: String,
    /// All settings in this snapshot
    pub settings: HashMap<String, SyncSetting>,
    /// Categories included
    pub categories: Vec<SyncCategory>,
}

/// Sync state for tracking changes
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncState {
    /// Last successful sync time
    pub last_sync: Option<DateTime<Utc>>,
    /// Local changes pending sync
    pub pending_changes: Vec<String>,
    /// Current sync status
    pub status: SyncStatus,
    /// Remote version we're synced to
    pub remote_version: Option<u32>,
    /// Local version
    pub local_version: u32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum SyncStatus {
    /// Synced with remote
    Synced,
    /// Local changes pending push
    PendingPush,
    /// Remote changes pending pull
    PendingPull,
    /// Conflicts need resolution
    Conflict,
    /// Sync in progress
    Syncing,
    /// Sync disabled
    Disabled,
    /// Error state
    Error,
}

/// Conflict between local and remote settings
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConflict {
    pub key: String,
    pub local_value: serde_json::Value,
    pub remote_value: serde_json::Value,
    pub local_modified: DateTime<Utc>,
    pub remote_modified: DateTime<Utc>,
    pub resolution: Option<ConflictResolution>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum ConflictResolution {
    /// Use local value
    KeepLocal,
    /// Use remote value
    UseRemote,
    /// Merge values (if possible)
    Merge,
    /// Manual resolution needed
    Manual,
}

// =============================================================================
// SYNC CONFIGURATION
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncConfig {
    /// Whether sync is enabled
    pub enabled: bool,
    /// Categories to sync
    pub sync_categories: Vec<SyncCategory>,
    /// Sync backend
    pub backend: SyncBackend,
    /// Auto-sync interval in seconds
    pub auto_sync_interval: Option<u64>,
    /// Default conflict resolution
    pub default_resolution: ConflictResolution,
    /// Device ID for this machine
    pub device_id: String,
    /// Device name (human readable)
    pub device_name: String,
}

impl Default for SyncConfig {
    fn default() -> Self {
        Self {
            enabled: false,
            sync_categories: vec![
                SyncCategory::Appearance,
                SyncCategory::Keybindings,
                SyncCategory::AiConfig,
                SyncCategory::Workflows,
            ],
            backend: SyncBackend::LocalFile {
                path: dirs::config_dir()
                    .unwrap_or_else(|| PathBuf::from("."))
                    .join("sam")
                    .join("sync"),
            },
            auto_sync_interval: Some(300), // 5 minutes
            default_resolution: ConflictResolution::KeepLocal,
            device_id: generate_device_id(),
            device_name: get_hostname(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SyncBackend {
    /// Local file sync (for testing or LAN sync)
    LocalFile { path: PathBuf },
    /// Cloud API sync
    CloudApi {
        api_url: String,
        api_key: Option<String>,
    },
    /// iCloud sync (macOS)
    ICloud,
    /// Custom backend
    Custom { endpoint: String },
}

// =============================================================================
// SETTINGS SYNC MANAGER
// =============================================================================

pub struct SettingsSync {
    config: SyncConfig,
    state: SyncState,
    local_settings: HashMap<String, SyncSetting>,
    conflicts: Vec<SyncConflict>,
    change_handlers: Vec<Box<dyn Fn(&SyncSetting) + Send + Sync>>,
}

impl SettingsSync {
    /// Create new sync manager with default config
    pub fn new() -> Self {
        Self::with_config(SyncConfig::default())
    }

    /// Create with custom config
    pub fn with_config(config: SyncConfig) -> Self {
        Self {
            config,
            state: SyncState {
                last_sync: None,
                pending_changes: Vec::new(),
                status: SyncStatus::Disabled,
                remote_version: None,
                local_version: 1,
            },
            local_settings: HashMap::new(),
            conflicts: Vec::new(),
            change_handlers: Vec::new(),
        }
    }

    /// Enable sync
    pub fn enable(&mut self) {
        self.config.enabled = true;
        self.state.status = SyncStatus::PendingPush;
    }

    /// Disable sync
    pub fn disable(&mut self) {
        self.config.enabled = false;
        self.state.status = SyncStatus::Disabled;
    }

    /// Set a setting value
    pub fn set<T: Serialize>(&mut self, key: &str, value: T, category: SyncCategory) -> Result<(), SyncError> {
        let json_value = serde_json::to_value(value)
            .map_err(|e| SyncError::SerializationError(e.to_string()))?;

        let hash = hash_value(&json_value);

        let setting = SyncSetting {
            key: key.to_string(),
            value: json_value,
            category,
            modified_at: Utc::now(),
            hash,
            modified_by: Some(self.config.device_id.clone()),
        };

        // Check if value actually changed
        if let Some(existing) = self.local_settings.get(key) {
            if existing.hash == setting.hash {
                return Ok(()); // No change
            }
        }

        self.local_settings.insert(key.to_string(), setting.clone());

        // Mark as pending
        if self.config.enabled {
            if !self.state.pending_changes.contains(&key.to_string()) {
                self.state.pending_changes.push(key.to_string());
            }
            self.state.status = SyncStatus::PendingPush;
        }

        // Notify handlers
        for handler in &self.change_handlers {
            handler(&setting);
        }

        Ok(())
    }

    /// Get a setting value
    pub fn get<T: for<'de> Deserialize<'de>>(&self, key: &str) -> Option<T> {
        self.local_settings
            .get(key)
            .and_then(|s| serde_json::from_value(s.value.clone()).ok())
    }

    /// Get raw setting
    pub fn get_raw(&self, key: &str) -> Option<&SyncSetting> {
        self.local_settings.get(key)
    }

    /// Get all settings in a category
    pub fn get_category(&self, category: SyncCategory) -> Vec<&SyncSetting> {
        self.local_settings
            .values()
            .filter(|s| s.category == category || category == SyncCategory::All)
            .collect()
    }

    /// Delete a setting
    pub fn delete(&mut self, key: &str) -> bool {
        if self.local_settings.remove(key).is_some() {
            if self.config.enabled {
                self.state.pending_changes.push(format!("-{}", key));
                self.state.status = SyncStatus::PendingPush;
            }
            true
        } else {
            false
        }
    }

    /// Push local changes to remote
    pub fn push(&mut self) -> Result<SyncResult, SyncError> {
        if !self.config.enabled {
            return Err(SyncError::SyncDisabled);
        }

        if self.state.pending_changes.is_empty() {
            return Ok(SyncResult {
                success: true,
                pushed: 0,
                pulled: 0,
                conflicts: 0,
            });
        }

        self.state.status = SyncStatus::Syncing;

        // Get settings to push
        let settings_to_push: Vec<SyncSetting> = self.state.pending_changes
            .iter()
            .filter_map(|key| {
                if key.starts_with('-') {
                    // Deletion - create tombstone
                    Some(SyncSetting {
                        key: key[1..].to_string(),
                        value: serde_json::Value::Null,
                        category: SyncCategory::All,
                        modified_at: Utc::now(),
                        hash: String::new(),
                        modified_by: Some(self.config.device_id.clone()),
                    })
                } else {
                    self.local_settings.get(key).cloned()
                }
            })
            .collect();

        let pushed_count = settings_to_push.len();

        match &self.config.backend {
            SyncBackend::LocalFile { path } => {
                self.push_to_local_file(path, &settings_to_push)?;
            }
            SyncBackend::CloudApi { api_url, api_key } => {
                self.push_to_cloud_api(api_url, api_key.as_deref(), &settings_to_push)?;
            }
            SyncBackend::ICloud => {
                self.push_to_icloud(&settings_to_push)?;
            }
            SyncBackend::Custom { endpoint } => {
                return Err(SyncError::NotImplemented(format!("Custom endpoint: {}", endpoint)));
            }
        }

        self.state.pending_changes.clear();
        self.state.local_version += 1;
        self.state.last_sync = Some(Utc::now());
        self.state.status = SyncStatus::Synced;

        Ok(SyncResult {
            success: true,
            pushed: pushed_count,
            pulled: 0,
            conflicts: 0,
        })
    }

    /// Pull remote changes
    pub fn pull(&mut self) -> Result<SyncResult, SyncError> {
        if !self.config.enabled {
            return Err(SyncError::SyncDisabled);
        }

        self.state.status = SyncStatus::Syncing;

        let remote_settings = match &self.config.backend {
            SyncBackend::LocalFile { path } => self.pull_from_local_file(path)?,
            SyncBackend::CloudApi { api_url, api_key } => {
                self.pull_from_cloud_api(api_url, api_key.as_deref())?
            }
            SyncBackend::ICloud => self.pull_from_icloud()?,
            SyncBackend::Custom { endpoint } => {
                return Err(SyncError::NotImplemented(format!("Custom endpoint: {}", endpoint)));
            }
        };

        let mut pulled = 0;
        let mut conflict_count = 0;

        for remote in remote_settings {
            // Skip if category not synced
            if !self.config.sync_categories.contains(&remote.category)
                && !self.config.sync_categories.contains(&SyncCategory::All) {
                continue;
            }

            if let Some(local) = self.local_settings.get(&remote.key) {
                // Check for conflict
                if local.hash != remote.hash && local.modified_at != remote.modified_at {
                    // Different values, different times - potential conflict
                    if local.modified_at > remote.modified_at {
                        // Local is newer, keep it (but mark as pending)
                        if !self.state.pending_changes.contains(&remote.key) {
                            self.state.pending_changes.push(remote.key.clone());
                        }
                    } else {
                        // Remote is newer - check resolution strategy
                        match self.config.default_resolution {
                            ConflictResolution::UseRemote => {
                                self.local_settings.insert(remote.key.clone(), remote.clone());
                                pulled += 1;
                            }
                            ConflictResolution::KeepLocal => {
                                // Keep local, mark as pending
                                if !self.state.pending_changes.contains(&remote.key) {
                                    self.state.pending_changes.push(remote.key.clone());
                                }
                            }
                            ConflictResolution::Manual | ConflictResolution::Merge => {
                                // Create conflict entry
                                self.conflicts.push(SyncConflict {
                                    key: remote.key.clone(),
                                    local_value: local.value.clone(),
                                    remote_value: remote.value.clone(),
                                    local_modified: local.modified_at,
                                    remote_modified: remote.modified_at,
                                    resolution: None,
                                });
                                conflict_count += 1;
                            }
                        }
                    }
                }
            } else {
                // New setting from remote
                self.local_settings.insert(remote.key.clone(), remote);
                pulled += 1;
            }
        }

        self.state.last_sync = Some(Utc::now());
        self.state.status = if conflict_count > 0 {
            SyncStatus::Conflict
        } else if !self.state.pending_changes.is_empty() {
            SyncStatus::PendingPush
        } else {
            SyncStatus::Synced
        };

        Ok(SyncResult {
            success: conflict_count == 0,
            pushed: 0,
            pulled,
            conflicts: conflict_count,
        })
    }

    /// Full sync (pull then push)
    pub fn sync(&mut self) -> Result<SyncResult, SyncError> {
        let pull_result = self.pull()?;

        if pull_result.conflicts > 0 {
            return Ok(pull_result);
        }

        let push_result = self.push()?;

        Ok(SyncResult {
            success: true,
            pushed: push_result.pushed,
            pulled: pull_result.pulled,
            conflicts: 0,
        })
    }

    /// Get current conflicts
    pub fn get_conflicts(&self) -> &[SyncConflict] {
        &self.conflicts
    }

    /// Resolve a conflict
    pub fn resolve_conflict(&mut self, key: &str, resolution: ConflictResolution) -> Result<(), SyncError> {
        let conflict_idx = self.conflicts.iter().position(|c| c.key == key)
            .ok_or_else(|| SyncError::ConflictNotFound(key.to_string()))?;

        let conflict = &self.conflicts[conflict_idx];

        match resolution {
            ConflictResolution::KeepLocal => {
                // Already have local, just mark as pending
                if !self.state.pending_changes.contains(&key.to_string()) {
                    self.state.pending_changes.push(key.to_string());
                }
            }
            ConflictResolution::UseRemote => {
                // Replace with remote
                if let Some(setting) = self.local_settings.get_mut(key) {
                    setting.value = conflict.remote_value.clone();
                    setting.modified_at = conflict.remote_modified;
                    setting.hash = hash_value(&conflict.remote_value);
                }
            }
            ConflictResolution::Merge => {
                // Attempt to merge (only works for objects)
                if let (Some(local_obj), Some(remote_obj)) =
                    (conflict.local_value.as_object(), conflict.remote_value.as_object())
                {
                    let mut merged = local_obj.clone();
                    for (k, v) in remote_obj {
                        if !merged.contains_key(k) {
                            merged.insert(k.clone(), v.clone());
                        }
                    }
                    if let Some(setting) = self.local_settings.get_mut(key) {
                        setting.value = serde_json::Value::Object(merged);
                        setting.modified_at = Utc::now();
                        setting.hash = hash_value(&setting.value);
                    }
                    if !self.state.pending_changes.contains(&key.to_string()) {
                        self.state.pending_changes.push(key.to_string());
                    }
                } else {
                    return Err(SyncError::MergeNotPossible(key.to_string()));
                }
            }
            ConflictResolution::Manual => {
                return Err(SyncError::ManualResolutionRequired(key.to_string()));
            }
        }

        self.conflicts.remove(conflict_idx);

        if self.conflicts.is_empty() && self.state.status == SyncStatus::Conflict {
            self.state.status = if self.state.pending_changes.is_empty() {
                SyncStatus::Synced
            } else {
                SyncStatus::PendingPush
            };
        }

        Ok(())
    }

    /// Export all settings to a snapshot
    pub fn export_snapshot(&self) -> SettingsSnapshot {
        SettingsSnapshot {
            version: self.state.local_version,
            created_at: Utc::now(),
            device_id: self.config.device_id.clone(),
            settings: self.local_settings.clone(),
            categories: self.config.sync_categories.clone(),
        }
    }

    /// Import settings from a snapshot
    pub fn import_snapshot(&mut self, snapshot: SettingsSnapshot, merge: bool) -> Result<usize, SyncError> {
        let mut imported = 0;

        for (key, setting) in snapshot.settings {
            if merge {
                // Only import if not exists or older
                if let Some(existing) = self.local_settings.get(&key) {
                    if existing.modified_at >= setting.modified_at {
                        continue;
                    }
                }
            }

            self.local_settings.insert(key.clone(), setting);
            if !self.state.pending_changes.contains(&key) {
                self.state.pending_changes.push(key);
            }
            imported += 1;
        }

        if imported > 0 {
            self.state.status = SyncStatus::PendingPush;
        }

        Ok(imported)
    }

    /// Get sync status
    pub fn status(&self) -> &SyncState {
        &self.state
    }

    /// Get config
    pub fn config(&self) -> &SyncConfig {
        &self.config
    }

    /// Update config
    pub fn update_config(&mut self, config: SyncConfig) {
        self.config = config;
    }

    /// Register change handler
    pub fn on_change<F>(&mut self, handler: F)
    where
        F: Fn(&SyncSetting) + Send + Sync + 'static,
    {
        self.change_handlers.push(Box::new(handler));
    }

    // =========================================================================
    // BACKEND IMPLEMENTATIONS
    // =========================================================================

    fn push_to_local_file(&self, path: &Path, settings: &[SyncSetting]) -> Result<(), SyncError> {
        std::fs::create_dir_all(path)
            .map_err(|e| SyncError::IoError(e.to_string()))?;

        // Load existing
        let sync_file = path.join("settings.json");
        let mut all_settings: HashMap<String, SyncSetting> = if sync_file.exists() {
            let content = std::fs::read_to_string(&sync_file)
                .map_err(|e| SyncError::IoError(e.to_string()))?;
            serde_json::from_str(&content)
                .map_err(|e| SyncError::SerializationError(e.to_string()))?
        } else {
            HashMap::new()
        };

        // Apply changes
        for setting in settings {
            if setting.value.is_null() {
                all_settings.remove(&setting.key);
            } else {
                all_settings.insert(setting.key.clone(), setting.clone());
            }
        }

        // Write back
        let content = serde_json::to_string_pretty(&all_settings)
            .map_err(|e| SyncError::SerializationError(e.to_string()))?;
        std::fs::write(&sync_file, content)
            .map_err(|e| SyncError::IoError(e.to_string()))?;

        Ok(())
    }

    fn pull_from_local_file(&self, path: &Path) -> Result<Vec<SyncSetting>, SyncError> {
        let sync_file = path.join("settings.json");

        if !sync_file.exists() {
            return Ok(Vec::new());
        }

        let content = std::fs::read_to_string(&sync_file)
            .map_err(|e| SyncError::IoError(e.to_string()))?;

        let settings: HashMap<String, SyncSetting> = serde_json::from_str(&content)
            .map_err(|e| SyncError::SerializationError(e.to_string()))?;

        Ok(settings.into_values().collect())
    }

    fn push_to_cloud_api(&self, _api_url: &str, _api_key: Option<&str>, _settings: &[SyncSetting]) -> Result<(), SyncError> {
        // Placeholder for cloud sync implementation
        // Would use reqwest or similar to POST to API
        Err(SyncError::NotImplemented("Cloud API push".to_string()))
    }

    fn pull_from_cloud_api(&self, _api_url: &str, _api_key: Option<&str>) -> Result<Vec<SyncSetting>, SyncError> {
        // Placeholder for cloud sync implementation
        Err(SyncError::NotImplemented("Cloud API pull".to_string()))
    }

    fn push_to_icloud(&self, _settings: &[SyncSetting]) -> Result<(), SyncError> {
        // Would use macOS NSUbiquitousKeyValueStore or similar
        Err(SyncError::NotImplemented("iCloud push".to_string()))
    }

    fn pull_from_icloud(&self) -> Result<Vec<SyncSetting>, SyncError> {
        Err(SyncError::NotImplemented("iCloud pull".to_string()))
    }
}

// =============================================================================
// RESULT AND ERROR TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SyncResult {
    pub success: bool,
    pub pushed: usize,
    pub pulled: usize,
    pub conflicts: usize,
}

#[derive(Debug)]
pub enum SyncError {
    SyncDisabled,
    IoError(String),
    SerializationError(String),
    NetworkError(String),
    ConflictNotFound(String),
    MergeNotPossible(String),
    ManualResolutionRequired(String),
    NotImplemented(String),
}

impl std::fmt::Display for SyncError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            SyncError::SyncDisabled => write!(f, "Sync is disabled"),
            SyncError::IoError(msg) => write!(f, "IO error: {}", msg),
            SyncError::SerializationError(msg) => write!(f, "Serialization error: {}", msg),
            SyncError::NetworkError(msg) => write!(f, "Network error: {}", msg),
            SyncError::ConflictNotFound(key) => write!(f, "Conflict not found: {}", key),
            SyncError::MergeNotPossible(key) => write!(f, "Cannot merge non-object values: {}", key),
            SyncError::ManualResolutionRequired(key) => write!(f, "Manual resolution required: {}", key),
            SyncError::NotImplemented(feature) => write!(f, "Not implemented: {}", feature),
        }
    }
}

impl std::error::Error for SyncError {}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn generate_device_id() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};

    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();

    let hostname = get_hostname();
    let combined = format!("{}-{}", hostname, timestamp);

    let mut hasher = DefaultHasher::new();
    combined.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

fn hash_value(value: &serde_json::Value) -> String {
    let json = serde_json::to_string(value).unwrap_or_default();
    let mut hasher = DefaultHasher::new();
    json.hash(&mut hasher);
    format!("{:016x}", hasher.finish())
}

fn get_hostname() -> String {
    std::env::var("HOSTNAME")
        .or_else(|_| std::env::var("COMPUTERNAME"))
        .unwrap_or_else(|_| "unknown-device".to_string())
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref SETTINGS_SYNC: Arc<Mutex<SettingsSync>> = Arc::new(Mutex::new(SettingsSync::new()));
}

/// Get the global sync instance
pub fn get_sync() -> Arc<Mutex<SettingsSync>> {
    SETTINGS_SYNC.clone()
}

/// Set a setting (convenience function)
pub fn set<T: Serialize>(key: &str, value: T, category: SyncCategory) -> Result<(), SyncError> {
    SETTINGS_SYNC.lock().unwrap().set(key, value, category)
}

/// Get a setting (convenience function)
pub fn get<T: for<'de> Deserialize<'de>>(key: &str) -> Option<T> {
    SETTINGS_SYNC.lock().unwrap().get(key)
}

/// Trigger sync
pub fn sync() -> Result<SyncResult, SyncError> {
    SETTINGS_SYNC.lock().unwrap().sync()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_set_and_get() {
        let mut sync = SettingsSync::new();

        sync.set("theme", "dark", SyncCategory::Appearance).unwrap();

        let value: String = sync.get("theme").unwrap();
        assert_eq!(value, "dark");
    }

    #[test]
    fn test_category_filter() {
        let mut sync = SettingsSync::new();

        sync.set("theme", "dark", SyncCategory::Appearance).unwrap();
        sync.set("model", "gpt-4", SyncCategory::AiConfig).unwrap();
        sync.set("font", "Fira Code", SyncCategory::Appearance).unwrap();

        let appearance = sync.get_category(SyncCategory::Appearance);
        assert_eq!(appearance.len(), 2);

        let ai = sync.get_category(SyncCategory::AiConfig);
        assert_eq!(ai.len(), 1);
    }

    #[test]
    fn test_delete() {
        let mut sync = SettingsSync::new();

        sync.set("temp", "value", SyncCategory::All).unwrap();
        assert!(sync.get::<String>("temp").is_some());

        sync.delete("temp");
        assert!(sync.get::<String>("temp").is_none());
    }

    #[test]
    fn test_no_duplicate_pending() {
        let mut sync = SettingsSync::new();
        sync.enable();

        sync.set("key", "value1", SyncCategory::All).unwrap();
        sync.set("key", "value2", SyncCategory::All).unwrap();
        sync.set("key", "value3", SyncCategory::All).unwrap();

        assert_eq!(sync.state.pending_changes.len(), 1);
    }

    #[test]
    fn test_export_import_snapshot() {
        let mut sync = SettingsSync::new();

        sync.set("setting1", "value1", SyncCategory::Appearance).unwrap();
        sync.set("setting2", 42, SyncCategory::AiConfig).unwrap();

        let snapshot = sync.export_snapshot();
        assert_eq!(snapshot.settings.len(), 2);

        let mut sync2 = SettingsSync::new();
        let imported = sync2.import_snapshot(snapshot, false).unwrap();
        assert_eq!(imported, 2);

        let v1: String = sync2.get("setting1").unwrap();
        assert_eq!(v1, "value1");

        let v2: i32 = sync2.get("setting2").unwrap();
        assert_eq!(v2, 42);
    }

    #[test]
    fn test_local_file_sync() {
        let temp_dir = std::env::temp_dir().join("sam_sync_test");
        let _ = std::fs::remove_dir_all(&temp_dir);

        let mut sync = SettingsSync::with_config(SyncConfig {
            enabled: true,
            backend: SyncBackend::LocalFile { path: temp_dir.clone() },
            ..SyncConfig::default()
        });

        sync.set("test_key", "test_value", SyncCategory::Appearance).unwrap();

        let result = sync.push().unwrap();
        assert!(result.success);
        assert_eq!(result.pushed, 1);

        // Verify file exists
        assert!(temp_dir.join("settings.json").exists());

        // Clean up
        let _ = std::fs::remove_dir_all(&temp_dir);
    }

    #[test]
    fn test_hash_changes() {
        let mut sync = SettingsSync::new();
        sync.enable();

        sync.set("key", "value1", SyncCategory::All).unwrap();
        assert_eq!(sync.state.pending_changes.len(), 1);

        // Setting same value shouldn't add to pending
        sync.state.pending_changes.clear();
        sync.set("key", "value1", SyncCategory::All).unwrap();
        assert_eq!(sync.state.pending_changes.len(), 0);

        // Different value should add
        sync.set("key", "value2", SyncCategory::All).unwrap();
        assert_eq!(sync.state.pending_changes.len(), 1);
    }

    #[test]
    fn test_sync_status() {
        let mut sync = SettingsSync::new();

        assert_eq!(sync.state.status, SyncStatus::Disabled);

        sync.enable();
        sync.set("key", "value", SyncCategory::All).unwrap();
        assert_eq!(sync.state.status, SyncStatus::PendingPush);
    }

    #[test]
    fn test_device_id_generation() {
        let id1 = generate_device_id();
        let id2 = generate_device_id();

        assert_eq!(id1.len(), 16);
        // IDs generated in same millisecond might be same
        // Just verify format
        assert!(id1.chars().all(|c| c.is_ascii_hexdigit()));
    }
}
