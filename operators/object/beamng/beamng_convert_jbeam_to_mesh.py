import bpy
import os
import json
import mathutils
from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore

class OBJECT_OT_BeamngConvertJbeamToMesh(Operator):
    """Convert JBeam to mesh object by removing custom properties and merging by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_mesh"
    bl_label = "DevTools: Convert JBeam to Mesh Object"
    bl_options = {'REGISTER', 'UNDO'}

    def get_ref_nodes(self, jbeam_data):
        """Extract reference nodes from the JBeam data."""
        for key, value in jbeam_data.items():
            if "refNodes" in value:
                headers, values = value["refNodes"]
                return dict(zip(headers[1:], values[1:]))  # Skip "ref:" and "ref"
        return {}

    def extract_node_positions(self, json_data):
        """Extract node positions from JBeam data while skipping metadata properties and headers."""
        node_positions = {}

        for obj_name, obj_data in json_data.items():
            if "nodes" in obj_data:
                nodes = obj_data["nodes"]

                # Debugging: Print first few entries to check format
                print(f"Nodes for {obj_name}: {nodes[:5]}")  # Print first few lines

                node_positions[obj_name] = {
                    entry[0]: mathutils.Vector((float(entry[1]), float(entry[2]), float(entry[3])))
                    for entry in nodes
                    if isinstance(entry, list) and len(entry) >= 4 and isinstance(entry[1], (int, float))
                }

        return node_positions





    def load_jbeam(self, filepath):
        """Load and clean JBeam file."""
        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"File not found: {filepath}")
            return None

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
                clean_text = json_cleanup(raw_text)
                return json.loads(clean_text)
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"Error loading JBeam file: {e}")
            return None

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected!")
            return {'CANCELLED'}

        # Get JBeam file path safely
        jbeam_path = obj.data.get('jbeam_file_path', None)
        if not jbeam_path:
            self.report({'WARNING'}, "Object is not a JBeam object or missing JBeam file path!")
            return {'CANCELLED'}

        json_data = self.load_jbeam(jbeam_path)
        if not json_data:
            return {'CANCELLED'}  # Already reported error inside load_jbeam()

        ref_nodes = self.get_ref_nodes(json_data)
        node_positions = self.extract_node_positions(json_data)

        # Debugging output
        print("refNodes ==========")
        pprint(ref_nodes)

        # Check if faceball exists before accessing
        if "faceball" in node_positions and "b29" in node_positions["faceball"]:
            print(node_positions["faceball"]["b29"])

        # Remove custom properties
        for key in list(obj.keys()):
            del obj[key]
        for key in list(obj.data.keys()):
            del obj.data[key]

        # Merge by distance (Updated from remove_doubles)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

        # Run additional operator
        bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()

        self.report({'INFO'}, f"Cleaned object and mesh data: {obj.name}")
        return {'FINISHED'}
