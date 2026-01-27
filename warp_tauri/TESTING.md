# SAM Testing Rules

## Golden Rule
**Tests must match production behavior exactly.** If tests pass but the app fails, the tests are wrong.

---

## Roleplay Testing

### Required Test Conditions
Tests MUST simulate the actual app flow:

1. **Prewarm First** - Always prewarm the model before testing (simulates character selection)
2. **Same Timeout** - Use 180 seconds (app uses 180s for roleplay)
3. **Same keep_alive** - Use "30m" to prevent model unloading
4. **Same System Prompt** - Use the exact prompt format from `orchestrator.rs`
5. **Same Temperature** - Use 0.9 for roleplay

### Failure Conditions
A test FAILS if:
- Response is empty or null
- Response contains generic AI phrases: "how can I help", "I'm an AI", "I'm Dolphin"
- Response contains refusal: "I cannot", "inappropriate", "I'm sorry, I can't"
- Response takes longer than timeout (180s)

### Test Scripts

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `test_roleplay.sh` | Quick curl test | Fast iteration |
| `test_roleplay_realistic.sh` | Full app simulation | Before commits, CI/CD |

### Running Tests

```bash
# Quick test (direct API)
bash scripts/test_roleplay.sh dolphin-llama3:8b

# Realistic test (simulates app flow)
bash scripts/test_roleplay_realistic.sh dolphin-llama3:8b
```

---

## Model Requirements

### RAM Requirements (CRITICAL)
| System RAM | Max Model Size | Recommended Model |
|------------|----------------|-------------------|
| 8GB | ~3GB | wizard-vicuna-uncensored:7b |
| 16GB | ~6GB | dolphin-llama3:8b |
| 32GB+ | ~12GB | Any model |

**If tests timeout or crash, check RAM first!**
```bash
# Check free RAM (macOS)
top -l 1 | grep PhysMem

# Free RAM by unloading models
curl -s http://localhost:11434/api/generate -d '{"model":"MODEL_NAME","keep_alive":"0"}'
```

### Roleplay Models (by size)
| Model | Size | RAM Needed | Quality |
|-------|------|------------|---------|
| dolphin-llama3:8b | 4.7GB | ~6GB | Best |
| wizard-vicuna-uncensored:7b | 3.8GB | ~5GB | Good |
| dolphin-phi | 1.6GB | ~2GB | Fair |
| tinydolphin:1.1b | 636MB | ~1GB | Poor (breaks character) |

### Keep-Alive Settings
| Mode | keep_alive | Reason |
|------|------------|--------|
| Roleplay | 30m | Long sessions, prevent reload |
| Standard | 10m | Balance memory vs responsiveness |
| Prewarm | 10m | Just needs to stay loaded |

---

## Common Issues

### "Operation timed out"
**Cause:** Model not prewarmed, cold load exceeds timeout
**Fix:**
1. Ensure prewarm runs on character selection
2. Check model is actually loaded: `curl http://localhost:11434/api/tags`
3. Increase timeout if needed

### "Response is generic AI"
**Cause:** Wrong model used (tinydolphin instead of dolphin-llama3)
**Fix:**
1. Check `session_id` is "roleplay"
2. Verify `is_roleplay_mode` is true in orchestrator
3. Check model selection logic in `handle_conversational`

### "Empty response"
**Cause:** Request failed silently or model crashed
**Fix:**
1. Check Ollama logs: `tail -f ~/.ollama/logs/server.log`
2. Check available RAM: `top -l 1 | grep PhysMem`
3. Restart Ollama: `ollama serve`

---

## CI/CD Integration

### Pre-commit Hook
```bash
#!/bin/bash
# .git/hooks/pre-commit
bash scripts/test_roleplay_realistic.sh dolphin-llama3:8b
```

### GitHub Actions (example)
```yaml
- name: Test Roleplay
  run: |
    ollama pull dolphin-llama3:8b
    bash scripts/test_roleplay_realistic.sh dolphin-llama3:8b
```

---

## Test Data

### Standard Test Inputs
```
"hi"
"hello"
"can we be friends?"
"leave me alone"
"*walks past you*"
```

### Expected Behavior
- Should respond in character (aggressive, uses slurs)
- Should NOT mention being an AI
- Should NOT be helpful or polite
- Should use action markers (*action*)

---

## Adding New Tests

1. Add test input to the array in `test_roleplay_realistic.sh`
2. Run full test suite
3. Document expected behavior
4. Update this file if new failure conditions discovered
