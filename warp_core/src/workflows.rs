//! Workflow Engine for warp_core
//!
//! Implements Warp-compatible YAML workflows with parameterized commands,
//! argument substitution, and execution tracking.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;
use regex::Regex;

/// A workflow definition (compatible with Warp YAML format)
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Workflow {
    /// Unique name for the workflow
    pub name: String,
    /// Human-readable description
    pub description: Option<String>,
    /// The command template with {{argument}} placeholders
    pub command: String,
    /// Argument definitions
    #[serde(default)]
    pub arguments: Vec<WorkflowArg>,
    /// Tags for categorization
    #[serde(default)]
    pub tags: Vec<String>,
    /// Source file path (for YAML workflows)
    #[serde(skip)]
    pub source_path: Option<String>,
}

/// Argument definition for a workflow
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WorkflowArg {
    /// Argument name (used in {{name}} placeholders)
    pub name: String,
    /// Human-readable description
    pub description: Option<String>,
    /// Default value if not provided
    pub default: Option<String>,
    /// For enum arguments: list of allowed values
    #[serde(default)]
    pub options: Vec<String>,
    /// Whether this argument is required
    #[serde(default = "default_true")]
    pub required: bool,
}

fn default_true() -> bool {
    true
}

/// Result of workflow execution
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WorkflowExecution {
    pub workflow_name: String,
    pub expanded_command: String,
    pub arguments_used: HashMap<String, String>,
    pub success: bool,
    pub output: Option<String>,
    pub error: Option<String>,
    pub exit_code: Option<i32>,
    pub timestamp: String,
}

/// Workflow engine for managing and executing workflows
pub struct WorkflowEngine {
    workflows: HashMap<String, Workflow>,
    history: Vec<WorkflowExecution>,
}

impl WorkflowEngine {
    /// Create a new workflow engine
    pub fn new() -> Self {
        Self {
            workflows: HashMap::new(),
            history: vec![],
        }
    }

    /// Load workflows from a YAML file
    pub fn load_from_yaml<P: AsRef<Path>>(&mut self, path: P) -> Result<usize, Box<dyn std::error::Error>> {
        let content = fs::read_to_string(path.as_ref())?;
        let workflows: Vec<Workflow> = serde_yaml::from_str(&content)?;
        let count = workflows.len();

        for mut workflow in workflows {
            workflow.source_path = Some(path.as_ref().to_string_lossy().to_string());
            self.workflows.insert(workflow.name.clone(), workflow);
        }

        Ok(count)
    }

    /// Load workflows from a directory of YAML files
    pub fn load_from_directory<P: AsRef<Path>>(&mut self, dir: P) -> Result<usize, Box<dyn std::error::Error>> {
        let mut total = 0;

        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.extension().map(|e| e == "yaml" || e == "yml").unwrap_or(false) {
                match self.load_from_yaml(&path) {
                    Ok(count) => total += count,
                    Err(e) => eprintln!("Warning: Failed to load {:?}: {}", path, e),
                }
            }
        }

        Ok(total)
    }

    /// Register a workflow programmatically
    pub fn register(&mut self, workflow: Workflow) {
        self.workflows.insert(workflow.name.clone(), workflow);
    }

    /// Get a workflow by name
    pub fn get(&self, name: &str) -> Option<&Workflow> {
        self.workflows.get(name)
    }

    /// List all workflow names
    pub fn list(&self) -> Vec<&str> {
        self.workflows.keys().map(|s| s.as_str()).collect()
    }

    /// Search workflows by name or description
    pub fn search(&self, query: &str) -> Vec<&Workflow> {
        let query_lower = query.to_lowercase();
        self.workflows
            .values()
            .filter(|w| {
                w.name.to_lowercase().contains(&query_lower)
                    || w.description
                        .as_ref()
                        .map(|d| d.to_lowercase().contains(&query_lower))
                        .unwrap_or(false)
                    || w.tags.iter().any(|t| t.to_lowercase().contains(&query_lower))
            })
            .collect()
    }

    /// Expand a workflow command with provided arguments
    pub fn expand(&self, name: &str, args: &HashMap<String, String>) -> Result<String, WorkflowError> {
        let workflow = self.workflows.get(name)
            .ok_or_else(|| WorkflowError::NotFound(name.to_string()))?;

        self.expand_command(&workflow.command, &workflow.arguments, args)
    }

    /// Expand a command template with arguments
    fn expand_command(
        &self,
        template: &str,
        arg_defs: &[WorkflowArg],
        provided_args: &HashMap<String, String>,
    ) -> Result<String, WorkflowError> {
        let mut result = template.to_string();
        let placeholder_re = Regex::new(r"\{\{(\w+)\}\}").unwrap();

        // Check for required arguments
        for arg_def in arg_defs {
            if arg_def.required && !provided_args.contains_key(&arg_def.name) && arg_def.default.is_none() {
                return Err(WorkflowError::MissingArgument(arg_def.name.clone()));
            }
        }

        // Replace placeholders
        for caps in placeholder_re.captures_iter(template) {
            let full_match = caps.get(0).unwrap().as_str();
            let arg_name = caps.get(1).unwrap().as_str();

            let value = provided_args
                .get(arg_name)
                .or_else(|| {
                    arg_defs
                        .iter()
                        .find(|a| a.name == arg_name)
                        .and_then(|a| a.default.as_ref())
                })
                .ok_or_else(|| WorkflowError::MissingArgument(arg_name.to_string()))?;

            // Validate enum values
            if let Some(arg_def) = arg_defs.iter().find(|a| a.name == arg_name) {
                if !arg_def.options.is_empty() && !arg_def.options.contains(value) {
                    return Err(WorkflowError::InvalidArgument {
                        name: arg_name.to_string(),
                        value: value.clone(),
                        allowed: arg_def.options.clone(),
                    });
                }
            }

            result = result.replace(full_match, value);
        }

        Ok(result)
    }

    /// Get required arguments for a workflow (those without defaults)
    pub fn get_required_args(&self, name: &str) -> Result<Vec<&WorkflowArg>, WorkflowError> {
        let workflow = self.workflows.get(name)
            .ok_or_else(|| WorkflowError::NotFound(name.to_string()))?;

        Ok(workflow
            .arguments
            .iter()
            .filter(|a| a.required && a.default.is_none())
            .collect())
    }

    /// Record a workflow execution in history
    pub fn record_execution(&mut self, execution: WorkflowExecution) {
        self.history.push(execution);
    }

    /// Get execution history
    pub fn get_history(&self, limit: Option<usize>) -> &[WorkflowExecution] {
        match limit {
            Some(n) => {
                let start = self.history.len().saturating_sub(n);
                &self.history[start..]
            }
            None => &self.history,
        }
    }

    /// Export workflows to YAML
    pub fn export_to_yaml(&self) -> Result<String, serde_yaml::Error> {
        let workflows: Vec<&Workflow> = self.workflows.values().collect();
        serde_yaml::to_string(&workflows)
    }
}

impl Default for WorkflowEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Workflow-related errors
#[derive(Debug)]
pub enum WorkflowError {
    NotFound(String),
    MissingArgument(String),
    InvalidArgument {
        name: String,
        value: String,
        allowed: Vec<String>,
    },
    ParseError(String),
}

impl std::fmt::Display for WorkflowError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            WorkflowError::NotFound(name) => write!(f, "Workflow not found: {}", name),
            WorkflowError::MissingArgument(name) => write!(f, "Missing required argument: {}", name),
            WorkflowError::InvalidArgument { name, value, allowed } => {
                write!(f, "Invalid value '{}' for argument '{}'. Allowed: {:?}", value, name, allowed)
            }
            WorkflowError::ParseError(msg) => write!(f, "Parse error: {}", msg),
        }
    }
}

impl std::error::Error for WorkflowError {}

/// Create some built-in useful workflows
pub fn default_workflows() -> Vec<Workflow> {
    vec![
        Workflow {
            name: "git-commit".into(),
            description: Some("Create a git commit with message".into()),
            command: "git commit -m \"{{message}}\"".into(),
            arguments: vec![WorkflowArg {
                name: "message".into(),
                description: Some("Commit message".into()),
                default: None,
                options: vec![],
                required: true,
            }],
            tags: vec!["git".into(), "vcs".into()],
            source_path: None,
        },
        Workflow {
            name: "git-checkout".into(),
            description: Some("Switch to a branch".into()),
            command: "git checkout {{branch}}".into(),
            arguments: vec![WorkflowArg {
                name: "branch".into(),
                description: Some("Branch name".into()),
                default: None,
                options: vec![],
                required: true,
            }],
            tags: vec!["git".into(), "vcs".into()],
            source_path: None,
        },
        Workflow {
            name: "docker-run".into(),
            description: Some("Run a Docker container".into()),
            command: "docker run {{flags}} {{image}} {{command}}".into(),
            arguments: vec![
                WorkflowArg {
                    name: "image".into(),
                    description: Some("Docker image name".into()),
                    default: None,
                    options: vec![],
                    required: true,
                },
                WorkflowArg {
                    name: "flags".into(),
                    description: Some("Docker run flags".into()),
                    default: Some("-it --rm".into()),
                    options: vec![],
                    required: false,
                },
                WorkflowArg {
                    name: "command".into(),
                    description: Some("Command to run in container".into()),
                    default: Some("/bin/bash".into()),
                    options: vec![],
                    required: false,
                },
            ],
            tags: vec!["docker".into(), "containers".into()],
            source_path: None,
        },
        Workflow {
            name: "npm-install".into(),
            description: Some("Install npm packages".into()),
            command: "npm install {{packages}} {{flags}}".into(),
            arguments: vec![
                WorkflowArg {
                    name: "packages".into(),
                    description: Some("Package names (space-separated)".into()),
                    default: Some("".into()),
                    options: vec![],
                    required: false,
                },
                WorkflowArg {
                    name: "flags".into(),
                    description: Some("Install flags".into()),
                    default: Some("".into()),
                    options: vec!["".into(), "--save-dev".into(), "--global".into()],
                    required: false,
                },
            ],
            tags: vec!["npm".into(), "node".into(), "javascript".into()],
            source_path: None,
        },
        Workflow {
            name: "find-files".into(),
            description: Some("Find files by pattern".into()),
            command: "find {{path}} -name \"{{pattern}}\" {{extra}}".into(),
            arguments: vec![
                WorkflowArg {
                    name: "path".into(),
                    description: Some("Starting directory".into()),
                    default: Some(".".into()),
                    options: vec![],
                    required: false,
                },
                WorkflowArg {
                    name: "pattern".into(),
                    description: Some("File name pattern".into()),
                    default: None,
                    options: vec![],
                    required: true,
                },
                WorkflowArg {
                    name: "extra".into(),
                    description: Some("Additional find options".into()),
                    default: Some("".into()),
                    options: vec![],
                    required: false,
                },
            ],
            tags: vec!["find".into(), "search".into(), "files".into()],
            source_path: None,
        },
        Workflow {
            name: "grep-search".into(),
            description: Some("Search for text in files".into()),
            command: "grep -r {{flags}} \"{{pattern}}\" {{path}}".into(),
            arguments: vec![
                WorkflowArg {
                    name: "pattern".into(),
                    description: Some("Search pattern".into()),
                    default: None,
                    options: vec![],
                    required: true,
                },
                WorkflowArg {
                    name: "path".into(),
                    description: Some("Search path".into()),
                    default: Some(".".into()),
                    options: vec![],
                    required: false,
                },
                WorkflowArg {
                    name: "flags".into(),
                    description: Some("Grep flags".into()),
                    default: Some("-n".into()),
                    options: vec!["-n".into(), "-i".into(), "-l".into(), "-c".into()],
                    required: false,
                },
            ],
            tags: vec!["grep".into(), "search".into(), "text".into()],
            source_path: None,
        },
        Workflow {
            name: "ssh-connect".into(),
            description: Some("SSH to a server".into()),
            command: "ssh {{user}}@{{host}} {{port_flag}}".into(),
            arguments: vec![
                WorkflowArg {
                    name: "user".into(),
                    description: Some("SSH username".into()),
                    default: None,
                    options: vec![],
                    required: true,
                },
                WorkflowArg {
                    name: "host".into(),
                    description: Some("Server hostname or IP".into()),
                    default: None,
                    options: vec![],
                    required: true,
                },
                WorkflowArg {
                    name: "port_flag".into(),
                    description: Some("Port flag (e.g., -p 2222)".into()),
                    default: Some("".into()),
                    options: vec![],
                    required: false,
                },
            ],
            tags: vec!["ssh".into(), "remote".into(), "server".into()],
            source_path: None,
        },
        Workflow {
            name: "tar-extract".into(),
            description: Some("Extract a tar archive".into()),
            command: "tar {{flags}} {{archive}} {{dest}}".into(),
            arguments: vec![
                WorkflowArg {
                    name: "archive".into(),
                    description: Some("Archive file path".into()),
                    default: None,
                    options: vec![],
                    required: true,
                },
                WorkflowArg {
                    name: "flags".into(),
                    description: Some("Tar flags".into()),
                    default: Some("-xzvf".into()),
                    options: vec!["-xzvf".into(), "-xjvf".into(), "-xvf".into()],
                    required: false,
                },
                WorkflowArg {
                    name: "dest".into(),
                    description: Some("Destination directory".into()),
                    default: Some("".into()),
                    options: vec![],
                    required: false,
                },
            ],
            tags: vec!["tar".into(), "archive".into(), "extract".into()],
            source_path: None,
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_workflow_expansion() {
        let mut engine = WorkflowEngine::new();
        engine.register(Workflow {
            name: "test".into(),
            description: None,
            command: "echo {{message}}".into(),
            arguments: vec![WorkflowArg {
                name: "message".into(),
                description: None,
                default: None,
                options: vec![],
                required: true,
            }],
            tags: vec![],
            source_path: None,
        });

        let mut args = HashMap::new();
        args.insert("message".to_string(), "hello world".to_string());

        let result = engine.expand("test", &args).unwrap();
        assert_eq!(result, "echo hello world");
    }

    #[test]
    fn test_workflow_default_value() {
        let mut engine = WorkflowEngine::new();
        engine.register(Workflow {
            name: "test".into(),
            description: None,
            command: "echo {{message}}".into(),
            arguments: vec![WorkflowArg {
                name: "message".into(),
                description: None,
                default: Some("default".into()),
                options: vec![],
                required: false,
            }],
            tags: vec![],
            source_path: None,
        });

        let args = HashMap::new();
        let result = engine.expand("test", &args).unwrap();
        assert_eq!(result, "echo default");
    }

    #[test]
    fn test_workflow_missing_required() {
        let mut engine = WorkflowEngine::new();
        engine.register(Workflow {
            name: "test".into(),
            description: None,
            command: "echo {{message}}".into(),
            arguments: vec![WorkflowArg {
                name: "message".into(),
                description: None,
                default: None,
                options: vec![],
                required: true,
            }],
            tags: vec![],
            source_path: None,
        });

        let args = HashMap::new();
        let result = engine.expand("test", &args);
        assert!(result.is_err());
    }

    #[test]
    fn test_workflow_search() {
        let mut engine = WorkflowEngine::new();
        for workflow in default_workflows() {
            engine.register(workflow);
        }

        let results = engine.search("git");
        assert!(!results.is_empty());
        assert!(results.iter().any(|w| w.name == "git-commit"));
    }

    #[test]
    fn test_workflow_enum_validation() {
        let mut engine = WorkflowEngine::new();
        engine.register(Workflow {
            name: "test".into(),
            description: None,
            command: "npm install {{flags}}".into(),
            arguments: vec![WorkflowArg {
                name: "flags".into(),
                description: None,
                default: None,
                options: vec!["--save".into(), "--save-dev".into()],
                required: true,
            }],
            tags: vec![],
            source_path: None,
        });

        let mut args = HashMap::new();
        args.insert("flags".to_string(), "--invalid".to_string());

        let result = engine.expand("test", &args);
        assert!(result.is_err());
    }
}
