/**
 * OSC 133 Parser - Block boundary detection for PTY streams
 * 
 * Implements parsing of OSC 133 escape sequences used by modern shells
 * to mark block boundaries (prompt start, command start, command end).
 * 
 * Reference: https://gitlab.freedesktop.org/Per_Bothner/specifications/-/blob/master/proposals/semantic-prompts.md
 */

use serde::{Deserialize, Serialize};
use std::fmt;

/// OSC 133 sequence types
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum OSC133Type {
    /// OSC 133 ; A - Mark prompt start
    PromptStart,
    /// OSC 133 ; B - Mark command start (right after prompt)
    CommandStart,
    /// OSC 133 ; C - Mark command end (before execution)
    CommandEnd,
    /// OSC 133 ; D [; <exit_code>] - Mark command execution finished
    CommandFinished { exit_code: Option<i32> },
    /// Unknown OSC 133 sequence
    Unknown(String),
}

/// Block boundary event
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BlockEvent {
    pub event_type: String,
    pub osc_type: Option<OSC133Type>,
    pub timestamp: String,
    pub data: Option<String>,
}

/// OSC 133 Parser
pub struct OSC133Parser {
    buffer: Vec<u8>,
    last_event: Option<BlockEvent>,
}

impl OSC133Parser {
    pub fn new() -> Self {
        Self {
            buffer: Vec::new(),
            last_event: None,
        }
    }

    /// Parse PTY data for OSC 133 sequences
    pub fn parse(&mut self, data: &[u8]) -> Vec<BlockEvent> {
        let mut events = Vec::new();
        
        self.buffer.extend_from_slice(data);
        
        // Look for OSC sequences: ESC ] 133 ; <type> [; <data>] ST
        // Where ST is either BEL (0x07) or ESC \ (0x1b 0x5c)
        let mut i = 0;
        while i < self.buffer.len() {
            // Check for ESC ] (OSC start)
            if i + 1 < self.buffer.len() 
                && self.buffer[i] == 0x1b 
                && self.buffer[i + 1] == b']' 
            {
                // Look for OSC 133
                if i + 5 < self.buffer.len() 
                    && &self.buffer[i+2..i+5] == b"133"
                    && self.buffer[i+5] == b';'
                {
                    // Find terminator (BEL or ESC \)
                    if let Some(end_pos) = self.find_osc_terminator(i + 6) {
                        let sequence = self.buffer[i+6..end_pos].to_vec();
                        if let Some(event) = self.parse_osc_133(&sequence) {
                            events.push(event);
                        }
                        i = end_pos + 1;
                        continue;
                    }
                }
            }
            i += 1;
        }
        
        // Keep last 1KB in buffer (for incomplete sequences)
        if self.buffer.len() > 1024 {
            self.buffer.drain(0..self.buffer.len() - 1024);
        }
        
        events
    }

    /// Find OSC terminator (BEL or ESC \)
    fn find_osc_terminator(&self, start: usize) -> Option<usize> {
        for i in start..self.buffer.len() {
            // BEL (0x07)
            if self.buffer[i] == 0x07 {
                return Some(i);
            }
            // ESC \ (0x1b 0x5c)
            if i + 1 < self.buffer.len() 
                && self.buffer[i] == 0x1b 
                && self.buffer[i + 1] == 0x5c 
            {
                return Some(i);
            }
        }
        None
    }

    /// Parse OSC 133 sequence data
    fn parse_osc_133(&mut self, data: &[u8]) -> Option<BlockEvent> {
        let s = String::from_utf8_lossy(data);
        let parts: Vec<&str> = s.split(';').collect();
        
        if parts.is_empty() {
            return None;
        }

        let osc_type = match parts[0].trim() {
            "A" => OSC133Type::PromptStart,
            "B" => OSC133Type::CommandStart,
            "C" => OSC133Type::CommandEnd,
            "D" => {
                let exit_code = if parts.len() > 1 {
                    parts[1].trim().parse::<i32>().ok()
                } else {
                    None
                };
                OSC133Type::CommandFinished { exit_code }
            }
            other => OSC133Type::Unknown(other.to_string()),
        };

        let event = BlockEvent {
            event_type: match osc_type {
                OSC133Type::PromptStart => "prompt_start".to_string(),
                OSC133Type::CommandStart => "command_start".to_string(),
                OSC133Type::CommandEnd => "command_end".to_string(),
                OSC133Type::CommandFinished { .. } => "command_finished".to_string(),
                OSC133Type::Unknown(_) => "unknown".to_string(),
            },
            osc_type: Some(osc_type),
            timestamp: chrono::Utc::now().to_rfc3339(),
            data: if parts.len() > 1 {
                Some(parts[1..].join(";"))
            } else {
                None
            },
        };

        self.last_event = Some(event.clone());
        Some(event)
    }

    /// Feed a single line and parse for OSC 133 sequences
    pub fn feed_line(&mut self, line: &str) -> Option<OSC133Type> {
        let events = self.parse(line.as_bytes());
        if let Some(event) = events.last() {
            event.osc_type.clone()
        } else {
            None
        }
    }
    
    /// Get the last parsed event
    pub fn get_last_event(&self) -> Option<&BlockEvent> {
        self.last_event.as_ref()
    }

    /// Fallback heuristic for block boundaries (when OSC 133 not present)
    pub fn detect_boundaries_heuristic(data: &str) -> Vec<BlockEvent> {
        let mut events = Vec::new();
        let lines: Vec<&str> = data.lines().collect();

        for line in lines {
            let trimmed = line.trim();
            
            // Detect prompt patterns
            if trimmed.ends_with('$') 
                || trimmed.ends_with('#') 
                || trimmed.ends_with('>') 
                || trimmed.contains("@") && trimmed.ends_with(|c| c == '$' || c == '#')
            {
                events.push(BlockEvent {
                    event_type: "prompt_detected".to_string(),
                    osc_type: None,
                    timestamp: chrono::Utc::now().to_rfc3339(),
                    data: Some(line.to_string()),
                });
            }
            
            // Detect command execution start (non-empty line after prompt)
            if !trimmed.is_empty() 
                && !trimmed.starts_with('#') 
                && !events.is_empty() 
            {
                if let Some(last) = events.last() {
                    if last.event_type == "prompt_detected" {
                        events.push(BlockEvent {
                            event_type: "command_detected".to_string(),
                            osc_type: None,
                            timestamp: chrono::Utc::now().to_rfc3339(),
                            data: Some(trimmed.to_string()),
                        });
                    }
                }
            }
        }

        events
    }
}

impl Default for OSC133Parser {
    fn default() -> Self {
        Self::new()
    }
}

impl fmt::Display for OSC133Type {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            OSC133Type::PromptStart => write!(f, "PromptStart"),
            OSC133Type::CommandStart => write!(f, "CommandStart"),
            OSC133Type::CommandEnd => write!(f, "CommandEnd"),
            OSC133Type::CommandFinished { exit_code } => {
                write!(f, "CommandFinished(exit_code: {:?})", exit_code)
            }
            OSC133Type::Unknown(s) => write!(f, "Unknown({})", s),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_parse_osc_133_prompt_start() {
        let mut parser = OSC133Parser::new();
        let data = b"\x1b]133;A\x07";
        let events = parser.parse(data);
        
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].event_type, "prompt_start");
    }

    #[test]
    fn test_parse_osc_133_command_finished() {
        let mut parser = OSC133Parser::new();
        let data = b"\x1b]133;D;0\x07";
        let events = parser.parse(data);
        
        assert_eq!(events.len(), 1);
        assert_eq!(events[0].event_type, "command_finished");
        if let Some(OSC133Type::CommandFinished { exit_code }) = &events[0].osc_type {
            assert_eq!(*exit_code, Some(0));
        }
    }

    #[test]
    fn test_heuristic_prompt_detection() {
        let data = "user@host:/path/to/dir$";
        let events = OSC133Parser::detect_boundaries_heuristic(data);
        
        assert!(!events.is_empty());
        assert_eq!(events[0].event_type, "prompt_detected");
    }
}
