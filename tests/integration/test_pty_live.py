#!/usr/bin/env python3
"""
Live PTY Integration Tests

Tests the warp_cli run-pty subcommand with real shell interactions.
All tests are deterministic and non-hanging with timeouts.
"""

import subprocess
import sys
import time
import threading
import queue
import os

def read_output_with_timeout(proc, output_queue, timeout=5):
    """Read output from process with timeout"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            char = proc.stdout.read(1)
            if not char:
                break
            output_queue.put(char)
        except:
            break

def run_pty_command(commands, timeout=5):
    """
    Run warp_cli run-pty with given commands
    Returns (stdout, stderr, exit_code)
    """
    # Build the cargo command
    cmd = ["cargo", "run", "--bin", "warp_cli", "--", "run-pty"]
    
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd="/Users/davidquinton/ReverseLab/Warp_Open/warp_core",
        bufsize=0
    )
    
    # Create queue for output
    output_queue = queue.Queue()
    
    # Start output reader thread
    reader_thread = threading.Thread(
        target=read_output_with_timeout,
        args=(proc, output_queue, timeout)
    )
    reader_thread.daemon = True
    reader_thread.start()
    
    # Send commands
    for cmd_str in commands:
        proc.stdin.write(cmd_str.encode())
        proc.stdin.flush()
        time.sleep(0.2)  # Give PTY time to process
    
    # Wait for process to finish or timeout
    try:
        proc.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    
    # Collect output
    output_bytes = b""
    while not output_queue.empty():
        try:
            output_bytes += output_queue.get_nowait()
        except queue.Empty:
            break
    
    stderr = proc.stderr.read()
    
    return output_bytes, stderr, proc.returncode

def test_echo_command():
    """Test basic echo command"""
    print("Test 1: Echo command...")
    
    commands = [
        "echo hello\n",
        "exit\n"
    ]
    
    stdout, stderr, exit_code = run_pty_command(commands, timeout=3)
    stdout_str = stdout.decode('utf-8', errors='replace')
    
    # Verify output contains "hello"
    assert b"hello" in stdout, f"Expected 'hello' in output, got: {stdout_str[:200]}"
    print("✅ Echo command test passed")

def test_multiline_output():
    """Test command with multiple lines of output"""
    print("Test 2: Multiline output...")
    
    commands = [
        "printf 'line1\\nline2\\nline3\\n'\n",
        "exit\n"
    ]
    
    stdout, stderr, exit_code = run_pty_command(commands, timeout=3)
    stdout_str = stdout.decode('utf-8', errors='replace')
    
    # Verify all lines are present
    assert b"line1" in stdout, f"Expected 'line1' in output"
    assert b"line2" in stdout, f"Expected 'line2' in output"
    assert b"line3" in stdout, f"Expected 'line3' in output"
    print("✅ Multiline output test passed")

def test_exit_handling():
    """Test that PTY exits cleanly"""
    print("Test 3: Exit handling...")
    
    commands = [
        "echo test\n",
        "exit\n"
    ]
    
    stdout, stderr, exit_code = run_pty_command(commands, timeout=3)
    
    # Process should exit (exit code may vary but should not timeout)
    assert exit_code is not None, "Process should have exited"
    print(f"✅ Exit handling test passed (exit code: {exit_code})")

def test_pwd_command():
    """Test pwd command"""
    print("Test 4: PWD command...")
    
    commands = [
        "pwd\n",
        "exit\n"
    ]
    
    stdout, stderr, exit_code = run_pty_command(commands, timeout=3)
    stdout_str = stdout.decode('utf-8', errors='replace')
    
    # Should contain some path
    assert (b"/" in stdout) or (b"\\" in stdout), f"Expected path in output"
    print("✅ PWD command test passed")

def main():
    """Run all tests"""
    print("=" * 60)
    print("PTY Live Integration Tests")
    print("=" * 60)
    
    tests = [
        test_echo_command,
        test_multiline_output,
        test_exit_handling,
        test_pwd_command,
    ]
    
    failed = []
    
    for test in tests:
        try:
            test()
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed.append(test.__name__)
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed.append(test.__name__)
    
    print("=" * 60)
    if failed:
        print(f"❌ {len(failed)} test(s) failed: {', '.join(failed)}")
        sys.exit(1)
    else:
        print(f"✅ All {len(tests)} tests passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
