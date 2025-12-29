// warp_core/tests/osc_parser_tests.rs
// Basic unit tests for OSC133 parser

use warp_core::osc_parser::OSC133Parser;

#[test]
fn test_parse_osc_133_prompt_start() {
    let mut parser = OSC133Parser::new();
    let input: &[u8] = b"\x1b]133;A\x07";
    let events = parser.parse(input);
    assert!(!events.is_empty(), "expected at least one OSC event");
    assert_eq!(events[0].event_type, "prompt_start");
}

#[test]
fn test_parse_osc_133_command_start() {
    let mut parser = OSC133Parser::new();
    let input: &[u8] = b"\x1b]133;B\x07";
    let events = parser.parse(input);
    assert!(!events.is_empty(), "expected at least one OSC event");
    assert_eq!(events[0].event_type, "command_start");
}

#[test]
fn test_parse_osc_133_command_finished_with_exit_code() {
    let mut parser = OSC133Parser::new();
    let input: &[u8] = b"\x1b]133;D;0\x07";
    let events = parser.parse(input);
    assert!(!events.is_empty(), "expected at least one OSC event");
    assert_eq!(events[0].event_type, "command_finished");
}

#[test]
fn test_overlapping_osc_sequences() {
    let mut parser = OSC133Parser::new();
    // Multiple OSC sequences in quick succession
    let input: &[u8] = b"\x1b]133;A\x07\x1b]133;B\x07";
    let events = parser.parse(input);
    assert!(events.len() >= 2, "expected multiple OSC events");
}

#[test]
fn test_parser_recovers_from_malformed_input() {
    let mut parser = OSC133Parser::new();
    // Partial/broken escape sequence
    let input: &[u8] = b"\x1b[0;3";
    let events = parser.parse(input);
    // Parser should not panic and should handle gracefully
    // May return 0 events but should not crash - just check it doesn't panic
    let _ = events.len();
}

#[test]
fn test_parser_with_mixed_content() {
    let mut parser = OSC133Parser::new();
    let input: &[u8] = b"\x1b]133;A\x07user@host:~$ echo test\r\n\x1b]133;D;0\x07";
    let events = parser.parse(input);
    assert!(events.len() >= 1, "expected OSC events in mixed content");
}
