// Streaming - Progressive output for instant paths
//
// Makes even fast responses feel responsive by streaming:
// 1. Deterministic command output line-by-line
// 2. Embedding search results as found
// 3. Template generation progressively

use serde::{Deserialize, Serialize};
use std::sync::mpsc::{self, Sender, Receiver};
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum StreamChunk {
    /// Text content to display
    Text(String),
    /// A code block starting (language hint)
    CodeStart(String),
    /// Code content within a code block
    CodeContent(String),
    /// End of code block
    CodeEnd,
    /// A search result found
    SearchResult(SearchResultChunk),
    /// Progress update
    Progress(ProgressChunk),
    /// Metadata (timing, source, etc.)
    Meta(MetaChunk),
    /// Stream complete
    Done,
    /// Error occurred
    Error(String),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResultChunk {
    pub file_path: String,
    pub line_number: usize,
    pub snippet: String,
    pub relevance: f32,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProgressChunk {
    pub current: u32,
    pub total: u32,
    pub message: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetaChunk {
    pub key: String,
    pub value: String,
}

// =============================================================================
// STREAM HANDLE
// =============================================================================

/// Handle for sending stream chunks
pub struct StreamSender {
    tx: Sender<StreamChunk>,
    chunk_delay_ms: u64,
}

impl StreamSender {
    /// Create a new stream sender with optional delay between chunks
    pub fn new(tx: Sender<StreamChunk>, chunk_delay_ms: u64) -> Self {
        Self { tx, chunk_delay_ms }
    }

    /// Send a text chunk
    pub fn text(&self, text: &str) {
        let _ = self.tx.send(StreamChunk::Text(text.to_string()));
        self.delay();
    }

    /// Send text line by line with optional delay
    pub fn text_lines(&self, text: &str) {
        for line in text.lines() {
            let _ = self.tx.send(StreamChunk::Text(format!("{}\n", line)));
            self.delay();
        }
    }

    /// Start a code block
    pub fn code_start(&self, language: &str) {
        let _ = self.tx.send(StreamChunk::CodeStart(language.to_string()));
    }

    /// Send code content
    pub fn code(&self, code: &str) {
        let _ = self.tx.send(StreamChunk::CodeContent(code.to_string()));
        self.delay();
    }

    /// Send code line by line
    pub fn code_lines(&self, code: &str) {
        for line in code.lines() {
            let _ = self.tx.send(StreamChunk::CodeContent(format!("{}\n", line)));
            self.delay();
        }
    }

    /// End a code block
    pub fn code_end(&self) {
        let _ = self.tx.send(StreamChunk::CodeEnd);
    }

    /// Send a search result
    pub fn search_result(&self, file_path: &str, line_number: usize, snippet: &str, relevance: f32) {
        let _ = self.tx.send(StreamChunk::SearchResult(SearchResultChunk {
            file_path: file_path.to_string(),
            line_number,
            snippet: snippet.to_string(),
            relevance,
        }));
        self.delay();
    }

    /// Send progress update
    pub fn progress(&self, current: u32, total: u32, message: &str) {
        let _ = self.tx.send(StreamChunk::Progress(ProgressChunk {
            current,
            total,
            message: message.to_string(),
        }));
    }

    /// Send metadata
    pub fn meta(&self, key: &str, value: &str) {
        let _ = self.tx.send(StreamChunk::Meta(MetaChunk {
            key: key.to_string(),
            value: value.to_string(),
        }));
    }

    /// Signal completion
    pub fn done(&self) {
        let _ = self.tx.send(StreamChunk::Done);
    }

    /// Signal error
    pub fn error(&self, msg: &str) {
        let _ = self.tx.send(StreamChunk::Error(msg.to_string()));
    }

    fn delay(&self) {
        if self.chunk_delay_ms > 0 {
            std::thread::sleep(std::time::Duration::from_millis(self.chunk_delay_ms));
        }
    }
}

/// Handle for receiving stream chunks
pub struct StreamReceiver {
    rx: Receiver<StreamChunk>,
}

impl StreamReceiver {
    /// Create a new stream receiver
    pub fn new(rx: Receiver<StreamChunk>) -> Self {
        Self { rx }
    }

    /// Receive next chunk (blocking)
    pub fn recv(&self) -> Option<StreamChunk> {
        self.rx.recv().ok()
    }

    /// Try to receive next chunk (non-blocking)
    pub fn try_recv(&self) -> Option<StreamChunk> {
        self.rx.try_recv().ok()
    }

    /// Collect all chunks into a string
    pub fn collect_text(&self) -> String {
        let mut result = String::new();
        while let Ok(chunk) = self.rx.recv() {
            match chunk {
                StreamChunk::Text(t) => result.push_str(&t),
                StreamChunk::CodeContent(c) => result.push_str(&c),
                StreamChunk::Done => break,
                StreamChunk::Error(e) => {
                    result.push_str(&format!("\nError: {}", e));
                    break;
                }
                _ => {}
            }
        }
        result
    }

    /// Iterate over chunks
    pub fn iter(&self) -> StreamIter<'_> {
        StreamIter { rx: &self.rx }
    }
}

pub struct StreamIter<'a> {
    rx: &'a Receiver<StreamChunk>,
}

impl<'a> Iterator for StreamIter<'a> {
    type Item = StreamChunk;

    fn next(&mut self) -> Option<Self::Item> {
        match self.rx.recv() {
            Ok(StreamChunk::Done) => None,
            Ok(chunk) => Some(chunk),
            Err(_) => None,
        }
    }
}

// =============================================================================
// STREAM CREATION
// =============================================================================

/// Create a streaming channel pair
pub fn create_stream() -> (StreamSender, StreamReceiver) {
    create_stream_with_delay(0)
}

/// Create a streaming channel pair with delay between chunks
pub fn create_stream_with_delay(delay_ms: u64) -> (StreamSender, StreamReceiver) {
    let (tx, rx) = mpsc::channel();
    (StreamSender::new(tx, delay_ms), StreamReceiver::new(rx))
}

// =============================================================================
// STREAMING HELPERS
// =============================================================================

/// Stream shell command output
pub fn stream_shell_output(sender: &StreamSender, output: &str) {
    sender.meta("type", "shell_output");
    sender.text_lines(output);
    sender.done();
}

/// Stream file content
pub fn stream_file_content(sender: &StreamSender, path: &str, content: &str) {
    sender.meta("type", "file_content");
    sender.meta("path", path);

    // Detect language from extension
    let language = detect_language(path);
    sender.code_start(&language);
    sender.code_lines(content);
    sender.code_end();
    sender.done();
}

/// Stream search results progressively
pub fn stream_search_results<F>(sender: &StreamSender, search_fn: F)
where
    F: FnOnce(&StreamSender),
{
    sender.meta("type", "search_results");
    search_fn(sender);
    sender.done();
}

/// Stream template generation
pub fn stream_template(sender: &StreamSender, template_name: &str, code: &str) {
    sender.meta("type", "template");
    sender.meta("template", template_name);
    sender.text(&format!("Generated from template: {}\n\n", template_name));
    sender.code_start(&detect_language_from_template(template_name));
    sender.code_lines(code);
    sender.code_end();
    sender.done();
}

// =============================================================================
// LANGUAGE DETECTION
// =============================================================================

fn detect_language(path: &str) -> String {
    let ext = path.rsplit('.').next().unwrap_or("");
    match ext {
        "rs" => "rust",
        "js" => "javascript",
        "jsx" => "jsx",
        "ts" => "typescript",
        "tsx" => "tsx",
        "py" => "python",
        "go" => "go",
        "java" => "java",
        "cpp" | "cc" | "cxx" => "cpp",
        "c" => "c",
        "h" | "hpp" => "cpp",
        "rb" => "ruby",
        "php" => "php",
        "swift" => "swift",
        "kt" => "kotlin",
        "scala" => "scala",
        "sh" | "bash" => "bash",
        "json" => "json",
        "yaml" | "yml" => "yaml",
        "toml" => "toml",
        "md" => "markdown",
        "html" => "html",
        "css" => "css",
        "scss" | "sass" => "scss",
        "sql" => "sql",
        "graphql" | "gql" => "graphql",
        _ => "text",
    }.to_string()
}

fn detect_language_from_template(template_name: &str) -> String {
    if template_name.contains("react") || template_name.contains("jsx") {
        "tsx".to_string()
    } else if template_name.contains("ts") || template_name.contains("typescript") {
        "typescript".to_string()
    } else if template_name.contains("rust") {
        "rust".to_string()
    } else if template_name.contains("python") {
        "python".to_string()
    } else if template_name.contains("go") {
        "go".to_string()
    } else {
        "text".to_string()
    }
}

// =============================================================================
// ACTIVE STREAMS REGISTRY
// =============================================================================

/// Registry for active streams (for Tauri event forwarding)
pub struct StreamRegistry {
    streams: std::collections::HashMap<String, Arc<Mutex<Vec<StreamChunk>>>>,
}

impl StreamRegistry {
    pub fn new() -> Self {
        Self {
            streams: std::collections::HashMap::new(),
        }
    }

    /// Create a new buffered stream
    pub fn create(&mut self, id: &str) -> String {
        let stream_id = if id.is_empty() {
            uuid::Uuid::new_v4().to_string()
        } else {
            id.to_string()
        };

        self.streams.insert(stream_id.clone(), Arc::new(Mutex::new(Vec::new())));
        stream_id
    }

    /// Add chunk to stream buffer
    pub fn push(&mut self, stream_id: &str, chunk: StreamChunk) {
        if let Some(buffer) = self.streams.get(stream_id) {
            if let Ok(mut buf) = buffer.lock() {
                buf.push(chunk);
            }
        }
    }

    /// Get and clear buffered chunks
    pub fn drain(&mut self, stream_id: &str) -> Vec<StreamChunk> {
        if let Some(buffer) = self.streams.get(stream_id) {
            if let Ok(mut buf) = buffer.lock() {
                return std::mem::take(&mut *buf);
            }
        }
        Vec::new()
    }

    /// Remove a stream
    pub fn remove(&mut self, stream_id: &str) {
        self.streams.remove(stream_id);
    }

    /// Check if stream exists
    pub fn exists(&self, stream_id: &str) -> bool {
        self.streams.contains_key(stream_id)
    }
}

// Global registry
lazy_static::lazy_static! {
    static ref STREAM_REGISTRY: Mutex<StreamRegistry> = Mutex::new(StreamRegistry::new());
}

pub fn stream_registry() -> std::sync::MutexGuard<'static, StreamRegistry> {
    STREAM_REGISTRY.lock().unwrap()
}

// =============================================================================
// PUBLIC API
// =============================================================================

/// Create a new stream and return its ID
pub fn create_buffered_stream(id: Option<&str>) -> String {
    stream_registry().create(id.unwrap_or(""))
}

/// Push a chunk to a buffered stream
pub fn push_to_stream(stream_id: &str, chunk: StreamChunk) {
    stream_registry().push(stream_id, chunk);
}

/// Drain chunks from a buffered stream
pub fn drain_stream(stream_id: &str) -> Vec<StreamChunk> {
    stream_registry().drain(stream_id)
}

/// Close and remove a stream
pub fn close_stream(stream_id: &str) {
    stream_registry().remove(stream_id);
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stream_text() {
        let (sender, receiver) = create_stream();

        std::thread::spawn(move || {
            sender.text("Hello ");
            sender.text("World!");
            sender.done();
        });

        let result = receiver.collect_text();
        assert_eq!(result, "Hello World!");
    }

    #[test]
    fn test_stream_lines() {
        let (sender, receiver) = create_stream();

        std::thread::spawn(move || {
            sender.text_lines("Line 1\nLine 2\nLine 3");
            sender.done();
        });

        let result = receiver.collect_text();
        assert_eq!(result, "Line 1\nLine 2\nLine 3\n");
    }

    #[test]
    fn test_stream_code() {
        let (sender, receiver) = create_stream();

        std::thread::spawn(move || {
            sender.code_start("rust");
            sender.code("fn main() {\n    println!(\"Hello\");\n}\n");
            sender.code_end();
            sender.done();
        });

        let result = receiver.collect_text();
        assert!(result.contains("fn main()"));
    }

    #[test]
    fn test_stream_iterator() {
        let (sender, receiver) = create_stream();

        std::thread::spawn(move || {
            sender.text("One");
            sender.text("Two");
            sender.text("Three");
            sender.done();
        });

        let chunks: Vec<_> = receiver.iter().collect();
        assert_eq!(chunks.len(), 3);
    }

    #[test]
    fn test_language_detection() {
        assert_eq!(detect_language("main.rs"), "rust");
        assert_eq!(detect_language("app.tsx"), "tsx");
        assert_eq!(detect_language("script.py"), "python");
        assert_eq!(detect_language("unknown.xyz"), "text");
    }

    #[test]
    fn test_buffered_stream() {
        let stream_id = create_buffered_stream(Some("test-stream"));

        push_to_stream(&stream_id, StreamChunk::Text("Hello".to_string()));
        push_to_stream(&stream_id, StreamChunk::Text("World".to_string()));

        let chunks = drain_stream(&stream_id);
        assert_eq!(chunks.len(), 2);

        // Drain again should be empty
        let chunks2 = drain_stream(&stream_id);
        assert_eq!(chunks2.len(), 0);

        close_stream(&stream_id);
    }
}
