// Speed Cache - Response caching and optimization for agent speed
//
// Implements multi-level caching to minimize LLM calls:
// 1. Exact match cache (deterministic responses)
// 2. Semantic similarity cache (similar queries)
// 3. Tool result cache (expensive operations)
// 4. Prompt prefix cache (common patterns)

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedResponse {
    pub query: String,
    pub response: String,
    pub processing_path: String,
    pub tool_calls: Vec<CachedToolCall>,
    pub timestamp: u64,
    pub hit_count: u32,
    pub latency_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CachedToolCall {
    pub tool: String,
    pub args_hash: String,
    pub result: String,
    pub success: bool,
}

#[derive(Debug, Clone, Serialize)]
pub struct CacheStats {
    pub exact_hits: u64,
    pub semantic_hits: u64,
    pub tool_hits: u64,
    pub misses: u64,
    pub evictions: u64,
    pub avg_latency_saved_ms: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptPrefix {
    pub prefix: String,
    pub category: String,
    pub response_template: Option<String>,
}

// =============================================================================
// SPEED CACHE
// =============================================================================

pub struct SpeedCache {
    // Exact match cache (query hash -> response)
    exact_cache: HashMap<u64, CachedResponse>,

    // Tool result cache (tool + args hash -> result)
    tool_cache: HashMap<String, (String, Instant)>,

    // Common prompt prefixes for fast routing
    prompt_prefixes: Vec<PromptPrefix>,

    // Stats
    stats: CacheStats,

    // Config
    max_exact_entries: usize,
    max_tool_entries: usize,
    tool_ttl: Duration,
    exact_ttl: Duration,
}

impl SpeedCache {
    pub fn new() -> Self {
        let mut cache = Self {
            exact_cache: HashMap::new(),
            tool_cache: HashMap::new(),
            prompt_prefixes: Vec::new(),
            stats: CacheStats {
                exact_hits: 0,
                semantic_hits: 0,
                tool_hits: 0,
                misses: 0,
                evictions: 0,
                avg_latency_saved_ms: 0.0,
            },
            max_exact_entries: 1000,
            max_tool_entries: 500,
            tool_ttl: Duration::from_secs(300),      // 5 minutes
            exact_ttl: Duration::from_secs(3600),    // 1 hour
        };
        cache.init_prompt_prefixes();
        cache
    }

    fn init_prompt_prefixes(&mut self) {
        // Common patterns that can be handled deterministically
        self.prompt_prefixes = vec![
            // Git commands
            PromptPrefix {
                prefix: "git status".to_string(),
                category: "git".to_string(),
                response_template: None,
            },
            PromptPrefix {
                prefix: "show git".to_string(),
                category: "git".to_string(),
                response_template: None,
            },

            // File operations
            PromptPrefix {
                prefix: "list files".to_string(),
                category: "file".to_string(),
                response_template: None,
            },
            PromptPrefix {
                prefix: "show file".to_string(),
                category: "file".to_string(),
                response_template: None,
            },
            PromptPrefix {
                prefix: "read ".to_string(),
                category: "file".to_string(),
                response_template: None,
            },

            // Search
            PromptPrefix {
                prefix: "find ".to_string(),
                category: "search".to_string(),
                response_template: None,
            },
            PromptPrefix {
                prefix: "search for".to_string(),
                category: "search".to_string(),
                response_template: None,
            },
            PromptPrefix {
                prefix: "where is".to_string(),
                category: "search".to_string(),
                response_template: None,
            },

            // System info
            PromptPrefix {
                prefix: "what time".to_string(),
                category: "system".to_string(),
                response_template: Some("current_time".to_string()),
            },
            PromptPrefix {
                prefix: "current directory".to_string(),
                category: "system".to_string(),
                response_template: Some("pwd".to_string()),
            },
        ];
    }

    /// Compute hash for query
    fn query_hash(&self, query: &str) -> u64 {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let normalized = query.to_lowercase().trim().to_string();
        let mut hasher = DefaultHasher::new();
        normalized.hash(&mut hasher);
        hasher.finish()
    }

    /// Compute hash for tool call
    fn tool_hash(&self, tool: &str, args: &serde_json::Value) -> String {
        format!("{}:{}", tool, args.to_string())
    }

    /// Check exact cache
    pub fn get_exact(&mut self, query: &str) -> Option<CachedResponse> {
        let hash = self.query_hash(query);
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();

        // Check if we have a valid cached entry
        let result = if let Some(cached) = self.exact_cache.get_mut(&hash) {
            if now - cached.timestamp < self.exact_ttl.as_secs() {
                cached.hit_count += 1;
                Some((cached.clone(), cached.latency_ms))
            } else {
                None // Expired
            }
        } else {
            None
        };

        match result {
            Some((cached, latency_ms)) => {
                self.stats.exact_hits += 1;
                self.update_latency_saved(latency_ms);
                Some(cached)
            }
            None => {
                // Either not found or expired - check if we need to remove
                if self.exact_cache.contains_key(&hash) {
                    self.exact_cache.remove(&hash);
                    self.stats.evictions += 1;
                } else {
                    self.stats.misses += 1;
                }
                None
            }
        }
    }

    /// Store in exact cache
    pub fn set_exact(&mut self, query: &str, response: CachedResponse) {
        // Evict if at capacity
        if self.exact_cache.len() >= self.max_exact_entries {
            self.evict_lru_exact();
        }

        let hash = self.query_hash(query);
        self.exact_cache.insert(hash, response);
    }

    /// Check tool cache
    pub fn get_tool_result(&mut self, tool: &str, args: &serde_json::Value) -> Option<String> {
        let key = self.tool_hash(tool, args);

        if let Some((result, timestamp)) = self.tool_cache.get(&key) {
            if timestamp.elapsed() < self.tool_ttl {
                self.stats.tool_hits += 1;
                return Some(result.clone());
            } else {
                self.tool_cache.remove(&key);
            }
        }

        None
    }

    /// Store tool result
    pub fn set_tool_result(&mut self, tool: &str, args: &serde_json::Value, result: &str) {
        if self.tool_cache.len() >= self.max_tool_entries {
            self.evict_old_tools();
        }

        let key = self.tool_hash(tool, args);
        self.tool_cache.insert(key, (result.to_string(), Instant::now()));
    }

    /// Check if query matches a fast-path prefix
    pub fn match_prefix(&self, query: &str) -> Option<&PromptPrefix> {
        let lower = query.to_lowercase();
        self.prompt_prefixes.iter().find(|p| lower.starts_with(&p.prefix))
    }

    /// Get category for a query based on prefix matching
    pub fn categorize(&self, query: &str) -> Option<String> {
        self.match_prefix(query).map(|p| p.category.clone())
    }

    fn evict_lru_exact(&mut self) {
        // Find least recently used (lowest hit count)
        if let Some((&hash_to_remove, _)) = self.exact_cache.iter()
            .min_by_key(|(_, v)| v.hit_count)
        {
            self.exact_cache.remove(&hash_to_remove);
            self.stats.evictions += 1;
        }
    }

    fn evict_old_tools(&mut self) {
        let ttl = self.tool_ttl;
        self.tool_cache.retain(|_, (_, ts)| ts.elapsed() < ttl);
        self.stats.evictions += 1;
    }

    fn update_latency_saved(&mut self, latency_ms: u64) {
        let total_hits = self.stats.exact_hits + self.stats.semantic_hits + self.stats.tool_hits;
        if total_hits > 0 {
            let current_total = self.stats.avg_latency_saved_ms * (total_hits - 1) as f64;
            self.stats.avg_latency_saved_ms = (current_total + latency_ms as f64) / total_hits as f64;
        }
    }

    /// Get cache statistics
    pub fn stats(&self) -> &CacheStats {
        &self.stats
    }

    /// Clear all caches
    pub fn clear(&mut self) {
        self.exact_cache.clear();
        self.tool_cache.clear();
        self.stats = CacheStats {
            exact_hits: 0,
            semantic_hits: 0,
            tool_hits: 0,
            misses: 0,
            evictions: 0,
            avg_latency_saved_ms: 0.0,
        };
    }

    /// Get hit rate as percentage
    pub fn hit_rate(&self) -> f64 {
        let total = self.stats.exact_hits + self.stats.semantic_hits +
                    self.stats.tool_hits + self.stats.misses;
        if total == 0 {
            return 0.0;
        }
        let hits = self.stats.exact_hits + self.stats.semantic_hits + self.stats.tool_hits;
        (hits as f64 / total as f64) * 100.0
    }
}

impl Default for SpeedCache {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// PARALLEL EXECUTOR
// =============================================================================

/// Execute multiple tool calls in parallel
pub async fn parallel_tool_execute<F, Fut, T>(
    calls: Vec<(String, serde_json::Value)>,
    executor: F,
) -> Vec<Result<T, String>>
where
    F: Fn(String, serde_json::Value) -> Fut + Send + Sync + Clone + 'static,
    Fut: std::future::Future<Output = Result<T, String>> + Send,
    T: Send + 'static,
{
    use tokio::task::JoinSet;

    let mut set = JoinSet::new();

    for (tool, args) in calls {
        let exec = executor.clone();
        set.spawn(async move {
            exec(tool, args).await
        });
    }

    let mut results = Vec::new();
    while let Some(result) = set.join_next().await {
        match result {
            Ok(r) => results.push(r),
            Err(e) => results.push(Err(format!("Task panicked: {}", e))),
        }
    }

    results
}

// =============================================================================
// GLOBAL CACHE
// =============================================================================

lazy_static::lazy_static! {
    pub static ref SPEED_CACHE: Mutex<SpeedCache> = Mutex::new(SpeedCache::new());
}

pub fn speed_cache() -> std::sync::MutexGuard<'static, SpeedCache> {
    SPEED_CACHE.lock().unwrap()
}

/// Check cache for exact match
pub fn cache_get(query: &str) -> Option<CachedResponse> {
    speed_cache().get_exact(query)
}

/// Store response in cache
pub fn cache_set(query: &str, response: CachedResponse) {
    speed_cache().set_exact(query, response);
}

/// Get tool result from cache
pub fn cache_tool_get(tool: &str, args: &serde_json::Value) -> Option<String> {
    speed_cache().get_tool_result(tool, args)
}

/// Store tool result in cache
pub fn cache_tool_set(tool: &str, args: &serde_json::Value, result: &str) {
    speed_cache().set_tool_result(tool, args, result);
}

/// Get cache stats
pub fn cache_stats() -> CacheStats {
    speed_cache().stats().clone()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_exact_cache() {
        let mut cache = SpeedCache::new();

        let response = CachedResponse {
            query: "git status".to_string(),
            response: "On branch main".to_string(),
            processing_path: "Deterministic".to_string(),
            tool_calls: vec![],
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            hit_count: 0,
            latency_ms: 50,
        };

        cache.set_exact("git status", response.clone());

        let cached = cache.get_exact("git status");
        assert!(cached.is_some());
        assert_eq!(cached.unwrap().response, "On branch main");
    }

    #[test]
    fn test_tool_cache() {
        let mut cache = SpeedCache::new();

        let args = serde_json::json!({"path": "/tmp"});
        cache.set_tool_result("read_file", &args, "file contents");

        let result = cache.get_tool_result("read_file", &args);
        assert!(result.is_some());
        assert_eq!(result.unwrap(), "file contents");
    }

    #[test]
    fn test_prefix_matching() {
        let cache = SpeedCache::new();

        let prefix = cache.match_prefix("git status please");
        assert!(prefix.is_some());
        assert_eq!(prefix.unwrap().category, "git");

        let prefix = cache.match_prefix("find all rust files");
        assert!(prefix.is_some());
        assert_eq!(prefix.unwrap().category, "search");
    }

    #[test]
    fn test_hit_rate() {
        let mut cache = SpeedCache::new();

        // Initially 0%
        assert_eq!(cache.hit_rate(), 0.0);

        // Add and hit
        let response = CachedResponse {
            query: "test".to_string(),
            response: "result".to_string(),
            processing_path: "Test".to_string(),
            tool_calls: vec![],
            timestamp: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_secs(),
            hit_count: 0,
            latency_ms: 100,
        };

        cache.set_exact("test", response);
        let _ = cache.get_exact("test");  // Hit
        let _ = cache.get_exact("missing");  // Miss

        assert!(cache.hit_rate() > 0.0);
    }

    #[test]
    fn test_categorize() {
        let cache = SpeedCache::new();

        assert_eq!(cache.categorize("git status"), Some("git".to_string()));
        assert_eq!(cache.categorize("read file.txt"), Some("file".to_string()));
        assert_eq!(cache.categorize("search for errors"), Some("search".to_string()));
        assert_eq!(cache.categorize("explain quantum physics"), None);
    }
}
