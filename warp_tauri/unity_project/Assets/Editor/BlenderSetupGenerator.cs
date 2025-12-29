using UnityEngine;
using UnityEditor;
using System.IO;

namespace SAM.Avatar.Editor
{
    /// <summary>
    /// Generates Blender Python scripts to set up your model with all required shape keys
    /// </summary>
    public class BlenderSetupGenerator : EditorWindow
    {
        [MenuItem("SAM/Generate Blender Shape Key Script")]
        public static void GenerateScript()
        {
            string script = GenerateBlenderScript();

            string path = EditorUtility.SaveFilePanel(
                "Save Blender Script",
                "",
                "atlas_shape_keys.py",
                "py"
            );

            if (!string.IsNullOrEmpty(path))
            {
                File.WriteAllText(path, script);
                Debug.Log($"[SAM] Blender script saved to: {path}");
                EditorUtility.RevealInFinder(path);
            }
        }

        [MenuItem("SAM/Show Required Shape Keys")]
        public static void ShowShapeKeys()
        {
            GetWindow<BlenderSetupGenerator>("SAM Shape Keys");
        }

        private Vector2 scrollPos;

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Required Shape Keys for SAM Avatar", EditorStyles.boldLabel);
            EditorGUILayout.Space();

            EditorGUILayout.HelpBox(
                "Your Blender model needs these shape keys (blend shapes) for full SAM integration.\n\n" +
                "Click 'Generate Blender Script' to create a Python script that adds them automatically.",
                MessageType.Info
            );

            EditorGUILayout.Space();

            if (GUILayout.Button("Generate Blender Script", GUILayout.Height(30)))
            {
                GenerateScript();
            }

            EditorGUILayout.Space();
            EditorGUILayout.LabelField("Shape Key List:", EditorStyles.boldLabel);

            scrollPos = EditorGUILayout.BeginScrollView(scrollPos);

            var names = BlendShapeNaming.GetAllExpectedNames();
            string currentCategory = "";

            foreach (var name in names)
            {
                string category = name.Split('_')[0];
                if (category != currentCategory)
                {
                    currentCategory = category;
                    EditorGUILayout.Space();
                    EditorGUILayout.LabelField(category.ToUpper(), EditorStyles.boldLabel);
                }

                EditorGUILayout.LabelField("  " + name);
            }

            EditorGUILayout.EndScrollView();
        }

        private static string GenerateBlenderScript()
        {
            return @"'''
SAM Avatar - Blender Shape Key Setup Script
==============================================
Run this script in Blender to create all required shape keys for SAM integration.

Usage:
1. Open your character model in Blender
2. Select the mesh object
3. Open the Scripting workspace
4. Paste this script and run it

The script will create shape keys for:
- Body customization (height, muscularity, etc.)
- Face customization (jaw, eyes, nose, etc.)
- Anatomy customization (size, shape, etc.)
- Lip sync visemes
- Animation expressions
'''

import bpy

def create_shape_keys():
    # Get active object
    obj = bpy.context.active_object

    if obj is None:
        print('ERROR: No object selected!')
        return

    if obj.type != 'MESH':
        print('ERROR: Selected object is not a mesh!')
        return

    mesh = obj.data
    print(f'Setting up shape keys for: {obj.name}')

    # Add basis shape key if not exists
    if mesh.shape_keys is None:
        obj.shape_key_add(name='Basis')
        print('Created Basis shape key')

    # All required shape keys
    shape_keys = {
        # ===== BODY =====
        'body': [
            # Overall
            'body_height', 'body_weight', 'body_muscularity', 'body_bodyFat', 'body_age',

            # Upper Body
            'body_shoulderWidth', 'body_chestSize', 'body_chestDefinition',
            'body_nippleSize', 'body_nipplePosition', 'body_armSize', 'body_forearmSize',
            'body_handSize', 'body_neckThickness', 'body_trapsSize',

            # Core
            'body_waistWidth', 'body_absDefinition', 'body_vTaperIntensity',
            'body_loveHandles', 'body_backWidth',

            # Lower Body
            'body_hipWidth', 'body_buttSize', 'body_buttShape', 'body_buttFirmness',
            'body_thighSize', 'body_thighGap', 'body_calfSize', 'body_calfDefinition',
            'body_ankleThickness', 'body_footSize',

            # Skin & Hair
            'body_skinTone', 'body_skinTexture', 'body_bodyHairDensity',
            'body_bodyHairPattern', 'body_tanLines', 'body_freckles',
            'body_scars', 'body_veinyness',

            # Posture
            'body_postureConfidence', 'body_shoulderRoll', 'body_hipTilt',
            'body_headTilt', 'body_stanceWidth',

            # Animation
            'body_breathing', 'body_buttJiggle', 'body_chestJiggle'
        ],

        # ===== FACE =====
        'face': [
            # Face Shape
            'face_faceLength', 'face_faceWidth', 'face_jawWidth', 'face_jawDefinition',
            'face_chinSize', 'face_chinShape', 'face_chinCleft',
            'face_cheekboneHeight', 'face_cheekboneProminence', 'face_cheekFullness',

            # Forehead
            'face_foreheadHeight', 'face_foreheadWidth', 'face_foreheadSlope', 'face_browRidgeSize',

            # Eyes
            'face_eyeSize', 'face_eyeWidth', 'face_eyeSpacing', 'face_eyeDepth',
            'face_eyeTilt', 'face_eyebrowThickness', 'face_eyebrowArch',
            'face_eyebrowSpacing', 'face_eyelashLength', 'face_upperEyelid', 'face_lowerEyelid',
            'face_crowsFeet', 'face_eyesClosed', 'face_eyeSquint', 'face_eyeNarrow',
            'face_eyeIntensity', 'face_eyeLidLower',

            # Nose
            'face_noseLength', 'face_noseWidth', 'face_noseBridgeHeight', 'face_noseBridgeWidth',
            'face_noseTipSize', 'face_noseTipShape', 'face_nostrilSize', 'face_nostrilFlare',

            # Mouth
            'face_mouthWidth', 'face_mouthPosition', 'face_upperLipSize', 'face_lowerLipSize',
            'face_lipFullness', 'face_cupidsBow', 'face_mouthCorners', 'face_philtrumDepth',
            'face_smile', 'face_smirk', 'face_frown', 'face_mouthOpen', 'face_jawClench',
            'face_tongueOut', 'face_chinUp',

            # Ears
            'face_earSize', 'face_earAngle', 'face_earlobeSize',

            # Facial Hair
            'face_beardDensity', 'face_beardLength', 'face_beardStyle',
            'face_mustacheSize', 'face_sideburnsLength', 'face_stubbleAmount', 'face_beardGray',

            # Hair
            'face_hairLength', 'face_hairVolume', 'face_hairGray', 'face_hairlineRecession',

            # Age
            'face_wrinkleForehead', 'face_wrinkleEyes', 'face_wrinkleMouth', 'face_skinAge',

            # Expressions
            'face_browRaise', 'face_browRaiseInner', 'face_browFurrow',

            # Visemes (lip sync)
            'face_viseme_REST', 'face_viseme_A', 'face_viseme_E', 'face_viseme_I',
            'face_viseme_O', 'face_viseme_U', 'face_viseme_M', 'face_viseme_F',
            'face_viseme_TH', 'face_viseme_S', 'face_viseme_T', 'face_viseme_K',
            'face_viseme_R', 'face_viseme_W'
        ],

        # ===== ANATOMY =====
        'anatomy': [
            # Size & Shape
            'anatomy_penisLength', 'anatomy_penisGirth', 'anatomy_penisHeadSize',
            'anatomy_penisCurvature', 'anatomy_penisCurvatureUp', 'anatomy_penisVeininess',
            'anatomy_circumcised', 'anatomy_foreskinLength',

            # Testicles
            'anatomy_scrotumSize', 'anatomy_testicleSize', 'anatomy_testicleHang',
            'anatomy_testicleAsymmetry',

            # Pubic
            'anatomy_pubicHairDensity', 'anatomy_pubicHairStyle', 'anatomy_groinDefinition',

            # State
            'anatomy_arousal', 'anatomy_erect'
        ]
    }

    # Create all shape keys
    created = 0
    existing = 0

    for category, keys in shape_keys.items():
        print(f'\n--- {category.upper()} ---')
        for name in keys:
            existing_keys = [sk.name for sk in mesh.shape_keys.key_blocks]
            if name not in existing_keys:
                obj.shape_key_add(name=name)
                created += 1
                print(f'  + Created: {name}')
            else:
                existing += 1
                print(f'  = Exists: {name}')

    # Summary
    total = len(mesh.shape_keys.key_blocks) - 1  # Exclude Basis
    print(f'\n===== SUMMARY =====')
    print(f'Created: {created}')
    print(f'Already existed: {existing}')
    print(f'Total shape keys: {total}')
    print(f'===================\n')

    print('Done! Your model is ready for SAM integration.')
    print('Export as FBX with shape keys enabled.')

# Run
create_shape_keys()
";
        }
    }
}
