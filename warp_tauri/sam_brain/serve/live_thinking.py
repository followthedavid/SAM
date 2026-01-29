#!/usr/bin/env python3
"""
SAM Live Thinking - Real LLM Thoughts, Not Gimmicks

This module streams REAL LLM output so you can:
- See actual reasoning as it happens
- Catch mistakes early in the thought process
- Interrupt if the model misunderstands
- Watch the model "think through" the problem

This is NOT decorative animation - it's the actual model output.

Updated 2026-01-20: Now uses MLX instead of Ollama (decommissioned 2026-01-18)
"""

import json
import time
import sys
from typing import Generator, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# MLX Cognitive Engine (lazy loaded)
_mlx_engine = None


class ThoughtType(Enum):
    REASONING = "reasoning"      # Chain of thought, analysis
    PLANNING = "planning"        # Steps it plans to take
    CODE = "code"                # Code blocks
    QUESTION = "question"        # Questions it's considering
    CONCLUSION = "conclusion"    # Final answers
    ERROR = "error"              # Error thoughts
    UNCERTAINTY = "uncertainty"  # When model is unsure


@dataclass
class ThoughtChunk:
    """A chunk of live thinking from the LLM"""
    text: str
    thought_type: ThoughtType
    token_count: int
    elapsed_ms: float
    is_complete: bool = False


@dataclass
class ThinkingSession:
    """A complete thinking session"""
    prompt: str
    full_response: str
    chunks: list
    total_tokens: int
    total_time_ms: float
    was_interrupted: bool = False


def classify_thought(text: str) -> ThoughtType:
    """
    Classify a chunk of text by what kind of thinking it represents.
    This helps visually distinguish different types of reasoning.
    """
    text_lower = text.lower()

    # Check for code
    if "```" in text or text.strip().startswith("def ") or text.strip().startswith("class "):
        return ThoughtType.CODE

    # Check for planning language
    planning_words = ["first", "then", "next", "step", "will", "need to", "should", "plan"]
    if any(word in text_lower for word in planning_words):
        return ThoughtType.PLANNING

    # Check for uncertainty
    uncertain_words = ["might", "maybe", "perhaps", "not sure", "could be", "possibly", "uncertain"]
    if any(word in text_lower for word in uncertain_words):
        return ThoughtType.UNCERTAINTY

    # Check for questions
    if "?" in text or text_lower.startswith("what") or text_lower.startswith("how"):
        return ThoughtType.QUESTION

    # Check for conclusions
    conclusion_words = ["therefore", "so the answer", "in conclusion", "the result", "finally"]
    if any(word in text_lower for word in conclusion_words):
        return ThoughtType.CONCLUSION

    # Default to reasoning
    return ThoughtType.REASONING


def get_mlx_engine():
    """Lazy-load the MLX cognitive engine."""
    global _mlx_engine
    if _mlx_engine is None:
        try:
            from cognitive.mlx_cognitive import MLXCognitiveEngine
            _mlx_engine = MLXCognitiveEngine()
        except ImportError as e:
            print(f"Warning: MLX engine not available: {e}", file=sys.stderr)
    return _mlx_engine


def stream_thinking(
    prompt: str,
    model: str = "1.5b",
    system_prompt: Optional[str] = None,
    on_chunk: Optional[Callable[[ThoughtChunk], None]] = None,
    show_live: bool = True
) -> Generator[ThoughtChunk, None, ThinkingSession]:
    """
    Stream the LLM's thinking in real-time using MLX.

    Args:
        prompt: The prompt to send
        model: Model size ("1.5b" or "3b")
        system_prompt: Optional system prompt for reasoning mode
        on_chunk: Callback for each chunk (for frontend integration)
        show_live: Whether to print to stdout in real-time

    Yields:
        ThoughtChunk objects as thinking happens

    Returns:
        ThinkingSession with complete results
    """

    # Default system prompt encourages showing reasoning
    if system_prompt is None:
        system_prompt = """You are SAM, a helpful AI assistant.
Think step by step and show your reasoning process.
Explain what you're considering and why.
If you're uncertain about something, say so."""

    chunks = []
    full_response = ""
    token_count = 0
    start_time = time.time()

    engine = get_mlx_engine()
    if not engine:
        error_chunk = ThoughtChunk(
            text="MLX engine not available",
            thought_type=ThoughtType.ERROR,
            token_count=0,
            elapsed_ms=0,
            is_complete=True
        )
        yield error_chunk
        return ThinkingSession(
            prompt=prompt,
            full_response="",
            chunks=[error_chunk],
            total_tokens=0,
            total_time_ms=0
        )

    try:
        # Build cognitive state for MLX engine
        cognitive_state = {
            "confidence": 0.5,
            "emotional_valence": 0.0,
            "system_prompt_override": system_prompt
        }

        # Context for thinking
        context = f"User wants to understand the reasoning. Be transparent about your thought process."

        buffer = ""

        # Stream from MLX engine
        for token in engine.generate_streaming(
            prompt=prompt,
            context=context,
            cognitive_state=cognitive_state
        ):
            if isinstance(token, str):
                full_response += token
                buffer += token
                token_count += 1

                # Yield chunks at natural break points
                if any(c in token for c in ".!?\n") or len(buffer) > 50:
                    elapsed = (time.time() - start_time) * 1000
                    thought_type = classify_thought(buffer)

                    chunk = ThoughtChunk(
                        text=buffer,
                        thought_type=thought_type,
                        token_count=token_count,
                        elapsed_ms=elapsed,
                        is_complete=False
                    )

                    chunks.append(chunk)

                    if on_chunk:
                        on_chunk(chunk)

                    if show_live:
                        print_chunk(chunk)

                    yield chunk
                    buffer = ""

        # Yield final chunk if buffer has content
        if buffer:
            elapsed = (time.time() - start_time) * 1000
            thought_type = classify_thought(buffer)
            final_chunk = ThoughtChunk(
                text=buffer,
                thought_type=thought_type,
                token_count=token_count,
                elapsed_ms=elapsed,
                is_complete=True
            )
            chunks.append(final_chunk)
            if on_chunk:
                on_chunk(final_chunk)
            if show_live:
                print_chunk(final_chunk)
            yield final_chunk

    except Exception as e:
        error_chunk = ThoughtChunk(
            text=f"Error: {e}",
            thought_type=ThoughtType.ERROR,
            token_count=token_count,
            elapsed_ms=(time.time() - start_time) * 1000,
            is_complete=True
        )
        chunks.append(error_chunk)
        if show_live:
            print_chunk(error_chunk)
        yield error_chunk

    total_time = (time.time() - start_time) * 1000

    return ThinkingSession(
        prompt=prompt,
        full_response=full_response,
        chunks=chunks,
        total_tokens=token_count,
        total_time_ms=total_time
    )


def print_chunk(chunk: ThoughtChunk):
    """Print a thought chunk with appropriate styling for terminal"""

    # Color codes for different thought types
    colors = {
        ThoughtType.REASONING: "\033[37m",      # White
        ThoughtType.PLANNING: "\033[36m",       # Cyan
        ThoughtType.CODE: "\033[33m",           # Yellow
        ThoughtType.QUESTION: "\033[35m",       # Magenta
        ThoughtType.CONCLUSION: "\033[32m",     # Green
        ThoughtType.ERROR: "\033[31m",          # Red
        ThoughtType.UNCERTAINTY: "\033[90m",    # Gray
    }

    reset = "\033[0m"
    color = colors.get(chunk.thought_type, "\033[37m")

    # Don't add newlines for streaming effect
    sys.stdout.write(f"{color}{chunk.text}{reset}")
    sys.stdout.flush()


def stream_with_interrupt(
    prompt: str,
    model: str = "sam-brain:latest",
    interrupt_check: Optional[Callable[[], bool]] = None
) -> ThinkingSession:
    """
    Stream thinking with ability to interrupt.

    Args:
        prompt: The prompt
        model: The model to use
        interrupt_check: Function that returns True to stop

    Returns:
        ThinkingSession (may be incomplete if interrupted)
    """
    chunks = []
    full_response = ""
    interrupted = False

    for chunk in stream_thinking(prompt, model, show_live=True):
        chunks.append(chunk)
        full_response += chunk.text

        # Check for interrupt
        if interrupt_check and interrupt_check():
            print("\n\033[33m[Interrupted by user]\033[0m")
            interrupted = True
            break

    return ThinkingSession(
        prompt=prompt,
        full_response=full_response,
        chunks=chunks,
        total_tokens=sum(c.token_count for c in chunks),
        total_time_ms=chunks[-1].elapsed_ms if chunks else 0,
        was_interrupted=interrupted
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURED THINKING - Make the model show its work
# ═══════════════════════════════════════════════════════════════════════════════

STRUCTURED_SYSTEM_PROMPT = """You are SAM, an AI assistant that thinks out loud.

When answering, structure your response like this:

**Understanding:** First, restate what you understand the user is asking.

**Thinking:** Show your reasoning process step by step. Consider:
- What do I know about this?
- What are the options?
- What could go wrong?

**Uncertainty:** If you're unsure about anything, say so clearly.

**Answer:** Give your final answer or solution.

This helps the user follow your reasoning and catch any misunderstandings early."""


def stream_structured_thinking(
    prompt: str,
    model: str = "1.5b",
    show_live: bool = True
) -> Generator[ThoughtChunk, None, ThinkingSession]:
    """
    Stream thinking with structured format that shows clear reasoning.
    """
    return stream_thinking(
        prompt=prompt,
        model=model,
        system_prompt=STRUCTURED_SYSTEM_PROMPT,
        show_live=show_live
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CODING-SPECIFIC THINKING
# ═══════════════════════════════════════════════════════════════════════════════

CODING_SYSTEM_PROMPT = """You are SAM, a coding assistant that explains its thinking.

When given a coding task:

1. **Understanding:** Restate the task to confirm understanding.

2. **Analysis:**
   - What files/functions are involved?
   - What's the current state?
   - What needs to change?

3. **Approach:** Explain your planned approach BEFORE writing code.

4. **Concerns:** Note any potential issues or edge cases.

5. **Implementation:** Then provide the code.

6. **Verification:** Explain how to verify it works.

Show your thinking at each step so the user can catch mistakes early."""


def stream_coding_thinking(
    prompt: str,
    model: str = "1.5b",
    show_live: bool = True
) -> Generator[ThoughtChunk, None, ThinkingSession]:
    """
    Stream coding-specific thinking with clear reasoning.
    """
    return stream_thinking(
        prompt=prompt,
        model=model,
        system_prompt=CODING_SYSTEM_PROMPT,
        show_live=show_live
    )


# ═══════════════════════════════════════════════════════════════════════════════
# API FOR FRONTEND
# ═══════════════════════════════════════════════════════════════════════════════

def thinking_to_sse(chunk: ThoughtChunk) -> str:
    """Format chunk as Server-Sent Event for frontend streaming"""
    return f"data: {json.dumps({
        'text': chunk.text,
        'type': chunk.thought_type.value,
        'tokens': chunk.token_count,
        'elapsed_ms': chunk.elapsed_ms,
        'complete': chunk.is_complete
    })}\n\n"


def get_thinking_colors() -> dict:
    """Get color scheme for frontend to use"""
    return {
        "reasoning": "#ffffff",    # White
        "planning": "#00bcd4",     # Cyan
        "code": "#ffc107",         # Amber
        "question": "#e91e63",     # Pink
        "conclusion": "#4caf50",   # Green
        "error": "#f44336",        # Red
        "uncertainty": "#9e9e9e",  # Gray
    }


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("SAM Live Thinking - See Real LLM Thoughts")
        print("\nUsage:")
        print("  python live_thinking.py ask <prompt>      # Ask with visible thinking")
        print("  python live_thinking.py code <prompt>     # Coding with reasoning")
        print("  python live_thinking.py structured <p>    # Structured thinking format")
        print("  python live_thinking.py test              # Quick test")
        print("\nThis shows REAL model output, not decorative animation.")
        print("You can watch the model's actual reasoning process.")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "test":
        print("\n\033[36m━━━ SAM Live Thinking Test ━━━\033[0m\n")
        print("\033[90mAsking: 'What is 2+2 and why?'\033[0m\n")

        for chunk in stream_thinking("What is 2+2 and why?", show_live=True):
            pass  # Chunks are printed in stream_thinking

        print("\n\n\033[36m━━━ Complete ━━━\033[0m\n")

    elif cmd == "ask":
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Hello, how are you?"
        print(f"\n\033[36m━━━ Asking: {prompt[:50]}... ━━━\033[0m\n")

        for chunk in stream_thinking(prompt, show_live=True):
            pass

        print("\n")

    elif cmd == "code":
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Write a function to check if a number is prime"
        print(f"\n\033[36m━━━ Coding Task ━━━\033[0m\n")
        print(f"\033[90m{prompt}\033[0m\n")

        for chunk in stream_coding_thinking(prompt, show_live=True):
            pass

        print("\n")

    elif cmd == "structured":
        prompt = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Should I use REST or GraphQL for my new API?"
        print(f"\n\033[36m━━━ Structured Thinking ━━━\033[0m\n")

        for chunk in stream_structured_thinking(prompt, show_live=True):
            pass

        print("\n")

    else:
        print(f"Unknown command: {cmd}")
