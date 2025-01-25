import bpy
import random

class OBJECT_OT_CreateBonesRandomVertices(bpy.types.Operator):
    """Create bones pointing to random vertices of the selected mesh object"""
    bl_idname = "object.devtools_armature_create_bones_random_vertices"
    bl_label = "DevTools: Create Bones Pointing to Random Vertices"
    bl_options = {'REGISTER', 'UNDO'}

    num_bones: bpy.props.IntProperty(
        name="Number of Bones",
        description="Number of bones to create",
        default=10,
        min=1
    )  # type: ignore
    
    armature_name: bpy.props.StringProperty(
        name="Armature Name",
        description="Name of the generated armature",
        default="RandomArmature"
    )  # type: ignore

    seed: bpy.props.IntProperty(
        name="Random Seed",
        description="Seed for random number generation",
        default=1,
        min=0
    )  # type: ignore

    def execute(self, context):
        mesh_object = context.object

        if not mesh_object or mesh_object.type != 'MESH':
            self.report({'ERROR'}, "A valid mesh object must be selected.")
            return {'CANCELLED'}
        
        bpy.ops.object.mode_set(mode='OBJECT')
        mesh = mesh_object.data
        mesh_vertices = [v.co for v in mesh.vertices]

        if self.num_bones > len(mesh_vertices):
            self.report({'WARNING'}, f"Number of bones exceeds the number of vertices. Reducing bone count to {len(mesh_vertices)}.")
            self.num_bones = len(mesh_vertices)

        random.seed(self.seed)
        bpy.ops.object.armature_add(enter_editmode=True, location=(0, 0, 0))
        armature = context.object
        armature.name = self.armature_name

        bpy.ops.object.mode_set(mode='EDIT')
        edit_bones = armature.data.edit_bones

        for i in range(self.num_bones):
            random_vertex = random.choice(mesh_vertices)
            bone_name = f"Bone_{i+1}"
            bone = edit_bones.new(bone_name)
            bone.head = (0, 0, 0)
            bone.tail = random_vertex

        bpy.ops.object.mode_set(mode='OBJECT')
        armature.select_set(True)
        mesh_object.select_set(True)
        context.view_layer.objects.active = armature
        bpy.ops.object.parent_set(type='ARMATURE_NAME')
        
        self.report({'INFO'}, f"Created armature '{self.armature_name}' with {self.num_bones} bones pointing to random vertices.")
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'