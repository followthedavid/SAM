#!/usr/bin/env python3
"""
ChatGPT/Claude Browser Bridge for SAM

Monitors ~/.sam_chatgpt_queue.json for tasks, processes them via browser automation,
and writes responses back. Uses Playwright for browser control.

Usage:
    python3 chatgpt_bridge.py [--provider chatgpt|claude] [--headless]

The queue file format:
    [{"id": "uuid", "prompt": "...", "status": "pending|processing|done|error", "response": "..."}]
"""

import asyncio
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)

# Configuration
QUEUE_PATH = Path.home() / ".sam_chatgpt_queue.json"
RESPONSE_PATH = Path.home() / ".sam_chatgpt_responses.json"
POLL_INTERVAL = 2  # seconds
TIMEOUT = 120  # seconds to wait for response

class BrowserBridge:
    def __init__(self, provider="chatgpt", headless=False):
        self.provider = provider
        self.headless = headless
        self.browser = None
        self.page = None
        self.logged_in = False

    async def setup(self):
        """Initialize browser with persistent context for saved login."""
        self.playwright = await async_playwright().start()

        # Use persistent context to keep login sessions
        user_data_dir = Path.home() / ".sam_browser_data" / self.provider
        user_data_dir.mkdir(parents=True, exist_ok=True)

        self.browser = await self.playwright.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=self.headless,
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )

        self.page = self.browser.pages[0] if self.browser.pages else await self.browser.new_page()

    async def navigate_to_chat(self):
        """Navigate to ChatGPT or Claude."""
        if self.provider == "chatgpt":
            await self.page.goto("https://chatgpt.com/", wait_until="networkidle")
        else:
            await self.page.goto("https://claude.ai/new", wait_until="networkidle")

        # Wait for page to load
        await asyncio.sleep(2)

        # Check if we're logged in
        if self.provider == "chatgpt":
            # Look for the main input textarea
            try:
                await self.page.wait_for_selector('textarea, div[contenteditable="true"]', timeout=5000)
                self.logged_in = True
                print(f"[Bridge] Logged into ChatGPT")
            except PlaywrightTimeout:
                print(f"[Bridge] Not logged into ChatGPT - please log in manually")
                self.logged_in = False
        else:
            # Claude
            try:
                await self.page.wait_for_selector('div[contenteditable="true"]', timeout=5000)
                self.logged_in = True
                print(f"[Bridge] Logged into Claude")
            except PlaywrightTimeout:
                print(f"[Bridge] Not logged into Claude - please log in manually")
                self.logged_in = False

    async def send_message(self, prompt: str) -> str:
        """Send a message and wait for response."""
        if not self.logged_in:
            return "[Error] Not logged in. Please log in to the browser window."

        try:
            if self.provider == "chatgpt":
                return await self._send_chatgpt(prompt)
            else:
                return await self._send_claude(prompt)
        except Exception as e:
            return f"[Error] {str(e)}"

    async def _send_chatgpt(self, prompt: str) -> str:
        """Send message to ChatGPT."""
        # Find input area
        input_area = await self.page.query_selector('textarea, div[contenteditable="true"]#prompt-textarea')
        if not input_area:
            # Try clicking new chat first
            new_chat = await self.page.query_selector('button:has-text("New chat"), a:has-text("New chat")')
            if new_chat:
                await new_chat.click()
                await asyncio.sleep(1)
            input_area = await self.page.query_selector('textarea, div[contenteditable="true"]')

        if not input_area:
            return "[Error] Could not find input area"

        # Type the prompt
        await input_area.fill(prompt)
        await asyncio.sleep(0.5)

        # Find and click send button
        send_btn = await self.page.query_selector('button[data-testid="send-button"], button[aria-label="Send prompt"]')
        if send_btn:
            await send_btn.click()
        else:
            # Try pressing Enter
            await input_area.press("Enter")

        # Wait for response
        print(f"[Bridge] Waiting for ChatGPT response...")
        response = await self._wait_for_response_chatgpt()
        return response

    async def _wait_for_response_chatgpt(self) -> str:
        """Wait for ChatGPT to finish responding."""
        start_time = time.time()
        last_response = ""
        stable_count = 0

        while time.time() - start_time < TIMEOUT:
            # Get the last assistant message
            messages = await self.page.query_selector_all('div[data-message-author-role="assistant"]')
            if messages:
                last_msg = messages[-1]
                text = await last_msg.inner_text()

                if text and text == last_response:
                    stable_count += 1
                    # Response is stable for 2 seconds
                    if stable_count >= 4:
                        # Check if still generating
                        stop_btn = await self.page.query_selector('button[aria-label="Stop generating"]')
                        if not stop_btn:
                            return text
                else:
                    stable_count = 0
                    last_response = text

            await asyncio.sleep(0.5)

        return last_response or "[Error] Timeout waiting for response"

    async def _send_claude(self, prompt: str) -> str:
        """Send message to Claude."""
        # Find input area
        input_area = await self.page.query_selector('div[contenteditable="true"]')
        if not input_area:
            return "[Error] Could not find Claude input area"

        # Type the prompt
        await input_area.fill(prompt)
        await asyncio.sleep(0.5)

        # Find and click send button
        send_btn = await self.page.query_selector('button[aria-label="Send Message"], button:has-text("Send")')
        if send_btn:
            await send_btn.click()
        else:
            # Try pressing Enter
            await self.page.keyboard.press("Enter")

        # Wait for response
        print(f"[Bridge] Waiting for Claude response...")
        response = await self._wait_for_response_claude()
        return response

    async def _wait_for_response_claude(self) -> str:
        """Wait for Claude to finish responding."""
        start_time = time.time()
        last_response = ""
        stable_count = 0

        while time.time() - start_time < TIMEOUT:
            # Get the last assistant message
            messages = await self.page.query_selector_all('div[data-testid="assistant-message"]')
            if not messages:
                messages = await self.page.query_selector_all('.prose')

            if messages:
                last_msg = messages[-1]
                text = await last_msg.inner_text()

                if text and text == last_response:
                    stable_count += 1
                    if stable_count >= 4:
                        return text
                else:
                    stable_count = 0
                    last_response = text

            await asyncio.sleep(0.5)

        return last_response or "[Error] Timeout waiting for response"

    async def close(self):
        """Close browser."""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


class QueueProcessor:
    def __init__(self, bridge: BrowserBridge):
        self.bridge = bridge

    def load_queue(self) -> list:
        """Load pending tasks from queue file."""
        if not QUEUE_PATH.exists():
            return []
        try:
            with open(QUEUE_PATH) as f:
                return json.load(f)
        except:
            return []

    def save_queue(self, queue: list):
        """Save queue back to file."""
        with open(QUEUE_PATH, "w") as f:
            json.dump(queue, f, indent=2)

    def save_response(self, task_id: str, response: str, success: bool):
        """Save response to responses file."""
        responses = {}
        if RESPONSE_PATH.exists():
            try:
                with open(RESPONSE_PATH) as f:
                    responses = json.load(f)
            except:
                pass

        responses[task_id] = {
            "response": response,
            "success": success,
            "timestamp": datetime.now().isoformat()
        }

        with open(RESPONSE_PATH, "w") as f:
            json.dump(responses, f, indent=2)

    async def process_pending(self):
        """Process all pending tasks."""
        queue = self.load_queue()
        processed = False

        for task in queue:
            if task.get("status") == "pending":
                task_id = task.get("id", "unknown")
                prompt = task.get("prompt", "")

                print(f"\n[Bridge] Processing task {task_id[:8]}...")
                print(f"[Bridge] Prompt: {prompt[:100]}...")

                task["status"] = "processing"
                self.save_queue(queue)

                # Send to AI
                response = await self.bridge.send_message(prompt)

                # Update task
                task["status"] = "done" if not response.startswith("[Error]") else "error"
                task["response"] = response
                task["completed_at"] = datetime.now().isoformat()
                self.save_queue(queue)

                # Also save to responses file for quick lookup
                self.save_response(task_id, response, task["status"] == "done")

                print(f"[Bridge] Task {task_id[:8]} completed")
                processed = True

        return processed

    async def run_forever(self):
        """Run continuously, processing tasks as they come in."""
        print(f"[Bridge] Starting queue processor")
        print(f"[Bridge] Watching: {QUEUE_PATH}")
        print(f"[Bridge] Provider: {self.bridge.provider}")
        print(f"[Bridge] Press Ctrl+C to stop\n")

        await self.bridge.setup()
        await self.bridge.navigate_to_chat()

        if not self.bridge.logged_in:
            print("\n[Bridge] Please log in to the browser window...")
            print("[Bridge] The bridge will start processing once you're logged in.\n")

            # Wait for login
            while not self.bridge.logged_in:
                await asyncio.sleep(5)
                await self.bridge.navigate_to_chat()

        print("[Bridge] Ready to process tasks!\n")

        while True:
            try:
                processed = await self.process_pending()
                if not processed:
                    await asyncio.sleep(POLL_INTERVAL)
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"[Bridge] Error: {e}")
                await asyncio.sleep(POLL_INTERVAL)

        await self.bridge.close()


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="ChatGPT/Claude Browser Bridge for SAM")
    parser.add_argument("--provider", choices=["chatgpt", "claude"], default="chatgpt",
                        help="Which AI provider to use (default: chatgpt)")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode (not recommended for first login)")
    args = parser.parse_args()

    bridge = BrowserBridge(provider=args.provider, headless=args.headless)
    processor = QueueProcessor(bridge)

    await processor.run_forever()


if __name__ == "__main__":
    asyncio.run(main())
