//! Privacy Logger - Split logging system
//!
//! - Private/ephemeral: Stored in memory only, cleared on session end
//! - Safe/persistent: Logged to disk, sanitized content only
//!
//! The private buffer is encrypted in memory and never touches disk.

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::path::PathBuf;
use std::sync::RwLock;
use chrono::{DateTime, Utc};

/// Log entry that can be either private (ephemeral) or safe (persistent)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: DateTime<Utc>,
    pub session_id: String,
    pub entry_type: LogEntryType,
    pub content: String,
    pub metadata: LogMetadata,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum LogEntryType {
    Query,              // User query
    SanitizedQuery,     // What was sent to external AI
    Response,           // AI response
    TaskExecution,      // Task that was executed
    Routing,            // Routing decision
    Error,              // Error occurred
    SystemEvent,        // System event (startup, etc.)
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogMetadata {
    pub was_private: bool,
    pub was_sanitized: bool,
    pub original_hash: Option<String>,  // Hash of original if sanitized
    pub routing_path: Option<String>,
    pub model_used: Option<String>,
    pub latency_ms: Option<u64>,
}

/// The split logger
pub struct PrivacyLogger {
    // Ephemeral buffer - private entries, memory only
    ephemeral_buffer: RwLock<VecDeque<EncryptedEntry>>,
    ephemeral_max_size: usize,

    // Session key for ephemeral encryption (regenerated each session)
    session_key: [u8; 32],

    // Persistent log path
    persistent_log_path: PathBuf,

    // Current session ID
    session_id: String,
}

/// Encrypted entry for ephemeral storage
struct EncryptedEntry {
    nonce: [u8; 12],
    ciphertext: Vec<u8>,
    timestamp: DateTime<Utc>,
}

impl PrivacyLogger {
    pub fn new() -> Self {
        // Generate session key
        let mut session_key = [0u8; 32];
        getrandom::getrandom(&mut session_key).unwrap_or_else(|_| {
            // Fallback to less secure random if getrandom fails
            use std::time::{SystemTime, UNIX_EPOCH};
            let seed = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64;
            for (i, byte) in session_key.iter_mut().enumerate() {
                *byte = ((seed >> (i % 8 * 8)) & 0xFF) as u8;
            }
        });

        let persistent_log_path = dirs::home_dir()
            .map(|h| h.join(".sam_logs"))
            .unwrap_or_else(|| PathBuf::from("/tmp/.sam_logs"));

        // Ensure log directory exists
        let _ = std::fs::create_dir_all(&persistent_log_path);

        let session_id = format!("session_{}", Utc::now().timestamp());

        Self {
            ephemeral_buffer: RwLock::new(VecDeque::with_capacity(1000)),
            ephemeral_max_size: 1000,
            session_key,
            persistent_log_path,
            session_id,
        }
    }

    /// Log a private entry (ephemeral, encrypted in memory)
    pub fn log_private(&self, entry_type: LogEntryType, content: &str, metadata: LogMetadata) {
        let entry = LogEntry {
            timestamp: Utc::now(),
            session_id: self.session_id.clone(),
            entry_type,
            content: content.to_string(),
            metadata,
        };

        // Serialize and encrypt
        if let Ok(serialized) = serde_json::to_vec(&entry) {
            let encrypted = self.encrypt(&serialized);

            let mut buffer = self.ephemeral_buffer.write().unwrap();

            // Enforce max size
            while buffer.len() >= self.ephemeral_max_size {
                buffer.pop_front();
            }

            buffer.push_back(encrypted);
        }
    }

    /// Log a safe entry (persistent, written to disk)
    pub fn log_safe(&self, entry_type: LogEntryType, content: &str, metadata: LogMetadata) {
        let entry = LogEntry {
            timestamp: Utc::now(),
            session_id: self.session_id.clone(),
            entry_type,
            content: content.to_string(),
            metadata,
        };

        // Write to daily log file
        let date = Utc::now().format("%Y-%m-%d");
        let log_file = self.persistent_log_path.join(format!("{}.jsonl", date));

        if let Ok(serialized) = serde_json::to_string(&entry) {
            let _ = std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&log_file)
                .and_then(|mut f| {
                    use std::io::Write;
                    writeln!(f, "{}", serialized)
                });
        }
    }

    /// Log with automatic routing based on privacy
    pub fn log(&self, entry_type: LogEntryType, content: &str, is_private: bool, metadata: LogMetadata) {
        if is_private {
            self.log_private(entry_type, content, metadata);
        } else {
            self.log_safe(entry_type, content, metadata);
        }
    }

    /// Log a query with sanitization info
    pub fn log_query_with_sanitization(
        &self,
        original: &str,
        sanitized: Option<&str>,
        original_hash: &str,
        is_private: bool,
    ) {
        // Always log the private original to ephemeral
        self.log_private(
            LogEntryType::Query,
            original,
            LogMetadata {
                was_private: is_private,
                was_sanitized: sanitized.is_some(),
                original_hash: Some(original_hash.to_string()),
                routing_path: None,
                model_used: None,
                latency_ms: None,
            },
        );

        // If sanitized, log the clean version to persistent
        if let Some(clean) = sanitized {
            if !is_private {
                self.log_safe(
                    LogEntryType::SanitizedQuery,
                    clean,
                    LogMetadata {
                        was_private: false,
                        was_sanitized: true,
                        original_hash: Some(original_hash.to_string()),
                        routing_path: None,
                        model_used: None,
                        latency_ms: None,
                    },
                );
            }
        }
    }

    /// Log task execution result
    pub fn log_task_execution(
        &self,
        task_type: &str,
        success: bool,
        output: &str,
        changes: &[String],
        is_private: bool,
    ) {
        let content = format!(
            "Task: {} | Success: {} | Changes: {:?}\nOutput: {}",
            task_type, success, changes, output
        );

        self.log(
            LogEntryType::TaskExecution,
            &content,
            is_private,
            LogMetadata {
                was_private: is_private,
                was_sanitized: false,
                original_hash: None,
                routing_path: None,
                model_used: None,
                latency_ms: None,
            },
        );
    }

    /// Log routing decision
    pub fn log_routing(
        &self,
        query: &str,
        path: &str,
        was_sanitized: bool,
        is_private: bool,
    ) {
        let content = format!("Routed to: {} | Sanitized: {}", path, was_sanitized);

        // Always log routing decisions to persistent (they're safe)
        self.log_safe(
            LogEntryType::Routing,
            &content,
            LogMetadata {
                was_private: is_private,
                was_sanitized,
                original_hash: None,
                routing_path: Some(path.to_string()),
                model_used: None,
                latency_ms: None,
            },
        );

        // If private, also log query hash (not content) to persistent for correlation
        if is_private {
            use std::collections::hash_map::DefaultHasher;
            use std::hash::{Hash, Hasher};
            let mut hasher = DefaultHasher::new();
            query.hash(&mut hasher);
            let hash = format!("{:x}", hasher.finish());

            self.log_safe(
                LogEntryType::Routing,
                &format!("Private query [hash: {}] routed to: {}", hash, path),
                LogMetadata {
                    was_private: true,
                    was_sanitized,
                    original_hash: Some(hash),
                    routing_path: Some(path.to_string()),
                    model_used: None,
                    latency_ms: None,
                },
            );
        }
    }

    /// Get recent ephemeral entries (decrypted)
    pub fn get_recent_private(&self, count: usize) -> Vec<LogEntry> {
        let buffer = self.ephemeral_buffer.read().unwrap();
        buffer
            .iter()
            .rev()
            .take(count)
            .filter_map(|encrypted| self.decrypt(encrypted))
            .collect()
    }

    /// Clear ephemeral buffer (call on session end)
    pub fn clear_ephemeral(&self) {
        let mut buffer = self.ephemeral_buffer.write().unwrap();
        buffer.clear();
    }

    /// Get persistent log entries for a date
    pub fn get_persistent_logs(&self, date: &str) -> Vec<LogEntry> {
        let log_file = self.persistent_log_path.join(format!("{}.jsonl", date));

        if let Ok(content) = std::fs::read_to_string(&log_file) {
            content
                .lines()
                .filter_map(|line| serde_json::from_str(line).ok())
                .collect()
        } else {
            vec![]
        }
    }

    // Simple XOR encryption for ephemeral buffer (good enough for memory-only)
    fn encrypt(&self, data: &[u8]) -> EncryptedEntry {
        let mut nonce = [0u8; 12];
        getrandom::getrandom(&mut nonce).unwrap_or_else(|_| {
            use std::time::{SystemTime, UNIX_EPOCH};
            let seed = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos() as u64;
            for (i, byte) in nonce.iter_mut().enumerate() {
                *byte = ((seed >> (i % 8 * 8)) & 0xFF) as u8;
            }
        });

        let mut ciphertext = data.to_vec();
        for (i, byte) in ciphertext.iter_mut().enumerate() {
            *byte ^= self.session_key[i % 32] ^ nonce[i % 12];
        }

        EncryptedEntry {
            nonce,
            ciphertext,
            timestamp: Utc::now(),
        }
    }

    fn decrypt(&self, entry: &EncryptedEntry) -> Option<LogEntry> {
        let mut plaintext = entry.ciphertext.clone();
        for (i, byte) in plaintext.iter_mut().enumerate() {
            *byte ^= self.session_key[i % 32] ^ entry.nonce[i % 12];
        }

        serde_json::from_slice(&plaintext).ok()
    }
}

impl Default for PrivacyLogger {
    fn default() -> Self {
        Self::new()
    }
}

// Global instance
lazy_static::lazy_static! {
    static ref LOGGER: PrivacyLogger = PrivacyLogger::new();
}

// Public API
pub fn log_private(entry_type: LogEntryType, content: &str) {
    LOGGER.log_private(entry_type, content, LogMetadata {
        was_private: true,
        was_sanitized: false,
        original_hash: None,
        routing_path: None,
        model_used: None,
        latency_ms: None,
    });
}

pub fn log_safe(entry_type: LogEntryType, content: &str) {
    LOGGER.log_safe(entry_type, content, LogMetadata {
        was_private: false,
        was_sanitized: false,
        original_hash: None,
        routing_path: None,
        model_used: None,
        latency_ms: None,
    });
}

pub fn log_query(original: &str, sanitized: Option<&str>, hash: &str, is_private: bool) {
    LOGGER.log_query_with_sanitization(original, sanitized, hash, is_private);
}

pub fn log_routing(query: &str, path: &str, was_sanitized: bool, is_private: bool) {
    LOGGER.log_routing(query, path, was_sanitized, is_private);
}

pub fn log_task(task_type: &str, success: bool, output: &str, changes: &[String], is_private: bool) {
    LOGGER.log_task_execution(task_type, success, output, changes, is_private);
}

pub fn clear_session() {
    LOGGER.clear_ephemeral();
}

pub fn get_recent_private(count: usize) -> Vec<LogEntry> {
    LOGGER.get_recent_private(count)
}

pub fn get_logs_for_date(date: &str) -> Vec<LogEntry> {
    LOGGER.get_persistent_logs(date)
}
