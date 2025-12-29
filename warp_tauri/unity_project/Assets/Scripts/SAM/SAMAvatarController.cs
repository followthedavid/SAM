using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace SAM.Avatar
{
    /// <summary>
    /// Main controller for the SAM avatar.
    /// Handles blend shapes, animations, physics, and connection to Warp Open.
    /// </summary>
    [RequireComponent(typeof(Animator))]
    public class SAMAvatarController : MonoBehaviour
    {
        public static SAMAvatarController Instance { get; private set; }

        [Header("Components")]
        [SerializeField] private SkinnedMeshRenderer bodyMesh;
        [SerializeField] private SkinnedMeshRenderer faceMesh;
        [SerializeField] private SkinnedMeshRenderer anatomyMesh;
        [SerializeField] private Animator animator;

        [Header("Connection")]
        [SerializeField] private string atlasHost = "localhost";
        [SerializeField] private int atlasPort = 8765;
        [SerializeField] private bool autoConnect = true;

        [Header("Settings")]
        [SerializeField] private float blendShapeTransitionSpeed = 5f;
        [SerializeField] private bool enablePhysics = true;
        [SerializeField] private bool enableBreathing = true;
        [SerializeField] private bool enableBlinking = true;

        // Connection
        private SAMConnection _connection;
        public bool IsConnected => _connection?.IsConnected ?? false;

        // Blend shape management
        private BlendShapeController _blendShapeController;
        private Dictionary<string, float> _targetBlendShapes = new Dictionary<string, float>();
        private Dictionary<string, float> _currentBlendShapes = new Dictionary<string, float>();

        // Animation state
        private AnimationState _currentAnimState = AnimationState.Idle;
        private EmotionalState _currentEmotion = EmotionalState.Neutral;
        private float _animationIntensity = 1f;

        // Idle behaviors
        private float _nextBlinkTime;
        private float _breathPhase;
        private Coroutine _lipSyncCoroutine;

        // Events
        public event Action OnConnected;
        public event Action OnDisconnected;
        public event Action<SAMMessage> OnMessageReceived;

        #region Lifecycle

        private void Awake()
        {
            if (Instance != null && Instance != this)
            {
                Destroy(gameObject);
                return;
            }
            Instance = this;

            if (animator == null) animator = GetComponent<Animator>();

            _blendShapeController = new BlendShapeController(bodyMesh, faceMesh, anatomyMesh);
            _connection = gameObject.AddComponent<SAMConnection>();
            _connection.OnMessageReceived += HandleMessage;
            _connection.OnConnected += () => OnConnected?.Invoke();
            _connection.OnDisconnected += () => OnDisconnected?.Invoke();
        }

        private void Start()
        {
            // Initialize blend shapes
            _blendShapeController.Initialize();
            InitializeBlendShapeTargets();

            // Schedule first blink
            _nextBlinkTime = Time.time + UnityEngine.Random.Range(2f, 6f);

            // Auto connect
            if (autoConnect)
            {
                Connect();
            }
        }

        private void Update()
        {
            // Smooth blend shape transitions
            UpdateBlendShapes();

            // Idle behaviors
            if (enableBlinking) UpdateBlinking();
            if (enableBreathing) UpdateBreathing();
        }

        private void OnDestroy()
        {
            if (_connection != null)
            {
                _connection.OnMessageReceived -= HandleMessage;
            }
        }

        #endregion

        #region Connection

        public void Connect()
        {
            _connection.Connect(atlasHost, atlasPort);
        }

        public void Connect(string host, int port)
        {
            atlasHost = host;
            atlasPort = port;
            _connection.Connect(host, port);
        }

        public void Disconnect()
        {
            _connection.Disconnect();
        }

        private void HandleMessage(SAMMessage message)
        {
            OnMessageReceived?.Invoke(message);

            switch (message.type)
            {
                case "animation":
                    HandleAnimationMessage(message);
                    break;
                case "emotion":
                    HandleEmotionMessage(message);
                    break;
                case "morph":
                    HandleMorphMessage(message);
                    break;
                case "lipsync":
                    HandleLipSyncMessage(message);
                    break;
                case "gesture":
                    HandleGestureMessage(message);
                    break;
                case "look":
                    HandleLookMessage(message);
                    break;
                case "custom":
                    HandleCustomMessage(message);
                    break;
            }
        }

        #endregion

        #region Message Handlers

        private void HandleAnimationMessage(SAMMessage msg)
        {
            if (Enum.TryParse<AnimationState>(msg.animation, true, out var state))
            {
                SetAnimationState(state, msg.intensity);
            }
        }

        private void HandleEmotionMessage(SAMMessage msg)
        {
            if (Enum.TryParse<EmotionalState>(msg.emotion, true, out var emotion))
            {
                SetEmotion(emotion, msg.intensity);
            }

            // Apply expression overrides if provided
            if (msg.expression != null)
            {
                if (msg.expression.TryGetValue("browRaise", out var brow))
                    SetBlendShape("face_browRaise", brow);
                if (msg.expression.TryGetValue("smirkIntensity", out var smirk))
                    SetBlendShape("face_smirk", smirk);
                if (msg.expression.TryGetValue("eyeIntensity", out var eye))
                    SetBlendShape("face_eyeIntensity", eye);
            }
        }

        private void HandleMorphMessage(SAMMessage msg)
        {
            if (msg.morph_targets == null) return;

            foreach (var kvp in msg.morph_targets)
            {
                SetBlendShape(kvp.Key, kvp.Value);
            }
        }

        private void HandleLipSyncMessage(SAMMessage msg)
        {
            if (msg.lipSyncData != null && msg.lipSyncData.Count > 0)
            {
                if (_lipSyncCoroutine != null)
                    StopCoroutine(_lipSyncCoroutine);
                _lipSyncCoroutine = StartCoroutine(PlayLipSync(msg.lipSyncData, msg.totalDuration));
            }
            else if (msg.stop)
            {
                StopLipSync();
            }
        }

        private void HandleGestureMessage(SAMMessage msg)
        {
            // Trigger gesture animation
            if (!string.IsNullOrEmpty(msg.gesture))
            {
                animator.SetTrigger($"Gesture_{msg.gesture}");
            }
        }

        private void HandleLookMessage(SAMMessage msg)
        {
            if (msg.target != null)
            {
                Vector3 lookTarget = new Vector3(
                    msg.target.TryGetValue("x", out var x) ? x : 0,
                    msg.target.TryGetValue("y", out var y) ? y : 1.6f,
                    msg.target.TryGetValue("z", out var z) ? z : 1
                );
                // Would implement IK look-at here
                Debug.Log($"[SAM] Look at: {lookTarget}");
            }
        }

        private void HandleCustomMessage(SAMMessage msg)
        {
            switch (msg.action)
            {
                case "blink":
                    TriggerBlink();
                    break;
                case "breathing":
                    if (msg.customData.TryGetValue("intensity", out var intensity))
                    {
                        SetBlendShape("body_breathing", intensity);
                    }
                    break;
            }
        }

        #endregion

        #region Animation

        public void SetAnimationState(AnimationState state, float intensity = 1f)
        {
            _currentAnimState = state;
            _animationIntensity = intensity;

            animator.SetInteger("AnimState", (int)state);
            animator.SetFloat("Intensity", intensity);

            Debug.Log($"[SAM] Animation: {state} @ {intensity:F2}");
        }

        public void SetEmotion(EmotionalState emotion, float intensity = 1f)
        {
            _currentEmotion = emotion;

            // Map emotion to blend shapes
            var emotionBlendShapes = GetEmotionBlendShapes(emotion);
            foreach (var kvp in emotionBlendShapes)
            {
                SetBlendShape(kvp.Key, kvp.Value * intensity);
            }

            Debug.Log($"[SAM] Emotion: {emotion} @ {intensity:F2}");
        }

        private Dictionary<string, float> GetEmotionBlendShapes(EmotionalState emotion)
        {
            return emotion switch
            {
                EmotionalState.Happy => new Dictionary<string, float>
                {
                    { "face_smile", 0.8f },
                    { "face_browRaise", 0.3f },
                    { "face_eyeSquint", 0.2f }
                },
                EmotionalState.Flirty => new Dictionary<string, float>
                {
                    { "face_smirk", 0.7f },
                    { "face_browRaise", 0.4f },
                    { "face_eyeLidLower", 0.3f }
                },
                EmotionalState.Confident => new Dictionary<string, float>
                {
                    { "face_smirk", 0.5f },
                    { "face_chinUp", 0.3f },
                    { "face_eyeIntensity", 0.6f }
                },
                EmotionalState.Intense => new Dictionary<string, float>
                {
                    { "face_eyeNarrow", 0.4f },
                    { "face_jawClench", 0.3f },
                    { "face_browFurrow", 0.2f }
                },
                EmotionalState.Concerned => new Dictionary<string, float>
                {
                    { "face_browRaiseInner", 0.5f },
                    { "face_frown", 0.3f }
                },
                EmotionalState.Playful => new Dictionary<string, float>
                {
                    { "face_smile", 0.6f },
                    { "face_browRaise", 0.4f },
                    { "face_tongueOut", 0.1f }
                },
                _ => new Dictionary<string, float>()
            };
        }

        #endregion

        #region Blend Shapes

        private void InitializeBlendShapeTargets()
        {
            // Initialize all blend shape targets to 0
            var allShapes = _blendShapeController.GetAllBlendShapeNames();
            foreach (var name in allShapes)
            {
                _targetBlendShapes[name] = 0f;
                _currentBlendShapes[name] = 0f;
            }
        }

        public void SetBlendShape(string name, float value)
        {
            _targetBlendShapes[name] = Mathf.Clamp01(value);
        }

        public void SetBlendShapeImmediate(string name, float value)
        {
            _targetBlendShapes[name] = Mathf.Clamp01(value);
            _currentBlendShapes[name] = Mathf.Clamp01(value);
            _blendShapeController.SetBlendShape(name, value);
        }

        private void UpdateBlendShapes()
        {
            foreach (var kvp in _targetBlendShapes)
            {
                string name = kvp.Key;
                float target = kvp.Value;

                if (!_currentBlendShapes.TryGetValue(name, out float current))
                {
                    current = 0f;
                    _currentBlendShapes[name] = current;
                }

                if (Mathf.Abs(target - current) > 0.001f)
                {
                    float newValue = Mathf.Lerp(current, target, Time.deltaTime * blendShapeTransitionSpeed);
                    _currentBlendShapes[name] = newValue;
                    _blendShapeController.SetBlendShape(name, newValue);
                }
            }
        }

        /// <summary>
        /// Apply full character customization from Warp Open
        /// </summary>
        public void ApplyCharacterConfig(Dictionary<string, float> bodyParams, Dictionary<string, float> faceParams)
        {
            foreach (var kvp in bodyParams)
            {
                SetBlendShape($"body_{kvp.Key}", kvp.Value);
            }

            foreach (var kvp in faceParams)
            {
                SetBlendShape($"face_{kvp.Key}", kvp.Value);
            }
        }

        #endregion

        #region Lip Sync

        private IEnumerator PlayLipSync(List<LipSyncFrame> frames, float totalDuration)
        {
            SetAnimationState(AnimationState.Talking);

            float startTime = Time.time;

            foreach (var frame in frames)
            {
                // Wait until frame timestamp
                float targetTime = startTime + (frame.timestamp / 1000f);
                while (Time.time < targetTime)
                {
                    yield return null;
                }

                // Set viseme blend shape
                string visemeShape = $"face_viseme_{frame.viseme}";
                SetBlendShapeImmediate(visemeShape, frame.intensity);

                // Hold for duration
                yield return new WaitForSeconds(frame.duration / 1000f);

                // Reset viseme
                SetBlendShapeImmediate(visemeShape, 0f);
            }

            SetAnimationState(AnimationState.Idle);
            _lipSyncCoroutine = null;
        }

        private void StopLipSync()
        {
            if (_lipSyncCoroutine != null)
            {
                StopCoroutine(_lipSyncCoroutine);
                _lipSyncCoroutine = null;
            }

            // Reset all viseme shapes
            foreach (var name in _blendShapeController.GetAllBlendShapeNames())
            {
                if (name.Contains("viseme"))
                {
                    SetBlendShapeImmediate(name, 0f);
                }
            }

            SetAnimationState(AnimationState.Idle);
        }

        #endregion

        #region Idle Behaviors

        private void UpdateBlinking()
        {
            if (Time.time >= _nextBlinkTime)
            {
                TriggerBlink();
                _nextBlinkTime = Time.time + UnityEngine.Random.Range(2f, 6f);
            }
        }

        private void TriggerBlink()
        {
            StartCoroutine(BlinkCoroutine());
        }

        private IEnumerator BlinkCoroutine()
        {
            // Close eyes
            float duration = 0.15f;
            float elapsed = 0f;

            while (elapsed < duration / 2)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / (duration / 2);
                SetBlendShapeImmediate("face_eyesClosed", t);
                yield return null;
            }

            // Open eyes
            elapsed = 0f;
            while (elapsed < duration / 2)
            {
                elapsed += Time.deltaTime;
                float t = 1f - (elapsed / (duration / 2));
                SetBlendShapeImmediate("face_eyesClosed", t);
                yield return null;
            }

            SetBlendShapeImmediate("face_eyesClosed", 0f);
        }

        private void UpdateBreathing()
        {
            _breathPhase += Time.deltaTime * 0.5f; // Slow breathing
            float breathValue = (Mathf.Sin(_breathPhase) + 1f) / 2f * 0.1f;
            SetBlendShape("body_breathing", breathValue);
        }

        #endregion

        #region Public API

        /// <summary>
        /// Set arousal state (0-1)
        /// </summary>
        public void SetArousalState(float level)
        {
            level = Mathf.Clamp01(level);

            SetBlendShape("anatomy_arousal", level);
            SetBlendShape("anatomy_erect", Mathf.Min(1f, level * 1.5f));
            SetBlendShape("body_breathing", 0.3f + level * 0.4f);

            Debug.Log($"[SAM] Arousal: {level:F2}");
        }

        /// <summary>
        /// Play a specific animation by name
        /// </summary>
        public void PlayAnimation(string animationName, float crossfade = 0.2f)
        {
            animator.CrossFade(animationName, crossfade);
        }

        /// <summary>
        /// Send a message back to Warp Open
        /// </summary>
        public void SendEvent(string eventType, Dictionary<string, object> data)
        {
            _connection.SendEvent(eventType, data);
        }

        #endregion
    }

    #region Enums

    public enum AnimationState
    {
        Idle = 0,
        Talking = 1,
        Thinking = 2,
        Listening = 3,
        Pleased = 4,
        Smirking = 5,
        Flirting = 6,
        Concerned = 7,
        Laughing = 8,
        EyebrowRaise = 9,
        HeadTilt = 10,
        Nod = 11,
        ShakeHead = 12,
        Wink = 13,
        Custom = 99
    }

    public enum EmotionalState
    {
        Neutral,
        Happy,
        Amused,
        Interested,
        Flirty,
        Confident,
        Thoughtful,
        Concerned,
        Playful,
        Intense
    }

    #endregion

    #region Data Classes

    [Serializable]
    public class LipSyncFrame
    {
        public float timestamp;
        public string viseme;
        public float intensity;
        public float duration;
    }

    #endregion
}
