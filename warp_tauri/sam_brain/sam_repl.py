#!/usr/bin/env python3
"""
SAM Interactive REPL
- Runs in terminal for dual-terminal system
- Auto-escalates to Claude when uncertain
- Logs interactions for training
"""

import sys
import os
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from sam_chat import chat, query_sam_brain
from datetime import datetime
import json
import readline  # For command history

# Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

# Training log
TRAINING_LOG = Path.home() / ".sam" / "repl_training.jsonl"
TRAINING_LOG.parent.mkdir(parents=True, exist_ok=True)


def log_interaction(prompt: str, response: str, provider: str):
    """Log interaction for training."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "response": response,
        "provider": provider,
    }
    with open(TRAINING_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def print_banner():
    """Print welcome banner."""
    print(f"""
{CYAN}╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   {BOLD}SAM Interactive Terminal{RESET}{CYAN}                                  ║
║   Self-improving AI with Claude Escalation                   ║
║                                                              ║
║   Commands:                                                  ║
║     /help     - Show help                                    ║
║     /status   - Show system status                           ║
║     /claude   - Force next query to Claude                   ║
║     /clear    - Clear screen                                 ║
║     /quit     - Exit                                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝{RESET}
""")


def show_status():
    """Show system status."""
    print(f"\n{YELLOW}SAM System Status{RESET}")
    print("=" * 40)

    # Check Ollama
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/ps", timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("models", [])
            if models:
                model = models[0].get("name", "unknown")
                print(f"  Ollama: {GREEN}Running{RESET} ({model})")
            else:
                print(f"  Ollama: {GREEN}Running{RESET} (no model loaded)")
        else:
            print(f"  Ollama: {RED}Error{RESET}")
    except:
        print(f"  Ollama: {RED}Not running{RESET}")

    # Check training log
    if TRAINING_LOG.exists():
        lines = sum(1 for _ in open(TRAINING_LOG))
        print(f"  Training log: {lines} interactions")
    else:
        print(f"  Training log: Empty")

    print()


def run_repl():
    """Main REPL loop."""
    print_banner()

    force_claude = False
    project_context = ""

    while True:
        try:
            # Prompt
            prompt_char = f"{RED}☁{RESET}" if force_claude else f"{GREEN}🧠{RESET}"
            user_input = input(f"\n{prompt_char} {BOLD}SAM>{RESET} ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower()

                if cmd == "/help":
                    print("""
Commands:
  /help           - Show this help
  /status         - Show system status
  /claude         - Force next query to Claude
  /project <path> - Set project context
  /clear          - Clear screen
  /quit or /exit  - Exit REPL
                    """)
                elif cmd == "/status":
                    show_status()
                elif cmd == "/claude":
                    force_claude = True
                    print(f"{YELLOW}Next query will use Claude{RESET}")
                elif cmd.startswith("/project "):
                    path = cmd[9:].strip()
                    if Path(path).exists():
                        readme = Path(path) / "README.md"
                        if readme.exists():
                            project_context = readme.read_text()[:2000]
                            print(f"{GREEN}Project context loaded from {path}{RESET}")
                        else:
                            project_context = f"Project at {path}"
                            print(f"{YELLOW}No README found, using path as context{RESET}")
                    else:
                        print(f"{RED}Path not found: {path}{RESET}")
                elif cmd == "/clear":
                    os.system("clear")
                    print_banner()
                elif cmd in ["/quit", "/exit"]:
                    print(f"\n{CYAN}Goodbye! 👋{RESET}\n")
                    break
                else:
                    print(f"{RED}Unknown command: {cmd}{RESET}")
                continue

            # Query SAM
            print(f"\n{YELLOW}Thinking...{RESET}")
            response = chat(user_input, project_context, force_claude=force_claude)

            # Determine provider from response
            provider = "claude" if "☁️" in response else "sam"

            # Log for training
            log_interaction(user_input, response, provider)

            # Print response
            print(f"\n{response}")

            # Reset force_claude
            force_claude = False

        except KeyboardInterrupt:
            print(f"\n{YELLOW}(Use /quit to exit){RESET}")
        except EOFError:
            print(f"\n{CYAN}Goodbye! 👋{RESET}\n")
            break
        except Exception as e:
            print(f"\n{RED}Error: {e}{RESET}")


if __name__ == "__main__":
    run_repl()
