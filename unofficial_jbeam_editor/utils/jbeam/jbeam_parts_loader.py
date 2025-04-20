import bpy
import os
from collections import defaultdict

from unofficial_jbeam_editor.utils.jbeam.jbeam_loader import JbeamFileLoader
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson, JbeamPart, NodeID, Node, Beam, Triangle, JbeamSlotType, JbeamPartName, JbeamPartID, JbeamPartData
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_creator import JbeamNodeMeshCreator
from unofficial_jbeam_editor.utils.jbeam.jbeam_parser import JbeamParser
from unofficial_jbeam_editor.utils.jbeam.jbeam_pc_parser import JbeamPcParser

from unofficial_jbeam_editor.utils.utils import Utils

class JbeamPartsLoader:
    def __init__(self, pc_parser: JbeamPcParser, operator):
        self.operator = operator
        self.pc_parser: JbeamPcParser = pc_parser
        self.mesh_creators: dict[int, JbeamNodeMeshCreator] = {}

    def load(self, force_reload=False):

        load_items: list[JbeamLoadItem] = self.pc_parser.get_jbeam_load_items()
        if force_reload:
            for load_item in load_items:
                JbeamFileLoader.clear_cache(load_item.file_path)
        parsers: list[JbeamParser] = []
        
        print("\n⏳🔄 Preparing to load Jbeam Load Items:\n" + "    - " + "\n    - ".join(str(item) for item in load_items))

        for load_item in load_items:
            loader = JbeamFileLoader(load_item, operator=self.operator)
            jbeam_json: JbeamJson = loader.load()
            if not jbeam_json:
                continue
            parser = JbeamParser(load_item)
            parser.parse(jbeam_json)
            parsers.append(parser)

        print("\n⏳🧩 Prepare parsing Beams and Triangles from loaded JBeam files to generate Node Meshes:\n" + "    - " + "\n    - ".join(str(item) for item in load_items))
        self._create_node_meshes(parsers)

    def _create_node_meshes(self, parsers: list[JbeamParser]):
        print(f"\n🧊 Creating Node Meshes from selected jbeam part names in: 📄 {self.pc_parser.pc.filepath}")

        grouped_parts = []
        visited_parts = set()
        group_counter = 0

        def can_be_grouped_with(source: JbeamPart, candidate: JbeamPart) -> bool:
            print(f"         🔧 Evaluating if '{candidate.slot_type}:{candidate.id}' can fit into slots of '{source.slot_type}:{source.id}'")
            for slot in source.slots:
                if isinstance(slot, (list, tuple)):
                    slot_type = slot[0]
                else:
                    slot_type = slot  # handle plain string slots

                print(f"           - Source slot accepts: '{slot_type}'")
                if candidate.slot_type == slot_type:
                    print(f"             ✅ MATCH: Candidate slotType '{candidate.slot_type}' fits into '{slot_type}'")
                    return True

            print(f"             ❌ NO MATCH found for {candidate.slot_type}")
            return False

        for parser in parsers:
            load_item: JbeamLoadItem = parser.parse_source
            jbeam_part: JbeamPart = parser.get_jbeam_part(load_item.part_id)

            if jbeam_part.id in visited_parts:
                continue

            print(f"\n🔹 Starting new group {group_counter} from root part: {jbeam_part.slot_type}:{jbeam_part.id}")
            group = []
            queue = [(jbeam_part, 0)]

            while queue:
                current_part, level = queue.pop(0)

                if current_part.id in visited_parts:
                    continue

                print(f"  🔍 Exploring part: {current_part.slot_type}:{current_part.id} (Level {level})")
                print(f"      SlotType: {current_part.slot_type}")
                print(f"      Raw Slots: {current_part.slots}")
                print(f"      Parsed Slots (accepts): {[slot if isinstance(slot, str) else slot[0] for slot in current_part.slots]}")
                current_parser = next(p for p in parsers if p.get_jbeam_part(current_part.id) == current_part)

                group.append({
                    "id": current_part.id,
                    "group_id": group_counter,
                    "level": level,
                    "parser": current_parser
                })
                visited_parts.add(current_part.id)

                # Check against all other parts
                for other_parser in parsers:
                    for candidate in other_parser.jbeam_parts.values():
                        if candidate.id in visited_parts or candidate.id == current_part.id:
                            continue

                        print(f"      🧪 Checking candidate: {candidate.slot_type}:{candidate.id}")
                        print(f"         Candidate slotType: {candidate.slot_type}")
                        print(f"         Candidate slots: {candidate.slots}")

                        if can_be_grouped_with(current_part, candidate):
                            print(f"         🔗 Adding to queue: {candidate.slot_type}:{candidate.id}")
                            queue.append((candidate, level + 1))

            if group:
                grouped_parts.extend(group)
                print(f"✅ Finalized group {group_counter} with {len(group)} part(s): {[p['id'] for p in group]}")
                group_counter += 1

        print("\n=== GROUPED RESULTS ===")
        for part in grouped_parts:
            print(f"Part ID: {part['id']}, Group ID: {part['group_id']}, Level: {part['level']}")
        reversed_parts = list(reversed(grouped_parts))

        # Group parts by group_id
        grouped_by_id = defaultdict(list)
        for part in grouped_parts:
            grouped_by_id[part["group_id"]].append(part)

        # Now sort the parts in each group by descending level
        for group_id in grouped_by_id:
            grouped_by_id[group_id] = sorted(grouped_by_id[group_id], key=lambda p: p["level"], reverse=True)

        # Print out the parts in the new order
        for group_id in grouped_by_id:
            for part in grouped_by_id[group_id]:
                print(f"Part ID: {part['id']}, Group ID: {part['group_id']}, Level: {part['level']}, Parser: {part['parser'].parse_source}")
                self._create_node_mesh(part['parser'], part['group_id'])






    def _create_node_mesh(self, parser: JbeamParser, group: int):
        load_item = parser.parse_source
        part_name = load_item.part_name
        slot_type = load_item.slot_type
        part_id = JbeamPart.generate_id(slot_type, part_name)
        print(f"🧰 {group}: '{part_id}' > assembling part structure ...")
        nodes_list: list[Node] = parser.get_nodes_list(part_id)
        if not nodes_list:
            Utils.log_and_report(f"No nodes list in part name '{part_id}'", self.operator, "INFO")
            return
        jmc = self.mesh_creators.get(group)
        if jmc is None:
            jmc = JbeamNodeMeshCreator()
            mesh_name = str(group) #f"{os.path.splitext(self.filename)[0]}.{part_id}"
            obj = jmc.create_object(mesh_name)
            self.mesh_creators[group] = jmc

        # Add vertices (this is done for both new and existing instances)
        if nodes_list:
            jmc.add_vertices(nodes_list)
        parser.parse_data_for_jbeam_object_conversion(obj, part_id, False)

        beams_list = parser.get_beams_list(part_id)
        tris_list = parser.get_triangles_list(part_id)
        if beams_list:
            jmc.add_edges(beams_list)
        if tris_list:
            jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, parser, part_id)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj