//! Intent Sanitizer - Transforms sensitive queries into clean, safe versions
//! for external LLM consumption while preserving the technical intent.
//!
//! The original sensitive context is kept ephemeral (not logged), while the
//! sanitized version and results ARE logged.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Sensitivity level of content
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum SensitivityLevel {
    Safe,           // Can be sent anywhere, logged normally
    Moderate,       // Needs minor rephrasing
    Sensitive,      // Needs significant sanitization
    Private,        // Never send externally, local only
}

/// Result of sanitization
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SanitizedQuery {
    pub original_hash: String,          // Hash of original (for correlation, not content)
    pub sanitized_text: String,         // Clean version for external LLMs
    pub sensitivity: SensitivityLevel,
    pub sanitization_notes: String,     // What was changed (for user transparency)
    pub can_send_external: bool,        // Whether this is safe to send out
    pub suggested_framing: Option<String>, // How to frame the request
}

/// Patterns that trigger sanitization
struct SensitivityPattern {
    patterns: Vec<&'static str>,
    level: SensitivityLevel,
    replacement_strategy: ReplacementStrategy,
}

#[derive(Clone)]
enum ReplacementStrategy {
    Reframe,        // Reframe as technical/creative writing task
    Generalize,     // Make more generic
    Abstract,       // Abstract away specifics
    LocalOnly,      // Don't send externally at all
}

pub struct IntentSanitizer {
    patterns: Vec<SensitivityPattern>,
    // Mapping of sensitive terms to safe alternatives
    term_mappings: HashMap<String, String>,
}

impl IntentSanitizer {
    pub fn new() -> Self {
        let mut term_mappings = HashMap::new();

        // Content type reframings
        term_mappings.insert("explicit".to_string(), "mature creative writing".to_string());
        term_mappings.insert("nsfw".to_string(), "adult fiction".to_string());
        term_mappings.insert("roleplay".to_string(), "interactive fiction".to_string());
        term_mappings.insert("erotic".to_string(), "romance fiction".to_string());
        term_mappings.insert("porn".to_string(), "adult content".to_string());
        term_mappings.insert("sex".to_string(), "intimate scene".to_string());
        term_mappings.insert("nude".to_string(), "figure study".to_string());

        // Technical reframings for code
        term_mappings.insert("hack".to_string(), "security research".to_string());
        term_mappings.insert("crack".to_string(), "reverse engineer".to_string());
        term_mappings.insert("bypass".to_string(), "work around".to_string());
        term_mappings.insert("exploit".to_string(), "vulnerability research".to_string());

        let patterns = vec![
            // Adult content - reframe as creative writing
            SensitivityPattern {
                patterns: vec!["explicit", "nsfw", "erotic", "sexual", "nude", "porn"],
                level: SensitivityLevel::Sensitive,
                replacement_strategy: ReplacementStrategy::Reframe,
            },
            // Personal/relationship - generalize
            SensitivityPattern {
                patterns: vec!["my girlfriend", "my boyfriend", "my partner", "my wife", "my husband"],
                level: SensitivityLevel::Moderate,
                replacement_strategy: ReplacementStrategy::Generalize,
            },
            // Security research - reframe as legitimate research
            SensitivityPattern {
                patterns: vec!["hack", "crack", "bypass", "exploit", "vulnerability"],
                level: SensitivityLevel::Moderate,
                replacement_strategy: ReplacementStrategy::Reframe,
            },
            // Truly private - never send externally
            SensitivityPattern {
                patterns: vec!["password", "api key", "secret", "credential", "private key", "ssn", "social security"],
                level: SensitivityLevel::Private,
                replacement_strategy: ReplacementStrategy::LocalOnly,
            },
        ];

        Self {
            patterns,
            term_mappings,
        }
    }

    /// Analyze and sanitize a query
    pub fn sanitize(&self, input: &str, explicit_private: bool) -> SanitizedQuery {
        let lower = input.to_lowercase();

        // Check if explicitly marked private
        if explicit_private || lower.contains("private") || lower.contains("privately") {
            return SanitizedQuery {
                original_hash: Self::hash_content(input),
                sanitized_text: String::new(),
                sensitivity: SensitivityLevel::Private,
                sanitization_notes: "Marked as private - processing locally only".to_string(),
                can_send_external: false,
                suggested_framing: None,
            };
        }

        // Detect sensitivity level
        let (level, strategy) = self.detect_sensitivity(&lower);

        match level {
            SensitivityLevel::Safe => SanitizedQuery {
                original_hash: Self::hash_content(input),
                sanitized_text: input.to_string(),
                sensitivity: SensitivityLevel::Safe,
                sanitization_notes: "No sanitization needed".to_string(),
                can_send_external: true,
                suggested_framing: None,
            },
            SensitivityLevel::Moderate => {
                let sanitized = self.apply_term_mappings(input);
                SanitizedQuery {
                    original_hash: Self::hash_content(input),
                    sanitized_text: sanitized.clone(),
                    sensitivity: SensitivityLevel::Moderate,
                    sanitization_notes: format!("Minor rephrasing applied"),
                    can_send_external: true,
                    suggested_framing: Some(self.generate_framing(&sanitized, &strategy)),
                }
            },
            SensitivityLevel::Sensitive => {
                let sanitized = self.deep_sanitize(input, &strategy);
                SanitizedQuery {
                    original_hash: Self::hash_content(input),
                    sanitized_text: sanitized.text.clone(),
                    sensitivity: SensitivityLevel::Sensitive,
                    sanitization_notes: sanitized.notes,
                    can_send_external: true,
                    suggested_framing: Some(sanitized.framing),
                }
            },
            SensitivityLevel::Private => SanitizedQuery {
                original_hash: Self::hash_content(input),
                sanitized_text: String::new(),
                sensitivity: SensitivityLevel::Private,
                sanitization_notes: "Contains private data - local processing only".to_string(),
                can_send_external: false,
                suggested_framing: None,
            },
        }
    }

    fn detect_sensitivity(&self, input: &str) -> (SensitivityLevel, ReplacementStrategy) {
        for pattern in &self.patterns {
            for p in &pattern.patterns {
                if input.contains(p) {
                    return (pattern.level.clone(), pattern.replacement_strategy.clone());
                }
            }
        }
        (SensitivityLevel::Safe, ReplacementStrategy::Reframe)
    }

    fn apply_term_mappings(&self, input: &str) -> String {
        let mut result = input.to_string();
        for (sensitive, safe) in &self.term_mappings {
            // Case-insensitive replacement
            let re = regex::RegexBuilder::new(&regex::escape(sensitive))
                .case_insensitive(true)
                .build()
                .unwrap();
            result = re.replace_all(&result, safe.as_str()).to_string();
        }
        result
    }

    fn deep_sanitize(&self, input: &str, strategy: &ReplacementStrategy) -> DeepSanitizeResult {
        match strategy {
            ReplacementStrategy::Reframe => {
                // Reframe as a technical/creative task
                let sanitized = self.apply_term_mappings(input);
                let framing = self.create_technical_framing(&sanitized);
                DeepSanitizeResult {
                    text: framing.clone(),
                    notes: "Reframed as creative/technical task".to_string(),
                    framing,
                }
            },
            ReplacementStrategy::Generalize => {
                let sanitized = self.generalize_personal_info(input);
                DeepSanitizeResult {
                    text: sanitized.clone(),
                    notes: "Personal details generalized".to_string(),
                    framing: sanitized,
                }
            },
            ReplacementStrategy::Abstract => {
                let sanitized = self.abstract_specifics(input);
                DeepSanitizeResult {
                    text: sanitized.clone(),
                    notes: "Specific details abstracted".to_string(),
                    framing: sanitized,
                }
            },
            ReplacementStrategy::LocalOnly => {
                DeepSanitizeResult {
                    text: String::new(),
                    notes: "Cannot sanitize - must process locally".to_string(),
                    framing: String::new(),
                }
            },
        }
    }

    fn create_technical_framing(&self, input: &str) -> String {
        // Detect what kind of content and frame appropriately
        let lower = input.to_lowercase();

        if lower.contains("story") || lower.contains("write") || lower.contains("fiction")
           || lower.contains("character") || lower.contains("dialogue") {
            format!("For a creative writing project: {}", input)
        } else if lower.contains("code") || lower.contains("function") || lower.contains("implement") {
            format!("For a software development task: {}", input)
        } else if lower.contains("image") || lower.contains("visual") || lower.contains("art") {
            format!("For an art/design project: {}", input)
        } else {
            format!("For a technical project: {}", input)
        }
    }

    fn generalize_personal_info(&self, input: &str) -> String {
        let mut result = input.to_string();
        // Replace personal references with generic ones
        let personal_patterns = [
            ("my girlfriend", "a character"),
            ("my boyfriend", "a character"),
            ("my partner", "a character"),
            ("my wife", "a character"),
            ("my husband", "a character"),
            ("my friend", "a character"),
        ];

        for (personal, generic) in personal_patterns {
            let re = regex::RegexBuilder::new(personal)
                .case_insensitive(true)
                .build()
                .unwrap();
            result = re.replace_all(&result, generic).to_string();
        }
        result
    }

    fn abstract_specifics(&self, input: &str) -> String {
        // Remove specific names, dates, locations
        let mut result = input.to_string();

        // This is a simplified version - in production would use NER
        // For now, just remove quoted strings that might be names
        let re = regex::Regex::new(r#""[^"]+""#).unwrap();
        result = re.replace_all(&result, "[REDACTED]").to_string();

        result
    }

    fn generate_framing(&self, content: &str, _strategy: &ReplacementStrategy) -> String {
        format!("Assist with the following technical task: {}", content)
    }

    fn hash_content(content: &str) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};
        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        format!("{:x}", hasher.finish())
    }

    /// Get a human-readable explanation of what was sanitized
    pub fn explain_sanitization(&self, result: &SanitizedQuery) -> String {
        match result.sensitivity {
            SensitivityLevel::Safe => {
                "Query is safe - sending as-is".to_string()
            },
            SensitivityLevel::Moderate => {
                format!("Minor adjustments made: {}\nSending: \"{}\"",
                    result.sanitization_notes,
                    &result.sanitized_text[..std::cmp::min(100, result.sanitized_text.len())])
            },
            SensitivityLevel::Sensitive => {
                format!("Significant sanitization applied: {}\nExternal LLM will see: \"{}...\"",
                    result.sanitization_notes,
                    &result.sanitized_text[..std::cmp::min(80, result.sanitized_text.len())])
            },
            SensitivityLevel::Private => {
                "Private mode - processing locally, nothing sent externally".to_string()
            },
        }
    }
}

struct DeepSanitizeResult {
    text: String,
    notes: String,
    framing: String,
}

impl Default for IntentSanitizer {
    fn default() -> Self {
        Self::new()
    }
}

// Global instance
lazy_static::lazy_static! {
    static ref SANITIZER: IntentSanitizer = IntentSanitizer::new();
}

pub fn sanitize_query(input: &str, explicit_private: bool) -> SanitizedQuery {
    SANITIZER.sanitize(input, explicit_private)
}

pub fn explain_sanitization(result: &SanitizedQuery) -> String {
    SANITIZER.explain_sanitization(result)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_safe_query() {
        let result = sanitize_query("How do I write a React component?", false);
        assert_eq!(result.sensitivity, SensitivityLevel::Safe);
        assert!(result.can_send_external);
    }

    #[test]
    fn test_private_query() {
        let result = sanitize_query("privately help me with something", false);
        assert_eq!(result.sensitivity, SensitivityLevel::Private);
        assert!(!result.can_send_external);
    }

    #[test]
    fn test_sensitive_reframe() {
        let result = sanitize_query("write an explicit story", false);
        assert_eq!(result.sensitivity, SensitivityLevel::Sensitive);
        assert!(result.can_send_external);
        assert!(result.sanitized_text.contains("mature creative writing"));
    }
}
