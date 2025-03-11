import bpy
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore

class JbeamMeshObject:
    def __init__(self, name="jbeam_mesh"):
        self.name = name
        self.obj = self.create_triangulated_cube()
        self.setup()
        self.set_jbeam_attributes()
        self.create_vertex_groups()

    def setup(self):
        j.set_jbeam_visuals(self.obj)
        j.add_gn_jbeam_visualizer_modifier(self.obj)

    def get_obj(self):
        return self.obj

    def create_triangulated_cube(self):
        mesh = bpy.data.meshes.new(f"{self.name}_mesh")
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        vertices = [
            (-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
            (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)
        ]

        faces = [
            (0, 3, 2), (2, 1, 0),  # Bottom
            (4, 5, 6), (6, 7, 4),  # Top
            (0, 1, 5), (5, 4, 0),  # Front
            (2, 3, 7), (7, 6, 2),  # Back
            (0, 3, 7), (7, 4, 0),  # Left
            (1, 2, 6), (6, 5, 1)   # Right
        ]

        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        return obj

    def set_jbeam_attributes(self):
        j.setup_default_scope_modifiers_and_node_ids(self.obj)
        
    def create_vertex_groups(self):
        node_group = "flexbody_mesh"
        vertex_groups_data = {
            f'group_{node_group}': list(range(8))
        }

        for group_name, vertex_indices in vertex_groups_data.items():
            group = self.obj.vertex_groups.new(name=group_name)
            group.add(vertex_indices, 1.0, 'REPLACE')
        
        bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()


class OBJECT_OT_create_jbeam_mesh_object(bpy.types.Operator):
    """Create a JBeam Mesh Object"""
    bl_idname = "object.devtools_beamng_create_jbeam_mesh_object"
    bl_label = "Create JBeam Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        JbeamMeshObject()
        return {'FINISHED'}
