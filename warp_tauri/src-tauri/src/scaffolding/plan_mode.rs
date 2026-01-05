// Plan Mode - Multi-step task planning before execution
//
// Like Claude Code's plan mode:
// 1. Analyze complex tasks
// 2. Generate step-by-step plan
// 3. Show plan to user for approval
// 4. Execute approved plan

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Plan {
    pub id: String,
    pub task: String,
    pub steps: Vec<PlanStep>,
    pub status: PlanStatus,
    pub created_at: u64,
    pub approved_at: Option<u64>,
    pub completed_at: Option<u64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlanStep {
    pub id: usize,
    pub description: String,
    pub action_type: ActionType,
    pub target: Option<String>,  // file path, command, etc.
    pub status: StepStatus,
    pub output: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum PlanStatus {
    Draft,      // Being created
    Pending,    // Waiting for user approval
    Approved,   // User approved, ready to execute
    Executing,  // Currently running
    Completed,  // All steps done
    Failed,     // Execution failed
    Cancelled,  // User cancelled
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum StepStatus {
    Pending,
    Running,
    Completed,
    Failed,
    Skipped,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum ActionType {
    ReadFile,
    WriteFile,
    EditFile,
    CreateFile,
    DeleteFile,
    RunCommand,
    SearchCode,
    Analyze,
    Generate,
    Test,
    Other,
}

// =============================================================================
// PLAN GENERATOR
// =============================================================================

pub struct PlanGenerator;

impl PlanGenerator {
    /// Analyze a task and generate a plan
    pub fn generate(task: &str) -> Plan {
        let steps = Self::analyze_task(task);

        Plan {
            id: uuid::Uuid::new_v4().to_string(),
            task: task.to_string(),
            steps,
            status: PlanStatus::Pending,
            created_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            approved_at: None,
            completed_at: None,
        }
    }

    /// Analyze task and break into steps
    fn analyze_task(task: &str) -> Vec<PlanStep> {
        let lower = task.to_lowercase();
        let mut steps = Vec::new();
        let mut step_id = 1;

        // Pattern: "add/create/implement X"
        if lower.contains("add ") || lower.contains("create ") || lower.contains("implement ") {
            // Step 1: Understand existing code
            steps.push(PlanStep {
                id: step_id,
                description: "Search codebase for related existing code".to_string(),
                action_type: ActionType::SearchCode,
                target: Some(Self::extract_subject(&lower)),
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            // Step 2: Read relevant files
            steps.push(PlanStep {
                id: step_id,
                description: "Read relevant files to understand structure".to_string(),
                action_type: ActionType::ReadFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            // Step 3: Generate code
            steps.push(PlanStep {
                id: step_id,
                description: "Generate the new code".to_string(),
                action_type: ActionType::Generate,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            // Step 4: Write/Edit files
            steps.push(PlanStep {
                id: step_id,
                description: "Write changes to files".to_string(),
                action_type: ActionType::WriteFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;
        }

        // Pattern: "fix/debug/resolve"
        if lower.contains("fix ") || lower.contains("debug ") || lower.contains("resolve ") {
            steps.push(PlanStep {
                id: step_id,
                description: "Identify the error location".to_string(),
                action_type: ActionType::SearchCode,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Read the problematic code".to_string(),
                action_type: ActionType::ReadFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Analyze and fix the issue".to_string(),
                action_type: ActionType::Analyze,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Apply the fix".to_string(),
                action_type: ActionType::EditFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;
        }

        // Pattern: "refactor"
        if lower.contains("refactor") {
            steps.push(PlanStep {
                id: step_id,
                description: "Analyze current code structure".to_string(),
                action_type: ActionType::Analyze,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Identify refactoring opportunities".to_string(),
                action_type: ActionType::SearchCode,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Create backup of affected files".to_string(),
                action_type: ActionType::ReadFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Apply refactoring changes".to_string(),
                action_type: ActionType::EditFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Verify changes compile/work".to_string(),
                action_type: ActionType::RunCommand,
                target: Some("cargo build".to_string()),
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;
        }

        // Pattern: "test"
        if lower.contains("test") || lower.contains("write test") {
            steps.push(PlanStep {
                id: step_id,
                description: "Identify code to test".to_string(),
                action_type: ActionType::SearchCode,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Read existing tests for patterns".to_string(),
                action_type: ActionType::ReadFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Generate test code".to_string(),
                action_type: ActionType::Generate,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Write test file".to_string(),
                action_type: ActionType::WriteFile,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
            step_id += 1;

            steps.push(PlanStep {
                id: step_id,
                description: "Run tests to verify".to_string(),
                action_type: ActionType::Test,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
        }

        // Default single-step plan if no patterns matched
        if steps.is_empty() {
            steps.push(PlanStep {
                id: 1,
                description: format!("Execute: {}", task),
                action_type: ActionType::Other,
                target: None,
                status: StepStatus::Pending,
                output: None,
            });
        }

        steps
    }

    fn extract_subject(task: &str) -> String {
        // Extract the main subject from the task
        let words: Vec<&str> = task.split_whitespace().collect();

        // Skip action words and get the rest
        let skip_words = ["add", "create", "implement", "a", "an", "the", "new"];
        let subject: Vec<&str> = words.iter()
            .filter(|w| !skip_words.contains(&w.to_lowercase().as_str()))
            .take(3)
            .copied()
            .collect();

        subject.join(" ")
    }

    /// Check if a task should use plan mode
    pub fn should_use_plan_mode(task: &str) -> bool {
        let lower = task.to_lowercase();

        // Complex tasks that benefit from planning
        let plan_triggers = [
            "refactor",
            "implement",
            "add feature",
            "create feature",
            "build",
            "migrate",
            "upgrade",
            "convert",
            "rewrite",
            "redesign",
            "integrate",
            "setup",
            "configure",
        ];

        plan_triggers.iter().any(|t| lower.contains(t))
    }
}

// =============================================================================
// PLAN STORE
// =============================================================================

pub struct PlanModeStore {
    plans: HashMap<String, Plan>,
    active_plan: Option<String>,
}

impl PlanModeStore {
    pub fn new() -> Self {
        Self {
            plans: HashMap::new(),
            active_plan: None,
        }
    }

    pub fn create_plan(&mut self, task: &str) -> &Plan {
        let plan = PlanGenerator::generate(task);
        let id = plan.id.clone();
        self.plans.insert(id.clone(), plan);
        self.active_plan = Some(id.clone());
        self.plans.get(&id).unwrap()
    }

    pub fn get_active_plan(&self) -> Option<&Plan> {
        self.active_plan.as_ref().and_then(|id| self.plans.get(id))
    }

    pub fn get_active_plan_mut(&mut self) -> Option<&mut Plan> {
        self.active_plan.as_ref().and_then(|id| self.plans.get_mut(id))
    }

    pub fn approve_plan(&mut self) -> Result<(), String> {
        if let Some(plan) = self.get_active_plan_mut() {
            plan.status = PlanStatus::Approved;
            plan.approved_at = Some(
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs()
            );
            Ok(())
        } else {
            Err("No active plan".to_string())
        }
    }

    pub fn reject_plan(&mut self) -> Result<(), String> {
        if let Some(plan) = self.get_active_plan_mut() {
            plan.status = PlanStatus::Cancelled;
            self.active_plan = None;
            Ok(())
        } else {
            Err("No active plan".to_string())
        }
    }

    pub fn update_step_status(&mut self, step_id: usize, status: StepStatus, output: Option<String>) {
        if let Some(plan) = self.get_active_plan_mut() {
            if let Some(step) = plan.steps.iter_mut().find(|s| s.id == step_id) {
                step.status = status;
                step.output = output;
            }
        }
    }

    pub fn complete_plan(&mut self) {
        if let Some(plan) = self.get_active_plan_mut() {
            plan.status = PlanStatus::Completed;
            plan.completed_at = Some(
                std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap()
                    .as_secs()
            );
        }
        self.active_plan = None;
    }

    pub fn format_plan_for_display(plan: &Plan) -> String {
        let mut output = String::new();

        output.push_str(&format!("## Plan: {}\n\n", plan.task));
        output.push_str(&format!("**Status:** {:?}\n\n", plan.status));
        output.push_str("### Steps:\n\n");

        for step in &plan.steps {
            let status_icon = match step.status {
                StepStatus::Pending => "⏳",
                StepStatus::Running => "🔄",
                StepStatus::Completed => "✅",
                StepStatus::Failed => "❌",
                StepStatus::Skipped => "⏭️",
            };

            output.push_str(&format!("{}. {} {}\n", step.id, status_icon, step.description));

            if let Some(target) = &step.target {
                output.push_str(&format!("   Target: `{}`\n", target));
            }
        }

        if plan.status == PlanStatus::Pending {
            output.push_str("\n---\n");
            output.push_str("Reply **approve** to execute this plan, or **reject** to cancel.\n");
        }

        output
    }
}

// Global store
lazy_static::lazy_static! {
    static ref PLAN_STORE: Mutex<PlanModeStore> = Mutex::new(PlanModeStore::new());
}

pub fn plan_store() -> std::sync::MutexGuard<'static, PlanModeStore> {
    PLAN_STORE.lock().unwrap()
}

// =============================================================================
// PUBLIC API
// =============================================================================

/// Check if we should enter plan mode for this task
pub fn should_plan(task: &str) -> bool {
    PlanGenerator::should_use_plan_mode(task)
}

/// Create a new plan for a task
pub fn create_plan(task: &str) -> String {
    let mut store = plan_store();
    let plan = store.create_plan(task);
    PlanModeStore::format_plan_for_display(plan)
}

/// Get current plan status
pub fn get_current_plan() -> Option<String> {
    let store = plan_store();
    store.get_active_plan().map(PlanModeStore::format_plan_for_display)
}

/// Approve the current plan
pub fn approve_current_plan() -> Result<String, String> {
    let mut store = plan_store();
    store.approve_plan()?;
    Ok("Plan approved. Starting execution...".to_string())
}

/// Reject the current plan
pub fn reject_current_plan() -> Result<String, String> {
    let mut store = plan_store();
    store.reject_plan()?;
    Ok("Plan cancelled.".to_string())
}

/// Check if user input is a plan response
pub fn is_plan_response(input: &str) -> Option<bool> {
    let lower = input.to_lowercase().trim().to_string();

    if lower == "approve" || lower == "yes" || lower == "y" || lower == "ok" || lower == "go" {
        Some(true)
    } else if lower == "reject" || lower == "no" || lower == "n" || lower == "cancel" {
        Some(false)
    } else {
        None
    }
}

/// Check if there's a pending plan
pub fn has_pending_plan() -> bool {
    let store = plan_store();
    store.get_active_plan()
        .map(|p| p.status == PlanStatus::Pending)
        .unwrap_or(false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_should_use_plan_mode() {
        assert!(PlanGenerator::should_use_plan_mode("refactor the auth module"));
        assert!(PlanGenerator::should_use_plan_mode("implement a new feature"));
        assert!(!PlanGenerator::should_use_plan_mode("git status"));
        assert!(!PlanGenerator::should_use_plan_mode("list files"));
    }

    #[test]
    fn test_plan_generation() {
        let plan = PlanGenerator::generate("add a login feature");
        assert!(!plan.steps.is_empty());
        assert_eq!(plan.status, PlanStatus::Pending);
    }

    #[test]
    fn test_plan_response_detection() {
        assert_eq!(is_plan_response("approve"), Some(true));
        assert_eq!(is_plan_response("yes"), Some(true));
        assert_eq!(is_plan_response("reject"), Some(false));
        assert_eq!(is_plan_response("no"), Some(false));
        assert_eq!(is_plan_response("something else"), None);
    }
}
