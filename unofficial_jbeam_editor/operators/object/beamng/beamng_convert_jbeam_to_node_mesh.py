import bpy
import json

from pprint import pprint
from bpy.types import Operator

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator
from unofficial_jbeam_editor.utils.jbeam.jbeam_props_storage import JbeamPropsStorageManager
from unofficial_jbeam_editor.utils.jbeam.jbeam_parser import JbeamParser

# deprecated operator, used to convert a jbeam object mesh generated by BeamNG's Jbeam Editor into this addon's Node Mesh
class OBJECT_OT_BeamngConvertJbeamToNodeMesh(Operator):
    """Convert object to Node Mesh by removing custom properties and merging by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_node_mesh"
    bl_label = "DevTools: Convert JBeam to Mesh Object (v2)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object

        if not obj:
            Utils.log_and_report("No mesh object selected!", self, 'WARNING')
            return {'CANCELLED'}

        bpy.ops.object.mode_set(mode='OBJECT')
        if obj.type == 'CURVE':
            bpy.ops.object.convert(target='MESH')
        elif j.is_node_mesh(obj):
            j.add_gn_jbeam_visualizer_modifier(obj)
            Utils.log_and_report("Object is already a Node Mesh", self, 'INFO')
            return {'CANCELLED'}
        elif obj.type != 'MESH':
            Utils.log_and_report(f"{repr(obj)} is not a mesh or curve object!", self, 'WARNING')
            return {'CANCELLED'}

        jbeam_path = obj.data.get('jbeam_file_path', None)
        is_jbeam_part = bool(jbeam_path)  # flag to check if the jbeam part object is an import from the original jbeam editor from BeamNG team

        if not jbeam_path:
            Utils.log_and_report("Object is not a JBeam part or missing JBeam file path! Proceeding with regular conversion..", self, 'WARNING')

        JbeamNodeMeshConfigurator.remove_custom_data_props(obj)
        JbeamNodeMeshConfigurator.remove_double_vertices(obj)

        if is_jbeam_part:
            self.setup_jbeam_part(obj, jbeam_path)
        else:
            self.setup_jbeam_blender_mesh(obj)

        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        Utils.log_and_report(f"Converted {obj.name} to Node Mesh!", self, 'INFO')
        return {'FINISHED'}

    def setup_jbeam_blender_mesh(self, obj):
        JbeamPropsStorageManager.get_instance().register_object(obj)
        j.setup_default_scope_modifiers_and_node_ids(obj)
        JbeamNodeMeshConfigurator.process_node_mesh_props(obj)

    def setup_jbeam_part(self, obj, jbeam_path):
        self.parser = JbeamParser()
        try:
            self.parser.load_jbeam(jbeam_path)
            self.parser.parse_data_for_jbeam_object_conversion(obj)
        except Exception as e:
            Utils.log_and_report(f"Failed to read file: {e}", self, 'ERROR')
            return {'CANCELLED'}

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, self.parser)