# Emotion System Deep Dive

**Package:** `emotion2vec_mlx/`
**Location:** `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/emotion2vec_mlx/`
**Version:** 0.1.0
**Date:** 2026-01-29

---

## 1. File-by-File Breakdown

### `__init__.py` -- Package Entry Point
Exposes the public API of the emotion system. Two functional halves:

- **Detection (INPUT):** `VoiceEmotionDetector`, `EmotionResult`, `EmotionCategory`, `PrimaryDimensions`, `get_available_backends`
- **Expression (OUTPUT):** `EmotionToProsody`, `ProsodyParameters`, `ProsodyApplicator`, `emotion_to_prosody`, `NEUTRAL_PROSODY`

Lists three backends: `prosodic` (works now), `whisper_mlx`, `emotion2vec` (marked "coming soon" in docstring, but actually has converted weights).

### `detector.py` -- Main Interface (VoiceEmotionDetector)
Unified detection interface. Key capabilities:

| Method | Purpose |
|--------|---------|
| `analyze(audio)` | One-shot emotion analysis from file path or numpy array |
| `analyze_streaming(chunk)` | Streaming analysis with 1s buffer, 500ms overlap |
| `get_history(window)` | Time-windowed history retrieval |
| `get_trajectory()` | 5-minute trajectory analysis (trend: improving/declining/stable/volatile) |
| `calibrate_baseline(samples)` | Per-speaker pitch baseline calibration (3-5 neutral samples) |

- Defaults to `prosodic` backend
- Maintains up to 100 results in history
- Falls back gracefully if requested backend is unavailable
- Accepts file paths (str/Path) or raw numpy arrays (auto-saves to temp WAV)

### `taxonomy.py` -- Emotion Taxonomy (26 Categories)
Defines the full emotional vocabulary using Russell's Circumplex Model:

**26 Emotion Categories in 5 Groups:**

| Group | Emotions |
|-------|----------|
| Negative-Activated (high arousal, negative valence) | anxious, nervous, frustrated, angry, stressed, panicked, impatient |
| Negative-Deactivated (low arousal, negative valence) | sad, tired, bored, disappointed, lonely, hopeless |
| Positive-Activated (high arousal, positive valence) | excited, happy, playful, flirty, curious, confident, amused |
| Positive-Deactivated (low arousal, positive valence) | calm, content, thoughtful, affectionate |
| Neutral | neutral, confused |

Supporting data structures:
- `Intensity`: SLIGHT / MODERATE / STRONG / INTENSE (mapped from 0-1 score)
- `PrimaryDimensions`: Valence (-1 to +1), Arousal (0 to 1), Dominance (0 to 1)
- `ProsodicMarkers`: pitch_mean_hz, pitch_std_hz, pitch_elevated, speech_rate_sps, speech_rate_category, pause_ratio, voice_tremor, breathiness, hesitation_count, energy_variance
- `EmotionResult`: Full analysis output with primary dimensions, top-3 categorical predictions, prosodic markers, audio quality, duration, timestamp, backend used, optional raw embedding
- `EmotionPrediction`: Single emotion + confidence + intensity
- `EMOTION_QUADRANTS`: Maps (valence_sign, arousal_level) to likely emotion categories
- `dimensions_to_likely_emotions()`: Rule-based VAD-to-category mapping with dominance refinement

The `to_context_string()` method on `EmotionResult` generates LLM-injectable strings like `[Voice sounds moderately anxious (elevated pitch, speaking quickly), possibly also stressed]`.

### `prosody_control.py` -- Emotion Expression (OUTPUT side)
Maps emotional states to TTS prosody parameters. This is the OUTPUT half -- making SAM EXPRESS emotions, not detect them.

**ProsodyParameters (8 dimensions):**
- `pitch_shift_semitones`: -6 to +6
- `pitch_variance`: 0.5 to 2.0 (1.0 = normal)
- `speech_rate`: 0.7 to 1.5
- `pause_multiplier`: 0.5 to 2.0
- `volume_db`: -6 to +6 dB
- `dynamic_range`: 0.5 to 1.5
- `breathiness`: 0.0 to 1.0
- `tremolo_amount`: 0.0 to 1.0

**All 26 emotions have hand-tuned prosody profiles**, based on Scherer (2003) and Juslin & Laukka (2003) research. Examples:
- ANGRY: lower pitch (-0.5st), very loud (+3dB), clipped pauses (0.5x)
- SAD: lower pitch (-1.5st), quiet (-2dB), slow (0.8x), breathy (0.3), longer pauses (1.5x)
- FLIRTY: slightly slower (0.95x), breathy (0.25), slight pitch rise (+0.5st)
- PANICKED: much higher pitch (+2.5st), very fast (1.35x), very loud (+4dB), tremor (0.5)

**EmotionToProsody** class with response strategies:
- `match`: Mirror user's emotion (scaled to 80% of confidence)
- `complement`: Respond complementarily (anxious user gets calm SAM)
- `amplify`: Amplify the emotional direction
- `neutral`: Always respond neutrally

Complement mapping is thoughtfully designed: negative-activated emotions map to CALM, negative-deactivated map to AFFECTIONATE, positive emotions are matched.

**ProsodyApplicator** supports three output modes:
1. `to_ssml()`: SSML markup for cloud TTS engines
2. `apply_to_audio()`: Direct audio modification via librosa (pitch shift, time stretch, volume, tremolo)
3. `get_rvc_params()`: RVC-compatible parameter dict (f0_up_key, rate)

### `backends/__init__.py` -- Backend Registry
Defines 4 backends with metadata:

| Backend | Quality | Speed | Memory | Requirements |
|---------|---------|-------|--------|--------------|
| emotion2vec | excellent | moderate | 400 MB | mlx |
| hybrid | excellent | moderate | 450 MB | mlx |
| whisper_mlx | good | fast | 500 MB | mlx, mlx_whisper |
| prosodic | basic | very_fast | 50 MB | none |

`get_available_backends()` checks MLX availability and whether emotion2vec weights exist on disk. If weights are found, emotion2vec is placed first in priority. `create_backend()` is a factory function.

**Bug:** The factory imports `ProsodicEmotionBackend` from `prosodic_backend.py`, but that file defines the class as `ProsodicBackend`. This will cause an `ImportError` at runtime when creating the prosodic backend via the factory. Direct instantiation (bypassing the factory) would work, but the `VoiceEmotionDetector` uses `create_backend()` which will fail.

### `backends/emotion2vec_backend.py` -- Neural Backend
Two classes:

**Emotion2VecBackend:**
- Loads the full Emotion2Vec MLX model
- Searches for weights in three locations: `models/weights/`, `/Volumes/David External/SAM_models/emotion2vec/`, `~/.cache/emotion2vec_mlx/`
- Falls back to random initialization (for testing) if no weights found
- Accepts numpy arrays (not file paths), resamples to 16kHz if needed
- Maps 9-class Emotion2Vec output to the 26-class taxonomy
- Does NOT extract prosodic markers (all zeros) -- relies on the model alone
- Streaming support with 500ms minimum, 1s context window

9-class to 26-class mapping:
- angry -> ANGRY
- disgusted -> FRUSTRATED
- fearful -> ANXIOUS
- happy -> HAPPY
- neutral -> NEUTRAL
- other -> NEUTRAL
- sad -> SAD
- surprised -> EXCITED
- unknown -> NEUTRAL

Each class has pre-defined VAD (Valence-Arousal-Dominance) values.

**HybridEmotionBackend:**
- Combines Emotion2Vec (70% weight) with prosodic analysis (30% weight)
- Uses E2V for categorical classification, prosodic for fine-grained VAD
- Falls back to pure prosodic if E2V weights not available
- **Bug:** The `analyze()` method constructs `EmotionResult` using keyword arguments (`primary_emotion=`, `secondary_emotion=`, etc.) that do not match the `EmotionResult` dataclass definition. `EmotionResult` uses positional/dataclass fields (`primary`, `categorical`, `prosodic`, etc.). This class would raise a `TypeError` at runtime.

### `backends/prosodic_backend.py` -- Acoustic Feature Backend
Pure signal processing, no ML. Extracts:

1. **Pitch (F0):** Uses librosa's `pyin` if available, falls back to autocorrelation-based pitch tracking. Detects mean, std, elevation above baseline (default 150Hz), and tremor (jitter > 2%).
2. **Energy:** RMS energy per 25ms frame with 10ms hop.
3. **Speech Rate:** Syllable estimation via energy envelope peak counting. Categories: slow (<3.5 sps), normal (3.5-5.5 sps), fast (>5.5 sps).
4. **Pauses:** Silence ratio using adaptive threshold (10% of overall RMS).
5. **Hesitations:** Brief energy dips (100-400ms) within speech.
6. **Breathiness:** Spectral flatness (librosa) or high/low frequency ratio fallback.
7. **Audio Quality:** Clipping detection, signal level check, crest factor analysis.

Dimension mapping (prosodic features to VAD):
- Arousal: elevated pitch (+0.2), fast rate (+0.15), high energy variance (+0.1), tremor (+0.1)
- Valence: breathiness (-0.1), hesitations (-0.15), pauses (-0.1). Note: starts at 0.0, biased slightly negative.
- Dominance: high energy variance (+0.1), fast rate (+0.1), monotone pitch (+0.1), hesitations (-0.2)

Confidence capped at 0.75 for prosodic-only detection (honest about limitations).

Audio loading fallback chain: mlx-audio -> torchaudio -> scipy.io.wavfile.

**Bug:** Class is named `ProsodicBackend`, but the factory in `backends/__init__.py` imports it as `ProsodicEmotionBackend`.

### `models/emotion2vec_mlx.py` -- MLX Model Architecture
Full native MLX implementation of Emotion2Vec (based on data2vec 2.0):

**Architecture:**
```
Raw Audio [batch, time]
    |
ConvFeatureExtractor (7 Conv1d layers)
    -> [batch, frames, 512]
    -> Linear projection to [batch, frames, 768]
    |
PositionalEncoding (sinusoidal)
    |
TransformerEncoder (8 layers, pre-norm)
    -> MultiHeadAttention (12 heads, 64 dim each)
    -> FeedForward (768 -> 3072 -> 768)
    -> LayerNorm + residual connections
    |
EmotionClassifier
    -> Mean pooling over sequence
    -> Linear [768 -> 9]
    -> Softmax
```

**Model Sizes:**
- Base: ~90M params (768 hidden, 12 heads, 8 layers, 3072 FFN)
- Large: ~300M params (1024 hidden, 16 heads, 24 layers, 4096 FFN)

Features:
- KV-cache support in attention layers for efficient inference
- `extract_features()` returns 768-dim embeddings for downstream tasks
- `predict()` returns full dict with emotion label, confidence, and all class probabilities
- `from_pretrained()` loads .safetensors or .npz weights

### `models/convert_to_mlx.py` -- Weight Name Mapper
Converts numpy-extracted weights to MLX format with careful name mapping:

Key mappings from data2vec naming:
- `d2v_model.modality_encoders.AUDIO.local_encoder.conv_layers` -> `feature_extractor.conv_layers`
- `d2v_model.blocks.N.attn.qkv` -> Split into separate `q_proj`, `k_proj`, `v_proj` (combined 2304x768 -> 3 x 768x768)
- `proj.weight/bias` -> `classifier.classifier.weight/bias`
- Conv weights transposed from [out, in, kernel] to [out, kernel, in] for MLX

Skips: extra_tokens, alibi, decoder, target, ema, context_encoder, modality-specific encoder.

Saves output as .safetensors and generates config.json.

### `models/convert_weights.py` -- End-to-End Conversion Pipeline
Full download-and-convert pipeline:

1. Downloads from HuggingFace (primary), FunASR, or ModelScope (fallbacks)
2. Loads PyTorch state dict (handles nested `model`/`state_dict` keys)
3. Maps weight names using a simpler pattern-replacement approach
4. Saves as .safetensors or .npz

Supports both remote download (`--model iic/emotion2vec_plus_base`) and local checkpoint conversion (`--local`).

### `models/extract_pytorch_weights.py` -- PyTorch Weight Extraction
Intermediate step: extracts PyTorch weights to numpy (.npz) format. Designed to run on a machine with PyTorch installed, producing a portable numpy file that can then be converted to MLX on the Mac without needing PyTorch.

Two-step workflow: `extract_pytorch_weights.py` -> `convert_to_mlx.py`

---

## 2. Is the Emotion2Vec Model Actually Converted and Working?

**Weights exist and are converted.** Found at:
```
/Volumes/David External/SAM_models/emotion2vec/
    emotion2vec_base_pytorch.npz    (373 MB - original numpy extraction)
    emotion2vec_base.safetensors    (245 MB - converted MLX weights)
    config.json                     (base model config)
```

The config confirms: base model, 768 hidden, 12 heads, 8 layers, 9 emotions.

**However, the model is NOT fully operational due to several bugs:**

1. **Backend factory bug:** `backends/__init__.py` line 99 imports `ProsodicEmotionBackend` but the class in `prosodic_backend.py` is named `ProsodicBackend`. Creating the prosodic backend via the factory will crash with `ImportError`.

2. **HybridEmotionBackend bug:** `emotion2vec_backend.py` lines 400-408 construct `EmotionResult` with wrong keyword arguments (`primary_emotion=`, `secondary_emotion=`, `secondary_confidence=`, `intensity=`, `raw_scores=`) that do not match the `EmotionResult` dataclass fields. This would crash with `TypeError`.

3. **Emotion2VecBackend `analyze()` signature mismatch:** The backend's `analyze()` method accepts `(audio: np.ndarray, sample_rate: int)` but `VoiceEmotionDetector.analyze()` calls `self._backend.analyze(audio_path, sample_rate)` passing a string file path. The emotion2vec backend expects numpy arrays, not file paths. Only the prosodic backend handles file paths.

4. **Weight path discovery works:** The `_find_weights()` method searches `/Volumes/David External/SAM_models/emotion2vec/` and the weights are there as `emotion2vec_base.safetensors`. However, the search pattern expects the file to be named `emotion2vec_base.safetensors` in a specific subdirectory structure that may not match exactly.

**Bottom line:** The model architecture is implemented, weights are converted, but runtime integration has multiple bugs that would prevent actual execution. The prosodic backend also has a naming bug. Only direct instantiation of `ProsodicBackend` (bypassing the factory) or manual `Emotion2VecBackend` usage would work.

---

## 3. Which Backend is Active?

**The prosodic backend is the active default**, but it is broken through the factory path.

Evidence:
- `VoiceEmotionDetector.__init__()` defaults to `backend="prosodic"`
- `voice/voice_pipeline.py` config field: `emotion_backend: str = "prosodic"`
- The `__init__.py` docstring says prosodic "works now"
- The emotion2vec backend is described as "coming soon" in the package docstring

**Actual runtime behavior:** The `create_backend("prosodic")` call would fail due to the `ProsodicEmotionBackend` vs `ProsodicBackend` naming mismatch. If this was ever run, it would crash at initialization.

The voice pipeline at `voice/voice_pipeline.py` does import and use the emotion system:
- Line 33: `from emotion2vec_mlx import (VoiceEmotionDetector, EmotionResult, EmotionToProsody, ...)`
- Line 115-116: Creates `VoiceEmotionDetector(backend=self.config.emotion_backend)`
- Line 170-176: Injects emotion context into LLM prompts
- Line 187-194: Uses `EmotionToProsody` for voice synthesis

---

## 4. How Does It Integrate with the Voice Pipeline?

The emotion system has a bidirectional design within `voice/voice_pipeline.py`:

### Input Path (Emotion Detection)
```
User Audio -> VoiceEmotionDetector.analyze()
    -> EmotionResult
    -> result.to_context_string()
    -> Injected into SAM's LLM prompt as "[Voice sounds moderately anxious ...]"
```

The pipeline buffers audio chunks and runs emotion detection periodically (every 500ms by default). The detected emotion state is stored as `self._current_emotion` and included in the prompt context sent to the LLM.

### Output Path (Emotion Expression)
```
SAM's response emotion
    -> EmotionToProsody.get_prosody(emotion, intensity)
    -> ProsodyParameters
    -> ProsodyApplicator.apply_to_audio() or .get_rvc_params()
    -> Modified TTS output
```

When synthesizing speech, the pipeline determines what emotion SAM should express and applies prosody modifications to the TTS output. This can use SSML for cloud TTS, direct audio manipulation via librosa, or RVC parameter injection.

### Response Strategies
The `EmotionToProsody.from_emotion_result()` method supports different response strategies:
- `match`: SAM mirrors the user's emotional state
- `complement`: SAM responds with an appropriate counter-emotion (e.g., calm response to anxious user)
- `amplify`: SAM amplifies the emotional direction
- `neutral`: Always neutral delivery

### Current Integration Status
The integration code exists in `voice/voice_pipeline.py` but given the bugs identified above, the emotion detection/expression pipeline is not functional. The voice pipeline would need the naming bugs fixed to actually use emotion detection.

---

## 5. What Emotions Can It Detect?

### Emotion2Vec Model (9 classes, neural)
The underlying Emotion2Vec model classifies into 9 categories:
1. angry
2. disgusted
3. fearful
4. happy
5. neutral
6. other
7. sad
8. surprised
9. unknown

### Extended Taxonomy (26 classes, mapped)
The system maps these 9 neural classes to a richer 26-category taxonomy using:
- Rule-based mapping (9 -> 26 via `EMOTION2VEC_TO_TAXONOMY`)
- VAD dimension analysis (valence/arousal/dominance to category via `dimensions_to_likely_emotions()`)
- Prosodic feature refinement (pitch, rate, tremor, breathiness as additional signals)

The 26 categories organized by quadrant:

**Negative-Activated:** anxious, nervous, frustrated, angry, stressed, panicked, impatient
**Negative-Deactivated:** sad, tired, bored, disappointed, lonely, hopeless
**Positive-Activated:** excited, happy, playful, flirty, curious, confident, amused
**Positive-Deactivated:** calm, content, thoughtful, affectionate
**Neutral:** neutral, confused

The prosodic backend can distinguish within quadrants using acoustic cues (e.g., high arousal + negative + low dominance = anxious vs. high arousal + negative + high dominance = angry).

---

## 6. Accuracy and Performance

### Emotion2Vec Neural Backend
- **Accuracy:** The original Emotion2Vec model reports state-of-the-art results on IEMOCAP and other benchmarks. The MLX port should match if weights are correctly converted.
- **Speed:** Moderate. Full transformer inference (8 layers, 768 hidden). Not benchmarked on M2 but estimated 100-500ms per utterance.
- **Memory:** ~400 MB for weights + runtime. Base model weights are 245 MB (safetensors).
- **Limitation:** Only 9 emotion classes from the neural model. The 26-class expansion is heuristic-based.
- **Status:** Weights converted but integration bugs prevent runtime use.

### Prosodic Backend
- **Accuracy:** Basic. Confidence is capped at 0.75 (the code itself acknowledges limitations). Valence detection from prosody alone is unreliable (the code notes "harder to determine from prosody alone"). Biased toward detecting negative emotions because positive prosodic cues are more ambiguous.
- **Speed:** Very fast. Pure numpy operations, no model loading. Estimated <50ms per utterance.
- **Memory:** ~50 MB (negligible).
- **Strengths:** Good at detecting arousal level (fast/slow speech, pitch elevation, tremor), anxiety markers (jitter, breathiness), and hesitation patterns.
- **Weaknesses:** Cannot reliably distinguish positive from negative emotions. Cannot distinguish between similar emotions within the same quadrant.

### Hybrid Backend
- **Design:** 70% Emotion2Vec + 30% Prosodic for VAD dimensions, Emotion2Vec for categorical classification.
- **Status:** Broken due to `EmotionResult` constructor bug. Never been tested.

### Key Performance Observations
1. The prosodic backend is honest about its confidence ceiling (0.75 max).
2. Audio quality estimation affects overall confidence.
3. Per-speaker calibration is supported but optional.
4. Streaming analysis uses 500ms overlap for temporal continuity.
5. No benchmarks or test suite exist in the codebase.

---

## 7. Summary of Issues

| Issue | Severity | Location |
|-------|----------|----------|
| `ProsodicEmotionBackend` vs `ProsodicBackend` naming mismatch | **Critical** -- prosodic backend cannot be created via factory | `backends/__init__.py` line 99 vs `prosodic_backend.py` line 22 |
| `HybridEmotionBackend.analyze()` uses wrong `EmotionResult` kwargs | **Critical** -- hybrid backend crashes at runtime | `backends/emotion2vec_backend.py` lines 400-408 |
| `Emotion2VecBackend.analyze()` expects numpy but `VoiceEmotionDetector` passes file path | **Critical** -- emotion2vec backend crashes at runtime | `backends/emotion2vec_backend.py` line 144 vs `detector.py` line 88 |
| `__init__.py` docstring says emotion2vec is "coming soon" but weights exist | **Minor** -- misleading documentation | `__init__.py` line 19 |
| No test suite | **Moderate** -- no way to verify correctness | N/A |
| `PositionalEncoding._build_pe()` uses `mx.array.at` which may not exist in MLX | **Potential** -- needs verification | `models/emotion2vec_mlx.py` line 141 |

---

## 8. Architecture Diagram

```
                    USER AUDIO
                        |
                        v
              VoiceEmotionDetector
                   (detector.py)
                        |
            +-----------+-----------+
            |           |           |
            v           v           v
       ProsodicBackend  Emotion2Vec  HybridBackend
       (prosodic_       Backend      (both combined)
        backend.py)     (emotion2vec_
                        backend.py)
            |               |
            v               v
       Acoustic        Emotion2VecMLX
       Features        (emotion2vec_mlx.py)
       (pitch,         CNN -> Transformer
        rate,           -> Classifier
        energy)         (9 classes)
            |               |
            +-------+-------+
                    |
                    v
             EmotionResult
             (taxonomy.py)
             26 categories +
             VAD dimensions +
             prosodic markers
                    |
          +---------+---------+
          |                   |
          v                   v
    LLM Context          EmotionToProsody
    Injection            (prosody_control.py)
    "[Voice sounds       ProsodyParameters
     anxious...]"        -> SSML / Audio / RVC
          |                   |
          v                   v
    SAM's Text           SAM's Voice
    Response             Output
```
