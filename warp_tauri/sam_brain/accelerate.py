#!/usr/bin/env python3
"""
SAM Accelerator - Light Speed Development
=========================================
Parallelizes everything to rapidly bootstrap SAM's capabilities.

Strategy:
1. Generate synthetic training data for missing capabilities
2. Batch process ALL available data sources in parallel
3. Wire tools directly to MLX inference
4. Create action loops where SAM executes, not just talks
5. Bootstrap from Claude's responses in real-time
"""

import json
import os
import subprocess
import sys
import asyncio
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import threading
import queue
import hashlib

# Paths
BRAIN_PATH = Path(__file__).parent
DATA_PATH = BRAIN_PATH / "data"
MODELS_PATH = BRAIN_PATH / "models"
EXTERNAL_PATH = Path("/Volumes/David External/SAM_training")

DATA_PATH.mkdir(parents=True, exist_ok=True)


class SyntheticDataGenerator:
    """Generate training data for capabilities SAM doesn't have yet."""

    # Templates for each capability type
    CAPABILITY_TEMPLATES = {
        "code_generation": [
            ("Write a Python function to {task}", "```python\n{code}\n```"),
            ("Create a {lang} class that {task}", "```{lang}\n{code}\n```"),
            ("Implement {algorithm} in {lang}", "```{lang}\n{code}\n```"),
        ],
        "code_review": [
            ("Review this code:\n```\n{code}\n```", "Issues found:\n{issues}\n\nSuggestions:\n{suggestions}"),
            ("What's wrong with this?\n{code}", "The problem is {problem}. Fix:\n{fix}"),
        ],
        "error_analysis": [
            ("Error: {error}\nCode: {code}", "This error means {explanation}. Fix by {fix}"),
            ("Why am I getting {error}?", "This happens because {cause}. Solution: {solution}"),
        ],
        "architecture_design": [
            ("Design a system for {task}", "Architecture:\n{architecture}\n\nComponents:\n{components}"),
            ("How should I structure {project}?", "Recommended structure:\n{structure}"),
        ],
        "debugging": [
            ("Debug: {symptom}\nCode: {code}", "Root cause: {cause}\nFix: {fix}"),
            ("Why doesn't {code} work?", "The issue is {issue}. Here's the fix:\n{fix}"),
        ],
        "multi_file_refactor": [
            ("Refactor {files} to {goal}", "Changes needed:\n{changes}"),
            ("How to extract {component} from {file}?", "Steps:\n{steps}"),
        ],
        "complex_reasoning": [
            ("Explain why {concept}", "The reason is {explanation}"),
            ("Compare {a} vs {b} for {use_case}", "{a} is better for {reason_a}. {b} is better for {reason_b}."),
        ],
        "math_reasoning": [
            ("Solve: {problem}", "Solution:\n{steps}\nAnswer: {answer}"),
            ("Calculate {expression}", "= {result}"),
        ],
        "creative_writing": [
            ("Write a {type} about {topic}", "{content}"),
            ("Create a {format} for {purpose}", "{content}"),
        ],
    }

    # Code snippets for synthetic generation
    CODE_SNIPPETS = {
        "python": [
            ("sort a list", "def sort_list(lst):\n    return sorted(lst)"),
            ("read a file", "def read_file(path):\n    with open(path) as f:\n        return f.read()"),
            ("http request", "import requests\ndef fetch(url):\n    return requests.get(url).json()"),
            ("parse json", "import json\ndef parse(data):\n    return json.loads(data)"),
            ("async function", "async def fetch_data(url):\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as resp:\n            return await resp.json()"),
        ],
        "javascript": [
            ("fetch data", "async function fetchData(url) {\n  const res = await fetch(url);\n  return res.json();\n}"),
            ("event listener", "element.addEventListener('click', (e) => {\n  console.log('clicked');\n});"),
            ("array map", "const doubled = arr.map(x => x * 2);"),
        ],
        "swift": [
            ("struct definition", "struct User {\n    let name: String\n    let age: Int\n}"),
            ("async function", "func fetchData() async throws -> Data {\n    let (data, _) = try await URLSession.shared.data(from: url)\n    return data\n}"),
        ],
        "rust": [
            ("struct with impl", "struct Counter {\n    count: i32,\n}\n\nimpl Counter {\n    fn new() -> Self {\n        Counter { count: 0 }\n    }\n    fn increment(&mut self) {\n        self.count += 1;\n    }\n}"),
        ],
    }

    ERRORS = [
        ("TypeError: 'NoneType' object is not subscriptable", "variable is None", "add null check"),
        ("IndexError: list index out of range", "accessing index beyond list length", "check list length first"),
        ("KeyError: 'key'", "dictionary doesn't have that key", "use .get() with default"),
        ("ModuleNotFoundError: No module named 'x'", "package not installed", "pip install x"),
        ("SyntaxError: invalid syntax", "typo or missing bracket", "check syntax near the error line"),
    ]

    def generate_batch(self, capability: str, count: int = 100) -> List[Dict]:
        """Generate synthetic training examples for a capability."""
        examples = []
        templates = self.CAPABILITY_TEMPLATES.get(capability, [])

        if not templates:
            return examples

        if capability == "code_generation":
            examples.extend(self._generate_code_examples(count))
        elif capability == "error_analysis":
            examples.extend(self._generate_error_examples(count))
        elif capability in ["debugging", "code_review"]:
            examples.extend(self._generate_debug_examples(count))
        else:
            examples.extend(self._generate_generic_examples(capability, count))

        return examples

    def _generate_code_examples(self, count: int) -> List[Dict]:
        """Generate code generation examples."""
        examples = []
        for lang, snippets in self.CODE_SNIPPETS.items():
            for task, code in snippets:
                examples.append({
                    "instruction": f"Write {lang} code to {task}",
                    "response": f"```{lang}\n{code}\n```",
                    "category": "code_generation"
                })
                # Variations
                examples.append({
                    "instruction": f"How do I {task} in {lang}?",
                    "response": f"Here's how to {task} in {lang}:\n\n```{lang}\n{code}\n```",
                    "category": "code_generation"
                })
        return examples[:count]

    def _generate_error_examples(self, count: int) -> List[Dict]:
        """Generate error analysis examples."""
        examples = []
        for error, cause, fix in self.ERRORS:
            examples.append({
                "instruction": f"I'm getting this error: {error}",
                "response": f"This error occurs because {cause}. To fix it, {fix}.",
                "category": "error_analysis"
            })
            examples.append({
                "instruction": f"What does '{error}' mean?",
                "response": f"This error means {cause}. The solution is to {fix}.",
                "category": "error_analysis"
            })
        return examples[:count]

    def _generate_debug_examples(self, count: int) -> List[Dict]:
        """Generate debugging examples."""
        examples = []
        debug_scenarios = [
            ("function returns None", "missing return statement", "add return statement"),
            ("infinite loop", "loop condition never becomes false", "add break condition or fix loop variable"),
            ("memory leak", "objects not being freed", "ensure resources are released"),
            ("slow performance", "inefficient algorithm or I/O", "optimize the bottleneck"),
            ("race condition", "unsynchronized shared state", "add proper locking"),
        ]
        for symptom, cause, fix in debug_scenarios:
            examples.append({
                "instruction": f"My code has {symptom}. How do I fix it?",
                "response": f"This is likely caused by {cause}. To fix it, {fix}.",
                "category": "debugging"
            })
        return examples[:count]

    def _generate_generic_examples(self, capability: str, count: int) -> List[Dict]:
        """Generate generic examples for other capabilities."""
        examples = []
        # Add some general patterns
        patterns = {
            "complex_reasoning": [
                ("Explain the trade-offs between X and Y", "X offers A while Y provides B. Choose X when C, choose Y when D."),
                ("Why would I use X instead of Y?", "X is better when you need A. Y is better for B."),
            ],
            "architecture_design": [
                ("How should I structure a web app?", "Use a layered architecture: presentation, business logic, data access."),
                ("Design a microservices system", "Split by domain boundaries. Use API gateway. Implement service discovery."),
            ],
        }
        for q, a in patterns.get(capability, []):
            examples.append({
                "instruction": q,
                "response": a,
                "category": capability
            })
        return examples[:count]


class DataSourceProcessor:
    """Process all available data sources in parallel."""

    def __init__(self):
        self.sources = []
        self._discover_sources()

    def _discover_sources(self):
        """Find all available data sources."""
        # Claude Code history
        claude_history = Path.home() / ".claude"
        if claude_history.exists():
            self.sources.append(("claude_history", claude_history))

        # ChatGPT export (already processed, but check for new)
        chatgpt_path = EXTERNAL_PATH / "conversations.json"
        if chatgpt_path.exists():
            self.sources.append(("chatgpt_export", chatgpt_path))

        # Any JSONL training files
        for jsonl in DATA_PATH.glob("*.jsonl"):
            self.sources.append(("training_file", jsonl))

        # Project documentation
        ssot_path = Path("/Volumes/Plex/SSOT")
        if ssot_path.exists():
            self.sources.append(("documentation", ssot_path))

    def process_all_parallel(self, max_workers: int = 4) -> Dict[str, int]:
        """Process all sources in parallel."""
        results = {}

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for source_type, source_path in self.sources:
                future = executor.submit(self._process_source, source_type, source_path)
                futures[future] = (source_type, source_path)

            for future in concurrent.futures.as_completed(futures):
                source_type, source_path = futures[future]
                try:
                    count = future.result()
                    results[f"{source_type}:{source_path.name}"] = count
                except Exception as e:
                    results[f"{source_type}:{source_path.name}"] = f"error: {e}"

        return results

    def _process_source(self, source_type: str, source_path: Path) -> int:
        """Process a single source."""
        if source_type == "claude_history":
            return self._process_claude_history(source_path)
        elif source_type == "chatgpt_export":
            return self._process_chatgpt(source_path)
        elif source_type == "documentation":
            return self._process_docs(source_path)
        elif source_type == "training_file":
            return self._count_jsonl(source_path)
        return 0

    def _process_claude_history(self, path: Path) -> int:
        """Extract training from Claude history."""
        count = 0
        for jsonl_file in path.rglob("*.jsonl"):
            try:
                with open(jsonl_file) as f:
                    for line in f:
                        if line.strip():
                            count += 1
            except:
                pass
        return count

    def _process_chatgpt(self, path: Path) -> int:
        """Count ChatGPT conversations."""
        try:
            with open(path) as f:
                data = json.load(f)
            return len(data) if isinstance(data, list) else 0
        except:
            return 0

    def _process_docs(self, path: Path) -> int:
        """Extract from documentation."""
        count = 0
        for md_file in path.rglob("*.md"):
            count += 1
        return count

    def _count_jsonl(self, path: Path) -> int:
        """Count lines in JSONL."""
        try:
            with open(path) as f:
                return sum(1 for _ in f)
        except:
            return 0


class ActionLoop:
    """Wire SAM's inference to actual tool execution."""

    def __init__(self):
        self.tool_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.running = False

    def start(self):
        """Start the action loop."""
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def stop(self):
        """Stop the action loop."""
        self.running = False

    def _worker(self):
        """Process tool executions."""
        while self.running:
            try:
                tool_name, params = self.tool_queue.get(timeout=1)
                result = self._execute_tool(tool_name, params)
                self.result_queue.put((tool_name, result))
            except queue.Empty:
                continue

    def _execute_tool(self, tool_name: str, params: Dict) -> Dict:
        """Execute a tool and return result."""
        tools = {
            "read": self._tool_read,
            "write": self._tool_write,
            "bash": self._tool_bash,
            "glob": self._tool_glob,
            "grep": self._tool_grep,
        }
        handler = tools.get(tool_name)
        if handler:
            return handler(params)
        return {"error": f"Unknown tool: {tool_name}"}

    def _tool_read(self, params: Dict) -> Dict:
        path = params.get("file_path", "")
        try:
            with open(path) as f:
                content = f.read()
            return {"success": True, "content": content[:10000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_write(self, params: Dict) -> Dict:
        path = params.get("file_path", "")
        content = params.get("content", "")
        try:
            with open(path, 'w') as f:
                f.write(content)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_bash(self, params: Dict) -> Dict:
        cmd = params.get("command", "")
        # Safety check
        dangerous = ["rm -rf", "sudo", "> /dev", "mkfs", "dd if="]
        if any(d in cmd for d in dangerous):
            return {"success": False, "error": "Dangerous command blocked"}
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            return {"success": True, "stdout": result.stdout[:5000], "stderr": result.stderr[:1000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_glob(self, params: Dict) -> Dict:
        pattern = params.get("pattern", "*")
        path = Path(params.get("path", "."))
        try:
            matches = list(path.glob(pattern))[:100]
            return {"success": True, "matches": [str(m) for m in matches]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _tool_grep(self, params: Dict) -> Dict:
        pattern = params.get("pattern", "")
        path = params.get("path", ".")
        try:
            result = subprocess.run(
                ["grep", "-r", "-l", pattern, path],
                capture_output=True, text=True, timeout=30
            )
            return {"success": True, "matches": result.stdout.strip().split("\n")[:50]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def queue_action(self, tool_name: str, params: Dict):
        """Queue a tool for execution."""
        self.tool_queue.put((tool_name, params))

    def get_results(self) -> List[tuple]:
        """Get all available results."""
        results = []
        while not self.result_queue.empty():
            results.append(self.result_queue.get_nowait())
        return results


class Accelerator:
    """Main accelerator that ties everything together."""

    def __init__(self):
        self.synthetic_gen = SyntheticDataGenerator()
        self.data_processor = DataSourceProcessor()
        self.action_loop = ActionLoop()

    def run_full_acceleration(self) -> Dict[str, Any]:
        """Run all acceleration strategies in parallel."""
        print("\n" + "=" * 60)
        print("SAM ACCELERATOR - LIGHT SPEED MODE")
        print("=" * 60)

        results = {
            "timestamp": datetime.now().isoformat(),
            "synthetic_data": {},
            "data_sources": {},
            "training_ready": False
        }

        # 1. Generate synthetic data for missing capabilities
        print("\n[1/4] Generating synthetic training data...")
        missing_caps = [
            "code_generation", "code_review", "error_analysis",
            "architecture_design", "debugging", "complex_reasoning",
            "math_reasoning", "creative_writing"
        ]

        all_synthetic = []
        for cap in missing_caps:
            examples = self.synthetic_gen.generate_batch(cap, 50)
            all_synthetic.extend(examples)
            results["synthetic_data"][cap] = len(examples)
            print(f"  {cap}: {len(examples)} examples")

        # Save synthetic data
        synthetic_path = DATA_PATH / "synthetic_training.jsonl"
        with open(synthetic_path, 'w') as f:
            for ex in all_synthetic:
                f.write(json.dumps(ex) + '\n')
        print(f"  Saved to {synthetic_path}")

        # 2. Process all data sources
        print("\n[2/4] Processing all data sources in parallel...")
        results["data_sources"] = self.data_processor.process_all_parallel()
        for source, count in results["data_sources"].items():
            print(f"  {source}: {count}")

        # 3. Merge all training data
        print("\n[3/4] Merging all training data...")
        merged_count = self._merge_training_data()
        print(f"  Total merged examples: {merged_count}")

        # 4. Prepare for training
        print("\n[4/4] Preparing training configuration...")
        config = self._prepare_training_config(merged_count)
        print(f"  Config saved to {config}")

        results["total_examples"] = merged_count
        results["training_ready"] = merged_count > 100

        # Summary
        print("\n" + "=" * 60)
        print("ACCELERATION COMPLETE")
        print("=" * 60)
        print(f"Total training examples: {merged_count}")
        print(f"Synthetic examples: {len(all_synthetic)}")
        print(f"Data sources processed: {len(results['data_sources'])}")

        if results["training_ready"]:
            print("\nReady to train! Run:")
            print("  python3 accelerate.py train")
        else:
            print("\nNeed more data before training.")

        return results

    def _merge_training_data(self) -> int:
        """Merge all training data into one file."""
        merged_path = DATA_PATH / "merged_training.jsonl"
        seen_hashes = set()
        count = 0

        with open(merged_path, 'w') as out:
            # Synthetic data
            synthetic_path = DATA_PATH / "synthetic_training.jsonl"
            if synthetic_path.exists():
                with open(synthetic_path) as f:
                    for line in f:
                        h = hashlib.md5(line.encode()).hexdigest()
                        if h not in seen_hashes:
                            out.write(line)
                            seen_hashes.add(h)
                            count += 1

            # ChatGPT processed data
            chatgpt_train = EXTERNAL_PATH / "processed" / "train.jsonl"
            if chatgpt_train.exists():
                with open(chatgpt_train) as f:
                    for line in f:
                        h = hashlib.md5(line.encode()).hexdigest()
                        if h not in seen_hashes:
                            out.write(line)
                            seen_hashes.add(h)
                            count += 1

            # Any other training files
            for jsonl in DATA_PATH.glob("*_training.jsonl"):
                if jsonl.name not in ["synthetic_training.jsonl", "merged_training.jsonl"]:
                    with open(jsonl) as f:
                        for line in f:
                            h = hashlib.md5(line.encode()).hexdigest()
                            if h not in seen_hashes:
                                out.write(line)
                                seen_hashes.add(h)
                                count += 1

        return count

    def _prepare_training_config(self, example_count: int) -> Path:
        """Create training configuration."""
        config = {
            "base_model": "mlx-community/Qwen2.5-Coder-1.5B-Instruct-4bit",
            "train_data": str(DATA_PATH / "merged_training.jsonl"),
            "output_dir": str(MODELS_PATH / "accelerated"),
            "iterations": min(600, example_count // 10),
            "batch_size": 2,
            "learning_rate": 1e-5,
            "lora_layers": 8,
            "save_every": 100,
            "timestamp": datetime.now().isoformat()
        }

        config_path = DATA_PATH / "training_config.json"
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)

        return config_path

    def run_training(self):
        """Execute the training with merged data."""
        config_path = DATA_PATH / "training_config.json"
        if not config_path.exists():
            print("No config found. Run acceleration first.")
            return

        with open(config_path) as f:
            config = json.load(f)

        print("\n" + "=" * 60)
        print("STARTING ACCELERATED TRAINING")
        print("=" * 60)
        print(f"Data: {config['train_data']}")
        print(f"Iterations: {config['iterations']}")
        print(f"Output: {config['output_dir']}")

        # Create output dir
        output_dir = Path(config['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run MLX training
        cmd = [
            "python3", "-m", "mlx_lm.lora",
            "--model", config["base_model"],
            "--train",
            "--data", str(DATA_PATH),
            "--adapter-path", str(output_dir),
            "--iters", str(config["iterations"]),
            "--batch-size", str(config["batch_size"]),
            "--learning-rate", str(config["learning_rate"]),
            "--num-layers", str(config["lora_layers"]),
            "--save-every", str(config["save_every"])
        ]

        print(f"\nRunning: {' '.join(cmd)}")
        subprocess.run(cmd)

    def bootstrap_from_claude(self, request: str) -> Dict:
        """
        Send a request to Claude and capture the response for training.
        This creates real-time training data from Claude's superior responses.
        """
        # This would integrate with Claude Code terminal
        # For now, return a placeholder
        return {
            "status": "would_capture",
            "request": request,
            "note": "Integrate with claude terminal for real-time bootstrapping"
        }


def main():
    accelerator = Accelerator()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "full":
            accelerator.run_full_acceleration()

        elif command == "train":
            accelerator.run_training()

        elif command == "synthetic":
            print("Generating synthetic data only...")
            gen = SyntheticDataGenerator()
            for cap in ["code_generation", "debugging", "error_analysis"]:
                examples = gen.generate_batch(cap, 100)
                print(f"  {cap}: {len(examples)}")

        elif command == "sources":
            print("Processing data sources...")
            processor = DataSourceProcessor()
            results = processor.process_all_parallel()
            for source, count in results.items():
                print(f"  {source}: {count}")

        else:
            print(f"Unknown command: {command}")
            print("Commands: full, train, synthetic, sources")
    else:
        # Default: run full acceleration
        accelerator.run_full_acceleration()


if __name__ == "__main__":
    main()
