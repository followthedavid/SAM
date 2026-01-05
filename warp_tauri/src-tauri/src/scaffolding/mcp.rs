// MCP - Model Context Protocol Implementation
//
// Implements the MCP specification for external tool servers.
// Supports both stdio and HTTP transports.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::{BufRead, BufReader, Write};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;

// =============================================================================
// JSON-RPC 2.0 TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcRequest {
    pub jsonrpc: String,
    pub id: Option<serde_json::Value>,
    pub method: String,
    #[serde(default)]
    pub params: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcResponse {
    pub jsonrpc: String,
    pub id: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<JsonRpcError>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JsonRpcError {
    pub code: i32,
    pub message: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub data: Option<serde_json::Value>,
}

// =============================================================================
// MCP TYPES
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpTool {
    pub name: String,
    pub description: String,
    #[serde(rename = "inputSchema")]
    pub input_schema: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpToolResult {
    pub content: Vec<McpContent>,
    #[serde(rename = "isError", default)]
    pub is_error: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum McpContent {
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "image")]
    Image { data: String, #[serde(rename = "mimeType")] mime_type: String },
    #[serde(rename = "resource")]
    Resource { uri: String, text: Option<String> },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpCapabilities {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tools: Option<ToolCapability>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub resources: Option<ResourceCapability>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub prompts: Option<PromptCapability>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolCapability {
    #[serde(rename = "listChanged", default)]
    pub list_changed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceCapability {
    #[serde(default)]
    pub subscribe: bool,
    #[serde(rename = "listChanged", default)]
    pub list_changed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PromptCapability {
    #[serde(rename = "listChanged", default)]
    pub list_changed: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerInfo {
    pub name: String,
    pub version: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InitializeResult {
    #[serde(rename = "protocolVersion")]
    pub protocol_version: String,
    pub capabilities: McpCapabilities,
    #[serde(rename = "serverInfo")]
    pub server_info: ServerInfo,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub instructions: Option<String>,
}

// =============================================================================
// MCP SERVER CONNECTION
// =============================================================================

pub struct McpServer {
    pub name: String,
    pub command: String,
    pub args: Vec<String>,
    pub env: HashMap<String, String>,
    process: Option<Child>,
    tools: Vec<McpTool>,
    initialized: bool,
    next_id: u64,
}

impl McpServer {
    pub fn new(name: &str, command: &str, args: Vec<String>) -> Self {
        Self {
            name: name.to_string(),
            command: command.to_string(),
            args,
            env: HashMap::new(),
            process: None,
            tools: Vec::new(),
            initialized: false,
            next_id: 1,
        }
    }

    pub fn with_env(mut self, key: &str, value: &str) -> Self {
        self.env.insert(key.to_string(), value.to_string());
        self
    }

    /// Start the MCP server process
    pub fn start(&mut self) -> Result<(), String> {
        let mut cmd = Command::new(&self.command);
        cmd.args(&self.args)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        for (key, value) in &self.env {
            cmd.env(key, value);
        }

        let child = cmd.spawn()
            .map_err(|e| format!("Failed to start MCP server '{}': {}", self.name, e))?;

        self.process = Some(child);
        Ok(())
    }

    /// Initialize the MCP connection
    pub fn initialize(&mut self) -> Result<InitializeResult, String> {
        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(serde_json::Value::Number(self.next_id.into())),
            method: "initialize".to_string(),
            params: serde_json::json!({
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": { "listChanged": true }
                },
                "clientInfo": {
                    "name": "SAM",
                    "version": "1.0.0"
                }
            }),
        };
        self.next_id += 1;

        let response = self.send_request(&request)?;

        // Parse initialize result
        let result: InitializeResult = serde_json::from_value(
            response.result.ok_or("No result in initialize response")?
        ).map_err(|e| format!("Failed to parse initialize result: {}", e))?;

        // Send initialized notification
        let notification = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: None,
            method: "notifications/initialized".to_string(),
            params: serde_json::json!({}),
        };
        self.send_notification(&notification)?;

        self.initialized = true;
        Ok(result)
    }

    /// List available tools from the server
    pub fn list_tools(&mut self) -> Result<Vec<McpTool>, String> {
        if !self.initialized {
            return Err("Server not initialized".to_string());
        }

        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(serde_json::Value::Number(self.next_id.into())),
            method: "tools/list".to_string(),
            params: serde_json::json!({}),
        };
        self.next_id += 1;

        let response = self.send_request(&request)?;

        #[derive(Deserialize)]
        struct ToolsListResult {
            tools: Vec<McpTool>,
        }

        let result: ToolsListResult = serde_json::from_value(
            response.result.ok_or("No result in tools/list response")?
        ).map_err(|e| format!("Failed to parse tools list: {}", e))?;

        self.tools = result.tools.clone();
        Ok(result.tools)
    }

    /// Call a tool on the server
    pub fn call_tool(&mut self, name: &str, arguments: serde_json::Value) -> Result<McpToolResult, String> {
        if !self.initialized {
            return Err("Server not initialized".to_string());
        }

        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(serde_json::Value::Number(self.next_id.into())),
            method: "tools/call".to_string(),
            params: serde_json::json!({
                "name": name,
                "arguments": arguments
            }),
        };
        self.next_id += 1;

        let response = self.send_request(&request)?;

        if let Some(error) = response.error {
            return Err(format!("Tool error: {} (code {})", error.message, error.code));
        }

        let result: McpToolResult = serde_json::from_value(
            response.result.ok_or("No result in tools/call response")?
        ).map_err(|e| format!("Failed to parse tool result: {}", e))?;

        Ok(result)
    }

    /// Get cached tools
    pub fn get_tools(&self) -> &[McpTool] {
        &self.tools
    }

    fn send_request(&mut self, request: &JsonRpcRequest) -> Result<JsonRpcResponse, String> {
        let process = self.process.as_mut()
            .ok_or("Server process not running")?;

        let stdin = process.stdin.as_mut()
            .ok_or("Failed to access stdin")?;

        let stdout = process.stdout.as_mut()
            .ok_or("Failed to access stdout")?;

        // Send request
        let request_json = serde_json::to_string(request)
            .map_err(|e| format!("Failed to serialize request: {}", e))?;

        writeln!(stdin, "{}", request_json)
            .map_err(|e| format!("Failed to write request: {}", e))?;

        stdin.flush()
            .map_err(|e| format!("Failed to flush stdin: {}", e))?;

        // Read response
        let mut reader = BufReader::new(stdout);
        let mut response_line = String::new();

        reader.read_line(&mut response_line)
            .map_err(|e| format!("Failed to read response: {}", e))?;

        let response: JsonRpcResponse = serde_json::from_str(&response_line)
            .map_err(|e| format!("Failed to parse response: {}", e))?;

        Ok(response)
    }

    fn send_notification(&mut self, notification: &JsonRpcRequest) -> Result<(), String> {
        let process = self.process.as_mut()
            .ok_or("Server process not running")?;

        let stdin = process.stdin.as_mut()
            .ok_or("Failed to access stdin")?;

        let json = serde_json::to_string(notification)
            .map_err(|e| format!("Failed to serialize notification: {}", e))?;

        writeln!(stdin, "{}", json)
            .map_err(|e| format!("Failed to write notification: {}", e))?;

        stdin.flush()
            .map_err(|e| format!("Failed to flush stdin: {}", e))?;

        Ok(())
    }

    /// Stop the server
    pub fn stop(&mut self) {
        if let Some(mut process) = self.process.take() {
            let _ = process.kill();
        }
        self.initialized = false;
        self.tools.clear();
    }
}

impl Drop for McpServer {
    fn drop(&mut self) {
        self.stop();
    }
}

// =============================================================================
// MCP MANAGER
// =============================================================================

pub struct McpManager {
    servers: HashMap<String, McpServer>,
}

impl McpManager {
    pub fn new() -> Self {
        Self {
            servers: HashMap::new(),
        }
    }

    /// Add a server configuration
    pub fn add_server(&mut self, name: &str, command: &str, args: Vec<String>) -> &mut McpServer {
        let server = McpServer::new(name, command, args);
        self.servers.insert(name.to_string(), server);
        self.servers.get_mut(name).unwrap()
    }

    /// Start and initialize a server
    pub fn connect(&mut self, name: &str) -> Result<Vec<McpTool>, String> {
        let server = self.servers.get_mut(name)
            .ok_or_else(|| format!("Server '{}' not found", name))?;

        server.start()?;
        server.initialize()?;
        server.list_tools()
    }

    /// Get all available tools across all connected servers
    pub fn all_tools(&self) -> Vec<(&str, &McpTool)> {
        let mut tools = Vec::new();
        for (server_name, server) in &self.servers {
            for tool in server.get_tools() {
                tools.push((server_name.as_str(), tool));
            }
        }
        tools
    }

    /// Call a tool on a specific server
    pub fn call_tool(&mut self, server_name: &str, tool_name: &str, args: serde_json::Value) -> Result<McpToolResult, String> {
        let server = self.servers.get_mut(server_name)
            .ok_or_else(|| format!("Server '{}' not found", server_name))?;

        server.call_tool(tool_name, args)
    }

    /// Find which server has a tool
    pub fn find_tool(&self, tool_name: &str) -> Option<&str> {
        for (server_name, server) in &self.servers {
            if server.get_tools().iter().any(|t| t.name == tool_name) {
                return Some(server_name);
            }
        }
        None
    }

    /// Disconnect all servers
    pub fn disconnect_all(&mut self) {
        for server in self.servers.values_mut() {
            server.stop();
        }
    }

    /// Get server names
    pub fn server_names(&self) -> Vec<&str> {
        self.servers.keys().map(|s| s.as_str()).collect()
    }

    /// Check if a server is connected
    pub fn is_connected(&self, name: &str) -> bool {
        self.servers.get(name)
            .map(|s| s.initialized)
            .unwrap_or(false)
    }
}

impl Default for McpManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL MCP MANAGER
// =============================================================================

lazy_static::lazy_static! {
    pub static ref MCP_MANAGER: Mutex<McpManager> = Mutex::new(McpManager::new());
}

pub fn mcp() -> std::sync::MutexGuard<'static, McpManager> {
    MCP_MANAGER.lock().unwrap()
}

/// Add an MCP server with optional environment variables
pub fn add_mcp_server(name: &str, command: &str, args: Vec<String>, env: HashMap<String, String>) {
    let mut mgr = mcp();
    let server = mgr.add_server(name, command, args);
    for (key, value) in env {
        server.env.insert(key, value);
    }
}

/// Connect to an MCP server
pub fn connect_mcp_server(name: &str) -> Result<Vec<McpTool>, String> {
    mcp().connect(name)
}

/// Call an MCP tool
pub fn call_mcp_tool(server: &str, tool: &str, args: serde_json::Value) -> Result<McpToolResult, String> {
    mcp().call_tool(server, tool, args)
}

/// Get all MCP tools
pub fn list_mcp_tools() -> Vec<(String, McpTool)> {
    let mgr = mcp();
    mgr.all_tools().iter()
        .map(|(s, t)| (s.to_string(), (*t).clone()))
        .collect()
}

// =============================================================================
// CONFIG LOADING
// =============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpServerConfig {
    pub command: String,
    #[serde(default)]
    pub args: Vec<String>,
    #[serde(default)]
    pub env: HashMap<String, String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct McpConfig {
    #[serde(rename = "mcpServers", default)]
    pub mcp_servers: HashMap<String, McpServerConfig>,
}

/// Load MCP servers from config file (Claude Code compatible format)
pub fn load_mcp_config(path: Option<&str>) -> Result<McpConfig, String> {
    let config_path = path.unwrap_or_else(|| {
        // Default path for Claude Code config
        if cfg!(target_os = "macos") {
            "~/Library/Application Support/Claude/claude_desktop_config.json"
        } else {
            "~/.config/claude/claude_desktop_config.json"
        }
    });

    // Expand ~ to home directory
    let expanded_path = if config_path.starts_with("~") {
        std::env::var("HOME")
            .map(|h| config_path.replacen("~", &h, 1))
            .unwrap_or_else(|_| config_path.to_string())
    } else {
        config_path.to_string()
    };

    let content = std::fs::read_to_string(&expanded_path)
        .map_err(|e| format!("Failed to read config from {}: {}", expanded_path, e))?;

    let config: McpConfig = serde_json::from_str(&content)
        .map_err(|e| format!("Failed to parse config: {}", e))?;

    // Load servers into manager
    let mut mgr = mcp();
    for (name, server_config) in &config.mcp_servers {
        let server = mgr.add_server(name, &server_config.command, server_config.args.clone());
        for (key, value) in &server_config.env {
            server.env.insert(key.clone(), value.clone());
        }
    }

    Ok(config)
}

/// Get list of server names
pub fn list_mcp_servers() -> Vec<String> {
    mcp().servers.keys().cloned().collect()
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_json_rpc_request_serialization() {
        let request = JsonRpcRequest {
            jsonrpc: "2.0".to_string(),
            id: Some(serde_json::Value::Number(1.into())),
            method: "tools/list".to_string(),
            params: serde_json::json!({}),
        };

        let json = serde_json::to_string(&request).unwrap();
        assert!(json.contains("jsonrpc"));
        assert!(json.contains("tools/list"));
    }

    #[test]
    fn test_mcp_tool_deserialization() {
        let json = r#"{
            "name": "calculate",
            "description": "Does math",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "a": {"type": "number"},
                    "b": {"type": "number"}
                }
            }
        }"#;

        let tool: McpTool = serde_json::from_str(json).unwrap();
        assert_eq!(tool.name, "calculate");
        assert_eq!(tool.description, "Does math");
    }

    #[test]
    fn test_mcp_manager_creation() {
        let mut mgr = McpManager::new();
        mgr.add_server("test", "echo", vec!["hello".to_string()]);
        assert!(mgr.servers.contains_key("test"));
    }

    #[test]
    fn test_mcp_content_types() {
        let text = McpContent::Text { text: "Hello".to_string() };
        let json = serde_json::to_string(&text).unwrap();
        assert!(json.contains("\"type\":\"text\""));
    }

    #[test]
    fn test_mcp_config_parsing() {
        let json = r#"{
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@anthropic/mcp-filesystem"]
                }
            }
        }"#;

        let config: McpConfig = serde_json::from_str(json).unwrap();
        assert!(config.mcp_servers.contains_key("filesystem"));
    }
}
