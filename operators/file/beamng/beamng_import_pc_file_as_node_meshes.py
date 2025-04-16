import bpy
import os

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson, JbeamPart, NodeID, Node, Beam, Triangle, JbeamPartName, JbeamPartData  # type: ignore
from dev_tools.utils.jbeam.jbeam_loader import JbeamFileLoader  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_pc_parser import JbeamPcParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_pc_file_loader import JbeamPcFileLoader  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_creator import JbeamNodeMeshCreator  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator  # type: ignore


class DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportPcFileToNodeMeshes(Operator, ImportHelper):
    """Import a .jbeam file"""
    bl_idname = "devtools_jbeam_editor.beamng_import_pc_file_to_node_meshes"
    bl_label = "DevTools: Import PC File"

    filename_ext = ".pc"
    filter_glob: StringProperty(
        default="*.pc",
        options={'HIDDEN'},
        maxlen=255,
    )  # type: ignore

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        #self.pc_path = self.filepath
        self.filename = os.path.basename(self.filepath)
        loader = JbeamPcFileLoader(self.filepath, self)
        data = loader.load()

        if not data:
            return {'CANCELLED'}

        self.directory = os.path.dirname(self.filepath)
        self.parser = JbeamPcParser(self.directory)
        self.parser.parse(data)
        Utils.log_and_report(f"✅ Part Configurator Load Success: {self.filepath}", self, "INFO")
        self._load_jbeam_files()
        return {'FINISHED'}

    def _load_jbeam_files(self):
        load_items: list[JbeamLoadItem] = self.parser.get_jbeam_load_items()
        print("Load items:", load_items)
        for load_item in load_items:
            loader = JbeamFileLoader(load_item, operator=self)
            jbeam_json: JbeamJson = loader.load()
            if not jbeam_json:
                continue
            parser = JbeamParser()
            parser.parse(jbeam_json)
            self._create_node_meshes(parser, load_item)

    def _create_node_meshes(self, parser: JbeamParser, load_item: JbeamLoadItem):
        dict[JbeamPartName, JbeamPartData]
        jbeam_parts: dict[JbeamPartName, JbeamPart] = parser.get_jbeam_parts()
        for part_name, part in jbeam_parts.items():
            if part_name == load_item.part_name and part.slot_type == load_item.slot_type:
                self._create_node_mesh(parser, part_name)

    def _create_node_mesh(self, parser: JbeamParser, part_name):
        print(f"Creating Part with name '{part_name}' ================================>")
        nodes_list: list[Node] = parser.get_nodes_list(part_name)
        if not nodes_list:
            Utils.log_and_report(f"No nodes list in part name '{part_name}'", self, "INFO")
            return
        mesh_name = f"{os.path.splitext(self.filename)[0]}.{part_name}"
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object(mesh_name)
        jmc.add_vertices(nodes_list)
        parser.parse_data_for_jbeam_object_conversion(obj, part_name, False)

        beams_list = parser.get_beams_list(part_name)
        tris_list = parser.get_triangles_list(part_name)
        jmc.add_edges(beams_list)
        jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, parser, part_name)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj