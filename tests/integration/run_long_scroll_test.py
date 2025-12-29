#!/usr/bin/env python3
# tests/integration/run_long_scroll_test.py

import subprocess
import json
import os
import sys
import time

def get_binary_path():
    # Prefer release binary for performance
    release_bin = os.path.join(os.getcwd(), "warp_core", "target", "release", "warp_cli")
    debug_bin = os.path.join(os.getcwd(), "warp_core", "target", "debug", "warp_cli")
    if os.path.exists(release_bin):
        return release_bin
    elif os.path.exists(debug_bin):
        return debug_bin
    return None

def run():
    bin_path = get_binary_path()
    if not bin_path:
        print("ERROR: Build warp_cli first: (cd warp_core && cargo build --release)")
        sys.exit(2)

    fix_path = os.path.join(os.path.dirname(__file__), "fixtures", "long_scroll.raw")
    if not os.path.exists(fix_path):
        print("ERROR: Fixture long_scroll.raw missing. Run: python3 tooling/generate_long_scroll.py")
        sys.exit(3)

    start = time.time()
    proc = subprocess.Popen([bin_path, "parse-stream", "--json", "--heuristic"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    with open(fix_path, "rb") as f:
        data = f.read()
    try:
        # proc.stdin.write(data)
        # proc.stdin.close()
        out, err = proc.communicate(input=data, timeout=30)  # generous timeout
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        print("ERROR: Process timed out after 30s")
        sys.exit(4)

    duration = time.time() - start
    
    if err:
        print(f"STDERR: {err.decode(errors='ignore')}")

    if not out:
        print("ERROR: No output — parser may have crashed")
        sys.exit(5)

    try:
        lines = out.decode().strip().split('\n')
        arr = [json.loads(line) for line in lines if line.strip()]
    except Exception as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        sys.exit(6)

    print(f"✅ Long scroll parsed {len(arr)} blocks in {duration:.2f}s")
    if len(arr) < 100:
        print(f"WARNING: expected many blocks for long_scroll; got {len(arr)}")

if __name__ == "__main__":
    run()
