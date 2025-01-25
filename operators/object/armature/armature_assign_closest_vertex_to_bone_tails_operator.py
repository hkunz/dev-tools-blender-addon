import bpy
import bmesh

from dev_tools.utils.object_utils import ObjectUtils # type: ignore

# Run operator OBJECT_OT_ArmatureCreateBonesFromEdgeSelection
# Select Mesh and Armature as active and run operator
# Now when you animate the mesh (i.e. cloth sim), the armature pose will follow vertices
# Duplicate Mesh & Armature then select Armature go into Pose mode then Pose > Animation > Bake Action... tick "Visual Keying" & "Clear Constraints"
# Now you can remove the animations of the mesh (i.e remove cloth sim)
# Select Mesh and Armature > Ctrl + P > Armature Deform With Automatic Weights
# Optionally add additional bones and assign vertices (vertex groups must be same name as bone) if you want to pin some vertices

class OBJECT_OT_ArmatureAssignClosestVertexToBoneTails(bpy.types.Operator):
    """Assign Closest Vertex to Armature Bone Tails stored in vertex groups"""
    bl_idname = "object.devtools_armature_assign_closest_vertex_to_bone_tails"
    bl_label = "DevTools: Assign Closest Vertex to Armature Bone Tails"

    @staticmethod
    def find_closest_vertex_to_bone(mesh_obj, position):
        """Find the closest vertex in the mesh to the given position."""
        mesh = mesh_obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()

        closest_index = None
        closest_distance = float("inf")

        for vert in bm.verts:
            dist = (vert.co - position).length
            if dist < closest_distance:
                closest_distance = dist
                closest_index = vert.index

        bm.free()
        return closest_index

    @staticmethod
    def create_vertex_group(obj, vertex_id, bone_name):
        grps = obj.vertex_groups

        existing = grps.get(bone_name)
        if existing:
            grps.remove(existing)

        vertex_group = grps.new(name=bone_name)
        vertex_group.add([vertex_id], 1.0, 'REPLACE')


    @staticmethod
    def add_damped_track_to_bone(armature_obj, bone_name, target_obj):
        bpy.context.view_layer.objects.active = armature_obj
        armature_obj.select_set(True)
        bpy.ops.object.mode_set(mode='POSE')  # Switch to POSE mode
        
        pose_bone = armature_obj.pose.bones.get(bone_name)
        if not pose_bone:
            return

        for constraint in pose_bone.constraints:
            if constraint.type == 'DAMPED_TRACK':
                pose_bone.constraints.remove(constraint)
                print(f"Removed existing Damped Track constraint from bone '{pose_bone.name}'")

        vertex_group = pose_bone.name
        constraint = pose_bone.constraints.new(type='DAMPED_TRACK')
        constraint.name = "Damped Track"
        constraint.target = target_obj
        constraint.subtarget = vertex_group
        constraint.track_axis = 'TRACK_Y'  # Options: 'TRACK_X', 'TRACK_Y', 'TRACK_Z', etc.
        print(f"Damped Track constraint added to bone '{pose_bone.name}'")


    def execute(self, context):
        if len(context.selected_objects) != 2:
            self.report({'WARNING'}, "Selected one Armature and one Mesh object")
            return {'CANCELLED'}

        armature_obj = context.view_layer.objects.active
        if armature_obj.type != 'ARMATURE':
            self.report({'WARNING'}, "Active object must be an Armature.")
            return {'CANCELLED'}

        mesh_obj = next((obj for obj in context.selected_objects if obj != armature_obj and obj.type == 'MESH'), None)
        if not mesh_obj:
            self.report({'WARNING'}, "The second selected object must be a mesh.")
            return {'CANCELLED'}

        if not ObjectUtils.check_origin_at_world_origin(context.selected_objects):
            self.report({'WARNING'}, "Objects must have origin at World Origin")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='EDIT')
        armature = armature_obj.data

        for bone in armature.edit_bones:
            closest_vertex = self.find_closest_vertex_to_bone(mesh_obj, bone.tail)
            print(f"{bone.name} > closest vertex is {closest_vertex}")
            self.create_vertex_group(mesh_obj, closest_vertex, bone.name)

        bpy.ops.object.mode_set(mode='POSE')
        for bone in armature_obj.pose.bones:
            self.add_damped_track_to_bone(armature_obj, bone.name, mesh_obj)

        bpy.ops.object.mode_set(mode='OBJECT')
        mesh_obj.select_set(True)
        armature_obj.select_set(True)
        context.view_layer.objects.active = armature_obj
        
        return {'FINISHED'}

    @classmethod
    def poll(cls, context):
        return context.object and context.object.type == 'MESH'