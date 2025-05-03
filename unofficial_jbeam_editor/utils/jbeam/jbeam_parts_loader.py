import bpy
import logging
from collections import defaultdict

from unofficial_jbeam_editor.utils.jbeam.jbeam_parser import JbeamParser
from unofficial_jbeam_editor.utils.jbeam.jbeam_loader import JbeamFileLoader
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import NodeID, Node, JbeamLoadItem, JbeamJson, JbeamPart, JbeamPartID
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_creator import JbeamNodeMeshCreator
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator
from unofficial_jbeam_editor.utils.utils import Utils

PartGroupID = str

class GroupedPart:
    def __init__(self, part, group_id, level, parser):
        self.id = part.id
        self.group_id: PartGroupID = group_id
        self.level = level
        self.parser = parser

    def __repr__(self):
        return f"GroupedPart(id={self.id}, group_id={self.group_id}, level={self.level}, parser={self.parser.parse_source})"

class JbeamPartsLoader:
    def __init__(self, pc_parser, operator):
        self.single_object = False  # assemble .pc as single object if True else assemble as separate objects
        self.operator = operator
        self.pc_parser = pc_parser
        self.mesh_creators: dict[PartGroupID, JbeamNodeMeshCreator] = {}

    def load(self, force_reload=False):
        load_items = self.pc_parser.get_jbeam_load_items()
        if force_reload:
            for load_item in load_items:
                JbeamFileLoader.clear_cache(load_item.file_path)

        parsers = self._load_and_parse_files(load_items)
        if parsers:
            self._create_node_meshes(parsers)

    def _load_and_parse_files(self, load_items):
        if not load_items:
            return []
        logging.debug(f"⏳🔄 Preparing to load Jbeam Load Items:\n    - " + "\n    - ".join(str(item) for item in load_items))
        parsers = []
        for load_item in load_items:
            loader = JbeamFileLoader(load_item, operator=self.operator)
            jbeam_json = loader.load()
            if not jbeam_json:
                continue
            parser = JbeamParser(load_item)
            parser.parse(jbeam_json)
            parsers.append(parser)
        return parsers

    def _create_node_meshes(self, parsers):
        logging.debug("⏳🧩 Parsing beams and triangles to generate node meshes.")
        grouped_parts = self._create_single_group(parsers) if self.single_object else self._group_parts(parsers)
        self._process_grouped_parts(grouped_parts)

    def _create_single_group(self, parsers):
        """Assign all parts into a single group (group_id=0) and return them as a flat list."""
        grouped_parts = []
        for parser in parsers:
            for part in parser.jbeam_parts.values():
                part.group_id = 0
                part.level = 0
                part.parser = parser
                grouped_parts.append(part)
        return grouped_parts


    def _group_parts(self, parsers):
        # logging.debug(f"🧊 Grouping Parts from selected Jbeam files")
        visited_parts: set[JbeamPartID] = set()
        grouped_parts: list[GroupedPart] = []
        group_counter: PartGroupID = 0

        parsers_by_id = {
            part.id: parser
            for parser in parsers
            for part in parser.jbeam_parts.values()
        }

        def can_be_grouped_with(source, candidate):
            # logging.debug(f"Evaluating if '{candidate.slot_type}:{candidate.id}' can fit into slots of '{source.slot_type}:{source.id}'")
            for slot in source.slots:
                slot_type = slot[0] if isinstance(slot, (list, tuple)) else slot
                # logging.debug(f"Source slot accepts: '{slot_type}'")
                if candidate.slot_type == slot_type:
                    # logging.debug(f"✅ MATCH: Candidate slotType fits into source slotType")
                    return True
            # logging.debug(f"❌ No match found for slot type '{slot_type}'")
            return False

        for parser in parsers:
            load_item = parser.parse_source
            jbeam_part = parser.get_jbeam_part(load_item.part_id)
            if not jbeam_part or jbeam_part.id in visited_parts:
                continue

            # logging.debug(f"🔹 Starting new group {group_counter} from root part: {jbeam_part.slot_type}:{jbeam_part.id}")
            group = self._explore_and_group_parts(parsers_by_id, jbeam_part, visited_parts, group_counter, can_be_grouped_with)
            grouped_parts.extend(group)
            # logging.debug(f"Finalized group {group_counter} with {len(group)} part(s): {[p.id for p in group]}")
            group_counter += 1

        return grouped_parts

    def _explore_and_group_parts(self, parsers_by_id, root_part, visited_parts, group_counter, can_be_grouped_with):
        group: list[GroupedPart] = []
        queue = [(root_part, 0)]  # Start with root part at level 0

        while queue:
            current_part, level = queue.pop(0)
            if current_part.id in visited_parts:
                continue

            # logging.debug(f"Exploring part: {current_part.slot_type}:{current_part.id} (Level {level})")
            current_parser = parsers_by_id.get(current_part.id)
            if not current_parser:
                continue

            group.append(GroupedPart(current_part, group_counter, level, current_parser))
            visited_parts.add(current_part.id)

            for other_parser in parsers_by_id.values():
                for candidate in other_parser.jbeam_parts.values():
                    if candidate.id in visited_parts or candidate.id == current_part.id:
                        continue
                    if can_be_grouped_with(current_part, candidate):
                        queue.append((candidate, level + 1))

        return group

    def _process_grouped_parts(self, grouped_parts):
        grouped_by_id = defaultdict(list)
        for part in grouped_parts:
            grouped_by_id[part.group_id].append(part)

        for group_id, parts in grouped_by_id.items():
            grouped_by_id[group_id] = sorted(parts, key=lambda p: p.level, reverse=True)

        for group_id, parts in grouped_by_id.items():
            any_nodes_added = False
            for part in parts:
                # logging.debug(f"Part ID: {part.id}, Group ID: {part.group_id}, Level: {part.level}, Parser: {part.parser.parse_source}")
                success = self._assemble_node_mesh_nodes(part.parser, part.group_id)
                any_nodes_added = any_nodes_added or success

            if not any_nodes_added:
                Utils.log_and_report(f"⚠️  Skipped mesh creation for group {group_id} (no nodes found).", self.operator, "INFO")
                continue

            nodes: dict[NodeID, Node] = {}
            node_origins: dict[NodeID, str] = {}  # Track which part added the node
            refnodes: dict[str, str] = {}
            refnodes_set = False

            for part in parts:
                for node_id, node in part.parser.get_nodes(part.id).items():
                    if node_id in nodes:
                        prev_part_id = node_origins.get(node_id, "unknown")
                        # logging.warning(f"⚠️  Duplicate node ID detected: '{node_id}' {node.position}" f"(already from part '{prev_part_id}', now also in part '{part.id}')")
                        if self.single_object:
                            continue
                    nodes[node_id] = node
                    node_origins[node_id] = part.id

                refnodes.update(part.parser.get_ref_nodes(part.id))
                self._assemble_node_mesh_beams_and_tris(part.parser, part.group_id)

            root_part = max(parts, key=lambda p: -p.level)
            mesh_name = root_part.id
            jmc, init = self._get_jbeam_mesh_creator(group_id)
            jmc.obj.name = jmc.obj.data.name = mesh_name

            Utils.log_and_report(f"✅ Created jbeam node mesh '{jmc.obj.name}'", self.operator, "INFO")

            success = JbeamNodeMeshConfigurator.assign_ref_nodes(jmc.obj, refnodes, nodes)
            refnodes_set = refnodes_set or success

            if not refnodes_set:
                Utils.log_and_report("No objects have refnodes assigned.", "INFO")

    def _get_jbeam_mesh_creator(self, group: PartGroupID) -> tuple[JbeamNodeMeshCreator, bool]:
        jmc = self.mesh_creators.get(group)
        if jmc:
            return jmc, False
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object(str(group))
        self.mesh_creators[group] = jmc
        return jmc, True

    def _assemble_node_mesh_nodes(self, parser, group):
        load_item = parser.parse_source
        part_id = JbeamPart.generate_id(load_item.slot_type, load_item.part_name)
        logging.debug(f"🧰 {group}: '{part_id}' > assembling part structure > Nodes ...")
        nodes_list = parser.get_nodes_list(part_id)

        if not nodes_list:
            Utils.log_and_report(f"No nodes in part '{part_id}', skipping ...", self.operator, "INFO")
            return False

        jmc, init = self._get_jbeam_mesh_creator(group)
        obj = jmc.obj
        jmc.add_vertices(nodes_list)
        parser.parse_data_for_jbeam_object_conversion(obj, part_id, False)
        JbeamNodeMeshConfigurator.process_node_mesh_props_for_nodes(obj, parser, part_id, init)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        return True

    def _assemble_node_mesh_beams_and_tris(self, parser, group):
        load_item = parser.parse_source
        part_id = JbeamPart.generate_id(load_item.slot_type, load_item.part_name)
        logging.debug(f"🧰 {group}: '{part_id}' > assembling part structure > Beams and Triangles ...")

        jmc, _ = self._get_jbeam_mesh_creator(group)
        obj = jmc.obj

        beams_list = parser.get_beams_list(part_id)
        tris_list = parser.get_triangles_list(part_id)

        if beams_list:
            jmc.add_edges(beams_list)
        if tris_list:
            jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props_for_beams_and_tris(obj, parser, part_id)
