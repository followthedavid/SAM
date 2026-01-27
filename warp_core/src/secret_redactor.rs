//! Secret Redaction Module for warp_core
//!
//! Automatically detects and masks sensitive data like API keys, passwords,
//! and tokens in terminal output before display, logging, or AI processing.

use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// A pattern for detecting secrets
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SecretPattern {
    pub name: String,
    pub pattern: String,
    pub enabled: bool,
    pub category: SecretCategory,
}

/// Categories of secrets for grouping and filtering
#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum SecretCategory {
    CloudProvider,  // AWS, GCP, Azure
    VersionControl, // GitHub, GitLab
    Authentication, // JWT, Bearer, OAuth
    Database,       // Connection strings
    Cryptographic,  // Private keys, certificates
    Generic,        // API keys, passwords
    Network,        // IPs (optional)
}

/// Result of redaction with metadata
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RedactionResult {
    pub redacted_text: String,
    pub original_length: usize,
    pub redactions: Vec<RedactionMatch>,
}

/// Information about a single redacted secret
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RedactionMatch {
    pub pattern_name: String,
    pub category: SecretCategory,
    pub start: usize,
    pub end: usize,
    pub original_value: String, // For reveal-on-hover
}

/// Main secret redactor
pub struct SecretRedactor {
    patterns: Vec<CompiledPattern>,
    replacement: String,
    enabled: bool,
    redact_ips: bool,
}

struct CompiledPattern {
    info: SecretPattern,
    regex: Regex,
}

impl SecretRedactor {
    /// Create a new redactor with default patterns
    pub fn new() -> Self {
        let patterns = Self::default_patterns();
        Self::with_patterns(patterns)
    }

    /// Create a redactor with custom patterns
    pub fn with_patterns(patterns: Vec<SecretPattern>) -> Self {
        let compiled: Vec<CompiledPattern> = patterns
            .into_iter()
            .filter(|p| p.enabled)
            .filter_map(|p| {
                Regex::new(&p.pattern).ok().map(|r| CompiledPattern {
                    info: p,
                    regex: r,
                })
            })
            .collect();

        Self {
            patterns: compiled,
            replacement: "••••••••".to_string(),
            enabled: true,
            redact_ips: false,
        }
    }

    /// Enable or disable redaction globally
    pub fn set_enabled(&mut self, enabled: bool) {
        self.enabled = enabled;
    }

    /// Enable or disable IP address redaction
    pub fn set_redact_ips(&mut self, redact: bool) {
        self.redact_ips = redact;
    }

    /// Set custom replacement string
    pub fn set_replacement(&mut self, replacement: String) {
        self.replacement = replacement;
    }

    /// Redact secrets from text (simple version - just returns redacted string)
    pub fn redact(&self, text: &str) -> String {
        if !self.enabled {
            return text.to_string();
        }
        self.redact_with_info(text).redacted_text
    }

    /// Redact secrets with full metadata (for reveal-on-hover, logging, etc.)
    pub fn redact_with_info(&self, text: &str) -> RedactionResult {
        if !self.enabled {
            return RedactionResult {
                redacted_text: text.to_string(),
                original_length: text.len(),
                redactions: vec![],
            };
        }

        let mut result = text.to_string();
        let mut redactions = vec![];
        let mut offset: i64 = 0;

        for compiled in &self.patterns {
            // Skip IP patterns if not enabled
            if compiled.info.category == SecretCategory::Network && !self.redact_ips {
                continue;
            }

            for mat in compiled.regex.find_iter(text) {
                let adjusted_start = (mat.start() as i64 + offset) as usize;
                let adjusted_end = (mat.end() as i64 + offset) as usize;

                redactions.push(RedactionMatch {
                    pattern_name: compiled.info.name.clone(),
                    category: compiled.info.category.clone(),
                    start: mat.start(),
                    end: mat.end(),
                    original_value: mat.as_str().to_string(),
                });

                // Replace in result
                let replacement_len = self.replacement.len();
                let match_len = adjusted_end - adjusted_start;
                result.replace_range(adjusted_start..adjusted_end, &self.replacement);
                offset += replacement_len as i64 - match_len as i64;
            }
        }

        RedactionResult {
            redacted_text: result,
            original_length: text.len(),
            redactions,
        }
    }

    /// Check if text contains any secrets (without modifying)
    pub fn contains_secrets(&self, text: &str) -> bool {
        if !self.enabled {
            return false;
        }
        self.patterns.iter().any(|p| p.regex.is_match(text))
    }

    /// Get statistics about redactions by category
    pub fn get_stats(&self, text: &str) -> HashMap<SecretCategory, usize> {
        let result = self.redact_with_info(text);
        let mut stats = HashMap::new();
        for redaction in result.redactions {
            *stats.entry(redaction.category).or_insert(0) += 1;
        }
        stats
    }

    /// Default patterns for common secrets
    fn default_patterns() -> Vec<SecretPattern> {
        vec![
            // AWS
            SecretPattern {
                name: "AWS Access Key ID".into(),
                pattern: r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}".into(),
                enabled: true,
                category: SecretCategory::CloudProvider,
            },
            SecretPattern {
                name: "AWS Secret Access Key".into(),
                pattern: r"(?i)(?:aws_secret_access_key|aws_secret_key|secret_access_key)\s*[=:]\s*[A-Za-z0-9/+=]{40}".into(),
                enabled: true,
                category: SecretCategory::CloudProvider,
            },
            SecretPattern {
                name: "AWS Session Token".into(),
                pattern: r"(?i)aws_session_token\s*[=:]\s*[A-Za-z0-9/+=]{100,}".into(),
                enabled: true,
                category: SecretCategory::CloudProvider,
            },

            // Google Cloud
            SecretPattern {
                name: "Google API Key".into(),
                pattern: r"AIza[0-9A-Za-z_-]{35}".into(),
                enabled: true,
                category: SecretCategory::CloudProvider,
            },
            SecretPattern {
                name: "Google OAuth Token".into(),
                pattern: r"ya29\.[0-9A-Za-z_-]+".into(),
                enabled: true,
                category: SecretCategory::CloudProvider,
            },

            // GitHub
            SecretPattern {
                name: "GitHub Personal Access Token".into(),
                pattern: r"ghp_[A-Za-z0-9]{36,}".into(),
                enabled: true,
                category: SecretCategory::VersionControl,
            },
            SecretPattern {
                name: "GitHub OAuth Access Token".into(),
                pattern: r"gho_[A-Za-z0-9]{36,}".into(),
                enabled: true,
                category: SecretCategory::VersionControl,
            },
            SecretPattern {
                name: "GitHub App Token".into(),
                pattern: r"(?:ghu|ghs)_[A-Za-z0-9]{36,}".into(),
                enabled: true,
                category: SecretCategory::VersionControl,
            },
            SecretPattern {
                name: "GitHub Refresh Token".into(),
                pattern: r"ghr_[A-Za-z0-9]{36,}".into(),
                enabled: true,
                category: SecretCategory::VersionControl,
            },

            // GitLab
            SecretPattern {
                name: "GitLab Personal Access Token".into(),
                pattern: r"glpat-[A-Za-z0-9_-]{20,}".into(),
                enabled: true,
                category: SecretCategory::VersionControl,
            },

            // Stripe
            SecretPattern {
                name: "Stripe API Key".into(),
                pattern: r"(?:sk|pk)_(?:live|test)_[A-Za-z0-9]{24,}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // Slack
            SecretPattern {
                name: "Slack Token".into(),
                pattern: r"xox[baprs]-[A-Za-z0-9-]{10,}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },
            SecretPattern {
                name: "Slack Webhook".into(),
                pattern: r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]+".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // Discord
            SecretPattern {
                name: "Discord Token".into(),
                pattern: r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },
            SecretPattern {
                name: "Discord Webhook".into(),
                pattern: r"https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_-]+".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // Authentication
            SecretPattern {
                name: "JWT Token".into(),
                pattern: r"eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*".into(),
                enabled: true,
                category: SecretCategory::Authentication,
            },
            SecretPattern {
                name: "Bearer Token".into(),
                pattern: r"(?i)bearer\s+[A-Za-z0-9_.~+/-]+=*".into(),
                enabled: true,
                category: SecretCategory::Authentication,
            },
            SecretPattern {
                name: "Basic Auth Header".into(),
                pattern: r"(?i)basic\s+[A-Za-z0-9+/]+=*".into(),
                enabled: true,
                category: SecretCategory::Authentication,
            },

            // Cryptographic
            SecretPattern {
                name: "RSA Private Key".into(),
                pattern: r"-----BEGIN RSA PRIVATE KEY-----".into(),
                enabled: true,
                category: SecretCategory::Cryptographic,
            },
            SecretPattern {
                name: "OpenSSH Private Key".into(),
                pattern: r"-----BEGIN OPENSSH PRIVATE KEY-----".into(),
                enabled: true,
                category: SecretCategory::Cryptographic,
            },
            SecretPattern {
                name: "PGP Private Key".into(),
                pattern: r"-----BEGIN PGP PRIVATE KEY BLOCK-----".into(),
                enabled: true,
                category: SecretCategory::Cryptographic,
            },
            SecretPattern {
                name: "EC Private Key".into(),
                pattern: r"-----BEGIN EC PRIVATE KEY-----".into(),
                enabled: true,
                category: SecretCategory::Cryptographic,
            },

            // Database
            SecretPattern {
                name: "PostgreSQL Connection String".into(),
                pattern: r"postgres(?:ql)?://[^:]+:[^@]+@[^\s]+".into(),
                enabled: true,
                category: SecretCategory::Database,
            },
            SecretPattern {
                name: "MySQL Connection String".into(),
                pattern: r"mysql://[^:]+:[^@]+@[^\s]+".into(),
                enabled: true,
                category: SecretCategory::Database,
            },
            SecretPattern {
                name: "MongoDB Connection String".into(),
                pattern: r"mongodb(?:\+srv)?://[^:]+:[^@]+@[^\s]+".into(),
                enabled: true,
                category: SecretCategory::Database,
            },
            SecretPattern {
                name: "Redis Connection String".into(),
                pattern: r"redis://[^:]+:[^@]+@[^\s]+".into(),
                enabled: true,
                category: SecretCategory::Database,
            },

            // Generic patterns
            SecretPattern {
                name: "Generic API Key".into(),
                pattern: r#"(?i)(?:api[_-]?key|apikey)\s*[=:]\s*['"]?[A-Za-z0-9_-]{20,}['"]?"#.into(),
                enabled: true,
                category: SecretCategory::Generic,
            },
            SecretPattern {
                name: "Generic Secret".into(),
                pattern: r#"(?i)(?:secret|token|password|passwd|pwd)\s*[=:]\s*['"]?[^\s'"]{8,}['"]?"#.into(),
                enabled: true,
                category: SecretCategory::Generic,
            },
            SecretPattern {
                name: "Password in URL".into(),
                pattern: r"://[^/:]+:([^@/]+)@".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },
            SecretPattern {
                name: "Password CLI Argument".into(),
                pattern: r"(?i)(?:-p|--password|--passwd)\s*[=\s]\s*[^\s]+".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // Network (optional - disabled by default)
            SecretPattern {
                name: "IPv4 Address".into(),
                pattern: r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b".into(),
                enabled: false, // Disabled by default - too many false positives
                category: SecretCategory::Network,
            },

            // Anthropic
            SecretPattern {
                name: "Anthropic API Key".into(),
                pattern: r"sk-ant-[A-Za-z0-9_-]{40,}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // OpenAI
            SecretPattern {
                name: "OpenAI API Key".into(),
                pattern: r"sk-[A-Za-z0-9]{48}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // Twilio
            SecretPattern {
                name: "Twilio API Key".into(),
                pattern: r"SK[A-Za-z0-9]{32}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // SendGrid
            SecretPattern {
                name: "SendGrid API Key".into(),
                pattern: r"SG\.[A-Za-z0-9_-]{22}\.[A-Za-z0-9_-]{43}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // Heroku
            SecretPattern {
                name: "Heroku API Key".into(),
                pattern: r"(?i)heroku[_-]?api[_-]?key\s*[=:]\s*[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}".into(),
                enabled: true,
                category: SecretCategory::CloudProvider,
            },

            // npm
            SecretPattern {
                name: "npm Token".into(),
                pattern: r"npm_[A-Za-z0-9]{36}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },

            // PyPI
            SecretPattern {
                name: "PyPI Token".into(),
                pattern: r"pypi-[A-Za-z0-9_-]{50,}".into(),
                enabled: true,
                category: SecretCategory::Generic,
            },
        ]
    }
}

impl Default for SecretRedactor {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_aws_access_key() {
        let redactor = SecretRedactor::new();
        let text = "export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
        assert!(!result.contains("AKIAIOSFODNN7EXAMPLE"));
    }

    #[test]
    fn test_github_token() {
        let redactor = SecretRedactor::new();
        let text = "gh auth login --with-token ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
        assert!(!result.contains("ghp_"));
    }

    #[test]
    fn test_jwt() {
        let redactor = SecretRedactor::new();
        let text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
        assert!(!result.contains("eyJ"));
    }

    #[test]
    fn test_password_in_url() {
        let redactor = SecretRedactor::new();
        let text = "postgresql://admin:supersecretpassword@localhost:5432/mydb";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
    }

    #[test]
    fn test_private_key() {
        let redactor = SecretRedactor::new();
        let text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQ...";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
    }

    #[test]
    fn test_openai_key() {
        let redactor = SecretRedactor::new();
        let text = "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz123456789012345678";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
    }

    #[test]
    fn test_anthropic_key() {
        let redactor = SecretRedactor::new();
        let text = "export ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
        let result = redactor.redact(text);
        assert!(result.contains("••••••••"));
    }

    #[test]
    fn test_no_false_positive_on_normal_text() {
        let redactor = SecretRedactor::new();
        let text = "Hello world, this is a normal command: ls -la";
        let result = redactor.redact(text);
        assert_eq!(result, text);
    }

    #[test]
    fn test_disabled_redactor() {
        let mut redactor = SecretRedactor::new();
        redactor.set_enabled(false);
        let text = "ghp_secrettoken123456789012345678901234";
        let result = redactor.redact(text);
        assert_eq!(result, text);
    }

    #[test]
    fn test_contains_secrets() {
        let redactor = SecretRedactor::new();
        assert!(redactor.contains_secrets("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"));
        assert!(!redactor.contains_secrets("hello world"));
    }

    #[test]
    fn test_redact_with_info() {
        let redactor = SecretRedactor::new();
        let text = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx";
        let result = redactor.redact_with_info(text);
        assert!(!result.redactions.is_empty());
        assert_eq!(result.redactions[0].pattern_name, "GitHub Personal Access Token");
    }
}
