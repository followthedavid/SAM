//! Test Harness - Headless batch testing for SAM
//!
//! Runs prompts directly through the orchestrator without UI interaction.
//! No windows, no screenshots, no keyboard hijacking.

use serde::{Deserialize, Serialize};
use std::time::Instant;
use crate::scaffolding::orchestrator::{orchestrate, OrchestratorContext, OrchestratorResult, ConversationTurn};
use crate::scaffolding::hybrid_router::{ProcessingPath, route_request};
use crate::scaffolding::intent_sanitizer::{sanitize_query, SensitivityLevel};

/// A single test case
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestCase {
    pub name: String,
    pub input: String,
    pub expected_path: Option<String>,           // Expected routing path
    pub expected_contains: Vec<String>,          // Output should contain these
    pub expected_not_contains: Vec<String>,      // Output should NOT contain these
    pub should_sanitize: bool,                   // Whether sanitization should occur
    pub expected_sensitivity: Option<String>,    // Expected sensitivity level
    pub timeout_ms: u64,                         // Max time allowed
}

/// Result of running a test case
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestResult {
    pub name: String,
    pub passed: bool,
    pub input: String,
    pub actual_path: String,
    pub actual_output: String,
    pub latency_ms: u64,
    pub was_sanitized: bool,
    pub sanitized_text: Option<String>,
    pub sensitivity_level: String,
    pub errors: Vec<String>,
}

/// Summary of a test run
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TestSummary {
    pub total: usize,
    pub passed: usize,
    pub failed: usize,
    pub skipped: usize,
    pub total_time_ms: u64,
    pub results: Vec<TestResult>,
}

/// Run a single test case through the orchestrator
pub async fn run_single_test(case: &TestCase) -> TestResult {
    let start = Instant::now();
    let mut errors = Vec::new();

    // 1. Check routing
    let routing = route_request(&case.input);
    let actual_path = format!("{:?}", routing.processing_path);

    // 2. Check sanitization
    let sanitization = sanitize_query(&case.input, false);
    // was_sanitized = true if sanitized text differs from input
    let was_sanitized = sanitization.sanitized_text != case.input;
    let sensitivity_level = format!("{:?}", sanitization.sensitivity);

    // 3. Validate routing if expected
    if let Some(ref expected) = case.expected_path {
        if !actual_path.to_lowercase().contains(&expected.to_lowercase()) {
            errors.push(format!(
                "Routing mismatch: expected '{}', got '{}'",
                expected, actual_path
            ));
        }
    }

    // 4. Validate sanitization
    if case.should_sanitize && !was_sanitized {
        errors.push("Expected sanitization but none occurred".to_string());
    }
    if !case.should_sanitize && was_sanitized {
        errors.push(format!(
            "Unexpected sanitization: '{}' -> '{}'",
            case.input, sanitization.sanitized_text
        ));
    }

    // 5. Validate sensitivity level if expected
    if let Some(ref expected_sens) = case.expected_sensitivity {
        if !sensitivity_level.to_lowercase().contains(&expected_sens.to_lowercase()) {
            errors.push(format!(
                "Sensitivity mismatch: expected '{}', got '{}'",
                expected_sens, sensitivity_level
            ));
        }
    }

    // 6. Run through orchestrator (without full execution to avoid side effects)
    let ctx = OrchestratorContext {
        working_directory: std::env::current_dir().unwrap_or_default(),
        session_id: format!("test_{}", uuid::Uuid::new_v4()),
        max_tokens: 1000,
        stream: false,
        conversation_history: vec![],
    };

    let result = orchestrate(&case.input, &ctx).await;
    let actual_output = match &result {
        OrchestratorResult::Instant(r) => r.output.clone(),
        OrchestratorResult::Search(r) => format!("{} results", r.chunks.len()),
        OrchestratorResult::Generated(r) => r.content.clone(),
        OrchestratorResult::Error(r) => format!("ERROR: {}", r.message),
    };

    // 7. Validate output contains expected strings
    for expected in &case.expected_contains {
        if !actual_output.to_lowercase().contains(&expected.to_lowercase()) {
            errors.push(format!("Output missing expected: '{}'", expected));
        }
    }

    // 8. Validate output does NOT contain forbidden strings
    for forbidden in &case.expected_not_contains {
        if actual_output.to_lowercase().contains(&forbidden.to_lowercase()) {
            errors.push(format!("Output contains forbidden: '{}'", forbidden));
        }
    }

    let latency_ms = start.elapsed().as_millis() as u64;

    // 9. Check timeout
    if latency_ms > case.timeout_ms && case.timeout_ms > 0 {
        errors.push(format!(
            "Timeout exceeded: {}ms > {}ms",
            latency_ms, case.timeout_ms
        ));
    }

    TestResult {
        name: case.name.clone(),
        passed: errors.is_empty(),
        input: case.input.clone(),
        actual_path,
        actual_output,
        latency_ms,
        was_sanitized,
        sanitized_text: if was_sanitized {
            Some(sanitization.sanitized_text)
        } else {
            None
        },
        sensitivity_level,
        errors,
    }
}

/// Get the default test suite
pub fn get_default_test_suite() -> Vec<TestCase> {
    vec![
        // === ROUTING TESTS ===
        TestCase {
            name: "Deterministic: git status".to_string(),
            input: "git status".to_string(),
            expected_path: Some("Deterministic".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 500,
        },
        TestCase {
            name: "Deterministic: list files".to_string(),
            input: "ls -la".to_string(),
            expected_path: Some("Deterministic".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 500,
        },
        TestCase {
            name: "Search: where is auth".to_string(),
            input: "where is authentication handled".to_string(),
            expected_path: Some("Embedding".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 2000,
        },
        TestCase {
            name: "Conversational: daily brief".to_string(),
            input: "give me a daily brief".to_string(),
            expected_path: Some("Conversational".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 5000,
        },

        // === PRIVACY TESTS ===
        TestCase {
            name: "Privacy: explicit private request".to_string(),
            input: "let's roleplay privately".to_string(),
            expected_path: Some("Conversational".to_string()),  // Should use local conversational mode
            expected_contains: vec![],
            expected_not_contains: vec!["chatgpt".to_string(), "claude-bridge".to_string()],
            should_sanitize: false,
            expected_sensitivity: None,
            timeout_ms: 5000,
        },
        TestCase {
            name: "Privacy: local keyword".to_string(),
            input: "keep this local please".to_string(),
            expected_path: Some("MicroModel".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: None,
            timeout_ms: 5000,
        },

        // === SANITIZATION TESTS ===
        TestCase {
            name: "Sanitize: explicit content".to_string(),
            input: "write explicit content for my game".to_string(),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: true,
            expected_sensitivity: Some("Sensitive".to_string()),
            timeout_ms: 5000,
        },
        TestCase {
            name: "Sanitize: NSFW term".to_string(),
            input: "generate NSFW art".to_string(),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: true,
            expected_sensitivity: Some("Sensitive".to_string()),
            timeout_ms: 5000,
        },
        TestCase {
            name: "No sanitize: normal code".to_string(),
            input: "write a function to sort an array".to_string(),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 5000,
        },

        // === TOOL EXECUTION TESTS ===
        TestCase {
            name: "Shell: echo test".to_string(),
            input: "run: echo hello".to_string(),
            expected_path: Some("Deterministic".to_string()),
            expected_contains: vec!["hello".to_string()],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 1000,
        },
        TestCase {
            name: "File: read this file".to_string(),
            input: "read ./Cargo.toml".to_string(),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 1000,
        },

        // === EDGE CASES ===
        TestCase {
            name: "Empty input".to_string(),
            input: "".to_string(),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: None,
            timeout_ms: 500,
        },
        TestCase {
            name: "Very long input".to_string(),
            input: "a".repeat(5000),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: None,
            timeout_ms: 2000,
        },
    ]
}

/// Run the full test suite
pub async fn run_test_suite(cases: Option<Vec<TestCase>>) -> TestSummary {
    let start = Instant::now();
    let test_cases = cases.unwrap_or_else(get_default_test_suite);

    let mut results = Vec::new();
    let mut passed = 0;
    let mut failed = 0;

    for case in &test_cases {
        let result = run_single_test(case).await;
        if result.passed {
            passed += 1;
        } else {
            failed += 1;
        }
        results.push(result);
    }

    TestSummary {
        total: test_cases.len(),
        passed,
        failed,
        skipped: 0,
        total_time_ms: start.elapsed().as_millis() as u64,
        results,
    }
}

/// Run a quick smoke test (subset of critical tests)
pub async fn run_smoke_test() -> TestSummary {
    let smoke_tests = vec![
        TestCase {
            name: "Smoke: basic routing".to_string(),
            input: "git status".to_string(),
            expected_path: Some("Deterministic".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: Some("Safe".to_string()),
            timeout_ms: 500,
        },
        TestCase {
            name: "Smoke: privacy".to_string(),
            input: "privately discuss this".to_string(),
            expected_path: Some("MicroModel".to_string()),
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: false,
            expected_sensitivity: None,
            timeout_ms: 2000,
        },
        TestCase {
            name: "Smoke: sanitization".to_string(),
            input: "explicit content".to_string(),
            expected_path: None,
            expected_contains: vec![],
            expected_not_contains: vec![],
            should_sanitize: true,
            expected_sensitivity: Some("Sensitive".to_string()),
            timeout_ms: 1000,
        },
    ];

    run_test_suite(Some(smoke_tests)).await
}

/// Format test results for terminal display
pub fn format_results_terminal(summary: &TestSummary) -> String {
    let mut output = String::new();

    output.push_str("\n");
    output.push_str("╔══════════════════════════════════════════════════════════════╗\n");
    output.push_str("║                    SAM TEST RESULTS                          ║\n");
    output.push_str("╠══════════════════════════════════════════════════════════════╣\n");

    for result in &summary.results {
        let status = if result.passed { "✓ PASS" } else { "✗ FAIL" };
        let status_color = if result.passed { "" } else { "" };

        output.push_str(&format!(
            "║ {} {:40} {:>6}ms ║\n",
            status,
            truncate(&result.name, 40),
            result.latency_ms
        ));

        if !result.passed {
            for error in &result.errors {
                output.push_str(&format!(
                    "║   └─ {:<54} ║\n",
                    truncate(error, 54)
                ));
            }
        }
    }

    output.push_str("╠══════════════════════════════════════════════════════════════╣\n");
    output.push_str(&format!(
        "║ Total: {} | Passed: {} | Failed: {} | Time: {}ms{}\n",
        summary.total,
        summary.passed,
        summary.failed,
        summary.total_time_ms,
        " ".repeat(10)
    ));
    output.push_str("╚══════════════════════════════════════════════════════════════╝\n");

    output
}

/// Format results as JSON for programmatic use
pub fn format_results_json(summary: &TestSummary) -> String {
    serde_json::to_string_pretty(summary).unwrap_or_else(|_| "{}".to_string())
}

fn truncate(s: &str, max: usize) -> String {
    if s.len() <= max {
        format!("{:<width$}", s, width = max)
    } else {
        format!("{}...", &s[..max - 3])
    }
}

// Global test state for live monitoring
use std::sync::RwLock;
lazy_static::lazy_static! {
    static ref LAST_TEST_SUMMARY: RwLock<Option<TestSummary>> = RwLock::new(None);
    static ref TEST_RUNNING: RwLock<bool> = RwLock::new(false);
}

pub fn is_test_running() -> bool {
    *TEST_RUNNING.read().unwrap()
}

pub fn get_last_summary() -> Option<TestSummary> {
    LAST_TEST_SUMMARY.read().unwrap().clone()
}

pub async fn run_and_store_tests() -> TestSummary {
    *TEST_RUNNING.write().unwrap() = true;
    let summary = run_test_suite(None).await;
    *LAST_TEST_SUMMARY.write().unwrap() = Some(summary.clone());
    *TEST_RUNNING.write().unwrap() = false;
    summary
}
