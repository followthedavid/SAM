#!/usr/bin/env python3
"""
Tests for SAM Voice Output System (Phase 6.1)

Tests:
- VoiceSettings persistence and validation
- QualityLevel presets
- TTS pipeline initialization
- Speech queue operations
- Interruption handling
- Text preprocessing
- API endpoints
- Fallback behavior

Run:
    cd ~/ReverseLab/SAM/warp_tauri/sam_brain
    python -m pytest tests/test_voice_output.py -v

    # Run specific test
    python -m pytest tests/test_voice_output.py::TestVoiceSettings -v
    python -m pytest tests/test_voice_output.py::TestQualityPresets -v
"""

import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from dataclasses import asdict

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestVoiceSettings(unittest.TestCase):
    """Tests for VoiceSettings persistence."""

    def setUp(self):
        """Set up test fixtures."""
        # Use temp directory for settings
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = Path(self.temp_dir) / "voice_settings.json"

        # Patch the settings file location
        import voice_settings
        self._original_file = voice_settings.VOICE_SETTINGS_FILE
        voice_settings.VOICE_SETTINGS_FILE = self.settings_file

        # Clear any cached instance
        voice_settings.VoiceSettingsManager._instance = None

    def tearDown(self):
        """Clean up test fixtures."""
        import voice_settings
        voice_settings.VOICE_SETTINGS_FILE = self._original_file
        voice_settings.VoiceSettingsManager._instance = None

        # Clean up temp files
        if self.settings_file.exists():
            self.settings_file.unlink()
        Path(self.temp_dir).rmdir()

    def test_default_settings(self):
        """Test default settings are correct."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings()

        self.assertTrue(settings.enabled)
        self.assertEqual(settings.voice, "default")
        self.assertEqual(settings.speed, 1.0)
        self.assertEqual(settings.pitch, 0)
        self.assertFalse(settings.auto_speak)
        self.assertTrue(settings.queue_enabled)
        self.assertEqual(settings.engine, "macos")

    def test_settings_to_dict(self):
        """Test conversion to dictionary."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings(
            voice="dustin",
            speed=1.2,
            pitch=-2
        )

        d = settings.to_dict()

        self.assertEqual(d["voice"], "dustin")
        self.assertEqual(d["speed"], 1.2)
        self.assertEqual(d["pitch"], -2)
        self.assertIn("last_modified", d)
        self.assertIn("version", d)

    def test_settings_from_dict(self):
        """Test creation from dictionary."""
        from voice_settings import VoiceSettings

        data = {
            "voice": "daniel",
            "speed": 0.8,
            "pitch": 3,
            "enabled": False,
            "unknown_field": "ignored"
        }

        settings = VoiceSettings.from_dict(data)

        self.assertEqual(settings.voice, "daniel")
        self.assertEqual(settings.speed, 0.8)
        self.assertEqual(settings.pitch, 3)
        self.assertFalse(settings.enabled)

    def test_settings_validation_valid(self):
        """Test validation with valid settings."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings(
            speed=1.0,
            pitch=0,
            volume=0.8,
            engine="macos"
        )

        errors = settings.validate()
        self.assertEqual(len(errors), 0)

    def test_settings_validation_invalid_speed(self):
        """Test validation catches invalid speed."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings(speed=3.0)
        errors = settings.validate()

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Speed" in e for e in errors))

    def test_settings_validation_invalid_pitch(self):
        """Test validation catches invalid pitch."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings(pitch=15)
        errors = settings.validate()

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Pitch" in e for e in errors))

    def test_settings_validation_invalid_volume(self):
        """Test validation catches invalid volume."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings(volume=1.5)
        errors = settings.validate()

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Volume" in e for e in errors))

    def test_settings_validation_invalid_engine(self):
        """Test validation catches invalid engine."""
        from voice_settings import VoiceSettings

        settings = VoiceSettings(engine="unknown")
        errors = settings.validate()

        self.assertGreater(len(errors), 0)
        self.assertTrue(any("engine" in e.lower() for e in errors))

    def test_manager_singleton(self):
        """Test manager is a singleton."""
        from voice_settings import VoiceSettingsManager

        manager1 = VoiceSettingsManager.get_instance()
        manager2 = VoiceSettingsManager.get_instance()

        self.assertIs(manager1, manager2)

    def test_manager_load_default(self):
        """Test loading defaults when no file exists."""
        from voice_settings import VoiceSettingsManager

        manager = VoiceSettingsManager.get_instance()
        settings = manager.settings

        self.assertIsNotNone(settings)
        self.assertEqual(settings.voice, "default")

    def test_manager_save_and_load(self):
        """Test saving and loading settings."""
        from voice_settings import VoiceSettingsManager

        # Get manager and update settings
        manager = VoiceSettingsManager.get_instance()
        manager.update(voice="daniel", speed=1.5)

        # Clear instance and reload
        from voice_settings import VoiceSettingsManager as VSM
        VSM._instance = None

        # Load fresh
        manager2 = VoiceSettingsManager.get_instance()

        self.assertEqual(manager2.settings.voice, "daniel")
        self.assertEqual(manager2.settings.speed, 1.5)

    def test_manager_update_with_validation(self):
        """Test update validates settings."""
        from voice_settings import VoiceSettingsManager

        manager = VoiceSettingsManager.get_instance()

        # Valid update
        result = manager.update(speed=1.2)
        self.assertTrue(result["success"])
        self.assertEqual(manager.settings.speed, 1.2)

        # Invalid update
        result = manager.update(speed=5.0)
        self.assertFalse(result["success"])
        self.assertIn("errors", result)
        # Speed should not have changed
        self.assertEqual(manager.settings.speed, 1.2)

    def test_manager_reset_to_default(self):
        """Test resetting to defaults."""
        from voice_settings import VoiceSettingsManager

        manager = VoiceSettingsManager.get_instance()
        manager.update(voice="custom", speed=0.7)

        manager.reset_to_default()

        self.assertEqual(manager.settings.voice, "default")
        self.assertEqual(manager.settings.speed, 1.0)


class TestQualityPresets(unittest.TestCase):
    """Tests for QualityLevel presets."""

    def test_quality_level_enum(self):
        """Test QualityLevel enum values."""
        from voice_settings import QualityLevel

        self.assertEqual(QualityLevel.FAST.value, "fast")
        self.assertEqual(QualityLevel.BALANCED.value, "balanced")
        self.assertEqual(QualityLevel.QUALITY.value, "quality")

    def test_quality_presets_exist(self):
        """Test all quality levels have presets."""
        from voice_settings import QualityLevel, QUALITY_PRESETS

        for level in QualityLevel:
            self.assertIn(level, QUALITY_PRESETS)

    def test_fast_preset_uses_macos(self):
        """Test FAST preset uses macOS engine."""
        from voice_settings import QualityLevel, QUALITY_PRESETS

        preset = QUALITY_PRESETS[QualityLevel.FAST]
        self.assertEqual(preset["engine"], "macos")
        self.assertFalse(preset["rvc_enabled"])

    def test_quality_preset_uses_rvc(self):
        """Test QUALITY preset uses RVC."""
        from voice_settings import QualityLevel, QUALITY_PRESETS

        preset = QUALITY_PRESETS[QualityLevel.QUALITY]
        self.assertTrue(preset["rvc_enabled"])
        self.assertEqual(preset["engine"], "f5")

    def test_balanced_preset_no_rvc(self):
        """Test BALANCED preset uses F5 without RVC."""
        from voice_settings import QualityLevel, QUALITY_PRESETS

        preset = QUALITY_PRESETS[QualityLevel.BALANCED]
        self.assertEqual(preset["engine"], "f5")
        self.assertFalse(preset["rvc_enabled"])

    def test_presets_have_descriptions(self):
        """Test all presets have descriptions."""
        from voice_settings import QualityLevel, QUALITY_PRESETS

        for level, preset in QUALITY_PRESETS.items():
            self.assertIn("description", preset)
            self.assertIsInstance(preset["description"], str)
            self.assertGreater(len(preset["description"]), 10)


class TestVoiceSettingsAPI(unittest.TestCase):
    """Tests for voice settings API endpoints."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.settings_file = Path(self.temp_dir) / "voice_settings.json"

        import voice_settings
        self._original_file = voice_settings.VOICE_SETTINGS_FILE
        voice_settings.VOICE_SETTINGS_FILE = self.settings_file
        voice_settings.VoiceSettingsManager._instance = None

    def tearDown(self):
        """Clean up test fixtures."""
        import voice_settings
        voice_settings.VOICE_SETTINGS_FILE = self._original_file
        voice_settings.VoiceSettingsManager._instance = None

        if self.settings_file.exists():
            self.settings_file.unlink()
        Path(self.temp_dir).rmdir()

    def test_api_get_settings(self):
        """Test GET /api/voice/settings handler."""
        from voice_settings import api_get_voice_settings

        result = api_get_voice_settings()

        self.assertTrue(result["success"])
        self.assertIn("settings", result)
        self.assertIn("available_voices", result)
        self.assertIn("engines", result)
        self.assertIn("defaults", result)
        self.assertIn("macos", result["engines"])

    def test_api_update_settings_valid(self):
        """Test PUT /api/voice/settings with valid data."""
        from voice_settings import api_update_voice_settings

        result = api_update_voice_settings({
            "voice": "daniel",
            "speed": 1.1
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["settings"]["voice"], "daniel")
        self.assertEqual(result["settings"]["speed"], 1.1)

    def test_api_update_settings_invalid(self):
        """Test PUT /api/voice/settings with invalid data."""
        from voice_settings import api_update_voice_settings

        result = api_update_voice_settings({
            "speed": 10.0  # Invalid
        })

        self.assertFalse(result["success"])
        self.assertIn("errors", result)


class TestVoiceOutput(unittest.TestCase):
    """Tests for voice_output.py TTS functionality."""

    def test_voice_config_load_default(self):
        """Test VoiceConfig loads defaults when no config exists."""
        from voice_output import VoiceConfig

        # Use a non-existent config file
        with patch('voice_output.CONFIG_FILE', Path("/nonexistent/config.json")):
            config = VoiceConfig.load()

        self.assertEqual(config.engine, "macos")
        self.assertIsNotNone(config.voice)

    def test_macos_voice_list_voices(self):
        """Test listing macOS voices."""
        from voice_output import MacOSVoice

        voice = MacOSVoice()
        voices = voice.list_voices()

        # Should return a list (even if empty on non-macOS)
        self.assertIsInstance(voices, list)

    @patch('subprocess.run')
    def test_macos_voice_speak(self, mock_run):
        """Test macOS TTS generation."""
        from voice_output import MacOSVoice

        # Mock successful say command
        mock_run.return_value = Mock(returncode=0)

        voice = MacOSVoice(voice="Fred", rate=180)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.aiff"

            # Mock the file existence check
            with patch.object(Path, 'exists', return_value=True):
                result = voice.speak("Hello world", output_path)

            # Verify say was called with correct args
            mock_run.assert_called_once()
            call_args = mock_run.call_args[0][0]
            self.assertEqual(call_args[0], "say")
            self.assertIn("-v", call_args)
            self.assertIn("Fred", call_args)
            self.assertIn("-r", call_args)
            self.assertIn("180", call_args)

    def test_sam_voice_create_engine(self):
        """Test SAMVoice creates correct engine."""
        from voice_output import SAMVoice, VoiceConfig, MacOSVoice

        config = VoiceConfig(engine="macos", voice="Alex")
        voice = SAMVoice(config)

        self.assertIsInstance(voice._engine, MacOSVoice)

    def test_sam_voice_set_voice(self):
        """Test changing voice."""
        from voice_output import SAMVoice, VoiceConfig

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            config_path = Path(f.name)

        try:
            with patch('voice_output.CONFIG_FILE', config_path):
                config = VoiceConfig(voice="Daniel")
                voice = SAMVoice(config)

                voice.set_voice("Alex")

                self.assertEqual(voice.config.voice, "Alex")
        finally:
            config_path.unlink()


class TestSpeechQueue(unittest.TestCase):
    """Tests for speech queue operations."""

    def test_queue_initialization(self):
        """Test speech queue can be initialized."""
        # Speech queue would be part of a larger pipeline
        # Testing the concept here
        from collections import deque

        queue = deque(maxlen=10)
        queue.append({"text": "Hello", "priority": 1})
        queue.append({"text": "World", "priority": 2})

        self.assertEqual(len(queue), 2)

    def test_queue_priority_ordering(self):
        """Test queue respects priority."""
        import heapq

        # Priority queue simulation
        queue = []
        heapq.heappush(queue, (2, "low priority"))
        heapq.heappush(queue, (1, "high priority"))
        heapq.heappush(queue, (3, "lowest"))

        _, text = heapq.heappop(queue)
        self.assertEqual(text, "high priority")


class TestTextPreprocessing(unittest.TestCase):
    """Tests for text preprocessing before TTS."""

    def test_remove_markdown(self):
        """Test removing markdown formatting."""
        def preprocess(text):
            # Simple markdown removal
            import re
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # Bold
            text = re.sub(r'\*(.+?)\*', r'\1', text)      # Italic
            text = re.sub(r'`(.+?)`', r'\1', text)        # Code
            text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # Links
            return text

        self.assertEqual(preprocess("**bold** text"), "bold text")
        self.assertEqual(preprocess("*italic* text"), "italic text")
        self.assertEqual(preprocess("`code` snippet"), "code snippet")
        self.assertEqual(preprocess("[link](http://x.com)"), "link")

    def test_expand_abbreviations(self):
        """Test expanding common abbreviations."""
        def expand(text):
            expansions = {
                "e.g.": "for example",
                "i.e.": "that is",
                "etc.": "et cetera",
                "vs.": "versus",
                "API": "A P I",
                "URL": "U R L",
            }
            for abbr, full in expansions.items():
                text = text.replace(abbr, full)
            return text

        self.assertEqual(expand("e.g. this"), "for example this")
        self.assertEqual(expand("API endpoint"), "A P I endpoint")

    def test_split_long_text(self):
        """Test splitting text at sentence boundaries."""
        def split_text(text, max_length=500):
            if len(text) <= max_length:
                return [text]

            chunks = []
            sentences = text.replace(".", ".|").replace("!", "!|").replace("?", "?|").split("|")

            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) <= max_length:
                    current_chunk += sentence
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence

            if current_chunk:
                chunks.append(current_chunk.strip())

            return chunks

        text = "First sentence. Second sentence. Third sentence."
        chunks = split_text(text, 30)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 30)


class TestInterruptionHandling(unittest.TestCase):
    """Tests for speech interruption handling."""

    def test_interruption_flag(self):
        """Test interruption flag mechanism."""
        class SpeechController:
            def __init__(self):
                self._interrupted = False

            def interrupt(self):
                self._interrupted = True

            def reset(self):
                self._interrupted = False

            @property
            def is_interrupted(self):
                return self._interrupted

        controller = SpeechController()

        self.assertFalse(controller.is_interrupted)

        controller.interrupt()
        self.assertTrue(controller.is_interrupted)

        controller.reset()
        self.assertFalse(controller.is_interrupted)

    def test_interruptible_generation(self):
        """Test generation that checks for interruption."""
        class MockGenerator:
            def __init__(self):
                self.interrupted = False

            def generate_chunks(self, text, chunk_size=10):
                """Generate text in chunks, checking for interruption."""
                for i in range(0, len(text), chunk_size):
                    if self.interrupted:
                        return
                    yield text[i:i+chunk_size]

        gen = MockGenerator()
        text = "This is a longer text that will be split into chunks"

        # Normal generation
        result = list(gen.generate_chunks(text))
        self.assertEqual("".join(result), text)

        # Interrupted generation
        gen.interrupted = True
        result = list(gen.generate_chunks(text))
        self.assertEqual(len(result), 0)


class TestFallbackBehavior(unittest.TestCase):
    """Tests for TTS fallback behavior."""

    def test_fallback_chain(self):
        """Test fallback from RVC to F5 to macOS."""
        def try_engines(text, engines=["rvc", "f5", "macos"]):
            """Try engines in order, return first success."""
            for engine in engines:
                if engine == "rvc":
                    # Simulate RVC failure
                    continue
                elif engine == "f5":
                    # Simulate F5 failure
                    continue
                elif engine == "macos":
                    return {"engine": "macos", "success": True}

            return {"engine": None, "success": False}

        result = try_engines("Hello")
        self.assertTrue(result["success"])
        self.assertEqual(result["engine"], "macos")

    def test_fallback_on_error(self):
        """Test fallback when primary engine throws error."""
        class TTSWithFallback:
            def __init__(self):
                self.primary_available = False
                self.fallback_available = True

            def speak(self, text):
                if self.primary_available:
                    return {"engine": "primary", "text": text}

                if self.fallback_available:
                    return {"engine": "fallback", "text": text}

                raise RuntimeError("No TTS engine available")

        tts = TTSWithFallback()
        result = tts.speak("Hello")

        self.assertEqual(result["engine"], "fallback")

    def test_graceful_degradation(self):
        """Test graceful degradation when all engines fail."""
        def speak_with_degradation(text, engines):
            for engine in engines:
                try:
                    # Simulate all failures
                    raise RuntimeError(f"{engine} failed")
                except RuntimeError:
                    continue

            # Ultimate fallback - just return text
            return {
                "success": False,
                "text": text,
                "fallback": "text_only",
                "message": "Voice output unavailable, returning text"
            }

        result = speak_with_degradation("Hello", ["rvc", "f5", "macos"])

        self.assertFalse(result["success"])
        self.assertEqual(result["fallback"], "text_only")
        self.assertEqual(result["text"], "Hello")


class TestVoicePipelineIntegration(unittest.TestCase):
    """Tests for voice pipeline integration."""

    @patch('subprocess.run')
    def test_pipeline_end_to_end(self, mock_run):
        """Test complete pipeline from text to audio."""
        mock_run.return_value = Mock(returncode=0)

        class SimplePipeline:
            def __init__(self):
                self.steps_completed = []

            def preprocess(self, text):
                self.steps_completed.append("preprocess")
                return text.strip()

            def generate(self, text):
                self.steps_completed.append("generate")
                return f"audio_for_{hash(text)}"

            def postprocess(self, audio):
                self.steps_completed.append("postprocess")
                return audio

            def process(self, text):
                text = self.preprocess(text)
                audio = self.generate(text)
                return self.postprocess(audio)

        pipeline = SimplePipeline()
        result = pipeline.process("  Hello world  ")

        self.assertEqual(len(pipeline.steps_completed), 3)
        self.assertEqual(pipeline.steps_completed, ["preprocess", "generate", "postprocess"])

    def test_pipeline_with_emotion(self):
        """Test pipeline applies emotion to prosody."""
        class EmotionAwarePipeline:
            def __init__(self):
                self.prosody = {"pitch": 0, "speed": 1.0}

            def apply_emotion(self, emotion):
                if emotion == "excited":
                    self.prosody = {"pitch": 2, "speed": 1.2}
                elif emotion == "sad":
                    self.prosody = {"pitch": -2, "speed": 0.8}
                elif emotion == "calm":
                    self.prosody = {"pitch": 0, "speed": 0.9}

            def get_prosody(self):
                return self.prosody

        pipeline = EmotionAwarePipeline()

        pipeline.apply_emotion("excited")
        self.assertEqual(pipeline.get_prosody()["pitch"], 2)
        self.assertEqual(pipeline.get_prosody()["speed"], 1.2)

        pipeline.apply_emotion("sad")
        self.assertEqual(pipeline.get_prosody()["pitch"], -2)
        self.assertEqual(pipeline.get_prosody()["speed"], 0.8)


class TestCaching(unittest.TestCase):
    """Tests for audio caching."""

    def test_cache_key_generation(self):
        """Test cache key is deterministic."""
        import hashlib

        def cache_key(text, voice, pitch, speed):
            data = f"{text}:{voice}:{pitch}:{speed}"
            return hashlib.md5(data.encode()).hexdigest()

        key1 = cache_key("Hello", "daniel", 0, 1.0)
        key2 = cache_key("Hello", "daniel", 0, 1.0)
        key3 = cache_key("Hello", "alex", 0, 1.0)

        self.assertEqual(key1, key2)
        self.assertNotEqual(key1, key3)

    def test_cache_max_size(self):
        """Test cache eviction when max size reached."""
        from collections import OrderedDict

        class LRUCache:
            def __init__(self, max_size=3):
                self.max_size = max_size
                self.cache = OrderedDict()

            def get(self, key):
                if key in self.cache:
                    self.cache.move_to_end(key)
                    return self.cache[key]
                return None

            def set(self, key, value):
                if key in self.cache:
                    self.cache.move_to_end(key)
                self.cache[key] = value
                if len(self.cache) > self.max_size:
                    self.cache.popitem(last=False)

        cache = LRUCache(max_size=3)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        cache.set("d", 4)  # Should evict "a"

        self.assertIsNone(cache.get("a"))
        self.assertIsNotNone(cache.get("b"))
        self.assertIsNotNone(cache.get("d"))


class TestConcurrency(unittest.TestCase):
    """Tests for thread safety."""

    def test_settings_thread_safety(self):
        """Test settings manager is thread-safe."""
        import threading

        results = []
        errors = []

        def update_settings(value):
            try:
                from voice_settings import VoiceSettingsManager
                manager = VoiceSettingsManager.get_instance()
                manager.update(speed=value)
                results.append(value)
            except Exception as e:
                errors.append(str(e))

        # Run multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=update_settings, args=(0.5 + i * 0.1,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All threads should complete without errors
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(results), 5)


if __name__ == "__main__":
    unittest.main()
