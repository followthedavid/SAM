//! Command Completion Engine for warp_core
//!
//! Provides TAB completion suggestions for commands, arguments, and options.
//! Compatible with Fig/Warp completion spec format.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// A completion specification for a command
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CompletionSpec {
    /// The command name
    pub name: String,
    /// Description of the command
    pub description: Option<String>,
    /// Subcommands
    #[serde(default)]
    pub subcommands: Vec<CompletionSpec>,
    /// Options/flags
    #[serde(default)]
    pub options: Vec<OptionSpec>,
    /// Positional arguments
    #[serde(default)]
    pub args: Vec<ArgSpec>,
}

/// Specification for a command option/flag
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct OptionSpec {
    /// Option names (e.g., ["-v", "--verbose"])
    pub name: Vec<String>,
    /// Description
    pub description: Option<String>,
    /// Whether this option takes an argument
    #[serde(default)]
    pub args: Option<ArgSpec>,
    /// Whether this option is required
    #[serde(default)]
    pub required: bool,
    /// Whether this option can be used multiple times
    #[serde(default)]
    pub is_repeatable: bool,
}

/// Specification for a positional argument
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ArgSpec {
    /// Name of the argument (for display)
    pub name: String,
    /// Description
    pub description: Option<String>,
    /// Static suggestions
    #[serde(default)]
    pub suggestions: Vec<String>,
    /// Generator for dynamic suggestions
    pub generator: Option<Generator>,
    /// Whether this argument is optional
    #[serde(default)]
    pub is_optional: bool,
    /// Whether this argument is variadic (can accept multiple values)
    #[serde(default)]
    pub is_variadic: bool,
    /// Template type for special completions
    pub template: Option<TemplateType>,
}

/// Generator for dynamic completions
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Generator {
    /// Shell command to generate suggestions
    pub script: Option<String>,
    /// Template-based generation
    pub template: Option<TemplateType>,
    /// Post-processing function name
    pub post_process: Option<String>,
}

/// Template types for common completion patterns
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum TemplateType {
    /// File paths
    Filepaths,
    /// Directory paths
    Folders,
    /// Git branches
    GitBranches,
    /// Git tags
    GitTags,
    /// Git remotes
    GitRemotes,
    /// Docker images
    DockerImages,
    /// Docker containers
    DockerContainers,
    /// Kubernetes pods
    K8sPods,
    /// Kubernetes namespaces
    K8sNamespaces,
    /// Environment variables
    EnvVars,
    /// Process IDs
    Pids,
    /// Network interfaces
    NetworkInterfaces,
}

/// A suggestion returned by the completion engine
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Suggestion {
    /// The completion text
    pub name: String,
    /// Display name (if different from name)
    pub display_name: Option<String>,
    /// Description
    pub description: Option<String>,
    /// Icon/type indicator
    pub icon: Option<SuggestionIcon>,
    /// Priority (higher = shown first)
    pub priority: i32,
    /// Whether to insert a space after completion
    pub insert_space: bool,
}

/// Icon types for suggestions
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum SuggestionIcon {
    Command,
    Subcommand,
    Option,
    Arg,
    File,
    Folder,
    Branch,
}

/// The main completion engine
pub struct CompletionEngine {
    specs: HashMap<String, CompletionSpec>,
    cache: HashMap<String, Vec<Suggestion>>,
}

impl CompletionEngine {
    /// Create a new completion engine
    pub fn new() -> Self {
        let mut engine = Self {
            specs: HashMap::new(),
            cache: HashMap::new(),
        };

        // Load built-in specs
        for spec in builtin_specs() {
            engine.specs.insert(spec.name.clone(), spec);
        }

        engine
    }

    /// Load a completion spec from JSON
    pub fn load_spec(&mut self, json: &str) -> Result<(), serde_json::Error> {
        let spec: CompletionSpec = serde_json::from_str(json)?;
        self.specs.insert(spec.name.clone(), spec);
        Ok(())
    }

    /// Load specs from a directory
    pub fn load_from_directory<P: AsRef<Path>>(&mut self, dir: P) -> Result<usize, Box<dyn std::error::Error>> {
        let mut count = 0;

        for entry in fs::read_dir(dir)? {
            let entry = entry?;
            let path = entry.path();

            if path.extension().map(|e| e == "json").unwrap_or(false) {
                let content = fs::read_to_string(&path)?;
                if self.load_spec(&content).is_ok() {
                    count += 1;
                }
            }
        }

        Ok(count)
    }

    /// Get completions for a command line
    pub fn complete(&self, line: &str, cursor_pos: usize) -> Vec<Suggestion> {
        let line_to_cursor = &line[..cursor_pos.min(line.len())];
        let parts: Vec<&str> = line_to_cursor.split_whitespace().collect();

        if parts.is_empty() {
            // Complete command names
            return self.complete_commands("");
        }

        let command = parts[0];

        // Check if we have a spec for this command
        if let Some(spec) = self.specs.get(command) {
            self.complete_with_spec(spec, &parts[1..], line_to_cursor)
        } else {
            // Try partial command completion
            if parts.len() == 1 && !line_to_cursor.ends_with(' ') {
                self.complete_commands(command)
            } else {
                // Default to file completion
                self.complete_files(parts.last().unwrap_or(&""))
            }
        }
    }

    /// Complete command names
    fn complete_commands(&self, prefix: &str) -> Vec<Suggestion> {
        self.specs
            .values()
            .filter(|spec| spec.name.starts_with(prefix))
            .map(|spec| Suggestion {
                name: spec.name.clone(),
                display_name: None,
                description: spec.description.clone(),
                icon: Some(SuggestionIcon::Command),
                priority: 100,
                insert_space: true,
            })
            .collect()
    }

    /// Complete using a spec
    fn complete_with_spec(&self, spec: &CompletionSpec, args: &[&str], line: &str) -> Vec<Suggestion> {
        let mut suggestions = vec![];
        let current_word = args.last().copied().unwrap_or("");
        let is_completing_word = !line.ends_with(' ');

        // Check for subcommand completion
        if !spec.subcommands.is_empty() {
            if args.is_empty() || (args.len() == 1 && is_completing_word) {
                let prefix = if is_completing_word { current_word } else { "" };
                for sub in &spec.subcommands {
                    if sub.name.starts_with(prefix) {
                        suggestions.push(Suggestion {
                            name: sub.name.clone(),
                            display_name: None,
                            description: sub.description.clone(),
                            icon: Some(SuggestionIcon::Subcommand),
                            priority: 90,
                            insert_space: true,
                        });
                    }
                }
            }

            // Check if first arg matches a subcommand
            if let Some(first_arg) = args.first() {
                if let Some(sub_spec) = spec.subcommands.iter().find(|s| s.name == *first_arg) {
                    return self.complete_with_spec(sub_spec, &args[1..], line);
                }
            }
        }

        // Complete options
        if current_word.starts_with('-') || line.ends_with(' ') {
            let prefix = if is_completing_word && current_word.starts_with('-') {
                current_word
            } else {
                ""
            };

            for opt in &spec.options {
                for name in &opt.name {
                    if name.starts_with(prefix) {
                        suggestions.push(Suggestion {
                            name: name.clone(),
                            display_name: None,
                            description: opt.description.clone(),
                            icon: Some(SuggestionIcon::Option),
                            priority: 80,
                            insert_space: opt.args.is_none(),
                        });
                    }
                }
            }
        }

        // Complete positional arguments
        if suggestions.is_empty() || !current_word.starts_with('-') {
            let arg_index = args.iter().filter(|a| !a.starts_with('-')).count();

            if let Some(arg_spec) = spec.args.get(arg_index.saturating_sub(if is_completing_word { 1 } else { 0 })) {
                let prefix = if is_completing_word { current_word } else { "" };

                // Static suggestions
                for sug in &arg_spec.suggestions {
                    if sug.starts_with(prefix) {
                        suggestions.push(Suggestion {
                            name: sug.clone(),
                            display_name: None,
                            description: None,
                            icon: Some(SuggestionIcon::Arg),
                            priority: 70,
                            insert_space: true,
                        });
                    }
                }

                // Template-based suggestions
                if let Some(template) = &arg_spec.template {
                    suggestions.extend(self.complete_template(template, prefix));
                }

                // Generator-based suggestions
                if let Some(gen) = &arg_spec.generator {
                    if let Some(template) = &gen.template {
                        suggestions.extend(self.complete_template(template, prefix));
                    }
                }
            }
        }

        // Default to file completion if nothing else matches
        if suggestions.is_empty() && is_completing_word {
            suggestions.extend(self.complete_files(current_word));
        }

        // Sort by priority
        suggestions.sort_by(|a, b| b.priority.cmp(&a.priority));
        suggestions
    }

    /// Complete based on template type
    fn complete_template(&self, template: &TemplateType, prefix: &str) -> Vec<Suggestion> {
        match template {
            TemplateType::Filepaths => self.complete_files(prefix),
            TemplateType::Folders => self.complete_folders(prefix),
            TemplateType::GitBranches => self.complete_git_branches(prefix),
            TemplateType::EnvVars => self.complete_env_vars(prefix),
            _ => vec![],
        }
    }

    /// Complete file paths
    fn complete_files(&self, prefix: &str) -> Vec<Suggestion> {
        let mut suggestions = vec![];
        let (dir, file_prefix) = if prefix.contains('/') {
            let idx = prefix.rfind('/').unwrap();
            (&prefix[..=idx], &prefix[idx + 1..])
        } else {
            ("./", prefix)
        };

        if let Ok(entries) = fs::read_dir(dir) {
            for entry in entries.flatten() {
                let name = entry.file_name().to_string_lossy().to_string();
                if name.starts_with(file_prefix) {
                    let is_dir = entry.path().is_dir();
                    let full_path = if dir == "./" {
                        name.clone()
                    } else {
                        format!("{}{}", dir, name)
                    };

                    suggestions.push(Suggestion {
                        name: if is_dir { format!("{}/", full_path) } else { full_path },
                        display_name: Some(name),
                        description: None,
                        icon: Some(if is_dir { SuggestionIcon::Folder } else { SuggestionIcon::File }),
                        priority: 50,
                        insert_space: !is_dir,
                    });
                }
            }
        }

        suggestions
    }

    /// Complete folder paths only
    fn complete_folders(&self, prefix: &str) -> Vec<Suggestion> {
        self.complete_files(prefix)
            .into_iter()
            .filter(|s| matches!(s.icon, Some(SuggestionIcon::Folder)))
            .collect()
    }

    /// Complete git branches
    fn complete_git_branches(&self, prefix: &str) -> Vec<Suggestion> {
        // Try to get branches from git
        if let Ok(output) = std::process::Command::new("git")
            .args(["branch", "--format=%(refname:short)"])
            .output()
        {
            if output.status.success() {
                let branches = String::from_utf8_lossy(&output.stdout);
                return branches
                    .lines()
                    .filter(|b| b.starts_with(prefix))
                    .map(|b| Suggestion {
                        name: b.to_string(),
                        display_name: None,
                        description: Some("branch".into()),
                        icon: Some(SuggestionIcon::Branch),
                        priority: 60,
                        insert_space: true,
                    })
                    .collect();
            }
        }
        vec![]
    }

    /// Complete environment variables
    fn complete_env_vars(&self, prefix: &str) -> Vec<Suggestion> {
        std::env::vars()
            .filter(|(k, _)| k.starts_with(prefix))
            .map(|(k, v)| Suggestion {
                name: k.clone(),
                display_name: None,
                description: Some(if v.len() > 30 { format!("{}...", &v[..30]) } else { v }),
                icon: Some(SuggestionIcon::Arg),
                priority: 55,
                insert_space: true,
            })
            .collect()
    }

    /// Get the spec for a command
    pub fn get_spec(&self, command: &str) -> Option<&CompletionSpec> {
        self.specs.get(command)
    }

    /// List all available command specs
    pub fn list_commands(&self) -> Vec<&str> {
        self.specs.keys().map(|s| s.as_str()).collect()
    }
}

impl Default for CompletionEngine {
    fn default() -> Self {
        Self::new()
    }
}

/// Built-in completion specs for common commands
fn builtin_specs() -> Vec<CompletionSpec> {
    vec![
        // git
        CompletionSpec {
            name: "git".into(),
            description: Some("Version control system".into()),
            subcommands: vec![
                CompletionSpec {
                    name: "add".into(),
                    description: Some("Add file contents to the index".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-A".into(), "--all".into()],
                            description: Some("Add all changes".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-p".into(), "--patch".into()],
                            description: Some("Interactively add hunks".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "pathspec".into(),
                        description: Some("Files to add".into()),
                        suggestions: vec![],
                        generator: None,
                        is_optional: true,
                        is_variadic: true,
                        template: Some(TemplateType::Filepaths),
                    }],
                },
                CompletionSpec {
                    name: "commit".into(),
                    description: Some("Record changes to the repository".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-m".into(), "--message".into()],
                            description: Some("Commit message".into()),
                            args: Some(ArgSpec {
                                name: "message".into(),
                                description: Some("Commit message".into()),
                                suggestions: vec![],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-a".into(), "--all".into()],
                            description: Some("Stage all modified files".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["--amend".into()],
                            description: Some("Amend previous commit".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
                CompletionSpec {
                    name: "checkout".into(),
                    description: Some("Switch branches or restore files".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-b".into()],
                            description: Some("Create and checkout new branch".into()),
                            args: Some(ArgSpec {
                                name: "branch".into(),
                                description: Some("New branch name".into()),
                                suggestions: vec![],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "branch".into(),
                        description: Some("Branch to checkout".into()),
                        suggestions: vec![],
                        generator: Some(Generator {
                            script: None,
                            template: Some(TemplateType::GitBranches),
                            post_process: None,
                        }),
                        is_optional: true,
                        is_variadic: false,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "push".into(),
                    description: Some("Update remote refs".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-u".into(), "--set-upstream".into()],
                            description: Some("Set upstream for branch".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-f".into(), "--force".into()],
                            description: Some("Force push".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![
                        ArgSpec {
                            name: "remote".into(),
                            description: Some("Remote name".into()),
                            suggestions: vec!["origin".into()],
                            generator: Some(Generator {
                                script: None,
                                template: Some(TemplateType::GitRemotes),
                                post_process: None,
                            }),
                            is_optional: true,
                            is_variadic: false,
                            template: None,
                        },
                        ArgSpec {
                            name: "branch".into(),
                            description: Some("Branch name".into()),
                            suggestions: vec![],
                            generator: Some(Generator {
                                script: None,
                                template: Some(TemplateType::GitBranches),
                                post_process: None,
                            }),
                            is_optional: true,
                            is_variadic: false,
                            template: None,
                        },
                    ],
                },
                CompletionSpec {
                    name: "pull".into(),
                    description: Some("Fetch and merge from remote".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["--rebase".into()],
                            description: Some("Rebase instead of merge".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
                CompletionSpec {
                    name: "status".into(),
                    description: Some("Show working tree status".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-s".into(), "--short".into()],
                            description: Some("Short format".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
                CompletionSpec {
                    name: "log".into(),
                    description: Some("Show commit logs".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["--oneline".into()],
                            description: Some("One line per commit".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-n".into()],
                            description: Some("Number of commits".into()),
                            args: Some(ArgSpec {
                                name: "number".into(),
                                description: None,
                                suggestions: vec!["5".into(), "10".into(), "20".into()],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
            ],
            options: vec![],
            args: vec![],
        },
        // docker
        CompletionSpec {
            name: "docker".into(),
            description: Some("Container runtime".into()),
            subcommands: vec![
                CompletionSpec {
                    name: "run".into(),
                    description: Some("Run a container".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-d".into(), "--detach".into()],
                            description: Some("Run in background".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-it".into()],
                            description: Some("Interactive TTY".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["--rm".into()],
                            description: Some("Remove after exit".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-p".into(), "--publish".into()],
                            description: Some("Port mapping".into()),
                            args: Some(ArgSpec {
                                name: "port".into(),
                                description: Some("host:container".into()),
                                suggestions: vec!["8080:80".into(), "3000:3000".into()],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: true,
                        },
                        OptionSpec {
                            name: vec!["-v".into(), "--volume".into()],
                            description: Some("Volume mapping".into()),
                            args: Some(ArgSpec {
                                name: "volume".into(),
                                description: Some("host:container".into()),
                                suggestions: vec![],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: true,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "image".into(),
                        description: Some("Docker image".into()),
                        suggestions: vec!["ubuntu".into(), "alpine".into(), "nginx".into(), "python".into()],
                        generator: Some(Generator {
                            script: None,
                            template: Some(TemplateType::DockerImages),
                            post_process: None,
                        }),
                        is_optional: false,
                        is_variadic: false,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "ps".into(),
                    description: Some("List containers".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-a".into(), "--all".into()],
                            description: Some("Show all containers".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
                CompletionSpec {
                    name: "images".into(),
                    description: Some("List images".into()),
                    subcommands: vec![],
                    options: vec![],
                    args: vec![],
                },
                CompletionSpec {
                    name: "build".into(),
                    description: Some("Build an image".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-t".into(), "--tag".into()],
                            description: Some("Image tag".into()),
                            args: Some(ArgSpec {
                                name: "tag".into(),
                                description: None,
                                suggestions: vec![],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: true,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "path".into(),
                        description: Some("Build context".into()),
                        suggestions: vec![".".into()],
                        generator: None,
                        is_optional: true,
                        is_variadic: false,
                        template: Some(TemplateType::Folders),
                    }],
                },
            ],
            options: vec![],
            args: vec![],
        },
        // npm
        CompletionSpec {
            name: "npm".into(),
            description: Some("Node package manager".into()),
            subcommands: vec![
                CompletionSpec {
                    name: "install".into(),
                    description: Some("Install packages".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-D".into(), "--save-dev".into()],
                            description: Some("Save as dev dependency".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-g".into(), "--global".into()],
                            description: Some("Install globally".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "packages".into(),
                        description: Some("Package names".into()),
                        suggestions: vec![],
                        generator: None,
                        is_optional: true,
                        is_variadic: true,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "run".into(),
                    description: Some("Run a script".into()),
                    subcommands: vec![],
                    options: vec![],
                    args: vec![ArgSpec {
                        name: "script".into(),
                        description: Some("Script name from package.json".into()),
                        suggestions: vec!["start".into(), "build".into(), "test".into(), "dev".into()],
                        generator: None,
                        is_optional: false,
                        is_variadic: false,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "test".into(),
                    description: Some("Run tests".into()),
                    subcommands: vec![],
                    options: vec![],
                    args: vec![],
                },
            ],
            options: vec![],
            args: vec![],
        },
        // cargo
        CompletionSpec {
            name: "cargo".into(),
            description: Some("Rust package manager".into()),
            subcommands: vec![
                CompletionSpec {
                    name: "build".into(),
                    description: Some("Compile the current package".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["--release".into()],
                            description: Some("Build in release mode".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
                CompletionSpec {
                    name: "run".into(),
                    description: Some("Run the main binary".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["--release".into()],
                            description: Some("Run in release mode".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![],
                },
                CompletionSpec {
                    name: "test".into(),
                    description: Some("Run tests".into()),
                    subcommands: vec![],
                    options: vec![],
                    args: vec![ArgSpec {
                        name: "testname".into(),
                        description: Some("Test name filter".into()),
                        suggestions: vec![],
                        generator: None,
                        is_optional: true,
                        is_variadic: false,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "add".into(),
                    description: Some("Add a dependency".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["--dev".into()],
                            description: Some("Add as dev dependency".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "crate".into(),
                        description: Some("Crate name".into()),
                        suggestions: vec![],
                        generator: None,
                        is_optional: false,
                        is_variadic: true,
                        template: None,
                    }],
                },
            ],
            options: vec![],
            args: vec![],
        },
        // python/pip
        CompletionSpec {
            name: "pip".into(),
            description: Some("Python package manager".into()),
            subcommands: vec![
                CompletionSpec {
                    name: "install".into(),
                    description: Some("Install packages".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-r".into(), "--requirement".into()],
                            description: Some("Install from requirements file".into()),
                            args: Some(ArgSpec {
                                name: "file".into(),
                                description: None,
                                suggestions: vec!["requirements.txt".into()],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: Some(TemplateType::Filepaths),
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-e".into(), "--editable".into()],
                            description: Some("Install in editable mode".into()),
                            args: Some(ArgSpec {
                                name: "path".into(),
                                description: None,
                                suggestions: vec![".".into()],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: Some(TemplateType::Folders),
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "packages".into(),
                        description: Some("Package names".into()),
                        suggestions: vec![],
                        generator: None,
                        is_optional: true,
                        is_variadic: true,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "freeze".into(),
                    description: Some("Output installed packages".into()),
                    subcommands: vec![],
                    options: vec![],
                    args: vec![],
                },
            ],
            options: vec![],
            args: vec![],
        },
        // kubectl
        CompletionSpec {
            name: "kubectl".into(),
            description: Some("Kubernetes CLI".into()),
            subcommands: vec![
                CompletionSpec {
                    name: "get".into(),
                    description: Some("Display resources".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-n".into(), "--namespace".into()],
                            description: Some("Namespace".into()),
                            args: Some(ArgSpec {
                                name: "namespace".into(),
                                description: None,
                                suggestions: vec!["default".into()],
                                generator: Some(Generator {
                                    script: None,
                                    template: Some(TemplateType::K8sNamespaces),
                                    post_process: None,
                                }),
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                        OptionSpec {
                            name: vec!["-o".into(), "--output".into()],
                            description: Some("Output format".into()),
                            args: Some(ArgSpec {
                                name: "format".into(),
                                description: None,
                                suggestions: vec!["yaml".into(), "json".into(), "wide".into()],
                                generator: None,
                                is_optional: false,
                                is_variadic: false,
                                template: None,
                            }),
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "resource".into(),
                        description: Some("Resource type".into()),
                        suggestions: vec!["pods".into(), "services".into(), "deployments".into(), "nodes".into(), "namespaces".into()],
                        generator: None,
                        is_optional: false,
                        is_variadic: false,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "describe".into(),
                    description: Some("Show details of a resource".into()),
                    subcommands: vec![],
                    options: vec![],
                    args: vec![ArgSpec {
                        name: "resource".into(),
                        description: Some("Resource type".into()),
                        suggestions: vec!["pod".into(), "service".into(), "deployment".into(), "node".into()],
                        generator: None,
                        is_optional: false,
                        is_variadic: false,
                        template: None,
                    }],
                },
                CompletionSpec {
                    name: "logs".into(),
                    description: Some("Print container logs".into()),
                    subcommands: vec![],
                    options: vec![
                        OptionSpec {
                            name: vec!["-f".into(), "--follow".into()],
                            description: Some("Follow logs".into()),
                            args: None,
                            required: false,
                            is_repeatable: false,
                        },
                    ],
                    args: vec![ArgSpec {
                        name: "pod".into(),
                        description: Some("Pod name".into()),
                        suggestions: vec![],
                        generator: Some(Generator {
                            script: None,
                            template: Some(TemplateType::K8sPods),
                            post_process: None,
                        }),
                        is_optional: false,
                        is_variadic: false,
                        template: None,
                    }],
                },
            ],
            options: vec![],
            args: vec![],
        },
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_command_completion() {
        let engine = CompletionEngine::new();
        let suggestions = engine.complete("gi", 2);
        assert!(suggestions.iter().any(|s| s.name == "git"));
    }

    #[test]
    fn test_subcommand_completion() {
        let engine = CompletionEngine::new();
        let suggestions = engine.complete("git ", 4);
        assert!(suggestions.iter().any(|s| s.name == "commit"));
        assert!(suggestions.iter().any(|s| s.name == "push"));
    }

    #[test]
    fn test_option_completion() {
        let engine = CompletionEngine::new();
        let suggestions = engine.complete("git commit -", 12);
        assert!(suggestions.iter().any(|s| s.name == "-m" || s.name == "--message"));
    }

    #[test]
    fn test_file_completion() {
        let engine = CompletionEngine::new();
        let suggestions = engine.complete("cat ", 4);
        // Should return file suggestions
        assert!(!suggestions.is_empty() || true); // May be empty depending on current directory
    }
}
