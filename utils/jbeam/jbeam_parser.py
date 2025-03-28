import mathutils
import json
import os

from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore

class JBeamElement:
    """Base class for all JBeam elements (Node, Beam, Triangle)."""
    def __init__(self, instance, element_id, index, props=None):
        self.instance = instance
        self.id = element_id
        self.index = index
        self.props = props or {}

    def __repr__(self):
        return f"{self.__class__.__name__}(instance={self.instance}, id={self.id}, index={self.index}, props={self.props})"

class Node(JBeamElement):
    def __init__(self, instance, node_id, index, position, props=None):
        super().__init__(instance, node_id, index, props)
        self.position = position

    def get_fixed(self):
        return self.props.get("fixed", False)

    def __repr__(self):
        return f"Node(instance={self.instance}, id={self.id}, index={self.index}, pos={self.position}, props={self.props})"

class Beam(JBeamElement):
    def __init__(self, instance, beam_id, node_id1, node_id2, index, props=None):
        super().__init__(instance, beam_id, index, props)
        self.node_id1 = node_id1
        self.node_id2 = node_id2

    def __repr__(self):
        return f"Beam(instance={self.instance}, id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, index={self.index}, props={self.props})"

class Triangle(JBeamElement):
    def __init__(self, instance, triangle_id, node_id1, node_id2, node_id3, index, props=None):
        super().__init__(instance, triangle_id, index, props)
        self.node_id1 = node_id1
        self.node_id2 = node_id2
        self.node_id3 = node_id3

    def __repr__(self):
        return f"Triangle(id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, node_id3={self.node_id3}, index={self.index}, props={self.props})"

class JbeamParser:
    def __init__(self):
        self.jbeam_data = None
        self.part_data = None
        self.verts_dic = None
        self.nodes = None
        self.beams = None
        self.triangles = None

    def load_jbeam(self, obj, filepath):
        """Load and clean JBeam file."""
        self.jbeam_data = None
        if not os.path.exists(filepath):
            self.report({'ERROR'}, f"File not found: {filepath}")
            return
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
                clean_text = json_cleanup(raw_text)
                self.jbeam_data = json.loads(clean_text)
                for part_name, part_data in self.jbeam_data.items():
                    if "nodes" in part_data: # TODO currently only handles 1 part for selected obj, the first partname in the list
                        break
                json_nodes = part_data.get("nodes", [])
                json_beams = part_data.get("beams", [])
                json_triangles = part_data.get("triangles", [])
                self.nodes = self.parse_nodes(json_nodes)
                self.parse_vertex_indices(obj)
                self.beams = self.parse_beams(obj, json_beams)
                self.triangles = self.parse_triangles(obj, json_triangles)
        except json.JSONDecodeError as e:
            self.report({'ERROR'}, f"Error loading JBeam file: {e}")
            return

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
                instance = 1 # only 1 instance can exist of one node ID unlike beams and triangles that can have multiple instances
                nodes.append(Node(instance, node_id, -1, position, current_props.copy()))

        return nodes

    def parse_elements(self, obj, json_data, structure_type): # parse beams or triangles
        """ Generic parser for beams and triangles """
        structures, current_props = [], {}
        seen_structures = {}  # Track unique beams/triangles and their instance counts
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
                nodes = [self.verts_dic.get(n) for n in entry[:len(entry)]]
                if any(n is None for n in nodes):
                    print(f"Warning: Missing nodes {entry[:len(entry)]} in nodes and possibly in jbeam nodes")
                    continue

                index = get_index([n.index for n in nodes])
                struct_id = tuple(sorted(entry[:len(entry)]))  # Store as a tuple (order-independent)

                # Determine instance count
                if struct_id not in seen_structures:
                    seen_structures[struct_id] = 1
                else:
                    seen_structures[struct_id] += 1

                instance = seen_structures[struct_id]
                #print(f"{structure_type[:-1].capitalize()} detected: {struct_id} (Instance: {instance}) => {current_props}")

                # Add Beam or Triangle
                structures.append(
                    (Beam if structure_type == "beams" else Triangle)(
                        instance, struct_id, *nodes, index, current_props.copy()
                    )
                )

        return structures

    def parse_beams(self, obj, json_beams):
        return self.parse_elements(obj, json_beams, "beams")

    def parse_triangles(self, obj, json_triangles):
        return self.parse_elements(obj, json_triangles, "triangles")

    def get_vertex_indices(self):
        return self.verts_dic

    def parse_vertex_indices(self, obj, epsilon=0.0005):
        self.verts_dic = {}
        for node in self.nodes:
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
                    self.verts_dic[node.id] = node
                else:
                    self.report({'ERROR'}, f"No vertex found within proximity of {node.id}")
                    node.index = None # Explicitly mark nodes with no close vertex

    def debug_print_verts_dic(self):
        for node_id, props in self.verts_dic.items():
            print(f"Key: {node_id}, Value: {props}")

    def get_nodes(self):
        return self.verts_dic.items()  # parse using: for node_id(str), node(Node) in nodes.items():

    def get_beams(self):
        return self.beams

    def get_triangles(self):
        return self.triangles

    def get_ref_nodes(self):
        """Extract reference nodes from the JBeam data, trimming colons from keys."""
        if not self.jbeam_data:
            print("No jbeam data loaded")
            return {}
        for key, value in self.jbeam_data.items():
            if "refNodes" in value:
                headers, values = value["refNodes"]
                return {h[:-1]: v for h, v in zip(headers[1:], values[1:])}  # Trim last char from keys
        return {}