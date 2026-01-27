# Voice Emotion Detection System - Design Document

## Vision

Detect nuanced emotional states from voice tonality - not what someone says, but *how* they say it. This system should recognize when someone sounds nervous, anxious, frustrated, or stressed even if their words don't explicitly convey it.

**Key Insight:** Humans communicate emotion through prosody (pitch, rhythm, energy) independently of lexical content. "I'm fine" can mean 10 different things depending on tone.

---

## Emotion Taxonomy

### Tier 1: Primary Dimensions (Always Detected)

Based on Russell's Circumplex Model:

| Dimension | Range | What It Measures |
|-----------|-------|------------------|
| **Valence** | -1.0 to +1.0 | Negative ←→ Positive |
| **Arousal** | 0.0 to 1.0 | Calm ←→ Activated |
| **Dominance** | 0.0 to 1.0 | Submissive ←→ Dominant |

### Tier 2: Categorical Emotions (26 States)

**Negative-Activated (High Arousal, Negative Valence):**
- `anxious` - worried, apprehensive, on edge
- `nervous` - jittery, uneasy, hesitant
- `frustrated` - blocked, annoyed, stuck
- `angry` - hostile, aggressive, irritated
- `stressed` - overwhelmed, pressured, tense
- `panicked` - fearful, alarmed, desperate
- `impatient` - rushed, agitated

**Negative-Deactivated (Low Arousal, Negative Valence):**
- `sad` - down, unhappy, melancholic
- `tired` - exhausted, drained, weary
- `bored` - disengaged, uninterested
- `disappointed` - let down, deflated
- `lonely` - isolated, disconnected
- `hopeless` - defeated, resigned

**Positive-Activated (High Arousal, Positive Valence):**
- `excited` - enthusiastic, energized, thrilled
- `happy` - joyful, pleased, content
- `playful` - teasing, lighthearted, mischievous
- `flirty` - coy, suggestive, charming
- `curious` - interested, engaged, inquisitive
- `confident` - assured, self-certain
- `amused` - entertained, finding humor

**Positive-Deactivated (Low Arousal, Positive Valence):**
- `calm` - peaceful, relaxed, serene
- `content` - satisfied, at ease
- `thoughtful` - reflective, contemplative
- `affectionate` - warm, loving, tender

**Neutral/Ambiguous:**
- `neutral` - baseline, unremarkable
- `confused` - uncertain, unclear

### Tier 3: Intensity Modifiers

Each emotion has intensity: `slight`, `moderate`, `strong`, `intense`

Example output:
```json
{
  "primary": {
    "valence": -0.4,
    "arousal": 0.7,
    "dominance": 0.3
  },
  "categorical": [
    {"emotion": "anxious", "confidence": 0.82, "intensity": "moderate"},
    {"emotion": "frustrated", "confidence": 0.45, "intensity": "slight"}
  ],
  "prosodic_markers": {
    "pitch_elevated": true,
    "speech_rate": "fast",
    "voice_tremor": true,
    "hesitation_markers": 3
  }
}
```

---

## Audio Features Extracted

### 1. Pitch (F0) Features
| Feature | What It Indicates |
|---------|-------------------|
| Mean F0 | Baseline pitch (higher = more aroused) |
| F0 Std Dev | Variability (monotone = depressed, high = excited) |
| F0 Range | Expressiveness |
| F0 Contour | Rising = questioning, falling = certain |
| Jitter | Pitch instability (tremor = nervous) |

### 2. Energy/Loudness Features
| Feature | What It Indicates |
|---------|-------------------|
| Mean Energy | Overall loudness |
| Energy Variance | Dynamic range |
| Attack Rate | How sharply speech starts (aggressive = fast attack) |
| Shimmer | Amplitude instability |

### 3. Temporal Features
| Feature | What It Indicates |
|---------|-------------------|
| Speech Rate | Words/syllables per second |
| Pause Duration | Longer = hesitant, thoughtful, or sad |
| Pause Frequency | More pauses = uncertainty |
| Articulation Rate | Speed excluding pauses |
| Hesitation Markers | "um", "uh", filled pauses |

### 4. Spectral Features
| Feature | What It Indicates |
|---------|-------------------|
| MFCCs (1-13) | Vocal tract shape, voice quality |
| Spectral Centroid | Brightness (higher = tense) |
| Spectral Flux | Change rate |
| Harmonic-to-Noise | Voice clarity (breathy = low HNR) |
| Formant Frequencies | Vowel shaping, tension |

### 5. Voice Quality Features
| Feature | What It Indicates |
|---------|-------------------|
| Breathiness | Air in voice (intimate, tired, or sad) |
| Creaky Voice | Vocal fry (casual, tired, or dismissive) |
| Tense Voice | Constricted (stressed, angry) |
| Modal Voice | Normal phonation |

---

## Model Architecture

### Option A: Wav2Vec2 + Emotion Head (Recommended)

```
Audio Input (16kHz)
       │
       ▼
┌─────────────────────┐
│  Wav2Vec2-Large     │  Pre-trained speech representations
│  (Facebook/wav2vec) │  Captures prosodic patterns
└─────────────────────┘
       │
       ▼ (768-dim embeddings per frame)
       │
┌─────────────────────┐
│  Temporal Pooling   │  Mean + Std + Attention pooling
└─────────────────────┘
       │
       ▼ (2304-dim utterance embedding)
       │
┌─────────────────────┐
│  Multi-Task Heads   │
│  ├─ Valence Head    │  → float [-1, 1]
│  ├─ Arousal Head    │  → float [0, 1]
│  ├─ Dominance Head  │  → float [0, 1]
│  └─ Category Head   │  → 26-class softmax
└─────────────────────┘
```

**Why Wav2Vec2:**
- Pre-trained on 960h of speech
- Learns prosodic patterns without explicit feature engineering
- State-of-the-art on emotion benchmarks
- MLX-compatible (Apple Silicon native)

### Option B: OpenSMILE + Classifier (Lightweight Fallback)

```
Audio Input
       │
       ▼
┌─────────────────────┐
│  OpenSMILE          │  Extract 6,373 acoustic features
│  (eGeMAPSv02)       │  (standardized feature set)
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  Feature Selection  │  Top 500 most predictive
└─────────────────────┘
       │
       ▼
┌─────────────────────┐
│  XGBoost Ensemble   │  Fast, interpretable
└─────────────────────┘
```

**Why OpenSMILE:**
- Explicit features (debuggable)
- Tiny runtime footprint
- Works offline, no GPU needed
- Good for real-time streaming

### Option C: Ensemble (Production)

Combine both approaches:
- Wav2Vec2 for primary detection
- OpenSMILE for feature explainability
- Weighted average based on audio quality

---

## Training Data Sources

### Public Datasets

| Dataset | Emotions | Hours | Notes |
|---------|----------|-------|-------|
| **IEMOCAP** | 9 emotions | 12h | Gold standard, acted + spontaneous |
| **RAVDESS** | 8 emotions | 7h | Professional actors, clean audio |
| **CREMA-D** | 6 emotions | 7h | Diverse speakers |
| **MSP-IMPROV** | 4 emotions | 9h | Improvised scenarios |
| **MELD** | 7 emotions | 13h | TV show clips (noisy but natural) |
| **CMU-MOSEI** | 6 emotions | 65h | YouTube monologues |

### Custom Data Collection

For nuanced emotions (anxious, frustrated, nervous):
1. Record yourself in actual states (not acted)
2. Label with state + intensity
3. Include context notes

### Data Augmentation
- Pitch shifting (±2 semitones)
- Time stretching (0.9x - 1.1x)
- Background noise injection
- Room impulse response convolution

---

## API Design

### Core Classes

```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class EmotionCategory(Enum):
    ANXIOUS = "anxious"
    NERVOUS = "nervous"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"
    STRESSED = "stressed"
    SAD = "sad"
    TIRED = "tired"
    EXCITED = "excited"
    HAPPY = "happy"
    PLAYFUL = "playful"
    FLIRTY = "flirty"
    CURIOUS = "curious"
    CONFIDENT = "confident"
    CALM = "calm"
    NEUTRAL = "neutral"
    # ... all 26

class Intensity(Enum):
    SLIGHT = "slight"
    MODERATE = "moderate"
    STRONG = "strong"
    INTENSE = "intense"

@dataclass
class EmotionPrediction:
    emotion: EmotionCategory
    confidence: float  # 0-1
    intensity: Intensity

@dataclass
class PrimaryDimensions:
    valence: float      # -1 to +1
    arousal: float      # 0 to 1
    dominance: float    # 0 to 1

@dataclass
class ProsodicMarkers:
    pitch_mean_hz: float
    pitch_std_hz: float
    pitch_elevated: bool
    speech_rate_sps: float  # syllables per second
    speech_rate_category: str  # "slow", "normal", "fast"
    pause_ratio: float
    voice_tremor: bool
    breathiness: float
    hesitation_count: int

@dataclass
class EmotionResult:
    """Complete emotion analysis result"""
    primary: PrimaryDimensions
    categorical: List[EmotionPrediction]  # Top 3 emotions
    prosodic: ProsodicMarkers
    audio_quality: float  # 0-1, affects confidence
    duration_seconds: float
    timestamp: str
```

### Main Interface

```python
class VoiceEmotionDetector:
    """
    Detects nuanced emotional states from voice.

    Usage:
        detector = VoiceEmotionDetector()
        result = detector.analyze("path/to/audio.wav")
        print(f"Feeling {result.categorical[0].emotion.value}")
    """

    def __init__(
        self,
        model: str = "wav2vec2",  # or "opensmile", "ensemble"
        device: str = "mps",       # or "cpu", "cuda"
        streaming: bool = False
    ):
        ...

    def analyze(
        self,
        audio: Union[str, Path, np.ndarray],
        sample_rate: int = 16000
    ) -> EmotionResult:
        """Analyze complete audio file or array."""
        ...

    def analyze_streaming(
        self,
        chunk: np.ndarray,
        sample_rate: int = 16000
    ) -> Optional[EmotionResult]:
        """
        Analyze audio chunk in real-time.
        Returns result every ~2 seconds of accumulated audio.
        """
        ...

    def get_emotion_history(
        self,
        window_seconds: float = 60.0
    ) -> List[EmotionResult]:
        """Get recent emotion detections for trend analysis."""
        ...

    def get_emotional_trajectory(self) -> dict:
        """
        Analyze how emotion changed over conversation.
        Returns: {"trend": "improving/declining/stable", "shifts": [...]}
        """
        ...
```

### Integration with SAM

```python
# In sam_api.py or cognitive engine

class SAMCognitiveState:
    """Enhanced cognitive state with voice emotion"""

    def __init__(self):
        self.voice_emotion = VoiceEmotionDetector()
        self.current_emotion: Optional[EmotionResult] = None
        self.emotion_history: List[EmotionResult] = []

    def process_voice_input(self, audio_path: str) -> str:
        """Process voice input with emotion detection."""

        # 1. Detect emotion from audio
        emotion = self.voice_emotion.analyze(audio_path)
        self.current_emotion = emotion
        self.emotion_history.append(emotion)

        # 2. Transcribe speech (existing Whisper pipeline)
        text = transcribe(audio_path)

        # 3. Build context for LLM
        emotion_context = self._build_emotion_context(emotion)

        # 4. Generate response with emotional awareness
        response = self.generate_response(
            text=text,
            emotion_context=emotion_context
        )

        return response

    def _build_emotion_context(self, emotion: EmotionResult) -> str:
        """Build natural language description of detected emotion."""

        top_emotion = emotion.categorical[0]
        intensity = top_emotion.intensity.value

        context = f"[User's voice sounds {intensity}ly {top_emotion.emotion.value}. "

        if emotion.primary.arousal > 0.7:
            context += "They seem agitated/activated. "
        elif emotion.primary.arousal < 0.3:
            context += "They seem low-energy/subdued. "

        if emotion.prosodic.voice_tremor:
            context += "There's a slight tremor in their voice. "

        if emotion.prosodic.speech_rate_category == "fast":
            context += "They're speaking quickly. "

        if emotion.prosodic.hesitation_count > 2:
            context += "They seem hesitant/uncertain. "

        context += "]"

        return context
```

---

## Real-Time Pipeline

```
Microphone Input (continuous)
         │
         ▼
┌─────────────────────┐
│  Audio Buffer       │  Accumulate 2-3 seconds
│  (ring buffer)      │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Voice Activity     │  Detect speech vs silence
│  Detection (VAD)    │
└─────────────────────┘
         │ (speech segments)
         ▼
┌─────────────────────┐
│  Feature Extraction │  OpenSMILE or Wav2Vec2
│  (async thread)     │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Emotion Inference  │  Multi-task model
│  (batched)          │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  Smoothing          │  Exponential moving average
│  (reduce jitter)    │  α = 0.3
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│  SAM Cognitive      │  Feed into response generation
│  State Update       │
└─────────────────────┘
```

---

## Reusability Architecture

### Project-Agnostic Design

```
voice_emotion/
├── __init__.py
├── detector.py          # Main VoiceEmotionDetector class
├── models/
│   ├── wav2vec2.py      # Wav2Vec2 backend
│   ├── opensmile.py     # OpenSMILE backend
│   └── ensemble.py      # Combined approach
├── features/
│   ├── prosodic.py      # Pitch, energy, timing
│   ├── spectral.py      # MFCCs, formants
│   └── quality.py       # Voice quality measures
├── taxonomy.py          # Emotion categories and mappings
├── streaming.py         # Real-time detection
├── visualization.py     # Emotion plots, trajectories
└── integrations/
    ├── sam.py           # SAM-specific integration
    ├── webhook.py       # Generic webhook callbacks
    └── websocket.py     # Real-time streaming API
```

### Configuration

```yaml
# voice_emotion_config.yaml
model:
  backend: "wav2vec2"  # or "opensmile", "ensemble"
  device: "mps"
  weights_path: null   # Use default, or specify custom

detection:
  min_audio_length_ms: 500
  max_audio_length_ms: 30000
  vad_threshold: 0.5

taxonomy:
  enabled_emotions:
    - anxious
    - nervous
    - frustrated
    - stressed
    - sad
    - tired
    - excited
    - happy
    - playful
    - calm
    - neutral

  # Map similar emotions for simpler output
  collapse_similar: true
  collapse_map:
    nervous: anxious
    stressed: anxious

streaming:
  buffer_seconds: 2.0
  overlap_seconds: 0.5
  smoothing_alpha: 0.3

output:
  include_prosodic_markers: true
  include_primary_dimensions: true
  confidence_threshold: 0.4
```

---

## Performance Targets

| Metric | Target | Notes |
|--------|--------|-------|
| Latency (file) | < 500ms | For 5s audio clip |
| Latency (streaming) | < 100ms | Per chunk update |
| Memory | < 1GB | On 8GB M2 |
| Accuracy (6-class) | > 70% | On IEMOCAP test set |
| Accuracy (26-class) | > 55% | Harder task |
| False positive (extreme) | < 5% | Don't cry wolf on "angry" |

---

## Implementation Phases

### Phase 1: Core Detection (Week 1)
- [ ] Set up Wav2Vec2 with MLX
- [ ] Implement basic 6-emotion detection
- [ ] Test on RAVDESS dataset
- [ ] Create simple API

### Phase 2: Nuanced Emotions (Week 2)
- [ ] Expand to 26-emotion taxonomy
- [ ] Add prosodic marker extraction
- [ ] Implement primary dimensions (VAD)
- [ ] Train/fine-tune on combined datasets

### Phase 3: Integration (Week 3)
- [ ] Wire into SAM cognitive state
- [ ] Add streaming support
- [ ] Create visualization dashboard
- [ ] Test with real conversations

### Phase 4: Polish (Week 4)
- [ ] Emotion trajectory tracking
- [ ] Confidence calibration
- [ ] Edge case handling
- [ ] Documentation

---

## Example Outputs

### Anxious User
```json
{
  "primary": {"valence": -0.3, "arousal": 0.75, "dominance": 0.25},
  "categorical": [
    {"emotion": "anxious", "confidence": 0.78, "intensity": "moderate"},
    {"emotion": "nervous", "confidence": 0.52, "intensity": "slight"}
  ],
  "prosodic": {
    "pitch_elevated": true,
    "speech_rate_category": "fast",
    "voice_tremor": true,
    "hesitation_count": 4
  }
}
```

### Frustrated User
```json
{
  "primary": {"valence": -0.5, "arousal": 0.65, "dominance": 0.6},
  "categorical": [
    {"emotion": "frustrated", "confidence": 0.85, "intensity": "strong"},
    {"emotion": "impatient", "confidence": 0.45, "intensity": "moderate"}
  ],
  "prosodic": {
    "pitch_elevated": false,
    "speech_rate_category": "fast",
    "voice_tremor": false,
    "hesitation_count": 1
  }
}
```

### Sad User
```json
{
  "primary": {"valence": -0.6, "arousal": 0.2, "dominance": 0.2},
  "categorical": [
    {"emotion": "sad", "confidence": 0.72, "intensity": "moderate"},
    {"emotion": "tired", "confidence": 0.38, "intensity": "slight"}
  ],
  "prosodic": {
    "pitch_elevated": false,
    "speech_rate_category": "slow",
    "voice_tremor": false,
    "hesitation_count": 2,
    "pause_ratio": 0.35
  }
}
```

---

## References

1. Russell, J.A. (1980). A circumplex model of affect.
2. Eyben, F. et al. (2016). The Geneva Minimalistic Acoustic Parameter Set (GeMAPS).
3. Baevski, A. et al. (2020). wav2vec 2.0: A Framework for Self-Supervised Learning of Speech Representations.
4. Pepino, L. et al. (2021). Emotion Recognition from Speech Using wav2vec 2.0 Embeddings.
