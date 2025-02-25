import bpy
import os
import json
import mathutils
from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore

class Node:
    def __init__(self, node_id, index, position, group, props):
        self.node_id = node_id
        self.index = index
        self.position = position
        self.group = group
        self.props = props

    def get_fixed(self):
        return self.props.get("fixed", False)

    def __repr__(self):
        return f"Node(id={self.node_id}, index={self.index}, pos={self.position}, group={self.group}, props={self.props})"

class OBJECT_OT_BeamngConvertJbeamToMesh_v2(Operator):
    """Convert JBeam to mesh object by removing custom properties and merging by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_mesh_v2"
    bl_label = "DevTools: Convert JBeam to Mesh Object (v2)"
    bl_options = {'REGISTER', 'UNDO'}

    def get_ref_nodes(self, jbeam_data):
        """Extract reference nodes from the JBeam data, trimming colons from keys."""
        for key, value in jbeam_data.items():
            if "refNodes" in value:
                headers, values = value["refNodes"]
                return {h[:-1]: v for h, v in zip(headers[1:], values[1:])}  # Trim last char from keys
        return {}

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

    def parse_nodes(self, json_nodes):
        nodes = []
        current_props = {}
        current_group = ""

        for entry in json_nodes:
            if isinstance(entry, dict):  
                if "group" in entry:
                    current_group = entry["group"]
                current_props.update(entry)
            elif isinstance(entry, list) and len(entry) >= 4:
                node_id, x, y, z = entry[:4]  
                
                if isinstance(x, str) or isinstance(y, str) or isinstance(z, str):
                    continue  # Skip header row
                
                position = mathutils.Vector((x, y, z))
                node_props = current_props.copy()  

                nodes.append(Node(node_id, -1, position, current_group, node_props))

        return nodes

    def get_vertex_indices(self, obj, json_data, part_name=None, epsilon=0.0005):
        verts_dic = {}

        if part_name is None:
            for part_name, obj_data in json_data.items():
                break

        json_nodes = json_data[part_name].get("nodes", [])
        nodes = self.parse_nodes(json_nodes)  

        for node in nodes:
            closest_vert_idx = None
            closest_dist_sq = float('inf')

            for vert in obj.data.vertices:
                vert_pos = obj.matrix_world @ vert.co  
                dist_sq = (vert_pos - node.position).length_squared

                if dist_sq < epsilon ** 2 and dist_sq < closest_dist_sq:
                    closest_dist_sq = dist_sq
                    closest_vert_idx = vert.index

            if closest_vert_idx is not None:
                node.index = closest_vert_idx
                verts_dic[node.node_id] = node 

        return verts_dic

    def assign_ref_nodes_to_vertex_groups(self, obj, ref_nodes, verts_dic):
        for group_name, node_id in ref_nodes.items():
            vg = obj.vertex_groups.get(group_name)
            if vg is None:
                print(f"Vertex group '{group_name}' not found, creating it.")
                vg = obj.vertex_groups.new(name=group_name)

            node = verts_dic.get(node_id)
            if node is None:
                print(f"Node ID '{node_id}' not found in verts_dic, skipping.")
                continue
            idx = node.index
            if idx < 0:
                self.report({'ERROR'}, f"No vertex index assigned to {node.node_id}")
                continue
            vg.add([idx], 1.0, 'REPLACE')
            print(f"Assigned vertex {idx} to vertex group '{group_name}'.")


    def assign_flex_groups_to_vertex_groups(self, obj, json_data, verts_dic):
        group_vertices = {}
        for part_name, part_data in json_data.items():
            if "nodes" not in part_data:
                continue
            current_group = None
            for node in part_data["nodes"]:
                if isinstance(node, dict) and "group" in node:
                    current_group = node["group"] or None
                elif isinstance(node, list) and current_group:
                    node_name = node[0]
                    if node_name in verts_dic:
                        if current_group not in group_vertices:
                            group_vertices[current_group] = []
                        index = verts_dic[node_name].index
                        if index < 0:
                            self.report({'ERROR'}, f"No vertex index assigned to {node_name}")
                            continue
                        group_vertices[current_group].append(index)

        for group_name, vertex_indices in group_vertices.items():
            if not group_name:
                continue
            vg = obj.vertex_groups.get(group_name)
            if vg is None:
                vg = obj.vertex_groups.new(name=group_name)
            vg.add(vertex_indices, 1.0, 'REPLACE')
            print(f"Assigned {len(vertex_indices)} vertices to the '{group_name}' vertex group.")

    def assign_fixed_nodes_to_vertex_groups(self, obj, verts_dic):
        vg_name = "fixed"
        vg = obj.vertex_groups.get(vg_name)
        if vg is None:
            vg = obj.vertex_groups.new(name=vg_name)
        fixed_indices = [node.index for node in verts_dic.values() if node.get_fixed() and node.index != -1]
        if fixed_indices:
            vg.add(fixed_indices, 1.0, 'REPLACE')

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
        self.remove_custom_data_props(obj)

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

        verts_dic = self.get_vertex_indices(obj, json_data)

        self.assign_fixed_nodes_to_vertex_groups(obj, verts_dic)
        self.assign_ref_nodes_to_vertex_groups(obj, ref_nodes, verts_dic)
        self.assign_flex_groups_to_vertex_groups(obj, json_data, verts_dic)

        reversed_verts_dic = {node.index: node.node_id for node_id, node in verts_dic.items()}
        obj.data["node_names"] = json.dumps(reversed_verts_dic)

        self.report({'INFO'}, f"Cleaned object and mesh data: {obj.name}")
        return {'FINISHED'}
