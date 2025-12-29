"""
SAM Character Factory - Blender Addon
Fully automated anatomically-correct character generation with physics.

Installation:
1. Zip this folder
2. Blender → Edit → Preferences → Add-ons → Install
3. Enable "SAM Character Factory"

Or run headless:
blender --background --python -m sam_character_factory -- --count 100
"""

bl_info = {
    "name": "SAM Character Factory",
    "author": "SAM AI",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > SAM",
    "description": "Automated anatomically-correct character generation with physics",
    "category": "Character",
}

import bpy
from bpy.props import (
    FloatProperty, IntProperty, BoolProperty,
    StringProperty, EnumProperty, FloatVectorProperty
)
from bpy.types import Panel, Operator, PropertyGroup

import json
import random
import math
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================================
# PROPERTY GROUPS
# ============================================================================

class SAMBodyProperties(PropertyGroup):
    """Body shape parameters."""

    height: FloatProperty(
        name="Height",
        description="Character height multiplier",
        default=1.0, min=0.85, max=1.15
    )
    weight: FloatProperty(
        name="Weight",
        description="Body mass",
        default=1.0, min=0.7, max=1.3
    )
    musculature: FloatProperty(
        name="Musculature",
        description="Muscle definition",
        default=0.5, min=0.0, max=1.0
    )
    body_fat: FloatProperty(
        name="Body Fat",
        description="Body fat percentage appearance",
        default=0.2, min=0.0, max=0.5
    )
    shoulder_width: FloatProperty(
        name="Shoulder Width",
        default=1.0, min=0.85, max=1.15
    )
    hip_width: FloatProperty(
        name="Hip Width",
        default=1.0, min=0.9, max=1.1
    )
    age: IntProperty(
        name="Age Appearance",
        default=30, min=20, max=55
    )
    skin_tone: FloatProperty(
        name="Skin Tone",
        description="0=light, 1=dark",
        default=0.5, min=0.0, max=1.0
    )
    body_hair: FloatProperty(
        name="Body Hair",
        default=0.3, min=0.0, max=1.0
    )


class SAMAnatomyProperties(PropertyGroup):
    """Anatomical parameters."""

    length: FloatProperty(
        name="Length",
        default=1.0, min=0.6, max=1.4
    )
    girth: FloatProperty(
        name="Girth",
        default=1.0, min=0.7, max=1.3
    )
    curvature: FloatProperty(
        name="Curvature",
        default=0.0, min=-0.3, max=0.3
    )
    circumcised: BoolProperty(
        name="Circumcised",
        default=False
    )
    testicle_size: FloatProperty(
        name="Testicle Size",
        default=1.0, min=0.7, max=1.3
    )
    testicle_hang: FloatProperty(
        name="Testicle Hang",
        default=0.5, min=0.2, max=0.8
    )


class SAMPhysicsProperties(PropertyGroup):
    """Physics simulation parameters."""

    enabled: BoolProperty(
        name="Enable Physics",
        default=True
    )
    mass: FloatProperty(
        name="Mass",
        default=0.3, min=0.1, max=1.0
    )
    stiffness: FloatProperty(
        name="Stiffness",
        default=0.5, min=0.1, max=0.9
    )
    damping: FloatProperty(
        name="Damping",
        default=0.5, min=0.0, max=1.0
    )
    gravity_influence: FloatProperty(
        name="Gravity",
        default=1.0, min=0.0, max=2.0
    )


class SAMGeneratorProperties(PropertyGroup):
    """Main generator properties."""

    body: bpy.props.PointerProperty(type=SAMBodyProperties)
    anatomy: bpy.props.PointerProperty(type=SAMAnatomyProperties)
    physics: bpy.props.PointerProperty(type=SAMPhysicsProperties)

    output_path: StringProperty(
        name="Output Path",
        default="//generated_characters/",
        subtype='DIR_PATH'
    )
    export_format: EnumProperty(
        name="Format",
        items=[
            ('FBX', 'FBX', 'Export as FBX'),
            ('GLTF', 'glTF', 'Export as glTF/GLB'),
            ('BLEND', 'Blend', 'Save as .blend'),
        ],
        default='FBX'
    )
    include_rig: BoolProperty(
        name="Include Rig",
        default=True
    )
    batch_count: IntProperty(
        name="Batch Count",
        default=10, min=1, max=1000
    )
    randomize: BoolProperty(
        name="Randomize",
        description="Use random parameters",
        default=True
    )


# ============================================================================
# CHARACTER GENERATOR CORE
# ============================================================================

class CharacterGenerator:
    """Core character generation logic."""

    def __init__(self, context):
        self.context = context
        self.props = context.scene.sam_generator

    def generate(self, name: str = None) -> dict:
        """Generate a complete character."""

        if name is None:
            name = f"SAM_Character_{random.randint(10000, 99999)}"

        # Clear scene
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete()

        # Get parameters
        params = self._get_params()

        # Generate components
        body = self._create_body(params)
        anatomy = self._create_anatomy(params)

        # Attach anatomy to body
        self._attach_anatomy(body, anatomy)

        # Apply materials
        self._apply_skin_material(body, params)
        self._apply_skin_material(anatomy, params, is_anatomy=True)

        # Create shape keys for states
        self._create_shape_keys(body, anatomy, params)

        # Rig
        armature = None
        if self.props.include_rig:
            armature = self._create_rig(body, anatomy)
            self._setup_drivers(armature, body, anatomy)

        # Physics
        if self.props.physics.enabled:
            self._setup_physics(anatomy, params)

        # Organize
        self._organize_hierarchy(body, anatomy, armature, name)

        return {
            'name': name,
            'params': params,
            'objects': {
                'body': body.name,
                'anatomy': anatomy.name,
                'armature': armature.name if armature else None
            }
        }

    def _get_params(self) -> dict:
        """Get parameters from UI or randomize."""
        if self.props.randomize:
            return self._randomize_params()

        return {
            # Body
            'height': self.props.body.height,
            'weight': self.props.body.weight,
            'musculature': self.props.body.musculature,
            'body_fat': self.props.body.body_fat,
            'shoulder_width': self.props.body.shoulder_width,
            'hip_width': self.props.body.hip_width,
            'age': self.props.body.age,
            'skin_tone': self.props.body.skin_tone,
            'body_hair': self.props.body.body_hair,
            # Anatomy
            'genital_length': self.props.anatomy.length,
            'genital_girth': self.props.anatomy.girth,
            'genital_curvature': self.props.anatomy.curvature,
            'circumcised': self.props.anatomy.circumcised,
            'testicle_size': self.props.anatomy.testicle_size,
            'testicle_hang': self.props.anatomy.testicle_hang,
            # Physics
            'physics_mass': self.props.physics.mass,
            'physics_stiffness': self.props.physics.stiffness,
            'physics_damping': self.props.physics.damping,
        }

    def _randomize_params(self) -> dict:
        """Generate random parameters."""
        return {
            'height': random.uniform(0.85, 1.15),
            'weight': random.uniform(0.7, 1.3),
            'musculature': random.uniform(0.0, 1.0),
            'body_fat': random.uniform(0.0, 0.5),
            'shoulder_width': random.uniform(0.85, 1.15),
            'hip_width': random.uniform(0.9, 1.1),
            'age': random.randint(20, 55),
            'skin_tone': random.uniform(0.0, 1.0),
            'body_hair': random.uniform(0.0, 1.0),
            'genital_length': random.uniform(0.6, 1.4),
            'genital_girth': random.uniform(0.7, 1.3),
            'genital_curvature': random.uniform(-0.2, 0.2),
            'circumcised': random.choice([True, False]),
            'testicle_size': random.uniform(0.8, 1.2),
            'testicle_hang': random.uniform(0.3, 0.7),
            'physics_mass': 0.3,
            'physics_stiffness': 0.5,
            'physics_damping': 0.5,
        }

    def _create_body(self, params: dict):
        """Create base body mesh."""
        # Try MakeHuman/MPFB2 first
        if hasattr(bpy.ops, 'mpfb') and hasattr(bpy.ops.mpfb, 'create_human'):
            try:
                bpy.ops.mpfb.create_human()
                body = self.context.active_object
                body.name = "Body"
                return body
            except:
                pass

        # Fallback: Create procedural body
        # Start with a subdivided cube, sculpt into body shape
        bpy.ops.mesh.primitive_cube_add(size=2)
        body = self.context.active_object
        body.name = "Body"

        # Add subdivision
        subsurf = body.modifiers.new("Subdivision", 'SUBSURF')
        subsurf.levels = 2
        subsurf.render_levels = 3

        # Apply basic body proportions
        body.scale = (
            0.4 * params['shoulder_width'],
            0.25 * params['weight'],
            1.0 * params['height']
        )
        bpy.ops.object.transform_apply(scale=True)

        return body

    def _create_anatomy(self, params: dict):
        """Create anatomical geometry."""
        objects = []

        length = params['genital_length']
        girth = params['genital_girth']

        # Shaft
        bpy.ops.mesh.primitive_cylinder_add(
            radius=0.015 * girth,
            depth=0.12 * length,
            vertices=32,
            end_fill_type='NGON'
        )
        shaft = self.context.active_object
        shaft.name = "Shaft"
        objects.append(shaft)

        # Add loop cuts for deformation
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.subdivide(number_cuts=8)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Glans
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.02 * girth,
            segments=32,
            ring_count=16
        )
        glans = self.context.active_object
        glans.name = "Glans"
        glans.scale = (1.0, 0.8, 1.2)
        glans.location.z = 0.06 * length
        bpy.ops.object.transform_apply(scale=True)
        objects.append(glans)

        # Foreskin (if not circumcised)
        if not params['circumcised']:
            bpy.ops.mesh.primitive_cylinder_add(
                radius=0.018 * girth,
                depth=0.025,
                vertices=32
            )
            foreskin = self.context.active_object
            foreskin.name = "Foreskin"
            foreskin.location.z = 0.05 * length
            objects.append(foreskin)

        # Scrotum
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.035 * params['testicle_size'],
            segments=24,
            ring_count=12
        )
        scrotum = self.context.active_object
        scrotum.name = "Scrotum"
        scrotum.scale = (1.2, 0.8, 1.0 + params['testicle_hang'] * 0.3)
        scrotum.location = (0, 0.01, -0.05)
        bpy.ops.object.transform_apply(scale=True)
        objects.append(scrotum)

        # Left testicle
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.015 * params['testicle_size'],
            segments=16,
            ring_count=8
        )
        left_testicle = self.context.active_object
        left_testicle.name = "Testicle_L"
        left_testicle.location = (-0.012, 0.005, -0.055 - params['testicle_hang'] * 0.02)
        objects.append(left_testicle)

        # Right testicle
        bpy.ops.mesh.primitive_uv_sphere_add(
            radius=0.015 * params['testicle_size'],
            segments=16,
            ring_count=8
        )
        right_testicle = self.context.active_object
        right_testicle.name = "Testicle_R"
        right_testicle.location = (0.012, 0.005, -0.055 - params['testicle_hang'] * 0.02)
        objects.append(right_testicle)

        # Join all parts
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        self.context.view_layer.objects.active = shaft
        bpy.ops.object.join()

        anatomy = self.context.active_object
        anatomy.name = "Anatomy"

        # Smooth shading
        bpy.ops.object.shade_smooth()

        # Add subdivision for smoothness
        subsurf = anatomy.modifiers.new("Subdivision", 'SUBSURF')
        subsurf.levels = 1
        subsurf.render_levels = 2

        return anatomy

    def _attach_anatomy(self, body, anatomy):
        """Position and attach anatomy to body."""
        # Position at pelvis
        anatomy.location = (0, -0.05, 0.95)
        anatomy.rotation_euler = (math.radians(-80), 0, 0)

        # Parent (but don't merge)
        anatomy.parent = body
        anatomy.matrix_parent_inverse = body.matrix_world.inverted()

    def _apply_skin_material(self, obj, params: dict, is_anatomy: bool = False):
        """Apply procedural skin material."""
        mat_name = "Skin_Anatomy" if is_anatomy else "Skin"
        mat = bpy.data.materials.get(mat_name)

        if mat is None:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True

            nodes = mat.node_tree.nodes
            links = mat.node_tree.links
            nodes.clear()

            # Principled BSDF
            bsdf = nodes.new('ShaderNodeBsdfPrincipled')
            bsdf.location = (0, 0)

            # Skin tone
            tone = params['skin_tone']
            if is_anatomy:
                # Slightly darker/more saturated for anatomy
                base_color = (
                    0.7 - tone * 0.4,
                    0.45 - tone * 0.3,
                    0.4 - tone * 0.25,
                    1.0
                )
            else:
                base_color = (
                    0.8 - tone * 0.5,
                    0.6 - tone * 0.4,
                    0.5 - tone * 0.35,
                    1.0
                )

            bsdf.inputs["Base Color"].default_value = base_color
            bsdf.inputs["Subsurface Weight"].default_value = 0.3
            bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.2, 0.1)
            bsdf.inputs["Roughness"].default_value = 0.4
            bsdf.inputs["Specular IOR Level"].default_value = 0.5

            # Output
            output = nodes.new('ShaderNodeOutputMaterial')
            output.location = (300, 0)
            links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        # Assign material
        if obj.data.materials:
            obj.data.materials[0] = mat
        else:
            obj.data.materials.append(mat)

    def _create_shape_keys(self, body, anatomy, params: dict):
        """Create shape keys for animation states."""
        # Anatomy shape keys
        if not anatomy.data.shape_keys:
            anatomy.shape_key_add(name="Basis")

        # Erect state
        sk_erect = anatomy.shape_key_add(name="Erect")

        # Modify vertices for erect shape
        basis = anatomy.data.shape_keys.key_blocks["Basis"]
        erect = anatomy.data.shape_keys.key_blocks["Erect"]

        for i, vert in enumerate(anatomy.data.vertices):
            # Raise and straighten
            basis_co = basis.data[i].co
            new_co = basis_co.copy()

            # Straighten (reduce droop)
            if basis_co.z > -0.03:  # Shaft vertices
                new_co.z += 0.02
                new_co.y -= 0.02

            erect.data[i].co = new_co

        # Size variations
        anatomy.shape_key_add(name="Size_Large")
        anatomy.shape_key_add(name="Size_Small")

        # Temperature (affects hang)
        anatomy.shape_key_add(name="Cold")
        anatomy.shape_key_add(name="Warm")

    def _create_rig(self, body, anatomy):
        """Create armature with custom bones."""
        # Create armature
        bpy.ops.object.armature_add(enter_editmode=True)
        armature_obj = self.context.active_object
        armature_obj.name = "Armature"
        armature = armature_obj.data
        armature.name = "Armature"

        # Remove default bone
        for bone in armature.edit_bones:
            armature.edit_bones.remove(bone)

        # Root bone
        root = armature.edit_bones.new("Root")
        root.head = (0, 0, 0)
        root.tail = (0, 0, 0.1)

        # Pelvis
        pelvis = armature.edit_bones.new("Pelvis")
        pelvis.head = (0, 0, 0.95)
        pelvis.tail = (0, 0, 1.0)
        pelvis.parent = root

        # Anatomy control bone
        anatomy_ctrl = armature.edit_bones.new("Anatomy_Control")
        anatomy_ctrl.head = (0, -0.05, 0.95)
        anatomy_ctrl.tail = (0, -0.05, 0.98)
        anatomy_ctrl.parent = pelvis

        # Anatomy bone chain (for physics/deformation)
        parent_bone = anatomy_ctrl
        for i in range(6):
            bone = armature.edit_bones.new(f"Anatomy_{i}")
            z_offset = 0.95 - i * 0.015
            bone.head = (0, -0.05 - i * 0.005, z_offset)
            bone.tail = (0, -0.05 - (i+1) * 0.005, z_offset - 0.015)
            bone.parent = parent_bone
            parent_bone = bone

        # Testicle bones
        for side, x in [("L", -0.012), ("R", 0.012)]:
            bone = armature.edit_bones.new(f"Testicle_{side}")
            bone.head = (x, 0.005, 0.895)
            bone.tail = (x, 0.005, 0.88)
            bone.parent = pelvis

        bpy.ops.object.mode_set(mode='OBJECT')

        # Add custom properties for control
        armature_obj["arousal"] = 0.0
        armature_obj["temperature"] = 0.5
        armature_obj["physics_enabled"] = True

        # Make properties animatable
        armature_obj.id_properties_ensure()
        for prop in ["arousal", "temperature"]:
            ui = armature_obj.id_properties_ui(prop)
            ui.update(min=0.0, max=1.0, soft_min=0.0, soft_max=1.0)

        # Parent meshes to armature
        for obj in [body, anatomy]:
            obj.select_set(True)
        self.context.view_layer.objects.active = armature_obj
        bpy.ops.object.parent_set(type='ARMATURE_AUTO')

        return armature_obj

    def _setup_drivers(self, armature, body, anatomy):
        """Set up drivers for animation control."""
        if not anatomy.data.shape_keys:
            return

        # Driver: arousal → Erect shape key
        erect_key = anatomy.data.shape_keys.key_blocks.get("Erect")
        if erect_key:
            driver = erect_key.driver_add("value").driver
            driver.type = 'AVERAGE'

            var = driver.variables.new()
            var.name = "arousal"
            var.type = 'SINGLE_PROP'
            var.targets[0].id = armature
            var.targets[0].data_path = '["arousal"]'

    def _setup_physics(self, anatomy, params: dict):
        """Set up soft body physics."""
        self.context.view_layer.objects.active = anatomy

        # Create vertex group for stiffness variation
        vg = anatomy.vertex_groups.new(name="Physics_Weight")

        # Weight vertices by position (base = stiff, tip = loose)
        for vert in anatomy.data.vertices:
            # Higher weight = more affected by goal (stiffer)
            # Base of anatomy should be stiff, tip should be loose
            z = vert.co.z
            if z > 0:  # Shaft
                weight = 1.0 - (z / 0.1)  # Tip is looser
            else:  # Scrotum
                weight = 0.3  # Always somewhat loose

            weight = max(0.1, min(1.0, weight))
            vg.add([vert.index], weight, 'REPLACE')

        # Add soft body modifier
        softbody = anatomy.modifiers.new("SoftBody", 'SOFT_BODY')

        sb = anatomy.soft_body
        sb.mass = params.get('physics_mass', 0.3)
        sb.friction = 0.5

        # Goal settings (shape retention)
        sb.goal_spring = params.get('physics_stiffness', 0.5)
        sb.goal_friction = params.get('physics_damping', 0.5)
        sb.vertex_group_goal = "Physics_Weight"

        # Edge settings (volume preservation)
        sb.use_edges = True
        sb.pull = 0.5
        sb.push = 0.5

        # Self collision
        sb.use_self_collision = True
        sb.ball_size = 0.02
        sb.ball_stiff = 1.0

    def _organize_hierarchy(self, body, anatomy, armature, name: str):
        """Organize objects into collection."""
        # Create collection
        collection = bpy.data.collections.new(name)
        self.context.scene.collection.children.link(collection)

        # Move objects to collection
        for obj in [body, anatomy]:
            if obj.name in self.context.scene.collection.objects:
                self.context.scene.collection.objects.unlink(obj)
            collection.objects.link(obj)

        if armature:
            if armature.name in self.context.scene.collection.objects:
                self.context.scene.collection.objects.unlink(armature)
            collection.objects.link(armature)

    def export(self, name: str, filepath: str = None):
        """Export character."""
        if filepath is None:
            output_dir = bpy.path.abspath(self.props.output_path)
            os.makedirs(output_dir, exist_ok=True)

            ext = {'FBX': 'fbx', 'GLTF': 'glb', 'BLEND': 'blend'}[self.props.export_format]
            filepath = os.path.join(output_dir, f"{name}.{ext}")

        bpy.ops.object.select_all(action='SELECT')

        if self.props.export_format == 'FBX':
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                add_leaf_bones=False,
                bake_anim=False,
                mesh_smooth_type='FACE',
            )
        elif self.props.export_format == 'GLTF':
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                use_selection=True,
                export_format='GLB',
            )
        elif self.props.export_format == 'BLEND':
            bpy.ops.wm.save_as_mainfile(filepath=filepath, copy=True)

        return filepath


# ============================================================================
# OPERATORS
# ============================================================================

class ATLAS_OT_generate_character(Operator):
    """Generate a single character"""
    bl_idname = "sam.generate_character"
    bl_label = "Generate Character"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        generator = CharacterGenerator(context)
        result = generator.generate()

        self.report({'INFO'}, f"Generated: {result['name']}")
        return {'FINISHED'}


class ATLAS_OT_generate_batch(Operator):
    """Generate multiple characters"""
    bl_idname = "sam.generate_batch"
    bl_label = "Generate Batch"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.sam_generator
        generator = CharacterGenerator(context)

        results = []
        for i in range(props.batch_count):
            result = generator.generate()
            filepath = generator.export(result['name'])
            result['filepath'] = filepath
            results.append(result)

            self.report({'INFO'}, f"Generated {i+1}/{props.batch_count}")

        # Save manifest
        output_dir = bpy.path.abspath(props.output_path)
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        self.report({'INFO'}, f"Generated {len(results)} characters")
        return {'FINISHED'}


class ATLAS_OT_export_character(Operator):
    """Export current character"""
    bl_idname = "sam.export_character"
    bl_label = "Export Character"

    def execute(self, context):
        generator = CharacterGenerator(context)
        filepath = generator.export("exported_character")

        self.report({'INFO'}, f"Exported to: {filepath}")
        return {'FINISHED'}


class ATLAS_OT_randomize(Operator):
    """Randomize all parameters"""
    bl_idname = "sam.randomize"
    bl_label = "Randomize"

    def execute(self, context):
        props = context.scene.sam_generator

        # Body
        props.body.height = random.uniform(0.85, 1.15)
        props.body.weight = random.uniform(0.7, 1.3)
        props.body.musculature = random.uniform(0.0, 1.0)
        props.body.body_fat = random.uniform(0.0, 0.5)
        props.body.skin_tone = random.uniform(0.0, 1.0)

        # Anatomy
        props.anatomy.length = random.uniform(0.6, 1.4)
        props.anatomy.girth = random.uniform(0.7, 1.3)
        props.anatomy.circumcised = random.choice([True, False])

        return {'FINISHED'}


# ============================================================================
# PANELS
# ============================================================================

class ATLAS_PT_main_panel(Panel):
    """Main SAM panel"""
    bl_label = "SAM Character Factory"
    bl_idname = "ATLAS_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SAM'

    def draw(self, context):
        layout = self.layout
        props = context.scene.sam_generator

        # Generate buttons
        box = layout.box()
        box.label(text="Generate", icon='OUTLINER_OB_ARMATURE')

        row = box.row()
        row.prop(props, "randomize")
        row.operator("sam.randomize", text="", icon='FILE_REFRESH')

        box.operator("sam.generate_character", icon='ADD')

        row = box.row()
        row.prop(props, "batch_count")
        row.operator("sam.generate_batch", text="Batch", icon='DUPLICATE')


class ATLAS_PT_body_panel(Panel):
    """Body parameters panel"""
    bl_label = "Body"
    bl_idname = "ATLAS_PT_body"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SAM'
    bl_parent_id = "ATLAS_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        body = context.scene.sam_generator.body

        layout.prop(body, "height")
        layout.prop(body, "weight")
        layout.prop(body, "musculature")
        layout.prop(body, "body_fat")
        layout.prop(body, "shoulder_width")
        layout.prop(body, "age")
        layout.prop(body, "skin_tone")


class ATLAS_PT_anatomy_panel(Panel):
    """Anatomy parameters panel"""
    bl_label = "Anatomy"
    bl_idname = "ATLAS_PT_anatomy"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SAM'
    bl_parent_id = "ATLAS_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        anatomy = context.scene.sam_generator.anatomy

        layout.prop(anatomy, "length")
        layout.prop(anatomy, "girth")
        layout.prop(anatomy, "curvature")
        layout.prop(anatomy, "circumcised")
        layout.prop(anatomy, "testicle_size")
        layout.prop(anatomy, "testicle_hang")


class ATLAS_PT_physics_panel(Panel):
    """Physics parameters panel"""
    bl_label = "Physics"
    bl_idname = "ATLAS_PT_physics"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SAM'
    bl_parent_id = "ATLAS_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        physics = context.scene.sam_generator.physics

        layout.prop(physics, "enabled")

        if physics.enabled:
            layout.prop(physics, "mass")
            layout.prop(physics, "stiffness")
            layout.prop(physics, "damping")


class ATLAS_PT_export_panel(Panel):
    """Export panel"""
    bl_label = "Export"
    bl_idname = "ATLAS_PT_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'SAM'
    bl_parent_id = "ATLAS_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.sam_generator

        layout.prop(props, "output_path")
        layout.prop(props, "export_format")
        layout.prop(props, "include_rig")

        layout.operator("sam.export_character", icon='EXPORT')


# ============================================================================
# REGISTRATION
# ============================================================================

classes = [
    SAMBodyProperties,
    SAMAnatomyProperties,
    SAMPhysicsProperties,
    SAMGeneratorProperties,
    ATLAS_OT_generate_character,
    ATLAS_OT_generate_batch,
    ATLAS_OT_export_character,
    ATLAS_OT_randomize,
    ATLAS_PT_main_panel,
    ATLAS_PT_body_panel,
    ATLAS_PT_anatomy_panel,
    ATLAS_PT_physics_panel,
    ATLAS_PT_export_panel,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Scene.sam_generator = bpy.props.PointerProperty(type=SAMGeneratorProperties)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

    del bpy.types.Scene.sam_generator


if __name__ == "__main__":
    register()
