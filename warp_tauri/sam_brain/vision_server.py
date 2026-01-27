#!/usr/bin/env python3
"""
SAM Vision Server - Persistent MLX Vision Model
Keeps nanoLLaVA loaded in memory for fast image processing.

Port: 8766 (one above main SAM API)
"""

import os
import sys
import json
import base64
import tempfile
import time
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("vision_server")

# Model configuration
MODEL_ID = "mlx-community/nanoLLaVA-1.5-bf16"
DEFAULT_PORT = 8766

# Global model state
model = None
processor = None
model_lock = Lock()
load_time = None

def load_vision_model():
    """Check that vision CLI is available."""
    global load_time

    logger.info(f"Checking vision CLI availability...")
    start = time.time()

    try:
        import subprocess
        result = subprocess.run(
            ["python3", "-m", "mlx_vlm", "generate", "--help"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            load_time = time.time() - start
            logger.info(f"Vision CLI ready (checked in {load_time:.1f}s)")
            return True
        else:
            logger.error("mlx_vlm CLI not available")
            return False
    except Exception as e:
        logger.error(f"Failed to check CLI: {e}")
        return False

def process_image(image_path: str, prompt: str, max_tokens: int = 150, temperature: float = 0.7) -> dict:
    """Process an image using CLI module via shell (avoids GPU timeout issues)."""
    import subprocess
    import shlex

    try:
        start = time.time()

        # Escape the prompt for shell
        escaped_prompt = prompt.replace('"', '\\"').replace("'", "'\"'\"'")

        # Use shell execution which works better than direct subprocess
        cmd = f'''python3 -m mlx_vlm generate \
            --model "{MODEL_ID}" \
            --image "{image_path}" \
            --prompt '{escaped_prompt}' \
            --max-tokens {max_tokens} \
            --temperature {temperature}'''

        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=120,
        )

        elapsed = time.time() - start

        if result.returncode == 0:
            # Parse CLI output
            output = result.stdout
            parts = output.split("==========")

            if len(parts) >= 2:
                middle = parts[1]
                if "<|im_start|>assistant" in middle:
                    response_start = middle.find("<|im_start|>assistant")
                    after_assistant = middle[response_start:]
                    if "\n" in after_assistant:
                        text = after_assistant.split("\n", 1)[1].strip()
                    else:
                        text = after_assistant.strip()
                else:
                    text = middle.strip()
            else:
                text = output.strip()

            return {
                "success": True,
                "response": text,
                "processing_time_ms": int(elapsed * 1000),
                "model": MODEL_ID,
            }
        else:
            return {"error": result.stderr, "success": False}

    except subprocess.TimeoutExpired:
        return {"error": "Processing timeout", "success": False}
    except Exception as e:
        logger.error(f"Processing error: {e}")
        return {"error": str(e), "success": False}

class VisionHandler(BaseHTTPRequestHandler):
    """HTTP request handler for vision API."""

    def log_message(self, format, *args):
        logger.info(f"{self.address_string()} - {format % args}")

    def send_json(self, data: dict, status: int = 200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self.send_json({
                "status": "ok",
                "model_loaded": model is not None,
                "model": MODEL_ID,
                "load_time": load_time,
            })
        elif self.path == "/status":
            self.send_json({
                "ready": model is not None,
                "model": MODEL_ID,
                "load_time_seconds": load_time,
            })
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        if self.path != "/process":
            self.send_json({"error": "Not found"}, 404)
            return

        try:
            # Read request body
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode()
            data = json.loads(body)

            # Get parameters
            prompt = data.get("prompt", "Describe this image")
            max_tokens = data.get("max_tokens", 150)
            temperature = data.get("temperature", 0.7)

            # Handle image input
            image_path = None
            temp_file = None

            if "image_base64" in data:
                # Decode base64 to temp file
                image_data = base64.b64decode(data["image_base64"])
                temp_file = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                temp_file.write(image_data)
                temp_file.close()
                image_path = temp_file.name
            elif "image_path" in data:
                image_path = data["image_path"]
                if not os.path.exists(image_path):
                    self.send_json({"error": f"Image not found: {image_path}"}, 400)
                    return
            else:
                self.send_json({"error": "No image provided (use image_base64 or image_path)"}, 400)
                return

            # Process image
            result = process_image(image_path, prompt, max_tokens, temperature)

            # Cleanup temp file
            if temp_file:
                try:
                    os.unlink(temp_file.name)
                except:
                    pass

            self.send_json(result)

        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
        except Exception as e:
            logger.error(f"Request error: {e}")
            self.send_json({"error": str(e)}, 500)

def run_server(port: int = DEFAULT_PORT):
    """Run the vision server."""
    # Load model first
    if not load_vision_model():
        logger.error("Failed to load model, exiting")
        sys.exit(1)

    # Start HTTP server
    server = HTTPServer(("0.0.0.0", port), VisionHandler)
    logger.info(f"Vision server running on http://localhost:{port}")
    logger.info("Endpoints:")
    logger.info("  GET  /health  - Check server status")
    logger.info("  GET  /status  - Model status")
    logger.info("  POST /process - Process image")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        server.shutdown()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    run_server(port)
