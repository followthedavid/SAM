"""
Conversation Events - Things that happen during a conversation

Events are emitted by the ConversationEngine and should be handled
by the application (play audio, update UI, etc.)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any
import numpy as np
import time


class EventType(Enum):
    """Types of events that can occur during conversation."""

    # Output events (SAM wants to emit audio)
    BACKCHANNEL = "backchannel"      # "mhm", "yeah", "right"
    THINKING = "thinking"             # "hmm...", breath sound
    RESPONSE_START = "response_start" # SAM is about to speak
    RESPONSE_CHUNK = "response_chunk" # Streaming audio chunk
    RESPONSE_END = "response_end"     # SAM finished speaking

    # Input events (user did something)
    USER_SPEAKING = "user_speaking"   # User started talking
    USER_FINISHED = "user_finished"   # User stopped (turn end predicted)
    USER_INTERRUPT = "user_interrupt" # User interrupted SAM

    # State events
    TURN_CHANGE = "turn_change"       # Turn changed (user→SAM or SAM→user)
    EMOTION_CHANGE = "emotion_change" # User's emotion changed significantly
    SILENCE = "silence"               # Extended silence detected

    # System events
    ERROR = "error"
    STATE_UPDATE = "state_update"


@dataclass
class ConversationEvent:
    """Base event class."""
    type: EventType
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


@dataclass
class BackchannelEvent(ConversationEvent):
    """SAM emits a backchannel ("mhm", "yeah", etc.)"""
    type: EventType = EventType.BACKCHANNEL
    text: str = ""           # What to say: "mhm", "yeah", "right", "I see"
    audio: Optional[np.ndarray] = None  # Pre-rendered audio if available

    # Why this backchannel was triggered
    trigger: str = "clause_end"  # "clause_end", "question", "emotion", "silence"


@dataclass
class ThinkingEvent(ConversationEvent):
    """SAM is thinking (emit thinking sound)."""
    type: EventType = EventType.THINKING
    sound: str = "hmm"       # "hmm", "breath", "uh"
    audio: Optional[np.ndarray] = None
    duration_ms: int = 500


@dataclass
class ResponseEvent(ConversationEvent):
    """SAM's response (or chunk of response)."""
    type: EventType = EventType.RESPONSE_START
    text: str = ""
    audio: Optional[np.ndarray] = None

    # For streaming
    is_final: bool = False
    chunk_index: int = 0

    # Prosody applied
    emotion: str = "neutral"
    prosody_params: dict = field(default_factory=dict)


@dataclass
class InterruptEvent(ConversationEvent):
    """User interrupted SAM."""
    type: EventType = EventType.USER_INTERRUPT

    # What SAM was saying when interrupted
    interrupted_text: str = ""
    interrupted_at_word: int = 0

    # What user said that caused interrupt
    user_text: str = ""


@dataclass
class TurnChangeEvent(ConversationEvent):
    """Turn changed between user and SAM."""
    type: EventType = EventType.TURN_CHANGE

    new_speaker: str = ""  # "user" or "sam"
    previous_speaker: str = ""

    # How the turn changed
    reason: str = ""  # "natural", "interrupt", "timeout", "backchannel"


@dataclass
class EmotionChangeEvent(ConversationEvent):
    """User's emotion changed significantly."""
    type: EventType = EventType.EMOTION_CHANGE

    previous_emotion: str = "neutral"
    new_emotion: str = "neutral"
    confidence: float = 0.0

    # Dimensions
    valence_delta: float = 0.0
    arousal_delta: float = 0.0


@dataclass
class UserSpeakingEvent(ConversationEvent):
    """User started or is speaking."""
    type: EventType = EventType.USER_SPEAKING

    # Partial transcript so far
    partial_text: str = ""

    # Turn prediction
    turn_end_probability: float = 0.0  # 0-1, how likely they're done

    # Emotion
    current_emotion: str = "neutral"
    arousal: float = 0.5


@dataclass
class UserFinishedEvent(ConversationEvent):
    """User finished speaking (turn end detected)."""
    type: EventType = EventType.USER_FINISHED

    # Final transcript
    text: str = ""

    # Detection method
    method: str = "turn_predictor"  # "turn_predictor", "silence", "explicit"
    confidence: float = 0.0

    # User state
    emotion: str = "neutral"

    # Time since last word
    silence_duration_ms: int = 0


# Backchannel templates
BACKCHANNELS = {
    "acknowledgment": ["mhm", "yeah", "right", "okay", "I see"],
    "interest": ["oh?", "really?", "interesting", "go on"],
    "agreement": ["exactly", "absolutely", "definitely", "yes"],
    "understanding": ["I understand", "I get it", "makes sense"],
    "empathy": ["I hear you", "that's tough", "I get that"],
    "thinking": ["hmm", "let me think", "well..."],
}


def select_backchannel(
    context: str = "general",
    emotion: str = "neutral",
    previous_backchannels: List[str] = None
) -> str:
    """
    Select an appropriate backchannel.

    Avoids repetition and matches context/emotion.
    """
    import random

    previous = previous_backchannels or []

    # Select category based on context
    if context == "question":
        category = "interest"
    elif context == "emotional":
        category = "empathy"
    elif context == "agreement":
        category = "agreement"
    elif context == "complex":
        category = "thinking"
    else:
        category = "acknowledgment"

    options = BACKCHANNELS.get(category, BACKCHANNELS["acknowledgment"])

    # Filter out recent ones
    available = [b for b in options if b not in previous[-3:]]
    if not available:
        available = options

    return random.choice(available)
