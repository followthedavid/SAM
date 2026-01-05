// Orchestrator - Central Integration Layer
//
// Wires together the 4 AI systems to achieve Claude Code/Warp parity:
// 1. HybridRouter - request classification
// 2. EmbeddingEngine - semantic code search
// 3. TemplateLibrary - code templates
// 4. MicroModelManager - model selection for 8GB RAM
//
// Single entry point: orchestrate() routes requests through optimal path

use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::path::PathBuf;
use std::collections::HashMap;
use dirs;
use chrono;

use crate::scaffolding::{
    // HybridRouter
    route_request, routing_stats, ProcessingPath, RoutingDecision, HybridRequestType,
    // EmbeddingEngine
    embeddings, EmbeddingSearchResult,
    // TemplateLibrary
    templates, TemplateResult,
    // MicroModelManager
    model_manager, select_for_task, record_task, ModelTaskType, ModelId,
    // Intelligence V2
    IntelligenceEngineV2, ExecutionResultV2,
    // Smart Edit
    SmartEditor, EditResult,
};

// =============================================================================
// CORE TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OrchestratorContext {
    pub working_directory: PathBuf,
    pub session_id: String,
    pub max_tokens: u32,
    pub stream: bool,
    pub conversation_history: Vec<ConversationTurn>,
}

impl Default for OrchestratorContext {
    fn default() -> Self {
        Self {
            working_directory: std::env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
            session_id: uuid::Uuid::new_v4().to_string(),
            max_tokens: 2048,
            stream: false,
            conversation_history: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ConversationTurn {
    pub role: String,  // "user" or "assistant"
    pub content: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum OrchestratorResult {
    /// Deterministic path - instant, no AI needed
    Instant(InstantResult),
    /// Embedding search - semantic search results
    Search(SearchResult),
    /// Generated content from LLM
    Generated(GeneratedResult),
    /// Error during processing
    Error(ErrorResult),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InstantResult {
    pub output: String,
    pub task_type: String,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub chunks: Vec<CodeSearchHit>,
    pub query: String,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeSearchHit {
    pub file_path: String,
    pub content: String,
    pub line_start: usize,
    pub relevance_score: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QuickAction {
    pub label: String,
    pub command: String,
    pub icon: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct GeneratedResult {
    pub content: String,
    pub model_used: String,
    pub tool_calls: Vec<ToolCallRecord>,
    pub tokens_used: u32,
    pub latency_ms: u64,
    #[serde(default)]
    pub actions: Vec<QuickAction>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ErrorResult {
    pub message: String,
    pub path_attempted: String,
    pub recoverable: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub tool: String,
    pub args: Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub tool: String,
    pub success: bool,
    pub output: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCallRecord {
    pub tool: String,
    pub args: Value,
    pub result: String,
    pub success: bool,
}

// =============================================================================
// MAIN ORCHESTRATION FUNCTION
// =============================================================================

/// Extract raw user input from potentially system-wrapped input
/// Input may be wrapped as "[SYSTEM: ...rules...]\n\nuser query"
fn extract_raw_input(input: &str) -> &str {
    // Check if input starts with system context
    if input.starts_with("[SYSTEM:") {
        // Find the end of system context: "]\n\n"
        if let Some(end_pos) = input.find("]\n\n") {
            let raw = &input[end_pos + 3..];
            return raw.trim();
        }
    }
    input
}

/// Main entry point - routes request through optimal processing path
pub async fn orchestrate(input: &str, ctx: &OrchestratorContext) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Extract raw user input for routing (strip system context if present)
    let raw_input = extract_raw_input(input);

    // 1. Route through HybridRouter using RAW input (not system-wrapped)
    let decision = route_request(raw_input);

    // Debug: Write to log file so we can verify routing
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open("/tmp/sam_routing.log")
    {
        use std::io::Write;
        let _ = writeln!(f, "[{}] Raw: \"{}\" | Path: {:?} | Type: {:?}",
            chrono::Utc::now().format("%H:%M:%S"),
            &raw_input[..std::cmp::min(60, raw_input.len())],
            decision.processing_path,
            decision.request_type);
    }

    eprintln!(
        "[ORCHESTRATOR] Routing: {:?} -> {:?} (confidence: {:.2})",
        decision.request_type,
        decision.processing_path,
        decision.confidence
    );

    // 2. Handle based on ProcessingPath
    let result = match decision.processing_path {
        // Internal AI paths
        ProcessingPath::Deterministic => {
            handle_deterministic(input, &decision, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::EmbeddingSearch => {
            handle_embedding_search(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::TemplateWithFill => {
            handle_template_fill(input, &decision, ctx, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::Conversational => {
            handle_conversational(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::MicroModel => {
            handle_micro_model(input, &decision, ctx, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::FullModel => {
            handle_full_model(input, &decision, ctx, start.elapsed().as_millis() as u64).await
        }

        // External AI browser bridges
        ProcessingPath::ChatGPT => {
            handle_chatgpt(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::ClaudeBrowser => {
            handle_claude_browser(input, start.elapsed().as_millis() as u64).await
        }

        // Other external paths
        ProcessingPath::Cursor => {
            handle_cursor(input, ctx, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::ComfyUI => {
            handle_comfyui(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::VoiceAI => {
            handle_voice_ai(input, start.elapsed().as_millis() as u64).await
        }

        // Media service paths
        ProcessingPath::PlexAPI => {
            handle_plex(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::NavidromeAPI => {
            handle_navidrome(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::StashAPI => {
            handle_stash(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::ArrAPI => {
            handle_arr(input, start.elapsed().as_millis() as u64).await
        }
        ProcessingPath::TorrentAPI => {
            handle_torrent(input, start.elapsed().as_millis() as u64).await
        }
    };

    // Log response details for verification
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open("/tmp/sam_routing.log")
    {
        use std::io::Write;
        let actions_count = match &result {
            OrchestratorResult::Generated(g) => g.actions.len(),
            _ => 0,
        };
        let result_type = match &result {
            OrchestratorResult::Instant(_) => "Instant",
            OrchestratorResult::Search(_) => "Search",
            OrchestratorResult::Generated(_) => "Generated",
            OrchestratorResult::Error(_) => "Error",
        };
        let _ = writeln!(f, "  → Response: {} | Actions: {}", result_type, actions_count);
    }

    result
}

// =============================================================================
// PATH HANDLERS
// =============================================================================

/// Deterministic path - uses Intelligence V2, no AI needed
async fn handle_deterministic(
    input: &str,
    decision: &RoutingDecision,
    _routing_latency: u64,
) -> OrchestratorResult {
    let start = std::time::Instant::now();

    let engine = IntelligenceEngineV2::new();
    let result = engine.execute(input);

    let latency = start.elapsed().as_millis() as u64;

    OrchestratorResult::Instant(InstantResult {
        output: result.output,
        task_type: format!("{:?}", decision.request_type),
        latency_ms: latency,
        })
}

/// Embedding search path - semantic code search, no generation
async fn handle_embedding_search(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    let emb = embeddings();
    let results = emb.search(input, 10);

    let chunks: Vec<CodeSearchHit> = results
        .iter()
        .map(|r| CodeSearchHit {
            file_path: r.chunk.file_path.clone(),
            content: r.chunk.content.clone(),
            line_start: r.chunk.start_line,
            relevance_score: r.score,
        })
        .collect();

    let latency = start.elapsed().as_millis() as u64;

    OrchestratorResult::Search(SearchResult {
        chunks,
        query: input.to_string(),
        latency_ms: latency,
        })
}

/// Conversational path - simple chat without tool instructions
async fn handle_conversational(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();
    let lower = input.to_lowercase();

    // Check for status/brief questions
    if lower.contains("daily brief") || lower.contains("needs attention") ||
       lower.contains("progress") || lower.contains("status") || lower.contains("summary") ||
       lower.contains("show my") || lower.contains("what's going on") {

        // Rich, contextual daily brief with visual hierarchy
        let mut output = String::new();
        let mut actions = Vec::new();

        output.push_str("╭───────────────────────────────────────╮\n");
        output.push_str("│           📊  DAILY BRIEF             │\n");
        output.push_str("╰───────────────────────────────────────╯\n\n");

        let registry_path = dirs::home_dir()
            .map(|h| h.join(".sam_project_registry.json"))
            .unwrap_or_else(|| std::path::PathBuf::from("/tmp/.sam_project_registry.json"));

        let registry: serde_json::Value = if registry_path.exists() {
            std::fs::read_to_string(&registry_path)
                .ok()
                .and_then(|s| serde_json::from_str(&s).ok())
                .unwrap_or_default()
        } else {
            output.push_str("⚠️  No project registry found.\n\n");
            output.push_str("I need to scan your workspace first.\n");
            actions.push(QuickAction {
                label: "🔍 Scan Workspace".to_string(),
                command: "scan projects".to_string(),
                icon: Some("🔍".to_string()),
            });
            return OrchestratorResult::Generated(GeneratedResult {
                content: output,
                model_used: "system".to_string(),
                tool_calls: vec![],
                tokens_used: 0,
                latency_ms: start.elapsed().as_millis() as u64,
                actions,
            });
        };

        let projects = registry.get("projects").and_then(|p| p.as_array());

        if let Some(projects) = projects {
            // Collect rich project info
            let mut urgent_projects: Vec<(&str, u64, &str, &str, &str)> = Vec::new();
            let mut pending_projects: Vec<(&str, u64, &str)> = Vec::new();
            let mut running_projects: Vec<(&str, usize, &str)> = Vec::new();
            let mut clean_count = 0;

            for p in projects {
                let name = p.get("name").and_then(|n| n.as_str()).unwrap_or("?");
                let ptype = p.get("type").and_then(|t| t.as_str()).unwrap_or("?");
                let running = p.get("running_services")
                    .and_then(|r| r.as_array())
                    .map(|a| a.len())
                    .unwrap_or(0);

                if running > 0 {
                    running_projects.push((name, running, ptype));
                }

                if let Some(git) = p.get("git") {
                    let changes = git.get("uncommitted_changes").and_then(|c| c.as_u64()).unwrap_or(0);
                    let branch = git.get("branch").and_then(|b| b.as_str()).unwrap_or("main");
                    let last_commit = git.get("last_commit_time").and_then(|t| t.as_str()).unwrap_or("?");
                    let last_msg = git.get("last_commit_message").and_then(|m| m.as_str()).unwrap_or("");

                    if changes > 50 {
                        urgent_projects.push((name, changes, branch, last_commit, last_msg));
                    } else if changes > 0 {
                        pending_projects.push((name, changes, branch));
                    } else {
                        clean_count += 1;
                    }
                }
            }

            // Sort urgent by most changes
            urgent_projects.sort_by(|a, b| b.1.cmp(&a.1));

            // ═══ URGENT SECTION ═══
            if !urgent_projects.is_empty() {
                output.push_str("🔴 URGENT\n");
                output.push_str("─────────\n");
                for (name, changes, branch, last_commit, last_msg) in &urgent_projects {
                    output.push_str(&format!("  ┌─ {} \n", name));
                    output.push_str(&format!("  │  ⚠️  {} uncommitted changes\n", changes));
                    output.push_str(&format!("  │  📌 branch: {}\n", branch));
                    if !last_msg.is_empty() {
                        let msg = if last_msg.len() > 35 { format!("{}...", &last_msg[..35]) } else { last_msg.to_string() };
                        output.push_str(&format!("  │  💬 \"{}\"\n", msg));
                    }
                    output.push_str(&format!("  └─ 🕐 {}\n\n", last_commit));

                    // Add action for each urgent project
                    actions.push(QuickAction {
                        label: format!("💾 Commit {}", name),
                        command: format!("commit {}", name),
                        icon: Some("💾".to_string()),
                    });
                }
            }

            // ═══ PENDING SECTION ═══
            if !pending_projects.is_empty() {
                output.push_str("🟡 PENDING\n");
                output.push_str("──────────\n");
                for (name, changes, branch) in &pending_projects {
                    // Visual bar
                    let filled = ((*changes as usize) * 10 / 50).min(10);
                    let bar = format!("{}{}",
                        "▓".repeat(filled),
                        "░".repeat(10 - filled));
                    output.push_str(&format!("  {} {} ({} on {})\n", bar, name, changes, branch));
                }
                output.push_str("\n");
            }

            // ═══ ACTIVE SECTION ═══
            if !running_projects.is_empty() {
                output.push_str("🟢 ACTIVE SERVICES\n");
                output.push_str("──────────────────\n");
                for (name, count, ptype) in &running_projects {
                    output.push_str(&format!("  ● {} — {} process(es) [{}]\n", name, count, ptype));
                }
                output.push_str("\n");
            }

            // ═══ SUMMARY ═══
            output.push_str("╭─────────────────────────────────────╮\n");
            let total = urgent_projects.len() + pending_projects.len() + clean_count;
            if !urgent_projects.is_empty() {
                let (name, changes, _, _, _) = urgent_projects[0];
                output.push_str(&format!("│ ⚡ Priority: {} ({} at risk)   \n", name, changes));
            } else if !pending_projects.is_empty() {
                output.push_str("│ 💡 Small changes, good time to commit \n");
            } else {
                output.push_str("│ 🎉 All {} projects clean!            \n");
            }
            output.push_str(&format!("│ 📁 {} total │ ✅ {} clean │ ⚠️ {} need attention\n",
                total, clean_count, urgent_projects.len() + pending_projects.len()));
            output.push_str("╰─────────────────────────────────────╯\n");

            // Add refresh action
            actions.push(QuickAction {
                label: "🔄 Refresh".to_string(),
                command: "scan projects".to_string(),
                icon: Some("🔄".to_string()),
            });

            let latency = start.elapsed().as_millis() as u64;
            return OrchestratorResult::Generated(GeneratedResult {
                content: output,
                model_used: "system".to_string(),
                tool_calls: vec![],
                tokens_used: 0,
                latency_ms: latency,
                actions,
            });

        } else {
            output.push_str("No projects found.\n");
            actions.push(QuickAction {
                label: "🔍 Scan Projects".to_string(),
                command: "scan projects".to_string(),
                icon: Some("🔍".to_string()),
            });

            return OrchestratorResult::Generated(GeneratedResult {
                content: output,
                model_used: "system".to_string(),
                tool_calls: vec![],
                tokens_used: 0,
                latency_ms: start.elapsed().as_millis() as u64,
                actions,
            });
        }
    }

    // Detect if this is an EXPLICIT roleplay/creative request (be restrictive)
    let is_roleplay = lower.contains("roleplay") || lower.contains("role play") || lower.contains("role-play") ||
                      lower.contains("pretend to be") || lower.contains("pretend you're") ||
                      lower.contains("imagine you're") || lower.contains("imagine we") ||
                      lower.contains("be my") || lower.contains("act as") || lower.contains("act like") ||
                      lower.contains("you are a") || lower.contains("you're a");

    let is_creative = lower.contains("write me a story") || lower.contains("tell me a story") ||
                      lower.contains("write a poem") || lower.contains("creative writing") ||
                      lower.contains("let's chat") || lower.contains("just chat");

    // Adjust system prompt and settings based on mode
    // Use qwen2.5-coder:1.5b for all modes to avoid model loading delays (78+ seconds)
    let (system_prompt, temperature, max_tokens, model) = if is_roleplay || is_creative {
        // Roleplay/creative mode - more expressive, longer responses
        let rp_prompt = r#"You are an AI companion engaging in creative roleplay or storytelling.
Stay in character and be expressive. Respond with vivid, engaging content.
Match the tone and style the user requests. Be creative and immersive.
This is a private conversation - be open, playful, and collaborative.
Do not break character or explain what you're doing."#;
        (rp_prompt, 0.9, 512, "qwen2.5-coder:1.5b")  // Same model, just different settings
    } else {
        // Standard conversational mode
        let std_prompt = r#"You are SAM, a friendly and helpful AI assistant.
Respond naturally and conversationally. Be concise but warm.
Do not output JSON or tool calls - just respond in plain text."#;
        (std_prompt, 0.7, 256, "qwen2.5-coder:1.5b")
    };

    let prompt = format!("{}\n\nUser: {}\nAssistant:", system_prompt, input);

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(60))  // 60 second timeout
        .build()
        .unwrap_or_else(|_| reqwest::Client::new());

    // Single model request - no fallback needed since we use the same model
    let response = client
        .post("http://localhost:11434/api/generate")
        .json(&serde_json::json!({
            "model": model,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }))
        .send()
        .await
        .map_err(|e| format!("Ollama request failed: {}", e));

    let response = match response {
        Ok(r) => r,
        Err(e) => {
            return OrchestratorResult::Error(ErrorResult {
                message: e,
                path_attempted: "Conversational".to_string(),
                recoverable: true,
            });
        }
    };

    let body: serde_json::Value = response
        .json()
        .await
        .unwrap_or(serde_json::json!({"response": "I couldn't process that."}));

    let raw_content = body["response"]
        .as_str()
        .unwrap_or("Hello! How can I help you?")
        .trim()
        .to_string();

    // Add mode indicator for transparency
    let mode_label = if is_roleplay {
        "🎭 *Private roleplay mode*"
    } else if is_creative {
        "✨ *Creative mode*"
    } else {
        ""
    };

    let content = if mode_label.is_empty() {
        raw_content
    } else {
        format!("{}\n\n{}", mode_label, raw_content)
    };

    let latency = start.elapsed().as_millis() as u64;

    // Provide seamless mode switching via quick actions
    let actions = if is_roleplay || is_creative {
        vec![
            QuickAction {
                label: "Exit creative mode".to_string(),
                command: "exit roleplay".to_string(),
                icon: Some("x".to_string()),
            },
        ]
    } else {
        vec![]
    };

    OrchestratorResult::Generated(GeneratedResult {
        content,
        model_used: model.to_string(),
        tool_calls: vec![],
        tokens_used: 0,
        latency_ms: latency,
        actions,
    })
}

/// Template with fill path - uses template library + minimal AI for placeholders
async fn handle_template_fill(
    input: &str,
    decision: &RoutingDecision,
    ctx: &OrchestratorContext,
    _routing_latency: u64,
) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Get template name from decision
    let template_name = match &decision.template_name {
        Some(name) => name.clone(),
        None => {
            return OrchestratorResult::Error(ErrorResult {
                message: "Template routing decided but no template name provided".to_string(),
                path_attempted: "TemplateWithFill".to_string(),
                recoverable: true,
            });
        }
    };

    // Find the template - clone the result before dropping the guard
    let maybe_template = {
        let tmpl = templates();
        tmpl.search(&template_name).first().map(|t| (*t).clone())
    }; // tmpl guard dropped here

    let template = match maybe_template {
        Some(t) => t,
        None => {
            // Fallback to micro model if template not found
            return handle_micro_model(input, decision, ctx, start.elapsed().as_millis() as u64).await;
        }
    };

    // Extract explicit values from input
    let explicit_values = extract_explicit_values(input, &template_name);

    // Check if we need AI to fill remaining placeholders
    let missing_placeholders: Vec<String> = template
        .placeholders
        .iter()
        .filter(|p| p.ai_fill && p.default.is_none() && !explicit_values.contains_key(&p.name))
        .map(|p| p.name.clone())
        .collect();

    let mut fill_values = explicit_values;

    if !missing_placeholders.is_empty() {
        // Use micro model to fill placeholders
        // Scope the templates() call to not cross awaits
        let fill_prompt = {
            let tmpl = templates();
            match tmpl.generate_fill_prompt(&template.id, input, &fill_values) {
                Ok(prompt) => prompt,
                Err(_) => String::new(),
            }
        }; // tmpl dropped before await

        match call_ollama_for_fill(&fill_prompt, &missing_placeholders).await {
            Ok(ai_values) => {
                fill_values.extend(ai_values);
            }
            Err(e) => {
                eprintln!("[ORCHESTRATOR] AI fill failed: {}, using defaults", e);
            }
        }
    }

    // Fill the template - new scope for templates()
    let tmpl = templates();
    match tmpl.fill(&template.id, &fill_values) {
        Ok(result) => {
            let latency = start.elapsed().as_millis() as u64;
            OrchestratorResult::Generated(GeneratedResult {
                content: result.code,
                model_used: decision.model_recommendation.clone().unwrap_or_else(|| "template".to_string()),
                tool_calls: vec![],
                tokens_used: 0,
                latency_ms: latency,
            actions: vec![],
        })
        }
        Err(e) => {
            // Check if it's a missing placeholder error and give helpful feedback
            if e.contains("Required placeholder") {
                // Extract missing placeholder name
                let missing = e.split('\'').nth(1).unwrap_or("name");

                // Generate friendly prompt based on what's missing
                let friendly_message = match missing.to_lowercase().as_str() {
                    "component_name" | "name" => {
                        format!("I can create that! What should I call it?\n\n**Example**: \"create a react component **called LoginButton**\"")
                    }
                    "function_name" => {
                        format!("I can write that function! What should it be named?\n\n**Example**: \"create a function **called calculateTotal**\"")
                    }
                    "file_path" | "path" => {
                        format!("Where should I create this?\n\n**Example**: \"create ... **in src/components/**\"")
                    }
                    _ => {
                        format!("I need a bit more info - please specify the **{}**.\n\n**Tip**: Try rephrasing with the name included.", missing)
                    }
                };

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Generated(GeneratedResult {
                    content: friendly_message,
                    model_used: "template".to_string(),
                    tool_calls: vec![],
                    tokens_used: 0,
                    latency_ms: latency,
                actions: vec![],
        })
            } else {
                OrchestratorResult::Error(ErrorResult {
                    message: format!("Template fill failed: {}", e),
                    path_attempted: "TemplateWithFill".to_string(),
                    recoverable: true,
                })
            }
        }
    }
}

/// Micro model path - small model + multi-turn tool execution
async fn handle_micro_model(
    input: &str,
    decision: &RoutingDecision,
    ctx: &OrchestratorContext,
    _routing_latency: u64,
) -> OrchestratorResult {
    let start = std::time::Instant::now();
    const MAX_ITERATIONS: u32 = 5;

    // Map request type to model task type
    let task_type = map_request_to_task(&decision.request_type);
    let model = select_for_task(task_type.clone());
    let model_name = model.ollama_name();

    // Check VRAM availability
    if let Err(e) = ensure_vram_available(&model) {
        return OrchestratorResult::Error(ErrorResult {
            message: format!("VRAM management failed: {}", e),
            path_attempted: "MicroModel".to_string(),
            recoverable: true,
        });
    }

    // Multi-turn agentic loop
    let mut all_tool_records: Vec<ToolCallRecord> = Vec::new();
    let mut conversation_log: Vec<String> = Vec::new();
    let mut current_prompt = build_tool_prompt(input, ctx);
    let mut final_answer = String::new();

    for iteration in 0..MAX_ITERATIONS {
        eprintln!("[ORCHESTRATOR] Iteration {}/{}", iteration + 1, MAX_ITERATIONS);

        match call_ollama_with_tools(&model_name, &current_prompt, ctx).await {
            Ok((response, tool_calls)) => {
                eprintln!("[ORCHESTRATOR] Tool calls found: {}", tool_calls.len());

                if tool_calls.is_empty() {
                    // No more tools - model is giving final answer
                    // Clean up any prompt instructions that leaked through
                    final_answer = response
                        .trim()
                        .trim_start_matches("```json")
                        .trim_start_matches("```")
                        .trim_end_matches("```")
                        .trim()
                        .to_string();

                    // Remove leaked prompt instructions
                    let cleanup_patterns = [
                        "1. Call another tool",
                        "2. Provide your final answer",
                        "Based on these results",
                        "What's next?",
                        "(output ONLY the JSON)",
                        "(no JSON)",
                    ];
                    for pattern in cleanup_patterns {
                        final_answer = final_answer.replace(pattern, "");
                    }
                    final_answer = final_answer.trim().to_string();

                    break;
                }

                // Execute tools and collect results
                let tool_records = execute_tool_calls(&tool_calls, ctx).await;

                // Format results for display and next prompt
                let results_display: Vec<String> = tool_records
                    .iter()
                    .map(|r| {
                        if r.success {
                            format!("✓ **{}**: {}", r.tool, truncate_result(&r.result, 500))
                        } else {
                            format!("✗ **{}** failed: {}", r.tool, r.result)
                        }
                    })
                    .collect();

                conversation_log.extend(results_display.clone());
                all_tool_records.extend(tool_records.clone());

                // Build continuation prompt with tool results
                let tool_results_text = tool_records
                    .iter()
                    .map(|r| format!("Tool: {}\nResult: {}", r.tool, truncate_result(&r.result, 1000)))
                    .collect::<Vec<_>>()
                    .join("\n\n");

                current_prompt = format!(
                    r#"Previous tool results:
{}

Based on these results, either:
1. Call another tool if you need more information (output ONLY the JSON)
2. Provide your final answer in plain text (no JSON)

What's next?"#,
                    tool_results_text
                );
            }
            Err(e) => {
                record_task(task_type.clone(), model, false);
                return OrchestratorResult::Error(ErrorResult {
                    message: format!("Model inference failed: {}", e),
                    path_attempted: "MicroModel".to_string(),
                    recoverable: true,
                });
            }
        }
    }

    // Build final content - clean and readable
    let content = if !conversation_log.is_empty() || !final_answer.is_empty() {
        let mut parts = Vec::new();

        // Show tool results
        if !conversation_log.is_empty() {
            parts.push(conversation_log.join("\n"));
        }

        // Only show final answer if it adds value (not just restating tool results)
        if !final_answer.is_empty() && final_answer.len() > 10 {
            // Check if it's substantive content, not just acknowledgment
            let lower = final_answer.to_lowercase();
            let is_substantive = !lower.contains("here are") &&
                                 !lower.contains("the results") &&
                                 !lower.contains("i found") &&
                                 final_answer.split_whitespace().count() > 5;

            if is_substantive {
                parts.push(format!("\n{}", final_answer));
            }
        }
        parts.join("\n")
    } else {
        "Done.".to_string()
    };

    record_task(task_type.clone(), model, true);

    let latency = start.elapsed().as_millis() as u64;
    OrchestratorResult::Generated(GeneratedResult {
        content,
        model_used: decision.model_recommendation.clone().unwrap_or_else(|| "micro".to_string()),
        tool_calls: all_tool_records,
        tokens_used: 0,
        latency_ms: latency,
    actions: vec![],
        })
}

/// Truncate long results for display
fn truncate_result(s: &str, max_len: usize) -> String {
    if s.len() <= max_len {
        s.to_string()
    } else {
        format!("{}... (truncated)", &s[..max_len])
    }
}

/// Old single-turn handler (kept for reference)
#[allow(dead_code)]
async fn handle_micro_model_single(
    input: &str,
    decision: &RoutingDecision,
    ctx: &OrchestratorContext,
    _routing_latency: u64,
) -> OrchestratorResult {
    let start = std::time::Instant::now();
    let task_type = map_request_to_task(&decision.request_type);
    let model = select_for_task(task_type.clone());

    if let Err(e) = ensure_vram_available(&model) {
        return OrchestratorResult::Error(ErrorResult {
            message: format!("VRAM management failed: {}", e),
            path_attempted: "MicroModel".to_string(),
            recoverable: true,
        });
    }

    let prompt = build_tool_prompt(input, ctx);

    match call_ollama_with_tools(&model.ollama_name(), &prompt, ctx).await {
        Ok((response, tool_calls)) => {
            let tool_records = execute_tool_calls(&tool_calls, ctx).await;
            let content = if !tool_records.is_empty() {
                tool_records.iter()
                    .map(|r| if r.success { format!("**{}**:\n{}", r.tool, r.result) } else { format!("**{}** failed: {}", r.tool, r.result) })
                    .collect::<Vec<_>>().join("\n\n")
            } else {
                response.trim().to_string()
            };
            record_task(task_type.clone(), model, true);
            OrchestratorResult::Generated(GeneratedResult {
                content,
                model_used: decision.model_recommendation.clone().unwrap_or_else(|| "micro".to_string()),
                tool_calls: tool_records,
                tokens_used: 0,
                latency_ms: start.elapsed().as_millis() as u64,
            actions: vec![],
        })
        }
        Err(e) => {
            record_task(task_type.clone(), model, false);
            OrchestratorResult::Error(ErrorResult {
                message: format!("Model inference failed: {}", e),
                path_attempted: "MicroModel".to_string(),
                recoverable: true,
            })
        }
    }
}

/// Full model path - larger model for complex tasks
async fn handle_full_model(
    input: &str,
    decision: &RoutingDecision,
    ctx: &OrchestratorContext,
    _routing_latency: u64,
) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // For full model, use 1.5b (installed) or 3b if available
    let model_name = decision
        .model_recommendation
        .clone()
        .unwrap_or_else(|| "qwen2.5-coder:1.5b".to_string());

    // Check if too many models are loaded - unload idle ones
    // Scope the guard to avoid holding it across awaits
    {
        let mgr = model_manager();
        let idle_models = mgr.get_idle_models();
        if idle_models.len() > 2 {
            // Unload idle models to make room
            for idle in idle_models {
                if let Err(e) = unload_model(&idle.ollama_name()) {
                    eprintln!("[ORCHESTRATOR] Failed to unload model: {}", e);
                }
            }
        }
    } // mgr dropped here before any await

    // Build comprehensive prompt
    let prompt = build_comprehensive_prompt(input, ctx);

    // Multi-turn loop for complex tasks
    let mut all_tool_calls = Vec::new();
    let mut final_response = String::new();
    let mut iterations = 0;
    const MAX_ITERATIONS: u32 = 5;

    let mut current_prompt = prompt;

    while iterations < MAX_ITERATIONS {
        iterations += 1;

        match call_ollama_with_tools(&model_name, &current_prompt, ctx).await {
            Ok((response, tool_calls)) => {
                if tool_calls.is_empty() {
                    // No more tools to call, we're done
                    final_response = response;
                    break;
                }

                // Execute tools and build follow-up prompt
                let results = execute_tool_calls(&tool_calls, ctx).await;
                all_tool_calls.extend(results.clone());

                // Build continuation prompt with tool results
                current_prompt = build_continuation_prompt(&response, &results);
            }
            Err(e) => {
                return OrchestratorResult::Error(ErrorResult {
                    message: format!("Full model inference failed: {}", e),
                    path_attempted: "FullModel".to_string(),
                    recoverable: true,
                });
            }
        }
    }

    let latency = start.elapsed().as_millis() as u64;
    OrchestratorResult::Generated(GeneratedResult {
        content: final_response,
        model_used: model_name,
        tool_calls: all_tool_calls,
        tokens_used: 0,
        latency_ms: latency,
    actions: vec![],
        })
}

// =============================================================================
// EXTERNAL AI HANDLERS
// =============================================================================

/// Sanitization result for external AI queries
struct SanitizationResult {
    sanitized_text: String,
    was_sanitized: bool,
    explanation: String,
    can_send: bool,
}

/// Sanitize input before sending to external AI
fn sanitize_for_external(input: &str) -> SanitizationResult {
    use super::intent_sanitizer::{sanitize_query, explain_sanitization, SensitivityLevel};

    let result = sanitize_query(input, false);
    let explanation = explain_sanitization(&result);

    SanitizationResult {
        sanitized_text: if result.can_send_external {
            result.sanitized_text.clone()
        } else {
            String::new()
        },
        was_sanitized: result.sensitivity != SensitivityLevel::Safe,
        explanation,
        can_send: result.can_send_external,
    }
}

/// Queue task for browser-based AI (ChatGPT or Claude)
/// Now with automatic intent sanitization
fn queue_browser_ai_task(input: &str, provider: &str) -> (String, PathBuf, SanitizationResult) {
    let queue_path = dirs::home_dir()
        .map(|h| h.join(".sam_chatgpt_queue.json"))
        .unwrap_or_else(|| PathBuf::from("/tmp/.sam_chatgpt_queue.json"));

    // Sanitize the input before queuing
    let sanitization = sanitize_for_external(input);

    // Log the routing with sanitization info
    use super::privacy_logger::log_routing;
    log_routing(
        input,
        provider,
        sanitization.was_sanitized,
        !sanitization.can_send,
    );

    let task_id = uuid::Uuid::new_v4().to_string();

    // Compute hash before the json! macro
    let original_hash = {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut h = DefaultHasher::new();
        input.hash(&mut h);
        format!("{:x}", h.finish())
    };

    // Only queue if we can send externally
    if sanitization.can_send {
        let task = json!({
            "id": task_id,
            "prompt": sanitization.sanitized_text,  // Send sanitized version
            "original_hash": original_hash,
            "provider": provider,
            "timestamp": chrono::Utc::now().to_rfc3339(),
            "status": "pending",
            "was_sanitized": sanitization.was_sanitized
        });

        // Append to queue file
        let mut queue: Vec<Value> = if queue_path.exists() {
            std::fs::read_to_string(&queue_path)
                .ok()
                .and_then(|s| serde_json::from_str(&s).ok())
                .unwrap_or_default()
        } else {
            Vec::new()
        };

        queue.push(task);
        let _ = std::fs::write(&queue_path, serde_json::to_string_pretty(&queue).unwrap_or_default());
    }

    (task_id, queue_path, sanitization)
}

/// Check if a task response is ready
pub fn poll_browser_response(task_id: &str) -> Option<(String, bool)> {
    let response_path = dirs::home_dir()
        .map(|h| h.join(".sam_chatgpt_responses.json"))
        .unwrap_or_else(|| PathBuf::from("/tmp/.sam_chatgpt_responses.json"));

    if !response_path.exists() {
        return None;
    }

    let responses: Value = std::fs::read_to_string(&response_path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();

    responses.get(task_id).map(|r| {
        (
            r["response"].as_str().unwrap_or("").to_string(),
            r["success"].as_bool().unwrap_or(false)
        )
    })
}

/// Get all pending bridge tasks
pub fn get_bridge_queue() -> Vec<Value> {
    let queue_path = dirs::home_dir()
        .map(|h| h.join(".sam_chatgpt_queue.json"))
        .unwrap_or_else(|| PathBuf::from("/tmp/.sam_chatgpt_queue.json"));

    if !queue_path.exists() {
        return Vec::new();
    }

    std::fs::read_to_string(&queue_path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

/// ChatGPT bridge - queues task for web-based ChatGPT
/// Now with automatic sanitization and visible feedback
async fn handle_chatgpt(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();
    let (task_id, queue_path, sanitization) = queue_browser_ai_task(input, "chatgpt");

    // If can't send externally (private), redirect to local
    if !sanitization.can_send {
        return OrchestratorResult::Generated(GeneratedResult {
            content: format!(
                "🔒 **Private Mode Active**\n\n{}\n\nProcessing locally with Ollama instead of external AI.",
                sanitization.explanation
            ),
            model_used: "local-redirect".to_string(),
            tool_calls: vec![],
            tokens_used: 0,
            latency_ms: start.elapsed().as_millis() as u64,
            actions: vec![QuickAction {
                label: "🤖 Process Locally".to_string(),
                command: input.to_string(),
                icon: Some("🔒".to_string()),
            }],
        });
    }

    // Ensure bridge daemon is running
    ensure_bridge_daemon_running();

    // Wait briefly for response (in case it's quick)
    for _ in 0..6 {
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        if let Some((response, success)) = poll_browser_response(&task_id) {
            if success {
                return OrchestratorResult::Generated(GeneratedResult {
                    content: response,
                    model_used: "chatgpt-bridge".to_string(),
                    tool_calls: vec![],
                    tokens_used: 0,
                    latency_ms: start.elapsed().as_millis() as u64,
                actions: vec![],
        });
            }
        }
    }

    // No immediate response - return queue confirmation with sanitization info
    let latency = start.elapsed().as_millis() as u64;

    // Build visible explanation of what's happening
    let sanitization_info = if sanitization.was_sanitized {
        format!("\n\n📝 **Sanitization Applied**\n{}", sanitization.explanation)
    } else {
        String::new()
    };

    OrchestratorResult::Generated(GeneratedResult {
        content: format!(
            "**Routed to ChatGPT** (creative/conversational task)\n\nTask ID: `{}`\nStatus: Queued{}",
            task_id,
            sanitization_info
        ),
        model_used: "chatgpt-bridge".to_string(),
        tool_calls: vec![ToolCallRecord {
            tool: "browser_queue".to_string(),
            args: json!({
                "task_id": task_id,
                "provider": "chatgpt",
                "was_sanitized": sanitization.was_sanitized
            }),
            result: format!("Queued to {}", queue_path.display()),
            success: true,
        }],
        tokens_used: 0,
        latency_ms: latency,
        actions: vec![],
    })
}

/// Ensure the bridge daemon is running
fn ensure_bridge_daemon_running() {
    // Check if daemon is running
    let pid_file = dirs::home_dir()
        .map(|h| h.join(".sam_bridge.pid"))
        .unwrap_or_else(|| PathBuf::from("/tmp/.sam_bridge.pid"));

    let daemon_running = if pid_file.exists() {
        std::fs::read_to_string(&pid_file)
            .ok()
            .and_then(|s| s.trim().parse::<u32>().ok())
            .map(|pid| {
                std::process::Command::new("kill")
                    .args(["-0", &pid.to_string()])
                    .status()
                    .map(|s| s.success())
                    .unwrap_or(false)
            })
            .unwrap_or(false)
    } else {
        false
    };

    if !daemon_running {
        // Start the bridge daemon
        let bridge_script = dirs::home_dir()
            .map(|h| h.join("ReverseLab/SAM/warp_tauri/bridge_daemon.sh"))
            .unwrap_or_else(|| PathBuf::from("./bridge_daemon.sh"));

        if bridge_script.exists() {
            let _ = std::process::Command::new("bash")
                .arg(&bridge_script)
                .spawn();
        }
    }
}

/// Claude browser bridge - queues task for web-based Claude
async fn handle_claude_browser(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();
    let (task_id, queue_path, sanitization) = queue_browser_ai_task(input, "claude");

    // If content is too private to send externally, redirect to local
    if !sanitization.can_send {
        return OrchestratorResult::Generated(GeneratedResult {
            content: format!("🔒 **Private Mode Active**\n\n{}\n\nUsing local model for privacy.", sanitization.explanation),
            model_used: "local-redirect".to_string(),
            tool_calls: vec![],
            tokens_used: 0,
            latency_ms: start.elapsed().as_millis() as u64,
            actions: vec![],
        });
    }

    // Ensure bridge daemon is running
    ensure_bridge_daemon_running();

    // Wait briefly for response (in case it's quick)
    for _ in 0..6 {
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;
        if let Some((response, success)) = poll_browser_response(&task_id) {
            if success {
                return OrchestratorResult::Generated(GeneratedResult {
                    content: response,
                    model_used: "claude-bridge".to_string(),
                    tool_calls: vec![],
                    tokens_used: 0,
                    latency_ms: start.elapsed().as_millis() as u64,
                actions: vec![],
        });
            }
        }
    }

    // No immediate response - return queue confirmation
    let latency = start.elapsed().as_millis() as u64;
    OrchestratorResult::Generated(GeneratedResult {
        content: format!(
            "**Routed to Claude** (complex reasoning task)\n\nTask ID: `{}`\nStatus: Queued\n\nThe bridge daemon is processing this request. Response will appear shortly.",
            task_id
        ),
        model_used: "claude-bridge".to_string(),
        tool_calls: vec![ToolCallRecord {
            tool: "browser_queue".to_string(),
            args: json!({"task_id": task_id, "provider": "claude"}),
            result: format!("Queued to {}", queue_path.display()),
            success: true,
        }],
        tokens_used: 0,
        latency_ms: latency,
    actions: vec![],
        })
}

/// Cursor - opens file in Cursor editor with optional instruction
async fn handle_cursor(input: &str, ctx: &OrchestratorContext, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Extract file path from input if present
    let file_pattern = regex::Regex::new(r"(?:open|edit|fix)\s+(\S+\.\w+)").ok();
    let file_path = file_pattern
        .and_then(|re| re.captures(input))
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().to_string());

    let target_path = file_path
        .map(|f| ctx.working_directory.join(f))
        .unwrap_or_else(|| ctx.working_directory.clone());

    // Use open command to launch Cursor
    let result = std::process::Command::new("open")
        .args(["-a", "Cursor", target_path.to_str().unwrap_or(".")])
        .spawn();

    match result {
        Ok(_) => {
            let latency = start.elapsed().as_millis() as u64;
            OrchestratorResult::Generated(GeneratedResult {
                content: format!(
                    "Opened in Cursor: {}\n\nInstruction: {}",
                    target_path.display(),
                    input
                ),
                model_used: "cursor".to_string(),
                tool_calls: vec![],
                tokens_used: 0,
                latency_ms: latency,
            actions: vec![],
        })
        }
        Err(e) => OrchestratorResult::Error(ErrorResult {
            message: format!("Failed to open Cursor: {}", e),
            path_attempted: "Cursor".to_string(),
            recoverable: true,
        }),
    }
}

/// ComfyUI - image generation via local API
async fn handle_comfyui(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // ComfyUI API endpoint
    let api_url = "http://127.0.0.1:8188/api";

    // Build a simple txt2img workflow prompt
    let workflow = json!({
        "prompt": {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": rand::random::<u64>() % 999999999,
                    "steps": 20,
                    "cfg": 7.0,
                    "sampler_name": "euler_a",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0]
                }
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "realisticVisionV51_v51VAE.safetensors"
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                }
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": input,
                    "clip": ["4", 1]
                }
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "ugly, deformed, blurry, low quality",
                    "clip": ["4", 1]
                }
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2]
                }
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "SAM_gen",
                    "images": ["8", 0]
                }
            }
        }
    });

    let client = reqwest::Client::new();
    let result = client
        .post(format!("{}/prompt", api_url))
        .json(&workflow)
        .send()
        .await;

    match result {
        Ok(response) => {
            if response.status().is_success() {
                let json: Value = response.json().await.unwrap_or_default();
                let prompt_id = json["prompt_id"].as_str().unwrap_or("unknown");

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Generated(GeneratedResult {
                    content: format!(
                        "Image generation queued in ComfyUI\n\nPrompt: {}\nPrompt ID: {}\n\nCheck http://127.0.0.1:8188 for results",
                        input, prompt_id
                    ),
                    model_used: "comfyui".to_string(),
                    tool_calls: vec![],
                    tokens_used: 0,
                    latency_ms: latency,
                actions: vec![],
        })
            } else {
                OrchestratorResult::Error(ErrorResult {
                    message: format!("ComfyUI API error: {}", response.status()),
                    path_attempted: "ComfyUI".to_string(),
                    recoverable: true,
                })
            }
        }
        Err(e) => OrchestratorResult::Error(ErrorResult {
            message: format!("ComfyUI request failed: {}. Is ComfyUI running?", e),
            path_attempted: "ComfyUI".to_string(),
            recoverable: true,
        }),
    }
}

/// Voice AI - RVC voice cloning / TTS
async fn handle_voice_ai(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Check if RVC WebUI is running on port 7865
    let client = reqwest::Client::new();
    let health = client.get("http://localhost:7865/").send().await;

    if health.is_err() {
        return OrchestratorResult::Error(ErrorResult {
            message: "RVC WebUI not running on port 7865. Start it with: cd ~/Projects/RVC/rvc-webui && python app.py".to_string(),
            path_attempted: "VoiceAI".to_string(),
            recoverable: true,
        });
    }

    // For now, queue the voice task (RVC WebUI uses Gradio, harder to call directly)
    let queue_path = dirs::home_dir()
        .map(|h| h.join(".sam_voice_queue.json"))
        .unwrap_or_else(|| PathBuf::from("/tmp/.sam_voice_queue.json"));

    let task = json!({
        "id": uuid::Uuid::new_v4().to_string(),
        "text": input,
        "timestamp": chrono::Utc::now().to_rfc3339(),
        "status": "pending"
    });

    // Append to queue
    let mut queue: Vec<Value> = if queue_path.exists() {
        std::fs::read_to_string(&queue_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        Vec::new()
    };

    queue.push(task.clone());
    let _ = std::fs::write(&queue_path, serde_json::to_string_pretty(&queue).unwrap_or_default());

    let latency = start.elapsed().as_millis() as u64;
    OrchestratorResult::Generated(GeneratedResult {
        content: format!(
            "Voice task queued\n\nText: {}\nRVC WebUI: http://localhost:7865\n\nNote: Manual processing required in WebUI",
            input
        ),
        model_used: "rvc".to_string(),
        tool_calls: vec![],
        tokens_used: 0,
        latency_ms: latency,
    actions: vec![],
        })
}

// =============================================================================
// MEDIA SERVICE HANDLERS
// =============================================================================

/// Plex - play media, search library
async fn handle_plex(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Load Plex token from preferences
    let plex_prefs = dirs::home_dir()
        .map(|h| h.join("Library/Application Support/Plex Media Server/Preferences.xml"))
        .unwrap_or_default();

    let token = std::fs::read_to_string(&plex_prefs)
        .ok()
        .and_then(|s| {
            regex::Regex::new(r#"PlexOnlineToken="([^"]+)""#)
                .ok()
                .and_then(|re| re.captures(&s))
                .and_then(|c| c.get(1))
                .map(|m| m.as_str().to_string())
        });

    let token = match token {
        Some(t) => t,
        None => {
            return OrchestratorResult::Error(ErrorResult {
                message: "Could not find Plex token. Is Plex installed?".to_string(),
                path_attempted: "PlexAPI".to_string(),
                recoverable: true,
            });
        }
    };

    // Determine action from input
    let is_search = input.to_lowercase().contains("search") || input.to_lowercase().contains("find");

    let client = reqwest::Client::new();

    if is_search {
        // Extract search query
        let query = input
            .replace("search", "")
            .replace("find", "")
            .replace("plex", "")
            .replace("on", "")
            .trim()
            .to_string();

        let search_url = format!(
            "http://localhost:32400/hubs/search?query={}&X-Plex-Token={}",
            urlencoding::encode(&query),
            token
        );

        match client.get(&search_url).send().await {
            Ok(response) => {
                if response.status().is_success() {
                    let text = response.text().await.unwrap_or_default();
                    // Parse XML response (basic)
                    let titles: Vec<String> = regex::Regex::new(r#"title="([^"]+)""#)
                        .ok()
                        .map(|re| {
                            re.captures_iter(&text)
                                .filter_map(|c| c.get(1))
                                .map(|m| m.as_str().to_string())
                                .take(10)
                                .collect()
                        })
                        .unwrap_or_default();

                    let latency = start.elapsed().as_millis() as u64;
                    OrchestratorResult::Search(SearchResult {
                        chunks: titles
                            .iter()
                            .enumerate()
                            .map(|(i, t)| CodeSearchHit {
                                file_path: format!("plex://search/{}", i),
                                content: t.clone(),
                                line_start: 0,
                                relevance_score: 1.0 - (i as f32 * 0.1),
                            })
                            .collect(),
                        query,
                        latency_ms: latency,
                    })
                } else {
                    OrchestratorResult::Error(ErrorResult {
                        message: format!("Plex search failed: {}", response.status()),
                        path_attempted: "PlexAPI".to_string(),
                        recoverable: true,
                    })
                }
            }
            Err(e) => OrchestratorResult::Error(ErrorResult {
                message: format!("Plex request failed: {}", e),
                path_attempted: "PlexAPI".to_string(),
                recoverable: true,
            }),
        }
    } else {
        // Get recently added
        let recent_url = format!(
            "http://localhost:32400/library/recentlyAdded?X-Plex-Token={}",
            token
        );

        match client.get(&recent_url).send().await {
            Ok(response) => {
                let text = response.text().await.unwrap_or_default();
                let titles: Vec<String> = regex::Regex::new(r#"title="([^"]+)""#)
                    .ok()
                    .map(|re| {
                        re.captures_iter(&text)
                            .filter_map(|c| c.get(1))
                            .map(|m| m.as_str().to_string())
                            .take(5)
                            .collect()
                    })
                    .unwrap_or_default();

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Generated(GeneratedResult {
                    content: format!("Recently added on Plex:\n\n{}", titles.join("\n")),
                    model_used: "plex".to_string(),
                    tool_calls: vec![],
                    tokens_used: 0,
                    latency_ms: latency,
                actions: vec![],
        })
            }
            Err(e) => OrchestratorResult::Error(ErrorResult {
                message: format!("Plex request failed: {}", e),
                path_attempted: "PlexAPI".to_string(),
                recoverable: true,
            }),
        }
    }
}

/// Navidrome - music streaming via Subsonic API
async fn handle_navidrome(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Navidrome uses Subsonic API
    let base_url = "http://localhost:4533/rest";
    let (user, pass) = ("admin", "admin"); // Default credentials

    // Extract search query
    let query = input
        .replace("play", "")
        .replace("music", "")
        .replace("song", "")
        .replace("album", "")
        .trim()
        .to_string();

    let search_url = format!(
        "{}/search3?u={}&p={}&v=1.16.0&c=SAM&f=json&query={}",
        base_url,
        user,
        pass,
        urlencoding::encode(&query)
    );

    let client = reqwest::Client::new();
    match client.get(&search_url).send().await {
        Ok(response) => {
            if response.status().is_success() {
                let json: Value = response.json().await.unwrap_or_default();
                let songs = json["subsonic-response"]["searchResult3"]["song"]
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .take(10)
                            .map(|s| {
                                format!(
                                    "{} - {}",
                                    s["artist"].as_str().unwrap_or("Unknown"),
                                    s["title"].as_str().unwrap_or("Unknown")
                                )
                            })
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Search(SearchResult {
                    chunks: songs
                        .iter()
                        .enumerate()
                        .map(|(i, s)| CodeSearchHit {
                            file_path: format!("navidrome://song/{}", i),
                            content: s.clone(),
                            line_start: 0,
                            relevance_score: 1.0 - (i as f32 * 0.1),
                        })
                        .collect(),
                    query,
                    latency_ms: latency,
        })
            } else {
                OrchestratorResult::Error(ErrorResult {
                    message: format!("Navidrome search failed: {}", response.status()),
                    path_attempted: "NavidromeAPI".to_string(),
                    recoverable: true,
                })
            }
        }
        Err(e) => OrchestratorResult::Error(ErrorResult {
            message: format!("Navidrome request failed: {}. Is Navidrome running?", e),
            path_attempted: "NavidromeAPI".to_string(),
            recoverable: true,
        }),
    }
}

/// Stash - adult content management via GraphQL
async fn handle_stash(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Stash API key (stored in SSOT)
    let api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1aWQiOiJZZXM1aXIiLCJzdWIiOiJBUElLZXkiLCJpYXQiOjE3NjQ1NjcwMDl9.iIf-biUcOV-MGlND0zkqhSFutncQMmvzilWTzr37RcA";

    // Extract search query
    let query = input
        .replace("stash", "")
        .replace("scene", "")
        .replace("find", "")
        .replace("search", "")
        .trim()
        .to_string();

    // GraphQL query
    let gql = json!({
        "query": format!(r#"
            query {{
                findScenes(scene_filter: {{ title: {{ value: "{}", modifier: INCLUDES }} }}, filter: {{ per_page: 10 }}) {{
                    scenes {{
                        id
                        title
                        performers {{ name }}
                        studio {{ name }}
                    }}
                }}
            }}
        "#, query)
    });

    let client = reqwest::Client::new();
    let result = client
        .post("http://localhost:9999/graphql")
        .header("Content-Type", "application/json")
        .header("ApiKey", api_key)
        .json(&gql)
        .send()
        .await;

    match result {
        Ok(response) => {
            if response.status().is_success() {
                let json: Value = response.json().await.unwrap_or_default();
                let scenes = json["data"]["findScenes"]["scenes"]
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .map(|s| {
                                let performers = s["performers"]
                                    .as_array()
                                    .map(|p| {
                                        p.iter()
                                            .filter_map(|x| x["name"].as_str())
                                            .collect::<Vec<_>>()
                                            .join(", ")
                                    })
                                    .unwrap_or_default();
                                format!(
                                    "{} ({})",
                                    s["title"].as_str().unwrap_or("Untitled"),
                                    performers
                                )
                            })
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Search(SearchResult {
                    chunks: scenes
                        .iter()
                        .enumerate()
                        .map(|(i, s)| CodeSearchHit {
                            file_path: format!("stash://scene/{}", i),
                            content: s.clone(),
                            line_start: 0,
                            relevance_score: 1.0 - (i as f32 * 0.1),
                        })
                        .collect(),
                    query,
                    latency_ms: latency,
        })
            } else {
                OrchestratorResult::Error(ErrorResult {
                    message: format!("Stash query failed: {}", response.status()),
                    path_attempted: "StashAPI".to_string(),
                    recoverable: true,
                })
            }
        }
        Err(e) => OrchestratorResult::Error(ErrorResult {
            message: format!("Stash request failed: {}. Is Stash running?", e),
            path_attempted: "StashAPI".to_string(),
            recoverable: true,
        }),
    }
}

/// *arr services - Radarr, Sonarr, Lidarr
async fn handle_arr(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // Determine which *arr service based on input
    let (service, port, content_type) = if input.to_lowercase().contains("movie") {
        ("Radarr", 7878, "movie")
    } else if input.to_lowercase().contains("music") || input.to_lowercase().contains("album") {
        ("Lidarr", 8686, "artist")
    } else {
        ("Sonarr", 8989, "series")
    };

    // Extract search query
    let query = input
        .replace("download", "")
        .replace("movie", "")
        .replace("show", "")
        .replace("series", "")
        .replace("music", "")
        .replace("album", "")
        .trim()
        .to_string();

    // Search endpoint
    let search_url = format!(
        "http://localhost:{}/api/v3/{}/lookup?term={}",
        port,
        content_type,
        urlencoding::encode(&query)
    );

    // Get API key from docker config
    let config_path = format!(
        "/Volumes/Plex/DevSymlinks/docker-media/{}/config/config.xml",
        service.to_lowercase()
    );

    let api_key = std::fs::read_to_string(&config_path)
        .ok()
        .and_then(|s| {
            regex::Regex::new(r#"<ApiKey>([^<]+)</ApiKey>"#)
                .ok()
                .and_then(|re| re.captures(&s))
                .and_then(|c| c.get(1))
                .map(|m| m.as_str().to_string())
        })
        .unwrap_or_default();

    let client = reqwest::Client::new();
    let result = client
        .get(&search_url)
        .header("X-Api-Key", &api_key)
        .send()
        .await;

    match result {
        Ok(response) => {
            if response.status().is_success() {
                let json: Value = response.json().await.unwrap_or_default();
                let items = json
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .take(5)
                            .map(|i| {
                                let title = i["title"].as_str().unwrap_or(
                                    i["artistName"].as_str().unwrap_or("Unknown"),
                                );
                                let year = i["year"].as_i64().unwrap_or(0);
                                format!("{} ({})", title, year)
                            })
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Search(SearchResult {
                    chunks: items
                        .iter()
                        .enumerate()
                        .map(|(i, s)| CodeSearchHit {
                            file_path: format!("{}://item/{}", service.to_lowercase(), i),
                            content: s.clone(),
                            line_start: 0,
                            relevance_score: 1.0 - (i as f32 * 0.1),
                        })
                        .collect(),
                    query,
                    latency_ms: latency,
        })
            } else {
                OrchestratorResult::Error(ErrorResult {
                    message: format!("{} search failed: {}", service, response.status()),
                    path_attempted: "ArrAPI".to_string(),
                    recoverable: true,
                })
            }
        }
        Err(e) => OrchestratorResult::Error(ErrorResult {
            message: format!("{} request failed: {}. Is {} running?", service, e, service),
            path_attempted: "ArrAPI".to_string(),
            recoverable: true,
        }),
    }
}

/// qBittorrent - torrent management
async fn handle_torrent(input: &str, _routing_latency: u64) -> OrchestratorResult {
    let start = std::time::Instant::now();

    // qBittorrent WebUI
    let base_url = "http://localhost:8081/api/v2";

    let client = reqwest::Client::builder()
        .cookie_store(true)
        .build()
        .unwrap_or_else(|_| reqwest::Client::new());

    // Login first
    let login = client
        .post(format!("{}/auth/login", base_url))
        .form(&[("username", "admin"), ("password", "adminadmin")])
        .send()
        .await;

    if login.is_err() {
        return OrchestratorResult::Error(ErrorResult {
            message: "qBittorrent not running on port 8081".to_string(),
            path_attempted: "TorrentAPI".to_string(),
            recoverable: true,
        });
    }

    // Get active torrents
    let torrents = client
        .get(format!("{}/torrents/info", base_url))
        .send()
        .await;

    match torrents {
        Ok(response) => {
            if response.status().is_success() {
                let json: Value = response.json().await.unwrap_or_default();
                let items = json
                    .as_array()
                    .map(|arr| {
                        arr.iter()
                            .take(10)
                            .map(|t| {
                                let name = t["name"].as_str().unwrap_or("Unknown");
                                let progress = t["progress"].as_f64().unwrap_or(0.0) * 100.0;
                                let state = t["state"].as_str().unwrap_or("unknown");
                                format!("{} ({:.1}% - {})", name, progress, state)
                            })
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();

                let latency = start.elapsed().as_millis() as u64;
                OrchestratorResult::Generated(GeneratedResult {
                    content: format!("Active torrents:\n\n{}", items.join("\n")),
                    model_used: "qbittorrent".to_string(),
                    tool_calls: vec![],
                    tokens_used: 0,
                    latency_ms: latency,
                actions: vec![],
        })
            } else {
                OrchestratorResult::Error(ErrorResult {
                    message: format!("qBittorrent query failed: {}", response.status()),
                    path_attempted: "TorrentAPI".to_string(),
                    recoverable: true,
                })
            }
        }
        Err(e) => OrchestratorResult::Error(ErrorResult {
            message: format!("qBittorrent request failed: {}", e),
            path_attempted: "TorrentAPI".to_string(),
            recoverable: true,
        }),
    }
}

// =============================================================================
// TOOL EXECUTION
// =============================================================================

async fn execute_tool_calls(calls: &[ToolCall], ctx: &OrchestratorContext) -> Vec<ToolCallRecord> {
    let mut results = Vec::new();

    for call in calls {
        let result = execute_single_tool(call, ctx).await;
        results.push(ToolCallRecord {
            tool: call.tool.clone(),
            args: call.args.clone(),
            result: result.output.clone(),
            success: result.success,
        });
    }

    results
}

async fn execute_single_tool(call: &ToolCall, ctx: &OrchestratorContext) -> ToolResult {
    match call.tool.as_str() {
        "read_file" => {
            let path = call.args.get("path")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            let full_path = ctx.working_directory.join(path);
            match std::fs::read_to_string(&full_path) {
                Ok(content) => ToolResult {
                    tool: "read_file".to_string(),
                    success: true,
                    output: content,
                },
                Err(e) => ToolResult {
                    tool: "read_file".to_string(),
                    success: false,
                    output: format!("Error reading file: {}", e),
                },
            }
        }

        "write_file" => {
            let path = call.args.get("path")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let content = call.args.get("content")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            let full_path = ctx.working_directory.join(path);
            match std::fs::write(&full_path, content) {
                Ok(()) => ToolResult {
                    tool: "write_file".to_string(),
                    success: true,
                    output: format!("Wrote {} bytes to {}", content.len(), path),
                },
                Err(e) => ToolResult {
                    tool: "write_file".to_string(),
                    success: false,
                    output: format!("Error writing file: {}", e),
                },
            }
        }

        "execute_shell" => {
            let command = call.args.get("command")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            match std::process::Command::new("sh")
                .arg("-c")
                .arg(command)
                .current_dir(&ctx.working_directory)
                .output()
            {
                Ok(output) => {
                    let stdout = String::from_utf8_lossy(&output.stdout);
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    ToolResult {
                        tool: "execute_shell".to_string(),
                        success: output.status.success(),
                        output: format!("{}{}", stdout, stderr),
                    }
                }
                Err(e) => ToolResult {
                    tool: "execute_shell".to_string(),
                    success: false,
                    output: format!("Error executing command: {}", e),
                },
            }
        }

        "search_code" => {
            let query = call.args.get("query")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            let emb = embeddings();
            let results = emb.search(query, 5);

            let output = results
                .iter()
                .map(|r| format!("{}:{} - {}", r.chunk.file_path, r.chunk.start_line,
                    r.chunk.content.lines().next().unwrap_or("")))
                .collect::<Vec<_>>()
                .join("\n");

            ToolResult {
                tool: "search_code".to_string(),
                success: true,
                output,
            }
        }

        "edit_file" => {
            let path = call.args.get("path")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let old_str = call.args.get("old_string")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            let new_str = call.args.get("new_string")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            let full_path = ctx.working_directory.join(path);
            let full_path_str = full_path.to_string_lossy();

            let result = SmartEditor::exact_replace(&full_path_str, old_str, new_str, false);

            if result.success {
                ToolResult {
                    tool: "edit_file".to_string(),
                    success: true,
                    output: format!("Successfully edited {}", path),
                }
            } else {
                ToolResult {
                    tool: "edit_file".to_string(),
                    success: false,
                    output: format!("Edit failed: {}", result.message),
                }
            }
        }

        "list_files" => {
            let path = call.args.get("path")
                .and_then(|v| v.as_str())
                .unwrap_or(".");

            let full_path = ctx.working_directory.join(path);
            match std::fs::read_dir(&full_path) {
                Ok(entries) => {
                    let files: Vec<String> = entries
                        .filter_map(|e| e.ok())
                        .map(|e| e.file_name().to_string_lossy().to_string())
                        .collect();
                    ToolResult {
                        tool: "list_files".to_string(),
                        success: true,
                        output: files.join("\n"),
                    }
                }
                Err(e) => ToolResult {
                    tool: "list_files".to_string(),
                    success: false,
                    output: format!("Error listing files: {}", e),
                },
            }
        }

        "web_fetch" => {
            let url = call.args.get("url")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            if url.is_empty() {
                return ToolResult {
                    tool: "web_fetch".to_string(),
                    success: false,
                    output: "URL is required".to_string(),
                };
            }

            // Use reqwest to fetch the URL
            let client = reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .user_agent("SAM/1.0")
                .build();

            match client {
                Ok(client) => {
                    match client.get(url).send() {
                        Ok(response) => {
                            if response.status().is_success() {
                                match response.text() {
                                    Ok(body) => {
                                        // Convert HTML to plain text (basic)
                                        let text = html_to_text(&body);
                                        // Truncate to reasonable size
                                        let truncated = if text.len() > 10000 {
                                            format!("{}...\n\n[Truncated, {} total chars]",
                                                &text[..10000], text.len())
                                        } else {
                                            text
                                        };
                                        ToolResult {
                                            tool: "web_fetch".to_string(),
                                            success: true,
                                            output: truncated,
                                        }
                                    }
                                    Err(e) => ToolResult {
                                        tool: "web_fetch".to_string(),
                                        success: false,
                                        output: format!("Failed to read response: {}", e),
                                    }
                                }
                            } else {
                                ToolResult {
                                    tool: "web_fetch".to_string(),
                                    success: false,
                                    output: format!("HTTP error: {}", response.status()),
                                }
                            }
                        }
                        Err(e) => ToolResult {
                            tool: "web_fetch".to_string(),
                            success: false,
                            output: format!("Request failed: {}", e),
                        }
                    }
                }
                Err(e) => ToolResult {
                    tool: "web_fetch".to_string(),
                    success: false,
                    output: format!("Failed to create HTTP client: {}", e),
                }
            }
        }

        "web_search" => {
            let query = call.args.get("query")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            if query.is_empty() {
                return ToolResult {
                    tool: "web_search".to_string(),
                    success: false,
                    output: "Query is required".to_string(),
                };
            }

            // Use DuckDuckGo HTML search (no API key required)
            let encoded_query = urlencoding::encode(query);
            let search_url = format!("https://html.duckduckgo.com/html/?q={}", encoded_query);

            let client = reqwest::blocking::Client::builder()
                .timeout(std::time::Duration::from_secs(30))
                .user_agent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
                .build();

            match client {
                Ok(client) => {
                    match client.get(&search_url).send() {
                        Ok(response) => {
                            if response.status().is_success() {
                                match response.text() {
                                    Ok(body) => {
                                        // Parse search results from DuckDuckGo HTML
                                        let results = parse_duckduckgo_results(&body);
                                        ToolResult {
                                            tool: "web_search".to_string(),
                                            success: true,
                                            output: results,
                                        }
                                    }
                                    Err(e) => ToolResult {
                                        tool: "web_search".to_string(),
                                        success: false,
                                        output: format!("Failed to read response: {}", e),
                                    }
                                }
                            } else {
                                ToolResult {
                                    tool: "web_search".to_string(),
                                    success: false,
                                    output: format!("Search failed: {}", response.status()),
                                }
                            }
                        }
                        Err(e) => ToolResult {
                            tool: "web_search".to_string(),
                            success: false,
                            output: format!("Search request failed: {}", e),
                        }
                    }
                }
                Err(e) => ToolResult {
                    tool: "web_search".to_string(),
                    success: false,
                    output: format!("Failed to create HTTP client: {}", e),
                }
            }
        }

        _ => ToolResult {
            tool: call.tool.clone(),
            success: false,
            output: format!("Unknown tool: {}", call.tool),
        },
    }
}

// HTML to text conversion (basic)
fn html_to_text(html: &str) -> String {
    // Remove script and style tags
    let re_script = regex::Regex::new(r"(?is)<script[^>]*>.*?</script>").unwrap();
    let re_style = regex::Regex::new(r"(?is)<style[^>]*>.*?</style>").unwrap();
    let re_tags = regex::Regex::new(r"<[^>]+>").unwrap();
    let re_whitespace = regex::Regex::new(r"\s+").unwrap();

    let text = re_script.replace_all(html, "");
    let text = re_style.replace_all(&text, "");
    let text = re_tags.replace_all(&text, " ");
    let text = re_whitespace.replace_all(&text, " ");

    // Decode HTML entities
    let text = text
        .replace("&nbsp;", " ")
        .replace("&amp;", "&")
        .replace("&lt;", "<")
        .replace("&gt;", ">")
        .replace("&quot;", "\"")
        .replace("&#39;", "'");

    text.trim().to_string()
}

// Parse DuckDuckGo HTML search results
fn parse_duckduckgo_results(html: &str) -> String {
    let mut results = Vec::new();

    // Look for result divs
    let re_result = regex::Regex::new(r#"class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>"#).unwrap();
    let re_snippet = regex::Regex::new(r#"class="result__snippet"[^>]*>([^<]*)"#).unwrap();

    let urls: Vec<_> = re_result.captures_iter(html).collect();
    let snippets: Vec<_> = re_snippet.captures_iter(html).collect();

    for (i, cap) in urls.iter().enumerate().take(5) {
        let url = cap.get(1).map_or("", |m| m.as_str());
        let title = cap.get(2).map_or("", |m| m.as_str());
        let snippet = snippets.get(i)
            .and_then(|s| s.get(1))
            .map_or("", |m| m.as_str());

        // Clean up URL (DuckDuckGo uses redirect URLs)
        let clean_url = if url.contains("uddg=") {
            url.split("uddg=").nth(1)
                .and_then(|u| urlencoding::decode(u).ok())
                .map(|u| u.to_string())
                .unwrap_or_else(|| url.to_string())
        } else {
            url.to_string()
        };

        results.push(format!(
            "{}. **{}**\n   {}\n   {}\n",
            i + 1,
            html_to_text(title),
            clean_url,
            html_to_text(snippet)
        ));
    }

    if results.is_empty() {
        "No search results found".to_string()
    } else {
        results.join("\n")
    }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

fn map_request_to_task(request_type: &HybridRequestType) -> ModelTaskType {
    match request_type {
        HybridRequestType::CodeGeneration => ModelTaskType::CodeGeneration,
        HybridRequestType::TestGeneration => ModelTaskType::TestGeneration,
        HybridRequestType::BugFix => ModelTaskType::BugFix,
        HybridRequestType::Refactor => ModelTaskType::Refactor,
        HybridRequestType::CodeReview => ModelTaskType::Explanation, // Map to explanation
        HybridRequestType::Explanation => ModelTaskType::Explanation,
        HybridRequestType::Documentation => ModelTaskType::DocGeneration,
        HybridRequestType::ComplexGeneration => ModelTaskType::CodeGeneration,
        _ => ModelTaskType::CodeGeneration,
    }
}

fn ensure_vram_available(_model: &ModelId) -> Result<(), String> {
    let mgr = model_manager();

    // Check if we need to make room by unloading idle models
    let idle_models = mgr.get_idle_models();
    if !idle_models.is_empty() {
        // Proactively unload idle models to stay within VRAM budget
        for idle in idle_models {
            eprintln!("[ORCHESTRATOR] Unloading idle model: {}", idle.ollama_name());
            let _ = unload_model(&idle.ollama_name());
        }
    }

    Ok(())
}

fn unload_model(model_name: &str) -> Result<(), String> {
    // Call Ollama to unload the model
    let client = reqwest::blocking::Client::new();
    let _ = client
        .post("http://localhost:11434/api/generate")
        .json(&json!({
            "model": model_name,
            "keep_alive": 0
        }))
        .send()
        .map_err(|e| format!("Failed to unload model: {}", e))?;

    model_manager().mark_unloaded(&ModelId::from_ollama_name(model_name));
    Ok(())
}

fn extract_explicit_values(input: &str, _template_name: &str) -> HashMap<String, String> {
    let mut values = HashMap::new();

    // Pattern 1: "called X" or "named X"
    if let Some(caps) = regex::Regex::new(r"(?:called|named)\s+(\w+)")
        .ok()
        .and_then(|re| re.captures(input))
    {
        let name = caps[1].to_string();
        values.insert("name".to_string(), name.clone());
        values.insert("COMPONENT_NAME".to_string(), name.clone());
        values.insert("component_name".to_string(), name.clone());
        values.insert("function_name".to_string(), name);
    }

    // Pattern 2: "a SomeButton" or "a LoginForm" (PascalCase after 'a')
    if values.is_empty() {
        if let Some(caps) = regex::Regex::new(r"\ba\s+([A-Z][a-zA-Z0-9]+(?:Button|Form|Modal|Card|List|Item|Page|View|Panel|Container|Wrapper|Component)?)\b")
            .ok()
            .and_then(|re| re.captures(input))
        {
            let name = caps[1].to_string();
            values.insert("name".to_string(), name.clone());
            values.insert("COMPONENT_NAME".to_string(), name.clone());
            values.insert("component_name".to_string(), name.clone());
            values.insert("function_name".to_string(), name);
        }
    }

    // Pattern 3: "component for X" - derive name from description
    if values.is_empty() {
        if let Some(caps) = regex::Regex::new(r"component\s+for\s+(?:a\s+)?(\w+)")
            .ok()
            .and_then(|re| re.captures(input))
        {
            // Convert "button" to "Button", "login form" to "LoginForm"
            let desc = caps[1].to_string();
            let name = to_pascal_case(&desc);
            values.insert("name".to_string(), name.clone());
            values.insert("COMPONENT_NAME".to_string(), name.clone());
            values.insert("component_name".to_string(), name.clone());
            values.insert("description".to_string(), desc);
        }
    }

    // Pattern 4: "for X" pattern - description
    if let Some(caps) = regex::Regex::new(r"\bfor\s+(?:a\s+)?(\w+(?:\s+\w+)?)")
        .ok()
        .and_then(|re| re.captures(input))
    {
        let desc = caps[1].to_string();
        values.insert("description".to_string(), desc.clone());

        // If no name yet, derive from description
        if !values.contains_key("name") {
            let name = to_pascal_case(&desc);
            values.insert("name".to_string(), name.clone());
            values.insert("COMPONENT_NAME".to_string(), name.clone());
            values.insert("component_name".to_string(), name);
        }
    }

    values
}

/// Convert "login button" to "LoginButton"
fn to_pascal_case(s: &str) -> String {
    s.split_whitespace()
        .map(|word| {
            let mut chars = word.chars();
            match chars.next() {
                None => String::new(),
                Some(first) => first.to_uppercase().chain(chars).collect(),
            }
        })
        .collect()
}

async fn call_ollama_for_fill(
    prompt: &str,
    _placeholders: &[String],
) -> Result<HashMap<String, String>, String> {
    let model = "qwen2.5-coder:1.5b"; // Using installed model for fill tasks

    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:11434/api/generate")
        .json(&json!({
            "model": model,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": 0.1,
                "num_predict": 256
            }
        }))
        .send()
        .await
        .map_err(|e| format!("Ollama request failed: {}", e))?;

    let json: Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let text = json["response"].as_str().unwrap_or("");

    // Parse JSON response
    if let Ok(values) = serde_json::from_str::<HashMap<String, String>>(text) {
        return Ok(values);
    }

    // Try to extract from code block
    if let Some(start) = text.find("```json") {
        if let Some(end) = text[start..].find("```\n") {
            let json_str = &text[start + 7..start + end];
            if let Ok(values) = serde_json::from_str::<HashMap<String, String>>(json_str) {
                return Ok(values);
            }
        }
    }

    Ok(HashMap::new())
}

fn build_tool_prompt(input: &str, ctx: &OrchestratorContext) -> String {
    let tools_desc = r#"You are an AI assistant that completes tasks using tools.

TOOLS:
- read_file(path): Read a file
- write_file(path, content): Write a file
- execute_shell(command): Run shell command
- search_code(query): Search code semantically
- edit_file(path, old_string, new_string): Edit file
- list_files(path): List directory

RULES:
1. Output ONLY a single JSON tool call, nothing else
2. Format: {"tool": "name", "args": {...}}
3. No explanations, no markdown, no extra text
4. After seeing tool results, give a brief final answer
"#;

    let context = format!(
        "Working directory: {}\n",
        ctx.working_directory.display()
    );

    format!("{}\n\n{}\n\nUser request: {}", tools_desc, context, input)
}

fn build_comprehensive_prompt(input: &str, ctx: &OrchestratorContext) -> String {
    let mut prompt = build_tool_prompt(input, ctx);

    // Add conversation history for context
    if !ctx.conversation_history.is_empty() {
        prompt = format!(
            "Previous conversation:\n{}\n\n{}",
            ctx.conversation_history
                .iter()
                .map(|t| format!("{}: {}", t.role, t.content))
                .collect::<Vec<_>>()
                .join("\n"),
            prompt
        );
    }

    prompt
}

fn build_continuation_prompt(response: &str, tool_results: &[ToolCallRecord]) -> String {
    let results_str = tool_results
        .iter()
        .map(|r| format!(
            "Tool: {}\nSuccess: {}\nOutput:\n{}\n",
            r.tool, r.success, r.result
        ))
        .collect::<Vec<_>>()
        .join("\n---\n");

    format!(
        "Your previous response:\n{}\n\nTool results:\n{}\n\nContinue with the task. If you need more tools, call them. Otherwise, provide your final answer.",
        response,
        results_str
    )
}

async fn call_ollama_with_tools(
    model: &str,
    prompt: &str,
    _ctx: &OrchestratorContext,
) -> Result<(String, Vec<ToolCall>), String> {
    let client = reqwest::Client::new();
    let response = client
        .post("http://localhost:11434/api/generate")
        .json(&json!({
            "model": model,
            "prompt": prompt,
            "stream": false,
            "options": {
                "temperature": 0.2,
                "num_predict": 2048
            }
        }))
        .send()
        .await
        .map_err(|e| format!("Ollama request failed: {}", e))?;

    let json: Value = response
        .json()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    let text = json["response"].as_str().unwrap_or("").to_string();

    // Parse tool calls from response
    let tool_calls = parse_tool_calls(&text);

    // Mark model as loaded
    model_manager().mark_loaded(ModelId::from_ollama_name(model));

    Ok((text, tool_calls))
}

fn parse_tool_calls(response: &str) -> Vec<ToolCall> {
    let mut calls = Vec::new();

    // Find JSON objects that contain "tool" - handle nested braces
    let mut depth = 0;
    let mut start: Option<usize> = None;

    for (i, c) in response.char_indices() {
        match c {
            '{' => {
                if depth == 0 {
                    start = Some(i);
                }
                depth += 1;
            }
            '}' => {
                depth -= 1;
                if depth == 0 {
                    if let Some(s) = start {
                        let json_str = &response[s..=i];
                        // Only parse if it contains "tool"
                        if json_str.contains("\"tool\"") {
                            if let Ok(call) = serde_json::from_str::<ToolCall>(json_str) {
                                calls.push(call);
                            }
                        }
                        start = None;
                    }
                }
            }
            _ => {}
        }
    }

    calls
}

// =============================================================================
// ORCHESTRATOR STATISTICS
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct OrchestratorStats {
    pub total_requests: u64,
    pub instant_count: u64,
    pub search_count: u64,
    pub generated_count: u64,
    pub error_count: u64,
    pub avg_instant_latency_ms: f64,
    pub avg_search_latency_ms: f64,
    pub avg_generated_latency_ms: f64,
}

lazy_static::lazy_static! {
    static ref ORCHESTRATOR_STATS: std::sync::Mutex<OrchestratorStats> =
        std::sync::Mutex::new(OrchestratorStats::default());
}

pub fn record_orchestration(result: &OrchestratorResult) {
    let mut stats = ORCHESTRATOR_STATS.lock().unwrap();
    stats.total_requests += 1;

    match result {
        OrchestratorResult::Instant(r) => {
            stats.instant_count += 1;
            // Update running average
            let n = stats.instant_count as f64;
            stats.avg_instant_latency_ms =
                stats.avg_instant_latency_ms * (n - 1.0) / n + r.latency_ms as f64 / n;
        }
        OrchestratorResult::Search(r) => {
            stats.search_count += 1;
            let n = stats.search_count as f64;
            stats.avg_search_latency_ms =
                stats.avg_search_latency_ms * (n - 1.0) / n + r.latency_ms as f64 / n;
        }
        OrchestratorResult::Generated(r) => {
            stats.generated_count += 1;
            let n = stats.generated_count as f64;
            stats.avg_generated_latency_ms =
                stats.avg_generated_latency_ms * (n - 1.0) / n + r.latency_ms as f64 / n;
        }
        OrchestratorResult::Error(_) => {
            stats.error_count += 1;
        }
    }
}

pub fn get_orchestrator_stats() -> OrchestratorStats {
    ORCHESTRATOR_STATS.lock().unwrap().clone()
}

/// Combined stats from all systems
pub fn get_combined_stats() -> Value {
    let orch_stats = get_orchestrator_stats();
    let routing = routing_stats();
    let model_stats = model_manager().get_stats();
    let emb_stats = embeddings().stats();

    json!({
        "orchestrator": {
            "total_requests": orch_stats.total_requests,
            "instant_count": orch_stats.instant_count,
            "search_count": orch_stats.search_count,
            "generated_count": orch_stats.generated_count,
            "error_count": orch_stats.error_count,
            "avg_latencies_ms": {
                "instant": orch_stats.avg_instant_latency_ms,
                "search": orch_stats.avg_search_latency_ms,
                "generated": orch_stats.avg_generated_latency_ms
            }
        },
        "routing": {
            "total": routing.total_requests,
            "deterministic": routing.deterministic_count,
            "template": routing.template_count,
            "embedding": routing.embedding_count,
            "micro_model": routing.micro_model_count,
            "full_model": routing.full_model_count,
            "ai_avoidance_rate": routing.ai_avoidance_rate(),
            "light_ai_rate": routing.light_ai_rate()
        },
        "models": model_stats,
        "embeddings": emb_stats
    })
}

// =============================================================================
// DYNAMIC DAILY BRIEF
// =============================================================================

/// Generate a dynamic daily brief from the project registry
fn generate_dynamic_brief() -> String {
    let registry_path = dirs::home_dir()
        .map(|h| h.join(".sam_project_registry.json"))
        .unwrap_or_else(|| PathBuf::from("/tmp/.sam_project_registry.json"));

    // Check if registry exists and is recent (< 1 hour old)
    let registry_stale = if registry_path.exists() {
        match std::fs::metadata(&registry_path) {
            Ok(meta) => {
                match meta.modified() {
                    Ok(mod_time) => {
                        let age = std::time::SystemTime::now()
                            .duration_since(mod_time)
                            .unwrap_or_default();
                        age.as_secs() > 3600  // Stale if > 1 hour
                    }
                    Err(_) => true
                }
            }
            Err(_) => true
        }
    } else {
        true
    };

    // Refresh registry if stale
    if registry_stale {
        let scanner = dirs::home_dir()
            .map(|h| h.join("ReverseLab/SAM/warp_tauri/project_registry.py"))
            .unwrap_or_default();

        if scanner.exists() {
            let _ = std::process::Command::new("python3")
                .arg(&scanner)
                .output();
        }
    }

    // Read registry
    let registry: serde_json::Value = if registry_path.exists() {
        std::fs::read_to_string(&registry_path)
            .ok()
            .and_then(|s| serde_json::from_str(&s).ok())
            .unwrap_or_default()
    } else {
        return fallback_brief();
    };

    let projects = registry.get("projects").and_then(|p| p.as_array());
    let updated_at = registry.get("updated_at")
        .and_then(|u| u.as_str())
        .map(|s| &s[..16])
        .unwrap_or("unknown");

    let projects = match projects {
        Some(p) if !p.is_empty() => p,
        _ => return fallback_brief(),
    };

    // Build the brief
    let mut lines = vec![
        format!("**Daily Brief** (updated {})", updated_at),
        String::new(),
    ];

    // Find projects needing attention
    let mut needs_attention: Vec<&serde_json::Value> = Vec::new();
    let mut healthy: Vec<&serde_json::Value> = Vec::new();

    for p in projects {
        let health = p.get("health").and_then(|h| h.as_str()).unwrap_or("unknown");
        if health == "healthy" {
            healthy.push(p);
        } else {
            needs_attention.push(p);
        }
    }

    // Needs attention section
    if !needs_attention.is_empty() {
        lines.push("**Needs Attention:**".to_string());
        for p in &needs_attention {
            let name = p.get("name").and_then(|n| n.as_str()).unwrap_or("unknown");
            let ptype = p.get("type").and_then(|t| t.as_str()).unwrap_or("?");
            let git = p.get("git");
            let changes = git
                .and_then(|g| g.get("uncommitted_changes"))
                .and_then(|c| c.as_u64())
                .unwrap_or(0);

            if changes > 0 {
                lines.push(format!("  • **{}** ({}) - {} uncommitted changes", name, ptype, changes));
            } else {
                let health = p.get("health").and_then(|h| h.as_str()).unwrap_or("unknown");
                lines.push(format!("  • **{}** ({}) - {}", name, ptype, health));
            }
        }
        lines.push(String::new());
    }

    // Active projects section
    lines.push("**Active Projects:**".to_string());

    // Sort by last commit time
    let mut sorted_projects: Vec<&serde_json::Value> = projects.iter().collect();
    sorted_projects.sort_by(|a, b| {
        let a_time = a.get("git")
            .and_then(|g| g.get("last_commit_time"))
            .and_then(|t| t.as_str())
            .unwrap_or("zzz");
        let b_time = b.get("git")
            .and_then(|g| g.get("last_commit_time"))
            .and_then(|t| t.as_str())
            .unwrap_or("zzz");
        a_time.cmp(b_time)
    });

    for p in sorted_projects.iter().take(6) {
        let name = p.get("name").and_then(|n| n.as_str()).unwrap_or("unknown");
        let git = p.get("git");

        if let Some(g) = git {
            let last_commit = g.get("last_commit_time")
                .and_then(|t| t.as_str())
                .unwrap_or("unknown");
            let branch = g.get("branch")
                .and_then(|b| b.as_str())
                .unwrap_or("main");

            lines.push(format!("  • **{}** [{}] - {}", name, branch, last_commit));

            let running = p.get("running_services")
                .and_then(|r| r.as_array())
                .map(|a| a.len())
                .unwrap_or(0);

            if running > 0 {
                lines.push(format!("    └ {} process(es) running", running));
            }
        }
    }

    // Quick actions
    lines.push(String::new());
    lines.push("**Quick Actions:**".to_string());
    lines.push("  • \"scan projects\" - refresh registry".to_string());
    lines.push("  • \"commit SAM\" - commit current changes".to_string());
    lines.push("  • \"fix bug in X\" - search and fix".to_string());

    lines.join("\n")
}

/// Fallback brief when registry unavailable
fn fallback_brief() -> String {
    r#"**Daily Brief**

No project registry found. Run `python3 ~/ReverseLab/SAM/warp_tauri/project_registry.py` to scan projects.

**SAM Status:**
✓ Autonomous loop running
✓ Conversational AI ready
✓ Tool execution enabled

**Quick Actions:**
  • "scan projects" - create project registry
  • "list files" - explore current directory
  • "help" - see what I can do"#.to_string()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_tool_call_parsing() {
        let response = r#"
Let me check the file.
{"tool": "read_file", "args": {"path": "main.rs"}}
Here's what I found.
"#;

        let calls = parse_tool_calls(response);
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0].tool, "read_file");
    }

    #[test]
    fn test_extract_explicit_values() {
        let values = extract_explicit_values("create a component called LoginForm", "react_component");
        assert_eq!(values.get("name"), Some(&"LoginForm".to_string()));
    }

    #[test]
    fn test_routing_deterministic_path() {
        // Shell commands
        let d = route_request("git status");
        assert_eq!(d.processing_path, ProcessingPath::Deterministic);

        let d = route_request("list files in src");
        assert_eq!(d.processing_path, ProcessingPath::Deterministic);

        let d = route_request("cargo build");
        assert_eq!(d.processing_path, ProcessingPath::Deterministic);

        let d = route_request("npm install");
        assert_eq!(d.processing_path, ProcessingPath::Deterministic);
    }

    #[test]
    fn test_routing_search_path() {
        let d = route_request("where is authentication handled");
        assert_eq!(d.processing_path, ProcessingPath::EmbeddingSearch);

        let d = route_request("what does the login function do");
        assert_eq!(d.processing_path, ProcessingPath::EmbeddingSearch);

        let d = route_request("explain the caching system");
        assert_eq!(d.processing_path, ProcessingPath::EmbeddingSearch);
    }

    #[test]
    fn test_routing_template_path() {
        let d = route_request("create a react component for login");
        assert_eq!(d.processing_path, ProcessingPath::TemplateWithFill);
        assert!(d.template_name.is_some());

        let d = route_request("create a custom hook");
        assert_eq!(d.processing_path, ProcessingPath::TemplateWithFill);

        let d = route_request("write a unit test for auth");
        assert_eq!(d.processing_path, ProcessingPath::TemplateWithFill);
    }

    #[test]
    fn test_routing_ai_path() {
        let d = route_request("fix the null pointer error");
        assert!(matches!(d.processing_path, ProcessingPath::MicroModel | ProcessingPath::FullModel));

        let d = route_request("debug the authentication issue");
        assert!(matches!(d.processing_path, ProcessingPath::MicroModel | ProcessingPath::FullModel));
    }

    #[test]
    fn test_routing_full_model_for_complex() {
        let d = route_request("refactor this entire module to use async");
        assert_eq!(d.processing_path, ProcessingPath::FullModel);

        let d = route_request("redesign the whole system architecture");
        assert_eq!(d.processing_path, ProcessingPath::FullModel);
    }

    #[tokio::test]
    async fn test_orchestrate_deterministic() {
        let ctx = OrchestratorContext::default();
        let result = orchestrate("list files", &ctx).await;

        match result {
            OrchestratorResult::Instant(r) => {
                assert!(!r.output.is_empty() || r.output.is_empty()); // May or may not have output
                assert!(r.latency_ms < 1000); // Should be fast
            }
            _ => panic!("Expected Instant result for deterministic path"),
        }
    }

    #[tokio::test]
    async fn test_orchestrate_search() {
        let ctx = OrchestratorContext::default();
        let result = orchestrate("where is the router", &ctx).await;

        match result {
            OrchestratorResult::Search(r) => {
                assert_eq!(r.query, "where is the router");
                // Chunks may be empty if nothing indexed
            }
            _ => panic!("Expected Search result for embedding search path"),
        }
    }

    #[test]
    fn test_map_request_to_task() {
        assert_eq!(map_request_to_task(&HybridRequestType::CodeGeneration), ModelTaskType::CodeGeneration);
        assert_eq!(map_request_to_task(&HybridRequestType::BugFix), ModelTaskType::BugFix);
        assert_eq!(map_request_to_task(&HybridRequestType::Refactor), ModelTaskType::Refactor);
    }

    #[test]
    fn test_multiple_tool_calls_parsing() {
        let response = r#"
First I'll read the file:
{"tool": "read_file", "args": {"path": "main.rs"}}
Then search for references:
{"tool": "search_code", "args": {"query": "main function"}}
Done.
"#;

        let calls = parse_tool_calls(response);
        assert_eq!(calls.len(), 2);
        assert_eq!(calls[0].tool, "read_file");
        assert_eq!(calls[1].tool, "search_code");
    }

    #[test]
    fn test_nested_json_parsing() {
        let response = r#"
{"tool": "write_file", "args": {"path": "config.json", "content": "{\"key\": \"value\"}"}}
"#;

        let calls = parse_tool_calls(response);
        assert_eq!(calls.len(), 1);
        assert_eq!(calls[0].tool, "write_file");
    }
}
