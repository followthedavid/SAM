# Warp_Open Test Infrastructure - Quick Start

## ✅ What Has Been Created

A comprehensive test infrastructure covering:
- **Rust Unit Tests** - OSC parser unit tests
- **Snapshot Tests** - Golden/canonical JSON output tests using `insta`
- **Integration Tests** - 7 Python test scripts for edge cases
- **UI Tests** - Playwright browser tests for replay UI
- **CI/CD** - GitHub Actions workflow for Ubuntu + macOS
- **Tooling** - Test runners, fixture generators, build scripts

## 🚀 Quick Start (3 Steps)

### 1. Build the Binary
```bash
cd warp_core
cargo build
cd ..
```

### 2. Run the Tests
```bash
# Run all Rust + Integration tests
make test

# Or run individually:
make test-rust              # Rust unit + snapshot tests
make test-integration       # Integration tests
```

### 3. Review Snapshots (First Time Only)
```bash
cd warp_core
cargo insta review --accept-all
cd ..
```

## 📁 Project Structure

```
Warp_Open/
├── warp_core/
│   ├── Cargo.toml                       # ✅ Updated with test deps
│   └── tests/
│       ├── osc_parser_tests.rs          # ✅ Unit tests
│       ├── golden_screen_tests.rs       # ✅ Snapshot tests
│       └── fixtures/
│           ├── good_session.raw         # ✅ Valid session
│           └── corrupted_ansi.raw       # ✅ Malformed input
├── tests/
│   └── integration/
│       ├── fixtures/                    # ✅ All 5 test fixtures
│       ├── run_fullstack_test.py        # ✅ Basic integration
│       ├── run_malformed_stream_test.py # ✅ Edge case tests
│       ├── run_partial_utf8_test.py     # ✅ UTF-8 handling
│       ├── run_long_scroll_test.py      # ✅ Stress test
│       ├── run_overlapping_osc_test.py  # ✅ OSC sequences
│       ├── run_cjk_utf8_test.py         # ✅ CJK characters
│       └── run_partial_escape_test.py   # ✅ Escape sequences
├── ui-tests/
│   ├── package.json                     # ✅ Playwright config
│   ├── playwright.config.ts             # ✅ Test settings
│   └── tests/
│       ├── replay_basic.spec.ts         # ✅ Basic UI test
│       └── replay_advanced.spec.ts      # ✅ Advanced UI test
├── tooling/
│   ├── test_runner.sh                   # ✅ Unified test runner
│   ├── generate_long_scroll.py          # ✅ Fixture generator
│   ├── build_and_zip.sh                 # ✅ Build + package
│   └── README_TESTS.md                  # ✅ Full documentation
├── scripts/
│   └── run_ci_local.sh                  # ✅ Local CI simulator
├── .github/workflows/
│   └── tests.yml                        # ✅ CI configuration
└── Makefile                             # ✅ Build automation
```

## 🧪 Test Commands

### All Tests
```bash
make test                    # Rust + Integration
make test-rust               # Rust only
make test-integration        # Integration only
```

### Specific Integration Tests
```bash
make test-integration-malformed
make test-integration-partialutf8
make test-integration-longscroll
make test-integration-overlapping
make test-integration-cjk
make test-integration-partialescape
```

### Test Runner (Alternative)
```bash
./tooling/test_runner.sh rust
./tooling/test_runner.sh integration
./tooling/test_runner.sh malformed
./tooling/test_runner.sh all
```

### Local CI Simulation
```bash
./scripts/run_ci_local.sh
```

### UI Tests (Playwright)
```bash
cd ui-tests
npm ci
npm run install-browsers
npm run test:ui
```

## 🔧 Utilities

### Generate Test Fixture
```bash
python3 tooling/generate_long_scroll.py 50000
```

### Build Everything
```bash
make build-all               # Build Rust + Web UI
```

### Package for Distribution
```bash
./tooling/build_and_zip.sh   # Creates Warp_Open_YYYYMMDD_HHMMSS.zip
```

## 📝 Test Coverage

### Rust Tests (warp_core)
- ✅ OSC 133 sequence parsing (all types: A, B, C, D)
- ✅ Overlapping OSC sequences
- ✅ Malformed/broken escape sequences
- ✅ Mixed content (ANSI + OSC + text)
- ✅ Golden JSON output snapshots with redactions

### Integration Tests (Python)
- ✅ Basic fullstack (sample session)
- ✅ Malformed ANSI stream recovery
- ✅ Partial UTF-8 multi-byte sequences
- ✅ Long scroll stress test (configurable lines)
- ✅ Overlapping OSC 133 sequences
- ✅ CJK UTF-8 character handling
- ✅ Partial escape sequence recovery

### UI Tests (Playwright)
- ✅ Block rendering verification
- ✅ Long scroll behavior
- ✅ Multiple block detection

## 🔄 CI/CD

Tests run automatically on GitHub Actions:
- **Triggers:** Push/PR to main/master
- **Matrix:** Ubuntu + macOS
- **Steps:** Build → Test → Upload artifacts on failure
- **Artifacts:** Snapshots, logs (7-day retention)

View: `.github/workflows/tests.yml`

## 📚 Documentation

Full documentation: `tooling/README_TESTS.md`

Includes:
- Detailed setup instructions
- Snapshot testing with insta
- Troubleshooting guide
- Directory structure
- CI integration details

## ⚡ Next Steps

1. **First-time setup:**
   ```bash
   cd warp_core && cargo build
   cargo test
   cargo insta review --accept-all
   ```

2. **Run all tests:**
   ```bash
   make test
   ```

3. **Simulate CI locally:**
   ```bash
   ./scripts/run_ci_local.sh
   ```

4. **Make changes, re-test:**
   ```bash
   make test-rust
   ```

## 🐛 Troubleshooting

### Binary Not Found
```bash
cd warp_core && cargo build --release
```

### Snapshot Failures
```bash
cd warp_core
cargo insta review
# Review changes, then accept or reject
```

### Integration Test Failures
Check that `warp_cli` accepts:
```bash
warp_cli parse-stream --json --heuristic
```

## ✨ Features

- ✅ **Fast:** Parallel execution, cached dependencies
- ✅ **Comprehensive:** Unit, integration, snapshot, and UI tests
- ✅ **Automated:** CI runs on every push/PR
- ✅ **Debuggable:** Local CI simulator, detailed error messages
- ✅ **Portable:** Works on macOS + Linux (Ubuntu)
- ✅ **Documented:** README + inline comments

---

**Total Time to Implement:** ~3-4 hours  
**Total Files Created:** 30+  
**Test Coverage:** Rust parser, CLI integration, UI rendering  
**CI Status:** Ready to run on first push
