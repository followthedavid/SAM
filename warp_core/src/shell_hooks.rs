//! Shell Hooks Integration for warp_core
//!
//! Provides shell integration scripts for precmd/preexec hooks
//! that enable better block detection, command timing, and CWD tracking.

use serde::{Deserialize, Serialize};

/// Supported shell types
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum ShellType {
    Bash,
    Zsh,
    Fish,
    PowerShell,
}

impl ShellType {
    /// Detect shell type from shell path or name
    pub fn detect(shell: &str) -> Option<Self> {
        let shell_lower = shell.to_lowercase();
        if shell_lower.contains("bash") {
            Some(ShellType::Bash)
        } else if shell_lower.contains("zsh") {
            Some(ShellType::Zsh)
        } else if shell_lower.contains("fish") {
            Some(ShellType::Fish)
        } else if shell_lower.contains("pwsh") || shell_lower.contains("powershell") {
            Some(ShellType::PowerShell)
        } else {
            None
        }
    }
}

/// Shell hooks manager
pub struct ShellHooks {
    shell: ShellType,
}

impl ShellHooks {
    /// Create hooks for a specific shell
    pub fn new(shell: ShellType) -> Self {
        Self { shell }
    }

    /// Create hooks by detecting shell from path
    pub fn detect(shell_path: &str) -> Option<Self> {
        ShellType::detect(shell_path).map(|shell| Self { shell })
    }

    /// Get the shell initialization script
    pub fn get_init_script(&self) -> String {
        match self.shell {
            ShellType::Bash => self.bash_init(),
            ShellType::Zsh => self.zsh_init(),
            ShellType::Fish => self.fish_init(),
            ShellType::PowerShell => self.powershell_init(),
        }
    }

    /// Get the script to add to shell rc file
    pub fn get_rc_snippet(&self) -> String {
        match self.shell {
            ShellType::Bash => self.bash_rc(),
            ShellType::Zsh => self.zsh_rc(),
            ShellType::Fish => self.fish_rc(),
            ShellType::PowerShell => self.powershell_rc(),
        }
    }

    /// Get OSC 133 sequence for prompt start
    pub fn osc_prompt_start() -> &'static str {
        "\x1b]133;A\x07"
    }

    /// Get OSC 133 sequence for command start
    pub fn osc_command_start() -> &'static str {
        "\x1b]133;B\x07"
    }

    /// Get OSC 133 sequence for command end
    pub fn osc_command_end() -> &'static str {
        "\x1b]133;C\x07"
    }

    /// Get OSC 133 sequence for command finished with exit code
    pub fn osc_command_finished(exit_code: i32) -> String {
        format!("\x1b]133;D;{}\x07", exit_code)
    }

    /// Get OSC 7 sequence for CWD notification
    pub fn osc_cwd(cwd: &str) -> String {
        format!("\x1b]7;file://{}\x07", cwd)
    }

    /// Bash initialization script
    fn bash_init(&self) -> String {
        r#"
# SAM/Warp Terminal Integration for Bash

__sam_prompt_start() {
    printf '\033]133;A\007'
}

__sam_command_start() {
    printf '\033]133;B\007'
}

__sam_command_end() {
    local exit_code=$?
    printf '\033]133;D;%d\007' "$exit_code"
    return $exit_code
}

__sam_cwd_notify() {
    printf '\033]7;file://%s%s\007' "$HOSTNAME" "$PWD"
}

__sam_preexec() {
    printf '\033]133;C\007'
}

# Install hooks
if [[ -z "$__SAM_HOOKS_INSTALLED" ]]; then
    export __SAM_HOOKS_INSTALLED=1

    # Wrap PROMPT_COMMAND
    __sam_original_prompt_command="${PROMPT_COMMAND:-}"

    PROMPT_COMMAND='__sam_command_end; __sam_prompt_start; __sam_cwd_notify; '"${__sam_original_prompt_command:+$__sam_original_prompt_command; }"'__sam_command_start'

    # For bash 4.4+, use DEBUG trap for preexec
    if [[ "${BASH_VERSINFO[0]}" -ge 4 ]] && [[ "${BASH_VERSINFO[1]}" -ge 4 ]]; then
        trap '__sam_preexec' DEBUG
    fi
fi
"#.to_string()
    }

    /// Zsh initialization script
    fn zsh_init(&self) -> String {
        r#"
# SAM/Warp Terminal Integration for Zsh

__sam_prompt_start() {
    print -n '\033]133;A\007'
}

__sam_command_start() {
    print -n '\033]133;B\007'
}

__sam_command_end() {
    print -n "\033]133;D;$?\007"
}

__sam_cwd_notify() {
    print -n "\033]7;file://${HOST}${PWD}\007"
}

__sam_preexec() {
    print -n '\033]133;C\007'
}

# Install hooks
if [[ -z "$__SAM_HOOKS_INSTALLED" ]]; then
    export __SAM_HOOKS_INSTALLED=1

    # Add to hook arrays
    autoload -Uz add-zsh-hook

    add-zsh-hook precmd __sam_prompt_start
    add-zsh-hook precmd __sam_cwd_notify
    add-zsh-hook precmd __sam_command_end
    add-zsh-hook preexec __sam_preexec

    # Wrap prompt to include command start marker
    __sam_setup_prompt() {
        PS1="%{$(__sam_command_start)%}${PS1}"
    }
    add-zsh-hook precmd __sam_setup_prompt
fi
"#.to_string()
    }

    /// Fish initialization script
    fn fish_init(&self) -> String {
        r#"
# SAM/Warp Terminal Integration for Fish

function __sam_prompt_start --on-event fish_prompt
    printf '\033]133;A\007'
end

function __sam_command_start --on-event fish_prompt
    printf '\033]133;B\007'
end

function __sam_preexec --on-event fish_preexec
    printf '\033]133;C\007'
end

function __sam_postexec --on-event fish_postexec
    printf '\033]133;D;%d\007' $status
end

function __sam_cwd_notify --on-variable PWD
    printf '\033]7;file://%s%s\007' (hostname) $PWD
end

# Mark as installed
if not set -q __SAM_HOOKS_INSTALLED
    set -g __SAM_HOOKS_INSTALLED 1
end
"#.to_string()
    }

    /// PowerShell initialization script
    fn powershell_init(&self) -> String {
        r#"
# SAM/Warp Terminal Integration for PowerShell

function global:__sam_prompt_start {
    [Console]::Write("`e]133;A`a")
}

function global:__sam_command_start {
    [Console]::Write("`e]133;B`a")
}

function global:__sam_command_end {
    param($exitCode)
    [Console]::Write("`e]133;D;$exitCode`a")
}

function global:__sam_cwd_notify {
    $cwd = (Get-Location).Path
    [Console]::Write("`e]7;file://$env:COMPUTERNAME$cwd`a")
}

# Wrap the prompt function
if (-not $global:__SAM_HOOKS_INSTALLED) {
    $global:__SAM_HOOKS_INSTALLED = $true

    # Save original prompt
    $global:__sam_original_prompt = $function:prompt

    function global:prompt {
        $lastExitCode = $LASTEXITCODE
        __sam_command_end $lastExitCode
        __sam_prompt_start
        __sam_cwd_notify
        $result = & $global:__sam_original_prompt
        __sam_command_start
        return $result
    }

    # Set up preexec via PSReadLine if available
    if (Get-Module -ListAvailable -Name PSReadLine) {
        Set-PSReadLineKeyHandler -Chord Enter -ScriptBlock {
            [Console]::Write("`e]133;C`a")
            [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
        }
    }
}
"#.to_string()
    }

    /// Bash rc snippet (to add to .bashrc)
    fn bash_rc(&self) -> String {
        r#"
# SAM Terminal Integration
if [[ "$TERM_PROGRAM" == "SAM" ]] || [[ -n "$SAM_TERMINAL" ]]; then
    source "$HOME/.sam/shell/bash_init.sh" 2>/dev/null || true
fi
"#.to_string()
    }

    /// Zsh rc snippet (to add to .zshrc)
    fn zsh_rc(&self) -> String {
        r#"
# SAM Terminal Integration
if [[ "$TERM_PROGRAM" == "SAM" ]] || [[ -n "$SAM_TERMINAL" ]]; then
    source "$HOME/.sam/shell/zsh_init.zsh" 2>/dev/null || true
fi
"#.to_string()
    }

    /// Fish rc snippet (to add to config.fish)
    fn fish_rc(&self) -> String {
        r#"
# SAM Terminal Integration
if test "$TERM_PROGRAM" = "SAM"; or test -n "$SAM_TERMINAL"
    source "$HOME/.sam/shell/fish_init.fish" 2>/dev/null; or true
end
"#.to_string()
    }

    /// PowerShell rc snippet (to add to profile)
    fn powershell_rc(&self) -> String {
        r#"
# SAM Terminal Integration
if ($env:TERM_PROGRAM -eq "SAM" -or $env:SAM_TERMINAL) {
    . "$HOME\.sam\shell\pwsh_init.ps1" 2>$null
}
"#.to_string()
    }

    /// Install shell hooks to user's home directory
    pub fn install(&self) -> Result<(), std::io::Error> {
        use std::fs;
        use std::path::PathBuf;

        let home = std::env::var("HOME").unwrap_or_else(|_| ".".to_string());
        let sam_dir = PathBuf::from(&home).join(".sam").join("shell");
        fs::create_dir_all(&sam_dir)?;

        let (filename, content) = match self.shell {
            ShellType::Bash => ("bash_init.sh", self.bash_init()),
            ShellType::Zsh => ("zsh_init.zsh", self.zsh_init()),
            ShellType::Fish => ("fish_init.fish", self.fish_init()),
            ShellType::PowerShell => ("pwsh_init.ps1", self.powershell_init()),
        };

        fs::write(sam_dir.join(filename), content)?;
        Ok(())
    }

    /// Get shell type
    pub fn shell_type(&self) -> &ShellType {
        &self.shell
    }
}

/// Command timing information
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CommandTiming {
    pub command: String,
    pub start_time: chrono::DateTime<chrono::Utc>,
    pub end_time: Option<chrono::DateTime<chrono::Utc>>,
    pub exit_code: Option<i32>,
    pub cwd: String,
}

impl CommandTiming {
    pub fn new(command: String, cwd: String) -> Self {
        Self {
            command,
            start_time: chrono::Utc::now(),
            end_time: None,
            exit_code: None,
            cwd,
        }
    }

    pub fn finish(&mut self, exit_code: i32) {
        self.end_time = Some(chrono::Utc::now());
        self.exit_code = Some(exit_code);
    }

    pub fn duration(&self) -> Option<chrono::Duration> {
        self.end_time.map(|end| end - self.start_time)
    }

    pub fn duration_ms(&self) -> Option<i64> {
        self.duration().map(|d| d.num_milliseconds())
    }
}

/// Parse OSC sequences from PTY output to extract hook data
pub fn parse_osc_hooks(data: &[u8]) -> Vec<HookEvent> {
    let mut events = vec![];
    let text = String::from_utf8_lossy(data);

    // Parse OSC 133 sequences
    let osc_re = regex::Regex::new(r"\x1b\]133;([A-D])(?:;(\d+))?\x07").unwrap();
    for caps in osc_re.captures_iter(&text) {
        let event_type = caps.get(1).map(|m| m.as_str()).unwrap_or("");
        let arg = caps.get(2).map(|m| m.as_str().parse::<i32>().ok()).flatten();

        let event = match event_type {
            "A" => HookEvent::PromptStart,
            "B" => HookEvent::CommandStart,
            "C" => HookEvent::CommandEnd,
            "D" => HookEvent::CommandFinished { exit_code: arg },
            _ => continue,
        };
        events.push(event);
    }

    // Parse OSC 7 (CWD) sequences
    let cwd_re = regex::Regex::new(r"\x1b\]7;file://[^/]*(/.+?)\x07").unwrap();
    for caps in cwd_re.captures_iter(&text) {
        if let Some(path) = caps.get(1) {
            events.push(HookEvent::CwdChanged {
                path: path.as_str().to_string(),
            });
        }
    }

    events
}

/// Hook events parsed from PTY output
#[derive(Clone, Debug, PartialEq)]
pub enum HookEvent {
    PromptStart,
    CommandStart,
    CommandEnd,
    CommandFinished { exit_code: Option<i32> },
    CwdChanged { path: String },
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_shell_detection() {
        assert_eq!(ShellType::detect("/bin/bash"), Some(ShellType::Bash));
        assert_eq!(ShellType::detect("/usr/bin/zsh"), Some(ShellType::Zsh));
        assert_eq!(ShellType::detect("/usr/bin/fish"), Some(ShellType::Fish));
        assert_eq!(ShellType::detect("pwsh"), Some(ShellType::PowerShell));
        assert_eq!(ShellType::detect("/bin/sh"), None);
    }

    #[test]
    fn test_osc_sequences() {
        assert_eq!(ShellHooks::osc_prompt_start(), "\x1b]133;A\x07");
        assert_eq!(ShellHooks::osc_command_finished(0), "\x1b]133;D;0\x07");
        assert_eq!(ShellHooks::osc_command_finished(1), "\x1b]133;D;1\x07");
    }

    #[test]
    fn test_parse_hooks() {
        let data = b"\x1b]133;A\x07prompt$ \x1b]133;B\x07ls\x1b]133;C\x07file1 file2\x1b]133;D;0\x07";
        let events = parse_osc_hooks(data);

        assert_eq!(events.len(), 4);
        assert_eq!(events[0], HookEvent::PromptStart);
        assert_eq!(events[1], HookEvent::CommandStart);
        assert_eq!(events[2], HookEvent::CommandEnd);
        assert_eq!(events[3], HookEvent::CommandFinished { exit_code: Some(0) });
    }

    #[test]
    fn test_parse_cwd_hook() {
        let data = b"\x1b]7;file://hostname/home/user/projects\x07";
        let events = parse_osc_hooks(data);

        assert_eq!(events.len(), 1);
        assert_eq!(
            events[0],
            HookEvent::CwdChanged {
                path: "/home/user/projects".to_string()
            }
        );
    }

    #[test]
    fn test_command_timing() {
        let mut timing = CommandTiming::new("ls -la".to_string(), "/home/user".to_string());
        assert!(timing.end_time.is_none());
        assert!(timing.exit_code.is_none());

        std::thread::sleep(std::time::Duration::from_millis(10));
        timing.finish(0);

        assert!(timing.end_time.is_some());
        assert_eq!(timing.exit_code, Some(0));
        assert!(timing.duration_ms().unwrap() >= 10);
    }
}
