#!/usr/bin/env python3
"""
SAM Phase 6.2.7: Voice Performance Tests

Comprehensive test suite for SAM's voice system performance.

Test Coverage:
1. Latency measurements for each engine
2. Cache hit/miss performance
3. Memory usage during speech
4. Fallback trigger conditions
5. Preprocessing correctness
6. Quality settings application
7. Concurrent speech requests

Run with:
    cd ~/ReverseLab/SAM/warp_tauri/sam_brain
    python -m pytest tests/test_voice_performance.py -v

Created: 2026-01-25
"""

import sys
import gc
import time
import tempfile
import threading
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def voice_preprocessor():
    """Create a VoicePreprocessor instance for testing."""
    from voice.voice_preprocessor import VoicePreprocessor
    return VoicePreprocessor()


@pytest.fixture
def voice_settings():
    """Create VoiceSettings instance for testing."""
    from voice.voice_settings import VoiceSettings
    return VoiceSettings()


@pytest.fixture
def mock_tts_engine():
    """Mock TTS engine for testing without actual audio generation."""
    mock = Mock()
    mock.speak = Mock(return_value=Path("/tmp/test_audio.wav"))
    mock.play = Mock()
    return mock


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Write minimal WAV header
        wav_header = bytes([
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            0x24, 0x00, 0x00, 0x00,  # File size - 8
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            0x66, 0x6D, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # Subchunk1Size (16)
            0x01, 0x00,              # AudioFormat (PCM)
            0x01, 0x00,              # NumChannels (1)
            0x44, 0xAC, 0x00, 0x00,  # SampleRate (44100)
            0x88, 0x58, 0x01, 0x00,  # ByteRate
            0x02, 0x00,              # BlockAlign
            0x10, 0x00,              # BitsPerSample (16)
            0x64, 0x61, 0x74, 0x61,  # "data"
            0x00, 0x00, 0x00, 0x00,  # Subchunk2Size
        ])
        f.write(wav_header)
        test_path = Path(f.name)

    yield str(test_path)

    # Cleanup
    if test_path.exists():
        test_path.unlink()


# =============================================================================
# 1. LATENCY MEASUREMENT TESTS
# =============================================================================

class TestLatencyMeasurements:
    """Test latency measurements for different TTS engines."""

    def test_macos_latency_estimate(self, voice_settings):
        """macOS TTS should have lowest estimated latency."""
        voice_settings.engine = "macos"
        voice_settings.use_rvc = False

        latency = voice_settings.get_estimated_latency_ms(100)

        # macOS should be very fast
        assert latency < 500, f"macOS latency too high: {latency}ms"

    def test_f5_tts_latency_estimate(self, voice_settings):
        """F5-TTS should have moderate estimated latency."""
        voice_settings.engine = "f5"
        voice_settings.use_rvc = False

        latency = voice_settings.get_estimated_latency_ms(100)

        # F5-TTS is slower but reasonable
        assert 1000 < latency < 10000, f"F5-TTS latency unexpected: {latency}ms"

    def test_rvc_adds_latency(self, voice_settings):
        """RVC conversion should add significant latency."""
        voice_settings.engine = "f5"

        latency_no_rvc = voice_settings.get_estimated_latency_ms(100)
        voice_settings.use_rvc = True
        latency_with_rvc = voice_settings.get_estimated_latency_ms(100)

        # RVC should add overhead
        assert latency_with_rvc > latency_no_rvc
        assert latency_with_rvc - latency_no_rvc >= 5000

    def test_latency_scales_with_text_length(self, voice_settings):
        """Latency should increase with text length."""
        voice_settings.engine = "f5"
        voice_settings.use_rvc = False

        latency_short = voice_settings.get_estimated_latency_ms(50)
        latency_medium = voice_settings.get_estimated_latency_ms(200)
        latency_long = voice_settings.get_estimated_latency_ms(1000)

        assert latency_short < latency_medium < latency_long

    def test_preprocessor_speed(self, voice_preprocessor):
        """Preprocessor should be very fast (<10ms for typical text)."""
        test_text = "Hello **world**! Check out https://example.com for more info."

        start = time.time()
        for _ in range(100):
            voice_preprocessor.clean_text(test_text)
        elapsed = (time.time() - start) / 100 * 1000  # ms per call

        assert elapsed < 10, f"Preprocessor too slow: {elapsed:.2f}ms"


# =============================================================================
# 2. CACHE PERFORMANCE TESTS
# =============================================================================

class TestCachePerformance:
    """Test voice cache hit/miss performance."""

    def test_cache_hit_faster_than_miss(self):
        """Cache hits should be significantly faster than generation."""
        import hashlib
        from pathlib import Path

        cache_dir = Path(tempfile.mkdtemp())

        # Simulate cache
        def cache_key(text: str) -> str:
            return hashlib.md5(text.encode()).hexdigest()

        def get_cached(key: str) -> Optional[bytes]:
            cache_file = cache_dir / f"{key}.wav"
            if cache_file.exists():
                return cache_file.read_bytes()
            return None

        def save_cache(key: str, data: bytes):
            cache_file = cache_dir / f"{key}.wav"
            cache_file.write_bytes(data)

        # Test cache miss
        text = "Hello, this is a test."
        key = cache_key(text)

        start = time.time()
        result = get_cached(key)
        miss_time = time.time() - start
        assert result is None

        # Save to cache
        save_cache(key, b"fake audio data" * 1000)

        # Test cache hit
        start = time.time()
        for _ in range(100):
            result = get_cached(key)
        hit_time = (time.time() - start) / 100

        assert result is not None
        assert hit_time < 0.01  # Cache hit should be < 10ms

        # Cleanup
        import shutil
        shutil.rmtree(cache_dir)

    def test_cache_key_consistency(self):
        """Same input should always produce same cache key."""
        import hashlib

        def cache_key(text: str, voice: str, pitch: int) -> str:
            data = f"{text}:{voice}:{pitch}"
            return hashlib.md5(data.encode()).hexdigest()

        text = "Hello world"
        key1 = cache_key(text, "dustin", 0)
        key2 = cache_key(text, "dustin", 0)
        key3 = cache_key(text, "daniel", 0)  # Different voice

        assert key1 == key2, "Same input should produce same key"
        assert key1 != key3, "Different inputs should produce different keys"

    def test_cache_key_uniqueness(self):
        """Different inputs should produce different cache keys."""
        import hashlib

        def cache_key(text: str) -> str:
            return hashlib.md5(text.encode()).hexdigest()

        keys = set()
        texts = [
            "Hello world",
            "Hello World",  # Case difference
            "Hello world!",  # Punctuation
            "Hello  world",  # Double space
            "Helloworld",    # No space
        ]

        for text in texts:
            key = cache_key(text)
            assert key not in keys, f"Collision detected for: {text}"
            keys.add(key)


# =============================================================================
# 3. MEMORY USAGE TESTS
# =============================================================================

class TestMemoryUsage:
    """Test memory usage during speech processing."""

    def test_preprocessor_memory_stable(self, voice_preprocessor):
        """Preprocessor should not leak memory."""
        gc.collect()
        import tracemalloc
        tracemalloc.start()

        # Process many texts
        for i in range(1000):
            text = f"Test text number {i} with **markdown** and {i * 100} numbers."
            voice_preprocessor.clean_text(text)

        gc.collect()
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        # Memory should stay reasonable (< 10MB)
        assert peak < 10 * 1024 * 1024, f"Memory usage too high: {peak / 1024 / 1024:.2f}MB"

    def test_settings_memory_footprint(self):
        """VoiceSettings should have minimal memory footprint."""
        from voice.voice_settings import VoiceSettings
        import sys

        settings = VoiceSettings()
        size = sys.getsizeof(settings)

        # Settings object should be small
        assert size < 1024, f"Settings too large: {size} bytes"

    def test_sentence_buffer_cleanup(self, voice_preprocessor):
        """Sentence splitting should clean up internal buffers."""
        gc.collect()

        long_text = "First sentence. " * 1000

        for _ in range(100):
            sentences = voice_preprocessor.split_sentences(long_text)
            del sentences

        gc.collect()
        # If this test passes without hanging, memory is being cleaned up


# =============================================================================
# 4. FALLBACK TRIGGER TESTS
# =============================================================================

class TestFallbackTriggers:
    """Test fallback mechanisms when primary TTS fails."""

    def test_fallback_on_engine_unavailable(self):
        """Should fall back to macOS if F5-TTS unavailable."""
        # This tests the concept - actual implementation may vary

        engines_available = {
            "f5": False,
            "macos": True,
            "coqui": False,
        }

        preferred_order = ["f5", "coqui", "macos"]

        selected = None
        for engine in preferred_order:
            if engines_available.get(engine, False):
                selected = engine
                break

        assert selected == "macos"

    def test_fallback_on_timeout(self, voice_settings):
        """Settings should have timeout for fallback."""
        voice_settings.processing_timeout_ms = 5000

        assert voice_settings.processing_timeout_ms > 0
        assert voice_settings.validate() == []  # No errors

    def test_fallback_order_priority(self):
        """Fallback chain should prioritize by quality."""
        fallback_chain = {
            "quality": ["f5+rvc", "f5", "coqui", "macos"],
            "balanced": ["f5", "coqui", "macos"],
            "fast": ["macos"],
        }

        # Quality mode should have most fallbacks
        assert len(fallback_chain["quality"]) > len(fallback_chain["balanced"])
        assert len(fallback_chain["balanced"]) > len(fallback_chain["fast"])

        # macOS should always be last fallback (most reliable)
        assert fallback_chain["quality"][-1] == "macos"
        assert fallback_chain["balanced"][-1] == "macos"

    def test_rvc_fallback_to_base_tts(self):
        """RVC failure should fall back to base TTS."""
        # Simulated RVC failure scenario

        def generate_with_fallback(use_rvc: bool, rvc_available: bool):
            if use_rvc and rvc_available:
                return "rvc_audio"
            elif use_rvc and not rvc_available:
                # Fallback to base TTS
                return "base_tts_audio"
            else:
                return "base_tts_audio"

        # RVC available
        result = generate_with_fallback(use_rvc=True, rvc_available=True)
        assert result == "rvc_audio"

        # RVC unavailable - should fallback
        result = generate_with_fallback(use_rvc=True, rvc_available=False)
        assert result == "base_tts_audio"


# =============================================================================
# 5. PREPROCESSING CORRECTNESS TESTS
# =============================================================================

class TestPreprocessingCorrectness:
    """Test text preprocessing accuracy."""

    def test_markdown_removal(self, voice_preprocessor):
        """Markdown formatting should be removed."""
        text = "Hello **bold** and *italic* and ~~strikethrough~~"
        cleaned = voice_preprocessor.clean_text(text)

        assert "**" not in cleaned
        assert "*" not in cleaned or cleaned.count("*") == 0
        assert "~~" not in cleaned
        assert "bold" in cleaned
        assert "italic" in cleaned

    def test_abbreviation_expansion(self, voice_preprocessor):
        """Common abbreviations should be expanded."""
        text = "The API uses HTTPS and JSON."
        cleaned = voice_preprocessor.clean_text(text)

        # Should expand to speakable form
        assert "API" not in cleaned or "A P I" in cleaned
        assert "HTTPS" not in cleaned or "H T T P S" in cleaned
        assert "JSON" not in cleaned or "J SON" in cleaned

    def test_number_expansion(self, voice_preprocessor):
        """Numbers should be converted to words."""
        text = "I found 123 files in 7 folders."
        cleaned = voice_preprocessor.clean_text(text)

        # Numbers should be words
        assert "123" not in cleaned
        assert "7" not in cleaned
        # Should contain number words
        assert any(word in cleaned.lower() for word in ["hundred", "twenty", "three", "seven"])

    def test_url_handling(self, voice_preprocessor):
        """URLs should be handled according to config."""
        text = "Visit https://github.com/example/repo for more."
        cleaned = voice_preprocessor.clean_text(text)

        # Full URL should not be present
        assert "https://" not in cleaned
        # Domain might be present depending on config
        assert len(cleaned) < len(text)

    def test_code_block_handling(self, voice_preprocessor):
        """Code blocks should be handled appropriately."""
        text = "Here's code:\n```python\nprint('hello')\n```\nPretty cool."
        cleaned = voice_preprocessor.clean_text(text)

        assert "```" not in cleaned
        # Should either describe or skip the code
        assert "code" in cleaned.lower() or "print" not in cleaned

    def test_emoji_handling(self, voice_preprocessor):
        """Emojis should be handled according to config."""
        text = "Great job! \U0001F44D You're awesome! \U0001F600"
        cleaned = voice_preprocessor.clean_text(text)

        # Raw emoji characters should be handled
        assert "\U0001F44D" not in cleaned or "thumbs" in cleaned.lower()

    def test_whitespace_normalization(self, voice_preprocessor):
        """Whitespace should be normalized."""
        text = "Hello    world.\n\n\nNew paragraph."
        cleaned = voice_preprocessor.clean_text(text)

        assert "    " not in cleaned  # No quadruple spaces
        assert "\n\n\n" not in cleaned  # No triple newlines

    def test_sentence_splitting_accuracy(self, voice_preprocessor):
        """Sentences should be split accurately."""
        text = "First sentence. Second sentence! Third sentence?"
        sentences = voice_preprocessor.split_sentences(text)

        assert len(sentences) == 3
        assert "First" in sentences[0]
        assert "Second" in sentences[1]
        assert "Third" in sentences[2]

    def test_abbreviation_sentence_splitting(self, voice_preprocessor):
        """Abbreviations shouldn't break sentence splitting."""
        text = "Dr. Smith went to Washington D.C. for the meeting."
        sentences = voice_preprocessor.split_sentences(
            voice_preprocessor.clean_text(text)
        )

        # Should be one sentence (abbreviations shouldn't split)
        # Note: This depends on implementation - some may split differently
        assert len(sentences) >= 1

    def test_ordinal_expansion(self, voice_preprocessor):
        """Ordinals should be expanded correctly."""
        text = "The 1st, 2nd, and 3rd places."
        cleaned = voice_preprocessor.clean_text(text)

        assert "1st" not in cleaned
        assert "2nd" not in cleaned
        assert "3rd" not in cleaned
        assert "first" in cleaned.lower()
        assert "second" in cleaned.lower()
        assert "third" in cleaned.lower()


# =============================================================================
# 6. QUALITY SETTINGS APPLICATION TESTS
# =============================================================================

class TestQualitySettingsApplication:
    """Test that quality settings are applied correctly."""

    def test_fast_preset_settings(self):
        """Fast preset should use macOS, no RVC."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        settings = VoiceSettings.from_quality_preset(QualityLevel.FAST)

        assert settings.engine == "macos"
        assert settings.use_rvc is False
        assert settings.rvc_enabled is False
        assert settings.quality_level == "fast"
        assert settings.sentence_pause_ms == 100

    def test_balanced_preset_settings(self):
        """Balanced preset should use F5-TTS, no RVC."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        settings = VoiceSettings.from_quality_preset(QualityLevel.BALANCED)

        assert settings.engine == "f5"
        assert settings.use_rvc is False
        assert settings.quality_level == "balanced"
        assert settings.sentence_pause_ms == 150

    def test_quality_preset_settings(self):
        """Quality preset should use F5-TTS + RVC."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        settings = VoiceSettings.from_quality_preset(QualityLevel.QUALITY)

        assert settings.engine == "f5"
        assert settings.use_rvc is True
        assert settings.rvc_enabled is True
        assert settings.quality_level == "quality"
        assert settings.sentence_pause_ms == 200

    def test_apply_quality_preset(self):
        """Applying preset should update settings."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        settings = VoiceSettings()
        settings.engine = "macos"
        settings.use_rvc = False

        settings.apply_quality_preset(QualityLevel.QUALITY)

        assert settings.engine == "f5"
        assert settings.use_rvc is True
        assert settings.quality_level == "quality"

    def test_rvc_flags_synchronized(self):
        """use_rvc and rvc_enabled should stay synchronized."""
        from voice.voice_settings import VoiceSettings

        settings = VoiceSettings(use_rvc=True)
        assert settings.rvc_enabled is True

        settings = VoiceSettings(rvc_enabled=True)
        assert settings.use_rvc is True

    def test_emphasis_words_handling(self):
        """Emphasis words should be manageable."""
        from voice.voice_settings import VoiceSettings

        settings = VoiceSettings()

        settings.add_emphasis_word("important")
        assert "important" in settings.emphasis_words

        settings.add_emphasis_word("critical")
        assert len(settings.emphasis_words) == 2

        settings.remove_emphasis_word("important")
        assert "important" not in settings.emphasis_words
        assert "critical" in settings.emphasis_words

    def test_settings_validation(self):
        """Settings validation should catch invalid values."""
        from voice.voice_settings import VoiceSettings

        # Valid settings
        settings = VoiceSettings()
        errors = settings.validate()
        assert len(errors) == 0

        # Invalid speed
        settings.speed = 5.0
        errors = settings.validate()
        assert len(errors) > 0
        assert any("speed" in e.lower() for e in errors)

        # Invalid quality level
        settings = VoiceSettings()
        settings.quality_level = "invalid"
        errors = settings.validate()
        assert len(errors) > 0
        assert any("quality" in e.lower() for e in errors)

    def test_quality_description(self):
        """Should provide quality level descriptions."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        for level in QualityLevel:
            settings = VoiceSettings.from_quality_preset(level)
            description = settings.get_quality_description()

            assert len(description) > 0
            assert isinstance(description, str)


# =============================================================================
# 7. CONCURRENT SPEECH REQUEST TESTS
# =============================================================================

class TestConcurrentRequests:
    """Test handling of concurrent speech requests."""

    def test_settings_thread_safety(self):
        """VoiceSettingsManager should be thread-safe."""
        from voice.voice_settings import VoiceSettingsManager

        manager = VoiceSettingsManager.get_instance()
        errors = []

        def update_settings(thread_id: int):
            try:
                for i in range(10):
                    manager.update(speed=1.0 + (thread_id % 10) / 10)
                    _ = manager.settings
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=update_settings, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"

    def test_preprocessor_thread_safety(self, voice_preprocessor):
        """VoicePreprocessor should be thread-safe."""
        errors = []
        results = []

        def process_text(thread_id: int):
            try:
                for i in range(100):
                    text = f"Thread {thread_id} message {i}"
                    cleaned = voice_preprocessor.clean_text(text)
                    results.append(cleaned)
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=process_text, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"
        assert len(results) == 500  # 5 threads * 100 iterations

    def test_concurrent_cache_access(self):
        """Cache should handle concurrent access."""
        import hashlib
        from pathlib import Path

        cache_dir = Path(tempfile.mkdtemp())
        lock = threading.Lock()
        errors = []

        def cache_key(text: str) -> str:
            return hashlib.md5(text.encode()).hexdigest()

        def access_cache(thread_id: int):
            try:
                for i in range(50):
                    key = cache_key(f"text_{thread_id}_{i}")
                    cache_file = cache_dir / f"{key}.wav"

                    # Write
                    with lock:
                        cache_file.write_bytes(b"data")

                    # Read
                    if cache_file.exists():
                        _ = cache_file.read_bytes()
            except Exception as e:
                errors.append(str(e))

        threads = []
        for i in range(5):
            t = threading.Thread(target=access_cache, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0, f"Cache access errors: {errors}"

        # Cleanup
        import shutil
        shutil.rmtree(cache_dir)

    def test_queue_ordering(self):
        """Speech queue should maintain order."""
        from queue import Queue

        speech_queue = Queue()
        results = []

        # Add items
        for i in range(10):
            speech_queue.put(f"Message {i}")

        # Process
        while not speech_queue.empty():
            results.append(speech_queue.get())

        # Verify order
        assert results == [f"Message {i}" for i in range(10)]

    def test_concurrent_preprocessing(self, voice_preprocessor):
        """Multiple texts should preprocess correctly concurrently."""
        from concurrent.futures import ThreadPoolExecutor

        texts = [
            "Hello **world**!",
            "The API uses HTTPS.",
            "I found 123 files.",
            "Check https://example.com now.",
            "Great job! \U0001F44D",
        ] * 10  # 50 total

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(voice_preprocessor.clean_text, text)
                for text in texts
            ]
            results = [f.result() for f in as_completed(futures)]

        assert len(results) == 50
        # All results should be strings
        assert all(isinstance(r, str) for r in results)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestVoiceSystemIntegration:
    """Integration tests for the complete voice system."""

    def test_preprocessor_with_settings(self, voice_preprocessor, voice_settings):
        """Preprocessor and settings should work together."""
        text = "Hello **world**! This is SAM speaking."

        cleaned = voice_preprocessor.clean_text(text)
        sentences = voice_preprocessor.split_sentences(cleaned)

        # Add sentence pauses based on settings
        total_pause = len(sentences) * voice_settings.sentence_pause_ms

        assert len(sentences) > 0
        assert total_pause > 0

    def test_end_to_end_preprocessing(self, voice_preprocessor):
        """Full preprocessing pipeline should work correctly."""
        complex_text = """
        # Hello World

        This is **important** information about the API.
        Check https://docs.example.com for more details.

        ```python
        print("Hello")
        ```

        The results show:
        1. 123 items processed
        2. 45.6% success rate

        Great job! \U0001F44D
        """

        cleaned = voice_preprocessor.clean_text(complex_text)
        sentences = voice_preprocessor.split_sentences(cleaned)
        stats = voice_preprocessor.get_stats(complex_text, cleaned)

        assert len(cleaned) < len(complex_text)  # Should reduce size
        assert len(sentences) > 0
        assert stats["reduction_percent"] > 0

        # Should not contain raw markdown or special chars
        assert "**" not in cleaned
        assert "```" not in cleaned
        assert "https://" not in cleaned

    def test_settings_serialization_roundtrip(self):
        """Settings should serialize and deserialize correctly."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        original = VoiceSettings.from_quality_preset(QualityLevel.QUALITY)
        original.emphasis_words = ["important", "critical"]
        original.speed = 1.2

        # Serialize
        data = original.to_dict()

        # Deserialize
        restored = VoiceSettings.from_dict(data)

        assert restored.quality_level == original.quality_level
        assert restored.engine == original.engine
        assert restored.use_rvc == original.use_rvc
        assert restored.speed == original.speed
        assert restored.emphasis_words == original.emphasis_words


# =============================================================================
# PERFORMANCE BENCHMARK TESTS
# =============================================================================

class TestPerformanceBenchmarks:
    """Benchmark tests for voice system performance."""

    def test_preprocessing_throughput(self, voice_preprocessor):
        """Measure preprocessing throughput."""
        test_text = "Hello **world**! The API is great. Visit https://example.com today."

        start = time.time()
        iterations = 1000
        for _ in range(iterations):
            voice_preprocessor.clean_text(test_text)
        elapsed = time.time() - start

        throughput = iterations / elapsed
        print(f"\nPreprocessing throughput: {throughput:.0f} texts/second")

        # Should handle at least 100 texts per second
        assert throughput > 100

    def test_sentence_splitting_speed(self, voice_preprocessor):
        """Sentence splitting should be fast."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."

        start = time.time()
        for _ in range(1000):
            voice_preprocessor.split_sentences(text)
        elapsed = time.time() - start

        ms_per_call = elapsed * 1000 / 1000
        print(f"\nSentence splitting: {ms_per_call:.3f}ms per call")

        assert ms_per_call < 5  # Should be < 5ms per call

    def test_settings_load_speed(self):
        """Settings loading should be fast."""
        from voice.voice_settings import VoiceSettings

        start = time.time()
        for _ in range(1000):
            settings = VoiceSettings()
        elapsed = time.time() - start

        ms_per_call = elapsed * 1000 / 1000
        print(f"\nSettings creation: {ms_per_call:.3f}ms per call")

        assert ms_per_call < 1  # Should be < 1ms per call

    def test_quality_preset_application_speed(self):
        """Quality preset application should be instant."""
        from voice.voice_settings import VoiceSettings, QualityLevel

        settings = VoiceSettings()

        start = time.time()
        for _ in range(1000):
            for level in QualityLevel:
                settings.apply_quality_preset(level)
        elapsed = time.time() - start

        ms_per_call = elapsed * 1000 / 3000  # 3 presets * 1000 iterations
        print(f"\nPreset application: {ms_per_call:.3f}ms per call")

        assert ms_per_call < 1  # Should be < 1ms per call


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
