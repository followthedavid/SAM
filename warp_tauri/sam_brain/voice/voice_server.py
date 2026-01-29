#!/usr/bin/env python3
"""
SAM Voice Server - Text-to-Speech with Dustin Steele voice conversion

Provides an HTTP API for converting text to speech using SAM's personality
with Dustin Steele's voice (trained via RVC).

Usage:
    python voice_server.py [--port 8765]

API Endpoints:
    POST /api/speak - Convert text to speech
    GET /api/voices - List available voices
    GET /api/health - Health check
"""

import os
import sys
import json
import tempfile
import subprocess
import asyncio
from pathlib import Path
from typing import Optional
import hashlib
import time

# FastAPI imports
try:
    from fastapi import FastAPI, HTTPException, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "pydantic"], check=True)
    from fastapi import FastAPI, HTTPException, Response
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from pydantic import BaseModel
    import uvicorn

# =============================================================================
# CONFIGURATION
# =============================================================================

RVC_PROJECT_PATH = Path("/Users/davidquinton/Projects/RVC/rvc-webui")
DUSTIN_MODEL_PATH = RVC_PROJECT_PATH / "assets" / "weights" / "dustin_steele_final.pth"
DUSTIN_LOGS_PATH = RVC_PROJECT_PATH / "logs" / "dustin_steele"
CACHE_DIR = Path(__file__).parent / "voice_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Default TTS voice (macOS) - Fred works better with RVC than Daniel
DEFAULT_TTS_VOICE = "Fred"  # American male voice for base TTS

# =============================================================================
# API MODELS
# =============================================================================

class SpeakRequest(BaseModel):
    """Request to convert text to speech"""
    text: str
    voice: str = "dustin"  # "dustin" or "default"
    pitch_shift: int = 0  # Semitones to shift (-12 to 12)
    speed: float = 1.0  # Speech speed multiplier
    format: str = "wav"  # Output format: wav, mp3, aiff

class VoiceInfo(BaseModel):
    """Information about an available voice"""
    id: str
    name: str
    description: str
    available: bool

# =============================================================================
# VOICE SERVER
# =============================================================================

class VoiceServer:
    """SAM Voice Server with RVC voice conversion"""

    def __init__(self):
        self.rvc_available = self._check_rvc()
        self.cache_enabled = True
        self.max_cache_size = 100  # Max cached items

    def _check_rvc(self) -> bool:
        """Check if RVC is available and model exists"""
        if not RVC_PROJECT_PATH.exists():
            print(f"[WARN] RVC project not found at {RVC_PROJECT_PATH}")
            return False
        if not DUSTIN_MODEL_PATH.exists():
            print(f"[WARN] Dustin model not found at {DUSTIN_MODEL_PATH}")
            return False
        return True

    def _cache_key(self, text: str, voice: str, pitch: int, speed: float) -> str:
        """Generate cache key for request"""
        data = f"{text}:{voice}:{pitch}:{speed}"
        return hashlib.md5(data.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[bytes]:
        """Get cached audio if exists"""
        cache_file = CACHE_DIR / f"{key}.wav"
        if cache_file.exists():
            return cache_file.read_bytes()
        return None

    def _save_cache(self, key: str, audio: bytes):
        """Save audio to cache"""
        cache_file = CACHE_DIR / f"{key}.wav"
        cache_file.write_bytes(audio)

        # Cleanup old cache files if too many
        cache_files = sorted(CACHE_DIR.glob("*.wav"), key=lambda p: p.stat().st_mtime)
        while len(cache_files) > self.max_cache_size:
            oldest = cache_files.pop(0)
            oldest.unlink()

    async def generate_base_tts(self, text: str, speed: float = 1.0) -> Path:
        """Generate base TTS using macOS say command"""
        output_file = Path(tempfile.mktemp(suffix=".aiff"))

        # Calculate rate (words per minute, default ~175)
        rate = int(175 * speed)

        cmd = [
            "say",
            "-v", DEFAULT_TTS_VOICE,
            "-r", str(rate),
            "-o", str(output_file),
            text
        ]

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        if not output_file.exists():
            raise RuntimeError("TTS generation failed")

        # Convert to WAV for RVC
        wav_file = Path(tempfile.mktemp(suffix=".wav"))
        convert_cmd = [
            "ffmpeg", "-y", "-i", str(output_file),
            "-ar", "44100", "-ac", "1",
            str(wav_file)
        ]

        process = await asyncio.create_subprocess_exec(
            *convert_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        output_file.unlink()  # Cleanup AIFF

        return wav_file

    async def convert_voice_rvc(self, input_wav: Path, pitch_shift: int = 0) -> Path:
        """Convert voice using RVC"""
        if not self.rvc_available:
            return input_wav  # Return original if RVC unavailable

        output_wav = Path(tempfile.mktemp(suffix="_dustin.wav"))

        # Use RVC's own Python environment
        rvc_python = RVC_PROJECT_PATH / "venv" / "bin" / "python"
        if not rvc_python.exists():
            rvc_python = Path("/Volumes/Plex/DevSymlinks/venvs/RVC_venv/bin/python")

        # Use RVC CLI inference
        cmd = [
            str(rvc_python),
            str(RVC_PROJECT_PATH / "tools" / "infer_cli.py"),
            "--input_path", str(input_wav),
            "--opt_path", str(output_wav),
            "--model_name", "dustin_steele_final.pth",
            "--f0up_key", str(pitch_shift),
            "--f0method", "harvest",
            "--index_rate", "0.5",
            "--filter_radius", "3",
            "--rms_mix_rate", "0.4",
            "--protect", "0.45"
        ]

        # Run from RVC directory
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(RVC_PROJECT_PATH),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "PYTHONPATH": str(RVC_PROJECT_PATH)}
        )
        stdout, stderr = await process.communicate()

        print(f"[DEBUG] RVC process finished with return code: {process.returncode}")
        if stderr:
            print(f"[DEBUG] RVC stderr: {stderr.decode()[-500:]}")  # Last 500 chars

        if process.returncode != 0:
            print(f"[WARN] RVC conversion failed with code {process.returncode}")
            return input_wav  # Fallback to original

        if not output_wav.exists():
            print(f"[WARN] RVC output file not created: {output_wav}")
            return input_wav

        print(f"[INFO] RVC conversion successful: {output_wav} ({output_wav.stat().st_size} bytes)")
        input_wav.unlink()  # Cleanup original

        return output_wav

    async def speak(self, request: SpeakRequest) -> bytes:
        """Convert text to speech with optional voice conversion"""

        # Check cache
        if self.cache_enabled:
            cache_key = self._cache_key(
                request.text,
                request.voice,
                request.pitch_shift,
                request.speed
            )
            cached = self._get_cached(cache_key)
            if cached:
                return cached

        # Generate base TTS
        base_wav = await self.generate_base_tts(request.text, request.speed)

        # Apply voice conversion if requested
        print(f"[DEBUG] Voice requested: {request.voice}, RVC available: {self.rvc_available}")
        if request.voice == "dustin" and self.rvc_available:
            print(f"[INFO] Starting RVC conversion for: {base_wav}")
            output_wav = await self.convert_voice_rvc(base_wav, request.pitch_shift)
        else:
            print(f"[INFO] Using base TTS without RVC")
            output_wav = base_wav

        # Read output
        audio_data = output_wav.read_bytes()

        # Cleanup
        if output_wav.exists():
            output_wav.unlink()

        # Cache result
        if self.cache_enabled:
            self._save_cache(cache_key, audio_data)

        return audio_data

    def list_voices(self) -> list[VoiceInfo]:
        """List available voices"""
        return [
            VoiceInfo(
                id="dustin",
                name="Dustin Steele",
                description="SAM's voice converted to Dustin Steele via RVC",
                available=self.rvc_available
            ),
            VoiceInfo(
                id="default",
                name="Default (Alex)",
                description="macOS default male voice",
                available=True
            )
        ]

# =============================================================================
# FASTAPI APP
# =============================================================================

app = FastAPI(
    title="SAM Voice Server",
    description="Text-to-Speech API with Dustin Steele voice",
    version="1.0.0"
)

# CORS for iPhone/web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)

# Global server instance
voice_server: Optional[VoiceServer] = None

@app.get("/")
async def root():
    """Serve the web interface"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "SAM Voice Server", "docs": "/docs"}

@app.on_event("startup")
async def startup():
    global voice_server
    voice_server = VoiceServer()
    print(f"[INFO] Voice server started. RVC available: {voice_server.rvc_available}")

@app.get("/api/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "ok",
        "rvc_available": voice_server.rvc_available if voice_server else False,
        "timestamp": time.time()
    }

@app.get("/api/voices")
async def list_voices():
    """List available voices"""
    if not voice_server:
        raise HTTPException(status_code=503, detail="Server not initialized")
    return [v.dict() for v in voice_server.list_voices()]

@app.post("/api/speak")
async def speak(request: SpeakRequest):
    """Convert text to speech"""
    if not voice_server:
        raise HTTPException(status_code=503, detail="Server not initialized")

    if not request.text or len(request.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text cannot be empty")

    if len(request.text) > 5000:
        raise HTTPException(status_code=400, detail="Text too long (max 5000 chars)")

    try:
        audio_data = await voice_server.speak(request)
        return Response(
            content=audio_data,
            media_type="audio/wav",
            headers={
                "Content-Disposition": 'attachment; filename="speech.wav"',
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/speak/stream")
async def speak_stream(request: SpeakRequest):
    """Stream audio (for longer texts) - placeholder for future"""
    # For now, just call regular speak
    return await speak(request)

# =============================================================================
# MAIN
# =============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="SAM Voice Server")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--https", action="store_true", help="Enable HTTPS")
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    cert_file = script_dir / "voice_cert.pem"
    key_file = script_dir / "voice_key.pem"

    protocol = "https" if args.https and cert_file.exists() else "http"

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║                    SAM VOICE SERVER                          ║
║                                                              ║
║  Endpoints:                                                  ║
║    POST /api/speak     - Text to speech                      ║
║    GET  /api/voices    - List available voices               ║
║    GET  /api/health    - Health check                        ║
║                                                              ║
║  iPhone Usage ({protocol.upper()}):                                       ║
║    {protocol}://192.168.132.63:{args.port}/api/speak                 ║
║                                                              ║
║  Note: For iOS, trust the certificate in Settings >          ║
║        General > About > Certificate Trust Settings          ║
╚══════════════════════════════════════════════════════════════╝
    """)

    if args.https and cert_file.exists() and key_file.exists():
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            ssl_certfile=str(cert_file),
            ssl_keyfile=str(key_file)
        )
    else:
        uvicorn.run(app, host=args.host, port=args.port)

if __name__ == "__main__":
    main()
