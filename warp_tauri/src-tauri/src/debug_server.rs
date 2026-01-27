//! Debug Server - HTTP endpoint for testing and inspection
//!
//! Provides real-time state queries without UI interaction.
//! Default port: 9998
//!
//! Endpoints:
//!   GET  /debug/state   - App state (tabs, conversations, errors)
//!   GET  /debug/ollama  - Ollama status (loaded models, queue)
//!   POST /debug/warm    - Force-warm models
//!   GET  /debug/ping    - Health check
//!
//! Usage from terminal:
//!   curl http://localhost:9998/debug/state
//!   curl http://localhost:9998/debug/ollama
//!   curl -X POST http://localhost:9998/debug/warm

use std::sync::atomic::{AtomicU64, Ordering};
use std::sync::Arc;
use tokio::io::{AsyncReadExt, AsyncWriteExt};
use tokio::net::TcpListener;
use tokio::sync::RwLock;

/// Debug state that can be updated from anywhere in the app
#[derive(Debug, Clone, Default)]
pub struct DebugState {
    pub active_tab: String,
    pub tab_count: u32,
    pub conversation_count: u32,
    pub last_error: Option<String>,
    pub last_model_used: Option<String>,
    pub last_route_decision: Option<String>,
    pub startup_complete: bool,
    pub models_warmed: bool,
}

lazy_static::lazy_static! {
    pub static ref DEBUG_STATE: Arc<RwLock<DebugState>> = Arc::new(RwLock::new(DebugState::default()));
    static ref REQUEST_COUNT: AtomicU64 = AtomicU64::new(0);
}

/// Update debug state - call this from anywhere in the app
pub async fn update_debug_state<F>(f: F)
where
    F: FnOnce(&mut DebugState),
{
    let mut state = DEBUG_STATE.write().await;
    f(&mut state);
}

/// Start the debug server on the specified port
pub async fn start_debug_server(port: u16) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    let addr = format!("127.0.0.1:{}", port);
    let listener = TcpListener::bind(&addr).await?;
    eprintln!("[DEBUG_SERVER] Listening on http://{}", addr);
    eprintln!("[DEBUG_SERVER] Endpoints: /debug/state, /debug/ollama, /debug/warm, /debug/ping");

    loop {
        match listener.accept().await {
            Ok((mut socket, _)) => {
                tokio::spawn(async move {
                    let mut buffer = [0u8; 4096];
                    if let Ok(n) = socket.read(&mut buffer).await {
                        if n > 0 {
                            let request = String::from_utf8_lossy(&buffer[..n]);
                            let response = handle_request(&request).await;
                            let _ = socket.write_all(response.as_bytes()).await;
                        }
                    }
                });
            }
            Err(e) => {
                eprintln!("[DEBUG_SERVER] Accept error: {}", e);
            }
        }
    }
}

async fn handle_request(request: &str) -> String {
    REQUEST_COUNT.fetch_add(1, Ordering::SeqCst);

    // Parse the request line
    let first_line = request.lines().next().unwrap_or("");
    let parts: Vec<&str> = first_line.split_whitespace().collect();

    if parts.len() < 2 {
        return http_response(400, "Bad Request");
    }

    let method = parts[0];
    let path = parts[1];

    match (method, path) {
        ("GET", "/debug/ping") => {
            http_json(200, r#"{"status":"ok","server":"sam-debug"}"#)
        }
        ("GET", "/debug/state") => {
            let state = DEBUG_STATE.read().await;
            let json = serde_json::json!({
                "active_tab": state.active_tab,
                "tab_count": state.tab_count,
                "conversation_count": state.conversation_count,
                "last_error": state.last_error,
                "last_model_used": state.last_model_used,
                "last_route_decision": state.last_route_decision,
                "startup_complete": state.startup_complete,
                "models_warmed": state.models_warmed,
                "request_count": REQUEST_COUNT.load(Ordering::SeqCst),
            });
            http_json(200, &json.to_string())
        }
        ("GET", "/debug/ollama") => {
            match get_ollama_status().await {
                Ok(json) => http_json(200, &json),
                Err(e) => http_json(500, &format!(r#"{{"error":"{}"}}"#, e)),
            }
        }
        ("POST", "/debug/warm") => {
            match warm_models().await {
                Ok(msg) => http_json(200, &format!(r#"{{"status":"ok","message":"{}"}}"#, msg)),
                Err(e) => http_json(500, &format!(r#"{{"error":"{}"}}"#, e)),
            }
        }
        ("GET", "/debug/help") => {
            let help = serde_json::json!({
                "endpoints": {
                    "GET /debug/ping": "Health check",
                    "GET /debug/state": "App state (tabs, errors, routing)",
                    "GET /debug/ollama": "Ollama model status",
                    "POST /debug/warm": "Force-warm all models",
                    "GET /debug/help": "This help message"
                }
            });
            http_json(200, &help.to_string())
        }
        _ => {
            http_response(404, "Not Found. Try GET /debug/help")
        }
    }
}

async fn get_ollama_status() -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .map_err(|e| e.to_string())?;

    // Get loaded models
    let ps_response = client
        .get("http://localhost:11434/api/ps")
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json::<serde_json::Value>()
        .await
        .map_err(|e| e.to_string())?;

    let models = ps_response.get("models").cloned().unwrap_or(serde_json::json!([]));
    let loaded_count = models.as_array().map(|a| a.len()).unwrap_or(0);

    // Get available models
    let tags_response = client
        .get("http://localhost:11434/api/tags")
        .send()
        .await
        .map_err(|e| e.to_string())?
        .json::<serde_json::Value>()
        .await
        .map_err(|e| e.to_string())?;

    let available = tags_response.get("models").cloned().unwrap_or(serde_json::json!([]));
    let available_count = available.as_array().map(|a| a.len()).unwrap_or(0);

    let result = serde_json::json!({
        "status": "running",
        "loaded_models": models,
        "loaded_count": loaded_count,
        "available_count": available_count,
        "ollama_url": "http://localhost:11434"
    });

    Ok(result.to_string())
}

async fn warm_models() -> Result<String, String> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(180))
        .build()
        .map_err(|e| e.to_string())?;

    let models = vec!["sam-trained:latest", "qwen2.5-coder:1.5b"];
    let mut results = Vec::new();

    for model in &models {
        let res = client
            .post("http://localhost:11434/api/generate")
            .json(&serde_json::json!({
                "model": model,
                "prompt": ".",
                "keep_alive": -1,
                "stream": false,
                "options": {"num_predict": 1}
            }))
            .send()
            .await;

        match res {
            Ok(_) => results.push(format!("{}: ok", model)),
            Err(e) => results.push(format!("{}: {}", model, e)),
        }
    }

    // Update debug state
    update_debug_state(|state| {
        state.models_warmed = true;
    }).await;

    Ok(results.join(", "))
}

fn http_response(status: u16, body: &str) -> String {
    let status_text = match status {
        200 => "OK",
        400 => "Bad Request",
        404 => "Not Found",
        500 => "Internal Server Error",
        _ => "Unknown",
    };

    format!(
        "HTTP/1.1 {} {}\r\nContent-Type: text/plain\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        status, status_text, body.len(), body
    )
}

fn http_json(status: u16, body: &str) -> String {
    let status_text = match status {
        200 => "OK",
        400 => "Bad Request",
        404 => "Not Found",
        500 => "Internal Server Error",
        _ => "Unknown",
    };

    format!(
        "HTTP/1.1 {} {}\r\nContent-Type: application/json\r\nContent-Length: {}\r\nAccess-Control-Allow-Origin: *\r\nConnection: close\r\n\r\n{}",
        status, status_text, body.len(), body
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_debug_state_update() {
        update_debug_state(|state| {
            state.active_tab = "test".to_string();
            state.tab_count = 5;
        }).await;

        let state = DEBUG_STATE.read().await;
        assert_eq!(state.active_tab, "test");
        assert_eq!(state.tab_count, 5);
    }
}
