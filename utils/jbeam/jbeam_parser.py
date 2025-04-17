import mathutils

from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_loader import JbeamLoadItem  # type: ignore
from dev_tools.utils.jbeam.jbeam_models import JbeamJson, JbeamPart, NodeID, Node, Beam, Triangle, JbeamPartName, JbeamPartSectionName, JbeamPartData  # type: ignore

#JbeamPartName = str
#JbeamPartSectionName = str  # section names include: information, slotType, sounds, flexbodies, nodes, beams, triangles, quads, etc
#JbeamPartData = dict[JbeamPartSectionName, Any]
#JbeamJson = dict[JbeamPartName, JbeamPartData]

class JbeamParser:
    def __init__(self, source:JbeamLoadItem=None):
        self.source = source
        self.jbeam_main_part = None
        self.jbeam_parts: dict[JbeamPartName, JbeamPart] = {}

    def parse(self, jbeam_json: JbeamJson):
        load_item = self.source
        #print(f"\n🧩 Prepare parsing Nodes from: 📄 {load_item.file_path}")
        for part_name, part_data in jbeam_json.items():
            p = JbeamPart()
            p.part_name = part_name
            if "slotType" in part_data:
                p.slot_type = part_data.get("slotType")
                if p.slot_type == "main":
                    self.jbeam_main_part = p
            if load_item and load_item.part_name and (load_item.part_name != p.part_name or load_item.slot_type != p.slot_type):
                #print(f" - Ignore irrelevant part {p.part_name} with slot type {p.slot_type}")
                continue
            if "refNodes" in part_data:
                headers, values = part_data["refNodes"]
                p.refnodes = {h[:-1]: v for h, v in zip(headers[:], values[:])}  # Trim last char from keys
            nodes: list = self._get_section("nodes", part_data)
            print(f"🧩 Parsing Nodes ⚪ {part_name}")
            if nodes:
                p.nodes_list = self._parse_nodes(nodes)
            else:
                print(f"    - No Nodes found in {part_name}.")
            p.json_beams = self._get_section("beams", part_data)
            p.json_triangles = self._get_section("triangles", part_data)
            p.json_quads = self._get_section("quads", part_data)

            self.jbeam_parts[part_name] = p
            print(f"    - Registered part {p}")

    def _get_section(self, section_name: JbeamPartSectionName, part_data: JbeamPartData) -> list:
        return part_data.get(section_name, [])

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
                    print(f"⚠️  WARNING: entry {entry} not a proper quad (ignored)")
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

    def _parse_nodes(self, json_nodes: list):
        nodes = []
        seen_node_ids = set()  # Track node_id uniqueness
        current_props = {}

        for entry in json_nodes:
            if isinstance(entry, dict):
                current_props.update(entry)
            elif isinstance(entry, list) and len(entry) >= 4:
                node_id, x, y, z = entry[:4]
                inline_props = entry[4] if len(entry) > 4 else {}

                if any(isinstance(v, str) for v in (x, y, z)):
                    continue  # Skip header row

                if node_id in seen_node_ids:
                    print(f"⚠️  Warning: Duplicate node '{node_id}' found and skipped ...")
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
        missing_node_warnings = set()

        for entry in json_data:
            if isinstance(entry, dict):
                current_props.update(entry)

            elif isinstance(entry, list):
                if all(isinstance(item, str) and item.startswith("id") and item.endswith(":") for item in entry):
                    print(f"    - Header detected: {entry} (ignored)")
                    continue

                nodes = None
                inline_props = None

                if structure_type == "beams" and len(entry) >= 2:
                    nodes = [part.nodes.get(n) for n in entry[:2]]
                    inline_props = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else {}

                elif structure_type == "triangles" and len(entry) >= 3:
                    nodes = [part.nodes.get(n) for n in entry[:3]]
                    inline_props = entry[3] if len(entry) > 3 and isinstance(entry[3], dict) else {}

                if any(n is None for n in nodes):
                    # print(f"⚠️  Missing nodes accessed by element {entry[:len(entry)]}. Nodes may be missing or the part depends on  base JBeam. Try importing the matching .pc file.")
                    missing_node_warnings.add(tuple(entry[:len(nodes)]))
                    continue

                index = get_index([n.index for n in nodes]) if lookup else -1
                struct_id = tuple(sorted(entry[:len(nodes)]))

                if struct_id not in seen_structures:
                    seen_structures[struct_id] = 1
                else:
                    seen_structures[struct_id] += 1

                instance = seen_structures[struct_id]

                props = current_props.copy()
                props.update(inline_props)

                structures.append(
                    (Beam if structure_type == "beams" else Triangle)(
                        instance, struct_id,
                        nodes[0].id, nodes[1].id,
                        *([nodes[2].id] if len(nodes) > 2 else []),
                        index, props
                    )
                )

        if missing_node_warnings:
            print(f"⚠️  Missing node references detected while accessing {structure_type.capitalize().rstrip('s')} elements:")
            grouped_warnings = [', '.join([str(list(pair)) for pair in sorted(missing_node_warnings)[i:i+5]]) for i in range(0, len(missing_node_warnings), 5)]
            for group in grouped_warnings:
                print(f"    - {group}")
            print("💡 Nodes may be missing or the part depends on a base JBeam. Try importing the matching .pc file.")

        return structures

    def _parse_beams(self, json_beams, mesh=None, part_name=""):
        print(f"🧩 Parsing Beams 🟰  {part_name}")
        lookup = {tuple(sorted((e.vertices[0], e.vertices[1]))): e.index for e in mesh.edges} if mesh else None
        return self._parse_elements(json_beams, "beams", part_name, lookup)

    def _parse_triangles(self, json_triangles, mesh=None, part_name=""):
        print(f"🧩 Parsing triangles 📐 {part_name}")
        lookup = {tuple(sorted(f.vertices)): f.index for f in mesh.polygons} if mesh else None
        return self._parse_elements(json_triangles, "triangles", part_name, lookup)

    # deprecated function: used to get the vertex indices of a BeamNG's Jbeam Editor object mesh during conversion into this addon's Node Mesh
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

    def get_jbeam_parts(self) -> dict[JbeamPartName, JbeamPart]:
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

    @property
    def parse_source(self) -> JbeamLoadItem:
        return self.source
