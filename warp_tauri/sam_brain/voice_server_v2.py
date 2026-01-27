#!/usr/bin/env python3
"""
SAM Voice Server v2 - F5-TTS + RVC Pipeline

Cutting edge voice synthesis:
1. F5-TTS (MLX native) for natural base speech
2. RVC voice conversion to Dustin Steele

Usage:
    python voice_server_v2.py [--port 8765]
"""

import os
import sys
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
import hashlib
import time
import tempfile

# FastAPI imports
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

# =============================================================================
# CONFIGURATION
# =============================================================================

RVC_PROJECT_PATH = Path("/Users/davidquinton/Projects/RVC/rvc-webui")
RVC_PYTHON = Path("/Volumes/Plex/DevSymlinks/venvs/RVC_venv/bin/python")
DUSTIN_MODEL = "dustin_steele_final.pth"

SAM_BRAIN_PATH = Path(__file__).parent
SAM_VENV_PYTHON = SAM_BRAIN_PATH / ".venv" / "bin" / "python"

CACHE_DIR = SAM_BRAIN_PATH / "voice_cache_v2"
CACHE_DIR.mkdir(exist_ok=True)

STATIC_DIR = SAM_BRAIN_PATH / "static"

# =============================================================================
# API MODELS
# =============================================================================

class SpeakRequest(BaseModel):
    text: str
    voice: str = "dustin"  # "dustin" or "default"
    speed: float = 1.0

# =============================================================================
# VOICE ENGINE
# =============================================================================

class VoiceEngineV2:
    """F5-TTS + RVC Pipeline"""

    def __init__(self):
        self.f5_available = self._check_f5()
        self.rvc_available = self._check_rvc()
        self.cache_enabled = True
        self.max_cache = 50

    def _check_f5(self) -> bool:
        """Check if F5-TTS is available"""
        try:
            result = subprocess.run(
                [str(SAM_VENV_PYTHON), "-c", "import f5_tts_mlx; print('ok')"],
                capture_output=True, text=True, timeout=10
            )
            return "ok" in result.stdout
        except:
            return False

    def _check_rvc(self) -> bool:
        """Check if RVC is available"""
        return RVC_PROJECT_PATH.exists() and RVC_PYTHON.exists()

    def _cache_key(self, text: str, voice: str) -> str:
        return hashlib.md5(f"{text}:{voice}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[bytes]:
        cache_file = CACHE_DIR / f"{key}.wav"
        if cache_file.exists():
            return cache_file.read_bytes()
        return None

    def _save_cache(self, key: str, audio: bytes):
        cache_file = CACHE_DIR / f"{key}.wav"
        cache_file.write_bytes(audio)
        # Cleanup old
        files = sorted(CACHE_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        while len(files) > self.max_cache:
            files.pop(0).unlink()

    async def generate_f5_speech(self, text: str) -> Path:
        """Generate natural speech with F5-TTS (MLX native)"""
        output_file = Path(tempfile.mktemp(suffix="_f5.wav"))

        cmd = [
            str(SAM_VENV_PYTHON), "-m", "f5_tts_mlx.generate",
            "--text", text,
            "--output", str(output_file),
            "--q", "4"  # 4-bit quantization for 8GB RAM
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(SAM_BRAIN_PATH)
        )
        stdout, stderr = await process.communicate()

        if not output_file.exists():
            print(f"[WARN] F5-TTS failed: {stderr.decode()[-500:]}")
            raise RuntimeError("F5-TTS generation failed")

        print(f"[INFO] F5-TTS generated: {output_file}")
        return output_file

    async def convert_to_dustin(self, input_wav: Path) -> Path:
        """Convert voice to Dustin using RVC"""
        # Convert to 44.1kHz for RVC
        wav_44k = Path(tempfile.mktemp(suffix="_44k.wav"))
        convert_cmd = ["ffmpeg", "-y", "-i", str(input_wav), "-ar", "44100", "-ac", "1", str(wav_44k)]

        process = await asyncio.create_subprocess_exec(
            *convert_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # Run RVC
        output_wav = Path(tempfile.mktemp(suffix="_dustin.wav"))

        cmd = [
            str(RVC_PYTHON),
            str(RVC_PROJECT_PATH / "tools" / "infer_cli.py"),
            "--input_path", str(wav_44k),
            "--opt_path", str(output_wav),
            "--model_name", DUSTIN_MODEL,
            "--f0up_key", "0",
            "--f0method", "harvest",
            "--protect", "0.4",
            "--rms_mix_rate", "0.5"
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(RVC_PROJECT_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": str(RVC_PROJECT_PATH)}
        )
        stdout, stderr = await process.communicate()

        # Cleanup temp
        wav_44k.unlink(missing_ok=True)
        input_wav.unlink(missing_ok=True)

        if not output_wav.exists():
            print(f"[WARN] RVC failed: {stderr.decode()[-500:]}")
            raise RuntimeError("RVC conversion failed")

        print(f"[INFO] RVC converted: {output_wav}")
        return output_wav

    async def speak(self, request: SpeakRequest) -> bytes:
        """Generate speech with F5-TTS + optional RVC conversion"""

        # Check cache
        if self.cache_enabled:
            key = self._cache_key(request.text, request.voice)
            cached = self._get_cached(key)
            if cached:
                print(f"[INFO] Cache hit for: {request.text[:30]}...")
                return cached

        # Generate base speech with F5-TTS
        print(f"[INFO] Generating F5-TTS for: {request.text[:50]}...")
        base_wav = await self.generate_f5_speech(request.text)

        # Apply Dustin voice conversion if requested
        if request.voice == "dustin" and self.rvc_available:
            print(f"[INFO] Converting to Dustin voice...")
            output_wav = await self.convert_to_dustin(base_wav)
        else:
            output_wav = base_wav

        # Read and cleanup
        audio_data = output_wav.read_bytes()
        output_wav.unlink(missing_ok=True)

        # Cache
        if self.cache_enabled:
            self._save_cache(key, audio_data)

        return audio_data

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="SAM Voice Server v2",
    description="F5-TTS + RVC Pipeline",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine: Optional[VoiceEngineV2] = None

@app.on_event("startup")
async def startup():
    global engine
    engine = VoiceEngineV2()
    print(f"[INFO] Voice Engine v2 started")
    print(f"[INFO] F5-TTS available: {engine.f5_available}")
    print(f"[INFO] RVC available: {engine.rvc_available}")

@app.get("/")
async def root():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "SAM Voice Server v2", "docs": "/docs"}

@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "version": "2.0",
        "f5_available": engine.f5_available if engine else False,
        "rvc_available": engine.rvc_available if engine else False,
        "pipeline": "F5-TTS (MLX) + RVC",
        "timestamp": time.time()
    }

@app.get("/api/voices")
async def list_voices():
    return [
        {"id": "dustin", "name": "Dustin Steele", "description": "F5-TTS + RVC trained voice", "available": engine.rvc_available if engine else False},
        {"id": "default", "name": "F5-TTS Default", "description": "Natural F5-TTS voice", "available": engine.f5_available if engine else False}
    ]

@app.post("/api/speak")
async def speak(request: SpeakRequest):
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not initialized")

    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(request.text) > 500:
        raise HTTPException(status_code=400, detail="Text too long (max 500 chars for v2)")

    try:
        audio_data = await engine.speak(request)
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="speech.wav"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "X-Pipeline": "F5-TTS-MLX + RVC"
            }
        )
    except Exception as e:
        print(f"[ERROR] {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SAM Voice Server v2")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║              SAM VOICE SERVER v2                              ║
║                                                               ║
║  Pipeline: F5-TTS (MLX Native) → RVC (Dustin)                 ║
║                                                               ║
║  Endpoints:                                                   ║
║    POST /api/speak     - Generate speech                      ║
║    GET  /api/voices    - List voices                          ║
║    GET  /api/health    - Health check                         ║
║                                                               ║
║  URL: https://voice.f4ggot.org                                ║
╚═══════════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
