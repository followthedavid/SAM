# SAM Avatar - Unity Project

Unity project for rendering the SAM avatar with real-time connection to Warp Open terminal.

## Requirements

- Unity 2022.3 LTS or newer
- macOS 11+ / iOS 15+ / Windows 10+
- Your 3D character model (FBX with blend shapes)

## Quick Start

### 1. Open in Unity

1. Open Unity Hub
2. Click "Add" → "Add project from disk"
3. Select this `unity_project` folder
4. Open with Unity 2022.3+

### 2. Set Up Your Model

#### In Blender (before export):

1. Open your character model
2. Go to **SAM → Generate Blender Shape Key Script** (or use the script in `Assets/Editor/`)
3. Run the Python script to create all required shape keys
4. Sculpt each shape key as needed
5. Export as FBX:
   - ☑️ Apply Modifiers
   - ☑️ Bake Animation (if any)
   - ☑️ Shape Keys

#### In Unity:

1. Import your FBX into `Assets/Characters/`
2. Select the model, in Inspector:
   - Rig → Animation Type: Humanoid (or Generic)
   - Model → Import BlendShapes: ☑️
3. Drag model into the scene
4. Add the `SAMAvatarController` component
5. Assign mesh references (body, face, anatomy)

### 3. Connect to Warp Open

The avatar auto-connects to `localhost:8765` by default.

To test manually:
```bash
# In warp_tauri directory
cd character_pipeline
python atlas_protocol.py --port 8765 --test
```

## Project Structure

```
Assets/
├── Scripts/
│   ├── SAM/
│   │   ├── SAMAvatarController.cs   # Main controller
│   │   ├── SAMConnection.cs         # WebSocket client
│   │   └── BlendShapeController.cs    # Shape key mapping
│   ├── Physics/
│   │   └── SoftBodyPhysics.cs         # Jiggle physics + JigglePhysics
│   ├── Animation/
│   │   ├── SAMAnimator.cs           # Main animator (idle, emotions, gestures)
│   │   ├── LipSyncController.cs       # Viseme-based lip sync
│   │   └── AnimationLibrary.cs        # Animation definitions & library
│   └── UI/
│       └── (debug UI)
├── Editor/
│   ├── BlenderSetupGenerator.cs       # Blender script generator
│   └── SAMSceneSetup.cs             # Scene creation & model setup
├── Scenes/
│   └── SAMAvatar.unity              # Main scene (auto-created)
├── Prefabs/
│   └── SAMAvatar.prefab             # Avatar prefab
├── Materials/
│   └── (skin, hair materials)
└── Shaders/
    └── SkinSSS.shader                 # Subsurface scattering skin
```

## Quick Scene Setup

In Unity, go to **SAM → Create Avatar Scene** to auto-generate:
- Three-point lighting (key, fill, rim)
- Orbit camera with mouse controls
- Avatar placeholder
- Debug UI canvas

Then select your imported model and use **SAM → Quick Setup Selected Model** to auto-add all components.

## Required Shape Keys

Your model needs these blend shapes (shape keys in Blender):

### Body (45 shapes)
- `body_height`, `body_weight`, `body_muscularity`, `body_bodyFat`
- `body_shoulderWidth`, `body_chestSize`, `body_armSize`
- `body_buttSize`, `body_buttShape`, `body_thighSize`, `body_calfSize`
- `body_breathing` (for idle animation)
- ... (see full list in BlendShapeController.cs)

### Face (60+ shapes)
- `face_jawWidth`, `face_jawDefinition`, `face_chinSize`
- `face_eyeSize`, `face_eyebrowThickness`, `face_noseLength`
- `face_smile`, `face_smirk`, `face_frown` (expressions)
- `face_viseme_A/E/I/O/U/M/F/TH/S/T/K/R/W` (lip sync)
- `face_beardDensity`, `face_hairLength`
- ... (see full list in BlendShapeController.cs)

### Anatomy (17 shapes)
- `anatomy_penisLength`, `anatomy_penisGirth`, `anatomy_penisHeadSize`
- `anatomy_penisCurvature`, `anatomy_penisCurvatureUp`
- `anatomy_circumcised`, `anatomy_foreskinLength`
- `anatomy_testicleSize`, `anatomy_testicleHang`, `anatomy_scrotumSize`
- `anatomy_arousal`, `anatomy_erect` (state)
- ... (see full list in BlendShapeController.cs)

## WebSocket Protocol

The avatar communicates with Warp Open via WebSocket:

### Commands (Warp → Unity)

```json
// Animation
{"type": "animation", "animation": "talking", "intensity": 0.8}

// Emotion
{"type": "emotion", "emotion": "flirty", "intensity": 1.0}

// Morph targets
{"type": "morph", "morph_targets": {"body_height": 0.7, "face_smile": 0.5}}

// Lip sync
{"type": "lipsync", "data": [...], "totalDuration": 2500}
```

### Events (Unity → Warp)

```json
// State change
{"type": "state_change", "data": {"animation": "idle"}}

// User interaction
{"type": "user_gesture", "data": {"gesture": "wave"}}
```

## Building

### macOS
1. File → Build Settings
2. Platform: macOS
3. Architecture: Apple Silicon (or Intel)
4. Build

### iOS
1. File → Build Settings
2. Platform: iOS
3. Switch Platform
4. Build → Open in Xcode → Archive

### Embedding in Warp Open
The avatar can be embedded as:
1. Separate window (current)
2. WebGL build embedded in terminal
3. Native view via Tauri plugin

## Physics

The project includes soft body physics for realistic anatomy movement:

- `SoftBodyPhysics.cs` - Spring-based jiggle for anatomy
- `JigglePhysics.cs` - Secondary motion for butt/chest

For production quality, consider:
- [Magica Cloth 2](https://assetstore.unity.com/packages/tools/physics/magica-cloth-2-242307)
- [Obi Softbody](https://assetstore.unity.com/packages/tools/physics/obi-softbody-130029)

## License

Part of Warp Open terminal project.
