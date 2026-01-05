// Intelligence Engine for SAM
//
// The key insight: We don't need AI to THINK. We need AI to ROUTE.
//
// A tiny 1.5B model cannot reason, but it CAN:
// - Classify intent into 1 of N categories
// - Extract entities (file paths, search terms)
// - Pick from a short list
//
// The REAL intelligence comes from:
// - Pre-built deterministic workflows
// - Powerful Unix tools (grep, find, ast-grep)
// - Tree-sitter for code understanding
// - Embeddings for similarity search
//
// This runs on 8GB Apple Silicon with insane efficiency.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::process::Command;

// =============================================================================
// TASK TAXONOMY - Every possible task SAM can do
// =============================================================================

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[repr(u8)]
pub enum TaskType {
    // File Operations (1-10)
    FindFiles = 1,
    ReadFile = 2,
    WriteFile = 3,
    EditFile = 4,
    DeleteFile = 5,
    MoveFile = 6,
    CopyFile = 7,
    CreateDirectory = 8,
    ListDirectory = 9,
    FileInfo = 10,

    // Code Search (11-20)
    SearchText = 11,
    SearchFunction = 12,
    SearchClass = 13,
    SearchImports = 14,
    SearchTodos = 15,
    SearchErrors = 16,
    FindReferences = 17,
    FindDefinition = 18,
    SearchPattern = 19,
    SearchRecent = 20,

    // Code Understanding (21-30)
    ExplainCode = 21,
    SummarizeFile = 22,
    ListFunctions = 23,
    ListClasses = 24,
    ShowDependencies = 25,
    ShowStructure = 26,
    FindSimilar = 27,
    CheckSyntax = 28,
    Lint = 29,
    TypeCheck = 30,

    // Code Generation (31-40)
    GenerateFunction = 31,
    GenerateClass = 32,
    GenerateTest = 33,
    GenerateDocstring = 34,
    RefactorCode = 35,
    FixBug = 36,
    AddFeature = 37,
    Optimize = 38,
    ConvertCode = 39,
    CompleteCode = 40,

    // Git Operations (41-50)
    GitStatus = 41,
    GitDiff = 42,
    GitLog = 43,
    GitCommit = 44,
    GitBranch = 45,
    GitCheckout = 46,
    GitPush = 47,
    GitPull = 48,
    GitStash = 49,
    GitBlame = 50,

    // Shell Operations (51-60)
    RunCommand = 51,
    InstallPackage = 52,
    BuildProject = 53,
    RunTests = 54,
    StartServer = 55,
    StopProcess = 56,
    CheckPort = 57,
    SystemInfo = 58,
    DiskUsage = 59,
    ProcessList = 60,

    // Project Operations (61-70)
    InitProject = 61,
    AddDependency = 62,
    UpdateDeps = 63,
    CleanProject = 64,
    FormatCode = 65,
    GenerateConfig = 66,
    SetupEnv = 67,
    Deploy = 68,
    Package = 69,
    Publish = 70,

    // Meta Operations (71-80)
    Help = 71,
    ListTasks = 72,
    ShowHistory = 73,
    Undo = 74,
    Redo = 75,
    SaveState = 76,
    LoadState = 77,
    Configure = 78,
    Reset = 79,
    Exit = 80,

    // Catch-all
    Unknown = 255,
}

impl TaskType {
    pub fn from_id(id: u8) -> Self {
        match id {
            1 => TaskType::FindFiles,
            2 => TaskType::ReadFile,
            3 => TaskType::WriteFile,
            4 => TaskType::EditFile,
            5 => TaskType::DeleteFile,
            6 => TaskType::MoveFile,
            7 => TaskType::CopyFile,
            8 => TaskType::CreateDirectory,
            9 => TaskType::ListDirectory,
            10 => TaskType::FileInfo,
            11 => TaskType::SearchText,
            12 => TaskType::SearchFunction,
            13 => TaskType::SearchClass,
            14 => TaskType::SearchImports,
            15 => TaskType::SearchTodos,
            16 => TaskType::SearchErrors,
            17 => TaskType::FindReferences,
            18 => TaskType::FindDefinition,
            19 => TaskType::SearchPattern,
            20 => TaskType::SearchRecent,
            21 => TaskType::ExplainCode,
            22 => TaskType::SummarizeFile,
            23 => TaskType::ListFunctions,
            24 => TaskType::ListClasses,
            25 => TaskType::ShowDependencies,
            26 => TaskType::ShowStructure,
            27 => TaskType::FindSimilar,
            28 => TaskType::CheckSyntax,
            29 => TaskType::Lint,
            30 => TaskType::TypeCheck,
            31 => TaskType::GenerateFunction,
            32 => TaskType::GenerateClass,
            33 => TaskType::GenerateTest,
            34 => TaskType::GenerateDocstring,
            35 => TaskType::RefactorCode,
            36 => TaskType::FixBug,
            37 => TaskType::AddFeature,
            38 => TaskType::Optimize,
            39 => TaskType::ConvertCode,
            40 => TaskType::CompleteCode,
            41 => TaskType::GitStatus,
            42 => TaskType::GitDiff,
            43 => TaskType::GitLog,
            44 => TaskType::GitCommit,
            45 => TaskType::GitBranch,
            46 => TaskType::GitCheckout,
            47 => TaskType::GitPush,
            48 => TaskType::GitPull,
            49 => TaskType::GitStash,
            50 => TaskType::GitBlame,
            51 => TaskType::RunCommand,
            52 => TaskType::InstallPackage,
            53 => TaskType::BuildProject,
            54 => TaskType::RunTests,
            55 => TaskType::StartServer,
            56 => TaskType::StopProcess,
            57 => TaskType::CheckPort,
            58 => TaskType::SystemInfo,
            59 => TaskType::DiskUsage,
            60 => TaskType::ProcessList,
            61 => TaskType::InitProject,
            62 => TaskType::AddDependency,
            63 => TaskType::UpdateDeps,
            64 => TaskType::CleanProject,
            65 => TaskType::FormatCode,
            66 => TaskType::GenerateConfig,
            67 => TaskType::SetupEnv,
            68 => TaskType::Deploy,
            69 => TaskType::Package,
            70 => TaskType::Publish,
            71 => TaskType::Help,
            72 => TaskType::ListTasks,
            73 => TaskType::ShowHistory,
            74 => TaskType::Undo,
            75 => TaskType::Redo,
            76 => TaskType::SaveState,
            77 => TaskType::LoadState,
            78 => TaskType::Configure,
            79 => TaskType::Reset,
            80 => TaskType::Exit,
            _ => TaskType::Unknown,
        }
    }
}

// =============================================================================
// KEYWORD CLASSIFIER - No AI needed for most classification
// =============================================================================

pub struct KeywordClassifier {
    patterns: HashMap<TaskType, Vec<&'static str>>,
}

impl KeywordClassifier {
    pub fn new() -> Self {
        let mut patterns = HashMap::new();

        // File operations
        patterns.insert(TaskType::FindFiles, vec![
            "find", "search for files", "locate", "where is", "find all", "*.py", "*.rs", "*.js"
        ]);
        patterns.insert(TaskType::ReadFile, vec![
            "read", "show", "cat", "display", "print", "view", "open", "contents of"
        ]);
        patterns.insert(TaskType::WriteFile, vec![
            "write", "create file", "save to", "output to", "write to"
        ]);
        patterns.insert(TaskType::EditFile, vec![
            "edit", "modify", "change", "update", "replace", "fix in"
        ]);
        patterns.insert(TaskType::ListDirectory, vec![
            "ls", "list", "dir", "what's in", "show folder", "directory"
        ]);

        // Search operations
        patterns.insert(TaskType::SearchText, vec![
            "grep", "search for", "find text", "look for", "where does", "contains"
        ]);
        patterns.insert(TaskType::SearchFunction, vec![
            "find function", "where is function", "def ", "fn ", "func ", "function"
        ]);
        patterns.insert(TaskType::SearchClass, vec![
            "find class", "where is class", "class ", "struct ", "type "
        ]);
        patterns.insert(TaskType::SearchErrors, vec![
            "find errors", "search errors", "error", "bug", "issue", "problem"
        ]);

        // Git operations
        patterns.insert(TaskType::GitStatus, vec![
            "git status", "status", "what changed", "modifications"
        ]);
        patterns.insert(TaskType::GitDiff, vec![
            "git diff", "diff", "changes", "what's different"
        ]);
        patterns.insert(TaskType::GitCommit, vec![
            "commit", "git commit", "save changes"
        ]);
        patterns.insert(TaskType::GitLog, vec![
            "git log", "history", "commits", "log"
        ]);

        // Shell operations
        patterns.insert(TaskType::RunCommand, vec![
            "run", "execute", "shell", "command", "$"
        ]);
        patterns.insert(TaskType::BuildProject, vec![
            "build", "compile", "make", "cargo build", "npm build"
        ]);
        patterns.insert(TaskType::RunTests, vec![
            "test", "run tests", "pytest", "cargo test", "npm test"
        ]);
        patterns.insert(TaskType::InstallPackage, vec![
            "install", "add package", "npm install", "pip install", "cargo add"
        ]);

        // Code understanding
        patterns.insert(TaskType::ExplainCode, vec![
            "explain", "what does", "how does", "understand", "meaning"
        ]);
        patterns.insert(TaskType::ListFunctions, vec![
            "list functions", "all functions", "show functions", "methods"
        ]);
        patterns.insert(TaskType::ShowStructure, vec![
            "structure", "architecture", "layout", "organization"
        ]);

        Self { patterns }
    }

    /// Classify input using keyword matching (fast, no AI)
    pub fn classify(&self, input: &str) -> (TaskType, f32) {
        let input_lower = input.to_lowercase();
        let mut best_match = TaskType::Unknown;
        let mut best_score = 0.0f32;

        for (task_type, keywords) in &self.patterns {
            let mut score = 0.0f32;
            for keyword in keywords {
                if input_lower.contains(keyword) {
                    // Longer keyword matches are worth more
                    score += keyword.len() as f32;
                }
            }
            if score > best_score {
                best_score = score;
                best_match = *task_type;
            }
        }

        // Normalize score to 0-1
        let confidence = (best_score / 20.0).min(1.0);
        (best_match, confidence)
    }
}

// =============================================================================
// ENTITY EXTRACTOR - Pull out file paths, search terms, etc.
// =============================================================================

pub struct EntityExtractor;

impl EntityExtractor {
    /// Extract file paths from input
    pub fn extract_paths(input: &str) -> Vec<String> {
        let mut paths = Vec::new();

        // Match quoted paths
        let quote_re = regex::Regex::new(r#"["']([^"']+)["']"#).unwrap();
        for cap in quote_re.captures_iter(input) {
            if let Some(m) = cap.get(1) {
                let p = m.as_str();
                if p.contains('/') || p.contains('.') {
                    paths.push(p.to_string());
                }
            }
        }

        // Match unquoted paths
        let path_re = regex::Regex::new(r"(?:^|\s)([~/.]?[\w\-./]+\.[\w]+)").unwrap();
        for cap in path_re.captures_iter(input) {
            if let Some(m) = cap.get(1) {
                paths.push(m.as_str().to_string());
            }
        }

        // Match directory paths
        let dir_re = regex::Regex::new(r"(?:^|\s)([~/][\w\-./]+)(?:\s|$)").unwrap();
        for cap in dir_re.captures_iter(input) {
            if let Some(m) = cap.get(1) {
                let p = m.as_str();
                if !paths.contains(&p.to_string()) {
                    paths.push(p.to_string());
                }
            }
        }

        paths
    }

    /// Extract search patterns
    pub fn extract_search_term(input: &str) -> Option<String> {
        // Look for quoted search terms
        let quote_re = regex::Regex::new(r#"["']([^"']+)["']"#).unwrap();
        if let Some(cap) = quote_re.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        // Look for "for X" pattern
        let for_re = regex::Regex::new(r"(?:for|find|search)\s+(\w+)").unwrap();
        if let Some(cap) = for_re.captures(input) {
            return cap.get(1).map(|m| m.as_str().to_string());
        }

        None
    }

    /// Extract glob patterns
    pub fn extract_glob(input: &str) -> Option<String> {
        let glob_re = regex::Regex::new(r"(\*\.[\w]+|\*\*/\*\.[\w]+)").unwrap();
        glob_re.captures(input).and_then(|c| c.get(1).map(|m| m.as_str().to_string()))
    }
}

// =============================================================================
// WORKFLOW ENGINE - Pre-built command sequences
// =============================================================================

#[derive(Debug, Clone)]
pub struct WorkflowStep {
    pub command: String,
    pub description: String,
    pub capture_output: bool,
    pub fail_ok: bool,
}

#[derive(Debug, Clone)]
pub struct Workflow {
    pub task_type: TaskType,
    pub steps: Vec<WorkflowStep>,
}

pub struct WorkflowEngine {
    workflows: HashMap<TaskType, fn(&ParsedTask) -> Vec<WorkflowStep>>,
}

impl WorkflowEngine {
    pub fn new() -> Self {
        let mut workflows: HashMap<TaskType, fn(&ParsedTask) -> Vec<WorkflowStep>> = HashMap::new();

        workflows.insert(TaskType::FindFiles, |task| {
            let pattern = task.glob.as_deref().unwrap_or("*");
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![WorkflowStep {
                command: format!("find {} -name '{}' 2>/dev/null | head -50", dir, pattern),
                description: format!("Finding files matching {} in {}", pattern, dir),
                capture_output: true,
                fail_ok: true,
            }]
        });

        workflows.insert(TaskType::ReadFile, |task| {
            let path = task.paths.first().map(|s| s.as_str()).unwrap_or("");
            vec![WorkflowStep {
                command: format!("cat '{}'", path),
                description: format!("Reading {}", path),
                capture_output: true,
                fail_ok: false,
            }]
        });

        workflows.insert(TaskType::SearchText, |task| {
            let pattern = task.search_term.as_deref().unwrap_or("");
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![WorkflowStep {
                command: format!("grep -rn '{}' {} 2>/dev/null | head -50", pattern, dir),
                description: format!("Searching for '{}' in {}", pattern, dir),
                capture_output: true,
                fail_ok: true,
            }]
        });

        workflows.insert(TaskType::SearchFunction, |task| {
            let name = task.search_term.as_deref().unwrap_or("");
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![WorkflowStep {
                command: format!(
                    "grep -rn -E '(def |fn |func |function ){}' {} 2>/dev/null | head -20",
                    name, dir
                ),
                description: format!("Finding function {}", name),
                capture_output: true,
                fail_ok: true,
            }]
        });

        workflows.insert(TaskType::ListDirectory, |task| {
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![WorkflowStep {
                command: format!("ls -la {}", dir),
                description: format!("Listing {}", dir),
                capture_output: true,
                fail_ok: false,
            }]
        });

        workflows.insert(TaskType::GitStatus, |_| {
            vec![WorkflowStep {
                command: "git status".to_string(),
                description: "Checking git status".to_string(),
                capture_output: true,
                fail_ok: false,
            }]
        });

        workflows.insert(TaskType::GitDiff, |_| {
            vec![WorkflowStep {
                command: "git diff".to_string(),
                description: "Showing git diff".to_string(),
                capture_output: true,
                fail_ok: false,
            }]
        });

        workflows.insert(TaskType::GitLog, |_| {
            vec![WorkflowStep {
                command: "git log --oneline -20".to_string(),
                description: "Showing recent commits".to_string(),
                capture_output: true,
                fail_ok: false,
            }]
        });

        workflows.insert(TaskType::BuildProject, |task| {
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![
                WorkflowStep {
                    command: format!("cd {} && if [ -f Cargo.toml ]; then cargo build; elif [ -f package.json ]; then npm run build; elif [ -f Makefile ]; then make; fi", dir),
                    description: "Building project".to_string(),
                    capture_output: true,
                    fail_ok: false,
                }
            ]
        });

        workflows.insert(TaskType::RunTests, |task| {
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![
                WorkflowStep {
                    command: format!("cd {} && if [ -f Cargo.toml ]; then cargo test; elif [ -f package.json ]; then npm test; elif [ -f pytest.ini ] || [ -f setup.py ]; then pytest; fi", dir),
                    description: "Running tests".to_string(),
                    capture_output: true,
                    fail_ok: false,
                }
            ]
        });

        workflows.insert(TaskType::ListFunctions, |task| {
            let path = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![WorkflowStep {
                command: format!(
                    "grep -n -E '^[[:space:]]*(def |fn |func |function |pub fn |async fn |export function )' {} | head -50",
                    path
                ),
                description: format!("Listing functions in {}", path),
                capture_output: true,
                fail_ok: true,
            }]
        });

        workflows.insert(TaskType::ShowStructure, |task| {
            let dir = task.paths.first().map(|s| s.as_str()).unwrap_or(".");
            vec![WorkflowStep {
                command: format!(
                    "find {} -type f \\( -name '*.py' -o -name '*.rs' -o -name '*.js' -o -name '*.ts' \\) | head -100 | sort",
                    dir
                ),
                description: format!("Showing structure of {}", dir),
                capture_output: true,
                fail_ok: true,
            }]
        });

        Self { workflows }
    }

    pub fn get_workflow(&self, task: &ParsedTask) -> Option<Vec<WorkflowStep>> {
        self.workflows.get(&task.task_type).map(|f| f(task))
    }
}

// =============================================================================
// PARSED TASK - Result of classification + entity extraction
// =============================================================================

#[derive(Debug, Clone)]
pub struct ParsedTask {
    pub task_type: TaskType,
    pub confidence: f32,
    pub paths: Vec<String>,
    pub search_term: Option<String>,
    pub glob: Option<String>,
    pub raw_input: String,
}

// =============================================================================
// INTELLIGENCE ENGINE - The main orchestrator
// =============================================================================

pub struct IntelligenceEngine {
    classifier: KeywordClassifier,
    workflow_engine: WorkflowEngine,
}

impl IntelligenceEngine {
    pub fn new() -> Self {
        Self {
            classifier: KeywordClassifier::new(),
            workflow_engine: WorkflowEngine::new(),
        }
    }

    /// Parse user input into a structured task (no AI needed!)
    pub fn parse(&self, input: &str) -> ParsedTask {
        let (task_type, confidence) = self.classifier.classify(input);
        let paths = EntityExtractor::extract_paths(input);
        let search_term = EntityExtractor::extract_search_term(input);
        let glob = EntityExtractor::extract_glob(input);

        ParsedTask {
            task_type,
            confidence,
            paths,
            search_term,
            glob,
            raw_input: input.to_string(),
        }
    }

    /// Execute a parsed task
    pub fn execute(&self, task: &ParsedTask) -> Result<String, String> {
        let steps = self.workflow_engine.get_workflow(task)
            .ok_or_else(|| format!("No workflow for task type: {:?}", task.task_type))?;

        let mut output = String::new();

        for step in steps {
            output.push_str(&format!("→ {}\n", step.description));

            let result = Command::new("sh")
                .arg("-c")
                .arg(&step.command)
                .output();

            match result {
                Ok(out) => {
                    let stdout = String::from_utf8_lossy(&out.stdout);
                    let stderr = String::from_utf8_lossy(&out.stderr);

                    if step.capture_output {
                        if !stdout.is_empty() {
                            output.push_str(&stdout);
                        }
                        if !stderr.is_empty() && !out.status.success() {
                            output.push_str(&format!("Error: {}", stderr));
                        }
                    }

                    if !out.status.success() && !step.fail_ok {
                        return Err(format!("Step failed: {}", step.description));
                    }
                }
                Err(e) => {
                    if !step.fail_ok {
                        return Err(format!("Failed to execute: {}", e));
                    }
                }
            }
        }

        Ok(output)
    }

    /// One-shot: parse and execute
    pub fn run(&self, input: &str) -> Result<String, String> {
        let task = self.parse(input);

        if task.confidence < 0.1 {
            return Err(format!(
                "Could not understand: '{}'. Try being more specific.",
                input
            ));
        }

        self.execute(&task)
    }
}

// =============================================================================
// TINY MODEL ROUTER - Only used when keyword matching fails
// =============================================================================

pub struct TinyModelRouter {
    ollama_url: String,
    model: String,
}

impl TinyModelRouter {
    pub fn new(ollama_url: &str, model: &str) -> Self {
        Self {
            ollama_url: ollama_url.to_string(),
            model: model.to_string(),
        }
    }

    /// Ask tiny model to classify (only when keyword matching fails)
    pub async fn classify(&self, input: &str) -> Result<TaskType, String> {
        let prompt = format!(
            r#"Classify this request into ONE number (1-80):

1=find files, 2=read file, 11=search text, 12=search function, 41=git status, 42=git diff, 51=run command

Request: "{}"

Reply with ONLY the number:"#,
            input.chars().take(100).collect::<String>()
        );

        let client = reqwest::Client::new();
        let response = client
            .post(&format!("{}/api/generate", self.ollama_url))
            .json(&serde_json::json!({
                "model": self.model,
                "prompt": prompt,
                "stream": false,
                "options": {
                    "num_predict": 5,
                    "temperature": 0.0
                }
            }))
            .send()
            .await
            .map_err(|e| e.to_string())?;

        let json: serde_json::Value = response.json().await.map_err(|e| e.to_string())?;
        let text = json["response"].as_str().unwrap_or("255");

        // Extract number from response
        let num: u8 = text
            .chars()
            .filter(|c| c.is_ascii_digit())
            .collect::<String>()
            .parse()
            .unwrap_or(255);

        Ok(TaskType::from_id(num))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_keyword_classifier() {
        let classifier = KeywordClassifier::new();

        let (task, conf) = classifier.classify("find all python files");
        assert_eq!(task, TaskType::FindFiles);
        assert!(conf > 0.0);

        let (task, _) = classifier.classify("git status");
        assert_eq!(task, TaskType::GitStatus);

        let (task, _) = classifier.classify("find function main");
        assert_eq!(task, TaskType::SearchFunction);
    }

    #[test]
    fn test_entity_extractor() {
        let paths = EntityExtractor::extract_paths("read the file /tmp/test.py");
        assert!(paths.contains(&"/tmp/test.py".to_string()));

        let paths = EntityExtractor::extract_paths("find *.rs in ~/projects");
        assert!(paths.iter().any(|p| p.contains("projects")));

        let term = EntityExtractor::extract_search_term("search for 'hello world'");
        assert_eq!(term, Some("hello world".to_string()));
    }

    #[test]
    fn test_intelligence_engine() {
        let engine = IntelligenceEngine::new();

        let task = engine.parse("find all *.py files in /tmp");
        assert_eq!(task.task_type, TaskType::FindFiles);
        assert!(task.glob.is_some());

        let task = engine.parse("git status");
        assert_eq!(task.task_type, TaskType::GitStatus);
    }
}
