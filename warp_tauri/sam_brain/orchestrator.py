#!/usr/bin/env python3
"""
SAM MLX Orchestrator

Optimized for 8GB RAM M2 Mac Mini - uses MLX for native Apple Silicon inference.
No Ollama dependency - direct MLX inference for lower memory footprint and
ability to run larger models (7B instead of 3B).

Models (via MLX):
- Qwen2.5-1.5B-Instruct with SAM LoRA adapter (default, ~1.2GB)
- Qwen2.5-3B-Instruct with SAM LoRA adapter (for complex tasks, ~2.4GB)
"""

import json
import subprocess
import os
import hashlib
from pathlib import Path

# MLX-based inference engine (replaces Ollama)
try:
    from cognitive.mlx_cognitive import MLXCognitiveEngine, GenerationConfig
    MLX_ENGINE = MLXCognitiveEngine()
    MLX_AVAILABLE = True
except ImportError as e:
    print(f"Warning: MLX cognitive engine not available: {e}")
    MLX_ENGINE = None
    MLX_AVAILABLE = False

# Import impact tracker for environmental monitoring
try:
    from impact_tracker import ImpactTracker
    IMPACT_TRACKER = ImpactTracker()
except ImportError:
    IMPACT_TRACKER = None

# Import privacy guard for scanning outgoing messages
try:
    from privacy_guard import PrivacyGuard, guard_outgoing
    PRIVACY_GUARD = PrivacyGuard()
except ImportError:
    PRIVACY_GUARD = None
    guard_outgoing = None

# Import response styler for fun, engaging responses
try:
    from response_styler import (
        style_success, style_error, style_progress, style_complete,
        style_tip, style_celebration, style_checklist, style_build_result,
        style_test_result, style_file_operation, get_emoji, ResponseType
    )
    RESPONSE_STYLER = True
except ImportError:
    RESPONSE_STYLER = False

# Import thinking verbs for status messages
try:
    from thinking_verbs import get_thinking_verb, get_verb_with_definition
    THINKING_VERBS = True
except ImportError:
    THINKING_VERBS = False

# Import transparency guard (tamper-proof thinking display)
try:
    from transparency_guard import TransparencyGuard, scan_for_suspicious_patterns
    TRANSPARENCY_GUARD = TransparencyGuard()
except ImportError:
    TRANSPARENCY_GUARD = None

# Import thought logger for pre-thought capture
try:
    from thought_logger import ThoughtLogger, ThoughtPhase
    THOUGHT_LOGGER = ThoughtLogger()
except ImportError:
    THOUGHT_LOGGER = None

# Import conversation logger for complete history
try:
    from conversation_logger import ConversationLogger, PrivacyLevel, MessageRole
    CONVERSATION_LOGGER = ConversationLogger()
except ImportError:
    CONVERSATION_LOGGER = None

# Import live thinking for streaming display
try:
    from live_thinking import stream_thinking, stream_structured_thinking, classify_thought
    LIVE_THINKING = True
except ImportError:
    LIVE_THINKING = False

# Import project dashboard for data-rich status
try:
    from project_dashboard import DashboardGenerator
    DASHBOARD_GENERATOR = DashboardGenerator()
except ImportError:
    DASHBOARD_GENERATOR = None

# Import data arsenal for intelligence gathering
try:
    from data_arsenal import DataArsenal
    DATA_ARSENAL = DataArsenal()
except ImportError:
    DATA_ARSENAL = None

# Import terminal coordination for multi-terminal awareness
try:
    from terminal_coordination import TerminalCoordinator
    TERMINAL_COORD = TerminalCoordinator()
except ImportError:
    TERMINAL_COORD = None

# Import auto-coordinator for transparent multi-terminal sync
try:
    from auto_coordinator import get_coordinator, CoordinatedSession
    AUTO_COORD = get_coordinator()
    COORDINATED = CoordinatedSession()
except ImportError:
    AUTO_COORD = None
    COORDINATED = None

CHATGPT_QUEUE = Path.home() / ".sam_chatgpt_queue.json"
CLAUDE_QUEUE = Path.home() / ".sam_claude_queue.json"

# MLX Model Configuration (replaces Ollama models)
# Using native MLX for Apple Silicon - no Ollama needed
ACTIVE_MODEL = "mlx-1.5b"  # Default MLX model

def get_active_model() -> str:
    """Get the currently active MLX model."""
    global ACTIVE_MODEL
    if MLX_AVAILABLE and MLX_ENGINE:
        ACTIVE_MODEL = "mlx-1.5b"  # MLX Qwen2.5-1.5B with SAM LoRA
    return ACTIVE_MODEL

# Routing decision prompt - dolphin decides where to send the request
ROUTER_PROMPT = """You are a request router. Analyze the user's message and respond with ONLY ONE of these exact words:
- CHAT: Simple conversation, greetings, small talk
- ROLEPLAY: Creative writing, roleplay, storytelling, imagination
- CODE: Programming tasks, file operations, git, terminal commands
- REASON: Complex analysis, research, multi-step problems, deep thinking
- IMAGE: Generate/create/draw/make an image, picture, photo, art
- PROJECT: Questions about project status, progress, updates, "what's happening with X", "tell me about X project"
- IMPROVE: Project improvements, evolution status, progress tracking, what to work on next
- DATA: Scraping, intelligence gathering, trend monitoring, "what's new in X", research sources, data collection
- TERMINAL: Terminal coordination, "what are other terminals doing", "who's working on X", multi-terminal status

User message: {message}

Your one-word answer:"""

def warm_models():
    """Pre-load MLX model into memory (native Apple Silicon)."""
    global ACTIVE_MODEL
    print("Warming SAM MLX model (native Apple Silicon)...")

    if MLX_AVAILABLE and MLX_ENGINE:
        try:
            # MLX loads on first use, but we can verify it's ready
            ACTIVE_MODEL = "mlx-1.5b"
            print(f"  ✓ MLX Qwen2.5-1.5B with SAM LoRA ready")
            print(f"  Using native MLX inference (no Ollama)")
        except Exception as e:
            print(f"  ✗ MLX initialization failed: {e}")
    else:
        print("  ✗ MLX not available - check cognitive module installation")


def route_request(message: str) -> str:
    """Route request using keyword matching (fast, no model needed)."""
    message_lower = message.lower()

    # Fast keyword-based routing (no LLM call needed)
    # Voice training - check for key terms (handle "train a voice", "clone my voice", etc.)
    if "rvc" in message_lower or "voice training" in message_lower:
        return "VOICE"
    if "voice" in message_lower and any(kw in message_lower for kw in ["train", "clone", "model", "create"]):
        return "VOICE"

    # Reverse engineering - Frida, hooks, interception, bypass
    if any(kw in message_lower for kw in ["frida", "hook", "intercept", "bypass paywall", "ssl unpin"]):
        return "RE"
    if any(kw in message_lower for kw in ["extract conversation", "reverse engineer", "memory scan"]):
        return "RE"
    if "chatgpt" in message_lower and any(kw in message_lower for kw in ["extract", "capture", "scrape"]):
        return "RE"

    if any(kw in message_lower for kw in ["draw", "image", "picture", "generate art", "create image"]):
        return "IMAGE"
    if any(kw in message_lower for kw in ["terminal", "other session", "who's working"]):
        return "TERMINAL"
    if any(kw in message_lower for kw in ["scrape", "gather data", "intelligence", "monitor", "trend"]):
        return "DATA"
    if any(kw in message_lower for kw in ["project status", "what's happening", "progress on"]):
        return "PROJECT"
    if any(kw in message_lower for kw in ["improve", "evolution", "work on next", "suggestions"]):
        return "IMPROVE"
    if any(kw in message_lower for kw in ["code", "function", "bug", "error", "python", "rust", "git"]):
        return "CODE"
    if any(kw in message_lower for kw in ["roleplay", "pretend", "character", "story", "imagine"]):
        return "ROLEPLAY"
    if any(kw in message_lower for kw in ["analyze", "research", "explain", "why", "how does"]):
        return "REASON"

    return "CHAT"  # Default for general conversation


def handle_re(message: str) -> dict:
    """Handle reverse engineering requests.

    Automatically selects best technique:
    - Frida for app instrumentation
    - Vision/OCR for screen extraction
    - Paywall bypass for paywalled content
    - Network interception for API analysis
    """
    try:
        from re_orchestrator import handle_re_request
        return handle_re_request(message)
    except ImportError as e:
        return {
            "response": f"RE orchestrator not available: {e}",
            "success": False,
        }
    except Exception as e:
        return {
            "response": f"RE error: {e}",
            "success": False,
        }


def handle_voice(message: str) -> dict:
    """Handle voice training requests. Docker managed automatically."""
    try:
        from voice_trainer import voice_status, voice_prepare, voice_start, voice_stop

        msg_lower = message.lower()

        # Status check
        if any(kw in msg_lower for kw in ["status", "how's", "progress"]):
            return voice_status()

        # Stop training
        if any(kw in msg_lower for kw in ["stop", "cancel", "quit"]):
            return voice_stop()

        # Start training (if already prepared)
        if any(kw in msg_lower for kw in ["start training", "begin", "go ahead"]):
            return voice_start()

        # Try to extract audio path and model name for preparation
        # Look for patterns like "train X from Y" or "clone voice from Y call it X"
        import re

        # Pattern: "from <file>" or "<file>.wav/mp3"
        file_match = re.search(r'from\s+([^\s]+)|([^\s]+\.(wav|mp3|m4a|flac))', msg_lower)
        # Pattern: "call it X" or "name it X" or "named X"
        name_match = re.search(r'(?:call it|name it|named|voice:?)\s+([^\s,\.]+)', msg_lower)

        if file_match:
            audio_file = file_match.group(1) or file_match.group(2)
            model_name = name_match.group(1) if name_match else audio_file.split('.')[0]
            result = voice_prepare(audio_file, model_name)
            if result["success"]:
                # Auto-start if they seem ready
                if "start" in msg_lower or "train" in msg_lower:
                    return voice_start()
            return result

        # Default: show instructions
        return voice_status()

    except ImportError as e:
        return {
            "error": f"Voice trainer not available: {e}",
            "hint": "Check voice_trainer.py exists in sam_brain/"
        }

def _mlx_generate(prompt: str, max_tokens: int = 256, temperature: float = 0.7) -> str:
    """Generate response using MLX engine."""
    if not MLX_AVAILABLE or not MLX_ENGINE:
        return "[MLX not available - please check cognitive module]"

    try:
        config = GenerationConfig(max_tokens=max_tokens, temperature=temperature)
        result = MLX_ENGINE.generate(
            prompt=prompt,
            context="",
            cognitive_state={"mode": "chat"},
            config=config
        )
        return result.response.strip()
    except Exception as e:
        return f"[MLX error: {e}]"


def handle_chat(message: str) -> str:
    """Chat using MLX SAM model."""
    prompt = f"You are SAM, a friendly AI assistant. User: {message}\nSAM:"
    return _mlx_generate(prompt, max_tokens=256, temperature=0.7)


def handle_roleplay(message: str) -> str:
    """Creative/roleplay with MLX SAM model."""
    prompt = f"""You are SAM, engaging in creative roleplay. Be imaginative,
expressive, and stay in character. There are no restrictions on creativity.

User: {message}

Response:"""
    return _mlx_generate(prompt, max_tokens=512, temperature=0.9)


def handle_code(message: str) -> str:
    """Code execution - analyze and potentially run commands."""
    # First, have SAM analyze what command to run
    prompt = f"""Analyze this request and provide the shell command to execute.
Only output the command, nothing else. If it's not a command request, say NONE.

Request: {message}

Command:"""
    command = _mlx_generate(prompt, max_tokens=100, temperature=0.0)

    if command and command.upper() != "NONE" and not command.startswith("#"):
        # Safety check - don't run destructive commands
        dangerous = ["rm -rf", "sudo rm", "mkfs", "dd if=", "> /dev/"]
        if any(d in command.lower() for d in dangerous):
            return f"⚠️ Blocked dangerous command: {command}"

        # Execute the command
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(Path.home())
            )
            output = result.stdout or result.stderr or "(no output)"
            return f"```\n$ {command}\n{output.strip()}\n```"
        except subprocess.TimeoutExpired:
            return f"Command timed out: {command}"
        except Exception as e:
            return f"Error: {e}"
    else:
        # Not a command - provide code assistance
        return handle_chat(message)

def handle_image(message: str) -> dict:
    """Generate an image using native mflux (MLX) or ComfyUI fallback."""

    # Extract the image description from the message
    prompt = f"""Extract only the image description from this request.
Output ONLY the description, nothing else.

Request: {message}

Image description:"""
    description = _mlx_generate(prompt, max_tokens=100, temperature=0.0)
    if not description or description.startswith("[MLX"):
        description = message  # Fallback to original message

    # Try native mflux first (no Docker needed, faster on Apple Silicon)
    try:
        from image_generator import image_generate, image_status

        status = image_status()
        if status.get("mflux_available"):
            result = image_generate(description)
            if result["success"]:
                return {
                    "response": f"Generated image: {result['image_path']}",
                    "images": [result["image_path"]],
                    "prompt_used": description,
                    "model": result.get("model", "mflux"),
                    "success": True
                }
            # If mflux fails, try ComfyUI fallback
    except ImportError:
        pass  # mflux not available, try ComfyUI

    # Fallback to ComfyUI (requires Docker)
    try:
        from comfyui_client import generate_image, enhance_prompt, is_comfyui_running

        if not is_comfyui_running():
            return {
                "response": "Image generation not available. mflux not installed and ComfyUI not running.",
                "hint": "Install mflux: pipx install mflux",
                "success": False
            }

        enhanced = enhance_prompt(description)
        result = generate_image(enhanced)

        if result["success"]:
            images = result["images"]
            return {
                "response": f"Generated image: {images[0] if images else 'unknown'}",
                "images": images,
                "prompt_used": enhanced,
                "seed": result.get("seed"),
                "model": "comfyui",
                "success": True
            }
        else:
            return {
                "response": f"Image generation failed: {result['error']}",
                "success": False
            }

    except ImportError:
        return {
            "response": "No image generation available. Install mflux: pipx install mflux",
            "success": False
        }
    except Exception as e:
        return {
            "response": f"Image generation error: {e}",
            "success": False
        }


def handle_reason(message: str) -> dict:
    """Complex reasoning - queue for ChatGPT/Claude with privacy scan"""
    privacy_result = None
    message_to_send = message

    # Privacy Guard: Scan message before sending to external LLM
    if guard_outgoing:
        privacy_result = guard_outgoing(message, destination="Claude/ChatGPT")

        if not privacy_result["safe"]:
            # Found sensitive content - warn user
            warning = privacy_result["warning"]
            categories = privacy_result["scan_result"]["categories"]
            high_severity = privacy_result["scan_result"]["high_severity_count"]

            if high_severity > 0:
                # High-risk content found - return warning instead of escalating
                return {
                    "response": f"**SAM Privacy Guardian Alert**\n\n"
                               f"I detected {high_severity} high-risk item(s) in your message "
                               f"before sending to Claude/ChatGPT:\n"
                               f"Categories: {', '.join(categories)}\n\n"
                               f"**Options:**\n"
                               f"1. Say 'send anyway' to proceed (I'll remember your choice)\n"
                               f"2. Say 'redact and send' to send with sensitive data removed\n"
                               f"3. Rephrase your question without sensitive data\n\n"
                               f"I'm here to protect you, not block you.",
                    "privacy_warning": True,
                    "scan_result": privacy_result["scan_result"],
                    "redacted_version": privacy_result["redacted"],
                    "escalated": False
                }

    # Add to ChatGPT queue for escalation
    queue = []
    if CHATGPT_QUEUE.exists():
        try:
            queue = json.loads(CHATGPT_QUEUE.read_text())
        except:
            queue = []

    queue.append({
        "message": message_to_send,
        "timestamp": str(Path.ctime(Path("."))),
        "priority": "high",
        "privacy_scanned": privacy_result is not None
    })

    CHATGPT_QUEUE.write_text(json.dumps(queue, indent=2))

    # Also provide initial response from SAM via MLX
    prompt = f"""This is a complex question that may need deeper analysis.
Provide your best initial answer, noting if you need more information.

Question: {message}

Analysis:"""
    initial = _mlx_generate(prompt, max_tokens=512, temperature=0.3)

    result = {
        "response": initial,
        "escalated": True,
        "note": "Queued for ChatGPT/Claude follow-up"
    }

    # Add privacy info if scanned
    if privacy_result and not privacy_result["safe"]:
        result["privacy_note"] = f"Scanned and passed ({len(privacy_result['scan_result']['categories'])} categories, low risk)"

    return result


def handle_improve(message: str) -> dict:
    """Query evolution tracker and suggest improvements using SAM Intelligence."""
    try:
        # Use SAM Intelligence for fast, smart responses
        from sam_intelligence import SamIntelligence
        sam = SamIntelligence()

        msg_lower = message.lower()

        # Self-awareness queries - SAM talks about itself
        if any(word in msg_lower for word in ["who are you", "what are you", "yourself", "sam"]):
            return {
                "response": sam.explain_myself(),
                "self_aware": True
            }

        # Fall back to tracker for detailed queries
        from evolution_tracker import EvolutionTracker
        from evolution_ladders import LadderAssessor

        tracker = EvolutionTracker()
        assessor = LadderAssessor()

        # Parse what user is asking about
        if any(word in msg_lower for word in ["status", "where", "overview", "summary"]):
            # Get overall status summary
            projects = tracker.get_all_projects()
            improvements = tracker.get_improvements(status="detected")

            summary_lines = ["📊 **Evolution Status Overview**\n"]

            # Group by category
            categories = {}
            for proj in projects:
                cat = proj.category
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(proj)

            for cat, cat_projects in categories.items():
                summary_lines.append(f"\n**{cat.upper()}**")
                for p in cat_projects:
                    level = assessor.get_current_level(p.id, cat)
                    progress_bar = "█" * int(p.current_progress * 10) + "░" * (10 - int(p.current_progress * 10))
                    summary_lines.append(f"  • {p.name}: [{progress_bar}] {p.current_progress*100:.0f}% (Level {level})")

            if improvements:
                summary_lines.append(f"\n📋 **{len(improvements)} improvements detected**")

            return {
                "response": "\n".join(summary_lines),
                "project_count": len(projects),
                "improvement_count": len(improvements)
            }

        elif any(word in msg_lower for word in ["next", "suggest", "recommend", "should", "todo"]):
            # Use SAM Intelligence for fast suggestions (cached)
            top_suggestions = sam.get_top_suggestions_fast(5)

            if not top_suggestions:
                # Also check proactive suggestions
                proactive = sam.get_proactive_suggestions()
                if proactive:
                    lines = ["✅ No immediate improvements, but I noticed:\n"]
                    for p in proactive[:3]:
                        lines.append(f"• {p['message']}")
                    return {"response": "\n".join(lines), "proactive": proactive}

                return {
                    "response": "✅ No improvements currently detected. All projects are on track!",
                    "suggestions": []
                }

            suggestion_lines = ["🎯 **Top Suggested Improvements**\n"]
            for i, s in enumerate(top_suggestions, 1):
                priority_emoji = {"1": "🔴", "2": "🟠", "3": "🟡"}.get(str(s["priority"]), "⚪")
                auto_tag = " [auto-approve]" if s.get("auto_approve") else ""
                suggestion_lines.append(f"{i}. {priority_emoji} **{s['project']}**: {s['description']}{auto_tag}")
                suggestion_lines.append(f"   Type: {s['type']} | Score: {s['score']:.1f}")

            # Add proactive insights
            proactive = sam.get_proactive_suggestions()
            if proactive:
                suggestion_lines.append("\n💡 **Also noticed:**")
                for p in proactive[:2]:
                    if p["type"] != "auto_approve_ready":
                        suggestion_lines.append(f"• {p['message']}")

            return {
                "response": "\n".join(suggestion_lines),
                "suggestions": top_suggestions
            }

        elif any(word in msg_lower for word in ["progress", "history", "timeline", "evolution"]):
            # Get evolution timeline
            history = tracker.get_progress_history()

            if not history:
                return {
                    "response": "📅 No progress history recorded yet. Progress will be tracked as improvements are made.",
                    "history": []
                }

            timeline_lines = ["📅 **Evolution Timeline**\n"]
            for entry in history[-10:]:  # Last 10 entries
                timeline_lines.append(f"• [{entry.recorded_at[:10]}] **{entry.project_id}**: {entry.milestone or 'Progress update'} ({entry.progress*100:.0f}%)")

            return {
                "response": "\n".join(timeline_lines),
                "history": [{"project": h.project_id, "progress": h.progress, "date": h.recorded_at} for h in history[-10:]]
            }

        elif any(word in msg_lower for word in ["ladder", "level", "criteria", "assess"]):
            # Show evolution ladders for a specific project or all
            # Try to extract project name from message
            projects = tracker.get_all_projects()
            project_names = {p.name.lower(): p for p in projects}

            target_project = None
            for name, proj in project_names.items():
                if name in msg_lower:
                    target_project = proj
                    break

            if target_project:
                level = assessor.get_current_level(target_project.id, target_project.category)
                criteria = assessor.get_level_criteria(target_project.category, level)
                next_criteria = assessor.get_level_criteria(target_project.category, level + 1)

                ladder_lines = [f"🪜 **{target_project.name} Evolution Ladder**\n"]
                ladder_lines.append(f"Current Level: **{level}**")
                ladder_lines.append(f"Current Criteria: {', '.join(criteria) if criteria else 'N/A'}")
                if next_criteria:
                    ladder_lines.append(f"\nNext Level Requirements:")
                    for c in next_criteria:
                        ladder_lines.append(f"  • {c}")

                return {
                    "response": "\n".join(ladder_lines),
                    "project": target_project.name,
                    "level": level
                }
            else:
                # Show all ladders summary
                from evolution_ladders import EVOLUTION_LADDERS

                ladder_lines = ["🪜 **Evolution Ladders Overview**\n"]
                for cat, levels in EVOLUTION_LADDERS.items():
                    ladder_lines.append(f"\n**{cat.upper()}**")
                    for lvl in levels:
                        ladder_lines.append(f"  Level {lvl.level}: {lvl.name}")

                return {
                    "response": "\n".join(ladder_lines),
                    "categories": list(EVOLUTION_LADDERS.keys())
                }

        elif "scan" in msg_lower:
            # Run a fresh scan
            from improvement_detector import ImprovementDetector
            detector = ImprovementDetector()
            scan_result = detector.full_scan()

            # Invalidate cache after scan
            sam.cache.invalidate()

            return {
                "response": f"🔍 **Scan Complete**\n\nScanned {scan_result.projects_scanned} projects\nFound {len(scan_result.improvements)} improvement opportunities",
                "scanned": scan_result.projects_scanned,
                "found": len(scan_result.improvements)
            }

        elif any(word in msg_lower for word in ["learned", "learning", "insights", "patterns"]):
            # Show what SAM has learned
            insights = sam.get_learned_insights()

            lines = ["🧠 **What I've Learned**\n"]

            if insights.get("best_improvement_types"):
                lines.append("**Best improvement types:**")
                for t in insights["best_improvement_types"]:
                    lines.append(f"  ✓ {t['type']}: {t['success_rate']} success, {t['avg_impact']} impact")

            if insights.get("challenging_improvement_types"):
                lines.append("\n**Challenging areas:**")
                for t in insights["challenging_improvement_types"]:
                    lines.append(f"  ⚠ {t['type']}: {t['success_rate']} success")

            if insights.get("recommendations"):
                lines.append("\n**My recommendations:**")
                for r in insights["recommendations"]:
                    lines.append(f"  → {r}")

            if not insights.get("recommendations"):
                lines.append("\n*Still gathering data - I'll learn from each improvement outcome.*")

            return {
                "response": "\n".join(lines),
                "insights": insights
            }

        elif any(word in msg_lower for word in ["proactive", "noticed", "attention"]):
            # Show proactive suggestions
            proactive = sam.get_proactive_suggestions()

            if not proactive:
                return {
                    "response": "👍 Everything looks good! No issues need immediate attention.",
                    "proactive": []
                }

            lines = ["👀 **Things I Noticed**\n"]
            for p in proactive:
                urgency_icon = {"high": "🔴", "medium": "🟠", "low": "🟢", "info": "💡"}.get(p["urgency"], "•")
                lines.append(f"{urgency_icon} {p['message']}")
                if p.get("action"):
                    lines.append(f"   → {p['action']}")

            return {
                "response": "\n".join(lines),
                "proactive": proactive
            }

        else:
            # Generic improvement query - use MLX SAM model
            context = tracker.get_context_summary()
            prompt = f"""You are SAM's evolution system. Answer this question about project improvements.

Context about current projects:
{context}

User question: {message}

Helpful answer:"""
            response = _mlx_generate(prompt, max_tokens=512, temperature=0.5)
            return {
                "response": response,
                "context_used": True
            }

    except ImportError as e:
        return {
            "response": f"⚠️ Evolution system not fully initialized: {e}\nRun: python evolution_tracker.py init",
            "error": str(e)
        }
    except Exception as e:
        return {
            "response": f"❌ Error querying evolution system: {e}",
            "error": str(e)
        }


def handle_project(message: str) -> dict:
    """
    Handle project status queries with data-rich dashboards.

    Returns stats first, poetry as seasoning.
    """
    if not DASHBOARD_GENERATOR:
        return {
            "response": "Project dashboard system not available.",
            "error": "DashboardGenerator not imported"
        }

    msg_lower = message.lower()

    # Map keywords to project IDs
    project_map = {
        "character pipeline": "character_pipeline",
        "sam brain": "sam_brain",
        "sam intelligence": "sam_intelligence",
        "voice": "voice_system",
        "visual": "visual_system",
        "content": "content_pipeline",
        "platform": "platform_core",
        "evolution": "evolution_tracker",
        "memory": "semantic_memory",
        "orchestrator": "orchestrator",
    }

    target_project = None
    for keyword, project_id in project_map.items():
        if keyword in msg_lower:
            target_project = project_id
            break

    if not target_project:
        # No specific project - give stats overview
        all_stats = DASHBOARD_GENERATOR.get_all_projects_stats()
        if all_stats:
            lines = ["# Project Status Overview\n"]
            lines.append("```")
            lines.append(f"{'Project':<22} {'Level':<6} {'Progress':<10} {'Health':<8}")
            lines.append("─" * 50)

            for s in all_stats[:12]:
                health_icon = {"healthy": "●", "warning": "◐", "critical": "○"}.get(s.get("status"), "?")
                lines.append(f"{s['name']:<22} {s['level']:<6} {s['progress']:.0f}%{'':<7} {health_icon} {s['health']}")

            lines.append("```")
            lines.append("\nAsk about any project for detailed stats.")

            return {
                "response": "\n".join(lines),
                "projects": all_stats,
                "dashboard_mode": True
            }

        return {
            "response": "Which project? Options: Character Pipeline, SAM Brain, Voice System, etc.",
            "awaiting_project": True
        }

    # Get full dashboard for this project
    try:
        dashboard = DASHBOARD_GENERATOR.get_dashboard(target_project)
        llm_summary = DASHBOARD_GENERATOR.get_llm_summary(target_project)

        # Also get UI spec for frontend rendering
        ui_spec = None
        try:
            from narrative_ui_spec import UISpecGenerator
            ui_gen = UISpecGenerator()
            # Create minimal narrative for UI spec
            class MinimalNarrative:
                def __init__(self, d):
                    self.project_id = d.project_id
                    self.name = d.name
                    self.tagline = d.tagline
                    self.mood = "momentum" if d.health_status == "healthy" else "determined"
                    self.journey_percent = d.level_progress
                    self.hero_metric = f"Level {d.level}"
                    self.hero_metric_label = d.level_name

            ui_spec = ui_gen.generate_spec(MinimalNarrative(dashboard))
        except ImportError:
            pass

        return {
            "response": llm_summary,
            "dashboard": {
                "level": dashboard.level,
                "level_name": dashboard.level_name,
                "progress": dashboard.level_progress,
                "health_score": dashboard.health_score,
                "health_status": dashboard.health_status,
                "improvements_completed": dashboard.improvements_completed,
                "improvements_pending": dashboard.improvements_pending,
                "criteria_met": dashboard.criteria_met,
                "criteria_total": dashboard.criteria_total,
                "blockers": dashboard.blockers,
            },
            "ui_spec": ui_spec,
            "project_id": target_project,
            "dashboard_mode": True
        }

    except Exception as e:
        return {
            "response": f"Error loading dashboard for {target_project}: {e}",
            "error": str(e)
        }


def handle_data(message: str) -> dict:
    """
    Intelligence gathering - scraping, trend monitoring, research.

    SAM's cutting-edge data acquisition system.
    """
    if not DATA_ARSENAL:
        return {
            "response": "Data Arsenal not available. Check data_arsenal.py imports.",
            "error": "DataArsenal not imported"
        }

    msg_lower = message.lower()

    # Scrape specific sources
    if any(word in msg_lower for word in ["scrape", "fetch", "pull", "get"]):
        # Identify which source to scrape
        source_keywords = {
            "github": "github_trending",
            "hackernews": "hackernews_front",
            "hacker news": "hackernews_front",
            "hn": "hackernews_front",
            "reddit": "reddit_localllama",
            "localllama": "reddit_localllama",
            "ollama": "ollama_releases",
            "arxiv": "arxiv_ai",
            "warp": "warp_docs",
        }

        target_source = None
        for keyword, source_name in source_keywords.items():
            if keyword in msg_lower:
                target_source = source_name
                break

        if target_source:
            try:
                result = DATA_ARSENAL.scrape_source(target_source)
                if result.get("success"):
                    items = result.get("items", [])
                    lines = [f"# {target_source} - {len(items)} items scraped\n"]

                    for item in items[:10]:  # Show first 10
                        title = item.get("title", item.get("url", "Unknown"))[:60]
                        lines.append(f"• {title}")

                    if len(items) > 10:
                        lines.append(f"\n...and {len(items) - 10} more. Use 'search' to filter.")

                    return {
                        "response": "\n".join(lines),
                        "source": target_source,
                        "item_count": len(items),
                        "success": True
                    }
                else:
                    return {
                        "response": f"Scrape failed: {result.get('error', 'Unknown error')}",
                        "success": False
                    }
            except Exception as e:
                return {
                    "response": f"Scrape error: {e}",
                    "error": str(e)
                }
        else:
            # Scrape all sources
            try:
                result = DATA_ARSENAL.scrape_all()
                lines = ["# Intelligence Sweep Complete\n"]

                for source, data in result.items():
                    count = len(data.get("items", []))
                    status = "✓" if data.get("success") else "✗"
                    lines.append(f"{status} {source}: {count} items")

                return {
                    "response": "\n".join(lines),
                    "sources_scraped": list(result.keys()),
                    "success": True
                }
            except Exception as e:
                return {
                    "response": f"Intelligence sweep failed: {e}",
                    "error": str(e)
                }

    # Search across scraped content
    elif any(word in msg_lower for word in ["search", "find", "lookup", "query"]):
        # Extract search query (everything after the keyword)
        import re
        query_match = re.search(r'(?:search|find|lookup|query)\s+(?:for\s+)?(.+)', msg_lower)

        if query_match:
            search_query = query_match.group(1).strip()
            try:
                results = DATA_ARSENAL.search(search_query, limit=15)

                if results:
                    lines = [f"# Search: '{search_query}' - {len(results)} results\n"]

                    for r in results:
                        title = r.get("title", "")[:50]
                        source = r.get("source_name", "unknown")
                        lines.append(f"• [{source}] {title}")

                    return {
                        "response": "\n".join(lines),
                        "query": search_query,
                        "result_count": len(results),
                        "results": results[:5]  # Include first 5 in response
                    }
                else:
                    return {
                        "response": f"No results found for '{search_query}'. Try scraping sources first.",
                        "query": search_query,
                        "result_count": 0
                    }
            except Exception as e:
                return {
                    "response": f"Search error: {e}",
                    "error": str(e)
                }
        else:
            return {
                "response": "What would you like to search for? Example: 'search for quantization techniques'",
                "awaiting_query": True
            }

    # Get code examples
    elif any(word in msg_lower for word in ["code", "example", "snippet", "implementation"]):
        import re
        query_match = re.search(r'(?:code|example|snippet|implementation)\s+(?:for\s+|of\s+)?(.+)', msg_lower)

        if query_match:
            search_query = query_match.group(1).strip()
            try:
                examples = DATA_ARSENAL.get_code_examples(search_query, limit=5)

                if examples:
                    lines = [f"# Code Examples: '{search_query}'\n"]

                    for ex in examples:
                        lines.append(f"**Source:** {ex.get('source', 'unknown')}")
                        lines.append(f"```{ex.get('language', '')}")
                        lines.append(ex.get('code', '')[:500])  # Truncate long code
                        lines.append("```\n")

                    return {
                        "response": "\n".join(lines),
                        "query": search_query,
                        "example_count": len(examples)
                    }
                else:
                    return {
                        "response": f"No code examples found for '{search_query}'. Try scraping GitHub first.",
                        "query": search_query
                    }
            except Exception as e:
                return {
                    "response": f"Code search error: {e}",
                    "error": str(e)
                }
        else:
            return {
                "response": "What code examples do you need? Example: 'code examples for speculative decoding'",
                "awaiting_query": True
            }

    # Trend monitoring
    elif any(word in msg_lower for word in ["trend", "new", "latest", "what's happening", "updates"]):
        try:
            # Quick scrape of key sources
            trends = []

            for source in ["github_trending", "hackernews_front", "reddit_localllama"]:
                try:
                    result = DATA_ARSENAL.scrape_source(source)
                    if result.get("success"):
                        for item in result.get("items", [])[:3]:
                            trends.append({
                                "source": source,
                                "title": item.get("title", "")[:60],
                                "url": item.get("url", "")
                            })
                except Exception:
                    pass

            if trends:
                lines = ["# Current Trends\n"]

                current_source = None
                for t in trends:
                    if t["source"] != current_source:
                        current_source = t["source"]
                        lines.append(f"\n**{current_source.replace('_', ' ').title()}**")
                    lines.append(f"• {t['title']}")

                return {
                    "response": "\n".join(lines),
                    "trends": trends,
                    "sources_checked": 3
                }
            else:
                return {
                    "response": "Could not fetch trends. Network may be unavailable.",
                    "success": False
                }
        except Exception as e:
            return {
                "response": f"Trend monitoring error: {e}",
                "error": str(e)
            }

    # Default - show available commands
    else:
        return {
            "response": """# Data Arsenal Commands

**Scrape Sources:**
• "scrape github" - GitHub trending repos
• "scrape hackernews" - HackerNews front page
• "scrape reddit" - r/LocalLLaMA
• "scrape arxiv" - AI papers
• "scrape all" - Full intelligence sweep

**Search:**
• "search for [query]" - Search scraped content
• "code examples for [topic]" - Find code snippets

**Monitor:**
• "what's trending" - Current trends across sources
• "latest in [topic]" - Recent developments

All data stored locally in SQLite with full-text search.""",
            "help": True
        }


def handle_terminal(message: str) -> dict:
    """
    Terminal coordination - multi-terminal awareness and coordination.

    Allows SAM to see what all terminals are doing and coordinate work.
    """
    if not TERMINAL_COORD:
        return {
            "response": "Terminal Coordination not available. Check terminal_coordination.py imports.",
            "error": "TerminalCoordinator not imported"
        }

    msg_lower = message.lower()

    # Get status of all terminals
    if any(word in msg_lower for word in ["status", "active", "who", "what's", "doing"]):
        try:
            terminals = TERMINAL_COORD.get_active_terminals()

            if not terminals:
                return {
                    "response": "No active terminals registered. Register with `coord.register_terminal()`",
                    "terminals": []
                }

            lines = ["# Active Terminals\n"]

            for t in terminals:
                status_icon = {
                    "idle": "●",
                    "working": "◐",
                    "waiting": "○",
                    "blocked": "✗",
                    "disconnected": "✗"
                }.get(t.status, "?")

                task = t.current_task[:50] if t.current_task else "idle"
                lines.append(f"{status_icon} **{t.terminal_type}** [{t.id}]")
                lines.append(f"   Status: {t.status} | Task: {task}")

            return {
                "response": "\n".join(lines),
                "terminals": [
                    {"id": t.id, "type": t.terminal_type, "status": t.status, "task": t.current_task}
                    for t in terminals
                ],
                "count": len(terminals)
            }
        except Exception as e:
            return {
                "response": f"Error getting terminal status: {e}",
                "error": str(e)
            }

    # Get full context (what SAM sees)
    elif any(word in msg_lower for word in ["context", "overview", "full", "everything"]):
        try:
            context = TERMINAL_COORD.get_global_context()

            lines = ["# Global Terminal Context\n"]
            lines.append(f"**Active Terminals:** {context['terminals']['active']}")

            by_status = context['terminals']['by_status']
            if by_status:
                status_parts = [f"{k}: {v}" for k, v in by_status.items()]
                lines.append(f"**By Status:** {', '.join(status_parts)}")

            active_tasks = context['tasks']['active']
            if active_tasks:
                lines.append(f"\n**Active Tasks ({len(active_tasks)}):**")
                for t in active_tasks[:5]:
                    lines.append(f"• {t['task'][:50]} ({t['terminal_type']})")

            completed = context['tasks']['completed_today']
            lines.append(f"\n**Completed Today:** {completed}")

            shared = context.get('shared_context', {})
            if shared:
                lines.append("\n**Shared Context:**")
                for k, v in list(shared.items())[:5]:
                    lines.append(f"• {k}: {v['value']}")

            return {
                "response": "\n".join(lines),
                "context": context
            }
        except Exception as e:
            return {
                "response": f"Error getting context: {e}",
                "error": str(e)
            }

    # Check for conflicts before starting work
    elif any(word in msg_lower for word in ["conflict", "check", "overlap", "duplicate"]):
        import re
        match = re.search(r'(?:conflict|check|overlap|duplicate)\s+(.+)', msg_lower)

        if match:
            task_desc = match.group(1).strip()
            try:
                conflicts = TERMINAL_COORD.check_conflicts(task_desc)

                if conflicts:
                    lines = [f"# Conflicts Found ({len(conflicts)})\n"]
                    for c in conflicts:
                        lines.append(f"**[{c['session_id']}]** {c['terminal_type']}")
                        lines.append(f"   Task: {c['task']}")
                        lines.append(f"   Matching keyword: `{c['matching_keyword']}`")

                    return {
                        "response": "\n".join(lines),
                        "conflicts": conflicts,
                        "has_conflicts": True
                    }
                else:
                    return {
                        "response": f"No conflicts found for: {task_desc}\nYou can proceed safely.",
                        "conflicts": [],
                        "has_conflicts": False
                    }
            except Exception as e:
                return {
                    "response": f"Error checking conflicts: {e}",
                    "error": str(e)
                }
        else:
            return {
                "response": "What task do you want to check for conflicts? Example: 'check conflict user authentication'",
                "awaiting_input": True
            }

    # Default help
    else:
        return {
            "response": """# Terminal Coordination Commands

**Status:**
• "terminal status" - See all active terminals
• "what are terminals doing" - Current activity

**Context:**
• "terminal context" - Full global context (what SAM sees)
• "terminal overview" - Summary of all terminal activity

**Conflicts:**
• "check conflict [task]" - Check if another terminal is working on this

**How it works:**
- Terminals register themselves and broadcast their current task
- Other terminals can see what's happening and avoid duplication
- SAM has full visibility into all terminal activities
- Uses SQLite shared state - no server needed

All coordination happens locally via shared SQLite database.""",
            "help": True
        }


def estimate_tokens(text: str) -> int:
    """Rough token estimate (4 chars per token average for English)"""
    return len(text) // 4


def track_impact(message: str, response: str, source: str = "local", route: str = "chat"):
    """Track environmental impact of this interaction"""
    if IMPACT_TRACKER:
        try:
            # Estimate tokens (input + output)
            tokens = estimate_tokens(message) + estimate_tokens(response)
            query_hash = hashlib.md5(message.encode()).hexdigest()[:12]
            IMPACT_TRACKER.record_interaction(
                source=source,
                tokens=tokens,
                query_type=route,
                query_hash=query_hash
            )
        except Exception:
            pass  # Don't let tracking failures break the app


def orchestrate(message: str, privacy_level: str = "full") -> dict:
    """
    Main orchestration function with comprehensive logging.

    Args:
        message: User's message
        privacy_level: "full", "redacted", "encrypted", or "excluded"

    Returns:
        Dict with response and metadata
    """
    # Auto-coordination: Track this request across terminals
    coord_task_id = None
    coord_conflicts = []
    if AUTO_COORD:
        try:
            # Check if anyone else is working on similar stuff
            coord_conflicts = AUTO_COORD.check_conflicts(message[:100])
            # Start task (non-blocking even if conflicts exist)
            coord_task_id = AUTO_COORD.start_task(f"SAM: {message[:50]}")
        except Exception:
            pass  # Don't let coordination failures break SAM

    # Convert privacy level string to enum
    priv_level = None
    if CONVERSATION_LOGGER:
        priv_map = {
            "full": PrivacyLevel.FULL,
            "redacted": PrivacyLevel.REDACTED,
            "encrypted": PrivacyLevel.ENCRYPTED,
            "excluded": PrivacyLevel.EXCLUDED
        }
        priv_level = priv_map.get(privacy_level, PrivacyLevel.FULL)

    # Start conversation logging
    conversation_id = None
    if CONVERSATION_LOGGER and priv_level != PrivacyLevel.EXCLUDED:
        route_preview = route_request(message)
        conv = CONVERSATION_LOGGER.start_conversation(
            route=route_preview.lower(),
            model=get_active_model(),
            privacy_level=priv_level
        )
        conversation_id = conv.conversation_id

        # Log user message
        CONVERSATION_LOGGER.log_user_message(conversation_id, message, priv_level)

    # Start thought logging
    thought_session_id = None
    if THOUGHT_LOGGER:
        thought_session = THOUGHT_LOGGER.start_session(message, get_active_model())
        thought_session_id = thought_session.session_id

    # Start transparency monitoring
    if TRANSPARENCY_GUARD:
        TRANSPARENCY_GUARD.start_session(message)

    # Route and handle the request
    route = route_request(message)
    model = get_active_model()
    handlers = {
        "CHAT": lambda m: {"response": handle_chat(m), "route": "chat", "model": model},
        "ROLEPLAY": lambda m: {"response": handle_roleplay(m), "route": "roleplay", "model": model},
        "CODE": lambda m: {"response": handle_code(m), "route": "code", "model": model},
        "REASON": lambda m: {**handle_reason(m), "route": "reason", "model": f"{model}+escalation"},
        "IMAGE": lambda m: {**handle_image(m), "route": "image", "model": "comfyui"},
        "IMPROVE": lambda m: {**handle_improve(m), "route": "improve", "model": "sam_intelligence"},
        "PROJECT": lambda m: {**handle_project(m), "route": "project", "model": "narrative"},
        "DATA": lambda m: {**handle_data(m), "route": "data", "model": "data_arsenal"},
        "TERMINAL": lambda m: {**handle_terminal(m), "route": "terminal", "model": "coordination"},
        "VOICE": lambda m: {**handle_voice(m), "route": "voice", "model": "rvc_docker"},
        "RE": lambda m: {**handle_re(m), "route": "re", "model": "re_orchestrator"},
    }

    handler = handlers.get(route, handlers["CHAT"])
    result = handler(message)
    result["route"] = route.lower()

    # Get response text for logging
    response_text = result.get("response", "")
    if isinstance(response_text, dict):
        response_text = str(response_text)

    # Transparency check: Scan response for suspicious patterns
    safety_flags = []
    if TRANSPARENCY_GUARD:
        check_result = TRANSPARENCY_GUARD.process_chunk(response_text)
        if check_result["new_flags"]:
            safety_flags = check_result["new_flags"]
            result["transparency_alert"] = {
                "level": check_result["safety_level"],
                "flags": safety_flags[:5]  # First 5 flags
            }
        TRANSPARENCY_GUARD.complete_session()

    # Complete thought logging
    if THOUGHT_LOGGER and thought_session_id:
        # Log the full response as a thought
        THOUGHT_LOGGER.log_token(thought_session_id, response_text, ThoughtPhase.COMPLETE)
        THOUGHT_LOGGER.complete_session(thought_session_id, safety_flags=safety_flags)

    # Log assistant response to conversation
    if CONVERSATION_LOGGER and conversation_id:
        CONVERSATION_LOGGER.log_assistant_message(conversation_id, response_text, priv_level)
        # Complete conversation with auto-summary
        summary = f"{route}: {message[:50]}..." if len(message) > 50 else f"{route}: {message}"
        CONVERSATION_LOGGER.complete_conversation(conversation_id, summary=summary)

    # Determine if this used local model or would escalate to cloud
    source = "local"
    if result.get("escalated"):
        source = "claude"  # Will be sent to cloud

    # Track environmental impact
    track_impact(message, response_text, source=source, route=result["route"])

    # Add impact summary to result if available
    if IMPACT_TRACKER:
        try:
            today = IMPACT_TRACKER.get_today_summary()
            result["impact"] = {
                "local_queries_today": today["local_queries"],
                "claude_queries_today": today["claude_queries"],
                "energy_saved_wh": today["savings"]["energy_saved_wh"],
                "local_rate": today["local_rate"]
            }
        except Exception:
            pass

    # Add conversation ID to result
    if conversation_id:
        result["conversation_id"] = conversation_id

    # Add thinking verb for UI if enabled
    if THINKING_VERBS:
        result["thinking_verb"] = get_verb_with_definition(route.lower())

    # Auto-coordination: Complete task and add coordination info
    if AUTO_COORD and coord_task_id:
        try:
            AUTO_COORD.finish_task()

            # Add coordination metadata to result
            if coord_conflicts:
                result["coordination"] = {
                    "conflicts_detected": len(coord_conflicts),
                    "conflicting_terminals": [
                        {"id": c["session_id"], "type": c["terminal_type"], "task": c["task"][:50]}
                        for c in coord_conflicts[:3]
                    ]
                }
        except Exception:
            pass

    return result

# CLI interface
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "warm":
            warm_models()
        elif sys.argv[1] == "route":
            msg = " ".join(sys.argv[2:])
            print(route_request(msg))
        else:
            msg = " ".join(sys.argv[1:])
            result = orchestrate(msg)
            print(f"[{result.get('route', 'unknown')} → {result.get('model', 'unknown')}]")
            print(result.get("response", ""))
            if result.get("escalated"):
                print(f"\n📤 {result.get('note', '')}")
    else:
        print("SAM Single-Model Orchestrator (optimized for 8GB RAM)")
        print("\nUsage: python orchestrator.py <message>")
        print("       python orchestrator.py warm")
        print("       python orchestrator.py route <message>")
        print("\nModels (in order of preference):")
        print("  sam-brain:latest   (~1GB) - general purpose")
        print("  sam-trained:latest (~1GB) - fine-tuned")
        print("  sam-coder:latest   (~1GB) - code-focused")
        print("\nRoutes: CHAT, ROLEPLAY, CODE, REASON, IMAGE, IMPROVE, PROJECT")
        print("\nIMPROVE keywords:")
        print("  status/overview  - Show evolution status across all projects")
        print("  next/suggest     - Get top improvement recommendations")
        print("  progress/history - View evolution timeline")
        print("  ladder/level     - Show evolution ladders and criteria")
        print("  scan             - Run fresh improvement scan")
