import bpy
import random
import math

def remove_metalballs():
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.name.startswith("Mball"):
            obj.select_set(True)
    bpy.ops.object.delete()

def random_ellipsoidal_point(a, b, c):
    theta = random.uniform(0, 2 * math.pi)
    phi = random.uniform(0, math.pi)
    x = a * math.sin(phi) * math.cos(theta)
    y = b * math.sin(phi) * math.sin(theta)
    z = c * math.cos(phi)
    return (x, y, z)

def create_metaball_cloud(num_metaballs, a, b, c, min_scale, max_scale, threshold):
    for i in range(num_metaballs):
        bpy.ops.object.metaball_add(type='BALL', enter_editmode=False, align='WORLD', location=(0, 0, 0))
        metaball = bpy.context.object
        position = random_ellipsoidal_point(a, b, c)
        metaball.location = position
        scale_factor = random.uniform(min_scale, max_scale)
        metaball.scale = (scale_factor, scale_factor, scale_factor)

    for obj in bpy.context.view_layer.objects:
        if obj.type == 'META':
            obj.data.threshold = threshold

def create_capsule(radius):
    bpy.ops.object.metaball_add(type='CAPSULE', enter_editmode=False, align='WORLD', location=(0, 0, 0))
    capsule = bpy.context.object
    capsule.scale = (radius, radius, radius)

class OBJECT_OT_BeamngCreateMetaBallCloud(bpy.types.Operator):
    """Create a customizable MetaBall cloud with a capsule"""
    bl_idname = "object.devtools_beamng_create_metalball_cloud"
    bl_label = "DevTools: Create MetaBall Cloud"
    bl_options = {'REGISTER', 'UNDO'}

    num_metaballs: bpy.props.IntProperty(
        name="Number of MetaBalls",
        description="Number of MetaBalls to generate",
        default=40,
        min=1
    ) # type: ignore

    a: bpy.props.FloatProperty(
        name="Radius X",
        description="Radius along the X-axis",
        default=6.0,
        min=0.1
    ) # type: ignore

    b: bpy.props.FloatProperty(
        name="Radius Y",
        description="Radius along the Y-axis",
        default=2.5,
        min=0.1
    ) # type: ignore

    c: bpy.props.FloatProperty(
        name="Radius Z",
        description="Radius along the Z-axis",
        default=2.0,
        min=0.1
    ) # type: ignore

    min_scale: bpy.props.FloatProperty(
        name="Min Scale",
        description="Minimum scale of the MetaBalls",
        default=0.5,
        min=0.1
    ) # type: ignore

    max_scale: bpy.props.FloatProperty(
        name="Max Scale",
        description="Maximum scale of the MetaBalls",
        default=1.5,
        min=0.1
    ) # type: ignore

    threshold: bpy.props.FloatProperty(
        name="Influence Threshold",
        description="Threshold value for MetaBall blending",
        default=0.5,
        min=0.1,
        max=1.0
    ) # type: ignore

    capsule_radius: bpy.props.FloatProperty(
        name="Capsule Radius",
        description="Radius of the capsule",
        default=1.0,
        min=0.1
    ) # type: ignore

    def execute(self, context):
        if context.object and context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        remove_metalballs()
        create_metaball_cloud(
            self.num_metaballs,
            self.a,
            self.b,
            self.c,
            self.min_scale,
            self.max_scale,
            self.threshold
        )
        create_capsule(self.capsule_radius)

        return {'FINISHED'}
