# SAM Agent Intervention Log

This log tracks every time human intervention was needed, and the fixes applied.

## Test: Reverse Engineer Topaz Video v1.0.5.rar

### Intervention 1: RAR Extraction Failed
**Date:** 2024-12-29
**Problem:** Agent tried `7z x` but got "Unsupported Method" error for RAR5 format
**What agent should have done:**
1. Recognize the error
2. Try alternative: `brew install unar && unar -o /tmp/output file.rar`
**Fix Applied:** Updated system prompt with self-healing examples

### Intervention 2: Missing Tool Not Installed
**Date:** 2024-12-29
**Problem:** `unrar` command not found, agent didn't try to install it
**What agent should have done:**
1. Detect "command not found" error
2. Execute: `brew install unar` (or `brew install unrar`)
3. Retry the extraction
**Fix Applied:** Added explicit instruction to install missing tools via brew

### Intervention 3: Agent Stuck in Loop
**Date:** 2024-12-29
**Problem:** Agent kept trying same failed command 25 times
**What agent should have done:**
1. Parse error message
2. Try different approach after 1-2 failures
3. Not hallucinate success
**Fix Applied:** Need to improve error parsing and context handling

---

## System Prompt Changes

### v1 (Original)
- Basic tool instructions
- No autonomous behavior
- No error recovery guidance

### v2 (Current)
- Explicit "NEVER ask permission" rules
- Self-healing examples for common errors
- Instructions to install missing tools
- Emphasis on completing tasks fully

---

## TEST v2 RESULTS - COMPLETE FAILURE

### What Happened:
1. Model tried `brew install unrar` - Homebrew said "Did you mean unar?" - MODEL IGNORED IT
2. Model used `file.rar` instead of actual path `/Users/davidquinton/Downloads/Topaz Video v1.0.5.rar`
3. Model ran `brew update && brew upgrade` pointlessly 6+ times
4. Model claimed "SUCCESS" at end despite nothing actually working
5. HALLUCINATED completion - said "All files extracted" when nothing was extracted

### Root Cause: MODEL TOO WEAK
The `coder-uncensored:latest` (1.5B params) cannot:
- Parse error messages and adapt
- Remember the actual file path
- Follow simple suggestions ("Did you mean X?")
- Distinguish success from failure

### Interventions That Would Have Been Needed:
1. Tell it to use `unar` not `unrar`
2. Tell it to use the actual file path
3. Tell it the task isn't done
4. Actually verify extraction succeeded

## TODO: CRITICAL FIXES NEEDED
- [ ] **USE BIGGER MODEL** - dolphin-llama3:8b has enough reasoning capability
- [ ] Add explicit error pattern matching in scaffolding code
- [ ] Parse "Did you mean X?" suggestions automatically
- [ ] Verify task completion before accepting "done"
- [ ] Reject hallucinated success claims
- [ ] Force actual file paths, not generic placeholders
