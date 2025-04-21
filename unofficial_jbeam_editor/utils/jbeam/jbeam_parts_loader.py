import bpy
import os

from collections import defaultdict
from unofficial_jbeam_editor.utils.jbeam.jbeam_parser import JbeamParser
from unofficial_jbeam_editor.utils.jbeam.jbeam_loader import JbeamFileLoader
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson, JbeamPart, JbeamPartID
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
        self.operator = operator
        self.pc_parser = pc_parser
        self.mesh_creators: dict[PartGroupID, JbeamNodeMeshCreator] = {}

    def load(self, force_reload=False):
        load_items = self.pc_parser.get_jbeam_load_items()
        if force_reload:
            for load_item in load_items:
                JbeamFileLoader.clear_cache(load_item.file_path)

        parsers = self._load_and_parse_files(load_items)
        self._create_node_meshes(parsers)

    def _load_and_parse_files(self, load_items):
        print(f"\n⏳🔄 Preparing to load Jbeam Load Items:\n    - " + "\n    - ".join(str(item) for item in load_items))
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
        print(f"\n⏳🧩 Prepare parsing Beams and Triangles from loaded JBeam files to generate Node Meshes.")
        grouped_parts = self._group_parts(parsers)
        self._process_grouped_parts(grouped_parts)

    def _group_parts(self, parsers):
        # print(f"\n🧊 Grouping Parts from selected Jbeam files")
        visited_parts: set[JbeamPartID] = set()
        grouped_parts: list[GroupedPart] = []
        group_counter: PartGroupID = 0

        parsers_by_id = {parser.get_jbeam_part(part.id).id: parser for parser in parsers for part in parser.jbeam_parts.values()}

        def can_be_grouped_with(source, candidate):
            # print(f"Evaluating if '{candidate.slot_type}:{candidate.id}' can fit into slots of '{source.slot_type}:{source.id}'")
            for slot in source.slots:
                slot_type = slot[0] if isinstance(slot, (list, tuple)) else slot
                # print(f"Source slot accepts: '{slot_type}'")
                if candidate.slot_type == slot_type:
                    # print(f"✅ MATCH: Candidate slotType fits into source slotType")
                    return True
            # print(f"❌ NO MATCH found")
            return False

        for parser in parsers:
            load_item = parser.parse_source
            jbeam_part = parser.get_jbeam_part(load_item.part_id)
            if jbeam_part.id in visited_parts:
                continue

            # print(f"\n🔹 Starting new group {group_counter} from root part: {jbeam_part.slot_type}:{jbeam_part.id}")
            group = self._explore_and_group_parts(parsers_by_id, jbeam_part, visited_parts, group_counter, can_be_grouped_with)
            grouped_parts.extend(group)
            # print(f"Finalized group {group_counter} with {len(group)} part(s): {[p.id for p in group]}")
            group_counter += 1

        return grouped_parts

    def _explore_and_group_parts(self, parsers_by_id, root_part, visited_parts, group_counter, can_be_grouped_with):
        group: list[GroupedPart] = []
        queue = [(root_part, 0)]  # Start with root part at level 0

        while queue:
            current_part, level = queue.pop(0)
            if current_part.id in visited_parts:
                continue

            # print(f"Exploring part: {current_part.slot_type}:{current_part.id} (Level {level})")
            current_parser = parsers_by_id.get(current_part.id)
            if not current_parser:
                continue

            grouped_part = GroupedPart(current_part, group_counter, level, current_parser)
            group.append(grouped_part)
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
            for part in parts:
                # print(f"Part ID: {part.id}, Group ID: {part.group_id}, Level: {part.level}, Parser: {part.parser.parse_source}")
                self._assemble_node_mesh(part.parser, part.group_id)

    def _assemble_node_mesh(self, parser, group):
        load_item = parser.parse_source
        part_name = load_item.part_name
        slot_type = load_item.slot_type
        part_id = JbeamPart.generate_id(slot_type, part_name)
        print(f"🧰 {group}: '{part_id}' > assembling part structure ...")
        nodes_list = parser.get_nodes_list(part_id)
        if not nodes_list:
            Utils.log_and_report(f"No nodes list in part name '{part_id}'", self.operator, "INFO")
            return

        jmc:JbeamNodeMeshCreator | None = self.mesh_creators.get(group)
        init: bool = jmc is None
        if init:
            jmc = JbeamNodeMeshCreator()
            mesh_name = str(group)
            obj = jmc.create_object(mesh_name)
            self.mesh_creators[group] = jmc
        else:
            obj = jmc.obj

        if nodes_list:
            jmc.add_vertices(nodes_list)

        parser.parse_data_for_jbeam_object_conversion(obj, part_id, False)

        beams_list = parser.get_beams_list(part_id)
        tris_list = parser.get_triangles_list(part_id)
        if beams_list:
            jmc.add_edges(beams_list)
        if tris_list:
            jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, parser, part_id, init)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
