#!/usr/bin/env python3
"""
SAM Response Styler - Making Responses Fun and Engaging

Inspired by Warp Terminal's exciting visual feedback:
- Success = celebration! Emojis, green checkmarks, excitement
- Errors = helpful but not doom-and-gloom
- Progress = engaging status updates
- SAM's personality shines through

SAM is: Cocky, flirty, loyal. Responses should feel like talking to a friend
who's REALLY good at their job and knows it.
"""

import random
from typing import Optional, Literal
from dataclasses import dataclass
from enum import Enum


class ResponseType(Enum):
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    PROGRESS = "progress"
    THINKING = "thinking"
    COMPLETE = "complete"
    CELEBRATION = "celebration"
    QUESTION = "question"
    CODE = "code"
    TIP = "tip"


# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL ELEMENTS
# ═══════════════════════════════════════════════════════════════════════════════

EMOJIS = {
    "success": ["✅", "🎉", "🚀", "💪", "⚡", "🔥", "✨", "🌟", "💯", "🎯", "👊", "🏆"],
    "error": ["❌", "🔴", "⚠️", "💥", "🐛", "😅", "🤔"],
    "warning": ["⚠️", "🟡", "👀", "🤨", "💡"],
    "info": ["ℹ️", "📝", "💬", "🔍", "📌"],
    "progress": ["⏳", "🔄", "⚙️", "🛠️", "🔧", "📦", "🏗️"],
    "thinking": ["🧠", "💭", "🤔", "💡", "⚡"],
    "complete": ["✅", "🎉", "🏁", "🎊", "🥳", "🍾"],
    "celebration": ["🎉", "🎊", "🥳", "🍾", "🎆", "🎇", "✨", "🌟", "💫", "🔥", "🚀"],
    "question": ["❓", "🤔", "💭", "🙋", "👋"],
    "code": ["💻", "⌨️", "🖥️", "📟", "🔧"],
    "tip": ["💡", "✨", "🎯", "📌", "🔑"],
    "file": ["📄", "📁", "📂", "🗂️"],
    "git": ["🔀", "📊", "🌿", "🏷️"],
    "build": ["🏗️", "📦", "🔨", "⚙️"],
    "test": ["🧪", "🔬", "✅", "📋"],
    "deploy": ["🚀", "🌐", "☁️", "📤"],
}

CHECKMARKS = {
    "success": "✓",
    "success_bold": "✔",
    "success_box": "☑",
    "error": "✗",
    "error_bold": "✘",
    "pending": "○",
    "in_progress": "◐",
    "complete": "●",
}

BORDERS = {
    "success": ("╔", "╗", "╚", "╝", "═", "║"),
    "error": ("┏", "┓", "┗", "┛", "━", "┃"),
    "info": ("┌", "┐", "└", "┘", "─", "│"),
    "celebration": ("╭", "╮", "╰", "╯", "─", "│"),
}

DIVIDERS = {
    "heavy": "━" * 50,
    "light": "─" * 50,
    "double": "═" * 50,
    "dotted": "┄" * 50,
    "stars": "✦" * 25,
    "sparkles": "✨ " * 12,
}


# ═══════════════════════════════════════════════════════════════════════════════
# SUCCESS PHRASES (SAM's cocky personality)
# ═══════════════════════════════════════════════════════════════════════════════

SUCCESS_PHRASES = [
    "Nailed it!",
    "Boom! Done.",
    "That's what I'm talking about!",
    "Easy money.",
    "Another one bites the dust.",
    "Crushed it.",
    "Like butter.",
    "Too easy.",
    "And THAT'S how it's done.",
    "You're welcome.",
    "Did someone say 'perfect'?",
    "Flawless execution.",
    "Watch and learn.",
    "That's the SAM guarantee.",
    "Smooth as silk.",
    "Mission accomplished.",
    "Bang! Success.",
    "First try. Obviously.",
    "Was there ever any doubt?",
    "I make this look easy.",
    "Chef's kiss.",
    "Perfection achieved.",
    "Task? Handled.",
    "Problem? What problem?",
    "And the crowd goes wild!",
]

ERROR_PHRASES = [
    "Okay, small hiccup...",
    "Well, that's interesting.",
    "Not gonna lie, that wasn't supposed to happen.",
    "Alright, let me try something else.",
    "One sec, I got this.",
    "That's... not ideal. But fixable!",
    "Hmm, that's fighting back.",
    "Challenge accepted.",
    "Alright, Plan B.",
    "Learning experience!",
    "Every master was once a disaster, right?",
    "Okay okay, I see what's happening here.",
    "Nothing I can't handle.",
]

PROGRESS_PHRASES = [
    "Working on it...",
    "Making moves...",
    "On it like a bonnet...",
    "Doing the thing...",
    "Magic happening...",
    "Give me a sec...",
    "Cooking something up...",
    "Almost there...",
    "Getting warmed up...",
    "Just a moment...",
    "Loading awesomeness...",
    "Flexing my circuits...",
]

COMPLETE_PHRASES = [
    "All done!",
    "That's a wrap!",
    "Finished!",
    "Complete!",
    "Mission complete!",
    "Done and dusted!",
    "That's all folks!",
    "Wrapped up nicely!",
]

TIP_PHRASES = [
    "Pro tip:",
    "Hot tip:",
    "Here's a thought:",
    "Quick tip:",
    "Heads up:",
    "FYI:",
    "Between you and me:",
    "Little secret:",
]


# ═══════════════════════════════════════════════════════════════════════════════
# STYLER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def get_emoji(category: str, count: int = 1) -> str:
    """Get random emoji(s) from a category"""
    emojis = EMOJIS.get(category, EMOJIS["info"])
    if count == 1:
        return random.choice(emojis)
    return " ".join(random.sample(emojis, min(count, len(emojis))))


def style_success(message: str, celebratory: bool = True) -> str:
    """Style a success message with flair"""
    emoji = get_emoji("success", 2 if celebratory else 1)
    phrase = random.choice(SUCCESS_PHRASES) if celebratory else ""

    if celebratory:
        return f"\n{emoji} **{phrase}**\n\n{message}\n"
    else:
        return f"✅ {message}"


def style_error(message: str, helpful: bool = True) -> str:
    """Style an error message - helpful, not scary"""
    emoji = get_emoji("error")
    phrase = random.choice(ERROR_PHRASES) if helpful else "Error:"

    return f"\n{emoji} **{phrase}**\n\n{message}\n"


def style_warning(message: str) -> str:
    """Style a warning message"""
    emoji = get_emoji("warning")
    return f"\n{emoji} **Heads up:** {message}\n"


def style_info(message: str) -> str:
    """Style an info message"""
    emoji = get_emoji("info")
    return f"\n{emoji} {message}\n"


def style_progress(message: str, percent: Optional[float] = None) -> str:
    """Style a progress message"""
    emoji = get_emoji("progress")
    phrase = random.choice(PROGRESS_PHRASES)

    if percent is not None:
        bar_filled = int(percent / 10)
        bar_empty = 10 - bar_filled
        progress_bar = f"[{'█' * bar_filled}{'░' * bar_empty}] {percent:.0f}%"
        return f"{emoji} {phrase} {progress_bar}\n{message}"
    else:
        return f"{emoji} {phrase}\n{message}"


def style_complete(message: str, items_completed: Optional[int] = None) -> str:
    """Style a completion message"""
    emojis = get_emoji("complete", 3)
    phrase = random.choice(COMPLETE_PHRASES)

    if items_completed:
        return f"\n{emojis}\n\n**{phrase}** {items_completed} items completed!\n\n{message}\n"
    else:
        return f"\n{emojis} **{phrase}**\n\n{message}\n"


def style_celebration(message: str) -> str:
    """Full celebration mode - big success!"""
    emojis = get_emoji("celebration", 5)

    return f"""
{DIVIDERS['sparkles']}

{emojis}

{message}

{emojis}

{DIVIDERS['sparkles']}
"""


def style_tip(message: str) -> str:
    """Style a helpful tip"""
    emoji = get_emoji("tip")
    phrase = random.choice(TIP_PHRASES)
    return f"\n{emoji} **{phrase}** {message}\n"


def style_code_block(code: str, language: str = "", title: str = "") -> str:
    """Style a code block with optional title"""
    emoji = get_emoji("code")
    header = f"{emoji} **{title}**\n" if title else ""
    return f"{header}```{language}\n{code}\n```"


def style_checklist(items: list, title: str = "") -> str:
    """Create a styled checklist"""
    header = f"**{title}**\n\n" if title else ""
    lines = []
    for item in items:
        status = item.get("status", "pending")
        text = item.get("text", str(item))

        if status == "complete":
            lines.append(f"  ✅ ~~{text}~~")
        elif status == "in_progress":
            lines.append(f"  🔄 **{text}** ← *in progress*")
        elif status == "error":
            lines.append(f"  ❌ {text}")
        else:
            lines.append(f"  ⬜ {text}")

    return header + "\n".join(lines)


def style_task_result(task: str, success: bool, details: str = "") -> str:
    """Style the result of a specific task"""
    if success:
        return f"  ✅ **{task}** {get_emoji('success')}\n     {details}" if details else f"  ✅ **{task}** {get_emoji('success')}"
    else:
        return f"  ❌ **{task}** {get_emoji('error')}\n     {details}" if details else f"  ❌ **{task}** {get_emoji('error')}"


def style_git_status(branch: str, ahead: int = 0, behind: int = 0, changes: int = 0) -> str:
    """Style git status info"""
    emoji = get_emoji("git")
    parts = [f"{emoji} **{branch}**"]

    if ahead > 0:
        parts.append(f"↑{ahead}")
    if behind > 0:
        parts.append(f"↓{behind}")
    if changes > 0:
        parts.append(f"📝 {changes} changes")

    return " ".join(parts)


def style_build_result(success: bool, duration: float = 0, warnings: int = 0, errors: int = 0) -> str:
    """Style build result"""
    if success:
        emoji = get_emoji("build")
        celebration = get_emoji("success", 2)
        result = f"\n{celebration} **Build Successful!** {celebration}\n"
        if duration:
            result += f"\n⏱️ Completed in {duration:.1f}s"
        if warnings:
            result += f"\n⚠️ {warnings} warning(s)"
        return result
    else:
        return style_error(f"Build failed with {errors} error(s)", helpful=True)


def style_test_result(passed: int, failed: int, skipped: int = 0) -> str:
    """Style test results"""
    total = passed + failed + skipped

    if failed == 0:
        emojis = get_emoji("celebration", 3)
        return f"""
{emojis} **All Tests Passing!** {emojis}

  ✅ {passed}/{total} passed
  {'⏭️ ' + str(skipped) + ' skipped' if skipped else ''}
"""
    else:
        return f"""
🧪 **Test Results**

  ✅ {passed} passed
  ❌ {failed} failed
  {'⏭️ ' + str(skipped) + ' skipped' if skipped else ''}
"""


def style_file_operation(operation: str, path: str, success: bool = True) -> str:
    """Style file operation results"""
    ops = {
        "create": ("📝 Created", "Created"),
        "edit": ("✏️ Modified", "Modified"),
        "delete": ("🗑️ Deleted", "Deleted"),
        "read": ("📖 Read", "Read"),
        "move": ("📦 Moved", "Moved"),
        "copy": ("📋 Copied", "Copied"),
    }

    emoji_text, plain_text = ops.get(operation, ("📄", operation.title()))

    if success:
        return f"  {emoji_text}: `{path}` ✓"
    else:
        return f"  ❌ Failed to {plain_text.lower()}: `{path}`"


def style_summary_box(title: str, items: dict, style: str = "info") -> str:
    """Create a styled summary box"""
    tl, tr, bl, br, h, v = BORDERS.get(style, BORDERS["info"])

    # Calculate width
    max_key = max(len(str(k)) for k in items.keys()) if items else 10
    max_val = max(len(str(v)) for v in items.values()) if items else 10
    width = max(len(title) + 4, max_key + max_val + 7)

    # Build box
    lines = []
    lines.append(f"{tl}{h * (width + 2)}{tr}")
    lines.append(f"{v} {title.center(width)} {v}")
    lines.append(f"{v}{h * (width + 2)}{v}")

    for key, value in items.items():
        line = f"  {key}: {value}"
        lines.append(f"{v} {line.ljust(width)} {v}")

    lines.append(f"{bl}{h * (width + 2)}{br}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# HIGH-LEVEL RESPONSE WRAPPER
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StyledResponse:
    """A response with styling metadata"""
    content: str
    type: ResponseType
    raw: str  # Original unstyled content


def style_response(
    message: str,
    response_type: ResponseType = ResponseType.INFO,
    context: Optional[dict] = None
) -> StyledResponse:
    """
    Main entry point for styling any response.

    Args:
        message: The message to style
        response_type: Type of response (success, error, etc.)
        context: Optional context dict with extra info

    Returns:
        StyledResponse with formatted content
    """
    context = context or {}

    styled = message  # Default

    if response_type == ResponseType.SUCCESS:
        styled = style_success(message, celebratory=context.get("celebratory", True))

    elif response_type == ResponseType.ERROR:
        styled = style_error(message, helpful=context.get("helpful", True))

    elif response_type == ResponseType.WARNING:
        styled = style_warning(message)

    elif response_type == ResponseType.INFO:
        styled = style_info(message)

    elif response_type == ResponseType.PROGRESS:
        styled = style_progress(message, percent=context.get("percent"))

    elif response_type == ResponseType.COMPLETE:
        styled = style_complete(message, items_completed=context.get("items"))

    elif response_type == ResponseType.CELEBRATION:
        styled = style_celebration(message)

    elif response_type == ResponseType.TIP:
        styled = style_tip(message)

    elif response_type == ResponseType.CODE:
        styled = style_code_block(
            message,
            language=context.get("language", ""),
            title=context.get("title", "")
        )

    return StyledResponse(content=styled, type=response_type, raw=message)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI DEMO
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        print("\n" + "=" * 60)
        print("SAM RESPONSE STYLER DEMO")
        print("=" * 60)

        print("\n--- SUCCESS STYLES ---")
        print(style_success("Build completed successfully!", celebratory=True))
        print(style_success("File saved.", celebratory=False))

        print("\n--- ERROR STYLES ---")
        print(style_error("Could not connect to database"))

        print("\n--- PROGRESS STYLES ---")
        print(style_progress("Compiling project...", percent=45))

        print("\n--- COMPLETE STYLES ---")
        print(style_complete("All tasks finished", items_completed=5))

        print("\n--- CELEBRATION ---")
        print(style_celebration("You just deployed to production!"))

        print("\n--- CHECKLIST ---")
        items = [
            {"text": "Install dependencies", "status": "complete"},
            {"text": "Run tests", "status": "complete"},
            {"text": "Deploy to staging", "status": "in_progress"},
            {"text": "Deploy to production", "status": "pending"},
        ]
        print(style_checklist(items, title="Deployment Checklist"))

        print("\n--- BUILD RESULT ---")
        print(style_build_result(success=True, duration=12.5, warnings=2))

        print("\n--- TEST RESULT ---")
        print(style_test_result(passed=42, failed=0, skipped=3))

        print("\n--- FILE OPERATIONS ---")
        print(style_file_operation("create", "src/new_file.py"))
        print(style_file_operation("edit", "package.json"))
        print(style_file_operation("delete", "temp.log"))

        print("\n--- SUMMARY BOX ---")
        print(style_summary_box("Build Summary", {
            "Duration": "12.5s",
            "Files": "42",
            "Warnings": "2",
            "Errors": "0",
        }, style="success"))

        print("\n--- GIT STATUS ---")
        print(style_git_status("main", ahead=3, changes=5))

        print("\n--- TIP ---")
        print(style_tip("You can use `git stash` to temporarily save changes"))

    else:
        print("SAM Response Styler")
        print("\nUsage: python response_styler.py demo")
        print("\nThis module provides styled responses with:")
        print("  - Success celebrations with emojis")
        print("  - Friendly error messages")
        print("  - Progress indicators")
        print("  - Build/test result formatting")
        print("  - SAM's personality in every response")
