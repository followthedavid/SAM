"""
Training Data Extractors
========================
Combines extraction logic from auto_learner.py and perpetual_learner.py.

Provides:
- TrainingExample: Dataclass for extracted training pairs
- ClaudeSessionExtractor: Extracts from ~/.claude/ session files
- CodebaseScanner: Wraps perpetual_learner's codebase scanning logic
- WebScraper: Thin wrapper interface for web scraping streams
"""

import re
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

# Paths
BRAIN_PATH = Path(__file__).parent.parent
DATA_PATH = BRAIN_PATH / "data"
CLAUDE_DIR = Path.home() / ".claude"
EXTERNAL = Path("/Volumes/David External")

# Quality thresholds
MIN_RESPONSE_LENGTH = 100
MIN_QUALITY_SCORE = 0.5


def log(msg: str):
    """Log with timestamp."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)


@dataclass
class TrainingExample:
    """A training example extracted from Claude."""
    id: str
    user_input: str
    claude_response: str
    category: str
    quality_score: float
    source_file: str
    extracted_at: str
    used_in_training: bool = False


class ClaudeSessionExtractor:
    """
    Extract training data from Claude Code sessions.

    Extracted from auto_learner.py ClaudeSessionExtractor class.
    Modified to accept a LearningDatabase instance.
    """

    def __init__(self, db):
        """
        Args:
            db: A LearningDatabase instance
        """
        self.db = db

    def find_session_files(self) -> List[Path]:
        """Find all Claude session files."""
        files = []

        # Main history file - THIS IS THE KEY ONE
        history_file = CLAUDE_DIR / "history.jsonl"
        if history_file.exists():
            files.append(history_file)

        # Check projects directory
        projects_dir = CLAUDE_DIR / "projects"
        if projects_dir.exists():
            # Look for conversation JSON and JSONL files
            for project in projects_dir.iterdir():
                if project.is_dir():
                    for f in project.glob("**/*.json"):
                        files.append(f)
                    for f in project.glob("**/*.jsonl"):
                        files.append(f)

        # Check for other JSONL conversation logs
        for f in CLAUDE_DIR.glob("*.jsonl"):
            if f.name != "history.jsonl":  # Already added
                files.append(f)

        # Filter to unprocessed - but always reprocess history.jsonl
        # since it grows over time
        return [f for f in files if f.name == "history.jsonl" or
                not self.db.is_file_processed(str(f))]

    def extract_from_file(self, file_path: Path) -> List[TrainingExample]:
        """Extract training examples from a session file."""
        examples = []

        try:
            if file_path.suffix == '.jsonl':
                examples = self._extract_from_jsonl(file_path)
            else:
                examples = self._extract_from_json(file_path)
        except Exception as e:
            log(f"[Extractor] Error extracting from {file_path}: {e}")

        return examples

    def _extract_from_jsonl(self, file_path: Path) -> List[TrainingExample]:
        """Extract from JSONL format."""
        examples = []

        # Special handling for Claude Code history.jsonl
        if file_path.name == "history.jsonl":
            return self._extract_from_claude_history(file_path)

        current_user_msg = None

        for line in open(file_path):
            try:
                msg = json.loads(line)
                role = msg.get("role", "")
                content = self._get_content(msg)

                if role == "user":
                    current_user_msg = content
                elif role == "assistant" and current_user_msg:
                    example = self._create_example(
                        current_user_msg, content, str(file_path)
                    )
                    if example:
                        examples.append(example)
                    current_user_msg = None
            except:
                continue

        return examples

    def _extract_from_claude_history(self, file_path: Path) -> List[TrainingExample]:
        """Extract from Claude Code history.jsonl format.

        The format alternates: user message, assistant message, user, assistant...
        Each entry has a "display" field with the content.
        """
        examples = []
        messages = []

        # Read all messages
        for line in open(file_path, errors='replace'):
            try:
                msg = json.loads(line)
                content = msg.get("display", "")
                session_id = msg.get("sessionId", "")
                timestamp = msg.get("timestamp", 0)

                if content:
                    messages.append({
                        "content": content,
                        "session_id": session_id,
                        "timestamp": timestamp,
                    })
            except:
                continue

        # Group by session and pair up messages
        # Messages alternate: user, assistant, user, assistant
        sessions = {}
        for msg in messages:
            sid = msg["session_id"]
            if sid not in sessions:
                sessions[sid] = []
            sessions[sid].append(msg)

        # Extract pairs from each session
        processed_hashes = set()

        for session_id, session_msgs in sessions.items():
            # Sort by timestamp within session
            session_msgs.sort(key=lambda x: x["timestamp"])

            # Pair up: assume alternating user/assistant
            for i in range(0, len(session_msgs) - 1, 2):
                user_content = session_msgs[i]["content"]
                assistant_content = session_msgs[i + 1]["content"]

                # Heuristic: user messages are usually shorter or questions
                # If assistant msg looks like a user msg, swap
                if len(assistant_content) < len(user_content) / 3:
                    user_content, assistant_content = assistant_content, user_content

                # Create hash to avoid duplicates
                pair_hash = hashlib.md5(
                    f"{user_content[:100]}{assistant_content[:100]}".encode()
                ).hexdigest()

                if pair_hash in processed_hashes:
                    continue
                processed_hashes.add(pair_hash)

                example = self._create_example(
                    user_content, assistant_content, str(file_path)
                )
                if example:
                    examples.append(example)

        return examples

    def _extract_from_json(self, file_path: Path) -> List[TrainingExample]:
        """Extract from JSON format."""
        examples = []

        try:
            data = json.load(open(file_path))
        except:
            return []

        # Handle different formats
        messages = data.get("messages", [])
        if not messages and "conversation" in data:
            messages = data["conversation"]
        if not messages and "mapping" in data:
            # ChatGPT format
            messages = self._flatten_mapping(data["mapping"])

        current_user_msg = None

        for msg in messages:
            role = msg.get("role", msg.get("author", {}).get("role", ""))
            content = self._get_content(msg)

            if role in ["user", "human"]:
                current_user_msg = content
            elif role in ["assistant", "ai"] and current_user_msg:
                example = self._create_example(
                    current_user_msg, content, str(file_path)
                )
                if example:
                    examples.append(example)
                current_user_msg = None

        return examples

    def _flatten_mapping(self, mapping: Dict) -> List[Dict]:
        """Flatten ChatGPT mapping format to messages."""
        messages = []
        for node in mapping.values():
            msg = node.get("message")
            if msg:
                messages.append(msg)
        return sorted(messages, key=lambda x: x.get("create_time", 0))

    def _get_content(self, msg: Dict) -> str:
        """Extract text content from a message."""
        content = msg.get("content", "")

        if isinstance(content, str):
            return content

        if isinstance(content, dict):
            parts = content.get("parts", [])
            if parts:
                return parts[0] if isinstance(parts[0], str) else str(parts[0])

        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, str):
                    text_parts.append(part)
                elif isinstance(part, dict) and part.get("type") == "text":
                    text_parts.append(part.get("text", ""))
            return "\n".join(text_parts)

        return str(content)

    def _create_example(self, user_input: str, response: str,
                        source: str) -> Optional[TrainingExample]:
        """Create a training example if quality is sufficient."""

        # Skip short exchanges
        if len(user_input) < 10 or len(response) < MIN_RESPONSE_LENGTH:
            return None

        # Skip refusals
        refusal_indicators = ["I can't", "I cannot", "I'm sorry, but", "I won't"]
        if any(ind in response for ind in refusal_indicators):
            return None

        # Calculate quality score
        quality = self._calculate_quality(user_input, response)
        if quality < MIN_QUALITY_SCORE:
            return None

        # Categorize
        category = self._categorize(user_input, response)

        # Create unique ID
        example_id = hashlib.md5(
            f"{user_input[:100]}{response[:100]}".encode()
        ).hexdigest()

        return TrainingExample(
            id=example_id,
            user_input=user_input[:4000],
            claude_response=response[:8000],
            category=category,
            quality_score=quality,
            source_file=source,
            extracted_at=datetime.now().isoformat(),
        )

    def _calculate_quality(self, user_input: str, response: str) -> float:
        """Calculate quality score for a training example."""
        score = 0.5

        # Length bonus
        if len(response) > 200: score += 0.1
        if len(response) > 500: score += 0.1
        if len(response) > 1000: score += 0.05

        # Code bonus
        if "```" in response: score += 0.15

        # Structure bonus
        if re.search(r'\d+\.\s', response): score += 0.1  # Numbered list
        if re.search(r'^#+\s', response, re.MULTILINE): score += 0.05  # Headers

        # Reasoning indicators
        reasoning = ["because", "therefore", "since", "thus", "this means"]
        if any(w in response.lower() for w in reasoning): score += 0.1

        # Penalty for very short prompts (might be ambiguous)
        if len(user_input) < 20: score -= 0.1

        return min(max(score, 0.0), 1.0)

    def _categorize(self, user_input: str, response: str) -> str:
        """Categorize the training example."""
        user_lower = user_input.lower()

        if "```" in response:
            if any(kw in user_lower for kw in ["write", "create", "implement", "code"]):
                return "code_generation"
            if any(kw in user_lower for kw in ["fix", "error", "bug", "debug"]):
                return "debugging"
            return "code_general"

        if any(kw in user_lower for kw in ["explain", "what", "how", "why"]):
            return "explanation"

        if any(kw in user_lower for kw in ["plan", "steps", "approach"]):
            return "planning"

        return "general"


class CodebaseScanner:
    """
    Scans local codebases for training examples.

    Thin wrapper around perpetual_learner's _stream_codebase_scanner logic.
    """

    def __init__(self):
        self.code_dirs = [
            Path.home() / "ReverseLab",
            Path.home() / "Developer",
        ]

    def scan(self) -> List[Tuple[str, str, str]]:
        """
        Scan codebases and return (instruction, response, category) tuples.

        Returns list of (instruction, response, category) for each discovered file.
        """
        results = []

        for code_dir in self.code_dirs:
            if not code_dir.exists():
                continue

            try:
                # Scan Python files
                for py_file in code_dir.rglob("*.py"):
                    try:
                        content = py_file.read_text()
                        if len(content) < 100 or len(content) > 50000:
                            continue
                        if 'def ' in content and '"""' in content:
                            instruction = f"Show the implementation of {py_file.stem}"
                            response = f"```python\n{content[:3000]}\n```"
                            results.append((instruction, response, "codebase_python"))
                    except:
                        continue

                # Scan Swift files
                for swift_file in code_dir.rglob("*.swift"):
                    try:
                        content = swift_file.read_text()
                        if 100 < len(content) < 50000:
                            instruction = f"Show {swift_file.stem}.swift implementation"
                            response = f"```swift\n{content[:3000]}\n```"
                            results.append((instruction, response, "codebase_swift"))
                    except:
                        continue

                # Scan JS/TS files
                for js_file in list(code_dir.rglob("*.js")) + list(code_dir.rglob("*.ts")):
                    try:
                        content = js_file.read_text()
                        if 100 < len(content) < 50000 and "node_modules" not in str(js_file):
                            lang = "typescript" if js_file.suffix == ".ts" else "javascript"
                            instruction = f"Show {js_file.stem} code"
                            response = f"```{lang}\n{content[:3000]}\n```"
                            results.append((instruction, response, f"codebase_{lang}"))
                    except:
                        continue

            except Exception as e:
                log(f"[Codebase] Error scanning {code_dir}: {e}")

        return results


class WebScraper:
    """
    Thin wrapper interface for web scraping streams.

    Provides access to perpetual_learner's scraping targets without
    copying all the scraping logic. Each method returns
    (instruction, response, category) tuples.
    """

    # Target configurations from perpetual_learner.py
    STACKOVERFLOW_TAGS = ['swift', 'ios', 'swiftui', 'frida', 'reverse-engineering', 'macos', 'rust', 'python']

    GITHUB_SEARCHES = ['swift ios app', 'frida script', 'swiftui example', 'reverse engineering ios']

    REDDIT_SUBREDDITS = [
        ('swift', 'apple'), ('iOSProgramming', 'apple'),
        ('reverseengineering', 're'), ('rust', 'rust'),
        ('WritingPrompts', 'roleplay'),
    ]

    APPLE_FRAMEWORKS = ['swiftui', 'uikit', 'foundation', 'combine', 'coreml', 'vision', 'homekit', 'appintents']

    FRIDA_PAGES = [
        ('https://frida.re/docs/javascript-api/', 'JavaScript API'),
        ('https://frida.re/docs/ios/', 'iOS'),
        ('https://frida.re/docs/macos/', 'macOS'),
    ]

    CHATGPT_DOMAINS = {
        "apple": ['swift', 'swiftui', 'ios', 'macos', 'xcode', 'coreml', 'homekit', 'metal', 'apple'],
        "reverse_engineering": ['frida', 'hopper', 'reverse', 'binary', 'hook', 'patch', 'jailbreak', 'disassemb'],
        "python": ['python', 'pip', 'django', 'flask', 'pandas', 'numpy', 'pytorch'],
        "rust": ['rust', 'cargo', 'tokio', 'async', 'ownership', 'borrow'],
        "javascript": ['javascript', 'typescript', 'react', 'node', 'npm', 'vue', 'angular'],
        "devops": ['docker', 'kubernetes', 'ci/cd', 'github actions', 'terraform', 'ansible'],
        "ml": ['machine learning', 'neural', 'training', 'model', 'inference', 'transformer', 'llm'],
    }

    def scrape_stackoverflow(self, tag: str) -> List[Tuple[str, str, str]]:
        """Scrape Stack Overflow Q&A for a given tag. Returns (instruction, response, category) tuples."""
        import urllib.request
        results = []
        try:
            url = f"https://stackoverflow.com/questions/tagged/{tag}?sort=votes&pagesize=10"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            questions = re.findall(r'<h3[^>]*class="[^"]*s-post-summary--content-title[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>', html, re.DOTALL)
            excerpts = re.findall(r'<div class="s-post-summary--content-excerpt">([^<]+)</div>', html)

            for q, excerpt in zip(questions[:10], excerpts[:10]):
                q = q.strip()
                excerpt = excerpt.strip()
                if q and excerpt and len(excerpt) > 50:
                    results.append((q, excerpt, f"stackoverflow_{tag}"))
        except Exception as e:
            log(f"[StackOverflow] Error for tag {tag}: {e}")
        return results

    def scrape_github(self, search: str) -> List[Tuple[str, str, str]]:
        """Scrape GitHub repository descriptions. Returns (instruction, response, category) tuples."""
        import urllib.request
        import urllib.parse
        results = []
        try:
            query = urllib.parse.quote(search)
            url = f"https://api.github.com/search/repositories?q={query}&sort=stars&per_page=5"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.v3+json'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            for repo in data.get('items', [])[:5]:
                name = repo.get('full_name', '')
                desc = repo.get('description', '') or ''
                if name and desc:
                    question = f"What is the {name.split('/')[-1]} project?"
                    results.append((question, desc[:1000], "github"))
        except Exception as e:
            log(f"[GitHub] Error for search '{search}': {e}")
        return results

    def scrape_reddit(self, subreddit: str, category: str) -> List[Tuple[str, str, str]]:
        """Scrape Reddit top posts. Returns (instruction, response, category) tuples."""
        import urllib.request
        results = []
        try:
            url = f"https://old.reddit.com/r/{subreddit}/top/.json?t=week&limit=10"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            for post in data.get('data', {}).get('children', [])[:10]:
                post_data = post.get('data', {})
                title = post_data.get('title', '')
                selftext = post_data.get('selftext', '')[:1000]
                if title and selftext and len(selftext) > 100:
                    results.append((title, selftext, f"reddit_{category}"))
        except Exception as e:
            log(f"[Reddit] Error for r/{subreddit}: {e}")
        return results

    def scrape_apple_docs(self, framework: str) -> List[Tuple[str, str, str]]:
        """Scrape Apple Developer Documentation. Returns (instruction, response, category) tuples."""
        import urllib.request
        results = []
        try:
            url = f"https://developer.apple.com/tutorials/data/documentation/{framework}.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            abstract = data.get('abstract', [])
            if abstract:
                text = ' '.join(a.get('text', '') for a in abstract if isinstance(a, dict))
                if text:
                    question = f"What is {framework.title()} in iOS/macOS development?"
                    results.append((question, text[:1500], "apple_docs"))
        except Exception as e:
            pass
        return results

    def scrape_frida_docs(self, url: str, topic: str) -> List[Tuple[str, str, str]]:
        """Scrape Frida documentation. Returns (instruction, response, category) tuples."""
        import urllib.request
        results = []
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=30) as resp:
                html = resp.read().decode('utf-8', errors='ignore')

            code_blocks = re.findall(r'<pre><code[^>]*>(.*?)</code></pre>', html, re.DOTALL)
            for code in code_blocks[:10]:
                clean_code = re.sub(r'<[^>]+>', '', code).strip()
                if len(clean_code) > 50:
                    question = f"Show me a Frida {topic} example"
                    results.append((question, f"```javascript\n{clean_code[:1500]}\n```", "frida_docs"))
        except Exception as e:
            log(f"[FridaDocs] Error: {e}")
        return results

    @staticmethod
    def extract_dialogues(text: str) -> List[Tuple[str, str]]:
        """Extract dialogue pairs from story text."""
        dialogues = []
        quotes = re.findall(r'"([^"]{10,200})"', text)

        for i in range(0, len(quotes) - 1, 2):
            if i + 1 < len(quotes):
                q1 = quotes[i].strip()
                q2 = quotes[i + 1].strip()
                if q1 and q2 and len(q1) > 10 and len(q2) > 10:
                    dialogues.append((q1, q2))

        return dialogues[:20]
