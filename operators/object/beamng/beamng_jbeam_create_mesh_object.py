import bpy
import json

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

        self.obj.data.attributes.new("jbeam_node_id", 'STRING', 'POINT')
        self.obj.data.attributes.new("jbeam_node_props", 'STRING', 'POINT')

        node_ids = {
            0: "n1",
            1: "n2",
            2: "n3",
            3: "n4",
            4: "n5",
            5: "n6",
            6: "n7",
            7: "n8",
        }

        scope_modifiers = {"collision": "true", "selfCollision": "false", "frictionCoef": 1.2, "nodeMaterial": "|NM_METAL", "nodeWeight": "5"},

        node_props = {
            0: scope_modifiers,
            1: scope_modifiers,
            2: scope_modifiers,
            3: scope_modifiers,
            4: scope_modifiers,
            5: scope_modifiers,
            6: scope_modifiers,
            7: scope_modifiers,
        }

        for vertex_idx in range(8):
            self.obj.data.attributes['jbeam_node_id'].data[vertex_idx].value = node_ids.get(vertex_idx, "").encode('utf-8') 
            self.obj.data.attributes['jbeam_node_props'].data[vertex_idx].value = json.dumps(node_props.get(vertex_idx, {})).encode('utf-8')

    def create_vertex_groups(self):
        node_group = "flexbody_mesh"
        vertex_groups_data = {
            f'group_{node_group}': [0, 1, 2, 3, 4, 5, 6, 7],
        }
        for group_name, vertex_indices in vertex_groups_data.items():
            group = self.obj.vertex_groups.new(name=group_name)
            for vertex_index in vertex_indices:
                group.add([vertex_index], 1.0, 'REPLACE')


class OBJECT_OT_create_jbeam_mesh_object(bpy.types.Operator):
    """Create a JBeam Mesh Object"""
    bl_idname = "object.devtools_beamng_create_jbeam_mesh_object"
    bl_label = "Create JBeam Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        JbeamMeshObject()
        return {'FINISHED'}

