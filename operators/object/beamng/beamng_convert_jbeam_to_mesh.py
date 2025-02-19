import bpy
import os
import json
import mathutils
from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.json_cleanup import json_cleanup # type: ignore

class OBJECT_OT_BeamngConvertJbeamToMesh(Operator):
    """Convert jbeam to mesh object by removing custom properties and merge by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_mesh"
    bl_label = "DevTools: Convert JBeam to Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def get_ref_nodes(self, jbeam_data):
        for key, value in jbeam_data.items():
            if "refNodes" in value:
                headers, values = value["refNodes"]
                return dict(zip(headers[1:], values[1:])) # Skip "ref:" and "ref"
        return {}

    def extract_node_positions(self, json_data):
        node_positions = {}

        for obj_name, obj_data in json_data.items():
            if "nodes" in obj_data:
                node_positions[obj_name] = {
                    entry[0]: mathutils.Vector((entry[1], entry[2], entry[3]))
                    for entry in obj_data["nodes"][1:] # Skip header row
                }
        # print(node_positions["faceball"]["b29"])  # Outputs: <Vector (x, y, z)>
        return node_positions

    def load_jbeam(self, filepath):
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    raw_text = f.read()
                    clean_text = json_cleanup(raw_text)
                    data = json.loads(clean_text)
                    return data
                except json.JSONDecodeError as e:
                    self.report({'ERROR'}, f"Error loading JBeam file: {e}")
                    return None
        else:
            self.report({'ERROR'}, f"File not found: {filepath}")
            return None

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected!")
            return {'CANCELLED'}

        jbeam_path = obj.data['jbeam_file_path']
        
        if not jbeam_path:
            self.report({'WARNING'}, "Object is not a Jbeam object!")
            return {'CANCELLED'}

        json_data = self.load_jbeam(jbeam_path)
        ref_nodes = self.get_ref_nodes(json_data)
        node_positions = self.extract_node_positions(json_data)

        print("refNodes ==========")
        pprint(ref_nodes)
        print(node_positions["faceball"]["b29"])



        for key in list(obj.keys()):
            del obj[key]
        for key in list(obj.data.keys()):
            del obj.data[key]

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles()
        bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()
        
        self.report({'INFO'}, f"Cleaned object and mesh data: {obj.name}")
        return {'FINISHED'}