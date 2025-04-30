import bpy
import os
import logging

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_loader import JbeamFileLoader
from unofficial_jbeam_editor.utils.jbeam.jbeam_parser import JbeamParser
from unofficial_jbeam_editor.utils.jbeam.jbeam_models import JbeamLoadItem, JbeamJson, JbeamPart, JbeamPartID
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_creator import JbeamNodeMeshCreator
from unofficial_jbeam_editor.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator

class DEVTOOLS_JBEAMEDITOR_IMPORT_OT_BeamngImportJbeamToNodeMesh(Operator, ImportHelper):
    """Import a .jbeam file"""
    bl_idname = "devtools_jbeam_editor.beamng_import_jbeam_file_to_node_mesh"
    bl_label = "DevTools: Import Jbeam File"

    filename_ext = ".jbeam"
    filter_glob: StringProperty(
        default="*.jbeam",
        options={'HIDDEN'},
        maxlen=255,
    )  # type: ignore

    force_reload: bpy.props.BoolProperty(name="Force Reload", default=False)  # type: ignore

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        self.filename = os.path.basename(self.filepath)
        load_item = JbeamLoadItem(self.filepath)
        loader = JbeamFileLoader(load_item, operator=self)
        jbeam_json: JbeamJson = loader.load(self.force_reload)

        if not jbeam_json:
            return {'CANCELLED'}

        self.parser = JbeamParser(load_item)
        self.parser.parse(jbeam_json)

        self.create_node_meshes()
        Utils.log_and_report(f"✅ Import Success: 📄 {self.filepath}", self, "INFO")
        return {'FINISHED'}

    def create_node_meshes(self):
        logging.debug(f"🧊 Creating Node Meshes from jbeam part names in: 📄 {self.filepath}")
        jbeam_parts: dict[JbeamPartID, JbeamPart] = self.parser.get_jbeam_parts()
        for part_id, part in jbeam_parts.items():
            self.create_node_mesh(part_id)

    def create_node_mesh(self, part_id):
        logging.debug(f"🧰 {self.filename}: '{part_id}' > assembling part structure ...")
        nodes_list = self.parser.get_nodes_list(part_id)
        if not nodes_list:
            Utils.log_and_report(f"No nodes list in part '{part_id}'", self, "INFO")
            return
        mesh_name = f"{os.path.splitext(self.filename)[0]}.{part_id}"
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object(mesh_name)
        jmc.add_vertices(nodes_list)
        self.parser.parse_data_for_jbeam_object_conversion(obj, part_id, False)

        beams_list = self.parser.get_beams_list(part_id)
        tris_list = self.parser.get_triangles_list(part_id)
        jmc.add_edges(beams_list)
        jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, self.parser, part_id)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj