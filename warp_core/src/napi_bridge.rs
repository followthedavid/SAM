/*!
 * N-API Bridge - Expose Rust functions to Node.js/Electron
 * 
 * Provides Node.js bindings for:
 * - Command execution
 * - File I/O operations
 * - Diff application
 * - OSC 133 parsing
 */

use napi::bindgen_prelude::*;
use napi_derive::napi;
use std::process::{Command, Stdio};
use std::path::Path;
use std::fs;
use std::io::{Write, Read};
use crate::osc_parser::{OSC133Parser, OSC133Type};

/// Execute a command and return stdout, stderr, and exit code
#[napi(object)]
pub struct CommandResult {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

#[napi]
pub fn run_script_js(cmd: String, args: Vec<String>, cwd: Option<String>) -> Result<CommandResult> {
    let mut command = Command::new(&cmd);
    command.args(&args);
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());
    
    if let Some(dir) = cwd {
        command.current_dir(dir);
    }
    
    let output = command
        .output()
        .map_err(|e| Error::from_reason(format!("Failed to execute command: {}", e)))?;
    
    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();
    let exit_code = output.status.code().unwrap_or(-1);
    
    Ok(CommandResult {
        stdout,
        stderr,
        exit_code,
    })
}

/// Read file contents
#[napi]
pub fn read_file_js(path: String) -> Result<String> {
    fs::read_to_string(&path)
        .map_err(|e| Error::from_reason(format!("Failed to read file {}: {}", path, e)))
}

/// Write file contents
#[napi]
pub fn write_file_js(path: String, content: String) -> Result<()> {
    // Ensure parent directory exists
    if let Some(parent) = Path::new(&path).parent() {
        fs::create_dir_all(parent)
            .map_err(|e| Error::from_reason(format!("Failed to create directory: {}", e)))?;
    }
    
    fs::write(&path, content)
        .map_err(|e| Error::from_reason(format!("Failed to write file {}: {}", path, e)))
}

/// Apply a unified diff to a file
#[napi]
pub fn apply_diff_js(file_path: String, diff: String) -> Result<String> {
    // Read original file
    let original = read_file_js(file_path.clone())?;
    
    // Apply diff using diffy
    let patch = diffy::Patch::from_str(&diff)
        .map_err(|e| Error::from_reason(format!("Invalid diff: {}", e)))?;
    
    let result = diffy::apply(&original, &patch)
        .map_err(|e| Error::from_reason(format!("Failed to apply diff: {}", e)))?;
    
    // Write back
    write_file_js(file_path, result.clone())?;
    
    Ok(result)
}

/// Parse PTY stream for OSC 133 sequences
#[napi(object)]
pub struct OSC133Event {
    pub event_type: String,
    pub exit_code: Option<i32>,
}

#[napi]
pub fn parse_osc_stream(data: String) -> Result<Vec<OSC133Event>> {
    let mut parser = OSC133Parser::new();
    let events = parser.parse(data.as_bytes());
    
    let results: Vec<OSC133Event> = events
        .into_iter()
        .filter_map(|event| {
            event.osc_type.map(|osc| {
                let exit_code = if let OSC133Type::CommandFinished { exit_code } = osc {
                    exit_code
                } else {
                    None
                };
                
                OSC133Event {
                    event_type: event.event_type,
                    exit_code,
                }
            })
        })
        .collect();
    
    Ok(results)
}

/// List directory contents
#[napi(object)]
pub struct DirEntry {
    pub name: String,
    pub is_dir: bool,
    pub size: i64,
}

#[napi]
pub fn list_dir_js(path: String) -> Result<Vec<DirEntry>> {
    let entries = fs::read_dir(&path)
        .map_err(|e| Error::from_reason(format!("Failed to read directory {}: {}", path, e)))?;
    
    let mut results = Vec::new();
    
    for entry in entries {
        let entry = entry.map_err(|e| Error::from_reason(format!("Failed to read entry: {}", e)))?;
        let metadata = entry.metadata()
            .map_err(|e| Error::from_reason(format!("Failed to read metadata: {}", e)))?;
        
        results.push(DirEntry {
            name: entry.file_name().to_string_lossy().to_string(),
            is_dir: metadata.is_dir(),
            size: metadata.len() as i64,
        });
    }
    
    Ok(results)
}

/// Check if path exists
#[napi]
pub fn path_exists_js(path: String) -> bool {
    Path::new(&path).exists()
}

/// Get absolute path
#[napi]
pub fn abs_path_js(path: String) -> Result<String> {
    let abs = fs::canonicalize(&path)
        .map_err(|e| Error::from_reason(format!("Failed to canonicalize path {}: {}", path, e)))?;
    
    Ok(abs.to_string_lossy().to_string())
}

/// Delete file or directory
#[napi]
pub fn delete_path_js(path: String, recursive: bool) -> Result<()> {
    let p = Path::new(&path);
    
    if p.is_dir() {
        if recursive {
            fs::remove_dir_all(&path)
                .map_err(|e| Error::from_reason(format!("Failed to delete directory {}: {}", path, e)))?;
        } else {
            fs::remove_dir(&path)
                .map_err(|e| Error::from_reason(format!("Failed to delete directory {}: {}", path, e)))?;
        }
    } else {
        fs::remove_file(&path)
            .map_err(|e| Error::from_reason(format!("Failed to delete file {}: {}", path, e)))?;
    }
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_command_execution() {
        let result = run_script_js("echo".to_string(), vec!["hello".to_string()], None).unwrap();
        assert_eq!(result.exit_code, 0);
        assert!(result.stdout.contains("hello"));
    }
    
    #[test]
    fn test_file_operations() {
        let path = "/tmp/warp_test_file.txt".to_string();
        let content = "test content".to_string();
        
        write_file_js(path.clone(), content.clone()).unwrap();
        let read = read_file_js(path.clone()).unwrap();
        assert_eq!(read, content);
        
        delete_path_js(path, false).unwrap();
    }
}
