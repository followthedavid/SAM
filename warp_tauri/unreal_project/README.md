# Warp SAM - Hyper-Realistic MetaHuman Avatar

Unreal Engine 5 project for rendering a hyper-realistic male avatar with MetaHuman technology.

## Features

- **Photorealistic rendering** via Lumen global illumination
- **Strand-based hair** with real-time simulation
- **200+ facial blend shapes** (FACS/ARKit compatible)
- **Real-time lip sync** with viseme mapping
- **Adult anatomy support** with physics
- **WebSocket integration** with Warp Open terminal

## Requirements

- Unreal Engine 5.3+
- macOS 12+ (Metal) / Windows 10+ (DX12)
- 16GB RAM minimum, 32GB recommended
- GPU with ray tracing support recommended (not required)

## Quick Start

### 1. Create Your MetaHuman

1. Go to [metahuman.unrealengine.com](https://metahuman.unrealengine.com)
2. Create a new MetaHuman (it's FREE)
3. Customize face, body, hair, clothing
4. Click "Download" → select "UE 5.3"
5. Open Quixel Bridge in UE, import your MetaHuman

### 2. Open This Project

```bash
# In Unreal Engine
File → Open Project → Select WarpSAM.uproject
```

### 3. Set Up the Avatar

1. Drag your MetaHuman into the level
2. Add `SAMMetaHumanController` component
3. Assign the mesh references:
   - Body Mesh: `BP_YourMetaHuman → Body`
   - Face Mesh: `BP_YourMetaHuman → Face`
   - Hair/Beard Grooms

### 4. Connect to Warp Open

The avatar auto-connects to `ws://localhost:8765`.

Test manually:
```bash
cd ../character_pipeline
python atlas_protocol.py --port 8765 --test
```

## Adding Adult Anatomy

MetaHuman doesn't include adult anatomy. Here's how to add it:

### Option A: Custom Mesh Addition

1. **Create in Blender:**
   ```
   - Model anatomically correct geometry
   - Rig with bones: shaft_base, shaft_mid, shaft_tip, glans, testicle_L, testicle_R
   - Add shape keys matching our naming convention
   - Export as FBX
   ```

2. **Import to UE:**
   ```
   - Import FBX with skeleton
   - Create Physics Asset for jiggle
   - Attach to MetaHuman pelvis bone
   ```

3. **Add soft body physics:**
   - Use Chaos Cloth or custom spring simulation
   - Configure bone chain dynamics

### Option B: Marketplace Assets

Several adult-ready assets exist on marketplaces:
- CGTrader (search "anatomically correct male")
- TurboSquid
- Sketchfab (some CC0)

Key requirements:
- Rigged skeleton compatible with UE
- Blend shapes for size/arousal states
- 4K+ textures for realism

### Shape Keys Required

```
anatomy_penisLength      (0-1: flaccid to maximum)
anatomy_penisGirth       (0-1: thin to thick)
anatomy_penisHeadSize    (0-1: proportional)
anatomy_penisCurvature   (0-1: straight to curved)
anatomy_circumcised      (0-1: foreskin to circumcised)
anatomy_testicleSize     (0-1: small to large)
anatomy_testicleHang     (0-1: tight to hanging)
anatomy_scrotumSize      (0-1: tight to full)
anatomy_arousal          (0-1: flaccid to erect)
anatomy_erect            (0-1: angle/firmness)
```

## Rendering Quality

### Enabled by Default

| Feature | Purpose |
|---------|---------|
| Lumen GI | Real-time global illumination |
| Nanite | Unlimited polygon detail |
| Hair Strands | Realistic hair simulation |
| Virtual Shadow Maps | Detailed shadows |
| SSS | Subsurface scattering for skin |
| Ray Tracing | Optional, for reflections/AO |

### Performance Tiers

**Ultra (RTX 3080+):**
- Full ray tracing
- 4K internal resolution
- Max hair strand density

**High (RTX 3060 / M1 Pro):**
- Lumen software tracing
- 1440p internal
- Medium hair density

**Medium (GTX 1080 / M1):**
- Reduced Lumen quality
- 1080p internal
- Lower hair density

## Project Structure

```
Source/SAM/
├── SAMModule.cpp           # Module registration
├── SAMConnection.h/.cpp    # WebSocket to Warp Open
├── SAMMetaHumanController  # Main avatar controller
└── (more to come)

Content/
├── MetaHumans/               # Your imported MetaHumans
├── Blueprints/               # Animation BPs, UI
├── Animations/               # Custom animations
└── Materials/                # Skin, anatomy materials
```

## WebSocket Protocol

Same as Unity version - see `../character_pipeline/atlas_protocol.py`

### Key Commands

```json
// Facial expression
{"type": "emotion", "emotion": "flirty", "intensity": 0.8}

// Morph targets
{"type": "morph", "morph_targets": {"jawOpen": 0.3}}

// Lip sync
{"type": "lipsync", "data": [{"time": 0, "viseme": "A", "intensity": 1}]}

// Arousal state
{"type": "arousal", "level": 0.5}
```

## Live Link (Optional)

For real-time facial capture from iPhone:

1. Install "Live Link Face" app on iPhone
2. Enable LiveLink plugin in UE
3. Connect iPhone to same network
4. Expressions drive MetaHuman in real-time

## Building

### macOS
```
File → Package Project → macOS
```

### iOS (for future companion app)
```
File → Package Project → iOS
# Requires Apple Developer account
```

## Troubleshooting

**Hair not rendering:**
- Enable HairStrands plugin
- Check groom binding to skeleton

**Poor performance:**
- Reduce Lumen quality in Project Settings
- Disable ray tracing if not needed
- Lower hair strand count

**WebSocket not connecting:**
- Verify Warp Open is running
- Check firewall settings
- Confirm port 8765 is available

## License

Part of Warp Open terminal project.
