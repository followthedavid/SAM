#!/usr/bin/env bash
# Test runner with timeout for PTY tests

set -e

echo "Running PTY tests with 15-second timeout..."

# Run test in background
cargo test --lib pty::tests::test_pty_write_input -- --nocapture &
TEST_PID=$!

# Wait for up to 15 seconds
SECONDS=0
while kill -0 $TEST_PID 2>/dev/null; do
    if [ $SECONDS -ge 15 ]; then
        echo "Test timed out after 15 seconds, killing..."
        kill -9 $TEST_PID 2>/dev/null || true
        exit 124
    fi
    sleep 0.5
done

# Check exit status
wait $TEST_PID
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Test passed!"
else
    echo "❌ Test failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
