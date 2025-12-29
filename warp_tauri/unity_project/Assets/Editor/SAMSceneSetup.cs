using UnityEngine;
using UnityEditor;
using UnityEditor.SceneManagement;

namespace SAM.Avatar.Editor
{
    /// <summary>
    /// Editor tool to quickly set up an SAM Avatar scene with proper lighting,
    /// camera, and all required components.
    /// </summary>
    public class SAMSceneSetup : EditorWindow
    {
        [MenuItem("SAM/Create Avatar Scene")]
        public static void CreateAvatarScene()
        {
            // Create new scene
            var scene = EditorSceneManager.NewScene(NewSceneSetup.DefaultGameObjects, NewSceneMode.Single);

            // Setup camera
            SetupCamera();

            // Setup lighting
            SetupLighting();

            // Create avatar root
            CreateAvatarRoot();

            // Create UI canvas
            CreateDebugUI();

            // Save scene
            string scenePath = "Assets/Scenes/SAMAvatar.unity";
            System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(Application.dataPath + "/" + scenePath.Substring(7)));
            EditorSceneManager.SaveScene(scene, scenePath);

            Debug.Log("[SAM] Scene created at: " + scenePath);
            EditorUtility.DisplayDialog("SAM Scene Setup",
                "Avatar scene created!\n\nNext steps:\n" +
                "1. Import your FBX model to Assets/Characters/\n" +
                "2. Drag model under 'SAM Avatar' object\n" +
                "3. Assign mesh references in SAMAvatarController",
                "OK");
        }

        private static void SetupCamera()
        {
            var mainCamera = Camera.main;
            if (mainCamera == null)
            {
                var cameraObj = new GameObject("Main Camera");
                mainCamera = cameraObj.AddComponent<Camera>();
                cameraObj.AddComponent<AudioListener>();
                cameraObj.tag = "MainCamera";
            }

            // Position camera for avatar viewing
            mainCamera.transform.position = new Vector3(0, 1.5f, 2.5f);
            mainCamera.transform.rotation = Quaternion.Euler(5, 180, 0);
            mainCamera.fieldOfView = 45f;
            mainCamera.nearClipPlane = 0.1f;
            mainCamera.farClipPlane = 100f;

            // Add orbit camera script placeholder
            var cameraController = mainCamera.gameObject.AddComponent<SAMCameraController>();
            Debug.Log("[SAM] Camera configured");
        }

        private static void SetupLighting()
        {
            // Find or create directional light
            var existingLight = Object.FindObjectOfType<Light>();
            if (existingLight != null && existingLight.type == LightType.Directional)
            {
                existingLight.gameObject.name = "Key Light";
                ConfigureKeyLight(existingLight);
            }
            else
            {
                var keyLightObj = new GameObject("Key Light");
                var keyLight = keyLightObj.AddComponent<Light>();
                ConfigureKeyLight(keyLight);
            }

            // Fill light
            var fillLightObj = new GameObject("Fill Light");
            var fillLight = fillLightObj.AddComponent<Light>();
            fillLight.type = LightType.Directional;
            fillLight.intensity = 0.4f;
            fillLight.color = new Color(0.9f, 0.95f, 1f);
            fillLight.shadows = LightShadows.None;
            fillLightObj.transform.rotation = Quaternion.Euler(30, -120, 0);

            // Rim light
            var rimLightObj = new GameObject("Rim Light");
            var rimLight = rimLightObj.AddComponent<Light>();
            rimLight.type = LightType.Directional;
            rimLight.intensity = 0.3f;
            rimLight.color = new Color(1f, 0.95f, 0.9f);
            rimLight.shadows = LightShadows.None;
            rimLightObj.transform.rotation = Quaternion.Euler(10, 180, 0);

            // Organize
            var lightingRoot = new GameObject("Lighting");
            existingLight?.transform.SetParent(lightingRoot.transform);
            fillLightObj.transform.SetParent(lightingRoot.transform);
            rimLightObj.transform.SetParent(lightingRoot.transform);

            // Ambient
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.5f, 0.6f, 0.7f);
            RenderSettings.ambientEquatorColor = new Color(0.4f, 0.4f, 0.4f);
            RenderSettings.ambientGroundColor = new Color(0.2f, 0.2f, 0.25f);

            Debug.Log("[SAM] Three-point lighting configured");
        }

        private static void ConfigureKeyLight(Light light)
        {
            light.type = LightType.Directional;
            light.intensity = 1.2f;
            light.color = new Color(1f, 0.98f, 0.95f);
            light.shadows = LightShadows.Soft;
            light.shadowStrength = 0.6f;
            light.transform.rotation = Quaternion.Euler(45, 45, 0);
        }

        private static void CreateAvatarRoot()
        {
            // Create root object
            var avatarRoot = new GameObject("SAM Avatar");
            avatarRoot.transform.position = Vector3.zero;

            // Add controller component
            var controller = avatarRoot.AddComponent<SAMAvatarController>();

            // Create placeholder for model
            var modelPlaceholder = new GameObject("Model (Drag FBX Here)");
            modelPlaceholder.transform.SetParent(avatarRoot.transform);
            modelPlaceholder.transform.localPosition = Vector3.zero;

            // Add placeholder visual
            var placeholder = GameObject.CreatePrimitive(PrimitiveType.Capsule);
            placeholder.name = "Placeholder Visual";
            placeholder.transform.SetParent(modelPlaceholder.transform);
            placeholder.transform.localPosition = new Vector3(0, 1, 0);
            placeholder.transform.localScale = new Vector3(0.5f, 1f, 0.5f);

            // Make placeholder semi-transparent
            var renderer = placeholder.GetComponent<Renderer>();
            var mat = new Material(Shader.Find("Standard"));
            mat.color = new Color(0.5f, 0.7f, 1f, 0.5f);
            mat.SetFloat("_Mode", 3); // Transparent
            mat.SetInt("_SrcBlend", (int)UnityEngine.Rendering.BlendMode.SrcAlpha);
            mat.SetInt("_DstBlend", (int)UnityEngine.Rendering.BlendMode.OneMinusSrcAlpha);
            mat.EnableKeyword("_ALPHABLEND_ON");
            mat.renderQueue = 3000;
            renderer.material = mat;

            // Remove collider
            Object.DestroyImmediate(placeholder.GetComponent<Collider>());

            // Create ground plane
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = "Ground";
            ground.transform.position = Vector3.zero;
            ground.transform.localScale = new Vector3(2, 1, 2);
            var groundMat = new Material(Shader.Find("Standard"));
            groundMat.color = new Color(0.15f, 0.15f, 0.18f);
            ground.GetComponent<Renderer>().material = groundMat;

            Debug.Log("[SAM] Avatar root created - drag your FBX model as child of 'Model' object");
        }

        private static void CreateDebugUI()
        {
            // Create canvas for debug UI
            var canvasObj = new GameObject("Debug UI");
            var canvas = canvasObj.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            canvasObj.AddComponent<UnityEngine.UI.CanvasScaler>();
            canvasObj.AddComponent<UnityEngine.UI.GraphicRaycaster>();

            // Add event system if needed
            if (Object.FindObjectOfType<UnityEngine.EventSystems.EventSystem>() == null)
            {
                var eventSystem = new GameObject("EventSystem");
                eventSystem.AddComponent<UnityEngine.EventSystems.EventSystem>();
                eventSystem.AddComponent<UnityEngine.EventSystems.StandaloneInputModule>();
            }

            Debug.Log("[SAM] Debug UI canvas created");
        }

        [MenuItem("SAM/Quick Setup Selected Model")]
        public static void QuickSetupModel()
        {
            var selected = Selection.activeGameObject;
            if (selected == null)
            {
                EditorUtility.DisplayDialog("No Selection",
                    "Please select your imported FBX model in the scene.", "OK");
                return;
            }

            // Check for skinned mesh renderer
            var skinnedMeshes = selected.GetComponentsInChildren<SkinnedMeshRenderer>();
            if (skinnedMeshes.Length == 0)
            {
                EditorUtility.DisplayDialog("No Skinned Mesh",
                    "Selected object has no SkinnedMeshRenderer. Make sure you've imported an FBX with a rigged mesh.", "OK");
                return;
            }

            // Add SAMAvatarController if not present
            var controller = selected.GetComponent<SAMAvatarController>();
            if (controller == null)
            {
                controller = selected.AddComponent<SAMAvatarController>();
            }

            // Try to auto-assign meshes
            foreach (var mesh in skinnedMeshes)
            {
                string meshName = mesh.name.ToLower();

                if (meshName.Contains("body") || meshName.Contains("torso"))
                {
                    // Body mesh
                    var field = controller.GetType().GetField("bodyMesh",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                    if (field != null) field.SetValue(controller, mesh);
                }
                else if (meshName.Contains("face") || meshName.Contains("head"))
                {
                    // Face mesh
                    var field = controller.GetType().GetField("faceMesh",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                    if (field != null) field.SetValue(controller, mesh);
                }
                else if (meshName.Contains("genital") || meshName.Contains("anatomy") || meshName.Contains("groin"))
                {
                    // Anatomy mesh
                    var field = controller.GetType().GetField("anatomyMesh",
                        System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Instance);
                    if (field != null) field.SetValue(controller, mesh);
                }
            }

            // Add SoftBodyPhysics to anatomy
            foreach (var mesh in skinnedMeshes)
            {
                string meshName = mesh.name.ToLower();
                if (meshName.Contains("genital") || meshName.Contains("anatomy") || meshName.Contains("groin"))
                {
                    if (mesh.GetComponent<SoftBodyPhysics>() == null)
                    {
                        mesh.gameObject.AddComponent<SoftBodyPhysics>();
                    }
                }
            }

            // Add Animator if not present
            if (selected.GetComponent<Animator>() == null)
            {
                selected.AddComponent<Animator>();
            }

            // Add SAMAnimator
            if (selected.GetComponent<SAMAnimator>() == null)
            {
                var animator = selected.AddComponent<SAMAnimator>();
                animator.avatarController = controller;
            }

            EditorUtility.SetDirty(selected);

            EditorUtility.DisplayDialog("Setup Complete",
                $"SAM components added to {selected.name}!\n\n" +
                $"Found {skinnedMeshes.Length} skinned meshes.\n\n" +
                "Please verify mesh assignments in SAMAvatarController inspector.",
                "OK");
        }
    }

    /// <summary>
    /// Simple orbit camera for viewing the avatar
    /// </summary>
    public class SAMCameraController : MonoBehaviour
    {
        [Header("Target")]
        public Transform target;
        public Vector3 targetOffset = new Vector3(0, 1.2f, 0);

        [Header("Orbit")]
        public float distance = 2.5f;
        public float minDistance = 0.5f;
        public float maxDistance = 10f;

        [Header("Rotation")]
        public float rotationSpeed = 5f;
        public float minVerticalAngle = -20f;
        public float maxVerticalAngle = 80f;

        [Header("Smoothing")]
        public float smoothTime = 0.1f;

        private float _currentHorizontal;
        private float _currentVertical = 15f;
        private float _currentDistance;
        private Vector3 _velocity;

        private void Start()
        {
            _currentDistance = distance;

            if (target == null)
            {
                // Try to find avatar
                var avatar = FindObjectOfType<SAMAvatarController>();
                if (avatar != null)
                {
                    target = avatar.transform;
                }
            }
        }

        private void LateUpdate()
        {
            if (target == null) return;

            // Mouse input
            if (Input.GetMouseButton(1)) // Right click to orbit
            {
                _currentHorizontal += Input.GetAxis("Mouse X") * rotationSpeed;
                _currentVertical -= Input.GetAxis("Mouse Y") * rotationSpeed;
                _currentVertical = Mathf.Clamp(_currentVertical, minVerticalAngle, maxVerticalAngle);
            }

            // Scroll to zoom
            float scroll = Input.GetAxis("Mouse ScrollWheel");
            _currentDistance -= scroll * 2f;
            _currentDistance = Mathf.Clamp(_currentDistance, minDistance, maxDistance);

            // Calculate position
            Quaternion rotation = Quaternion.Euler(_currentVertical, _currentHorizontal, 0);
            Vector3 targetPos = target.position + targetOffset;
            Vector3 desiredPosition = targetPos - rotation * Vector3.forward * _currentDistance;

            // Smooth
            transform.position = Vector3.SmoothDamp(transform.position, desiredPosition, ref _velocity, smoothTime);
            transform.LookAt(targetPos);
        }
    }
}
