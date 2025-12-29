using System.Collections.Generic;
using UnityEngine;

namespace SAM.Avatar
{
    /// <summary>
    /// Maps Warp Open character customization parameters to Unity blend shapes.
    /// Supports 100+ parameters across body, face, and anatomy.
    ///
    /// Blend shape naming convention in your model:
    /// - Body: body_height, body_muscularity, body_chestSize, etc.
    /// - Face: face_jawWidth, face_eyeSize, face_beardDensity, etc.
    /// - Anatomy: anatomy_penisLength, anatomy_testicleSize, etc.
    /// - Visemes: face_viseme_A, face_viseme_E, face_viseme_O, etc.
    /// </summary>
    public class BlendShapeController
    {
        private SkinnedMeshRenderer _bodyMesh;
        private SkinnedMeshRenderer _faceMesh;
        private SkinnedMeshRenderer _anatomyMesh;

        // Blend shape index caches
        private Dictionary<string, BlendShapeInfo> _blendShapeCache = new Dictionary<string, BlendShapeInfo>();

        // All expected blend shape names (for validation)
        private static readonly string[] BodyBlendShapes = new[]
        {
            // Overall
            "body_height", "body_weight", "body_muscularity", "body_bodyFat", "body_age",

            // Upper Body
            "body_shoulderWidth", "body_chestSize", "body_chestDefinition",
            "body_nippleSize", "body_nipplePosition", "body_armSize", "body_forearmSize",
            "body_handSize", "body_neckThickness", "body_trapsSize",

            // Core
            "body_waistWidth", "body_absDefinition", "body_vTaperIntensity",
            "body_loveHandles", "body_backWidth",

            // Lower Body
            "body_hipWidth", "body_buttSize", "body_buttShape", "body_buttFirmness",
            "body_thighSize", "body_thighGap", "body_calfSize", "body_calfDefinition",
            "body_ankleThickness", "body_footSize",

            // Skin & Hair
            "body_skinTone", "body_skinTexture", "body_bodyHairDensity",
            "body_bodyHairPattern", "body_tanLines", "body_freckles",
            "body_scars", "body_veinyness",

            // Posture
            "body_postureConfidence", "body_shoulderRoll", "body_hipTilt",
            "body_headTilt", "body_stanceWidth",

            // Animation
            "body_breathing"
        };

        private static readonly string[] FaceBlendShapes = new[]
        {
            // Face Shape
            "face_faceLength", "face_faceWidth", "face_jawWidth", "face_jawDefinition",
            "face_chinSize", "face_chinShape", "face_chinCleft",
            "face_cheekboneHeight", "face_cheekboneProminence", "face_cheekFullness",

            // Forehead
            "face_foreheadHeight", "face_foreheadWidth", "face_foreheadSlope", "face_browRidgeSize",

            // Eyes
            "face_eyeSize", "face_eyeWidth", "face_eyeSpacing", "face_eyeDepth",
            "face_eyeTilt", "face_eyeColor", "face_eyebrowThickness", "face_eyebrowArch",
            "face_eyebrowSpacing", "face_eyelashLength", "face_upperEyelid", "face_lowerEyelid",
            "face_crowsFeet", "face_eyesClosed", "face_eyeSquint", "face_eyeNarrow",
            "face_eyeIntensity", "face_eyeLidLower",

            // Nose
            "face_noseLength", "face_noseWidth", "face_noseBridgeHeight", "face_noseBridgeWidth",
            "face_noseTipSize", "face_noseTipShape", "face_nostrilSize", "face_nostrilFlare",

            // Mouth
            "face_mouthWidth", "face_mouthPosition", "face_upperLipSize", "face_lowerLipSize",
            "face_lipFullness", "face_lipColor", "face_cupidsBow", "face_mouthCorners",
            "face_philtrumDepth", "face_smile", "face_smirk", "face_frown",
            "face_mouthOpen", "face_jawClench", "face_tongueOut", "face_chinUp",

            // Ears
            "face_earSize", "face_earAngle", "face_earlobeSize", "face_earlobeAttached",

            // Facial Hair
            "face_beardDensity", "face_beardLength", "face_beardStyle",
            "face_mustacheSize", "face_sideburnsLength", "face_stubbleAmount", "face_beardGray",

            // Hair
            "face_hairStyle", "face_hairLength", "face_hairVolume", "face_hairColor",
            "face_hairGray", "face_hairlineRecession", "face_hairPartSide", "face_hairTexture",

            // Age
            "face_wrinkleForehead", "face_wrinkleEyes", "face_wrinkleMouth",
            "face_skinAge", "face_facialAsymmetry",

            // Expression overrides
            "face_browRaise", "face_browRaiseInner", "face_browFurrow",

            // Visemes (lip sync)
            "face_viseme_REST", "face_viseme_A", "face_viseme_E", "face_viseme_I",
            "face_viseme_O", "face_viseme_U", "face_viseme_M", "face_viseme_F",
            "face_viseme_TH", "face_viseme_S", "face_viseme_T", "face_viseme_K",
            "face_viseme_R", "face_viseme_W"
        };

        private static readonly string[] AnatomyBlendShapes = new[]
        {
            // Size & Shape
            "anatomy_penisLength", "anatomy_penisGirth", "anatomy_penisHeadSize",
            "anatomy_penisCurvature", "anatomy_penisCurvatureUp", "anatomy_penisVeininess",
            "anatomy_circumcised", "anatomy_foreskinLength",

            // Testicles
            "anatomy_scrotumSize", "anatomy_testicleSize", "anatomy_testicleHang",
            "anatomy_testicleAsymmetry",

            // Pubic
            "anatomy_pubicHairDensity", "anatomy_pubicHairStyle", "anatomy_groinDefinition",

            // State
            "anatomy_arousal", "anatomy_erect"
        };

        public BlendShapeController(
            SkinnedMeshRenderer bodyMesh,
            SkinnedMeshRenderer faceMesh,
            SkinnedMeshRenderer anatomyMesh)
        {
            _bodyMesh = bodyMesh;
            _faceMesh = faceMesh;
            _anatomyMesh = anatomyMesh;
        }

        /// <summary>
        /// Initialize and cache all blend shape indices
        /// </summary>
        public void Initialize()
        {
            CacheBlendShapes(_bodyMesh, "body");
            CacheBlendShapes(_faceMesh, "face");
            CacheBlendShapes(_anatomyMesh, "anatomy");

            Debug.Log($"[BlendShape] Cached {_blendShapeCache.Count} blend shapes");

            // Log any missing expected shapes
            ValidateBlendShapes();
        }

        private void CacheBlendShapes(SkinnedMeshRenderer mesh, string prefix)
        {
            if (mesh == null || mesh.sharedMesh == null) return;

            Mesh sharedMesh = mesh.sharedMesh;
            int count = sharedMesh.blendShapeCount;

            for (int i = 0; i < count; i++)
            {
                string name = sharedMesh.GetBlendShapeName(i);

                // Normalize name (remove any prefix if already present)
                string normalizedName = name;
                if (!name.StartsWith(prefix + "_"))
                {
                    normalizedName = $"{prefix}_{name}";
                }

                _blendShapeCache[normalizedName] = new BlendShapeInfo
                {
                    Mesh = mesh,
                    Index = i,
                    OriginalName = name
                };

                // Also cache the original name
                _blendShapeCache[name] = _blendShapeCache[normalizedName];
            }
        }

        private void ValidateBlendShapes()
        {
            var allExpected = new List<string>();
            allExpected.AddRange(BodyBlendShapes);
            allExpected.AddRange(FaceBlendShapes);
            allExpected.AddRange(AnatomyBlendShapes);

            var missing = new List<string>();
            foreach (var name in allExpected)
            {
                if (!_blendShapeCache.ContainsKey(name))
                {
                    missing.Add(name);
                }
            }

            if (missing.Count > 0)
            {
                Debug.LogWarning($"[BlendShape] Missing {missing.Count} blend shapes in model:\n" +
                    string.Join(", ", missing.GetRange(0, Mathf.Min(10, missing.Count))) +
                    (missing.Count > 10 ? $"... and {missing.Count - 10} more" : ""));
            }
        }

        /// <summary>
        /// Set a blend shape value (0-1)
        /// </summary>
        public void SetBlendShape(string name, float value)
        {
            if (_blendShapeCache.TryGetValue(name, out var info))
            {
                info.Mesh.SetBlendShapeWeight(info.Index, value * 100f);
            }
        }

        /// <summary>
        /// Get current blend shape value
        /// </summary>
        public float GetBlendShape(string name)
        {
            if (_blendShapeCache.TryGetValue(name, out var info))
            {
                return info.Mesh.GetBlendShapeWeight(info.Index) / 100f;
            }
            return 0f;
        }

        /// <summary>
        /// Check if a blend shape exists
        /// </summary>
        public bool HasBlendShape(string name)
        {
            return _blendShapeCache.ContainsKey(name);
        }

        /// <summary>
        /// Get all cached blend shape names
        /// </summary>
        public IEnumerable<string> GetAllBlendShapeNames()
        {
            return _blendShapeCache.Keys;
        }

        /// <summary>
        /// Reset all blend shapes to default (0)
        /// </summary>
        public void ResetAll()
        {
            foreach (var info in _blendShapeCache.Values)
            {
                info.Mesh.SetBlendShapeWeight(info.Index, 0f);
            }
        }

        /// <summary>
        /// Apply a full character configuration
        /// </summary>
        public void ApplyConfiguration(Dictionary<string, float> values)
        {
            foreach (var kvp in values)
            {
                SetBlendShape(kvp.Key, kvp.Value);
            }
        }

        private class BlendShapeInfo
        {
            public SkinnedMeshRenderer Mesh;
            public int Index;
            public string OriginalName;
        }
    }

    /// <summary>
    /// Utility to help with blend shape naming in Blender
    /// </summary>
    public static class BlendShapeNaming
    {
        /// <summary>
        /// Get all expected blend shape names for your Blender model
        /// </summary>
        public static string[] GetAllExpectedNames()
        {
            var all = new List<string>();

            // Body shapes
            all.AddRange(new[]
            {
                "body_height", "body_weight", "body_muscularity", "body_bodyFat", "body_age",
                "body_shoulderWidth", "body_chestSize", "body_chestDefinition",
                "body_nippleSize", "body_nipplePosition", "body_armSize", "body_forearmSize",
                "body_handSize", "body_neckThickness", "body_trapsSize",
                "body_waistWidth", "body_absDefinition", "body_vTaperIntensity",
                "body_loveHandles", "body_backWidth",
                "body_hipWidth", "body_buttSize", "body_buttShape", "body_buttFirmness",
                "body_thighSize", "body_thighGap", "body_calfSize", "body_calfDefinition",
                "body_ankleThickness", "body_footSize",
                "body_skinTone", "body_skinTexture", "body_bodyHairDensity",
                "body_bodyHairPattern", "body_tanLines", "body_freckles",
                "body_scars", "body_veinyness",
                "body_postureConfidence", "body_shoulderRoll", "body_hipTilt",
                "body_headTilt", "body_stanceWidth", "body_breathing"
            });

            // Face shapes
            all.AddRange(new[]
            {
                "face_faceLength", "face_faceWidth", "face_jawWidth", "face_jawDefinition",
                "face_chinSize", "face_chinShape", "face_chinCleft",
                "face_cheekboneHeight", "face_cheekboneProminence", "face_cheekFullness",
                "face_foreheadHeight", "face_foreheadWidth", "face_foreheadSlope", "face_browRidgeSize",
                "face_eyeSize", "face_eyeWidth", "face_eyeSpacing", "face_eyeDepth",
                "face_eyeTilt", "face_eyebrowThickness", "face_eyebrowArch",
                "face_eyebrowSpacing", "face_eyelashLength", "face_upperEyelid", "face_lowerEyelid",
                "face_crowsFeet", "face_eyesClosed",
                "face_noseLength", "face_noseWidth", "face_noseBridgeHeight", "face_noseBridgeWidth",
                "face_noseTipSize", "face_noseTipShape", "face_nostrilSize", "face_nostrilFlare",
                "face_mouthWidth", "face_mouthPosition", "face_upperLipSize", "face_lowerLipSize",
                "face_lipFullness", "face_cupidsBow", "face_mouthCorners", "face_philtrumDepth",
                "face_smile", "face_smirk", "face_frown", "face_mouthOpen",
                "face_earSize", "face_earAngle", "face_earlobeSize",
                "face_beardDensity", "face_beardLength", "face_beardStyle",
                "face_mustacheSize", "face_sideburnsLength", "face_stubbleAmount", "face_beardGray",
                "face_hairLength", "face_hairVolume", "face_hairGray", "face_hairlineRecession",
                "face_wrinkleForehead", "face_wrinkleEyes", "face_wrinkleMouth", "face_skinAge"
            });

            // Visemes
            all.AddRange(new[]
            {
                "face_viseme_REST", "face_viseme_A", "face_viseme_E", "face_viseme_I",
                "face_viseme_O", "face_viseme_U", "face_viseme_M", "face_viseme_F",
                "face_viseme_TH", "face_viseme_S", "face_viseme_T", "face_viseme_K",
                "face_viseme_R", "face_viseme_W"
            });

            // Anatomy shapes
            all.AddRange(new[]
            {
                "anatomy_penisLength", "anatomy_penisGirth", "anatomy_penisHeadSize",
                "anatomy_penisCurvature", "anatomy_penisCurvatureUp", "anatomy_penisVeininess",
                "anatomy_circumcised", "anatomy_foreskinLength",
                "anatomy_scrotumSize", "anatomy_testicleSize", "anatomy_testicleHang",
                "anatomy_testicleAsymmetry",
                "anatomy_pubicHairDensity", "anatomy_pubicHairStyle", "anatomy_groinDefinition",
                "anatomy_arousal", "anatomy_erect"
            });

            return all.ToArray();
        }

        /// <summary>
        /// Generate a Python script for Blender to create all shape keys
        /// </summary>
        public static string GenerateBlenderScript()
        {
            var names = GetAllExpectedNames();
            var script = @"
import bpy

# Get active object
obj = bpy.context.active_object
if obj is None or obj.type != 'MESH':
    print('Select a mesh object first!')
else:
    mesh = obj.data

    # Add basis shape key if not exists
    if mesh.shape_keys is None:
        obj.shape_key_add(name='Basis')

    # Shape keys to create
    shape_keys = [
";
            foreach (var name in names)
            {
                script += $"        '{name}',\n";
            }

            script += @"    ]

    # Create each shape key
    for name in shape_keys:
        if name not in [sk.name for sk in mesh.shape_keys.key_blocks]:
            obj.shape_key_add(name=name)
            print(f'Created: {name}')
        else:
            print(f'Exists: {name}')

    print(f'\nTotal shape keys: {len(mesh.shape_keys.key_blocks)}')
";
            return script;
        }
    }
}
