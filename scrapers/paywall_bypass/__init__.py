"""
Universal Paywall Bypass System
Advanced, cutting-edge, comprehensive paywall circumvention framework.

Architecture:
- Multi-layer detection and bypass
- Machine learning paywall fingerprinting
- Stealth browser automation
- Distributed proxy rotation
- Community-driven rule database
- Self-healing bypass chains
"""

from .core import PaywallBypasser
from .detector import PaywallDetector
from .methods import BypassMethod, BypassChain
from .browser import StealthBrowser
from .archives import ArchiveLayer
from .extractors import ContentExtractor

__version__ = "1.0.0"
__all__ = [
    "PaywallBypasser",
    "PaywallDetector",
    "BypassMethod",
    "BypassChain",
    "StealthBrowser",
    "ArchiveLayer",
    "ContentExtractor",
]
