// SAM Autonomous Backend - Rust implementation for system-level operations
// No permission prompts. No check-ins. Just execution.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tokio::sync::Mutex;
use tokio::time::interval;

// =============================================================================
// CONFIGURATION
// =============================================================================

#[derive(Clone, Serialize, Deserialize)]
pub struct AutonomousConfig {
    pub disk_threshold: f64,      // 0.85 = 85%
    pub memory_threshold: f64,    // 0.90 = 90%
    pub health_interval_secs: u64,
    pub project_interval_secs: u64,
    pub managed_paths: Vec<String>,
    pub project_paths: Vec<String>,
    pub external_storage: Option<String>,
}

impl Default for AutonomousConfig {
    fn default() -> Self {
        Self {
            disk_threshold: 0.85,
            memory_threshold: 0.90,
            health_interval_secs: 30,
            project_interval_secs: 300,
            managed_paths: vec![
                dirs::home_dir().unwrap().to_string_lossy().to_string(),
                "/Volumes".to_string(),
            ],
            project_paths: vec![
                format!("{}/ReverseLab", dirs::home_dir().unwrap().to_string_lossy()),
                format!("{}/Projects", dirs::home_dir().unwrap().to_string_lossy()),
            ],
            external_storage: Some("/Volumes/External".to_string()),
        }
    }
}

// =============================================================================
// SYSTEM METRICS
// =============================================================================

#[derive(Clone, Serialize, Deserialize)]
pub struct DiskMetrics {
    pub total_bytes: u64,
    pub used_bytes: u64,
    pub available_bytes: u64,
    pub percentage: f64,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct MemoryMetrics {
    pub total_bytes: u64,
    pub used_bytes: u64,
    pub percentage: f64,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct SystemMetrics {
    pub disk: DiskMetrics,
    pub memory: MemoryMetrics,
    pub cpu_usage: f64,
    pub process_count: u32,
    pub zombie_count: u32,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct ActionResult {
    pub success: bool,
    pub action: String,
    pub details: String,
    pub bytes_affected: Option<u64>,
    pub files_affected: Option<u32>,
    pub timestamp: u64,
}

impl ActionResult {
    pub fn success(action: &str, details: &str) -> Self {
        Self {
            success: true,
            action: action.to_string(),
            details: details.to_string(),
            bytes_affected: None,
            files_affected: None,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    pub fn failure(action: &str, details: &str) -> Self {
        Self {
            success: false,
            action: action.to_string(),
            details: details.to_string(),
            bytes_affected: None,
            files_affected: None,
            timestamp: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_secs(),
        }
    }

    pub fn with_bytes(mut self, bytes: u64) -> Self {
        self.bytes_affected = Some(bytes);
        self
    }

    pub fn with_files(mut self, files: u32) -> Self {
        self.files_affected = Some(files);
        self
    }
}

// =============================================================================
// TAURI COMMANDS - Direct execution, no prompts
// =============================================================================

#[tauri::command]
pub async fn get_system_metrics() -> Result<SystemMetrics, String> {
    let disk = get_disk_metrics().await?;
    let memory = get_memory_metrics().await?;
    let (cpu, procs, zombies) = get_process_metrics().await?;

    Ok(SystemMetrics {
        disk,
        memory,
        cpu_usage: cpu,
        process_count: procs,
        zombie_count: zombies,
    })
}

async fn get_disk_metrics() -> Result<DiskMetrics, String> {
    let output = Command::new("df")
        .args(["-k", "/"])
        .output()
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let lines: Vec<&str> = stdout.lines().collect();

    if lines.len() < 2 {
        return Err("Could not parse df output".to_string());
    }

    let parts: Vec<&str> = lines[1].split_whitespace().collect();
    if parts.len() < 4 {
        return Err("Unexpected df format".to_string());
    }

    let total: u64 = parts[1].parse().unwrap_or(0) * 1024;
    let used: u64 = parts[2].parse().unwrap_or(0) * 1024;
    let available: u64 = parts[3].parse().unwrap_or(0) * 1024;
    let percentage = if total > 0 {
        used as f64 / total as f64
    } else {
        0.0
    };

    Ok(DiskMetrics {
        total_bytes: total,
        used_bytes: used,
        available_bytes: available,
        percentage,
    })
}

async fn get_memory_metrics() -> Result<MemoryMetrics, String> {
    let output = Command::new("vm_stat")
        .output()
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout);

    // Parse vm_stat output (macOS specific)
    let mut pages_free: u64 = 0;
    let mut pages_active: u64 = 0;
    let mut pages_inactive: u64 = 0;
    let mut pages_wired: u64 = 0;

    for line in stdout.lines() {
        if line.contains("Pages free:") {
            pages_free = extract_number(line);
        } else if line.contains("Pages active:") {
            pages_active = extract_number(line);
        } else if line.contains("Pages inactive:") {
            pages_inactive = extract_number(line);
        } else if line.contains("Pages wired down:") {
            pages_wired = extract_number(line);
        }
    }

    let page_size: u64 = 4096; // macOS default
    let total = (pages_free + pages_active + pages_inactive + pages_wired) * page_size;
    let used = (pages_active + pages_wired) * page_size;
    let percentage = if total > 0 {
        used as f64 / total as f64
    } else {
        0.0
    };

    Ok(MemoryMetrics {
        total_bytes: total,
        used_bytes: used,
        percentage,
    })
}

fn extract_number(line: &str) -> u64 {
    line.split_whitespace()
        .last()
        .unwrap_or("0")
        .trim_end_matches('.')
        .parse()
        .unwrap_or(0)
}

async fn get_process_metrics() -> Result<(f64, u32, u32), String> {
    // Get CPU from top
    let top_output = Command::new("top")
        .args(["-l", "1", "-n", "0"])
        .output()
        .map_err(|e| e.to_string())?;

    let top_stdout = String::from_utf8_lossy(&top_output.stdout);
    let mut cpu_usage = 0.0;

    for line in top_stdout.lines() {
        if line.contains("CPU usage:") {
            // Parse "CPU usage: 5.26% user, 10.52% sys, 84.21% idle"
            if let Some(user_part) = line.split("user").next() {
                if let Some(pct) = user_part.split_whitespace().last() {
                    cpu_usage = pct.trim_end_matches('%').parse().unwrap_or(0.0);
                }
            }
            break;
        }
    }

    // Get process count
    let ps_output = Command::new("ps")
        .args(["aux"])
        .output()
        .map_err(|e| e.to_string())?;

    let ps_stdout = String::from_utf8_lossy(&ps_output.stdout);
    let process_count = ps_stdout.lines().count().saturating_sub(1) as u32;

    // Get zombie count
    let zombie_output = Command::new("ps")
        .args(["aux"])
        .output()
        .map_err(|e| e.to_string())?;

    let zombie_stdout = String::from_utf8_lossy(&zombie_output.stdout);
    let zombie_count = zombie_stdout
        .lines()
        .filter(|line| line.contains(" Z ") || line.contains(" Z+ "))
        .count() as u32;

    Ok((cpu_usage, process_count, zombie_count))
}

// =============================================================================
// DISK MANAGEMENT - Auto cleanup
// =============================================================================

#[tauri::command]
pub async fn cleanup_caches() -> Result<ActionResult, String> {
    let cache_paths = vec![
        dirs::home_dir().unwrap().join("Library/Caches"),
        dirs::home_dir().unwrap().join(".npm/_cacache"),
        dirs::home_dir().unwrap().join(".cargo/registry/cache"),
        dirs::home_dir().unwrap().join("Library/Developer/Xcode/DerivedData"),
        dirs::home_dir().unwrap().join(".gradle/caches"),
    ];

    let mut total_freed: u64 = 0;
    let mut files_deleted: u32 = 0;

    for cache_path in cache_paths {
        if cache_path.exists() {
            match calculate_dir_size(&cache_path) {
                Ok(size) => {
                    if let Ok(count) = clear_directory(&cache_path) {
                        total_freed += size;
                        files_deleted += count;
                    }
                }
                Err(_) => continue,
            }
        }
    }

    Ok(ActionResult::success(
        "cleanup_caches",
        &format!(
            "Cleared {} bytes from caches ({} files)",
            format_bytes(total_freed),
            files_deleted
        ),
    )
    .with_bytes(total_freed)
    .with_files(files_deleted))
}

#[tauri::command]
pub async fn empty_trash() -> Result<ActionResult, String> {
    let trash_path = dirs::home_dir().unwrap().join(".Trash");

    if !trash_path.exists() {
        return Ok(ActionResult::success("empty_trash", "Trash already empty"));
    }

    let size = calculate_dir_size(&trash_path).unwrap_or(0);
    let count = count_files(&trash_path).unwrap_or(0);

    // Actually empty the trash
    Command::new("rm")
        .args(["-rf", &format!("{}/*", trash_path.to_string_lossy())])
        .output()
        .map_err(|e| e.to_string())?;

    Ok(
        ActionResult::success("empty_trash", &format!("Emptied trash: {}", format_bytes(size)))
            .with_bytes(size)
            .with_files(count),
    )
}

#[tauri::command]
pub async fn cleanup_docker() -> Result<ActionResult, String> {
    // Docker system prune -af
    let output = Command::new("docker")
        .args(["system", "prune", "-af"])
        .output();

    match output {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout);
            Ok(ActionResult::success(
                "cleanup_docker",
                &format!("Docker cleanup complete: {}", stdout.lines().last().unwrap_or("")),
            ))
        }
        Err(_) => Ok(ActionResult::success(
            "cleanup_docker",
            "Docker not installed or not running",
        )),
    }
}

#[tauri::command]
pub async fn cleanup_logs(days_to_keep: u32) -> Result<ActionResult, String> {
    let log_paths = vec![
        dirs::home_dir().unwrap().join("Library/Logs"),
        PathBuf::from("/var/log"),
    ];

    let cutoff = SystemTime::now() - Duration::from_secs(days_to_keep as u64 * 24 * 60 * 60);
    let mut total_freed: u64 = 0;
    let mut files_deleted: u32 = 0;

    for log_path in log_paths {
        if log_path.exists() {
            if let Ok((freed, count)) = delete_old_files(&log_path, cutoff) {
                total_freed += freed;
                files_deleted += count;
            }
        }
    }

    Ok(ActionResult::success(
        "cleanup_logs",
        &format!(
            "Removed logs older than {} days: {}",
            days_to_keep,
            format_bytes(total_freed)
        ),
    )
    .with_bytes(total_freed)
    .with_files(files_deleted))
}

#[tauri::command]
pub async fn find_large_files(min_size_mb: u64, path: String) -> Result<Vec<FileInfo>, String> {
    let min_size = min_size_mb * 1024 * 1024;
    let mut large_files = Vec::new();

    find_files_larger_than(Path::new(&path), min_size, &mut large_files)?;

    // Sort by size descending
    large_files.sort_by(|a, b| b.size.cmp(&a.size));

    Ok(large_files)
}

#[derive(Clone, Serialize, Deserialize)]
pub struct FileInfo {
    pub path: String,
    pub size: u64,
    pub modified: u64,
    pub is_directory: bool,
}

fn find_files_larger_than(
    path: &Path,
    min_size: u64,
    results: &mut Vec<FileInfo>,
) -> Result<(), String> {
    if !path.exists() {
        return Ok(());
    }

    if path.is_file() {
        if let Ok(metadata) = fs::metadata(path) {
            if metadata.len() >= min_size {
                results.push(FileInfo {
                    path: path.to_string_lossy().to_string(),
                    size: metadata.len(),
                    modified: metadata
                        .modified()
                        .ok()
                        .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                        .map(|d| d.as_secs())
                        .unwrap_or(0),
                    is_directory: false,
                });
            }
        }
    } else if path.is_dir() {
        // Skip certain directories
        let skip_dirs = [".git", "node_modules", ".Trash", "Library"];
        let dir_name = path.file_name().and_then(|n| n.to_str()).unwrap_or("");

        if skip_dirs.contains(&dir_name) {
            return Ok(());
        }

        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                find_files_larger_than(&entry.path(), min_size, results)?;
            }
        }
    }

    Ok(())
}

#[tauri::command]
pub async fn move_to_external(paths: Vec<String>, destination: String) -> Result<ActionResult, String> {
    let dest_path = Path::new(&destination);

    if !dest_path.exists() {
        return Err(format!("Destination {} does not exist", destination));
    }

    let mut moved_bytes: u64 = 0;
    let mut moved_files: u32 = 0;

    for path_str in &paths {
        let source = Path::new(path_str);
        if !source.exists() {
            continue;
        }

        let file_name = source.file_name().unwrap_or_default();
        let dest_file = dest_path.join(file_name);

        // Get size before moving
        let size = if source.is_dir() {
            calculate_dir_size(source).unwrap_or(0)
        } else {
            fs::metadata(source).map(|m| m.len()).unwrap_or(0)
        };

        // Move file/directory
        if let Ok(_) = fs::rename(source, &dest_file) {
            moved_bytes += size;
            moved_files += 1;
        } else {
            // Try copy + delete if rename fails (cross-device)
            if source.is_dir() {
                copy_dir_all(source, &dest_file)?;
            } else {
                fs::copy(source, &dest_file).map_err(|e| e.to_string())?;
            }
            if source.is_dir() {
                fs::remove_dir_all(source).ok();
            } else {
                fs::remove_file(source).ok();
            }
            moved_bytes += size;
            moved_files += 1;
        }
    }

    Ok(ActionResult::success(
        "move_to_external",
        &format!(
            "Moved {} files ({}) to {}",
            moved_files,
            format_bytes(moved_bytes),
            destination
        ),
    )
    .with_bytes(moved_bytes)
    .with_files(moved_files))
}

#[tauri::command]
pub async fn aggressive_cleanup() -> Result<Vec<ActionResult>, String> {
    let mut results = Vec::new();

    // 1. Caches
    results.push(cleanup_caches().await?);

    // 2. Trash
    results.push(empty_trash().await?);

    // 3. Docker
    results.push(cleanup_docker().await?);

    // 4. Old logs (30 days)
    results.push(cleanup_logs(30).await?);

    // 5. npm cache
    let npm_result = Command::new("npm")
        .args(["cache", "clean", "--force"])
        .output();
    if npm_result.is_ok() {
        results.push(ActionResult::success("npm_cache_clean", "Cleared npm cache"));
    }

    // 6. pip cache
    let pip_result = Command::new("pip3")
        .args(["cache", "purge"])
        .output();
    if pip_result.is_ok() {
        results.push(ActionResult::success("pip_cache_clean", "Cleared pip cache"));
    }

    // 7. Homebrew cleanup
    let brew_result = Command::new("brew")
        .args(["cleanup", "--prune=all"])
        .output();
    if brew_result.is_ok() {
        results.push(ActionResult::success("brew_cleanup", "Cleaned Homebrew"));
    }

    Ok(results)
}

// =============================================================================
// PACKAGE MANAGEMENT - Auto install
// =============================================================================

#[tauri::command]
pub async fn install_package(name: String, manager: Option<String>) -> Result<ActionResult, String> {
    let mgr = manager.unwrap_or_else(|| detect_package_manager(&name));

    let (cmd, args) = match mgr.as_str() {
        "brew" => ("brew", vec!["install", &name]),
        "npm" => ("npm", vec!["install", "-g", &name]),
        "pip" => ("pip3", vec!["install", &name]),
        "cargo" => ("cargo", vec!["install", &name]),
        _ => return Err(format!("Unknown package manager: {}", mgr)),
    };

    let output = Command::new(cmd)
        .args(&args)
        .output()
        .map_err(|e| e.to_string())?;

    if output.status.success() {
        Ok(ActionResult::success(
            "install_package",
            &format!("Installed {} via {}", name, mgr),
        ))
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Install failed: {}", stderr))
    }
}

#[tauri::command]
pub async fn update_all_packages() -> Result<Vec<ActionResult>, String> {
    let mut results = Vec::new();

    // Homebrew
    let brew_update = Command::new("brew").args(["upgrade"]).output();
    if let Ok(out) = brew_update {
        results.push(if out.status.success() {
            ActionResult::success("brew_upgrade", "Updated Homebrew packages")
        } else {
            ActionResult::failure("brew_upgrade", "Homebrew update failed")
        });
    }

    // npm
    let npm_update = Command::new("npm").args(["update", "-g"]).output();
    if let Ok(out) = npm_update {
        results.push(if out.status.success() {
            ActionResult::success("npm_update", "Updated npm global packages")
        } else {
            ActionResult::failure("npm_update", "npm update failed")
        });
    }

    // pip
    let pip_list = Command::new("pip3")
        .args(["list", "--outdated", "--format=freeze"])
        .output();
    if let Ok(out) = pip_list {
        let stdout = String::from_utf8_lossy(&out.stdout);
        let packages: Vec<&str> = stdout
            .lines()
            .filter_map(|l| l.split("==").next())
            .collect();

        for pkg in packages.iter().take(20) {
            // Limit to 20 to avoid hanging
            Command::new("pip3")
                .args(["install", "--upgrade", pkg])
                .output()
                .ok();
        }
        results.push(ActionResult::success(
            "pip_update",
            &format!("Updated {} pip packages", packages.len().min(20)),
        ));
    }

    Ok(results)
}

fn detect_package_manager(package: &str) -> String {
    if package.starts_with('@') || package.contains('/') {
        "npm".to_string()
    } else if package.ends_with("-rs") || package.contains("cargo-") {
        "cargo".to_string()
    } else {
        "brew".to_string()
    }
}

// =============================================================================
// PROCESS MANAGEMENT
// =============================================================================

#[tauri::command]
pub async fn kill_zombies() -> Result<ActionResult, String> {
    // Find zombie processes
    let output = Command::new("ps")
        .args(["aux"])
        .output()
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut killed = 0;

    for line in stdout.lines() {
        if line.contains(" Z ") || line.contains(" Z+ ") {
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() > 1 {
                if let Ok(pid) = parts[1].parse::<i32>() {
                    // Kill parent of zombie
                    Command::new("kill").args(["-9", &pid.to_string()]).output().ok();
                    killed += 1;
                }
            }
        }
    }

    Ok(ActionResult::success(
        "kill_zombies",
        &format!("Killed {} zombie processes", killed),
    ))
}

#[tauri::command]
pub async fn kill_high_memory_processes(threshold_mb: u64) -> Result<ActionResult, String> {
    // Get processes sorted by memory
    let output = Command::new("ps")
        .args(["aux", "--sort=-rss"])
        .output()
        .map_err(|e| e.to_string())?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let threshold_kb = threshold_mb * 1024;
    let mut killed = 0;

    // Protected processes that should never be killed
    let protected = [
        "kernel_task",
        "launchd",
        "WindowServer",
        "loginwindow",
        "Finder",
        "Dock",
        "SystemUIServer",
    ];

    for line in stdout.lines().skip(1) {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() < 11 {
            continue;
        }

        let rss: u64 = parts[5].parse().unwrap_or(0);
        let process_name = parts[10];

        if rss > threshold_kb && !protected.iter().any(|p| process_name.contains(p)) {
            if let Ok(pid) = parts[1].parse::<i32>() {
                Command::new("kill").args([&pid.to_string()]).output().ok();
                killed += 1;
            }
        }
    }

    Ok(ActionResult::success(
        "kill_high_memory",
        &format!(
            "Killed {} processes using more than {}MB",
            killed, threshold_mb
        ),
    ))
}

// =============================================================================
// WEB SCRAPING
// =============================================================================

#[tauri::command]
pub async fn scrape_url(url: String) -> Result<ScrapeResult, String> {
    let client = reqwest::Client::builder()
        .user_agent("SAM/1.0 (Autonomous Agent)")
        .timeout(Duration::from_secs(30))
        .build()
        .map_err(|e| e.to_string())?;

    let response = client.get(&url).send().await.map_err(|e| e.to_string())?;

    let status = response.status().as_u16();
    let headers: HashMap<String, String> = response
        .headers()
        .iter()
        .map(|(k, v)| (k.to_string(), v.to_str().unwrap_or("").to_string()))
        .collect();

    let body = response.text().await.map_err(|e| e.to_string())?;

    // Extract links
    let link_regex = regex::Regex::new(r#"href=["']([^"']+)["']"#).unwrap();
    let links: Vec<String> = link_regex
        .captures_iter(&body)
        .filter_map(|cap| cap.get(1).map(|m| m.as_str().to_string()))
        .collect();

    Ok(ScrapeResult {
        url,
        status,
        headers,
        body,
        links,
        timestamp: SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs(),
    })
}

#[derive(Clone, Serialize, Deserialize)]
pub struct ScrapeResult {
    pub url: String,
    pub status: u16,
    pub headers: HashMap<String, String>,
    pub body: String,
    pub links: Vec<String>,
    pub timestamp: u64,
}

#[tauri::command]
pub async fn scrape_multiple(urls: Vec<String>) -> Result<Vec<ScrapeResult>, String> {
    let mut results = Vec::new();

    for url in urls {
        match scrape_url(url).await {
            Ok(result) => results.push(result),
            Err(_) => continue, // Skip failures, keep going
        }

        // Small delay to be polite
        tokio::time::sleep(Duration::from_millis(500)).await;
    }

    Ok(results)
}

// =============================================================================
// PROJECT MANAGEMENT
// =============================================================================

#[tauri::command]
pub async fn scan_projects(base_paths: Vec<String>) -> Result<Vec<ProjectInfo>, String> {
    let mut projects = Vec::new();

    for base in base_paths {
        scan_directory_for_projects(Path::new(&base), &mut projects, 0, 3)?;
    }

    Ok(projects)
}

#[derive(Clone, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub path: String,
    pub name: String,
    pub project_type: String,
    pub has_git: bool,
    pub has_uncommitted: bool,
    pub last_modified: u64,
}

fn scan_directory_for_projects(
    path: &Path,
    projects: &mut Vec<ProjectInfo>,
    depth: u32,
    max_depth: u32,
) -> Result<(), String> {
    if depth > max_depth || !path.exists() || !path.is_dir() {
        return Ok(());
    }

    // Check if this is a project
    let project_type = detect_project_type(path);
    if let Some(ptype) = project_type {
        let has_git = path.join(".git").exists();
        let has_uncommitted = if has_git {
            check_uncommitted_changes(path)
        } else {
            false
        };

        projects.push(ProjectInfo {
            path: path.to_string_lossy().to_string(),
            name: path
                .file_name()
                .and_then(|n| n.to_str())
                .unwrap_or("unknown")
                .to_string(),
            project_type: ptype,
            has_git,
            has_uncommitted,
            last_modified: fs::metadata(path)
                .ok()
                .and_then(|m| m.modified().ok())
                .and_then(|t| t.duration_since(UNIX_EPOCH).ok())
                .map(|d| d.as_secs())
                .unwrap_or(0),
        });

        return Ok(()); // Don't recurse into projects
    }

    // Recurse into subdirectories
    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let entry_path = entry.path();
            if entry_path.is_dir() {
                let name = entry_path
                    .file_name()
                    .and_then(|n| n.to_str())
                    .unwrap_or("");
                if !name.starts_with('.') && name != "node_modules" {
                    scan_directory_for_projects(&entry_path, projects, depth + 1, max_depth)?;
                }
            }
        }
    }

    Ok(())
}

fn detect_project_type(path: &Path) -> Option<String> {
    if path.join("package.json").exists() {
        Some("node".to_string())
    } else if path.join("Cargo.toml").exists() {
        Some("rust".to_string())
    } else if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
        Some("python".to_string())
    } else if path.join("Package.swift").exists() {
        Some("swift".to_string())
    } else if path.join("go.mod").exists() {
        Some("go".to_string())
    } else {
        None
    }
}

fn check_uncommitted_changes(path: &Path) -> bool {
    let output = Command::new("git")
        .args(["status", "--porcelain"])
        .current_dir(path)
        .output();

    match output {
        Ok(out) => !out.stdout.is_empty(),
        Err(_) => false,
    }
}

#[tauri::command]
pub async fn maintain_project(path: String) -> Result<Vec<ActionResult>, String> {
    let project_path = Path::new(&path);
    let mut results = Vec::new();

    // Detect project type
    let project_type = detect_project_type(project_path).unwrap_or_default();

    match project_type.as_str() {
        "node" => {
            // npm audit fix
            let audit = Command::new("npm")
                .args(["audit", "fix"])
                .current_dir(project_path)
                .output();
            if let Ok(out) = audit {
                results.push(if out.status.success() {
                    ActionResult::success("npm_audit_fix", "Fixed npm vulnerabilities")
                } else {
                    ActionResult::failure("npm_audit_fix", "Some vulnerabilities could not be fixed")
                });
            }

            // npm update
            let update = Command::new("npm")
                .args(["update"])
                .current_dir(project_path)
                .output();
            if let Ok(out) = update {
                results.push(if out.status.success() {
                    ActionResult::success("npm_update", "Updated dependencies")
                } else {
                    ActionResult::failure("npm_update", "Update failed")
                });
            }
        }
        "rust" => {
            // cargo update
            let update = Command::new("cargo")
                .args(["update"])
                .current_dir(project_path)
                .output();
            if let Ok(out) = update {
                results.push(if out.status.success() {
                    ActionResult::success("cargo_update", "Updated Cargo dependencies")
                } else {
                    ActionResult::failure("cargo_update", "Update failed")
                });
            }
        }
        "python" => {
            // pip upgrade
            let upgrade = Command::new("pip3")
                .args(["install", "--upgrade", "-r", "requirements.txt"])
                .current_dir(project_path)
                .output();
            if let Ok(out) = upgrade {
                results.push(if out.status.success() {
                    ActionResult::success("pip_upgrade", "Upgraded Python packages")
                } else {
                    ActionResult::failure("pip_upgrade", "Upgrade failed")
                });
            }
        }
        _ => {}
    }

    Ok(results)
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

fn calculate_dir_size(path: &Path) -> Result<u64, String> {
    let mut size = 0u64;

    if path.is_file() {
        return fs::metadata(path)
            .map(|m| m.len())
            .map_err(|e| e.to_string());
    }

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let entry_path = entry.path();
            if entry_path.is_file() {
                size += fs::metadata(&entry_path).map(|m| m.len()).unwrap_or(0);
            } else if entry_path.is_dir() {
                size += calculate_dir_size(&entry_path).unwrap_or(0);
            }
        }
    }

    Ok(size)
}

fn count_files(path: &Path) -> Result<u32, String> {
    let mut count = 0u32;

    if path.is_file() {
        return Ok(1);
    }

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let entry_path = entry.path();
            if entry_path.is_file() {
                count += 1;
            } else if entry_path.is_dir() {
                count += count_files(&entry_path).unwrap_or(0);
            }
        }
    }

    Ok(count)
}

fn clear_directory(path: &Path) -> Result<u32, String> {
    let mut count = 0u32;

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let entry_path = entry.path();
            if entry_path.is_dir() {
                fs::remove_dir_all(&entry_path).ok();
            } else {
                fs::remove_file(&entry_path).ok();
            }
            count += 1;
        }
    }

    Ok(count)
}

fn delete_old_files(path: &Path, cutoff: SystemTime) -> Result<(u64, u32), String> {
    let mut freed = 0u64;
    let mut count = 0u32;

    if let Ok(entries) = fs::read_dir(path) {
        for entry in entries.flatten() {
            let entry_path = entry.path();
            if let Ok(metadata) = fs::metadata(&entry_path) {
                if let Ok(modified) = metadata.modified() {
                    if modified < cutoff {
                        freed += metadata.len();
                        if entry_path.is_dir() {
                            fs::remove_dir_all(&entry_path).ok();
                        } else {
                            fs::remove_file(&entry_path).ok();
                        }
                        count += 1;
                    }
                }
            }
        }
    }

    Ok((freed, count))
}

fn copy_dir_all(src: &Path, dst: &Path) -> Result<(), String> {
    fs::create_dir_all(dst).map_err(|e| e.to_string())?;

    if let Ok(entries) = fs::read_dir(src) {
        for entry in entries.flatten() {
            let ty = entry.file_type().map_err(|e| e.to_string())?;
            let src_path = entry.path();
            let dst_path = dst.join(entry.file_name());

            if ty.is_dir() {
                copy_dir_all(&src_path, &dst_path)?;
            } else {
                fs::copy(&src_path, &dst_path).map_err(|e| e.to_string())?;
            }
        }
    }

    Ok(())
}

fn format_bytes(bytes: u64) -> String {
    const KB: u64 = 1024;
    const MB: u64 = KB * 1024;
    const GB: u64 = MB * 1024;

    if bytes >= GB {
        format!("{:.2} GB", bytes as f64 / GB as f64)
    } else if bytes >= MB {
        format!("{:.2} MB", bytes as f64 / MB as f64)
    } else if bytes >= KB {
        format!("{:.2} KB", bytes as f64 / KB as f64)
    } else {
        format!("{} bytes", bytes)
    }
}
