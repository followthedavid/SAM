# SAM AI Capabilities

## Hardware Constraints
- **Machine**: Mac Mini M2 (8GB RAM)
- **Available memory for models**: ~1-1.5GB after system overhead
- **No paid API keys** - fully local or browser-based

## Local Models (Ollama)

### Models Available
| Model | Size | Use Case | Performance |
|-------|------|----------|-------------|
| `tinydolphin:1.1b` | 636MB | Chat, roleplay, explanations | Good for conversation, BAD for code generation |
| `qwen2.5-coder:1.5b` | 986MB | Code generation, debugging | Excellent for all coding tasks |
| `qwen2.5-coder:3b` | 1.9GB | Complex coding | Better quality but slower to load |
| `stablelm2:1.6b` | 982MB | General chat | Alternative to tinydolphin |
| `sam-brain` | 986MB | Custom SAM responses | Fine-tuned qwen2.5-coder |

### Model Selection (orchestrator.rs)
The router now automatically detects task type and selects the best model:

**Coding Tasks** → `qwen2.5-coder:1.5b`
- Triggers: "write code", "create function", "fix this", "debug", "refactor"
- Language keywords: python, rust, javascript, etc.
- Shell commands: "linux command", "bash command"
- Temperature: 0.3 (more deterministic)
- Max tokens: 300

**Roleplay Mode** → `tinydolphin:1.1b`
- Character-based conversations
- Temperature: 0.9 (creative)
- Few-shot examples for consistent character voice

**Creative Mode** → `tinydolphin:1.1b`
- Writing, storytelling
- Temperature: 0.85

**General Chat** → `tinydolphin:1.1b`
- Default conversation
- Temperature: 0.7

## Browser Bridge (External AI Fallback)

For complex tasks that exceed local model capabilities, SAM can route to ChatGPT or Claude via browser automation. The bridge **actually extracts responses** from the AI (not placeholder text).

### Architecture
```
SAM → ai_bridge.cjs → Playwright Browser → ChatGPT/Claude → Extract Response → SAM
```

### Components
- **Main Bridge**: `ai_bridge.cjs` - Unified Playwright-based bridge that extracts actual responses
- **Queue File**: `~/.sam_chatgpt_queue.json`
- **Responses**: `~/.sam_chatgpt_responses.json`
- **Profile**: `~/.sam-ai-bridge-profile` - Persistent browser session (stay logged in)
- **Thread Manager**: `chatgpt_thread_manager.cjs` - For phone-to-terminal communication

### Usage
```bash
# Send a single prompt and get actual response
node ai_bridge.cjs send "Write hello world in Python"
node ai_bridge.cjs send "Explain quantum computing" --claude

# Run as daemon processing the queue
node ai_bridge.cjs daemon

# Check status
node ai_bridge.cjs status

# Quick test
node ai_bridge.cjs test
```

### Supported Providers
- **ChatGPT**: Opens chatgpt.com, extracts from `[data-message-author-role="assistant"]`
- **Claude**: Opens claude.ai/new, extracts from assistant messages

### How Response Extraction Works
1. Opens browser with persistent profile (stays logged in)
2. Navigates to ChatGPT/Claude
3. Counts existing messages
4. Types prompt and submits
5. Waits for streaming to stop (checks for `.result-streaming` class)
6. Extracts text from newest assistant message
7. Returns actual response content

### Rust Integration
The browser bridge integrates with the Rust backend:
```rust
// In orchestrator - auto-fallback when no API keys
use crate::scaffolding::external_ai::{call_ai_with_fallback, queue_browser_bridge};

// Queue for async processing
let task_id = queue_browser_bridge("complex prompt", "chatgpt")?;

// Or call synchronously (blocks while browser runs)
let response = call_browser_bridge_sync("prompt", "chatgpt")?;
```

## Performance Testing Results

### tinydolphin:1.1b
| Task | Result |
|------|--------|
| Hello World | FAIL (empty response) |
| Add Function | FAIL (empty response) |
| Code Explanation | PASS |
| Bug Finding | PASS |
| Shell Commands | PARTIAL |

### qwen2.5-coder:1.5b
| Task | Result |
|------|--------|
| Hello World | PASS |
| Add Function | PASS |
| Code Explanation | PASS |
| Bug Finding | PASS |
| Shell Commands | PASS |
| List Comprehension | PASS |
| Refactoring | PASS |

## Ollama Management Commands

SAM provides built-in Tauri commands for managing Ollama:

### From Frontend (Vue)
```typescript
import { invoke } from '@tauri-apps/api/tauri';

// Check Ollama status
const status = await invoke('cmd_ollama_status');
// Returns: { running: boolean, models: string[], current_model: string | null }

// Restart Ollama
const result = await invoke('cmd_restart_ollama');
// Returns: "Ollama restarted. 9 models available."

// Pre-warm a model (keeps it loaded for 10 minutes)
await invoke('cmd_warm_model', { model: 'qwen2.5-coder:1.5b' });

// Unload a model to free memory
await invoke('cmd_unload_model', { model: 'tinydolphin:1.1b' });
```

### Use Cases
- **Restart button** when Ollama becomes unresponsive
- **Status indicator** showing if AI is available
- **Model selector** with warm/unload controls
- **Memory management** - unload unused models

## Best Practices

1. **Pre-warm models** with `cmd_warm_model` to avoid cold-start latency
2. **Use few-shot prompts** for small models - they respond better to examples
3. **Route coding to qwen2.5-coder** - tinydolphin will fail silently
4. **Browser bridge for complex tasks** - OAuth implementation, architectural questions
5. **Memory management** - only one model hot at a time to stay under 8GB
6. **Restart Ollama** when requests time out repeatedly

## Mode Indicators
SAM displays the current mode in responses:
- `💻 *Code mode (qwen2.5-coder)*` - Coding task detected
- `🎭 *Roleplay mode*` - Character conversation
- `✨ *Creative mode*` - Creative writing
- `🔍 *Search mode*` - Web/code search
- `🔧 *System mode*` - System commands
- `💬 *Chat mode*` - General conversation

### Chat UI Mode Indicator
The chat panel (ChatPanel.vue) displays a colored mode badge for each assistant message:
- **Blue** (`mode-code`) - Code generation tasks
- **Yellow** (`mode-search`) - Search queries
- **Purple** (`mode-roleplay`) - Character roleplay
- **Orange** (`mode-creative`) - Creative writing
- **Gray** (`mode-chat`) - General conversation

## Character Memory Persistence

SAM remembers roleplay character conversations across sessions.

### Storage Location
- **Memory files**: `~/.sam/character_memory/<character_id>.json`
- **Active state**: `~/.sam/active_character.json`

### Data Structure
```rust
pub struct CharacterMemory {
    pub character_id: String,
    pub character_name: String,
    pub started_at: DateTime<Utc>,
    pub last_active: DateTime<Utc>,
    pub messages: Vec<CharacterMessage>,
    pub remembered_facts: Vec<String>,  // Things the character "remembers"
    pub custom_traits: Vec<String>,      // User-defined personality traits
}
```

### Tauri Commands
```typescript
// Get or create character memory
const memory = await invoke('cmd_get_character_memory', { characterId: 'char_123' });

// Add a message to history
await invoke('cmd_add_character_message', {
    characterId: 'char_123',
    role: 'user',
    content: 'Hello!'
});

// Get recent context for prompt building
const context = await invoke('cmd_get_recent_character_context', {
    characterId: 'char_123',
    maxMessages: 10
});

// Remember a fact about the conversation
await invoke('cmd_remember_character_fact', {
    characterId: 'char_123',
    fact: 'User mentioned they love hiking'
});

// Set active character (persists across app restarts)
await invoke('cmd_set_active_character', {
    characterId: 'char_123',
    characterName: 'Alex'
});

// Get active character
const active = await invoke('cmd_get_active_character');
// Returns: { active_character_id: "char_123", active_character_name: "Alex" }

// Clear active character
await invoke('cmd_clear_active_character');

// List all characters with saved memory
const characters = await invoke('cmd_list_characters_with_memory');

// Clear history but keep character
await invoke('cmd_clear_character_history', { characterId: 'char_123' });

// Delete character memory entirely
await invoke('cmd_delete_character_memory', { characterId: 'char_123' });
```

### Use Cases
- **Resume conversations** - Continue where you left off with a character
- **Build relationships** - Character remembers facts about you
- **Consistent personality** - Custom traits persist across sessions
- **Multi-character support** - Switch between characters, each with own memory
