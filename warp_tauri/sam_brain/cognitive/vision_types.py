"""
Shared vision type definitions.

Single source of truth for VisionTier and related enums.
All vision modules should import from here.
"""

from enum import Enum


class VisionTier(Enum):
    """Vision processing tiers ordered by resource cost."""
    ZERO_COST = 0      # Apple Vision, PIL (instant, 0 extra RAM)
    LIGHTWEIGHT = 1    # CoreML, small classifiers (~200MB)
    LOCAL_VLM = 2      # nanoLLaVA (~4GB RAM)
    CLAUDE = 3         # Claude via terminal bridge (network, 0 local RAM)
