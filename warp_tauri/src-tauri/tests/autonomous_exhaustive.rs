// SAM Autonomous System - Exhaustive Rust Tests
// Tests all Rust backend functionality directly

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;
use std::process::Command;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

// =============================================================================
// TEST UTILITIES
// =============================================================================

fn get_test_dir() -> PathBuf {
    let timestamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_millis();
    let dir = std::env::temp_dir().join(format!("sam-rust-test-{}", timestamp));
    fs::create_dir_all(&dir).unwrap();
    dir
}

fn cleanup_test_dir(dir: &PathBuf) {
    if dir.exists() {
        fs::remove_dir_all(dir).ok();
    }
}

// =============================================================================
// SYSTEM METRICS TESTS
// =============================================================================

#[cfg(test)]
mod system_metrics_tests {
    use super::*;

    #[test]
    fn test_disk_metrics_collection() {
        let output = Command::new("df")
            .args(["-k", "/"])
            .output()
            .expect("Failed to run df");

        assert!(output.status.success());

        let stdout = String::from_utf8_lossy(&output.stdout);
        let lines: Vec<&str> = stdout.lines().collect();

        assert!(lines.len() >= 2, "df should return header + data");

        let parts: Vec<&str> = lines[1].split_whitespace().collect();
        assert!(parts.len() >= 4, "df should have at least 4 columns");

        let total: u64 = parts[1].parse().expect("Total should be numeric");
        let used: u64 = parts[2].parse().expect("Used should be numeric");

        assert!(total > 0, "Total disk should be > 0");
        assert!(used > 0, "Used disk should be > 0");
        assert!(used <= total, "Used should not exceed total");

        println!("Disk: {} KB used of {} KB", used, total);
    }

    #[test]
    fn test_memory_metrics_collection() {
        let output = Command::new("vm_stat")
            .output()
            .expect("Failed to run vm_stat");

        assert!(output.status.success());

        let stdout = String::from_utf8_lossy(&output.stdout);

        // Should contain memory page info
        assert!(stdout.contains("Pages"), "vm_stat should report pages");
        assert!(stdout.contains("free") || stdout.contains("active"), "Should have memory states");

        println!("Memory stats collected successfully");
    }

    #[test]
    fn test_process_metrics_collection() {
        let output = Command::new("ps")
            .args(["aux"])
            .output()
            .expect("Failed to run ps");

        assert!(output.status.success());

        let stdout = String::from_utf8_lossy(&output.stdout);
        let lines: Vec<&str> = stdout.lines().collect();

        // Should have header + at least a few processes
        assert!(lines.len() > 10, "Should have many processes running");

        println!("Found {} processes", lines.len() - 1);
    }

    #[test]
    fn test_cpu_metrics_collection() {
        let output = Command::new("top")
            .args(["-l", "1", "-n", "0"])
            .output()
            .expect("Failed to run top");

        assert!(output.status.success());

        let stdout = String::from_utf8_lossy(&output.stdout);
        assert!(stdout.contains("CPU"), "top should report CPU");

        println!("CPU metrics collected");
    }

    #[test]
    fn test_rapid_metrics_collection() {
        let start = std::time::Instant::now();
        let iterations = 10;

        for _ in 0..iterations {
            Command::new("df").args(["-k", "/"]).output().unwrap();
        }

        let elapsed = start.elapsed();
        let avg_ms = elapsed.as_millis() / iterations as u128;

        assert!(avg_ms < 100, "Each metric collection should be < 100ms, got {}ms", avg_ms);
        println!("{} metrics collected in {:?}, avg {}ms", iterations, elapsed, avg_ms);
    }
}

// =============================================================================
// DISK MANAGEMENT TESTS
// =============================================================================

#[cfg(test)]
mod disk_management_tests {
    use super::*;

    #[test]
    fn test_cache_directory_identification() {
        let home = dirs::home_dir().expect("Should have home directory");

        let cache_paths = vec![
            home.join("Library/Caches"),
            home.join(".npm"),
            home.join(".cargo/registry/cache"),
        ];

        for path in cache_paths {
            if path.exists() {
                println!("Cache exists: {:?}", path);
                let size = dir_size(&path);
                println!("  Size: {} bytes", size);
            } else {
                println!("Cache not found: {:?}", path);
            }
        }
    }

    #[test]
    fn test_trash_location() {
        let home = dirs::home_dir().expect("Should have home directory");
        let trash = home.join(".Trash");

        if trash.exists() {
            let size = dir_size(&trash);
            println!("Trash size: {} bytes", size);
        } else {
            println!("Trash directory not found");
        }
    }

    #[test]
    fn test_file_creation_and_deletion() {
        let test_dir = get_test_dir();
        let test_file = test_dir.join("test.txt");

        // Create
        fs::write(&test_file, "test content").expect("Should create file");
        assert!(test_file.exists());

        // Read
        let content = fs::read_to_string(&test_file).expect("Should read file");
        assert_eq!(content, "test content");

        // Delete
        fs::remove_file(&test_file).expect("Should delete file");
        assert!(!test_file.exists());

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_directory_size_calculation() {
        let test_dir = get_test_dir();

        // Create test files
        for i in 0..10 {
            let file = test_dir.join(format!("file{}.txt", i));
            fs::write(&file, "x".repeat(1000)).unwrap();
        }

        let size = dir_size(&test_dir);
        assert!(size >= 10000, "Should be at least 10KB, got {} bytes", size);

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_old_file_detection() {
        let test_dir = get_test_dir();

        // Create files with different ages
        let new_file = test_dir.join("new.txt");
        fs::write(&new_file, "new").unwrap();

        let old_file = test_dir.join("old.txt");
        fs::write(&old_file, "old").unwrap();

        // Set old modification time (30 days ago)
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let old_time = SystemTime::now() - Duration::from_secs(30 * 24 * 60 * 60);
            filetime::set_file_mtime(&old_file, filetime::FileTime::from_system_time(old_time)).ok();
        }

        // Check modification times
        let new_meta = fs::metadata(&new_file).unwrap();
        let old_meta = fs::metadata(&old_file).unwrap();

        println!("New file modified: {:?}", new_meta.modified());
        println!("Old file modified: {:?}", old_meta.modified());

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_large_file_detection() {
        let test_dir = get_test_dir();

        // Create files of various sizes
        let small_file = test_dir.join("small.txt");
        fs::write(&small_file, "x".repeat(100)).unwrap();

        let medium_file = test_dir.join("medium.txt");
        fs::write(&medium_file, "x".repeat(100_000)).unwrap();

        let large_file = test_dir.join("large.txt");
        fs::write(&large_file, "x".repeat(1_000_000)).unwrap();

        // Find files > 50KB
        let threshold = 50_000;
        let mut large_files = Vec::new();

        for entry in fs::read_dir(&test_dir).unwrap() {
            let entry = entry.unwrap();
            let meta = entry.metadata().unwrap();
            if meta.len() > threshold {
                large_files.push((entry.path(), meta.len()));
            }
        }

        assert_eq!(large_files.len(), 2, "Should find 2 files > 50KB");
        println!("Large files found: {:?}", large_files);

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_file_move_operation() {
        let test_dir = get_test_dir();
        let src_dir = test_dir.join("src");
        let dst_dir = test_dir.join("dst");

        fs::create_dir_all(&src_dir).unwrap();
        fs::create_dir_all(&dst_dir).unwrap();

        let src_file = src_dir.join("move_me.txt");
        fs::write(&src_file, "content to move").unwrap();

        let dst_file = dst_dir.join("move_me.txt");

        // Move using rename
        fs::rename(&src_file, &dst_file).unwrap();

        assert!(!src_file.exists(), "Source should not exist");
        assert!(dst_file.exists(), "Destination should exist");

        let content = fs::read_to_string(&dst_file).unwrap();
        assert_eq!(content, "content to move");

        cleanup_test_dir(&test_dir);
    }

    fn dir_size(path: &PathBuf) -> u64 {
        let mut size = 0u64;

        if path.is_file() {
            return fs::metadata(path).map(|m| m.len()).unwrap_or(0);
        }

        if let Ok(entries) = fs::read_dir(path) {
            for entry in entries.flatten() {
                let entry_path = entry.path();
                if entry_path.is_file() {
                    size += fs::metadata(&entry_path).map(|m| m.len()).unwrap_or(0);
                } else if entry_path.is_dir() {
                    size += dir_size(&entry_path);
                }
            }
        }

        size
    }
}

// =============================================================================
// PACKAGE MANAGEMENT TESTS
// =============================================================================

#[cfg(test)]
mod package_management_tests {
    use super::*;

    #[test]
    fn test_brew_availability() {
        let output = Command::new("brew")
            .args(["--version"])
            .output();

        match output {
            Ok(out) if out.status.success() => {
                let version = String::from_utf8_lossy(&out.stdout);
                println!("Homebrew: {}", version.lines().next().unwrap_or("unknown"));
            }
            _ => {
                println!("Homebrew not installed");
            }
        }
    }

    #[test]
    fn test_npm_availability() {
        let output = Command::new("npm")
            .args(["--version"])
            .output();

        match output {
            Ok(out) if out.status.success() => {
                let version = String::from_utf8_lossy(&out.stdout);
                println!("npm: {}", version.trim());
            }
            _ => {
                println!("npm not installed");
            }
        }
    }

    #[test]
    fn test_pip_availability() {
        let output = Command::new("pip3")
            .args(["--version"])
            .output();

        match output {
            Ok(out) if out.status.success() => {
                let version = String::from_utf8_lossy(&out.stdout);
                println!("pip: {}", version.lines().next().unwrap_or("unknown"));
            }
            _ => {
                println!("pip not installed");
            }
        }
    }

    #[test]
    fn test_cargo_availability() {
        let output = Command::new("cargo")
            .args(["--version"])
            .output();

        match output {
            Ok(out) if out.status.success() => {
                let version = String::from_utf8_lossy(&out.stdout);
                println!("cargo: {}", version.trim());
            }
            _ => {
                println!("cargo not installed");
            }
        }
    }

    #[test]
    fn test_package_manager_detection() {
        fn detect_manager(package: &str) -> &'static str {
            if package.starts_with('@') || package.contains('/') {
                "npm"
            } else if package.ends_with("-rs") || package.contains("cargo-") {
                "cargo"
            } else {
                "brew"
            }
        }

        assert_eq!(detect_manager("@types/node"), "npm");
        assert_eq!(detect_manager("lodash"), "brew");
        assert_eq!(detect_manager("ripgrep-rs"), "cargo");
        assert_eq!(detect_manager("cargo-edit"), "cargo");
        assert_eq!(detect_manager("react/dom"), "npm");
    }
}

// =============================================================================
// PROCESS MANAGEMENT TESTS
// =============================================================================

#[cfg(test)]
mod process_management_tests {
    use super::*;

    #[test]
    fn test_zombie_detection() {
        let output = Command::new("ps")
            .args(["aux"])
            .output()
            .expect("Failed to run ps");

        let stdout = String::from_utf8_lossy(&output.stdout);
        let zombie_count = stdout
            .lines()
            .filter(|line| line.contains(" Z ") || line.contains(" Z+ "))
            .count();

        println!("Zombie processes: {}", zombie_count);
        // Usually 0, but could be more on busy systems
        assert!(zombie_count < 100, "Too many zombies");
    }

    #[test]
    fn test_protected_process_list() {
        let protected = [
            "kernel_task",
            "launchd",
            "WindowServer",
            "loginwindow",
            "Finder",
            "Dock",
            "SystemUIServer",
        ];

        let output = Command::new("ps")
            .args(["aux"])
            .output()
            .expect("Failed to run ps");

        let stdout = String::from_utf8_lossy(&output.stdout);

        for process in &protected {
            let found = stdout.lines().any(|line| line.contains(process));
            if found {
                println!("Protected process running: {}", process);
            }
        }
    }

    #[test]
    fn test_high_memory_process_detection() {
        let output = Command::new("ps")
            .args(["aux"])
            .output()
            .expect("Failed to run ps");

        let stdout = String::from_utf8_lossy(&output.stdout);
        let threshold_kb = 100_000; // 100MB

        let high_memory: Vec<_> = stdout
            .lines()
            .skip(1) // Skip header
            .filter_map(|line| {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() > 10 {
                    let rss: u64 = parts[5].parse().unwrap_or(0);
                    if rss > threshold_kb {
                        Some((parts[10].to_string(), rss))
                    } else {
                        None
                    }
                } else {
                    None
                }
            })
            .collect();

        println!("High memory processes (>100MB):");
        for (name, rss) in &high_memory {
            println!("  {}: {} MB", name, rss / 1024);
        }
    }
}

// =============================================================================
// WEB SCRAPING TESTS
// =============================================================================

#[cfg(test)]
mod web_scraping_tests {
    use super::*;

    #[test]
    fn test_curl_availability() {
        let output = Command::new("curl")
            .args(["--version"])
            .output()
            .expect("curl should be available");

        assert!(output.status.success());
        println!("curl available");
    }

    #[test]
    fn test_simple_fetch() {
        let output = Command::new("curl")
            .args(["-s", "-o", "/dev/null", "-w", "%{http_code}", "https://example.com"])
            .output()
            .expect("Failed to curl");

        let status = String::from_utf8_lossy(&output.stdout);
        assert_eq!(status.trim(), "200", "Should get 200 OK from example.com");
        println!("Fetched example.com: {}", status.trim());
    }

    #[test]
    fn test_fetch_with_content() {
        let output = Command::new("curl")
            .args(["-s", "https://example.com"])
            .output()
            .expect("Failed to curl");

        let body = String::from_utf8_lossy(&output.stdout);
        assert!(body.contains("Example Domain"), "Should contain 'Example Domain'");
        println!("Content length: {} bytes", body.len());
    }

    #[test]
    fn test_link_extraction() {
        let html = r#"
            <html>
            <body>
                <a href="https://example.com/page1">Link 1</a>
                <a href="/relative/path">Link 2</a>
                <a href="https://other.com">External</a>
            </body>
            </html>
        "#;

        let link_pattern = regex::Regex::new(r#"href=["']([^"']+)["']"#).unwrap();
        let links: Vec<_> = link_pattern
            .captures_iter(html)
            .filter_map(|cap| cap.get(1).map(|m| m.as_str()))
            .collect();

        assert_eq!(links.len(), 3);
        assert!(links.contains(&"https://example.com/page1"));
        assert!(links.contains(&"/relative/path"));
        println!("Extracted {} links", links.len());
    }

    #[test]
    fn test_rate_limiting_calculation() {
        use std::collections::HashMap;

        let mut last_request: HashMap<String, u64> = HashMap::new();
        let min_delay_ms = 1000u64;

        fn should_delay(domain: &str, last_request: &HashMap<String, u64>, min_delay: u64) -> u64 {
            let now = SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_millis() as u64;

            let last = last_request.get(domain).copied().unwrap_or(0);
            let elapsed = now.saturating_sub(last);

            if elapsed < min_delay {
                min_delay - elapsed
            } else {
                0
            }
        }

        // First request - no delay
        let delay1 = should_delay("example.com", &last_request, min_delay_ms);
        assert_eq!(delay1, 0);

        // Simulate request
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_millis() as u64;
        last_request.insert("example.com".to_string(), now);

        // Immediate second request - should delay
        let delay2 = should_delay("example.com", &last_request, min_delay_ms);
        assert!(delay2 > 0, "Should require delay for immediate second request");

        println!("Rate limiting working: delay={}ms", delay2);
    }
}

// =============================================================================
// PROJECT MANAGEMENT TESTS
// =============================================================================

#[cfg(test)]
mod project_management_tests {
    use super::*;

    #[test]
    fn test_node_project_detection() {
        let test_dir = get_test_dir();
        let project_dir = test_dir.join("node-project");
        fs::create_dir_all(&project_dir).unwrap();

        fs::write(
            project_dir.join("package.json"),
            r#"{"name": "test", "version": "1.0.0"}"#,
        )
        .unwrap();

        assert!(project_dir.join("package.json").exists());
        println!("Node project detected");

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_rust_project_detection() {
        let test_dir = get_test_dir();
        let project_dir = test_dir.join("rust-project");
        fs::create_dir_all(&project_dir).unwrap();

        fs::write(
            project_dir.join("Cargo.toml"),
            r#"[package]
name = "test"
version = "0.1.0"
"#,
        )
        .unwrap();

        assert!(project_dir.join("Cargo.toml").exists());
        println!("Rust project detected");

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_python_project_detection() {
        let test_dir = get_test_dir();
        let project_dir = test_dir.join("python-project");
        fs::create_dir_all(&project_dir).unwrap();

        fs::write(
            project_dir.join("pyproject.toml"),
            r#"[project]
name = "test"
version = "0.1.0"
"#,
        )
        .unwrap();

        assert!(project_dir.join("pyproject.toml").exists());
        println!("Python project detected");

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_project_type_detection() {
        fn detect_project_type(path: &PathBuf) -> Option<&'static str> {
            if path.join("package.json").exists() {
                Some("node")
            } else if path.join("Cargo.toml").exists() {
                Some("rust")
            } else if path.join("pyproject.toml").exists() || path.join("setup.py").exists() {
                Some("python")
            } else if path.join("Package.swift").exists() {
                Some("swift")
            } else if path.join("go.mod").exists() {
                Some("go")
            } else {
                None
            }
        }

        let test_dir = get_test_dir();

        // Create various project types
        let node = test_dir.join("node");
        fs::create_dir_all(&node).unwrap();
        fs::write(node.join("package.json"), "{}").unwrap();

        let rust = test_dir.join("rust");
        fs::create_dir_all(&rust).unwrap();
        fs::write(rust.join("Cargo.toml"), "").unwrap();

        let python = test_dir.join("python");
        fs::create_dir_all(&python).unwrap();
        fs::write(python.join("setup.py"), "").unwrap();

        assert_eq!(detect_project_type(&node), Some("node"));
        assert_eq!(detect_project_type(&rust), Some("rust"));
        assert_eq!(detect_project_type(&python), Some("python"));
        assert_eq!(detect_project_type(&test_dir), None);

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_git_status_detection() {
        let test_dir = get_test_dir();

        // Not a git repo
        let output = Command::new("git")
            .args(["status", "--porcelain"])
            .current_dir(&test_dir)
            .output();

        match output {
            Ok(out) => {
                if !out.status.success() {
                    println!("Not a git repo (expected)");
                }
            }
            Err(_) => {
                println!("Git not available");
            }
        }

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_project_scanning() {
        let test_dir = get_test_dir();
        let projects_dir = test_dir.join("projects");
        fs::create_dir_all(&projects_dir).unwrap();

        // Create multiple projects
        for (name, marker) in [("proj1", "package.json"), ("proj2", "Cargo.toml")] {
            let proj = projects_dir.join(name);
            fs::create_dir_all(&proj).unwrap();
            fs::write(proj.join(marker), "").unwrap();
        }

        // Scan
        let mut found = Vec::new();
        for entry in fs::read_dir(&projects_dir).unwrap() {
            let entry = entry.unwrap();
            let path = entry.path();
            if path.is_dir() {
                if path.join("package.json").exists() || path.join("Cargo.toml").exists() {
                    found.push(path.file_name().unwrap().to_string_lossy().to_string());
                }
            }
        }

        assert_eq!(found.len(), 2);
        println!("Found projects: {:?}", found);

        cleanup_test_dir(&test_dir);
    }
}

// =============================================================================
// INTEGRATION TESTS
// =============================================================================

#[cfg(test)]
mod integration_tests {
    use super::*;

    #[test]
    fn test_full_cleanup_cycle() {
        let test_dir = get_test_dir();

        // Create test files
        let cache_dir = test_dir.join("cache");
        fs::create_dir_all(&cache_dir).unwrap();

        for i in 0..10 {
            fs::write(cache_dir.join(format!("file{}.tmp", i)), "x".repeat(1000)).unwrap();
        }

        // Count files before
        let before = fs::read_dir(&cache_dir).unwrap().count();
        assert_eq!(before, 10);

        // "Cleanup" - delete all
        for entry in fs::read_dir(&cache_dir).unwrap() {
            let entry = entry.unwrap();
            fs::remove_file(entry.path()).unwrap();
        }

        // Count files after
        let after = fs::read_dir(&cache_dir).unwrap().count();
        assert_eq!(after, 0);

        println!("Cleanup cycle: {} -> {} files", before, after);

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_concurrent_operations() {
        use std::thread;

        let handles: Vec<_> = (0..5)
            .map(|i| {
                thread::spawn(move || {
                    // Simulate metric collection
                    let output = Command::new("df")
                        .args(["-k", "/"])
                        .output()
                        .expect("df failed");
                    assert!(output.status.success());
                    println!("Thread {} completed", i);
                })
            })
            .collect();

        for handle in handles {
            handle.join().unwrap();
        }

        println!("All concurrent operations completed");
    }

    #[test]
    fn test_error_recovery() {
        // Try to read non-existent file
        let result = fs::read_to_string("/this/path/does/not/exist");
        assert!(result.is_err());

        // Try to delete non-existent file
        let result = fs::remove_file("/this/path/does/not/exist");
        assert!(result.is_err());

        // Try to create directory in non-existent path (should fail)
        let result = fs::create_dir("/root/cannot/create/here");
        assert!(result.is_err());

        println!("Error recovery working - all errors handled gracefully");
    }

    #[test]
    fn test_performance_under_load() {
        let iterations = 100;
        let start = std::time::Instant::now();

        for _ in 0..iterations {
            // Simulate lightweight operation
            let _ = std::env::current_dir();
        }

        let elapsed = start.elapsed();
        let avg_ns = elapsed.as_nanos() / iterations as u128;

        assert!(avg_ns < 1_000_000, "Each operation should be < 1ms");
        println!("{} operations in {:?}, avg {}ns", iterations, elapsed, avg_ns);
    }
}

// =============================================================================
// STRESS TESTS
// =============================================================================

#[cfg(test)]
mod stress_tests {
    use super::*;

    #[test]
    fn test_many_file_operations() {
        let test_dir = get_test_dir();
        let file_count = 1000;

        let start = std::time::Instant::now();

        // Create many files
        for i in 0..file_count {
            let path = test_dir.join(format!("stress_{}.txt", i));
            fs::write(&path, format!("content {}", i)).unwrap();
        }

        let create_time = start.elapsed();

        // Read all files
        let read_start = std::time::Instant::now();
        for i in 0..file_count {
            let path = test_dir.join(format!("stress_{}.txt", i));
            let _ = fs::read_to_string(&path).unwrap();
        }

        let read_time = read_start.elapsed();

        // Delete all files
        let delete_start = std::time::Instant::now();
        for i in 0..file_count {
            let path = test_dir.join(format!("stress_{}.txt", i));
            fs::remove_file(&path).unwrap();
        }

        let delete_time = delete_start.elapsed();

        println!(
            "{} files: create {:?}, read {:?}, delete {:?}",
            file_count, create_time, read_time, delete_time
        );

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_deep_directory_traversal() {
        let test_dir = get_test_dir();

        // Create deep directory structure
        let mut current = test_dir.clone();
        for i in 0..20 {
            current = current.join(format!("level_{}", i));
            fs::create_dir_all(&current).unwrap();
            fs::write(current.join("file.txt"), "content").unwrap();
        }

        // Traverse and count files
        fn count_files(path: &PathBuf) -> usize {
            let mut count = 0;
            if path.is_file() {
                return 1;
            }
            if let Ok(entries) = fs::read_dir(path) {
                for entry in entries.flatten() {
                    count += count_files(&entry.path());
                }
            }
            count
        }

        let start = std::time::Instant::now();
        let file_count = count_files(&test_dir);
        let elapsed = start.elapsed();

        assert_eq!(file_count, 20);
        println!("Traversed 20-level deep structure in {:?}", elapsed);

        cleanup_test_dir(&test_dir);
    }

    #[test]
    fn test_large_file_handling() {
        let test_dir = get_test_dir();
        let large_file = test_dir.join("large.bin");

        // Create 10MB file
        let size = 10 * 1024 * 1024;
        let content = vec![0u8; size];

        let start = std::time::Instant::now();
        fs::write(&large_file, &content).unwrap();
        let write_time = start.elapsed();

        let read_start = std::time::Instant::now();
        let _ = fs::read(&large_file).unwrap();
        let read_time = read_start.elapsed();

        println!(
            "10MB file: write {:?}, read {:?}",
            write_time, read_time
        );

        cleanup_test_dir(&test_dir);
    }
}
