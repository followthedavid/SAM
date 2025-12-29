// warp_core/tests/golden_screen_tests.rs
// Golden/snapshot tests using insta for canonical JSON output

use assert_cmd::Command;
use insta::assert_json_snapshot;
use serde_json::Value;

#[test]
fn golden_single_short_session() {
    // Small inline fixture representing a short ANSI+OSC stream
    let fixture = b"\x1b[0m\x1b[27m\x1b[24m\x1b[Juser@host:~$ echo hi\r\nhi\r\n";

    // Spawn warp_cli parse-stream --json
    let mut cmd = Command::cargo_bin("warp_cli").expect("warp_cli binary must be built");
    let output = cmd
        .arg("parse-stream")
        .arg("--json")
        .write_stdin(fixture)
        .assert()
        .success()
        .get_output()
        .clone();

    // Parse JSON output
    let json_out = String::from_utf8_lossy(&output.stdout);
    
    // Split by newlines and parse each JSON block
    let json_lines: Vec<Value> = json_out
        .lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect();

    // Snapshot the canonical JSON with redactions for non-deterministic fields
    assert_json_snapshot!("golden_single_short_session", json_lines, {
        "[].id" => "[redacted]",
        "[].timestamp" => "[redacted]"
    });
}

#[test]
fn golden_with_heuristic_fallback() {
    // Test with heuristic mode when OSC sequences aren't present
    let fixture = b"user@host:~$ echo test\r\ntest\r\n";

    let mut cmd = Command::cargo_bin("warp_cli").expect("warp_cli binary must be built");
    let output = cmd
        .arg("parse-stream")
        .arg("--json")
        .arg("--heuristic")
        .write_stdin(fixture)
        .assert()
        .success()
        .get_output()
        .clone();

    let json_out = String::from_utf8_lossy(&output.stdout);
    let json_lines: Vec<Value> = json_out
        .lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| serde_json::from_str(line).ok())
        .collect();

    assert_json_snapshot!("golden_with_heuristic_fallback", json_lines, {
        "[].id" => "[redacted]",
        "[].timestamp" => "[redacted]"
    });
}
