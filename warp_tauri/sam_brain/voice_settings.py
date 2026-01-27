#!/usr/bin/env python3
"""
SAM Voice Settings - Persistent configuration for voice output.

Manages voice settings including:
- Voice selection (macOS voices, RVC models)
- Speed and pitch adjustments
- Auto-speak behavior
- Queue management
- Quality levels (fast/balanced/quality)
- Sentence pauses and emphasis

Storage: ~/.sam/voice_settings.json

Usage:
    from voice_settings import VoiceSettings, get_voice_settings, QualityLevel

    settings = get_voice_settings()
    settings.enabled = True
    settings.voice = "dustin"
    settings.quality_level = QualityLevel.QUALITY
    settings.save()

    # Or use presets
    settings = VoiceSettings.from_quality_preset(QualityLevel.BALANCED)

API Integration:
    GET  /api/voice/settings - Get current settings
    PUT  /api/voice/settings - Update settings
"""

import json
import os
from pathlib import Path
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import threading


# Storage location
SAM_CONFIG_DIR = Path.home() / ".sam"
VOICE_SETTINGS_FILE = SAM_CONFIG_DIR / "voice_settings.json"


# =============================================================================
# QUALITY LEVELS AND PRESETS
# =============================================================================

class QualityLevel(Enum):
    """Voice synthesis quality level presets."""
    FAST = "fast"           # macOS say only - instant, robotic
    BALANCED = "balanced"   # F5-TTS, no RVC - natural, moderate speed
    QUALITY = "quality"     # F5-TTS + RVC - best quality, slower


# Quality preset configurations
QUALITY_PRESETS = {
    QualityLevel.FAST: {
        "engine": "macos",
        "rvc_enabled": False,
        "sentence_pause_ms": 100,
        "processing_timeout_ms": 2000,
        "cache_enabled": True,
        "description": "Instant response using macOS TTS. Best for quick feedback."
    },
    QualityLevel.BALANCED: {
        "engine": "f5",
        "rvc_enabled": False,
        "sentence_pause_ms": 150,
        "processing_timeout_ms": 10000,
        "cache_enabled": True,
        "description": "Natural F5-TTS without voice conversion. Good balance."
    },
    QualityLevel.QUALITY: {
        "engine": "f5",
        "rvc_enabled": True,
        "sentence_pause_ms": 200,
        "processing_timeout_ms": 30000,
        "cache_enabled": True,
        "description": "F5-TTS with RVC voice conversion. Best quality."
    },
}


@dataclass
class VoiceSettings:
    """
    Voice output settings with persistence.

    Attributes:
        enabled: Whether voice output is active
        voice: Voice identifier (e.g., "default", "dustin", "daniel")
        speed: Speech rate multiplier (0.5 to 2.0)
        pitch: Pitch shift in semitones (-12 to 12)
        auto_speak: Automatically speak responses
        queue_enabled: Enable speech queue for multiple requests
        volume: Volume level (0.0 to 1.0)
        engine: TTS engine ("macos", "f5", "coqui")
        rvc_enabled: Apply RVC voice conversion
        rvc_model: RVC model to use (e.g., "dustin_steele")
        max_text_length: Maximum characters to speak
        cache_enabled: Cache generated audio
        interruption_enabled: Allow speech interruption
        quality_level: Quality preset ("fast", "balanced", "quality")
        use_rvc: Whether to use RVC voice conversion
        sentence_pause_ms: Pause between sentences in milliseconds
        emphasis_words: List of words to emphasize during speech
    """

    # Core settings
    enabled: bool = True
    voice: str = "default"
    speed: float = 1.0
    pitch: int = 0

    # Behavior settings
    auto_speak: bool = False
    queue_enabled: bool = True
    volume: float = 1.0

    # Engine settings
    engine: str = "macos"
    rvc_enabled: bool = False
    rvc_model: str = "dustin_steele"

    # Performance settings
    max_text_length: int = 5000
    cache_enabled: bool = True
    cache_max_items: int = 100

    # Advanced settings
    interruption_enabled: bool = True
    emotion_prosody: bool = True

    # Quality settings (Phase 6.2.6)
    quality_level: str = "balanced"  # "fast", "balanced", "quality"
    use_rvc: bool = False            # Whether to use RVC (alias for rvc_enabled)
    sentence_pause_ms: int = 150     # Pause between sentences
    emphasis_words: List[str] = field(default_factory=list)  # Words to emphasize
    processing_timeout_ms: int = 10000  # Max time to wait for TTS

    # Metadata
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    version: int = 2

    def __post_init__(self):
        """Synchronize rvc_enabled and use_rvc flags."""
        # Keep rvc_enabled and use_rvc in sync
        if self.use_rvc:
            self.rvc_enabled = True
        elif self.rvc_enabled:
            self.use_rvc = True

    @classmethod
    def from_quality_preset(cls, quality_level: QualityLevel) -> "VoiceSettings":
        """
        Create settings from a quality preset.

        Args:
            quality_level: Desired quality level

        Returns:
            VoiceSettings configured for that quality level
        """
        preset = QUALITY_PRESETS[quality_level]

        return cls(
            quality_level=quality_level.value,
            engine=preset["engine"],
            rvc_enabled=preset["rvc_enabled"],
            use_rvc=preset["rvc_enabled"],
            sentence_pause_ms=preset["sentence_pause_ms"],
            processing_timeout_ms=preset["processing_timeout_ms"],
            cache_enabled=preset["cache_enabled"],
        )

    @classmethod
    def fast(cls) -> "VoiceSettings":
        """Create fast quality settings (macOS say only)."""
        return cls.from_quality_preset(QualityLevel.FAST)

    @classmethod
    def balanced(cls) -> "VoiceSettings":
        """Create balanced quality settings (F5-TTS, no RVC)."""
        return cls.from_quality_preset(QualityLevel.BALANCED)

    @classmethod
    def quality(cls) -> "VoiceSettings":
        """Create high quality settings (F5-TTS + RVC)."""
        return cls.from_quality_preset(QualityLevel.QUALITY)

    def apply_quality_preset(self, quality_level: QualityLevel):
        """
        Apply a quality preset to current settings.

        Args:
            quality_level: Quality level to apply
        """
        preset = QUALITY_PRESETS[quality_level]

        self.quality_level = quality_level.value
        self.engine = preset["engine"]
        self.rvc_enabled = preset["rvc_enabled"]
        self.use_rvc = preset["rvc_enabled"]
        self.sentence_pause_ms = preset["sentence_pause_ms"]
        self.processing_timeout_ms = preset["processing_timeout_ms"]
        self.cache_enabled = preset["cache_enabled"]

    def get_quality_level_enum(self) -> QualityLevel:
        """Get the quality level as an enum."""
        try:
            return QualityLevel(self.quality_level)
        except ValueError:
            return QualityLevel.BALANCED

    def get_quality_description(self) -> str:
        """Get description of current quality level."""
        try:
            level = QualityLevel(self.quality_level)
            return QUALITY_PRESETS[level]["description"]
        except (ValueError, KeyError):
            return "Custom quality settings"

    def add_emphasis_word(self, word: str):
        """Add a word to the emphasis list."""
        if word not in self.emphasis_words:
            self.emphasis_words.append(word)

    def remove_emphasis_word(self, word: str):
        """Remove a word from the emphasis list."""
        if word in self.emphasis_words:
            self.emphasis_words.remove(word)

    def get_estimated_latency_ms(self, text_length: int) -> int:
        """
        Estimate processing latency for given text length.

        Args:
            text_length: Number of characters in text

        Returns:
            Estimated latency in milliseconds
        """
        # Base latencies by engine
        base_latencies = {
            "macos": 100,
            "f5": 3000,
            "coqui": 2000,
            "openvoice": 2500,
        }

        base = base_latencies.get(self.engine, 1000)

        # Per-character time (rough estimate)
        per_char = {
            "macos": 1,
            "f5": 15,
            "coqui": 10,
            "openvoice": 12,
        }

        char_time = per_char.get(self.engine, 10) * text_length

        # RVC overhead
        rvc_overhead = 5000 if self.use_rvc else 0

        return base + char_time + rvc_overhead

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VoiceSettings":
        """Create from dictionary."""
        # Filter to only known fields
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def validate(self) -> List[str]:
        """
        Validate settings and return list of errors.

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not 0.5 <= self.speed <= 2.0:
            errors.append(f"Speed must be between 0.5 and 2.0 (got {self.speed})")

        if not -12 <= self.pitch <= 12:
            errors.append(f"Pitch must be between -12 and 12 (got {self.pitch})")

        if not 0.0 <= self.volume <= 1.0:
            errors.append(f"Volume must be between 0.0 and 1.0 (got {self.volume})")

        if self.engine not in ("macos", "f5", "coqui", "openvoice"):
            errors.append(f"Unknown engine: {self.engine}")

        if self.max_text_length < 100:
            errors.append(f"max_text_length must be at least 100 (got {self.max_text_length})")

        if self.quality_level not in ("fast", "balanced", "quality"):
            errors.append(f"quality_level must be 'fast', 'balanced', or 'quality' (got {self.quality_level})")

        if self.sentence_pause_ms < 0:
            errors.append(f"sentence_pause_ms must be >= 0 (got {self.sentence_pause_ms})")

        if self.processing_timeout_ms < 100:
            errors.append(f"processing_timeout_ms must be >= 100 (got {self.processing_timeout_ms})")

        return errors


class VoiceSettingsManager:
    """
    Manages voice settings with thread-safe persistence.

    Features:
    - Automatic loading on startup
    - Thread-safe save operations
    - Settings validation
    - Default value handling
    """

    _instance: Optional["VoiceSettingsManager"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._settings: Optional[VoiceSettings] = None
        self._file_lock = threading.Lock()
        self._ensure_config_dir()
        self.load()

    @classmethod
    def get_instance(cls) -> "VoiceSettingsManager":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_config_dir(self):
        """Ensure configuration directory exists."""
        SAM_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    def load(self) -> VoiceSettings:
        """
        Load settings from disk.

        Returns:
            VoiceSettings instance (defaults if file doesn't exist)
        """
        with self._file_lock:
            if VOICE_SETTINGS_FILE.exists():
                try:
                    with open(VOICE_SETTINGS_FILE, 'r') as f:
                        data = json.load(f)
                    self._settings = VoiceSettings.from_dict(data)
                except (json.JSONDecodeError, KeyError, TypeError) as e:
                    print(f"Warning: Could not load voice settings: {e}")
                    self._settings = self.get_default()
            else:
                self._settings = self.get_default()

        return self._settings

    def save(self) -> bool:
        """
        Persist current settings to disk.

        Returns:
            True if successful, False otherwise
        """
        if self._settings is None:
            return False

        # Update modification timestamp
        self._settings.last_modified = datetime.now().isoformat()

        with self._file_lock:
            try:
                with open(VOICE_SETTINGS_FILE, 'w') as f:
                    json.dump(self._settings.to_dict(), f, indent=2)
                return True
            except (IOError, OSError) as e:
                print(f"Error saving voice settings: {e}")
                return False

    def get_default(self) -> VoiceSettings:
        """
        Get default voice settings.

        Returns:
            VoiceSettings with default values
        """
        return VoiceSettings()

    def reset_to_default(self) -> VoiceSettings:
        """
        Reset all settings to defaults.

        Returns:
            New default VoiceSettings
        """
        self._settings = self.get_default()
        self.save()
        return self._settings

    @property
    def settings(self) -> VoiceSettings:
        """Get current settings."""
        if self._settings is None:
            self.load()
        return self._settings

    def update(self, **kwargs) -> Dict[str, Any]:
        """
        Update settings with validation.

        Args:
            **kwargs: Settings to update

        Returns:
            Dict with 'success', 'settings', and optionally 'errors'
        """
        if self._settings is None:
            self.load()

        # Create a copy with updates
        current_dict = self._settings.to_dict()
        current_dict.update(kwargs)

        # Validate
        new_settings = VoiceSettings.from_dict(current_dict)
        errors = new_settings.validate()

        if errors:
            return {
                "success": False,
                "errors": errors,
                "settings": self._settings.to_dict()
            }

        # Apply
        self._settings = new_settings
        self.save()

        return {
            "success": True,
            "settings": self._settings.to_dict()
        }

    def get_available_voices(self) -> List[Dict[str, Any]]:
        """
        Get list of available voices.

        Returns:
            List of voice info dictionaries
        """
        voices = [
            {
                "id": "default",
                "name": "System Default",
                "engine": "macos",
                "description": "macOS default voice"
            }
        ]

        # Add macOS voices
        try:
            import subprocess
            result = subprocess.run(
                ["say", "-v", "?"],
                capture_output=True,
                text=True,
                timeout=5
            )
            for line in result.stdout.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    locale = parts[1]
                    # Only include English voices by default
                    if locale.startswith("en"):
                        voices.append({
                            "id": name.lower(),
                            "name": name,
                            "engine": "macos",
                            "locale": locale,
                            "description": f"macOS {name} voice ({locale})"
                        })
        except Exception:
            pass

        # Add RVC voices if available
        rvc_weights = Path.home() / "Projects" / "RVC" / "rvc-webui" / "assets" / "weights"
        if rvc_weights.exists():
            for pth_file in rvc_weights.glob("*.pth"):
                name = pth_file.stem
                voices.append({
                    "id": name.lower().replace(" ", "_"),
                    "name": name.replace("_", " ").title(),
                    "engine": "rvc",
                    "path": str(pth_file),
                    "description": f"RVC voice clone: {name}"
                })

        return voices


# Convenience functions

def get_voice_settings() -> VoiceSettings:
    """Get current voice settings (loads if needed)."""
    return VoiceSettingsManager.get_instance().settings


def save_voice_settings() -> bool:
    """Save current voice settings."""
    return VoiceSettingsManager.get_instance().save()


def update_voice_settings(**kwargs) -> Dict[str, Any]:
    """Update voice settings with validation."""
    return VoiceSettingsManager.get_instance().update(**kwargs)


def reset_voice_settings() -> VoiceSettings:
    """Reset to default settings."""
    return VoiceSettingsManager.get_instance().reset_to_default()


def get_available_voices() -> List[Dict[str, Any]]:
    """Get list of available voices."""
    return VoiceSettingsManager.get_instance().get_available_voices()


# API endpoint handlers

def api_get_voice_settings() -> Dict[str, Any]:
    """
    API handler for GET /api/voice/settings.

    Returns:
        Dict with settings and available voices
    """
    manager = VoiceSettingsManager.get_instance()
    settings = manager.settings

    return {
        "success": True,
        "settings": settings.to_dict(),
        "available_voices": manager.get_available_voices(),
        "engines": ["macos", "f5", "coqui", "openvoice"],
        "quality_levels": {
            "fast": QUALITY_PRESETS[QualityLevel.FAST],
            "balanced": QUALITY_PRESETS[QualityLevel.BALANCED],
            "quality": QUALITY_PRESETS[QualityLevel.QUALITY],
        },
        "current_quality": settings.quality_level,
        "quality_description": settings.get_quality_description(),
        "defaults": VoiceSettings().to_dict()
    }


def api_update_voice_settings(updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    API handler for PUT /api/voice/settings.

    Args:
        updates: Dictionary of settings to update

    Returns:
        Dict with success status and current settings
    """
    manager = VoiceSettingsManager.get_instance()
    return manager.update(**updates)


# CLI interface

def main():
    """Command line interface for voice settings."""
    import argparse

    parser = argparse.ArgumentParser(description="SAM Voice Settings")
    subparsers = parser.add_subparsers(dest="command")

    # show command
    subparsers.add_parser("show", help="Show current settings")

    # set command
    set_parser = subparsers.add_parser("set", help="Set a setting")
    set_parser.add_argument("key", help="Setting key")
    set_parser.add_argument("value", help="Setting value")

    # reset command
    subparsers.add_parser("reset", help="Reset to defaults")

    # voices command
    subparsers.add_parser("voices", help="List available voices")

    # enable/disable commands
    subparsers.add_parser("enable", help="Enable voice output")
    subparsers.add_parser("disable", help="Disable voice output")

    args = parser.parse_args()

    manager = VoiceSettingsManager.get_instance()

    if args.command == "show":
        print("Voice Settings:")
        print("-" * 40)
        settings = manager.settings.to_dict()
        for key, value in sorted(settings.items()):
            print(f"  {key}: {value}")

    elif args.command == "set":
        # Convert value type
        value = args.value
        if value.lower() == "true":
            value = True
        elif value.lower() == "false":
            value = False
        elif value.replace(".", "").replace("-", "").isdigit():
            value = float(value) if "." in args.value else int(value)

        result = manager.update(**{args.key: value})
        if result["success"]:
            print(f"Set {args.key} = {value}")
        else:
            print(f"Error: {result['errors']}")

    elif args.command == "reset":
        manager.reset_to_default()
        print("Settings reset to defaults")

    elif args.command == "voices":
        voices = manager.get_available_voices()
        print(f"Available Voices ({len(voices)}):")
        print("-" * 40)
        for v in voices:
            print(f"  [{v['engine']:8}] {v['id']:20} - {v['description']}")

    elif args.command == "enable":
        manager.update(enabled=True)
        print("Voice output enabled")

    elif args.command == "disable":
        manager.update(enabled=False)
        print("Voice output disabled")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
