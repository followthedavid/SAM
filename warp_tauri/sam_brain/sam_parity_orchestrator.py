#!/usr/bin/env python3
"""
SAM Parity Orchestrator - The master system for Claude Code + ChatGPT equivalence

This orchestrates all SAM systems to achieve parity with cloud AI assistants:

ARCHITECTURE:
┌─────────────────────────────────────────────────────────────────────┐
│                        SAM PARITY SYSTEM                            │
├─────────────────────────────────────────────────────────────────────┤
│  User Request                                                       │
│       ↓                                                             │
│  ┌─────────────────┐                                                │
│  │ Capability Router│ → Detect what skills are needed               │
│  └────────┬────────┘                                                │
│           ↓                                                         │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │ Local Handler   │ or │ Claude Escalator │ → Based on confidence │
│  └────────┬────────┘    └────────┬────────┘                        │
│           ↓                      ↓                                  │
│  ┌─────────────────┐    ┌─────────────────┐                        │
│  │ Tool Execution  │    │ Learn from Claude│                        │
│  └────────┬────────┘    └────────┬────────┘                        │
│           ↓                      ↓                                  │
│  ┌─────────────────────────────────────────┐                        │
│  │           Response to User              │                        │
│  └─────────────────────────────────────────┘                        │
│                                                                     │
│  Background: Training pipeline accumulates examples                 │
│  Background: Periodic fine-tuning improves local handling           │
└─────────────────────────────────────────────────────────────────────┘

CAPABILITY COVERAGE:
┌──────────────────────┬────────────────────┬────────────────────────┐
│ Capability           │ SAM Handles?       │ Method                 │
├──────────────────────┼────────────────────┼────────────────────────┤
│ File operations      │ ✓ Native           │ tool_system.py         │
│ Code generation      │ ✓ MLX + LoRA       │ cognitive/mlx_*        │
│ Code editing         │ ✓ Native           │ tool_system.py         │
│ Bash execution       │ ✓ Native + safety  │ tool_system.py         │
│ Git operations       │ ✓ Native           │ tool_system.py         │
│ Web search           │ → Escalate         │ claude_learning.py     │
│ Complex reasoning    │ → Escalate/learn   │ parity_system.py       │
│ Vision               │ ✓ Multi-tier       │ cognitive/vision_*     │
│ Voice                │ ✓ Native           │ voice_pipeline.py      │
│ Memory               │ ✓ Semantic         │ semantic_memory.py     │
│ Planning             │ ✓ + templates      │ tool_system.py         │
│ Image generation     │ ✓ ComfyUI          │ orchestrator.py        │
└──────────────────────┴────────────────────┴────────────────────────┘

TRAINING DATA SOURCES:
- ChatGPT export: 13,161 examples (processed)
- Claude conversations: Ongoing extraction
- Escalation learning: Every Claude call = training example
- Manual curation: High-quality hand-picked examples
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Add parent to path for imports
BRAIN_DIR = Path(__file__).parent
sys.path.insert(0, str(BRAIN_DIR))

from parity_system import (
    Capability,
    CapabilityRouter,
    SelfTrainingLoop,
    CAPABILITY_MAP,
)
from tool_system import ToolRegistry, ToolResult
from claude_learning import RealTimeLearner


@dataclass
class ParityStatus:
    """Current parity status with cloud assistants."""
    capabilities_local: int
    capabilities_escalate: int
    training_examples: int
    escalation_events: int
    last_training: Optional[str]
    model_version: str


class SAMParityOrchestrator:
    """
    Master orchestrator for SAM parity with Claude Code + ChatGPT.

    Goals:
    1. Handle as many requests locally as possible
    2. Escalate intelligently when needed
    3. Learn from every escalation
    4. Continuously improve through fine-tuning
    """

    def __init__(self):
        self.brain_dir = BRAIN_DIR
        self.router = CapabilityRouter()
        self.tools = ToolRegistry()
        self.training_loop = SelfTrainingLoop(self.brain_dir)
        self.realtime_learner = RealTimeLearner(self.brain_dir)

        # Load MLX model (lazy)
        self._model = None
        self._tokenizer = None

    def _load_model(self):
        """Lazy load the MLX model."""
        if self._model is not None:
            return

        try:
            from mlx_lm import load
            model_path = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

            # Check for fine-tuned adapter
            adapter_path = self.brain_dir / "models" / "latest" / "adapters"
            if adapter_path.exists():
                print(f"Loading with adapter: {adapter_path}")
                self._model, self._tokenizer = load(
                    model_path,
                    adapter_path=str(adapter_path)
                )
            else:
                self._model, self._tokenizer = load(model_path)

        except ImportError:
            print("MLX not available, will escalate all requests")

    def get_status(self) -> ParityStatus:
        """Get current parity status."""
        local_count = sum(1 for p in CAPABILITY_MAP.values() if p.sam_can_handle)
        escalate_count = len(CAPABILITY_MAP) - local_count

        # Count training examples
        training_file = self.brain_dir / "training_data.jsonl"
        training_count = 0
        if training_file.exists():
            training_count = sum(1 for _ in open(training_file))

        # Add processed ChatGPT data
        processed_dir = Path("/Volumes/David External/SAM_training/processed")
        if (processed_dir / "train.jsonl").exists():
            training_count += sum(1 for _ in open(processed_dir / "train.jsonl"))

        # Escalation events
        escalation_file = self.brain_dir / "escalation_data" / "escalation_events.jsonl"
        escalation_count = 0
        if escalation_file.exists():
            escalation_count = sum(1 for _ in open(escalation_file))

        return ParityStatus(
            capabilities_local=local_count,
            capabilities_escalate=escalate_count,
            training_examples=training_count,
            escalation_events=escalation_count,
            last_training=self._get_last_training_date(),
            model_version="Qwen2.5-Coder-1.5B + LoRA",
        )

    def _get_last_training_date(self) -> Optional[str]:
        """Get date of last training run."""
        runs_file = self.brain_dir / "training_runs.json"
        if runs_file.exists():
            try:
                runs = json.load(open(runs_file))
                if runs:
                    return runs[-1].get("start_time")
            except:
                pass
        return None

    def process_request(
        self,
        request: str,
        context: str = "",
        allow_escalation: bool = True,
    ) -> Tuple[str, Dict]:
        """
        Process a user request with full parity system.

        Returns (response, metadata)
        """
        metadata = {
            "escalated": False,
            "capabilities": [],
            "tools_used": [],
            "confidence": 0.0,
        }

        # 1. Detect capabilities needed
        capabilities = self.router.detect_capability(request)
        metadata["capabilities"] = [(c.value, conf) for c, conf in capabilities]

        # 2. Check if we should escalate
        primary_cap = capabilities[0][0] if capabilities else Capability.CONVERSATION
        should_escalate, confidence = self.training_loop.should_escalate(request, primary_cap)
        metadata["confidence"] = confidence

        # 3. Try local handling first
        if not should_escalate or not allow_escalation:
            response = self._handle_locally(request, context, capabilities)
            if response and self._is_quality_response(response):
                return response, metadata

        # 4. Escalate if needed
        if allow_escalation:
            metadata["escalated"] = True
            response = self._escalate_to_claude(request, context, primary_cap)
            return response, metadata

        # 5. Fallback
        return "I'm not confident in my answer. Would you like me to escalate to Claude?", metadata

    def _handle_locally(
        self,
        request: str,
        context: str,
        capabilities: List[Tuple[Capability, float]]
    ) -> Optional[str]:
        """Handle request with local model and tools."""

        # Check for tool-use requests
        tool_result = self._try_tool_use(request)
        if tool_result:
            return tool_result

        # Use MLX model for generation
        self._load_model()
        if self._model is None:
            return None

        try:
            from mlx_lm import generate

            # Build prompt
            prompt = self._build_prompt(request, context, capabilities)

            response = generate(
                self._model,
                self._tokenizer,
                prompt=prompt,
                max_tokens=2000,
                temp=0.7,
            )

            return response

        except Exception as e:
            print(f"Local generation error: {e}")
            return None

    def _try_tool_use(self, request: str) -> Optional[str]:
        """Check if request needs tool use and execute."""
        request_lower = request.lower()

        # File reading
        if any(kw in request_lower for kw in ["read", "show", "cat", "display"]):
            # Try to extract path
            import re
            path_match = re.search(r'[\w/\.\-_~]+\.\w+', request)
            if path_match:
                result = self.tools.execute("Read", file_path=path_match.group())
                if result.success:
                    return result.output

        # Git status
        if "git status" in request_lower:
            result = self.tools.execute("GitStatus")
            if result.success:
                return result.output

        # Git diff
        if "git diff" in request_lower:
            result = self.tools.execute("GitDiff")
            if result.success:
                return result.output

        # File search
        if any(kw in request_lower for kw in ["find file", "search for", "where is"]):
            import re
            pattern_match = re.search(r'\*?\w+\.\w+', request)
            if pattern_match:
                pattern = f"**/{pattern_match.group()}"
                result = self.tools.execute("Glob", pattern=pattern)
                if result.success:
                    return result.output

        return None

    def _build_prompt(
        self,
        request: str,
        context: str,
        capabilities: List[Tuple[Capability, float]]
    ) -> str:
        """Build prompt for local model."""
        parts = []

        # System context
        parts.append("You are SAM, a helpful AI coding assistant. Be direct and efficient.")

        # Tool availability
        if any(c in [Capability.FILE_READ, Capability.FILE_WRITE, Capability.BASH_EXECUTE]
               for c, _ in capabilities):
            parts.append("\nYou have access to file and bash tools. Use TOOL: format to invoke them.")

        # Context
        if context:
            parts.append(f"\nContext:\n{context}")

        # Request
        parts.append(f"\nUser: {request}")
        parts.append("\nSAM:")

        return '\n'.join(parts)

    def _is_quality_response(self, response: str) -> bool:
        """Check if response meets quality threshold."""
        if not response or len(response) < 10:
            return False

        error_indicators = ["I don't know", "I'm not sure", "Error:", "I cannot"]
        return not any(ind in response for ind in error_indicators)

    def _escalate_to_claude(
        self,
        request: str,
        context: str,
        capability: Capability
    ) -> str:
        """
        Escalate to Claude and learn from the response.

        This is the KEY learning mechanism: every escalation teaches SAM.
        """
        # For now, return a placeholder - in production this would call Claude
        # The actual Claude call would be done through the terminal or API

        # Record the escalation for later when we get Claude's response
        print(f"[ESCALATION NEEDED] Capability: {capability.value}")
        print(f"Request: {request[:200]}...")

        # In actual use, this would:
        # 1. Call Claude via API or terminal
        # 2. Capture response
        # 3. Call self.realtime_learner.record_interaction()
        # 4. Return response to user

        return f"""[SAM would escalate to Claude for: {capability.value}]

Request: {request[:100]}...

To actually escalate, use Claude Code terminal or call the Claude API.
SAM will automatically learn from Claude's response for future queries."""

    def record_claude_response(self, request: str, response: str, capability: str = "auto"):
        """
        Record a Claude response for learning.

        Call this after getting a response from Claude to train SAM.
        """
        self.realtime_learner.record_interaction(
            user_request=request,
            response=response,
            source="claude",
            category=capability,
        )

        # Check if we should trigger training
        ready, count = self.training_loop.check_training_ready()
        if ready:
            print(f"Training ready with {count} examples. Run: python parity_system.py training")

    def trigger_training(self):
        """Trigger a training run if we have enough examples."""
        ready, count = self.training_loop.check_training_ready()

        if not ready:
            print(f"Not enough examples yet: {count}/50")
            return False

        # Export training data
        output = self.training_loop.export_training_data()
        print(f"Training data exported to: {output}")

        # Combine with ChatGPT processed data
        chatgpt_dir = Path("/Volumes/David External/SAM_training/processed")
        if chatgpt_dir.exists():
            print(f"Also available: ChatGPT data at {chatgpt_dir}")

        print("\nTo train:")
        print(f"  python -m mlx_lm.lora \\")
        print(f"    --model Qwen/Qwen2.5-Coder-1.5B-Instruct \\")
        print(f"    --data {output} \\")
        print(f"    --train")

        return True


def print_parity_dashboard():
    """Print a dashboard showing SAM's current parity status."""
    orchestrator = SAMParityOrchestrator()
    status = orchestrator.get_status()

    print("=" * 70)
    print("SAM PARITY DASHBOARD")
    print("=" * 70)
    print()

    # Capability coverage
    total_caps = status.capabilities_local + status.capabilities_escalate
    pct_local = (status.capabilities_local / total_caps) * 100 if total_caps else 0

    print("CAPABILITY COVERAGE")
    print("-" * 40)
    print(f"  Local handling:  {status.capabilities_local}/{total_caps} ({pct_local:.0f}%)")
    print(f"  Needs escalation: {status.capabilities_escalate}/{total_caps}")
    print()

    # Training data
    print("TRAINING DATA")
    print("-" * 40)
    print(f"  Total examples:     {status.training_examples:,}")
    print(f"  Escalation events:  {status.escalation_events}")
    print(f"  Last training:      {status.last_training or 'Never'}")
    print()

    # Model info
    print("MODEL")
    print("-" * 40)
    print(f"  Base: {status.model_version}")
    print()

    # Next steps
    print("NEXT STEPS FOR PARITY")
    print("-" * 40)

    if status.training_examples < 100:
        print("  1. [ ] Need more training examples")
        print("       Run: python chatgpt_processor.py")
    else:
        print("  1. [✓] Training data available")

    if status.escalation_events < 50:
        print(f"  2. [ ] More escalation learning needed ({status.escalation_events}/50)")
        print("       Use SAM, let it escalate, record Claude responses")
    else:
        print("  2. [✓] Escalation learning data available")

    if not status.last_training:
        print("  3. [ ] Run initial training")
        print("       Run: python training_pipeline.py train")
    else:
        print(f"  3. [✓] Model trained ({status.last_training})")

    print()


def main():
    import sys

    if len(sys.argv) < 2:
        print_parity_dashboard()
        print("Commands:")
        print("  dashboard  - Show parity status (default)")
        print("  status     - Show detailed status JSON")
        print("  process    - Process a request")
        print("  train      - Trigger training if ready")
        print("  record     - Record a Claude response")
        return

    cmd = sys.argv[1]

    if cmd == "dashboard":
        print_parity_dashboard()

    elif cmd == "status":
        orchestrator = SAMParityOrchestrator()
        status = orchestrator.get_status()
        print(json.dumps({
            "capabilities_local": status.capabilities_local,
            "capabilities_escalate": status.capabilities_escalate,
            "training_examples": status.training_examples,
            "escalation_events": status.escalation_events,
            "last_training": status.last_training,
            "model_version": status.model_version,
        }, indent=2))

    elif cmd == "process":
        if len(sys.argv) < 3:
            print("Usage: sam_parity_orchestrator.py process <request>")
            return

        request = " ".join(sys.argv[2:])
        orchestrator = SAMParityOrchestrator()
        response, metadata = orchestrator.process_request(request)

        print(f"\nCapabilities: {metadata['capabilities']}")
        print(f"Confidence: {metadata['confidence']:.2f}")
        print(f"Escalated: {metadata['escalated']}")
        print(f"\nResponse:\n{response}")

    elif cmd == "train":
        orchestrator = SAMParityOrchestrator()
        orchestrator.trigger_training()

    elif cmd == "record":
        if len(sys.argv) < 4:
            print("Usage: sam_parity_orchestrator.py record <request> <response>")
            return

        request = sys.argv[2]
        response = sys.argv[3]
        orchestrator = SAMParityOrchestrator()
        orchestrator.record_claude_response(request, response)
        print("Recorded for learning")

    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
