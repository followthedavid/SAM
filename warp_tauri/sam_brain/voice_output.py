#!/usr/bin/env python3
"""
SAM Voice Output - Text-to-Speech integration.

Supports:
1. macOS built-in voices (instant, no setup)
2. Coqui TTS (more natural, needs install)
3. RVC voice cloning (custom voice, needs model)

Usage:
  python voice_output.py speak "Hello world"
  python voice_output.py speak "Hello" --voice daniel
  python voice_output.py speak "Hello" --output /tmp/hello.wav
  python voice_output.py list-voices
  python voice_output.py test
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

SCRIPT_DIR = Path(__file__).parent
VOICE_CACHE = SCRIPT_DIR / "voice_cache"
VOICE_CACHE.mkdir(exist_ok=True)

# Configuration
CONFIG_FILE = SCRIPT_DIR / "voice_config.json"
DEFAULT_CONFIG = {
    "engine": "macos",  # macos, coqui, rvc
    "voice": "Daniel",  # macOS voice name
    "rate": 180,        # Words per minute
    "save_audio": True, # Save audio files
    "play_audio": True, # Play audio immediately
    "rvc_model": None,  # Path to RVC model when using RVC
}


@dataclass
class VoiceConfig:
    engine: str = "macos"
    voice: str = "Daniel"
    rate: int = 180
    save_audio: bool = True
    play_audio: bool = True
    rvc_model: Optional[str] = None

    @classmethod
    def load(cls) -> "VoiceConfig":
        if CONFIG_FILE.exists():
            data = json.load(open(CONFIG_FILE))
            return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
        return cls()

    def save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.__dict__, f, indent=2)


class VoiceEngine:
    """Base voice engine interface."""

    def speak(self, text: str, output_path: Optional[Path] = None) -> Optional[Path]:
        raise NotImplementedError


class MacOSVoice(VoiceEngine):
    """macOS built-in TTS using 'say' command."""

    def __init__(self, voice: str = "Daniel", rate: int = 180):
        self.voice = voice
        self.rate = rate

    def list_voices(self) -> list[dict]:
        """List available macOS voices."""
        result = subprocess.run(
            ["say", "-v", "?"],
            capture_output=True,
            text=True
        )
        voices = []
        for line in result.stdout.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 2:
                name = parts[0]
                locale = parts[1]
                voices.append({"name": name, "locale": locale})
        return voices

    def speak(self, text: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """Generate speech from text."""
        if output_path is None:
            output_path = VOICE_CACHE / f"sam_{hash(text) % 100000}.aiff"

        cmd = [
            "say",
            "-v", self.voice,
            "-r", str(self.rate),
            "-o", str(output_path),
            text
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and output_path.exists():
            return output_path
        return None

    def play(self, audio_path: Path):
        """Play audio file."""
        subprocess.run(["afplay", str(audio_path)], capture_output=True)


class CoquiVoice(VoiceEngine):
    """Coqui TTS for more natural voices."""

    def __init__(self, model: str = "tts_models/en/ljspeech/tacotron2-DDC"):
        self.model = model
        self._tts = None

    def _get_tts(self):
        if self._tts is None:
            try:
                from TTS.api import TTS
                self._tts = TTS(model_name=self.model)
            except ImportError:
                raise RuntimeError("Coqui TTS not installed. Run: pip install TTS")
        return self._tts

    def speak(self, text: str, output_path: Optional[Path] = None) -> Optional[Path]:
        if output_path is None:
            output_path = VOICE_CACHE / f"sam_{hash(text) % 100000}.wav"

        tts = self._get_tts()
        tts.tts_to_file(text=text, file_path=str(output_path))

        if output_path.exists():
            return output_path
        return None

    def play(self, audio_path: Path):
        subprocess.run(["afplay", str(audio_path)], capture_output=True)


class RVCVoice(VoiceEngine):
    """RVC voice cloning - use a cloned voice."""

    def __init__(self, model_path: str, base_voice: VoiceEngine = None):
        self.model_path = Path(model_path)
        self.base_voice = base_voice or MacOSVoice()

    def speak(self, text: str, output_path: Optional[Path] = None) -> Optional[Path]:
        # First generate base audio
        base_audio = self.base_voice.speak(text)
        if not base_audio:
            return None

        if output_path is None:
            output_path = VOICE_CACHE / f"sam_rvc_{hash(text) % 100000}.wav"

        # TODO: Call RVC inference here
        # For now, just return the base audio
        # When RVC is ready, this will convert the voice
        import shutil
        shutil.copy(base_audio, output_path)

        return output_path

    def play(self, audio_path: Path):
        subprocess.run(["afplay", str(audio_path)], capture_output=True)


class SAMVoice:
    """Main SAM voice interface."""

    def __init__(self, config: Optional[VoiceConfig] = None):
        self.config = config or VoiceConfig.load()
        self._engine = self._create_engine()

    def _create_engine(self) -> VoiceEngine:
        if self.config.engine == "macos":
            return MacOSVoice(
                voice=self.config.voice,
                rate=self.config.rate
            )
        elif self.config.engine == "coqui":
            return CoquiVoice()
        elif self.config.engine == "rvc":
            if not self.config.rvc_model:
                raise ValueError("RVC model path not configured")
            return RVCVoice(self.config.rvc_model)
        else:
            raise ValueError(f"Unknown engine: {self.config.engine}")

    def speak(self, text: str, output_path: Optional[str] = None) -> dict:
        """Speak text and return result info."""
        out_path = Path(output_path) if output_path else None

        audio_path = self._engine.speak(text, out_path)

        result = {
            "success": audio_path is not None,
            "text": text,
            "engine": self.config.engine,
            "voice": self.config.voice,
        }

        if audio_path:
            result["audio_path"] = str(audio_path)
            result["audio_size"] = audio_path.stat().st_size

            if self.config.play_audio:
                self._engine.play(audio_path)
                result["played"] = True

        return result

    def list_voices(self) -> list[dict]:
        """List available voices for current engine."""
        if isinstance(self._engine, MacOSVoice):
            return self._engine.list_voices()
        return []

    def set_voice(self, voice: str):
        """Change voice."""
        self.config.voice = voice
        self.config.save()
        self._engine = self._create_engine()

    def set_engine(self, engine: str):
        """Change TTS engine."""
        self.config.engine = engine
        self.config.save()
        self._engine = self._create_engine()


# CLI
def main():
    import argparse

    parser = argparse.ArgumentParser(description="SAM Voice Output")
    subparsers = parser.add_subparsers(dest="command")

    # speak command
    speak_parser = subparsers.add_parser("speak", help="Speak text")
    speak_parser.add_argument("text", help="Text to speak")
    speak_parser.add_argument("--voice", "-v", help="Voice name")
    speak_parser.add_argument("--output", "-o", help="Output file path")
    speak_parser.add_argument("--no-play", action="store_true", help="Don't play audio")

    # list-voices command
    subparsers.add_parser("list-voices", help="List available voices")

    # test command
    subparsers.add_parser("test", help="Test voice output")

    # config command
    config_parser = subparsers.add_parser("config", help="Show/set config")
    config_parser.add_argument("--voice", help="Set voice")
    config_parser.add_argument("--engine", help="Set engine (macos, coqui, rvc)")
    config_parser.add_argument("--rate", type=int, help="Set speech rate")

    args = parser.parse_args()

    voice = SAMVoice()

    if args.command == "speak":
        if args.voice:
            voice.set_voice(args.voice)
        if args.no_play:
            voice.config.play_audio = False

        result = voice.speak(args.text, args.output)
        print(json.dumps(result, indent=2))

    elif args.command == "list-voices":
        voices = voice.list_voices()
        print(f"Available voices ({len(voices)}):")
        for v in voices:
            print(f"  {v['name']:20} ({v['locale']})")

    elif args.command == "test":
        print("Testing SAM voice output...")
        phrases = [
            "Hello, I am SAM, your intelligent assistant.",
            "I have analyzed 3,241 projects across 7 drives.",
            "The build completed successfully.",
            "I found 3 potential issues in your code.",
        ]
        for phrase in phrases:
            print(f"\nSpeaking: {phrase}")
            result = voice.speak(phrase)
            print(f"  Audio: {result.get('audio_path', 'failed')}")

    elif args.command == "config":
        if args.voice:
            voice.set_voice(args.voice)
            print(f"Voice set to: {args.voice}")
        if args.engine:
            voice.set_engine(args.engine)
            print(f"Engine set to: {args.engine}")
        if args.rate:
            voice.config.rate = args.rate
            voice.config.save()
            print(f"Rate set to: {args.rate}")

        if not any([args.voice, args.engine, args.rate]):
            print("Current config:")
            print(json.dumps(voice.config.__dict__, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
