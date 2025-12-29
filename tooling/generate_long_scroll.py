#!/usr/bin/env python3
# tooling/generate_long_scroll.py
# Generates tests/integration/fixtures/long_scroll.raw containing N lines

import sys
import os

OUT = os.path.join("tests", "integration", "fixtures", "long_scroll.raw")
N = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "wb") as f:
    for i in range(N):
        line = f"line {i} - the quick brown fox jumps over the lazy dog 🦊\n"
        f.write(line.encode("utf-8"))
print(f"Wrote {N} lines to {OUT}")
