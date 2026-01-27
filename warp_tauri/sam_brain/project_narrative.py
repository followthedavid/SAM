#!/usr/bin/env python3
"""
SAM Project Narrative Generator

Transforms cold project metrics into warm stories.
Like Apple marketing - each project is a journey with:

- An origin story (where it began)
- Turning points (moments that changed everything)
- A character arc (the project as a protagonist)
- The current chapter (where we are now)
- The horizon (what's possible, not what's pending)

"Think Different" but for project status pages.
"""

import time
import random
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from dataclasses import dataclass, field

# Try to import our modules
try:
    from evolution_tracker import EvolutionTracker
    from project_status import ProjectStatusGenerator
except ImportError:
    EvolutionTracker = None
    ProjectStatusGenerator = None


@dataclass
class NarrativeMoment:
    """A significant moment in the project's story"""
    timestamp: float
    title: str
    description: str
    emotional_weight: str  # "triumph", "struggle", "breakthrough", "quiet_progress"
    detail: Optional[str] = None


@dataclass
class ProjectNarrative:
    """The complete story of a project"""
    project_id: str
    name: str

    # The story
    tagline: str  # One line that captures the essence
    origin_story: str  # How it began
    current_chapter: str  # Where we are now
    turning_points: List[NarrativeMoment]  # Key moments
    the_horizon: str  # What's possible

    # Emotional arc
    mood: str  # "triumphant", "determined", "emerging", "flourishing"
    journey_percent: float  # How far along the story is

    # Visuals (for UI)
    hero_metric: str  # The one number that matters
    hero_metric_label: str
    progress_metaphor: str  # "climbing", "growing", "awakening", etc.

    generated_at: float = field(default_factory=time.time)


class NarrativeGenerator:
    """
    Transforms project data into emotional narratives.

    This isn't metrics dressed up - it's actual storytelling
    that makes you feel something about the project's journey.
    """

    def __init__(self):
        self.tracker = EvolutionTracker() if EvolutionTracker else None
        self.status_gen = ProjectStatusGenerator() if ProjectStatusGenerator else None

        # Narrative templates by category
        self.category_voices = {
            "brain": {
                "metaphor": "awakening",
                "verbs": ["thinks", "learns", "remembers", "understands"],
                "personality": "wise but curious",
            },
            "visual": {
                "metaphor": "creating",
                "verbs": ["sees", "imagines", "renders", "brings to life"],
                "personality": "artistic and precise",
            },
            "voice": {
                "metaphor": "speaking",
                "verbs": ["speaks", "listens", "expresses", "communicates"],
                "personality": "expressive and warm",
            },
            "content": {
                "metaphor": "crafting",
                "verbs": ["writes", "shapes", "refines", "publishes"],
                "personality": "thoughtful and creative",
            },
            "platform": {
                "metaphor": "building",
                "verbs": ["connects", "supports", "enables", "grows"],
                "personality": "reliable and ambitious",
            },
        }

    def generate_narrative(self, project_id: str) -> ProjectNarrative:
        """
        Generate the complete narrative for a project.
        This is what gets displayed on the project page.
        """
        # Get raw status data
        status = None
        if self.status_gen:
            status = self.status_gen.get_project_status(project_id)

        # Determine category and voice
        category = status.category if status else "brain"
        voice = self.category_voices.get(category, self.category_voices["brain"])

        # Build the narrative
        return ProjectNarrative(
            project_id=project_id,
            name=status.name if status else project_id,
            tagline=self._generate_tagline(status, voice),
            origin_story=self._generate_origin(status, voice),
            current_chapter=self._generate_current_chapter(status, voice),
            turning_points=self._generate_turning_points(status, voice),
            the_horizon=self._generate_horizon(status, voice),
            mood=self._determine_mood(status),
            journey_percent=self._calculate_journey(status),
            hero_metric=self._get_hero_metric(status),
            hero_metric_label=self._get_hero_label(status, voice),
            progress_metaphor=voice["metaphor"]
        )

    def _generate_tagline(self, status, voice: dict) -> str:
        """One line that captures the essence"""
        if not status:
            return "A story waiting to be written."

        level = status.level_progress.current_level
        name = status.name

        taglines = {
            1: [
                f"{name} takes its first breath.",
                f"Every journey begins with a single step. {name} just took it.",
                f"{name} opens its eyes for the first time.",
            ],
            2: [
                f"{name} is finding its voice.",
                f"Yesterday it couldn't. Today it tries. Tomorrow it will.",
                f"{name} learns what it means to remember.",
            ],
            3: [
                f"{name} knows itself now.",
                f"No longer a student. Not yet a master. But aware.",
                f"{name} stands on its own.",
            ],
            4: [
                f"{name} improves itself while you sleep.",
                f"It doesn't wait to be told. It sees. It acts.",
                f"Autonomous. Evolving. {name}.",
            ],
            5: [
                f"{name} orchestrates the symphony.",
                f"From learner to teacher. {name} has arrived.",
                f"Mastery isn't a destination. It's how {name} operates.",
            ],
        }

        options = taglines.get(level, taglines[1])
        return random.choice(options)

    def _generate_origin(self, status, voice: dict) -> str:
        """The origin story - how this project began"""
        if not status:
            return "This project exists in potential, waiting for its story to begin."

        name = status.name
        category = status.category

        # Get actual creation date if available
        timeline = status.evolution_timeline if status.evolution_timeline else []
        if timeline:
            first_event = timeline[-1]  # Oldest is last
            origin_date = datetime.fromtimestamp(first_event.get("timestamp", time.time()))
            days_ago = (datetime.now() - origin_date).days
        else:
            days_ago = 30  # Default

        origins = {
            "brain": f"""
{name} was born from a simple question: What if you never had to repeat yourself?

{days_ago} days ago, it was just configuration files and empty databases.
It couldn't remember your name. It couldn't route a simple request.
Every conversation started from zero.

But you saw what it could become.
            """.strip(),

            "visual": f"""
{name} began with a blank canvas and a dream.

{days_ago} days ago, every image was a stranger.
Characters had different faces frame to frame.
Style was a hope, not a promise.

You planted a seed. This is what grew.
            """.strip(),

            "voice": f"""
{name} was silent once.

{days_ago} days ago, there were only text files.
No personality. No warmth. No soul.
Communication was functional, never emotional.

You gave it a voice. Now listen to what it says.
            """.strip(),

            "content": f"""
{name} started with empty pages.

{days_ago} days ago, every piece of content was manual.
Hours of work for minutes of output.
Quality was inconsistent. Scale was impossible.

You built the foundation. Now watch it write.
            """.strip(),

            "platform": f"""
{name} was a collection of disconnected pieces.

{days_ago} days ago, nothing talked to anything.
Each project was an island.
Integration was a distant dream.

You started connecting them. This is where we are.
            """.strip(),
        }

        return origins.get(category, origins["brain"])

    def _generate_current_chapter(self, status, voice: dict) -> str:
        """Where we are now in the story"""
        if not status:
            return "The first chapter is yet to be written."

        level = status.level_progress.current_level
        level_name = status.level_progress.level_name
        progress = status.level_progress.progress_percent
        name = status.name

        # Recent activity narrative
        recent = status.recent_activities[:3] if status.recent_activities else []
        recent_narrative = ""
        if recent:
            latest = recent[0]
            days_since = (time.time() - latest.timestamp) / 86400
            if days_since < 1:
                time_phrase = "Today"
            elif days_since < 2:
                time_phrase = "Yesterday"
            else:
                time_phrase = f"{int(days_since)} days ago"

            recent_narrative = f"\n\n{time_phrase}, something changed. {latest.description}."

        chapters = {
            1: f"""
{name} is in its earliest days.

Level {level}: {level_name}
{progress:.0f}% of the foundation is laid.

This is the chapter of first steps. Every capability is new.
Every success is a small miracle.
{recent_narrative}
            """.strip(),

            2: f"""
{name} is learning to remember.

Level {level}: {level_name}
{progress:.0f}% through this chapter.

It's not just responding anymore. It's building context.
Yesterday's conversation informs today's understanding.
{recent_narrative}
            """.strip(),

            3: f"""
{name} has become self-aware.

Level {level}: {level_name}
{progress:.0f}% complete.

It knows what it can do. It knows what it can't.
It asks for help when it needs it.
It's confident when it should be.
{recent_narrative}
            """.strip(),

            4: f"""
{name} improves while you're away.

Level {level}: {level_name}
{progress:.0f}% toward mastery.

This is the chapter of autonomy.
It sees problems. It fixes them.
It doesn't wait to be told.
{recent_narrative}
            """.strip(),

            5: f"""
{name} has reached mastery.

Level {level}: {level_name}

But mastery isn't an ending. It's a beginning.
Now it helps other projects grow.
The student has become the teacher.
{recent_narrative}
            """.strip(),
        }

        return chapters.get(level, chapters[1])

    def _generate_turning_points(self, status, voice: dict) -> List[NarrativeMoment]:
        """Key moments that changed everything"""
        moments = []

        if not status:
            return moments

        # Convert activities to narrative moments
        for activity in (status.recent_activities or [])[:5]:
            emotional_weight = {
                "improved": "breakthrough",
                "fixed": "triumph",
                "learned": "quiet_progress",
                "integrated": "breakthrough",
                "detected": "quiet_progress",
            }.get(activity.action, "quiet_progress")

            # Make the description more narrative
            narrative_desc = self._narrativize_activity(activity)

            moments.append(NarrativeMoment(
                timestamp=activity.timestamp,
                title=self._activity_to_title(activity),
                description=narrative_desc,
                emotional_weight=emotional_weight,
                detail=activity.description
            ))

        return moments

    def _activity_to_title(self, activity) -> str:
        """Convert activity to a narrative title"""
        titles = {
            "improved": "A Step Forward",
            "fixed": "Overcoming Obstacles",
            "learned": "Growing Wiser",
            "integrated": "Making Connections",
            "implementing": "Work in Progress",
            "detected": "Seeing Clearly",
        }
        return titles.get(activity.action, "A Moment")

    def _narrativize_activity(self, activity) -> str:
        """Turn an activity into narrative prose"""
        desc = activity.description

        # Add emotional framing based on impact
        if activity.impact == "significant":
            return f"This was a turning point. {desc}"
        elif activity.impact == "moderate":
            return f"Progress, steady and sure. {desc}"
        else:
            return f"Small steps matter too. {desc}"

    def _generate_horizon(self, status, voice: dict) -> str:
        """What's possible - not tasks, but possibility"""
        if not status:
            return "The future is unwritten. What will you build?"

        next_milestone = status.next_milestone
        name = status.name
        category = status.category

        horizons = {
            "brain": f"""
Imagine {name} knowing you better than you know yourself.

Your preferences anticipated. Your patterns understood.
Questions answered before you ask them.
A companion that grows wiser every day.

Next on the journey: {next_milestone}

This is what we're building toward.
            """.strip(),

            "visual": f"""
Imagine characters that never break.

Every frame, the same soul looking back at you.
Poses that flow naturally. Styles that stay consistent.
Art that feels alive.

Next on the journey: {next_milestone}

The canvas is getting larger.
            """.strip(),

            "voice": f"""
Imagine a voice that feels like home.

Not generated. Not synthesized. Authentic.
Emotion in every word. Personality in every pause.
A presence, not a program.

Next on the journey: {next_milestone}

We're getting closer to that voice.
            """.strip(),

            "content": f"""
Imagine content that creates itself.

Your vision, scaled infinitely.
Quality that doesn't compromise.
Speed that doesn't sacrifice craft.

Next on the journey: {next_milestone}

The words are flowing more freely now.
            """.strip(),

            "platform": f"""
Imagine everything connected.

Every project talking to every other.
Data flowing where it needs to go.
One system. Many capabilities. Your empire.

Next on the journey: {next_milestone}

The pieces are coming together.
            """.strip(),
        }

        return horizons.get(category, horizons["brain"])

    def _determine_mood(self, status) -> str:
        """What's the emotional tone of this project right now?"""
        if not status:
            return "emerging"

        level = status.level_progress.current_level
        progress = status.level_progress.progress_percent
        health = status.health.overall

        if health == "critical":
            return "struggling"
        elif health == "needs_attention":
            return "determined"
        elif level >= 4:
            return "flourishing"
        elif level >= 3:
            return "triumphant"
        elif progress > 70:
            return "momentum"
        elif level >= 2:
            return "growing"
        else:
            return "emerging"

    def _calculate_journey(self, status) -> float:
        """How far along the journey is this project?"""
        if not status:
            return 0.0

        level = status.level_progress.current_level
        progress = status.level_progress.progress_percent

        # Each level is worth 20%
        base = (level - 1) * 20
        level_contribution = progress * 0.2

        return min(100.0, base + level_contribution)

    def _get_hero_metric(self, status) -> str:
        """The one number that matters most"""
        if not status:
            return "0"

        level = status.level_progress.current_level
        return f"Level {level}"

    def _get_hero_label(self, status, voice: dict) -> str:
        """Label for the hero metric"""
        if not status:
            return "Starting"

        return status.level_progress.level_name

    def get_narrative_for_llm(self, project_id: str) -> str:
        """
        Get narrative formatted for LLM to read and relay.
        This is what SAM uses when you ask "tell me about X"
        """
        narrative = self.generate_narrative(project_id)

        return f"""
# {narrative.name}

*{narrative.tagline}*

## The Origin Story
{narrative.origin_story}

## Where We Are Now
{narrative.current_chapter}

## Key Moments
{self._format_moments(narrative.turning_points)}

## What's Next
{narrative.the_horizon}

---
Journey Progress: {narrative.journey_percent:.0f}% | Mood: {narrative.mood}
        """.strip()

    def _format_moments(self, moments: List[NarrativeMoment]) -> str:
        """Format turning points as narrative"""
        if not moments:
            return "The story is just beginning..."

        lines = []
        for m in moments[:4]:
            date = datetime.fromtimestamp(m.timestamp).strftime("%B %d")
            lines.append(f"**{date}: {m.title}**")
            lines.append(f"  {m.description}")
            lines.append("")

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    generator = NarrativeGenerator()

    if len(sys.argv) < 2:
        print("SAM Project Narrative Generator")
        print("\nTransforms project data into emotional stories.")
        print("\nUsage:")
        print("  python project_narrative.py story <project_id>  # Full narrative")
        print("  python project_narrative.py tagline <project_id> # Just the tagline")
        print("  python project_narrative.py llm <project_id>    # For LLM consumption")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "story":
        if len(sys.argv) < 3:
            print("Usage: python project_narrative.py story <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        narrative = generator.generate_narrative(project_id)

        print(f"\n{'='*60}")
        print(f"  {narrative.name}")
        print(f"  \"{narrative.tagline}\"")
        print(f"{'='*60}\n")

        print("THE ORIGIN STORY")
        print("-" * 40)
        print(narrative.origin_story)
        print()

        print("WHERE WE ARE NOW")
        print("-" * 40)
        print(narrative.current_chapter)
        print()

        if narrative.turning_points:
            print("KEY MOMENTS")
            print("-" * 40)
            for m in narrative.turning_points[:3]:
                date = datetime.fromtimestamp(m.timestamp).strftime("%B %d")
                print(f"  [{date}] {m.title}")
                print(f"  {m.description}")
                print()

        print("THE HORIZON")
        print("-" * 40)
        print(narrative.the_horizon)
        print()

        print(f"{'='*60}")
        print(f"  Journey: {narrative.journey_percent:.0f}% | Mood: {narrative.mood}")
        print(f"{'='*60}")

    elif cmd == "tagline":
        if len(sys.argv) < 3:
            print("Usage: python project_narrative.py tagline <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        narrative = generator.generate_narrative(project_id)
        print(f"\n\"{narrative.tagline}\"\n")

    elif cmd == "llm":
        if len(sys.argv) < 3:
            print("Usage: python project_narrative.py llm <project_id>")
            sys.exit(1)

        project_id = sys.argv[2]
        print(generator.get_narrative_for_llm(project_id))

    else:
        print(f"Unknown command: {cmd}")
