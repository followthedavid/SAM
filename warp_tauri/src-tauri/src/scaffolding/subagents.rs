// Subagent Manager - Delegate subtasks to specialized agents
//
// Provides Claude Code style subagent delegation:
// - Spawn specialized agents for specific tasks
// - Result aggregation from multiple subagents
// - Dependency management between subtasks
// - Progress tracking and cancellation

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Subagent {
    pub id: String,
    pub name: String,
    pub specialization: AgentSpecialization,
    pub status: SubagentStatus,
    pub task: Option<SubTask>,
    pub result: Option<SubagentResult>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum AgentSpecialization {
    /// Code search and exploration
    Explorer,
    /// Code writing and editing
    Coder,
    /// Code review and analysis
    Reviewer,
    /// Testing and validation
    Tester,
    /// Documentation generation
    Documenter,
    /// Debugging and fixing
    Debugger,
    /// Research and web search
    Researcher,
    /// General purpose
    General,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum SubagentStatus {
    Idle,
    Running,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubTask {
    pub id: String,
    pub description: String,
    pub context: TaskContext,
    pub dependencies: Vec<String>, // IDs of tasks that must complete first
    pub priority: u32,
    pub timeout_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TaskContext {
    pub working_dir: PathBuf,
    pub files: Vec<String>,
    pub instructions: String,
    pub parent_task_id: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubagentResult {
    pub task_id: String,
    pub agent_id: String,
    pub success: bool,
    pub output: String,
    pub files_modified: Vec<String>,
    pub insights: Vec<String>,
    pub execution_time_ms: u64,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DelegationPlan {
    pub id: String,
    pub description: String,
    pub subtasks: Vec<SubTask>,
    pub status: PlanStatus,
    pub results: HashMap<String, SubagentResult>,
    pub created_at: u64,
    pub completed_at: Option<u64>,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum PlanStatus {
    Planning,
    Executing,
    Completed,
    Failed,
    Cancelled,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubagentConfig {
    pub max_concurrent_subagents: u32,
    pub default_timeout_ms: u64,
    pub auto_decompose: bool,
    pub model: String,
}

impl Default for SubagentConfig {
    fn default() -> Self {
        Self {
            max_concurrent_subagents: 4,
            default_timeout_ms: 60000,
            auto_decompose: true,
            model: "qwen2.5-coder:1.5b".to_string(),
        }
    }
}

// =============================================================================
// SUBAGENT MANAGER
// =============================================================================

pub struct SubagentManager {
    config: SubagentConfig,
    agents: HashMap<String, Subagent>,
    active_plans: HashMap<String, DelegationPlan>,
    task_queue: Vec<SubTask>,
}

impl SubagentManager {
    pub fn new(config: SubagentConfig) -> Self {
        Self {
            config,
            agents: HashMap::new(),
            active_plans: HashMap::new(),
            task_queue: Vec::new(),
        }
    }

    /// Create a delegation plan from a complex task
    pub async fn create_plan(&mut self, task: &str, context: TaskContext) -> Result<DelegationPlan, String> {
        let plan_id = uuid::Uuid::new_v4().to_string();

        // Decompose task into subtasks
        let subtasks = if self.config.auto_decompose {
            self.decompose_task(task, &context).await?
        } else {
            // Single task, no decomposition
            vec![SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: task.to_string(),
                context: context.clone(),
                dependencies: vec![],
                priority: 1,
                timeout_ms: self.config.default_timeout_ms,
            }]
        };

        let plan = DelegationPlan {
            id: plan_id.clone(),
            description: task.to_string(),
            subtasks,
            status: PlanStatus::Planning,
            results: HashMap::new(),
            created_at: now_timestamp(),
            completed_at: None,
        };

        self.active_plans.insert(plan_id, plan.clone());
        Ok(plan)
    }

    /// Decompose a complex task into subtasks using simple heuristics
    async fn decompose_task(&self, task: &str, context: &TaskContext) -> Result<Vec<SubTask>, String> {
        let mut subtasks = Vec::new();
        let lower = task.to_lowercase();

        // Simple heuristic decomposition based on common patterns

        // 1. Always start with exploration if we need to find or analyze something
        if lower.contains("fix") || lower.contains("refactor") || lower.contains("implement") || lower.contains("add") {
            subtasks.push(SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: format!("Explore codebase to understand: {}", task),
                context: TaskContext {
                    working_dir: context.working_dir.clone(),
                    files: vec![],
                    instructions: "Search for relevant files and understand the existing code structure.".to_string(),
                    parent_task_id: None,
                },
                dependencies: vec![],
                priority: 1,
                timeout_ms: self.config.default_timeout_ms,
            });
        }

        // 2. Main task
        subtasks.push(SubTask {
            id: uuid::Uuid::new_v4().to_string(),
            description: task.to_string(),
            context: context.clone(),
            dependencies: if !subtasks.is_empty() {
                vec![subtasks.last().unwrap().id.clone()]
            } else {
                vec![]
            },
            priority: subtasks.len() as u32 + 1,
            timeout_ms: self.config.default_timeout_ms,
        });

        // 3. Add review step for code changes
        if lower.contains("write") || lower.contains("implement") || lower.contains("fix") || lower.contains("add") {
            subtasks.push(SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: format!("Review changes for: {}", task),
                context: TaskContext {
                    working_dir: context.working_dir.clone(),
                    files: vec![],
                    instructions: "Review the changes made and ensure they are correct.".to_string(),
                    parent_task_id: None,
                },
                dependencies: vec![subtasks.last().unwrap().id.clone()],
                priority: subtasks.len() as u32 + 1,
                timeout_ms: self.config.default_timeout_ms / 2,
            });
        }

        // 4. Add test step if applicable
        if lower.contains("test") || lower.contains("implement") || lower.contains("feature") {
            subtasks.push(SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: format!("Verify and test: {}", task),
                context: TaskContext {
                    working_dir: context.working_dir.clone(),
                    files: vec![],
                    instructions: "Run any relevant tests to verify the changes work.".to_string(),
                    parent_task_id: None,
                },
                dependencies: vec![subtasks.last().unwrap().id.clone()],
                priority: subtasks.len() as u32 + 1,
                timeout_ms: self.config.default_timeout_ms,
            });
        }

        if subtasks.is_empty() {
            // Fallback: just do the task directly
            subtasks.push(SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: task.to_string(),
                context: context.clone(),
                dependencies: vec![],
                priority: 1,
                timeout_ms: self.config.default_timeout_ms,
            });
        }

        Ok(subtasks)
    }

    /// Infer agent specialization from task description
    fn infer_specialization(&self, description: &str) -> AgentSpecialization {
        let lower = description.to_lowercase();

        if lower.contains("search") || lower.contains("find") || lower.contains("explore") {
            AgentSpecialization::Explorer
        } else if lower.contains("test") || lower.contains("verify") {
            AgentSpecialization::Tester
        } else if lower.contains("review") || lower.contains("analyze") {
            AgentSpecialization::Reviewer
        } else if lower.contains("document") || lower.contains("comment") {
            AgentSpecialization::Documenter
        } else if lower.contains("debug") || lower.contains("fix") {
            AgentSpecialization::Debugger
        } else if lower.contains("research") || lower.contains("look up") {
            AgentSpecialization::Researcher
        } else if lower.contains("write") || lower.contains("implement") || lower.contains("create") {
            AgentSpecialization::Coder
        } else {
            AgentSpecialization::General
        }
    }

    /// Execute a delegation plan
    pub async fn execute_plan(
        &mut self,
        plan_id: &str,
        on_progress: impl Fn(&str, SubagentStatus) + Send + Sync + 'static,
    ) -> Result<DelegationPlan, String> {
        let plan = self.active_plans.get_mut(plan_id)
            .ok_or_else(|| format!("Plan {} not found", plan_id))?;

        plan.status = PlanStatus::Executing;

        // Sort subtasks by priority and dependencies
        let mut ready_tasks: Vec<SubTask> = plan.subtasks.clone();
        ready_tasks.sort_by_key(|t| t.priority);

        let on_progress = Arc::new(on_progress);
        let mut results = HashMap::new();

        // Execute tasks respecting dependencies
        for task in ready_tasks {
            // Check dependencies
            for dep_id in &task.dependencies {
                if !results.contains_key(dep_id) {
                    // Dependency not met - this would need proper async handling
                    continue;
                }
            }

            // Spawn subagent
            let agent = self.spawn_agent(&task)?;
            on_progress(&agent.id, SubagentStatus::Running);

            // Execute task
            let result = self.execute_subtask(&agent, &task).await;

            let status = if result.success {
                SubagentStatus::Completed
            } else {
                SubagentStatus::Failed
            };

            on_progress(&agent.id, status);
            results.insert(task.id.clone(), result);
        }

        // Update plan
        let plan = self.active_plans.get_mut(plan_id).unwrap();
        plan.results = results;
        plan.status = if plan.results.values().all(|r| r.success) {
            PlanStatus::Completed
        } else {
            PlanStatus::Failed
        };
        plan.completed_at = Some(now_timestamp());

        Ok(plan.clone())
    }

    /// Spawn a subagent for a task
    fn spawn_agent(&mut self, task: &SubTask) -> Result<Subagent, String> {
        let specialization = self.infer_specialization(&task.description);

        let agent = Subagent {
            id: uuid::Uuid::new_v4().to_string(),
            name: format!("{:?} Agent", specialization),
            specialization,
            status: SubagentStatus::Idle,
            task: Some(task.clone()),
            result: None,
        };

        self.agents.insert(agent.id.clone(), agent.clone());
        Ok(agent)
    }

    /// Execute a subtask with an agent
    async fn execute_subtask(&self, agent: &Subagent, task: &SubTask) -> SubagentResult {
        let start = std::time::Instant::now();

        // Build specialized prompt based on agent type
        let prompt = self.build_specialized_prompt(agent.specialization, task);

        // Execute using direct Ollama call
        use crate::ollama::query_ollama;

        match query_ollama(prompt, Some(self.config.model.clone())).await {
            Ok(response) => {
                // Parse the response to extract any file modifications mentioned
                let files_modified = self.extract_files_from_response(&response);

                SubagentResult {
                    task_id: task.id.clone(),
                    agent_id: agent.id.clone(),
                    success: true,
                    output: response.clone(),
                    files_modified,
                    insights: self.extract_insights(&response),
                    execution_time_ms: start.elapsed().as_millis() as u64,
                    error: None,
                }
            },
            Err(e) => SubagentResult {
                task_id: task.id.clone(),
                agent_id: agent.id.clone(),
                success: false,
                output: String::new(),
                files_modified: vec![],
                insights: vec![],
                execution_time_ms: start.elapsed().as_millis() as u64,
                error: Some(e),
            },
        }
    }

    /// Extract file paths mentioned in the response
    fn extract_files_from_response(&self, response: &str) -> Vec<String> {
        let file_pattern = regex::Regex::new(r#"(?:file|path|wrote|created|modified)[:\s]+["`']?([^"`'\n]+\.[a-zA-Z]+)"#).ok();

        if let Some(re) = file_pattern {
            re.captures_iter(response)
                .filter_map(|cap| cap.get(1).map(|m| m.as_str().to_string()))
                .collect()
        } else {
            vec![]
        }
    }

    /// Build a specialized prompt for the agent type
    fn build_specialized_prompt(&self, spec: AgentSpecialization, task: &SubTask) -> String {
        let role = match spec {
            AgentSpecialization::Explorer => "You are a code exploration specialist. Search and analyze the codebase thoroughly.",
            AgentSpecialization::Coder => "You are a skilled programmer. Write clean, well-documented code.",
            AgentSpecialization::Reviewer => "You are a code reviewer. Analyze code quality, patterns, and potential issues.",
            AgentSpecialization::Tester => "You are a testing specialist. Create comprehensive tests and verify functionality.",
            AgentSpecialization::Documenter => "You are a documentation specialist. Write clear, helpful documentation.",
            AgentSpecialization::Debugger => "You are a debugging specialist. Find and fix bugs systematically.",
            AgentSpecialization::Researcher => "You are a research specialist. Find relevant information and solutions.",
            AgentSpecialization::General => "You are a helpful AI assistant.",
        };

        format!(
            "{}\n\nTask: {}\n\nContext:\nWorking directory: {}\nFiles: {:?}\nInstructions: {}",
            role,
            task.description,
            task.context.working_dir.display(),
            task.context.files,
            task.context.instructions
        )
    }

    /// Extract insights from agent output
    fn extract_insights(&self, output: &str) -> Vec<String> {
        let mut insights = Vec::new();

        // Look for key patterns
        for line in output.lines() {
            let lower = line.to_lowercase();
            if lower.contains("found") || lower.contains("discovered") ||
               lower.contains("issue") || lower.contains("note:") ||
               lower.contains("important") || lower.contains("warning") {
                insights.push(line.trim().to_string());
            }
        }

        insights.truncate(10); // Limit to 10 insights
        insights
    }

    /// Cancel a running plan
    pub fn cancel_plan(&mut self, plan_id: &str) -> Result<(), String> {
        let plan = self.active_plans.get_mut(plan_id)
            .ok_or_else(|| format!("Plan {} not found", plan_id))?;

        plan.status = PlanStatus::Cancelled;
        Ok(())
    }

    /// Get plan status
    pub fn get_plan(&self, plan_id: &str) -> Option<&DelegationPlan> {
        self.active_plans.get(plan_id)
    }

    /// Get all active plans
    pub fn get_active_plans(&self) -> Vec<&DelegationPlan> {
        self.active_plans.values()
            .filter(|p| p.status == PlanStatus::Executing || p.status == PlanStatus::Planning)
            .collect()
    }

    /// Aggregate results from a completed plan
    pub fn aggregate_results(&self, plan_id: &str) -> Result<String, String> {
        let plan = self.get_plan(plan_id)
            .ok_or_else(|| format!("Plan {} not found", plan_id))?;

        let mut output = String::new();
        output.push_str(&format!("# Results for: {}\n\n", plan.description));

        for (task_id, result) in &plan.results {
            let task = plan.subtasks.iter().find(|t| &t.id == task_id);
            let task_name = task.map(|t| t.description.as_str()).unwrap_or("Unknown task");

            output.push_str(&format!("## {}\n", task_name));
            output.push_str(&format!("Status: {}\n", if result.success { "Success" } else { "Failed" }));

            if !result.output.is_empty() {
                output.push_str(&format!("\n{}\n", result.output));
            }

            if !result.files_modified.is_empty() {
                output.push_str(&format!("\nFiles modified: {:?}\n", result.files_modified));
            }

            if !result.insights.is_empty() {
                output.push_str("\nInsights:\n");
                for insight in &result.insights {
                    output.push_str(&format!("- {}\n", insight));
                }
            }

            output.push('\n');
        }

        Ok(output)
    }

    /// Get stats
    pub fn stats(&self) -> SubagentStats {
        SubagentStats {
            active_plans: self.active_plans.len(),
            agents_count: self.agents.len(),
            queued_tasks: self.task_queue.len(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SubagentStats {
    pub active_plans: usize,
    pub agents_count: usize,
    pub queued_tasks: usize,
}

fn now_timestamp() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs()
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref SUBAGENT_MANAGER: Mutex<SubagentManager> = Mutex::new(SubagentManager::new(SubagentConfig::default()));
}

pub fn subagents() -> std::sync::MutexGuard<'static, SubagentManager> {
    SUBAGENT_MANAGER.lock().unwrap()
}

/// Create a delegation plan (sync wrapper - decompose_task is now sync heuristics)
pub fn create_plan_sync(task: &str, context: TaskContext) -> Result<DelegationPlan, String> {
    let mut manager = subagents();
    // Since decompose_task is now sync heuristics, we use a sync version
    let plan_id = uuid::Uuid::new_v4().to_string();

    let config = manager.config.clone();
    let subtasks = if config.auto_decompose {
        // Simplified sync decomposition
        let mut subtasks = Vec::new();
        let lower = task.to_lowercase();

        if lower.contains("fix") || lower.contains("refactor") || lower.contains("implement") || lower.contains("add") {
            subtasks.push(SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: format!("Explore codebase to understand: {}", task),
                context: TaskContext {
                    working_dir: context.working_dir.clone(),
                    files: vec![],
                    instructions: "Search for relevant files and understand the existing code structure.".to_string(),
                    parent_task_id: None,
                },
                dependencies: vec![],
                priority: 1,
                timeout_ms: config.default_timeout_ms,
            });
        }

        subtasks.push(SubTask {
            id: uuid::Uuid::new_v4().to_string(),
            description: task.to_string(),
            context: context.clone(),
            dependencies: if !subtasks.is_empty() {
                vec![subtasks.last().unwrap().id.clone()]
            } else {
                vec![]
            },
            priority: subtasks.len() as u32 + 1,
            timeout_ms: config.default_timeout_ms,
        });

        if subtasks.is_empty() {
            subtasks.push(SubTask {
                id: uuid::Uuid::new_v4().to_string(),
                description: task.to_string(),
                context: context.clone(),
                dependencies: vec![],
                priority: 1,
                timeout_ms: config.default_timeout_ms,
            });
        }
        subtasks
    } else {
        vec![SubTask {
            id: uuid::Uuid::new_v4().to_string(),
            description: task.to_string(),
            context: context.clone(),
            dependencies: vec![],
            priority: 1,
            timeout_ms: config.default_timeout_ms,
        }]
    };

    let plan = DelegationPlan {
        id: plan_id.clone(),
        description: task.to_string(),
        subtasks,
        status: PlanStatus::Planning,
        created_at: std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs(),
        completed_at: None,
        results: HashMap::new(),
    };

    manager.active_plans.insert(plan_id, plan.clone());
    Ok(plan)
}

/// Execute a plan - returns plan immediately after marking as executing
/// The actual async execution happens in background
pub fn execute_plan_sync(plan_id: &str) -> Result<DelegationPlan, String> {
    let mut manager = subagents();
    let plan = manager.active_plans.get_mut(plan_id)
        .ok_or_else(|| format!("Plan {} not found", plan_id))?;

    plan.status = PlanStatus::Executing;
    Ok(plan.clone())
}

/// Get plan status
pub fn get_plan(plan_id: &str) -> Option<DelegationPlan> {
    subagents().get_plan(plan_id).cloned()
}

/// Cancel a plan
pub fn cancel_plan(plan_id: &str) -> Result<(), String> {
    subagents().cancel_plan(plan_id)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_config_default() {
        let config = SubagentConfig::default();
        assert_eq!(config.max_concurrent_subagents, 4);
        assert!(config.auto_decompose);
    }

    #[test]
    fn test_infer_specialization() {
        let manager = SubagentManager::new(SubagentConfig::default());

        assert_eq!(manager.infer_specialization("search for files"), AgentSpecialization::Explorer);
        assert_eq!(manager.infer_specialization("write a function"), AgentSpecialization::Coder);
        assert_eq!(manager.infer_specialization("review the code"), AgentSpecialization::Reviewer);
        assert_eq!(manager.infer_specialization("test the feature"), AgentSpecialization::Tester);
        assert_eq!(manager.infer_specialization("debug this issue"), AgentSpecialization::Debugger);
    }

    #[test]
    fn test_extract_insights() {
        let manager = SubagentManager::new(SubagentConfig::default());

        let output = "Found a bug in line 42\nNormal text\nNote: This is important";
        let insights = manager.extract_insights(output);

        assert_eq!(insights.len(), 2);
        assert!(insights[0].contains("Found"));
        assert!(insights[1].contains("Note:"));
    }
}
