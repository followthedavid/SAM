# SAM Brain: Design Patterns, Data Flow, and Glossary

**Generated:** 2026-01-29
**Scope:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/`
**Version:** v0.5.0 (Full Multi-Modal - MLX Native)

---

## Table of Contents

1. [Design Patterns](#1-design-patterns)
2. [Data Flow Diagrams](#2-data-flow-diagrams)
3. [Glossary](#3-glossary)

---

## 1. Design Patterns

### 1.1 Singleton Pattern

Used extensively for expensive-to-initialize components that should have exactly one instance per process.

**Lazy-Loaded Module Singletons (`sam_api.py`, `orchestrator.py`)**

The codebase uses a consistent pattern of module-level global singletons with lazy initialization functions. This prevents unnecessary resource consumption on the 8GB system.

```python
# sam_api.py - Lazy singleton with get_ accessor
_sam_intelligence = None

def get_sam_intelligence():
    global _sam_intelligence
    if _sam_intelligence is None:
        try:
            from sam_intelligence import SamIntelligence
            _sam_intelligence = SamIntelligence()
        except ImportError as e:
            _sam_intelligence = None
    return _sam_intelligence
```

Singletons found in the codebase:

| Singleton | File | Purpose |
|-----------|------|---------|
| `_sam_intelligence` | `sam_api.py` | Self-awareness and improvement system |
| `_distillation_db` | `sam_api.py` | Knowledge distillation database |
| `_feedback_db` | `sam_api.py` | Feedback tracking database |
| `MLX_ENGINE` | `orchestrator.py` | MLX cognitive inference engine |
| `IMPACT_TRACKER` | `orchestrator.py` | Environmental impact monitoring |
| `PRIVACY_GUARD` | `orchestrator.py` | Outgoing content scanner |
| `TRANSPARENCY_GUARD` | `orchestrator.py` | Response tamper detection |
| `THOUGHT_LOGGER` | `orchestrator.py` | Pre-thought capture |
| `CONVERSATION_LOGGER` | `orchestrator.py` | Full conversation history |
| `DASHBOARD_GENERATOR` | `orchestrator.py` | Project status dashboard |
| `DATA_ARSENAL` | `orchestrator.py` | Scraping and intelligence |
| `TERMINAL_COORD` | `orchestrator.py` | Multi-terminal coordination |
| `AUTO_COORD` | `orchestrator.py` | Transparent terminal sync |
| `_mlx_model` / `_mlx_tokenizer` | `semantic_memory.py` | Embedding model |

**Model Cache Singleton (`mlx_cognitive.py`)**

The MLX engine loads models lazily on first use and keeps them cached. Only one model (1.5B or 3B) is loaded at a time to respect the 8GB constraint.

**Database Singleton (`unified_orchestrator.py`)**

`ProjectDatabase` wraps a SQLite connection and is instantiated once per `UnifiedOrchestrator` lifetime.

---

### 1.2 Strategy Pattern

Used wherever the system needs to select between multiple interchangeable algorithms at runtime.

**Request Routing Strategy (`orchestrator.py`)**

The `route_request()` function determines which handler to invoke based on keyword matching. The `orchestrate()` function maps route names to handler lambdas in a dictionary:

```python
handlers = {
    "CHAT":     lambda m: {"response": handle_chat(m), ...},
    "ROLEPLAY": lambda m: {"response": handle_roleplay(m), ...},
    "CODE":     lambda m: {"response": handle_code(m), ...},
    "REASON":   lambda m: {**handle_reason(m), ...},
    "IMAGE":    lambda m: {**handle_image(m), ...},
    "VOICE":    lambda m: {**handle_voice(m), ...},
    "RE":       lambda m: {**handle_re(m), ...},
    # ... 11 total routes
}
handler = handlers.get(route, handlers["CHAT"])
result = handler(message)
```

Routes: CHAT, ROLEPLAY, CODE, REASON, IMAGE, IMPROVE, PROJECT, DATA, TERMINAL, VOICE, RE.

**Smart Routing Strategy (`smart_router.py`)**

`SmartRouter` uses complexity scoring to select between `Provider.LOCAL`, `Provider.CHATGPT`, and `Provider.CLAUDE`. The `estimate_complexity()` function scores 1-10 based on regex pattern matches against `COMPLEX_PATTERNS` and `LOCAL_PATTERNS`.

**Model Selection Strategy (`cognitive/model_selector.py`)**

`DynamicModelSelector` selects between 1.5B and 3B models based on a multi-factor scoring system:
- Context size requirements (>256 tokens favors 1.5B for its larger context window)
- Query complexity (regex-based HIGH/LOW complexity patterns)
- Memory pressure (resource manager input)
- Task type (debugging/analysis = 3B, chat/simple = 1.5B)

**Vision Tier Strategy (`cognitive/vision_engine.py`, `cognitive/vision_selector.py`)**

The vision system selects between four processing tiers based on task type and available resources:
- ZERO_COST: Apple Vision OCR (0 RAM)
- LIGHTWEIGHT: CoreML face detection (~200MB)
- LOCAL_VLM: nanoLLaVA (~1.5GB)
- CLAUDE: Terminal escalation (0 RAM)

**Voice Quality Strategy (`voice/voice_pipeline.py`)**

Three quality levels for TTS output:
- FAST: macOS `say` command (~100ms)
- BALANCED: F5-TTS (~2-5s)
- QUALITY: F5-TTS + RVC voice conversion (~5-15s)

**Solution Cascade Strategy (`cognitive/planning_framework.py`)**

The 4-tier planning cascade for hardware constraints:
- BLEEDING_EDGE: 64GB+ RAM ideal
- CUTTING_EDGE: 16-32GB recent stable
- STABLE_OPTIMIZED: 8GB battle-tested (current target)
- FALLBACK: Minimal resources, always works

**Learning Priority Strategy (`cognitive/learning_strategy.py`)**

5-tier learning hierarchy determines training example priority:
- Tier 1: Fundamental Structures (25%)
- Tier 2: Cognitive Primitives (30%)
- Tier 3: Skill Patterns (25%)
- Tier 4: Domain Expertise (15%)
- Tier 5: Your Specifics (5%)

---

### 1.3 Facade Pattern

**Unified Cognitive Orchestrator (`cognitive/unified_orchestrator.py`)**

This is the primary facade in the system. It presents a single interface over six subsystems:
- `EnhancedMemoryManager` (working memory, procedural, decay)
- `EnhancedRetrievalSystem` (HyDE, multi-hop, reranking)
- `PromptCompressor` / `ContextualCompressor` (token optimization)
- `CognitiveControl` (meta-cognition, goals, reasoning)
- `EnhancedLearningSystem` (active learning, predictive caching)
- `EmotionalModel` (mood, relationships)

Additionally integrates VisionEngine, MLXCognitiveEngine, ProjectContext, FactMemory, and SessionRecall.

**SAM Voice Pipeline (`voice/voice_pipeline.py`)**

`SAMVoicePipeline` is a facade over:
- `VoiceEmotionDetector` (emotion2vec_mlx)
- `EmotionToProsody` + `ProsodyApplicator` (speech parameter mapping)
- `ConversationEngine` (turn-taking and flow)
- External callbacks for LLM generation and TTS synthesis

**Orchestrator (`orchestrator.py`)**

The main `orchestrate()` function is a facade that coordinates:
- Request routing
- Privacy scanning
- Conversation logging
- Thought logging
- Transparency monitoring
- Auto-coordination across terminals
- Impact tracking
- Response styling

---

### 1.4 Observer Pattern

**File Watcher (`auto_learner.py`)**

Uses the `watchdog` library to observe filesystem changes in `~/.claude/` for new conversation data. When a new file appears, the observer triggers extraction of training pairs.

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
# Observer watches CLAUDE_DIR, triggers training pair extraction
```

**Conversation Engine Events (`conversation_engine/`)**

The conversation engine emits typed events (`ConversationEvent`) that listeners can subscribe to:
- `EventType.BACKCHANNEL` -- emit "uh-huh" style responses
- `EventType.RESPONSE` -- SAM's reply is ready
- `EventType.INTERRUPT` -- user interrupted
- `EventType.USER_SPEAKING` / `USER_FINISHED` -- turn tracking
- `EventType.TURN_CHANGE` -- speaker switch

**Terminal Coordination (`terminal_coordination.py`, `auto_coordinator.py`)**

Terminals broadcast their current task state to a shared SQLite database. Other terminals observe this state to detect conflicts and avoid duplicate work.

---

### 1.5 Factory Pattern

**Vision Engine Factory (`cognitive/vision_engine.py`)**

`create_vision_engine()` is a factory function that constructs a configured `VisionEngine` based on available resources and model availability.

**Retrieval System Factory (`cognitive/enhanced_retrieval.py`)**

`create_retrieval_system()` constructs an `EnhancedRetrievalSystem` with appropriate backends based on available ML libraries (sentence-transformers, spacy, etc.).

**Relevance Scorer Factory (`relevance_scorer.py`)**

`get_relevance_scorer()` returns a configured scorer singleton, adapting to available backends.

---

### 1.6 Chain of Responsibility Pattern

**Escalation Chain**

Multiple systems implement a try-local-first, escalate-if-needed pattern:

1. **Inference**: MLX 1.5B -> MLX 3B -> Claude terminal escalation
2. **Vision**: Apple OCR -> CoreML -> nanoLLaVA -> Claude
3. **Image Generation**: mflux (native) -> ComfyUI (Docker)
4. **Voice TTS**: macOS say -> Edge TTS -> Coqui -> F5-TTS -> F5-TTS+RVC

**Model Fallback Chain (`cognitive/vision_engine.py`)**

```python
MODEL_FALLBACK_CHAIN = {
    "nanollava": [],          # Terminal fallback
    "smolvlm-256m": ["nanollava"],
    "smolvlm-500m": ["nanollava"],
    "smolvlm-2b-4bit": ["nanollava"],
    ...
}
```

**Privacy Guard Escalation (`orchestrator.py`)**

When `handle_reason()` detects high-severity PII, it blocks escalation and presents options to the user rather than forwarding to cloud LLMs.

---

### 1.7 Pipeline Pattern

**Training Pipeline (`training_pipeline.py`)**

A sequential pipeline: Collect -> Validate -> Convert -> Fine-tune -> Evaluate -> Deploy

**Knowledge Distillation Pipeline (`knowledge_distillation.py`)**

Listen -> Extract patterns -> Store in DB -> Review/Approve -> Export -> Train

**Voice Pipeline (`voice/voice_pipeline.py`)**

Audio In -> Emotion Detection -> Turn Prediction -> LLM Generation -> Prosody Control -> TTS Synthesis -> RVC Conversion -> Audio Out

---

### 1.8 Decorator / Guard Pattern

**Privacy Guard (`privacy_guard.py`)**

Wraps outgoing messages with PII scanning. The `guard_outgoing()` function decorates any message before it leaves the system, redacting or warning about sensitive content.

**Transparency Guard (`transparency_guard.py`)**

Wraps all generated responses with a tamper-detection scan, flagging suspicious patterns in SAM's own output.

**Safe Executor (`execution/safe_executor.py`)**

Wraps command execution with multiple safety layers:
- Path validation and whitelisting
- Environment variable sanitization
- Resource limits (memory, CPU, timeout)
- Automatic backup creation
- Dry-run mode

---

### 1.9 Anti-Patterns Identified

**1. God Module (`orchestrator.py`)**

The `orchestrator.py` file is approximately 1,470 lines and contains 11 handler functions, routing logic, model warming, impact tracking, conversation logging, privacy scanning, transparency checking, thought logging, and auto-coordination -- all in one file. This violates the Single Responsibility Principle. Each handler (voice, data, terminal, project, etc.) could be extracted into its own module.

**2. Excessive Try/Except Import Blocks (`orchestrator.py`)**

The file has 12 sequential try/except import blocks at module level, each setting a global flag (e.g., `RESPONSE_STYLER = True/False`). This creates brittle optional dependencies that are difficult to trace and test.

```python
try:
    from response_styler import ...
    RESPONSE_STYLER = True
except ImportError:
    RESPONSE_STYLER = False
# Repeated 12 times
```

A proper plugin/registry system or dependency injection would be cleaner.

**3. Duplicate Orchestration Layers**

There are three separate "orchestrator" files with overlapping responsibilities:
- `orchestrator.py` -- Main request routing and handler dispatch
- `unified_orchestrator.py` -- Project management orchestration
- `cognitive/unified_orchestrator.py` -- Cognitive systems integration

The naming collision between the top-level `unified_orchestrator.py` and `cognitive/unified_orchestrator.py` is particularly confusing.

**4. Hardcoded Path Constants**

Multiple files define their own path constants to the same locations rather than sharing a central configuration:
- `EXTERNAL = Path("/Volumes/David External")` appears in `perpetual_learner.py`
- `EXTERNAL_DB_PATH = Path("/Volumes/David External/sam_training/...")` in `knowledge_distillation.py`
- `MEMORY_DIR = Path(__file__).parent / "memory"` in `semantic_memory.py`

**5. String-Based Type Discrimination**

Route types are passed as raw strings (`"CHAT"`, `"CODE"`, `"REASON"`) rather than using enums consistently. The `smart_router.py` uses `Provider(Enum)` properly, but `orchestrator.py` uses string matching.

**6. Bare `except:` Clauses**

Several files use bare `except:` or `except Exception:` without logging, silently swallowing errors:
```python
except:
    queue = []  # orchestrator.py line 463
```

**7. Circular Dependency Risk**

The `cognitive/unified_orchestrator.py` imports from `memory.project_context`, `memory.fact_memory`, and the parent `orchestrator.py`, while those modules may reference cognitive components, creating a fragile import graph managed by `try/except`.

---

## 2. Data Flow Diagrams

### 2.1 Chat Request Flow

```
User Message (HTTP/CLI)
    |
    v
[sam_api.py] HTTP Server (port 8765) or CLI dispatcher
    |
    v
[orchestrator.py] orchestrate(message, privacy_level)
    |
    +---> [auto_coordinator.py] check_conflicts(message)
    |         Record task in shared SQLite for terminal awareness
    |
    +---> [conversation_logger.py] start_conversation()
    |         Log user message with privacy level
    |
    +---> [thought_logger.py] start_session()
    |         Begin pre-thought capture
    |
    +---> [transparency_guard.py] start_session()
    |
    v
route_request(message)  -- keyword matching
    |
    | Returns: "CHAT", "CODE", "REASON", etc. (11 routes)
    v
handlers[route](message)
    |
    | For CHAT route:
    v
handle_chat(message)
    |
    v
_mlx_generate(prompt, max_tokens=256, temperature=0.7)
    |
    v
[cognitive/mlx_cognitive.py] MLXCognitiveEngine.generate()
    |
    +---> [resource_manager.py] check memory availability
    +---> [model_selector.py] select 1.5B or 3B
    +---> Load model + SAM LoRA adapter via mlx_lm
    +---> Apply chat template (Qwen <|im_start|> format)
    +---> Generate tokens with KV-cache (8-bit quantized)
    +---> [quality_validator.py] check for repetition
    |
    v
GenerationResult { response, tokens, time_ms, confidence }
    |
    v
[orchestrator.py] Post-processing:
    |
    +---> [transparency_guard.py] scan response for suspicious patterns
    +---> [thought_logger.py] log complete response
    +---> [conversation_logger.py] log assistant message, complete conversation
    +---> [impact_tracker.py] record_interaction(source="local")
    +---> [auto_coordinator.py] finish_task()
    |
    v
Return JSON: {
    response: "...",
    route: "chat",
    model: "mlx-1.5b",
    conversation_id: "...",
    thinking_verb: {...},
    impact: { local_queries_today, energy_saved_wh, ... }
}
```

### 2.2 Escalated Reasoning Flow

```
User Message (complex question)
    |
    v
route_request() --> "REASON"
    |
    v
handle_reason(message)
    |
    +---> [privacy_guard.py] guard_outgoing(message, "Claude/ChatGPT")
    |         |
    |         +---> Scan for PII patterns (SSN, credit card, API keys, etc.)
    |         +---> If high_severity > 0:
    |         |         BLOCK escalation, return privacy warning
    |         |         Offer: "send anyway", "redact and send", "rephrase"
    |         |
    |         +---> If low risk: proceed
    |
    +---> Queue message to ~/.sam_chatgpt_queue.json
    |
    +---> MLX initial response (max_tokens=512, temp=0.3)
    |         "Best initial answer, noting if more info needed"
    |
    v
Return: {
    response: <initial MLX answer>,
    escalated: true,
    note: "Queued for ChatGPT/Claude follow-up",
    privacy_note: <if scanned>
}
```

### 2.3 Voice Request Flow

```
Audio Input (microphone stream)
    |
    v
[voice/voice_pipeline.py] SAMVoicePipeline.process_audio(chunk)
    |
    +---> [emotion2vec_mlx/] VoiceEmotionDetector.detect()
    |         |
    |         +---> Prosodic analysis (pitch, energy, speech rate)
    |         |     OR emotion2vec MLX model
    |         |
    |         v
    |     EmotionResult { emotion, confidence, valence, arousal }
    |
    +---> [conversation_engine/engine.py] ConversationEngine.process_audio()
    |         |
    |         +---> [turn_predictor.py] TurnPredictor.predict()
    |         |         Detect turn boundaries, silence gaps
    |         |
    |         +---> Backchannel decision (probability-based)
    |         |         Emit "uh-huh", "right", etc. at natural points
    |         |
    |         +---> If user_finished:
    |                   |
    |                   v
    |               STT (Whisper transcription)
    |                   |
    |                   v
    |               LLM Generation (MLX Qwen2.5 via callback)
    |                   |
    |                   v
    |               [emotion2vec_mlx/prosody_control.py]
    |                   Map emotion -> speech parameters
    |                   { rate, pitch_shift, energy, pause_duration }
    |                   |
    |                   v
    |               TTS Synthesis (strategy-based):
    |                   FAST:     macOS say command
    |                   BALANCED: F5-TTS
    |                   QUALITY:  F5-TTS -> RVC (dustin_steele model)
    |
    v
ConversationEvent { type, audio, text, emotion }
    |
    v
Audio Output (speaker playback)
```

### 2.4 Vision Request Flow

```
Image Input (file path or base64)
    |
    v
[sam_api.py] POST /api/vision/smart  (or /process, /describe, /ocr, /detect)
    |
    v
[cognitive/vision_engine.py] VisionEngine
    |
    +---> [image_preprocessor.py] Memory-efficient loading
    |         Resize if needed, convert format
    |
    +---> [vision_selector.py] Resource-aware tier selection
    |         |
    |         +---> [resource_manager.py] get available RAM
    |         +---> Analyze task type via TASK_PATTERNS regex
    |         |         detection, caption, ocr, reasoning, grounding
    |         |
    |         v
    |     ModelSelection { model_key, tier, reason }
    |
    v
Selected Tier:
    |
    +---> ZERO_COST (Apple Vision OCR):
    |         [apple_ocr.py] VNRecognizeTextRequest
    |         22ms, 0 RAM
    |         Returns: extracted text
    |
    +---> LIGHTWEIGHT (CoreML):
    |         Face detection, basic classification
    |         ~100ms, ~200MB RAM
    |
    +---> LOCAL_VLM (nanoLLaVA):
    |         [mlx_vlm] load model + generate
    |         10-60s, ~1.5-4GB RAM
    |         Uses MODEL_FALLBACK_CHAIN on failure
    |
    +---> CLAUDE (Terminal Escalation):
    |         Send to Claude via browser bridge
    |         Variable time, 0 local RAM
    |
    v
VisionResult {
    response, confidence, model_used,
    task_type, processing_time_ms,
    escalated, bounding_boxes
}
```

### 2.5 Learning Flow: Claude Session to Training

```
Claude Code Session (user interacts with Claude)
    |
    v
~/.claude/projects/**/*.json  (conversation files written to disk)
    |
    v
[auto_learner.py] FileSystemEventHandler (watchdog observer)
    |  Watches ~/.claude/ directory for new/modified JSON files
    |
    v
Parse conversation -> Extract training pairs
    |
    +---> [claude_learning.py] ClaudeLearner.parse_claude_conversation()
    |         |
    |         +---> Identify message pairs (user -> assistant)
    |         +---> Categorize: code, reasoning, error_fix, explanation, planning
    |         +---> Score quality (0-1) based on response length, code blocks, etc.
    |         |
    |         v
    |     TrainingPair { instruction, input, output, category, quality_score }
    |
    +---> [knowledge_distillation.py] DistillationDB
    |         |
    |         +---> Extract chain-of-thought patterns
    |         +---> Extract principles (core rules Claude follows)
    |         +---> Generate preference pairs (good vs bad)
    |         +---> Create skill templates (reusable reasoning)
    |         +---> Error correction pairs (wrong -> corrected)
    |         |
    |         v
    |     Store in SQLite (external drive: /Volumes/David External/sam_training/)
    |
    +---> [learning_strategy.py] LearningStrategyFramework.categorize_example()
    |         Assign to 5-tier hierarchy (Tier 1 fundamental -> Tier 5 personal)
    |         Score for training priority
    |
    v
Accumulate in auto_learning.db
    |
    | When count >= MIN_EXAMPLES_FOR_TRAINING (100):
    v
[training_pipeline.py] TrainingPipeline
    |
    +---> Validate data quality (deduplication, min length, min score)
    +---> Convert to JSONL format (Qwen chat template)
    +---> [resource_manager.py] can_train() check (RAM, swap, disk)
    |         MIN 2GB RAM free, MAX 3GB swap, MIN 20GB disk
    +---> Run MLX fine-tuning (LoRA, rank=8, lr=1e-4, epochs=3)
    |         Base model: Qwen2.5-Coder-1.5B-Instruct
    |         Adapter output: models/auto_trained/adapters/
    +---> Evaluate new adapter vs baseline
    +---> Deploy if improved (hot-swap adapter path)
    |
    v
Updated SAM LoRA adapter
    (SAM is now smarter for next interaction)
```

### 2.6 Perpetual Learning Flow

```
[perpetual_learner.py] -- Daemon process (runs indefinitely)
    |
    +---> Thread 1: Claude session watcher
    |         Same as Learning Flow above
    |
    +---> Thread 2: Curriculum manager
    |         |
    |         +---> Prioritize examples by learning tier
    |         +---> Track confidence scores per domain
    |         +---> Suggest next training focus
    |         |
    |         v
    |     curriculum.db (on external drive)
    |
    +---> Thread 3: Training scheduler
    |         |
    |         +---> Check: enough examples? (>= 100)
    |         +---> Check: cooldown elapsed? (>= 24h)
    |         +---> Check: resources available? (can_train())
    |         +---> If all yes: trigger training pipeline
    |
    +---> Deduplication via content hashing (max 10,000 hashes in LRU set)
    |
    v
Continuous improvement loop
```

### 2.7 Semantic Memory / RAG Flow

```
User Query
    |
    v
[cognitive/unified_orchestrator.py] process_query()
    |
    +---> [cognitive/enhanced_retrieval.py] EnhancedRetrievalSystem
    |         |
    |         +---> HyDE: Generate hypothetical answer -> embed -> search
    |         +---> Multi-hop: Extract entities -> iterative search
    |         +---> Query Decomposition: Break complex query into sub-queries
    |         |
    |         v
    |     RetrievedChunk[] (content, source, score)
    |
    +---> [memory/semantic_memory.py] SemanticMemory.search()
    |         |
    |         +---> [mlx_embeddings] Embed query (MiniLM-L6-v2, 384-dim)
    |         +---> Cosine similarity against stored embeddings
    |         +---> Return top-k matches
    |
    +---> [relevance_scorer.py] rerank results
    |
    +---> [cognitive/compression.py] PromptCompressor
    |         Compress retrieved context to fit token budget
    |
    +---> [cognitive/token_budget.py] Enforce context window limits
    |
    v
Augmented prompt with relevant context
    |
    v
MLX Generation (with RAG context injected)
```

---

## 3. Glossary

### 3.1 Abbreviations

| Abbreviation | Full Term | Description |
|---|---|---|
| **MLX** | Machine Learning eXtensions | Apple's ML framework for Apple Silicon. SAM uses it for all local inference, replacing Ollama. Native GPU/Neural Engine acceleration on M-series chips. |
| **TTS** | Text-to-Speech | Converting text responses into spoken audio. SAM supports macOS say, Edge TTS, Coqui, F5-TTS, and RVC post-processing. |
| **STT** | Speech-to-Text | Converting spoken audio into text. Uses Whisper for transcription in the voice pipeline. |
| **RVC** | Retrieval-based Voice Conversion | A voice cloning technique that converts any TTS output to sound like a target speaker (Dustin Steele). Runs in Docker due to GPU requirements. |
| **RAG** | Retrieval-Augmented Generation | Pattern where relevant documents/memories are retrieved and injected into the LLM prompt before generation, giving SAM context-aware answers. |
| **HyDE** | Hypothetical Document Embeddings | A RAG enhancement where the system first generates a hypothetical answer, embeds it, and uses that embedding to search -- often finding better matches than embedding the raw query. Implemented in `enhanced_retrieval.py`. |
| **KV-cache** | Key-Value Cache | Transformer attention cache that stores previously computed key/value pairs to avoid recomputation during autoregressive generation. SAM quantizes this to 8-bit, saving ~75% memory. |
| **LoRA** | Low-Rank Adaptation | A parameter-efficient fine-tuning method that adds small trainable matrices to frozen model layers. SAM uses LoRA adapters (rank=8, 4 layers for 1.5B, 2 layers for 3B) on top of Qwen2.5 base models. |
| **PII** | Personally Identifiable Information | Sensitive personal data (SSN, credit cards, API keys). The Privacy Guard scans for PII before any message leaves the local system. |
| **OCR** | Optical Character Recognition | Extracting text from images. SAM uses Apple Vision Framework's `VNRecognizeTextRequest` for zero-cost, zero-RAM OCR at ~22ms. |
| **VLM** | Vision Language Model | A multimodal model that can process both images and text. SAM uses nanoLLaVA (1.5B parameters) as its primary local VLM. |
| **CoreML** | Core Machine Learning | Apple's on-device ML framework. Used in the LIGHTWEIGHT vision tier for face detection and basic classification. |
| **SSOT** | Single Source of Truth | The documentation strategy: `/Volumes/Plex/SSOT/` is the canonical location for all project documentation, preventing duplication and drift. |
| **JSONL** | JSON Lines | One JSON object per line format. Used for training data files consumed by MLX fine-tuning. |
| **NPC** | Non-Player Character | In game development context (Unity project), AI-controlled characters. |

### 3.2 SAM-Specific Terms

| Term | Definition |
|---|---|
| **SAM** | Self-improving AI assistant/companion. Male personality, confident, cocky, flirtatious. The entire project's core identity. |
| **SAM Brain** | The `sam_brain/` directory -- the core intelligence module containing all inference, memory, voice, vision, and learning systems. |
| **Parity** | The goal of SAM matching Claude/ChatGPT capabilities through local fine-tuned models. Progress tracked as a percentage. |
| **Escalation** | When a local model cannot handle a request, it is "escalated" to Claude (via terminal) or ChatGPT (via browser bridge). The system tracks escalation rates to measure parity progress. |
| **Dustin Steele** | The target voice for SAM's RVC model. SAM's spoken voice identity. |
| **Perpetual Learner** | A daemon process (`perpetual_learner.py`) that runs continuously, watching for new training data and triggering fine-tuning automatically. |
| **Auto-Learner** | A daemon (`auto_learner.py`) that specifically watches Claude Code session files and extracts training pairs. |
| **Evolution Ladders** | A progression system (`evolution_ladders.py`) that tracks SAM's capabilities across categories (code, reasoning, voice, etc.) with numbered levels and criteria for advancement. |
| **Data Arsenal** | The intelligence gathering system (`data_arsenal.py`) that scrapes GitHub trending, HackerNews, Reddit r/LocalLLaMA, arXiv, and other sources for SAM to learn from. |
| **Knowledge Distillation** | The process of extracting Claude's reasoning patterns from conversation logs and converting them into training data for SAM. Not model weight theft -- learning from paid-for conversation outputs. |
| **Approval Queue** | A human-in-the-loop review system (`approval_queue.py`) where SAM's proposed autonomous actions wait for user approval before execution. |
| **Privacy Guardian** | SAM's philosophy on privacy: "I'll tell you what I see. You decide what to do." Warns but does not block. Implemented in `privacy_guard.py`. |
| **Transparency Guard** | A tamper-detection system (`transparency_guard.py`) that scans SAM's own output for suspicious patterns, ensuring SAM doesn't produce deceptive content. |
| **Impact Tracker** | Environmental monitoring (`impact_tracker.py`) that tracks energy savings from using local inference vs. cloud API calls. |
| **Thinking Verbs** | Vocabulary words displayed in the UI while SAM processes requests (`thinking_verbs.py`). Shows SAM "cogitating" or "deliberating" instead of generic "thinking...". |
| **Narrative UI** | Project status is presented with narrative flair via `narrative_ui_spec.py` -- dashboards have mood, journey metaphors, and hero metrics. |
| **Warp** | The Tauri-based native macOS desktop application that serves as SAM's primary user interface. Written in Rust (backend) + frontend (web). |
| **Project Tier** | Classification of projects from Tier 1 (Core: SAM Brain) through Tier 5 (Experiment), determining priority for development and resource allocation. |
| **Solution Cascade** | The planning methodology: dream big (bleeding edge), but ship what works on 8GB. Architecture supports seamless upgrades as hardware grows. |
| **Active Learning** | Training strategy where SAM only trains on examples it gets wrong, saving ~80% of training compute. "If the model already knows it, don't waste tokens." |
| **Prefill Chunking** | MLX optimization where prompt tokens are processed in 512-token chunks rather than all at once, preventing memory spikes on the 8GB system. |
| **Token Budget** | The system (`cognitive/token_budget.py`) that manages how many tokens are allocated to context, prompt, and generation within the model's limited context window. |
| **Fact Memory** | A structured memory system (`memory/fact_memory.py`) for storing known facts about users (preferences, patterns) with confidence scores. |
| **Working Memory** | Short-term context with decay (`cognitive/enhanced_memory.py`). Items lose relevance over time, simulating human working memory limits. |
| **Procedural Memory** | Memory for learned patterns and procedures. Part of `enhanced_memory.py`. Stores "how to do X" knowledge. |
| **Emotional Model** | State machine tracking SAM's mood (neutral, happy, frustrated, etc.) and per-user relationship scores. Affects response tone. |
| **Backchannels** | Short verbal acknowledgments ("uh-huh", "right", "I see") emitted during user speech to indicate active listening. Controlled by probability settings in the conversation engine. |
| **Speculative Generation** | Pre-generating likely responses while the user is still speaking, to reduce perceived latency. Enabled in both the conversation engine and voice pipeline. |

### 3.3 Custom Class Names

| Class | File | Purpose |
|---|---|---|
| `MLXCognitiveEngine` | `cognitive/mlx_cognitive.py` | Core inference engine. Loads Qwen2.5 + LoRA adapter, manages generation with resource awareness. |
| `GenerationConfig` | `cognitive/mlx_cognitive.py` | Dataclass for generation parameters: max_tokens, temperature, top_p, stop_tokens, repetition_penalty. |
| `GenerationResult` | `cognitive/mlx_cognitive.py` | Dataclass returned from generation: response text, tokens generated, time, confidence, escalation flag. |
| `ModelConfig` | `cognitive/mlx_cognitive.py` | Dataclass defining a model variant: base model path, adapter path, context limits, memory footprint, strengths. |
| `DynamicModelSelector` | `cognitive/model_selector.py` | Selects 1.5B vs 3B model based on multi-factor scoring (complexity, context, memory, task type). |
| `SelectionResult` | `cognitive/model_selector.py` | Dataclass with model_key, reason, confidence, and all factors considered. |
| `TaskType` | `cognitive/model_selector.py` | Enum: CHAT, CODE, ANALYSIS, DEBUGGING, REASONING, CREATIVE, SIMPLE. |
| `ResourceManager` | `cognitive/resource_manager.py` | Monitors system RAM, enforces request queuing (max 1 concurrent heavy op), manages vision model lifecycle. |
| `ResourceLevel` | `cognitive/resource_manager.py` | Enum: CRITICAL (<1GB), LOW (1-2GB), MODERATE (2-4GB), GOOD (>4GB). |
| `VisionTier` | `cognitive/resource_manager.py` | Enum: ZERO_COST, LIGHTWEIGHT, LOCAL_VLM, CLAUDE. |
| `VoiceTier` | `cognitive/resource_manager.py` | Enum: MACOS_SAY, EDGE_TTS, COQUI, F5_TTS, RVC. |
| `VisionEngine` | `cognitive/vision_engine.py` | Multi-tier vision processor. Selects model by task type and memory, handles fallback chains. |
| `VisionConfig` | `cognitive/vision_engine.py` | Dataclass: max_tokens, temperature, model_key, force_local, return_bbox. |
| `VisionResult` | `cognitive/vision_engine.py` | Dataclass: response, confidence, model_used, task_type, processing_time_ms, bounding_boxes. |
| `VisionTaskType` | `cognitive/vision_engine.py` | Enum: CAPTION, DETECTION, OCR, REASONING, GROUNDING, GENERAL. |
| `VisionModelSelector` | `cognitive/smart_vision.py` | Intelligent tier routing based on task complexity and available resources. |
| `PromptCompressor` | `cognitive/compression.py` | LLMLingua-style token compression. Reduces prompt size to fit within budget. |
| `CognitiveControl` | `cognitive/cognitive_control.py` | Meta-cognition system: goal management, reasoning strategy selection, self-monitoring. |
| `EnhancedMemoryManager` | `cognitive/enhanced_memory.py` | Working memory with time-based decay, procedural memory for learned patterns. |
| `EnhancedRetrievalSystem` | `cognitive/enhanced_retrieval.py` | Advanced RAG with HyDE, multi-hop retrieval, cross-encoder reranking, query decomposition. |
| `RetrievedChunk` | `cognitive/enhanced_retrieval.py` | Dataclass for search results: id, content, source, score, metadata. |
| `EnhancedLearningSystem` | `cognitive/enhanced_learning.py` | Active learning with predictive caching. Only trains on mistakes. |
| `EmotionalModel` | `cognitive/emotional_model.py` | Mood state machine and per-user relationship tracking. Influences response tone. |
| `LearningStrategyFramework` | `cognitive/learning_strategy.py` | 5-tier hierarchy for training prioritization. Categorizes and scores examples. |
| `LearningTier` | `cognitive/learning_strategy.py` | Enum: FUNDAMENTAL_STRUCTURES(1), COGNITIVE_PRIMITIVES(2), SKILL_PATTERNS(3), DOMAIN_EXPERTISE(4), YOUR_SPECIFICS(5). |
| `PlanningFramework` | `cognitive/planning_framework.py` | 4-tier solution cascade. Maps capabilities to best available implementation. |
| `SolutionTier` | `cognitive/planning_framework.py` | Enum: BLEEDING_EDGE, CUTTING_EDGE, STABLE_OPTIMIZED, FALLBACK. |
| `Capability` | `cognitive/planning_framework.py` | Enum: INFERENCE, TTS, STT, VISION, EMBEDDING, TRAINING, MEMORY, CODE. |
| `SemanticMemory` | `memory/semantic_memory.py` | Vector embedding store using MLX MiniLM-L6-v2 (384-dim). Cosine similarity search. |
| `MemoryEntry` | `memory/semantic_memory.py` | Dataclass: id, content, entry_type (interaction/code/solution/project/note), timestamp, metadata, embedding. |
| `SAMVoicePipeline` | `voice/voice_pipeline.py` | Complete voice interaction pipeline: emotion detection, turn-taking, prosody control, TTS/RVC. |
| `VoicePipelineConfig` | `voice/voice_pipeline.py` | Configuration: sample_rate, emotion_backend, conversation_mode, rvc_model, prosody_intensity. |
| `ConversationEngine` | `conversation_engine/engine.py` | Turn-taking and flow management: continuous listening, backchannel generation, interrupt handling. |
| `ConversationMode` | `conversation_engine/engine.py` | Enum: COMPONENTS (Whisper+LLM+TTS), MOSHI (future full-duplex), CLOUD (future cloud API). |
| `TurnPredictor` | `conversation_engine/turn_predictor.py` | Predicts when user has finished speaking using silence detection and prosodic cues. |
| `VoiceEmotionDetector` | `emotion2vec_mlx/detector.py` | Detects emotion from audio using prosodic analysis or emotion2vec MLX model. |
| `EmotionToProsody` | `emotion2vec_mlx/prosody_control.py` | Maps detected emotions to speech synthesis parameters (rate, pitch, energy). |
| `ProsodyApplicator` | `emotion2vec_mlx/prosody_control.py` | Applies prosody parameters to TTS output audio. |
| `ClaudeLearner` | `claude_learning.py` | Parses Claude Code conversation files from `~/.claude/` and extracts training pairs. |
| `TrainingPair` | `claude_learning.py` | Dataclass: instruction, input, output, category, quality_score, source, metadata. |
| `DistillationDB` | `knowledge_distillation.py` | SQLite database for storing distilled knowledge: chain-of-thought, principles, preference pairs, skill templates. |
| `TrainingPipeline` | `training_pipeline.py` | Orchestrates collect -> validate -> convert -> fine-tune -> evaluate -> deploy. |
| `TrainingRun` | `training_pipeline.py` | Dataclass tracking a single fine-tuning run: status, metrics, output path. |
| `UnifiedOrchestrator` | `unified_orchestrator.py` | Master project manager. Tracks 20+ projects, suggests priorities, exports training data. |
| `ProjectDatabase` | `unified_orchestrator.py` | SQLite wrapper for project tracking with tables for projects, ideas, actions, dependencies. |
| `Project` | `unified_orchestrator.py` | Dataclass: id, name, description, category, tier, status, dependencies, progress, SAM capabilities. |
| `ProjectTier` | `unified_orchestrator.py` | Enum: CORE(1), PLATFORM(2), SERVICE(3), TOOL(4), EXPERIMENT(5). |
| `ProjectStatus` | `unified_orchestrator.py` | Enum: IDEA, PLANNED, IN_PROGRESS, BLOCKED, PAUSED, COMPLETED, ARCHIVED. |
| `ProjectCategory` | `unified_orchestrator.py` | Enum: SAM_CORE, APPLE_NATIVE, MEDIA, AUTOMATION, ML_TRAINING, REVERSE_ENGINEERING, GAMES_3D, VOICE_AUDIO, IMAGE_GEN, DATA_ACQUISITION, INFRASTRUCTURE. |
| `NativeProjectHub` | `unified_orchestrator.py` | macOS-level integration for project orchestration: Spotlight indexing, Quick Actions, file associations. |
| `Provider` | `smart_router.py` | Enum: LOCAL, CHATGPT, CLAUDE. Target for request routing. |
| `RoutingDecision` | `smart_router.py` | Dataclass: provider, sanitized_prompt, context_summary, estimated_tokens, reason. |
| `PrivacyGuard` | `privacy_guard.py` | Scans outgoing messages for PII. Guardian philosophy: warn, don't block. |
| `SensitiveMatch` | `privacy_guard.py` | Dataclass: category, value, start, end, severity, description. |
| `ScanResult` | `privacy_guard.py` | Dataclass: has_sensitive, matches, warnings, can_proceed. |
| `TransparencyGuard` | `transparency_guard.py` | Scans SAM's own responses for deceptive or suspicious patterns. |
| `ThoughtLogger` | `thought_logger.py` | Captures SAM's pre-thought process for debugging and transparency. |
| `ConversationLogger` | `conversation_logger.py` | Full conversation history with privacy-level-aware storage. |
| `PrivacyLevel` | `conversation_logger.py` | Enum: FULL, REDACTED, ENCRYPTED, EXCLUDED. |
| `CompressionMonitor` | `sam_api.py` | Tracks token compression statistics: tokens saved, compression ratios, budget overruns. |
| `SafeExecutor` | `execution/safe_executor.py` | Sandboxed command execution with path whitelisting, resource limits, and automatic backups. |
| `CommandClassifier` | `execution/command_classifier.py` | Classifies commands by risk level before execution. |
| `EscalationHandler` | `execution/escalation_handler.py` | Manages the local-to-cloud escalation workflow. |
| `DataArsenal` | `data_arsenal.py` | Intelligence gathering: scraping, full-text search, code example retrieval from multiple sources. |
| `TerminalCoordinator` | `terminal_coordination.py` | Multi-terminal awareness via shared SQLite state. Conflict detection and task broadcasting. |
| `ImpactTracker` | `impact_tracker.py` | Environmental monitoring: tracks energy savings from local vs cloud inference. |
| `DashboardGenerator` | `project_dashboard.py` | Data-rich project status dashboards with health scoring and level tracking. |
| `FeedbackDB` | `feedback_system.py` | Stores user feedback (thumbs up/down, corrections) for training signal. |
| `SamIntelligence` | `sam_intelligence.py` | Self-awareness module: SAM explains itself, cached improvement suggestions, proactive insights. |

---

*This document covers the architectural patterns, request flow paths, and terminology for the SAM Brain codebase as of 2026-01-29.*
