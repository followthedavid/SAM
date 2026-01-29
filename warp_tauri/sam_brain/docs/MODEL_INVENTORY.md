# SAM Model Inventory

Generated: 2026-01-29

Total model storage: ~31 GB across three locations
- `/Volumes/David External/SAM_models/` -- 6.9 GB
- `~/.sam/models/` -- 953 MB (mirrors of external drive models)
- `~/.cache/huggingface/hub/` -- 24 GB

---

## 1. CORE LLM -- MLX Qwen2.5 Base Models

These are the base language models SAM uses for all text generation.

### 1a. Qwen2.5-1.5B-Instruct-4bit (PRIMARY)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-1.5B-Instruct-4bit` |
| Size | 839 MB |
| Format | MLX safetensors (4-bit quantized) |
| HF ID | `mlx-community/Qwen2.5-1.5B-Instruct-4bit` |
| Loaded by | `cognitive/mlx_cognitive.py` -- `MODEL_CONFIGS["1.5b"]` |
| Actively used | YES -- primary inference model for chat, code, general tasks |
| Breaks without it | ALL SAM text generation. This is the default model. |

### 1b. Qwen2.5-3B-Instruct-4bit (SECONDARY)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-3B-Instruct-4bit` |
| Size | 1.6 GB |
| Format | MLX safetensors (4-bit quantized) |
| HF ID | `mlx-community/Qwen2.5-3B-Instruct-4bit` |
| Loaded by | `cognitive/mlx_cognitive.py` -- `MODEL_CONFIGS["3b"]` |
| Actively used | YES -- used for complex reasoning, analysis tasks via model selector |
| Breaks without it | Complex reasoning degrades to 1.5B; system still functions. |

### 1c. Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit` |
| Size | 839 MB |
| Format | MLX safetensors (4-bit quantized) |
| HF ID | `mlx-community/Josiefied-Qwen2.5-1.5B-Instruct-abliterated-v1-4bit` |
| Loaded by | `mlx_inference.py` -- `BASE_MODEL` constant |
| Actively used | YES -- used by `mlx_inference.py` for standalone/roleplay inference |
| Breaks without it | `mlx_inference.py` standalone mode fails; `sam_api.py` unaffected (uses mlx_cognitive.py). |

### 1d. Qwen2.5-0.5B-Instruct-4bit

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-0.5B-Instruct-4bit` |
| Size | 276 MB |
| Format | MLX safetensors (4-bit quantized) |
| HF ID | `mlx-community/Qwen2.5-0.5B-Instruct-4bit` |
| Loaded by | No direct code reference found; likely experimental/downloaded but unused |
| Actively used | NO |
| Breaks without it | Nothing. Safe to remove. |

### 1e. Qwen2.5-Coder-1.5B-Instruct-4bit

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--Qwen2.5-Coder-1.5B-Instruct-4bit` |
| Size | 839 MB |
| Format | MLX safetensors (4-bit quantized) |
| HF ID | `mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit` |
| Loaded by | No active code reference in current SAM brain |
| Actively used | NO -- likely an earlier experiment |
| Breaks without it | Nothing. Safe to remove. |

### 1f. Qwen2.5-Coder-1.5B-Instruct (full precision)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Coder-1.5B-Instruct` |
| Size | 2.9 GB |
| Format | Standard safetensors (full precision) |
| Loaded by | No active code reference |
| Actively used | NO -- full precision copy, too large for 8GB |
| Breaks without it | Nothing. Safe to remove (saves 2.9 GB). |

---

## 2. SAM LORA ADAPTERS (Fine-tuned Personality)

These are SAM's fine-tuned personality/behavior adapters.

### 2a. sam-brain-fused (FUSED MODEL -- PRIMARY for mlx_inference.py)

| Field | Value |
|-------|-------|
| Path (internal) | `~/.sam/models/sam-brain-fused/` |
| Path (external) | `/Volumes/David External/SAM_models/sam_fused/models/sam-brain-fused/` |
| Size | 839 MB (each copy) |
| Format | MLX safetensors (fused -- adapter baked into base model) |
| Key file | `model.safetensors` (828 MB) + `tokenizer.json` (11 MB) |
| Loaded by | `mlx_inference.py` -- `FUSED_MODEL_PATH` |
| Actively used | YES -- primary model for `mlx_inference.py` standalone mode |
| Breaks without it | `mlx_inference.py` falls back to adapter mode. |
| Note | Duplicate exists on both internal and external storage (identical). |

### 2b. sam-abliterated-lora (ADAPTER for mlx_inference.py)

| Field | Value |
|-------|-------|
| Path (internal) | `~/.sam/models/sam-abliterated-lora/adapters/` |
| Path (external) | `/Volumes/David External/SAM_models/sam_fused/models/sam-abliterated-lora/adapters/` |
| Size | 28 MB (each copy) |
| Format | MLX safetensors (LoRA adapter) |
| Key file | `adapters.safetensors` (5.0 MB) + checkpoints |
| Loaded by | `mlx_inference.py` -- `ADAPTER_PATH` |
| Actively used | YES -- fallback if fused model not found |
| Breaks without it | `mlx_inference.py` falls back to base model (no SAM personality). |

### 2c. sam-brain-lora (LATEST TRAINING ADAPTER)

| Field | Value |
|-------|-------|
| Path (internal) | `~/.sam/models/sam-brain-lora/adapters/` |
| Path (external) | `/Volumes/David External/SAM_models/sam_fused/models/sam-brain-lora/adapters/` |
| Size | 86 MB (each copy) |
| Format | MLX safetensors (LoRA adapter) |
| Key file | `adapters.safetensors` (10 MB) + training data + checkpoints |
| Loaded by | Not directly referenced in current code; training artifact |
| Actively used | PARTIALLY -- stores training data used for retraining |
| Breaks without it | Training pipeline loses latest adapter. |

### 2d. Adapter Archive (External -- /Volumes/David External/SAM_models/adapters/)

Multiple historical LoRA adapter versions from training experiments:

| Adapter | Size | Format | Status |
|---------|------|--------|--------|
| `sam_lora/` | ~78 MB | safetensors | Historical -- first training run |
| `sam_lora_v2/` | ~26 MB | safetensors | Historical |
| `sam_lora_1.5b_v2/` | ~30 MB | safetensors | ACTIVE -- loaded by `mlx_cognitive.py` ("1.5b" config) |
| `sam_lora_3b_lite/` | ~19 MB | safetensors | ACTIVE -- loaded by `mlx_cognitive.py` ("3b" config) |
| `sam_lora_1.5b/` | config only | -- | Incomplete training run |
| `sam_lora_1.5b_576/` | config only | -- | Incomplete training run |
| `sam_lora_1.5b_640/` | config only | -- | Incomplete training run |
| `sam_lora_1.5b_768/` | config only | -- | Incomplete training run |
| `sam_lora_1.5b_1024/` | config only | -- | Incomplete training run |
| `sam_lora_3b/` | config only | -- | Incomplete training run |
| `sam_lora_3b_320/` | config only | -- | Incomplete training run |
| `sam_lora_3b_384/` | config only | -- | Incomplete training run |
| `sam_lora_3b_384v2/` | config only | -- | Incomplete training run |

**NOTE:** The `mlx_cognitive.py` config paths use lowercase `sam_models` but actual directory is `SAM_models`. This could be a bug -- verify symlink or case-insensitive filesystem behavior.

---

## 3. VISION MODELS

### 3a. nanoLLaVA-1.5-bf16 (PRIMARY VISION)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--nanoLLaVA-1.5-bf16` |
| Size | 2.0 GB |
| Format | MLX safetensors (bf16) |
| HF ID | `mlx-community/nanoLLaVA-1.5-bf16` |
| Loaded by | `cognitive/vision_engine.py` -- `VISION_MODELS["nanollava"]`, `DEFAULT_MODEL` |
| Actively used | YES -- primary vision model, only VLM that works without PyTorch |
| Breaks without it | All LOCAL_VLM vision processing fails. OCR still works (Apple Vision). |

### 3b. SmolVLM2-256M-Video-Instruct-mlx

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--SmolVLM2-256M-Video-Instruct-mlx` |
| Size | 494 MB |
| Format | MLX |
| Loaded by | `cognitive/vision_engine.py` -- `VISION_MODELS["smolvlm-256m"]` |
| Actively used | CONDITIONAL -- requires PyTorch for processor; nanoLLaVA preferred |
| Breaks without it | Fallback to nanoLLaVA. No impact. |

### 3c. SmolVLM2-500M-Video-Instruct-mlx

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--SmolVLM2-500M-Video-Instruct-mlx` |
| Size | 973 MB |
| Format | MLX |
| Loaded by | `cognitive/vision_engine.py` -- `VISION_MODELS["smolvlm-500m"]` |
| Actively used | CONDITIONAL -- requires PyTorch |
| Breaks without it | No impact. |

### 3d. SmolVLM-Instruct-4bit

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--mlx-community--SmolVLM-Instruct-4bit` |
| Size | 1.4 GB |
| Format | MLX safetensors (4-bit) |
| Loaded by | `cognitive/vision_engine.py` -- `VISION_MODELS["smolvlm-2b-4bit"]` |
| Actively used | NO -- too large for 8GB (3.5GB RAM needed) |
| Breaks without it | Nothing. Safe to remove (saves 1.4 GB). |

### 3e. moondream2

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--vikhyatk--moondream2` |
| Size | 3.6 GB |
| Format | safetensors |
| Loaded by | `cognitive/vision_engine.py` -- marked `deprecated: True` |
| Actively used | NO -- model type not supported in current mlx_vlm |
| Breaks without it | Nothing. Safe to remove (saves 3.6 GB). |

---

## 4. EMBEDDING MODELS

### 4a. all-MiniLM-L6-v2 (PRIMARY EMBEDDINGS)

| Field | Value |
|-------|-------|
| Path (MLX) | `~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2` |
| Size | 87 MB |
| Format | PyTorch bin / safetensors (loaded via mlx_embeddings or sentence-transformers) |
| HF ID | `sentence-transformers/all-MiniLM-L6-v2` |
| Loaded by | `memory/semantic_memory.py` -- `EMBEDDING_MODEL`; `cognitive/doc_indexer.py`; `cognitive/enhanced_retrieval.py` |
| Actively used | YES -- all semantic search, memory recall, document indexing |
| Breaks without it | Semantic memory search, RAG retrieval, document indexing all fail. |

### 4b. BGE-small-en-v1.5

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--BAAI--bge-small-en-v1.5` |
| Size | 128 MB |
| Format | safetensors |
| Loaded by | No direct code reference found in current codebase |
| Actively used | NO -- likely experimental |
| Breaks without it | Nothing. Safe to remove. |

### 4c. cross-encoder/ms-marco-MiniLM-L-6-v2

| Field | Value |
|-------|-------|
| Path | Not cached (downloaded on demand by sentence-transformers) |
| Size | ~500 MB (at runtime) |
| Format | PyTorch |
| Loaded by | `cognitive/enhanced_retrieval.py` -- `ResultReranker` class |
| Actively used | CONDITIONAL -- only if sentence-transformers available and enough RAM |
| Breaks without it | Reranking falls back to lightweight TF-IDF scorer. Graceful degradation. |

---

## 5. EMOTION DETECTION

### 5a. Emotion2Vec Base (MLX converted)

| Field | Value |
|-------|-------|
| Path | `/Volumes/David External/SAM_models/emotion2vec/emotion2vec_base.safetensors` |
| Size | 234 MB |
| Format | safetensors (MLX converted) |
| Loaded by | `emotion2vec_mlx/backends/emotion2vec_backend.py` -- `Emotion2VecBackend._find_weights()` |
| Actively used | YES -- neural emotion detection from audio |
| Breaks without it | Emotion detection falls back to prosodic heuristics (lower accuracy). |

### 5b. Emotion2Vec Base PyTorch (source weights)

| Field | Value |
|-------|-------|
| Path | `/Volumes/David External/SAM_models/emotion2vec/emotion2vec_base_pytorch.npz` |
| Size | 356 MB |
| Format | NumPy archive (extracted PyTorch weights for conversion) |
| Loaded by | Used by `emotion2vec_mlx/models/convert_weights.py` during conversion |
| Actively used | NO -- only needed for re-conversion |
| Breaks without it | Cannot re-convert weights. Safe to remove if safetensors version works. |

### 5c. Emotion2Vec Plus Base (HuggingFace cache)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--emotion2vec--emotion2vec_plus_base` |
| Size | 1.0 GB |
| Format | PyTorch |
| Loaded by | Not directly referenced by MLX code (source for conversion) |
| Actively used | NO -- the converted MLX version (5a) is used instead |
| Breaks without it | Nothing currently. Source for future re-conversions. |

---

## 6. VOICE / TTS MODELS

### 6a. F5-TTS MLX

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--lucasnewman--f5-tts-mlx` |
| Size | 1.6 GB |
| Format | MLX safetensors |
| HF ID | `lucasnewman/f5-tts-mlx` |
| Loaded by | Voice pipeline (BALANCED/QUALITY presets via `voice_settings.py`) |
| Actively used | YES -- natural TTS for balanced/quality voice output |
| Breaks without it | Voice falls back to macOS `say` command (robotic but functional). |

### 6b. Vocos Mel 24kHz (vocoder for F5-TTS)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--lucasnewman--vocos-mel-24khz` |
| Size | 52 MB |
| Format | MLX safetensors |
| HF ID | `lucasnewman/vocos-mel-24khz` |
| Loaded by | Required by F5-TTS as the vocoder component |
| Actively used | YES -- required for F5-TTS to produce audio |
| Breaks without it | F5-TTS fails; falls back to macOS `say`. |

### 6c. Chatterbox (ResembleAI)

| Field | Value |
|-------|-------|
| Path | `~/.cache/huggingface/hub/models--ResembleAI--chatterbox` |
| Size | 3.0 GB |
| Format | PyTorch checkpoints |
| Loaded by | No direct code reference in current SAM brain |
| Actively used | NO -- likely experimental TTS alternative |
| Breaks without it | Nothing. Safe to remove (saves 3.0 GB). |

### 6d. RVC / Voice Conversion Models (HuggingFace cache)

| Model | Path | Size | Status |
|-------|------|------|--------|
| `lj1995/VoiceConversionWebUI` | `~/.cache/huggingface/hub/models--lj1995--VoiceConversionWebUI` | 4 KB | Metadata only (incomplete download) |
| `facebook/hubert-base-ls960` | `~/.cache/huggingface/hub/models--facebook--hubert-base-ls960` | 720 MB | RVC dependency (feature extraction) |
| `facebook/wav2vec2-base-960h` | `~/.cache/huggingface/hub/models--facebook--wav2vec2-base-960h` | 24 KB | Metadata only |

**RVC Voice Model (Dustin Steele):**
- Expected path: `~/ReverseLab/SAM/voice_models/dustin_steele/`
- Current status: DIRECTORY NOT FOUND (not yet trained or moved)
- Referenced by: `cognitive/planning_framework.py` line 146

---

## 7. FACE DETECTION / RECOGNITION

### 7a. InsightFace Buffalo_L

| Field | Value |
|-------|-------|
| Path | `/Volumes/David External/SAM_models/insightface/models/buffalo_l/` |
| Size | 325 MB (models) + 275 MB (zip) = 600 MB total |
| Format | ONNX |
| Components | `1k3d68.onnx` (137 MB), `det_10g.onnx` (16 MB), `2d106det.onnx` (4.8 MB), `genderage.onnx` (1.3 MB), `w600k_r50.onnx` (166 MB) |
| Loaded by | InsightFace library (used by ComfyUI face workflows) |
| Actively used | CONDITIONAL -- only when ComfyUI face-related workflows run |
| Breaks without it | Face detection/recognition in image generation pipelines. |

---

## 8. IMAGE GENERATION

### 8a. RealisticVision v5.1 (Stable Diffusion)

| Field | Value |
|-------|-------|
| Path | `/Volumes/David External/SAM_models/ComfyUI_models/checkpoints/realisticVisionV51_v51VAE.safetensors` |
| Size | 4.0 GB |
| Format | safetensors (SD 1.5 checkpoint with VAE) |
| Loaded by | ComfyUI via `comfyui_client.py` |
| Actively used | CONDITIONAL -- only when image generation is requested |
| Breaks without it | Image generation fails. ComfyUI needs at least one checkpoint. |

---

## 9. OTHER CACHED MODELS (Not actively used by SAM)

| Model | Path | Size | Notes |
|-------|------|------|-------|
| `meta-llama/Llama-3.2-3B-Instruct` | HF cache | 12 KB | Metadata only (gated model, not downloaded) |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | HF cache | 2.1 GB | Not referenced in SAM code. Safe to remove. |
| `pyannote/segmentation-3.0` | HF cache | 5.6 MB | Speaker diarization. Not actively used. |
| `pyannote/speaker-diarization-3.1` | HF cache | 8 KB | Metadata only. |
| `pyannote/speaker-diarization-community-1` | HF cache | 268 KB | Metadata only. |
| `pyannote/wespeaker-voxceleb-resnet34-LM` | HF cache | 25 MB | Speaker embedding. Not actively used. |
| `M4869/WavMark` | HF cache | 9.6 MB | Audio watermarking. Not referenced in code. |
| `moondream/md3p-int4` | Not cached | -- | Referenced in vision_engine.py but marked deprecated. |

---

## 10. MEMORY/INDEX FILES (Not models, but model-dependent)

| File | Path | Size | Purpose |
|------|------|------|---------|
| `index.npy` | `sam_brain/memory/index.npy` | 5 KB | Semantic memory vector index (generated by MiniLM) |
| `index_ollama_backup.npy` | `sam_brain/memory/index_ollama_backup.npy` | 161 KB | Old Ollama-era embeddings backup |
| `embeddings.json` | `sam_brain/memory/embeddings.json` | 22 KB | Memory entry metadata |
| `embeddings_index.json` | External (`sam_fused/`) | 10 MB | Larger embedding index |

---

## SUMMARY: Space Recovery Opportunities

Models that can be safely removed (no code references, deprecated, or duplicates):

| Model | Size | Reason |
|-------|------|--------|
| `vikhyatk/moondream2` | 3.6 GB | Deprecated in vision_engine.py |
| `ResembleAI/chatterbox` | 3.0 GB | No code reference |
| `Qwen/Qwen2.5-Coder-1.5B-Instruct` (full) | 2.9 GB | Full precision, unused |
| `TinyLlama/TinyLlama-1.1B-Chat-v1.0` | 2.1 GB | No code reference |
| `SmolVLM-Instruct-4bit` | 1.4 GB | Too large for 8GB RAM |
| `emotion2vec_plus_base` (HF cache) | 1.0 GB | MLX converted version used instead |
| `Qwen2.5-Coder-1.5B-Instruct-4bit` | 839 MB | No active code reference |
| `Qwen2.5-0.5B-Instruct-4bit` | 276 MB | No active code reference |
| `BAAI/bge-small-en-v1.5` | 128 MB | No active code reference |
| `emotion2vec_base_pytorch.npz` | 356 MB | Source weights; safetensors exists |
| **Total recoverable** | **~15.6 GB** | |

## SUMMARY: Critical Models (DO NOT REMOVE)

| Model | Size | Why critical |
|-------|------|-------------|
| Qwen2.5-1.5B-Instruct-4bit | 839 MB | Primary LLM |
| Qwen2.5-3B-Instruct-4bit | 1.6 GB | Complex reasoning |
| Josiefied-Qwen2.5-1.5B-abliterated-4bit | 839 MB | mlx_inference.py base |
| sam_lora_1.5b_v2 (adapters) | 30 MB | SAM personality (1.5B) |
| sam_lora_3b_lite (adapters) | 19 MB | SAM personality (3B) |
| sam-brain-fused | 839 MB | Fused inference model |
| sam-abliterated-lora | 28 MB | Fallback adapter |
| nanoLLaVA-1.5-bf16 | 2.0 GB | Vision processing |
| all-MiniLM-L6-v2 | 87 MB | Semantic memory embeddings |
| emotion2vec_base.safetensors | 234 MB | Emotion detection |
| F5-TTS MLX | 1.6 GB | Natural voice output |
| vocos-mel-24khz | 52 MB | F5-TTS vocoder |
| hubert-base-ls960 | 720 MB | RVC feature extraction |
| RealisticVision v5.1 | 4.0 GB | Image generation |

## POTENTIAL ISSUES FOUND

1. **Path case mismatch**: `mlx_cognitive.py` references `/Volumes/David External/sam_models/adapters/` (lowercase) but actual path is `/Volumes/David External/SAM_models/adapters/`. macOS is case-insensitive by default so this works, but could break on case-sensitive filesystems.

2. **Duplicate model storage**: `sam-brain-fused`, `sam-abliterated-lora`, and `sam-brain-lora` each exist in both `~/.sam/models/` and `/Volumes/David External/SAM_models/sam_fused/models/`. Total duplication: ~953 MB.

3. **Missing RVC voice model**: `cognitive/planning_framework.py` checks for `~/ReverseLab/SAM/voice_models/dustin_steele/` but this directory does not exist. Voice cloning (QUALITY preset) cannot function.

4. **Roleplay adapter empty**: `mlx_inference.py` references `/Volumes/David External/nifty_archive/models/sam-roleplay-qwen-lora/` which exists but is empty. Roleplay mode falls back to default adapter.
