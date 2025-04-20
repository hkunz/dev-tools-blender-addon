import bpy
import os

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
        self.mesh_creators: dict[JbeamPartID, JbeamNodeMeshCreator] = {}

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
        #self._create_node_meshes(parsers)

    def _create_node_meshes(self, parsers: list[JbeamParser]):
        print(f"\n🧊 Creating Node Meshes from selected jbeam part names in: 📄 {self.filepath}")
        for parser in parsers:
            load_item: JbeamLoadItem = parser.parse_source
            jbeam_parts: dict[JbeamPartID, JbeamPart] = parser.get_jbeam_parts()
            for part_id, part in jbeam_parts.items():
                if part_id == load_item.part_id:
                    for other_parser in parsers:
                        if parser == other_parser:
                            continue
                        other_jbeam_parts: dict[JbeamPartID, JbeamPart] = other_parser.get_jbeam_parts()
                        for other_part_name, other_part in other_jbeam_parts.items():
                            if other_part_name in part.slots:
                                self._create_node_mesh(parser)

    def _create_node_mesh(self, parser: JbeamParser):
        load_item = parser.parse_source
        part_name = load_item.part_name
        slot_type = load_item.slot_type
        part_id = JbeamPart.generate_id(slot_type, part_name)
        print(f"🧰 {self.filename}: '{part_id}' > assembling part structure ...")
        nodes_list: list[Node] = parser.get_nodes_list(part_id)
        if not nodes_list:
            Utils.log_and_report(f"No nodes list in part name '{part_id}'", self.operator, "INFO")
            return
        jmc = self.mesh_creators
        mesh_name = f"{os.path.splitext(self.filename)[0]}.{part_id}"
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object(mesh_name)
        jmc.add_vertices(nodes_list)
        parser.parse_data_for_jbeam_object_conversion(obj, part_id, False)

        beams_list = parser.get_beams_list(part_id)
        tris_list = parser.get_triangles_list(part_id)
        jmc.add_edges(beams_list)
        jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, parser, part_id)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj