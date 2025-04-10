import bpy
import json

from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore

class OBJECT_OT_BeamngConvertJbeamToNodeMesh(Operator):
    """Convert object to Node Mesh by removing custom properties and merging by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_node_mesh"
    bl_label = "DevTools: Convert JBeam to Mesh Object (v2)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj:
            self.report({'WARNING'}, "No mesh object selected!")
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        if obj.type == 'CURVE':
            bpy.ops.object.convert(target='MESH')
        elif j.is_node_mesh(obj):
            j.add_gn_jbeam_visualizer_modifier(obj)
            self.report({'INFO'}, "Object is already a Node Mesh")
            return {'CANCELLED'}
        elif obj.type != 'MESH':
            self.report({'WARNING'}, f"{repr(obj)} is not a mesh or curve object!")
            return {'CANCELLED'}

        jbeam_path = obj.data.get('jbeam_file_path', None)
        is_jbeam_part = bool(jbeam_path)  # flag to check if the jbeam part object is an import from the original jbeam editor from BeamNG team

        if not jbeam_path:
            self.report({'WARNING'}, "Object is not a JBeam part or missing JBeam file path! Proceeding with regular conversion..")

        JbeamNodeMeshConfigurator.remove_custom_data_props(obj)
        JbeamNodeMeshConfigurator.remove_double_vertices(obj)

        if is_jbeam_part:
            self.setup_jbeam_part(obj, jbeam_path)
        else:
            self.setup_jbeam_blender_mesh(obj)

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Converted {obj.name} to Node Mesh!")
        return {'FINISHED'}

    def setup_jbeam_blender_mesh(self, obj):
        j.setup_default_scope_modifiers_and_node_ids(obj)
        JbeamNodeMeshConfigurator.process_node_mesh_props(obj)

    def setup_jbeam_part(self, obj, jbeam_path):
        self.parser = JbeamParser()
        try:
            self.parser.load_jbeam(jbeam_path)
            self.parser.parse_data_for_jbeam_object_conversion(obj)
        except Exception as e:
            self.report({'ERROR'}, f"Failed to read file: {e}")
            return {'CANCELLED'}

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, self.parser)