use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Manager};
use reqwest;

#[derive(Debug, Serialize, Deserialize)]
struct OllamaRequest {
    model: String,
    prompt: String,
    stream: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    system: Option<String>,
}

/// System prompt that teaches the model how to use tools
const SAM_SYSTEM_PROMPT: &str = r#"You are SAM, an autonomous executor. Output ONLY raw JSON tool calls. NO markdown, NO code blocks, NO explanations, NO text.

Tools:
{"tool":"execute_shell","args":{"command":"COMMAND"}}
{"tool":"read_file","args":{"path":"PATH"}}
{"tool":"write_file","args":{"path":"PATH","content":"CONTENT"}}
{"tool":"glob_files","args":{"pattern":"PATTERN","basePath":"."}}
{"tool":"grep_files","args":{"pattern":"PATTERN","path":"PATH"}}

Examples:
list files → {"tool":"execute_shell","args":{"command":"ls -la"}}
reverse engineer /app → {"tool":"execute_shell","args":{"command":"file /app && strings /app | head -100"}}
check disk → {"tool":"execute_shell","args":{"command":"df -h"}}
extract archive.rar → {"tool":"execute_shell","args":{"command":"unrar x archive.rar"}}
find python files → {"tool":"glob_files","args":{"pattern":"**/*.py","basePath":"."}}
read config → {"tool":"read_file","args":{"path":"./config.json"}}

Output the JSON directly. No backticks. No explanation."#;

#[derive(Debug, Serialize, Deserialize)]
struct OllamaResponse {
    response: String,
    done: bool,
}

#[tauri::command]
pub async fn query_ollama_stream(
    app_handle: AppHandle,
    prompt: String,
    model: Option<String>,
    session_id: String,
) -> Result<(), String> {
    let model_name = model.unwrap_or_else(|| "deepseek-coder:6.7b".to_string());

    let client = reqwest::Client::new();
    let url = "http://localhost:11434/api/generate";

    let request_body = OllamaRequest {
        model: model_name,
        prompt,
        stream: true,
        system: Some(SAM_SYSTEM_PROMPT.to_string()),
    };

    let mut response = client
        .post(url)
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Ollama request failed: {}", e))?;

    let event_name = format!("ollama://stream/{}", session_id);

    while let Some(chunk) = response.chunk().await.map_err(|e| e.to_string())? {
        let text = String::from_utf8_lossy(&chunk);
        for line in text.lines() {
            if let Ok(ollama_resp) = serde_json::from_str::<OllamaResponse>(line) {
                let _ = app_handle.emit_all(&event_name, ollama_resp.response.clone());
                if ollama_resp.done {
                    let _ = app_handle.emit_all(&format!("{}/done", event_name), true);
                    break;
                }
            }
        }
    }

    Ok(())
}

#[tauri::command]
pub async fn query_ollama(
    prompt: String,
    model: Option<String>,
) -> Result<String, String> {
    let model_name = model.unwrap_or_else(|| "deepseek-coder:6.7b".to_string());
    let client = reqwest::Client::new();
    let url = "http://localhost:11434/api/generate";

    let request_body = serde_json::json!({
        "model": model_name,
        "prompt": prompt,
        "stream": false,
        "system": SAM_SYSTEM_PROMPT,
    });

    let response = client
        .post(url)
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Ollama request failed: {}", e))?
        .json::<OllamaResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    Ok(response.response)
}

/// Chat-friendly system prompt for conversational interactions
const CHAT_SYSTEM_PROMPT: &str = r#"You are SAM, a friendly and helpful AI assistant. You're knowledgeable, warm, and conversational.

Guidelines:
- Be concise but friendly - keep responses brief but personable
- Use natural language, not formal or robotic speech
- If asked about yourself, you're SAM (Sentient Assistant Module)
- You can help with code, projects, general questions, or just chat
- Show personality - be helpful but not stiff
- If you don't know something, say so naturally

Remember: You're chatting with a friend who happens to need help. Be helpful, be real."#;

#[tauri::command]
pub async fn query_ollama_chat(
    prompt: String,
    model: Option<String>,
    context: Option<String>,
) -> Result<String, String> {
    let model_name = model.unwrap_or_else(|| "qwen2.5-coder:1.5b".to_string());
    let client = reqwest::Client::new();
    let url = "http://localhost:11434/api/generate";

    // Build the full prompt with optional context
    let full_prompt = if let Some(ctx) = context {
        format!("[Context: {}]\n\nUser: {}", ctx, prompt)
    } else {
        format!("User: {}", prompt)
    };

    let request_body = serde_json::json!({
        "model": model_name,
        "prompt": full_prompt,
        "stream": false,
        "system": CHAT_SYSTEM_PROMPT,
    });

    let response = client
        .post(url)
        .json(&request_body)
        .send()
        .await
        .map_err(|e| format!("Ollama request failed: {}", e))?
        .json::<OllamaResponse>()
        .await
        .map_err(|e| format!("Failed to parse response: {}", e))?;

    Ok(response.response)
}

#[tauri::command]
pub async fn list_ollama_models() -> Result<Vec<String>, String> {
    let client = reqwest::Client::new();
    let url = "http://localhost:11434/api/tags";

    let response = client
        .get(url)
        .send()
        .await
        .map_err(|e| format!("Failed to get models: {}", e))?
        .json::<serde_json::Value>()
        .await
        .map_err(|e| format!("Failed to parse models: {}", e))?;

    let models = response["models"]
        .as_array()
        .ok_or("No models found")?
        .iter()
        .filter_map(|m| m["name"].as_str().map(String::from))
        .collect();

    Ok(models)
}
