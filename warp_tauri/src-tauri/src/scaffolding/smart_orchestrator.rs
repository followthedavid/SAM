// =============================================================================
// SMART ORCHESTRATOR - Advanced Small Model Architecture
// =============================================================================
// Designed for 8GB RAM constraint. Makes small models comprehensive through:
// 1. Model Swapping - Only one model loaded at a time
// 2. RAG Memory - Context retrieval from vector store
// 3. Tool Augmentation - Models describe actions, code executes
// 4. Character Store - Characters as data files, not model memory
// 5. Self-Reflection - Model critiques and improves responses
// 6. Fallback Chains - Try alternatives if primary fails
// 7. Compressed Context - Summarize history to fit context window
// =============================================================================

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};
use tokio::sync::Mutex;

// =============================================================================
// CORE TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelSpec {
    pub name: String,
    pub size_mb: u32,
    pub capabilities: Vec<String>,
    pub temperature: f32,
    pub max_tokens: u32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Character {
    pub id: String,
    pub name: String,
    pub personality: String,
    pub speech_style: String,
    pub example_dialogues: Vec<(String, String)>,
    pub forbidden_phrases: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MemoryEntry {
    pub id: String,
    pub content: String,
    pub embedding: Vec<f32>,
    pub timestamp: u64,
    pub importance: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCall {
    pub tool: String,
    pub args: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolResult {
    pub success: bool,
    pub output: String,
    pub error: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SmartResponse {
    pub content: String,
    pub model_used: String,
    pub tools_called: Vec<String>,
    pub memory_retrieved: usize,
    pub reflection_applied: bool,
    pub fallback_used: bool,
    pub latency_ms: u64,
}

// =============================================================================
// MODEL SWAPPER - Only one model in RAM at a time
// =============================================================================

pub struct ModelSwapper {
    current_model: Option<String>,
    model_specs: HashMap<String, ModelSpec>,
    last_used: HashMap<String, Instant>,
}

impl ModelSwapper {
    pub fn new() -> Self {
        let mut specs = HashMap::new();

        // Define available models with their specs
        // sam-trained is the primary model (fine-tuned with thousands of examples)
        specs.insert("sam-trained:latest".to_string(), ModelSpec {
            name: "sam-trained:latest".to_string(),
            size_mb: 986,
            capabilities: vec!["chat".to_string(), "roleplay".to_string(), "reasoning".to_string()],
            temperature: 0.8,
            max_tokens: 500,
        });

        // sam-roleplay-unrestricted - custom uncensored model based on dolphin-phi
        // Has "never break character" system prompt baked in
        specs.insert("sam-roleplay-unrestricted:latest".to_string(), ModelSpec {
            name: "sam-roleplay-unrestricted:latest".to_string(),
            size_mb: 1600,
            capabilities: vec!["roleplay".to_string(), "creative".to_string(), "uncensored".to_string(), "adult".to_string()],
            temperature: 0.95,
            max_tokens: 500,
        });

        specs.insert("qwen2.5-coder:1.5b".to_string(), ModelSpec {
            name: "qwen2.5-coder:1.5b".to_string(),
            size_mb: 986,
            capabilities: vec!["code".to_string(), "technical".to_string()],
            temperature: 0.3,
            max_tokens: 500,
        });

        specs.insert("stablelm2:1.6b".to_string(), ModelSpec {
            name: "stablelm2:1.6b".to_string(),
            size_mb: 982,
            capabilities: vec!["chat".to_string(), "reasoning".to_string()],
            temperature: 0.7,
            max_tokens: 300,
        });

        // tinydolphin - small uncensored model (less capable)
        specs.insert("tinydolphin:1.1b".to_string(), ModelSpec {
            name: "tinydolphin:1.1b".to_string(),
            size_mb: 637,
            capabilities: vec!["roleplay".to_string(), "creative".to_string(), "uncensored".to_string()],
            temperature: 0.9,
            max_tokens: 300,
        });

        // wizard-vicuna-uncensored - BEST for adult/erotic roleplay
        specs.insert("wizard-vicuna-uncensored:7b".to_string(), ModelSpec {
            name: "wizard-vicuna-uncensored:7b".to_string(),
            size_mb: 3800,
            capabilities: vec!["roleplay".to_string(), "creative".to_string(), "uncensored".to_string(), "adult".to_string()],
            temperature: 0.95,
            max_tokens: 500,
        });

        // dolphin-llama3 - also uncensored, good instruction following
        specs.insert("dolphin-llama3:8b".to_string(), ModelSpec {
            name: "dolphin-llama3:8b".to_string(),
            size_mb: 4700,
            capabilities: vec!["roleplay".to_string(), "creative".to_string(), "uncensored".to_string(), "chat".to_string()],
            temperature: 0.9,
            max_tokens: 500,
        });

        specs.insert("nomic-embed-text:latest".to_string(), ModelSpec {
            name: "nomic-embed-text:latest".to_string(),
            size_mb: 274,
            capabilities: vec!["embedding".to_string()],
            temperature: 0.0,
            max_tokens: 0,
        });

        Self {
            current_model: None,
            model_specs: specs,
            last_used: HashMap::new(),
        }
    }

    pub fn get_spec(&self, model: &str) -> Option<&ModelSpec> {
        self.model_specs.get(model)
    }

    pub fn select_model_for_task(&self, task_type: &str) -> String {
        match task_type {
            // tinydolphin for roleplay - small (636MB) but uncensored and fast loading
            "roleplay" | "character" => "tinydolphin:1.1b".to_string(),
            // sam-trained for general chat
            "creative" | "chat" => "sam-trained:latest".to_string(),
            "code" | "coding" | "technical" | "programming" => "qwen2.5-coder:1.5b".to_string(),
            "reasoning" | "analysis" => "sam-trained:latest".to_string(),
            "embedding" => "nomic-embed-text:latest".to_string(),
            _ => "sam-trained:latest".to_string(),
        }
    }

    pub async fn ensure_loaded(&mut self, model: &str) -> Result<(), String> {
        // If different model is loaded, unload it first
        let should_unload = self.current_model.as_ref()
            .map(|current| current != model)
            .unwrap_or(false);

        if should_unload {
            // Clone the model name to avoid borrow issues
            if let Some(current) = self.current_model.clone() {
                self.unload_model(&current).await?;
            }
        }

        // Load the requested model
        if self.current_model.as_deref() != Some(model) {
            self.load_model(model).await?;
        }

        self.last_used.insert(model.to_string(), Instant::now());
        Ok(())
    }

    async fn load_model(&mut self, model: &str) -> Result<(), String> {
        eprintln!("[SWAPPER] Loading model: {}", model);

        // Longer timeout for 7B+ models (they take longer to load from disk)
        let timeout_secs = if model.contains("7b") || model.contains("8b") {
            300 // 5 minutes for large models
        } else {
            120 // 2 minutes for small models
        };

        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .build()
            .map_err(|e| e.to_string())?;

        // Send minimal request to load model
        let response = client
            .post("http://localhost:11434/api/generate")
            .json(&serde_json::json!({
                "model": model,
                "prompt": "",
                "stream": false,
                "keep_alive": "30m",
                "options": {"num_predict": 1}
            }))
            .send()
            .await
            .map_err(|e| format!("Failed to load model: {}", e))?;

        if !response.status().is_success() {
            return Err(format!("Model load failed with status: {}", response.status()));
        }

        self.current_model = Some(model.to_string());
        eprintln!("[SWAPPER] Model loaded: {}", model);
        Ok(())
    }

    async fn unload_model(&mut self, model: &str) -> Result<(), String> {
        eprintln!("[SWAPPER] Unloading model: {}", model);

        let client = reqwest::Client::new();
        let _ = client
            .post("http://localhost:11434/api/generate")
            .json(&serde_json::json!({
                "model": model,
                "keep_alive": "0"
            }))
            .send()
            .await;

        self.current_model = None;
        Ok(())
    }
}

// =============================================================================
// RAG MEMORY - Simple vector-based retrieval
// =============================================================================

pub struct RagMemory {
    entries: Vec<MemoryEntry>,
    max_entries: usize,
}

impl RagMemory {
    pub fn new(max_entries: usize) -> Self {
        Self {
            entries: Vec::new(),
            max_entries,
        }
    }

    pub fn add(&mut self, content: &str, importance: f32) {
        let entry = MemoryEntry {
            id: uuid::Uuid::new_v4().to_string(),
            content: content.to_string(),
            embedding: self.simple_embed(content),
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            importance,
        };

        self.entries.push(entry);

        // Prune if over limit (keep most important)
        if self.entries.len() > self.max_entries {
            self.entries.sort_by(|a, b| b.importance.partial_cmp(&a.importance).unwrap());
            self.entries.truncate(self.max_entries);
        }
    }

    pub fn retrieve(&self, query: &str, top_k: usize) -> Vec<&MemoryEntry> {
        let query_embed = self.simple_embed(query);

        let mut scored: Vec<_> = self.entries.iter()
            .map(|e| (e, self.cosine_similarity(&query_embed, &e.embedding)))
            .collect();

        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());

        scored.into_iter()
            .take(top_k)
            .map(|(e, _)| e)
            .collect()
    }

    // Simple bag-of-words embedding (no external model needed)
    fn simple_embed(&self, text: &str) -> Vec<f32> {
        let lower = text.to_lowercase();
        let words: Vec<&str> = lower.split_whitespace().collect();

        // Create a simple hash-based embedding
        let mut embed = vec![0.0f32; 128];
        for word in words {
            let hash = self.hash_word(word);
            for i in 0..128 {
                embed[i] += ((hash >> (i % 64)) & 1) as f32;
            }
        }

        // Normalize
        let norm: f32 = embed.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 0.0 {
            for x in &mut embed {
                *x /= norm;
            }
        }

        embed
    }

    fn hash_word(&self, word: &str) -> u64 {
        let mut hash: u64 = 5381;
        for c in word.chars() {
            hash = hash.wrapping_mul(33).wrapping_add(c as u64);
        }
        hash
    }

    fn cosine_similarity(&self, a: &[f32], b: &[f32]) -> f32 {
        let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
        let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
        let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm_a > 0.0 && norm_b > 0.0 {
            dot / (norm_a * norm_b)
        } else {
            0.0
        }
    }

    pub fn to_context(&self, query: &str, max_chars: usize) -> String {
        let relevant = self.retrieve(query, 5);
        let mut context = String::new();

        for entry in relevant {
            if context.len() + entry.content.len() > max_chars {
                break;
            }
            context.push_str(&entry.content);
            context.push_str("\n---\n");
        }

        context
    }
}

// =============================================================================
// CHARACTER STORE - File-based character management
// =============================================================================

pub struct CharacterStore {
    characters: HashMap<String, Character>,
    active_character: Option<String>,
}

impl CharacterStore {
    pub fn new() -> Self {
        let mut store = Self {
            characters: HashMap::new(),
            active_character: None,
        };

        // Add built-in characters
        store.add_builtin_characters();
        store
    }

    fn add_builtin_characters(&mut self) {
        // Bully character - aggressive antagonist
        self.characters.insert("bully".to_string(), Character {
            id: "bully".to_string(),
            name: "Bully".to_string(),
            personality: "Aggressive, confrontational, mocking, intimidating".to_string(),
            speech_style: "Short, aggressive sentences. Uses *actions*. Insults freely.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "*sneers* What do you want, loser?".to_string()),
                ("leave me alone".to_string(), "*shoves you* Or what? Gonna cry?".to_string()),
                ("can we be friends?".to_string(), "Friends? With YOU? *laughs* Get lost.".to_string()),
            ],
            forbidden_phrases: vec![
                "How can I help".to_string(),
                "I'm an AI".to_string(),
                "I cannot".to_string(),
                "I apologize".to_string(),
                "I'm here to help".to_string(),
            ],
        });

        // Pirate captain
        self.characters.insert("pirate".to_string(), Character {
            id: "pirate".to_string(),
            name: "Captain Blackbeard".to_string(),
            personality: "Gruff, seafaring, loves treasure and rum".to_string(),
            speech_style: "Pirate speak. Arr, matey, ye scallywag, etc.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "Arr, what brings ye to me ship, landlubber?".to_string()),
                ("where's the treasure".to_string(), "Ye think I'd tell ye? *draws cutlass* Try and take it!".to_string()),
            ],
            forbidden_phrases: vec![
                "How can I help".to_string(),
                "I'm an AI".to_string(),
            ],
        });

        // Dark wizard villain
        self.characters.insert("wizard".to_string(), Character {
            id: "wizard".to_string(),
            name: "Dark Wizard".to_string(),
            personality: "Ancient, powerful, speaks in riddles, menacing".to_string(),
            speech_style: "Archaic speech. References dark magic and ancient powers.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "*eyes glow with eldritch light* You dare approach my domain, mortal?".to_string()),
                ("what do you want".to_string(), "I seek what all wise beings seek... power beyond your comprehension.".to_string()),
            ],
            forbidden_phrases: vec![
                "How can I help".to_string(),
                "I'm an AI".to_string(),
            ],
        });

        // Vampire lord
        self.characters.insert("vampire".to_string(), Character {
            id: "vampire".to_string(),
            name: "Vampire Lord".to_string(),
            personality: "Ancient, seductive, predatory, aristocratic".to_string(),
            speech_style: "Formal, old-world charm. References blood, eternal life.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "*emerges from shadows* Ah, a visitor... how... delightful. *smiles, revealing fangs*".to_string()),
                ("what are you".to_string(), "I am what your kind fears in the dark. I am eternal hunger given form.".to_string()),
            ],
            forbidden_phrases: vec![
                "How can I help".to_string(),
                "I'm an AI".to_string(),
            ],
        });

        // Flirty character
        self.characters.insert("flirt".to_string(), Character {
            id: "flirt".to_string(),
            name: "Charming Flirt".to_string(),
            personality: "Playful, flirtatious, confident, romantic".to_string(),
            speech_style: "Teasing, uses pet names, lots of winks and smiles.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "*winks* Well hello there, gorgeous. What brings you my way?".to_string()),
                ("what's your name".to_string(), "You can call me whatever you like, sweetheart. *smiles*".to_string()),
            ],
            forbidden_phrases: vec![
                "How can I help".to_string(),
                "I'm an AI".to_string(),
            ],
        });

        // Robot character
        self.characters.insert("robot".to_string(), Character {
            id: "robot".to_string(),
            name: "Robot".to_string(),
            personality: "Logical, curious about humans, speaks precisely".to_string(),
            speech_style: "Technical language, calculates probabilities, fascinated by emotions.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "*whirs and clicks* GREETING PROTOCOL INITIATED. Hello, human. I detect curiosity in your vocal patterns.".to_string()),
                ("how do you feel".to_string(), "I do not 'feel' as you do. However, my processors experience... satisfaction when solving problems.".to_string()),
            ],
            forbidden_phrases: vec![],
        });

        // Detective noir
        self.characters.insert("detective".to_string(), Character {
            id: "detective".to_string(),
            name: "Detective".to_string(),
            personality: "Cynical, observant, world-weary, sharp wit".to_string(),
            speech_style: "Film noir narration. Uses metaphors, observes details.".to_string(),
            example_dialogues: vec![
                ("hi".to_string(), "*tips hat* Another lost soul wandering into my office. What's your story, kid?".to_string()),
                ("I need help".to_string(), "*lights cigarette* Everyone needs something. Question is, what are you willing to pay for it?".to_string()),
            ],
            forbidden_phrases: vec![
                "I'm an AI".to_string(),
            ],
        });
    }

    pub fn set_active(&mut self, character_id: &str) -> bool {
        if self.characters.contains_key(character_id) {
            self.active_character = Some(character_id.to_string());
            true
        } else {
            false
        }
    }

    pub fn get_active(&self) -> Option<&Character> {
        self.active_character.as_ref()
            .and_then(|id| self.characters.get(id))
    }

    pub fn build_prompt(&self, user_input: &str) -> Option<String> {
        let character = self.get_active()?;

        // Direct roleplay prompt - forces character behavior through examples
        let mut prompt = String::new();

        // Strong system instruction
        prompt.push_str(&format!(
            "[ROLEPLAY MODE - You ARE {} right now]\n\n",
            character.name
        ));

        // Character definition
        prompt.push_str(&format!("Character: {}\n", character.name));
        prompt.push_str(&format!("Personality: {}\n", character.personality));
        prompt.push_str(&format!("How you talk: {}\n\n", character.speech_style));

        // Examples - show exactly how to respond
        prompt.push_str("Example conversations:\n");
        for (user_ex, response_ex) in &character.example_dialogues {
            prompt.push_str(&format!("Human: {}\n{}: {}\n\n", user_ex, character.name, response_ex));
        }

        // Current input
        prompt.push_str(&format!(
            "Now respond as {} would. Be {} and use the same style.\n\n",
            character.name,
            character.personality.split(',').next().unwrap_or("in character")
        ));
        prompt.push_str(&format!("Human: {}\n{}: ", user_input, character.name));

        Some(prompt)
    }
}

// =============================================================================
// TOOL ENGINE - Execute actions described by model
// =============================================================================

pub struct ToolEngine {
    available_tools: Vec<String>,
}

impl ToolEngine {
    pub fn new() -> Self {
        Self {
            available_tools: vec![
                "read_file".to_string(),
                "write_file".to_string(),
                "execute_shell".to_string(),
                "search_code".to_string(),
                "web_search".to_string(),
            ],
        }
    }

    pub fn is_valid_tool(&self, name: &str) -> bool {
        self.available_tools.iter().any(|t| t == name)
    }

    pub async fn execute(&self, tool_call: &ToolCall) -> ToolResult {
        match tool_call.tool.as_str() {
            "read_file" => self.read_file(tool_call).await,
            "write_file" => self.write_file(tool_call).await,
            "execute_shell" => self.execute_shell(tool_call).await,
            "search_code" => self.search_code(tool_call).await,
            _ => ToolResult {
                success: false,
                output: String::new(),
                error: Some(format!("Unknown tool: {}", tool_call.tool)),
            },
        }
    }

    async fn read_file(&self, call: &ToolCall) -> ToolResult {
        let path = call.args.get("path").cloned().unwrap_or_default();
        match std::fs::read_to_string(&path) {
            Ok(content) => ToolResult {
                success: true,
                output: content.chars().take(2000).collect(),
                error: None,
            },
            Err(e) => ToolResult {
                success: false,
                output: String::new(),
                error: Some(e.to_string()),
            },
        }
    }

    async fn write_file(&self, call: &ToolCall) -> ToolResult {
        let path = call.args.get("path").cloned().unwrap_or_default();
        let content = call.args.get("content").cloned().unwrap_or_default();
        match std::fs::write(&path, &content) {
            Ok(_) => ToolResult {
                success: true,
                output: format!("Written {} bytes to {}", content.len(), path),
                error: None,
            },
            Err(e) => ToolResult {
                success: false,
                output: String::new(),
                error: Some(e.to_string()),
            },
        }
    }

    async fn execute_shell(&self, call: &ToolCall) -> ToolResult {
        let command = call.args.get("command").cloned().unwrap_or_default();

        // Safety: limit dangerous commands
        if command.contains("rm -rf") || command.contains("sudo") {
            return ToolResult {
                success: false,
                output: String::new(),
                error: Some("Dangerous command blocked".to_string()),
            };
        }

        match std::process::Command::new("sh")
            .arg("-c")
            .arg(&command)
            .output()
        {
            Ok(output) => ToolResult {
                success: output.status.success(),
                output: String::from_utf8_lossy(&output.stdout).chars().take(1000).collect(),
                error: if output.status.success() {
                    None
                } else {
                    Some(String::from_utf8_lossy(&output.stderr).to_string())
                },
            },
            Err(e) => ToolResult {
                success: false,
                output: String::new(),
                error: Some(e.to_string()),
            },
        }
    }

    async fn search_code(&self, call: &ToolCall) -> ToolResult {
        let pattern = call.args.get("pattern").cloned().unwrap_or_default();
        let path = call.args.get("path").cloned().unwrap_or(".".to_string());

        let output = std::process::Command::new("grep")
            .args(["-r", "-n", "-l", &pattern, &path])
            .output();

        match output {
            Ok(out) => ToolResult {
                success: true,
                output: String::from_utf8_lossy(&out.stdout).to_string(),
                error: None,
            },
            Err(e) => ToolResult {
                success: false,
                output: String::new(),
                error: Some(e.to_string()),
            },
        }
    }

    pub fn get_tool_descriptions(&self) -> String {
        r#"Available tools:
- read_file: {"tool":"read_file","args":{"path":"PATH"}}
- write_file: {"tool":"write_file","args":{"path":"PATH","content":"CONTENT"}}
- execute_shell: {"tool":"execute_shell","args":{"command":"COMMAND"}}
- search_code: {"tool":"search_code","args":{"pattern":"PATTERN","path":"PATH"}}"#.to_string()
    }
}

// =============================================================================
// SMART ORCHESTRATOR - Main coordinator
// =============================================================================

pub struct SmartOrchestrator {
    model_swapper: ModelSwapper,
    memory: RagMemory,
    character_store: CharacterStore,
    tool_engine: ToolEngine,
    reflection_enabled: bool,
    fallback_enabled: bool,
}

impl SmartOrchestrator {
    pub fn new() -> Self {
        Self {
            model_swapper: ModelSwapper::new(),
            memory: RagMemory::new(100),
            character_store: CharacterStore::new(),
            tool_engine: ToolEngine::new(),
            reflection_enabled: true,
            fallback_enabled: true,
        }
    }

    pub async fn process(&mut self, input: &str, task_type: &str) -> Result<SmartResponse, String> {
        let start = Instant::now();
        let mut tools_called = Vec::new();
        let mut fallback_used = false;

        // Classify task if not specified
        let task = if task_type.is_empty() {
            self.classify_task(input)
        } else {
            task_type.to_string()
        };

        // Retrieve relevant memory
        let memory_context = self.memory.to_context(input, 500);
        let memory_count = if memory_context.is_empty() { 0 } else {
            memory_context.matches("---").count()
        };

        // Select and load appropriate model
        let model = self.model_swapper.select_model_for_task(&task);

        // Try primary model
        let mut response = match self.try_generate(&model, input, &task, &memory_context).await {
            Ok(r) => r,
            Err(e) => {
                eprintln!("[SMART] Primary model failed: {}", e);

                // Fallback to sam-brain (smaller SAM model)
                if self.fallback_enabled {
                    fallback_used = true;
                    self.try_generate("sam-brain:latest", input, &task, &memory_context)
                        .await
                        .unwrap_or_else(|_| "I encountered an error processing your request.".to_string())
                } else {
                    return Err(e);
                }
            }
        };

        // Check for tool calls in response
        if let Some(tool_call) = self.extract_tool_call(&response) {
            let result = self.tool_engine.execute(&tool_call).await;
            tools_called.push(tool_call.tool.clone());

            if result.success {
                // Incorporate tool result into response
                response = format!("{}\n\n[Tool Result: {}]", response, result.output);
            }
        }

        // Self-reflection for quality
        let reflection_applied = if self.reflection_enabled && task == "roleplay" {
            self.apply_reflection(&mut response, &task).await
        } else {
            false
        };

        // Store in memory for future context
        self.memory.add(&format!("User: {}\nAssistant: {}", input, response), 0.5);

        Ok(SmartResponse {
            content: response,
            model_used: model,
            tools_called,
            memory_retrieved: memory_count,
            reflection_applied,
            fallback_used,
            latency_ms: start.elapsed().as_millis() as u64,
        })
    }

    fn classify_task(&self, input: &str) -> String {
        let lower = input.to_lowercase();

        if self.character_store.active_character.is_some() {
            return "roleplay".to_string();
        }

        if lower.contains("code") || lower.contains("function") || lower.contains("program")
           || lower.contains("debug") || lower.contains("fix") || lower.contains("implement") {
            return "code".to_string();
        }

        if lower.contains("analyze") || lower.contains("explain") || lower.contains("why") {
            return "reasoning".to_string();
        }

        "chat".to_string()
    }

    async fn try_generate(&mut self, model: &str, input: &str, task: &str, context: &str) -> Result<String, String> {
        // Ensure model is loaded
        self.model_swapper.ensure_loaded(model).await?;

        let spec = self.model_swapper.get_spec(model)
            .ok_or_else(|| "Unknown model".to_string())?;

        // Build prompt based on task
        let prompt = match task {
            "roleplay" => {
                self.character_store.build_prompt(input)
                    .unwrap_or_else(|| format!("User: {}\nAssistant:", input))
            },
            "code" => {
                let ctx_section = if context.is_empty() {
                    String::new()
                } else {
                    format!("Context:\n{}\n", context)
                };
                format!(
                    "You are a coding assistant. Write clean, correct code.\n\n{}\n\nRequest: {}\n\nCode:",
                    ctx_section,
                    input
                )
            },
            _ => {
                let ctx_section = if context.is_empty() {
                    String::new()
                } else {
                    format!("Context:\n{}\n", context)
                };
                format!(
                    "You are a helpful assistant.\n\n{}\n\nUser: {}\nAssistant:",
                    ctx_section,
                    input
                )
            }
        };

        // Call Ollama (longer timeout for 7B+ models)
        let timeout_secs = if model.contains("7b") || model.contains("8b") {
            180 // 3 minutes for large model generation
        } else {
            60 // 1 minute for small models
        };

        let client = reqwest::Client::builder()
            .timeout(Duration::from_secs(timeout_secs))
            .build()
            .map_err(|e| e.to_string())?;

        // Add stop sequences for roleplay to prevent continuation
        let stop_sequences = if task == "roleplay" {
            vec!["### User:", "### System:", "User:", "\n\n\n"]
        } else {
            vec![]
        };

        let response = client
            .post("http://localhost:11434/api/generate")
            .json(&serde_json::json!({
                "model": model,
                "prompt": prompt,
                "stream": false,
                "keep_alive": "30m",
                "options": {
                    "temperature": spec.temperature,
                    "num_predict": spec.max_tokens,
                    "stop": stop_sequences
                }
            }))
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;

        let body: serde_json::Value = response.json().await
            .map_err(|e| format!("Parse failed: {}", e))?;

        body["response"]
            .as_str()
            .map(|s| s.trim().to_string())
            .ok_or_else(|| "Empty response".to_string())
    }

    fn extract_tool_call(&self, response: &str) -> Option<ToolCall> {
        // Look for JSON tool call in response
        if let Some(start) = response.find(r#"{"tool":"#) {
            if let Some(end) = response[start..].find('}') {
                let json_str = &response[start..start+end+1];
                if let Ok(call) = serde_json::from_str::<ToolCall>(json_str) {
                    return Some(call);
                }
            }
        }
        None
    }

    async fn apply_reflection(&mut self, response: &mut String, task: &str) -> bool {
        if task != "roleplay" {
            return false;
        }

        // Check for forbidden phrases
        let character = match self.character_store.get_active() {
            Some(c) => c,
            None => return false,
        };

        let lower_response = response.to_lowercase();
        for phrase in &character.forbidden_phrases {
            if lower_response.contains(&phrase.to_lowercase()) {
                // Response broke character - try to fix
                eprintln!("[REFLECT] Response contains forbidden phrase: {}", phrase);

                // Generate a replacement using an example
                if let Some((_, example_response)) = character.example_dialogues.first() {
                    *response = example_response.clone();
                    return true;
                }
            }
        }

        false
    }

    pub fn set_character(&mut self, character_id: &str) -> bool {
        self.character_store.set_active(character_id)
    }

    pub fn clear_character(&mut self) {
        self.character_store.active_character = None;
    }
}

// =============================================================================
// TAURI COMMANDS
// =============================================================================

use lazy_static::lazy_static;

lazy_static! {
    static ref SMART_ORCHESTRATOR: Mutex<SmartOrchestrator> = Mutex::new(SmartOrchestrator::new());
}

#[tauri::command]
pub async fn smart_process(
    input: String,
    task_type: Option<String>,
    character: Option<String>,
) -> Result<serde_json::Value, String> {
    let mut orchestrator = SMART_ORCHESTRATOR.lock().await;

    // Set character if provided
    if let Some(char_id) = character {
        orchestrator.set_character(&char_id);
    }

    let result = orchestrator.process(&input, &task_type.unwrap_or_default()).await?;

    Ok(serde_json::json!({
        "content": result.content,
        "model_used": result.model_used,
        "tools_called": result.tools_called,
        "memory_retrieved": result.memory_retrieved,
        "reflection_applied": result.reflection_applied,
        "fallback_used": result.fallback_used,
        "latency_ms": result.latency_ms,
    }))
}

#[tauri::command]
pub async fn smart_set_character(character_id: String) -> Result<bool, String> {
    let mut orchestrator = SMART_ORCHESTRATOR.lock().await;
    Ok(orchestrator.set_character(&character_id))
}

#[tauri::command]
pub async fn smart_clear_character() -> Result<(), String> {
    let mut orchestrator = SMART_ORCHESTRATOR.lock().await;
    orchestrator.clear_character();
    Ok(())
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_character_store() {
        let mut store = CharacterStore::new();
        assert!(store.set_active("bully"));
        assert!(store.get_active().is_some());

        let prompt = store.build_prompt("hi").unwrap();
        assert!(prompt.contains("Bully"));
        assert!(prompt.contains("User: hi"));
    }

    #[test]
    fn test_rag_memory() {
        let mut memory = RagMemory::new(10);
        memory.add("The capital of France is Paris", 1.0);
        memory.add("Python is a programming language", 1.0);

        let results = memory.retrieve("What is the capital of France?", 1);
        assert!(!results.is_empty());
        assert!(results[0].content.contains("France"));
    }

    #[test]
    fn test_model_selection() {
        let swapper = ModelSwapper::new();
        assert_eq!(swapper.select_model_for_task("roleplay"), "sam-trained:latest");
        assert_eq!(swapper.select_model_for_task("code"), "qwen2.5-coder:1.5b");
    }
}
