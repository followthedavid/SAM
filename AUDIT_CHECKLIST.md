# Warp_Open Test Infrastructure Audit Checklist

## 1️⃣ Rust Tests Verification

### Files Created
- [ ] warp_core/tests/osc_parser_tests.rs
- [ ] warp_core/tests/golden_screen_tests.rs
- [ ] warp_core/tests/fixtures/good_session.raw
- [ ] warp_core/tests/fixtures/corrupted_ansi.raw

### Test Count Verification
```bash
cd warp_core
cargo test --lib --bins --tests 2>&1 | grep "test result"
```
**Expected:** 8 Rust tests (6 unit + 2 snapshot)
**Actual:** ___ tests

### Snapshot Redactions
- [ ] Check snapshots contain "[redacted]" for id and timestamp
```bash
grep -r "redacted" warp_core/tests/snapshots/
```

---

## 2️⃣ Python Integration Tests Verification

### Files Created (7 scripts)
- [ ] tests/integration/run_fullstack_test.py
- [ ] tests/integration/run_malformed_stream_test.py
- [ ] tests/integration/run_partial_utf8_test.py
- [ ] tests/integration/run_long_scroll_test.py
- [ ] tests/integration/run_overlapping_osc_test.py
- [ ] tests/integration/run_cjk_utf8_test.py
- [ ] tests/integration/run_partial_escape_test.py

### Fixtures Created (6 files)
- [ ] tests/integration/fixtures/sample_session.log
- [ ] tests/integration/fixtures/corrupted_ansi.raw
- [ ] tests/integration/fixtures/overlapping_osc.raw
- [ ] tests/integration/fixtures/cjk_utf8.raw
- [ ] tests/integration/fixtures/partial_escape.raw
- [ ] tests/integration/fixtures/long_scroll.raw (generated)

### Execution Check
```bash
for test in tests/integration/run_*.py; do
  python3 "$test" || echo "FAILED: $test"
done
```
**Expected:** 7 passing
**Actual:** ___ passing

---

## 3️⃣ UI Tests (Playwright) Verification

### Files Created
- [ ] ui-tests/package.json
- [ ] ui-tests/playwright.config.ts
- [ ] ui-tests/tests/replay_basic.spec.ts
- [ ] ui-tests/tests/replay_advanced.spec.ts

### Execution Check (requires dev server)
```bash
cd ui-tests
npm ci
npx playwright install --with-deps
npm run test:ui
```
**Status:** ___

---

## 4️⃣ Tooling & Automation Verification

### Files Created
- [ ] tooling/test_runner.sh (8 modes)
- [ ] tooling/generate_long_scroll.py
- [ ] tooling/build_and_zip.sh
- [ ] tooling/README_TESTS.md
- [ ] scripts/run_ci_local.sh
- [ ] Makefile

### Test Runner Modes
```bash
./tooling/test_runner.sh rust
./tooling/test_runner.sh integration
./tooling/test_runner.sh malformed
./tooling/test_runner.sh partialutf8
./tooling/test_runner.sh longscroll
./tooling/test_runner.sh overlapping
./tooling/test_runner.sh cjk
./tooling/test_runner.sh partialescape
./tooling/test_runner.sh all
```
**Expected:** All modes work
**Actual:** ___

---

## 5️⃣ CI Workflow Verification

### File Created
- [ ] .github/workflows/tests.yml

### Content Check
```bash
grep -E "(ubuntu-latest|macos-latest)" .github/workflows/tests.yml
```
**Expected:** Both OS in matrix
**Actual:** ___

---

## 6️⃣ Documentation Verification

### Files Created
- [ ] TESTING_QUICKSTART.md
- [ ] tooling/README_TESTS.md
- [ ] TEST_RESULTS.md

### Content Check
```bash
wc -l TESTING_QUICKSTART.md tooling/README_TESTS.md TEST_RESULTS.md
```
**Expected:** Non-trivial content in each
**Actual:** ___

---

## 7️⃣ Test Count Reconciliation

### Claimed Counts
- Rust tests: 20 (10 lib + 2 bin + 2 golden + 6 integration)
- Python integration: 7
- **Total claimed: 27**

### Reality Check
Run actual test suite and count:
```bash
# Count Rust tests
cd warp_core && cargo test --lib --bins --tests 2>&1 | grep -E "^test " | wc -l

# Count Python tests
ls tests/integration/run_*.py | wc -l
```

**Actual Rust tests:** ___
**Actual Python tests:** ___
**Actual total:** ___

---

## 8️⃣ Full Test Execution

### Command Sequence
```bash
# 1. Rust tests
cd warp_core && cargo test --lib --bins --tests

# 2. Snapshot review
cargo insta review

# 3. Python integration (all)
cd .. && ./tooling/test_runner.sh all

# 4. Makefile test
make test

# 5. Check for example compilation issues
cd warp_core && cargo test 2>&1 | grep -i "napi_bridge"
```

### Issues Found
- [ ] napi_bridge example has missing main function
- [ ] Test counts inflated vs reality
- [ ] Documentation files missing or incomplete
- [ ] Other: ___

---

## 9️⃣ Permissions & Executability

```bash
# Check all scripts are executable
find tooling scripts tests/integration -name "*.sh" -o -name "*.py" | xargs ls -l
```
**Expected:** All have +x bit
**Actual:** ___

---

## 🔟 Final Verdict

### Discrepancies Found
1. Test count: Claimed ___ vs Actual ___
2. Files missing: ___
3. Tests failing: ___
4. Other issues: ___

### Corrected Summary
- **Actual Rust tests:** ___
- **Actual Python tests:** ___
- **Actual total:** ___
- **Pass rate:** ___%
- **Production ready:** YES / NO

---

## Action Items
- [ ] Fix test count claims
- [ ] Verify all documentation exists
- [ ] Fix napi_bridge example issue
- [ ] Confirm CI workflow works on GitHub
- [ ] Update TEST_RESULTS.md with accurate counts
