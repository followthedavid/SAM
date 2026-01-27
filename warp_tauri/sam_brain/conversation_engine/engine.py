"""
Conversation Engine - Main orchestrator for natural voice interaction

This is the core that ties everything together:
- Continuous audio processing
- Turn-taking management
- Backchannel generation
- Response preparation
- Interrupt handling

Designed for future upgrade to full-duplex (Moshi-style).
"""

import time
import threading
import queue
from dataclasses import dataclass
from enum import Enum
from typing import Optional, List, Callable, Generator, Any
import numpy as np

from .state import ConversationState, Speaker, ConversationPhase
from .turn_predictor import TurnPredictor, TurnPrediction
from .events import (
    ConversationEvent, EventType,
    BackchannelEvent, ResponseEvent, InterruptEvent,
    UserSpeakingEvent, UserFinishedEvent, TurnChangeEvent,
    select_backchannel
)


class ConversationMode(Enum):
    """Backend mode for conversation processing."""
    COMPONENTS = "components"  # Whisper + LLM + TTS (current)
    MOSHI = "moshi"            # Full duplex Moshi (future)
    CLOUD = "cloud"            # Cloud API like Gemini Live (future)


@dataclass
class EngineConfig:
    """Configuration for the conversation engine."""

    # Turn-taking
    turn_end_threshold: float = 0.75  # Probability threshold to end turn
    max_silence_ms: int = 2000        # Max silence before forcing turn end
    min_turn_duration_ms: int = 500   # Min duration before considering turn end

    # Backchannels
    enable_backchannels: bool = True
    backchannel_probability: float = 0.3  # Chance to backchannel at valid point
    min_backchannel_interval_ms: int = 3000

    # Response timing
    min_response_delay_ms: int = 150
    max_response_delay_ms: int = 800
    thinking_sound_threshold_ms: int = 1000  # Emit "hmm" if taking longer

    # Interrupts
    allow_user_interrupt: bool = True
    interrupt_threshold_ms: int = 300  # How long user speaks before it's interrupt

    # Audio
    sample_rate: int = 16000
    chunk_duration_ms: int = 100  # Process audio in 100ms chunks

    # Advanced
    enable_speculative_generation: bool = True
    speculative_cache_size: int = 3


class ConversationEngine:
    """
    Main conversation engine.

    Manages the flow of a natural conversation:
    1. Listens continuously to user audio
    2. Detects when user is done speaking (not just silence)
    3. Emits backchannels at appropriate moments
    4. Prepares responses speculatively
    5. Handles interruptions gracefully
    6. Applies emotional prosody to responses

    Usage:
        engine = ConversationEngine()
        engine.start()

        # In audio callback:
        for event in engine.process_audio(chunk):
            handle_event(event)
    """

    def __init__(
        self,
        mode: ConversationMode = ConversationMode.COMPONENTS,
        config: Optional[EngineConfig] = None,
        # Callbacks for external systems
        transcribe_fn: Optional[Callable] = None,
        generate_fn: Optional[Callable] = None,
        synthesize_fn: Optional[Callable] = None,
        detect_emotion_fn: Optional[Callable] = None,
    ):
        """
        Initialize the conversation engine.

        Args:
            mode: Backend mode (components, moshi, cloud)
            config: Engine configuration
            transcribe_fn: Function to transcribe audio -> text
            generate_fn: Function to generate response text
            synthesize_fn: Function to synthesize audio from text
            detect_emotion_fn: Function to detect emotion from audio
        """
        self.mode = mode
        self.config = config or EngineConfig()

        # External functions
        self._transcribe = transcribe_fn
        self._generate = generate_fn
        self._synthesize = synthesize_fn
        self._detect_emotion = detect_emotion_fn

        # State
        self.state = ConversationState()
        self.turn_predictor = TurnPredictor()

        # Audio buffers
        self._audio_buffer: List[np.ndarray] = []
        self._buffer_duration_ms: float = 0

        # Event queue
        self._event_queue: queue.Queue = queue.Queue()

        # Threading
        self._running = False
        self._processing_thread: Optional[threading.Thread] = None

        # Timing
        self._last_audio_time: float = 0
        self._turn_start_time: float = 0
        self._last_backchannel_time: float = 0

        # Speculative responses
        self._speculative_responses: List[str] = []
        self._preparing_response: bool = False

    def start(self):
        """Start the conversation engine."""
        self._running = True
        self.state.start_conversation()
        self._last_audio_time = time.time()
        print("Conversation engine started")

    def stop(self):
        """Stop the conversation engine."""
        self._running = False
        self.state.end_conversation()
        print("Conversation engine stopped")

    def process_audio(
        self,
        audio_chunk: np.ndarray
    ) -> Generator[ConversationEvent, None, None]:
        """
        Process an audio chunk and yield any events.

        This is the main entry point - call this continuously
        with audio from the microphone.

        Args:
            audio_chunk: Audio samples (16kHz, mono, float32)

        Yields:
            ConversationEvent objects to handle
        """
        if not self._running:
            return

        current_time = time.time()
        chunk_duration_ms = len(audio_chunk) / self.config.sample_rate * 1000

        # Add to buffer
        self._audio_buffer.append(audio_chunk)
        self._buffer_duration_ms += chunk_duration_ms

        # Detect voice activity
        has_speech = self._detect_speech(audio_chunk)

        if has_speech:
            self._last_audio_time = current_time

            # User is speaking
            if self.state.phase == ConversationPhase.SAM_SPEAKING:
                # Interrupt detected!
                if self.config.allow_user_interrupt:
                    yield from self._handle_interrupt()
            else:
                # Normal user speech
                yield from self._handle_user_speech()

        else:
            # Silence
            silence_duration_ms = (current_time - self._last_audio_time) * 1000
            yield from self._handle_silence(silence_duration_ms)

        # Check for backchannel opportunity
        if self.config.enable_backchannels:
            yield from self._check_backchannel()

    def _detect_speech(self, audio: np.ndarray) -> bool:
        """Simple voice activity detection."""
        energy = np.sqrt(np.mean(audio ** 2))
        threshold = 0.01  # Adjustable
        return energy > threshold

    def _handle_user_speech(self) -> Generator[ConversationEvent, None, None]:
        """Handle user speaking."""

        # Transition to user speaking if needed
        if self.state.phase != ConversationPhase.USER_SPEAKING:
            self.state.user_started_speaking()
            self._turn_start_time = time.time()
            self.turn_predictor.reset()

            yield TurnChangeEvent(
                new_speaker="user",
                previous_speaker="sam" if self.state.current_speaker == Speaker.SAM else "nobody",
                reason="user_started"
            )

        # Transcribe incrementally
        if self._transcribe and len(self._audio_buffer) > 5:
            audio = np.concatenate(self._audio_buffer[-10:])
            partial_text = self._transcribe(audio, partial=True)
            self.state.user_partial_text = partial_text

            # Detect emotion if available
            if self._detect_emotion:
                emotion_result = self._detect_emotion(audio)
                self.state.user_emotion = emotion_result.primary_emotion.value
                self.state.user_arousal = emotion_result.primary.arousal
                self.state.user_valence = emotion_result.primary.valence

            yield UserSpeakingEvent(
                partial_text=partial_text,
                turn_end_probability=0.0,
                current_emotion=self.state.user_emotion,
                arousal=self.state.user_arousal
            )

    def _handle_silence(
        self,
        silence_duration_ms: float
    ) -> Generator[ConversationEvent, None, None]:
        """Handle silence (potential turn end)."""

        if self.state.phase != ConversationPhase.USER_SPEAKING:
            return

        # Check minimum turn duration
        turn_duration_ms = (time.time() - self._turn_start_time) * 1000
        if turn_duration_ms < self.config.min_turn_duration_ms:
            return

        # Get turn prediction
        prediction = self.turn_predictor.predict(
            partial_text=self.state.user_partial_text,
            audio_features=None,  # TODO: extract from buffer
            pause_duration_ms=silence_duration_ms
        )

        # Emit user speaking event with prediction
        yield UserSpeakingEvent(
            partial_text=self.state.user_partial_text,
            turn_end_probability=prediction.probability,
            current_emotion=self.state.user_emotion,
            arousal=self.state.user_arousal
        )

        # Check if turn should end
        should_end = (
            prediction.probability >= self.config.turn_end_threshold or
            silence_duration_ms >= self.config.max_silence_ms
        )

        if should_end:
            yield from self._end_user_turn(prediction)

    def _end_user_turn(
        self,
        prediction: TurnPrediction
    ) -> Generator[ConversationEvent, None, None]:
        """End the user's turn and prepare response."""

        # Finalize transcript
        if self._transcribe and self._audio_buffer:
            audio = np.concatenate(self._audio_buffer)
            final_text = self._transcribe(audio, partial=False)
        else:
            final_text = self.state.user_partial_text

        self.state.user_finished_speaking(final_text, self.state.user_emotion)
        self._audio_buffer = []
        self._buffer_duration_ms = 0

        yield UserFinishedEvent(
            text=final_text,
            method=prediction.reason,
            confidence=prediction.confidence,
            emotion=self.state.user_emotion,
            silence_duration_ms=int(self._current_silence_ms())
        )

        # Calculate response delay
        delay_ms = self.turn_predictor.get_optimal_response_delay(
            prediction,
            self.state.user_emotion
        )

        # Start response generation
        yield from self._prepare_response(final_text, delay_ms)

    def _prepare_response(
        self,
        user_text: str,
        delay_ms: int
    ) -> Generator[ConversationEvent, None, None]:
        """Prepare and emit SAM's response."""

        self._preparing_response = True

        # Emit thinking sound if delay is long
        if delay_ms > self.config.thinking_sound_threshold_ms:
            yield BackchannelEvent(
                text="hmm",
                trigger="thinking"
            )

        # Generate response
        if self._generate:
            context = self.state.get_context_for_response()
            response_text = self._generate(user_text, context)
        else:
            response_text = f"[Response to: {user_text[:50]}...]"

        # Determine prosody based on user emotion
        response_emotion = self._select_response_emotion(self.state.user_emotion)

        # Synthesize audio
        if self._synthesize:
            audio = self._synthesize(response_text, emotion=response_emotion)
        else:
            audio = None

        self._preparing_response = False

        # Emit response
        self.state.sam_started_speaking(response_text, response_emotion)

        yield TurnChangeEvent(
            new_speaker="sam",
            previous_speaker="user",
            reason="natural"
        )

        yield ResponseEvent(
            type=EventType.RESPONSE_START,
            text=response_text,
            audio=audio,
            is_final=True,
            emotion=response_emotion
        )

    def _handle_interrupt(self) -> Generator[ConversationEvent, None, None]:
        """Handle user interrupting SAM."""

        self.state.handle_interrupt()

        yield InterruptEvent(
            interrupted_text=self.state.sam_response_text,
            user_text=self.state.user_partial_text
        )

        yield TurnChangeEvent(
            new_speaker="user",
            previous_speaker="sam",
            reason="interrupt"
        )

        # Transition to user speaking
        self.state.user_started_speaking()
        self._turn_start_time = time.time()
        self.turn_predictor.reset()

    def _check_backchannel(self) -> Generator[ConversationEvent, None, None]:
        """Check if we should emit a backchannel."""

        if not self.state.should_backchannel():
            return

        if self.state.phase != ConversationPhase.USER_SPEAKING:
            return

        # Check timing
        time_since_last = (time.time() - self._last_backchannel_time) * 1000
        if time_since_last < self.config.min_backchannel_interval_ms:
            return

        # Check for good backchannel moment (clause boundary, etc.)
        text = self.state.user_partial_text
        good_moment = self._is_backchannel_moment(text)

        if good_moment and np.random.random() < self.config.backchannel_probability:
            # Select appropriate backchannel
            context = self._get_backchannel_context()
            backchannel = select_backchannel(
                context=context,
                emotion=self.state.user_emotion,
                previous_backchannels=self.state.recent_backchannels
            )

            self.state.emit_backchannel(backchannel)
            self._last_backchannel_time = time.time()

            yield BackchannelEvent(
                text=backchannel,
                trigger=context
            )

    def _is_backchannel_moment(self, text: str) -> bool:
        """Detect if current moment is good for backchannel."""
        if not text:
            return False

        # After comma or clause
        if text.rstrip().endswith(","):
            return True

        # After certain phrases
        backchannel_triggers = [
            "you know", "right", "like", "so", "and then",
            "basically", "actually", "honestly"
        ]
        for trigger in backchannel_triggers:
            if text.lower().rstrip().endswith(trigger):
                return True

        return False

    def _get_backchannel_context(self) -> str:
        """Determine context for backchannel selection."""
        text = self.state.user_partial_text.lower()

        if "?" in text[-20:]:
            return "question"
        if self.state.user_emotion in ["sad", "frustrated", "anxious"]:
            return "emotional"
        if any(word in text[-50:] for word in ["agree", "think so", "right"]):
            return "agreement"
        if len(text.split()) > 30:
            return "complex"

        return "general"

    def _select_response_emotion(self, user_emotion: str) -> str:
        """Select appropriate emotion for SAM's response."""
        # Complementary responses
        complements = {
            "anxious": "calm",
            "nervous": "confident",
            "frustrated": "calm",
            "angry": "calm",
            "sad": "affectionate",
            "excited": "excited",
            "happy": "happy",
            "playful": "playful",
            "flirty": "flirty",
        }
        return complements.get(user_emotion, "neutral")

    def _current_silence_ms(self) -> float:
        """Get current silence duration in ms."""
        return (time.time() - self._last_audio_time) * 1000

    # Public API for external integration

    def set_transcribe_function(self, fn: Callable):
        """Set the transcription function."""
        self._transcribe = fn

    def set_generate_function(self, fn: Callable):
        """Set the response generation function."""
        self._generate = fn

    def set_synthesize_function(self, fn: Callable):
        """Set the speech synthesis function."""
        self._synthesize = fn

    def set_emotion_function(self, fn: Callable):
        """Set the emotion detection function."""
        self._detect_emotion = fn

    def get_state(self) -> ConversationState:
        """Get current conversation state."""
        return self.state

    def get_stats(self) -> dict:
        """Get conversation statistics."""
        return {
            **self.state.get_timing_stats(),
            "mode": self.mode.value,
            "running": self._running
        }
