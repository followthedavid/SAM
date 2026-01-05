// Hybrid Router - Orchestration Layer (Option 1)
//
// Decides the optimal path for each request:
// 1. Keyword/deterministic match (instant, no AI)
// 2. Template + fill-in (minimal AI)
// 3. Embedding search (semantic, no generation)
// 4. Micro-model generation (full AI, smallest model)
//
// Goal: Handle 80%+ of requests without heavy LLM usage

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// =============================================================================
// REQUEST CLASSIFICATION
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum RequestType {
    // No AI needed - handled by intelligence_v2
    ShellCommand,           // "list files", "git status"
    FileOperation,          // "read config.rs", "delete temp/"
    Navigation,             // "go to src/", "open main.rs"

    // Template + minimal AI
    CodeGeneration,         // "create a react component"
    TestGeneration,         // "write tests for login"
    BoilerplateGeneration,  // "add api endpoint"

    // Embedding search (semantic, no generation)
    CodeSearch,             // "where is auth handled?"
    Explanation,            // "what does this function do?"
    Documentation,          // "how does the cache work?"

    // Full AI required
    BugFix,                 // "fix the null pointer error"
    Refactor,               // "refactor this to use async"
    CodeReview,             // "review this PR"
    ComplexGeneration,      // "implement a rate limiter"

    // === EXTERNAL SERVICE ROUTING ===
    // Media commands
    MediaPlayback,          // "play X", "stream Y"
    MediaDownload,          // "download movie X", "get album Y"
    MediaSearch,            // "find scenes with X", "search music"
    MediaManagement,        // "tag album", "organize library"

    // Creative AI
    ImageGeneration,        // "generate image of X"
    VoiceSynthesis,         // "say X in voice Y"
    CreativeWriting,        // "write a story about X"

    // External AI routing
    ChatGPTTask,            // Creative, conversational, drafts
    CursorTask,             // Code editing in Cursor
    ClaudeTask,             // Complex reasoning (this system)

    // Unknown - needs classification
    Unknown,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ProcessingPath {
    Deterministic,      // Use intelligence_v2, no AI
    TemplateWithFill,   // Use template, small AI fill
    EmbeddingSearch,    // Semantic search, no generation
    Conversational,     // Simple chat, no tools needed
    MicroModel,         // Small specialized model (Ollama)
    FullModel,          // Larger model for complex tasks

    // === EXTERNAL AI BROWSER BRIDGES ===
    ChatGPT,            // Route to ChatGPT via browser bridge
    ClaudeBrowser,      // Route to Claude via browser bridge

    // === EXTERNAL SERVICE PATHS ===
    Cursor,             // Open in Cursor editor
    ComfyUI,            // Image generation pipeline
    VoiceAI,            // TTS + RVC pipeline

    // === MEDIA SERVICE PATHS ===
    PlexAPI,            // Plex media server
    NavidromeAPI,       // Music streaming
    StashAPI,           // Stash GraphQL
    ArrAPI,             // Radarr/Sonarr/Lidarr
    TorrentAPI,         // qBittorrent
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RoutingDecision {
    pub request_type: RequestType,
    pub processing_path: ProcessingPath,
    pub model_recommendation: Option<String>,
    pub template_name: Option<String>,
    pub confidence: f32,
    pub reasoning: String,
}

// =============================================================================
// HYBRID ROUTER
// =============================================================================

pub struct HybridRouter {
    // Keyword patterns for classification
    deterministic_patterns: Vec<(&'static str, RequestType)>,
    template_patterns: Vec<(&'static str, RequestType)>,
    search_patterns: Vec<(&'static str, RequestType)>,
    ai_patterns: Vec<(&'static str, RequestType)>,
}

impl HybridRouter {
    pub fn new() -> Self {
        Self {
            deterministic_patterns: Self::build_deterministic_patterns(),
            template_patterns: Self::build_template_patterns(),
            search_patterns: Self::build_search_patterns(),
            ai_patterns: Self::build_ai_patterns(),
        }
    }

    // Main routing function
    pub fn route(&self, request: &str) -> RoutingDecision {
        let lower = request.to_lowercase();

        // Priority 1: Check for deterministic (no AI needed)
        if let Some((req_type, confidence)) = self.match_deterministic(&lower) {
            return RoutingDecision {
                request_type: req_type.clone(),
                processing_path: ProcessingPath::Deterministic,
                model_recommendation: None,
                template_name: None,
                confidence,
                reasoning: "Matched deterministic pattern - no AI needed".to_string(),
            };
        }

        // Priority 2: Check for conversational/status queries EARLY
        // (before search, so "daily brief" doesn't match code search patterns)
        if Self::is_conversational(&lower) {
            return RoutingDecision {
                request_type: RequestType::Unknown,
                processing_path: ProcessingPath::Conversational,
                model_recommendation: Some("qwen2.5-coder:1.5b".to_string()),
                template_name: None,
                confidence: 0.9,
                reasoning: "Conversational/status message - no tools needed".to_string(),
            };
        }

        // Priority 3: Check for template-based generation
        if let Some((req_type, template, confidence)) = self.match_template(&lower) {
            return RoutingDecision {
                request_type: req_type.clone(),
                processing_path: ProcessingPath::TemplateWithFill,
                model_recommendation: Some("qwen2.5-coder:1.5b".to_string()),
                template_name: Some(template.to_string()),
                confidence,
                reasoning: "Template available - minimal AI for fill-in".to_string(),
            };
        }

        // Priority 4: Check for search/explanation (embedding)
        if let Some((req_type, confidence)) = self.match_search(&lower) {
            return RoutingDecision {
                request_type: req_type.clone(),
                processing_path: ProcessingPath::EmbeddingSearch,
                model_recommendation: None,
                template_name: None,
                confidence,
                reasoning: "Semantic search - embeddings only, no generation".to_string(),
            };
        }

        // Priority 4: Check for AI-required tasks
        if let Some((req_type, model, confidence)) = self.match_ai(&lower) {
            // Check if task exceeds local model capabilities
            // Privacy check - if user wants privacy, use local models only
            let wants_privacy = lower.contains("private") || lower.contains("privately") || lower.contains("local");

            let (path, reasoning) = if wants_privacy {
                // Check if this is a conversational/creative request that wants privacy
                if Self::is_creative_or_conversational(&lower) {
                    (ProcessingPath::Conversational, "Private conversational mode - local model only".to_string())
                } else {
                    // Override external AI - use local Ollama for privacy
                    (ProcessingPath::MicroModel, "Private mode - using local model only".to_string())
                }
            } else if Self::requires_claude(&lower) {
                (ProcessingPath::ClaudeBrowser, "Complex reasoning - routing to Claude".to_string())
            } else if Self::requires_chatgpt(&lower) {
                (ProcessingPath::ChatGPT, "Creative/conversational task - routing to ChatGPT".to_string())
            } else if Self::is_complex(&lower) {
                (ProcessingPath::FullModel, "Complex task - using full model".to_string())
            } else {
                (ProcessingPath::MicroModel, "AI generation required".to_string())
            };

            return RoutingDecision {
                request_type: req_type.clone(),
                processing_path: path,
                model_recommendation: Some(model.to_string()),
                template_name: None,
                confidence,
                reasoning,
            };
        }

        // Default: Unknown, use micro model for classification
        RoutingDecision {
            request_type: RequestType::Unknown,
            processing_path: ProcessingPath::MicroModel,
            model_recommendation: Some("qwen2.5-coder:1.5b".to_string()),
            template_name: None,
            confidence: 0.3,
            reasoning: "Could not classify - using micro model".to_string(),
        }
    }

    // Check if request is creative or conversational (roleplay, chat, stories)
    // Used to ensure private creative requests get Conversational path, not MicroModel
    fn is_creative_or_conversational(request: &str) -> bool {
        let creative_patterns = [
            // Roleplay & creative
            "roleplay", "role play", "pretend", "imagine", "story",
            "chat", "talk", "conversation", "discuss", "tell me",
            // Character/persona
            "be my", "act as", "you are", "pretend you're",
            // Creative writing
            "write me", "create a story", "poem", "script",
            // General conversation
            "let's", "can we", "would you", "could you",
            "help me", "i want to", "i need",
        ];

        creative_patterns.iter().any(|p| request.contains(p))
    }

    // Check if request is conversational (greetings, casual chat, simple questions)
    fn is_conversational(request: &str) -> bool {
        let conversational_patterns = [
            // Greetings
            "hi", "hello", "hey", "howdy", "sup", "yo",
            "good morning", "good afternoon", "good evening",
            "what's up", "how are you", "how's it going",
            // Simple questions about SAM
            "who are you", "what are you", "what can you do",
            "what is sam", "tell me about yourself",
            // Thanks/Acknowledgments
            "thanks", "thank you", "thx", "ty",
            "got it", "ok", "okay", "cool", "nice",
            // Farewells
            "bye", "goodbye", "see you", "later", "cya",
            // Meta/Status questions (don't use tools for these)
            "daily brief", "what needs attention", "show my progress",
            "status update", "what's pending", "summary", "overview",
            "what did i accomplish", "what have i done", "my projects",
            "priorities", "what should i focus",
        ];

        // Check if the request matches conversational patterns
        // For status/brief queries, be more lenient with length
        let word_count = request.split_whitespace().count();
        let matches_pattern = conversational_patterns.iter().any(|p| request.contains(p));

        // Status queries can be longer (up to 15 words)
        // Greetings should be short (up to 8 words)
        let is_status_query = request.contains("brief") ||
                              request.contains("status") ||
                              request.contains("progress") ||
                              request.contains("attention") ||
                              request.contains("summary");

        let length_ok = if is_status_query {
            word_count <= 15
        } else {
            word_count <= 8
        };

        length_ok && matches_pattern
    }

    // Check if request is complex (needs larger model)
    fn is_complex(request: &str) -> bool {
        let complex_indicators = [
            "refactor", "redesign", "architect", "optimize",
            "implement from scratch", "build a complete",
            "complex", "advanced", "sophisticated",
            "multiple files", "entire", "whole system",
        ];

        complex_indicators.iter().any(|ind| request.contains(ind))
    }

    // Check if request requires Claude (complex reasoning, analysis, planning)
    fn requires_claude(request: &str) -> bool {
        let claude_indicators = [
            // Deep analysis
            "analyze in depth", "deep dive", "thorough analysis",
            "explain why", "root cause", "investigate",
            // Architecture & planning
            "design a system", "plan the implementation", "architect",
            "create a plan", "strategy for", "approach to",
            // Multi-step reasoning
            "step by step", "break down", "systematically",
            "consider all", "evaluate options", "compare approaches",
            // Code review & understanding
            "review this code", "what's wrong with", "improve this",
            "security audit", "performance analysis",
            // Long-form generation
            "write documentation", "create a guide", "explain everything",
        ];

        // Also check length - very long requests often need Claude
        let is_long = request.split_whitespace().count() > 50;

        claude_indicators.iter().any(|ind| request.contains(ind)) || is_long
    }

    // Check if request requires ChatGPT (creative, conversational, brainstorming)
    fn requires_chatgpt(request: &str) -> bool {
        let chatgpt_indicators = [
            // Creative tasks
            "write a story", "creative", "brainstorm",
            "come up with ideas", "imagine", "roleplay",
            // Conversational
            "let's discuss", "what do you think", "your opinion",
            "help me understand", "explain like",
            // Content creation
            "write an email", "draft a message", "compose",
            "marketing copy", "blog post", "social media",
            // General knowledge
            "what is", "who is", "history of", "tell me about",
        ];

        chatgpt_indicators.iter().any(|ind| request.contains(ind))
    }

    // ==========================================================================
    // Pattern Matching
    // ==========================================================================

    fn match_deterministic(&self, request: &str) -> Option<(RequestType, f32)> {
        for (pattern, req_type) in &self.deterministic_patterns {
            if request.contains(pattern) {
                return Some((req_type.clone(), 0.95));
            }
        }
        None
    }

    fn match_template(&self, request: &str) -> Option<(RequestType, &'static str, f32)> {
        // Template patterns with their template names - using slices for variable-length patterns
        let templates: &[(&[&str], &str, &str)] = &[
            // React - more flexible patterns
            (&["react component", "create component", "new component", "make component"], "CodeGeneration", "react_component"),
            (&["create hook", "new hook", "custom hook", "react hook"], "CodeGeneration", "react_hook"),

            // API
            (&["create endpoint", "add endpoint", "new api", "rest endpoint", "api endpoint"], "BoilerplateGeneration", "api_endpoint"),
            (&["create route", "add route", "new route"], "BoilerplateGeneration", "api_route"),

            // Tests
            (&["write test", "add test", "create test", "unit test", "test for"], "TestGeneration", "unit_test"),
            (&["integration test", "e2e test", "end to end"], "TestGeneration", "integration_test"),

            // Rust
            (&["create struct", "new struct", "rust struct", "a struct"], "CodeGeneration", "rust_struct"),
            (&["create enum", "new enum", "rust enum", "an enum"], "CodeGeneration", "rust_enum"),
            (&["impl block", "implement trait", "impl trait"], "CodeGeneration", "rust_impl"),

            // Python
            (&["create class", "python class", "new class", "a class"], "CodeGeneration", "python_class"),
            (&["create function", "python function", "def ", "a function"], "CodeGeneration", "python_function"),

            // TypeScript
            (&["create interface", "typescript interface", "ts interface", "an interface"], "CodeGeneration", "ts_interface"),
            (&["create type", "typescript type", "ts type"], "CodeGeneration", "ts_type"),

            // General
            (&["create module", "new module", "add module"], "BoilerplateGeneration", "module"),
            (&["create config", "configuration file", "config file"], "BoilerplateGeneration", "config"),
            (&["dockerfile", "docker compose", "docker file"], "BoilerplateGeneration", "docker"),
            (&["github action", "ci pipeline", "workflow file"], "BoilerplateGeneration", "ci_pipeline"),
        ];

        for (patterns, req_type_str, template_name) in templates {
            for pattern in *patterns {
                if request.contains(pattern) {
                    let req_type = match *req_type_str {
                        "CodeGeneration" => RequestType::CodeGeneration,
                        "TestGeneration" => RequestType::TestGeneration,
                        "BoilerplateGeneration" => RequestType::BoilerplateGeneration,
                        _ => RequestType::CodeGeneration,
                    };
                    return Some((req_type, template_name, 0.85));
                }
            }
        }
        None
    }

    fn match_search(&self, request: &str) -> Option<(RequestType, f32)> {
        for (pattern, req_type) in &self.search_patterns {
            if request.contains(pattern) {
                return Some((req_type.clone(), 0.9));
            }
        }
        None
    }

    fn match_ai(&self, request: &str) -> Option<(RequestType, &'static str, f32)> {
        for (pattern, req_type) in &self.ai_patterns {
            if request.contains(pattern) {
                // Use 1.5b for all tasks (only installed coder model)
                let model = "qwen2.5-coder:1.5b";
                return Some((req_type.clone(), model, 0.8));
            }
        }
        None
    }

    // ==========================================================================
    // Pattern Builders
    // ==========================================================================

    fn build_deterministic_patterns() -> Vec<(&'static str, RequestType)> {
        vec![
            // Shell commands (handled by intelligence_v2)
            ("list files", RequestType::ShellCommand),
            ("show files", RequestType::ShellCommand),
            ("git status", RequestType::ShellCommand),
            ("git log", RequestType::ShellCommand),
            ("git diff", RequestType::ShellCommand),
            ("git branch", RequestType::ShellCommand),
            ("git commit", RequestType::ShellCommand),
            ("git push", RequestType::ShellCommand),
            ("git pull", RequestType::ShellCommand),
            ("run build", RequestType::ShellCommand),
            ("run test", RequestType::ShellCommand),
            ("npm install", RequestType::ShellCommand),
            ("cargo build", RequestType::ShellCommand),
            ("cargo test", RequestType::ShellCommand),
            ("docker ps", RequestType::ShellCommand),
            ("docker build", RequestType::ShellCommand),
            ("kill process", RequestType::ShellCommand),
            ("find process", RequestType::ShellCommand),

            // File operations
            ("read file", RequestType::FileOperation),
            ("open file", RequestType::FileOperation),
            ("delete file", RequestType::FileOperation),
            ("create directory", RequestType::FileOperation),
            ("move file", RequestType::FileOperation),
            ("copy file", RequestType::FileOperation),
            ("rename file", RequestType::FileOperation),

            // Navigation
            ("go to", RequestType::Navigation),
            ("navigate to", RequestType::Navigation),
            ("open folder", RequestType::Navigation),
            ("cd ", RequestType::Navigation),
        ]
    }

    fn build_template_patterns() -> Vec<(&'static str, RequestType)> {
        vec![
            ("create component", RequestType::CodeGeneration),
            ("create hook", RequestType::CodeGeneration),
            ("create endpoint", RequestType::BoilerplateGeneration),
            ("create test", RequestType::TestGeneration),
            ("write test", RequestType::TestGeneration),
            ("add test", RequestType::TestGeneration),
        ]
    }

    fn build_search_patterns() -> Vec<(&'static str, RequestType)> {
        vec![
            // Search patterns
            ("where is", RequestType::CodeSearch),
            ("where does", RequestType::CodeSearch),
            ("find where", RequestType::CodeSearch),
            ("locate", RequestType::CodeSearch),
            ("search for", RequestType::CodeSearch),

            // Explanation patterns
            ("what does", RequestType::Explanation),
            ("what is", RequestType::Explanation),
            ("how does", RequestType::Explanation),
            ("explain", RequestType::Explanation),
            ("understand", RequestType::Explanation),

            // Documentation patterns
            ("how to", RequestType::Documentation),
            ("how do i", RequestType::Documentation),
            ("show me how", RequestType::Documentation),
            ("document", RequestType::Documentation),
        ]
    }

    fn build_ai_patterns() -> Vec<(&'static str, RequestType)> {
        vec![
            // Bug fix
            ("fix", RequestType::BugFix),
            ("debug", RequestType::BugFix),
            ("error", RequestType::BugFix),
            ("bug", RequestType::BugFix),
            ("broken", RequestType::BugFix),
            ("not working", RequestType::BugFix),
            ("issue", RequestType::BugFix),

            // Refactor
            ("refactor", RequestType::Refactor),
            ("improve", RequestType::Refactor),
            ("optimize", RequestType::Refactor),
            ("clean up", RequestType::Refactor),
            ("simplify", RequestType::Refactor),

            // Code review
            ("review", RequestType::CodeReview),
            ("check this", RequestType::CodeReview),
            ("look at", RequestType::CodeReview),
            ("feedback", RequestType::CodeReview),

            // Complex generation
            ("implement", RequestType::ComplexGeneration),
            ("build", RequestType::ComplexGeneration),
            ("design", RequestType::ComplexGeneration),
            ("architect", RequestType::ComplexGeneration),

            // === MEDIA COMMANDS ===
            ("play", RequestType::MediaPlayback),
            ("stream", RequestType::MediaPlayback),
            ("watch", RequestType::MediaPlayback),
            ("listen to", RequestType::MediaPlayback),

            ("download movie", RequestType::MediaDownload),
            ("download album", RequestType::MediaDownload),
            ("download song", RequestType::MediaDownload),
            ("get movie", RequestType::MediaDownload),
            ("get album", RequestType::MediaDownload),

            ("find scene", RequestType::MediaSearch),
            ("search plex", RequestType::MediaSearch),
            ("search music", RequestType::MediaSearch),
            ("find performer", RequestType::MediaSearch),

            ("tag album", RequestType::MediaManagement),
            ("organize library", RequestType::MediaManagement),
            ("scan library", RequestType::MediaManagement),

            // === CREATIVE AI ===
            ("generate image", RequestType::ImageGeneration),
            ("create image", RequestType::ImageGeneration),
            ("draw", RequestType::ImageGeneration),
            ("make picture", RequestType::ImageGeneration),

            ("say in voice", RequestType::VoiceSynthesis),
            ("speak as", RequestType::VoiceSynthesis),
            ("voice clone", RequestType::VoiceSynthesis),

            ("write story", RequestType::CreativeWriting),
            ("write poem", RequestType::CreativeWriting),
            ("creative", RequestType::CreativeWriting),

            // === EXTERNAL AI ROUTING ===
            ("ask chatgpt", RequestType::ChatGPTTask),
            ("chatgpt", RequestType::ChatGPTTask),
            ("gpt", RequestType::ChatGPTTask),

            ("open in cursor", RequestType::CursorTask),
            ("edit in cursor", RequestType::CursorTask),
            ("cursor", RequestType::CursorTask),
        ]
    }

    // Map RequestType to ProcessingPath for external services
    pub fn get_external_path(request_type: &RequestType) -> Option<ProcessingPath> {
        match request_type {
            RequestType::MediaPlayback | RequestType::MediaSearch => Some(ProcessingPath::PlexAPI),
            RequestType::MediaDownload => Some(ProcessingPath::ArrAPI),
            RequestType::MediaManagement => Some(ProcessingPath::NavidromeAPI),
            RequestType::ImageGeneration => Some(ProcessingPath::ComfyUI),
            RequestType::VoiceSynthesis => Some(ProcessingPath::VoiceAI),
            RequestType::ChatGPTTask | RequestType::CreativeWriting => Some(ProcessingPath::ChatGPT),
            RequestType::CursorTask => Some(ProcessingPath::Cursor),
            _ => None,
        }
    }
}

// =============================================================================
// ROUTING STATISTICS
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct RoutingStats {
    pub total_requests: u64,
    pub deterministic_count: u64,
    pub template_count: u64,
    pub embedding_count: u64,
    pub micro_model_count: u64,
    pub full_model_count: u64,
    // External service counts
    pub chatgpt_count: u64,
    pub cursor_count: u64,
    pub comfyui_count: u64,
    pub voice_count: u64,
    pub media_count: u64,
}

impl RoutingStats {
    pub fn record(&mut self, decision: &RoutingDecision) {
        self.total_requests += 1;
        match decision.processing_path {
            ProcessingPath::Deterministic => self.deterministic_count += 1,
            ProcessingPath::TemplateWithFill => self.template_count += 1,
            ProcessingPath::EmbeddingSearch => self.embedding_count += 1,
            ProcessingPath::Conversational => self.micro_model_count += 1, // Count with micro
            ProcessingPath::MicroModel => self.micro_model_count += 1,
            ProcessingPath::FullModel => self.full_model_count += 1,
            // External AI browser bridges
            ProcessingPath::ChatGPT | ProcessingPath::ClaudeBrowser => self.chatgpt_count += 1,
            // External services
            ProcessingPath::Cursor => self.cursor_count += 1,
            ProcessingPath::ComfyUI => self.comfyui_count += 1,
            ProcessingPath::VoiceAI => self.voice_count += 1,
            ProcessingPath::PlexAPI | ProcessingPath::NavidromeAPI |
            ProcessingPath::StashAPI | ProcessingPath::ArrAPI |
            ProcessingPath::TorrentAPI => self.media_count += 1,
        }
    }

    pub fn ai_avoidance_rate(&self) -> f32 {
        if self.total_requests == 0 {
            return 0.0;
        }
        let non_ai = self.deterministic_count + self.embedding_count;
        non_ai as f32 / self.total_requests as f32
    }

    pub fn light_ai_rate(&self) -> f32 {
        if self.total_requests == 0 {
            return 0.0;
        }
        let light = self.deterministic_count + self.embedding_count + self.template_count;
        light as f32 / self.total_requests as f32
    }
}

// Global router
lazy_static::lazy_static! {
    pub static ref HYBRID_ROUTER: std::sync::Mutex<HybridRouter> =
        std::sync::Mutex::new(HybridRouter::new());
    pub static ref ROUTING_STATS: std::sync::Mutex<RoutingStats> =
        std::sync::Mutex::new(RoutingStats::default());
}

pub fn router() -> std::sync::MutexGuard<'static, HybridRouter> {
    HYBRID_ROUTER.lock().unwrap()
}

pub fn stats() -> std::sync::MutexGuard<'static, RoutingStats> {
    ROUTING_STATS.lock().unwrap()
}

/// Route a request and record statistics
pub fn route_request(request: &str) -> RoutingDecision {
    let decision = router().route(request);
    stats().record(&decision);
    decision
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_deterministic_routing() {
        let router = HybridRouter::new();

        let decision = router.route("git status");
        assert_eq!(decision.processing_path, ProcessingPath::Deterministic);

        let decision = router.route("list files in src");
        assert_eq!(decision.processing_path, ProcessingPath::Deterministic);
    }

    #[test]
    fn test_template_routing() {
        let router = HybridRouter::new();

        let decision = router.route("create a react component for login");
        assert_eq!(decision.processing_path, ProcessingPath::TemplateWithFill);
        assert!(decision.template_name.is_some());
    }

    #[test]
    fn test_search_routing() {
        let router = HybridRouter::new();

        let decision = router.route("where is authentication handled?");
        assert_eq!(decision.processing_path, ProcessingPath::EmbeddingSearch);

        let decision = router.route("what does the login function do?");
        assert_eq!(decision.processing_path, ProcessingPath::EmbeddingSearch);
    }

    #[test]
    fn test_ai_routing() {
        let router = HybridRouter::new();

        let decision = router.route("fix the null pointer error in main.rs");
        assert!(matches!(decision.processing_path, ProcessingPath::MicroModel | ProcessingPath::FullModel));
    }

    #[test]
    fn test_daily_brief_routing() {
        let router = HybridRouter::new();

        // This is the exact user query that should route to Conversational
        let decision = router.route("Give me my daily brief - what needs attention across all projects?");
        println!("Routing: {:?} -> {:?}", decision.request_type, decision.processing_path);
        println!("Reasoning: {}", decision.reasoning);
        assert_eq!(decision.processing_path, ProcessingPath::Conversational,
            "Expected Conversational but got {:?}", decision.processing_path);

        // Simpler version
        let decision2 = router.route("daily brief");
        println!("Simple query: {:?} -> {:?}", decision2.request_type, decision2.processing_path);
        assert_eq!(decision2.processing_path, ProcessingPath::Conversational);

        // Another variant
        let decision3 = router.route("what needs attention");
        println!("Attention query: {:?} -> {:?}", decision3.request_type, decision3.processing_path);
        assert_eq!(decision3.processing_path, ProcessingPath::Conversational);
    }
}
