/*
 * SAM Character Importer for Unity 2022+
 *
 * This plugin automates:
 * 1. Importing generated FBX characters from Blender
 * 2. Setting up soft body physics for anatomy (using Magica Cloth 2 or Obi)
 * 3. Connecting to SAM Avatar Bridge via WebSocket
 * 4. Real-time animation control from SAM AI
 *
 * Usage in Unity:
 *     // Import a character
 *     SAMImporter.ImportCharacter("/path/to/character.fbx");
 *
 *     // Connect to SAM
 *     SAMConnection.Instance.Connect();
 *
 *     // Apply animation state
 *     SAMAnimator.SetState(AnimationState.Talking);
 *
 * Requires: Unity 2022.3+, Newtonsoft.JSON, WebSocketSharp (optional: Magica Cloth 2)
 */

using System;
using System.Collections.Generic;
using System.IO;
using System.Threading.Tasks;
using UnityEngine;
using UnityEditor;
using UnityEditor.AssetImporter;

#if UNITY_EDITOR
using UnityEditor.Animations;
#endif

namespace SAM.Character
{
    // ============================================================================
    // CONFIGURATION
    // ============================================================================

    [CreateAssetMenu(fileName = "SAMConfig", menuName = "SAM/Configuration")]
    public class SAMConfig : ScriptableObject
    {
        [Header("SAM WebSocket Settings")]
        public string samHost = "localhost";
        public int samPort = 8765;

        [Header("Import Settings")]
        public string importDestination = "Assets/Characters/SAM";
        public string animationDestination = "Assets/Animations/SAM";

        [Header("Physics Settings")]
        [Range(0f, 1f)] public float softBodyStiffness = 0.3f;
        [Range(0f, 1f)] public float softBodyDamping = 0.5f;
        [Range(0f, 2f)] public float collisionThickness = 0.5f;

        [Header("Material Settings")]
        public bool autoCreateMaterials = true;
        public bool subsurfaceScattering = true;
        public Shader skinShader;

        [Header("Bone Mapping (Blender to Unity)")]
        public BoneMapping[] boneMappings = new BoneMapping[]
        {
            new BoneMapping { sourceName = "anatomy_root", targetName = "anatomy_root" },
            new BoneMapping { sourceName = "shaft_base", targetName = "shaft_base" },
            new BoneMapping { sourceName = "shaft_mid", targetName = "shaft_mid" },
            new BoneMapping { sourceName = "shaft_tip", targetName = "shaft_tip" },
            new BoneMapping { sourceName = "glans", targetName = "glans" },
            new BoneMapping { sourceName = "testicle_L", targetName = "testicle_L" },
            new BoneMapping { sourceName = "testicle_R", targetName = "testicle_R" },
            new BoneMapping { sourceName = "scrotum", targetName = "scrotum" }
        };

        private static SAMConfig _instance;
        public static SAMConfig Instance
        {
            get
            {
                if (_instance == null)
                {
                    _instance = Resources.Load<SAMConfig>("SAMConfig");
                    if (_instance == null)
                    {
                        _instance = CreateInstance<SAMConfig>();
                    }
                }
                return _instance;
            }
        }
    }

    [Serializable]
    public class BoneMapping
    {
        public string sourceName;
        public string targetName;
    }

    // ============================================================================
    // ANIMATION STATES
    // ============================================================================

    public enum AnimationState
    {
        Idle,
        Talking,
        Thinking,
        Listening,
        Smirking,
        Flirting,
        Wink,
        EyebrowRaise,
        Laugh,
        Concerned,
        Excited,
        Aroused,
        Climax,
        Relaxed
    }

    public enum EmotionalState
    {
        Neutral,
        Happy,
        Sad,
        Confident,
        Flirty,
        Intense,
        Playful,
        Thoughtful,
        Concerned
    }

    // ============================================================================
    // DATA CLASSES
    // ============================================================================

    [Serializable]
    public class ImportedCharacter
    {
        public string name;
        public GameObject prefab;
        public SkinnedMeshRenderer skinnedMesh;
        public Animator animator;
        public Avatar avatar;
        public RuntimeAnimatorController animatorController;
        public List<Material> materials = new List<Material>();
        public Dictionary<string, int> blendShapeIndices = new Dictionary<string, int>();
        public List<string> morphTargetNames = new List<string>();

        // Runtime components
        [NonSerialized] public GameObject instance;
        [NonSerialized] public SAMSoftBodyController softBodyController;
    }

    [Serializable]
    public class SAMMessage
    {
        public string type;
        public string animation;
        public string emotion;
        public Dictionary<string, float> morph_targets;
        public string text;
        public float intensity = 1f;
    }

    // ============================================================================
    // CHARACTER IMPORTER (Editor)
    // ============================================================================

#if UNITY_EDITOR
    public class SAMCharacterImporter : EditorWindow
    {
        private static Dictionary<string, ImportedCharacter> _importedCharacters =
            new Dictionary<string, ImportedCharacter>();

        private string fbxPath = "";
        private string characterName = "";
        private bool setupPhysics = true;
        private bool createAnimator = true;

        [MenuItem("SAM/Import Character")]
        public static void ShowWindow()
        {
            GetWindow<SAMCharacterImporter>("SAM Character Importer");
        }

        private void OnGUI()
        {
            GUILayout.Label("SAM Character Import", EditorStyles.boldLabel);
            GUILayout.Space(10);

            EditorGUILayout.BeginHorizontal();
            fbxPath = EditorGUILayout.TextField("FBX Path:", fbxPath);
            if (GUILayout.Button("Browse", GUILayout.Width(60)))
            {
                string path = EditorUtility.OpenFilePanel("Select FBX", "", "fbx");
                if (!string.IsNullOrEmpty(path))
                {
                    fbxPath = path;
                    characterName = Path.GetFileNameWithoutExtension(path);
                }
            }
            EditorGUILayout.EndHorizontal();

            characterName = EditorGUILayout.TextField("Character Name:", characterName);

            GUILayout.Space(10);
            GUILayout.Label("Options", EditorStyles.boldLabel);
            setupPhysics = EditorGUILayout.Toggle("Setup Soft Body Physics", setupPhysics);
            createAnimator = EditorGUILayout.Toggle("Create Animator Controller", createAnimator);

            GUILayout.Space(20);

            EditorGUI.BeginDisabledGroup(string.IsNullOrEmpty(fbxPath));
            if (GUILayout.Button("Import Character", GUILayout.Height(40)))
            {
                ImportCharacter(fbxPath, characterName);
            }
            EditorGUI.EndDisabledGroup();

            GUILayout.Space(20);

            // List imported characters
            if (_importedCharacters.Count > 0)
            {
                GUILayout.Label("Imported Characters", EditorStyles.boldLabel);
                foreach (var kvp in _importedCharacters)
                {
                    EditorGUILayout.BeginHorizontal();
                    GUILayout.Label(kvp.Key);
                    if (GUILayout.Button("Select", GUILayout.Width(60)))
                    {
                        Selection.activeObject = kvp.Value.prefab;
                    }
                    EditorGUILayout.EndHorizontal();
                }
            }
        }

        public static ImportedCharacter ImportCharacter(
            string fbxPath,
            string name = null,
            string destination = null)
        {
            if (!File.Exists(fbxPath))
            {
                Debug.LogError($"[SAM] FBX not found: {fbxPath}");
                return null;
            }

            string charName = name ?? Path.GetFileNameWithoutExtension(fbxPath);
            string destPath = destination ?? $"{SAMConfig.Instance.importDestination}/{charName}";

            Debug.Log($"[SAM] Importing character: {charName}");

            // Ensure destination exists
            if (!AssetDatabase.IsValidFolder(destPath))
            {
                CreateFolderRecursive(destPath);
            }

            // Copy FBX to project
            string targetFbxPath = $"{destPath}/{charName}.fbx";
            string absoluteTargetPath = Path.Combine(
                Application.dataPath.Replace("Assets", ""),
                targetFbxPath
            );

            File.Copy(fbxPath, absoluteTargetPath, true);
            AssetDatabase.Refresh();

            // Configure import settings
            ConfigureModelImporter(targetFbxPath);

            // Load imported asset
            GameObject modelPrefab = AssetDatabase.LoadAssetAtPath<GameObject>(targetFbxPath);
            if (modelPrefab == null)
            {
                Debug.LogError($"[SAM] Failed to load imported model: {targetFbxPath}");
                return null;
            }

            // Create character data
            var character = new ImportedCharacter
            {
                name = charName,
                prefab = modelPrefab
            };

            // Get skinned mesh renderer
            character.skinnedMesh = modelPrefab.GetComponentInChildren<SkinnedMeshRenderer>();
            if (character.skinnedMesh != null)
            {
                // Get blend shapes
                Mesh mesh = character.skinnedMesh.sharedMesh;
                for (int i = 0; i < mesh.blendShapeCount; i++)
                {
                    string shapeName = mesh.GetBlendShapeName(i);
                    character.blendShapeIndices[shapeName] = i;
                    character.morphTargetNames.Add(shapeName);
                }

                Debug.Log($"[SAM] Found {mesh.blendShapeCount} blend shapes");
            }

            // Get animator
            character.animator = modelPrefab.GetComponent<Animator>();
            if (character.animator != null)
            {
                character.avatar = character.animator.avatar;
            }

            // Setup materials
            if (SAMConfig.Instance.autoCreateMaterials)
            {
                SetupMaterials(character, destPath);
            }

            // Create animator controller
            CreateAnimatorController(character, destPath);

            // Store reference
            _importedCharacters[charName] = character;

            Debug.Log($"[SAM] Character imported successfully: {charName}");
            Debug.Log($"[SAM]   - Blend shapes: {character.morphTargetNames.Count}");
            Debug.Log($"[SAM]   - Materials: {character.materials.Count}");

            return character;
        }

        private static void CreateFolderRecursive(string path)
        {
            string[] parts = path.Split('/');
            string current = parts[0];

            for (int i = 1; i < parts.Length; i++)
            {
                string next = parts[i];
                string fullPath = $"{current}/{next}";

                if (!AssetDatabase.IsValidFolder(fullPath))
                {
                    AssetDatabase.CreateFolder(current, next);
                }
                current = fullPath;
            }
        }

        private static void ConfigureModelImporter(string assetPath)
        {
            ModelImporter importer = AssetImporter.GetAtPath(assetPath) as ModelImporter;
            if (importer == null) return;

            // General settings
            importer.importAnimation = true;
            importer.importBlendShapes = true;
            importer.importBlendShapeNormals = ModelImporterNormals.Calculate;

            // Rig settings
            importer.animationType = ModelImporterAnimationType.Human;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;

            // Materials
            importer.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
            importer.materialLocation = ModelImporterMaterialLocation.InPrefab;

            // Apply
            importer.SaveAndReimport();
        }

        private static void SetupMaterials(ImportedCharacter character, string destPath)
        {
            if (character.skinnedMesh == null) return;

            Material[] materials = character.skinnedMesh.sharedMaterials;

            for (int i = 0; i < materials.Length; i++)
            {
                Material mat = materials[i];
                if (mat == null) continue;

                string matName = mat.name;
                bool isSkin = matName.ToLower().Contains("skin") ||
                              matName.ToLower().Contains("body") ||
                              matName.ToLower().Contains("anatomy");

                if (isSkin && SAMConfig.Instance.subsurfaceScattering)
                {
                    // Create skin material with SSS
                    Material skinMat = CreateSkinMaterial(matName, destPath);
                    if (skinMat != null)
                    {
                        materials[i] = skinMat;
                        character.materials.Add(skinMat);
                    }
                }
                else
                {
                    character.materials.Add(mat);
                }
            }

            // Apply materials
            character.skinnedMesh.sharedMaterials = materials;
        }

        private static Material CreateSkinMaterial(string name, string destPath)
        {
            // Use skin shader if available, otherwise URP/HDRP Lit
            Shader shader = SAMConfig.Instance.skinShader;
            if (shader == null)
            {
                shader = Shader.Find("Universal Render Pipeline/Lit") ??
                         Shader.Find("HDRP/Lit") ??
                         Shader.Find("Standard");
            }

            if (shader == null) return null;

            Material mat = new Material(shader);
            mat.name = $"M_{name}_Skin";

            // Configure for skin
            if (mat.HasProperty("_Smoothness"))
                mat.SetFloat("_Smoothness", 0.4f);

            if (mat.HasProperty("_Metallic"))
                mat.SetFloat("_Metallic", 0f);

            // Subsurface scattering (HDRP)
            if (mat.HasProperty("_DiffusionProfileHash"))
            {
                // Would set diffusion profile here
            }

            // Save material
            string matPath = $"{destPath}/Materials/{mat.name}.mat";
            CreateFolderRecursive($"{destPath}/Materials");
            AssetDatabase.CreateAsset(mat, matPath);

            return mat;
        }

        private static void CreateAnimatorController(ImportedCharacter character, string destPath)
        {
            // Create animator controller
            string controllerPath = $"{destPath}/{character.name}_Controller.controller";

            AnimatorController controller = AnimatorController.CreateAnimatorControllerAtPath(controllerPath);

            // Add parameters
            controller.AddParameter("State", AnimatorControllerParameterType.Int);
            controller.AddParameter("Intensity", AnimatorControllerParameterType.Float);
            controller.AddParameter("Arousal", AnimatorControllerParameterType.Float);
            controller.AddParameter("IsTalking", AnimatorControllerParameterType.Bool);

            // Add base layer states
            AnimatorStateMachine rootStateMachine = controller.layers[0].stateMachine;

            // Create states for each animation state
            foreach (AnimationState state in Enum.GetValues(typeof(AnimationState)))
            {
                AnimatorState animState = rootStateMachine.AddState(state.ToString());
                // Motion would be assigned when animations are imported
            }

            // Set default state
            rootStateMachine.defaultState = rootStateMachine.states[0].state;

            // Add blend tree for emotions (optional)
            AnimatorState blendState = rootStateMachine.AddState("EmotionBlend");
            BlendTree blendTree;
            controller.CreateBlendTreeInController("EmotionBlend", out blendTree);
            blendTree.blendType = BlendTreeType.Simple1D;
            blendTree.blendParameter = "Intensity";
            blendState.motion = blendTree;

            // Save
            EditorUtility.SetDirty(controller);
            AssetDatabase.SaveAssets();

            character.animatorController = controller;

            // Apply to prefab animator
            if (character.animator != null)
            {
                character.animator.runtimeAnimatorController = controller;
            }
        }

        public static ImportedCharacter GetCharacter(string name)
        {
            return _importedCharacters.TryGetValue(name, out var character) ? character : null;
        }
    }
#endif

    // ============================================================================
    // ATLAS CONNECTION (Runtime)
    // ============================================================================

    public class SAMConnection : MonoBehaviour
    {
        public static SAMConnection Instance { get; private set; }

        public event Action<SAMMessage> OnMessageReceived;
        public event Action OnConnected;
        public event Action OnDisconnected;

        public bool IsConnected { get; private set; }

        private WebSocketClient _webSocket;
        private ImportedCharacter _currentCharacter;
        private Queue<SAMMessage> _messageQueue = new Queue<SAMMessage>();

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }

            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        private void Update()
        {
            // Process message queue on main thread
            while (_messageQueue.Count > 0)
            {
                var msg = _messageQueue.Dequeue();
                ProcessMessage(msg);
            }
        }

        public void SetCharacter(ImportedCharacter character)
        {
            _currentCharacter = character;
        }

        public void Connect(string host = null, int port = 0)
        {
            host = host ?? SAMConfig.Instance.samHost;
            port = port > 0 ? port : SAMConfig.Instance.samPort;

            string uri = $"ws://{host}:{port}";

            Debug.Log($"[SAM] Connecting to {uri}");

            _webSocket = new WebSocketClient();
            _webSocket.OnOpen += HandleOpen;
            _webSocket.OnMessage += HandleMessage;
            _webSocket.OnClose += HandleClose;
            _webSocket.OnError += HandleError;

            _ = _webSocket.ConnectAsync(uri);
        }

        public void Disconnect()
        {
            if (_webSocket != null)
            {
                _webSocket.Close();
                _webSocket = null;
            }

            IsConnected = false;
        }

        private void HandleOpen()
        {
            Debug.Log("[SAM] Connected to server");
            IsConnected = true;

            // Send registration
            SendMessage(new
            {
                type = "register",
                client = "unity",
                capabilities = new[] { "animation", "morph_targets", "physics" }
            });

            OnConnected?.Invoke();
        }

        private void HandleMessage(string data)
        {
            try
            {
                var msg = JsonUtility.FromJson<SAMMessage>(data);
                _messageQueue.Enqueue(msg);
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[SAM] Failed to parse message: {e.Message}");
            }
        }

        private void HandleClose()
        {
            Debug.Log("[SAM] Disconnected from server");
            IsConnected = false;
            OnDisconnected?.Invoke();
        }

        private void HandleError(string error)
        {
            Debug.LogError($"[SAM] WebSocket error: {error}");
        }

        private void ProcessMessage(SAMMessage msg)
        {
            if (_currentCharacter == null) return;

            OnMessageReceived?.Invoke(msg);

            switch (msg.type)
            {
                case "animation":
                    SetAnimationState(msg.animation, msg.intensity);
                    break;

                case "emotion":
                    SetEmotion(msg.emotion, msg.intensity);
                    break;

                case "morph":
                    if (msg.morph_targets != null)
                    {
                        SetMorphTargets(msg.morph_targets);
                    }
                    break;

                case "speak":
                    PlaySpeechAnimation(msg.text);
                    break;
            }
        }

        private void SetAnimationState(string state, float intensity)
        {
            if (_currentCharacter?.animator == null) return;

            if (Enum.TryParse<AnimationState>(state, true, out var animState))
            {
                _currentCharacter.animator.SetInteger("State", (int)animState);
                _currentCharacter.animator.SetFloat("Intensity", intensity);
            }

            Debug.Log($"[SAM] Animation: {state} @ {intensity}");
        }

        private void SetEmotion(string emotion, float intensity)
        {
            // Map emotion to blend shapes
            var emotionMorphs = new Dictionary<string, Dictionary<string, float>>
            {
                { "happy", new Dictionary<string, float> { {"smile", 0.8f}, {"brow_raise", 0.3f} } },
                { "sad", new Dictionary<string, float> { {"frown", 0.6f}, {"brow_furrow", 0.4f} } },
                { "confident", new Dictionary<string, float> { {"smirk", 0.5f}, {"chin_up", 0.3f} } },
                { "flirty", new Dictionary<string, float> { {"wink", 0.7f}, {"smile", 0.4f} } },
                { "intense", new Dictionary<string, float> { {"eye_narrow", 0.4f}, {"jaw_clench", 0.3f} } },
                { "aroused", new Dictionary<string, float> { {"arousal", intensity}, {"breathing", 0.5f} } }
            };

            if (emotionMorphs.TryGetValue(emotion.ToLower(), out var morphs))
            {
                SetMorphTargets(morphs);
            }

            Debug.Log($"[SAM] Emotion: {emotion} @ {intensity}");
        }

        private void SetMorphTargets(Dictionary<string, float> targets)
        {
            if (_currentCharacter?.skinnedMesh == null) return;

            foreach (var kvp in targets)
            {
                if (_currentCharacter.blendShapeIndices.TryGetValue(kvp.Key, out int index))
                {
                    _currentCharacter.skinnedMesh.SetBlendShapeWeight(index, kvp.Value * 100f);
                }
            }
        }

        private void PlaySpeechAnimation(string text)
        {
            if (_currentCharacter?.animator == null) return;

            _currentCharacter.animator.SetBool("IsTalking", true);

            // Would trigger lip sync here
            Debug.Log($"[SAM] Speaking: {text?.Substring(0, Math.Min(50, text?.Length ?? 0))}...");
        }

        public void SendMessage(object data)
        {
            if (_webSocket == null || !IsConnected) return;

            string json = JsonUtility.ToJson(data);
            _webSocket.Send(json);
        }

        private void OnDestroy()
        {
            Disconnect();
        }
    }

    // ============================================================================
    // WEBSOCKET CLIENT (Simple Implementation)
    // ============================================================================

    public class WebSocketClient
    {
        public event Action OnOpen;
        public event Action<string> OnMessage;
        public event Action OnClose;
        public event Action<string> OnError;

        private System.Net.WebSockets.ClientWebSocket _ws;
        private System.Threading.CancellationTokenSource _cts;
        private bool _isConnected;

        public async Task ConnectAsync(string uri)
        {
            try
            {
                _ws = new System.Net.WebSockets.ClientWebSocket();
                _cts = new System.Threading.CancellationTokenSource();

                await _ws.ConnectAsync(new Uri(uri), _cts.Token);

                _isConnected = true;
                OnOpen?.Invoke();

                // Start receiving
                _ = ReceiveLoopAsync();
            }
            catch (Exception e)
            {
                OnError?.Invoke(e.Message);
            }
        }

        private async Task ReceiveLoopAsync()
        {
            var buffer = new byte[8192];

            try
            {
                while (_isConnected && _ws.State == System.Net.WebSockets.WebSocketState.Open)
                {
                    var result = await _ws.ReceiveAsync(
                        new ArraySegment<byte>(buffer),
                        _cts.Token
                    );

                    if (result.MessageType == System.Net.WebSockets.WebSocketMessageType.Close)
                    {
                        break;
                    }

                    string message = System.Text.Encoding.UTF8.GetString(buffer, 0, result.Count);
                    OnMessage?.Invoke(message);
                }
            }
            catch (Exception e)
            {
                if (_isConnected)
                {
                    OnError?.Invoke(e.Message);
                }
            }
            finally
            {
                _isConnected = false;
                OnClose?.Invoke();
            }
        }

        public void Send(string message)
        {
            if (_ws?.State != System.Net.WebSockets.WebSocketState.Open) return;

            var bytes = System.Text.Encoding.UTF8.GetBytes(message);
            _ = _ws.SendAsync(
                new ArraySegment<byte>(bytes),
                System.Net.WebSockets.WebSocketMessageType.Text,
                true,
                _cts.Token
            );
        }

        public void Close()
        {
            _isConnected = false;
            _cts?.Cancel();

            if (_ws?.State == System.Net.WebSockets.WebSocketState.Open)
            {
                _ = _ws.CloseAsync(
                    System.Net.WebSockets.WebSocketCloseStatus.NormalClosure,
                    "Client disconnecting",
                    System.Threading.CancellationToken.None
                );
            }
        }
    }

    // ============================================================================
    // SOFT BODY CONTROLLER
    // ============================================================================

    [RequireComponent(typeof(SkinnedMeshRenderer))]
    public class SAMSoftBodyController : MonoBehaviour
    {
        [Header("Soft Body Settings")]
        [Range(0f, 1f)] public float stiffness = 0.3f;
        [Range(0f, 1f)] public float damping = 0.5f;
        [Range(0f, 2f)] public float collisionRadius = 0.5f;

        [Header("Anatomy Bones")]
        public string[] softBodyBones = new[]
        {
            "shaft_base", "shaft_mid", "shaft_tip",
            "glans", "testicle_L", "testicle_R", "scrotum"
        };

        [Header("State")]
        [Range(0f, 1f)] public float arousalLevel = 0f;

        private SkinnedMeshRenderer _skinnedMesh;
        private Dictionary<string, Transform> _boneTransforms = new Dictionary<string, Transform>();
        private Dictionary<string, Vector3> _boneRestPositions = new Dictionary<string, Vector3>();
        private Dictionary<string, Quaternion> _boneRestRotations = new Dictionary<string, Quaternion>();

        private bool _simulationEnabled;

        private void Awake()
        {
            _skinnedMesh = GetComponent<SkinnedMeshRenderer>();
            CacheBones();
        }

        private void CacheBones()
        {
            Transform root = _skinnedMesh.rootBone ?? transform;

            foreach (string boneName in softBodyBones)
            {
                Transform bone = FindBoneRecursive(root, boneName);
                if (bone != null)
                {
                    _boneTransforms[boneName] = bone;
                    _boneRestPositions[boneName] = bone.localPosition;
                    _boneRestRotations[boneName] = bone.localRotation;
                }
            }

            Debug.Log($"[SAM] Cached {_boneTransforms.Count} soft body bones");
        }

        private Transform FindBoneRecursive(Transform parent, string name)
        {
            if (parent.name == name) return parent;

            foreach (Transform child in parent)
            {
                Transform found = FindBoneRecursive(child, name);
                if (found != null) return found;
            }

            return null;
        }

        public void EnableSimulation()
        {
            _simulationEnabled = true;
            Debug.Log("[SAM] Soft body simulation enabled");
        }

        public void DisableSimulation()
        {
            _simulationEnabled = false;
            ResetToRestPose();
            Debug.Log("[SAM] Soft body simulation disabled");
        }

        private void ResetToRestPose()
        {
            foreach (var kvp in _boneTransforms)
            {
                if (_boneRestPositions.TryGetValue(kvp.Key, out var pos))
                {
                    kvp.Value.localPosition = pos;
                }
                if (_boneRestRotations.TryGetValue(kvp.Key, out var rot))
                {
                    kvp.Value.localRotation = rot;
                }
            }
        }

        private void FixedUpdate()
        {
            if (!_simulationEnabled) return;

            // Simple spring-based soft body simulation
            // In production, use Magica Cloth 2 or Obi
            SimulateSoftBody();
        }

        private void SimulateSoftBody()
        {
            // Simplified jiggle physics
            // Real implementation would use cloth/softbody physics
            foreach (var kvp in _boneTransforms)
            {
                Transform bone = kvp.Value;

                // Add subtle movement based on velocity
                Vector3 restPos = _boneRestPositions[kvp.Key];
                Vector3 offset = Vector3.zero;

                // Add gravity influence
                offset += Vector3.down * (1f - stiffness) * 0.01f;

                // Dampen
                offset *= (1f - damping);

                // Apply
                bone.localPosition = Vector3.Lerp(bone.localPosition, restPos + offset, Time.fixedDeltaTime * 10f);
            }
        }

        public void SetArousalState(float level)
        {
            arousalLevel = Mathf.Clamp01(level);

            // Apply blend shapes for arousal
            if (_skinnedMesh?.sharedMesh != null)
            {
                Mesh mesh = _skinnedMesh.sharedMesh;

                // Find arousal-related blend shapes
                for (int i = 0; i < mesh.blendShapeCount; i++)
                {
                    string shapeName = mesh.GetBlendShapeName(i).ToLower();

                    if (shapeName.Contains("arousal") || shapeName.Contains("erect"))
                    {
                        _skinnedMesh.SetBlendShapeWeight(i, level * 100f);
                    }
                }
            }

            Debug.Log($"[SAM] Arousal state: {level:F2}");
        }

        public void ApplyForce(Vector3 direction, float magnitude)
        {
            if (!_simulationEnabled) return;

            // Apply force to all soft body bones
            foreach (var kvp in _boneTransforms)
            {
                Vector3 force = direction.normalized * magnitude * (1f - stiffness);
                kvp.Value.localPosition += force * Time.fixedDeltaTime;
            }
        }
    }

    // ============================================================================
    // ATLAS ANIMATOR COMPONENT
    // ============================================================================

    [RequireComponent(typeof(Animator))]
    public class SAMAnimator : MonoBehaviour
    {
        [Header("Character")]
        public ImportedCharacter character;

        [Header("Animation")]
        public AnimationState currentState = AnimationState.Idle;
        public EmotionalState currentEmotion = EmotionalState.Neutral;

        [Header("Blend Speeds")]
        public float stateBlendSpeed = 5f;
        public float emotionBlendSpeed = 3f;

        private Animator _animator;
        private SkinnedMeshRenderer _skinnedMesh;
        private Dictionary<string, int> _blendShapeIndices = new Dictionary<string, int>();
        private Dictionary<string, float> _targetBlendWeights = new Dictionary<string, float>();
        private Dictionary<string, float> _currentBlendWeights = new Dictionary<string, float>();

        private void Awake()
        {
            _animator = GetComponent<Animator>();
            _skinnedMesh = GetComponentInChildren<SkinnedMeshRenderer>();

            CacheBlendShapes();
        }

        private void CacheBlendShapes()
        {
            if (_skinnedMesh?.sharedMesh == null) return;

            Mesh mesh = _skinnedMesh.sharedMesh;
            for (int i = 0; i < mesh.blendShapeCount; i++)
            {
                string name = mesh.GetBlendShapeName(i);
                _blendShapeIndices[name] = i;
                _currentBlendWeights[name] = 0f;
                _targetBlendWeights[name] = 0f;
            }
        }

        private void Update()
        {
            // Smooth blend shape transitions
            foreach (var kvp in _targetBlendWeights)
            {
                string name = kvp.Key;
                float target = kvp.Value;

                if (_currentBlendWeights.TryGetValue(name, out float current))
                {
                    float newValue = Mathf.Lerp(current, target, Time.deltaTime * emotionBlendSpeed);
                    _currentBlendWeights[name] = newValue;

                    if (_blendShapeIndices.TryGetValue(name, out int index))
                    {
                        _skinnedMesh.SetBlendShapeWeight(index, newValue * 100f);
                    }
                }
            }
        }

        public void SetState(AnimationState state, float intensity = 1f)
        {
            currentState = state;
            _animator.SetInteger("State", (int)state);
            _animator.SetFloat("Intensity", intensity);
        }

        public void SetEmotion(EmotionalState emotion, float intensity = 1f)
        {
            currentEmotion = emotion;

            // Reset all emotion blend shapes
            foreach (var key in new List<string>(_targetBlendWeights.Keys))
            {
                _targetBlendWeights[key] = 0f;
            }

            // Set target blend shapes for emotion
            var emotionMorphs = GetEmotionMorphs(emotion);
            foreach (var kvp in emotionMorphs)
            {
                if (_targetBlendWeights.ContainsKey(kvp.Key))
                {
                    _targetBlendWeights[kvp.Key] = kvp.Value * intensity;
                }
            }
        }

        public void SetMorphTarget(string name, float value)
        {
            if (_targetBlendWeights.ContainsKey(name))
            {
                _targetBlendWeights[name] = value;
            }
        }

        private Dictionary<string, float> GetEmotionMorphs(EmotionalState emotion)
        {
            return emotion switch
            {
                EmotionalState.Happy => new Dictionary<string, float>
                {
                    {"smile", 0.8f}, {"brow_raise", 0.3f}, {"eye_squint", 0.2f}
                },
                EmotionalState.Sad => new Dictionary<string, float>
                {
                    {"frown", 0.6f}, {"brow_furrow", 0.4f}, {"mouth_down", 0.3f}
                },
                EmotionalState.Confident => new Dictionary<string, float>
                {
                    {"smirk", 0.5f}, {"chin_up", 0.3f}, {"brow_raise_single", 0.2f}
                },
                EmotionalState.Flirty => new Dictionary<string, float>
                {
                    {"wink", 0.7f}, {"smile", 0.4f}, {"brow_raise", 0.2f}
                },
                EmotionalState.Intense => new Dictionary<string, float>
                {
                    {"eye_narrow", 0.4f}, {"jaw_clench", 0.3f}, {"nostril_flare", 0.2f}
                },
                EmotionalState.Playful => new Dictionary<string, float>
                {
                    {"smile", 0.6f}, {"tongue_out", 0.3f}, {"brow_raise", 0.4f}
                },
                EmotionalState.Thoughtful => new Dictionary<string, float>
                {
                    {"brow_furrow", 0.3f}, {"eye_look_up", 0.4f}, {"lip_purse", 0.2f}
                },
                EmotionalState.Concerned => new Dictionary<string, float>
                {
                    {"brow_raise_inner", 0.5f}, {"frown", 0.3f}, {"mouth_open", 0.1f}
                },
                _ => new Dictionary<string, float>()
            };
        }
    }

    // ============================================================================
    // EDITOR MENU ITEMS
    // ============================================================================

#if UNITY_EDITOR
    public static class SAMMenuItems
    {
        [MenuItem("SAM/Connect to Server")]
        public static void ConnectToServer()
        {
            // Ensure connection manager exists
            var connection = GameObject.FindObjectOfType<SAMConnection>();
            if (connection == null)
            {
                var go = new GameObject("SAMConnection");
                connection = go.AddComponent<SAMConnection>();
            }

            connection.Connect();
        }

        [MenuItem("SAM/Disconnect from Server")]
        public static void DisconnectFromServer()
        {
            var connection = GameObject.FindObjectOfType<SAMConnection>();
            if (connection != null)
            {
                connection.Disconnect();
            }
        }

        [MenuItem("SAM/Create Config")]
        public static void CreateConfig()
        {
            var config = ScriptableObject.CreateInstance<SAMConfig>();

            string path = "Assets/Resources";
            if (!AssetDatabase.IsValidFolder(path))
            {
                AssetDatabase.CreateFolder("Assets", "Resources");
            }

            AssetDatabase.CreateAsset(config, $"{path}/SAMConfig.asset");
            AssetDatabase.SaveAssets();

            Selection.activeObject = config;
            Debug.Log("[SAM] Created configuration asset at Assets/Resources/SAMConfig.asset");
        }

        [MenuItem("SAM/Setup Selected Character")]
        public static void SetupSelectedCharacter()
        {
            GameObject selected = Selection.activeGameObject;
            if (selected == null)
            {
                Debug.LogWarning("[SAM] No GameObject selected");
                return;
            }

            // Add required components
            if (selected.GetComponent<Animator>() == null)
            {
                selected.AddComponent<Animator>();
            }

            if (selected.GetComponent<SAMAnimator>() == null)
            {
                selected.AddComponent<SAMAnimator>();
            }

            var skinned = selected.GetComponentInChildren<SkinnedMeshRenderer>();
            if (skinned != null && skinned.GetComponent<SAMSoftBodyController>() == null)
            {
                skinned.gameObject.AddComponent<SAMSoftBodyController>();
            }

            Debug.Log($"[SAM] Setup complete for {selected.name}");
        }
    }
#endif
}
