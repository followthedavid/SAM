"""
Conversation Engine - Natural Voice Interaction for SAM

Full-duplex capable conversation system with:
- Continuous listening (even while speaking)
- Neural turn-taking prediction
- Backchannel generation ("mhm", "yeah")
- Interrupt handling
- Speculative response caching
- Emotion-aware prosody

Architecture supports backend swapping:
- "components" mode: Whisper + LLM + TTS (current, works on 8GB)
- "moshi" mode: Full duplex Moshi-7B (future, needs 4-bit quant)
- "cloud" mode: Gemini Live API (future, best quality)

Usage:
    from conversation_engine import ConversationEngine

    engine = ConversationEngine(mode="components")
    engine.start()

    # Feed audio continuously
    for chunk in audio_stream:
        events = engine.process_audio(chunk)
        for event in events:
            if event.type == "backchannel":
                play_audio(event.audio)
            elif event.type == "response":
                play_audio(event.audio)
            elif event.type == "interrupt":
                stop_playback()
"""

from .engine import ConversationEngine, ConversationMode
from .events import (
    ConversationEvent, EventType,
    BackchannelEvent, ResponseEvent, InterruptEvent
)
from .turn_predictor import TurnPredictor
from .state import ConversationState

__version__ = "0.1.0"
__all__ = [
    "ConversationEngine",
    "ConversationMode",
    "ConversationEvent",
    "EventType",
    "BackchannelEvent",
    "ResponseEvent",
    "InterruptEvent",
    "TurnPredictor",
    "ConversationState",
]
