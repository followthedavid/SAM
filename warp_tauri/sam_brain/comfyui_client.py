#!/usr/bin/env python3
"""
ComfyUI Client for SAM Brain
Enables SAM to generate images via ComfyUI's API
"""

import json
import uuid
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional
import time

# Try websocket import - optional for async operation
try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False
    print("websocket-client not installed - using sync API only")

COMFYUI_URL = "127.0.0.1:8188"
OUTPUT_DIR = Path("/Users/davidquinton/ai-studio/ComfyUI/output")

# Default workflow for text-to-image with Realistic Vision
DEFAULT_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 7,
            "denoise": 1,
            "latent_image": ["5", 0],
            "model": ["4", 0],
            "negative": ["7", 0],
            "positive": ["6", 0],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 0,
            "steps": 20
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "realisticVisionV51_v51VAE.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 512,
            "width": 512
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["4", 1],
            "text": ""
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["4", 1],
            "text": "bad quality, blurry, ugly, deformed, bad anatomy"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "SAM",
            "images": ["8", 0]
        }
    }
}

# Workflow with LoRA support (for when you train your aesthetic)
LORA_WORKFLOW = {
    "3": {
        "class_type": "KSampler",
        "inputs": {
            "cfg": 7,
            "denoise": 1,
            "latent_image": ["5", 0],
            "model": ["10", 0],  # From LoRA loader
            "negative": ["7", 0],
            "positive": ["6", 0],
            "sampler_name": "euler",
            "scheduler": "normal",
            "seed": 0,
            "steps": 20
        }
    },
    "4": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {
            "ckpt_name": "realisticVisionV51_v51VAE.safetensors"
        }
    },
    "5": {
        "class_type": "EmptyLatentImage",
        "inputs": {
            "batch_size": 1,
            "height": 512,
            "width": 512
        }
    },
    "6": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["10", 1],  # From LoRA loader
            "text": ""
        }
    },
    "7": {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "clip": ["10", 1],
            "text": "bad quality, blurry, ugly, deformed, bad anatomy"
        }
    },
    "8": {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["3", 0],
            "vae": ["4", 2]
        }
    },
    "9": {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": "SAM",
            "images": ["8", 0]
        }
    },
    "10": {
        "class_type": "LoraLoader",
        "inputs": {
            "lora_name": "",  # Set when using
            "strength_model": 0.8,
            "strength_clip": 0.8,
            "model": ["4", 0],
            "clip": ["4", 1]
        }
    }
}


def is_comfyui_running() -> bool:
    """Check if ComfyUI server is running"""
    try:
        urllib.request.urlopen(f"http://{COMFYUI_URL}/system_stats", timeout=2)
        return True
    except:
        return False


def queue_prompt(prompt: dict) -> str:
    """Queue a workflow for execution, returns prompt_id"""
    data = json.dumps({"prompt": prompt}).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFYUI_URL}/prompt", data=data)
    response = json.loads(urllib.request.urlopen(req).read())
    return response.get("prompt_id", "")


def get_history(prompt_id: str) -> dict:
    """Get generation history for a prompt"""
    url = f"http://{COMFYUI_URL}/history/{prompt_id}"
    with urllib.request.urlopen(url) as response:
        return json.loads(response.read())


def get_image(filename: str, subfolder: str = "", folder_type: str = "output") -> bytes:
    """Download a generated image"""
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{COMFYUI_URL}/view?{url_values}") as response:
        return response.read()


def wait_for_completion(prompt_id: str, timeout: int = 120) -> dict:
    """Poll for completion (fallback when websocket not available)"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            history = get_history(prompt_id)
            if prompt_id in history:
                return history[prompt_id]
        except:
            pass
        time.sleep(1)
    return {}


def generate_image(
    prompt: str,
    negative: str = "bad quality, blurry, ugly, deformed, bad anatomy",
    width: int = 512,
    height: int = 512,
    steps: int = 20,
    cfg: float = 7.0,
    seed: Optional[int] = None,
    lora_name: Optional[str] = None,
    lora_strength: float = 0.8
) -> dict:
    """
    Generate an image from a text prompt

    Args:
        prompt: Text description of the image
        negative: Things to avoid in generation
        width: Image width (default 512)
        height: Image height (default 512)
        steps: Sampling steps (default 20)
        cfg: Guidance scale (default 7.0)
        seed: Random seed (None for random)
        lora_name: Optional LoRA model filename
        lora_strength: LoRA strength (default 0.8)

    Returns:
        dict with 'success', 'images', 'error' keys
    """
    if not is_comfyui_running():
        return {
            "success": False,
            "error": "ComfyUI not running. Start it with: cd ~/ai-studio/ComfyUI && python main.py",
            "images": []
        }

    # Select workflow
    if lora_name:
        workflow = json.loads(json.dumps(LORA_WORKFLOW))
        workflow["10"]["inputs"]["lora_name"] = lora_name
        workflow["10"]["inputs"]["strength_model"] = lora_strength
        workflow["10"]["inputs"]["strength_clip"] = lora_strength
    else:
        workflow = json.loads(json.dumps(DEFAULT_WORKFLOW))

    # Set parameters
    workflow["6"]["inputs"]["text"] = prompt
    workflow["7"]["inputs"]["text"] = negative
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    workflow["3"]["inputs"]["steps"] = steps
    workflow["3"]["inputs"]["cfg"] = cfg
    workflow["3"]["inputs"]["seed"] = seed if seed is not None else int(time.time() * 1000) % 2147483647

    try:
        # Queue the prompt
        prompt_id = queue_prompt(workflow)

        if not prompt_id:
            return {"success": False, "error": "Failed to queue prompt", "images": []}

        # Wait for completion
        if HAS_WEBSOCKET:
            # Use websocket for efficient waiting
            client_id = str(uuid.uuid4())
            ws = websocket.WebSocket()
            ws.connect(f"ws://{COMFYUI_URL}/ws?clientId={client_id}")

            while True:
                out = ws.recv()
                if isinstance(out, str):
                    message = json.loads(out)
                    if message['type'] == 'executing':
                        data = message['data']
                        if data['node'] is None and data['prompt_id'] == prompt_id:
                            break
            ws.close()
        else:
            # Fallback to polling
            time.sleep(2)  # Initial wait

        # Get results
        history = wait_for_completion(prompt_id)

        if not history:
            return {"success": False, "error": "Generation timed out", "images": []}

        # Extract image paths
        images = []
        outputs = history.get('outputs', {})
        for node_id in outputs:
            node_output = outputs[node_id]
            if 'images' in node_output:
                for img in node_output['images']:
                    img_path = OUTPUT_DIR / img['subfolder'] / img['filename'] if img['subfolder'] else OUTPUT_DIR / img['filename']
                    images.append(str(img_path))

        return {
            "success": True,
            "images": images,
            "prompt_id": prompt_id,
            "seed": workflow["3"]["inputs"]["seed"]
        }

    except Exception as e:
        return {"success": False, "error": str(e), "images": []}


def list_available_models() -> dict:
    """List available checkpoints and LoRAs"""
    try:
        checkpoints_dir = Path("/Users/davidquinton/ai-studio/ComfyUI/models/checkpoints")
        loras_dir = Path("/Users/davidquinton/ai-studio/ComfyUI/models/loras")

        checkpoints = [f.name for f in checkpoints_dir.glob("*.safetensors")]
        loras = [f.name for f in loras_dir.glob("*.safetensors")]

        return {
            "checkpoints": checkpoints,
            "loras": loras
        }
    except Exception as e:
        return {"error": str(e)}


def enhance_prompt(base_prompt: str) -> str:
    """Enhance a basic prompt with quality boosters for realistic images"""
    quality_tags = [
        "masterpiece",
        "best quality",
        "highly detailed",
        "professional photography",
        "8k uhd",
        "realistic lighting"
    ]

    # Don't add if already has quality tags
    if any(tag in base_prompt.lower() for tag in ["masterpiece", "best quality", "8k"]):
        return base_prompt

    return f"{', '.join(quality_tags)}, {base_prompt}"


# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("ComfyUI Client for SAM")
        print("Usage:")
        print("  python comfyui_client.py check       - Check if ComfyUI is running")
        print("  python comfyui_client.py models      - List available models")
        print("  python comfyui_client.py generate <prompt>")
        print("  python comfyui_client.py generate <prompt> --lora <name>")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "check":
        if is_comfyui_running():
            print("ComfyUI is running at http://127.0.0.1:8188")
        else:
            print("ComfyUI is not running")
            print("Start with: cd ~/ai-studio/ComfyUI && python main.py")

    elif cmd == "models":
        models = list_available_models()
        print("Available checkpoints:")
        for ckpt in models.get("checkpoints", []):
            print(f"  - {ckpt}")
        print("\nAvailable LoRAs:")
        for lora in models.get("loras", []):
            print(f"  - {lora}")

    elif cmd == "generate":
        if len(sys.argv) < 3:
            print("Usage: python comfyui_client.py generate <prompt>")
            sys.exit(1)

        # Parse args
        lora_name = None
        prompt_parts = []
        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--lora" and i + 1 < len(sys.argv):
                lora_name = sys.argv[i + 1]
                i += 2
            else:
                prompt_parts.append(sys.argv[i])
                i += 1

        prompt = " ".join(prompt_parts)
        enhanced = enhance_prompt(prompt)

        print(f"Generating: {enhanced}")
        if lora_name:
            print(f"Using LoRA: {lora_name}")

        result = generate_image(enhanced, lora_name=lora_name)

        if result["success"]:
            print(f"Generated {len(result['images'])} image(s):")
            for img in result["images"]:
                print(f"  {img}")
            print(f"Seed: {result['seed']}")
        else:
            print(f"Error: {result['error']}")
