//! Launch Configurations for warp_core
//!
//! Manage terminal launch configurations with custom shell, environment,
//! working directory, and startup commands. Similar to Warp's launch configs
//! and VS Code's launch.json.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;

/// A terminal launch configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LaunchConfig {
    /// Unique identifier
    pub id: String,
    /// Display name
    pub name: String,
    /// Description (optional)
    pub description: Option<String>,
    /// Icon name or emoji
    pub icon: Option<String>,
    /// Shell to use (optional, uses default if not specified)
    pub shell: Option<ShellConfig>,
    /// Working directory
    pub cwd: Option<PathBuf>,
    /// Environment variables to set
    pub env: HashMap<String, String>,
    /// Environment variables to unset
    pub env_remove: Vec<String>,
    /// Commands to run on startup
    pub startup_commands: Vec<String>,
    /// Whether to run startup commands silently
    pub silent_startup: bool,
    /// SSH connection settings (for remote terminals)
    pub ssh: Option<SshConfig>,
    /// Docker container settings
    pub docker: Option<DockerConfig>,
    /// Kubernetes pod settings
    pub kubernetes: Option<KubernetesConfig>,
    /// Custom keybindings for this profile
    pub keybindings: HashMap<String, String>,
    /// Color scheme override
    pub color_scheme: Option<String>,
    /// Font override
    pub font: Option<FontConfig>,
    /// Tags for organization
    pub tags: Vec<String>,
    /// Whether this is a favorite/pinned config
    pub favorite: bool,
    /// Last used timestamp
    pub last_used: Option<chrono::DateTime<chrono::Utc>>,
    /// Usage count
    pub use_count: u64,
}

/// Shell configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ShellConfig {
    /// Path to shell executable
    pub path: PathBuf,
    /// Arguments to pass to shell
    pub args: Vec<String>,
    /// Login shell flag
    pub login: bool,
}

/// SSH connection configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SshConfig {
    /// Remote host
    pub host: String,
    /// SSH port (default 22)
    pub port: u16,
    /// Username
    pub user: Option<String>,
    /// Path to private key
    pub identity_file: Option<PathBuf>,
    /// SSH config file to use
    pub config_file: Option<PathBuf>,
    /// Additional SSH options
    pub options: HashMap<String, String>,
    /// Command to run after connecting
    pub remote_command: Option<String>,
    /// Port forwarding rules
    pub port_forwards: Vec<PortForward>,
    /// Keep alive interval in seconds
    pub keep_alive: Option<u32>,
}

/// Port forwarding configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PortForward {
    /// Local port
    pub local_port: u16,
    /// Remote host (or localhost)
    pub remote_host: String,
    /// Remote port
    pub remote_port: u16,
    /// Direction: local or remote
    pub direction: PortForwardDirection,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum PortForwardDirection {
    /// Forward local port to remote
    Local,
    /// Forward remote port to local
    Remote,
    /// Dynamic SOCKS proxy
    Dynamic,
}

/// Docker container configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DockerConfig {
    /// Container name or ID (for exec)
    pub container: Option<String>,
    /// Image name (for run)
    pub image: Option<String>,
    /// Docker command (run, exec, compose)
    pub command: DockerCommand,
    /// Compose file path
    pub compose_file: Option<PathBuf>,
    /// Service name (for compose)
    pub service: Option<String>,
    /// Additional docker args
    pub args: Vec<String>,
    /// Shell to use inside container
    pub shell: Option<String>,
    /// Mount volumes
    pub volumes: Vec<VolumeMount>,
    /// Port mappings
    pub ports: Vec<PortMapping>,
    /// Environment variables for container
    pub env: HashMap<String, String>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum DockerCommand {
    Run,
    Exec,
    Compose,
}

/// Volume mount configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct VolumeMount {
    pub source: PathBuf,
    pub target: String,
    pub read_only: bool,
}

/// Port mapping configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PortMapping {
    pub host_port: u16,
    pub container_port: u16,
    pub protocol: String, // tcp or udp
}

/// Kubernetes configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct KubernetesConfig {
    /// Kubernetes context
    pub context: Option<String>,
    /// Namespace
    pub namespace: Option<String>,
    /// Pod name or selector
    pub pod: String,
    /// Container name (if multiple)
    pub container: Option<String>,
    /// Command type (exec, logs, port-forward)
    pub command: K8sCommand,
    /// Shell to use for exec
    pub shell: Option<String>,
    /// Port forwards for port-forward command
    pub ports: Vec<u16>,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum K8sCommand {
    Exec,
    Logs,
    PortForward,
}

/// Font configuration
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FontConfig {
    pub family: String,
    pub size: f32,
    pub line_height: Option<f32>,
    pub ligatures: bool,
}

/// Launch configuration manager
pub struct LaunchConfigManager {
    /// All configurations
    configs: HashMap<String, LaunchConfig>,
    /// Storage path
    config_path: PathBuf,
    /// Default config ID
    default_config: Option<String>,
}

impl LaunchConfigManager {
    /// Create a new manager with storage path
    pub fn new(config_path: impl Into<PathBuf>) -> Self {
        let path = config_path.into();
        let mut manager = Self {
            configs: HashMap::new(),
            config_path: path.clone(),
            default_config: None,
        };

        // Load existing configs
        if let Err(e) = manager.load() {
            eprintln!("Failed to load launch configs: {}", e);
        }

        // Add built-in configs if empty
        if manager.configs.is_empty() {
            manager.add_builtin_configs();
        }

        manager
    }

    /// Add a new configuration
    pub fn add(&mut self, config: LaunchConfig) -> Result<(), ConfigError> {
        if self.configs.contains_key(&config.id) {
            return Err(ConfigError::AlreadyExists(config.id));
        }
        self.configs.insert(config.id.clone(), config);
        self.save()?;
        Ok(())
    }

    /// Update an existing configuration
    pub fn update(&mut self, config: LaunchConfig) -> Result<(), ConfigError> {
        if !self.configs.contains_key(&config.id) {
            return Err(ConfigError::NotFound(config.id));
        }
        self.configs.insert(config.id.clone(), config);
        self.save()?;
        Ok(())
    }

    /// Remove a configuration
    pub fn remove(&mut self, id: &str) -> Result<LaunchConfig, ConfigError> {
        let config = self.configs.remove(id)
            .ok_or_else(|| ConfigError::NotFound(id.to_string()))?;
        self.save()?;
        Ok(config)
    }

    /// Get a configuration by ID
    pub fn get(&self, id: &str) -> Option<&LaunchConfig> {
        self.configs.get(id)
    }

    /// Get all configurations
    pub fn list(&self) -> Vec<&LaunchConfig> {
        self.configs.values().collect()
    }

    /// Get configurations by tag
    pub fn get_by_tag(&self, tag: &str) -> Vec<&LaunchConfig> {
        self.configs.values()
            .filter(|c| c.tags.contains(&tag.to_string()))
            .collect()
    }

    /// Get favorite configurations
    pub fn get_favorites(&self) -> Vec<&LaunchConfig> {
        self.configs.values()
            .filter(|c| c.favorite)
            .collect()
    }

    /// Get recently used configurations
    pub fn get_recent(&self, limit: usize) -> Vec<&LaunchConfig> {
        let mut configs: Vec<_> = self.configs.values()
            .filter(|c| c.last_used.is_some())
            .collect();

        configs.sort_by(|a, b| b.last_used.cmp(&a.last_used));
        configs.truncate(limit);
        configs
    }

    /// Set the default configuration
    pub fn set_default(&mut self, id: &str) -> Result<(), ConfigError> {
        if !self.configs.contains_key(id) {
            return Err(ConfigError::NotFound(id.to_string()));
        }
        self.default_config = Some(id.to_string());
        self.save()?;
        Ok(())
    }

    /// Get the default configuration
    pub fn get_default(&self) -> Option<&LaunchConfig> {
        self.default_config.as_ref().and_then(|id| self.configs.get(id))
    }

    /// Record usage of a configuration
    pub fn record_usage(&mut self, id: &str) -> Result<(), ConfigError> {
        let config = self.configs.get_mut(id)
            .ok_or_else(|| ConfigError::NotFound(id.to_string()))?;
        config.last_used = Some(chrono::Utc::now());
        config.use_count += 1;
        self.save()?;
        Ok(())
    }

    /// Build the command line for a configuration
    pub fn build_command(&self, config: &LaunchConfig) -> Vec<String> {
        let mut cmd = Vec::new();

        // Handle SSH
        if let Some(ref ssh) = config.ssh {
            cmd.push("ssh".to_string());

            if ssh.port != 22 {
                cmd.push("-p".to_string());
                cmd.push(ssh.port.to_string());
            }

            if let Some(ref identity) = ssh.identity_file {
                cmd.push("-i".to_string());
                cmd.push(identity.display().to_string());
            }

            for forward in &ssh.port_forwards {
                match forward.direction {
                    PortForwardDirection::Local => {
                        cmd.push("-L".to_string());
                        cmd.push(format!("{}:{}:{}",
                            forward.local_port,
                            forward.remote_host,
                            forward.remote_port
                        ));
                    }
                    PortForwardDirection::Remote => {
                        cmd.push("-R".to_string());
                        cmd.push(format!("{}:{}:{}",
                            forward.remote_port,
                            forward.remote_host,
                            forward.local_port
                        ));
                    }
                    PortForwardDirection::Dynamic => {
                        cmd.push("-D".to_string());
                        cmd.push(forward.local_port.to_string());
                    }
                }
            }

            for (key, value) in &ssh.options {
                cmd.push("-o".to_string());
                cmd.push(format!("{}={}", key, value));
            }

            let host = if let Some(ref user) = ssh.user {
                format!("{}@{}", user, ssh.host)
            } else {
                ssh.host.clone()
            };
            cmd.push(host);

            if let Some(ref remote_cmd) = ssh.remote_command {
                cmd.push(remote_cmd.clone());
            }

            return cmd;
        }

        // Handle Docker
        if let Some(ref docker) = config.docker {
            cmd.push("docker".to_string());

            match docker.command {
                DockerCommand::Run => {
                    cmd.push("run".to_string());
                    cmd.push("-it".to_string());
                    cmd.push("--rm".to_string());

                    for (key, value) in &docker.env {
                        cmd.push("-e".to_string());
                        cmd.push(format!("{}={}", key, value));
                    }

                    for vol in &docker.volumes {
                        cmd.push("-v".to_string());
                        let mount = if vol.read_only {
                            format!("{}:{}:ro", vol.source.display(), vol.target)
                        } else {
                            format!("{}:{}", vol.source.display(), vol.target)
                        };
                        cmd.push(mount);
                    }

                    for port in &docker.ports {
                        cmd.push("-p".to_string());
                        cmd.push(format!("{}:{}", port.host_port, port.container_port));
                    }

                    cmd.extend(docker.args.clone());

                    if let Some(ref image) = docker.image {
                        cmd.push(image.clone());
                    }

                    if let Some(ref shell) = docker.shell {
                        cmd.push(shell.clone());
                    }
                }
                DockerCommand::Exec => {
                    cmd.push("exec".to_string());
                    cmd.push("-it".to_string());
                    cmd.extend(docker.args.clone());

                    if let Some(ref container) = docker.container {
                        cmd.push(container.clone());
                    }

                    cmd.push(docker.shell.clone().unwrap_or_else(|| "/bin/sh".to_string()));
                }
                DockerCommand::Compose => {
                    cmd.clear();
                    cmd.push("docker-compose".to_string());

                    if let Some(ref file) = docker.compose_file {
                        cmd.push("-f".to_string());
                        cmd.push(file.display().to_string());
                    }

                    cmd.push("exec".to_string());

                    if let Some(ref service) = docker.service {
                        cmd.push(service.clone());
                    }

                    cmd.push(docker.shell.clone().unwrap_or_else(|| "/bin/sh".to_string()));
                }
            }

            return cmd;
        }

        // Handle Kubernetes
        if let Some(ref k8s) = config.kubernetes {
            cmd.push("kubectl".to_string());

            if let Some(ref context) = k8s.context {
                cmd.push("--context".to_string());
                cmd.push(context.clone());
            }

            if let Some(ref ns) = k8s.namespace {
                cmd.push("-n".to_string());
                cmd.push(ns.clone());
            }

            match k8s.command {
                K8sCommand::Exec => {
                    cmd.push("exec".to_string());
                    cmd.push("-it".to_string());
                    cmd.push(k8s.pod.clone());

                    if let Some(ref container) = k8s.container {
                        cmd.push("-c".to_string());
                        cmd.push(container.clone());
                    }

                    cmd.push("--".to_string());
                    cmd.push(k8s.shell.clone().unwrap_or_else(|| "/bin/sh".to_string()));
                }
                K8sCommand::Logs => {
                    cmd.push("logs".to_string());
                    cmd.push("-f".to_string());
                    cmd.push(k8s.pod.clone());

                    if let Some(ref container) = k8s.container {
                        cmd.push("-c".to_string());
                        cmd.push(container.clone());
                    }
                }
                K8sCommand::PortForward => {
                    cmd.push("port-forward".to_string());
                    cmd.push(k8s.pod.clone());

                    for port in &k8s.ports {
                        cmd.push(port.to_string());
                    }
                }
            }

            return cmd;
        }

        // Default: local shell
        if let Some(ref shell) = config.shell {
            cmd.push(shell.path.display().to_string());
            if shell.login {
                cmd.push("-l".to_string());
            }
            cmd.extend(shell.args.clone());
        }

        cmd
    }

    /// Build environment variables for a configuration
    pub fn build_env(&self, config: &LaunchConfig) -> HashMap<String, String> {
        let mut env: HashMap<String, String> = std::env::vars().collect();

        // Remove specified vars
        for key in &config.env_remove {
            env.remove(key);
        }

        // Add/override with config vars
        for (key, value) in &config.env {
            env.insert(key.clone(), value.clone());
        }

        env
    }

    // Private methods

    fn load(&mut self) -> Result<(), ConfigError> {
        if !self.config_path.exists() {
            return Ok(());
        }

        let content = std::fs::read_to_string(&self.config_path)
            .map_err(|e| ConfigError::IoError(e.to_string()))?;

        let data: SavedData = serde_json::from_str(&content)
            .map_err(|e| ConfigError::ParseError(e.to_string()))?;

        self.configs = data.configs.into_iter()
            .map(|c| (c.id.clone(), c))
            .collect();
        self.default_config = data.default_config;

        Ok(())
    }

    fn save(&self) -> Result<(), ConfigError> {
        let data = SavedData {
            configs: self.configs.values().cloned().collect(),
            default_config: self.default_config.clone(),
        };

        // Ensure parent directory exists
        if let Some(parent) = self.config_path.parent() {
            std::fs::create_dir_all(parent)
                .map_err(|e| ConfigError::IoError(e.to_string()))?;
        }

        let content = serde_json::to_string_pretty(&data)
            .map_err(|e| ConfigError::ParseError(e.to_string()))?;

        std::fs::write(&self.config_path, content)
            .map_err(|e| ConfigError::IoError(e.to_string()))?;

        Ok(())
    }

    fn add_builtin_configs(&mut self) {
        // Default local shell
        let local = LaunchConfig {
            id: "local".to_string(),
            name: "Local Shell".to_string(),
            description: Some("Default local terminal".to_string()),
            icon: Some("terminal".to_string()),
            shell: None, // Use system default
            cwd: None,
            env: HashMap::new(),
            env_remove: vec![],
            startup_commands: vec![],
            silent_startup: false,
            ssh: None,
            docker: None,
            kubernetes: None,
            keybindings: HashMap::new(),
            color_scheme: None,
            font: None,
            tags: vec!["local".to_string()],
            favorite: true,
            last_used: None,
            use_count: 0,
        };

        self.configs.insert(local.id.clone(), local);
        self.default_config = Some("local".to_string());
    }
}

/// Saved data format
#[derive(Serialize, Deserialize)]
struct SavedData {
    configs: Vec<LaunchConfig>,
    default_config: Option<String>,
}

/// Configuration errors
#[derive(Debug)]
pub enum ConfigError {
    NotFound(String),
    AlreadyExists(String),
    IoError(String),
    ParseError(String),
}

impl std::fmt::Display for ConfigError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            ConfigError::NotFound(id) => write!(f, "Configuration not found: {}", id),
            ConfigError::AlreadyExists(id) => write!(f, "Configuration already exists: {}", id),
            ConfigError::IoError(msg) => write!(f, "IO error: {}", msg),
            ConfigError::ParseError(msg) => write!(f, "Parse error: {}", msg),
        }
    }
}

impl std::error::Error for ConfigError {}

/// Builder for creating launch configs
pub struct LaunchConfigBuilder {
    config: LaunchConfig,
}

impl LaunchConfigBuilder {
    pub fn new(id: &str, name: &str) -> Self {
        Self {
            config: LaunchConfig {
                id: id.to_string(),
                name: name.to_string(),
                description: None,
                icon: None,
                shell: None,
                cwd: None,
                env: HashMap::new(),
                env_remove: vec![],
                startup_commands: vec![],
                silent_startup: false,
                ssh: None,
                docker: None,
                kubernetes: None,
                keybindings: HashMap::new(),
                color_scheme: None,
                font: None,
                tags: vec![],
                favorite: false,
                last_used: None,
                use_count: 0,
            },
        }
    }

    pub fn description(mut self, desc: &str) -> Self {
        self.config.description = Some(desc.to_string());
        self
    }

    pub fn icon(mut self, icon: &str) -> Self {
        self.config.icon = Some(icon.to_string());
        self
    }

    pub fn shell(mut self, path: impl Into<PathBuf>, args: Vec<String>, login: bool) -> Self {
        self.config.shell = Some(ShellConfig {
            path: path.into(),
            args,
            login,
        });
        self
    }

    pub fn cwd(mut self, path: impl Into<PathBuf>) -> Self {
        self.config.cwd = Some(path.into());
        self
    }

    pub fn env(mut self, key: &str, value: &str) -> Self {
        self.config.env.insert(key.to_string(), value.to_string());
        self
    }

    pub fn startup_command(mut self, cmd: &str) -> Self {
        self.config.startup_commands.push(cmd.to_string());
        self
    }

    pub fn ssh(mut self, host: &str, user: Option<&str>) -> Self {
        self.config.ssh = Some(SshConfig {
            host: host.to_string(),
            port: 22,
            user: user.map(String::from),
            identity_file: None,
            config_file: None,
            options: HashMap::new(),
            remote_command: None,
            port_forwards: vec![],
            keep_alive: None,
        });
        self
    }

    pub fn docker_exec(mut self, container: &str) -> Self {
        self.config.docker = Some(DockerConfig {
            container: Some(container.to_string()),
            image: None,
            command: DockerCommand::Exec,
            compose_file: None,
            service: None,
            args: vec![],
            shell: Some("/bin/sh".to_string()),
            volumes: vec![],
            ports: vec![],
            env: HashMap::new(),
        });
        self
    }

    pub fn docker_run(mut self, image: &str) -> Self {
        self.config.docker = Some(DockerConfig {
            container: None,
            image: Some(image.to_string()),
            command: DockerCommand::Run,
            compose_file: None,
            service: None,
            args: vec![],
            shell: None,
            volumes: vec![],
            ports: vec![],
            env: HashMap::new(),
        });
        self
    }

    pub fn kubernetes(mut self, pod: &str, namespace: Option<&str>) -> Self {
        self.config.kubernetes = Some(KubernetesConfig {
            context: None,
            namespace: namespace.map(String::from),
            pod: pod.to_string(),
            container: None,
            command: K8sCommand::Exec,
            shell: Some("/bin/sh".to_string()),
            ports: vec![],
        });
        self
    }

    pub fn tag(mut self, tag: &str) -> Self {
        self.config.tags.push(tag.to_string());
        self
    }

    pub fn favorite(mut self) -> Self {
        self.config.favorite = true;
        self
    }

    pub fn build(self) -> LaunchConfig {
        self.config
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_create_manager() {
        let dir = tempdir().unwrap();
        let manager = LaunchConfigManager::new(dir.path().join("configs.json"));

        assert!(manager.get("local").is_some());
    }

    #[test]
    fn test_add_config() {
        let dir = tempdir().unwrap();
        let mut manager = LaunchConfigManager::new(dir.path().join("configs.json"));

        let config = LaunchConfigBuilder::new("dev", "Development")
            .description("Dev environment")
            .cwd("/home/user/projects")
            .env("NODE_ENV", "development")
            .startup_command("nvm use 18")
            .tag("development")
            .build();

        manager.add(config).unwrap();
        assert!(manager.get("dev").is_some());
    }

    #[test]
    fn test_ssh_command() {
        let dir = tempdir().unwrap();
        let manager = LaunchConfigManager::new(dir.path().join("configs.json"));

        let config = LaunchConfigBuilder::new("server", "Remote Server")
            .ssh("example.com", Some("admin"))
            .build();

        let cmd = manager.build_command(&config);
        assert!(cmd.contains(&"ssh".to_string()));
        assert!(cmd.contains(&"admin@example.com".to_string()));
    }

    #[test]
    fn test_docker_command() {
        let dir = tempdir().unwrap();
        let manager = LaunchConfigManager::new(dir.path().join("configs.json"));

        let config = LaunchConfigBuilder::new("nginx", "Nginx Container")
            .docker_exec("nginx-container")
            .build();

        let cmd = manager.build_command(&config);
        assert!(cmd.contains(&"docker".to_string()));
        assert!(cmd.contains(&"exec".to_string()));
        assert!(cmd.contains(&"nginx-container".to_string()));
    }

    #[test]
    fn test_favorites() {
        let dir = tempdir().unwrap();
        let mut manager = LaunchConfigManager::new(dir.path().join("configs.json"));

        let config = LaunchConfigBuilder::new("fav", "Favorite Config")
            .favorite()
            .build();

        manager.add(config).unwrap();

        let favorites = manager.get_favorites();
        assert!(favorites.iter().any(|c| c.id == "fav"));
    }

    #[test]
    fn test_record_usage() {
        let dir = tempdir().unwrap();
        let mut manager = LaunchConfigManager::new(dir.path().join("configs.json"));

        manager.record_usage("local").unwrap();

        let config = manager.get("local").unwrap();
        assert_eq!(config.use_count, 1);
        assert!(config.last_used.is_some());
    }
}
