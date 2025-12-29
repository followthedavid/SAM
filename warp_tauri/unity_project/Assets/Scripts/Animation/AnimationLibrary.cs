using System.Collections.Generic;
using UnityEngine;

namespace SAM.Avatar
{
    /// <summary>
    /// Library of all available animations for the SAM avatar.
    /// Organizes animations by category and provides metadata.
    /// </summary>
    [CreateAssetMenu(fileName = "AnimationLibrary", menuName = "SAM/Animation Library")]
    public class AnimationLibrary : ScriptableObject
    {
        [Header("Idle Animations")]
        public AnimationEntry[] idleAnimations;

        [Header("Talking Animations")]
        public AnimationEntry[] talkingAnimations;

        [Header("Expression Animations")]
        public AnimationEntry[] expressionAnimations;

        [Header("Gesture Animations")]
        public AnimationEntry[] gestureAnimations;

        [Header("Intimate Animations")]
        public AnimationEntry[] intimateAnimations;

        [Header("Transition Animations")]
        public AnimationEntry[] transitionAnimations;

        // Runtime lookup
        private Dictionary<string, AnimationEntry> _animationLookup;

        public void Initialize()
        {
            _animationLookup = new Dictionary<string, AnimationEntry>();

            AddToLookup(idleAnimations);
            AddToLookup(talkingAnimations);
            AddToLookup(expressionAnimations);
            AddToLookup(gestureAnimations);
            AddToLookup(intimateAnimations);
            AddToLookup(transitionAnimations);

            Debug.Log($"[AnimationLibrary] Initialized with {_animationLookup.Count} animations");
        }

        private void AddToLookup(AnimationEntry[] entries)
        {
            if (entries == null) return;

            foreach (var entry in entries)
            {
                if (!string.IsNullOrEmpty(entry.id) && entry.clip != null)
                {
                    _animationLookup[entry.id] = entry;
                }
            }
        }

        public AnimationEntry GetAnimation(string id)
        {
            if (_animationLookup == null) Initialize();
            return _animationLookup.TryGetValue(id, out var entry) ? entry : null;
        }

        public AnimationEntry[] GetAnimationsByCategory(AnimationCategory category)
        {
            switch (category)
            {
                case AnimationCategory.Idle: return idleAnimations;
                case AnimationCategory.Talking: return talkingAnimations;
                case AnimationCategory.Expression: return expressionAnimations;
                case AnimationCategory.Gesture: return gestureAnimations;
                case AnimationCategory.Intimate: return intimateAnimations;
                case AnimationCategory.Transition: return transitionAnimations;
                default: return new AnimationEntry[0];
            }
        }

        public AnimationEntry GetRandomAnimation(AnimationCategory category)
        {
            var animations = GetAnimationsByCategory(category);
            if (animations == null || animations.Length == 0) return null;
            return animations[Random.Range(0, animations.Length)];
        }
    }

    [System.Serializable]
    public class AnimationEntry
    {
        [Tooltip("Unique identifier for this animation")]
        public string id;

        [Tooltip("Display name")]
        public string displayName;

        [Tooltip("The animation clip")]
        public AnimationClip clip;

        [Tooltip("Category for organization")]
        public AnimationCategory category;

        [Tooltip("Tags for searching/filtering")]
        public string[] tags;

        [Tooltip("Whether this animation loops")]
        public bool isLooping;

        [Tooltip("Default playback speed")]
        [Range(0.1f, 3f)]
        public float defaultSpeed = 1f;

        [Tooltip("Crossfade time when transitioning to this animation")]
        [Range(0f, 1f)]
        public float crossfadeTime = 0.2f;

        [Tooltip("Minimum arousal level required (for intimate animations)")]
        [Range(0f, 1f)]
        public float minArousalLevel = 0f;

        [Tooltip("Description for content moderation")]
        [TextArea]
        public string description;
    }

    public enum AnimationCategory
    {
        Idle,
        Talking,
        Expression,
        Gesture,
        Intimate,
        Transition
    }

    /// <summary>
    /// Default animation definitions (used when no library asset exists)
    /// </summary>
    public static class DefaultAnimations
    {
        public static readonly AnimationDefinition[] Idle = new[]
        {
            new AnimationDefinition("idle_default", "Default Idle", true, "Standing relaxed, subtle breathing"),
            new AnimationDefinition("idle_confident", "Confident Stance", true, "Standing with confident posture"),
            new AnimationDefinition("idle_relaxed", "Relaxed", true, "Casual relaxed stance"),
            new AnimationDefinition("idle_attentive", "Attentive", true, "Alert and focused"),
            new AnimationDefinition("idle_bored", "Bored", true, "Slight shifting, looking around"),
            new AnimationDefinition("idle_thinking", "Thinking", true, "Contemplative pose"),
        };

        public static readonly AnimationDefinition[] Talking = new[]
        {
            new AnimationDefinition("talk_casual", "Casual Talk", true, "Relaxed conversational gestures"),
            new AnimationDefinition("talk_excited", "Excited Talk", true, "Animated, enthusiastic gestures"),
            new AnimationDefinition("talk_serious", "Serious Talk", true, "Minimal movement, focused"),
            new AnimationDefinition("talk_explaining", "Explaining", true, "Hand gestures while explaining"),
            new AnimationDefinition("talk_whisper", "Whisper", true, "Leaning in, quiet talking"),
            new AnimationDefinition("talk_flirty", "Flirty Talk", false, "Playful, suggestive body language"),
        };

        public static readonly AnimationDefinition[] Expressions = new[]
        {
            new AnimationDefinition("expr_happy", "Happy", false, "Genuine smile and bright eyes"),
            new AnimationDefinition("expr_sad", "Sad", false, "Downcast expression"),
            new AnimationDefinition("expr_surprised", "Surprised", false, "Wide eyes, raised brows"),
            new AnimationDefinition("expr_angry", "Angry", false, "Furrowed brow, tense jaw"),
            new AnimationDefinition("expr_flirty", "Flirty", false, "Smirk, intense eye contact"),
            new AnimationDefinition("expr_seductive", "Seductive", false, "Bedroom eyes, slight smile"),
            new AnimationDefinition("expr_aroused", "Aroused", false, "Heavy-lidded, parted lips"),
            new AnimationDefinition("expr_ecstasy", "Ecstasy", false, "Peak pleasure expression"),
        };

        public static readonly AnimationDefinition[] Gestures = new[]
        {
            new AnimationDefinition("gest_wave", "Wave", false, "Friendly wave"),
            new AnimationDefinition("gest_nod", "Nod", false, "Affirmative nod"),
            new AnimationDefinition("gest_shake_head", "Shake Head", false, "Negative head shake"),
            new AnimationDefinition("gest_shrug", "Shrug", false, "Shoulder shrug"),
            new AnimationDefinition("gest_wink", "Wink", false, "Playful wink"),
            new AnimationDefinition("gest_flex", "Flex", false, "Show off muscles"),
            new AnimationDefinition("gest_stretch", "Stretch", false, "Full body stretch"),
            new AnimationDefinition("gest_yawn", "Yawn", false, "Tired yawn and stretch"),
            new AnimationDefinition("gest_blow_kiss", "Blow Kiss", false, "Playful kiss blow"),
            new AnimationDefinition("gest_beckon", "Beckon", false, "Come here gesture"),
        };

        public static readonly AnimationDefinition[] Intimate = new[]
        {
            // SFW intimate
            new AnimationDefinition("int_kiss_lips", "Kiss Lips", false, "Gentle kiss"),
            new AnimationDefinition("int_embrace", "Embrace", false, "Warm hug"),
            new AnimationDefinition("int_caress_face", "Caress Face", false, "Gentle face touch"),

            // NSFW - Solo
            new AnimationDefinition("int_strip_shirt", "Remove Shirt", false, "Slowly remove shirt"),
            new AnimationDefinition("int_strip_pants", "Remove Pants", false, "Remove pants"),
            new AnimationDefinition("int_touch_chest", "Touch Chest", false, "Self chest touch"),
            new AnimationDefinition("int_touch_abs", "Touch Abs", false, "Run hand over abs"),
            new AnimationDefinition("int_stroke_slow", "Stroke Slow", true, "Slow self-pleasure"),
            new AnimationDefinition("int_stroke_medium", "Stroke Medium", true, "Medium pace"),
            new AnimationDefinition("int_stroke_fast", "Stroke Fast", true, "Fast pace"),
            new AnimationDefinition("int_edge", "Edge", true, "Edging animation"),
            new AnimationDefinition("int_climax", "Climax", false, "Climax animation"),
            new AnimationDefinition("int_recovery", "Recovery", false, "Post-climax relaxation"),

            // NSFW - Interactive poses
            new AnimationDefinition("int_present", "Present", true, "Display pose"),
            new AnimationDefinition("int_tease", "Tease", true, "Teasing movements"),
            new AnimationDefinition("int_thrust_slow", "Thrust Slow", true, "Slow thrust motion"),
            new AnimationDefinition("int_thrust_medium", "Thrust Medium", true, "Medium thrust motion"),
            new AnimationDefinition("int_thrust_fast", "Thrust Fast", true, "Fast thrust motion"),
        };

        public static readonly AnimationDefinition[] Transitions = new[]
        {
            new AnimationDefinition("trans_idle_to_sit", "Idle to Sit", false, "Transition to sitting"),
            new AnimationDefinition("trans_sit_to_idle", "Sit to Idle", false, "Stand up from sitting"),
            new AnimationDefinition("trans_idle_to_lie", "Idle to Lie", false, "Lie down"),
            new AnimationDefinition("trans_lie_to_idle", "Lie to Idle", false, "Get up from lying"),
        };
    }

    [System.Serializable]
    public struct AnimationDefinition
    {
        public string Id;
        public string Name;
        public bool IsLooping;
        public string Description;

        public AnimationDefinition(string id, string name, bool isLooping, string description)
        {
            Id = id;
            Name = name;
            IsLooping = isLooping;
            Description = description;
        }
    }
}
