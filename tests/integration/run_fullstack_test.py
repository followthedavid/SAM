#!/usr/bin/env python3
# tests/integration/run_fullstack_test.py
# Basic harness: run warp_cli parse-stream --json --heuristic, feed fixture, assert blocks parsed

import subprocess
import json
import sys
import os

def get_binary_path():
    """Try release first, fallback to debug"""
    release_bin = os.path.join(os.getcwd(), "warp_core", "target", "release", "warp_cli")
    debug_bin = os.path.join(os.getcwd(), "warp_core", "target", "debug", "warp_cli")
    
    if os.path.exists(release_bin):
        return release_bin
    elif os.path.exists(debug_bin):
        return debug_bin
    else:
        return None

def run():
    bin_path = get_binary_path()
    if not bin_path:
        print("ERROR: warp_cli not built. Run: (cd warp_core && cargo build)")
        sys.exit(2)
    
    fix_path = os.path.join(os.path.dirname(__file__), "fixtures", "sample_session.log")
    
    proc = subprocess.Popen([bin_path, "parse-stream", "--json", "--heuristic"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        with open(fix_path, "rb") as f:
            data = f.read()
        out, err = proc.communicate(input=data, timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        print("ERROR: Process timed out")
        sys.exit(3)

    if err:
        print(f"STDERR: {err.decode(errors='ignore')}")

    if not out:
        print("ERROR: No output from warp_cli")
        sys.exit(4)

    # Parse JSON output (may be JSON lines format)
    try:
        lines = out.decode().strip().split('\n')
        arr = [json.loads(line) for line in lines if line.strip()]
    except Exception as e:
        print(f"ERROR: Failed to parse JSON output: {e}")
        sys.exit(5)

    assert isinstance(arr, list), "expected list of blocks"
    assert len(arr) >= 1, "parsed at least one block"
    print(f"✅ Integration test OK: parsed {len(arr)} blocks")

if __name__ == "__main__":
    run()
