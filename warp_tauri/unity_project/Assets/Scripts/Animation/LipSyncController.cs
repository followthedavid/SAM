using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace SAM.Avatar
{
    /// <summary>
    /// Handles real-time lip synchronization using visemes.
    /// Receives lip sync data from Warp Open and applies to face blend shapes.
    /// </summary>
    public class LipSyncController : MonoBehaviour
    {
        [Header("References")]
        public BlendShapeController blendShapes;

        [Header("Settings")]
        [Range(0f, 2f)] public float intensity = 1f;
        [Range(0f, 1f)] public float smoothing = 0.3f;
        [Range(0f, 1f)] public float jawContribution = 0.4f;

        [Header("Debug")]
        public bool showDebugViseme;
        public string currentViseme = "REST";

        // Viseme data
        private Dictionary<string, float> _currentVisemes = new Dictionary<string, float>();
        private Dictionary<string, float> _targetVisemes = new Dictionary<string, float>();

        // Lip sync queue for pre-generated audio
        private Queue<LipSyncFrame> _lipSyncQueue = new Queue<LipSyncFrame>();
        private bool _isPlayingLipSync;
        private float _lipSyncStartTime;

        // All viseme names
        private static readonly string[] VisemeNames = {
            "face_viseme_REST", "face_viseme_A", "face_viseme_E", "face_viseme_I",
            "face_viseme_O", "face_viseme_U", "face_viseme_M", "face_viseme_F",
            "face_viseme_TH", "face_viseme_S", "face_viseme_T", "face_viseme_K",
            "face_viseme_R", "face_viseme_W"
        };

        public struct LipSyncFrame
        {
            public float Time;
            public string Viseme;
            public float Intensity;
        }

        private void Awake()
        {
            // Initialize all visemes to 0
            foreach (var viseme in VisemeNames)
            {
                _currentVisemes[viseme] = 0f;
                _targetVisemes[viseme] = 0f;
            }
        }

        private void Update()
        {
            if (_isPlayingLipSync)
            {
                UpdatePreGeneratedLipSync();
            }

            // Smooth transition between current and target visemes
            foreach (var viseme in VisemeNames)
            {
                float current = _currentVisemes[viseme];
                float target = _targetVisemes[viseme];

                _currentVisemes[viseme] = Mathf.Lerp(current, target, Time.deltaTime / Mathf.Max(0.01f, smoothing));

                // Apply to blend shape
                if (blendShapes != null)
                {
                    blendShapes.SetBlendShape(viseme, _currentVisemes[viseme] * intensity);
                }
            }

            // Apply jaw movement based on mouth opening visemes
            UpdateJaw();
        }

        private void UpdateJaw()
        {
            if (blendShapes == null) return;

            // Calculate jaw opening from vowel visemes
            float jawOpen = 0f;
            jawOpen += _currentVisemes["face_viseme_A"] * 0.8f;
            jawOpen += _currentVisemes["face_viseme_E"] * 0.4f;
            jawOpen += _currentVisemes["face_viseme_I"] * 0.3f;
            jawOpen += _currentVisemes["face_viseme_O"] * 0.7f;
            jawOpen += _currentVisemes["face_viseme_U"] * 0.5f;

            jawOpen = Mathf.Clamp01(jawOpen);
            blendShapes.SetBlendShape("face_mouthOpen", jawOpen * jawContribution * intensity);
        }

        #region Real-time Lip Sync

        /// <summary>
        /// Set a single viseme value (for real-time streaming)
        /// </summary>
        public void SetViseme(string viseme, float value)
        {
            string fullName = viseme.StartsWith("face_viseme_") ? viseme : $"face_viseme_{viseme}";

            if (_targetVisemes.ContainsKey(fullName))
            {
                // Reset all other visemes
                foreach (var key in VisemeNames)
                {
                    _targetVisemes[key] = 0f;
                }

                _targetVisemes[fullName] = Mathf.Clamp01(value);
                currentViseme = viseme;
            }
        }

        /// <summary>
        /// Set multiple visemes at once (for blended phonemes)
        /// </summary>
        public void SetVisemes(Dictionary<string, float> visemes)
        {
            // Reset all
            foreach (var key in VisemeNames)
            {
                _targetVisemes[key] = 0f;
            }

            // Apply new values
            foreach (var kvp in visemes)
            {
                string fullName = kvp.Key.StartsWith("face_viseme_") ? kvp.Key : $"face_viseme_{kvp.Key}";
                if (_targetVisemes.ContainsKey(fullName))
                {
                    _targetVisemes[fullName] = Mathf.Clamp01(kvp.Value);
                }
            }
        }

        #endregion

        #region Pre-generated Lip Sync

        /// <summary>
        /// Load lip sync data for pre-generated audio
        /// Format: list of {time, viseme, intensity}
        /// </summary>
        public void LoadLipSyncData(List<LipSyncFrame> frames)
        {
            _lipSyncQueue.Clear();

            foreach (var frame in frames)
            {
                _lipSyncQueue.Enqueue(frame);
            }

            Debug.Log($"[LipSync] Loaded {frames.Count} frames");
        }

        /// <summary>
        /// Load lip sync data from JSON array
        /// </summary>
        public void LoadLipSyncDataFromJson(object[] jsonData)
        {
            var frames = new List<LipSyncFrame>();

            foreach (var item in jsonData)
            {
                if (item is Dictionary<string, object> dict)
                {
                    var frame = new LipSyncFrame
                    {
                        Time = dict.ContainsKey("time") ? System.Convert.ToSingle(dict["time"]) : 0f,
                        Viseme = dict.ContainsKey("viseme") ? dict["viseme"].ToString() : "REST",
                        Intensity = dict.ContainsKey("intensity") ? System.Convert.ToSingle(dict["intensity"]) : 1f
                    };
                    frames.Add(frame);
                }
            }

            LoadLipSyncData(frames);
        }

        /// <summary>
        /// Start playing loaded lip sync data
        /// </summary>
        public void StartLipSync()
        {
            _isPlayingLipSync = true;
            _lipSyncStartTime = Time.time;
            Debug.Log("[LipSync] Started playback");
        }

        /// <summary>
        /// Stop lip sync playback
        /// </summary>
        public void StopLipSync()
        {
            _isPlayingLipSync = false;
            _lipSyncQueue.Clear();

            // Reset to rest
            foreach (var key in VisemeNames)
            {
                _targetVisemes[key] = 0f;
            }
            _targetVisemes["face_viseme_REST"] = 1f;

            Debug.Log("[LipSync] Stopped playback");
        }

        private void UpdatePreGeneratedLipSync()
        {
            float currentTime = (Time.time - _lipSyncStartTime) * 1000f; // Convert to ms

            // Process all frames up to current time
            while (_lipSyncQueue.Count > 0)
            {
                var frame = _lipSyncQueue.Peek();

                if (frame.Time <= currentTime)
                {
                    _lipSyncQueue.Dequeue();
                    SetViseme(frame.Viseme, frame.Intensity);
                }
                else
                {
                    break;
                }
            }

            // Check if finished
            if (_lipSyncQueue.Count == 0)
            {
                _isPlayingLipSync = false;
                SetViseme("REST", 1f);
            }
        }

        #endregion

        #region Utility

        /// <summary>
        /// Map a phoneme to viseme
        /// </summary>
        public static string PhonemeToViseme(string phoneme)
        {
            phoneme = phoneme.ToUpper();

            // IPA to viseme mapping
            var mapping = new Dictionary<string, string>
            {
                // Vowels
                {"AA", "A"}, {"AE", "A"}, {"AH", "A"}, {"AO", "O"}, {"AW", "O"},
                {"AY", "A"}, {"EH", "E"}, {"ER", "R"}, {"EY", "E"}, {"IH", "I"},
                {"IY", "I"}, {"OW", "O"}, {"OY", "O"}, {"UH", "U"}, {"UW", "U"},

                // Consonants
                {"B", "M"}, {"P", "M"}, {"M", "M"},
                {"F", "F"}, {"V", "F"},
                {"TH", "TH"}, {"DH", "TH"},
                {"S", "S"}, {"Z", "S"}, {"SH", "S"}, {"ZH", "S"}, {"CH", "S"}, {"JH", "S"},
                {"T", "T"}, {"D", "T"}, {"N", "T"},
                {"K", "K"}, {"G", "K"}, {"NG", "K"},
                {"R", "R"}, {"L", "R"},
                {"W", "W"}, {"Y", "I"}, {"HH", "REST"},

                // Silence
                {"SIL", "REST"}, {"", "REST"}
            };

            return mapping.TryGetValue(phoneme, out string viseme) ? viseme : "REST";
        }

        /// <summary>
        /// Get current speaking intensity (for animation blending)
        /// </summary>
        public float GetSpeakingIntensity()
        {
            float total = 0f;
            foreach (var kvp in _currentVisemes)
            {
                if (kvp.Key != "face_viseme_REST")
                {
                    total += kvp.Value;
                }
            }
            return Mathf.Clamp01(total);
        }

        /// <summary>
        /// Reset to rest position
        /// </summary>
        public void Reset()
        {
            foreach (var key in VisemeNames)
            {
                _currentVisemes[key] = 0f;
                _targetVisemes[key] = 0f;
            }
            _targetVisemes["face_viseme_REST"] = 1f;
            currentViseme = "REST";
        }

        #endregion

        private void OnGUI()
        {
            if (!showDebugViseme) return;

            GUI.Label(new Rect(10, 10, 200, 25), $"Current Viseme: {currentViseme}");

            int y = 35;
            foreach (var kvp in _currentVisemes)
            {
                if (kvp.Value > 0.01f)
                {
                    string name = kvp.Key.Replace("face_viseme_", "");
                    GUI.Label(new Rect(10, y, 100, 20), name);
                    GUI.HorizontalSlider(new Rect(110, y, 100, 20), kvp.Value, 0f, 1f);
                    y += 22;
                }
            }
        }
    }
}
