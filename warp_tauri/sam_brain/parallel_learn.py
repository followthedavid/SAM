#!/usr/bin/env python3
"""
Parallel Learning Streams for SAM
=================================
Maximizes throughput by running multiple learning pipelines simultaneously.
"""

import os
import sys
import json
import subprocess
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import threading
import queue

BRAIN_PATH = Path(__file__).parent
DATA_PATH = BRAIN_PATH / "data"
EXTERNAL = Path("/Volumes/David External")

DATA_PATH.mkdir(parents=True, exist_ok=True)


class ParallelLearner:
    """Run multiple learning streams in parallel."""

    def __init__(self, max_workers: int = 6):
        self.max_workers = max_workers
        self.results = {}
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

    def run_all_streams(self) -> Dict[str, Any]:
        """Launch all learning streams in parallel."""
        print("\n" + "=" * 60)
        print("PARALLEL LEARNING - ALL STREAMS")
        print("=" * 60)

        streams = {
            "chatgpt_apple": self._stream_chatgpt_apple,
            "chatgpt_code": self._stream_chatgpt_code,
            "chatgpt_re": self._stream_chatgpt_reverse_engineering,
            "claude_history": self._stream_claude_history,
            "your_code": self._stream_your_codebase,
            "your_frida": self._stream_frida_scripts,
            "apple_docs": self._stream_apple_patterns,
            "synthetic_swift": self._stream_synthetic_swift,
            "synthetic_re": self._stream_synthetic_re,
        }

        futures = {}
        for name, func in streams.items():
            future = self.executor.submit(func)
            futures[future] = name
            print(f"  [STARTED] {name}")

        # Collect results as they complete
        for future in concurrent.futures.as_completed(futures):
            name = futures[future]
            try:
                count = future.result()
                self.results[name] = count
                print(f"  [DONE] {name}: {count} examples")
            except Exception as e:
                self.results[name] = f"error: {e}"
                print(f"  [ERROR] {name}: {e}")

        # Merge all results
        total = self._merge_all_training_data()

        print("\n" + "=" * 60)
        print(f"TOTAL TRAINING EXAMPLES: {total}")
        print("=" * 60)

        return self.results

    def _stream_chatgpt_apple(self) -> int:
        """Extract Apple-related conversations from ChatGPT export."""
        chatgpt_path = EXTERNAL / "SAM_training" / "conversations.json"
        if not chatgpt_path.exists():
            return 0

        apple_keywords = [
            'swift', 'swiftui', 'xcode', 'ios', 'macos', 'ipados',
            'uikit', 'appkit', 'coreml', 'vision', 'metal', 'homekit',
            'shortcuts', 'siri', 'apple watch', 'watchos', 'tvos',
            'cocoa', 'objective-c', 'objc', 'foundation', 'combine',
            'app store', 'testflight', 'notarization', 'codesign',
            'entitlements', 'provisioning', 'apple silicon', 'm1', 'm2',
            'mlx', 'coredata', 'cloudkit', 'icloud', 'keychain'
        ]

        examples = []
        with open(chatgpt_path) as f:
            conversations = json.load(f)

        for conv in conversations:
            mapping = conv.get("mapping", {})
            messages = []

            for node in mapping.values():
                msg = node.get("message")
                if msg and msg.get("content", {}).get("parts"):
                    role = msg.get("author", {}).get("role", "")
                    text = " ".join(msg["content"]["parts"])
                    if text.strip():
                        messages.append((role, text))

            # Check if Apple-related
            full_text = " ".join(t for _, t in messages).lower()
            if any(kw in full_text for kw in apple_keywords):
                # Extract Q&A pairs
                for i in range(len(messages) - 1):
                    if messages[i][0] == "user" and messages[i+1][0] == "assistant":
                        q, a = messages[i][1], messages[i+1][1]
                        if len(a) > 100:
                            examples.append({
                                "instruction": q[:1500],
                                "response": a[:3000],
                                "category": "apple"
                            })

        # Save
        output = DATA_PATH / "stream_chatgpt_apple.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_chatgpt_code(self) -> int:
        """Extract code-heavy conversations from ChatGPT."""
        chatgpt_path = EXTERNAL / "SAM_training" / "conversations.json"
        if not chatgpt_path.exists():
            return 0

        examples = []
        with open(chatgpt_path) as f:
            conversations = json.load(f)

        for conv in conversations:
            mapping = conv.get("mapping", {})
            messages = []

            for node in mapping.values():
                msg = node.get("message")
                if msg and msg.get("content", {}).get("parts"):
                    role = msg.get("author", {}).get("role", "")
                    text = " ".join(msg["content"]["parts"])
                    if text.strip():
                        messages.append((role, text))

            # Check for code blocks
            for i in range(len(messages) - 1):
                if messages[i][0] == "user" and messages[i+1][0] == "assistant":
                    q, a = messages[i][1], messages[i+1][1]
                    if "```" in a and len(a) > 200:
                        examples.append({
                            "instruction": q[:1500],
                            "response": a[:3000],
                            "category": "code"
                        })

        output = DATA_PATH / "stream_chatgpt_code.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_chatgpt_reverse_engineering(self) -> int:
        """Extract reverse engineering conversations."""
        chatgpt_path = EXTERNAL / "SAM_training" / "conversations.json"
        if not chatgpt_path.exists():
            return 0

        re_keywords = [
            'reverse engineer', 'frida', 'hopper', 'ida', 'ghidra',
            'disassembly', 'binary', 'hook', 'inject', 'patch',
            'jailbreak', 'tweak', 'dylib', 'mach-o', 'arm64',
            'objc_msgSend', 'method swizzle', 'runtime', 'class-dump',
            'cycript', 'lldb', 'debugger', 'breakpoint', 'memory',
            'hex', 'assembly', 'decompile', 'symbols', 'export'
        ]

        examples = []
        with open(chatgpt_path) as f:
            conversations = json.load(f)

        for conv in conversations:
            mapping = conv.get("mapping", {})
            messages = []

            for node in mapping.values():
                msg = node.get("message")
                if msg and msg.get("content", {}).get("parts"):
                    role = msg.get("author", {}).get("role", "")
                    text = " ".join(msg["content"]["parts"])
                    if text.strip():
                        messages.append((role, text))

            full_text = " ".join(t for _, t in messages).lower()
            if any(kw in full_text for kw in re_keywords):
                for i in range(len(messages) - 1):
                    if messages[i][0] == "user" and messages[i+1][0] == "assistant":
                        q, a = messages[i][1], messages[i+1][1]
                        if len(a) > 100:
                            examples.append({
                                "instruction": q[:1500],
                                "response": a[:3000],
                                "category": "reverse_engineering"
                            })

        output = DATA_PATH / "stream_chatgpt_re.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_claude_history(self) -> int:
        """Extract from all Claude Code history."""
        claude_dir = Path.home() / ".claude"
        if not claude_dir.exists():
            return 0

        examples = []
        for history_file in claude_dir.rglob("*.jsonl"):
            try:
                with open(history_file) as f:
                    lines = [json.loads(l) for l in f if l.strip()]

                for i in range(0, len(lines) - 1, 2):
                    user_msg = lines[i]
                    asst_msg = lines[i + 1] if i + 1 < len(lines) else None

                    if not asst_msg:
                        continue

                    # Extract text
                    user_text = self._extract_text(user_msg)
                    asst_text = self._extract_text(asst_msg)

                    if user_text and asst_text and len(asst_text) > 100:
                        examples.append({
                            "instruction": user_text[:1500],
                            "response": asst_text[:3000],
                            "category": "claude"
                        })
            except:
                continue

        output = DATA_PATH / "stream_claude_history.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _extract_text(self, msg: dict) -> str:
        """Extract text from Claude message format."""
        content = msg.get("message", {}).get("content", "")
        if isinstance(content, list):
            return " ".join(
                c.get("text", "") for c in content
                if isinstance(c, dict) and c.get("type") == "text"
            )
        return str(content) if content else ""

    def _stream_your_codebase(self) -> int:
        """Learn from your existing code patterns."""
        code_dirs = [
            Path.home() / "ReverseLab" / "SAM",
            Path.home() / "ReverseLab" / "frida",
            Path.home() / "ReverseLab" / "GridPlayer",
        ]

        examples = []
        for code_dir in code_dirs:
            if not code_dir.exists():
                continue

            for py_file in code_dir.rglob("*.py"):
                try:
                    content = py_file.read_text()
                    if len(content) < 100:
                        continue

                    # Extract docstrings as instruction/response pairs
                    if '"""' in content:
                        # Function with docstring
                        examples.append({
                            "instruction": f"Show me the code in {py_file.name}",
                            "response": f"```python\n{content[:2000]}\n```",
                            "category": "your_code"
                        })
                except:
                    continue

            for swift_file in code_dir.rglob("*.swift"):
                try:
                    content = swift_file.read_text()
                    if len(content) > 100:
                        examples.append({
                            "instruction": f"Show me {swift_file.name}",
                            "response": f"```swift\n{content[:2000]}\n```",
                            "category": "your_code"
                        })
                except:
                    continue

        output = DATA_PATH / "stream_your_code.jsonl"
        with open(output, 'w') as f:
            for ex in examples[:500]:  # Limit
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_frida_scripts(self) -> int:
        """Learn from your Frida scripts."""
        frida_dirs = [
            Path.home() / "ReverseLab" / "frida",
            Path.home() / "ReverseLab" / "SAM" / "frida",
        ]

        examples = []
        frida_patterns = [
            ("How do I hook a function with Frida?", "Interceptor.attach"),
            ("How do I read memory with Frida?", "Memory.read"),
            ("How do I find a class in iOS?", "ObjC.classes"),
            ("How do I hook an Objective-C method?", "ObjC.classes.ClassName"),
        ]

        for frida_dir in frida_dirs:
            if not frida_dir.exists():
                continue

            for js_file in frida_dir.rglob("*.js"):
                try:
                    content = js_file.read_text()
                    if "Interceptor" in content or "ObjC" in content:
                        examples.append({
                            "instruction": f"Write a Frida script like {js_file.name}",
                            "response": f"```javascript\n{content[:2000]}\n```",
                            "category": "frida"
                        })
                except:
                    continue

        # Add pattern examples
        for q, pattern in frida_patterns:
            examples.append({
                "instruction": q,
                "response": f"Use `{pattern}` - here's an example:\n```javascript\n// Frida script\n{pattern}(...)\n```",
                "category": "frida"
            })

        output = DATA_PATH / "stream_frida.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_apple_patterns(self) -> int:
        """Generate Apple development patterns."""
        patterns = [
            # SwiftUI
            ("Create a SwiftUI view with a list", "```swift\nstruct ContentView: View {\n    var items = [\"A\", \"B\", \"C\"]\n    var body: some View {\n        List(items, id: \\.self) { item in\n            Text(item)\n        }\n    }\n}\n```"),
            ("SwiftUI navigation", "```swift\nNavigationStack {\n    List {\n        NavigationLink(\"Detail\", value: item)\n    }\n    .navigationDestination(for: Item.self) { item in\n        DetailView(item: item)\n    }\n}\n```"),
            ("SwiftUI state management", "```swift\n@State private var count = 0\n@Binding var value: String\n@StateObject var viewModel = ViewModel()\n@ObservedObject var model: Model\n@EnvironmentObject var settings: Settings\n```"),

            # Combine
            ("Combine publisher", "```swift\nlet publisher = URLSession.shared.dataTaskPublisher(for: url)\n    .map(\\.data)\n    .decode(type: Response.self, decoder: JSONDecoder())\n    .receive(on: DispatchQueue.main)\n    .sink { completion in } receiveValue: { value in }\n```"),

            # CoreML
            ("Load CoreML model", "```swift\nlet config = MLModelConfiguration()\nlet model = try MyModel(configuration: config)\nlet prediction = try model.prediction(input: input)\n```"),

            # Vision
            ("Vision text recognition", "```swift\nlet request = VNRecognizeTextRequest { request, error in\n    guard let observations = request.results as? [VNRecognizedTextObservation] else { return }\n    let text = observations.compactMap { $0.topCandidates(1).first?.string }.joined()\n}\nrequest.recognitionLevel = .accurate\n```"),

            # App lifecycle
            ("SwiftUI app entry", "```swift\n@main\nstruct MyApp: App {\n    var body: some Scene {\n        WindowGroup {\n            ContentView()\n        }\n    }\n}\n```"),

            # Async/await
            ("Swift async/await", "```swift\nfunc fetchData() async throws -> Data {\n    let (data, response) = try await URLSession.shared.data(from: url)\n    guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {\n        throw APIError.invalidResponse\n    }\n    return data\n}\n```"),

            # HomeKit
            ("HomeKit accessory", "```swift\nlet homeManager = HMHomeManager()\nhomeManager.delegate = self\nfor home in homeManager.homes {\n    for accessory in home.accessories {\n        print(accessory.name)\n    }\n}\n```"),

            # Shortcuts
            ("App Intents for Shortcuts", "```swift\nstruct MyIntent: AppIntent {\n    static var title: LocalizedStringResource = \"My Action\"\n    func perform() async throws -> some IntentResult {\n        return .result()\n    }\n}\n```"),
        ]

        examples = []
        for q, a in patterns:
            examples.append({
                "instruction": q,
                "response": a,
                "category": "apple_patterns"
            })

        output = DATA_PATH / "stream_apple_patterns.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_synthetic_swift(self) -> int:
        """Generate synthetic Swift training data."""
        examples = []

        swift_concepts = [
            ("What are Swift optionals?", "Optionals in Swift represent a value that may or may not exist. Declared with `?` (e.g., `var name: String?`). Unwrap with `if let`, `guard let`, or `!` (force unwrap). Use `??` for default values."),
            ("Explain Swift protocols", "Protocols define a blueprint of methods and properties. Classes, structs, and enums can conform to protocols. Use `protocol MyProtocol { }` and conform with `: MyProtocol`."),
            ("What's the difference between struct and class in Swift?", "Structs are value types (copied on assignment), classes are reference types (shared). Structs can't inherit. Use structs for simple data, classes for identity/inheritance."),
            ("How do closures work in Swift?", "Closures are self-contained blocks of code. Syntax: `{ (params) -> ReturnType in statements }`. Capture values from surrounding context. Use `@escaping` for async callbacks."),
            ("Explain Swift generics", "Generics let you write flexible, reusable code. Use `<T>` as placeholder: `func swap<T>(_ a: inout T, _ b: inout T)`. Constrain with `where T: Protocol`."),
            ("What's ARC in Swift?", "Automatic Reference Counting manages memory for class instances. Increments count on strong reference, decrements on release. Use `weak` or `unowned` to prevent retain cycles."),
            ("How do I handle errors in Swift?", "Use `throws` on functions, `try` to call them, `catch` to handle errors. Define errors with `enum MyError: Error`. Use `try?` for optional result, `try!` to force."),
            ("What are property wrappers?", "Property wrappers add behavior to properties. Define with `@propertyWrapper struct`. Built-in: `@State`, `@Binding`, `@Published`. Access wrapped value and projected value (`$`)."),
            ("Explain Swift actors", "Actors protect mutable state from data races. Declare with `actor`. Access properties/methods with `await`. Use `@MainActor` for UI work."),
            ("What's the Sendable protocol?", "Sendable marks types safe to share across concurrency domains. Value types are implicitly Sendable. Use `@Sendable` for closures. Required for actor boundaries."),
        ]

        for q, a in swift_concepts:
            examples.append({"instruction": q, "response": a, "category": "swift"})

        output = DATA_PATH / "stream_synthetic_swift.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _stream_synthetic_re(self) -> int:
        """Generate synthetic reverse engineering training data."""
        examples = []

        re_concepts = [
            ("How do I start reverse engineering an iOS app?", "1. Get the IPA (decrypt with frida-ios-dump if needed)\n2. Extract and examine with `unzip`\n3. Run `class-dump` on the binary\n4. Open in Hopper/IDA for disassembly\n5. Use Frida to hook at runtime"),
            ("What is method swizzling?", "Method swizzling exchanges implementations of two methods at runtime. In ObjC: `method_exchangeImplementations()`. Used to intercept/modify behavior without source code."),
            ("How do I hook a function with Frida?", "```javascript\nInterceptor.attach(ptr('0x123456'), {\n    onEnter: function(args) {\n        console.log('Called with:', args[0]);\n    },\n    onLeave: function(retval) {\n        console.log('Returned:', retval);\n    }\n});\n```"),
            ("How do I find Objective-C classes in Frida?", "```javascript\nfor (var cls in ObjC.classes) {\n    if (cls.includes('Target')) {\n        console.log(cls);\n    }\n}\n// Or: ObjC.classes.ClassName\n```"),
            ("What's a Mach-O binary?", "Mach-O is macOS/iOS executable format. Contains: header (magic, CPU type), load commands (segments, libraries), and data (code, symbols). Analyze with `otool`, `nm`, or Hopper."),
            ("How do I bypass SSL pinning?", "Use Frida scripts to hook SSL validation functions. Target `SecTrustEvaluate`, `SSL_CTX_set_verify`, or app-specific pinning. Tools: objection, ssl-kill-switch2."),
            ("What's ASLR and how to handle it?", "Address Space Layout Randomization randomizes memory addresses. In Frida, use `Module.getBaseAddress('binary')` to get the slide, then add offsets."),
            ("How do I dump decrypted iOS app?", "Use frida-ios-dump: `dump.py com.app.bundle`. Or manually: attach debugger, dump memory regions, reconstruct binary. Requires jailbreak."),
            ("What tools for static analysis?", "Hopper (disassembly, decompile), IDA Pro (industry standard), Ghidra (free, NSA), class-dump (ObjC headers), jtool2 (Mach-O analysis)."),
            ("How do I trace function calls?", "Frida: `Stalker.follow()` for instruction tracing. Or hook specific functions with Interceptor. DTrace on macOS for system-wide tracing."),
        ]

        for q, a in re_concepts:
            examples.append({"instruction": q, "response": a, "category": "reverse_engineering"})

        output = DATA_PATH / "stream_synthetic_re.jsonl"
        with open(output, 'w') as f:
            for ex in examples:
                f.write(json.dumps(ex) + '\n')

        return len(examples)

    def _merge_all_training_data(self) -> int:
        """Merge all stream outputs into one training file."""
        import hashlib

        merged_path = DATA_PATH / "parallel_merged.jsonl"
        seen = set()
        count = 0

        with open(merged_path, 'w') as out:
            for stream_file in DATA_PATH.glob("stream_*.jsonl"):
                try:
                    with open(stream_file) as f:
                        for line in f:
                            h = hashlib.md5(line.encode()).hexdigest()
                            if h not in seen:
                                out.write(line)
                                seen.add(h)
                                count += 1
                except:
                    continue

            # Also include existing training data
            existing = DATA_PATH / "merged_training.jsonl"
            if existing.exists():
                with open(existing) as f:
                    for line in f:
                        h = hashlib.md5(line.encode()).hexdigest()
                        if h not in seen:
                            out.write(line)
                            seen.add(h)
                            count += 1

        return count


def main():
    import sys

    learner = ParallelLearner(max_workers=8)

    if len(sys.argv) > 1 and sys.argv[1] == "train":
        # Run training after parallel learning
        results = learner.run_all_streams()

        print("\nStarting training with merged data...")
        merged = DATA_PATH / "parallel_merged.jsonl"
        if merged.exists():
            # Create train/valid split
            with open(merged) as f:
                lines = f.readlines()

            split = int(len(lines) * 0.9)
            with open(DATA_PATH / "train.jsonl", 'w') as f:
                f.writelines(lines[:split])
            with open(DATA_PATH / "valid.jsonl", 'w') as f:
                f.writelines(lines[split:])

            print(f"Train: {split}, Valid: {len(lines) - split}")

            # Run MLX training
            subprocess.run([
                "python3", "-m", "mlx_lm.lora",
                "--model", "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
                "--train",
                "--data", str(DATA_PATH),
                "--adapter-path", str(BRAIN_PATH / "models" / "parallel_trained"),
                "--iters", "500",
                "--batch-size", "2",
                "--num-layers", "8",
                "--save-every", "100"
            ])
    else:
        learner.run_all_streams()


if __name__ == "__main__":
    main()
