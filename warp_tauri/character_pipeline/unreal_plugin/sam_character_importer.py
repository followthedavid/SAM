"""
SAM Character Importer for Unreal Engine 5

This plugin automates:
1. Importing generated FBX characters from Blender
2. Setting up Chaos soft body physics for anatomy
3. Connecting to SAM Avatar Bridge via WebSocket
4. Real-time animation control from SAM AI

Usage in Unreal:
    import sam_character_importer as aci

    # Import a character
    aci.import_character("/path/to/character.fbx")

    # Connect to SAM
    aci.connect_to_sam()

    # Apply animation state
    aci.set_animation("talking")

Requires: Unreal Engine 5.x with Python scripting enabled
"""

import unreal
import json
import asyncio
import threading
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

try:
    import websockets
except ImportError:
    websockets = None
    unreal.log_warning("websockets not installed - SAM connection disabled")


# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    """Plugin configuration"""

    # SAM WebSocket settings
    ATLAS_HOST = "localhost"
    ATLAS_PORT = 8765

    # Import settings
    IMPORT_DESTINATION = "/Game/Characters/SAM"
    ANIMATION_DESTINATION = "/Game/Animations/SAM"

    # Physics settings
    SOFT_BODY_STIFFNESS = 0.3
    SOFT_BODY_DAMPING = 0.5
    COLLISION_THICKNESS = 0.5

    # Material settings
    AUTO_CREATE_MATERIALS = True
    SUBSURFACE_SCATTERING = True

    # Bone mapping (Blender to UE)
    BONE_MAPPING = {
        "anatomy_root": "anatomy_root",
        "shaft_base": "shaft_base",
        "shaft_mid": "shaft_mid",
        "shaft_tip": "shaft_tip",
        "glans": "glans",
        "testicle_L": "testicle_L",
        "testicle_R": "testicle_R",
        "scrotum": "scrotum"
    }


# ============================================================================
# ANIMATION STATES
# ============================================================================

class AnimationState(Enum):
    """Available animation states"""
    IDLE = "idle"
    TALKING = "talking"
    THINKING = "thinking"
    LISTENING = "listening"
    SMIRKING = "smirking"
    FLIRTING = "flirting"
    WINK = "wink"
    EYEBROW_RAISE = "eyebrow_raise"
    LAUGH = "laugh"
    CONCERNED = "concerned"
    EXCITED = "excited"
    AROUSED = "aroused"
    CLIMAX = "climax"
    RELAXED = "relaxed"


class EmotionalState(Enum):
    """Emotional expressions"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    SAD = "sad"
    CONFIDENT = "confident"
    FLIRTY = "flirty"
    INTENSE = "intense"
    PLAYFUL = "playful"
    THOUGHTFUL = "thoughtful"
    CONCERNED = "concerned"


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class ImportedCharacter:
    """Represents an imported character"""
    name: str
    skeletal_mesh: unreal.SkeletalMesh
    skeleton: unreal.Skeleton
    physics_asset: unreal.PhysicsAsset
    materials: List[unreal.MaterialInstanceDynamic]
    morph_targets: Dict[str, float]
    soft_body_component: Optional[Any] = None


@dataclass
class SAMMessage:
    """Message from SAM"""
    type: str
    animation: Optional[str] = None
    emotion: Optional[str] = None
    morph_targets: Optional[Dict[str, float]] = None
    text: Optional[str] = None
    intensity: Optional[float] = None


# ============================================================================
# CHARACTER IMPORTER
# ============================================================================

class CharacterImporter:
    """Handles FBX character import and setup"""

    def __init__(self):
        self.imported_characters: Dict[str, ImportedCharacter] = {}
        self.asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        self.editor_asset_library = unreal.EditorAssetLibrary

    def import_character(
        self,
        fbx_path: str,
        name: Optional[str] = None,
        destination: Optional[str] = None
    ) -> ImportedCharacter:
        """
        Import an FBX character with full setup

        Args:
            fbx_path: Path to FBX file
            name: Character name (derived from file if not provided)
            destination: Import destination in Content Browser

        Returns:
            ImportedCharacter with all assets
        """
        path = Path(fbx_path)
        if not path.exists():
            raise FileNotFoundError(f"FBX not found: {fbx_path}")

        char_name = name or path.stem
        dest_path = destination or f"{Config.IMPORT_DESTINATION}/{char_name}"

        unreal.log(f"[SAM] Importing character: {char_name}")

        # Create import task
        import_task = self._create_import_task(str(path), dest_path)

        # Execute import
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([import_task])

        # Get imported skeletal mesh
        skeletal_mesh = self._find_imported_mesh(dest_path, char_name)
        if not skeletal_mesh:
            raise RuntimeError(f"Failed to import skeletal mesh from {fbx_path}")

        # Get skeleton
        skeleton = skeletal_mesh.skeleton

        # Setup physics asset
        physics_asset = self._setup_physics_asset(skeletal_mesh, char_name)

        # Setup materials
        materials = self._setup_materials(skeletal_mesh)

        # Get morph targets
        morph_targets = self._get_morph_targets(skeletal_mesh)

        # Create character record
        character = ImportedCharacter(
            name=char_name,
            skeletal_mesh=skeletal_mesh,
            skeleton=skeleton,
            physics_asset=physics_asset,
            materials=materials,
            morph_targets=morph_targets
        )

        self.imported_characters[char_name] = character

        unreal.log(f"[SAM] Character imported successfully: {char_name}")
        unreal.log(f"[SAM]   - Morph targets: {len(morph_targets)}")
        unreal.log(f"[SAM]   - Materials: {len(materials)}")

        return character

    def _create_import_task(self, fbx_path: str, destination: str) -> unreal.AssetImportTask:
        """Create FBX import task with optimal settings"""
        task = unreal.AssetImportTask()
        task.filename = fbx_path
        task.destination_path = destination
        task.replace_existing = True
        task.automated = True
        task.save = True

        # FBX import options
        options = unreal.FbxImportUI()
        options.import_mesh = True
        options.import_textures = True
        options.import_materials = True
        options.import_as_skeletal = True
        options.import_animations = False  # Animations imported separately
        options.import_morph_targets = True

        # Skeletal mesh options
        options.skeletal_mesh_import_data.import_morph_targets = True
        options.skeletal_mesh_import_data.update_skeleton_reference_pose = False
        options.skeletal_mesh_import_data.use_t0_as_ref_pose = True

        task.options = options

        return task

    def _find_imported_mesh(
        self,
        destination: str,
        name: str
    ) -> Optional[unreal.SkeletalMesh]:
        """Find the imported skeletal mesh"""
        # Try common naming patterns
        patterns = [
            f"{destination}/{name}",
            f"{destination}/{name}_Mesh",
            f"{destination}/SK_{name}"
        ]

        for pattern in patterns:
            if unreal.EditorAssetLibrary.does_asset_exist(pattern):
                asset = unreal.EditorAssetLibrary.load_asset(pattern)
                if isinstance(asset, unreal.SkeletalMesh):
                    return asset

        # Search destination folder
        assets = unreal.EditorAssetLibrary.list_assets(destination)
        for asset_path in assets:
            asset = unreal.EditorAssetLibrary.load_asset(asset_path)
            if isinstance(asset, unreal.SkeletalMesh):
                return asset

        return None

    def _setup_physics_asset(
        self,
        skeletal_mesh: unreal.SkeletalMesh,
        name: str
    ) -> unreal.PhysicsAsset:
        """Create and configure physics asset for anatomy"""

        # Create physics asset
        physics_asset = skeletal_mesh.physics_asset
        if not physics_asset:
            # Create new physics asset
            factory = unreal.PhysicsAssetFactory()
            physics_asset = factory.create_physics_asset(skeletal_mesh)

        # Configure anatomy bones for soft body
        anatomy_bones = [
            "shaft_base", "shaft_mid", "shaft_tip",
            "glans", "testicle_L", "testicle_R", "scrotum"
        ]

        for bone_name in anatomy_bones:
            self._configure_soft_body_bone(physics_asset, bone_name)

        unreal.log(f"[SAM] Physics asset configured with soft body for {len(anatomy_bones)} bones")

        return physics_asset

    def _configure_soft_body_bone(
        self,
        physics_asset: unreal.PhysicsAsset,
        bone_name: str
    ):
        """Configure a bone for soft body physics"""
        # Note: This is a simplified version - full implementation
        # would use Chaos cloth/soft body system

        # Find body setup for this bone
        for i in range(physics_asset.get_editor_property('skeletal_body_setups').__len__()):
            body_setup = physics_asset.get_editor_property('skeletal_body_setups')[i]
            if body_setup.bone_name.to_string() == bone_name:
                # Set physics properties
                body_setup.set_editor_property('physics_type', unreal.PhysicsType.SIMULATED)
                body_setup.set_editor_property('collision_response', unreal.BodyCollisionResponse.ENABLED)
                break

    def _setup_materials(
        self,
        skeletal_mesh: unreal.SkeletalMesh
    ) -> List[unreal.MaterialInstanceDynamic]:
        """Setup materials with subsurface scattering for skin"""
        materials = []

        if not Config.AUTO_CREATE_MATERIALS:
            return materials

        # Get material slots
        num_materials = skeletal_mesh.get_num_materials()

        for i in range(num_materials):
            slot_name = skeletal_mesh.get_material_slot_name(i)

            # Check if this is a skin material
            is_skin = any(term in slot_name.lower() for term in ['skin', 'body', 'anatomy'])

            if is_skin and Config.SUBSURFACE_SCATTERING:
                # Create skin material with SSS
                material = self._create_skin_material(slot_name)
                if material:
                    skeletal_mesh.set_material(i, material)
                    materials.append(material)

        return materials

    def _create_skin_material(self, name: str) -> Optional[unreal.MaterialInstanceDynamic]:
        """Create a skin material with subsurface scattering"""
        # Load base skin material (you'd create this in editor)
        base_material_path = "/Game/Materials/M_Skin_Base"

        if not unreal.EditorAssetLibrary.does_asset_exist(base_material_path):
            unreal.log_warning(f"[SAM] Base skin material not found: {base_material_path}")
            return None

        base_material = unreal.EditorAssetLibrary.load_asset(base_material_path)

        # Create dynamic instance
        material = unreal.MaterialInstanceDynamic.create(base_material, None, name)

        # Set default parameters
        material.set_scalar_parameter_value("SubsurfaceIntensity", 0.8)
        material.set_scalar_parameter_value("Roughness", 0.4)
        material.set_vector_parameter_value(
            "SubsurfaceColor",
            unreal.LinearColor(0.8, 0.2, 0.1, 1.0)  # Reddish skin tone
        )

        return material

    def _get_morph_targets(self, skeletal_mesh: unreal.SkeletalMesh) -> Dict[str, float]:
        """Get available morph targets and their default values"""
        morph_targets = {}

        # Get morph target names
        # Note: Exact API depends on UE version
        try:
            morph_target_set = skeletal_mesh.get_morph_target_names()
            for name in morph_target_set:
                morph_targets[str(name)] = 0.0
        except:
            # Fallback for older API
            pass

        return morph_targets


# ============================================================================
# ANIMATION IMPORTER
# ============================================================================

class AnimationImporter:
    """Handles animation import and retargeting"""

    def __init__(self, character: ImportedCharacter):
        self.character = character

    def import_animation(
        self,
        fbx_path: str,
        name: Optional[str] = None
    ) -> unreal.AnimSequence:
        """Import animation and apply to character skeleton"""
        path = Path(fbx_path)
        anim_name = name or path.stem

        dest_path = f"{Config.ANIMATION_DESTINATION}/{self.character.name}"

        # Create import task
        task = unreal.AssetImportTask()
        task.filename = str(path)
        task.destination_path = dest_path
        task.replace_existing = True
        task.automated = True

        # Animation import options
        options = unreal.FbxImportUI()
        options.import_mesh = False
        options.import_animations = True
        options.skeleton = self.character.skeleton

        # Animation settings
        options.anim_sequence_import_data.animation_length = unreal.FBXAnimationLengthImportType.EXPORTED_TIME
        options.anim_sequence_import_data.import_bone_tracks = True
        options.anim_sequence_import_data.import_custom_attribute = True
        options.anim_sequence_import_data.import_morph_targets = True

        task.options = options

        # Execute import
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])

        # Find imported animation
        anim_path = f"{dest_path}/{anim_name}"
        if unreal.EditorAssetLibrary.does_asset_exist(anim_path):
            return unreal.EditorAssetLibrary.load_asset(anim_path)

        return None

    def import_motion_data(
        self,
        json_path: str
    ) -> Optional[unreal.AnimSequence]:
        """Import motion data from extraction pipeline"""
        path = Path(json_path)
        if not path.exists():
            return None

        with open(path) as f:
            data = json.load(f)

        # Convert to animation curve
        # This would generate animation from the extracted keyframes
        # For now, log what we'd do

        unreal.log(f"[SAM] Would import motion data:")
        unreal.log(f"[SAM]   - Frames: {data.get('frame_count', 0)}")
        unreal.log(f"[SAM]   - FPS: {data.get('fps', 30)}")
        unreal.log(f"[SAM]   - Landmarks: {len(data.get('landmarks', []))}")

        return None


# ============================================================================
# ATLAS CONNECTION
# ============================================================================

class SAMConnection:
    """WebSocket connection to SAM AI"""

    def __init__(self):
        self.connected = False
        self.websocket = None
        self.event_loop = None
        self.thread = None
        self.current_character: Optional[ImportedCharacter] = None
        self.callbacks: Dict[str, List[callable]] = {}

    def set_character(self, character: ImportedCharacter):
        """Set the active character for SAM control"""
        self.current_character = character

    def connect(self, host: str = None, port: int = None):
        """Connect to SAM WebSocket server"""
        if websockets is None:
            unreal.log_error("[SAM] websockets module not available")
            return False

        host = host or Config.ATLAS_HOST
        port = port or Config.ATLAS_PORT

        def run_event_loop():
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            self.event_loop.run_until_complete(self._connect(host, port))
            self.event_loop.run_forever()

        self.thread = threading.Thread(target=run_event_loop, daemon=True)
        self.thread.start()

        return True

    async def _connect(self, host: str, port: int):
        """Async connection handler"""
        uri = f"ws://{host}:{port}"

        try:
            async with websockets.connect(uri) as ws:
                self.websocket = ws
                self.connected = True

                unreal.log(f"[SAM] Connected to {uri}")

                # Send registration
                await self._send({
                    "type": "register",
                    "client": "unreal",
                    "capabilities": ["animation", "morph_targets", "physics"]
                })

                # Listen for messages
                async for message in ws:
                    await self._handle_message(message)

        except Exception as e:
            unreal.log_error(f"[SAM] Connection failed: {e}")
            self.connected = False

    async def _handle_message(self, message: str):
        """Handle incoming message from SAM"""
        try:
            data = json.loads(message)
            msg = SAMMessage(
                type=data.get("type", "unknown"),
                animation=data.get("animation"),
                emotion=data.get("emotion"),
                morph_targets=data.get("morph_targets"),
                text=data.get("text"),
                intensity=data.get("intensity")
            )

            # Apply to character
            if self.current_character:
                self._apply_sam_command(msg)

            # Fire callbacks
            for callback in self.callbacks.get(msg.type, []):
                callback(msg)

        except Exception as e:
            unreal.log_warning(f"[SAM] Message parse error: {e}")

    def _apply_sam_command(self, msg: SAMMessage):
        """Apply SAM command to current character"""
        if not self.current_character:
            return

        if msg.type == "animation":
            self._set_animation(msg.animation, msg.intensity or 1.0)

        elif msg.type == "emotion":
            self._set_emotion(msg.emotion, msg.intensity or 1.0)

        elif msg.type == "morph":
            self._set_morph_targets(msg.morph_targets)

        elif msg.type == "speak":
            self._play_speech_animation(msg.text)

    def _set_animation(self, animation: str, intensity: float):
        """Set character animation state"""
        # This would interface with Animation Blueprint
        unreal.log(f"[SAM] Animation: {animation} @ {intensity}")

    def _set_emotion(self, emotion: str, intensity: float):
        """Set emotional expression via morph targets"""
        # Map emotion to morph targets
        emotion_morphs = {
            "happy": {"smile": 0.8, "brow_raise": 0.3},
            "sad": {"frown": 0.6, "brow_furrow": 0.4},
            "confident": {"smirk": 0.5, "chin_up": 0.3},
            "flirty": {"wink": 0.7, "smile": 0.4, "brow_raise": 0.2},
            "intense": {"eye_narrow": 0.4, "jaw_clench": 0.3},
            "aroused": {"arousal": intensity, "breathing": 0.5}
        }

        if emotion in emotion_morphs:
            self._set_morph_targets(emotion_morphs[emotion])

    def _set_morph_targets(self, targets: Dict[str, float]):
        """Set morph target values"""
        if not targets:
            return

        # Apply morph targets to skeletal mesh component
        # In practice, this would be done through the anim blueprint
        for name, value in targets.items():
            if name in self.current_character.morph_targets:
                self.current_character.morph_targets[name] = value
                unreal.log(f"[SAM] Morph: {name} = {value}")

    def _play_speech_animation(self, text: str):
        """Animate character speaking"""
        # This would trigger lip sync and facial animation
        unreal.log(f"[SAM] Speaking: {text[:50]}...")

    async def _send(self, data: dict):
        """Send message to SAM"""
        if self.websocket and self.connected:
            await self.websocket.send(json.dumps(data))

    def on(self, event_type: str, callback: callable):
        """Register event callback"""
        if event_type not in self.callbacks:
            self.callbacks[event_type] = []
        self.callbacks[event_type].append(callback)

    def disconnect(self):
        """Disconnect from SAM"""
        if self.event_loop:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
        self.connected = False


# ============================================================================
# SOFT BODY CONTROLLER
# ============================================================================

class SoftBodyController:
    """Controls Chaos soft body physics for anatomy"""

    def __init__(self, character: ImportedCharacter):
        self.character = character
        self.simulation_enabled = False

    def enable_simulation(self):
        """Enable soft body simulation"""
        self.simulation_enabled = True
        unreal.log("[SAM] Soft body simulation enabled")

    def disable_simulation(self):
        """Disable soft body simulation"""
        self.simulation_enabled = False
        unreal.log("[SAM] Soft body simulation disabled")

    def set_stiffness(self, value: float):
        """Set soft body stiffness (0-1)"""
        # Would modify Chaos cloth/soft body parameters
        pass

    def set_damping(self, value: float):
        """Set soft body damping (0-1)"""
        pass

    def apply_force(self, direction: unreal.Vector, magnitude: float):
        """Apply force to soft body"""
        pass

    def set_arousal_state(self, level: float):
        """Set anatomical arousal state (0-1)"""
        # Blend between shape key states
        if level > 0:
            morph_targets = {
                "arousal": level,
                "erect": min(1.0, level * 1.5)
            }
            # Apply to character
            for name, value in morph_targets.items():
                if name in self.character.morph_targets:
                    self.character.morph_targets[name] = value


# ============================================================================
# GLOBAL INSTANCES
# ============================================================================

_importer: Optional[CharacterImporter] = None
_sam_connection: Optional[SAMConnection] = None
_current_character: Optional[ImportedCharacter] = None


def get_importer() -> CharacterImporter:
    """Get or create character importer"""
    global _importer
    if _importer is None:
        _importer = CharacterImporter()
    return _importer


def get_sam_connection() -> SAMConnection:
    """Get or create SAM connection"""
    global _sam_connection
    if _sam_connection is None:
        _sam_connection = SAMConnection()
    return _sam_connection


# ============================================================================
# PUBLIC API
# ============================================================================

def import_character(
    fbx_path: str,
    name: str = None,
    destination: str = None
) -> ImportedCharacter:
    """
    Import a character from FBX

    Args:
        fbx_path: Path to FBX file
        name: Character name
        destination: Import destination

    Returns:
        ImportedCharacter object
    """
    global _current_character

    importer = get_importer()
    character = importer.import_character(fbx_path, name, destination)
    _current_character = character

    # Set as SAM target
    sam = get_sam_connection()
    sam.set_character(character)

    return character


def import_animation(
    fbx_path: str,
    name: str = None,
    character: ImportedCharacter = None
) -> unreal.AnimSequence:
    """Import animation for a character"""
    char = character or _current_character
    if not char:
        raise RuntimeError("No character loaded")

    anim_importer = AnimationImporter(char)
    return anim_importer.import_animation(fbx_path, name)


def connect_to_sam(host: str = None, port: int = None) -> bool:
    """Connect to SAM AI server"""
    sam = get_sam_connection()
    return sam.connect(host, port)


def disconnect_from_sam():
    """Disconnect from SAM"""
    sam = get_sam_connection()
    sam.disconnect()


def set_animation(state: str, intensity: float = 1.0):
    """Set character animation state"""
    sam = get_sam_connection()
    if sam.connected:
        asyncio.run_coroutine_threadsafe(
            sam._send({
                "type": "animation_ack",
                "state": state,
                "intensity": intensity
            }),
            sam.event_loop
        )


def set_emotion(emotion: str, intensity: float = 1.0):
    """Set character emotion"""
    sam = get_sam_connection()
    sam._set_emotion(emotion, intensity)


def set_morph_target(name: str, value: float):
    """Set a morph target value"""
    if _current_character and name in _current_character.morph_targets:
        _current_character.morph_targets[name] = value


def batch_import(
    fbx_directory: str,
    pattern: str = "*.fbx"
) -> List[ImportedCharacter]:
    """Batch import multiple characters"""
    import glob

    directory = Path(fbx_directory)
    files = list(directory.glob(pattern))

    characters = []
    for fbx_file in files:
        try:
            char = import_character(str(fbx_file))
            characters.append(char)
        except Exception as e:
            unreal.log_error(f"[SAM] Failed to import {fbx_file}: {e}")

    return characters


# ============================================================================
# EDITOR COMMANDS
# ============================================================================

@unreal.uclass()
class SAMEditorCommands(unreal.EditorUtilityToolMenuEntry):
    """Editor menu commands for SAM"""

    @unreal.ufunction(static=True, meta=dict(Category="SAM"))
    def import_character_dialog():
        """Open file dialog to import character"""
        # This would open native file dialog
        pass

    @unreal.ufunction(static=True, meta=dict(Category="SAM"))
    def connect_sam():
        """Connect to SAM server"""
        connect_to_sam()

    @unreal.ufunction(static=True, meta=dict(Category="SAM"))
    def disconnect_sam():
        """Disconnect from SAM server"""
        disconnect_from_sam()


# ============================================================================
# INITIALIZATION
# ============================================================================

def initialize():
    """Initialize the SAM plugin"""
    unreal.log("[SAM] Character Importer initialized")
    unreal.log(f"[SAM] Import destination: {Config.IMPORT_DESTINATION}")
    unreal.log(f"[SAM] SAM server: {Config.ATLAS_HOST}:{Config.ATLAS_PORT}")


# Auto-initialize when module is loaded
try:
    initialize()
except:
    pass  # May fail if loaded outside Unreal
