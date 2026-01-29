"""
SAM Voice Module - Text-to-Speech, Voice Cloning, and Audio Processing

This module provides a comprehensive voice system for SAM including:
- Text-to-Speech with multiple engines (macOS, Coqui, RVC)
- Voice cloning via RVC
- Audio preprocessing for TTS
- Voice caching with LRU eviction
- Voice training pipeline
- HTTP API server for voice services
- Voice extraction from multi-speaker audio

Usage:
    # Voice output
    from voice import SAMVoice, VoiceConfig, MacOSVoice
    voice = SAMVoice()
    voice.speak("Hello world")

    # Voice settings
    from voice import VoiceSettings, get_voice_settings, QualityLevel
    settings = get_voice_settings()
    settings.enabled = True
    settings.save()

    # Voice pipeline
    from voice import SAMVoicePipeline, VoicePipelineConfig
    pipeline = SAMVoicePipeline()
    pipeline.start()

    # Voice cache
    from voice import VoiceCache, get_cache
    cache = VoiceCache()

    # Voice bridge
    from voice import VoiceBridge, get_bridge
    bridge = get_bridge()

    # Preprocessing
    from voice import VoicePreprocessor, clean_for_tts

    # Voice training
    from voice import VoiceTrainer, voice_status, voice_prepare
"""

# voice_output.py - TTS engines and output
from voice.voice_output import (
    VoiceConfig,
    VoiceEngine,
    MacOSVoice,
    CoquiVoice,
    RVCVoice,
    SAMVoice,
)

# voice_settings.py - Persistent voice configuration
from voice.voice_settings import (
    VoiceSettings,
    VoiceSettingsManager,
    QualityLevel,
    QUALITY_PRESETS,
    get_voice_settings,
    save_voice_settings,
    update_voice_settings,
    reset_voice_settings,
    get_available_voices,
    api_get_voice_settings,
    api_update_voice_settings,
)

# voice_pipeline.py - Complete voice interaction pipeline
from voice.voice_pipeline import (
    SAMVoicePipeline,
    VoicePipelineConfig,
    create_voice_pipeline,
)

# voice_cache.py - TTS caching with LRU eviction
from voice.voice_cache import (
    VoiceCache,
    CacheEntry,
    get_cache,
)

# voice_bridge.py - RVC voice cloning bridge
from voice.voice_bridge import (
    VoiceBridge,
    # VoiceConfig is already imported from voice_output
    get_bridge,
    speak,
    list_voices,
)

# voice_preprocessor.py - Text preprocessing for TTS
from voice.voice_preprocessor import (
    VoicePreprocessor,
    PreprocessorConfig,
    URLHandling,
    CodeBlockHandling,
    EmojiHandling,
    clean_for_tts,
    split_for_tts,
    number_to_words,
    float_to_words,
)

# voice_trainer.py - RVC voice training
from voice.voice_trainer import (
    VoiceTrainer,
    get_trainer,
    voice_status,
    voice_prepare,
    voice_start,
    voice_stop,
)

# voice_extraction_pipeline.py - Multi-speaker voice extraction
from voice.voice_extraction_pipeline import (
    VoiceExtractionPipeline,
    Segment,
    SpeakerProfile,
    ExtractionMode,
)

# Note: voice_server.py exports are not included here as it's meant
# to be run as a standalone server, not imported

__all__ = [
    # voice_output
    "VoiceConfig",
    "VoiceEngine",
    "MacOSVoice",
    "CoquiVoice",
    "RVCVoice",
    "SAMVoice",
    # voice_settings
    "VoiceSettings",
    "VoiceSettingsManager",
    "QualityLevel",
    "QUALITY_PRESETS",
    "get_voice_settings",
    "save_voice_settings",
    "update_voice_settings",
    "reset_voice_settings",
    "get_available_voices",
    "api_get_voice_settings",
    "api_update_voice_settings",
    # voice_pipeline
    "SAMVoicePipeline",
    "VoicePipelineConfig",
    "create_voice_pipeline",
    # voice_cache
    "VoiceCache",
    "CacheEntry",
    "get_cache",
    # voice_bridge
    "VoiceBridge",
    "get_bridge",
    "speak",
    "list_voices",
    # voice_preprocessor
    "VoicePreprocessor",
    "PreprocessorConfig",
    "URLHandling",
    "CodeBlockHandling",
    "EmojiHandling",
    "clean_for_tts",
    "split_for_tts",
    "number_to_words",
    "float_to_words",
    # voice_trainer
    "VoiceTrainer",
    "get_trainer",
    "voice_status",
    "voice_prepare",
    "voice_start",
    "voice_stop",
    # voice_extraction_pipeline
    "VoiceExtractionPipeline",
    "Segment",
    "SpeakerProfile",
    "ExtractionMode",
]
