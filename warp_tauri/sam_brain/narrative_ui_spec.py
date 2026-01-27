#!/usr/bin/env python3
"""
SAM Narrative UI Specification

Generates visual specifications for project narratives:
- Infographic symbols and icons
- Parallax layer configurations
- Color palettes by mood
- Animation timings
- Progress visualizations

This file outputs JSON that the Vue frontend consumes
to render beautiful, Apple-like project pages.
"""

import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from enum import Enum


class SymbolSet(Enum):
    """Infographic symbol categories"""
    PROGRESS = "progress"      # Journey indicators
    STATUS = "status"          # Health/state icons
    ACTION = "action"          # Activity type icons
    MOOD = "mood"              # Emotional state icons
    LEVEL = "level"            # Evolution level icons
    CATEGORY = "category"      # Project type icons


# ═══════════════════════════════════════════════════════════════════════════════
# SYMBOL LIBRARY
# ═══════════════════════════════════════════════════════════════════════════════

SYMBOLS = {
    # Progress Journey Symbols
    "journey_start": "◯",
    "journey_progress": "◐",
    "journey_complete": "●",
    "journey_milestone": "◆",
    "journey_current": "◉",

    # Status Indicators
    "status_excellent": "✦",
    "status_good": "✧",
    "status_attention": "⚡",
    "status_critical": "⚠",
    "status_unknown": "◌",

    # Health Hearts
    "health_full": "♥",
    "health_half": "♡",
    "health_empty": "○",

    # Activity Types
    "activity_improved": "↑",
    "activity_fixed": "✓",
    "activity_learned": "✎",
    "activity_integrated": "⟷",
    "activity_detected": "◎",
    "activity_implementing": "⟳",

    # Mood Icons
    "mood_flourishing": "✿",
    "mood_triumphant": "★",
    "mood_momentum": "→",
    "mood_growing": "↗",
    "mood_emerging": "◇",
    "mood_determined": "◈",
    "mood_struggling": "△",

    # Evolution Levels
    "level_1": "①",
    "level_2": "②",
    "level_3": "③",
    "level_4": "④",
    "level_5": "⑤",
    "level_max": "✪",

    # Category Icons
    "category_brain": "🧠",
    "category_visual": "🎨",
    "category_voice": "🎙",
    "category_content": "📝",
    "category_platform": "🌐",

    # Decorative
    "divider_wave": "〰",
    "divider_dots": "···",
    "quote_open": "❝",
    "quote_close": "❞",
    "arrow_journey": "➤",
    "spark": "✧",
    "star_empty": "☆",
    "star_full": "★",
}

# Alternative Unicode-safe versions for terminals
SYMBOLS_SAFE = {
    "journey_start": "[O]",
    "journey_progress": "[=>]",
    "journey_complete": "[*]",
    "journey_milestone": "[+]",
    "status_excellent": "[!]",
    "status_good": "[v]",
    "level_1": "[1]",
    "level_2": "[2]",
    "level_3": "[3]",
    "level_4": "[4]",
    "level_5": "[5]",
}


# ═══════════════════════════════════════════════════════════════════════════════
# COLOR PALETTES
# ═══════════════════════════════════════════════════════════════════════════════

COLOR_PALETTES = {
    # By mood
    "flourishing": {
        "primary": "#10B981",      # Emerald green
        "secondary": "#34D399",
        "accent": "#A7F3D0",
        "background": "#ECFDF5",
        "text": "#065F46",
        "gradient_start": "#10B981",
        "gradient_end": "#059669",
    },
    "triumphant": {
        "primary": "#F59E0B",      # Amber gold
        "secondary": "#FBBF24",
        "accent": "#FDE68A",
        "background": "#FFFBEB",
        "text": "#92400E",
        "gradient_start": "#F59E0B",
        "gradient_end": "#D97706",
    },
    "momentum": {
        "primary": "#3B82F6",      # Blue
        "secondary": "#60A5FA",
        "accent": "#BFDBFE",
        "background": "#EFF6FF",
        "text": "#1E40AF",
        "gradient_start": "#3B82F6",
        "gradient_end": "#2563EB",
    },
    "growing": {
        "primary": "#8B5CF6",      # Purple
        "secondary": "#A78BFA",
        "accent": "#DDD6FE",
        "background": "#F5F3FF",
        "text": "#5B21B6",
        "gradient_start": "#8B5CF6",
        "gradient_end": "#7C3AED",
    },
    "emerging": {
        "primary": "#6B7280",      # Gray (potential)
        "secondary": "#9CA3AF",
        "accent": "#E5E7EB",
        "background": "#F9FAFB",
        "text": "#374151",
        "gradient_start": "#6B7280",
        "gradient_end": "#4B5563",
    },
    "determined": {
        "primary": "#EF4444",      # Red (fire)
        "secondary": "#F87171",
        "accent": "#FECACA",
        "background": "#FEF2F2",
        "text": "#991B1B",
        "gradient_start": "#EF4444",
        "gradient_end": "#DC2626",
    },
    "struggling": {
        "primary": "#F97316",      # Orange (warning warmth)
        "secondary": "#FB923C",
        "accent": "#FED7AA",
        "background": "#FFF7ED",
        "text": "#9A3412",
        "gradient_start": "#F97316",
        "gradient_end": "#EA580C",
    },

    # By category
    "brain": {
        "primary": "#8B5CF6",
        "secondary": "#A78BFA",
        "accent": "#C4B5FD",
        "glow": "rgba(139, 92, 246, 0.3)",
    },
    "visual": {
        "primary": "#EC4899",
        "secondary": "#F472B6",
        "accent": "#FBCFE8",
        "glow": "rgba(236, 72, 153, 0.3)",
    },
    "voice": {
        "primary": "#06B6D4",
        "secondary": "#22D3EE",
        "accent": "#A5F3FC",
        "glow": "rgba(6, 182, 212, 0.3)",
    },
    "content": {
        "primary": "#F59E0B",
        "secondary": "#FBBF24",
        "accent": "#FDE68A",
        "glow": "rgba(245, 158, 11, 0.3)",
    },
    "platform": {
        "primary": "#10B981",
        "secondary": "#34D399",
        "accent": "#A7F3D0",
        "glow": "rgba(16, 185, 129, 0.3)",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PARALLAX CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ParallaxLayer:
    """Configuration for a single parallax layer"""
    id: str
    depth: float         # 0 = foreground, 1 = background
    speed: float         # Scroll speed multiplier
    opacity: float       # Layer opacity
    blur: float          # Gaussian blur in pixels
    content_type: str    # "text", "symbol", "shape", "gradient"
    z_index: int


PARALLAX_PRESETS = {
    "hero_section": [
        ParallaxLayer(
            id="bg_gradient",
            depth=1.0,
            speed=0.1,
            opacity=0.8,
            blur=0,
            content_type="gradient",
            z_index=0
        ),
        ParallaxLayer(
            id="floating_symbols",
            depth=0.8,
            speed=0.2,
            opacity=0.15,
            blur=2,
            content_type="symbol",
            z_index=1
        ),
        ParallaxLayer(
            id="mid_shapes",
            depth=0.5,
            speed=0.4,
            opacity=0.1,
            blur=0,
            content_type="shape",
            z_index=2
        ),
        ParallaxLayer(
            id="content",
            depth=0.0,
            speed=1.0,
            opacity=1.0,
            blur=0,
            content_type="text",
            z_index=10
        ),
    ],

    "timeline_section": [
        ParallaxLayer(
            id="timeline_track",
            depth=0.9,
            speed=0.15,
            opacity=0.5,
            blur=0,
            content_type="shape",
            z_index=0
        ),
        ParallaxLayer(
            id="milestone_markers",
            depth=0.3,
            speed=0.7,
            opacity=1.0,
            blur=0,
            content_type="symbol",
            z_index=5
        ),
        ParallaxLayer(
            id="milestone_content",
            depth=0.0,
            speed=1.0,
            opacity=1.0,
            blur=0,
            content_type="text",
            z_index=10
        ),
    ],

    "horizon_section": [
        ParallaxLayer(
            id="horizon_glow",
            depth=1.0,
            speed=0.05,
            opacity=0.6,
            blur=20,
            content_type="gradient",
            z_index=0
        ),
        ParallaxLayer(
            id="distant_shapes",
            depth=0.85,
            speed=0.1,
            opacity=0.08,
            blur=5,
            content_type="shape",
            z_index=1
        ),
        ParallaxLayer(
            id="near_shapes",
            depth=0.4,
            speed=0.5,
            opacity=0.12,
            blur=0,
            content_type="shape",
            z_index=2
        ),
        ParallaxLayer(
            id="horizon_text",
            depth=0.0,
            speed=1.0,
            opacity=1.0,
            blur=0,
            content_type="text",
            z_index=10
        ),
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# ANIMATION SPECIFICATIONS
# ═══════════════════════════════════════════════════════════════════════════════

ANIMATIONS = {
    "fade_in": {
        "keyframes": [
            {"offset": 0, "opacity": 0, "transform": "translateY(20px)"},
            {"offset": 1, "opacity": 1, "transform": "translateY(0)"},
        ],
        "duration": 600,
        "easing": "ease-out",
    },

    "pulse_glow": {
        "keyframes": [
            {"offset": 0, "box_shadow": "0 0 0 0 rgba(var(--primary), 0.4)"},
            {"offset": 0.5, "box_shadow": "0 0 20px 10px rgba(var(--primary), 0.2)"},
            {"offset": 1, "box_shadow": "0 0 0 0 rgba(var(--primary), 0)"},
        ],
        "duration": 2000,
        "easing": "ease-in-out",
        "iterations": "infinite",
    },

    "float": {
        "keyframes": [
            {"offset": 0, "transform": "translateY(0)"},
            {"offset": 0.5, "transform": "translateY(-10px)"},
            {"offset": 1, "transform": "translateY(0)"},
        ],
        "duration": 3000,
        "easing": "ease-in-out",
        "iterations": "infinite",
    },

    "progress_fill": {
        "keyframes": [
            {"offset": 0, "width": "0%"},
            {"offset": 1, "width": "var(--progress)"},
        ],
        "duration": 1500,
        "easing": "cubic-bezier(0.4, 0, 0.2, 1)",
    },

    "milestone_pop": {
        "keyframes": [
            {"offset": 0, "transform": "scale(0)", "opacity": 0},
            {"offset": 0.6, "transform": "scale(1.2)", "opacity": 1},
            {"offset": 1, "transform": "scale(1)", "opacity": 1},
        ],
        "duration": 400,
        "easing": "cubic-bezier(0.34, 1.56, 0.64, 1)",
    },

    "typewriter": {
        "keyframes": [
            {"offset": 0, "width": "0"},
            {"offset": 1, "width": "100%"},
        ],
        "duration": 2000,
        "easing": "steps(40)",
    },

    "shimmer": {
        "keyframes": [
            {"offset": 0, "background_position": "-200% 0"},
            {"offset": 1, "background_position": "200% 0"},
        ],
        "duration": 3000,
        "easing": "linear",
        "iterations": "infinite",
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# INFOGRAPHIC COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProgressRing:
    """Circular progress indicator spec"""
    size: int = 120
    stroke_width: int = 8
    progress: float = 0.0
    color_primary: str = "#3B82F6"
    color_track: str = "#E5E7EB"
    show_percentage: bool = True
    show_label: bool = True
    label: str = ""
    animation: str = "progress_fill"


@dataclass
class JourneyTimeline:
    """Visual timeline spec"""
    orientation: str = "horizontal"  # or "vertical"
    milestones: List[dict] = field(default_factory=list)
    current_position: float = 0.0
    track_color: str = "#E5E7EB"
    progress_color: str = "#3B82F6"
    milestone_size: int = 24
    show_labels: bool = True
    parallax_enabled: bool = True


@dataclass
class StatCard:
    """Infographic stat card spec"""
    value: str
    label: str
    icon: str
    trend: str = "neutral"  # "up", "down", "neutral"
    trend_value: str = ""
    color_scheme: str = "momentum"
    size: str = "medium"  # "small", "medium", "large"


@dataclass
class MoodIndicator:
    """Visual mood representation"""
    mood: str
    symbol: str
    color: str
    pulse_animation: bool = True
    glow_effect: bool = True


# ═══════════════════════════════════════════════════════════════════════════════
# UI SPEC GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class UISpecGenerator:
    """
    Generates complete UI specifications for a project narrative.
    Output is JSON that Vue frontend consumes.
    """

    def generate_spec(
        self,
        narrative,  # ProjectNarrative from project_narrative.py
    ) -> dict:
        """Generate complete UI spec for a narrative"""

        mood = narrative.mood
        category = narrative.name.lower().replace(" ", "_")

        # Get appropriate palettes
        mood_palette = COLOR_PALETTES.get(mood, COLOR_PALETTES["emerging"])
        category_palette = COLOR_PALETTES.get(
            self._detect_category(narrative),
            COLOR_PALETTES["brain"]
        )

        return {
            "project_id": narrative.project_id,
            "name": narrative.name,

            # Colors
            "colors": {
                "mood": mood_palette,
                "category": category_palette,
                "primary": mood_palette["primary"],
                "background": mood_palette["background"],
            },

            # Symbols
            "symbols": {
                "level": SYMBOLS.get(f"level_{min(narrative.journey_percent // 20 + 1, 5):.0f}", SYMBOLS["level_1"]),
                "mood": SYMBOLS.get(f"mood_{mood}", SYMBOLS["mood_emerging"]),
                "category": SYMBOLS.get(f"category_{self._detect_category(narrative)}", "◯"),
                "health": self._get_health_symbols(narrative.journey_percent),
            },

            # Progress ring
            "progress_ring": asdict(ProgressRing(
                progress=narrative.journey_percent / 100,
                color_primary=mood_palette["primary"],
                label=narrative.hero_metric_label,
            )),

            # Journey timeline
            "journey_timeline": asdict(JourneyTimeline(
                current_position=narrative.journey_percent / 100,
                progress_color=mood_palette["primary"],
                milestones=self._generate_milestones(narrative),
            )),

            # Parallax layers
            "parallax": {
                "hero": [asdict(l) for l in PARALLAX_PRESETS["hero_section"]],
                "timeline": [asdict(l) for l in PARALLAX_PRESETS["timeline_section"]],
                "horizon": [asdict(l) for l in PARALLAX_PRESETS["horizon_section"]],
            },

            # Animations
            "animations": {
                "entrance": ANIMATIONS["fade_in"],
                "progress": ANIMATIONS["progress_fill"],
                "milestone": ANIMATIONS["milestone_pop"],
                "tagline": ANIMATIONS["typewriter"],
                "glow": ANIMATIONS["pulse_glow"],
            },

            # Mood indicator
            "mood_indicator": asdict(MoodIndicator(
                mood=mood,
                symbol=SYMBOLS.get(f"mood_{mood}", "◇"),
                color=mood_palette["primary"],
                pulse_animation=mood in ["flourishing", "triumphant", "momentum"],
                glow_effect=mood in ["flourishing", "triumphant"],
            )),

            # Stat cards
            "stat_cards": self._generate_stat_cards(narrative, mood_palette),

            # Floating symbols for parallax background
            "floating_symbols": self._get_floating_symbols(narrative),
        }

    def _detect_category(self, narrative) -> str:
        """Detect category from narrative"""
        name_lower = narrative.name.lower()
        if "brain" in name_lower or "sam" in name_lower or "intelligence" in name_lower:
            return "brain"
        elif "visual" in name_lower or "image" in name_lower or "character" in name_lower:
            return "visual"
        elif "voice" in name_lower or "speech" in name_lower:
            return "voice"
        elif "content" in name_lower or "writing" in name_lower:
            return "content"
        else:
            return "platform"

    def _get_health_symbols(self, journey_percent: float) -> List[str]:
        """Generate health heart display"""
        full_hearts = int(journey_percent / 20)
        half = 1 if (journey_percent % 20) >= 10 else 0
        empty = 5 - full_hearts - half

        return (
            [SYMBOLS["health_full"]] * full_hearts +
            [SYMBOLS["health_half"]] * half +
            [SYMBOLS["health_empty"]] * empty
        )

    def _generate_milestones(self, narrative) -> List[dict]:
        """Generate milestone data for timeline"""
        milestones = [
            {"position": 0.0, "label": "Origin", "symbol": SYMBOLS["journey_start"]},
            {"position": 0.2, "label": "Level 1", "symbol": SYMBOLS["level_1"]},
            {"position": 0.4, "label": "Level 2", "symbol": SYMBOLS["level_2"]},
            {"position": 0.6, "label": "Level 3", "symbol": SYMBOLS["level_3"]},
            {"position": 0.8, "label": "Level 4", "symbol": SYMBOLS["level_4"]},
            {"position": 1.0, "label": "Mastery", "symbol": SYMBOLS["level_max"]},
        ]

        # Mark current position
        current = narrative.journey_percent / 100
        for m in milestones:
            m["reached"] = m["position"] <= current
            m["current"] = abs(m["position"] - current) < 0.1

        return milestones

    def _generate_stat_cards(self, narrative, palette: dict) -> List[dict]:
        """Generate stat cards for the narrative"""
        return [
            asdict(StatCard(
                value=narrative.hero_metric,
                label=narrative.hero_metric_label,
                icon=SYMBOLS.get(f"level_{narrative.hero_metric.split()[-1]}", SYMBOLS["level_1"]),
                color_scheme=narrative.mood,
                size="large"
            )),
            asdict(StatCard(
                value=f"{narrative.journey_percent:.0f}%",
                label="Journey",
                icon=SYMBOLS["journey_progress"],
                trend="up" if narrative.journey_percent > 50 else "neutral",
                color_scheme=narrative.mood,
                size="medium"
            )),
        ]

    def _get_floating_symbols(self, narrative) -> List[dict]:
        """Get symbols for parallax background"""
        category = self._detect_category(narrative)

        base_symbols = [
            SYMBOLS["spark"],
            SYMBOLS["star_empty"],
            SYMBOLS["journey_milestone"],
        ]

        category_symbol = SYMBOLS.get(f"category_{category}", SYMBOLS["spark"])

        return [
            {"symbol": s, "count": 3, "size_range": [12, 24]}
            for s in base_symbols + [category_symbol]
        ]


def generate_ui_spec_json(narrative) -> str:
    """Generate JSON UI spec for frontend"""
    generator = UISpecGenerator()
    spec = generator.generate_spec(narrative)
    return json.dumps(spec, indent=2, default=str)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("SAM Narrative UI Specification Generator")
        print("\nGenerates visual specs for project pages.")
        print("\nUsage:")
        print("  python narrative_ui_spec.py symbols     # List all symbols")
        print("  python narrative_ui_spec.py colors      # Show color palettes")
        print("  python narrative_ui_spec.py parallax    # Show parallax presets")
        print("  python narrative_ui_spec.py animations  # Show animation specs")
        print("  python narrative_ui_spec.py spec <id>   # Full spec for project")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "symbols":
        print("\n📌 Symbol Library\n")
        for name, symbol in SYMBOLS.items():
            print(f"  {symbol}  {name}")

    elif cmd == "colors":
        print("\n🎨 Color Palettes\n")
        for name, palette in COLOR_PALETTES.items():
            print(f"\n  {name.upper()}")
            for key, value in palette.items():
                print(f"    {key}: {value}")

    elif cmd == "parallax":
        print("\n📐 Parallax Presets\n")
        for name, layers in PARALLAX_PRESETS.items():
            print(f"\n  {name.upper()}")
            for layer in layers:
                print(f"    [{layer.id}] depth={layer.depth} speed={layer.speed}")

    elif cmd == "animations":
        print("\n✨ Animation Specifications\n")
        for name, spec in ANIMATIONS.items():
            print(f"\n  {name}")
            print(f"    duration: {spec['duration']}ms")
            print(f"    easing: {spec['easing']}")

    elif cmd == "spec":
        # Would need actual narrative data
        print("Run with project_narrative.py to generate full spec")

    else:
        print(f"Unknown command: {cmd}")
