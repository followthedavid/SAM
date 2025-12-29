using System.Collections.Generic;
using UnityEngine;

namespace SAM.Avatar
{
    /// <summary>
    /// Soft body physics simulation for anatomy.
    /// Uses spring-based jiggle physics for realistic movement.
    ///
    /// For production, consider using:
    /// - Magica Cloth 2 (Asset Store)
    /// - Obi Softbody (Asset Store)
    /// - Unity Cloth component
    /// </summary>
    [RequireComponent(typeof(SkinnedMeshRenderer))]
    public class SoftBodyPhysics : MonoBehaviour
    {
        [Header("Physics Settings")]
        [Range(0f, 1f)] public float stiffness = 0.3f;
        [Range(0f, 1f)] public float damping = 0.5f;
        [Range(0f, 1f)] public float gravity = 0.3f;
        [Range(0f, 2f)] public float mass = 1f;

        [Header("Collision")]
        public bool enableCollision = true;
        [Range(0f, 0.5f)] public float collisionRadius = 0.05f;
        public LayerMask collisionLayers = -1;

        [Header("Bones to Simulate")]
        public string[] softBodyBones = new[]
        {
            "shaft_base", "shaft_mid", "shaft_tip", "glans",
            "testicle_L", "testicle_R", "scrotum"
        };

        [Header("State")]
        [Range(0f, 1f)] public float arousalLevel = 0f;

        // Runtime data
        private SkinnedMeshRenderer _mesh;
        private Transform _rootBone;
        private Dictionary<string, BoneState> _boneStates = new Dictionary<string, BoneState>();
        private bool _initialized;

        private class BoneState
        {
            public Transform Bone;
            public Vector3 RestLocalPosition;
            public Quaternion RestLocalRotation;
            public Vector3 Velocity;
            public Vector3 CurrentOffset;
        }

        private void Awake()
        {
            _mesh = GetComponent<SkinnedMeshRenderer>();
        }

        private void Start()
        {
            Initialize();
        }

        public void Initialize()
        {
            if (_initialized) return;

            _rootBone = _mesh.rootBone ?? transform;
            CacheBones();
            _initialized = true;

            Debug.Log($"[SoftBody] Initialized with {_boneStates.Count} bones");
        }

        private void CacheBones()
        {
            foreach (string boneName in softBodyBones)
            {
                Transform bone = FindBoneRecursive(_rootBone, boneName);
                if (bone != null)
                {
                    _boneStates[boneName] = new BoneState
                    {
                        Bone = bone,
                        RestLocalPosition = bone.localPosition,
                        RestLocalRotation = bone.localRotation,
                        Velocity = Vector3.zero,
                        CurrentOffset = Vector3.zero
                    };
                }
            }
        }

        private Transform FindBoneRecursive(Transform parent, string name)
        {
            if (parent.name.ToLower().Contains(name.ToLower()))
                return parent;

            foreach (Transform child in parent)
            {
                Transform found = FindBoneRecursive(child, name);
                if (found != null) return found;
            }

            return null;
        }

        private void FixedUpdate()
        {
            if (!_initialized) return;

            foreach (var state in _boneStates.Values)
            {
                SimulateBone(state);
            }
        }

        private void SimulateBone(BoneState state)
        {
            if (state.Bone == null) return;

            // Calculate forces
            Vector3 force = Vector3.zero;

            // Gravity
            force += Vector3.down * gravity * mass;

            // Spring force (return to rest)
            Vector3 displacement = state.CurrentOffset;
            force -= displacement * stiffness * 100f;

            // Damping
            force -= state.Velocity * damping * 10f;

            // Apply arousal stiffening
            float effectiveStiffness = Mathf.Lerp(stiffness, 1f, arousalLevel * 0.7f);
            force -= displacement * (effectiveStiffness - stiffness) * 50f;

            // Integrate
            state.Velocity += force * Time.fixedDeltaTime;
            state.CurrentOffset += state.Velocity * Time.fixedDeltaTime;

            // Collision
            if (enableCollision)
            {
                HandleCollision(state);
            }

            // Clamp offset
            float maxOffset = 0.1f * (1f - arousalLevel * 0.5f);
            if (state.CurrentOffset.magnitude > maxOffset)
            {
                state.CurrentOffset = state.CurrentOffset.normalized * maxOffset;
                state.Velocity *= 0.5f;
            }

            // Apply to bone
            state.Bone.localPosition = state.RestLocalPosition + state.Bone.parent.InverseTransformVector(state.CurrentOffset);
        }

        private void HandleCollision(BoneState state)
        {
            Vector3 worldPos = state.Bone.position;

            Collider[] hits = Physics.OverlapSphere(worldPos, collisionRadius, collisionLayers);
            foreach (var hit in hits)
            {
                if (hit.transform.IsChildOf(transform)) continue;

                Vector3 closestPoint = hit.ClosestPoint(worldPos);
                Vector3 pushDir = worldPos - closestPoint;
                float distance = pushDir.magnitude;

                if (distance < collisionRadius && distance > 0.001f)
                {
                    pushDir.Normalize();
                    float penetration = collisionRadius - distance;
                    state.CurrentOffset += pushDir * penetration;
                    state.Velocity = Vector3.Reflect(state.Velocity, pushDir) * 0.3f;
                }
            }
        }

        /// <summary>
        /// Apply external force (e.g., from movement or interaction)
        /// </summary>
        public void ApplyForce(Vector3 force)
        {
            foreach (var state in _boneStates.Values)
            {
                state.Velocity += force * (1f / mass);
            }
        }

        /// <summary>
        /// Apply force to a specific bone
        /// </summary>
        public void ApplyForce(string boneName, Vector3 force)
        {
            if (_boneStates.TryGetValue(boneName, out var state))
            {
                state.Velocity += force * (1f / mass);
            }
        }

        /// <summary>
        /// Set arousal state (affects stiffness and position)
        /// </summary>
        public void SetArousalState(float level)
        {
            arousalLevel = Mathf.Clamp01(level);

            // Arousal affects rest position for some bones
            if (_boneStates.TryGetValue("shaft_tip", out var tipState))
            {
                // Tip moves up/forward with arousal
                Vector3 arousalOffset = new Vector3(0, level * 0.02f, level * 0.05f);
                tipState.RestLocalPosition = tipState.RestLocalPosition + arousalOffset * (1f - arousalLevel);
            }
        }

        /// <summary>
        /// Reset all bones to rest position
        /// </summary>
        public void ResetToRest()
        {
            foreach (var state in _boneStates.Values)
            {
                state.CurrentOffset = Vector3.zero;
                state.Velocity = Vector3.zero;
                state.Bone.localPosition = state.RestLocalPosition;
                state.Bone.localRotation = state.RestLocalRotation;
            }
        }

        private void OnDrawGizmosSelected()
        {
            if (!Application.isPlaying || !_initialized) return;

            Gizmos.color = Color.cyan;
            foreach (var state in _boneStates.Values)
            {
                if (state.Bone != null)
                {
                    Gizmos.DrawWireSphere(state.Bone.position, collisionRadius);
                }
            }
        }
    }

    /// <summary>
    /// Simple jiggle physics for secondary motion (butt, pecs, etc.)
    /// </summary>
    public class JigglePhysics : MonoBehaviour
    {
        [Header("Settings")]
        [Range(0f, 1f)] public float jiggleAmount = 0.3f;
        [Range(0f, 1f)] public float stiffness = 0.5f;
        [Range(0f, 1f)] public float damping = 0.3f;

        [Header("Blend Shapes")]
        public SkinnedMeshRenderer targetMesh;
        public string[] jiggleBlendShapes = new[] { "body_buttJiggle", "body_chestJiggle" };

        private Vector3 _lastPosition;
        private Vector3 _velocity;
        private float[] _jiggleValues;
        private Dictionary<string, int> _blendShapeIndices = new Dictionary<string, int>();

        private void Start()
        {
            if (targetMesh == null) targetMesh = GetComponent<SkinnedMeshRenderer>();

            _lastPosition = transform.position;
            _jiggleValues = new float[jiggleBlendShapes.Length];

            // Cache blend shape indices
            if (targetMesh?.sharedMesh != null)
            {
                for (int i = 0; i < targetMesh.sharedMesh.blendShapeCount; i++)
                {
                    string name = targetMesh.sharedMesh.GetBlendShapeName(i);
                    _blendShapeIndices[name] = i;
                }
            }
        }

        private void LateUpdate()
        {
            // Calculate movement velocity
            Vector3 currentPosition = transform.position;
            Vector3 movement = currentPosition - _lastPosition;
            _lastPosition = currentPosition;

            // Accumulate velocity
            _velocity += movement;

            // Apply jiggle physics
            for (int i = 0; i < jiggleBlendShapes.Length; i++)
            {
                // Calculate jiggle from velocity
                float jiggle = _velocity.magnitude * jiggleAmount * 10f;

                // Spring physics
                float target = Mathf.Clamp01(jiggle);
                _jiggleValues[i] = Mathf.Lerp(_jiggleValues[i], target, Time.deltaTime * stiffness * 10f);

                // Apply to blend shape
                string shapeName = jiggleBlendShapes[i];
                if (_blendShapeIndices.TryGetValue(shapeName, out int index))
                {
                    targetMesh.SetBlendShapeWeight(index, _jiggleValues[i] * 100f);
                }
            }

            // Dampen velocity
            _velocity *= 1f - (damping * 5f * Time.deltaTime);
        }
    }
}
