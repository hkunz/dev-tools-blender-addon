import bpy
import bmesh
import os
import json
import mathutils
from pprint import pprint
from bpy.types import Operator

from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class JBeamElement:
    """Base class for all JBeam elements (Node, Beam, Triangle)."""
    def __init__(self, element_id, index, props=None):
        self.id = element_id
        self.index = index
        self.props = props or {}

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, index={self.index}, props={self.props})"

class Node(JBeamElement):
    def __init__(self, node_id, index, position, props=None):
        super().__init__(node_id, index, props)
        self.position = position

    def get_fixed(self):
        return self.props.get("fixed", False)

    def __repr__(self):
        return f"Node(id={self.id}, index={self.index}, pos={self.position}, props={self.props})"

class Beam(JBeamElement):
    def __init__(self, beam_id, node_id1, node_id2, index, props=None):
        super().__init__(beam_id, index, props)
        self.node_id1 = node_id1
        self.node_id2 = node_id2

    def __repr__(self):
        return f"Beam(id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, index={self.index}, props={self.props})"

class Triangle(JBeamElement):
    def __init__(self, triangle_id, node_id1, node_id2, node_id3, index, props=None):
        super().__init__(triangle_id, index, props)
        self.node_id1 = node_id1
        self.node_id2 = node_id2
        self.node_id3 = node_id3

    def __repr__(self):
        return f"Triangle(id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, node_id3={self.node_id3}, index={self.index}, props={self.props})"

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
        seen_node_ids = set()  # Track node_id uniqueness
        current_props = {}

        for entry in json_nodes:
            if isinstance(entry, dict):
                current_props.update(entry)
            elif isinstance(entry, list) and len(entry) >= 4:
                node_id, x, y, z = entry[:4]

                if any(isinstance(v, str) for v in (x, y, z)):
                    continue  # Skip header row

                if node_id in seen_node_ids:
                    print(f"Warning: Duplicate node_id found and skipped: {node_id}")
                    continue  # Skip duplicate node_id

                seen_node_ids.add(node_id)
                position = mathutils.Vector((x, y, z))
                nodes.append(Node(node_id, -1, position, current_props.copy()))

        return nodes

    def parse_elements(self, obj, json_data, verts_dic, structure_type):
        """ Generic parser for beams and triangles """
        structures, current_props = [], {}
        seen_structures = set()  # Track unique beams/triangles
        mesh = obj.data

        if structure_type == "beams":
            lookup = {tuple(sorted((e.vertices[0], e.vertices[1]))): e.index for e in mesh.edges}
        elif structure_type == "triangles":
            lookup = {tuple(sorted(f.vertices)): f.index for f in mesh.polygons}
        else:
            raise ValueError("Invalid structure type")

        def get_index(indices):
            return lookup.get(tuple(sorted(indices)))

        for entry in json_data:
            if isinstance(entry, dict):
                current_props.update(entry)
            elif isinstance(entry, list) and len(entry) >= (2 if structure_type == "beams" else 3):
                if all(isinstance(item, str) and item.startswith("id") and item.endswith(":") for item in entry):
                    print(f"Header detected: {entry} (ignored)")
                    continue
                nodes = [verts_dic.get(n) for n in entry[:len(entry)]]
                if any(n is None for n in nodes):
                    print(f"Warning: Missing nodes {entry[:len(entry)]} in verts_dic and possibly in jbeam nodes")
                    continue

                index = get_index([n.index for n in nodes])
                struct_id = tuple(sorted(entry[:len(entry)]))  # Store as a tuple (order-independent)

                if struct_id in seen_structures:
                    print(f"Warning: Duplicate {structure_type[:-1]} found and skipped: {entry[:len(entry)]}")
                    continue  # Skip duplicate beam/triangle

                seen_structures.add(struct_id)
                structures.append(
                    (Beam if structure_type == "beams" else Triangle)(struct_id, *nodes, index, current_props.copy())
                )

        return structures

    def parse_beams(self, obj, json_beams, verts_dic):
        return self.parse_elements(obj, json_beams, verts_dic, "beams")

    def parse_triangles(self, obj, json_triangles, verts_dic):
        return self.parse_elements(obj, json_triangles, verts_dic, "triangles")

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
                    verts_dic[node.id] = node
                else:
                    self.report({'ERROR'}, f"No vertex found within proximity of {node.id}")
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
                self.report({'ERROR'}, f"No vertex index assigned to {node.id}")
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

        for node_id, node in verts_dic.items():
            if not hasattr(node, "index") or node.index < 0:
                self.report({'ERROR'}, f"Invalid vertex index for node {node_id}")
                continue

            idx = node.index
            flat_data = {}

            if hasattr(node, "props") and isinstance(node.props, dict):
                #flat_data.update({k: v for k, v in node.props.items() if k != "group"})
                flat_data.update({k: json.dumps(v) for k, v in node.props.items()})


            j.set_node_id(obj, idx, str(node.id))
            j.set_node_props(obj, idx, flat_data)

    def store_beam_props_in_edge_attributes(self, obj, part_data, verts_dic):
        json_beams = part_data.get("beams", [])
        beams = self.parse_beams(obj, json_beams, verts_dic)

        for beam in beams:
            if beam.index is None:
                self.report({'ERROR'}, f"No edge found for beam {beam.id}")
                continue

            j.set_beam_props(obj, beam.index, beam.props)

    def store_triangle_props_in_face_attributes(self, obj, part_data, verts_dic):
        json_triangles = part_data.get("triangles", [])
        triangles = self.parse_triangles(obj, json_triangles, verts_dic)

        for triangle in triangles:
            if triangle.index is None:
                self.report({'ERROR'}, f"No face found for triangle {triangle.id}")
                continue

            j.set_triangle_props(obj, triangle.index, triangle.props)

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
            #self.assign_flex_groups_to_vertex_groups(obj, part_data, verts_dic) #  groups are now also part of the scope modifiers instead of vertex groups
            self.create_node_mesh_attributes(obj)
            self.store_node_props_in_vertex_attributes(obj, verts_dic)
            self.store_beam_props_in_edge_attributes(obj, part_data, verts_dic)
            self.store_triangle_props_in_face_attributes(obj, part_data, verts_dic)
        else:
            j.setup_default_scope_modifiers_and_node_ids(obj)

        bpy.ops.object.devtools_beamng_create_refnodes_vertex_groups()

        self.report({'INFO'}, f"Converted {obj.name} to Node Mesh!")
        return {'FINISHED'}
