#!/usr/bin/env python3
"""
SAM Thinking Display - Animated Thinking States

Like Warp's cycling transparent thoughts while processing.
Provides streams of thinking verbs that cycle during LLM inference.

Features:
- Cycling thinking verbs with smooth transitions
- Context-aware thoughts based on task type
- Transparent/faded styling hints for frontend
- Progress stages for longer tasks
"""

import time
import random
import threading
from typing import Optional, Generator, Callable
from dataclasses import dataclass, field
from enum import Enum
import json

# Import our thinking verbs
try:
    from thinking_verbs import (
        get_thinking_verb, get_verb_with_definition,
        get_loading_sequence, ROUTE_VERB_MAP, VERBS_BY_CATEGORY
    )
except ImportError:
    # Fallback if not available
    def get_thinking_verb(route=None, category=None, with_definition=False):
        verbs = ["Thinking", "Processing", "Analyzing", "Computing"]
        v = random.choice(verbs)
        if with_definition:
            return (v, "Working on it")
        return v

    def get_loading_sequence(count=5, route=None):
        return [("Thinking", "Working on it")] * count


class ThinkingState(Enum):
    IDLE = "idle"
    STARTING = "starting"
    THINKING = "thinking"
    DEEP_THINKING = "deep_thinking"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class ThinkingFrame:
    """A single frame of the thinking animation"""
    verb: str
    definition: str
    state: ThinkingState
    progress: float  # 0.0 to 1.0
    elapsed_seconds: float
    opacity: float = 0.7  # For transparent effect (0.0 = invisible, 1.0 = solid)
    is_transitioning: bool = False


@dataclass
class ThinkingSession:
    """Tracks a thinking session"""
    id: str
    route: str
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    state: ThinkingState = ThinkingState.STARTING
    current_verb: str = "Starting"
    frames_generated: int = 0

    @property
    def elapsed(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    @property
    def is_active(self) -> bool:
        return self.state not in (ThinkingState.COMPLETE, ThinkingState.ERROR)


class ThinkingDisplay:
    """
    Manages thinking display animations.

    Usage:
        display = ThinkingDisplay()

        # Start a thinking session
        session = display.start_session("code")

        # Generate frames (for frontend polling)
        for frame in display.stream_frames(session.id, interval=0.5):
            print(f"{frame.verb}... ({frame.definition})")
            if some_condition:
                break

        # Or get a single frame
        frame = display.get_frame(session.id)

        # Complete the session
        display.complete_session(session.id, success=True)
    """

    def __init__(self):
        self.sessions: dict[str, ThinkingSession] = {}
        self._lock = threading.Lock()
        self._frame_counter = 0

    def start_session(self, route: str = "chat", session_id: Optional[str] = None) -> ThinkingSession:
        """Start a new thinking session"""
        session_id = session_id or f"think_{int(time.time() * 1000)}"

        session = ThinkingSession(
            id=session_id,
            route=route,
            state=ThinkingState.STARTING
        )

        with self._lock:
            self.sessions[session_id] = session

        return session

    def get_session(self, session_id: str) -> Optional[ThinkingSession]:
        """Get a session by ID"""
        return self.sessions.get(session_id)

    def get_frame(self, session_id: str) -> Optional[ThinkingFrame]:
        """Get the current thinking frame for a session"""
        session = self.sessions.get(session_id)
        if not session or not session.is_active:
            return None

        elapsed = session.elapsed
        self._frame_counter += 1

        # Determine state based on elapsed time
        if elapsed < 0.5:
            state = ThinkingState.STARTING
            progress = elapsed / 0.5
        elif elapsed < 3.0:
            state = ThinkingState.THINKING
            progress = (elapsed - 0.5) / 2.5
        elif elapsed < 10.0:
            state = ThinkingState.DEEP_THINKING
            progress = (elapsed - 3.0) / 7.0
        else:
            state = ThinkingState.DEEP_THINKING
            progress = min(1.0, (elapsed - 10.0) / 20.0)

        # Get a contextual verb
        verb, definition = get_thinking_verb(route=session.route, with_definition=True)

        # Update session
        session.state = state
        session.current_verb = verb
        session.frames_generated += 1

        # Calculate opacity (fade in/out for transitions)
        # Pulse between 0.5 and 0.9 for organic feel
        cycle = (elapsed * 2) % 1.0
        opacity = 0.5 + 0.4 * abs(cycle - 0.5) * 2

        return ThinkingFrame(
            verb=verb,
            definition=definition,
            state=state,
            progress=progress,
            elapsed_seconds=elapsed,
            opacity=opacity,
            is_transitioning=self._frame_counter % 3 == 0  # Transition every 3rd frame
        )

    def stream_frames(
        self,
        session_id: str,
        interval: float = 0.5,
        max_frames: int = 100
    ) -> Generator[ThinkingFrame, None, None]:
        """
        Generator that yields thinking frames at regular intervals.

        Use this for real-time streaming to frontend.
        """
        session = self.sessions.get(session_id)
        if not session:
            return

        frame_count = 0
        last_verb = None

        while session.is_active and frame_count < max_frames:
            frame = self.get_frame(session_id)
            if frame:
                # Avoid repeating the same verb twice in a row
                if frame.verb == last_verb:
                    frame = self.get_frame(session_id)  # Get another one
                last_verb = frame.verb
                yield frame
            frame_count += 1
            time.sleep(interval)

    def complete_session(self, session_id: str, success: bool = True) -> Optional[ThinkingSession]:
        """Mark a session as complete"""
        session = self.sessions.get(session_id)
        if session:
            session.state = ThinkingState.COMPLETE if success else ThinkingState.ERROR
            session.end_time = time.time()
        return session

    def get_all_active(self) -> list[ThinkingSession]:
        """Get all active thinking sessions"""
        return [s for s in self.sessions.values() if s.is_active]

    def cleanup_old_sessions(self, max_age_seconds: float = 300):
        """Remove completed sessions older than max_age"""
        cutoff = time.time() - max_age_seconds
        with self._lock:
            to_remove = [
                sid for sid, session in self.sessions.items()
                if not session.is_active and session.end_time and session.end_time < cutoff
            ]
            for sid in to_remove:
                del self.sessions[sid]


# ═══════════════════════════════════════════════════════════════════════════════
# WEBSOCKET / SSE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def frame_to_json(frame: ThinkingFrame) -> str:
    """Convert a frame to JSON for frontend consumption"""
    return json.dumps({
        "verb": frame.verb,
        "definition": frame.definition,
        "state": frame.state.value,
        "progress": frame.progress,
        "elapsed": frame.elapsed_seconds,
        "opacity": frame.opacity,
        "transitioning": frame.is_transitioning,
    })


def frame_to_sse(frame: ThinkingFrame) -> str:
    """Format frame as Server-Sent Event"""
    return f"data: {frame_to_json(frame)}\n\n"


def create_thinking_callback(display: ThinkingDisplay, session_id: str) -> Callable:
    """
    Create a callback function for LLM streaming that updates thinking state.

    Usage with ollama:
        callback = create_thinking_callback(display, session.id)
        # Pass callback to streaming LLM call
    """
    def callback(chunk: str):
        session = display.get_session(session_id)
        if session:
            # Update state based on token generation
            if session.state == ThinkingState.STARTING:
                session.state = ThinkingState.THINKING
    return callback


# ═══════════════════════════════════════════════════════════════════════════════
# TERMINAL DISPLAY (for CLI testing)
# ═══════════════════════════════════════════════════════════════════════════════

def print_thinking_animation(route: str = "chat", duration: float = 5.0):
    """
    Print an animated thinking display to terminal.
    Good for testing and CLI mode.
    """
    import sys

    display = ThinkingDisplay()
    session = display.start_session(route)

    start = time.time()
    last_verb = ""

    print("\n")  # Start with newline

    try:
        while time.time() - start < duration:
            frame = display.get_frame(session.id)
            if frame and frame.verb != last_verb:
                # Clear line and print new verb
                sys.stdout.write(f"\r\033[K")  # Clear line
                # Use ANSI for faded effect (gray color)
                opacity_ansi = "\033[90m" if frame.opacity < 0.7 else "\033[37m"
                reset = "\033[0m"
                sys.stdout.write(f"{opacity_ansi}  {frame.verb}... {reset}")
                sys.stdout.flush()
                last_verb = frame.verb
            time.sleep(0.4)
    except KeyboardInterrupt:
        pass
    finally:
        display.complete_session(session.id)
        sys.stdout.write("\r\033[K")  # Clear line
        print("  ✅ Done!")


def print_thinking_with_progress(route: str = "code", steps: list = None):
    """
    Print thinking with progress through steps.
    """
    import sys

    steps = steps or [
        "Analyzing request",
        "Searching codebase",
        "Generating solution",
        "Formatting response",
    ]

    display = ThinkingDisplay()
    session = display.start_session(route)

    for i, step in enumerate(steps):
        progress = (i + 1) / len(steps)
        verb, defn = get_thinking_verb(route=route, with_definition=True)

        # Progress bar
        filled = int(progress * 20)
        bar = "█" * filled + "░" * (20 - filled)

        print(f"\r\033[K  [{bar}] {step}... ({verb})", end="", flush=True)
        time.sleep(1.0 + random.random())

    display.complete_session(session.id)
    print(f"\r\033[K  [████████████████████] ✅ Complete!")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Thinking Display")
        print("\nUsage:")
        print("  python thinking_display.py demo [route]   # Show animated thinking")
        print("  python thinking_display.py progress       # Show progress animation")
        print("  python thinking_display.py frames [route] # Print frame JSON")
        print("\nRoutes: chat, code, roleplay, reason, image, improve")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "demo":
        route = sys.argv[2] if len(sys.argv) > 2 else "chat"
        print(f"\nSimulating '{route}' thinking for 5 seconds...")
        print_thinking_animation(route, duration=5.0)

    elif cmd == "progress":
        print("\nSimulating multi-step processing...")
        print_thinking_with_progress("code")

    elif cmd == "frames":
        route = sys.argv[2] if len(sys.argv) > 2 else "chat"
        display = ThinkingDisplay()
        session = display.start_session(route)

        print(f"\nGenerating 10 frames for '{route}' route:\n")
        for i, frame in enumerate(display.stream_frames(session.id, interval=0.3, max_frames=10)):
            print(f"Frame {i+1}: {frame_to_json(frame)}")

        display.complete_session(session.id)

    else:
        print(f"Unknown command: {cmd}")
