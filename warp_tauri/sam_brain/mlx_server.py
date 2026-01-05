#!/usr/bin/env python3
"""
SAM Brain MLX Server
HTTP API compatible with Ollama's /api/generate endpoint
Runs on port 11435 (one above Ollama)
"""

import sys
import json
import time
import argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock

# MLX imports
from mlx_lm import load, generate

# Paths
FUSED_MODEL_PATH = Path.home() / ".sam" / "models" / "sam-brain-fused"
ADAPTER_PATH = Path.home() / ".sam" / "models" / "sam-brain-lora" / "adapters"
BASE_MODEL = "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit"

# System prompt
SYSTEM_PROMPT = """You are SAM (Smart Autonomous Manager), an AI assistant specialized in:
- Software development and code review
- Project management and task routing
- Understanding codebases and documentation

Be concise and direct. Provide working code, not pseudocode."""

# Global model instance
model = None
tokenizer = None
model_lock = Lock()

def load_model():
    """Load the fine-tuned model."""
    global model, tokenizer

    if FUSED_MODEL_PATH.exists():
        print(f"Loading fused model from {FUSED_MODEL_PATH}", file=sys.stderr)
        model, tokenizer = load(str(FUSED_MODEL_PATH))
    elif ADAPTER_PATH.exists():
        print(f"Loading base model with adapters", file=sys.stderr)
        model, tokenizer = load(BASE_MODEL, adapter_path=str(ADAPTER_PATH))
    else:
        print(f"Loading base model (no fine-tuning)", file=sys.stderr)
        model, tokenizer = load(BASE_MODEL)

    print("Model loaded and ready!", file=sys.stderr)

def generate_response(prompt, max_tokens=500, temperature=0.7):
    """Generate a response using the loaded model."""
    global model, tokenizer

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]

    formatted = tokenizer.apply_chat_template(
        messages,
        add_generation_prompt=True,
        tokenize=False
    )

    with model_lock:
        response = generate(
            model,
            tokenizer,
            prompt=formatted,
            max_tokens=max_tokens,
            verbose=False
        )

    # Clean up stop tokens and repetition
    if response:
        # Remove everything after first <|im_end|>
        if "<|im_end|>" in response:
            response = response.split("<|im_end|>")[0]
        # Also clean other end markers
        for marker in ["<|end|>", "<|endoftext|>", "</s>", "<|assistant|>"]:
            if marker in response:
                response = response.split(marker)[0]

    return response.strip()

class MLXHandler(BaseHTTPRequestHandler):
    """HTTP handler for MLX inference."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/api/tags' or self.path == '/api/models':
            # Return model info (Ollama-compatible)
            self.send_json({
                "models": [{
                    "name": "sam-brain-mlx",
                    "model": "sam-brain-mlx",
                    "size": 868000000,
                    "details": {
                        "family": "qwen2.5-coder",
                        "parameter_size": "1.5B",
                        "quantization": "4bit"
                    }
                }]
            })
        elif self.path == '/health' or self.path == '/':
            self.send_json({"status": "ok", "model": "sam-brain-mlx"})
        else:
            self.send_json({"error": "Not found"}, 404)

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode()

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, 400)
            return

        if self.path == '/api/generate':
            prompt = data.get('prompt', '')
            max_tokens = data.get('options', {}).get('num_predict', 500)
            temperature = data.get('options', {}).get('temperature', 0.7)
            stream = data.get('stream', False)

            if not prompt:
                self.send_json({"error": "No prompt provided"}, 400)
                return

            start_time = time.time()
            response = generate_response(prompt, max_tokens, temperature)
            elapsed = time.time() - start_time

            # Ollama-compatible response
            result = {
                "model": "sam-brain-mlx",
                "response": response,
                "done": True,
                "context": [],
                "total_duration": int(elapsed * 1e9),
                "load_duration": 0,
                "prompt_eval_count": len(prompt.split()),
                "eval_count": len(response.split()),
                "eval_duration": int(elapsed * 1e9)
            }

            self.send_json(result)

        elif self.path == '/api/chat':
            messages = data.get('messages', [])
            max_tokens = data.get('options', {}).get('num_predict', 500)

            # Extract last user message
            prompt = ""
            for msg in messages:
                if msg.get('role') == 'user':
                    prompt = msg.get('content', '')

            if not prompt:
                self.send_json({"error": "No user message"}, 400)
                return

            start_time = time.time()
            response = generate_response(prompt, max_tokens)
            elapsed = time.time() - start_time

            result = {
                "model": "sam-brain-mlx",
                "message": {"role": "assistant", "content": response},
                "done": True,
                "total_duration": int(elapsed * 1e9)
            }

            self.send_json(result)

        else:
            self.send_json({"error": "Unknown endpoint"}, 404)

def main():
    parser = argparse.ArgumentParser(description="SAM Brain MLX Server")
    parser.add_argument("--port", type=int, default=11435, help="Port to listen on")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    args = parser.parse_args()

    print(f"Loading SAM Brain model...", file=sys.stderr)
    load_model()

    server = HTTPServer((args.host, args.port), MLXHandler)
    print(f"\n{'='*50}", file=sys.stderr)
    print(f"  SAM Brain MLX Server", file=sys.stderr)
    print(f"  http://{args.host}:{args.port}", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)
    print(f"\nEndpoints:", file=sys.stderr)
    print(f"  POST /api/generate - Generate text", file=sys.stderr)
    print(f"  POST /api/chat     - Chat completion", file=sys.stderr)
    print(f"  GET  /api/tags     - List models", file=sys.stderr)
    print(f"  GET  /health       - Health check", file=sys.stderr)
    print(f"\nReady for requests!\n", file=sys.stderr)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", file=sys.stderr)
        server.shutdown()

if __name__ == "__main__":
    main()
