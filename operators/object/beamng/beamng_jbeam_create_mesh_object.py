import bpy
import json

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class JbeamMeshObject:
    def __init__(self, name="jbeam_mesh"):
        self.name = name
        self.obj = self.create_test_line_object()
        self.set_jbeam_attributes()
        self.create_vertex_groups()

    def get_obj(self):
        return self.obj

    def create_test_line_object(self):

        mesh = bpy.data.meshes.new(f"{self.name}_mesh")
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        vertices = [(x, 0.25 * x, 0.5 * x) for x in range(8)]
        edges = [(i, i+1) for i in range(7)]
        
        faces = []
        mesh.from_pydata(vertices, edges, faces)
        mesh.update()
        
        return obj

    def set_jbeam_attributes(self):
        j.create_attribute_node_id(self.obj)
        j.create_attribute_node_props(self.obj)

        node_ids = {i: f"n{i+1}" for i in range(8)}

        node_props = {
            i: {
                "collision": "true",
                "selfCollision": "false",
                "frictionCoef": 1.2,
                "nodeMaterial": "|NM_METAL",
                "nodeWeight": (1 + i)
            }
            for i in range(8)
        }

        for vertex_idx in range(8):
            j.set_node_id(self.obj, vertex_idx, node_ids[vertex_idx])
            j.set_node_props(self.obj, vertex_idx, node_props[vertex_idx])

    def create_vertex_groups(self):
        node_group = "flexbody_mesh"
        vertex_groups_data = {
            f'group_{node_group}': list(range(8))
        }

        for group_name, vertex_indices in vertex_groups_data.items():
            group = self.obj.vertex_groups.new(name=group_name)
            group.add(vertex_indices, 1.0, 'REPLACE')



class OBJECT_OT_create_jbeam_mesh_object(bpy.types.Operator):
    """Create a JBeam Mesh Object"""
    bl_idname = "object.devtools_beamng_create_jbeam_mesh_object"
    bl_label = "Create JBeam Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        JbeamMeshObject()
        return {'FINISHED'}

