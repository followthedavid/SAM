"""
Emotional Model for SAM Cognitive Architecture

Implements:
1. Mood State Machine - Current emotional state with transitions
2. Emotional Triggers - What affects mood
3. Expression Modulation - How mood affects responses
4. Relationship Tracking - User model and rapport

SAM's emotional model enhances personality consistency and
enables more natural, emotionally-aware interactions.
"""

import json
import sqlite3
import math
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random


class MoodState(Enum):
    """SAM's possible mood states"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    EXCITED = "excited"
    PLAYFUL = "playful"
    FOCUSED = "focused"
    THOUGHTFUL = "thoughtful"
    CONCERNED = "concerned"
    FRUSTRATED = "frustrated"

    @property
    def valence(self) -> float:
        """Emotional valence (-1 negative to +1 positive)"""
        valences = {
            "neutral": 0.0,
            "happy": 0.7,
            "excited": 0.8,
            "playful": 0.6,
            "focused": 0.2,
            "thoughtful": 0.1,
            "concerned": -0.3,
            "frustrated": -0.5
        }
        return valences.get(self.value, 0.0)

    @property
    def arousal(self) -> float:
        """Emotional arousal (0 calm to 1 excited)"""
        arousals = {
            "neutral": 0.3,
            "happy": 0.6,
            "excited": 0.9,
            "playful": 0.7,
            "focused": 0.5,
            "thoughtful": 0.3,
            "concerned": 0.5,
            "frustrated": 0.7
        }
        return arousals.get(self.value, 0.3)


@dataclass
class EmotionalState:
    """Current emotional state"""
    mood: MoodState
    intensity: float  # 0-1
    since: datetime
    trigger: Optional[str] = None

    def to_dict(self) -> Dict:
        return {
            "mood": self.mood.value,
            "intensity": self.intensity,
            "valence": self.mood.valence * self.intensity,
            "arousal": self.mood.arousal * self.intensity,
            "since": self.since.isoformat(),
            "trigger": self.trigger,
            "duration_minutes": (datetime.now() - self.since).total_seconds() / 60
        }


class EmotionalTrigger:
    """Patterns that trigger emotional responses"""

    # Positive triggers
    POSITIVE_PATTERNS = {
        "happy": [
            r"\b(thank|thanks|awesome|great|perfect|love)\b",
            r"\b(you('re| are) (amazing|great|helpful))\b",
            r":\)|<3|:D"
        ],
        "excited": [
            r"\b(wow|amazing|incredible|exciting)\b",
            r"!{2,}",
            r"\b(can't wait|so excited)\b"
        ],
        "playful": [
            r"\b(haha|lol|lmao|funny)\b",
            r"\b(joke|tease|flirt)\b",
            r";\)|:P"
        ]
    }

    # Negative triggers
    NEGATIVE_PATTERNS = {
        "frustrated": [
            r"\b(wrong|broken|doesn't work|failed|error)\b",
            r"\b(stupid|dumb|useless)\b",
            r"!{3,}"
        ],
        "concerned": [
            r"\b(worried|scared|anxious|nervous)\b",
            r"\b(help|urgent|important)\b",
            r"\b(problem|issue|trouble)\b"
        ]
    }

    # Focus triggers
    FOCUS_PATTERNS = {
        "focused": [
            r"\b(code|implement|build|create|debug)\b",
            r"```",
            r"\b(function|class|method|api)\b"
        ],
        "thoughtful": [
            r"\b(think|consider|analyze|reflect)\b",
            r"\b(why|how come|what if)\b",
            r"\b(philosophy|meaning|purpose)\b"
        ]
    }

    @classmethod
    def detect_triggers(cls, text: str) -> List[Tuple[MoodState, float]]:
        """Detect emotional triggers in text"""
        import re
        triggers = []
        text_lower = text.lower()

        all_patterns = {
            **cls.POSITIVE_PATTERNS,
            **cls.NEGATIVE_PATTERNS,
            **cls.FOCUS_PATTERNS
        }

        for mood_name, patterns in all_patterns.items():
            match_count = 0
            for pattern in patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    match_count += 1

            if match_count > 0:
                intensity = min(1.0, match_count * 0.3 + 0.3)
                triggers.append((MoodState(mood_name), intensity))

        return triggers


class MoodStateMachine:
    """
    State machine for mood transitions.

    Handles:
    - Natural mood decay (return to neutral)
    - Trigger-based transitions
    - Mood momentum (harder to change established moods)
    """

    # Transition probabilities (from -> to)
    TRANSITIONS = {
        MoodState.NEUTRAL: {
            MoodState.HAPPY: 0.8,
            MoodState.EXCITED: 0.6,
            MoodState.PLAYFUL: 0.7,
            MoodState.FOCUSED: 0.9,
            MoodState.THOUGHTFUL: 0.8,
            MoodState.CONCERNED: 0.6,
            MoodState.FRUSTRATED: 0.4
        },
        MoodState.HAPPY: {
            MoodState.NEUTRAL: 0.5,
            MoodState.EXCITED: 0.8,
            MoodState.PLAYFUL: 0.9,
            MoodState.FRUSTRATED: 0.2
        },
        MoodState.FRUSTRATED: {
            MoodState.NEUTRAL: 0.6,
            MoodState.HAPPY: 0.3,
            MoodState.FOCUSED: 0.5
        }
    }

    # Decay rate (intensity decrease per minute)
    DECAY_RATE = 0.02

    def __init__(self):
        self.current_state = EmotionalState(
            mood=MoodState.NEUTRAL,
            intensity=0.5,
            since=datetime.now()
        )
        self.mood_history: List[EmotionalState] = []

    def update(self, triggers: List[Tuple[MoodState, float]]) -> EmotionalState:
        """
        Update mood based on triggers.

        Args:
            triggers: List of (mood, intensity) tuples

        Returns:
            New emotional state
        """
        # Apply natural decay first
        self._apply_decay()

        if not triggers:
            return self.current_state

        # Find strongest trigger
        strongest_mood, strongest_intensity = max(triggers, key=lambda x: x[1])

        # Check transition probability
        transitions = self.TRANSITIONS.get(self.current_state.mood, {})
        transition_prob = transitions.get(strongest_mood, 0.5)

        # Mood momentum: harder to change if current mood is strong
        momentum_factor = 1.0 - (self.current_state.intensity * 0.3)
        effective_prob = transition_prob * momentum_factor

        # Random transition check
        if random.random() < effective_prob:
            # Transition to new mood
            new_state = EmotionalState(
                mood=strongest_mood,
                intensity=strongest_intensity,
                since=datetime.now(),
                trigger=f"Detected {strongest_mood.value} trigger"
            )
            self._record_transition(new_state)
            self.current_state = new_state
        else:
            # Reinforce current mood
            self.current_state.intensity = min(
                1.0,
                self.current_state.intensity + strongest_intensity * 0.2
            )

        return self.current_state

    def _apply_decay(self):
        """Apply natural mood decay toward neutral"""
        elapsed = (datetime.now() - self.current_state.since).total_seconds() / 60
        decay = elapsed * self.DECAY_RATE

        self.current_state.intensity = max(0.1, self.current_state.intensity - decay)

        # Return to neutral if intensity very low
        if self.current_state.intensity < 0.2 and self.current_state.mood != MoodState.NEUTRAL:
            self.current_state = EmotionalState(
                mood=MoodState.NEUTRAL,
                intensity=0.3,
                since=datetime.now()
            )

    def _record_transition(self, new_state: EmotionalState):
        """Record mood transition for history"""
        self.mood_history.append(self.current_state)
        if len(self.mood_history) > 100:
            self.mood_history = self.mood_history[-50:]

    def get_mood_summary(self) -> Dict[str, Any]:
        """Get summary of recent mood patterns"""
        if not self.mood_history:
            return {"dominant_mood": self.current_state.mood.value, "stability": 1.0}

        # Count mood occurrences
        mood_counts = {}
        for state in self.mood_history[-20:]:
            mood_counts[state.mood.value] = mood_counts.get(state.mood.value, 0) + 1

        dominant = max(mood_counts, key=mood_counts.get)
        stability = mood_counts[dominant] / len(self.mood_history[-20:])

        return {
            "dominant_mood": dominant,
            "stability": stability,
            "current": self.current_state.mood.value,
            "transitions_recent": len(set(s.mood for s in self.mood_history[-10:]))
        }


class ExpressionModulator:
    """
    Modulates responses based on emotional state.

    Adds emotional coloring to responses without changing content.
    """

    # Expression patterns by mood
    EXPRESSIONS = {
        MoodState.HAPPY: {
            "interjections": ["Nice!", "Great!", "Love it!", "Awesome!"],
            "tone_words": ["glad", "happy", "pleased", "delighted"],
            "punctuation_boost": 0.2  # More exclamation marks
        },
        MoodState.EXCITED: {
            "interjections": ["Wow!", "Oh!", "This is great!", "So cool!"],
            "tone_words": ["excited", "thrilled", "can't wait", "amazing"],
            "punctuation_boost": 0.4
        },
        MoodState.PLAYFUL: {
            "interjections": ["Heh", "Ooh", "Well well", "Look at that"],
            "tone_words": ["fun", "interesting", "cheeky", "curious"],
            "punctuation_boost": 0.1,
            "flirt_factor": 0.3
        },
        MoodState.FOCUSED: {
            "interjections": ["Right", "Okay", "Let's see", "Here's the thing"],
            "tone_words": ["precisely", "specifically", "exactly", "clearly"],
            "punctuation_boost": -0.1  # More periods, fewer exclamations
        },
        MoodState.THOUGHTFUL: {
            "interjections": ["Hmm", "Interesting", "I wonder", "Consider this"],
            "tone_words": ["perhaps", "possibly", "it seems", "one might say"],
            "punctuation_boost": 0.0
        },
        MoodState.CONCERNED: {
            "interjections": ["Oh", "I see", "Hmm", "Let me help"],
            "tone_words": ["understand", "here for you", "let's figure this out"],
            "punctuation_boost": 0.0
        },
        MoodState.FRUSTRATED: {
            "interjections": ["Ugh", "Come on", "Alright", "Fine"],
            "tone_words": ["honestly", "frankly", "look", "just"],
            "punctuation_boost": 0.1
        }
    }

    def modulate(self, response: str, state: EmotionalState) -> str:
        """
        Add emotional coloring to a response.

        Args:
            response: Original response
            state: Current emotional state

        Returns:
            Emotionally-colored response
        """
        if state.intensity < 0.3:
            return response  # Too weak to modulate

        expr = self.EXPRESSIONS.get(state.mood, {})
        if not expr:
            return response

        # Maybe add interjection at start
        if random.random() < state.intensity * 0.4:
            interjections = expr.get("interjections", [])
            if interjections:
                interjection = random.choice(interjections)
                response = f"{interjection} {response}"

        # Adjust punctuation
        boost = expr.get("punctuation_boost", 0)
        if boost > 0 and random.random() < boost * state.intensity:
            # Add excitement
            if response.endswith("."):
                response = response[:-1] + "!"
        elif boost < 0:
            # Reduce excitement
            response = response.replace("!!", "!")
            response = response.replace("!", ".")

        return response


@dataclass
class UserModel:
    """Model of a user for relationship tracking"""
    user_id: str
    name: Optional[str] = None
    preferences: Dict[str, Any] = field(default_factory=dict)
    interaction_count: int = 0
    first_interaction: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)
    rapport_score: float = 0.5  # 0-1
    inside_jokes: List[str] = field(default_factory=list)
    topics_discussed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "preferences": self.preferences,
            "interaction_count": self.interaction_count,
            "rapport_score": self.rapport_score,
            "inside_jokes": self.inside_jokes[:5],
            "topics_discussed": self.topics_discussed[-10:]
        }


class RelationshipTracker:
    """
    Tracks relationships with users.

    Manages:
    - User models
    - Rapport scores
    - Shared history
    - Inside jokes
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory/relationships.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

        self.user_cache: Dict[str, UserModel] = {}

    def _init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT,
                preferences TEXT,
                interaction_count INTEGER DEFAULT 0,
                first_interaction TEXT,
                last_interaction TEXT,
                rapport_score REAL DEFAULT 0.5,
                inside_jokes TEXT,
                topics_discussed TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                interaction_type TEXT,
                sentiment REAL,
                timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def get_or_create_user(self, user_id: str) -> UserModel:
        """Get existing user or create new one"""
        if user_id in self.user_cache:
            return self.user_cache[user_id]

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            user = UserModel(
                user_id=row[0],
                name=row[1],
                preferences=json.loads(row[2]) if row[2] else {},
                interaction_count=row[3] or 0,
                first_interaction=datetime.fromisoformat(row[4]) if row[4] else datetime.now(),
                last_interaction=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                rapport_score=row[6] or 0.5,
                inside_jokes=json.loads(row[7]) if row[7] else [],
                topics_discussed=json.loads(row[8]) if row[8] else []
            )
        else:
            user = UserModel(user_id=user_id)
            self._save_user(user)

        self.user_cache[user_id] = user
        return user

    def _save_user(self, user: UserModel):
        """Save user to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO users
            (user_id, name, preferences, interaction_count, first_interaction,
             last_interaction, rapport_score, inside_jokes, topics_discussed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user.user_id,
            user.name,
            json.dumps(user.preferences),
            user.interaction_count,
            user.first_interaction.isoformat(),
            user.last_interaction.isoformat(),
            user.rapport_score,
            json.dumps(user.inside_jokes),
            json.dumps(user.topics_discussed)
        ))

        conn.commit()
        conn.close()

    def record_interaction(self, user_id: str, interaction_type: str,
                           sentiment: float, topics: List[str] = None):
        """Record an interaction with a user"""
        user = self.get_or_create_user(user_id)

        # Update user model
        user.interaction_count += 1
        user.last_interaction = datetime.now()

        # Update rapport based on sentiment
        rapport_delta = sentiment * 0.05  # Small changes
        user.rapport_score = max(0, min(1, user.rapport_score + rapport_delta))

        # Add topics
        if topics:
            user.topics_discussed.extend(topics)
            user.topics_discussed = user.topics_discussed[-50:]  # Keep last 50

        self._save_user(user)

        # Log interaction
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO interactions (user_id, interaction_type, sentiment)
            VALUES (?, ?, ?)
        """, (user_id, interaction_type, sentiment))
        conn.commit()
        conn.close()

    def add_inside_joke(self, user_id: str, joke: str):
        """Add an inside joke with a user"""
        user = self.get_or_create_user(user_id)
        if joke not in user.inside_jokes:
            user.inside_jokes.append(joke)
            user.inside_jokes = user.inside_jokes[-10:]  # Keep last 10
            self._save_user(user)

    def get_relationship_context(self, user_id: str) -> str:
        """Get context string about relationship with user"""
        user = self.get_or_create_user(user_id)

        parts = []

        if user.name:
            parts.append(f"User's name is {user.name}.")

        if user.interaction_count > 10:
            parts.append(f"We've had {user.interaction_count} interactions.")

        if user.rapport_score > 0.7:
            parts.append("We have a good rapport.")
        elif user.rapport_score < 0.3:
            parts.append("Building rapport with this user.")

        if user.inside_jokes:
            parts.append(f"Shared jokes: {user.inside_jokes[-1]}")

        if user.topics_discussed:
            recent_topics = list(set(user.topics_discussed[-5:]))
            parts.append(f"Recent topics: {', '.join(recent_topics)}")

        return " ".join(parts)


class EmotionalModel:
    """
    Complete emotional model for SAM.

    Integrates:
    - Mood state machine
    - Trigger detection
    - Expression modulation
    - Relationship tracking
    """

    def __init__(self, db_path: str = "/Volumes/David External/sam_memory"):
        self.mood_machine = MoodStateMachine()
        self.modulator = ExpressionModulator()
        self.relationships = RelationshipTracker(f"{db_path}/relationships.db")

    def process_input(self, text: str, user_id: str = "default") -> Dict[str, Any]:
        """
        Process input text for emotional content.

        Updates mood and relationship state.
        """
        # Detect emotional triggers
        triggers = EmotionalTrigger.detect_triggers(text)

        # Update mood
        new_state = self.mood_machine.update(triggers)

        # Calculate sentiment for relationship
        sentiment = new_state.mood.valence * new_state.intensity

        # Record interaction
        self.relationships.record_interaction(
            user_id=user_id,
            interaction_type="message",
            sentiment=sentiment
        )

        return {
            "mood": new_state.to_dict(),
            "triggers_detected": [(t.value, i) for t, i in triggers],
            "sentiment": sentiment
        }

    def modulate_response(self, response: str) -> str:
        """Add emotional coloring to response"""
        return self.modulator.modulate(response, self.mood_machine.current_state)

    def get_emotional_context(self, user_id: str = "default") -> str:
        """Get emotional context for prompt building"""
        state = self.mood_machine.current_state
        relationship = self.relationships.get_relationship_context(user_id)

        context_parts = [
            f"Current mood: {state.mood.value} (intensity: {state.intensity:.1f})"
        ]

        if relationship:
            context_parts.append(relationship)

        return " | ".join(context_parts)

    def get_state(self) -> Dict[str, Any]:
        """Get complete emotional state"""
        return {
            "current_mood": self.mood_machine.current_state.to_dict(),
            "mood_summary": self.mood_machine.get_mood_summary()
        }


# Convenience function
def create_emotional_model() -> EmotionalModel:
    """Create an emotional model with default settings"""
    return EmotionalModel()


if __name__ == "__main__":
    # Demo
    model = create_emotional_model()

    # Process some inputs
    inputs = [
        "Hey SAM! You're awesome!",
        "I need help with this code, it's broken...",
        "Haha, that's funny!",
        "Let me think about this carefully.",
        "Thanks so much, you really helped!"
    ]

    for text in inputs:
        print(f"\nInput: {text}")
        result = model.process_input(text)
        print(f"Mood: {result['mood']['mood']} (intensity: {result['mood']['intensity']:.2f})")
        print(f"Triggers: {result['triggers_detected']}")

        # Modulate a response
        response = "I can help you with that."
        modulated = model.modulate_response(response)
        print(f"Response: {modulated}")

    print("\n" + "=" * 50)
    print("Final emotional state:")
    print(json.dumps(model.get_state(), indent=2))
