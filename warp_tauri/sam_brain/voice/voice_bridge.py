#!/usr/bin/env python3
"""
SAM Voice Bridge - Connect to RVC voice cloning for voice responses.

Integrates SAM with:
- RVC (Retrieval-based Voice Conversion) for voice cloning
- Text-to-Speech for response audio
- Voice input processing (future)

Enables SAM to respond in cloned voices.
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

# Paths
RVC_PROJECT = Path.home() / "Projects" / "RVC" / "rvc-webui"
RVC_WEIGHTS = RVC_PROJECT / "weights"
RVC_LOGS = RVC_PROJECT / "logs"
SAM_VOICE_TRAINING = Path("/Volumes/David External/SAM_Voice_Training")

SCRIPT_DIR = Path(__file__).parent
VOICE_CONFIG_FILE = SCRIPT_DIR / "voice_config.json"
AUDIO_OUTPUT_DIR = SCRIPT_DIR / "audio_output"


class VoiceConfig:
    def __init__(self):
        self.config = self._load()
        AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)

    def _load(self) -> Dict:
        """Load voice configuration."""
        if VOICE_CONFIG_FILE.exists():
            return json.load(open(VOICE_CONFIG_FILE))
        return {
            "enabled": False,
            "default_voice": None,
            "tts_engine": "say",  # macOS say, or edge-tts, pyttsx3
            "rvc_enabled": False,
            "voices": {}
        }

    def _save(self):
        """Save voice configuration."""
        json.dump(self.config, open(VOICE_CONFIG_FILE, "w"), indent=2)

    def enable(self):
        """Enable voice output."""
        self.config["enabled"] = True
        self._save()

    def disable(self):
        """Disable voice output."""
        self.config["enabled"] = False
        self._save()

    def set_default_voice(self, voice_name: str):
        """Set default voice for responses."""
        self.config["default_voice"] = voice_name
        self._save()

    def add_voice(self, name: str, model_path: str, index_path: str = None):
        """Add a voice model."""
        self.config["voices"][name] = {
            "model_path": model_path,
            "index_path": index_path,
            "added_at": datetime.now().isoformat()
        }
        self._save()


class VoiceBridge:
    def __init__(self):
        self.config = VoiceConfig()
        self.rvc_available = self._check_rvc()

    def _check_rvc(self) -> bool:
        """Check if RVC is available."""
        return RVC_PROJECT.exists() and RVC_WEIGHTS.exists()

    def list_available_voices(self) -> List[Dict]:
        """List available RVC voice models."""
        voices = []

        # Check RVC weights folder
        if RVC_WEIGHTS.exists():
            for pth_file in RVC_WEIGHTS.glob("*.pth"):
                name = pth_file.stem
                index_file = RVC_WEIGHTS / f"{name}.index"
                voices.append({
                    "name": name,
                    "model_path": str(pth_file),
                    "index_path": str(index_file) if index_file.exists() else None,
                    "source": "rvc_weights"
                })

        # Check RVC logs folder for training models
        if RVC_LOGS.exists():
            for model_dir in RVC_LOGS.iterdir():
                if model_dir.is_dir():
                    # Look for latest checkpoint
                    checkpoints = list(model_dir.glob("G_*.pth"))
                    if checkpoints:
                        latest = max(checkpoints, key=lambda p: p.stat().st_mtime)
                        voices.append({
                            "name": model_dir.name,
                            "model_path": str(latest),
                            "index_path": None,
                            "source": "rvc_training"
                        })

        return voices

    def list_training_data(self) -> List[Dict]:
        """List available voice training data."""
        data = []

        if SAM_VOICE_TRAINING.exists():
            for audio_file in SAM_VOICE_TRAINING.glob("*.mp4"):
                data.append({
                    "name": audio_file.stem,
                    "path": str(audio_file),
                    "size_mb": audio_file.stat().st_size / (1024 * 1024)
                })

        return data

    def text_to_speech(self, text: str, output_path: Path = None) -> Optional[Path]:
        """Convert text to speech using macOS say command."""
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = AUDIO_OUTPUT_DIR / f"tts_{timestamp}.aiff"

        try:
            # Use macOS say command
            subprocess.run(
                ["say", "-o", str(output_path), text],
                check=True,
                capture_output=True
            )
            return output_path
        except subprocess.CalledProcessError as e:
            print(f"TTS failed: {e}")
            return None

    def convert_voice(self, audio_path: Path, voice_name: str, output_path: Path = None) -> Optional[Path]:
        """Convert audio to target voice using RVC."""
        if not self.rvc_available:
            print("RVC not available")
            return None

        voices = {v["name"]: v for v in self.list_available_voices()}
        if voice_name not in voices:
            print(f"Voice not found: {voice_name}")
            return None

        voice = voices[voice_name]

        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = AUDIO_OUTPUT_DIR / f"rvc_{voice_name}_{timestamp}.wav"

        # RVC inference command
        # This is a simplified version - actual RVC has more options
        cmd = [
            "python3", str(RVC_PROJECT / "infer_cli.py"),
            "--model", voice["model_path"],
            "--input", str(audio_path),
            "--output", str(output_path),
        ]

        if voice.get("index_path"):
            cmd.extend(["--index", voice["index_path"]])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                return output_path
            else:
                print(f"RVC failed: {result.stderr}")
                return None
        except Exception as e:
            print(f"RVC error: {e}")
            return None

    def speak(self, text: str, voice_name: str = None) -> Optional[Path]:
        """Speak text, optionally with voice conversion."""
        if not self.config.config["enabled"]:
            print(text)  # Just print if voice disabled
            return None

        # Generate TTS
        tts_path = self.text_to_speech(text)
        if not tts_path:
            return None

        # Apply voice conversion if requested
        if voice_name or self.config.config["default_voice"]:
            target_voice = voice_name or self.config.config["default_voice"]
            converted = self.convert_voice(tts_path, target_voice)
            if converted:
                # Play converted audio
                subprocess.run(["afplay", str(converted)])
                return converted

        # Play original TTS
        subprocess.run(["afplay", str(tts_path)])
        return tts_path

    def play_audio(self, path: Path):
        """Play an audio file."""
        subprocess.run(["afplay", str(path)])

    def status(self) -> Dict:
        """Get voice bridge status."""
        return {
            "enabled": self.config.config["enabled"],
            "rvc_available": self.rvc_available,
            "default_voice": self.config.config["default_voice"],
            "available_voices": len(self.list_available_voices()),
            "training_data_files": len(self.list_training_data()),
            "rvc_project": str(RVC_PROJECT),
            "training_data_path": str(SAM_VOICE_TRAINING)
        }


# Global instance
_bridge = None


def get_bridge() -> VoiceBridge:
    """Get global voice bridge instance."""
    global _bridge
    if _bridge is None:
        _bridge = VoiceBridge()
    return _bridge


def speak(text: str, voice: str = None) -> Optional[Path]:
    """Speak text."""
    return get_bridge().speak(text, voice)


def list_voices() -> List[Dict]:
    """List available voices."""
    return get_bridge().list_available_voices()


if __name__ == "__main__":
    import sys

    bridge = VoiceBridge()

    if len(sys.argv) < 2:
        print("SAM Voice Bridge")
        print("-" * 40)
        status = bridge.status()
        for k, v in status.items():
            print(f"  {k}: {v}")
        print("\nCommands: voices, training, speak <text>, enable, disable, test")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "voices":
        voices = bridge.list_available_voices()
        print(f"Available voices ({len(voices)}):")
        for v in voices:
            print(f"  {v['name']}: {v['source']}")

    elif cmd == "training":
        data = bridge.list_training_data()
        print(f"Training data ({len(data)}):")
        for d in data[:10]:
            print(f"  {d['name']}: {d['size_mb']:.1f} MB")

    elif cmd == "speak":
        text = " ".join(sys.argv[2:])
        bridge.speak(text)

    elif cmd == "enable":
        bridge.config.enable()
        print("Voice output enabled")

    elif cmd == "disable":
        bridge.config.disable()
        print("Voice output disabled")

    elif cmd == "test":
        print("Testing TTS...")
        path = bridge.text_to_speech("Hello, I am SAM, your AI coding assistant.")
        if path:
            print(f"Generated: {path}")
            bridge.play_audio(path)

    elif cmd == "set-voice" and len(sys.argv) > 2:
        bridge.config.set_default_voice(sys.argv[2])
        print(f"Default voice set to: {sys.argv[2]}")

    else:
        print(f"Unknown command: {cmd}")
