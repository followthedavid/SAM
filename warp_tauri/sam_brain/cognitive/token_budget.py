"""
Token Budget Manager for SAM Cognitive System

Manages token allocation across system prompt, context, and generation
to stay within hardware limits (512 for 1.5B, 256 for 3B).
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class TokenBudget:
    """Token allocation for a generation request."""
    total_available: int      # 512 or 256
    system_prompt: int        # Fixed allocation for system prompt
    context: int              # Compressed context from RAG/memory
    query: int                # User input
    generation_reserve: int   # Reserved for response generation
    actual_used: int = 0      # Actual tokens used

    @property
    def remaining_for_generation(self) -> int:
        """Tokens available for generation."""
        used = self.system_prompt + self.context + self.query
        return max(0, self.total_available - used)

    @property
    def utilization(self) -> float:
        """Current utilization ratio (0-1)."""
        used = self.system_prompt + self.context + self.query
        return min(1.0, used / self.total_available) if self.total_available > 0 else 0

    def is_valid(self) -> bool:
        """Check if budget allows for meaningful generation."""
        return self.remaining_for_generation >= 50  # Minimum for response

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_available": self.total_available,
            "system_prompt": self.system_prompt,
            "context": self.context,
            "query": self.query,
            "generation_reserve": self.generation_reserve,
            "remaining": self.remaining_for_generation,
            "utilization": self.utilization,
            "is_valid": self.is_valid()
        }


class TokenBudgetManager:
    """
    Manages token allocation to maximize context utilization.

    Budget Structure (512 tokens for 1.5B):
    - System prompt:     80 tokens (15%)
    - Compressed context: 250 tokens (49%)
    - User query:        82 tokens (16%)
    - Generation:        100 tokens (20%)

    Budget Structure (256 tokens for 3B):
    - System prompt:     40 tokens (15%)
    - Compressed context: 100 tokens (39%)
    - User query:        46 tokens (18%)
    - Generation:        70 tokens (28%)
    """

    # Token limits by model
    MODEL_LIMITS = {
        "1.5b": 512,
        "3b": 256
    }

    # Allocation ratios by model
    ALLOCATION_RATIOS = {
        "1.5b": {
            "system": 0.15,      # 80 tokens
            "context": 0.49,    # 250 tokens
            "query": 0.16,      # 82 tokens
            "generation": 0.20  # 100 tokens
        },
        "3b": {
            "system": 0.15,     # 40 tokens
            "context": 0.39,    # 100 tokens
            "query": 0.18,      # 46 tokens
            "generation": 0.28  # 70 tokens
        }
    }

    # Qwen tokenization multiplier (words to tokens)
    TOKENIZATION_FACTOR = 1.3

    def __init__(self):
        """Initialize token budget manager."""
        self._allocation_history = []

    def allocate(
        self,
        model_key: str,
        system_prompt: str,
        context: str,
        query: str,
        compressor: Optional[Any] = None
    ) -> Tuple[TokenBudget, str, str, str]:
        """
        Allocate tokens and compress if needed.

        Args:
            model_key: "1.5b" or "3b"
            system_prompt: System prompt text
            context: Context text (will be compressed if needed)
            query: User query
            compressor: Optional ContextualCompressor instance

        Returns:
            (TokenBudget, compressed_system, compressed_context, truncated_query)
        """
        total = self.MODEL_LIMITS.get(model_key, 512)
        ratios = self.ALLOCATION_RATIOS.get(model_key, self.ALLOCATION_RATIOS["1.5b"])

        # Calculate allocations
        system_budget = int(total * ratios["system"])
        context_budget = int(total * ratios["context"])
        query_budget = int(total * ratios["query"])
        generation_budget = int(total * ratios["generation"])

        # Count current tokens
        system_tokens = self.count_tokens(system_prompt)
        context_tokens = self.count_tokens(context)
        query_tokens = self.count_tokens(query)

        # Compress/truncate as needed
        final_system = system_prompt
        final_context = context
        final_query = query

        # Truncate system prompt if over budget
        if system_tokens > system_budget:
            final_system = self._truncate_to_tokens(system_prompt, system_budget)
            system_tokens = system_budget

        # Compress context if over budget
        if context_tokens > context_budget:
            if compressor:
                final_context = compressor.compress_for_query(
                    context, query, target_tokens=context_budget
                )
            else:
                final_context = self._truncate_to_tokens(context, context_budget)
            context_tokens = context_budget

        # Truncate query if over budget
        if query_tokens > query_budget:
            final_query = self._truncate_to_tokens(query, query_budget)
            query_tokens = query_budget

        budget = TokenBudget(
            total_available=total,
            system_prompt=system_tokens,
            context=context_tokens,
            query=query_tokens,
            generation_reserve=generation_budget
        )

        self._allocation_history.append(budget)

        return budget, final_system, final_context, final_query

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses Qwen tokenization factor (words * 1.3).
        """
        if not text:
            return 0

        words = len(text.split())
        return int(words * self.TOKENIZATION_FACTOR)

    def estimate_tokens_needed(
        self,
        system_prompt: str,
        context: str,
        query: str,
        expected_response_length: int = 100
    ) -> int:
        """Estimate total tokens needed for a request."""
        return (
            self.count_tokens(system_prompt) +
            self.count_tokens(context) +
            self.count_tokens(query) +
            expected_response_length
        )

    def get_model_for_budget(
        self,
        system_prompt: str,
        context: str,
        query: str,
        preferred_model: str = "1.5b"
    ) -> str:
        """
        Get best model that fits the token budget.

        Returns preferred model if it fits, otherwise fallback.
        """
        needed = self.estimate_tokens_needed(system_prompt, context, query)

        # Try preferred model first
        if needed <= self.MODEL_LIMITS.get(preferred_model, 512):
            return preferred_model

        # If preferred is 3B but doesn't fit, try 1.5B
        if preferred_model == "3b" and needed <= self.MODEL_LIMITS["1.5b"]:
            return "1.5b"

        # Default to 1.5B (more context)
        return "1.5b"

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token budget."""
        if not text:
            return ""

        words = text.split()
        target_words = int(max_tokens / self.TOKENIZATION_FACTOR)

        if len(words) <= target_words:
            return text

        # Truncate with ellipsis
        return " ".join(words[:target_words - 1]) + "..."

    def get_allocation_stats(self) -> Dict[str, Any]:
        """Get statistics on token allocations."""
        if not self._allocation_history:
            return {"total_allocations": 0}

        total = len(self._allocation_history)
        avg_utilization = sum(b.utilization for b in self._allocation_history) / total
        valid_count = sum(1 for b in self._allocation_history if b.is_valid())

        return {
            "total_allocations": total,
            "average_utilization": avg_utilization,
            "valid_ratio": valid_count / total,
            "last_budget": self._allocation_history[-1].to_dict() if self._allocation_history else None
        }


# Preset token budgets for quick access
PRESET_BUDGETS = {
    "1.5b_full": TokenBudget(
        total_available=512,
        system_prompt=80,
        context=250,
        query=82,
        generation_reserve=100
    ),
    "1.5b_minimal": TokenBudget(
        total_available=512,
        system_prompt=40,
        context=300,
        query=72,
        generation_reserve=100
    ),
    "3b_full": TokenBudget(
        total_available=256,
        system_prompt=40,
        context=100,
        query=46,
        generation_reserve=70
    ),
    "3b_minimal": TokenBudget(
        total_available=256,
        system_prompt=20,
        context=120,
        query=46,
        generation_reserve=70
    )
}


def get_preset_budget(preset_name: str) -> TokenBudget:
    """Get a preset token budget by name."""
    return PRESET_BUDGETS.get(preset_name, PRESET_BUDGETS["1.5b_full"])


if __name__ == "__main__":
    # Demo
    print("Token Budget Manager Demo")
    print("=" * 50)

    manager = TokenBudgetManager()

    # Test inputs
    system_prompt = """You are SAM, a confident and charming AI assistant.
    Be witty, direct, and helpful. Use natural humor."""

    context = """The user previously asked about Python decorators.
    They mentioned they are working on a Flask application.
    The codebase uses type hints throughout.""" * 5  # Make it longer

    query = "How do I create a custom decorator that logs function calls?"

    print(f"System tokens: {manager.count_tokens(system_prompt)}")
    print(f"Context tokens: {manager.count_tokens(context)}")
    print(f"Query tokens: {manager.count_tokens(query)}")
    print()

    # Test 1.5B allocation
    print("1.5B Allocation:")
    budget, sys, ctx, q = manager.allocate("1.5b", system_prompt, context, query)
    print(f"  Budget: {budget.to_dict()}")
    print(f"  Context compressed: {manager.count_tokens(context)} -> {manager.count_tokens(ctx)}")
    print()

    # Test 3B allocation
    print("3B Allocation:")
    budget, sys, ctx, q = manager.allocate("3b", system_prompt, context, query)
    print(f"  Budget: {budget.to_dict()}")
    print()

    print("Stats:", manager.get_allocation_stats())
