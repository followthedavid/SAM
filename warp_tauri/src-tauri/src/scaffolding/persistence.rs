// Persistence Layer for SAM
//
// Ensures agent state survives crashes and restarts.
// Provides checkpoint/resume capability for long-running tasks.

use serde::{Deserialize, Serialize};
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write, BufReader, BufWriter};
use std::path::PathBuf;
use chrono::{DateTime, Utc};

/// Base directory for SAM persistence
fn sam_dir() -> PathBuf {
    let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
    PathBuf::from(format!("{}/.sam", home))
}

/// Ensure all persistence directories exist
pub fn ensure_dirs() -> std::io::Result<()> {
    let base = sam_dir();
    fs::create_dir_all(base.join("tasks"))?;
    fs::create_dir_all(base.join("checkpoints"))?;
    fs::create_dir_all(base.join("backups"))?;
    fs::create_dir_all(base.join("logs"))?;
    Ok(())
}

/// A persistent task that survives restarts
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PersistentTask {
    pub id: String,
    pub description: String,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
    pub phase: String,
    pub phase_index: u32,
    pub total_phases: u32,
    pub work_dir: String,
    pub findings: Vec<String>,
    pub executed_commands: Vec<ExecutedCommand>,
    pub files_created: Vec<String>,
    pub files_modified: Vec<String>,
    pub status: TaskStatus,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutedCommand {
    pub command: String,
    pub output: String,
    pub success: bool,
    pub timestamp: DateTime<Utc>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TaskStatus {
    Running,
    Paused,
    Completed,
    Failed,
    WaitingForInput,
}

impl PersistentTask {
    pub fn new(id: &str, description: &str, work_dir: &str) -> Self {
        Self {
            id: id.to_string(),
            description: description.to_string(),
            created_at: Utc::now(),
            updated_at: Utc::now(),
            phase: "Extract".to_string(),
            phase_index: 0,
            total_phases: 11, // All phases in lean_agent
            work_dir: work_dir.to_string(),
            findings: Vec::new(),
            executed_commands: Vec::new(),
            files_created: Vec::new(),
            files_modified: Vec::new(),
            status: TaskStatus::Running,
            error: None,
        }
    }

    /// Save task state to disk
    pub fn save(&self) -> std::io::Result<()> {
        ensure_dirs()?;
        let path = sam_dir().join("tasks").join(format!("{}.json", self.id));
        let file = File::create(&path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        Ok(())
    }

    /// Load task state from disk
    pub fn load(id: &str) -> std::io::Result<Self> {
        let path = sam_dir().join("tasks").join(format!("{}.json", id));
        let file = File::open(&path)?;
        let reader = BufReader::new(file);
        serde_json::from_reader(reader)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
    }

    /// List all tasks
    pub fn list_all() -> std::io::Result<Vec<String>> {
        ensure_dirs()?;
        let path = sam_dir().join("tasks");
        let mut tasks = Vec::new();
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            if let Some(name) = entry.path().file_stem() {
                tasks.push(name.to_string_lossy().to_string());
            }
        }
        Ok(tasks)
    }

    /// Create a checkpoint
    pub fn checkpoint(&self) -> std::io::Result<()> {
        ensure_dirs()?;
        let path = sam_dir()
            .join("checkpoints")
            .join(format!("{}_{}.json", self.id, self.phase_index));
        let file = File::create(&path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        Ok(())
    }

    /// Resume from latest checkpoint
    pub fn resume_from_checkpoint(id: &str) -> std::io::Result<Self> {
        ensure_dirs()?;
        let checkpoints_dir = sam_dir().join("checkpoints");

        // Find latest checkpoint for this task
        let mut latest: Option<(u32, PathBuf)> = None;
        for entry in fs::read_dir(&checkpoints_dir)? {
            let entry = entry?;
            let name = entry.file_name().to_string_lossy().to_string();
            if name.starts_with(id) && name.ends_with(".json") {
                // Extract step number
                if let Some(step_str) = name.strip_prefix(&format!("{}_", id))
                    .and_then(|s| s.strip_suffix(".json"))
                {
                    if let Ok(step) = step_str.parse::<u32>() {
                        if latest.is_none() || step > latest.as_ref().unwrap().0 {
                            latest = Some((step, entry.path()));
                        }
                    }
                }
            }
        }

        match latest {
            Some((_, path)) => {
                let file = File::open(&path)?;
                let reader = BufReader::new(file);
                serde_json::from_reader(reader)
                    .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
            }
            None => Self::load(id), // Fall back to main task file
        }
    }

    /// Advance to next phase
    pub fn advance_phase(&mut self, new_phase: &str) {
        self.phase = new_phase.to_string();
        self.phase_index += 1;
        self.updated_at = Utc::now();
        let _ = self.checkpoint();
        let _ = self.save();
    }

    /// Record a command execution
    pub fn record_command(&mut self, command: &str, output: &str, success: bool) {
        self.executed_commands.push(ExecutedCommand {
            command: command.to_string(),
            output: output.to_string(),
            success,
            timestamp: Utc::now(),
        });
        self.updated_at = Utc::now();
        let _ = self.save();
    }

    /// Add a finding
    pub fn add_finding(&mut self, finding: &str) {
        self.findings.push(finding.to_string());
        self.updated_at = Utc::now();
        let _ = self.save();
    }

    /// Mark file as created
    pub fn mark_file_created(&mut self, path: &str) {
        if !self.files_created.contains(&path.to_string()) {
            self.files_created.push(path.to_string());
            let _ = self.save();
        }
    }

    /// Mark file as modified
    pub fn mark_file_modified(&mut self, path: &str) {
        if !self.files_modified.contains(&path.to_string()) {
            self.files_modified.push(path.to_string());
            let _ = self.save();
        }
    }

    /// Mark task as completed
    pub fn complete(&mut self) {
        self.status = TaskStatus::Completed;
        self.phase = "Complete".to_string();
        self.updated_at = Utc::now();
        let _ = self.save();
    }

    /// Mark task as failed
    pub fn fail(&mut self, error: &str) {
        self.status = TaskStatus::Failed;
        self.error = Some(error.to_string());
        self.updated_at = Utc::now();
        let _ = self.save();
    }
}

/// File backup system - backup before any modification
pub struct FileBackup;

impl FileBackup {
    /// Backup a file before modifying it
    pub fn backup(path: &str) -> std::io::Result<String> {
        ensure_dirs()?;

        let source = PathBuf::from(path);
        if !source.exists() {
            return Ok(String::new()); // Nothing to backup
        }

        let filename = source.file_name()
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_else(|| "unknown".to_string());

        let timestamp = Utc::now().format("%Y%m%d_%H%M%S").to_string();
        let backup_name = format!("{}_{}", timestamp, filename);
        let backup_path = sam_dir().join("backups").join(&backup_name);

        fs::copy(&source, &backup_path)?;

        Ok(backup_path.to_string_lossy().to_string())
    }

    /// Restore a file from backup
    pub fn restore(backup_path: &str, target_path: &str) -> std::io::Result<()> {
        fs::copy(backup_path, target_path)?;
        Ok(())
    }

    /// List all backups
    pub fn list_backups() -> std::io::Result<Vec<String>> {
        ensure_dirs()?;
        let path = sam_dir().join("backups");
        let mut backups = Vec::new();
        for entry in fs::read_dir(path)? {
            let entry = entry?;
            backups.push(entry.path().to_string_lossy().to_string());
        }
        backups.sort();
        backups.reverse(); // Most recent first
        Ok(backups)
    }
}

/// Protected files that SAM cannot modify
pub struct ProtectedFiles {
    paths: Vec<String>,
    patterns: Vec<String>,
}

impl ProtectedFiles {
    pub fn new() -> Self {
        Self {
            paths: vec![
                // Critical system paths
                "/etc".to_string(),
                "/usr".to_string(),
                "/bin".to_string(),
                "/sbin".to_string(),
                "/System".to_string(),
                // SAM's own code (prevent self-destruction)
                "/Users/davidquinton/ReverseLab/SAM".to_string(),
                "/Applications/SAM.app".to_string(),
            ],
            patterns: vec![
                // Never modify these file types
                ".git".to_string(),
                "node_modules".to_string(),
                ".env".to_string(),
                "credentials".to_string(),
                "password".to_string(),
                "secret".to_string(),
            ],
        }
    }

    /// Load custom protected files from config
    pub fn load() -> std::io::Result<Self> {
        ensure_dirs()?;
        let path = sam_dir().join("protected_files.json");

        if path.exists() {
            let file = File::open(&path)?;
            let reader = BufReader::new(file);
            Ok(serde_json::from_reader(reader)
                .unwrap_or_else(|_| Self::new()))
        } else {
            let pf = Self::new();
            pf.save()?;
            Ok(pf)
        }
    }

    /// Save protected files config
    pub fn save(&self) -> std::io::Result<()> {
        ensure_dirs()?;
        let path = sam_dir().join("protected_files.json");
        let file = File::create(&path)?;
        let writer = BufWriter::new(file);
        serde_json::to_writer_pretty(writer, &serde_json::json!({
            "paths": self.paths,
            "patterns": self.patterns,
        })).map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        Ok(())
    }

    /// Check if a path is protected
    pub fn is_protected(&self, path: &str) -> bool {
        // Check exact paths
        for protected in &self.paths {
            if path.starts_with(protected) {
                return true;
            }
        }

        // Check patterns
        for pattern in &self.patterns {
            if path.contains(pattern) {
                return true;
            }
        }

        false
    }

    /// Add a protected path
    pub fn add_path(&mut self, path: &str) {
        if !self.paths.contains(&path.to_string()) {
            self.paths.push(path.to_string());
            let _ = self.save();
        }
    }
}

impl Serialize for ProtectedFiles {
    fn serialize<S>(&self, serializer: S) -> Result<S::Ok, S::Error>
    where
        S: serde::Serializer,
    {
        use serde::ser::SerializeStruct;
        let mut state = serializer.serialize_struct("ProtectedFiles", 2)?;
        state.serialize_field("paths", &self.paths)?;
        state.serialize_field("patterns", &self.patterns)?;
        state.end()
    }
}

impl<'de> Deserialize<'de> for ProtectedFiles {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        struct Helper {
            paths: Vec<String>,
            patterns: Vec<String>,
        }

        let helper = Helper::deserialize(deserializer)?;
        Ok(Self {
            paths: helper.paths,
            patterns: helper.patterns,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_protected_files() {
        let pf = ProtectedFiles::new();
        assert!(pf.is_protected("/etc/passwd"));
        assert!(pf.is_protected("/Users/davidquinton/ReverseLab/SAM/test.rs"));
        assert!(!pf.is_protected("/tmp/test.txt"));
    }

    #[test]
    fn test_task_persistence() {
        let task = PersistentTask::new("test_001", "Test task", "/tmp/test");
        assert!(task.save().is_ok());

        let loaded = PersistentTask::load("test_001").unwrap();
        assert_eq!(loaded.description, "Test task");
    }
}
