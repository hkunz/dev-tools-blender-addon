import mathutils
import logging

from typing import Union

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_loader import JbeamLoadItem
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JbeamJson, JbeamPart, JbeamSlotType, NodeID, Node, Beam, Triangle, JbeamPartID, JbeamPartSectionName, JbeamPartData, JsonJbeamElement, JbeamElementProps


class JbeamParser:
    def __init__(self, source:JbeamLoadItem=None):
        self.source = source
        self.jbeam_main_part = None
        self.jbeam_parts: dict[JbeamPartID, JbeamPart] = {}

    def parse(self, jbeam_json: JbeamJson):
        load_item = self.source
        #logging.debug(f"\n🧩 Prepare parsing Nodes from: 📄 {load_item.file_path}")
        for part_name, part_data in jbeam_json.items():
            p = JbeamPart()
            p.part_name = part_name

            if "slotType" in part_data:
                p.slot_type = part_data.get("slotType")
                if p.slot_type == "main":
                    self.jbeam_main_part = p

            if "refNodes" in part_data:
                headers, values = part_data["refNodes"]
                p.refnodes = {h[:-1]: v for h, v in zip(headers[:], values[:])}  # Trim last char from keys

            if load_item.is_part_set and load_item.part_id != p.id:
                # logging.debug(f" - Ignore irrelevant part {p.part_name} with slot type {p.slot_type}")
                continue

            if "slots" in part_data:
                slot_rows = part_data["slots"]
                if isinstance(slot_rows, list) and len(slot_rows) > 1:
                    p.slots = [row[0] for row in slot_rows[1:] if isinstance(row, list) and len(row) > 0]
            nodes = self._get_section("nodes", part_data)
            logging.debug(f"🧩 Parsing Nodes ⚪ {part_name}")
            if nodes:
                p.nodes_list = self._parse_nodes(nodes)
            else:
                logging.debug(f"    - No Nodes found in {part_name}.")
            p.json_beams = self._get_section("beams", part_data)
            p.json_triangles = self._get_section("triangles", part_data)
            p.json_quads = self._get_section("quads", part_data)

            self.jbeam_parts[p.id] = p
            logging.debug(f"    - Registered part {p}")

    def _get_section(self, section_name: JbeamPartSectionName, part_data: JbeamPartData) -> list[Union[JbeamElementProps, JsonJbeamElement]]:
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
                    logging.debug(f"⚠️  WARNING: entry {entry} not a proper quad (ignored)")
            else:
                result.append(entry)  # Keep dicts and others as-is
        return result

    def parse_data_for_jbeam_object_conversion(self, obj, part_id="", get_vertex_indices=True):
        mesh = obj.data
        part = self.get_jbeam_part(part_id)
        try:
            if get_vertex_indices:
                self._retrieve_closest_vertex_indices(obj, part)
            part.nodes.update({node.id: node for node in part.nodes_list})
            part.beams_list = self._parse_beams(part.json_beams, mesh, part_id)
            part.triangles_list = self._parse_triangles(part.json_triangles, mesh, part_id)
            if not part.json_quads:
                return
            logging.debug("Extend triangles list with quads")
            tris_from_quads = self._split_quads_into_triangles(part.json_quads)
            tris_from_quads_list = self._parse_triangles(tris_from_quads, mesh, part_id)
            part.triangles_list = (part.triangles_list or []) + tris_from_quads_list

        except Exception as e:
            Utils.log_and_raise(f"An error occurred while processing the remaining JBeam data: {e}", RuntimeError, e)   

    def _parse_nodes(self, json_nodes: list):
        nodes: list[Node] = []
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
                    logging.debug(f"⚠️  Warning: Duplicate node '{node_id}' found and skipped ...")
                    continue  # Skip duplicate node_id

                seen_node_ids.add(node_id)
                position = mathutils.Vector((x, y, z))
                props = current_props.copy()
                props.update(inline_props)
                instance = 1 # only 1 instance can exist of one node ID unlike beams and triangles that can have multiple instances
                nodes.append(Node(instance, node_id, -1, position, props))

        return nodes

    def _parse_elements(self, json_data, structure_type, part_id="", lookup=None):
        """ Generic parser for beams and triangles """
        structures, current_props = [], {}
        part = self.get_jbeam_part(part_id)

        def get_index(indices):
            return lookup.get(tuple(sorted(indices)))

        if not json_data:
            logging.debug(f"No {structure_type} to parse because JSON data doesn't have '{structure_type}' node in JBeam part '{part.id}'")
            return

        seen_structures = {}  # Track unique beams/triangles and their instance counts
        missing_node_warnings = []

        # TODO # FIXME This is still a workaround which needs to be fixed: nodes are not found for the base part because they are in the child part but we maybe need the dummy nodes
        def get_or_create_dummy_node(self, part, name):
            if name not in part.nodes:
                dummy = Node(instance=1, node_id=name, index=-1, position=(0,0,0))  # or some other sentinel index
                part.nodes[name] = dummy
            return part.nodes[name]

        for entry in json_data:
            if isinstance(entry, dict):
                current_props.update(entry)

            elif isinstance(entry, list):
                if all(isinstance(item, str) and item.startswith("id") and item.endswith(":") for item in entry):
                    logging.debug(f"    - Header detected: {entry} (ignored)")
                    continue

                nodes = None
                inline_props = None

                if structure_type == "beams" and len(entry) >= 2:
                    nodes = [part.nodes.get(n) or get_or_create_dummy_node(self, part, n) for n in entry[:2]]  # nodes = [part.nodes.get(n) for n in entry[:2]]
                    inline_props = entry[2] if len(entry) > 2 and isinstance(entry[2], dict) else {}

                elif structure_type == "triangles" and len(entry) >= 3:
                    nodes = [part.nodes.get(n) or get_or_create_dummy_node(self, part, n) for n in entry[:3]]  # nodes = [part.nodes.get(n) for n in entry[:3]]
                    inline_props = entry[3] if len(entry) > 3 and isinstance(entry[3], dict) else {}

                if any(n is None for n in nodes):
                    # Store which node names were missing
                    missing = [name for name, node in zip(entry, nodes) if node is None]
                    missing_node_warnings.append((entry[:len(nodes)], missing))
                    continue # FIXME nodes are not found for the base part because they are in the child part

                index = get_index([n.index for n in nodes]) if lookup else -1
                struct_id = tuple(sorted(entry[:len(nodes)]))

                seen_structures[struct_id] = seen_structures.get(struct_id, 0) + 1
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
            logging.debug(f"⚠️  Missing node references detected while accessing {structure_type.capitalize().rstrip('s')} elements:")
            for full_entry, missing_names in missing_node_warnings:
                logging.debug(f"    - {full_entry} (missing: {missing_names})")
            logging.debug("💡 Nodes may be missing or the part depends on a base JBeam. Try importing the matching .pc file.")

        return structures

    def _parse_beams(self, json_beams, mesh=None, part_id=""):
        logging.debug(f"🧩 Parsing Beams 🟰  {part_id}")
        lookup = {tuple(sorted((e.vertices[0], e.vertices[1]))): e.index for e in mesh.edges} if mesh else None
        return self._parse_elements(json_beams, "beams", part_id, lookup)

    def _parse_triangles(self, json_triangles, mesh=None, part_id=""):
        logging.debug(f"🧩 Parsing triangles 📐 {part_id}")
        lookup = {tuple(sorted(f.vertices)): f.index for f in mesh.polygons} if mesh else None
        return self._parse_elements(json_triangles, "triangles", part_id, lookup)

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

    def debug_print_nodes(self, part_id=""):
        part = self.get_jbeam_part(part_id)
        if not part:
            logging.debug(f"Part '{part_id}' not found.")
            return
        nodes: dict[NodeID, Node] = part.nodes
        items = nodes.items() # Iterable[Tuple[NodeID, Node]]
        for node_id, node in items:
            logging.debug(f"{node_id} => {node}")
            # i.e.: 'node_1' => Node(instance=1, id=a1ll, index=5, pos=<Vector (0.6800, -0.9350, 0.1100)>, props={'frictionCoef': 1.2, 'nodeMaterial': '|NM_RUBBER', 'nodeWeight': 1, 'collision': True, 'selfCollision': True, 'group': 'mattress'})

    def get_jbeam_parts(self) -> dict[JbeamPartID, JbeamPart]:
        return self.jbeam_parts

    def get_jbeam_part(self, part_id: str = "") -> JbeamPart | None:
        if part_id:
            if part_id not in self.jbeam_parts:
                logging.debug(f"Parser: No part 'slot_type:part_name'='{part_id}' found")
                return None
            return self.jbeam_parts.get(part_id)
        return next(iter(self.jbeam_parts.values()), None)

    def _get_jbeam_part_main(self):
        return self._get_jbeam_part_by_slot_type("main")

    def _get_jbeam_part_by_slot_type(self, slot_type: str) -> JbeamPart | None:
        for part in self.jbeam_parts.values():
            if part.slot_type == slot_type:
                return part
        if self.jbeam_main_part:
            return self.jbeam_main_part
        # logging.debug(f"Parser: No part with slot_type '{slot_type}' found")
        return None

    def find_part_with_slottable_slot_type(self, slot_type: JbeamSlotType) -> JbeamPart:
        for part in self.jbeam_parts.values():
            if slot_type in part.slots:
                return part
        logging.debug(f"JbeamParser: No part found with a slot accepting slot_type '{slot_type}'")
        return None

    def get_nodes(self, part_id: str = "") -> dict[NodeID, Node]:
        part = self.get_jbeam_part(part_id)
        return part.nodes if part else {}

    def get_nodes_list(self, part_id: str = "") -> list[Node]:
        part = self.get_jbeam_part(part_id)
        return part.nodes_list if part else []

    def get_beams_list(self, part_id: str = "") -> list[Beam]:
        part = self.get_jbeam_part(part_id)
        return part.beams_list if part else []

    def get_triangles_list(self, part_id: str = "") -> list[Triangle]:
        part = self.get_jbeam_part(part_id)
        return part.triangles_list if part else []

    def get_ref_nodes(self, part_id: str = "") -> dict[str, str]:
        part = self.get_jbeam_part(part_id)
        if part and part.refnodes:
            return part.refnodes
        part = self._get_jbeam_part_main()
        if part and part.refnodes:
            return part.refnodes
        # logging.debug(f"[JBeam Parser] No refnodes found for part `{part_id}` or main part: '{part.part_name if part else 'None'}'")
        return {}

    @property
    def parse_source(self) -> JbeamLoadItem:
        return self.source
