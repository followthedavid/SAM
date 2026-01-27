#!/usr/bin/env python3
"""
SAM Native Image Generation Module

Uses mflux (MLX-based Stable Diffusion) for native Apple Silicon image generation.
No Docker needed - runs directly on M2 with ~40% faster performance.

Usage (via SAM):
  "Generate an image of a sunset"
  "Draw a cat in space"
  "Create art of mountains"

SAM will:
1. Extract the prompt
2. Generate using mflux
3. Return the image path
"""

import subprocess
import os
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Output directory
OUTPUT_DIR = Path.home() / "Pictures" / "SAM_Generated"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ImageGenerator:
    """Manages native image generation through mflux."""

    def __init__(self):
        self.status = "idle"
        self.last_image = None
        self.model = "schnell"  # Fast model, good for 8GB RAM

    def get_status(self) -> Dict[str, Any]:
        """Get current generator status."""
        mflux_available = self._check_mflux()

        return {
            "status": self.status,
            "mflux_available": mflux_available,
            "model": self.model,
            "output_dir": str(OUTPUT_DIR),
            "last_image": str(self.last_image) if self.last_image else None,
            "instructions": self._get_instructions(mflux_available)
        }

    def _get_instructions(self, available: bool) -> str:
        if not available:
            return "mflux not installed. Run: pipx install mflux"
        return "Ready to generate images. Just describe what you want."

    def _check_mflux(self) -> bool:
        """Check if mflux is available."""
        try:
            result = subprocess.run(
                ["mflux-generate", "--help"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except:
            return False

    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Generate an image from a prompt.

        Args:
            prompt: Text description of the image
            **kwargs: Optional parameters:
                - width: Image width (default 512)
                - height: Image height (default 512)
                - steps: Inference steps (default 4 for schnell)
                - seed: Random seed (optional)
        """
        if not self._check_mflux():
            return {
                "success": False,
                "error": "mflux not available",
                "hint": "Run: pipx install mflux"
            }

        self.status = "generating"

        # Build output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_prompt = "".join(c if c.isalnum() or c == " " else "_" for c in prompt[:30])
        safe_prompt = safe_prompt.replace(" ", "_")
        output_path = OUTPUT_DIR / f"{timestamp}_{safe_prompt}.png"

        # Build command
        width = kwargs.get("width", 512)
        height = kwargs.get("height", 512)
        steps = kwargs.get("steps", 4)  # schnell is fast, 4 steps is good
        seed = kwargs.get("seed")

        cmd = [
            "mflux-generate",
            "--prompt", prompt,
            "--model", self.model,
            "--width", str(width),
            "--height", str(height),
            "--steps", str(steps),
            "--output", str(output_path),
            "--low-ram"  # Important for 8GB Mac Mini
        ]

        if seed:
            cmd.extend(["--seed", str(seed)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0 and output_path.exists():
                self.status = "idle"
                self.last_image = output_path

                return {
                    "success": True,
                    "image_path": str(output_path),
                    "prompt": prompt,
                    "model": self.model,
                    "dimensions": f"{width}x{height}",
                    "message": f"Image generated: {output_path.name}"
                }
            else:
                self.status = "error"
                return {
                    "success": False,
                    "error": result.stderr or "Generation failed",
                    "stdout": result.stdout
                }

        except subprocess.TimeoutExpired:
            self.status = "timeout"
            return {
                "success": False,
                "error": "Generation timed out (5 minute limit)"
            }
        except Exception as e:
            self.status = "error"
            return {
                "success": False,
                "error": str(e)
            }


# Singleton for SAM to use
_generator = None


def get_generator() -> ImageGenerator:
    global _generator
    if _generator is None:
        _generator = ImageGenerator()
    return _generator


# Quick functions for orchestrator
def image_status() -> Dict[str, Any]:
    """Get image generator status."""
    return get_generator().get_status()


def image_generate(prompt: str, **kwargs) -> Dict[str, Any]:
    """Generate an image from a prompt."""
    return get_generator().generate(prompt, **kwargs)
