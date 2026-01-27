//! Structured Logging - JSON-formatted logs for machine parsing
//!
//! Provides structured logging that outputs JSON for easy parsing
//! in tests and monitoring tools.
//!
//! Usage:
//!   use crate::structured_log::{log_event, LogLevel};
//!
//!   log_event(LogLevel::Info, "ORCHESTRATOR", "routing", json!({
//!       "input": "hello",
//!       "decision": "Conversational",
//!       "confidence": 0.9
//!   }));
//!
//! Output (to stderr and optionally file):
//!   {"timestamp":"2024-01-10T12:34:56Z","level":"info","component":"ORCHESTRATOR","event":"routing","data":{"input":"hello","decision":"Conversational","confidence":0.9}}

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::fs::{File, OpenOptions};
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;

lazy_static::lazy_static! {
    static ref LOG_FILE: Mutex<Option<File>> = Mutex::new(None);
    static ref LOG_CONFIG: Mutex<LogConfig> = Mutex::new(LogConfig::default());
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
}

impl LogLevel {
    fn as_str(&self) -> &'static str {
        match self {
            LogLevel::Debug => "debug",
            LogLevel::Info => "info",
            LogLevel::Warn => "warn",
            LogLevel::Error => "error",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogEntry {
    pub timestamp: DateTime<Utc>,
    pub level: String,
    pub component: String,
    pub event: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub message: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct LogConfig {
    pub json_output: bool,
    pub file_path: Option<PathBuf>,
    pub min_level: LogLevel,
    pub include_component: bool,
}

impl Default for LogConfig {
    fn default() -> Self {
        Self {
            json_output: true,
            file_path: None,
            min_level: LogLevel::Info,
            include_component: true,
        }
    }
}

/// Initialize the structured logger
pub fn init_logger(config: LogConfig) {
    if let Some(path) = &config.file_path {
        if let Ok(file) = OpenOptions::new()
            .create(true)
            .append(true)
            .open(path)
        {
            if let Ok(mut log_file) = LOG_FILE.lock() {
                *log_file = Some(file);
            }
        }
    }

    if let Ok(mut cfg) = LOG_CONFIG.lock() {
        *cfg = config;
    }
}

/// Log an event with structured data
pub fn log_event(
    level: LogLevel,
    component: &str,
    event: &str,
    data: serde_json::Value,
) {
    log_entry(level, component, event, None, Some(data));
}

/// Log a message with optional data
pub fn log_message(
    level: LogLevel,
    component: &str,
    event: &str,
    message: &str,
    data: Option<serde_json::Value>,
) {
    log_entry(level, component, event, Some(message.to_string()), data);
}

fn log_entry(
    level: LogLevel,
    component: &str,
    event: &str,
    message: Option<String>,
    data: Option<serde_json::Value>,
) {
    let config = match LOG_CONFIG.lock() {
        Ok(guard) => (*guard).clone(),
        Err(_) => LogConfig::default(),
    };

    // Check minimum level
    let level_order = |l: &LogLevel| match l {
        LogLevel::Debug => 0,
        LogLevel::Info => 1,
        LogLevel::Warn => 2,
        LogLevel::Error => 3,
    };

    if level_order(&level) < level_order(&config.min_level) {
        return;
    }

    let entry = LogEntry {
        timestamp: Utc::now(),
        level: level.as_str().to_string(),
        component: component.to_string(),
        event: event.to_string(),
        message,
        data,
    };

    let output = if config.json_output {
        serde_json::to_string(&entry).unwrap_or_else(|_| format!("{:?}", entry))
    } else {
        // Traditional format: [COMPONENT] event: message
        let msg = entry.message.as_deref().unwrap_or("");
        let data_str = entry.data
            .as_ref()
            .map(|d| format!(" {:?}", d))
            .unwrap_or_default();

        format!(
            "[{}] {}: {}{}",
            entry.component,
            entry.event,
            msg,
            data_str
        )
    };

    // Output to stderr
    eprintln!("{}", output);

    // Output to file if configured
    if let Ok(mut log_file) = LOG_FILE.lock() {
        if let Some(ref mut file) = *log_file {
            let _ = writeln!(file, "{}", output);
        }
    }
}

/// Log macros for convenience
#[macro_export]
macro_rules! slog_debug {
    ($component:expr, $event:expr, $data:expr) => {
        $crate::structured_log::log_event(
            $crate::structured_log::LogLevel::Debug,
            $component,
            $event,
            $data,
        )
    };
    ($component:expr, $event:expr, $msg:expr, $data:expr) => {
        $crate::structured_log::log_message(
            $crate::structured_log::LogLevel::Debug,
            $component,
            $event,
            $msg,
            $data,
        )
    };
}

#[macro_export]
macro_rules! slog_info {
    ($component:expr, $event:expr, $data:expr) => {
        $crate::structured_log::log_event(
            $crate::structured_log::LogLevel::Info,
            $component,
            $event,
            $data,
        )
    };
    ($component:expr, $event:expr, $msg:expr, $data:expr) => {
        $crate::structured_log::log_message(
            $crate::structured_log::LogLevel::Info,
            $component,
            $event,
            $msg,
            $data,
        )
    };
}

#[macro_export]
macro_rules! slog_warn {
    ($component:expr, $event:expr, $data:expr) => {
        $crate::structured_log::log_event(
            $crate::structured_log::LogLevel::Warn,
            $component,
            $event,
            $data,
        )
    };
    ($component:expr, $event:expr, $msg:expr, $data:expr) => {
        $crate::structured_log::log_message(
            $crate::structured_log::LogLevel::Warn,
            $component,
            $event,
            $msg,
            $data,
        )
    };
}

#[macro_export]
macro_rules! slog_error {
    ($component:expr, $event:expr, $data:expr) => {
        $crate::structured_log::log_event(
            $crate::structured_log::LogLevel::Error,
            $component,
            $event,
            $data,
        )
    };
    ($component:expr, $event:expr, $msg:expr, $data:expr) => {
        $crate::structured_log::log_message(
            $crate::structured_log::LogLevel::Error,
            $component,
            $event,
            $msg,
            $data,
        )
    };
}

/// Read recent logs from the log file
pub fn read_recent_logs(count: usize) -> Vec<LogEntry> {
    let config = match LOG_CONFIG.lock() {
        Ok(guard) => (*guard).clone(),
        Err(_) => LogConfig::default(),
    };

    if let Some(path) = config.file_path {
        if let Ok(content) = std::fs::read_to_string(&path) {
            return content
                .lines()
                .filter_map(|line| serde_json::from_str(line).ok())
                .collect::<Vec<LogEntry>>()
                .into_iter()
                .rev()
                .take(count)
                .collect();
        }
    }

    Vec::new()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_log_entry_serialization() {
        let entry = LogEntry {
            timestamp: Utc::now(),
            level: "info".to_string(),
            component: "TEST".to_string(),
            event: "test_event".to_string(),
            message: Some("Test message".to_string()),
            data: Some(serde_json::json!({"key": "value"})),
        };

        let json = serde_json::to_string(&entry).unwrap();
        assert!(json.contains("\"level\":\"info\""));
        assert!(json.contains("\"component\":\"TEST\""));
    }

    #[test]
    fn test_log_levels() {
        assert_eq!(LogLevel::Debug.as_str(), "debug");
        assert_eq!(LogLevel::Info.as_str(), "info");
        assert_eq!(LogLevel::Warn.as_str(), "warn");
        assert_eq!(LogLevel::Error.as_str(), "error");
    }
}
