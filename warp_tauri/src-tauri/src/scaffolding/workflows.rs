// Workflows - Saved Parameterized Command Sequences (Warp-style)
//
// Save, edit, and replay command workflows with variable substitution.
// Zero AI overhead - pure deterministic execution.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

// =============================================================================
// WORKFLOW TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Workflow {
    pub id: String,
    pub name: String,
    pub description: Option<String>,
    pub steps: Vec<WorkflowStep>,
    pub parameters: Vec<WorkflowParam>,
    pub tags: Vec<String>,
    pub created_at: i64,
    pub last_used: Option<i64>,
    pub use_count: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowStep {
    pub command: String,           // Command with {{param}} placeholders
    pub description: Option<String>,
    pub continue_on_error: bool,   // Whether to continue if this step fails
    pub timeout_ms: Option<u64>,   // Optional timeout
    pub working_dir: Option<String>, // Optional directory override
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowParam {
    pub name: String,
    pub description: Option<String>,
    pub default: Option<String>,
    pub required: bool,
    pub param_type: ParamType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum ParamType {
    String,
    Path,
    Number,
    Boolean,
    Choice(Vec<String>),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WorkflowRun {
    pub workflow_id: String,
    pub parameters: HashMap<String, String>,
    pub steps: Vec<StepResult>,
    pub started_at: i64,
    pub finished_at: Option<i64>,
    pub success: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StepResult {
    pub step_index: usize,
    pub command: String,        // Resolved command (params substituted)
    pub output: String,
    pub exit_code: i32,
    pub duration_ms: u64,
    pub success: bool,
}

// =============================================================================
// WORKFLOW STORE
// =============================================================================

pub struct WorkflowStore {
    workflows: HashMap<String, Workflow>,
    history: Vec<WorkflowRun>,
    storage_path: PathBuf,
}

impl WorkflowStore {
    pub fn new() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let storage_path = PathBuf::from(format!("{}/.sam/workflows.json", home));

        let mut store = Self {
            workflows: HashMap::new(),
            history: Vec::new(),
            storage_path,
        };
        store.load();
        store
    }

    fn load(&mut self) {
        if let Ok(data) = fs::read_to_string(&self.storage_path) {
            if let Ok(stored) = serde_json::from_str::<StoredWorkflows>(&data) {
                self.workflows = stored.workflows;
                self.history = stored.history;
            }
        }
    }

    pub fn save(&self) {
        let stored = StoredWorkflows {
            workflows: self.workflows.clone(),
            history: self.history.clone(),
        };

        if let Some(parent) = self.storage_path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Ok(data) = serde_json::to_string_pretty(&stored) {
            let _ = fs::write(&self.storage_path, data);
        }
    }

    // Create a new workflow
    pub fn create(&mut self, name: &str, description: Option<&str>) -> Workflow {
        let id = format!("wf_{}", chrono::Utc::now().timestamp_millis());
        let workflow = Workflow {
            id: id.clone(),
            name: name.to_string(),
            description: description.map(|s| s.to_string()),
            steps: Vec::new(),
            parameters: Vec::new(),
            tags: Vec::new(),
            created_at: chrono::Utc::now().timestamp(),
            last_used: None,
            use_count: 0,
        };
        self.workflows.insert(id, workflow.clone());
        self.save();
        workflow
    }

    // Add a step to workflow
    pub fn add_step(&mut self, workflow_id: &str, command: &str, description: Option<&str>) -> Result<(), String> {
        let workflow = self.workflows.get_mut(workflow_id)
            .ok_or_else(|| "Workflow not found".to_string())?;

        workflow.steps.push(WorkflowStep {
            command: command.to_string(),
            description: description.map(|s| s.to_string()),
            continue_on_error: false,
            timeout_ms: None,
            working_dir: None,
        });

        // Auto-detect parameters from {{param}} syntax
        let re = regex::Regex::new(r"\{\{(\w+)\}\}").unwrap();
        for cap in re.captures_iter(command) {
            let param_name = &cap[1];
            if !workflow.parameters.iter().any(|p| p.name == param_name) {
                workflow.parameters.push(WorkflowParam {
                    name: param_name.to_string(),
                    description: None,
                    default: None,
                    required: true,
                    param_type: ParamType::String,
                });
            }
        }

        self.save();
        Ok(())
    }

    // Add a parameter definition
    pub fn add_param(&mut self, workflow_id: &str, param: WorkflowParam) -> Result<(), String> {
        let workflow = self.workflows.get_mut(workflow_id)
            .ok_or_else(|| "Workflow not found".to_string())?;

        // Update existing or add new
        if let Some(existing) = workflow.parameters.iter_mut().find(|p| p.name == param.name) {
            *existing = param;
        } else {
            workflow.parameters.push(param);
        }

        self.save();
        Ok(())
    }

    // Get workflow by ID
    pub fn get(&self, id: &str) -> Option<&Workflow> {
        self.workflows.get(id)
    }

    // List all workflows
    pub fn list(&self) -> Vec<&Workflow> {
        let mut workflows: Vec<_> = self.workflows.values().collect();
        workflows.sort_by(|a, b| b.use_count.cmp(&a.use_count)); // Most used first
        workflows
    }

    // Search workflows by name or tag
    pub fn search(&self, query: &str) -> Vec<&Workflow> {
        let query_lower = query.to_lowercase();
        self.workflows.values()
            .filter(|w| {
                w.name.to_lowercase().contains(&query_lower) ||
                w.tags.iter().any(|t| t.to_lowercase().contains(&query_lower)) ||
                w.description.as_ref().map(|d| d.to_lowercase().contains(&query_lower)).unwrap_or(false)
            })
            .collect()
    }

    // Delete workflow
    pub fn delete(&mut self, id: &str) -> bool {
        let removed = self.workflows.remove(id).is_some();
        if removed {
            self.save();
        }
        removed
    }

    // Resolve parameters in a command
    pub fn resolve_command(command: &str, params: &HashMap<String, String>) -> String {
        let mut resolved = command.to_string();
        for (key, value) in params {
            resolved = resolved.replace(&format!("{{{{{}}}}}", key), value);
        }
        resolved
    }

    // Validate parameters before running
    pub fn validate_params(&self, workflow_id: &str, params: &HashMap<String, String>) -> Result<(), Vec<String>> {
        let workflow = self.workflows.get(workflow_id)
            .ok_or_else(|| vec!["Workflow not found".to_string()])?;

        let mut errors = Vec::new();

        for param in &workflow.parameters {
            if param.required && !params.contains_key(&param.name) && param.default.is_none() {
                errors.push(format!("Missing required parameter: {}", param.name));
            }
        }

        if errors.is_empty() {
            Ok(())
        } else {
            Err(errors)
        }
    }

    // Get resolved steps (with parameters substituted)
    pub fn get_resolved_steps(&self, workflow_id: &str, params: &HashMap<String, String>) -> Result<Vec<String>, String> {
        let workflow = self.workflows.get(workflow_id)
            .ok_or_else(|| "Workflow not found".to_string())?;

        // Merge defaults with provided params
        let mut merged_params = HashMap::new();
        for param in &workflow.parameters {
            if let Some(default) = &param.default {
                merged_params.insert(param.name.clone(), default.clone());
            }
        }
        merged_params.extend(params.clone());

        Ok(workflow.steps.iter()
            .map(|step| Self::resolve_command(&step.command, &merged_params))
            .collect())
    }

    // Record a workflow run
    pub fn record_run(&mut self, run: WorkflowRun) {
        // Update workflow stats
        if let Some(workflow) = self.workflows.get_mut(&run.workflow_id) {
            workflow.last_used = Some(chrono::Utc::now().timestamp());
            workflow.use_count += 1;
        }

        // Keep last 100 runs
        self.history.push(run);
        if self.history.len() > 100 {
            self.history.remove(0);
        }

        self.save();
    }

    // Get run history for a workflow
    pub fn get_history(&self, workflow_id: &str) -> Vec<&WorkflowRun> {
        self.history.iter()
            .filter(|r| r.workflow_id == workflow_id)
            .collect()
    }
}

#[derive(Serialize, Deserialize)]
struct StoredWorkflows {
    workflows: HashMap<String, Workflow>,
    history: Vec<WorkflowRun>,
}

// =============================================================================
// BUILT-IN WORKFLOWS
// =============================================================================

pub fn get_builtin_workflows() -> Vec<Workflow> {
    vec![
        // Git: Feature branch workflow
        Workflow {
            id: "builtin_git_feature".to_string(),
            name: "Git Feature Branch".to_string(),
            description: Some("Create feature branch, make changes, commit and push".to_string()),
            steps: vec![
                WorkflowStep {
                    command: "git checkout -b {{branch_name}}".to_string(),
                    description: Some("Create and switch to feature branch".to_string()),
                    continue_on_error: false,
                    timeout_ms: None,
                    working_dir: None,
                },
                WorkflowStep {
                    command: "git add -A".to_string(),
                    description: Some("Stage all changes".to_string()),
                    continue_on_error: false,
                    timeout_ms: None,
                    working_dir: None,
                },
                WorkflowStep {
                    command: "git commit -m \"{{commit_message}}\"".to_string(),
                    description: Some("Commit with message".to_string()),
                    continue_on_error: false,
                    timeout_ms: None,
                    working_dir: None,
                },
                WorkflowStep {
                    command: "git push -u origin {{branch_name}}".to_string(),
                    description: Some("Push to remote".to_string()),
                    continue_on_error: false,
                    timeout_ms: None,
                    working_dir: None,
                },
            ],
            parameters: vec![
                WorkflowParam {
                    name: "branch_name".to_string(),
                    description: Some("Name of the feature branch".to_string()),
                    default: None,
                    required: true,
                    param_type: ParamType::String,
                },
                WorkflowParam {
                    name: "commit_message".to_string(),
                    description: Some("Commit message".to_string()),
                    default: None,
                    required: true,
                    param_type: ParamType::String,
                },
            ],
            tags: vec!["git".to_string(), "feature".to_string()],
            created_at: 0,
            last_used: None,
            use_count: 0,
        },

        // Rust: Build and test
        Workflow {
            id: "builtin_rust_test".to_string(),
            name: "Rust Build & Test".to_string(),
            description: Some("Build, run tests, and check formatting".to_string()),
            steps: vec![
                WorkflowStep {
                    command: "cargo fmt --check".to_string(),
                    description: Some("Check formatting".to_string()),
                    continue_on_error: true,
                    timeout_ms: Some(30000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "cargo clippy -- -D warnings".to_string(),
                    description: Some("Run clippy lints".to_string()),
                    continue_on_error: true,
                    timeout_ms: Some(120000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "cargo build --release".to_string(),
                    description: Some("Build release".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(300000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "cargo test".to_string(),
                    description: Some("Run tests".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(120000),
                    working_dir: None,
                },
            ],
            parameters: vec![],
            tags: vec!["rust".to_string(), "build".to_string(), "test".to_string()],
            created_at: 0,
            last_used: None,
            use_count: 0,
        },

        // Node: Install, build, test
        Workflow {
            id: "builtin_node_ci".to_string(),
            name: "Node CI".to_string(),
            description: Some("Install dependencies, build, and test".to_string()),
            steps: vec![
                WorkflowStep {
                    command: "{{package_manager}} install".to_string(),
                    description: Some("Install dependencies".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(120000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "{{package_manager}} run build".to_string(),
                    description: Some("Build project".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(180000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "{{package_manager}} test".to_string(),
                    description: Some("Run tests".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(120000),
                    working_dir: None,
                },
            ],
            parameters: vec![
                WorkflowParam {
                    name: "package_manager".to_string(),
                    description: Some("npm, yarn, pnpm, or bun".to_string()),
                    default: Some("npm".to_string()),
                    required: false,
                    param_type: ParamType::Choice(vec![
                        "npm".to_string(),
                        "yarn".to_string(),
                        "pnpm".to_string(),
                        "bun".to_string(),
                    ]),
                },
            ],
            tags: vec!["node".to_string(), "javascript".to_string(), "ci".to_string()],
            created_at: 0,
            last_used: None,
            use_count: 0,
        },

        // Docker: Build and push
        Workflow {
            id: "builtin_docker_push".to_string(),
            name: "Docker Build & Push".to_string(),
            description: Some("Build Docker image and push to registry".to_string()),
            steps: vec![
                WorkflowStep {
                    command: "docker build -t {{image_name}}:{{tag}} .".to_string(),
                    description: Some("Build image".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(600000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "docker push {{image_name}}:{{tag}}".to_string(),
                    description: Some("Push to registry".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(300000),
                    working_dir: None,
                },
            ],
            parameters: vec![
                WorkflowParam {
                    name: "image_name".to_string(),
                    description: Some("Full image name including registry".to_string()),
                    default: None,
                    required: true,
                    param_type: ParamType::String,
                },
                WorkflowParam {
                    name: "tag".to_string(),
                    description: Some("Image tag".to_string()),
                    default: Some("latest".to_string()),
                    required: false,
                    param_type: ParamType::String,
                },
            ],
            tags: vec!["docker".to_string(), "deploy".to_string()],
            created_at: 0,
            last_used: None,
            use_count: 0,
        },

        // Deploy: SSH and restart
        Workflow {
            id: "builtin_ssh_deploy".to_string(),
            name: "SSH Deploy".to_string(),
            description: Some("Deploy via SSH: pull, build, restart".to_string()),
            steps: vec![
                WorkflowStep {
                    command: "ssh {{host}} 'cd {{deploy_path}} && git pull'".to_string(),
                    description: Some("Pull latest code".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(60000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "ssh {{host}} 'cd {{deploy_path}} && {{build_command}}'".to_string(),
                    description: Some("Build on server".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(300000),
                    working_dir: None,
                },
                WorkflowStep {
                    command: "ssh {{host}} 'sudo systemctl restart {{service_name}}'".to_string(),
                    description: Some("Restart service".to_string()),
                    continue_on_error: false,
                    timeout_ms: Some(30000),
                    working_dir: None,
                },
            ],
            parameters: vec![
                WorkflowParam {
                    name: "host".to_string(),
                    description: Some("SSH host (user@hostname)".to_string()),
                    default: None,
                    required: true,
                    param_type: ParamType::String,
                },
                WorkflowParam {
                    name: "deploy_path".to_string(),
                    description: Some("Path to project on server".to_string()),
                    default: None,
                    required: true,
                    param_type: ParamType::Path,
                },
                WorkflowParam {
                    name: "build_command".to_string(),
                    description: Some("Build command to run".to_string()),
                    default: Some("npm run build".to_string()),
                    required: false,
                    param_type: ParamType::String,
                },
                WorkflowParam {
                    name: "service_name".to_string(),
                    description: Some("Systemd service name".to_string()),
                    default: None,
                    required: true,
                    param_type: ParamType::String,
                },
            ],
            tags: vec!["ssh".to_string(), "deploy".to_string()],
            created_at: 0,
            last_used: None,
            use_count: 0,
        },
    ]
}

// Global store
lazy_static::lazy_static! {
    pub static ref WORKFLOW_STORE: std::sync::Mutex<WorkflowStore> =
        std::sync::Mutex::new(WorkflowStore::new());
}

pub fn workflows() -> std::sync::MutexGuard<'static, WorkflowStore> {
    WORKFLOW_STORE.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_resolve_command() {
        let mut params = HashMap::new();
        params.insert("name".to_string(), "feature-x".to_string());
        params.insert("msg".to_string(), "Add feature".to_string());

        let cmd = "git checkout -b {{name}} && git commit -m \"{{msg}}\"";
        let resolved = WorkflowStore::resolve_command(cmd, &params);

        assert_eq!(resolved, "git checkout -b feature-x && git commit -m \"Add feature\"");
    }

    #[test]
    fn test_workflow_creation() {
        let mut store = WorkflowStore::new();
        let wf = store.create("Test Workflow", Some("A test"));

        assert!(!wf.id.is_empty());
        assert_eq!(wf.name, "Test Workflow");
    }
}
