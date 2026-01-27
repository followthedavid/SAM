#!/usr/bin/env python3
"""
SAM Unified Reverse Engineering Orchestrator

Integrates all RE capabilities into a single interface:
- Frida instrumentation (10 scripts)
- Network interception (mitmproxy, SSL unpinning)
- Vision/OCR extraction (macOS Vision)
- Paywall bypass (smart technique selection)
- Desktop automation (AppleScript)
- Memory analysis

SAM can ask questions like:
- "What's this app doing under the hood?"
- "Bypass the paywall on this article"
- "Intercept the API calls from this app"
- "Extract the conversation from ChatGPT"

And this orchestrator selects the right technique automatically.

Usage:
    from re_orchestrator import REOrchestrator, analyze_target
    result = analyze_target("ChatGPT.app", goal="extract_conversation")
"""

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger("re_orchestrator")

# Paths to RE tools
RE_ROOT = Path(__file__).parent.parent  # warp_tauri/
FRIDA_SCRIPTS = RE_ROOT
SCRAPERS_ROOT = RE_ROOT.parent / "scrapers"
BYPASS_ROOT = SCRAPERS_ROOT / "paywall_bypass"


class RETarget(Enum):
    """Types of targets we can analyze."""
    DESKTOP_APP = "desktop_app"       # macOS .app bundle
    WEB_APP = "web_app"               # Browser-based app
    WEBSITE = "website"               # Static website
    API = "api"                       # REST/GraphQL API
    PAYWALLED = "paywalled"           # Paywall-protected content
    BINARY = "binary"                 # Binary executable
    NETWORK = "network"               # Network traffic


class RETechnique(Enum):
    """Available RE techniques."""
    FRIDA_SSL_UNPIN = "frida_ssl_unpin"
    FRIDA_MEMORY_SCAN = "frida_memory_scan"
    FRIDA_SWIFT_RUNTIME = "frida_swift_runtime"
    FRIDA_WEBRTC = "frida_webrtc"
    FRIDA_JSON_INTERCEPT = "frida_json_intercept"
    FRIDA_UI_RENDER = "frida_ui_render"
    MITMPROXY = "mitmproxy"
    VISION_OCR = "vision_ocr"
    DESKTOP_AUTOMATION = "desktop_automation"
    PAYWALL_BYPASS = "paywall_bypass"
    WAYBACK_ARCHIVE = "wayback_archive"
    SCRAPY_SPIDER = "scrapy_spider"


@dataclass
class REResult:
    """Result from an RE operation."""
    technique: RETechnique
    success: bool
    target: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    duration_ms: int = 0
    confidence: float = 0.0
    raw_output: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d['technique'] = self.technique.value
        return d


@dataclass
class REContext:
    """Context for an RE operation."""
    target: str
    target_type: RETarget
    goal: str
    constraints: List[str] = None
    previous_attempts: List[RETechnique] = None

    def __post_init__(self):
        if self.constraints is None:
            self.constraints = []
        if self.previous_attempts is None:
            self.previous_attempts = []


class REOrchestrator:
    """
    Unified orchestrator for all reverse engineering capabilities.

    Automatically selects the best technique based on:
    - Target type (app, website, API, etc.)
    - Goal (extract data, bypass protection, intercept traffic)
    - Previous attempt success/failure
    - System resource availability
    """

    def __init__(self):
        self.technique_success_rates: Dict[RETechnique, float] = {
            t: 0.5 for t in RETechnique
        }
        self.history: List[REResult] = []
        self._frida_processes: Dict[str, subprocess.Popen] = {}

        # Map targets to preferred techniques
        self.technique_map = {
            RETarget.DESKTOP_APP: [
                RETechnique.VISION_OCR,          # Most reliable for ChatGPT
                RETechnique.FRIDA_SWIFT_RUNTIME,
                RETechnique.FRIDA_MEMORY_SCAN,
                RETechnique.FRIDA_SSL_UNPIN,
            ],
            RETarget.WEB_APP: [
                RETechnique.MITMPROXY,
                RETechnique.FRIDA_JSON_INTERCEPT,
            ],
            RETarget.WEBSITE: [
                RETechnique.SCRAPY_SPIDER,
            ],
            RETarget.PAYWALLED: [
                RETechnique.WAYBACK_ARCHIVE,
                RETechnique.PAYWALL_BYPASS,
            ],
            RETarget.API: [
                RETechnique.MITMPROXY,
                RETechnique.FRIDA_JSON_INTERCEPT,
            ],
            RETarget.NETWORK: [
                RETechnique.FRIDA_WEBRTC,
                RETechnique.MITMPROXY,
            ],
        }

    # =========================================================================
    # Main Interface
    # =========================================================================

    def analyze(self, context: REContext) -> REResult:
        """
        Analyze a target using the best available technique.

        Args:
            context: REContext with target info and goal

        Returns:
            REResult with extracted data or error
        """
        logger.info(f"Analyzing {context.target} (type: {context.target_type.value}, goal: {context.goal})")

        # Get techniques for this target type
        techniques = self.technique_map.get(context.target_type, [])

        # Filter out previously failed techniques
        available = [t for t in techniques if t not in context.previous_attempts]

        if not available:
            return REResult(
                technique=RETechnique.VISION_OCR,  # Fallback
                success=False,
                target=context.target,
                error="All techniques exhausted",
            )

        # Sort by success rate
        available.sort(key=lambda t: self.technique_success_rates[t], reverse=True)

        # Try techniques in order
        for technique in available:
            logger.info(f"Trying technique: {technique.value}")

            try:
                result = self._execute_technique(technique, context)

                # Update success rate
                rate = self.technique_success_rates[technique]
                self.technique_success_rates[technique] = rate * 0.9 + (0.1 if result.success else 0.0)

                self.history.append(result)

                if result.success:
                    return result

                # Mark as attempted
                context.previous_attempts.append(technique)

            except Exception as e:
                logger.error(f"Technique {technique.value} failed: {e}")
                context.previous_attempts.append(technique)

        return REResult(
            technique=available[0],
            success=False,
            target=context.target,
            error="All techniques failed",
        )

    def _execute_technique(self, technique: RETechnique, context: REContext) -> REResult:
        """Execute a specific technique."""
        start = datetime.now()

        handlers = {
            RETechnique.FRIDA_SSL_UNPIN: self._frida_ssl_unpin,
            RETechnique.FRIDA_MEMORY_SCAN: self._frida_memory_scan,
            RETechnique.FRIDA_SWIFT_RUNTIME: self._frida_swift_runtime,
            RETechnique.FRIDA_WEBRTC: self._frida_webrtc,
            RETechnique.FRIDA_JSON_INTERCEPT: self._frida_json_intercept,
            RETechnique.FRIDA_UI_RENDER: self._frida_ui_render,
            RETechnique.MITMPROXY: self._mitmproxy,
            RETechnique.VISION_OCR: self._vision_ocr,
            RETechnique.DESKTOP_AUTOMATION: self._desktop_automation,
            RETechnique.PAYWALL_BYPASS: self._paywall_bypass,
            RETechnique.WAYBACK_ARCHIVE: self._wayback_archive,
            RETechnique.SCRAPY_SPIDER: self._scrapy_spider,
        }

        handler = handlers.get(technique)
        if not handler:
            return REResult(
                technique=technique,
                success=False,
                target=context.target,
                error=f"No handler for {technique.value}",
            )

        result = handler(context)
        result.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        return result

    # =========================================================================
    # Frida Techniques
    # =========================================================================

    def _run_frida_script(self, script_name: str, target: str, timeout: int = 30) -> REResult:
        """Run a Frida script against a target."""
        script_path = FRIDA_SCRIPTS / script_name

        if not script_path.exists():
            return REResult(
                technique=RETechnique.FRIDA_SSL_UNPIN,
                success=False,
                target=target,
                error=f"Script not found: {script_name}",
            )

        try:
            # Find the process
            process = target.replace(".app", "")

            cmd = ["frida", "-n", process, "-l", str(script_path)]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return REResult(
                technique=RETechnique.FRIDA_SSL_UNPIN,
                success=result.returncode == 0,
                target=target,
                raw_output=result.stdout,
                error=result.stderr if result.returncode != 0 else None,
            )

        except subprocess.TimeoutExpired:
            return REResult(
                technique=RETechnique.FRIDA_SSL_UNPIN,
                success=False,
                target=target,
                error="Frida timeout",
            )
        except Exception as e:
            return REResult(
                technique=RETechnique.FRIDA_SSL_UNPIN,
                success=False,
                target=target,
                error=str(e),
            )

    def _frida_ssl_unpin(self, context: REContext) -> REResult:
        """SSL certificate unpinning."""
        return self._run_frida_script("frida_ssl_unpin_chatgpt.js", context.target)

    def _frida_memory_scan(self, context: REContext) -> REResult:
        """Memory scanning for patterns."""
        result = self._run_frida_script("frida_memory_scraper.js", context.target, timeout=60)
        result.technique = RETechnique.FRIDA_MEMORY_SCAN
        return result

    def _frida_swift_runtime(self, context: REContext) -> REResult:
        """Swift runtime analysis."""
        result = self._run_frida_script("frida_swift_runtime.js", context.target)
        result.technique = RETechnique.FRIDA_SWIFT_RUNTIME
        return result

    def _frida_webrtc(self, context: REContext) -> REResult:
        """WebRTC traffic interception."""
        result = self._run_frida_script("frida_webrtc_intercept.js", context.target)
        result.technique = RETechnique.FRIDA_WEBRTC
        return result

    def _frida_json_intercept(self, context: REContext) -> REResult:
        """JSON/NSData interception."""
        result = self._run_frida_script("frida_simple_intercept.js", context.target)
        result.technique = RETechnique.FRIDA_JSON_INTERCEPT
        return result

    def _frida_ui_render(self, context: REContext) -> REResult:
        """UI rendering layer hooks."""
        result = self._run_frida_script("frida_ui_render_hook.js", context.target)
        result.technique = RETechnique.FRIDA_UI_RENDER
        return result

    # =========================================================================
    # Vision/OCR
    # =========================================================================

    def _vision_ocr(self, context: REContext) -> REResult:
        """Extract text using macOS Vision framework."""
        try:
            # Import screen scraper
            sys.path.insert(0, str(RE_ROOT))
            from screen_scraper_vision import extract_chatgpt_conversation

            text = extract_chatgpt_conversation()

            return REResult(
                technique=RETechnique.VISION_OCR,
                success=bool(text),
                target=context.target,
                data={"text": text, "source": "vision_ocr"},
                confidence=0.85,  # OCR is typically 85-95% accurate
            )

        except ImportError:
            # Fallback to screencapture + Vision
            return self._vision_ocr_fallback(context)
        except Exception as e:
            return REResult(
                technique=RETechnique.VISION_OCR,
                success=False,
                target=context.target,
                error=str(e),
            )

    def _vision_ocr_fallback(self, context: REContext) -> REResult:
        """Fallback OCR using screencapture + pyobjc."""
        try:
            import tempfile
            from PIL import Image

            # Capture screen
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
                screenshot_path = f.name

            subprocess.run(["screencapture", "-x", screenshot_path], check=True)

            # Use Apple Vision via pyobjc
            try:
                import Vision
                import Quartz

                # Load image
                image_url = Quartz.CFURLCreateFromFileSystemRepresentation(
                    None, screenshot_path.encode(), len(screenshot_path), False
                )
                cg_image_source = Quartz.CGImageSourceCreateWithURL(image_url, None)
                cg_image = Quartz.CGImageSourceCreateImageAtIndex(cg_image_source, 0, None)

                # Create request
                request = Vision.VNRecognizeTextRequest.alloc().init()
                request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)

                # Process
                handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(
                    cg_image, {}
                )
                handler.performRequests_error_([request], None)

                # Extract text
                results = request.results()
                text_parts = []
                for obs in results:
                    top_candidate = obs.topCandidates_(1)[0]
                    text_parts.append(top_candidate.string())

                text = "\n".join(text_parts)

                return REResult(
                    technique=RETechnique.VISION_OCR,
                    success=bool(text),
                    target=context.target,
                    data={"text": text, "source": "vision_framework"},
                    confidence=0.9,
                )

            finally:
                os.unlink(screenshot_path)

        except Exception as e:
            return REResult(
                technique=RETechnique.VISION_OCR,
                success=False,
                target=context.target,
                error=str(e),
            )

    # =========================================================================
    # Network Interception
    # =========================================================================

    def _mitmproxy(self, context: REContext) -> REResult:
        """Network interception via mitmproxy."""
        # Check if mitmproxy is running
        try:
            result = subprocess.run(
                ["pgrep", "-f", "mitmproxy"],
                capture_output=True,
            )

            if result.returncode != 0:
                return REResult(
                    technique=RETechnique.MITMPROXY,
                    success=False,
                    target=context.target,
                    error="mitmproxy not running. Start with: mitmproxy -s mitm_chatgpt_intercept.py",
                )

            # mitmproxy is running, check for captured data
            log_path = RE_ROOT / "mitm_capture.log"
            if log_path.exists():
                with open(log_path) as f:
                    data = f.read()
                return REResult(
                    technique=RETechnique.MITMPROXY,
                    success=bool(data),
                    target=context.target,
                    data={"captured": data},
                )

            return REResult(
                technique=RETechnique.MITMPROXY,
                success=False,
                target=context.target,
                error="No data captured yet",
            )

        except Exception as e:
            return REResult(
                technique=RETechnique.MITMPROXY,
                success=False,
                target=context.target,
                error=str(e),
            )

    # =========================================================================
    # Desktop Automation
    # =========================================================================

    def _desktop_automation(self, context: REContext) -> REResult:
        """AppleScript-based automation."""
        try:
            script = '''
            tell application "System Events"
                tell process "{}"
                    set allWindows to every window
                    set result to ""
                    repeat with w in allWindows
                        set result to result & (name of w) & "\n"
                    end repeat
                    return result
                end tell
            end tell
            '''.format(context.target.replace(".app", ""))

            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )

            return REResult(
                technique=RETechnique.DESKTOP_AUTOMATION,
                success=result.returncode == 0,
                target=context.target,
                data={"windows": result.stdout.strip().split("\n")},
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return REResult(
                technique=RETechnique.DESKTOP_AUTOMATION,
                success=False,
                target=context.target,
                error=str(e),
            )

    # =========================================================================
    # Paywall Bypass
    # =========================================================================

    def _paywall_bypass(self, context: REContext) -> REResult:
        """Smart paywall bypass."""
        try:
            sys.path.insert(0, str(BYPASS_ROOT))
            from smart_bypass import bypass_paywall

            text = bypass_paywall(context.target)

            return REResult(
                technique=RETechnique.PAYWALL_BYPASS,
                success=bool(text),
                target=context.target,
                data={"text": text, "source": "paywall_bypass"},
            )

        except ImportError:
            return REResult(
                technique=RETechnique.PAYWALL_BYPASS,
                success=False,
                target=context.target,
                error="paywall_bypass module not available",
            )
        except Exception as e:
            return REResult(
                technique=RETechnique.PAYWALL_BYPASS,
                success=False,
                target=context.target,
                error=str(e),
            )

    def _wayback_archive(self, context: REContext) -> REResult:
        """Try Wayback Machine for archived content."""
        try:
            import urllib.request
            import urllib.parse

            url = context.target
            wayback_url = f"https://archive.org/wayback/available?url={urllib.parse.quote(url)}"

            with urllib.request.urlopen(wayback_url, timeout=10) as response:
                data = json.loads(response.read())

            snapshots = data.get("archived_snapshots", {})
            if snapshots.get("closest"):
                archive_url = snapshots["closest"]["url"]

                # Fetch archived content
                with urllib.request.urlopen(archive_url, timeout=30) as response:
                    content = response.read().decode()

                return REResult(
                    technique=RETechnique.WAYBACK_ARCHIVE,
                    success=True,
                    target=context.target,
                    data={"archive_url": archive_url, "content": content[:10000]},
                )

            return REResult(
                technique=RETechnique.WAYBACK_ARCHIVE,
                success=False,
                target=context.target,
                error="No archive found",
            )

        except Exception as e:
            return REResult(
                technique=RETechnique.WAYBACK_ARCHIVE,
                success=False,
                target=context.target,
                error=str(e),
            )

    # =========================================================================
    # Scrapy Spider
    # =========================================================================

    def _scrapy_spider(self, context: REContext) -> REResult:
        """Run a Scrapy spider for the target."""
        try:
            # Determine spider based on URL
            url = context.target
            spider_name = self._detect_spider(url)

            if not spider_name:
                return REResult(
                    technique=RETechnique.SCRAPY_SPIDER,
                    success=False,
                    target=context.target,
                    error="No spider available for this URL",
                )

            # Run spider
            cmd = [
                sys.executable, "-m", "scraper_system", "run", spider_name,
                "--pages", "1",
            ]

            result = subprocess.run(
                cmd,
                cwd=str(SCRAPERS_ROOT),
                capture_output=True,
                text=True,
                timeout=300,
            )

            return REResult(
                technique=RETechnique.SCRAPY_SPIDER,
                success=result.returncode == 0,
                target=context.target,
                data={"spider": spider_name, "output": result.stdout},
                error=result.stderr if result.returncode != 0 else None,
            )

        except Exception as e:
            return REResult(
                technique=RETechnique.SCRAPY_SPIDER,
                success=False,
                target=context.target,
                error=str(e),
            )

    def _detect_spider(self, url: str) -> Optional[str]:
        """Detect which spider to use for a URL."""
        url_lower = url.lower()

        spider_map = {
            "archiveofourown.org": "ao3",
            "ao3.org": "ao3",
            "nifty.org": "nifty",
            "literotica.com": "literotica",
            "reddit.com": "reddit_rp",
            "f-list.net": "flist",
            "wwd.com": "wwd",
            "gq.com": "gq_esquire",
            "esquire.com": "gq_esquire",
            "thecut.com": "thecut",
        }

        for domain, spider in spider_map.items():
            if domain in url_lower:
                return spider

        return None

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup(self):
        """Cleanup any running processes."""
        for name, proc in self._frida_processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                proc.kill()

        self._frida_processes.clear()


# =============================================================================
# Convenience Functions
# =============================================================================

_orchestrator: Optional[REOrchestrator] = None


def get_orchestrator() -> REOrchestrator:
    """Get singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = REOrchestrator()
    return _orchestrator


def analyze_target(target: str, goal: str = "extract", target_type: RETarget = None) -> REResult:
    """
    High-level function to analyze a target.

    Args:
        target: The target (app name, URL, etc.)
        goal: What to achieve (extract, intercept, bypass, etc.)
        target_type: Type of target (auto-detected if not provided)

    Returns:
        REResult with the analysis
    """
    # Auto-detect target type
    if target_type is None:
        if target.endswith(".app"):
            target_type = RETarget.DESKTOP_APP
        elif target.startswith("http"):
            if "paywall" in goal or any(
                domain in target for domain in ["nytimes", "wsj", "bloomberg", "ft.com"]
            ):
                target_type = RETarget.PAYWALLED
            else:
                target_type = RETarget.WEBSITE
        elif "/" in target or "." in target:
            target_type = RETarget.WEBSITE
        else:
            target_type = RETarget.DESKTOP_APP

    context = REContext(
        target=target,
        target_type=target_type,
        goal=goal,
    )

    return get_orchestrator().analyze(context)


def extract_conversation(app: str = "ChatGPT") -> REResult:
    """Extract conversation from a chat app."""
    return analyze_target(
        f"{app}.app",
        goal="extract_conversation",
        target_type=RETarget.DESKTOP_APP,
    )


def bypass_paywall(url: str) -> REResult:
    """Bypass paywall for a URL."""
    return analyze_target(
        url,
        goal="bypass_paywall",
        target_type=RETarget.PAYWALLED,
    )


def intercept_api(app: str) -> REResult:
    """Intercept API calls from an app."""
    return analyze_target(
        f"{app}.app",
        goal="intercept_api",
        target_type=RETarget.DESKTOP_APP,
    )


# =============================================================================
# Integration with SAM Orchestrator
# =============================================================================

def handle_re_request(message: str) -> dict:
    """
    Handle RE-related requests from SAM orchestrator.

    This function is called by orchestrator.py when it detects
    an RE-related request.

    Args:
        message: User message

    Returns:
        dict with response and metadata
    """
    message_lower = message.lower()

    # Detect intent
    if "extract" in message_lower and ("chatgpt" in message_lower or "conversation" in message_lower):
        result = extract_conversation()
        return {
            "response": f"Extracted conversation using {result.technique.value}",
            "data": result.data,
            "success": result.success,
        }

    elif "bypass" in message_lower and "paywall" in message_lower:
        # Extract URL from message
        urls = re.findall(r'https?://[^\s]+', message)
        if urls:
            result = bypass_paywall(urls[0])
            return {
                "response": f"Paywall bypass {'successful' if result.success else 'failed'}",
                "data": result.data,
                "success": result.success,
            }
        return {"response": "Please provide a URL to bypass", "success": False}

    elif "intercept" in message_lower or "api" in message_lower:
        # Find app name
        apps = re.findall(r'(\w+)\.app', message)
        if apps:
            result = intercept_api(apps[0])
            return {
                "response": f"API interception {'running' if result.success else 'failed'}",
                "data": result.data,
                "success": result.success,
            }
        return {"response": "Please specify an app to intercept", "success": False}

    elif "frida" in message_lower or "hook" in message_lower:
        # Direct Frida request
        apps = re.findall(r'(\w+)(?:\.app)?', message)
        if apps:
            orchestrator = get_orchestrator()
            result = orchestrator._frida_ssl_unpin(REContext(
                target=apps[-1] + ".app",
                target_type=RETarget.DESKTOP_APP,
                goal="hook",
            ))
            return {
                "response": f"Frida hook {'attached' if result.success else 'failed'}",
                "data": result.data,
                "success": result.success,
            }

    return {
        "response": "I can help with reverse engineering. Try:\n"
                    "- 'Extract conversation from ChatGPT'\n"
                    "- 'Bypass paywall on <url>'\n"
                    "- 'Intercept API calls from <app>'\n"
                    "- 'Run Frida hook on <app>'",
        "success": False,
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="SAM RE Orchestrator")
    parser.add_argument("target", nargs="?", help="Target to analyze")
    parser.add_argument("--goal", "-g", default="extract", help="Goal (extract, bypass, intercept)")
    parser.add_argument("--type", "-t", choices=[t.value for t in RETarget], help="Target type")

    args = parser.parse_args()

    if not args.target:
        print("SAM RE Orchestrator")
        print("=" * 40)
        print("\nAvailable techniques:")
        for t in RETechnique:
            print(f"  - {t.value}")
        print("\nTarget types:")
        for t in RETarget:
            print(f"  - {t.value}")
        print("\nUsage:")
        print("  python re_orchestrator.py ChatGPT.app --goal extract")
        print("  python re_orchestrator.py https://nytimes.com/article --goal bypass")
        sys.exit(0)

    target_type = RETarget(args.type) if args.type else None
    result = analyze_target(args.target, args.goal, target_type)

    print(json.dumps(result.to_dict(), indent=2))
