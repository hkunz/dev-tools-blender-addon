import bpy

from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j
from unofficial_jbeam_editor.utils.jbeam.jbeam_props_storage import JbeamPropsStorageManager

class JbeamNodeMesh:
    def __init__(self, name="NodeMesh"):
        self.name = name
        self.obj = None

    def create(self):
        self.obj = self.create_triangulated_cube()
        self.setup()
        self.set_jbeam_attributes()
        return self.obj

    def setup(self):
        j.set_jbeam_visuals(self.obj)
        j.add_gn_jbeam_visualizer_modifier(self.obj)
        JbeamPropsStorageManager.get_instance().register_object(self.obj)

    def get_obj(self):
        return self.obj

    def create_triangulated_cube(self):
        mesh = bpy.data.meshes.new(f"{self.name}_mesh")
        obj = bpy.data.objects.new(self.name, mesh)
        bpy.context.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        vertices = [
            (-0.25, -0.25, -0.25), (0.25, -0.25, -0.25), (0.25, 0.25, -0.25), (-0.25, 0.25, -0.25),
            (-0.25, -0.25, 0.25), (0.25, -0.25, 0.25), (0.25, 0.25, 0.25), (-0.25, 0.25, 0.25)
        ]

        faces = [
            (0, 3, 2), (2, 1, 0),  # Bottom
            (4, 5, 6), (6, 7, 4),  # Top
            (0, 1, 5), (5, 4, 0),  # Front
            (2, 3, 7), (7, 6, 2),  # Back
            (0, 7, 3), (7, 0, 4),  # Left 
            (1, 2, 6), (6, 5, 1)   # Right
        ]

        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        return obj

    def set_jbeam_attributes(self):
        j.setup_default_scope_modifiers_and_node_ids(self.obj)
        

class OBJECT_OT_BeamngJbeamCreateNodeMesh(bpy.types.Operator):
    """Create a JBeam Node Mesh Object"""
    bl_idname = "object.devtools_beamng_jbeam_create_node_mesh"
    bl_label = "Create JBeam Node Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        nm = JbeamNodeMesh()
        obj = nm.create()
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        return {'FINISHED'}
