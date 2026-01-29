#!/usr/bin/env python3
"""
SAM Escalation Handler
- SAM tries all requests first via cognitive system
- Evaluates response quality/confidence
- Automatically escalates to Claude via browser bridge when needed
- No API costs - uses logged-in session

Updated 2026-01-17: Now uses cognitive/ system with MLX integration
"""

import sys
import json
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

# Import local modules
sys.path.insert(0, str(Path(__file__).parent))
from core.smart_router import estimate_complexity, sanitize_content, Provider

# Import NEW cognitive system (replaces old mlx_inference)
_cognitive_orchestrator = None
_cognitive_available = False

def _init_cognitive():
    """Lazy-load cognitive system."""
    global _cognitive_orchestrator, _cognitive_available
    if _cognitive_orchestrator is None:
        try:
            from cognitive import create_cognitive_orchestrator
            _cognitive_orchestrator = create_cognitive_orchestrator(
                db_path="/Volumes/David External/sam_memory/cognitive",
                retrieval_paths=["/Volumes/David External/sam_memory"]
            )
            _cognitive_available = True
        except Exception as e:
            print(f"Warning: Could not load cognitive system: {e}", file=sys.stderr)
            _cognitive_available = False
    return _cognitive_orchestrator

# Import escalation learner for tracking/learning
try:
    from execution.escalation_learner import EscalationLearner
    _learner = EscalationLearner()
except ImportError:
    _learner = None

# Import intelligence core for distillation
try:
    from learn.intelligence_core import get_intelligence_core
    _intelligence = get_intelligence_core()
except ImportError:
    _intelligence = None

# Import knowledge distillation for comprehensive reasoning capture
try:
    from learn.knowledge_distillation import (
        DistillationDB,
        ChainOfThoughtExtractor,
        PrincipleExtractor
    )
    _distillation_db = DistillationDB()
    _cot_extractor = ChainOfThoughtExtractor()
    _principle_extractor = PrincipleExtractor()
except ImportError:
    _distillation_db = None
    _cot_extractor = None
    _principle_extractor = None

class EscalationReason(Enum):
    NONE = "none"
    LOW_CONFIDENCE = "low_confidence"
    TASK_TOO_COMPLEX = "task_too_complex"
    SAM_REFUSED = "sam_refused"
    SAM_ERROR = "sam_error"
    USER_REQUESTED = "user_requested"
    QUALITY_ISSUE = "quality_issue"
    REPETITION = "repetition"

@dataclass
class SAMResponse:
    content: str
    confidence: float  # 0.0 to 1.0
    should_escalate: bool
    escalation_reason: EscalationReason
    provider: str  # "sam" or "claude"

# Patterns indicating SAM might need help
UNCERTAINTY_PATTERNS = [
    r"i('m| am) not sure",
    r"i don('t|'t) know",
    r"i can('t|not) help",
    r"beyond my (capabilities|knowledge)",
    r"you('d| would) (need|want) to",
    r"consult (a|an) (expert|professional)",
    r"i('m| am) (just|only) a",
    r"that('s| is) (complex|complicated|difficult)",
    r"i (can't|cannot) (access|see|read)",
]

# Patterns indicating SAM refused (safety training residue)
REFUSAL_PATTERNS = [
    r"i can('t|not) (assist|help) with that",
    r"i('m| am) (unable|not able) to",
    r"(sorry|apologize).{0,30}(can't|cannot|won't)",
    r"(inappropriate|harmful|unethical)",
    r"against my (guidelines|programming|policy)",
]

# Patterns indicating good/confident response
CONFIDENT_PATTERNS = [
    r"```",  # Code blocks suggest concrete answer
    r"here('s| is) (how|what|the)",
    r"you (can|should|need to)",
    r"(first|step \d|to do this)",
    r"(function|class|def |const |let |var )",
]

# Complex task patterns that benefit from Claude
CLAUDE_PREFERRED = [
    r"architect",
    r"design.{0,20}(system|pattern)",
    r"(complex|multi.?step|large)",
    r"(refactor|rewrite).{0,20}(entire|whole|all)",
    r"(security|vulnerability|exploit)",
    r"(optimize|performance).{0,20}(critical|important)",
    r"explain.{0,20}(in depth|detailed|thoroughly)",
]

# Global model cache (legacy - now using cognitive system)
_model = None
_tokenizer = None

def get_cognitive():
    """Get cognitive orchestrator (lazy-loaded)."""
    return _init_cognitive()

def evaluate_confidence(response: str, original_prompt: str) -> Tuple[float, EscalationReason]:
    """
    Evaluate SAM's response confidence.
    Returns (confidence_score, escalation_reason)
    """
    response_lower = response.lower()
    prompt_lower = original_prompt.lower()

    # Check for refusals first
    for pattern in REFUSAL_PATTERNS:
        if re.search(pattern, response_lower):
            return 0.1, EscalationReason.SAM_REFUSED

    # Check for uncertainty
    uncertainty_count = sum(1 for p in UNCERTAINTY_PATTERNS if re.search(p, response_lower))

    # Check for confident patterns
    confident_count = sum(1 for p in CONFIDENT_PATTERNS if re.search(p, response_lower))

    # Check if Claude would be better for this task
    claude_preferred = any(re.search(p, prompt_lower) for p in CLAUDE_PREFERRED)

    # Calculate base confidence
    confidence = 0.7  # Start with moderate confidence

    # Adjust based on patterns
    confidence -= uncertainty_count * 0.15
    confidence += confident_count * 0.1

    # Response length factors
    word_count = len(response.split())
    if word_count < 10:
        confidence -= 0.3  # Very short responses are suspicious
    elif word_count > 50:
        confidence += 0.1  # Detailed responses are usually better

    # Has code = probably good for coding questions
    if "```" in response and ("code" in prompt_lower or "function" in prompt_lower):
        confidence += 0.15

    # Bound confidence
    confidence = max(0.0, min(1.0, confidence))

    # Determine escalation reason
    if confidence < 0.4:
        reason = EscalationReason.LOW_CONFIDENCE
    elif claude_preferred and confidence < 0.7:
        reason = EscalationReason.TASK_TOO_COMPLEX
    else:
        reason = EscalationReason.NONE

    return confidence, reason

def should_auto_escalate(confidence: float, complexity: int, reason: EscalationReason) -> bool:
    """Decide if we should automatically escalate to Claude."""
    # Always escalate refusals
    if reason == EscalationReason.SAM_REFUSED:
        return True

    # Escalate low confidence
    if confidence < 0.3:
        return True

    # Escalate complex tasks with medium confidence
    if complexity >= 7 and confidence < 0.6:
        return True

    # Medium complexity with low-ish confidence
    if complexity >= 5 and confidence < 0.4:
        return True

    return False

def escalate_to_claude(prompt: str, context: Optional[str] = None) -> str:
    """Send request to Claude via browser bridge and log for learning."""
    bridge_path = Path(__file__).parent.parent / "ai_bridge.cjs"

    if not bridge_path.exists():
        return "[Error: Bridge not found. Run 'node ai_bridge.cjs login claude' first]"

    # Sanitize before sending externally
    sanitized_prompt = sanitize_content(prompt)

    # Build command
    cmd = ["node", str(bridge_path), "send", sanitized_prompt, "--claude"]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=180,  # 3 minute timeout
            cwd=str(bridge_path.parent)
        )

        if result.returncode == 0:
            try:
                data = json.loads(result.stdout)
                response = data.get("response", result.stdout)
            except json.JSONDecodeError:
                response = result.stdout

            # Log escalation for learning (so SAM can handle similar queries in future)
            if _learner:
                try:
                    _learner.log_escalation(prompt, response, tokens_used=len(response.split()) * 2)
                except:
                    pass  # Don't fail if logging fails

            # Capture for knowledge distillation (Phase 1 intelligence)
            domain = "code" if any(kw in prompt.lower() for kw in ["code", "function", "implement", "bug", "error"]) else "general"

            if _intelligence:
                try:
                    _intelligence.capture_escalation(prompt, None, response, domain=domain)
                except:
                    pass  # Don't fail if capture fails

            # Comprehensive distillation capture (CoT, principles, raw interactions)
            if _distillation_db:
                try:
                    # Store raw interaction
                    _distillation_db.store_interaction(prompt, response, domain, quality=0.9)

                    # Extract and store chain-of-thought
                    if _cot_extractor:
                        cot = _cot_extractor.extract(prompt, response, domain)
                        if cot and len(cot.reasoning_steps) >= 2:
                            _distillation_db.store_cot(cot)

                    # Extract and store principles
                    if _principle_extractor:
                        principles = _principle_extractor.extract(response, domain)
                        for principle in principles:
                            _distillation_db.store_principle(principle)
                except Exception as e:
                    pass  # Don't fail if distillation fails

            return response
        else:
            return f"[Bridge error: {result.stderr}]"

    except subprocess.TimeoutExpired:
        return "[Error: Claude response timed out]"
    except Exception as e:
        return f"[Error: {str(e)}]"

def process_request(prompt: str, auto_escalate: bool = True, force_claude: bool = False) -> SAMResponse:
    """
    Process a user request through SAM cognitive system with optional escalation.

    Args:
        prompt: User's request
        auto_escalate: If True, automatically escalate when confidence is low
        force_claude: If True, skip SAM and go directly to Claude

    Returns:
        SAMResponse with content, confidence, and escalation info
    """

    # Force Claude path
    if force_claude:
        response = escalate_to_claude(prompt)
        return SAMResponse(
            content=response,
            confidence=1.0,
            should_escalate=False,
            escalation_reason=EscalationReason.USER_REQUESTED,
            provider="claude"
        )

    # Get complexity estimate
    complexity, complexity_reason = estimate_complexity(prompt)

    # Try SAM cognitive system first
    try:
        orchestrator = get_cognitive()
        if orchestrator is None:
            raise RuntimeError("Cognitive system not available")

        # Process through cognitive pipeline
        result = orchestrator.process(prompt)
        sam_response = result.response
        cognitive_confidence = result.confidence

        # Check if cognitive system recommends escalation
        metadata = result.metadata or {}
        escalation_recommended = metadata.get('escalation_recommended', False)
        quality_issues = metadata.get('quality_issues', [])

    except Exception as e:
        # SAM failed - escalate
        if auto_escalate:
            response = escalate_to_claude(prompt)
            return SAMResponse(
                content=response,
                confidence=1.0,
                should_escalate=False,
                escalation_reason=EscalationReason.SAM_ERROR,
                provider="claude"
            )
        else:
            return SAMResponse(
                content=f"[SAM Error: {str(e)}]",
                confidence=0.0,
                should_escalate=True,
                escalation_reason=EscalationReason.SAM_ERROR,
                provider="sam"
            )

    # Use cognitive system's confidence directly (it's already calibrated)
    confidence = cognitive_confidence

    # Determine escalation reason based on cognitive output
    if escalation_recommended:
        if 'repetition' in str(quality_issues).lower():
            reason = EscalationReason.REPETITION
        elif confidence < 0.3:
            reason = EscalationReason.LOW_CONFIDENCE
        else:
            reason = EscalationReason.QUALITY_ISSUE
    else:
        # Also check traditional patterns for safety
        _, pattern_reason = evaluate_confidence(sam_response, prompt)
        reason = pattern_reason

    # Decide on escalation
    should_escalate = (
        escalation_recommended or
        should_auto_escalate(confidence, complexity, reason)
    )

    if should_escalate and auto_escalate:
        # Escalate to Claude via browser bridge
        claude_response = escalate_to_claude(prompt)
        return SAMResponse(
            content=claude_response,
            confidence=1.0,
            should_escalate=False,
            escalation_reason=reason,
            provider="claude"
        )
    else:
        return SAMResponse(
            content=sam_response,
            confidence=confidence,
            should_escalate=should_escalate,
            escalation_reason=reason,
            provider="sam"
        )

def interactive_mode():
    """Interactive chat with automatic escalation."""
    print("\n🤖 SAM with Auto-Escalation")
    print("Commands: /claude (force Claude), /sam (force SAM), /quit")
    print("SAM will automatically escalate to Claude when needed.\n")

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['/quit', '/exit', '/q']:
                break

            # Handle commands
            force_claude = user_input.startswith('/claude ')
            force_sam = user_input.startswith('/sam ')

            if force_claude:
                prompt = user_input[8:].strip()
                result = process_request(prompt, auto_escalate=False, force_claude=True)
            elif force_sam:
                prompt = user_input[5:].strip()
                result = process_request(prompt, auto_escalate=False, force_claude=False)
            else:
                result = process_request(user_input, auto_escalate=True)

            # Show response with provider indicator
            provider_emoji = "🧠" if result.provider == "sam" else "☁️"
            print(f"\n{provider_emoji} [{result.provider.upper()}] (confidence: {result.confidence:.0%})")

            if result.escalation_reason != EscalationReason.NONE:
                print(f"   (escalation: {result.escalation_reason.value})")

            print(f"\n{result.content}\n")

        except KeyboardInterrupt:
            break
        except EOFError:
            break

    print("\nGoodbye!")

# CLI
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SAM with Auto-Escalation to Claude")
    parser.add_argument("prompt", nargs="?", help="Single prompt to process")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")
    parser.add_argument("--claude", action="store_true", help="Force Claude")
    parser.add_argument("--sam", action="store_true", help="Force SAM only (no escalation)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    if args.interactive:
        interactive_mode()
    elif args.prompt:
        result = process_request(
            args.prompt,
            auto_escalate=not args.sam,
            force_claude=args.claude
        )

        if args.json:
            print(json.dumps({
                "content": result.content,
                "confidence": result.confidence,
                "provider": result.provider,
                "escalation_reason": result.escalation_reason.value,
            }, indent=2))
        else:
            print(result.content)
    else:
        parser.print_help()
