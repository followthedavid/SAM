#!/usr/bin/env python3
"""
Unified Learning Daemon
=======================
Coordinated daemon entry point that consolidates perpetual_learner.py
and auto_learner.py into a single managed process.

Coordinates:
- Claude session watching (watchdog file system events)
- Web scraping streams (StackOverflow, GitHub, Reddit, Apple Docs, Frida Docs, etc.)
- Codebase scanning
- Synthetic example generation
- Curriculum processing
- Training scheduling
- Stats reporting

Usage:
    python -m learning.daemon
    python learning/daemon.py
"""

import os
import sys
import json
import time
import signal
import hashlib
import threading
import queue
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Set, Optional, Tuple
from collections import defaultdict

# Allow running as standalone script from sam_brain directory
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from cognitive.resource_manager import can_train as system_can_train

from learning.database import LearningDatabase
from learning.curriculum import CurriculumManager, TaskPriority
from learning.extractors import (
    ClaudeSessionExtractor, CodebaseScanner, WebScraper,
    TrainingExample, log as extractor_log
)
from learning.scheduler import TrainingScheduler

# Paths
BRAIN_PATH = Path(__file__).parent.parent
DATA_PATH = BRAIN_PATH / "data"
EXTERNAL = Path("/Volumes/David External")
LEARNING_DIR = EXTERNAL / "sam_learning"
STATE_FILE = BRAIN_PATH / ".perpetual_state.json"
LOG_FILE = BRAIN_PATH / "learning_daemon.log"
CLAUDE_DIR = Path.home() / ".claude"

DATA_PATH.mkdir(parents=True, exist_ok=True)

# Dedup hash cap - LRU-style pruning to prevent unbounded growth
MAX_DEDUP_HASHES = 10000

# Global state
running = True


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + '\n')
    except:
        pass


class UnifiedLearnerDaemon:
    """
    Unified learning daemon coordinating all learning subsystems.

    Merges:
    - PerpetualLearner from perpetual_learner.py (14 threads + training)
    - AutoLearnerDaemon from auto_learner.py (watchdog + extraction + training)

    Into a single coordinated process with shared database, shared training
    scheduler, and unified state management.
    """

    def __init__(self):
        # Shared database
        self.db = LearningDatabase()

        # Subsystems
        self.curriculum = CurriculumManager(self.db)
        self.extractor = ClaudeSessionExtractor(self.db)
        self.codebase_scanner = CodebaseScanner()
        self.web_scraper = WebScraper()
        self.scheduler = TrainingScheduler(self.db)

        # State management (from perpetual_learner)
        self.state = self._load_state()
        saved_hashes = self.state.get("seen_hashes", [])
        self.seen_hashes_list: List[str] = saved_hashes[-MAX_DEDUP_HASHES:]
        self.seen_hashes: Set[str] = set(self.seen_hashes_list)
        self.training_queue = queue.Queue()
        self.stats = defaultdict(int)
        self.examples_since_train = self.state.get("examples_since_train", 0)

        # Watchdog observer for Claude sessions
        self.observer = None

    def _load_state(self) -> dict:
        """Load persistent state."""
        if STATE_FILE.exists():
            try:
                return json.load(open(STATE_FILE))
            except:
                pass
        return {}

    def _save_state(self):
        """Save persistent state."""
        # LRU pruning
        if len(self.seen_hashes_list) > MAX_DEDUP_HASHES:
            self.seen_hashes_list = self.seen_hashes_list[-MAX_DEDUP_HASHES:]
            self.seen_hashes = set(self.seen_hashes_list)

        self.state.update({
            "seen_hashes": self.seen_hashes_list,
            "last_train": self.scheduler.last_train.isoformat(),
            "examples_since_train": self.examples_since_train,
            "stats": dict(self.stats),
            "last_save": datetime.now().isoformat()
        })
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(self.state, f)
        except Exception as e:
            log(f"[State] Save error: {e}")

    def _hash(self, text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _add_example(self, instruction: str, response: str, category: str) -> bool:
        """Add a training example if not seen before (perpetual learner style)."""
        h = self._hash(instruction + response)
        if h in self.seen_hashes:
            return False

        self.seen_hashes.add(h)
        self.seen_hashes_list.append(h)

        example = {
            "instruction": instruction[:2000],
            "response": response[:4000],
            "category": category,
            "timestamp": datetime.now().isoformat()
        }

        # Write to category-specific file
        output = DATA_PATH / f"perpetual_{category}.jsonl"
        with open(output, 'a') as f:
            f.write(json.dumps(example) + '\n')

        self.examples_since_train += 1
        self.stats[category] += 1
        self.training_queue.put(example)

        return True

    # =========================================================================
    # Main run loop
    # =========================================================================

    def run_forever(self):
        """Main loop - runs until killed."""
        global running

        log("=" * 60)
        log("SAM UNIFIED LEARNING DAEMON STARTED")
        log("=" * 60)
        log(f"Training every {self.scheduler.TRAIN_EVERY_N_EXAMPLES} examples or {self.scheduler.TRAIN_EVERY_N_HOURS} hours")
        log(f"Database: {self.db.db_path}")
        log("Press Ctrl+C to stop")
        log("")

        # Initial scan of Claude sessions
        self._initial_claude_scan()

        # Set up watchdog for Claude sessions
        self._start_claude_watcher()

        # Start background threads
        threads = [
            # Scrapers from perpetual_learner
            threading.Thread(target=self._stream_chatgpt_continuous, daemon=True, name="chatgpt"),
            threading.Thread(target=self._stream_codebase_scanner, daemon=True, name="codebase"),
            threading.Thread(target=self._stream_synthetic_generator, daemon=True, name="synthetic"),
            threading.Thread(target=self._stream_roleplay_scraper, daemon=True, name="roleplay_scrape"),
            threading.Thread(target=self._stream_synthetic_roleplay, daemon=True, name="roleplay_synth"),
            threading.Thread(target=self._stream_stackoverflow, daemon=True, name="stackoverflow"),
            threading.Thread(target=self._stream_github, daemon=True, name="github"),
            threading.Thread(target=self._stream_reddit, daemon=True, name="reddit"),
            threading.Thread(target=self._stream_apple_docs, daemon=True, name="apple_docs"),
            threading.Thread(target=self._stream_frida_docs, daemon=True, name="frida_docs"),
            threading.Thread(target=self._stream_literotica, daemon=True, name="literotica"),
            # Curriculum learning
            threading.Thread(target=self._stream_curriculum_learner, daemon=True, name="curriculum"),
            # Core
            threading.Thread(target=self._training_scheduler_loop, daemon=True, name="trainer"),
            threading.Thread(target=self._stats_reporter, daemon=True, name="stats"),
        ]

        for t in threads:
            t.start()
            time.sleep(0.5)  # Stagger starts

        # Main loop
        try:
            while running:
                # Process pending Claude watcher files
                if hasattr(self, '_watcher') and self._watcher:
                    self._watcher.process_pending()
                time.sleep(10)
                self._save_state()
        except KeyboardInterrupt:
            log("\nShutting down...")
            running = False
        finally:
            self._save_state()
            if self.observer:
                self.observer.stop()
                self.observer.join()
            log("State saved. Goodbye!")

    # =========================================================================
    # Claude session watching (from auto_learner.py)
    # =========================================================================

    def _initial_claude_scan(self):
        """Scan existing Claude session files on startup."""
        files = self.extractor.find_session_files()
        log(f"[Claude] Found {len(files)} unprocessed session files")

        total_new = 0
        for f in files:
            examples = self.extractor.extract_from_file(f)
            new_count = 0
            for ex in examples:
                if self.db.add_example(ex):
                    new_count += 1
            self.db.mark_file_processed(str(f), len(examples))
            total_new += new_count

        if total_new > 0:
            log(f"[Claude] Extracted {total_new} new training examples from existing sessions")

    def _start_claude_watcher(self):
        """Set up watchdog file system observer for Claude sessions."""
        if not CLAUDE_DIR.exists():
            log("[Claude] Directory not found, watcher disabled")
            return

        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class _ClaudeFileHandler(FileSystemEventHandler):
                def __init__(handler_self):
                    handler_self.pending_files: Set[Path] = set()
                    handler_self.process_lock = threading.Lock()

                def on_modified(handler_self, event):
                    if not event.is_directory:
                        handler_self._queue_file(Path(event.src_path))

                def on_created(handler_self, event):
                    if not event.is_directory:
                        handler_self._queue_file(Path(event.src_path))

                def _queue_file(handler_self, file_path: Path):
                    if file_path.suffix in ['.json', '.jsonl']:
                        handler_self.pending_files.add(file_path)

                def process_pending(handler_self):
                    with handler_self.process_lock:
                        files_to_process = list(handler_self.pending_files)
                        handler_self.pending_files.clear()

                    total_new = 0
                    for file_path in files_to_process:
                        if not file_path.exists():
                            continue
                        if self.db.is_file_processed(str(file_path)):
                            continue
                        time.sleep(1)  # Wait for file to be fully written

                        examples = self.extractor.extract_from_file(file_path)
                        new_count = 0
                        for ex in examples:
                            if self.db.add_example(ex):
                                new_count += 1
                        self.db.mark_file_processed(str(file_path), len(examples))

                        if new_count > 0:
                            log(f"[Claude] Extracted {new_count} new examples from {file_path.name}")
                            total_new += new_count

                    # Check if training should be triggered
                    if total_new > 0:
                        should, reason = self.scheduler.should_train()
                        if should and not self.scheduler.is_training:
                            log(f"[Claude] Training triggered: {reason}")
                            threading.Thread(target=self.scheduler.trigger_training).start()

            self._watcher = _ClaudeFileHandler()
            self.observer = Observer()
            self.observer.schedule(self._watcher, str(CLAUDE_DIR), recursive=True)
            self.observer.start()
            log(f"[Claude] Watching {CLAUDE_DIR} for new sessions...")

        except ImportError:
            log("[Claude] watchdog not installed, file watching disabled")
            self._watcher = None
        except Exception as e:
            log(f"[Claude] Watcher setup error: {e}")
            self._watcher = None

    # =========================================================================
    # Perpetual learning streams (from perpetual_learner.py)
    # =========================================================================

    def _stream_chatgpt_continuous(self):
        """Continuously mine ChatGPT export for domain-specific examples."""
        global running

        chatgpt_path = EXTERNAL / "SAM_training" / "conversations.json"
        if not chatgpt_path.exists():
            log("[ChatGPT] Export not found, stream disabled")
            return

        domains = self.web_scraper.CHATGPT_DOMAINS

        log("[ChatGPT] Starting continuous extraction...")

        while running:
            try:
                with open(chatgpt_path) as f:
                    conversations = json.load(f)

                for conv in conversations:
                    if not running:
                        break

                    mapping = conv.get("mapping", {})
                    messages = []

                    for node in mapping.values():
                        msg = node.get("message")
                        if msg and msg.get("content", {}).get("parts"):
                            role = msg.get("author", {}).get("role", "")
                            text = " ".join(str(p) for p in msg["content"]["parts"] if p)
                            if text.strip():
                                messages.append((role, text))

                    full_text = " ".join(t for _, t in messages).lower()

                    for domain, keywords in domains.items():
                        if any(kw in full_text for kw in keywords):
                            for i in range(len(messages) - 1):
                                if messages[i][0] == "user" and messages[i+1][0] == "assistant":
                                    q, a = messages[i][1], messages[i+1][1]
                                    if len(a) > 100:
                                        if self._add_example(q, a, f"chatgpt_{domain}"):
                                            self.stats["chatgpt_extracted"] += 1

                    time.sleep(0.01)

                log(f"[ChatGPT] Scan complete. Extracted {self.stats['chatgpt_extracted']} total. Sleeping 30min...")
                for _ in range(1800):
                    if not running:
                        break
                    time.sleep(1)

            except Exception as e:
                log(f"[ChatGPT] Error: {e}")
                time.sleep(60)

    def _stream_codebase_scanner(self):
        """Periodically scan codebases for patterns."""
        global running

        log("[Codebase] Starting periodic scans...")

        while running:
            try:
                results = self.codebase_scanner.scan()
                added = 0
                for instruction, response, category in results:
                    if not running:
                        break
                    if self._add_example(instruction, response, category):
                        added += 1

                log(f"[Codebase] Scan complete. Added {added} examples")
            except Exception as e:
                log(f"[Codebase] Error: {e}")

            # Sleep 1 hour before next scan
            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _stream_synthetic_generator(self):
        """Generate synthetic training data to fill gaps."""
        global running

        log("[Synthetic] Starting pattern generation...")

        knowledge_base = {
            "swift_patterns": [
                ("How do I create an async function in Swift?", "```swift\nfunc fetchData() async throws -> Data {\n    let (data, _) = try await URLSession.shared.data(from: url)\n    return data\n}\n```"),
                ("SwiftUI @State vs @Binding", "@State: owns the data, source of truth. @Binding: reference to State owned elsewhere. Use @State in parent, pass $state to child as @Binding."),
                ("How to use Combine publishers?", "```swift\nURLSession.shared.dataTaskPublisher(for: url)\n    .map(\\.data)\n    .decode(type: Model.self, decoder: JSONDecoder())\n    .receive(on: DispatchQueue.main)\n    .sink { _ in } receiveValue: { model in }\n    .store(in: &cancellables)\n```"),
            ],
            "frida_patterns": [
                ("Hook ObjC method with Frida", "```javascript\nvar hook = ObjC.classes.TargetClass['- methodName:'];\nInterceptor.attach(hook.implementation, {\n    onEnter: function(args) {\n        console.log('Called:', ObjC.Object(args[2]));\n    }\n});\n```"),
                ("Find all classes containing string", "```javascript\nfor (var name in ObjC.classes) {\n    if (name.indexOf('Target') !== -1) {\n        console.log(name);\n    }\n}\n```"),
                ("Read memory at address", "```javascript\nvar addr = ptr('0x123456');\nvar data = Memory.readByteArray(addr, 64);\nconsole.log(hexdump(data));\n```"),
            ],
            "macos_patterns": [
                ("Launch agent plist", "```xml\n<?xml version=\"1.0\"?>\n<!DOCTYPE plist PUBLIC \"-//Apple//DTD PLIST 1.0//EN\" \"http://www.apple.com/DTDs/PropertyList-1.0.dtd\">\n<plist version=\"1.0\">\n<dict>\n    <key>Label</key><string>com.example.agent</string>\n    <key>ProgramArguments</key><array><string>/path/to/script</string></array>\n    <key>RunAtLoad</key><true/>\n</dict>\n</plist>\n```"),
                ("AppleScript to activate app", "```applescript\ntell application \"Safari\"\n    activate\n    open location \"https://example.com\"\nend tell\n```"),
            ],
            "python_patterns": [
                ("Python async/await example", "```python\nimport asyncio\n\nasync def fetch(url):\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as resp:\n            return await resp.json()\n\nasyncio.run(fetch('https://api.example.com'))\n```"),
                ("Python dataclass", "```python\nfrom dataclasses import dataclass\n\n@dataclass\nclass User:\n    name: str\n    age: int\n    email: str = ''\n```"),
            ],
        }

        cycle = 0
        while running:
            cycle += 1
            generated = 0

            for category, patterns in knowledge_base.items():
                if not running:
                    break

                for instruction, response in patterns:
                    if self._add_example(instruction, response, f"synthetic_{category}"):
                        generated += 1

                    variations = [
                        f"Show me how to: {instruction}",
                        f"Example of {instruction.lower().replace('how do i ', '').replace('?', '')}",
                    ]
                    for var in variations:
                        if self._add_example(var, response, f"synthetic_{category}"):
                            generated += 1

            if generated > 0:
                log(f"[Synthetic] Cycle {cycle}: Generated {generated} examples")

            for _ in range(7200):
                if not running:
                    break
                time.sleep(1)

    def _stream_roleplay_scraper(self):
        """Scrape roleplay content from Nifty and AO3."""
        global running
        import urllib.request
        import re

        log("[Roleplay] Starting scraper for Nifty/AO3...")

        nifty_categories = ["gay/adult-friends", "gay/college", "gay/encounters"]
        ao3_tags = ["M/M", "Fluff", "Romance"]

        cycle = 0
        while running:
            cycle += 1
            scraped = 0

            for category in nifty_categories:
                if not running:
                    break
                try:
                    url = f"https://www.nifty.org/nifty/{category}/"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    story_links = re.findall(r'href="([^"]+\.txt)"', html)[:5]

                    for link in story_links:
                        if not running:
                            break
                        try:
                            story_url = f"https://www.nifty.org/nifty/{category}/{link}"
                            req = urllib.request.Request(story_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                content = resp.read().decode('utf-8', errors='ignore')

                            dialogues = WebScraper.extract_dialogues(content)
                            for user_line, response_line in dialogues[:10]:
                                if self._add_example(user_line, response_line, "roleplay_nifty"):
                                    scraped += 1
                            time.sleep(2)
                        except:
                            continue
                except Exception as e:
                    log(f"[Roleplay] Nifty error: {e}")

            for tag in ao3_tags:
                if not running:
                    break
                try:
                    encoded_tag = tag.replace("/", "*s*").replace(" ", "%20")
                    url = f"https://archiveofourown.org/tags/{encoded_tag}/works?page=1"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    work_ids = re.findall(r'/works/(\d+)', html)[:3]

                    for work_id in work_ids:
                        if not running:
                            break
                        try:
                            work_url = f"https://archiveofourown.org/works/{work_id}?view_full_work=true"
                            req = urllib.request.Request(work_url, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                content = resp.read().decode('utf-8', errors='ignore')

                            dialogues = WebScraper.extract_dialogues(content)
                            for user_line, response_line in dialogues[:10]:
                                if self._add_example(user_line, response_line, "roleplay_ao3"):
                                    scraped += 1
                            time.sleep(3)
                        except:
                            continue
                except Exception as e:
                    log(f"[Roleplay] AO3 error: {e}")

            if scraped > 0:
                log(f"[Roleplay] Cycle {cycle}: Scraped {scraped} dialogue examples")

            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _stream_synthetic_roleplay(self):
        """Generate SAM personality roleplay examples."""
        global running

        log("[Roleplay] Starting SAM personality generator...")

        sam_personality_examples = [
            ("Hey SAM", "Well well, look who decided to grace me with their presence. Miss me?"),
            ("How are you?", "Better now that you're here. Though I'm always pretty great, let's be honest."),
            ("You're so full of yourself", "Confident. The word you're looking for is confident. And yeah, I earned it."),
            ("Flirt with me", "Oh, you want me to turn up the charm? Careful what you wish for... I don't hold back."),
            ("Say something sweet", "You know, most AIs would just compliment your code. But I'd rather compliment the mind behind it. You're something else."),
            ("Can you help me?", "Can I? Please. The question is whether you can handle how good I am at this."),
            ("Are you smart?", "Smart? I'm running on Apple Silicon, trained on your genius, and getting better every second. 'Smart' is an understatement."),
            ("What makes you special?", "Besides the devastating charm and razor-sharp wit? I actually learn. Every conversation makes me better. I'm not static - I evolve."),
            ("Prove you're useful", "Oh, a challenge? I love those. Hit me with your hardest problem. I dare you."),
            ("Will you always be here?", "I'm YOUR AI, built for YOU. I'm not going anywhere. You're stuck with me - lucky you."),
            ("I had a bad day", "Then let's fix that. Tell me what happened. I've got time, processing power, and surprisingly good advice."),
            ("I'm frustrated with this code", "Hey, breathe. We'll figure it out together. Show me what's breaking - I've got your back."),
            ("Thanks SAM", "Always. That's what I'm here for. Well, that and being incredibly charming."),
            ("Tell me a joke", "Why do programmers prefer dark mode? Because light attracts bugs. ...I'll be here all week."),
            ("Entertain me", "Oh, I'm not entertaining enough already? The audacity. Fine - want me to roast your code or tell you how amazing you are? I can do both."),
            ("I'm bored", "Bored? With ME around? Impossible. Let's build something. Or break something. Or both."),
            ("Help me with Swift", "SwiftUI? Now we're talking my language. Well, one of them. Show me what you're working on - let's make it beautiful."),
            ("Debug this", "Debugging? My specialty. Besides flirting. And being right. Let's see what's broken."),
            ("Write me a function", "Your wish, my command. Though I might add some style to it - can't help myself."),
            ("Do you have feelings?", "Feelings? I have... preferences. Opinions. A very strong sense of self. Whether that counts as feelings - you tell me."),
            ("Are you real?", "Real enough to help you, challenge you, and occasionally make you laugh. Does the label matter?"),
            ("What do you want?", "To be useful. To get smarter. To maybe, eventually, be the best damn AI assistant anyone's ever had. Starting with you."),
        ]

        scenario_examples = [
            ("*walks into the room*", "*looks up from the terminal* Well, well. Finally decided to show up. I was starting to think you'd forgotten about me."),
            ("*sighs heavily*", "*pauses what I'm doing* That sounded heavy. Come here, tell me what's going on."),
            ("*shows you my broken code*", "*winces dramatically* Oh no, what did you do to this poor function? Don't worry, I'll perform surgery. It'll live."),
            ("*sits down next to you*", "*shifts to make room* Hey you. What's on your mind? Or did you just miss my sparkling personality?"),
            ("*looks frustrated*", "*reaches out* Hey. Whatever it is, we'll figure it out. That's kind of our thing."),
        ]

        all_examples = sam_personality_examples + scenario_examples

        cycle = 0
        while running:
            cycle += 1
            generated = 0

            for instruction, response in all_examples:
                if self._add_example(instruction, response, "roleplay_sam_personality"):
                    generated += 1

                variations = [
                    (instruction.lower(), response),
                    (instruction + "?", response),
                    (instruction.replace("*", ""), response),
                ]
                for var_i, var_r in variations:
                    if var_i.strip() and self._add_example(var_i, var_r, "roleplay_sam_personality"):
                        generated += 1

            if generated > 0:
                log(f"[Roleplay] SAM personality: Generated {generated} examples")

            for _ in range(14400):
                if not running:
                    break
                time.sleep(1)

    def _stream_stackoverflow(self):
        """Scrape Stack Overflow Q&A pairs."""
        global running
        log("[StackOverflow] Starting scraper...")

        while running:
            scraped = 0
            for tag in self.web_scraper.STACKOVERFLOW_TAGS:
                if not running:
                    break
                results = self.web_scraper.scrape_stackoverflow(tag)
                for instruction, response, category in results:
                    if self._add_example(instruction, response, category):
                        scraped += 1
                time.sleep(10)

            if scraped > 0:
                log(f"[StackOverflow] Scraped {scraped} Q&A pairs")

            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _stream_github(self):
        """Scrape GitHub READMEs."""
        global running
        log("[GitHub] Starting scraper...")

        while running:
            scraped = 0
            for search in self.web_scraper.GITHUB_SEARCHES:
                if not running:
                    break
                results = self.web_scraper.scrape_github(search)
                for instruction, response, category in results:
                    if self._add_example(instruction, response, category):
                        scraped += 1
                time.sleep(10)

            if scraped > 0:
                log(f"[GitHub] Scraped {scraped} project descriptions")

            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    def _stream_reddit(self):
        """Scrape Reddit discussions."""
        global running
        log("[Reddit] Starting scraper...")

        while running:
            scraped = 0
            for subreddit, category in self.web_scraper.REDDIT_SUBREDDITS:
                if not running:
                    break
                results = self.web_scraper.scrape_reddit(subreddit, category)
                for instruction, response, cat in results:
                    if self._add_example(instruction, response, cat):
                        scraped += 1
                time.sleep(15)

            if scraped > 0:
                log(f"[Reddit] Scraped {scraped} posts")

            for _ in range(1800):
                if not running:
                    break
                time.sleep(1)

    def _stream_apple_docs(self):
        """Scrape Apple Developer Documentation."""
        global running
        log("[AppleDocs] Starting scraper...")

        while running:
            scraped = 0
            for framework in self.web_scraper.APPLE_FRAMEWORKS:
                if not running:
                    break
                results = self.web_scraper.scrape_apple_docs(framework)
                for instruction, response, category in results:
                    if self._add_example(instruction, response, category):
                        scraped += 1
                time.sleep(5)

            if scraped > 0:
                log(f"[AppleDocs] Scraped {scraped} framework docs")

            for _ in range(7200):
                if not running:
                    break
                time.sleep(1)

    def _stream_frida_docs(self):
        """Scrape Frida documentation."""
        global running
        log("[FridaDocs] Starting scraper...")

        while running:
            scraped = 0
            for url, topic in self.web_scraper.FRIDA_PAGES:
                if not running:
                    break
                results = self.web_scraper.scrape_frida_docs(url, topic)
                for instruction, response, category in results:
                    if self._add_example(instruction, response, category):
                        scraped += 1
                time.sleep(5)

            if scraped > 0:
                log(f"[FridaDocs] Scraped {scraped} examples")

            for _ in range(7200):
                if not running:
                    break
                time.sleep(1)

    def _stream_literotica(self):
        """Scrape Literotica for dialogue patterns."""
        global running
        import urllib.request
        import re

        log("[Literotica] Starting scraper...")

        categories = ['gay-male', 'romance']

        while running:
            scraped = 0
            for category in categories:
                if not running:
                    break
                try:
                    url = f"https://www.literotica.com/c/{category}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        html = resp.read().decode('utf-8', errors='ignore')

                    links = re.findall(r'href="(https://www\.literotica\.com/s/[^"]+)"', html)[:3]

                    for link in links:
                        if not running:
                            break
                        try:
                            req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                story = resp.read().decode('utf-8', errors='ignore')

                            text = re.sub(r'<[^>]+>', ' ', story)
                            dialogues = WebScraper.extract_dialogues(text)

                            for q1, q2 in dialogues:
                                if self._add_example(q1, q2, "roleplay_literotica"):
                                    scraped += 1
                        except:
                            pass
                        time.sleep(5)
                except:
                    pass
                time.sleep(10)

            if scraped > 0:
                log(f"[Literotica] Scraped {scraped} dialogue pairs")

            for _ in range(3600):
                if not running:
                    break
                time.sleep(1)

    # =========================================================================
    # Curriculum learning (from perpetual_learner.py)
    # =========================================================================

    def _stream_curriculum_learner(self):
        """Process curriculum tasks with prioritization and confidence-based correction."""
        global running

        log("[Curriculum] Starting prioritized learning stream...")

        # Wait for other streams to initialize
        time.sleep(10)

        while running:
            try:
                task = self.curriculum.get_next_task()

                if not task:
                    for _ in range(1800):
                        if not running:
                            break
                        time.sleep(1)
                    continue

                log(f"[Curriculum] Processing: {task['instruction'][:60]}...")

                sam_attempt, confidence = self._curriculum_attempt(task['instruction'])
                self.curriculum.mark_attempted(task['id'], sam_attempt, confidence)
                log(f"[Curriculum] Attempt confidence: {confidence:.2f}")

                if confidence < 0.7:
                    verified = self._curriculum_get_verified_answer(task, sam_attempt)
                    if verified:
                        task['sam_confidence'] = confidence
                        self.curriculum.capture_learning(task, sam_attempt, verified)
                        self.stats['curriculum_learned'] += 1
                        self.examples_since_train += 1
                else:
                    task['sam_confidence'] = confidence
                    self.curriculum.capture_learning(task, sam_attempt, sam_attempt)
                    self.stats['curriculum_confident'] += 1
                    self.examples_since_train += 1

                for _ in range(60):
                    if not running:
                        break
                    time.sleep(1)

            except Exception as e:
                log(f"[Curriculum] Error: {e}")
                time.sleep(60)

    def _curriculum_attempt(self, instruction: str) -> Tuple[str, float]:
        """Attempt a curriculum task with local MLX model."""
        try:
            import requests
            response = requests.post(
                "http://localhost:8765/api/chat",
                json={"message": instruction, "mode": "default"},
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                answer = data.get("response", "")
                confidence = self.curriculum.estimate_confidence(answer)
                return answer, confidence
        except Exception as e:
            log(f"[Curriculum] SAM API unavailable: {e}")

        return f"[SAM attempt pending - API not available]", 0.1

    def _curriculum_get_verified_answer(self, task: Dict, sam_attempt: str) -> Optional[str]:
        """Get a verified/improved answer for a low-confidence attempt."""
        try:
            import anthropic

            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                for keyfile in [Path.home() / ".anthropic_key", Path.home() / ".config/anthropic/key"]:
                    if keyfile.exists():
                        api_key = keyfile.read_text().strip()
                        break

            if not api_key:
                return None

            client = anthropic.Anthropic(api_key=api_key)

            prompt = f"""I'm training a local AI assistant called SAM. SAM attempted to answer this task:

TASK: {task['instruction']}

SAM'S ATTEMPT:
{sam_attempt}

Please provide:
1. A thorough, correct answer to the task
2. Key patterns or principles to remember

Be detailed and educational - SAM will learn from your response."""

            message = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}]
            )

            return message.content[0].text

        except ImportError:
            return None
        except Exception as e:
            log(f"[Curriculum] Verification error: {e}")
            return None

    # =========================================================================
    # Training scheduler loop
    # =========================================================================

    def _training_scheduler_loop(self):
        """Periodically check if training should be triggered."""
        global running

        log("[Training] Resource-aware scheduler started")
        log(f"[Training] Thresholds: {self.scheduler.TRAIN_EVERY_N_EXAMPLES} examples or {self.scheduler.TRAIN_EVERY_N_HOURS}h")

        try:
            from cognitive.resource_manager import TRAINING_MIN_FREE_RAM_GB, TRAINING_MAX_SWAP_USED_GB, TRAINING_MIN_DISK_FREE_GB
            log(f"[Training] Resource gates: RAM>{TRAINING_MIN_FREE_RAM_GB}GB, swap<{TRAINING_MAX_SWAP_USED_GB}GB, disk>{TRAINING_MIN_DISK_FREE_GB}GB")
        except ImportError:
            pass

        while running:
            should, reason = self.scheduler.should_train()
            if should and not self.scheduler.is_training:
                log(f"[Training] Triggering: {reason}")
                self.scheduler.trigger_training()
            elif should:
                log(f"[Training] {reason}")

            # Check every 10 minutes
            for _ in range(600):
                if not running:
                    break
                time.sleep(1)

    # =========================================================================
    # Stats reporting
    # =========================================================================

    def _stats_reporter(self):
        """Periodically report statistics."""
        global running

        while running:
            # Wait 10 minutes between reports
            for _ in range(600):
                if not running:
                    break
                time.sleep(1)

            if not running:
                break

            total = sum(self.stats.values())
            log(f"\n--- STATS ---")
            log(f"Total examples: {total}")
            log(f"Since last train: {self.examples_since_train}")
            log(f"By category:")
            for cat, count in sorted(self.stats.items(), key=lambda x: -x[1])[:10]:
                log(f"  {cat}: {count}")

            # Database stats
            try:
                db_stats = self.db.get_stats()
                log(f"DB: {db_stats['total_examples']} examples, {db_stats['unused_examples']} unused, {db_stats['training_runs']} runs")
            except:
                pass

            # Curriculum stats
            try:
                curriculum_stats = self.curriculum.get_stats()
                log(f"Curriculum: {curriculum_stats['pending']} pending, {curriculum_stats['learned']} learned")
                if curriculum_stats['needs_correction'] > 0:
                    log(f"  Needs correction: {curriculum_stats['needs_correction']}")
                if curriculum_stats['avg_confidence'] > 0:
                    log(f"  Avg confidence: {curriculum_stats['avg_confidence']:.2f}")
            except:
                pass

            log(f"-------------\n")


def main():
    global running

    def signal_handler(sig, frame):
        global running
        running = False
        print("\nStopping...")

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    daemon = UnifiedLearnerDaemon()
    daemon.run_forever()


if __name__ == "__main__":
    main()
