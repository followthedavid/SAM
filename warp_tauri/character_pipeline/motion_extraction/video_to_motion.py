"""
Video to Motion Pipeline
Extracts motion data from videos and applies to generated characters.

Supports:
- MediaPipe for pose estimation
- OpenPose (if installed)
- DensePose for detailed body tracking
- Custom anatomical tracking

Usage:
    python video_to_motion.py --input videos/ --output motions/
"""

import os
import sys
import json
import asyncio
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ProcessPoolExecutor
import numpy as np

# Try to import optional dependencies
try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    print("Warning: OpenCV not installed. Install with: pip install opencv-python")

try:
    import mediapipe as mp
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False
    print("Warning: MediaPipe not installed. Install with: pip install mediapipe")


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class JointPosition:
    """3D joint position with confidence."""
    x: float
    y: float
    z: float
    confidence: float = 1.0


@dataclass
class PoseFrame:
    """Single frame of pose data."""
    frame_number: int
    timestamp: float
    joints: Dict[str, JointPosition]

    # Anatomical-specific tracking
    pelvis_rotation: Optional[Tuple[float, float, float]] = None
    hip_angle: Optional[float] = None


@dataclass
class MotionClip:
    """Complete motion capture clip."""
    name: str
    source_video: str
    fps: float
    frame_count: int
    duration: float
    frames: List[PoseFrame]

    # Metadata
    resolution: Tuple[int, int] = (1920, 1080)
    tracking_method: str = "mediapipe"

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            'name': self.name,
            'source_video': self.source_video,
            'fps': self.fps,
            'frame_count': self.frame_count,
            'duration': self.duration,
            'resolution': self.resolution,
            'tracking_method': self.tracking_method,
            'frames': [
                {
                    'frame_number': f.frame_number,
                    'timestamp': f.timestamp,
                    'joints': {
                        k: asdict(v) for k, v in f.joints.items()
                    },
                    'pelvis_rotation': f.pelvis_rotation,
                    'hip_angle': f.hip_angle,
                }
                for f in self.frames
            ]
        }

    def save(self, filepath: str):
        """Save motion clip to JSON."""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> 'MotionClip':
        """Load motion clip from JSON."""
        with open(filepath) as f:
            data = json.load(f)

        frames = [
            PoseFrame(
                frame_number=fd['frame_number'],
                timestamp=fd['timestamp'],
                joints={
                    k: JointPosition(**v)
                    for k, v in fd['joints'].items()
                },
                pelvis_rotation=tuple(fd['pelvis_rotation']) if fd.get('pelvis_rotation') else None,
                hip_angle=fd.get('hip_angle'),
            )
            for fd in data['frames']
        ]

        return cls(
            name=data['name'],
            source_video=data['source_video'],
            fps=data['fps'],
            frame_count=data['frame_count'],
            duration=data['duration'],
            frames=frames,
            resolution=tuple(data.get('resolution', (1920, 1080))),
            tracking_method=data.get('tracking_method', 'unknown'),
        )


# ============================================================================
# MOTION EXTRACTORS
# ============================================================================

class MediaPipeExtractor:
    """Extract motion using MediaPipe Pose."""

    # MediaPipe landmark indices
    LANDMARK_NAMES = {
        0: 'nose',
        11: 'left_shoulder',
        12: 'right_shoulder',
        13: 'left_elbow',
        14: 'right_elbow',
        15: 'left_wrist',
        16: 'right_wrist',
        23: 'left_hip',
        24: 'right_hip',
        25: 'left_knee',
        26: 'right_knee',
        27: 'left_ankle',
        28: 'right_ankle',
    }

    def __init__(self):
        if not HAS_MEDIAPIPE:
            raise ImportError("MediaPipe not installed")

        self.pose = mp.solutions.pose.Pose(
            static_image_mode=False,
            model_complexity=2,  # Most accurate
            enable_segmentation=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def extract(self, video_path: str) -> MotionClip:
        """Extract motion from video."""
        if not HAS_CV2:
            raise ImportError("OpenCV not installed")

        cap = cv2.VideoCapture(video_path)

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = frame_count / fps

        frames = []
        frame_num = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to RGB
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Process
            results = self.pose.process(rgb)

            if results.pose_landmarks:
                joints = {}

                for idx, name in self.LANDMARK_NAMES.items():
                    landmark = results.pose_landmarks.landmark[idx]
                    joints[name] = JointPosition(
                        x=landmark.x,
                        y=landmark.y,
                        z=landmark.z,
                        confidence=landmark.visibility,
                    )

                # Calculate pelvis rotation from hip positions
                pelvis_rotation = self._calculate_pelvis_rotation(joints)
                hip_angle = self._calculate_hip_angle(joints)

                pose_frame = PoseFrame(
                    frame_number=frame_num,
                    timestamp=frame_num / fps,
                    joints=joints,
                    pelvis_rotation=pelvis_rotation,
                    hip_angle=hip_angle,
                )
                frames.append(pose_frame)

            frame_num += 1

            # Progress
            if frame_num % 100 == 0:
                print(f"  Processed {frame_num}/{frame_count} frames")

        cap.release()

        return MotionClip(
            name=Path(video_path).stem,
            source_video=video_path,
            fps=fps,
            frame_count=frame_count,
            duration=duration,
            frames=frames,
            resolution=(width, height),
            tracking_method='mediapipe',
        )

    def _calculate_pelvis_rotation(self, joints: Dict[str, JointPosition]) -> Tuple[float, float, float]:
        """Calculate pelvis rotation from hip positions."""
        left_hip = joints.get('left_hip')
        right_hip = joints.get('right_hip')

        if not left_hip or not right_hip:
            return (0.0, 0.0, 0.0)

        # Calculate rotation angles
        dx = right_hip.x - left_hip.x
        dy = right_hip.y - left_hip.y
        dz = right_hip.z - left_hip.z

        # Yaw (rotation around vertical axis)
        yaw = np.arctan2(dz, dx)

        # Pitch (forward/backward tilt)
        pitch = np.arctan2(dy, np.sqrt(dx*dx + dz*dz))

        # Roll (side to side)
        roll = np.arctan2(dy, dx)

        return (float(pitch), float(yaw), float(roll))

    def _calculate_hip_angle(self, joints: Dict[str, JointPosition]) -> float:
        """Calculate hip flexion angle."""
        # Simplified - would need more landmarks for accurate calculation
        left_hip = joints.get('left_hip')
        left_knee = joints.get('left_knee')

        if not left_hip or not left_knee:
            return 0.0

        dy = left_knee.y - left_hip.y
        dz = left_knee.z - left_hip.z

        angle = np.arctan2(dz, dy)
        return float(np.degrees(angle))


class AnatomicalTracker:
    """
    Specialized tracker for anatomical motion.
    Uses region-of-interest detection and motion flow.
    """

    def __init__(self):
        if not HAS_CV2:
            raise ImportError("OpenCV not installed")

    def extract_anatomical_motion(
        self,
        video_path: str,
        roi: Optional[Tuple[int, int, int, int]] = None
    ) -> Dict[str, List[float]]:
        """
        Extract motion specifically for anatomical regions.

        Returns motion vectors for:
        - position_x, position_y
        - velocity_x, velocity_y
        - swing_angle
        - bounce_intensity
        """
        cap = cv2.VideoCapture(video_path)

        fps = cap.get(cv2.CAP_PROP_FPS)

        # Motion data
        positions_x = []
        positions_y = []
        velocities_x = []
        velocities_y = []
        swing_angles = []

        prev_frame = None
        prev_center = None

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Apply ROI if specified
            if roi:
                x, y, w, h = roi
                gray = gray[y:y+h, x:x+w]

            if prev_frame is not None:
                # Optical flow
                flow = cv2.calcOpticalFlowFarneback(
                    prev_frame, gray, None,
                    pyr_scale=0.5, levels=3, winsize=15,
                    iterations=3, poly_n=5, poly_sigma=1.2,
                    flags=0
                )

                # Calculate motion metrics
                mean_flow_x = np.mean(flow[..., 0])
                mean_flow_y = np.mean(flow[..., 1])

                velocities_x.append(float(mean_flow_x))
                velocities_y.append(float(mean_flow_y))

                # Track center of motion
                magnitude = np.sqrt(flow[..., 0]**2 + flow[..., 1]**2)
                if np.max(magnitude) > 0.1:
                    y_coords, x_coords = np.where(magnitude > np.percentile(magnitude, 90))
                    if len(x_coords) > 0:
                        center_x = np.mean(x_coords)
                        center_y = np.mean(y_coords)
                        positions_x.append(float(center_x))
                        positions_y.append(float(center_y))

                        if prev_center:
                            dx = center_x - prev_center[0]
                            dy = center_y - prev_center[1]
                            angle = np.arctan2(dx, dy)
                            swing_angles.append(float(np.degrees(angle)))
                        else:
                            swing_angles.append(0.0)

                        prev_center = (center_x, center_y)
                    else:
                        positions_x.append(positions_x[-1] if positions_x else 0.0)
                        positions_y.append(positions_y[-1] if positions_y else 0.0)
                        swing_angles.append(0.0)
                else:
                    positions_x.append(positions_x[-1] if positions_x else 0.0)
                    positions_y.append(positions_y[-1] if positions_y else 0.0)
                    swing_angles.append(0.0)

            prev_frame = gray.copy()

        cap.release()

        return {
            'fps': fps,
            'position_x': positions_x,
            'position_y': positions_y,
            'velocity_x': velocities_x,
            'velocity_y': velocities_y,
            'swing_angle': swing_angles,
        }


# ============================================================================
# BLENDER INTEGRATION
# ============================================================================

def apply_motion_to_blender(motion_clip: MotionClip, blend_file: str, output_file: str):
    """
    Apply extracted motion to a Blender character.
    Runs Blender in background mode.
    """

    script = f'''
import bpy
import json

# Load motion data
motion_data = json.loads("""{json.dumps(motion_clip.to_dict())}""")

# Get armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

if not armature:
    print("No armature found!")
    exit(1)

# Set frame range
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = motion_data['frame_count']
bpy.context.scene.render.fps = int(motion_data['fps'])

# Apply motion to bones
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='POSE')

for frame_data in motion_data['frames']:
    frame_num = frame_data['frame_number']
    bpy.context.scene.frame_set(frame_num)

    # Apply pelvis rotation
    if frame_data.get('pelvis_rotation'):
        pelvis_bone = armature.pose.bones.get('Pelvis')
        if pelvis_bone:
            pelvis_bone.rotation_euler = frame_data['pelvis_rotation']
            pelvis_bone.keyframe_insert(data_path='rotation_euler', frame=frame_num)

    # Apply joint positions (simplified - would need IK for full implementation)
    joints = frame_data.get('joints', {{}})

    # Hip angle affects anatomy control
    if frame_data.get('hip_angle'):
        anatomy_ctrl = armature.pose.bones.get('Anatomy_Control')
        if anatomy_ctrl:
            # Convert hip angle to anatomy rotation
            anatomy_ctrl.rotation_euler.x = frame_data['hip_angle'] * 0.5
            anatomy_ctrl.keyframe_insert(data_path='rotation_euler', frame=frame_num)

bpy.ops.object.mode_set(mode='OBJECT')

# Save
bpy.ops.wm.save_as_mainfile(filepath="{output_file}")
print("Motion applied successfully!")
'''

    # Write script to temp file
    script_path = "/tmp/apply_motion.py"
    with open(script_path, 'w') as f:
        f.write(script)

    # Run Blender
    result = subprocess.run([
        'blender', '--background', blend_file,
        '--python', script_path
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Blender error: {result.stderr}")
        return False

    return True


def apply_anatomical_motion_to_blender(
    anatomical_motion: Dict[str, List[float]],
    blend_file: str,
    output_file: str
):
    """Apply anatomical-specific motion to character."""

    fps = anatomical_motion['fps']
    frame_count = len(anatomical_motion['velocity_x'])

    script = f'''
import bpy
import json

# Motion data
velocities_x = {anatomical_motion['velocity_x']}
velocities_y = {anatomical_motion['velocity_y']}
swing_angles = {anatomical_motion['swing_angle']}
fps = {fps}

# Get armature
armature = None
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        armature = obj
        break

if not armature:
    print("No armature found!")
    exit(1)

# Set frame range
bpy.context.scene.frame_start = 0
bpy.context.scene.frame_end = len(velocities_x)
bpy.context.scene.render.fps = int(fps)

# Apply motion to anatomy bones
bpy.context.view_layer.objects.active = armature
bpy.ops.object.mode_set(mode='POSE')

for i, (vx, vy, angle) in enumerate(zip(velocities_x, velocities_y, swing_angles)):
    bpy.context.scene.frame_set(i)

    # Apply to anatomy bone chain
    for j in range(6):
        bone_name = f"Anatomy_{{j}}"
        bone = armature.pose.bones.get(bone_name)
        if bone:
            # Propagate motion down chain with increasing effect
            factor = (j + 1) / 6

            bone.rotation_euler.x = vx * 0.1 * factor
            bone.rotation_euler.z = angle * 0.02 * factor

            bone.keyframe_insert(data_path='rotation_euler', frame=i)

    # Apply to testicle bones
    for side in ['L', 'R']:
        bone = armature.pose.bones.get(f"Testicle_{{side}}")
        if bone:
            bone.location.y = vy * 0.01
            bone.keyframe_insert(data_path='location', frame=i)

bpy.ops.object.mode_set(mode='OBJECT')

# Save
bpy.ops.wm.save_as_mainfile(filepath="{output_file}")
print("Anatomical motion applied!")
'''

    script_path = "/tmp/apply_anatomical_motion.py"
    with open(script_path, 'w') as f:
        f.write(script)

    result = subprocess.run([
        'blender', '--background', blend_file,
        '--python', script_path
    ], capture_output=True, text=True)

    return result.returncode == 0


# ============================================================================
# BATCH PROCESSING
# ============================================================================

class MotionPipeline:
    """Complete video-to-animated-character pipeline."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.motion_dir = self.output_dir / "motions"
        self.motion_dir.mkdir(exist_ok=True)

        self.characters_dir = self.output_dir / "characters"
        self.characters_dir.mkdir(exist_ok=True)

        self.animated_dir = self.output_dir / "animated"
        self.animated_dir.mkdir(exist_ok=True)

        # Extractors
        self.pose_extractor = MediaPipeExtractor() if HAS_MEDIAPIPE else None
        self.anatomical_extractor = AnatomicalTracker() if HAS_CV2 else None

    async def process_video(
        self,
        video_path: str,
        generate_character: bool = True,
        extract_anatomical: bool = True,
    ) -> dict:
        """Process a single video through the complete pipeline."""

        video_path = Path(video_path)
        name = video_path.stem

        print(f"\nProcessing: {name}")
        result = {'video': str(video_path), 'name': name}

        # Step 1: Extract body motion
        if self.pose_extractor:
            print("  Extracting body motion...")
            motion_clip = self.pose_extractor.extract(str(video_path))

            motion_path = self.motion_dir / f"{name}_body.json"
            motion_clip.save(str(motion_path))
            result['body_motion'] = str(motion_path)

        # Step 2: Extract anatomical motion
        if extract_anatomical and self.anatomical_extractor:
            print("  Extracting anatomical motion...")
            anatomical_motion = self.anatomical_extractor.extract_anatomical_motion(
                str(video_path)
            )

            anatomical_path = self.motion_dir / f"{name}_anatomical.json"
            with open(anatomical_path, 'w') as f:
                json.dump(anatomical_motion, f)
            result['anatomical_motion'] = str(anatomical_path)

        # Step 3: Generate character (calls Blender addon)
        if generate_character:
            print("  Generating character...")
            character_path = self.characters_dir / f"{name}.blend"

            # Call Blender to generate character
            gen_result = subprocess.run([
                'blender', '--background',
                '--python-expr', f'''
import bpy
import sys
sys.path.insert(0, "{Path(__file__).parent.parent / 'blender_addon'}")
from __init__ import CharacterGenerator, SAMGeneratorProperties

# Register properties manually for background mode
bpy.types.Scene.sam_generator = bpy.props.PointerProperty(type=SAMGeneratorProperties)

# Generate
generator = CharacterGenerator(bpy.context)
result = generator.generate(name="{name}")

# Save
bpy.ops.wm.save_as_mainfile(filepath="{character_path}")
'''
            ], capture_output=True, text=True)

            if gen_result.returncode == 0:
                result['character'] = str(character_path)

        # Step 4: Apply motion to character
        if result.get('character') and result.get('body_motion'):
            print("  Applying motion...")

            motion_clip = MotionClip.load(result['body_motion'])
            animated_path = self.animated_dir / f"{name}_animated.blend"

            if apply_motion_to_blender(motion_clip, result['character'], str(animated_path)):
                result['animated'] = str(animated_path)

            # Apply anatomical motion if available
            if result.get('anatomical_motion'):
                with open(result['anatomical_motion']) as f:
                    anatomical_motion = json.load(f)

                if apply_anatomical_motion_to_blender(
                    anatomical_motion,
                    str(animated_path),
                    str(animated_path)
                ):
                    print("  Anatomical motion applied")

        # Step 5: Export for game engine
        if result.get('animated'):
            print("  Exporting...")
            export_path = self.animated_dir / f"{name}.fbx"

            subprocess.run([
                'blender', '--background', result['animated'],
                '--python-expr', f'''
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.export_scene.fbx(filepath="{export_path}", use_selection=True)
'''
            ], capture_output=True)

            result['exported'] = str(export_path)

        return result

    async def process_batch(
        self,
        video_dir: str,
        max_concurrent: int = 4,
    ) -> List[dict]:
        """Process all videos in a directory."""

        video_dir = Path(video_dir)
        videos = list(video_dir.glob("*.mp4")) + list(video_dir.glob("*.mov"))

        print(f"Found {len(videos)} videos")

        results = []

        # Process with limited concurrency
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_with_limit(video):
            async with semaphore:
                return await self.process_video(str(video))

        tasks = [process_with_limit(v) for v in videos]
        results = await asyncio.gather(*tasks)

        # Save manifest
        manifest_path = self.output_dir / "manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(results, f, indent=2)

        return results


# ============================================================================
# CLI
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Video to Motion Pipeline")
    parser.add_argument("--input", "-i", required=True, help="Input video or directory")
    parser.add_argument("--output", "-o", default="./output", help="Output directory")
    parser.add_argument("--no-character", action="store_true", help="Skip character generation")
    parser.add_argument("--no-anatomical", action="store_true", help="Skip anatomical tracking")
    parser.add_argument("--concurrent", type=int, default=4, help="Max concurrent processes")

    args = parser.parse_args()

    pipeline = MotionPipeline(output_dir=args.output)

    input_path = Path(args.input)

    if input_path.is_file():
        # Single video
        result = asyncio.run(pipeline.process_video(
            str(input_path),
            generate_character=not args.no_character,
            extract_anatomical=not args.no_anatomical,
        ))
        print(f"\nResult: {json.dumps(result, indent=2)}")
    else:
        # Directory of videos
        results = asyncio.run(pipeline.process_batch(
            str(input_path),
            max_concurrent=args.concurrent,
        ))
        print(f"\nProcessed {len(results)} videos")


if __name__ == "__main__":
    main()
