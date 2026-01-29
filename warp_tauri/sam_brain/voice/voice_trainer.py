#!/usr/bin/env python3
"""
SAM Voice Training Module

Handles RVC voice cloning with automatic Docker management.
No UI needed - just tell SAM what you want.

Usage (via SAM):
  "Train a voice from my audio"
  "Clone this voice"
  "Create a voice model"

SAM will:
1. Guide you through providing audio
2. Start Docker automatically
3. Run training
4. Clean up when done
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Dict, Any

# Paths
RVC_DIR = Path.home() / "Projects/RVC/rvc-webui"
DATASETS_DIR = RVC_DIR / "datasets"
AUDIO_INPUT = Path.home() / "Desktop"  # Default place to look for audio


class VoiceTrainer:
    """Manages RVC voice training through SAM."""

    def __init__(self):
        self.status = "idle"
        self.current_model = None

    def get_status(self) -> Dict[str, Any]:
        """Get current training status."""
        docker_running = self._is_docker_running()
        rvc_running = self._is_rvc_running()

        return {
            "status": self.status,
            "docker_running": docker_running,
            "rvc_running": rvc_running,
            "current_model": self.current_model,
            "datasets_dir": str(DATASETS_DIR),
            "instructions": self._get_instructions()
        }

    def _get_instructions(self) -> str:
        """Context-aware instructions."""
        if self.status == "idle":
            return """To train a voice:
1. Put 10+ minutes of clean audio in ~/Desktop/ (wav/mp3)
2. Tell me the filename and what to name the voice
3. I'll handle Docker and training automatically"""

        elif self.status == "ready":
            return "Audio prepared. Say 'start training' to begin."

        elif self.status == "training":
            return f"Training {self.current_model}... Check http://localhost:7865"

        return "Voice trainer ready."

    def prepare_audio(self, audio_path: str, model_name: str) -> Dict[str, Any]:
        """Prepare audio for training."""
        audio = Path(audio_path).expanduser()

        # Check common locations
        if not audio.exists():
            for base in [AUDIO_INPUT, Path.home() / "Downloads", Path.home()]:
                candidate = base / audio_path
                if candidate.exists():
                    audio = candidate
                    break

        if not audio.exists():
            return {
                "success": False,
                "error": f"Audio not found: {audio_path}",
                "hint": "Put the audio file on Desktop or give full path"
            }

        # Create dataset directory
        dataset_dir = DATASETS_DIR / model_name
        dataset_dir.mkdir(parents=True, exist_ok=True)

        # Copy audio
        dest = dataset_dir / audio.name
        shutil.copy2(audio, dest)

        self.status = "ready"
        self.current_model = model_name

        return {
            "success": True,
            "message": f"Audio prepared for '{model_name}'",
            "audio_file": str(dest),
            "next_step": "Say 'start training' or I can start it now"
        }

    def start_training(self, use_docker: bool = False) -> Dict[str, Any]:
        """Start the training process.

        Args:
            use_docker: If True, use Docker. Default False uses native MPS (~336MB vs ~2GB).
        """
        if not self.current_model:
            return {
                "success": False,
                "error": "No audio prepared. First tell me the audio file and model name."
            }

        self.status = "training"

        # Choose script based on mode
        if use_docker:
            script = Path.home() / "ReverseLab/SAM/scripts/rvc_train.sh"
            mode = "Docker"
            cleanup_note = "Docker quits automatically, freeing RAM"
        else:
            script = Path.home() / "ReverseLab/SAM/scripts/rvc_native.sh"
            mode = "Native MPS"
            cleanup_note = "Uses ~336MB RAM (vs ~2GB with Docker)"

        try:
            # Start in new terminal
            subprocess.Popen([
                "osascript", "-e",
                f'tell app "Terminal" to do script "{script}"'
            ])

            return {
                "success": True,
                "message": f"Training started for '{self.current_model}' ({mode})",
                "ui": "http://localhost:7865",
                "instructions": [
                    "1. Open http://localhost:7865 in browser",
                    f"2. Select dataset: {self.current_model}",
                    "3. Click 'Train' (takes ~1-6 hours)",
                    "4. When done, just close the Terminal",
                    f"5. {cleanup_note}"
                ],
                "note": "I'll remember this is running. Ask me 'voice training status' anytime."
            }
        except Exception as e:
            self.status = "error"
            return {
                "success": False,
                "error": str(e)
            }

    def stop_training(self) -> Dict[str, Any]:
        """Stop training and cleanup."""
        try:
            # Stop native RVC process
            subprocess.run(
                ["pkill", "-f", "infer-web.py"],
                capture_output=True
            )

            # Also try stopping Docker containers (if Docker mode was used)
            subprocess.run(
                ["docker-compose", "down"],
                cwd=RVC_DIR,
                capture_output=True
            )

            # Quit Docker if running
            subprocess.run([
                "osascript", "-e", 'quit app "Docker"'
            ], capture_output=True)

            self.status = "idle"
            self.current_model = None

            return {
                "success": True,
                "message": "Training stopped. RAM freed."
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _is_docker_running(self) -> bool:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True
        )
        return result.returncode == 0

    def _is_rvc_running(self) -> bool:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=rvc", "-q"],
            capture_output=True,
            text=True
        )
        return bool(result.stdout.strip())


# Singleton for SAM to use
_trainer = None

def get_trainer() -> VoiceTrainer:
    global _trainer
    if _trainer is None:
        _trainer = VoiceTrainer()
    return _trainer


# Quick functions for orchestrator
def voice_status() -> Dict[str, Any]:
    """Get voice training status."""
    return get_trainer().get_status()

def voice_prepare(audio_path: str, model_name: str) -> Dict[str, Any]:
    """Prepare audio for training."""
    return get_trainer().prepare_audio(audio_path, model_name)

def voice_start() -> Dict[str, Any]:
    """Start training."""
    return get_trainer().start_training()

def voice_stop() -> Dict[str, Any]:
    """Stop training and cleanup."""
    return get_trainer().stop_training()
