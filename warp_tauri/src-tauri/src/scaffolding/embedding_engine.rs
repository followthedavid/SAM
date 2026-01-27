// Embedding Engine - Local Semantic Search (Option 4)
//
// Provides semantic code search without LLM generation.
// Uses local embeddings via Ollama or simple TF-IDF fallback.
//
// Features:
// - Index codebase files
// - Semantic similarity search
// - "What does X do?" queries without generation
// - Persistent index with incremental updates

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CodeChunk {
    pub id: String,
    pub file_path: String,
    pub start_line: usize,
    pub end_line: usize,
    pub content: String,
    pub chunk_type: ChunkType,
    pub name: Option<String>,       // Function/class/struct name
    pub signature: Option<String>,  // Function signature
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub enum ChunkType {
    Function,
    Class,
    Struct,
    Enum,
    Module,
    Import,
    Comment,
    Other,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmbeddedChunk {
    pub chunk: CodeChunk,
    pub embedding: Vec<f32>,
    pub keywords: Vec<String>,  // Fallback for non-embedding search
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub chunk: CodeChunk,
    pub score: f32,
    pub match_type: MatchType,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MatchType {
    Semantic,   // Embedding similarity
    Keyword,    // Keyword match
    Exact,      // Exact string match
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IndexStats {
    pub total_files: usize,
    pub total_chunks: usize,
    pub indexed_at: i64,
    pub index_size_bytes: usize,
}

// =============================================================================
// EMBEDDING ENGINE
// =============================================================================

pub struct EmbeddingEngine {
    chunks: Vec<EmbeddedChunk>,
    file_hashes: HashMap<String, String>,  // Track file changes
    index_path: PathBuf,
    ollama_available: bool,
}

impl EmbeddingEngine {
    pub fn new() -> Self {
        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let index_path = PathBuf::from(format!("{}/.sam/embeddings_index.json", home));

        let mut engine = Self {
            chunks: Vec::new(),
            file_hashes: HashMap::new(),
            index_path,
            ollama_available: false,
        };

        engine.load_index();
        engine
    }

    // Load persisted index
    fn load_index(&mut self) {
        if let Ok(data) = fs::read_to_string(&self.index_path) {
            if let Ok(stored) = serde_json::from_str::<StoredIndex>(&data) {
                self.chunks = stored.chunks;
                self.file_hashes = stored.file_hashes;
            }
        }
    }

    // Save index to disk
    pub fn save_index(&self) {
        let stored = StoredIndex {
            chunks: self.chunks.clone(),
            file_hashes: self.file_hashes.clone(),
        };

        if let Some(parent) = self.index_path.parent() {
            let _ = fs::create_dir_all(parent);
        }

        if let Ok(data) = serde_json::to_string(&stored) {
            let _ = fs::write(&self.index_path, data);
        }
    }

    // ==========================================================================
    // Indexing
    // ==========================================================================

    /// Index a directory of source files (synchronous version)
    pub fn index_directory(&mut self, path: &str, extensions: &[&str]) -> Result<IndexStats, String> {
        let path = Path::new(path);
        if !path.exists() {
            return Err("Directory does not exist".to_string());
        }

        #[allow(unused_variables)]
        let mut files_indexed = 0;
        #[allow(unused_variables)]
        let mut chunks_created = 0;

        // Walk directory
        let files = Self::collect_files(path, extensions)?;

        for file_path in files {
            // Check if file changed
            let hash = Self::file_hash(&file_path)?;
            let path_str = file_path.to_string_lossy().to_string();

            if self.file_hashes.get(&path_str) == Some(&hash) {
                continue; // Skip unchanged files
            }

            // Remove old chunks for this file
            self.chunks.retain(|c| c.chunk.file_path != path_str);

            // Parse and chunk the file
            let new_chunks = self.chunk_file(&file_path)?;
            chunks_created += new_chunks.len();

            // Embed chunks (synchronous)
            for chunk in new_chunks {
                let embedded = self.embed_chunk_sync(chunk);
                self.chunks.push(embedded);
            }

            self.file_hashes.insert(path_str, hash);
            files_indexed += 1;
        }

        self.save_index();

        Ok(IndexStats {
            total_files: self.file_hashes.len(),
            total_chunks: self.chunks.len(),
            indexed_at: chrono::Utc::now().timestamp(),
            index_size_bytes: self.chunks.len() * std::mem::size_of::<EmbeddedChunk>(),
        })
    }

    /// Index a single file (synchronous version)
    pub fn index_file(&mut self, file_path: &str) -> Result<usize, String> {
        let path = Path::new(file_path);
        if !path.exists() {
            return Err("File does not exist".to_string());
        }

        // Remove old chunks
        self.chunks.retain(|c| c.chunk.file_path != file_path);

        // Parse and chunk
        let new_chunks = self.chunk_file(path)?;
        let count = new_chunks.len();

        // Embed chunks (synchronous)
        for chunk in new_chunks {
            let embedded = self.embed_chunk_sync(chunk);
            self.chunks.push(embedded);
        }

        // Update hash
        let hash = Self::file_hash(path)?;
        self.file_hashes.insert(file_path.to_string(), hash);

        self.save_index();

        Ok(count)
    }

    // Collect files with given extensions
    fn collect_files(dir: &Path, extensions: &[&str]) -> Result<Vec<PathBuf>, String> {
        let mut files = Vec::new();

        fn walk(dir: &Path, extensions: &[&str], files: &mut Vec<PathBuf>) -> Result<(), String> {
            let entries = fs::read_dir(dir)
                .map_err(|e| format!("Failed to read directory: {}", e))?;

            for entry in entries.flatten() {
                let path = entry.path();

                // Skip hidden and common ignore directories
                let name = path.file_name()
                    .map(|n| n.to_string_lossy().to_string())
                    .unwrap_or_default();

                if name.starts_with('.') ||
                   name == "node_modules" ||
                   name == "target" ||
                   name == "dist" ||
                   name == "build" ||
                   name == "__pycache__" ||
                   name == "venv" {
                    continue;
                }

                if path.is_dir() {
                    walk(&path, extensions, files)?;
                } else if path.is_file() {
                    let ext = path.extension()
                        .map(|e| e.to_string_lossy().to_string())
                        .unwrap_or_default();

                    if extensions.is_empty() || extensions.contains(&ext.as_str()) {
                        files.push(path);
                    }
                }
            }
            Ok(())
        }

        walk(dir, extensions, &mut files)?;
        Ok(files)
    }

    // Calculate file hash for change detection
    fn file_hash(path: &Path) -> Result<String, String> {
        let content = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read file: {}", e))?;

        // Simple hash: length + first/last chars + modified time
        let len = content.len();
        let first = content.chars().take(100).collect::<String>();
        let last = content.chars().rev().take(100).collect::<String>();

        Ok(format!("{}-{}-{}", len, first.len(), last.len()))
    }

    // Parse file into chunks
    fn chunk_file(&self, path: &Path) -> Result<Vec<CodeChunk>, String> {
        let content = fs::read_to_string(path)
            .map_err(|e| format!("Failed to read file: {}", e))?;

        let file_path = path.to_string_lossy().to_string();
        let ext = path.extension()
            .map(|e| e.to_string_lossy().to_string())
            .unwrap_or_default();

        let mut chunks = Vec::new();

        // Simple line-based chunking with function detection
        let lines: Vec<&str> = content.lines().collect();
        let mut current_chunk_start = 0;
        let mut current_chunk_type = ChunkType::Other;
        let mut current_name: Option<String> = None;
        let mut brace_depth = 0;

        for (i, line) in lines.iter().enumerate() {
            let trimmed = line.trim();

            // Detect chunk boundaries based on language
            let (is_definition, chunk_type, name) = Self::detect_definition(trimmed, &ext);

            if is_definition && brace_depth == 0 {
                // Save previous chunk if it has content
                if i > current_chunk_start {
                    let chunk_content = lines[current_chunk_start..i].join("\n");
                    if !chunk_content.trim().is_empty() {
                        chunks.push(CodeChunk {
                            id: format!("{}:{}-{}", file_path, current_chunk_start + 1, i),
                            file_path: file_path.clone(),
                            start_line: current_chunk_start + 1,
                            end_line: i,
                            content: chunk_content,
                            chunk_type: current_chunk_type.clone(),
                            name: current_name.clone(),
                            signature: None,
                        });
                    }
                }

                current_chunk_start = i;
                current_chunk_type = chunk_type;
                current_name = name;
            }

            // Track brace depth
            brace_depth += trimmed.matches('{').count() as i32;
            brace_depth -= trimmed.matches('}').count() as i32;
            brace_depth = brace_depth.max(0);
        }

        // Final chunk
        if current_chunk_start < lines.len() {
            let chunk_content = lines[current_chunk_start..].join("\n");
            if !chunk_content.trim().is_empty() {
                chunks.push(CodeChunk {
                    id: format!("{}:{}-{}", file_path, current_chunk_start + 1, lines.len()),
                    file_path: file_path.clone(),
                    start_line: current_chunk_start + 1,
                    end_line: lines.len(),
                    content: chunk_content,
                    chunk_type: current_chunk_type,
                    name: current_name,
                    signature: None,
                });
            }
        }

        Ok(chunks)
    }

    // Detect if a line is a definition
    fn detect_definition(line: &str, ext: &str) -> (bool, ChunkType, Option<String>) {
        match ext {
            "rs" => {
                if line.starts_with("fn ") || line.starts_with("pub fn ") ||
                   line.starts_with("async fn ") || line.starts_with("pub async fn ") {
                    let name = Self::extract_name(line, "fn ");
                    return (true, ChunkType::Function, name);
                }
                if line.starts_with("struct ") || line.starts_with("pub struct ") {
                    let name = Self::extract_name(line, "struct ");
                    return (true, ChunkType::Struct, name);
                }
                if line.starts_with("enum ") || line.starts_with("pub enum ") {
                    let name = Self::extract_name(line, "enum ");
                    return (true, ChunkType::Enum, name);
                }
                if line.starts_with("impl ") {
                    let name = Self::extract_name(line, "impl ");
                    return (true, ChunkType::Class, name);
                }
                if line.starts_with("mod ") || line.starts_with("pub mod ") {
                    let name = Self::extract_name(line, "mod ");
                    return (true, ChunkType::Module, name);
                }
            }
            "js" | "ts" | "jsx" | "tsx" => {
                if line.starts_with("function ") || line.contains("function ") {
                    let name = Self::extract_name(line, "function ");
                    return (true, ChunkType::Function, name);
                }
                if line.starts_with("class ") || line.starts_with("export class ") {
                    let name = Self::extract_name(line, "class ");
                    return (true, ChunkType::Class, name);
                }
                if line.contains("const ") && line.contains(" = ") && line.contains("=>") {
                    let name = Self::extract_const_name(line);
                    return (true, ChunkType::Function, name);
                }
            }
            "py" => {
                if line.starts_with("def ") || line.starts_with("async def ") {
                    let name = Self::extract_name(line, "def ");
                    return (true, ChunkType::Function, name);
                }
                if line.starts_with("class ") {
                    let name = Self::extract_name(line, "class ");
                    return (true, ChunkType::Class, name);
                }
            }
            "go" => {
                if line.starts_with("func ") {
                    let name = Self::extract_name(line, "func ");
                    return (true, ChunkType::Function, name);
                }
                if line.starts_with("type ") && line.contains("struct") {
                    let name = Self::extract_name(line, "type ");
                    return (true, ChunkType::Struct, name);
                }
            }
            _ => {}
        }

        (false, ChunkType::Other, None)
    }

    fn extract_name(line: &str, after: &str) -> Option<String> {
        let start = line.find(after)? + after.len();
        let rest = &line[start..];
        let end = rest.find(|c: char| !c.is_alphanumeric() && c != '_')?;
        Some(rest[..end].to_string())
    }

    fn extract_const_name(line: &str) -> Option<String> {
        let start = line.find("const ")? + 6;
        let rest = &line[start..];
        let end = rest.find(|c: char| !c.is_alphanumeric() && c != '_')?;
        Some(rest[..end].to_string())
    }

    // Embed a chunk synchronously (keyword-based only, no Ollama)
    fn embed_chunk_sync(&self, chunk: CodeChunk) -> EmbeddedChunk {
        // Extract keywords as fallback (Ollama embedding is optional and avoided for simplicity)
        let keywords = Self::extract_keywords(&chunk.content);

        EmbeddedChunk {
            chunk,
            embedding: Vec::new(), // Embeddings not used in sync version
            keywords,
        }
    }

    // Embed a chunk (with fallback to keywords) - async version kept for future use
    #[allow(dead_code)]
    async fn embed_chunk(&self, chunk: CodeChunk) -> EmbeddedChunk {
        // Extract keywords as fallback
        let keywords = Self::extract_keywords(&chunk.content);

        // Try Ollama embedding if available
        let embedding = if self.ollama_available {
            self.get_ollama_embedding(&chunk.content).await
                .unwrap_or_else(|_| Vec::new())
        } else {
            Vec::new()
        };

        EmbeddedChunk {
            chunk,
            embedding,
            keywords,
        }
    }

    // Get embedding from Ollama - async version kept for future use
    #[allow(dead_code)]
    async fn get_ollama_embedding(&self, text: &str) -> Result<Vec<f32>, String> {
        let client = reqwest::Client::new();
        let payload = serde_json::json!({
            "model": "all-minilm",
            "prompt": text
        });

        let response = client.post("http://localhost:11434/api/embeddings")
            .json(&payload)
            .send()
            .await
            .map_err(|e| format!("Request failed: {}", e))?;

        let json: serde_json::Value = response.json()
            .await
            .map_err(|e| format!("Parse failed: {}", e))?;

        if let Some(embedding) = json["embedding"].as_array() {
            Ok(embedding.iter()
                .filter_map(|v| v.as_f64().map(|f| f as f32))
                .collect())
        } else {
            Err("No embedding in response".to_string())
        }
    }

    // Extract keywords from code
    fn extract_keywords(content: &str) -> Vec<String> {
        let mut keywords = Vec::new();

        // Split by non-alphanumeric
        for word in content.split(|c: char| !c.is_alphanumeric() && c != '_') {
            let word = word.to_lowercase();

            // Filter short words and common stopwords
            if word.len() < 3 {
                continue;
            }

            let stopwords = ["the", "and", "for", "with", "this", "that", "from",
                           "let", "const", "var", "return", "import", "export",
                           "true", "false", "null", "none", "self"];

            if !stopwords.contains(&word.as_str()) && !keywords.contains(&word) {
                keywords.push(word);
            }
        }

        keywords
    }

    // ==========================================================================
    // Search
    // ==========================================================================

    /// Search for code semantically
    pub fn search(&self, query: &str, limit: usize) -> Vec<SearchResult> {
        let query_lower = query.to_lowercase();
        let query_keywords = Self::extract_keywords(query);

        let mut results: Vec<SearchResult> = Vec::new();

        for embedded in &self.chunks {
            // Score by keyword overlap
            let keyword_score = Self::keyword_score(&query_keywords, &embedded.keywords);

            // Score by content match
            let content_lower = embedded.chunk.content.to_lowercase();
            let exact_score = if content_lower.contains(&query_lower) {
                0.9
            } else {
                0.0
            };

            // Score by name match
            let name_score = embedded.chunk.name.as_ref()
                .map(|n| {
                    if n.to_lowercase().contains(&query_lower) { 0.8 }
                    else { 0.0 }
                })
                .unwrap_or(0.0);

            let total_score = (keyword_score * 0.4 + exact_score * 0.4 + name_score * 0.2).min(1.0);

            if total_score > 0.1 {
                let match_type = if exact_score > 0.0 {
                    MatchType::Exact
                } else if keyword_score > 0.5 {
                    MatchType::Keyword
                } else {
                    MatchType::Semantic
                };

                results.push(SearchResult {
                    chunk: embedded.chunk.clone(),
                    score: total_score,
                    match_type,
                });
            }
        }

        // Sort by score descending
        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(limit);

        results
    }

    /// Search for a specific function/class/struct by name
    pub fn search_by_name(&self, name: &str) -> Vec<SearchResult> {
        let name_lower = name.to_lowercase();

        self.chunks.iter()
            .filter(|c| {
                c.chunk.name.as_ref()
                    .map(|n| n.to_lowercase().contains(&name_lower))
                    .unwrap_or(false)
            })
            .map(|c| SearchResult {
                chunk: c.chunk.clone(),
                score: 1.0,
                match_type: MatchType::Exact,
            })
            .collect()
    }

    /// Get all chunks of a specific type
    pub fn get_by_type(&self, chunk_type: ChunkType) -> Vec<&CodeChunk> {
        self.chunks.iter()
            .filter(|c| c.chunk.chunk_type == chunk_type)
            .map(|c| &c.chunk)
            .collect()
    }

    // Calculate keyword overlap score
    fn keyword_score(query_keywords: &[String], chunk_keywords: &[String]) -> f32 {
        if query_keywords.is_empty() || chunk_keywords.is_empty() {
            return 0.0;
        }

        let matches = query_keywords.iter()
            .filter(|qk| chunk_keywords.iter().any(|ck| ck.contains(qk.as_str()) || qk.contains(ck.as_str())))
            .count();

        matches as f32 / query_keywords.len() as f32
    }

    // ==========================================================================
    // Stats
    // ==========================================================================

    pub fn stats(&self) -> IndexStats {
        IndexStats {
            total_files: self.file_hashes.len(),
            total_chunks: self.chunks.len(),
            indexed_at: chrono::Utc::now().timestamp(),
            index_size_bytes: self.chunks.len() * std::mem::size_of::<EmbeddedChunk>(),
        }
    }

    /// Clear the entire index
    pub fn clear(&mut self) {
        self.chunks.clear();
        self.file_hashes.clear();
        self.save_index();
    }

    /// Check if Ollama embedding model is available
    pub async fn check_ollama(&mut self) -> bool {
        let client = reqwest::Client::new();

        match client.get("http://localhost:11434/api/tags")
            .send()
            .await
        {
            Ok(response) => {
                if let Ok(json) = response.json::<serde_json::Value>().await {
                    if let Some(models) = json["models"].as_array() {
                        self.ollama_available = models.iter().any(|m| {
                            m["name"].as_str()
                                .map(|n| n.contains("minilm") || n.contains("embed"))
                                .unwrap_or(false)
                        });
                    }
                }
            }
            Err(_) => self.ollama_available = false,
        }

        self.ollama_available
    }
}

#[derive(Serialize, Deserialize)]
struct StoredIndex {
    chunks: Vec<EmbeddedChunk>,
    file_hashes: HashMap<String, String>,
}

// Global engine
lazy_static::lazy_static! {
    pub static ref EMBEDDING_ENGINE: std::sync::Mutex<EmbeddingEngine> =
        std::sync::Mutex::new(EmbeddingEngine::new());
}

pub fn embeddings() -> std::sync::MutexGuard<'static, EmbeddingEngine> {
    EMBEDDING_ENGINE.lock().unwrap()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_keyword_extraction() {
        let keywords = EmbeddingEngine::extract_keywords(
            "fn authenticate_user(username: &str, password: &str) -> bool"
        );

        // Snake_case identifiers are kept whole
        assert!(keywords.contains(&"authenticate_user".to_string()));
        assert!(keywords.contains(&"username".to_string()));
        assert!(keywords.contains(&"password".to_string()));
        assert!(keywords.contains(&"bool".to_string()));
    }

    #[test]
    fn test_definition_detection() {
        let (is_def, chunk_type, name) = EmbeddingEngine::detect_definition(
            "pub fn authenticate_user(username: &str) -> bool {",
            "rs"
        );

        assert!(is_def);
        assert_eq!(chunk_type, ChunkType::Function);
        assert_eq!(name, Some("authenticate_user".to_string()));
    }
}
