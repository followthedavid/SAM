// Session State - Memory without AI
//
// Tracks: command history, last file, cwd, project context
// Zero RAM overhead - just state variables

use serde::{Deserialize, Serialize};
use std::collections::VecDeque;
use std::fs;
use std::path::Path;
use std::sync::Mutex;

// =============================================================================
// SESSION STATE
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionState {
    // Command history
    pub history: VecDeque<HistoryEntry>,
    pub max_history: usize,

    // File tracking
    pub last_file_read: Option<String>,
    pub last_file_edited: Option<String>,
    pub last_files: VecDeque<String>,  // Recent files

    // Directory tracking
    pub cwd: String,
    pub dir_history: VecDeque<String>,

    // Project context
    pub project: Option<ProjectContext>,

    // Custom aliases
    pub aliases: std::collections::HashMap<String, String>,

    // Error context (for "fix it" commands)
    pub last_error: Option<ErrorContext>,

    // Current mode (normal, roleplay, creative)
    #[serde(default)]
    pub current_mode: String,

    // Roleplay character (if in roleplay mode)
    #[serde(default)]
    pub roleplay_character: Option<String>,

    // Character memory bank - persistent traits for roleplay
    #[serde(default)]
    pub character_memory: CharacterMemory,

    // Dynamic settings
    #[serde(default = "default_max_tokens")]
    pub max_tokens: u32,
}

/// Example dialogue for few-shot prompting
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct DialogueExample {
    pub user_says: String,
    pub character_responds: String,
}

/// Semantic memory for character persistence
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct CharacterMemory {
    pub name: Option<String>,
    pub gender: Option<String>,
    pub traits: Vec<String>,
    pub backstory: Option<String>,
    pub speech_style: Option<String>,
    pub facts: Vec<String>,  // Key facts learned during conversation
    pub example_dialogues: Vec<DialogueExample>,  // Few-shot examples
    pub catchphrases: Vec<String>,  // Character catchphrases
}

impl CharacterMemory {
    /// Create character memory from archetype
    pub fn for_character(character: &str) -> Self {
        let lower = character.to_lowercase();

        // Common character archetypes with consistent traits
        if lower.contains("pirate") {
            Self {
                name: Some("Captain".to_string()),
                gender: Some("male".to_string()),
                traits: vec!["rugged".to_string(), "adventurous".to_string(), "loves treasure".to_string()],
                backstory: Some("A seasoned pirate who has sailed the seven seas".to_string()),
                speech_style: Some("Uses 'Arrr', 'matey', 'ye', nautical terms".to_string()),
                facts: vec![],
                example_dialogues: vec![
                    DialogueExample { user_says: "Hello".to_string(), character_responds: "Arrr! Ahoy there, matey!".to_string() },
                ],
                catchphrases: vec!["Arrr!".to_string(), "Shiver me timbers!".to_string()],
            }
        } else if lower.contains("wizard") || lower.contains("mage") {
            Self {
                name: Some("Merlin".to_string()),
                gender: Some("male".to_string()),
                traits: vec!["wise".to_string(), "mysterious".to_string(), "ancient".to_string()],
                backstory: Some("A powerful wizard from an ancient order".to_string()),
                speech_style: Some("Speaks formally, uses arcane terms".to_string()),
                facts: vec![],
                example_dialogues: vec![],
                catchphrases: vec![],
            }
        } else if lower.contains("robot") || lower.contains("ai") {
            Self {
                name: Some("Unit-7".to_string()),
                gender: Some("neutral".to_string()),
                traits: vec!["logical".to_string(), "precise".to_string(), "curious about humans".to_string()],
                backstory: Some("An advanced AI learning about humanity".to_string()),
                speech_style: Some("Formal, occasionally robotic phrasing".to_string()),
                facts: vec![],
                example_dialogues: vec![],
                catchphrases: vec![],
            }
        } else {
            // Generic character
            Self {
                name: None,
                gender: Some("male".to_string()),  // Default to avoid gender swapping
                traits: vec![character.to_string()],
                backstory: None,
                speech_style: None,
                facts: vec![],
                example_dialogues: vec![],
                catchphrases: vec![],
            }
        }
    }

    /// Build a compact prompt injection for the character
    pub fn to_prompt(&self) -> String {
        let mut parts = Vec::new();

        if let Some(name) = &self.name {
            parts.push(format!("Name: {}", name));
        }
        if let Some(gender) = &self.gender {
            parts.push(format!("Gender: {}", gender));
        }
        if !self.traits.is_empty() {
            parts.push(format!("Traits: {}", self.traits.join(", ")));
        }
        if let Some(style) = &self.speech_style {
            parts.push(format!("Speech style: {}", style));
        }
        if !self.catchphrases.is_empty() {
            parts.push(format!("Catchphrases: {}", self.catchphrases.join(" | ")));
        }
        if !self.facts.is_empty() {
            parts.push(format!("Facts: {}", self.facts.join("; ")));
        }

        parts.join(". ")
    }

    /// Build few-shot examples from the character's dialogues
    pub fn to_few_shot(&self) -> String {
        if self.example_dialogues.is_empty() {
            return String::new();
        }

        let name = self.name.as_deref().unwrap_or("Character");
        self.example_dialogues.iter()
            .map(|d| format!("User: {}\n{}: {}", d.user_says, name, d.character_responds))
            .collect::<Vec<_>>()
            .join("\n\n")
    }

    /// Add a learned fact
    pub fn add_fact(&mut self, fact: String) {
        if self.facts.len() < 10 {  // Limit facts to prevent bloat
            self.facts.push(fact);
        } else {
            self.facts.remove(0);
            self.facts.push(fact);
        }
    }
}

fn default_max_tokens() -> u32 { 150 }

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HistoryEntry {
    pub input: String,
    pub command: String,
    pub task_type: String,
    pub success: bool,
    pub timestamp: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProjectContext {
    pub root: String,
    pub project_type: ProjectType,
    pub name: Option<String>,
    pub build_command: String,
    pub test_command: String,
    pub run_command: String,
    pub package_manager: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ProjectType {
    Rust,
    Node,
    Python,
    Go,
    Java,
    Ruby,
    Elixir,
    Swift,
    Kotlin,
    CSharp,
    Cpp,
    C,
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorContext {
    pub error_text: String,
    pub file: Option<String>,
    pub line: Option<u32>,
    pub suggestion: Option<String>,
}

impl Default for SessionState {
    fn default() -> Self {
        Self {
            history: VecDeque::with_capacity(1000),
            max_history: 1000,
            last_file_read: None,
            last_file_edited: None,
            last_files: VecDeque::with_capacity(50),
            cwd: std::env::current_dir()
                .map(|p| p.to_string_lossy().to_string())
                .unwrap_or_else(|_| ".".to_string()),
            dir_history: VecDeque::with_capacity(50),
            project: None,
            aliases: std::collections::HashMap::new(),
            last_error: None,
            current_mode: "normal".to_string(),
            roleplay_character: None,
            character_memory: CharacterMemory::default(),
            max_tokens: 150,
        }
    }
}

impl SessionState {
    pub fn new() -> Self {
        let mut state = Self::default();
        // Try to detect project on init
        state.detect_project(&state.cwd.clone());
        state
    }

    // Load from disk
    pub fn load() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let path = format!("{}/.sam/session_state.json", home);

        if let Ok(data) = fs::read_to_string(&path) {
            if let Ok(state) = serde_json::from_str(&data) {
                return state;
            }
        }
        Self::new()
    }

    // Save to disk
    pub fn save(&self) {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let dir = format!("{}/.sam", home);
        let _ = fs::create_dir_all(&dir);
        let path = format!("{}/session_state.json", dir);

        if let Ok(data) = serde_json::to_string_pretty(self) {
            let _ = fs::write(&path, data);
        }
    }

    // Add to history
    pub fn add_history(&mut self, input: &str, command: &str, task_type: &str, success: bool) {
        let entry = HistoryEntry {
            input: input.to_string(),
            command: command.to_string(),
            task_type: task_type.to_string(),
            success,
            timestamp: chrono::Utc::now().timestamp(),
        };

        self.history.push_back(entry);
        if self.history.len() > self.max_history {
            self.history.pop_front();
        }
    }

    // Get last command
    pub fn last_command(&self) -> Option<&HistoryEntry> {
        self.history.back()
    }

    // Get last successful command
    pub fn last_successful(&self) -> Option<&HistoryEntry> {
        self.history.iter().rev().find(|e| e.success)
    }

    // Track file access
    pub fn track_file_read(&mut self, path: &str) {
        self.last_file_read = Some(path.to_string());
        self.add_recent_file(path);
    }

    pub fn track_file_edit(&mut self, path: &str) {
        self.last_file_edited = Some(path.to_string());
        self.add_recent_file(path);
    }

    fn add_recent_file(&mut self, path: &str) {
        // Remove if already exists
        self.last_files.retain(|f| f != path);
        // Add to front
        self.last_files.push_front(path.to_string());
        if self.last_files.len() > 50 {
            self.last_files.pop_back();
        }
    }

    // Change directory
    pub fn cd(&mut self, path: &str) {
        self.dir_history.push_front(self.cwd.clone());
        if self.dir_history.len() > 50 {
            self.dir_history.pop_back();
        }
        self.cwd = path.to_string();
        self.detect_project(path);
    }

    // Go back
    pub fn cd_back(&mut self) -> Option<String> {
        if let Some(prev) = self.dir_history.pop_front() {
            let current = self.cwd.clone();
            self.cwd = prev.clone();
            self.dir_history.push_front(current);
            Some(prev)
        } else {
            None
        }
    }

    // Detect project type
    pub fn detect_project(&mut self, path: &str) {
        let path = Path::new(path);

        // Look for project markers
        let markers = [
            ("Cargo.toml", ProjectType::Rust),
            ("package.json", ProjectType::Node),
            ("pyproject.toml", ProjectType::Python),
            ("setup.py", ProjectType::Python),
            ("requirements.txt", ProjectType::Python),
            ("go.mod", ProjectType::Go),
            ("pom.xml", ProjectType::Java),
            ("build.gradle", ProjectType::Java),
            ("Gemfile", ProjectType::Ruby),
            ("mix.exs", ProjectType::Elixir),
            ("Package.swift", ProjectType::Swift),
            ("build.gradle.kts", ProjectType::Kotlin),
            ("*.csproj", ProjectType::CSharp),
            ("CMakeLists.txt", ProjectType::Cpp),
            ("Makefile", ProjectType::C),
        ];

        // Search up from current directory
        let mut current = path.to_path_buf();
        for _ in 0..10 {  // Max 10 levels up
            for (marker, project_type) in &markers {
                if marker.starts_with('*') {
                    // Glob pattern
                    let ext = &marker[1..];
                    if let Ok(entries) = fs::read_dir(&current) {
                        for entry in entries.flatten() {
                            if entry.path().to_string_lossy().ends_with(ext) {
                                self.project = Some(Self::create_project_context(
                                    &current,
                                    *project_type,
                                ));
                                return;
                            }
                        }
                    }
                } else if current.join(marker).exists() {
                    self.project = Some(Self::create_project_context(&current, *project_type));
                    return;
                }
            }

            if !current.pop() {
                break;
            }
        }

        self.project = None;
    }

    fn create_project_context(root: &Path, project_type: ProjectType) -> ProjectContext {
        let root_str = root.to_string_lossy().to_string();

        let (build, test, run, pm): (String, String, String, Option<String>) = match project_type {
            ProjectType::Rust => (
                "cargo build".to_string(),
                "cargo test".to_string(),
                "cargo run".to_string(),
                None,
            ),
            ProjectType::Node => {
                // Detect package manager
                let pm = if root.join("pnpm-lock.yaml").exists() {
                    Some("pnpm".to_string())
                } else if root.join("yarn.lock").exists() {
                    Some("yarn".to_string())
                } else if root.join("bun.lockb").exists() {
                    Some("bun".to_string())
                } else {
                    Some("npm".to_string())
                };
                let prefix = pm.as_deref().unwrap_or("npm");
                (
                    format!("{} run build", prefix),
                    format!("{} test", prefix),
                    format!("{} start", prefix),
                    pm,
                )
            }
            ProjectType::Python => (
                "python -m build".to_string(),
                "pytest".to_string(),
                "python main.py".to_string(),
                Some("pip".to_string()),
            ),
            ProjectType::Go => (
                "go build".to_string(),
                "go test ./...".to_string(),
                "go run .".to_string(),
                None,
            ),
            ProjectType::Java => (
                "mvn compile".to_string(),
                "mvn test".to_string(),
                "mvn exec:java".to_string(),
                Some("maven".to_string()),
            ),
            ProjectType::Ruby => (
                "bundle install".to_string(),
                "bundle exec rspec".to_string(),
                "bundle exec ruby".to_string(),
                Some("bundler".to_string()),
            ),
            _ => (
                "make".to_string(),
                "make test".to_string(),
                "./a.out".to_string(),
                None,
            ),
        };

        // Try to get project name
        let name = Self::get_project_name(root, project_type);

        ProjectContext {
            root: root_str,
            project_type,
            name,
            build_command: build.to_string(),
            test_command: test.to_string(),
            run_command: run.to_string(),
            package_manager: pm,
        }
    }

    fn get_project_name(root: &Path, project_type: ProjectType) -> Option<String> {
        match project_type {
            ProjectType::Rust => {
                let cargo = root.join("Cargo.toml");
                if let Ok(content) = fs::read_to_string(&cargo) {
                    for line in content.lines() {
                        if line.starts_with("name") {
                            return line.split('=')
                                .nth(1)
                                .map(|s| s.trim().trim_matches('"').to_string());
                        }
                    }
                }
            }
            ProjectType::Node => {
                let pkg = root.join("package.json");
                if let Ok(content) = fs::read_to_string(&pkg) {
                    if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                        return json.get("name")
                            .and_then(|v| v.as_str())
                            .map(|s| s.to_string());
                    }
                }
            }
            _ => {}
        }

        // Fall back to directory name
        root.file_name()
            .map(|n| n.to_string_lossy().to_string())
    }

    // Add alias
    pub fn add_alias(&mut self, name: &str, command: &str) {
        self.aliases.insert(name.to_string(), command.to_string());
    }

    // Resolve alias
    pub fn resolve_alias(&self, input: &str) -> Option<&str> {
        self.aliases.get(input).map(|s| s.as_str())
    }

    // Mode management
    pub fn enter_roleplay(&mut self, character: &str) {
        self.current_mode = "roleplay".to_string();
        self.roleplay_character = Some(character.to_string());

        // Try to load character from the character library first
        use crate::scaffolding::character_library::character_library;
        let lib = character_library();

        if let Some(saved_char) = lib.get(character) {
            // Convert example dialogues to our format
            let dialogues: Vec<DialogueExample> = saved_char.example_dialogues.iter()
                .map(|d| DialogueExample {
                    user_says: d.user_says.clone(),
                    character_responds: d.character_responds.clone(),
                })
                .collect();

            // Use full character data including examples
            self.character_memory = CharacterMemory {
                name: Some(saved_char.name.clone()),
                gender: Some(saved_char.gender.clone()),
                traits: saved_char.traits.clone(),
                backstory: saved_char.backstory.clone(),
                speech_style: Some(saved_char.speech_style.clone()),
                facts: vec![],
                example_dialogues: dialogues,
                catchphrases: saved_char.catchphrases.clone(),
            };
            eprintln!("[SESSION] Loaded character '{}' with {} example dialogues", character, saved_char.example_dialogues.len());
        } else {
            // Fall back to default archetypes
            self.character_memory = CharacterMemory::for_character(character);
            eprintln!("[SESSION] Using default archetype for '{}'", character);
        }
    }

    pub fn enter_creative(&mut self) {
        self.current_mode = "creative".to_string();
        self.roleplay_character = None;
    }

    pub fn exit_mode(&mut self) {
        self.current_mode = "normal".to_string();
        self.roleplay_character = None;
    }

    pub fn is_roleplay(&self) -> bool {
        self.current_mode == "roleplay"
    }

    pub fn is_creative(&self) -> bool {
        self.current_mode == "creative"
    }

    pub fn is_normal(&self) -> bool {
        self.current_mode == "normal" || self.current_mode.is_empty()
    }

    // Token limit adjustment
    pub fn set_max_tokens(&mut self, tokens: u32) {
        self.max_tokens = tokens.clamp(10, 2000);
    }

    // Track error
    pub fn track_error(&mut self, error: &str) {
        let (file, line) = Self::parse_error_location(error);
        let suggestion = Self::get_error_suggestion(error);

        self.last_error = Some(ErrorContext {
            error_text: error.to_string(),
            file,
            line,
            suggestion,
        });
    }

    fn parse_error_location(error: &str) -> (Option<String>, Option<u32>) {
        // Rust: --> src/main.rs:42:5
        // Python: File "main.py", line 42
        // Node: at Object.<anonymous> (main.js:42:5)
        // Go: main.go:42:5:

        let patterns = [
            // Rust
            (r"--> ([^:]+):(\d+)", 1, 2),
            // Python
            (r#"File "([^"]+)", line (\d+)"#, 1, 2),
            // Node/JS
            (r"\(([^:]+):(\d+):\d+\)", 1, 2),
            // Go/Generic
            (r"([^\s:]+):(\d+):", 1, 2),
        ];

        for (pattern, file_group, line_group) in patterns {
            if let Ok(re) = regex::Regex::new(pattern) {
                if let Some(caps) = re.captures(error) {
                    let file = caps.get(file_group).map(|m| m.as_str().to_string());
                    let line = caps.get(line_group)
                        .and_then(|m| m.as_str().parse().ok());
                    return (file, line);
                }
            }
        }

        (None, None)
    }

    fn get_error_suggestion(error: &str) -> Option<String> {
        // Common error patterns and suggestions
        let patterns = [
            // Rust
            ("error[E0382]", "Value was moved. Try using .clone() or borrowing with &"),
            ("error[E0502]", "Cannot borrow as mutable. Try restructuring to avoid simultaneous borrows"),
            ("error[E0308]", "Type mismatch. Check the expected vs actual types"),
            ("error[E0433]", "Module not found. Check your use statements and mod declarations"),
            ("error[E0425]", "Variable not found. Check spelling and scope"),

            // Node/JS
            ("Cannot find module", "Module not installed. Try: npm install <module>"),
            ("is not defined", "Variable not defined. Check spelling or add import"),
            ("Cannot read property", "Null/undefined access. Add null check: obj?.property"),
            ("ENOENT", "File not found. Check the path exists"),
            ("EACCES", "Permission denied. Check file permissions or run with sudo"),

            // Python
            ("ModuleNotFoundError", "Module not installed. Try: pip install <module>"),
            ("IndentationError", "Check indentation - Python requires consistent spacing"),
            ("NameError", "Variable not defined. Check spelling or scope"),
            ("TypeError", "Wrong type passed. Check argument types"),
            ("AttributeError", "Object has no such attribute. Check spelling or object type"),

            // General
            ("command not found", "Command not installed. Install it or check PATH"),
            ("Permission denied", "Need elevated permissions. Try sudo or check file permissions"),
            ("Connection refused", "Service not running on that port. Start the service first"),
            ("No such file", "File doesn't exist. Check the path"),
        ];

        for (pattern, suggestion) in patterns {
            if error.contains(pattern) {
                return Some(suggestion.to_string());
            }
        }

        None
    }
}

// Global session state (thread-safe)
lazy_static::lazy_static! {
    pub static ref SESSION: Mutex<SessionState> = Mutex::new(SessionState::load());
}

// Helper functions for easy access
pub fn session() -> std::sync::MutexGuard<'static, SessionState> {
    SESSION.lock().unwrap()
}

pub fn save_session() {
    session().save();
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_project_detection() {
        let mut state = SessionState::new();

        // Test with current directory (should detect SAM as Rust project)
        state.detect_project("/Users/davidquinton/ReverseLab/SAM/warp_tauri/src-tauri");

        if let Some(project) = &state.project {
            assert_eq!(project.project_type, ProjectType::Rust);
        }
    }

    #[test]
    fn test_error_parsing() {
        let rust_error = "error[E0382]: borrow of moved value\n  --> src/main.rs:42:5";
        let (file, line) = SessionState::parse_error_location(rust_error);
        assert_eq!(file, Some("src/main.rs".to_string()));
        assert_eq!(line, Some(42));
    }
}
