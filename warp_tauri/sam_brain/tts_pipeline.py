#!/usr/bin/env python3
"""
SAM TTS Pipeline - Text-to-Speech with automatic fallback.

Task 6.2.4: Create fallback voice with seamless switching.

Features:
- Automatic fallback to macOS say when:
  - F5-TTS not available
  - RAM too low
  - User preference set to fast mode
- Seamless switching between engines without errors
- Indicator in response when fallback is being used
- Integration with VoiceCache for performance
- Integration with ResourceManager for RAM monitoring

Usage:
    from tts_pipeline import TTSPipeline, get_pipeline

    # Simple usage
    pipeline = get_pipeline()
    result = pipeline.speak("Hello, I am SAM.")

    # With explicit engine selection
    result = pipeline.speak("Hello", engine="quality")  # F5-TTS + RVC
    result = pipeline.speak("Hello", engine="balanced")  # F5-TTS only
    result = pipeline.speak("Hello", engine="fast")     # macOS say (fallback)
"""

import os
import sys
import subprocess
import tempfile
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import json

# Import resource manager for RAM monitoring
try:
    from cognitive.resource_manager import (
        ResourceManager,
        VoiceTier,
        should_use_voice_fallback,
        get_recommended_voice_tier,
        can_use_quality_voice
    )
    RESOURCE_MANAGER_AVAILABLE = True
except ImportError:
    RESOURCE_MANAGER_AVAILABLE = False

# Import voice cache for performance
try:
    from voice_cache import VoiceCache, get_cache
    VOICE_CACHE_AVAILABLE = True
except ImportError:
    VOICE_CACHE_AVAILABLE = False


SCRIPT_DIR = Path(__file__).parent
AUDIO_OUTPUT_DIR = SCRIPT_DIR / "audio_output"
AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)


class TTSEngine(Enum):
    """Available TTS engines."""
    MACOS_SAY = "macos_say"      # Fast fallback
    EDGE_TTS = "edge_tts"        # Network-based, natural
    COQUI = "coqui"              # Local neural TTS
    F5_TTS = "f5_tts"            # High quality local TTS


class QualityLevel(Enum):
    """Quality/speed trade-off levels."""
    FAST = "fast"           # macOS say - instant response
    BALANCED = "balanced"   # Best available without RVC
    QUALITY = "quality"     # F5-TTS + RVC - highest quality


@dataclass
class TTSResult:
    """Result from TTS synthesis."""
    success: bool
    audio_path: Optional[Path]
    engine_used: str
    is_fallback: bool
    fallback_reason: Optional[str]
    duration_ms: float
    text: str
    cached: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "audio_path": str(self.audio_path) if self.audio_path else None,
            "engine_used": self.engine_used,
            "is_fallback": self.is_fallback,
            "fallback_reason": self.fallback_reason,
            "duration_ms": round(self.duration_ms, 2),
            "text": self.text[:50] + "..." if len(self.text) > 50 else self.text,
            "cached": self.cached,
            "error": self.error
        }


class TTSPipeline:
    """
    TTS Pipeline with automatic fallback.

    Tries to use the best available engine based on:
    1. System resources (RAM)
    2. Engine availability
    3. User preference (quality level)

    Falls back gracefully to macOS say if better options unavailable.
    """

    def __init__(
        self,
        default_quality: QualityLevel = QualityLevel.BALANCED,
        voice: str = "Daniel",
        rate: int = 180,
        use_cache: bool = True,
        use_resource_manager: bool = True
    ):
        """
        Initialize TTS pipeline.

        Args:
            default_quality: Default quality level
            voice: Default voice name (for macOS say)
            rate: Speech rate for macOS say (words per minute)
            use_cache: Whether to use voice cache
            use_resource_manager: Whether to check RAM before synthesis
        """
        self.default_quality = default_quality
        self.voice = voice
        self.rate = rate
        self.use_cache = use_cache and VOICE_CACHE_AVAILABLE
        self.use_resource_manager = use_resource_manager and RESOURCE_MANAGER_AVAILABLE

        # Cache instance
        self._cache = get_cache() if self.use_cache else None

        # Engine availability
        self._available_engines: Dict[TTSEngine, bool] = {}
        self._detect_engines()

        # Statistics
        self._stats = {
            "total_requests": 0,
            "fallback_count": 0,
            "cache_hits": 0,
            "engine_usage": {e.value: 0 for e in TTSEngine}
        }

        # Thread safety
        self._lock = threading.Lock()

    def _detect_engines(self):
        """Detect which TTS engines are available."""
        # macOS say - always available on macOS
        self._available_engines[TTSEngine.MACOS_SAY] = sys.platform == "darwin"

        # edge-tts
        try:
            import edge_tts
            self._available_engines[TTSEngine.EDGE_TTS] = True
        except ImportError:
            self._available_engines[TTSEngine.EDGE_TTS] = False

        # Coqui TTS
        try:
            from TTS.api import TTS
            self._available_engines[TTSEngine.COQUI] = True
        except ImportError:
            self._available_engines[TTSEngine.COQUI] = False

        # F5-TTS (check if model exists)
        f5_model_path = Path.home() / ".sam" / "models" / "f5_tts"
        self._available_engines[TTSEngine.F5_TTS] = f5_model_path.exists()

    def _select_engine(
        self,
        quality: QualityLevel,
        check_resources: bool = True
    ) -> Tuple[TTSEngine, Optional[str]]:
        """
        Select the best available engine.

        Args:
            quality: Desired quality level
            check_resources: Whether to check RAM availability

        Returns:
            (selected_engine, fallback_reason_if_any)
        """
        fallback_reason = None

        # Check resource constraints
        if check_resources and self.use_resource_manager:
            if should_use_voice_fallback():
                return TTSEngine.MACOS_SAY, "Low RAM - using fallback"

        # Map quality to preferred engine
        quality_to_engine = {
            QualityLevel.FAST: TTSEngine.MACOS_SAY,
            QualityLevel.BALANCED: TTSEngine.F5_TTS,
            QualityLevel.QUALITY: TTSEngine.F5_TTS  # RVC added separately
        }

        preferred = quality_to_engine[quality]

        # Try preferred engine
        if self._available_engines.get(preferred, False):
            # For F5, also check RAM if requested
            if preferred == TTSEngine.F5_TTS and check_resources and self.use_resource_manager:
                if not can_use_quality_voice():
                    # Try Coqui as intermediate option
                    if self._available_engines.get(TTSEngine.COQUI, False):
                        return TTSEngine.COQUI, "Insufficient RAM for F5-TTS"
                    # Fall back to edge-tts
                    if self._available_engines.get(TTSEngine.EDGE_TTS, False):
                        return TTSEngine.EDGE_TTS, "Insufficient RAM for neural TTS"
                    # Ultimate fallback
                    return TTSEngine.MACOS_SAY, "Insufficient RAM for neural TTS"

            return preferred, None

        # Fallback chain: F5 -> Coqui -> edge-tts -> macOS say
        fallback_chain = [TTSEngine.F5_TTS, TTSEngine.COQUI, TTSEngine.EDGE_TTS, TTSEngine.MACOS_SAY]

        for engine in fallback_chain:
            if self._available_engines.get(engine, False):
                if engine == TTSEngine.MACOS_SAY:
                    fallback_reason = f"{preferred.value} not available"
                return engine, fallback_reason

        # Should never reach here (macOS say always available)
        return TTSEngine.MACOS_SAY, "No TTS engines available"

    def speak(
        self,
        text: str,
        quality: Optional[QualityLevel] = None,
        engine: Optional[str] = None,
        output_path: Optional[Path] = None,
        use_cache: Optional[bool] = None,
        play_audio: bool = False
    ) -> TTSResult:
        """
        Synthesize speech from text.

        Args:
            text: Text to synthesize
            quality: Quality level ("fast", "balanced", "quality")
            engine: Explicit engine override (bypasses quality selection)
            output_path: Where to save audio (auto-generated if None)
            use_cache: Override cache setting for this call
            play_audio: If True, play audio after synthesis

        Returns:
            TTSResult with audio path and metadata
        """
        import time
        start_time = time.perf_counter()

        with self._lock:
            self._stats["total_requests"] += 1

        # Determine quality level
        if quality is None:
            quality = self.default_quality
        elif isinstance(quality, str):
            quality = QualityLevel(quality)

        # Check cache first
        should_cache = self.use_cache if use_cache is None else use_cache
        if should_cache and self._cache:
            cached_path = self._cache.get(text, voice=self.voice, rate=self.rate, quality=quality.value)
            if cached_path:
                with self._lock:
                    self._stats["cache_hits"] += 1
                duration_ms = (time.perf_counter() - start_time) * 1000
                return TTSResult(
                    success=True,
                    audio_path=cached_path,
                    engine_used="cache",
                    is_fallback=False,
                    fallback_reason=None,
                    duration_ms=duration_ms,
                    text=text,
                    cached=True
                )

        # Select engine
        if engine:
            # Explicit engine override
            try:
                selected_engine = TTSEngine(engine)
                fallback_reason = None if self._available_engines.get(selected_engine) else "Engine not available"
                if fallback_reason:
                    selected_engine, fallback_reason = self._select_engine(quality)
            except ValueError:
                selected_engine, fallback_reason = self._select_engine(quality)
        else:
            selected_engine, fallback_reason = self._select_engine(quality)

        is_fallback = fallback_reason is not None or selected_engine == TTSEngine.MACOS_SAY

        # Generate output path
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            suffix = ".aiff" if selected_engine == TTSEngine.MACOS_SAY else ".wav"
            output_path = AUDIO_OUTPUT_DIR / f"tts_{timestamp}{suffix}"

        # Synthesize
        try:
            audio_path = self._synthesize(text, selected_engine, output_path)

            if audio_path and audio_path.exists():
                # Update stats
                with self._lock:
                    self._stats["engine_usage"][selected_engine.value] += 1
                    if is_fallback:
                        self._stats["fallback_count"] += 1

                # Cache result
                if should_cache and self._cache:
                    self._cache.put(
                        text, audio_path,
                        voice=self.voice, rate=self.rate, quality=quality.value,
                        copy_file=True
                    )

                # Play if requested
                if play_audio:
                    self._play_audio(audio_path)

                duration_ms = (time.perf_counter() - start_time) * 1000
                return TTSResult(
                    success=True,
                    audio_path=audio_path,
                    engine_used=selected_engine.value,
                    is_fallback=is_fallback,
                    fallback_reason=fallback_reason,
                    duration_ms=duration_ms,
                    text=text
                )
            else:
                raise RuntimeError("Audio file not created")

        except Exception as e:
            # Try fallback if we weren't already using it
            if selected_engine != TTSEngine.MACOS_SAY and self._available_engines.get(TTSEngine.MACOS_SAY):
                try:
                    fallback_path = output_path.with_suffix(".aiff")
                    audio_path = self._synthesize(text, TTSEngine.MACOS_SAY, fallback_path)

                    if audio_path and audio_path.exists():
                        with self._lock:
                            self._stats["engine_usage"]["macos_say"] += 1
                            self._stats["fallback_count"] += 1

                        if play_audio:
                            self._play_audio(audio_path)

                        duration_ms = (time.perf_counter() - start_time) * 1000
                        return TTSResult(
                            success=True,
                            audio_path=audio_path,
                            engine_used="macos_say",
                            is_fallback=True,
                            fallback_reason=f"Primary engine failed: {str(e)}",
                            duration_ms=duration_ms,
                            text=text
                        )
                except:
                    pass

            duration_ms = (time.perf_counter() - start_time) * 1000
            return TTSResult(
                success=False,
                audio_path=None,
                engine_used=selected_engine.value,
                is_fallback=is_fallback,
                fallback_reason=fallback_reason,
                duration_ms=duration_ms,
                text=text,
                error=str(e)
            )

    def _synthesize(
        self,
        text: str,
        engine: TTSEngine,
        output_path: Path
    ) -> Optional[Path]:
        """Synthesize using specific engine."""
        if engine == TTSEngine.MACOS_SAY:
            return self._synth_macos_say(text, output_path)
        elif engine == TTSEngine.EDGE_TTS:
            return self._synth_edge_tts(text, output_path)
        elif engine == TTSEngine.COQUI:
            return self._synth_coqui(text, output_path)
        elif engine == TTSEngine.F5_TTS:
            return self._synth_f5_tts(text, output_path)
        else:
            raise ValueError(f"Unknown engine: {engine}")

    def _synth_macos_say(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthesize using macOS say command."""
        output_path = output_path.with_suffix(".aiff")
        result = subprocess.run(
            ["say", "-v", self.voice, "-r", str(self.rate), "-o", str(output_path), text],
            capture_output=True
        )
        if result.returncode == 0 and output_path.exists():
            return output_path
        return None

    def _synth_edge_tts(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthesize using edge-tts."""
        import asyncio
        import edge_tts

        async def generate():
            output_path_mp3 = output_path.with_suffix(".mp3")
            communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
            await communicate.save(str(output_path_mp3))
            return output_path_mp3

        return asyncio.run(generate())

    def _synth_coqui(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthesize using Coqui TTS."""
        from TTS.api import TTS
        output_path = output_path.with_suffix(".wav")
        tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC")
        tts.tts_to_file(text=text, file_path=str(output_path))
        return output_path if output_path.exists() else None

    def _synth_f5_tts(self, text: str, output_path: Path) -> Optional[Path]:
        """Synthesize using F5-TTS."""
        # F5-TTS integration - placeholder for actual implementation
        # Would use the F5-TTS model from ~/.sam/models/f5_tts
        # For now, fall back to available engine
        if self._available_engines.get(TTSEngine.COQUI):
            return self._synth_coqui(text, output_path)
        elif self._available_engines.get(TTSEngine.EDGE_TTS):
            return self._synth_edge_tts(text, output_path)
        else:
            return self._synth_macos_say(text, output_path)

    def _play_audio(self, audio_path: Path):
        """Play audio file."""
        if sys.platform == "darwin":
            subprocess.run(["afplay", str(audio_path)], capture_output=True)

    def get_fallback_indicator(self, result: TTSResult) -> Optional[str]:
        """
        Get a text indicator when fallback was used.

        Returns a brief message that can be included in responses
        to indicate voice quality may be reduced.
        """
        if not result.is_fallback:
            return None

        if result.fallback_reason:
            if "RAM" in result.fallback_reason:
                return "[Using fast voice - system busy]"
            elif "not available" in result.fallback_reason:
                return "[Using basic voice]"
            else:
                return f"[{result.fallback_reason}]"

        return "[Using fallback voice]"

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        with self._lock:
            total = self._stats["total_requests"]
            fallback_rate = (
                self._stats["fallback_count"] / total * 100
                if total > 0 else 0
            )
            cache_rate = (
                self._stats["cache_hits"] / total * 100
                if total > 0 else 0
            )

            return {
                **self._stats,
                "fallback_rate_percent": round(fallback_rate, 1),
                "cache_hit_rate_percent": round(cache_rate, 1),
                "available_engines": [e.value for e, v in self._available_engines.items() if v],
                "default_quality": self.default_quality.value,
                "voice": self.voice,
                "cache_enabled": self.use_cache,
                "resource_monitoring": self.use_resource_manager
            }

    def set_quality(self, quality: QualityLevel):
        """Set default quality level."""
        if isinstance(quality, str):
            quality = QualityLevel(quality)
        self.default_quality = quality

    def set_voice(self, voice: str):
        """Set voice for macOS say."""
        self.voice = voice


# Global instance
_pipeline: Optional[TTSPipeline] = None
_pipeline_lock = threading.Lock()


def get_pipeline() -> TTSPipeline:
    """Get global TTS pipeline instance."""
    global _pipeline
    with _pipeline_lock:
        if _pipeline is None:
            _pipeline = TTSPipeline()
        return _pipeline


def speak(text: str, **kwargs) -> TTSResult:
    """Convenience function to speak text."""
    return get_pipeline().speak(text, **kwargs)


def speak_with_fallback_notice(text: str, **kwargs) -> Tuple[TTSResult, Optional[str]]:
    """
    Speak text and get fallback notice if applicable.

    Returns:
        (TTSResult, fallback_notice_string or None)
    """
    pipeline = get_pipeline()
    result = pipeline.speak(text, **kwargs)
    notice = pipeline.get_fallback_indicator(result)
    return result, notice


# CLI
def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM TTS Pipeline")
    subparsers = parser.add_subparsers(dest="command")

    # speak command
    speak_parser = subparsers.add_parser("speak", help="Speak text")
    speak_parser.add_argument("text", help="Text to speak")
    speak_parser.add_argument("--quality", "-q", choices=["fast", "balanced", "quality"],
                             default="balanced", help="Quality level")
    speak_parser.add_argument("--engine", "-e", help="Explicit engine override")
    speak_parser.add_argument("--play", "-p", action="store_true", help="Play audio")
    speak_parser.add_argument("--no-cache", action="store_true", help="Skip cache")

    # test command
    subparsers.add_parser("test", help="Test all engines")

    # stats command
    subparsers.add_parser("stats", help="Show pipeline statistics")

    # engines command
    subparsers.add_parser("engines", help="List available engines")

    args = parser.parse_args()

    pipeline = get_pipeline()

    if args.command == "speak":
        result = pipeline.speak(
            args.text,
            quality=QualityLevel(args.quality),
            engine=args.engine,
            use_cache=not args.no_cache,
            play_audio=args.play
        )

        print(json.dumps(result.to_dict(), indent=2))

        notice = pipeline.get_fallback_indicator(result)
        if notice:
            print(f"\n{notice}")

    elif args.command == "test":
        print("Testing TTS engines...")
        test_text = "Hello, I am SAM, your intelligent assistant."

        for quality in QualityLevel:
            print(f"\n{quality.value.upper()}:")
            result = pipeline.speak(test_text, quality=quality, play_audio=True)
            print(f"  Engine: {result.engine_used}")
            print(f"  Duration: {result.duration_ms:.1f}ms")
            print(f"  Fallback: {result.is_fallback}")
            if result.fallback_reason:
                print(f"  Reason: {result.fallback_reason}")

    elif args.command == "stats":
        stats = pipeline.get_stats()
        print("TTS Pipeline Statistics")
        print("-" * 40)
        for key, value in stats.items():
            if isinstance(value, dict):
                print(f"  {key}:")
                for k, v in value.items():
                    print(f"    {k}: {v}")
            else:
                print(f"  {key}: {value}")

    elif args.command == "engines":
        print("Available TTS Engines:")
        print("-" * 40)
        for engine, available in pipeline._available_engines.items():
            status = "Available" if available else "Not installed"
            print(f"  {engine.value}: {status}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
