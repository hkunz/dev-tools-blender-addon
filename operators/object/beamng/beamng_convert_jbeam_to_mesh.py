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
        """Extract reference nodes from the JBeam data, trimming colons from keys."""
        for key, value in jbeam_data.items():
            if "refNodes" in value:
                headers, values = value["refNodes"]
                return {h[:-1]: v for h, v in zip(headers[1:], values[1:])}  # Trim last char from keys
        return {}

    def extract_node_positions(self, json_data):
        """Extract node positions from JBeam data while skipping metadata properties and headers."""
        node_positions = {}

        for obj_name, obj_data in json_data.items():
            if "nodes" in obj_data:
                nodes = obj_data["nodes"]
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

    def remove_custom_data_props(self, obj):
        for key in list(obj.keys()):
            del obj[key]
        for key in list(obj.data.keys()):
            del obj.data[key]

    def get_vertex_indices(self, obj, node_positions, obj_name=None, epsilon=0.0005):
        if obj_name is None:
            obj_name = next(iter(node_positions))  # Use the first key if no obj_name is given

        mesh = obj.data
        verts_dic = {}

        for node_id, node_pos in node_positions[obj_name].items():
            node_vec = mathutils.Vector(node_pos)

            # Find the closest vertex
            min_dist = float('inf')
            closest_vert_idx = -1
            for v in mesh.vertices:
                vert_vec = obj.matrix_world @ v.co  # Convert to world space
                dist = (node_vec - vert_vec).length

                if dist < min_dist and dist <= epsilon:
                    min_dist = dist
                    closest_vert_idx = v.index

            if closest_vert_idx != -1:
                verts_dic[node_id] = closest_vert_idx
            else:
                print(f"Warning: No vertex found within {epsilon} for node '{node_id}'.")

        return verts_dic

    def get_fixed_vertices(self, nodes):
        """Extracts a list of node IDs that belong to the 'fixed' vertex group."""
        fixed_nodes = []
        is_fixed = False  # Track whether we are in a fixed section

        for entry in nodes:
            if isinstance(entry, dict):  # Check for {"fixed": true} or {"fixed": false}
                if "fixed" in entry:
                    is_fixed = entry["fixed"]
            elif isinstance(entry, list) and len(entry) == 4:  # Node entries have 4 elements
                if is_fixed:
                    fixed_nodes.append(entry[0])  # Store node ID if inside a fixed section

        return fixed_nodes

    def assign_ref_nodes_to_vertex_groups(self, obj, ref_nodes, verts_dic):
        for group_name, node_id in ref_nodes.items():
            # Try to get the vertex group, create if it doesn't exist
            vg = obj.vertex_groups.get(group_name)
            if vg is None:
                print(f"Vertex group '{group_name}' not found, creating it.")
                vg = obj.vertex_groups.new(name=group_name)

            idx = verts_dic.get(node_id)
            if idx is None:
                print(f"Node ID '{node_id}' not found in verts_dic, skipping.")
                continue

            vg.add([idx], 1.0, 'REPLACE')
            print(f"Assigned vertex {idx} to vertex group '{group_name}'.")


    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'WARNING'}, "No mesh object selected!")
            return {'CANCELLED'}

        jbeam_path = obj.data.get('jbeam_file_path', None)
        if not jbeam_path:
            self.report({'WARNING'}, "Object is not a JBeam object or missing JBeam file path!")
            return {'CANCELLED'}

        json_data = self.load_jbeam(jbeam_path)
        if not json_data:
            return {'CANCELLED'}

        ref_nodes = self.get_ref_nodes(json_data)
        node_positions = self.extract_node_positions(json_data)

        first_key = next(iter(node_positions))
        # print(node_positions[first_key]["b29"]) # print(node_positions["faceball"]["b29"])

        self.remove_custom_data_props(obj)

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

        verts_dic = self.get_vertex_indices(obj, node_positions)
        #print("index2 ====", verts_dic["ref"])

        # bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups() # vertex groups not found maybe timing issue
        # bpy.context.view_layer.update()

        # **Extract "fixed" nodes and convert them to vertex indices**
        fixed_nodes = []
        for obj_name, obj_data in json_data.items():
            if "nodes" in obj_data:
                fixed_nodes.extend(self.get_fixed_vertices(obj_data["nodes"]))

        print(f"Fixed nodes: {fixed_nodes}")

        fixed_vertex_indices = [verts_dic[node] for node in fixed_nodes if node in verts_dic]

        if fixed_vertex_indices:
            vg_fixed = obj.vertex_groups.get("fixed")
            if vg_fixed is None:
                vg_fixed = obj.vertex_groups.new(name="fixed")

            vg_fixed.add(fixed_vertex_indices, 1.0, 'REPLACE')
            print(f"Assigned {len(fixed_vertex_indices)} vertices to the 'fixed' vertex group.")

        self.assign_ref_nodes_to_vertex_groups(obj, ref_nodes, verts_dic)
        reversed_verts_dic = {v: k for k, v in verts_dic.items()}
        obj.data["node_names"] = json.dumps(reversed_verts_dic)

        self.report({'INFO'}, f"Cleaned object and mesh data: {obj.name}")
        return {'FINISHED'}
