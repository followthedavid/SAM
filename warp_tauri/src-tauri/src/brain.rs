//! SAM Brain Integration
//!
//! Provides Tauri commands to access the SAM Brain modules:
//! - Project inventory (3,241 projects across 7 drives)
//! - Semantic memory and knowledge graph
//! - Style-aware code generation (sam-coder model)
//! - Multi-agent coordination

use serde::{Deserialize, Serialize};
use std::process::Command;
use std::path::PathBuf;

const BRAIN_DIR: &str = concat!(env!("CARGO_MANIFEST_DIR"), "/../sam_brain");

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectInfo {
    pub path: String,
    pub name: String,
    pub status: String,
    pub languages: Vec<String>,
    pub lines: u64,
    pub importance_score: u32,
    pub starred: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrainStatus {
    pub project_count: u32,
    pub active_projects: u32,
    pub memory_entries: u32,
    pub mlx_model: String,
    pub style_profile_loaded: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CategoryInfo {
    pub name: String,
    pub count: u32,
}

/// Get brain status and health
#[tauri::command]
pub fn get_brain_status() -> Result<BrainStatus, String> {
    // Check if inventory exists
    let inventory_path = PathBuf::from(BRAIN_DIR)
        .join("exhaustive_analysis")
        .join("master_inventory.json");

    if !inventory_path.exists() {
        return Ok(BrainStatus {
            project_count: 0,
            active_projects: 0,
            memory_entries: 0,
            mlx_model: "qwen2.5-1.5b+sam-lora".to_string(),
            style_profile_loaded: false,
        });
    }

    // Read inventory for counts
    let inventory = std::fs::read_to_string(&inventory_path)
        .map_err(|e| format!("Failed to read inventory: {}", e))?;

    let data: serde_json::Value = serde_json::from_str(&inventory)
        .map_err(|e| format!("Failed to parse inventory: {}", e))?;

    let projects = data.get("projects").and_then(|p| p.as_object());
    let project_count = projects.map(|p| p.len() as u32).unwrap_or(0);

    let active_projects = projects.map(|p| {
        p.values()
            .filter(|v| v.get("status").and_then(|s| s.as_str()) == Some("active"))
            .count() as u32
    }).unwrap_or(0);

    // MLX model (Ollama decommissioned 2026-01-18)
    // Check style profile
    let style_path = PathBuf::from(BRAIN_DIR)
        .join("training_data")
        .join("style_profile.json");

    Ok(BrainStatus {
        project_count,
        active_projects,
        memory_entries: 0, // TODO: integrate semantic memory
        mlx_model: "qwen2.5-1.5b+sam-lora".to_string(),
        style_profile_loaded: style_path.exists(),
    })
}

/// Search projects by query
#[tauri::command]
pub fn search_projects(query: String) -> Result<Vec<ProjectInfo>, String> {
    let output = Command::new("python3")
        .current_dir(BRAIN_DIR)
        .args(["project_browser.py", "search", &query])
        .output()
        .map_err(|e| format!("Failed to run project browser: {}", e))?;

    // For now, parse from inventory directly
    let inventory_path = PathBuf::from(BRAIN_DIR)
        .join("exhaustive_analysis")
        .join("master_inventory.json");

    let inventory = std::fs::read_to_string(&inventory_path)
        .map_err(|e| format!("Failed to read inventory: {}", e))?;

    let data: serde_json::Value = serde_json::from_str(&inventory)
        .map_err(|e| format!("Failed to parse inventory: {}", e))?;

    let query_lower = query.to_lowercase();
    let mut results = Vec::new();

    if let Some(projects) = data.get("projects").and_then(|p| p.as_object()) {
        for (path, info) in projects {
            let name = info.get("name").and_then(|n| n.as_str()).unwrap_or("");
            let desc = info.get("description").and_then(|d| d.as_str()).unwrap_or("");

            if name.to_lowercase().contains(&query_lower)
               || path.to_lowercase().contains(&query_lower)
               || desc.to_lowercase().contains(&query_lower) {
                results.push(ProjectInfo {
                    path: path.clone(),
                    name: name.to_string(),
                    status: info.get("status").and_then(|s| s.as_str()).unwrap_or("unknown").to_string(),
                    languages: info.get("languages")
                        .and_then(|l| l.as_array())
                        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
                        .unwrap_or_default(),
                    lines: info.get("total_lines").and_then(|l| l.as_u64()).unwrap_or(0),
                    importance_score: info.get("importance_score").and_then(|s| s.as_u64()).unwrap_or(0) as u32,
                    starred: info.get("starred").and_then(|s| s.as_bool()).unwrap_or(false),
                });
            }
        }
    }

    // Sort by importance score
    results.sort_by(|a, b| b.importance_score.cmp(&a.importance_score));
    results.truncate(50); // Limit results

    Ok(results)
}

/// Get project categories
#[tauri::command]
pub fn get_project_categories() -> Result<Vec<CategoryInfo>, String> {
    let output = Command::new("python3")
        .current_dir(BRAIN_DIR)
        .args(["project_browser.py", "categories"])
        .output()
        .map_err(|e| format!("Failed to run project browser: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut categories = Vec::new();

    for line in stdout.lines() {
        let parts: Vec<&str> = line.trim().split(':').collect();
        if parts.len() == 2 {
            let name = parts[0].trim().to_string();
            if let Ok(count) = parts[1].trim().split_whitespace().next().unwrap_or("0").parse::<u32>() {
                categories.push(CategoryInfo { name, count });
            }
        }
    }

    Ok(categories)
}

/// Generate code using MLX via sam_api.py (Ollama decommissioned 2026-01-18)
#[tauri::command]
pub async fn generate_code(prompt: String, context: Option<String>) -> Result<String, String> {
    let full_prompt = if let Some(ctx) = context {
        format!("{}\n\n{}", ctx, prompt)
    } else {
        prompt
    };

    let client = reqwest::Client::new();
    let resp = client.post("http://localhost:8765/api/query")
        .json(&serde_json::json!({"query": full_prompt}))
        .send()
        .await
        .map_err(|e| format!("MLX request failed: {}", e))?;

    let json: serde_json::Value = resp.json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    json.get("response")
        .and_then(|v| v.as_str())
        .map(|s| s.to_string())
        .ok_or_else(|| "No response from MLX".to_string())
}

/// Get starred/favorite projects
#[tauri::command]
pub fn get_starred_projects() -> Result<Vec<ProjectInfo>, String> {
    let inventory_path = PathBuf::from(BRAIN_DIR)
        .join("exhaustive_analysis")
        .join("master_inventory.json");

    let inventory = std::fs::read_to_string(&inventory_path)
        .map_err(|e| format!("Failed to read inventory: {}", e))?;

    let data: serde_json::Value = serde_json::from_str(&inventory)
        .map_err(|e| format!("Failed to parse inventory: {}", e))?;

    let mut results = Vec::new();

    if let Some(projects) = data.get("projects").and_then(|p| p.as_object()) {
        for (path, info) in projects {
            if info.get("starred").and_then(|s| s.as_bool()).unwrap_or(false) {
                results.push(ProjectInfo {
                    path: path.clone(),
                    name: info.get("name").and_then(|n| n.as_str()).unwrap_or("").to_string(),
                    status: info.get("status").and_then(|s| s.as_str()).unwrap_or("unknown").to_string(),
                    languages: info.get("languages")
                        .and_then(|l| l.as_array())
                        .map(|arr| arr.iter().filter_map(|v| v.as_str().map(|s| s.to_string())).collect())
                        .unwrap_or_default(),
                    lines: info.get("total_lines").and_then(|l| l.as_u64()).unwrap_or(0),
                    importance_score: info.get("importance_score").and_then(|s| s.as_u64()).unwrap_or(0) as u32,
                    starred: true,
                });
            }
        }
    }

    results.sort_by(|a, b| b.importance_score.cmp(&a.importance_score));
    Ok(results)
}

/// Add memory entry
#[tauri::command]
pub async fn add_memory(topic: String, content: String, importance: f32) -> Result<(), String> {
    let output = Command::new("python3")
        .current_dir(BRAIN_DIR)
        .args([
            "-c",
            &format!(
                r#"
import json
from semantic_memory import SemanticMemory
mem = SemanticMemory()
mem.add('{}', '{}', importance={})
mem.save()
print('OK')
"#,
                topic.replace("'", "\\'"),
                content.replace("'", "\\'"),
                importance
            ),
        ])
        .output()
        .map_err(|e| format!("Failed to add memory: {}", e))?;

    if output.status.success() {
        Ok(())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}

/// Query semantic memory
#[tauri::command]
pub async fn query_memory(query: String, limit: Option<u32>) -> Result<String, String> {
    let limit = limit.unwrap_or(5);

    let output = Command::new("python3")
        .current_dir(BRAIN_DIR)
        .args([
            "-c",
            &format!(
                r#"
import json
from semantic_memory import SemanticMemory
mem = SemanticMemory()
results = mem.query('{}', top_k={})
print(json.dumps(results, indent=2))
"#,
                query.replace("'", "\\'"),
                limit
            ),
        ])
        .output()
        .map_err(|e| format!("Failed to query memory: {}", e))?;

    if output.status.success() {
        Ok(String::from_utf8_lossy(&output.stdout).to_string())
    } else {
        Err(String::from_utf8_lossy(&output.stderr).to_string())
    }
}
