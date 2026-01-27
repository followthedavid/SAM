"""
Conversation State - Tracks the current state of the conversation

Manages:
- Who is currently speaking
- Turn history
- Emotion trajectory
- Backchannel timing
- Response preparation state
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any
import time


class Speaker(Enum):
    """Who is currently speaking."""
    NOBODY = "nobody"
    USER = "user"
    SAM = "sam"
    BOTH = "both"  # Full duplex: both speaking


class ConversationPhase(Enum):
    """High-level conversation phase."""
    IDLE = "idle"                  # No active conversation
    LISTENING = "listening"        # Waiting for user
    USER_SPEAKING = "user_speaking"
    PROCESSING = "processing"      # SAM is thinking
    SAM_SPEAKING = "sam_speaking"
    OVERLAP = "overlap"            # Both speaking (interrupt or duplex)


@dataclass
class TurnInfo:
    """Information about a single turn."""
    speaker: Speaker
    text: str
    start_time: float
    end_time: Optional[float] = None
    emotion: str = "neutral"
    was_interrupted: bool = False
    backchannel_count: int = 0


@dataclass
class ConversationState:
    """
    Full state of the current conversation.

    Updated continuously by the ConversationEngine.
    """

    # Current state
    phase: ConversationPhase = ConversationPhase.IDLE
    current_speaker: Speaker = Speaker.NOBODY

    # Turn tracking
    turns: List[TurnInfo] = field(default_factory=list)
    current_turn_start: Optional[float] = None

    # User state
    user_partial_text: str = ""
    user_final_text: str = ""
    user_emotion: str = "neutral"
    user_arousal: float = 0.5
    user_valence: float = 0.0

    # SAM state
    sam_response_text: str = ""
    sam_response_emotion: str = "neutral"
    sam_is_preparing_response: bool = False
    sam_speculative_responses: List[str] = field(default_factory=list)

    # Timing
    last_user_audio_time: float = 0.0
    last_sam_audio_time: float = 0.0
    last_backchannel_time: float = 0.0
    conversation_start_time: Optional[float] = None

    # Backchannel tracking
    recent_backchannels: List[str] = field(default_factory=list)
    backchannel_count: int = 0

    # Interrupt tracking
    interrupt_count: int = 0
    sam_was_interrupted: bool = False

    # Audio buffers
    user_audio_buffer: List[Any] = field(default_factory=list)
    sam_audio_queue: List[Any] = field(default_factory=list)

    def start_conversation(self):
        """Initialize a new conversation."""
        self.phase = ConversationPhase.LISTENING
        self.current_speaker = Speaker.NOBODY
        self.conversation_start_time = time.time()
        self.turns = []

    def end_conversation(self):
        """End the current conversation."""
        self.phase = ConversationPhase.IDLE
        self.current_speaker = Speaker.NOBODY

    def user_started_speaking(self, initial_text: str = ""):
        """User began speaking."""
        self.phase = ConversationPhase.USER_SPEAKING
        self.current_speaker = Speaker.USER
        self.current_turn_start = time.time()
        self.user_partial_text = initial_text
        self.last_user_audio_time = time.time()

    def user_finished_speaking(self, final_text: str, emotion: str = "neutral"):
        """User finished their turn."""
        turn = TurnInfo(
            speaker=Speaker.USER,
            text=final_text,
            start_time=self.current_turn_start or time.time(),
            end_time=time.time(),
            emotion=emotion
        )
        self.turns.append(turn)

        self.user_final_text = final_text
        self.user_emotion = emotion
        self.phase = ConversationPhase.PROCESSING

    def sam_started_speaking(self, response_text: str, emotion: str = "neutral"):
        """SAM began responding."""
        self.phase = ConversationPhase.SAM_SPEAKING
        self.current_speaker = Speaker.SAM
        self.current_turn_start = time.time()
        self.sam_response_text = response_text
        self.sam_response_emotion = emotion
        self.last_sam_audio_time = time.time()

    def sam_finished_speaking(self):
        """SAM finished responding."""
        turn = TurnInfo(
            speaker=Speaker.SAM,
            text=self.sam_response_text,
            start_time=self.current_turn_start or time.time(),
            end_time=time.time(),
            emotion=self.sam_response_emotion,
            was_interrupted=self.sam_was_interrupted,
            backchannel_count=self.backchannel_count
        )
        self.turns.append(turn)

        self.phase = ConversationPhase.LISTENING
        self.current_speaker = Speaker.NOBODY
        self.sam_was_interrupted = False
        self.backchannel_count = 0

    def handle_interrupt(self, user_text: str = ""):
        """User interrupted SAM."""
        self.sam_was_interrupted = True
        self.interrupt_count += 1
        self.phase = ConversationPhase.OVERLAP
        self.current_speaker = Speaker.BOTH
        self.user_partial_text = user_text

    def emit_backchannel(self, backchannel: str):
        """Record that a backchannel was emitted."""
        self.recent_backchannels.append(backchannel)
        if len(self.recent_backchannels) > 10:
            self.recent_backchannels.pop(0)
        self.last_backchannel_time = time.time()
        self.backchannel_count += 1

    def should_backchannel(self) -> bool:
        """Determine if it's appropriate to emit a backchannel."""
        # Don't backchannel if we just did
        time_since_last = time.time() - self.last_backchannel_time
        if time_since_last < 2.0:  # At least 2 seconds between backchannels
            return False

        # Don't backchannel if SAM is speaking
        if self.current_speaker == Speaker.SAM:
            return False

        # Don't backchannel too frequently
        if self.backchannel_count > 3:
            return False

        return True

    def get_context_for_response(self) -> Dict[str, Any]:
        """Get conversation context for response generation."""
        return {
            "user_text": self.user_final_text,
            "user_emotion": self.user_emotion,
            "user_arousal": self.user_arousal,
            "user_valence": self.user_valence,
            "turn_count": len(self.turns),
            "was_interrupted": self.sam_was_interrupted,
            "recent_turns": [
                {"speaker": t.speaker.value, "text": t.text[:100], "emotion": t.emotion}
                for t in self.turns[-5:]
            ]
        }

    def get_timing_stats(self) -> Dict[str, float]:
        """Get conversation timing statistics."""
        if not self.conversation_start_time:
            return {}

        total_duration = time.time() - self.conversation_start_time
        user_time = sum(
            (t.end_time or 0) - t.start_time
            for t in self.turns if t.speaker == Speaker.USER
        )
        sam_time = sum(
            (t.end_time or 0) - t.start_time
            for t in self.turns if t.speaker == Speaker.SAM
        )

        return {
            "total_duration_s": total_duration,
            "user_speaking_s": user_time,
            "sam_speaking_s": sam_time,
            "turn_count": len(self.turns),
            "interrupts": self.interrupt_count,
            "backchannels": sum(t.backchannel_count for t in self.turns)
        }
