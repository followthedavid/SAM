# Warp_Open Test Infrastructure

Comprehensive test suite for Warp_Open covering Rust unit tests, integration tests, snapshot tests, and UI tests.

## Quick Start

### Prerequisites
- Rust stable toolchain (via `rustup`)
- Python 3.9+
- Node.js 20.x
- npm

### Initial Setup

1. **Build the project:**
```bash
cd warp_core
cargo build
```

2. **Generate test fixtures:**
```bash
python3 tooling/generate_long_scroll.py 50000
```

## Running Tests

### All Tests
```bash
make test
```

### Rust Tests Only
```bash
make test-rust
# or
cd warp_core && cargo test
```

### Integration Tests

**Run basic integration test:**
```bash
make test-integration
# or
./tooling/test_runner.sh integration
```

**Run specific integration tests:**
```bash
make test-integration-malformed
make test-integration-partialutf8
make test-integration-longscroll
make test-integration-overlapping
make test-integration-cjk
make test-integration-partialescape
```

**Run all integration tests:**
```bash
./tooling/test_runner.sh all
```

### UI Tests (Playwright)

**Note:** UI tests require a dev server running at http://localhost:4000

```bash
# Install dependencies
cd ui-tests
npm ci
npm run install-browsers

# Run tests
npm run test:ui

# Run in headed mode (see browser)
npm run test:ui:headed
```

## Snapshot Testing (insta)

### First Run
On the first test run, insta will generate snapshots:
```bash
cd warp_core
cargo test
```

### Review Snapshots
```bash
cd warp_core
cargo insta review
```

### Accept All Snapshots
```bash
cd warp_core
cargo insta review --accept-all
```

## Local CI Simulation

Run the same steps as CI locally:
```bash
./scripts/run_ci_local.sh
```

## Test Fixtures

### Generate Long Scroll Fixture
```bash
python3 tooling/generate_long_scroll.py [NUM_LINES]
```
Default: 100,000 lines. For faster tests, use fewer lines (e.g., 20,000).

### Existing Fixtures
- `warp_core/tests/fixtures/good_session.raw` - Valid ANSI/OSC stream
- `warp_core/tests/fixtures/corrupted_ansi.raw` - Broken CSI sequences
- `tests/integration/fixtures/sample_session.log` - Basic session
- `tests/integration/fixtures/overlapping_osc.raw` - Overlapping OSC sequences
- `tests/integration/fixtures/cjk_utf8.raw` - CJK character test
- `tests/integration/fixtures/partial_escape.raw` - Partial escape sequences

## Troubleshooting

### Binary Not Found
If tests fail with "warp_cli binary not found":
```bash
cd warp_core
cargo build --release
```

### Wrong CLI Flags
All integration tests assume:
```bash
warp_cli parse-stream --json --heuristic
```
If your CLI uses different flags, update the test scripts in `tests/integration/`.

### Snapshot Failures
If snapshots fail due to non-deterministic data:
1. Check `warp_core/tests/golden_screen_tests.rs`
2. Add redactions for variable fields (timestamps, IDs, etc.)
3. Re-run tests and accept new snapshots

### Port Conflicts
UI tests use port 4000 by default. If blocked:
1. Change port in server command
2. Update URL in `ui-tests/tests/*.spec.ts`

## Directory Structure

```
Warp_Open/
├── warp_core/
│   ├── tests/
│   │   ├── osc_parser_tests.rs       # Unit tests
│   │   ├── golden_screen_tests.rs    # Snapshot tests
│   │   └── fixtures/                 # Rust test fixtures
│   └── Cargo.toml                    # Dev-deps: insta, assert_cmd
├── tests/
│   └── integration/
│       ├── fixtures/                 # Integration test fixtures
│       ├── run_fullstack_test.py     # Basic integration test
│       ├── run_malformed_stream_test.py
│       ├── run_partial_utf8_test.py
│       ├── run_long_scroll_test.py
│       ├── run_overlapping_osc_test.py
│       ├── run_cjk_utf8_test.py
│       └── run_partial_escape_test.py
├── ui-tests/
│   ├── tests/
│   │   ├── replay_basic.spec.ts      # Basic UI test
│   │   └── replay_advanced.spec.ts   # Advanced UI test
│   ├── playwright.config.ts
│   └── package.json
├── tooling/
│   ├── test_runner.sh                # Unified test runner
│   ├── generate_long_scroll.py       # Fixture generator
│   ├── build_and_zip.sh              # Build + package utility
│   └── README_TESTS.md               # This file
├── scripts/
│   └── run_ci_local.sh               # Local CI simulator
├── .github/workflows/
│   └── tests.yml                     # CI configuration
└── Makefile                          # Build + test automation
```

## CI Integration

Tests run automatically on push/PR via GitHub Actions:
- Runs on Ubuntu + macOS
- Caches Cargo and npm dependencies
- Uploads test artifacts on failure

View workflow: `.github/workflows/tests.yml`

## Build & Package

Build everything and create a distributable zip:
```bash
./tooling/build_and_zip.sh
```

Creates: `Warp_Open_YYYYMMDD_HHMMSS.zip`

## Additional Resources

- [insta docs](https://insta.rs/)
- [Playwright docs](https://playwright.dev/)
- [assert_cmd docs](https://docs.rs/assert_cmd/)

## Support

For issues or questions, check:
1. This README
2. Individual test file comments
3. CI logs in GitHub Actions
