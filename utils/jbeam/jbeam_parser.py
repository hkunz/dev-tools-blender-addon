import mathutils
import json
import os

from typing import Optional, Iterable, Tuple

from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore

NodeID = str
ElementID = str  # can be NodeID or beam id (i.e. [node_1|node_2]) or triangle id (i.e. [node_1|node_2|node_3])
ScopeModifier = ScopeModifierValue = str
Props = dict[ScopeModifier, ScopeModifierValue]  # i.e. {"frictionCoef":"1.2","nodeMaterial":"|NM_RUBBER","nodeWeight":"1","collision":"true","selfCollision":"true","group":"mattress"}

class JBeamElement:
    """Base class for all JBeam elements (Node, Beam, Triangle)."""
    def __init__(self, instance, element_id, index, props=None):
        self.instance: int = instance  # you can have multiple instances of a beam or a triangle in jbeam
        self.id: ElementID  = element_id
        self.index: int = index  # vertex, edge, or face index
        self.props: Props = props if props is not None else {}

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
        self.node_id1: str = node_id1
        self.node_id2: str = node_id2

    def __repr__(self):
        return f"Beam(instance={self.instance}, id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, index={self.index}, props={self.props})"

class Triangle(JBeamElement):
    def __init__(self, instance, triangle_id, node_id1, node_id2, node_id3, index, props=None):
        super().__init__(instance, triangle_id, index, props)
        self.node_id1: str = node_id1
        self.node_id2: str = node_id2
        self.node_id3: str = node_id3

    def __repr__(self):
        return f"Triangle(id={self.id}, node_id1={self.node_id1}, node_id2={self.node_id2}, node_id3={self.node_id3}, index={self.index}, props={self.props})"

class JbeamPart:
    def __init__(self):
        self.part_name: str = None
        self.part_data = None
        self.json_str: str = None
        self.slot_type: str = None
        self.refnodes: dict[str, str] = {}
        self.nodes: dict[NodeID, Node] = {}
        self.nodes_list: list[Node] = []
        self.beams_list: list[Beam] = []
        self.triangles_list: list[Triangle] = []
        self.json_beams = None
        self.json_triangles = None
        self.json_quads = None

class JbeamParser:
    def __init__(self):
        self.jbeam_data = None
        self.jbeam_main_part = None
        self.jbeam_parts: dict[str, JbeamPart] = {}

    def load_jbeam(self, filepath):
        """Load and clean JBeam file from path."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")
        try:
            print("=============================================================")
            print("Loading:", filepath)
            with open(filepath, "r", encoding="utf-8") as f:
                raw_text = f.read()
            print("Raw data loaded. Start parsing...")
            self._load_jbeam_data(raw_text)
        except FileNotFoundError as e:
            Utils.log_and_raise(f"File not found: {filepath}", FileNotFoundError, e)
        except json.JSONDecodeError as e:
            Utils.log_and_raise(f"Error decoding JSON from JBeam file: {e}", ValueError, e)

    def load_jbeam_from_string(self, text):
        """Load and clean JBeam file from string."""
        try:
            self._load_jbeam_data(text)
            print("Loaded jbeam successfully from fixed string")
        except json.JSONDecodeError as e:
            Utils.log_and_raise(f"Error decoding JSON from JBeam string: {e}", ValueError, e)

    def _load_jbeam_data(self, text):
        """Internal shared logic to clean and parse JBeam text."""
        self.json_str = json_cleanup(text)
        self.jbeam_data = json.loads(self.json_str)

        for part_name, part_data in self.jbeam_data.items(): 
            p = JbeamPart()

            if "nodes" in part_data:
                json_nodes = part_data.get("nodes")
                p.nodes_list = self._parse_nodes(json_nodes)
            if "beams" in part_data:
                p.json_beams = part_data.get("beams")
            if "triangles" in part_data:
                p.json_triangles = part_data.get("triangles")
            if "quads" in part_data:
                p.json_quads = part_data.get("quads")
            if "slotType" in part_data:
                p.slot_type = part_data.get("slotType")
                if p.slot_type == "main":
                    self.jbeam_main_part = p
            if "refNodes" in part_data:
                headers, values = part_data["refNodes"]
                p.refnodes = {h[:-1]: v for h, v in zip(headers[:], values[:])}  # Trim last char from keys

            self.jbeam_parts[part_name] = p
            print(f"Registered part {p} named '{part_name}' with slot type '{p.slot_type}'")

    def _split_quads_into_triangles(self, quads_json: list) -> list:
        result = []
        for entry in quads_json:
            if isinstance(entry, list) and len(entry) >= 4:
                *nodes, last = entry
                has_props = isinstance(last, dict)
                quad = nodes if has_props else entry
                props = last if has_props else {}

                if len(quad) >= 4:
                    n1, n2, n3, n4 = quad[:4]
                    result.append([n1, n2, n3, props.copy()])
                    result.append([n3, n4, n1, props.copy()])
                else:
                    print(f"WARNING: entry {entry} not a proper quad (ignored)")
            else:
                result.append(entry)  # Keep dicts and others as-is
        return result

    def parse_data_for_jbeam_object_conversion(self, obj, part_name="", get_vertex_indices=True):
        mesh = obj.data
        part = self.get_jbeam_part(part_name)
        try:
            if get_vertex_indices:
                self._retrieve_closest_vertex_indices(obj, part)
            part.nodes.update({node.id: node for node in part.nodes_list})
            part.beams_list = self._parse_beams(part.json_beams, mesh, part_name)
            part.triangles_list = self._parse_triangles(part.json_triangles, mesh, part_name)
            if not part.json_quads:
                return
            print("Extend triangles list with quads")
            tris_from_quads = self._split_quads_into_triangles(part.json_quads)
            tris_from_quads_list = self._parse_triangles(tris_from_quads, mesh, part_name)
            part.triangles_list = (part.triangles_list or []) + tris_from_quads_list

        except Exception as e:
            Utils.log_and_raise(f"An error occurred while processing the remaining JBeam data: {e}", RuntimeError, e)   

    def _parse_nodes(self, json_nodes):
        nodes = []
        seen_node_ids = set()  # Track node_id uniqueness
        current_props = {}
        print("Parsing nodes ...")

        for entry in json_nodes:
            if isinstance(entry, dict):
                current_props.update(entry)
            elif isinstance(entry, list) and len(entry) >= 4:
                node_id, x, y, z = entry[:4]
                inline_props = entry[4] if len(entry) > 4 else {}

                if any(isinstance(v, str) for v in (x, y, z)):
                    continue  # Skip header row

                if node_id in seen_node_ids:
                    print(f"Warning: Duplicate node_id found and skipped: {node_id}")
                    continue  # Skip duplicate node_id

                seen_node_ids.add(node_id)
                position = mathutils.Vector((x, y, z))
                props = current_props.copy()
                props.update(inline_props)
                instance = 1 # only 1 instance can exist of one node ID unlike beams and triangles that can have multiple instances
                nodes.append(Node(instance, node_id, -1, position, props))

        return nodes

    def _parse_elements(self, json_data, structure_type, part_name="", lookup=None): # parse beams or triangles
        """ Generic parser for beams and triangles """
        structures, current_props = [], {}
        seen_structures = {}  # Track unique beams/triangles and their instance counts
        part = self.get_jbeam_part(part_name)

        def get_index(indices):
            return lookup.get(tuple(sorted(indices)))

        if not json_data:
            print(f"No {structure_type} to parse because json data doesn't have '{structure_type}' node in jbeam part '{part.part_name}'")
            return
        for entry in json_data:
            if isinstance(entry, dict):
                current_props.update(entry)
            elif isinstance(entry, list): # and len(entry) >= (2 if structure_type == "beams" else 3):
                if all(isinstance(item, str) and item.startswith("id") and item.endswith(":") for item in entry):
                    print(f"Header detected: {entry} (ignored)")
                    continue
                nodes = None
                inline_props = None
                if structure_type == "beams" and len(entry) >= 2:
                    # Beams have 2 items for the nodes, with optional properties after that
                    nodes = [part.nodes.get(n) for n in entry[:2]]  # Always expect 2 node IDs
                    inline_props = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else {}

                elif structure_type == "triangles" and len(entry) >= 3:
                    # Triangles have 3 items for the nodes, with optional properties after that
                    nodes = [part.nodes.get(n) for n in entry[:3]]  # Always expect 3 node IDs
                    inline_props = entry[3] if len(entry) > 3 and isinstance(entry[3], dict) else {}
                if any(n is None for n in nodes):
                    print(f"Warning: Missing nodes accessed by element {entry[:len(entry)]}. Nodes possibly missing in jbeam file or limitation in the addon (still work-in-progress) where some nodes reside in a base jbeam file")
                    continue

                index = get_index([n.index for n in nodes]) if lookup else -1
                struct_id = tuple(sorted(entry[:len(nodes)]))

                # Determine instance count # FIXME: Currently there is no support for this syntax of inline scope modifier: ["BACKl1","BACKl5", {"highlight":{"radius":0.2, "col":"#00ff00ff" }}], like that in "vehicles\large_crusher\large_crusher_boxes.jbeam"
                if struct_id not in seen_structures:
                    seen_structures[struct_id] = 1
                else:
                    seen_structures[struct_id] += 1

                instance = seen_structures[struct_id]
                #print(f"{structure_type[:-1].capitalize()} detected: {struct_id} (Instance: {instance}) => {current_props}")

                props = current_props.copy()
                props.update(inline_props)

                structures.append(
                    (Beam if structure_type == "beams" else Triangle)(
                        instance, struct_id,
                        nodes[0].id, nodes[1].id,  # For Beam, pass only two node IDs (node_id1, node_id2)
                        *([nodes[2].id] if len(nodes) > 2 else []),  # For Triangle, pass three node IDs if available, otherwise just pass two valid IDs
                        index, props
                    )
                )

        return structures

    def _parse_beams(self, json_beams, mesh=None, part_name=""):
        print("Parsing beams ...")
        lookup = {tuple(sorted((e.vertices[0], e.vertices[1]))): e.index for e in mesh.edges} if mesh else None
        return self._parse_elements(json_beams, "beams", part_name, lookup)

    def _parse_triangles(self, json_triangles, mesh=None, part_name=""):
        print("Parsing triangles ...")
        lookup = {tuple(sorted(f.vertices)): f.index for f in mesh.polygons} if mesh else None
        return self._parse_elements(json_triangles, "triangles", part_name, lookup)

    def _retrieve_closest_vertex_indices(self, obj, part: JbeamPart, epsilon=0.0005):
        for node in part.nodes_list:
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
                else:
                    raise ValueError(f"No vertex found within proximity of {node.id}")
            else:
                # Handle the case where no vertex is found (this is redundant unless obj.data.vertices is empty)
                raise ValueError(f"No vertex found at all for node {node.id}")

    def debug_print_nodes(self, part_name=""):
        part = self.get_jbeam_part(part_name)
        if not part:
            print(f"Part '{part_name}' not found.")
            return
        nodes: dict[NodeID, Node] = part.nodes
        items = nodes.items() # Iterable[Tuple[NodeID, Node]]
        for node_id, node in items:
            print(f"{node_id} => {node}")
            # i.e.: 'node_1' => Node(instance=1, id=a1ll, index=5, pos=<Vector (0.6800, -0.9350, 0.1100)>, props={'frictionCoef': 1.2, 'nodeMaterial': '|NM_RUBBER', 'nodeWeight': 1, 'collision': True, 'selfCollision': True, 'group': 'mattress'})

    def get_jbeam_parts(self) -> dict[str, JbeamPart]:
        return self.jbeam_parts

    def get_jbeam_part(self, part_name: str = "") -> JbeamPart | None:
        if part_name:
            if part_name not in self.jbeam_parts:
                print(f"Parser: No part name '{part_name}' found")
                return None
            return self.jbeam_parts.get(part_name)
        return next(iter(self.jbeam_parts.values()), None)

    def _get_jbeam_part_main(self):
        return self._get_jbeam_part_by_slot_type("main")

    def _get_jbeam_part_by_slot_type(self, slot_type: str) -> JbeamPart | None:
        for part in self.jbeam_parts.values():
            if part.slot_type == slot_type:
                return part
        print(f"Parser: No part with slot_type '{slot_type}' found")
        return None

    def get_json_str(self) -> str:
        return self.json_str

    def get_nodes(self, part_name: str = "") -> dict[NodeID, Node]:
        part = self.get_jbeam_part(part_name)
        return part.nodes if part else {}

    def get_nodes_list(self, part_name: str = "") -> list[Node]:
        part = self.get_jbeam_part(part_name)
        return part.nodes_list if part else []

    def get_beams_list(self, part_name: str = "") -> list[Beam]:
        part = self.get_jbeam_part(part_name)
        return part.beams_list if part else []

    def get_triangles_list(self, part_name: str = "") -> list[Triangle]:
        part = self.get_jbeam_part(part_name)
        return part.triangles_list if part else []

    def get_ref_nodes(self, part_name: str = "") -> dict[str, str]:
        part = self.get_jbeam_part(part_name)
        if part and part.refnodes:
            return part.refnodes
        part = self._get_jbeam_part_main()
        if part and part.refnodes:
            return part.refnodes
        print(f"[JBeam Parser] No refnodes found for part `{part_name}` or main part: '{part.part_name if part else 'None'}'")
        return {}
