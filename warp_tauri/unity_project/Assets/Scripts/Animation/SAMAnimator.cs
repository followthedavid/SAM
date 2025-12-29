using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace SAM.Avatar
{
    /// <summary>
    /// Handles all animations for the SAM avatar including:
    /// - Idle behaviors (breathing, blinking, subtle movements)
    /// - Talking animations with lip sync
    /// - Emotional expressions
    /// - Intimate/adult animations
    /// - Gesture library
    /// </summary>
    [RequireComponent(typeof(Animator))]
    public class SAMAnimator : MonoBehaviour
    {
        [Header("References")]
        public SAMAvatarController avatarController;
        public BlendShapeController blendShapes;

        [Header("Idle Settings")]
        [Range(0f, 1f)] public float idleIntensity = 0.5f;
        [Range(1f, 5f)] public float breathingRate = 2.5f;
        [Range(0.5f, 3f)] public float blinkInterval = 2f;

        [Header("Animation Layers")]
        public int baseLayer = 0;
        public int upperBodyLayer = 1;
        public int faceLayer = 2;
        public int anatomyLayer = 3;

        // Animator
        private Animator _animator;
        private Dictionary<string, int> _animationHashes = new Dictionary<string, int>();

        // State
        private AnimationState _currentState = AnimationState.Idle;
        private float _breathingPhase;
        private float _blinkTimer;
        private float _nextBlinkTime;
        private bool _isBlinking;

        // Coroutines
        private Coroutine _currentAnimation;
        private Coroutine _emotionCoroutine;

        public enum AnimationState
        {
            Idle,
            Talking,
            Listening,
            Thinking,
            Emotional,
            Intimate,
            Custom
        }

        private void Awake()
        {
            _animator = GetComponent<Animator>();
            CacheAnimationHashes();
        }

        private void Start()
        {
            _nextBlinkTime = Random.Range(blinkInterval * 0.5f, blinkInterval * 1.5f);
            StartCoroutine(IdleLoop());
        }

        private void CacheAnimationHashes()
        {
            // Cache animation parameter hashes for performance
            string[] animParams = {
                "IsIdle", "IsTalking", "IsListening", "IsThinking",
                "TalkIntensity", "EmotionIntensity", "ArousalLevel",
                "GestureIndex", "Speed", "BlendWeight"
            };

            foreach (var param in animParams)
            {
                _animationHashes[param] = Animator.StringToHash(param);
            }
        }

        private IEnumerator IdleLoop()
        {
            while (true)
            {
                if (_currentState == AnimationState.Idle || _currentState == AnimationState.Listening)
                {
                    UpdateBreathing();
                    UpdateBlinking();
                    UpdateSubtleMovements();
                }

                yield return null;
            }
        }

        private void UpdateBreathing()
        {
            _breathingPhase += Time.deltaTime * breathingRate;
            float breathValue = (Mathf.Sin(_breathingPhase) + 1f) * 0.5f * idleIntensity;

            if (blendShapes != null)
            {
                blendShapes.SetBlendShape("body_breathing", breathValue);
            }
        }

        private void UpdateBlinking()
        {
            _blinkTimer += Time.deltaTime;

            if (!_isBlinking && _blinkTimer >= _nextBlinkTime)
            {
                StartCoroutine(DoBlink());
            }
        }

        private IEnumerator DoBlink()
        {
            _isBlinking = true;

            // Close eyes
            float closeTime = 0.08f;
            float holdTime = 0.05f;
            float openTime = 0.12f;

            float elapsed = 0f;
            while (elapsed < closeTime)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / closeTime;
                blendShapes?.SetBlendShape("face_eyesClosed", t);
                yield return null;
            }

            yield return new WaitForSeconds(holdTime);

            elapsed = 0f;
            while (elapsed < openTime)
            {
                elapsed += Time.deltaTime;
                float t = 1f - (elapsed / openTime);
                blendShapes?.SetBlendShape("face_eyesClosed", t);
                yield return null;
            }

            blendShapes?.SetBlendShape("face_eyesClosed", 0f);

            _isBlinking = false;
            _blinkTimer = 0f;
            _nextBlinkTime = Random.Range(blinkInterval * 0.5f, blinkInterval * 1.5f);
        }

        private void UpdateSubtleMovements()
        {
            // Subtle head and body micro-movements for lifelike appearance
            float time = Time.time;

            // Very subtle head movement
            float headTilt = Mathf.Sin(time * 0.3f) * 0.02f * idleIntensity;
            float headTurn = Mathf.Sin(time * 0.2f + 1f) * 0.015f * idleIntensity;

            blendShapes?.SetBlendShape("body_headTilt", 0.5f + headTilt);

            // Weight shift
            float weightShift = Mathf.Sin(time * 0.15f) * 0.1f * idleIntensity;
            blendShapes?.SetBlendShape("body_hipTilt", 0.5f + weightShift);
        }

        #region Public Animation Methods

        /// <summary>
        /// Play a named animation
        /// </summary>
        public void PlayAnimation(string animationName, float crossfade = 0.2f)
        {
            if (_currentAnimation != null)
            {
                StopCoroutine(_currentAnimation);
            }

            int hash = Animator.StringToHash(animationName);
            _animator.CrossFade(hash, crossfade);

            Debug.Log($"[SAMAnimator] Playing: {animationName}");
        }

        /// <summary>
        /// Set animation state
        /// </summary>
        public void SetState(AnimationState state)
        {
            _currentState = state;

            // Update animator parameters
            SetBool("IsIdle", state == AnimationState.Idle);
            SetBool("IsTalking", state == AnimationState.Talking);
            SetBool("IsListening", state == AnimationState.Listening);
            SetBool("IsThinking", state == AnimationState.Thinking);

            Debug.Log($"[SAMAnimator] State: {state}");
        }

        /// <summary>
        /// Start talking animation with intensity
        /// </summary>
        public void StartTalking(float intensity = 0.7f)
        {
            SetState(AnimationState.Talking);
            SetFloat("TalkIntensity", intensity);
        }

        /// <summary>
        /// Stop talking and return to idle
        /// </summary>
        public void StopTalking()
        {
            SetState(AnimationState.Idle);
            SetFloat("TalkIntensity", 0f);
        }

        /// <summary>
        /// Play emotional expression
        /// </summary>
        public void PlayEmotion(string emotion, float intensity = 1f, float duration = 2f)
        {
            if (_emotionCoroutine != null)
            {
                StopCoroutine(_emotionCoroutine);
            }

            _emotionCoroutine = StartCoroutine(DoEmotion(emotion, intensity, duration));
        }

        private IEnumerator DoEmotion(string emotion, float intensity, float duration)
        {
            var previousState = _currentState;
            _currentState = AnimationState.Emotional;

            // Apply emotion blend shapes
            var emotionShapes = GetEmotionBlendShapes(emotion);

            // Fade in
            float fadeTime = 0.3f;
            float elapsed = 0f;

            while (elapsed < fadeTime)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / fadeTime;

                foreach (var kvp in emotionShapes)
                {
                    blendShapes?.SetBlendShape(kvp.Key, kvp.Value * t * intensity);
                }

                yield return null;
            }

            // Hold
            yield return new WaitForSeconds(duration - fadeTime * 2);

            // Fade out
            elapsed = 0f;
            while (elapsed < fadeTime)
            {
                elapsed += Time.deltaTime;
                float t = 1f - (elapsed / fadeTime);

                foreach (var kvp in emotionShapes)
                {
                    blendShapes?.SetBlendShape(kvp.Key, kvp.Value * t * intensity);
                }

                yield return null;
            }

            // Reset
            foreach (var kvp in emotionShapes)
            {
                blendShapes?.SetBlendShape(kvp.Key, 0f);
            }

            _currentState = previousState;
        }

        private Dictionary<string, float> GetEmotionBlendShapes(string emotion)
        {
            var shapes = new Dictionary<string, float>();

            switch (emotion.ToLower())
            {
                case "happy":
                case "joy":
                    shapes["face_smile"] = 0.8f;
                    shapes["face_cheekFullness"] = 0.3f;
                    shapes["face_eyeSquint"] = 0.2f;
                    break;

                case "flirty":
                case "seductive":
                    shapes["face_smirk"] = 0.6f;
                    shapes["face_eyeNarrow"] = 0.3f;
                    shapes["face_eyebrowArch"] = 0.4f;
                    shapes["face_eyeIntensity"] = 0.5f;
                    break;

                case "thinking":
                case "curious":
                    shapes["face_browRaise"] = 0.3f;
                    shapes["face_eyeSquint"] = 0.15f;
                    shapes["body_headTilt"] = 0.3f;
                    break;

                case "surprised":
                    shapes["face_browRaise"] = 0.7f;
                    shapes["face_eyeSize"] = 0.3f;
                    shapes["face_mouthOpen"] = 0.4f;
                    break;

                case "sad":
                    shapes["face_frown"] = 0.5f;
                    shapes["face_browFurrow"] = 0.4f;
                    shapes["face_eyeLidLower"] = 0.3f;
                    break;

                case "angry":
                    shapes["face_browFurrow"] = 0.7f;
                    shapes["face_jawClench"] = 0.5f;
                    shapes["face_eyeNarrow"] = 0.4f;
                    break;

                case "confident":
                    shapes["face_smirk"] = 0.3f;
                    shapes["face_chinUp"] = 0.4f;
                    shapes["body_postureConfidence"] = 0.6f;
                    break;

                case "aroused":
                case "turned_on":
                    shapes["face_eyeNarrow"] = 0.2f;
                    shapes["face_mouthOpen"] = 0.15f;
                    shapes["face_eyeIntensity"] = 0.6f;
                    shapes["body_breathing"] = 0.7f;
                    break;

                default:
                    shapes["face_smile"] = 0.2f;
                    break;
            }

            return shapes;
        }

        /// <summary>
        /// Play a gesture animation
        /// </summary>
        public void PlayGesture(string gesture)
        {
            if (_currentAnimation != null)
            {
                StopCoroutine(_currentAnimation);
            }

            _currentAnimation = StartCoroutine(DoGesture(gesture));
        }

        private IEnumerator DoGesture(string gesture)
        {
            switch (gesture.ToLower())
            {
                case "wave":
                    yield return DoWaveGesture();
                    break;

                case "nod":
                    yield return DoNodGesture();
                    break;

                case "shake_head":
                    yield return DoShakeHeadGesture();
                    break;

                case "shrug":
                    yield return DoShrugGesture();
                    break;

                case "wink":
                    yield return DoWinkGesture();
                    break;

                case "flex":
                    yield return DoFlexGesture();
                    break;

                case "stretch":
                    yield return DoStretchGesture();
                    break;

                default:
                    Debug.LogWarning($"[SAMAnimator] Unknown gesture: {gesture}");
                    break;
            }
        }

        private IEnumerator DoWaveGesture()
        {
            PlayAnimation("Wave");
            yield return new WaitForSeconds(2f);
        }

        private IEnumerator DoNodGesture()
        {
            float duration = 0.8f;
            float elapsed = 0f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / duration;
                float nod = Mathf.Sin(t * Mathf.PI * 3) * 0.15f;
                blendShapes?.SetBlendShape("body_headTilt", 0.5f - nod);
                yield return null;
            }

            blendShapes?.SetBlendShape("body_headTilt", 0.5f);
        }

        private IEnumerator DoShakeHeadGesture()
        {
            PlayAnimation("ShakeHead");
            yield return new WaitForSeconds(1.5f);
        }

        private IEnumerator DoShrugGesture()
        {
            float duration = 1.2f;
            float elapsed = 0f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / duration;
                float shrug = Mathf.Sin(t * Mathf.PI) * 0.4f;
                blendShapes?.SetBlendShape("body_shoulderRoll", 0.5f + shrug);

                // Slight head tilt
                blendShapes?.SetBlendShape("body_headTilt", 0.5f + shrug * 0.3f);
                yield return null;
            }

            blendShapes?.SetBlendShape("body_shoulderRoll", 0.5f);
            blendShapes?.SetBlendShape("body_headTilt", 0.5f);
        }

        private IEnumerator DoWinkGesture()
        {
            float duration = 0.4f;

            // Close one eye
            float elapsed = 0f;
            while (elapsed < 0.1f)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / 0.1f;
                blendShapes?.SetBlendShape("face_eyesClosed", t * 0.5f); // Partial close for wink effect
                yield return null;
            }

            yield return new WaitForSeconds(0.15f);

            elapsed = 0f;
            while (elapsed < 0.15f)
            {
                elapsed += Time.deltaTime;
                float t = 1f - (elapsed / 0.15f);
                blendShapes?.SetBlendShape("face_eyesClosed", t * 0.5f);
                yield return null;
            }

            blendShapes?.SetBlendShape("face_eyesClosed", 0f);
        }

        private IEnumerator DoFlexGesture()
        {
            PlayAnimation("Flex");

            // Increase muscle definition during flex
            float duration = 2f;
            float elapsed = 0f;
            float baseMuscularity = blendShapes?.GetBlendShape("body_muscularity") ?? 0.5f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = elapsed / duration;
                float flexPeak = Mathf.Sin(t * Mathf.PI);

                blendShapes?.SetBlendShape("body_muscularity", baseMuscularity + flexPeak * 0.2f);
                blendShapes?.SetBlendShape("body_absDefinition", flexPeak * 0.3f);
                blendShapes?.SetBlendShape("body_chestDefinition", flexPeak * 0.25f);

                yield return null;
            }

            blendShapes?.SetBlendShape("body_muscularity", baseMuscularity);
        }

        private IEnumerator DoStretchGesture()
        {
            PlayAnimation("Stretch");
            yield return new WaitForSeconds(3f);
        }

        #endregion

        #region Intimate Animations

        /// <summary>
        /// Set arousal level (affects anatomy physics and expressions)
        /// </summary>
        public void SetArousalLevel(float level)
        {
            level = Mathf.Clamp01(level);
            SetFloat("ArousalLevel", level);

            // Apply to anatomy blend shapes
            blendShapes?.SetBlendShape("anatomy_arousal", level);

            // Subtle expression changes
            blendShapes?.SetBlendShape("face_eyeIntensity", level * 0.4f);
            blendShapes?.SetBlendShape("body_breathing", 0.3f + level * 0.4f);

            // Notify physics system if present
            var softBody = GetComponentInChildren<SoftBodyPhysics>();
            if (softBody != null)
            {
                softBody.SetArousalState(level);
            }
        }

        /// <summary>
        /// Play intimate animation by name
        /// </summary>
        public void PlayIntimateAnimation(string animationName, float speed = 1f)
        {
            _currentState = AnimationState.Intimate;

            SetFloat("Speed", speed);
            PlayAnimation(animationName);

            Debug.Log($"[SAMAnimator] Intimate animation: {animationName} @ {speed}x");
        }

        /// <summary>
        /// Stop intimate animation and return to idle
        /// </summary>
        public void StopIntimateAnimation(float fadeOutTime = 1f)
        {
            StartCoroutine(DoIntimateWindDown(fadeOutTime));
        }

        private IEnumerator DoIntimateWindDown(float duration)
        {
            float startArousal = blendShapes?.GetBlendShape("anatomy_arousal") ?? 0f;
            float elapsed = 0f;

            while (elapsed < duration)
            {
                elapsed += Time.deltaTime;
                float t = 1f - (elapsed / duration);
                SetArousalLevel(startArousal * t);
                yield return null;
            }

            SetArousalLevel(0f);
            SetState(AnimationState.Idle);
        }

        #endregion

        #region Animator Helpers

        private void SetBool(string name, bool value)
        {
            if (_animationHashes.TryGetValue(name, out int hash))
            {
                _animator.SetBool(hash, value);
            }
        }

        private void SetFloat(string name, float value)
        {
            if (_animationHashes.TryGetValue(name, out int hash))
            {
                _animator.SetFloat(hash, value);
            }
        }

        private void SetTrigger(string name)
        {
            if (_animationHashes.TryGetValue(name, out int hash))
            {
                _animator.SetTrigger(hash);
            }
        }

        #endregion
    }
}
