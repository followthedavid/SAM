// Web Search and Fetch - External data lookup for agents
//
// Provides WebSearch and WebFetch capabilities similar to Claude Code:
// - WebSearch: Query search engines (DuckDuckGo, Brave)
// - WebFetch: Retrieve and parse web content
// - Caching to avoid duplicate requests
// - Rate limiting for API compliance

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{Duration, Instant};

// =============================================================================
// TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResult {
    pub title: String,
    pub url: String,
    pub snippet: String,
    pub source: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SearchResponse {
    pub query: String,
    pub results: Vec<SearchResult>,
    pub total_results: u64,
    pub search_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FetchedPage {
    pub url: String,
    pub title: Option<String>,
    pub content: String,
    pub content_type: String,
    pub status_code: u16,
    pub fetch_time_ms: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebSearchConfig {
    pub default_engine: SearchEngine,
    pub max_results: usize,
    pub timeout_ms: u64,
    pub cache_ttl_secs: u64,
    pub rate_limit_per_min: u32,
}

#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq)]
pub enum SearchEngine {
    DuckDuckGo,
    Brave,
    Google,
    Bing,
}

impl Default for WebSearchConfig {
    fn default() -> Self {
        Self {
            default_engine: SearchEngine::DuckDuckGo,
            max_results: 10,
            timeout_ms: 10000,
            cache_ttl_secs: 300, // 5 minutes
            rate_limit_per_min: 30,
        }
    }
}

// =============================================================================
// WEB SEARCH ENGINE
// =============================================================================

pub struct WebSearchEngine {
    config: WebSearchConfig,
    cache: HashMap<String, (SearchResponse, Instant)>,
    fetch_cache: HashMap<String, (FetchedPage, Instant)>,
    request_times: Vec<Instant>,
    brave_api_key: Option<String>,
}

impl WebSearchEngine {
    pub fn new(config: WebSearchConfig) -> Self {
        Self {
            config,
            cache: HashMap::new(),
            fetch_cache: HashMap::new(),
            request_times: Vec::new(),
            brave_api_key: std::env::var("BRAVE_API_KEY").ok(),
        }
    }

    /// Search the web using configured engine
    pub async fn search(&mut self, query: &str) -> Result<SearchResponse, String> {
        self.search_with_engine(query, self.config.default_engine).await
    }

    /// Search using a specific engine
    pub async fn search_with_engine(&mut self, query: &str, engine: SearchEngine) -> Result<SearchResponse, String> {
        let cache_key = format!("{}:{}", engine_name(engine), query);

        // Check cache
        if let Some((cached, timestamp)) = self.cache.get(&cache_key) {
            if timestamp.elapsed().as_secs() < self.config.cache_ttl_secs {
                return Ok(cached.clone());
            }
        }

        // Rate limiting
        self.enforce_rate_limit()?;

        let start = Instant::now();
        let results = match engine {
            SearchEngine::DuckDuckGo => self.search_duckduckgo(query).await?,
            SearchEngine::Brave => self.search_brave(query).await?,
            SearchEngine::Google => self.search_google(query).await?,
            SearchEngine::Bing => self.search_bing(query).await?,
        };

        let response = SearchResponse {
            query: query.to_string(),
            results,
            total_results: 0, // Would come from API
            search_time_ms: start.elapsed().as_millis() as u64,
        };

        // Cache result
        self.cache.insert(cache_key, (response.clone(), Instant::now()));

        Ok(response)
    }

    /// Fetch a web page and extract content
    pub async fn fetch(&mut self, url: &str) -> Result<FetchedPage, String> {
        self.fetch_with_options(url, true).await
    }

    /// Fetch with options (extract_text: convert HTML to plain text)
    pub async fn fetch_with_options(&mut self, url: &str, extract_text: bool) -> Result<FetchedPage, String> {
        // Check cache
        if let Some((cached, timestamp)) = self.fetch_cache.get(url) {
            if timestamp.elapsed().as_secs() < self.config.cache_ttl_secs {
                return Ok(cached.clone());
            }
        }

        // Rate limiting
        self.enforce_rate_limit()?;

        let start = Instant::now();

        // Use reqwest for HTTP requests
        let client = reqwest::Client::builder()
            .timeout(Duration::from_millis(self.config.timeout_ms))
            .user_agent("SAM/1.0 (AI Assistant)")
            .build()
            .map_err(|e| format!("Failed to create HTTP client: {}", e))?;

        let response = client.get(url)
            .send()
            .await
            .map_err(|e| format!("Failed to fetch {}: {}", url, e))?;

        let status_code = response.status().as_u16();
        let content_type = response
            .headers()
            .get("content-type")
            .and_then(|v| v.to_str().ok())
            .unwrap_or("text/html")
            .to_string();

        let body = response.text().await
            .map_err(|e| format!("Failed to read response body: {}", e))?;

        // Extract text from HTML if requested
        let (content, title) = if extract_text && content_type.contains("text/html") {
            let extracted = extract_text_from_html(&body);
            (extracted.0, extracted.1)
        } else {
            (body, None)
        };

        let page = FetchedPage {
            url: url.to_string(),
            title,
            content,
            content_type,
            status_code,
            fetch_time_ms: start.elapsed().as_millis() as u64,
        };

        // Cache result
        self.fetch_cache.insert(url.to_string(), (page.clone(), Instant::now()));

        Ok(page)
    }

    /// Search DuckDuckGo (uses instant answer API)
    async fn search_duckduckgo(&self, query: &str) -> Result<Vec<SearchResult>, String> {
        let url = format!(
            "https://api.duckduckgo.com/?q={}&format=json&no_html=1&skip_disambig=1",
            urlencoding::encode(query)
        );

        let client = reqwest::Client::new();
        let response = client.get(&url)
            .timeout(Duration::from_millis(self.config.timeout_ms))
            .send()
            .await
            .map_err(|e| format!("DuckDuckGo search failed: {}", e))?;

        let json: serde_json::Value = response.json().await
            .map_err(|e| format!("Failed to parse DuckDuckGo response: {}", e))?;

        let mut results = Vec::new();

        // Abstract (main result)
        if let Some(abstract_text) = json["Abstract"].as_str() {
            if !abstract_text.is_empty() {
                results.push(SearchResult {
                    title: json["Heading"].as_str().unwrap_or("Result").to_string(),
                    url: json["AbstractURL"].as_str().unwrap_or("").to_string(),
                    snippet: abstract_text.to_string(),
                    source: "DuckDuckGo".to_string(),
                });
            }
        }

        // Related topics
        if let Some(topics) = json["RelatedTopics"].as_array() {
            for topic in topics.iter().take(self.config.max_results - results.len()) {
                if let Some(text) = topic["Text"].as_str() {
                    results.push(SearchResult {
                        title: topic["FirstURL"].as_str()
                            .and_then(|u| u.split('/').last())
                            .unwrap_or("Related")
                            .to_string(),
                        url: topic["FirstURL"].as_str().unwrap_or("").to_string(),
                        snippet: text.to_string(),
                        source: "DuckDuckGo".to_string(),
                    });
                }
            }
        }

        Ok(results)
    }

    /// Search Brave (requires API key)
    async fn search_brave(&self, query: &str) -> Result<Vec<SearchResult>, String> {
        let api_key = self.brave_api_key.as_ref()
            .ok_or("Brave API key not set (BRAVE_API_KEY env var)")?;

        let url = format!(
            "https://api.search.brave.com/res/v1/web/search?q={}",
            urlencoding::encode(query)
        );

        let client = reqwest::Client::new();
        let response = client.get(&url)
            .header("Accept", "application/json")
            .header("X-Subscription-Token", api_key)
            .timeout(Duration::from_millis(self.config.timeout_ms))
            .send()
            .await
            .map_err(|e| format!("Brave search failed: {}", e))?;

        let json: serde_json::Value = response.json().await
            .map_err(|e| format!("Failed to parse Brave response: {}", e))?;

        let mut results = Vec::new();

        if let Some(web_results) = json["web"]["results"].as_array() {
            for result in web_results.iter().take(self.config.max_results) {
                results.push(SearchResult {
                    title: result["title"].as_str().unwrap_or("").to_string(),
                    url: result["url"].as_str().unwrap_or("").to_string(),
                    snippet: result["description"].as_str().unwrap_or("").to_string(),
                    source: "Brave".to_string(),
                });
            }
        }

        Ok(results)
    }

    /// Search Google (placeholder - requires API setup)
    async fn search_google(&self, _query: &str) -> Result<Vec<SearchResult>, String> {
        Err("Google search requires Custom Search API key. Use DuckDuckGo or Brave instead.".to_string())
    }

    /// Search Bing (placeholder - requires API setup)
    async fn search_bing(&self, _query: &str) -> Result<Vec<SearchResult>, String> {
        Err("Bing search requires Azure API key. Use DuckDuckGo or Brave instead.".to_string())
    }

    fn enforce_rate_limit(&mut self) -> Result<(), String> {
        let now = Instant::now();
        let one_minute_ago = now - Duration::from_secs(60);

        // Remove old timestamps
        self.request_times.retain(|t| *t > one_minute_ago);

        if self.request_times.len() >= self.config.rate_limit_per_min as usize {
            return Err(format!(
                "Rate limit exceeded: {} requests per minute",
                self.config.rate_limit_per_min
            ));
        }

        self.request_times.push(now);
        Ok(())
    }

    /// Clear all caches
    pub fn clear_cache(&mut self) {
        self.cache.clear();
        self.fetch_cache.clear();
    }

    /// Get cache statistics
    pub fn cache_stats(&self) -> (usize, usize) {
        (self.cache.len(), self.fetch_cache.len())
    }
}

// =============================================================================
// HTML TEXT EXTRACTION
// =============================================================================

/// Extract plain text and title from HTML
fn extract_text_from_html(html: &str) -> (String, Option<String>) {
    // Simple regex-based extraction (for production, use a proper HTML parser)
    let mut text = html.to_string();

    // Extract title
    let title = extract_tag_content(&text, "title");

    // Remove script and style tags
    text = remove_tag_and_content(&text, "script");
    text = remove_tag_and_content(&text, "style");
    text = remove_tag_and_content(&text, "noscript");

    // Remove all HTML tags
    let tag_regex = regex::Regex::new(r"<[^>]+>").unwrap();
    text = tag_regex.replace_all(&text, " ").to_string();

    // Decode HTML entities
    text = text.replace("&nbsp;", " ");
    text = text.replace("&amp;", "&");
    text = text.replace("&lt;", "<");
    text = text.replace("&gt;", ">");
    text = text.replace("&quot;", "\"");
    text = text.replace("&#39;", "'");

    // Normalize whitespace
    let whitespace_regex = regex::Regex::new(r"\s+").unwrap();
    text = whitespace_regex.replace_all(&text, " ").trim().to_string();

    // Truncate if too long (keep first 50KB)
    if text.len() > 50000 {
        text = text[..50000].to_string();
        text.push_str("... [truncated]");
    }

    (text, title)
}

fn extract_tag_content(html: &str, tag: &str) -> Option<String> {
    let pattern = format!(r"<{}\b[^>]*>(.*?)</{}>", tag, tag);
    let regex = regex::Regex::new(&pattern).ok()?;
    regex.captures(html)
        .and_then(|c| c.get(1))
        .map(|m| m.as_str().trim().to_string())
}

fn remove_tag_and_content(html: &str, tag: &str) -> String {
    let pattern = format!(r"(?is)<{}\b[^>]*>.*?</{}>", tag, tag);
    if let Ok(regex) = regex::Regex::new(&pattern) {
        regex.replace_all(html, "").to_string()
    } else {
        html.to_string()
    }
}

fn engine_name(engine: SearchEngine) -> &'static str {
    match engine {
        SearchEngine::DuckDuckGo => "duckduckgo",
        SearchEngine::Brave => "brave",
        SearchEngine::Google => "google",
        SearchEngine::Bing => "bing",
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref WEB_SEARCH: Mutex<WebSearchEngine> = Mutex::new(WebSearchEngine::new(WebSearchConfig::default()));
}

pub fn web_search() -> std::sync::MutexGuard<'static, WebSearchEngine> {
    WEB_SEARCH.lock().unwrap()
}

/// Search the web
pub async fn search(query: &str) -> Result<SearchResponse, String> {
    let mut engine = web_search();
    engine.search(query).await
}

/// Search with specific engine
pub async fn search_with(query: &str, engine: SearchEngine) -> Result<SearchResponse, String> {
    let mut search_engine = web_search();
    search_engine.search_with_engine(query, engine).await
}

/// Fetch a web page
pub async fn fetch(url: &str) -> Result<FetchedPage, String> {
    let mut engine = web_search();
    engine.fetch(url).await
}

/// Fetch with text extraction option
pub async fn fetch_with_options(url: &str, extract_text: bool) -> Result<FetchedPage, String> {
    let mut engine = web_search();
    engine.fetch_with_options(url, extract_text).await
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_html_extraction() {
        let html = r#"
            <html>
            <head><title>Test Page</title></head>
            <body>
                <script>alert('hi');</script>
                <p>Hello World</p>
                <style>.foo { color: red; }</style>
            </body>
            </html>
        "#;

        let (text, title) = extract_text_from_html(html);
        assert!(text.contains("Hello World"));
        assert!(!text.contains("alert"));
        assert!(!text.contains("color: red"));
        assert_eq!(title, Some("Test Page".to_string()));
    }

    #[test]
    fn test_config_default() {
        let config = WebSearchConfig::default();
        assert_eq!(config.max_results, 10);
        assert_eq!(config.default_engine, SearchEngine::DuckDuckGo);
    }

    #[test]
    fn test_engine_name() {
        assert_eq!(engine_name(SearchEngine::DuckDuckGo), "duckduckgo");
        assert_eq!(engine_name(SearchEngine::Brave), "brave");
    }
}
