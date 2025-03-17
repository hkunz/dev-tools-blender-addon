import bpy
import bmesh
import os
import json
import mathutils
from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class Node:
    def __init__(self, node_id, index, position, group=None, props=None):
        self.node_id = node_id
        self.index = index
        self.position = position
        self.group = [group] if isinstance(group, str) else (group if group else [])
        self.props = props if props else {}

    def get_fixed(self):
        return self.props.get("fixed", False)

    def __repr__(self):
        return (f"Node(id={self.node_id}, index={self.index}, pos={self.position}, "f"group={self.group}, props={self.props})")

class Beam:
    def __init__(self, beam_id, node_id1, node_id2, index, props=None):
        self.beam_id = beam_id
        self.node_id1 = node_id1
        self.node_id2 = node_id2
        self.index = index
        self.props = props if props else {}

    def __repr__(self):
        return (f"Beam(id={self.beam_id}, node_id1={self.node_id1}, node_id2={self.node_id2}, index={self.index}, props={self.props})")

class OBJECT_OT_BeamngConvertJbeamToNodeMesh(Operator):
    """Convert object to Node Mesh by removing custom properties and merging by distance"""
    bl_idname = "object.devtools_beamng_convert_jbeam_to_node_mesh"
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
        current_group = None

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
                node_group = [current_group] if isinstance(current_group, str) else current_group
                nodes.append(Node(node_id, -1, position, node_group, node_props))
        return nodes

    def parse_beams(self, obj, json_beams, verts_dic):
        beams = []
        current_props = {}
        mesh = obj.data
        edge_lookup = {tuple(sorted((e.vertices[0], e.vertices[1]))): e.index for e in mesh.edges} # Precompute edge lookup dictionary

        def get_edge_index(i1, i2):
            return edge_lookup.get(tuple(sorted((i1, i2))))  # Handles both directions

        for i, entry in enumerate(json_beams, start=1):
            if isinstance(entry, dict):
                current_props.update(entry)
            elif isinstance(entry, list) and len(entry) >= 2:
                n1, n2 = entry[:2]
                node1, node2 = verts_dic.get(n1), verts_dic.get(n2)
                if node1 is None or node2 is None:
                    print(f"Warning: Missing nodes {n1}, {n2} in verts_dic and possibly in jbeam nodes")
                    continue

                edge_index = get_edge_index(node1.index, node2.index)
                beam_id = f"[{n1}|{n2}]"
                beam_props = current_props.copy()
                beams.append(Beam(beam_id, n1, n2, edge_index, beam_props))

        return beams

    def get_vertex_indices(self, obj, part_data, epsilon=0.0005):
        verts_dic = {}
        json_nodes = part_data.get("nodes", [])
        nodes = self.parse_nodes(json_nodes)

        for node in nodes:
            closest_vert_idx = None
            closest_dist_sq = float('inf')

            for vert in obj.data.vertices:
                vert_pos = obj.matrix_world @ vert.co  
                dist_sq = (vert_pos - node.position).length_squared

                if dist_sq < closest_dist_sq:
                    closest_dist_sq = dist_sq
                    closest_vert_idx = vert.index

            if closest_vert_idx is not None:
                if closest_dist_sq < epsilon ** 2:  # Check if closest vertex is within range
                    node.index = closest_vert_idx
                    verts_dic[node.node_id] = node
                else:
                    self.report({'ERROR'}, f"No vertex found within proximity of {node.node_id}")
                    node.index = None # Explicitly mark nodes with no close vertex

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

    def assign_flex_groups_to_vertex_groups(self, obj, json_part_data, verts_dic):       
        current_group = None
        group_vertices = {}
        for node in json_part_data["nodes"]:
            if isinstance(node, dict) and "group" in node:
                current_group = node["group"] or None  # Could be a list or None
            elif isinstance(node, list) and current_group:
                node_name = node[0]
                if node_name in verts_dic:
                    index = verts_dic[node_name].index
                    if index < 0:
                        self.report({'ERROR'}, f"No vertex index assigned to {node_name}")
                        continue
                    
                    # Ensure `current_group` is always a list
                    groups = [current_group] if isinstance(current_group, str) else current_group
                    
                    for group in groups:
                        if not group:
                            continue
                        if group not in group_vertices:
                            group_vertices[group] = []
                        group_vertices[group].append(index)

        for group_name, vertex_indices in group_vertices.items():
            if not group_name:
                continue
            vg = obj.vertex_groups.get(group_name)
            if vg is None:
                vg = obj.vertex_groups.new(name=group_name)
            vg.add(vertex_indices, 1.0, 'REPLACE')
            print(f"Assigned {len(vertex_indices)} vertices to the '{group_name}' vertex group.")

    def create_node_mesh_attributes(self, obj):
        j.remove_old_jbeam_attributes(obj)
        j.create_node_mesh_attributes(obj)

    def store_node_props_in_vertex_attributes(self, obj, verts_dic):

        for node_id, vert_props in verts_dic.items():
            if not hasattr(vert_props, "index") or vert_props.index < 0:
                self.report({'ERROR'}, f"Invalid vertex index for node {node_id}")
                continue

            idx = vert_props.index
            flat_data = {}

            if hasattr(vert_props, "props") and isinstance(vert_props.props, dict):
                flat_data.update({k: v for k, v in vert_props.props.items() if k != "group"})

            j.set_node_id(obj, idx, str(vert_props.node_id))
            j.set_node_props(obj, idx, flat_data)

    def store_beam_props_in_edge_attributes(self, obj, part_data, verts_dic):
        json_beams = part_data.get("beams", [])
        beams = self.parse_beams(obj, json_beams, verts_dic)

        for beam in beams:
            if beam.index is None:
                self.report({'ERROR'}, f"No edge found for beam {beam.beam_id}")
                continue

            j.set_beam_props(obj, beam.index, beam.props)

    def create_default_flex_group(self, obj):
        node_group = "flexbody_mesh"
        vertex_groups_data = {
            f'group_{node_group}': list(range(len(obj.data.vertices)))
        }

        for group_name, vertex_indices in vertex_groups_data.items():
            group = obj.vertex_groups.new(name=group_name)
            group.add(vertex_indices, 1.0, 'REPLACE')

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
            self.report({'WARNING'}, f"{repr(obj)} is not a mesh object!")
            return {'CANCELLED'}

        j.set_jbeam_visuals(obj)
        j.add_gn_jbeam_visualizer_modifier(obj)

        jbeam_path = obj.data.get('jbeam_file_path', None)
        ref_nodes = None
        is_jbeam_part = False

        if not jbeam_path:
            self.report({'WARNING'}, "Object is not a JBeam part or missing JBeam file path!")
        else:
            is_jbeam_part = True
            json_data = self.load_jbeam(jbeam_path)
            if json_data:
                ref_nodes = self.get_ref_nodes(json_data)
            for part_name, part_data in json_data.items():
                if "nodes" in part_data: # TODO currently only handles 1 part for selected obj, the first partname in the list
                    break
 
        self.remove_custom_data_props(obj)

        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.remove_doubles(threshold=0.0005)
        bpy.ops.object.mode_set(mode='OBJECT')

        if is_jbeam_part:
            verts_dic = self.get_vertex_indices(obj, part_data)
            self.assign_ref_nodes_to_vertex_groups(obj, ref_nodes, verts_dic)
            self.assign_flex_groups_to_vertex_groups(obj, part_data, verts_dic)
            self.create_node_mesh_attributes(obj)
            self.store_node_props_in_vertex_attributes(obj, verts_dic)
            self.store_beam_props_in_edge_attributes(obj, part_data, verts_dic)
        else:
            self.create_default_flex_group(obj)
            j.setup_default_scope_modifiers_and_node_ids(obj)

        bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()

        self.report({'INFO'}, f"Converted {obj.name} to Node Mesh!")
        return {'FINISHED'}
