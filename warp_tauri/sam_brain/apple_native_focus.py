#!/usr/bin/env python3
"""
SAM Apple Native Focus - Laser-Focused Training

Everything is Apple. Everything is native. No cross-platform fluff.

Focus Areas:
  ┌─────────────────────────────────────────────────────────────────────────┐
  │  APPLE NATIVE STACK                                                      │
  ├─────────────────────────────────────────────────────────────────────────┤
  │                                                                          │
  │  LANGUAGES:                                                             │
  │    Swift (primary)      → SwiftUI, Combine, async/await                 │
  │    Objective-C         → Legacy interop only                            │
  │    Python              → MLX, scripting, automation                     │
  │    Rust                → Performance-critical native                    │
  │                                                                          │
  │  FRAMEWORKS:                                                            │
  │    SwiftUI             → Primary UI framework                           │
  │    AppKit              → macOS native when needed                       │
  │    Core ML             → On-device ML                                   │
  │    Metal               → GPU compute                                    │
  │    AVFoundation        → Audio/Video                                    │
  │    Vision              → Image analysis                                 │
  │    NaturalLanguage     → Text processing                               │
  │    Speech              → STT/TTS native                                 │
  │                                                                          │
  │  NATIVE TOOLS:                                                          │
  │    Xcode               → IDE, instruments, debugging                    │
  │    MLX                 → Apple Silicon ML                               │
  │    Accelerate          → SIMD, BLAS, FFT                               │
  │    Tauri               → Native app wrapper (Rust + webview)            │
  │                                                                          │
  │  HARDWARE:                                                              │
  │    M-series chips      → Unified memory, Neural Engine                  │
  │    8GB optimization    → Our constraint = our expertise                 │
  │                                                                          │
  └─────────────────────────────────────────────────────────────────────────┘

What We DON'T Need:
  - Windows development
  - Linux desktop
  - Android
  - Cross-platform frameworks (Electron, React Native, Flutter)
  - Generic cloud architectures
  - Non-Apple ML frameworks (PyTorch CPU, TensorFlow)

This focus means:
  - 50% less training data needed
  - Deeper expertise in what matters
  - SAM becomes THE expert on Apple native development
"""

import os
import sys
import json
import sqlite3
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Set
from dataclasses import dataclass

# Paths
SAM_BRAIN = Path(__file__).parent
TRAINING_OUTPUT = SAM_BRAIN / "training_data"

# ═══════════════════════════════════════════════════════════════════════════════
# APPLE NATIVE FOCUS CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

APPLE_FOCUS = {
    # Primary languages
    "languages": {
        "swift": {
            "priority": 1,
            "patterns": [
                r"\bswift\b", r"\bswiftui\b", r"\bcombine\b",
                r"\basync\s+let\b", r"\bawait\b", r"\bactor\b",
                r"\bstruct\s+\w+\s*:", r"@\w+\s+var", r"some\s+View",
            ],
            "keywords": ["swift", "swiftui", "combine", "@State", "@Binding",
                        "@Published", "ObservableObject", "actor", "async"],
        },
        "python_mlx": {
            "priority": 1,
            "patterns": [
                r"\bmlx\.", r"\bimport mlx", r"mx\.\w+",
                r"apple.?silicon", r"metal\s+backend",
            ],
            "keywords": ["mlx", "mx.", "apple silicon", "metal", "mps"],
        },
        "rust_native": {
            "priority": 2,
            "patterns": [
                r"\btauri\b", r"#\[tauri", r"fn\s+\w+.*->",
                r"\buse\s+std::", r"impl\s+\w+\s+for",
            ],
            "keywords": ["tauri", "rust", "cargo", "wasm"],
        },
        "objc_interop": {
            "priority": 3,
            "patterns": [
                r"@objc", r"@interface", r"@implementation",
                r"\[.*\s+\w+\]",  # Objective-C method call
            ],
            "keywords": ["objective-c", "@objc", "bridging", "NSObject"],
        },
    },

    # Apple frameworks
    "frameworks": {
        "swiftui": {
            "priority": 1,
            "patterns": [
                r"View\s*{", r"body:\s*some\s+View",
                r"@State", r"@Binding", r"@Environment",
                r"VStack|HStack|ZStack", r"\.modifier\(",
            ],
            "concepts": ["declarative UI", "state management", "view composition"],
        },
        "appkit": {
            "priority": 2,
            "patterns": [
                r"NSWindow", r"NSView", r"NSApplication",
                r"NSNotification", r"NSEvent",
            ],
            "concepts": ["window management", "event handling", "AppKit lifecycle"],
        },
        "coreml": {
            "priority": 1,
            "patterns": [
                r"CoreML", r"MLModel", r"VNCoreMLRequest",
                r"\.mlmodel", r"MLArrayBatchProvider",
            ],
            "concepts": ["on-device ML", "model conversion", "prediction"],
        },
        "metal": {
            "priority": 2,
            "patterns": [
                r"MTL\w+", r"MTKView", r"metal",
                r"compute.?kernel", r"shader",
            ],
            "concepts": ["GPU compute", "shaders", "render pipeline"],
        },
        "avfoundation": {
            "priority": 2,
            "patterns": [
                r"AV\w+", r"AVAudioEngine", r"AVSpeech",
                r"CMSampleBuffer", r"AVPlayer",
            ],
            "concepts": ["audio processing", "video capture", "playback"],
        },
        "vision": {
            "priority": 1,
            "patterns": [
                r"VN\w+Request", r"VNImageRequestHandler",
                r"VNRecognizedText", r"VNFaceObservation",
            ],
            "concepts": ["OCR", "face detection", "object detection", "image analysis"],
        },
    },

    # Exclude patterns (things we don't want)
    "exclude": {
        "cross_platform": [
            r"\belectron\b", r"\breact.?native\b", r"\bflutter\b",
            r"\bxamarin\b", r"\bcordova\b", r"\bionic\b",
        ],
        "non_apple": [
            r"\bandroid\b", r"\bwindows\b", r"\blinux desktop\b",
            r"\bwin32\b", r"\b\.NET\b", r"\bC#\b",
        ],
        "cloud_generic": [
            r"\bAWS\b", r"\bAzure\b", r"\bGCP\b",
            r"\bkubernetes\b", r"\bdocker.?compose\b",
        ],
        "non_mlx_ml": [
            r"\btorch\.cuda\b", r"\btensorflow\b", r"\bkeras\b",
            r"\bGPU.?cluster\b", r"\bTPU\b",
        ],
    },
}


class AppleNativeFilter:
    """Filter and prioritize Apple-native content."""

    def __init__(self):
        self.config = APPLE_FOCUS
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile regex patterns for speed."""
        self.include_patterns = {}
        for category, items in self.config["languages"].items():
            self.include_patterns[category] = [
                re.compile(p, re.IGNORECASE) for p in items["patterns"]
            ]
        for category, items in self.config["frameworks"].items():
            self.include_patterns[f"fw_{category}"] = [
                re.compile(p, re.IGNORECASE) for p in items["patterns"]
            ]

        self.exclude_patterns = []
        for category, patterns in self.config["exclude"].items():
            for p in patterns:
                self.exclude_patterns.append(re.compile(p, re.IGNORECASE))

    def is_apple_native(self, text: str) -> Tuple[bool, List[str]]:
        """Check if content is Apple-native focused."""
        if not text:
            return False, []

        # Check excludes first
        for pattern in self.exclude_patterns:
            if pattern.search(text):
                return False, ["excluded"]

        # Check includes
        matched_categories = []
        for category, patterns in self.include_patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    matched_categories.append(category)
                    break

        return len(matched_categories) > 0, matched_categories

    def score_apple_relevance(self, text: str) -> float:
        """Score how relevant content is to Apple native development."""
        if not text:
            return 0.0

        score = 0.0
        text_lower = text.lower()

        # Check for exclusions (strong negative)
        for pattern in self.exclude_patterns:
            if pattern.search(text):
                return 0.0  # Instant disqualification

        # Score by language priority
        for lang, config in self.config["languages"].items():
            priority = config["priority"]
            for keyword in config["keywords"]:
                if keyword.lower() in text_lower:
                    score += (4 - priority) * 0.1  # Higher priority = more points

        # Score by framework presence
        for fw, config in self.config["frameworks"].items():
            priority = config["priority"]
            for pattern in config["patterns"]:
                if re.search(pattern, text, re.IGNORECASE):
                    score += (4 - priority) * 0.15
                    break

        # Bonus for M-series / Apple Silicon specific
        if any(p in text_lower for p in ["m1", "m2", "m3", "apple silicon", "neural engine"]):
            score += 0.3

        # Bonus for memory optimization (our constraint)
        if any(p in text_lower for p in ["8gb", "memory efficient", "low memory", "unified memory"]):
            score += 0.2

        return min(1.0, score)

    def filter_examples(self, examples: List[Dict]) -> List[Dict]:
        """Filter examples to Apple-native only."""
        filtered = []

        for ex in examples:
            content = ""
            if "messages" in ex:
                for msg in ex["messages"]:
                    content += msg.get("content", "") + " "
            else:
                content = ex.get("user_content", "") + " " + ex.get("assistant_content", "")

            is_native, categories = self.is_apple_native(content)

            if is_native:
                relevance = self.score_apple_relevance(content)
                ex["apple_relevance"] = relevance
                ex["apple_categories"] = categories
                filtered.append(ex)

        # Sort by relevance
        filtered.sort(key=lambda x: x.get("apple_relevance", 0), reverse=True)

        return filtered


# ═══════════════════════════════════════════════════════════════════════════════
# APPLE-FOCUSED TRAINING CURRICULUM
# ═══════════════════════════════════════════════════════════════════════════════

APPLE_CURRICULUM = {
    "phase_1_fundamentals": {
        "name": "Swift & SwiftUI Fundamentals",
        "target_examples": 3000,
        "topics": [
            "Swift syntax and semantics",
            "SwiftUI view basics",
            "State management (@State, @Binding)",
            "Basic layout (VStack, HStack, ZStack)",
            "Swift async/await",
        ],
    },
    "phase_2_intermediate": {
        "name": "Native Framework Mastery",
        "target_examples": 4000,
        "topics": [
            "Combine framework",
            "Core ML integration",
            "Vision framework (OCR, detection)",
            "AVFoundation basics",
            "SwiftUI navigation and data flow",
        ],
    },
    "phase_3_advanced": {
        "name": "Performance & Optimization",
        "target_examples": 3000,
        "topics": [
            "Metal compute",
            "MLX inference optimization",
            "Memory management on 8GB",
            "Accelerate framework",
            "Instruments profiling",
        ],
    },
    "phase_4_integration": {
        "name": "System Integration",
        "target_examples": 2000,
        "topics": [
            "Tauri + Rust backend",
            "Python + Swift bridging",
            "AppKit for macOS specifics",
            "Background processing",
            "File system integration",
        ],
    },
    "phase_5_expertise": {
        "name": "Deep Expertise",
        "target_examples": 1500,
        "topics": [
            "Custom ML model deployment",
            "Voice pipeline (STT/TTS native)",
            "Real-time audio processing",
            "Neural Engine optimization",
            "App Store deployment",
        ],
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# APPLE-NATIVE TRAINING EXAMPLES (HIGH VALUE)
# ═══════════════════════════════════════════════════════════════════════════════

APPLE_NATIVE_EXAMPLES = [
    {
        "category": "swiftui_state",
        "user": "What's the difference between @State, @Binding, @StateObject, and @ObservedObject in SwiftUI?",
        "assistant": """These property wrappers manage different ownership and lifecycle patterns:

**@State** - Owned by THIS view, value type
```swift
struct CounterView: View {
    @State private var count = 0  // This view owns this value

    var body: some View {
        Button("Count: \\(count)") { count += 1 }
    }
}
```
Use for: Simple value types (Int, String, Bool) that this view controls.

**@Binding** - Reference to state owned ELSEWHERE
```swift
struct ChildView: View {
    @Binding var count: Int  // Parent owns this, we just reference it

    var body: some View {
        Button("Increment") { count += 1 }  // Modifies parent's state
    }
}

// Parent passes binding:
ChildView(count: $count)  // $ creates binding
```
Use for: When child views need to modify parent's state.

**@StateObject** - Owned by THIS view, reference type (ObservableObject)
```swift
struct ParentView: View {
    @StateObject private var viewModel = ViewModel()  // Created and owned here

    var body: some View {
        ChildView(viewModel: viewModel)
    }
}
```
Use for: Creating and owning ObservableObject instances. Only create once.

**@ObservedObject** - Reference to object owned ELSEWHERE
```swift
struct ChildView: View {
    @ObservedObject var viewModel: ViewModel  // Passed in, not owned

    var body: some View {
        Text(viewModel.data)
    }
}
```
Use for: Receiving ObservableObject from parent. Don't use for creation.

**The Rule**: Own it? Use @State/@StateObject. Reference it? Use @Binding/@ObservedObject.""",
    },
    {
        "category": "mlx_optimization",
        "user": "How do I optimize MLX inference for 8GB RAM on M2?",
        "assistant": """For 8GB M2 optimization with MLX, focus on these strategies:

**1. KV-Cache Quantization (Biggest Win)**
```python
import mlx.core as mx
from mlx_lm import load, generate

# Load with 4-bit quantization
model, tokenizer = load(
    "mlx-community/Qwen2.5-3B-Instruct-4bit",
    tokenizer_config={"trust_remote_code": True}
)

# Use quantized KV-cache for 75% memory savings
response = generate(
    model, tokenizer,
    prompt="Your prompt",
    max_tokens=512,
    kv_cache_quantization=True,  # Critical for 8GB
    kv_cache_bits=8              # 8-bit cache
)
```

**2. Prefill Chunking**
```python
# Don't load entire context at once
def chunked_prefill(prompt, chunk_size=512):
    tokens = tokenizer.encode(prompt)
    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i:i+chunk_size]
        model.prefill(chunk)  # Process in chunks
        mx.eval(model.cache)  # Evaluate before next chunk
```

**3. Model Selection by Task**
```python
# Use smaller model when possible
MODELS = {
    "simple": "Qwen2.5-1.5B-4bit",  # Fast, fits easily
    "complex": "Qwen2.5-3B-4bit",    # Better quality
}

def select_model(query):
    if is_simple_query(query):
        return load(MODELS["simple"])
    return load(MODELS["complex"])
```

**4. Memory Monitoring**
```python
import psutil

def check_memory():
    mem = psutil.virtual_memory()
    available_gb = mem.available / (1024**3)

    if available_gb < 2.0:
        # Too low - use smaller model or clear cache
        mx.metal.clear_cache()
        return False
    return True
```

**5. Lazy Loading**
```python
# Don't load model until needed
_model = None

def get_model():
    global _model
    if _model is None:
        _model = load("Qwen2.5-1.5B-4bit")
    return _model
```

**Memory Budget for 8GB**:
- OS + Apps: ~2GB reserved
- Model (4-bit 3B): ~2GB
- KV-Cache: ~1-2GB (with quantization)
- Working memory: ~2GB
- Buffer: ~1GB

With these optimizations, you can run 3B models comfortably on 8GB.""",
    },
    {
        "category": "tauri_rust",
        "user": "How do I call Rust functions from Swift in a Tauri app?",
        "assistant": """Tauri uses a command pattern - Rust exposes commands that the frontend calls via IPC.

**1. Define Rust Command**
```rust
// src-tauri/src/main.rs
use tauri::Manager;

#[tauri::command]
fn process_text(input: String) -> Result<String, String> {
    // Your Rust logic here
    let result = input.to_uppercase();
    Ok(result)
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![process_text])
        .run(tauri::generate_context!())
        .expect("error running app");
}
```

**2. Call from Frontend (JavaScript)**
```javascript
// In your webview JavaScript
import { invoke } from '@tauri-apps/api/tauri'

async function callRust(text) {
    try {
        const result = await invoke('process_text', { input: text })
        return result
    } catch (error) {
        console.error('Rust call failed:', error)
    }
}
```

**3. For Native Swift (macOS only)**

If you need actual Swift↔Rust, use C FFI:

```rust
// Rust: expose C-compatible function
#[no_mangle]
pub extern "C" fn rust_process(input: *const c_char) -> *mut c_char {
    // Convert, process, return
}
```

```swift
// Swift: call via bridging header
@_silgen_name("rust_process")
func rustProcess(_ input: UnsafePointer<CChar>) -> UnsafeMutablePointer<CChar>

// Usage
let result = String(cString: rustProcess(input.cString(using: .utf8)!))
```

**Recommended Pattern for SAM**:
1. Use Tauri commands for most communication (clean, async, typed)
2. Keep heavy compute in Rust
3. UI state in SwiftUI/JavaScript
4. Only use FFI for performance-critical hot paths

**Pro tip**: Tauri 2.0 supports native Swift plugins directly - check `tauri-plugin-swift` for cleaner integration.""",
    },
    {
        "category": "vision_ocr",
        "user": "How do I use Apple's Vision framework for fast OCR?",
        "assistant": """Vision framework gives you fast, accurate, FREE OCR - no API calls needed.

**Basic OCR (22ms typical)**
```swift
import Vision

func performOCR(on image: CGImage) async throws -> String {
    return try await withCheckedThrowingContinuation { continuation in
        let request = VNRecognizeTextRequest { request, error in
            guard let observations = request.results as? [VNRecognizedTextObservation] else {
                continuation.resume(throwing: error ?? OCRError.noResults)
                return
            }

            let text = observations
                .compactMap { $0.topCandidates(1).first?.string }
                .joined(separator: "\\n")

            continuation.resume(returning: text)
        }

        // Fast mode for speed, accurate for quality
        request.recognitionLevel = .fast  // or .accurate
        request.usesLanguageCorrection = true

        let handler = VNImageRequestHandler(cgImage: image)
        try? handler.perform([request])
    }
}
```

**With Bounding Boxes (for UI overlay)**
```swift
struct TextBlock {
    let text: String
    let boundingBox: CGRect
    let confidence: Float
}

func ocrWithLocations(image: CGImage) async throws -> [TextBlock] {
    // Similar setup, but extract bounds:
    let blocks = observations.flatMap { observation in
        observation.topCandidates(1).map { candidate in
            TextBlock(
                text: candidate.string,
                boundingBox: observation.boundingBox,  // Normalized 0-1
                confidence: candidate.confidence
            )
        }
    }
    return blocks
}
```

**Python via PyObjC (for MLX integration)**
```python
import Vision
import Quartz

def apple_ocr(image_path: str) -> str:
    \"\"\"Fast OCR using Apple Vision - ~22ms per image.\"\"\"
    # Load image
    url = Foundation.NSURL.fileURLWithPath_(image_path)
    source = Quartz.CGImageSourceCreateWithURL(url, None)
    image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)

    # Create request
    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelFast)

    # Process
    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(image, None)
    handler.performRequests_error_([request], None)

    # Extract text
    results = request.results()
    text = "\\n".join(obs.topCandidates_(1)[0].string() for obs in results)

    return text
```

**Performance Tips**:
1. `.fast` mode: ~22ms, good for most text
2. `.accurate` mode: ~200ms, better for handwriting
3. Batch images for GPU efficiency
4. Cache results - Vision is deterministic

**Why Apple Vision > Cloud OCR**:
- Zero latency (no network)
- Zero cost (no API fees)
- Privacy (data stays on device)
- Fast (22ms vs 500ms+ API calls)""",
    },
]


def generate_apple_training():
    """Generate Apple-native focused training examples."""
    output_file = TRAINING_OUTPUT / f"apple_native_{datetime.now().strftime('%Y%m%d')}.jsonl"

    with open(output_file, 'w') as f:
        for ex in APPLE_NATIVE_EXAMPLES:
            training = {
                "messages": [
                    {"role": "user", "content": ex["user"]},
                    {"role": "assistant", "content": ex["assistant"]}
                ],
                "metadata": {
                    "category": ex["category"],
                    "source": "apple_native_focus",
                    "quality": 0.95
                }
            }
            f.write(json.dumps(training) + "\n")

    print(f"Generated {len(APPLE_NATIVE_EXAMPLES)} Apple-native examples to {output_file}")
    return len(APPLE_NATIVE_EXAMPLES)


def status():
    """Show Apple-native focus status."""
    print("\n" + "═" * 60)
    print("  APPLE NATIVE FOCUS")
    print("═" * 60)

    print("\n🍎 LANGUAGES (Priority Order)")
    print("─" * 60)
    for lang, config in APPLE_FOCUS["languages"].items():
        priority = config["priority"]
        indicator = "★" * (4 - priority) + "☆" * (priority - 1)
        print(f"  {indicator} {lang:15} Keywords: {', '.join(config['keywords'][:5])}")

    print("\n📦 FRAMEWORKS")
    print("─" * 60)
    for fw, config in APPLE_FOCUS["frameworks"].items():
        priority = config["priority"]
        indicator = "★" * (4 - priority) + "☆" * (priority - 1)
        concepts = ", ".join(config["concepts"][:3])
        print(f"  {indicator} {fw:15} → {concepts}")

    print("\n🚫 EXCLUDED (Not Apple Native)")
    print("─" * 60)
    for category, patterns in APPLE_FOCUS["exclude"].items():
        readable = [p.replace(r"\b", "").replace("\\", "") for p in patterns[:4]]
        print(f"  {category:20} {', '.join(readable)}")

    print("\n📚 CURRICULUM PHASES")
    print("─" * 60)
    total_examples = 0
    for phase, config in APPLE_CURRICULUM.items():
        target = config["target_examples"]
        total_examples += target
        print(f"  {config['name']}")
        print(f"      Target: {target:,} examples")
        print(f"      Topics: {', '.join(config['topics'][:3])}...")

    print(f"\n  TOTAL: {total_examples:,} focused examples")

    print("\n" + "═" * 60)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        status()
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "status":
        status()

    elif cmd == "generate":
        count = generate_apple_training()
        print(f"\nGenerated {count} examples")

    elif cmd == "filter":
        # Filter existing training data
        filter_obj = AppleNativeFilter()

        all_examples = []
        for jsonl_file in TRAINING_OUTPUT.glob("*.jsonl"):
            with open(jsonl_file) as f:
                for line in f:
                    try:
                        all_examples.append(json.loads(line))
                    except:
                        continue

        print(f"Loaded {len(all_examples)} examples")

        apple_only = filter_obj.filter_examples(all_examples)
        print(f"Apple-native: {len(apple_only)} ({len(apple_only)/len(all_examples)*100:.1f}%)")

        # Save filtered
        output = TRAINING_OUTPUT / f"apple_filtered_{datetime.now().strftime('%Y%m%d')}.jsonl"
        with open(output, 'w') as f:
            for ex in apple_only[:10000]:  # Top 10K by relevance
                f.write(json.dumps(ex) + "\n")
        print(f"Saved to {output}")

    else:
        print(f"Unknown: {cmd}")


if __name__ == "__main__":
    main()
