// Skills System - Slash Commands for SAM
//
// Extensible command system similar to Claude Code's skills.
// Users can invoke skills with /command syntax.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Skill {
    pub id: String,
    pub name: String,
    pub description: String,
    pub usage: String,
    pub examples: Vec<String>,
    pub category: SkillCategory,
    pub handler: SkillHandler,
    pub enabled: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum SkillCategory {
    Git,
    Code,
    File,
    Web,
    System,
    AI,
    Custom,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum SkillHandler {
    /// Built-in Rust function
    Builtin(String),
    /// Shell command template
    Shell(String),
    /// Prompt template for AI
    Prompt(String),
    /// Workflow reference
    Workflow(String),
    /// JavaScript for frontend
    JavaScript(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillInvocation {
    pub skill_id: String,
    pub args: Vec<String>,
    pub raw_input: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillResult {
    pub success: bool,
    pub output: String,
    pub actions_taken: Vec<String>,
    pub follow_up: Option<String>,
}

// =============================================================================
// SKILL MANAGER
// =============================================================================

pub struct SkillManager {
    skills: HashMap<String, Skill>,
    aliases: HashMap<String, String>,
}

impl SkillManager {
    pub fn new() -> Self {
        let mut mgr = Self {
            skills: HashMap::new(),
            aliases: HashMap::new(),
        };
        mgr.register_builtins();
        mgr
    }

    /// Register a skill
    pub fn register(&mut self, skill: Skill) {
        self.skills.insert(skill.id.clone(), skill);
    }

    /// Register an alias for a skill
    pub fn alias(&mut self, alias: &str, skill_id: &str) {
        self.aliases.insert(alias.to_string(), skill_id.to_string());
    }

    /// Parse a slash command
    pub fn parse(&self, input: &str) -> Option<SkillInvocation> {
        if !input.starts_with('/') {
            return None;
        }

        let parts: Vec<&str> = input[1..].split_whitespace().collect();
        if parts.is_empty() {
            return None;
        }

        let command = parts[0].to_lowercase();
        let args: Vec<String> = parts[1..].iter().map(|s| s.to_string()).collect();

        // Check for alias
        let skill_id = self.aliases.get(&command)
            .cloned()
            .unwrap_or_else(|| command.clone());

        if self.skills.contains_key(&skill_id) {
            Some(SkillInvocation {
                skill_id,
                args,
                raw_input: input.to_string(),
            })
        } else {
            None
        }
    }

    /// Execute a skill
    pub async fn execute(&self, invocation: &SkillInvocation, cwd: &str) -> SkillResult {
        let skill = match self.skills.get(&invocation.skill_id) {
            Some(s) => s,
            None => return SkillResult {
                success: false,
                output: format!("Unknown skill: {}", invocation.skill_id),
                actions_taken: vec![],
                follow_up: None,
            },
        };

        if !skill.enabled {
            return SkillResult {
                success: false,
                output: format!("Skill '{}' is disabled", skill.name),
                actions_taken: vec![],
                follow_up: None,
            };
        }

        match &skill.handler {
            SkillHandler::Builtin(name) => {
                self.execute_builtin(name, &invocation.args, cwd).await
            }
            SkillHandler::Shell(template) => {
                self.execute_shell(template, &invocation.args, cwd).await
            }
            SkillHandler::Prompt(template) => {
                self.execute_prompt(template, &invocation.args).await
            }
            SkillHandler::Workflow(workflow_id) => {
                self.execute_workflow(workflow_id, &invocation.args).await
            }
            SkillHandler::JavaScript(_js) => {
                // Would be handled by frontend
                SkillResult {
                    success: false,
                    output: "JavaScript skills must be executed in frontend".to_string(),
                    actions_taken: vec![],
                    follow_up: None,
                }
            }
        }
    }

    async fn execute_builtin(&self, name: &str, args: &[String], cwd: &str) -> SkillResult {
        match name {
            "git_status" => {
                self.run_shell("git status", cwd).await
            }
            "git_diff" => {
                let file = args.first().map(|s| s.as_str()).unwrap_or("");
                self.run_shell(&format!("git diff {}", file), cwd).await
            }
            "git_log" => {
                let count = args.first().unwrap_or(&"10".to_string()).clone();
                self.run_shell(&format!("git log --oneline -n {}", count), cwd).await
            }
            "git_commit" => {
                let message = args.join(" ");
                if message.is_empty() {
                    return SkillResult {
                        success: false,
                        output: "Commit message required".to_string(),
                        actions_taken: vec![],
                        follow_up: Some("Usage: /commit <message>".to_string()),
                    };
                }
                self.run_shell(&format!("git add -A && git commit -m \"{}\"", message), cwd).await
            }
            "git_push" => {
                self.run_shell("git push", cwd).await
            }
            "git_pull" => {
                self.run_shell("git pull", cwd).await
            }
            "git_branch" => {
                if args.is_empty() {
                    self.run_shell("git branch -a", cwd).await
                } else {
                    self.run_shell(&format!("git checkout -b {}", args[0]), cwd).await
                }
            }
            "list_files" => {
                let path = args.first().map(|s| s.as_str()).unwrap_or(".");
                self.run_shell(&format!("ls -la {}", path), cwd).await
            }
            "find_files" => {
                let pattern = args.first().map(|s| s.as_str()).unwrap_or("*");
                self.run_shell(&format!("find . -name \"{}\" -type f 2>/dev/null | head -20", pattern), cwd).await
            }
            "grep_code" => {
                if args.is_empty() {
                    return SkillResult {
                        success: false,
                        output: "Search pattern required".to_string(),
                        actions_taken: vec![],
                        follow_up: Some("Usage: /grep <pattern>".to_string()),
                    };
                }
                let pattern = &args[0];
                self.run_shell(&format!("grep -rn \"{}\" . --include='*.rs' --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | head -30", pattern), cwd).await
            }
            "run_tests" => {
                // Detect project type and run appropriate tests
                let result = self.detect_and_run_tests(cwd).await;
                result
            }
            "build" => {
                self.detect_and_build(cwd).await
            }
            "clean" => {
                self.detect_and_clean(cwd).await
            }
            "help" => {
                self.show_help()
            }
            _ => SkillResult {
                success: false,
                output: format!("Unknown builtin: {}", name),
                actions_taken: vec![],
                follow_up: None,
            },
        }
    }

    async fn run_shell(&self, command: &str, cwd: &str) -> SkillResult {
        match std::process::Command::new("sh")
            .arg("-c")
            .arg(command)
            .current_dir(cwd)
            .output()
        {
            Ok(output) => {
                let stdout = String::from_utf8_lossy(&output.stdout);
                let stderr = String::from_utf8_lossy(&output.stderr);
                SkillResult {
                    success: output.status.success(),
                    output: format!("{}{}", stdout, stderr),
                    actions_taken: vec![format!("Executed: {}", command)],
                    follow_up: None,
                }
            }
            Err(e) => SkillResult {
                success: false,
                output: format!("Failed to execute: {}", e),
                actions_taken: vec![],
                follow_up: None,
            },
        }
    }

    async fn execute_shell(&self, template: &str, args: &[String], cwd: &str) -> SkillResult {
        let mut command = template.to_string();

        // Replace $1, $2, etc. with args
        for (i, arg) in args.iter().enumerate() {
            command = command.replace(&format!("${}", i + 1), arg);
        }
        command = command.replace("$@", &args.join(" "));

        self.run_shell(&command, cwd).await
    }

    async fn execute_prompt(&self, template: &str, args: &[String]) -> SkillResult {
        let mut prompt = template.to_string();

        for (i, arg) in args.iter().enumerate() {
            prompt = prompt.replace(&format!("${}", i + 1), arg);
        }
        prompt = prompt.replace("$@", &args.join(" "));

        SkillResult {
            success: true,
            output: prompt,
            actions_taken: vec!["Generated prompt for AI".to_string()],
            follow_up: Some("This prompt should be sent to the AI model".to_string()),
        }
    }

    async fn execute_workflow(&self, _workflow_id: &str, _args: &[String]) -> SkillResult {
        // Would integrate with workflow system
        SkillResult {
            success: false,
            output: "Workflow execution not yet implemented".to_string(),
            actions_taken: vec![],
            follow_up: None,
        }
    }

    async fn detect_and_run_tests(&self, cwd: &str) -> SkillResult {
        // Check for various test runners
        if std::path::Path::new(&format!("{}/Cargo.toml", cwd)).exists() {
            return self.run_shell("cargo test", cwd).await;
        }
        if std::path::Path::new(&format!("{}/package.json", cwd)).exists() {
            return self.run_shell("npm test", cwd).await;
        }
        if std::path::Path::new(&format!("{}/pytest.ini", cwd)).exists() ||
           std::path::Path::new(&format!("{}/setup.py", cwd)).exists() {
            return self.run_shell("pytest", cwd).await;
        }
        if std::path::Path::new(&format!("{}/go.mod", cwd)).exists() {
            return self.run_shell("go test ./...", cwd).await;
        }

        SkillResult {
            success: false,
            output: "Could not detect test framework".to_string(),
            actions_taken: vec![],
            follow_up: Some("Supported: cargo test, npm test, pytest, go test".to_string()),
        }
    }

    async fn detect_and_build(&self, cwd: &str) -> SkillResult {
        if std::path::Path::new(&format!("{}/Cargo.toml", cwd)).exists() {
            return self.run_shell("cargo build", cwd).await;
        }
        if std::path::Path::new(&format!("{}/package.json", cwd)).exists() {
            return self.run_shell("npm run build", cwd).await;
        }
        if std::path::Path::new(&format!("{}/Makefile", cwd)).exists() {
            return self.run_shell("make", cwd).await;
        }
        if std::path::Path::new(&format!("{}/go.mod", cwd)).exists() {
            return self.run_shell("go build ./...", cwd).await;
        }

        SkillResult {
            success: false,
            output: "Could not detect build system".to_string(),
            actions_taken: vec![],
            follow_up: None,
        }
    }

    async fn detect_and_clean(&self, cwd: &str) -> SkillResult {
        if std::path::Path::new(&format!("{}/Cargo.toml", cwd)).exists() {
            return self.run_shell("cargo clean", cwd).await;
        }
        if std::path::Path::new(&format!("{}/package.json", cwd)).exists() {
            return self.run_shell("rm -rf node_modules", cwd).await;
        }
        if std::path::Path::new(&format!("{}/Makefile", cwd)).exists() {
            return self.run_shell("make clean", cwd).await;
        }

        SkillResult {
            success: false,
            output: "Could not detect build system for cleaning".to_string(),
            actions_taken: vec![],
            follow_up: None,
        }
    }

    fn show_help(&self) -> SkillResult {
        let mut help = String::from("Available Skills:\n\n");

        let mut by_category: HashMap<SkillCategory, Vec<&Skill>> = HashMap::new();
        for skill in self.skills.values() {
            by_category.entry(skill.category.clone()).or_default().push(skill);
        }

        for (category, skills) in by_category {
            help.push_str(&format!("## {:?}\n", category));
            for skill in skills {
                help.push_str(&format!("  /{} - {}\n", skill.id, skill.description));
            }
            help.push('\n');
        }

        SkillResult {
            success: true,
            output: help,
            actions_taken: vec![],
            follow_up: None,
        }
    }

    /// List all skills
    pub fn list(&self) -> Vec<&Skill> {
        self.skills.values().collect()
    }

    /// Get a skill by ID
    pub fn get(&self, id: &str) -> Option<&Skill> {
        self.skills.get(id)
    }

    /// Search skills
    pub fn search(&self, query: &str) -> Vec<&Skill> {
        let query = query.to_lowercase();
        self.skills.values()
            .filter(|s| {
                s.id.to_lowercase().contains(&query) ||
                s.name.to_lowercase().contains(&query) ||
                s.description.to_lowercase().contains(&query)
            })
            .collect()
    }

    /// Register built-in skills
    fn register_builtins(&mut self) {
        // Git skills
        self.register(Skill {
            id: "status".to_string(),
            name: "Git Status".to_string(),
            description: "Show git repository status".to_string(),
            usage: "/status".to_string(),
            examples: vec!["/status".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_status".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "diff".to_string(),
            name: "Git Diff".to_string(),
            description: "Show git diff".to_string(),
            usage: "/diff [file]".to_string(),
            examples: vec!["/diff".to_string(), "/diff src/main.rs".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_diff".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "log".to_string(),
            name: "Git Log".to_string(),
            description: "Show recent commits".to_string(),
            usage: "/log [count]".to_string(),
            examples: vec!["/log".to_string(), "/log 20".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_log".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "commit".to_string(),
            name: "Git Commit".to_string(),
            description: "Stage all and commit with message".to_string(),
            usage: "/commit <message>".to_string(),
            examples: vec!["/commit Fix typo in README".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_commit".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "push".to_string(),
            name: "Git Push".to_string(),
            description: "Push to remote".to_string(),
            usage: "/push".to_string(),
            examples: vec!["/push".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_push".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "pull".to_string(),
            name: "Git Pull".to_string(),
            description: "Pull from remote".to_string(),
            usage: "/pull".to_string(),
            examples: vec!["/pull".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_pull".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "branch".to_string(),
            name: "Git Branch".to_string(),
            description: "List branches or create new".to_string(),
            usage: "/branch [name]".to_string(),
            examples: vec!["/branch".to_string(), "/branch feature-x".to_string()],
            category: SkillCategory::Git,
            handler: SkillHandler::Builtin("git_branch".to_string()),
            enabled: true,
        });

        // File skills
        self.register(Skill {
            id: "ls".to_string(),
            name: "List Files".to_string(),
            description: "List files in directory".to_string(),
            usage: "/ls [path]".to_string(),
            examples: vec!["/ls".to_string(), "/ls src".to_string()],
            category: SkillCategory::File,
            handler: SkillHandler::Builtin("list_files".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "find".to_string(),
            name: "Find Files".to_string(),
            description: "Find files by pattern".to_string(),
            usage: "/find <pattern>".to_string(),
            examples: vec!["/find *.rs".to_string(), "/find test_*".to_string()],
            category: SkillCategory::File,
            handler: SkillHandler::Builtin("find_files".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "grep".to_string(),
            name: "Search Code".to_string(),
            description: "Search for pattern in code".to_string(),
            usage: "/grep <pattern>".to_string(),
            examples: vec!["/grep TODO".to_string(), "/grep fn main".to_string()],
            category: SkillCategory::Code,
            handler: SkillHandler::Builtin("grep_code".to_string()),
            enabled: true,
        });

        // Build skills
        self.register(Skill {
            id: "test".to_string(),
            name: "Run Tests".to_string(),
            description: "Run project tests".to_string(),
            usage: "/test".to_string(),
            examples: vec!["/test".to_string()],
            category: SkillCategory::Code,
            handler: SkillHandler::Builtin("run_tests".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "build".to_string(),
            name: "Build Project".to_string(),
            description: "Build the project".to_string(),
            usage: "/build".to_string(),
            examples: vec!["/build".to_string()],
            category: SkillCategory::Code,
            handler: SkillHandler::Builtin("build".to_string()),
            enabled: true,
        });

        self.register(Skill {
            id: "clean".to_string(),
            name: "Clean Build".to_string(),
            description: "Clean build artifacts".to_string(),
            usage: "/clean".to_string(),
            examples: vec!["/clean".to_string()],
            category: SkillCategory::Code,
            handler: SkillHandler::Builtin("clean".to_string()),
            enabled: true,
        });

        // System skills
        self.register(Skill {
            id: "help".to_string(),
            name: "Help".to_string(),
            description: "Show available skills".to_string(),
            usage: "/help".to_string(),
            examples: vec!["/help".to_string()],
            category: SkillCategory::System,
            handler: SkillHandler::Builtin("help".to_string()),
            enabled: true,
        });

        // Set up aliases
        self.alias("st", "status");
        self.alias("co", "commit");
        self.alias("br", "branch");
    }
}

impl Default for SkillManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL SKILL MANAGER
// =============================================================================

lazy_static::lazy_static! {
    pub static ref SKILL_MANAGER: Mutex<SkillManager> = Mutex::new(SkillManager::new());
}

pub fn skills() -> std::sync::MutexGuard<'static, SkillManager> {
    SKILL_MANAGER.lock().unwrap()
}

/// Parse a potential skill invocation
pub fn parse_skill(input: &str) -> Option<SkillInvocation> {
    skills().parse(input)
}

/// Execute a skill
pub async fn execute_skill(invocation: &SkillInvocation, cwd: &str) -> SkillResult {
    // Get skill info while holding the lock, then release before async work
    let skill_info = {
        let mgr = skills();
        match mgr.get(&invocation.skill_id) {
            Some(s) => Some((s.clone(), s.enabled)),
            None => None,
        }
    };

    let (skill, enabled) = match skill_info {
        Some((s, e)) => (s, e),
        None => return SkillResult {
            success: false,
            output: format!("Unknown skill: {}", invocation.skill_id),
            actions_taken: vec![],
            follow_up: None,
        },
    };

    if !enabled {
        return SkillResult {
            success: false,
            output: format!("Skill '{}' is disabled", skill.name),
            actions_taken: vec![],
            follow_up: None,
        };
    }

    // Execute skill outside the lock
    execute_skill_handler(&skill.handler, &invocation.args, cwd).await
}

/// Execute a skill handler (internal, no mutex)
async fn execute_skill_handler(handler: &SkillHandler, args: &[String], cwd: &str) -> SkillResult {
    match handler {
        SkillHandler::Builtin(name) => {
            execute_builtin_skill(name, args, cwd).await
        }
        SkillHandler::Shell(template) => {
            execute_shell_skill(template, args, cwd).await
        }
        SkillHandler::Prompt(template) => {
            execute_prompt_skill(template, args)
        }
        SkillHandler::Workflow(_workflow_id) => {
            SkillResult {
                success: false,
                output: "Workflow execution not yet implemented".to_string(),
                actions_taken: vec![],
                follow_up: None,
            }
        }
        SkillHandler::JavaScript(_js) => {
            SkillResult {
                success: false,
                output: "JavaScript skills must be executed in frontend".to_string(),
                actions_taken: vec![],
                follow_up: None,
            }
        }
    }
}

async fn run_shell_command(command: &str, cwd: &str) -> SkillResult {
    match std::process::Command::new("sh")
        .arg("-c")
        .arg(command)
        .current_dir(cwd)
        .output()
    {
        Ok(output) => {
            let stdout = String::from_utf8_lossy(&output.stdout);
            let stderr = String::from_utf8_lossy(&output.stderr);
            SkillResult {
                success: output.status.success(),
                output: format!("{}{}", stdout, stderr),
                actions_taken: vec![format!("Executed: {}", command)],
                follow_up: None,
            }
        }
        Err(e) => SkillResult {
            success: false,
            output: format!("Failed to execute: {}", e),
            actions_taken: vec![],
            follow_up: None,
        },
    }
}

async fn execute_builtin_skill(name: &str, args: &[String], cwd: &str) -> SkillResult {
    match name {
        "git_status" => run_shell_command("git status", cwd).await,
        "git_diff" => {
            let file = args.first().map(|s| s.as_str()).unwrap_or("");
            run_shell_command(&format!("git diff {}", file), cwd).await
        }
        "git_log" => {
            let count = args.first().unwrap_or(&"10".to_string()).clone();
            run_shell_command(&format!("git log --oneline -n {}", count), cwd).await
        }
        "git_commit" => {
            let message = args.join(" ");
            if message.is_empty() {
                return SkillResult {
                    success: false,
                    output: "Commit message required".to_string(),
                    actions_taken: vec![],
                    follow_up: Some("Usage: /commit <message>".to_string()),
                };
            }
            run_shell_command(&format!("git add -A && git commit -m \"{}\"", message), cwd).await
        }
        "git_push" => run_shell_command("git push", cwd).await,
        "git_pull" => run_shell_command("git pull", cwd).await,
        "git_branch" => {
            if args.is_empty() {
                run_shell_command("git branch -a", cwd).await
            } else {
                run_shell_command(&format!("git checkout -b {}", args[0]), cwd).await
            }
        }
        "list_files" => {
            let path = args.first().map(|s| s.as_str()).unwrap_or(".");
            run_shell_command(&format!("ls -la {}", path), cwd).await
        }
        "find_files" => {
            let pattern = args.first().map(|s| s.as_str()).unwrap_or("*");
            run_shell_command(&format!("find . -name \"{}\" -type f 2>/dev/null | head -20", pattern), cwd).await
        }
        "grep_code" => {
            if args.is_empty() {
                return SkillResult {
                    success: false,
                    output: "Search pattern required".to_string(),
                    actions_taken: vec![],
                    follow_up: Some("Usage: /grep <pattern>".to_string()),
                };
            }
            let pattern = &args[0];
            run_shell_command(&format!("grep -rn \"{}\" . --include='*.rs' --include='*.ts' --include='*.js' --include='*.py' 2>/dev/null | head -30", pattern), cwd).await
        }
        "run_tests" => {
            if std::path::Path::new(&format!("{}/Cargo.toml", cwd)).exists() {
                return run_shell_command("cargo test", cwd).await;
            }
            if std::path::Path::new(&format!("{}/package.json", cwd)).exists() {
                return run_shell_command("npm test", cwd).await;
            }
            SkillResult {
                success: false,
                output: "Could not detect test framework".to_string(),
                actions_taken: vec![],
                follow_up: Some("Supported: cargo test, npm test".to_string()),
            }
        }
        "build" => {
            if std::path::Path::new(&format!("{}/Cargo.toml", cwd)).exists() {
                return run_shell_command("cargo build", cwd).await;
            }
            if std::path::Path::new(&format!("{}/package.json", cwd)).exists() {
                return run_shell_command("npm run build", cwd).await;
            }
            SkillResult {
                success: false,
                output: "Could not detect build system".to_string(),
                actions_taken: vec![],
                follow_up: None,
            }
        }
        "clean" => {
            if std::path::Path::new(&format!("{}/Cargo.toml", cwd)).exists() {
                return run_shell_command("cargo clean", cwd).await;
            }
            if std::path::Path::new(&format!("{}/package.json", cwd)).exists() {
                return run_shell_command("rm -rf node_modules", cwd).await;
            }
            SkillResult {
                success: false,
                output: "Could not detect build system for cleaning".to_string(),
                actions_taken: vec![],
                follow_up: None,
            }
        }
        "help" => {
            let mgr = skills();
            let skills_list: Vec<_> = mgr.list().iter().map(|s| format!("/{} - {}", s.id, s.description)).collect();
            SkillResult {
                success: true,
                output: format!("Available Skills:\n{}", skills_list.join("\n")),
                actions_taken: vec![],
                follow_up: None,
            }
        }
        _ => SkillResult {
            success: false,
            output: format!("Unknown builtin: {}", name),
            actions_taken: vec![],
            follow_up: None,
        },
    }
}

async fn execute_shell_skill(template: &str, args: &[String], cwd: &str) -> SkillResult {
    let mut command = template.to_string();
    for (i, arg) in args.iter().enumerate() {
        command = command.replace(&format!("${}", i + 1), arg);
    }
    command = command.replace("$@", &args.join(" "));
    run_shell_command(&command, cwd).await
}

fn execute_prompt_skill(template: &str, args: &[String]) -> SkillResult {
    let mut prompt = template.to_string();
    for (i, arg) in args.iter().enumerate() {
        prompt = prompt.replace(&format!("${}", i + 1), arg);
    }
    prompt = prompt.replace("$@", &args.join(" "));
    SkillResult {
        success: true,
        output: prompt,
        actions_taken: vec!["Generated prompt for AI".to_string()],
        follow_up: Some("This prompt should be sent to the AI model".to_string()),
    }
}

/// List all skills
pub fn list_skills() -> Vec<Skill> {
    skills().list().iter().map(|s| (*s).clone()).collect()
}

/// Search skills
pub fn search_skills(query: &str) -> Vec<Skill> {
    skills().search(query).iter().map(|s| (*s).clone()).collect()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_skill() {
        let mgr = SkillManager::new();

        let result = mgr.parse("/status");
        assert!(result.is_some());
        assert_eq!(result.unwrap().skill_id, "status");

        let result = mgr.parse("/commit Fix bug");
        assert!(result.is_some());
        let inv = result.unwrap();
        assert_eq!(inv.skill_id, "commit");
        assert_eq!(inv.args, vec!["Fix", "bug"]);
    }

    #[test]
    fn test_parse_alias() {
        let mgr = SkillManager::new();

        let result = mgr.parse("/st");
        assert!(result.is_some());
        assert_eq!(result.unwrap().skill_id, "status");
    }

    #[test]
    fn test_parse_non_skill() {
        let mgr = SkillManager::new();

        assert!(mgr.parse("hello").is_none());
        assert!(mgr.parse("/unknown_command").is_none());
    }

    #[test]
    fn test_search_skills() {
        let mgr = SkillManager::new();

        let results = mgr.search("git");
        assert!(!results.is_empty());

        let results = mgr.search("commit");
        assert!(results.iter().any(|s| s.id == "commit"));
    }

    #[test]
    fn test_list_skills() {
        let mgr = SkillManager::new();
        let skills = mgr.list();
        assert!(skills.len() >= 10); // We have at least 10 builtins
    }

    #[tokio::test]
    async fn test_help_skill() {
        let mgr = SkillManager::new();

        let invocation = SkillInvocation {
            skill_id: "help".to_string(),
            args: vec![],
            raw_input: "/help".to_string(),
        };

        let result = mgr.execute(&invocation, ".").await;
        assert!(result.success);
        assert!(result.output.contains("Available Skills"));
    }
}
