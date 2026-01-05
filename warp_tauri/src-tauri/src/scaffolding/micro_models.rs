// Micro-Model Manager (Option 2)
//
// Manages specialized small models for different tasks:
// - Code completion: qwen2.5-coder:0.5b (fastest)
// - Bug fixing: qwen2.5-coder:1.5b
// - Complex generation: qwen2.5-coder:3b
// - General chat: qwen2.5:0.5b
//
// Handles model loading/unloading to stay within 8GB RAM

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};

// =============================================================================
// MODEL DEFINITIONS
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum ModelId {
    // Coder models (specialized for code)
    CoderTiny,      // qwen2.5-coder:0.5b - ~400MB
    CoderSmall,     // qwen2.5-coder:1.5b - ~1GB
    CoderMedium,    // qwen2.5-coder:3b - ~2GB

    // General models
    GeneralTiny,    // qwen2.5:0.5b
    GeneralSmall,   // qwen2.5:1.5b

    // Specialized (if available)
    Starcoder,      // starcoder2:3b - code completion
    Deepseek,       // deepseek-coder:1.3b

    // Custom/Other
    Custom(String),
}

impl ModelId {
    pub fn ollama_name(&self) -> String {
        match self {
            // All coder models map to 1.5b (only installed version)
            ModelId::CoderTiny => "qwen2.5-coder:1.5b".to_string(),
            ModelId::CoderSmall => "qwen2.5-coder:1.5b".to_string(),
            ModelId::CoderMedium => "qwen2.5-coder:1.5b".to_string(),
            ModelId::GeneralTiny => "qwen2.5:0.5b".to_string(),
            ModelId::GeneralSmall => "qwen2.5:1.5b".to_string(),
            ModelId::Starcoder => "starcoder2:3b".to_string(),
            ModelId::Deepseek => "deepseek-coder:1.3b".to_string(),
            ModelId::Custom(name) => name.clone(),
        }
    }

    pub fn estimated_vram_mb(&self) -> u64 {
        match self {
            ModelId::CoderTiny | ModelId::GeneralTiny => 400,
            ModelId::CoderSmall | ModelId::GeneralSmall | ModelId::Deepseek => 1000,
            ModelId::CoderMedium | ModelId::Starcoder => 2000,
            ModelId::Custom(_) => 1500, // Conservative estimate
        }
    }

    pub fn from_ollama_name(name: &str) -> Self {
        match name {
            "qwen2.5-coder:0.5b" => ModelId::CoderTiny,
            "qwen2.5-coder:1.5b" => ModelId::CoderSmall,
            "qwen2.5-coder:3b" => ModelId::CoderMedium,
            "qwen2.5:0.5b" => ModelId::GeneralTiny,
            "qwen2.5:1.5b" => ModelId::GeneralSmall,
            "starcoder2:3b" => ModelId::Starcoder,
            "deepseek-coder:1.3b" => ModelId::Deepseek,
            other => ModelId::Custom(other.to_string()),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelCapabilities {
    pub code_completion: bool,
    pub code_generation: bool,
    pub bug_fixing: bool,
    pub refactoring: bool,
    pub explanation: bool,
    pub chat: bool,
    pub fill_in_middle: bool,
}

impl ModelCapabilities {
    pub fn coder() -> Self {
        Self {
            code_completion: true,
            code_generation: true,
            bug_fixing: true,
            refactoring: true,
            explanation: true,
            chat: false,
            fill_in_middle: false,
        }
    }

    pub fn general() -> Self {
        Self {
            code_completion: false,
            code_generation: false,
            bug_fixing: false,
            refactoring: false,
            explanation: true,
            chat: true,
            fill_in_middle: false,
        }
    }

    pub fn starcoder() -> Self {
        Self {
            code_completion: true,
            code_generation: true,
            bug_fixing: false,
            refactoring: false,
            explanation: false,
            chat: false,
            fill_in_middle: true,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelInfo {
    pub id: ModelId,
    pub capabilities: ModelCapabilities,
    pub context_length: usize,
    pub speed_rating: u8,  // 1-10, higher is faster
    pub quality_rating: u8, // 1-10, higher is better
}

// =============================================================================
// TASK TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum TaskType {
    CodeCompletion,     // Inline completion, autocomplete
    CodeGeneration,     // Generate new code from description
    BugFix,             // Fix errors, debug
    Refactor,           // Improve existing code
    Explanation,        // Explain code
    TestGeneration,     // Generate tests
    DocGeneration,      // Generate documentation
    Chat,               // General conversation
    TemplFill,          // Fill in template placeholders
}

// =============================================================================
// MODEL MANAGER
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoadedModel {
    pub id: ModelId,
    pub loaded_at: u64,  // Unix timestamp
    pub last_used: u64,
    pub use_count: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelManagerConfig {
    pub max_vram_mb: u64,
    pub idle_unload_seconds: u64,
    pub prefer_speed: bool,  // vs quality
}

impl Default for ModelManagerConfig {
    fn default() -> Self {
        Self {
            max_vram_mb: 6000,  // Leave 2GB for system on 8GB Mac
            idle_unload_seconds: 300,  // 5 minutes
            prefer_speed: true,
        }
    }
}

pub struct MicroModelManager {
    config: ModelManagerConfig,
    loaded_models: HashMap<ModelId, LoadedModel>,
    model_info: HashMap<ModelId, ModelInfo>,
    task_history: Vec<(TaskType, ModelId, bool)>,  // (task, model, success)
}

impl MicroModelManager {
    pub fn new(config: ModelManagerConfig) -> Self {
        let mut manager = Self {
            config,
            loaded_models: HashMap::new(),
            model_info: HashMap::new(),
            task_history: Vec::new(),
        };
        manager.register_builtin_models();
        manager
    }

    fn register_builtin_models(&mut self) {
        // Coder Tiny - fastest for completions
        self.model_info.insert(ModelId::CoderTiny, ModelInfo {
            id: ModelId::CoderTiny,
            capabilities: ModelCapabilities::coder(),
            context_length: 32768,
            speed_rating: 10,
            quality_rating: 6,
        });

        // Coder Small - good balance
        self.model_info.insert(ModelId::CoderSmall, ModelInfo {
            id: ModelId::CoderSmall,
            capabilities: ModelCapabilities::coder(),
            context_length: 32768,
            speed_rating: 8,
            quality_rating: 8,
        });

        // Coder Medium - highest quality
        self.model_info.insert(ModelId::CoderMedium, ModelInfo {
            id: ModelId::CoderMedium,
            capabilities: ModelCapabilities::coder(),
            context_length: 32768,
            speed_rating: 5,
            quality_rating: 10,
        });

        // General Tiny
        self.model_info.insert(ModelId::GeneralTiny, ModelInfo {
            id: ModelId::GeneralTiny,
            capabilities: ModelCapabilities::general(),
            context_length: 32768,
            speed_rating: 10,
            quality_rating: 5,
        });

        // General Small
        self.model_info.insert(ModelId::GeneralSmall, ModelInfo {
            id: ModelId::GeneralSmall,
            capabilities: ModelCapabilities::general(),
            context_length: 32768,
            speed_rating: 8,
            quality_rating: 7,
        });

        // Starcoder (if available)
        self.model_info.insert(ModelId::Starcoder, ModelInfo {
            id: ModelId::Starcoder,
            capabilities: ModelCapabilities::starcoder(),
            context_length: 16384,
            speed_rating: 7,
            quality_rating: 8,
        });
    }

    /// Select the best model for a task
    pub fn select_model(&self, task: &TaskType) -> ModelId {
        let candidates = self.get_capable_models(task);

        if candidates.is_empty() {
            // Fallback to coder small
            return ModelId::CoderSmall;
        }

        // Score each candidate
        let mut best: Option<(ModelId, i32)> = None;

        for model_id in candidates {
            if let Some(info) = self.model_info.get(&model_id) {
                let mut score: i32 = 0;

                // Factor in speed vs quality preference
                if self.config.prefer_speed {
                    score += info.speed_rating as i32 * 2;
                    score += info.quality_rating as i32;
                } else {
                    score += info.speed_rating as i32;
                    score += info.quality_rating as i32 * 2;
                }

                // Bonus for already loaded models
                if self.loaded_models.contains_key(&model_id) {
                    score += 10;
                }

                // Consider VRAM constraints
                let current_vram = self.current_vram_usage();
                if current_vram + info.id.estimated_vram_mb() > self.config.max_vram_mb {
                    score -= 20;  // Penalty if would exceed VRAM
                }

                // Consider past success rate
                let success_rate = self.get_success_rate(&model_id, task);
                score += (success_rate * 10.0) as i32;

                if best.is_none() || score > best.as_ref().unwrap().1 {
                    best = Some((model_id, score));
                }
            }
        }

        best.map(|(id, _)| id).unwrap_or(ModelId::CoderSmall)
    }

    /// Get models capable of a task
    fn get_capable_models(&self, task: &TaskType) -> Vec<ModelId> {
        self.model_info.iter()
            .filter(|(_, info)| {
                match task {
                    TaskType::CodeCompletion => info.capabilities.code_completion,
                    TaskType::CodeGeneration => info.capabilities.code_generation,
                    TaskType::BugFix => info.capabilities.bug_fixing,
                    TaskType::Refactor => info.capabilities.refactoring,
                    TaskType::Explanation => info.capabilities.explanation,
                    TaskType::TestGeneration => info.capabilities.code_generation,
                    TaskType::DocGeneration => info.capabilities.explanation,
                    TaskType::Chat => info.capabilities.chat || info.capabilities.explanation,
                    TaskType::TemplFill => info.capabilities.code_generation,
                }
            })
            .map(|(id, _)| id.clone())
            .collect()
    }

    /// Calculate current VRAM usage
    fn current_vram_usage(&self) -> u64 {
        self.loaded_models.keys()
            .map(|id| id.estimated_vram_mb())
            .sum()
    }

    /// Get success rate for a model on a task type
    fn get_success_rate(&self, model_id: &ModelId, task: &TaskType) -> f32 {
        let relevant: Vec<_> = self.task_history.iter()
            .filter(|(t, m, _)| t == task && m == model_id)
            .collect();

        if relevant.is_empty() {
            return 0.5;  // No data, assume average
        }

        let successes = relevant.iter().filter(|(_, _, s)| *s).count();
        successes as f32 / relevant.len() as f32
    }

    /// Record task result for learning
    pub fn record_result(&mut self, task: TaskType, model_id: ModelId, success: bool) {
        self.task_history.push((task, model_id, success));

        // Keep history bounded
        if self.task_history.len() > 1000 {
            self.task_history.drain(0..500);
        }
    }

    /// Mark a model as loaded
    pub fn mark_loaded(&mut self, model_id: ModelId) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        self.loaded_models.insert(model_id.clone(), LoadedModel {
            id: model_id,
            loaded_at: now,
            last_used: now,
            use_count: 0,
        });
    }

    /// Mark a model as used
    pub fn mark_used(&mut self, model_id: &ModelId) {
        if let Some(model) = self.loaded_models.get_mut(model_id) {
            model.last_used = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs();
            model.use_count += 1;
        }
    }

    /// Get models that should be unloaded (idle too long)
    pub fn get_idle_models(&self) -> Vec<ModelId> {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        self.loaded_models.iter()
            .filter(|(_, model)| {
                now - model.last_used > self.config.idle_unload_seconds
            })
            .map(|(id, _)| id.clone())
            .collect()
    }

    /// Mark a model as unloaded
    pub fn mark_unloaded(&mut self, model_id: &ModelId) {
        self.loaded_models.remove(model_id);
    }

    /// Get the optimal prompt format for a model
    pub fn get_prompt_format(&self, model_id: &ModelId, task: &TaskType) -> PromptFormat {
        match model_id {
            ModelId::CoderTiny | ModelId::CoderSmall | ModelId::CoderMedium => {
                PromptFormat::Qwen {
                    system: Self::get_system_prompt(task),
                }
            }
            ModelId::Starcoder => {
                PromptFormat::FillInMiddle {
                    prefix_marker: "<fim_prefix>".to_string(),
                    suffix_marker: "<fim_suffix>".to_string(),
                    middle_marker: "<fim_middle>".to_string(),
                }
            }
            ModelId::Deepseek => {
                PromptFormat::Qwen {
                    system: Self::get_system_prompt(task),
                }
            }
            _ => PromptFormat::Plain,
        }
    }

    fn get_system_prompt(task: &TaskType) -> String {
        match task {
            TaskType::CodeCompletion => {
                "You are a code completion assistant. Complete the code naturally and concisely. Only output the completion, no explanations.".to_string()
            }
            TaskType::CodeGeneration => {
                "You are a code generation assistant. Generate clean, well-structured code based on the requirements. Include brief comments for complex logic.".to_string()
            }
            TaskType::BugFix => {
                "You are a debugging assistant. Identify and fix bugs in the code. Explain what was wrong and show the corrected code.".to_string()
            }
            TaskType::Refactor => {
                "You are a refactoring assistant. Improve the code's structure, readability, and efficiency while maintaining functionality.".to_string()
            }
            TaskType::Explanation => {
                "You are a code explanation assistant. Explain the code clearly and concisely, focusing on what it does and how it works.".to_string()
            }
            TaskType::TestGeneration => {
                "You are a test generation assistant. Generate comprehensive tests covering edge cases and common scenarios.".to_string()
            }
            TaskType::DocGeneration => {
                "You are a documentation assistant. Generate clear, comprehensive documentation for the code.".to_string()
            }
            TaskType::Chat => {
                "You are a helpful programming assistant. Answer questions clearly and provide code examples when relevant.".to_string()
            }
            TaskType::TemplFill => {
                "You are a template filling assistant. Fill in the placeholders with appropriate values based on context. Output only JSON with the filled values.".to_string()
            }
        }
    }

    /// Get statistics about model usage
    pub fn get_stats(&self) -> ModelManagerStats {
        let total_tasks = self.task_history.len();
        let successful = self.task_history.iter().filter(|(_, _, s)| *s).count();

        let mut model_usage: HashMap<String, u64> = HashMap::new();
        for (_, model_id, _) in &self.task_history {
            *model_usage.entry(model_id.ollama_name()).or_insert(0) += 1;
        }

        ModelManagerStats {
            total_tasks: total_tasks as u64,
            success_rate: if total_tasks > 0 { successful as f32 / total_tasks as f32 } else { 0.0 },
            loaded_models: self.loaded_models.len() as u64,
            current_vram_mb: self.current_vram_usage(),
            model_usage,
        }
    }

    /// List all available models
    pub fn list_models(&self) -> Vec<&ModelInfo> {
        self.model_info.values().collect()
    }

    /// Check if a model is currently loaded
    pub fn is_loaded(&self, model_id: &ModelId) -> bool {
        self.loaded_models.contains_key(model_id)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum PromptFormat {
    Plain,
    Qwen { system: String },
    FillInMiddle {
        prefix_marker: String,
        suffix_marker: String,
        middle_marker: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelManagerStats {
    pub total_tasks: u64,
    pub success_rate: f32,
    pub loaded_models: u64,
    pub current_vram_mb: u64,
    pub model_usage: HashMap<String, u64>,
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    pub static ref MODEL_MANAGER: std::sync::Mutex<MicroModelManager> =
        std::sync::Mutex::new(MicroModelManager::new(ModelManagerConfig::default()));
}

pub fn manager() -> std::sync::MutexGuard<'static, MicroModelManager> {
    MODEL_MANAGER.lock().unwrap()
}

/// Select the best model for a task
pub fn select_for_task(task: TaskType) -> ModelId {
    manager().select_model(&task)
}

/// Record a task result
pub fn record_task(task: TaskType, model_id: ModelId, success: bool) {
    manager().record_result(task, model_id, success);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_model_selection() {
        let manager = MicroModelManager::new(ModelManagerConfig::default());

        // Code completion should prefer speed
        let model = manager.select_model(&TaskType::CodeCompletion);
        // Should pick a fast model (CoderTiny has speed_rating 10)
        assert!(matches!(model, ModelId::CoderTiny | ModelId::CoderSmall));
    }

    #[test]
    fn test_vram_tracking() {
        let mut manager = MicroModelManager::new(ModelManagerConfig::default());

        manager.mark_loaded(ModelId::CoderSmall);
        assert!(manager.current_vram_usage() >= 1000);

        manager.mark_loaded(ModelId::CoderTiny);
        assert!(manager.current_vram_usage() >= 1400);

        manager.mark_unloaded(&ModelId::CoderSmall);
        assert!(manager.current_vram_usage() < 1000);
    }

    #[test]
    fn test_success_rate_tracking() {
        let mut manager = MicroModelManager::new(ModelManagerConfig::default());

        manager.record_result(TaskType::CodeCompletion, ModelId::CoderTiny, true);
        manager.record_result(TaskType::CodeCompletion, ModelId::CoderTiny, true);
        manager.record_result(TaskType::CodeCompletion, ModelId::CoderTiny, false);

        let rate = manager.get_success_rate(&ModelId::CoderTiny, &TaskType::CodeCompletion);
        assert!((rate - 0.666).abs() < 0.01);
    }
}
