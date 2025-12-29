#!/usr/bin/env python3
# tests/integration/run_malformed_stream_test.py

import subprocess
import json
import os
import sys

def get_binary_path():
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
        print("ERROR: warp_cli binary not found. Run: (cd warp_core && cargo build)")
        sys.exit(2)

    fix_path = os.path.join(os.path.dirname(__file__), "fixtures", "corrupted_ansi.raw")
    with open(fix_path, "rb") as f:
        data = f.read()

    proc = subprocess.Popen([bin_path, "parse-stream", "--json", "--heuristic"],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        # proc.stdin.write(data)
        # proc.stdin.close()
        out, err = proc.communicate(input=data, timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    if err:
        print(f"STDERR: {err.decode(errors='ignore')}")

    if not out:
        print("ERROR: No output produced from corrupted input (expected graceful output)")
        sys.exit(3)

    try:
        lines = out.decode().strip().split('\n')
        arr = [json.loads(line) for line in lines if line.strip()]
    except Exception as e:
        print(f"ERROR: Output was not valid JSON: {e}")
        sys.exit(4)

    if not isinstance(arr, list):
        print("ERROR: Expected JSON array of blocks")
        sys.exit(5)
    
    # Parser should recover gracefully
    print(f"✅ Malformed stream test OK — parsed {len(arr)} items")

if __name__ == "__main__":
    run()
