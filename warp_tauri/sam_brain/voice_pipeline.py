"""
SAM Voice Pipeline - Complete voice interaction system

Wires together:
- Emotion detection (emotion2vec_mlx)
- Natural conversation (conversation_engine)
- Prosody control for TTS
- Integration with SAM's cognitive systems

This is the main entry point for voice-based interaction with SAM.

Usage:
    from voice_pipeline import SAMVoicePipeline

    pipeline = SAMVoicePipeline()
    pipeline.start()

    # Stream audio from microphone
    for chunk in mic_stream:
        for event in pipeline.process_audio(chunk):
            if event.audio is not None:
                play_audio(event.audio)
"""

import time
import threading
from pathlib import Path
from typing import Optional, Callable, Generator, Any
from dataclasses import dataclass
import numpy as np

# Emotion system
from emotion2vec_mlx import (
    VoiceEmotionDetector,
    EmotionToProsody,
    ProsodyApplicator,
    EmotionResult
)

# Conversation engine
from conversation_engine import (
    ConversationEngine,
    ConversationMode,
    ConversationEvent,
    EventType,
    ConversationState
)


@dataclass
class VoicePipelineConfig:
    """Configuration for the voice pipeline."""

    # Audio settings
    sample_rate: int = 16000
    chunk_size_ms: int = 100

    # Emotion detection
    emotion_backend: str = "prosodic"  # or "whisper_mlx", "emotion2vec"
    emotion_update_interval_ms: int = 500

    # Conversation
    conversation_mode: str = "components"
    enable_backchannels: bool = True
    backchannel_probability: float = 0.25

    # Prosody
    response_strategy: str = "complement"  # or "match", "amplify", "neutral"
    prosody_intensity: float = 0.8

    # TTS/RVC integration
    rvc_enabled: bool = True
    rvc_model: str = "dustin_steele"  # Once trained

    # Performance
    enable_speculative_generation: bool = True
    max_response_tokens: int = 150


class SAMVoicePipeline:
    """
    Complete voice interaction pipeline for SAM.

    Integrates:
    1. Audio input processing
    2. Emotion detection from user's voice
    3. Natural turn-taking and conversation flow
    4. Emotionally-aware response generation
    5. Prosody-controlled speech synthesis
    6. Voice cloning via RVC

    Designed for real-time, natural conversation.
    """

    def __init__(
        self,
        config: Optional[VoicePipelineConfig] = None,
        # External callbacks
        llm_generate: Optional[Callable] = None,
        tts_synthesize: Optional[Callable] = None,
        rvc_convert: Optional[Callable] = None,
    ):
        """
        Initialize the voice pipeline.

        Args:
            config: Pipeline configuration
            llm_generate: Function(text, context) -> response_text
            tts_synthesize: Function(text, prosody) -> audio
            rvc_convert: Function(audio, params) -> converted_audio
        """
        self.config = config or VoicePipelineConfig()

        # Initialize emotion detector
        self._emotion_detector = VoiceEmotionDetector(
            backend=self.config.emotion_backend
        )

        # Initialize prosody mapper
        self._prosody_mapper = EmotionToProsody()
        self._prosody_applicator = ProsodyApplicator()

        # Initialize conversation engine
        self._conversation = ConversationEngine(
            mode=ConversationMode(self.config.conversation_mode)
        )

        # Set up conversation callbacks
        self._setup_conversation_callbacks(llm_generate, tts_synthesize)

        # External functions
        self._llm_generate = llm_generate
        self._tts_synthesize = tts_synthesize
        self._rvc_convert = rvc_convert

        # State
        self._running = False
        self._current_emotion: Optional[EmotionResult] = None
        self._last_emotion_update = 0
        self._audio_buffer: list = []

        # Statistics
        self._stats = {
            "utterances_processed": 0,
            "responses_generated": 0,
            "backchannels_emitted": 0,
            "interrupts_handled": 0,
            "emotion_detections": 0
        }

    def _setup_conversation_callbacks(
        self,
        llm_generate: Optional[Callable],
        tts_synthesize: Optional[Callable]
    ):
        """Wire up the conversation engine with our functions."""

        # Transcription - use Whisper MLX when available
        def transcribe(audio: np.ndarray, partial: bool = False) -> str:
            # TODO: Wire to mlx-whisper
            # For now, placeholder
            return "[transcription placeholder]"

        # Response generation with emotion context
        def generate(user_text: str, context: dict) -> str:
            if not llm_generate:
                return f"I hear you saying: {user_text[:50]}..."

            # Build emotion-aware prompt
            emotion_context = ""
            if self._current_emotion:
                emotion_context = self._current_emotion.to_context_string()

            full_context = {
                **context,
                "user_emotion": emotion_context
            }

            return llm_generate(user_text, full_context)

        # Speech synthesis with prosody
        def synthesize(text: str, emotion: str = "neutral") -> np.ndarray:
            if not tts_synthesize:
                return np.zeros(16000)  # 1 second silence

            # Get prosody for response emotion
            from emotion2vec_mlx import EmotionCategory
            try:
                emotion_cat = EmotionCategory(emotion)
            except:
                emotion_cat = EmotionCategory.NEUTRAL

            prosody = self._prosody_mapper.get_prosody(
                emotion_cat,
                intensity=self.config.prosody_intensity
            )

            # Generate base audio
            audio = tts_synthesize(text, prosody)

            # Apply RVC if enabled
            if self._rvc_convert and self.config.rvc_enabled:
                rvc_params = self._prosody_applicator.get_rvc_params(prosody)
                audio = self._rvc_convert(audio, rvc_params)

            return audio

        # Emotion detection
        def detect_emotion(audio: np.ndarray) -> EmotionResult:
            return self._emotion_detector.analyze(audio)

        # Set callbacks
        self._conversation.set_transcribe_function(transcribe)
        self._conversation.set_generate_function(generate)
        self._conversation.set_synthesize_function(synthesize)
        self._conversation.set_emotion_function(detect_emotion)

    def start(self):
        """Start the voice pipeline."""
        self._running = True
        self._conversation.start()
        print("SAM Voice Pipeline started")
        print(f"  Emotion backend: {self.config.emotion_backend}")
        print(f"  Response strategy: {self.config.response_strategy}")
        print(f"  RVC enabled: {self.config.rvc_enabled}")

    def stop(self):
        """Stop the voice pipeline."""
        self._running = False
        self._conversation.stop()
        print("SAM Voice Pipeline stopped")

    def process_audio(
        self,
        audio_chunk: np.ndarray
    ) -> Generator[ConversationEvent, None, None]:
        """
        Process an audio chunk from the microphone.

        This is the main entry point - call continuously with audio.

        Args:
            audio_chunk: Audio samples (16kHz, mono, float32)

        Yields:
            ConversationEvent objects (backchannels, responses, etc.)
        """
        if not self._running:
            return

        # Buffer audio for emotion detection
        self._audio_buffer.append(audio_chunk)
        buffer_duration = sum(len(c) for c in self._audio_buffer) / self.config.sample_rate * 1000

        # Periodic emotion update
        current_time = time.time() * 1000
        if current_time - self._last_emotion_update > self.config.emotion_update_interval_ms:
            if buffer_duration > 500:  # Need at least 500ms
                self._update_emotion()
                self._last_emotion_update = current_time

        # Process through conversation engine
        for event in self._conversation.process_audio(audio_chunk):
            # Track statistics
            self._update_stats(event)

            # Enhance event with current emotion context
            if hasattr(event, 'metadata'):
                event.metadata['user_emotion'] = (
                    self._current_emotion.primary_emotion.value
                    if self._current_emotion else "unknown"
                )

            yield event

    def _update_emotion(self):
        """Update emotion detection from buffered audio."""
        if not self._audio_buffer:
            return

        # Combine recent audio
        audio = np.concatenate(self._audio_buffer[-20:])  # Last ~2 seconds

        # Detect emotion
        self._current_emotion = self._emotion_detector.analyze(audio)
        self._stats["emotion_detections"] += 1

        # Trim buffer
        if len(self._audio_buffer) > 30:
            self._audio_buffer = self._audio_buffer[-20:]

    def _update_stats(self, event: ConversationEvent):
        """Update statistics from event."""
        if event.type == EventType.USER_FINISHED:
            self._stats["utterances_processed"] += 1
        elif event.type == EventType.RESPONSE_START:
            self._stats["responses_generated"] += 1
        elif event.type == EventType.BACKCHANNEL:
            self._stats["backchannels_emitted"] += 1
        elif event.type == EventType.USER_INTERRUPT:
            self._stats["interrupts_handled"] += 1

    def get_current_emotion(self) -> Optional[EmotionResult]:
        """Get the current detected user emotion."""
        return self._current_emotion

    def get_conversation_state(self) -> ConversationState:
        """Get the current conversation state."""
        return self._conversation.get_state()

    def get_stats(self) -> dict:
        """Get pipeline statistics."""
        return {
            **self._stats,
            "conversation": self._conversation.get_stats(),
            "emotion_detector": self._emotion_detector.get_stats()
        }

    def get_emotional_trajectory(self) -> dict:
        """Get how user's emotion has changed over conversation."""
        return self._emotion_detector.get_trajectory()

    # Configuration methods

    def set_response_strategy(self, strategy: str):
        """
        Set how SAM responds emotionally.

        Args:
            strategy: "complement" (calm if anxious), "match", "amplify", "neutral"
        """
        self.config.response_strategy = strategy

    def set_backchannel_probability(self, probability: float):
        """Set probability of emitting backchannels (0-1)."""
        self.config.backchannel_probability = probability
        self._conversation.config.backchannel_probability = probability

    def enable_rvc(self, enabled: bool = True, model: str = None):
        """Enable/disable RVC voice cloning."""
        self.config.rvc_enabled = enabled
        if model:
            self.config.rvc_model = model

    # Integration helpers

    def create_sam_integration(self) -> dict:
        """
        Create integration hooks for SAM's main system.

        Returns dict of functions to wire into SAM's orchestrator.
        """
        return {
            "process_voice_input": self.process_audio,
            "get_user_emotion": self.get_current_emotion,
            "get_conversation_state": self.get_conversation_state,
            "set_response_strategy": self.set_response_strategy,
        }


# Convenience function for quick setup
def create_voice_pipeline(
    llm_fn: Callable = None,
    tts_fn: Callable = None,
    rvc_fn: Callable = None,
    **config_kwargs
) -> SAMVoicePipeline:
    """
    Create a voice pipeline with optional custom functions.

    Args:
        llm_fn: LLM generation function
        tts_fn: TTS synthesis function
        rvc_fn: RVC conversion function
        **config_kwargs: Override config options

    Returns:
        Configured SAMVoicePipeline
    """
    config = VoicePipelineConfig(**config_kwargs)
    return SAMVoicePipeline(
        config=config,
        llm_generate=llm_fn,
        tts_synthesize=tts_fn,
        rvc_convert=rvc_fn
    )


# Demo/test
if __name__ == "__main__":
    print("SAM Voice Pipeline")
    print("=" * 50)

    # Create pipeline with defaults
    pipeline = SAMVoicePipeline()

    print("\nPipeline created with:")
    print(f"  Emotion backend: {pipeline.config.emotion_backend}")
    print(f"  Response strategy: {pipeline.config.response_strategy}")
    print(f"  Backchannels: {pipeline.config.enable_backchannels}")

    print("\nTo use with real audio:")
    print("""
    pipeline.start()

    # In your audio callback:
    for chunk in microphone_stream:
        for event in pipeline.process_audio(chunk):
            if event.type == EventType.RESPONSE_START:
                play_audio(event.audio)
            elif event.type == EventType.BACKCHANNEL:
                play_audio(generate_backchannel_audio(event.text))
    """)
