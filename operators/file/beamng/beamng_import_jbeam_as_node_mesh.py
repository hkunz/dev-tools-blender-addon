import bpy
import os

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_loader import JbeamFileLoader  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_creator import JbeamNodeMeshCreator  # type: ignore
from dev_tools.utils.jbeam.jbeam_node_mesh_configurator import JbeamNodeMeshConfigurator  # type: ignore

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

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        self.filename = os.path.basename(self.filepath)
        loader = JbeamFileLoader(self.filepath, operator=self)
        try:
            self.parser = loader.load()
        except Exception:
            return {'CANCELLED'}

        self.create_node_meshes()
        Utils.log_and_report(f"✅ Import Success: {self.filename}", self, "INFO")
        return {'FINISHED'}

    def create_node_meshes(self):
        jbeam_parts: dict[str, object] = self.parser.get_jbeam_parts()
        for part_name, part in jbeam_parts.items():
            self.create_node_mesh(part_name)

    def create_node_mesh(self, part_name):
        print(f"Creating Part with name '{part_name}' ================================>")
        nodes_list = self.parser.get_nodes_list(part_name)
        if not nodes_list:
            Utils.log_and_report(f"No nodes list in part name '{part_name}'", self, "INFO")
            return
        mesh_name = f"{os.path.splitext(self.filename)[0]}.{part_name}"
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object(mesh_name)
        jmc.add_vertices(nodes_list)
        self.parser.parse_data_for_jbeam_object_conversion(obj, part_name, False)

        beams_list = self.parser.get_beams_list(part_name)
        tris_list = self.parser.get_triangles_list(part_name)
        jmc.add_edges(beams_list)
        jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, self.parser, part_name)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj