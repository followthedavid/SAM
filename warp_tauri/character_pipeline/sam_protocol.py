"""
SAM Avatar Bridge Protocol
============================

Shared protocol implementation for Unity/Unreal/Godot communication with SAM.
This module can be used as:
1. A standalone WebSocket server for testing
2. A reference for implementing the protocol in game engines
3. A bridge between multiple game engine clients

Protocol Messages:
- SAM -> Game Engine: Commands (animation, emotion, lipsync, gesture, look, custom)
- Game Engine -> SAM: Events (user_gesture, user_touch, state_change, error)

Usage:
    # Start the bridge server
    python sam_protocol.py --port 8765

    # Or use programmatically
    from sam_protocol import SAMBridge, SAMCommand, SAMEvent

    bridge = SAMBridge()
    await bridge.start()
    await bridge.send_animation("talking")
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Any, Callable, Awaitable, Set
import argparse

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
except ImportError:
    websockets = None
    WebSocketServerProtocol = Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SAMBridge")


# ============================================================================
# ENUMS
# ============================================================================

class AnimationState(Enum):
    IDLE = "idle"
    TALKING = "talking"
    THINKING = "thinking"
    LISTENING = "listening"
    PLEASED = "pleased"
    SMIRKING = "smirking"
    FLIRTING = "flirting"
    CONCERNED = "concerned"
    LAUGHING = "laughing"
    EYEBROW_RAISE = "eyebrow_raise"
    HEAD_TILT = "head_tilt"
    NOD = "nod"
    SHAKE_HEAD = "shake_head"
    WINK = "wink"
    CUSTOM = "custom"


class EmotionalState(Enum):
    NEUTRAL = "neutral"
    HAPPY = "happy"
    AMUSED = "amused"
    INTERESTED = "interested"
    FLIRTY = "flirty"
    CONFIDENT = "confident"
    THOUGHTFUL = "thoughtful"
    CONCERNED = "concerned"
    PLAYFUL = "playful"
    INTENSE = "intense"


class BodyPosture(Enum):
    RELAXED = "relaxed"
    ALERT = "alert"
    LEANING_FORWARD = "leaning_forward"
    LEANING_BACK = "leaning_back"


class CommandType(Enum):
    ANIMATION = "animation"
    EMOTION = "emotion"
    LIPSYNC = "lipsync"
    GESTURE = "gesture"
    LOOK = "look"
    MORPH = "morph"
    CUSTOM = "custom"


class EventType(Enum):
    USER_GESTURE = "user_gesture"
    USER_TOUCH = "user_touch"
    STATE_CHANGE = "state_change"
    ERROR = "error"
    REGISTER = "register"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class FacialExpression:
    browRaise: float = 0.0       # 0-1
    smirkIntensity: float = 0.3  # 0-1
    eyeIntensity: float = 0.5    # 0-1
    jawTension: float = 0.0      # 0-1


@dataclass
class LipSyncFrame:
    timestamp: float
    viseme: str         # A, E, I, O, U, M, F, TH, S, T, K, R, W, REST
    intensity: float    # 0-1
    duration: float     # ms


@dataclass
class SAMCommand:
    """Command from SAM to game engine"""
    type: str
    payload: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp() * 1000)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "SAMCommand":
        obj = json.loads(data)
        return cls(**obj)


@dataclass
class SAMEvent:
    """Event from game engine to SAM"""
    type: str
    data: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp() * 1000)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @classmethod
    def from_json(cls, data: str) -> "SAMEvent":
        obj = json.loads(data)
        return cls(**obj)


@dataclass
class ConnectedClient:
    """Represents a connected game engine client"""
    websocket: WebSocketServerProtocol
    engine: str  # "unity", "unreal", "godot", "custom"
    capabilities: List[str]
    connected_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_message: float = field(default_factory=lambda: datetime.now().timestamp())


# ============================================================================
# VISEME MAPPING (Text to Lip Sync)
# ============================================================================

PHONEME_TO_VISEME = {
    # Vowels
    'AA': 'A', 'AE': 'A', 'AH': 'A',
    'AO': 'O', 'AW': 'O',
    'AY': 'A',
    'EH': 'E', 'ER': 'E', 'EY': 'E',
    'IH': 'I', 'IY': 'I',
    'OW': 'O', 'OY': 'O',
    'UH': 'U', 'UW': 'U',
    # Consonants
    'B': 'M', 'P': 'M', 'M': 'M',
    'F': 'F', 'V': 'F',
    'TH': 'TH', 'DH': 'TH',
    'S': 'S', 'Z': 'S', 'SH': 'S', 'ZH': 'S', 'CH': 'S', 'JH': 'S',
    'T': 'T', 'D': 'T', 'N': 'T', 'L': 'T',
    'K': 'K', 'G': 'K', 'NG': 'K',
    'R': 'R',
    'W': 'W',
    'Y': 'I',
    'HH': 'REST',
    'REST': 'REST', ' ': 'REST', '.': 'REST', ',': 'REST'
}

TEXT_TO_VISEMES = {
    'a': ['A'], 'e': ['E'], 'i': ['I'], 'o': ['O'], 'u': ['U'],
    'b': ['M', 'REST'], 'p': ['M', 'REST'], 'm': ['M', 'M'],
    'f': ['F'], 'v': ['F'],
    'th': ['TH'],
    's': ['S'], 'z': ['S'], 'sh': ['S'], 'ch': ['S'],
    't': ['T', 'REST'], 'd': ['T', 'REST'], 'n': ['T'], 'l': ['T'],
    'k': ['K', 'REST'], 'g': ['K', 'REST'],
    'r': ['R'], 'w': ['W'], 'y': ['I'],
    ' ': ['REST'], '.': ['REST', 'REST'], ',': ['REST']
}

# Emotion to facial expression mapping
EMOTION_EXPRESSIONS = {
    EmotionalState.NEUTRAL: FacialExpression(0, 0.2, 0.5, 0),
    EmotionalState.HAPPY: FacialExpression(0.2, 0.6, 0.7, 0),
    EmotionalState.AMUSED: FacialExpression(0.3, 0.7, 0.6, 0),
    EmotionalState.INTERESTED: FacialExpression(0.4, 0.3, 0.8, 0),
    EmotionalState.FLIRTY: FacialExpression(0.5, 0.8, 0.9, 0),
    EmotionalState.CONFIDENT: FacialExpression(0.2, 0.6, 0.7, 0),
    EmotionalState.THOUGHTFUL: FacialExpression(0.1, 0.1, 0.4, 0),
    EmotionalState.CONCERNED: FacialExpression(0.3, 0, 0.6, 0.2),
    EmotionalState.PLAYFUL: FacialExpression(0.4, 0.7, 0.8, 0),
    EmotionalState.INTENSE: FacialExpression(0.1, 0.4, 1.0, 0.3),
}

# Emotion to morph target mapping for character anatomy
EMOTION_MORPH_TARGETS = {
    "happy": {"smile": 0.8, "brow_raise": 0.3},
    "sad": {"frown": 0.6, "brow_furrow": 0.4},
    "confident": {"smirk": 0.5, "chin_up": 0.3},
    "flirty": {"wink": 0.7, "smile": 0.4, "brow_raise": 0.2},
    "intense": {"eye_narrow": 0.4, "jaw_clench": 0.3},
    "aroused": {"arousal": 0.8, "breathing": 0.5}
}


# ============================================================================
# LIP SYNC GENERATOR
# ============================================================================

def generate_lip_sync(text: str, duration_ms: float) -> List[LipSyncFrame]:
    """Generate lip sync frames from text"""
    visemes: List[LipSyncFrame] = []
    clean_text = ''.join(c for c in text.lower() if c.isalpha() or c in ' .,')
    chars = list(clean_text)

    if not chars:
        return visemes

    time_per_char = duration_ms / len(chars)
    current_time = 0.0

    i = 0
    while i < len(chars):
        char = chars[i]
        next_char = chars[i + 1] if i + 1 < len(chars) else ''
        combo = char + next_char

        # Check for digraphs first
        if combo in TEXT_TO_VISEMES:
            viseme_list = TEXT_TO_VISEMES[combo]
            i += 2  # Skip next char
        else:
            viseme_list = TEXT_TO_VISEMES.get(char, ['REST'])
            i += 1

        for viseme in viseme_list:
            frame = LipSyncFrame(
                timestamp=current_time,
                viseme=viseme,
                intensity=0.0 if viseme == 'REST' else 0.8,
                duration=time_per_char / len(viseme_list)
            )
            visemes.append(frame)
            current_time += frame.duration

    return visemes


# ============================================================================
# ATLAS BRIDGE SERVER
# ============================================================================

class SAMBridge:
    """
    WebSocket bridge for SAM <-> Game Engine communication

    Usage:
        bridge = SAMBridge(port=8765)
        await bridge.start()

        # Send commands to all connected clients
        await bridge.send_animation("talking")
        await bridge.send_emotion("flirty", 0.8)

        # Handle events from clients
        @bridge.on_event("user_gesture")
        def handle_gesture(client, event):
            print(f"User gesture: {event.data}")
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: Dict[str, ConnectedClient] = {}
        self.event_handlers: Dict[str, List[Callable]] = {}
        self.server = None
        self._running = False

    async def start(self):
        """Start the WebSocket server"""
        if websockets is None:
            raise ImportError("websockets module required: pip install websockets")

        self._running = True
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )

        logger.info(f"[SAM Bridge] Server started on ws://{self.host}:{self.port}")
        return self.server

    async def stop(self):
        """Stop the WebSocket server"""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        logger.info("[SAM Bridge] Server stopped")

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        client_id = str(id(websocket))
        logger.info(f"[SAM Bridge] New connection: {client_id}")

        try:
            async for message in websocket:
                await self._handle_message(websocket, client_id, message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            if client_id in self.clients:
                del self.clients[client_id]
                logger.info(f"[SAM Bridge] Client disconnected: {client_id}")

    async def _handle_message(
        self,
        websocket: WebSocketServerProtocol,
        client_id: str,
        message: str
    ):
        """Handle incoming message from client"""
        try:
            data = json.loads(message)

            # Handle registration
            if data.get("type") == "register":
                client = ConnectedClient(
                    websocket=websocket,
                    engine=data.get("client", "unknown"),
                    capabilities=data.get("capabilities", [])
                )
                self.clients[client_id] = client
                logger.info(
                    f"[SAM Bridge] Client registered: {client.engine} "
                    f"(capabilities: {client.capabilities})"
                )

                # Send acknowledgment
                await websocket.send(json.dumps({
                    "type": "registered",
                    "client_id": client_id,
                    "timestamp": datetime.now().timestamp() * 1000
                }))
                return

            # Update last message time
            if client_id in self.clients:
                self.clients[client_id].last_message = datetime.now().timestamp()

            # Parse as event
            event = SAMEvent(
                type=data.get("type", "unknown"),
                data=data.get("data", data),
                timestamp=data.get("timestamp", datetime.now().timestamp() * 1000)
            )

            # Trigger handlers
            handlers = self.event_handlers.get(event.type, [])
            client = self.clients.get(client_id)

            for handler in handlers:
                if asyncio.iscoroutinefunction(handler):
                    await handler(client, event)
                else:
                    handler(client, event)

        except json.JSONDecodeError as e:
            logger.error(f"[SAM Bridge] JSON parse error: {e}")
        except Exception as e:
            logger.error(f"[SAM Bridge] Message handling error: {e}")

    def on_event(self, event_type: str):
        """Decorator to register event handler"""
        def decorator(func: Callable):
            if event_type not in self.event_handlers:
                self.event_handlers[event_type] = []
            self.event_handlers[event_type].append(func)
            return func
        return decorator

    async def _send_to_all(self, command: SAMCommand):
        """Send command to all connected clients"""
        message = command.to_json()
        for client_id, client in list(self.clients.items()):
            try:
                await client.websocket.send(message)
            except Exception as e:
                logger.error(f"[SAM Bridge] Send error to {client_id}: {e}")

    async def _send_to_client(self, client_id: str, command: SAMCommand):
        """Send command to specific client"""
        if client_id in self.clients:
            try:
                await self.clients[client_id].websocket.send(command.to_json())
            except Exception as e:
                logger.error(f"[SAM Bridge] Send error to {client_id}: {e}")

    # ========================================================================
    # HIGH-LEVEL COMMAND API
    # ========================================================================

    async def send_animation(
        self,
        animation: str,
        blend: float = 0.3,
        loop: bool = True,
        duration: Optional[float] = None
    ):
        """Send animation command"""
        command = SAMCommand(
            type="animation",
            payload={
                "animation": animation,
                "blend": blend,
                "loop": loop,
                "duration": duration
            }
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Animation: {animation}")

    async def send_emotion(
        self,
        emotion: str,
        intensity: float = 1.0
    ):
        """Send emotion command"""
        # Get facial expression for emotion
        try:
            emotion_enum = EmotionalState(emotion)
            expression = EMOTION_EXPRESSIONS.get(emotion_enum, FacialExpression())
        except ValueError:
            expression = FacialExpression()

        command = SAMCommand(
            type="emotion",
            payload={
                "emotion": emotion,
                "intensity": intensity,
                "expression": asdict(expression)
            }
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Emotion: {emotion} @ {intensity}")

    async def send_morph_targets(self, targets: Dict[str, float]):
        """Send morph target values"""
        command = SAMCommand(
            type="morph",
            payload={
                "morph_targets": targets
            }
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Morph targets: {targets}")

    async def send_lip_sync(
        self,
        text: str,
        duration_ms: float
    ):
        """Send lip sync data for speech"""
        frames = generate_lip_sync(text, duration_ms)

        command = SAMCommand(
            type="lipsync",
            payload={
                "data": [asdict(f) for f in frames],
                "totalDuration": duration_ms
            }
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Lip sync: {len(frames)} frames")

    async def send_gesture(
        self,
        gesture: str,
        hand: str = "right",
        intensity: float = 0.7
    ):
        """Send gesture command"""
        command = SAMCommand(
            type="gesture",
            payload={
                "gesture": gesture,
                "hand": hand,
                "intensity": intensity
            }
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Gesture: {gesture} ({hand})")

    async def send_look_at(
        self,
        target: str | Dict[str, float]
    ):
        """Send look-at command"""
        if isinstance(target, str):
            if target == "user":
                target_pos = {"x": 0, "y": 1.6, "z": 1}
            elif target == "away":
                target_pos = {"x": 2, "y": 1.4, "z": 0}
            else:
                target_pos = {"x": 0, "y": 0, "z": 1}
        else:
            target_pos = target

        command = SAMCommand(
            type="look",
            payload={"target": target_pos}
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Look at: {target_pos}")

    async def send_custom(self, action: str, **kwargs):
        """Send custom command"""
        command = SAMCommand(
            type="custom",
            payload={"action": action, **kwargs}
        )
        await self._send_to_all(command)
        logger.debug(f"[SAM Bridge] Custom: {action}")

    # ========================================================================
    # HIGH-LEVEL BEHAVIOR API
    # ========================================================================

    async def speak(self, text: str, duration_ms: Optional[float] = None):
        """Animate character speaking with lip sync"""
        # Estimate duration if not provided (roughly 150ms per word)
        if duration_ms is None:
            word_count = len(text.split())
            duration_ms = word_count * 150

        await self.send_emotion("confident")
        await self.send_animation("talking")
        await self.send_lip_sync(text, duration_ms)

        # Schedule end of speaking
        async def end_speaking():
            await asyncio.sleep(duration_ms / 1000)
            await self.send_animation("idle")
            await self.send_emotion("neutral")

        asyncio.create_task(end_speaking())

    async def react(self, sentiment: str):
        """React to user message with appropriate animation"""
        reactions = {
            "positive": (EmotionalState.HAPPY, AnimationState.SMIRKING),
            "negative": (EmotionalState.CONCERNED, AnimationState.HEAD_TILT),
            "question": (EmotionalState.INTERESTED, AnimationState.EYEBROW_RAISE),
            "flirty": (EmotionalState.FLIRTY, AnimationState.WINK),
            "neutral": (EmotionalState.NEUTRAL, AnimationState.LISTENING)
        }

        emotion, animation = reactions.get(
            sentiment,
            (EmotionalState.NEUTRAL, AnimationState.IDLE)
        )

        await self.send_emotion(emotion.value)
        await self.send_animation(animation.value)

    async def flirt(self):
        """Flirty animation sequence"""
        await self.send_emotion("flirty", 1.0)
        await self.send_animation("wink")
        await self.send_gesture("point", "right", 0.5)

        await asyncio.sleep(2)

        await self.send_emotion("confident")
        await self.send_animation("smirking")

    async def set_arousal(self, level: float):
        """Set anatomical arousal state (0-1)"""
        targets = {
            "arousal": level,
            "erect": min(1.0, level * 1.5),
            "breathing": 0.3 + level * 0.4
        }
        await self.send_morph_targets(targets)

    # ========================================================================
    # STATUS & MONITORING
    # ========================================================================

    def get_connected_clients(self) -> List[Dict[str, Any]]:
        """Get list of connected clients"""
        return [
            {
                "id": client_id,
                "engine": client.engine,
                "capabilities": client.capabilities,
                "connected_at": client.connected_at,
                "last_message": client.last_message
            }
            for client_id, client in self.clients.items()
        ]

    @property
    def client_count(self) -> int:
        """Number of connected clients"""
        return len(self.clients)

    def has_capability(self, capability: str) -> bool:
        """Check if any connected client has a capability"""
        return any(
            capability in client.capabilities
            for client in self.clients.values()
        )


# ============================================================================
# STANDALONE SERVER
# ============================================================================

async def main():
    """Run standalone bridge server"""
    parser = argparse.ArgumentParser(description="SAM Avatar Bridge Server")
    parser.add_argument("--host", default="localhost", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--test", action="store_true", help="Run test sequence")
    args = parser.parse_args()

    bridge = SAMBridge(host=args.host, port=args.port)

    # Register event handlers
    @bridge.on_event("user_gesture")
    async def on_gesture(client, event):
        logger.info(f"[Event] User gesture from {client.engine}: {event.data}")

    @bridge.on_event("state_change")
    async def on_state_change(client, event):
        logger.info(f"[Event] State change from {client.engine}: {event.data}")

    await bridge.start()

    if args.test:
        # Run test sequence after 5 seconds
        async def test_sequence():
            await asyncio.sleep(5)
            if bridge.client_count > 0:
                logger.info("[Test] Running test sequence...")

                await bridge.send_animation("idle")
                await asyncio.sleep(2)

                await bridge.send_emotion("happy")
                await bridge.send_animation("smirking")
                await asyncio.sleep(2)

                await bridge.speak("Hello, I'm SAM. Nice to meet you.")
                await asyncio.sleep(3)

                await bridge.flirt()
                await asyncio.sleep(3)

                await bridge.set_arousal(0.5)
                await asyncio.sleep(2)

                await bridge.set_arousal(0)
                await bridge.send_emotion("neutral")
                await bridge.send_animation("idle")

                logger.info("[Test] Test sequence complete")
            else:
                logger.warning("[Test] No clients connected, skipping test")

        asyncio.create_task(test_sequence())

    # Keep running
    try:
        await asyncio.Future()  # Run forever
    except asyncio.CancelledError:
        await bridge.stop()


if __name__ == "__main__":
    asyncio.run(main())
