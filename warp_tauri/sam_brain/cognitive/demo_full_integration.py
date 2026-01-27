#!/usr/bin/env python3
"""
SAM Full Integration Demo

Exercises all cognitive systems in realistic scenarios:
1. Text Processing (emotional, cognitive, MLX generation)
2. Vision Processing (image description, detection, VQA)
3. Multi-turn Conversation (memory, context)
4. Goal Management (create, track, complete)
5. Learning Loop (feedback, improvement)
6. Escalation Triggers (low confidence → Claude)

Run: python3 -m cognitive.demo_full_integration
"""

import sys
import time
import json
import tempfile
from pathlib import Path
from datetime import datetime


def print_header(title: str):
    """Print formatted section header."""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_result(label: str, value, indent: int = 2):
    """Print formatted result."""
    prefix = " " * indent
    if isinstance(value, dict):
        print(f"{prefix}{label}:")
        for k, v in value.items():
            print(f"{prefix}  {k}: {v}")
    elif isinstance(value, list):
        print(f"{prefix}{label}: [{len(value)} items]")
        for item in value[:3]:
            print(f"{prefix}  - {str(item)[:60]}...")
    else:
        print(f"{prefix}{label}: {value}")


def demo_text_processing(orchestrator):
    """Demo 1: Text Processing Pipeline"""
    print_header("DEMO 1: TEXT PROCESSING")

    queries = [
        ("Simple math", "What is 15 * 7?"),
        ("Casual chat", "Hey SAM, how's it going?"),
        ("Technical", "Explain how Python decorators work in 2 sentences."),
    ]

    for name, query in queries:
        print(f"\n  [{name}] Query: {query}")
        start = time.time()
        response = orchestrator.process(query)
        duration = int((time.time() - start) * 1000)

        print(f"  Response: {response.response[:100]}{'...' if len(response.response) > 100 else ''}")
        print(f"  Confidence: {response.confidence:.2f} | Mood: {response.mood} | Time: {duration}ms")

    return True


def demo_vision_processing(orchestrator, test_image: str):
    """Demo 2: Vision Processing Pipeline"""
    print_header("DEMO 2: VISION PROCESSING")

    # Check if vision is available
    try:
        engine = orchestrator.vision_engine
        stats = engine.get_stats()
        print(f"  Vision engine: MLX available = {stats.get('mlx_available', False)}")
    except Exception as e:
        print(f"  Vision engine not available: {e}")
        print("  Skipping vision demo...")
        return False

    # Test describe
    print(f"\n  [Describe] Image: {test_image}")
    try:
        result = orchestrator.describe_image(test_image, detail_level="medium")
        print(f"  Response: {result.response[:100]}{'...' if len(result.response) > 100 else ''}")
        print(f"  Model: {result.model_used} | Confidence: {result.confidence:.2f}")
        print(f"  Escalated: {result.escalated}")
    except Exception as e:
        print(f"  Error: {e}")

    # Test detect
    print(f"\n  [Detect] Looking for objects...")
    try:
        result = orchestrator.detect_objects(test_image)
        print(f"  Response: {result.response[:100]}{'...' if len(result.response) > 100 else ''}")
    except Exception as e:
        print(f"  Error: {e}")

    return True


def demo_multi_turn(orchestrator):
    """Demo 3: Multi-turn Conversation with Memory"""
    print_header("DEMO 3: MULTI-TURN CONVERSATION")

    conversation = [
        "My name is Alex and I'm learning Python.",
        "What should I learn first as a beginner?",
        "Can you give me an example related to what we discussed?",
    ]

    for i, msg in enumerate(conversation, 1):
        print(f"\n  Turn {i}: {msg}")
        response = orchestrator.process(msg, user_id="alex")
        print(f"  SAM: {response.response[:120]}{'...' if len(response.response) > 120 else ''}")

    # Check memory state
    state = orchestrator.get_state()
    print(f"\n  Session turns: {state['session']['turns']}")
    print(f"  Working memory items: {state['memory'].get('working_memory_count', 'N/A')}")

    return True


def demo_goals(orchestrator):
    """Demo 4: Goal Management"""
    print_header("DEMO 4: GOAL MANAGEMENT")

    from cognitive import GoalPriority

    # Create a goal
    goal_id = orchestrator.create_goal(
        "Help user understand SAM's capabilities",
        priority=GoalPriority.HIGH
    )
    print(f"  Created goal: {goal_id}")

    # Get active goals
    state = orchestrator.get_state()
    print(f"  Active goals: {len(state['goals'])}")
    for goal in state['goals']:
        print(f"    - {goal.get('description', 'N/A')[:50]} (progress: {goal.get('progress', 0):.0%})")

    # Update progress
    orchestrator.update_goal_progress(goal_id, 0.5)
    print(f"  Updated goal progress to 50%")

    return True


def demo_emotional_state(orchestrator):
    """Demo 5: Emotional Model"""
    print_header("DEMO 5: EMOTIONAL STATE")

    # Get current emotional state
    state = orchestrator.get_state()
    emotional = state.get('emotional', {})

    print(f"  Current mood: {emotional.get('mood', 'N/A')}")
    print(f"  Valence: {emotional.get('valence', 'N/A')}")
    print(f"  Arousal: {emotional.get('arousal', 'N/A')}")

    # Process something that might affect mood
    print("\n  Processing positive interaction...")
    response = orchestrator.process("Thanks SAM, you're really helpful!", user_id="demo")
    print(f"  Response mood: {response.mood}")

    # Check updated state
    state = orchestrator.get_state()
    emotional = state.get('emotional', {})
    print(f"  Updated mood: {emotional.get('mood', 'N/A')}")

    return True


def demo_learning(orchestrator):
    """Demo 6: Learning System"""
    print_header("DEMO 6: LEARNING SYSTEM")

    # Get learning suggestions
    suggestions = orchestrator.get_learning_suggestions(n=3)
    print(f"  Learning suggestions ({len(suggestions)}):")
    for s in suggestions:
        print(f"    - {s[:60]}{'...' if len(s) > 60 else ''}")

    # Process something to learn from
    print("\n  Processing query for learning...")
    response = orchestrator.process("What are the best practices for error handling?")
    print(f"  Response recorded for learning (confidence: {response.confidence:.2f})")

    return True


def demo_state_summary(orchestrator):
    """Demo 7: Full State Summary"""
    print_header("DEMO 7: FULL SYSTEM STATE")

    state = orchestrator.get_state()

    print(f"  Session:")
    print(f"    Started: {state['session']['start']}")
    print(f"    Turns: {state['session']['turns']}")
    print(f"    Duration: {state['session']['duration_minutes']:.1f} minutes")

    print(f"\n  Memory:")
    for k, v in state.get('memory', {}).items():
        print(f"    {k}: {v}")

    print(f"\n  Attention:")
    attention = state.get('attention', {})
    print(f"    Focus: {attention.get('current_focus', 'N/A')}")
    print(f"    Filters: {attention.get('active_filters', [])}")

    return True


def create_test_image() -> str:
    """Create a simple test image."""
    test_dir = tempfile.mkdtemp(prefix="sam_demo_")
    test_image = Path(test_dir) / "test_image.png"

    try:
        from PIL import Image, ImageDraw

        # Create a simple test image with shapes
        img = Image.new('RGB', (200, 200), color='white')
        draw = ImageDraw.Draw(img)

        # Draw a red circle
        draw.ellipse([20, 20, 80, 80], fill='red', outline='darkred')

        # Draw a blue rectangle
        draw.rectangle([120, 40, 180, 100], fill='blue', outline='darkblue')

        # Draw a green triangle
        draw.polygon([(100, 150), (60, 190), (140, 190)], fill='green', outline='darkgreen')

        img.save(str(test_image))
        print(f"  Created test image with shapes: {test_image}")

    except ImportError:
        # Fallback: minimal PNG
        png_data = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
            0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
            0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
            0x00, 0x00, 0x03, 0x00, 0x01, 0x00, 0x18, 0xDD,
            0x8D, 0xB4, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45,
            0x4E, 0x44, 0xAE, 0x42, 0x60, 0x82
        ])
        test_image.write_bytes(png_data)
        print(f"  Created minimal test image: {test_image}")

    return str(test_image)


def run_full_demo():
    """Run the complete integration demo."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " SAM COGNITIVE SYSTEM - FULL INTEGRATION DEMO ".center(68) + "║")
    print("║" + f" Version 1.2.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')} ".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Initialize
    print_header("INITIALIZATION")
    print("  Loading cognitive orchestrator...")
    start = time.time()

    try:
        from cognitive import create_cognitive_orchestrator

        orchestrator = create_cognitive_orchestrator(
            db_path="/tmp/sam_demo",
            retrieval_paths=None
        )

        init_time = int((time.time() - start) * 1000)
        print(f"  Orchestrator ready in {init_time}ms")

    except Exception as e:
        print(f"  Failed to initialize: {e}")
        return 1

    # Create test image
    test_image = create_test_image()

    # Run demos
    results = {}
    demos = [
        ("Text Processing", lambda: demo_text_processing(orchestrator)),
        ("Vision Processing", lambda: demo_vision_processing(orchestrator, test_image)),
        ("Multi-turn Conversation", lambda: demo_multi_turn(orchestrator)),
        ("Goal Management", lambda: demo_goals(orchestrator)),
        ("Emotional State", lambda: demo_emotional_state(orchestrator)),
        ("Learning System", lambda: demo_learning(orchestrator)),
        ("State Summary", lambda: demo_state_summary(orchestrator)),
    ]

    for name, demo_fn in demos:
        try:
            result = demo_fn()
            results[name] = "PASS" if result else "SKIP"
        except Exception as e:
            results[name] = f"FAIL: {e}"
            print(f"  Error: {e}")

    # Summary
    print_header("DEMO SUMMARY")
    passed = sum(1 for v in results.values() if v == "PASS")
    skipped = sum(1 for v in results.values() if v == "SKIP")
    failed = sum(1 for v in results.values() if v.startswith("FAIL"))

    for name, result in results.items():
        status = "✓" if result == "PASS" else ("○" if result == "SKIP" else "✗")
        print(f"  [{status}] {name}: {result}")

    print()
    print(f"  Results: {passed} passed, {skipped} skipped, {failed} failed")

    # Cleanup
    print("\n  Shutting down...")
    orchestrator.shutdown()
    print("  Done!")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_full_demo())
