import bpy
import os

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_pc_parser import JbeamPcParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_pc_file_loader import JbeamPcFileLoader  # type: ignore


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
        self.pc_path = self.filepath
        self.filename = os.path.basename(self.pc_path)
        self.parser = JbeamPcParser()

        loader = JbeamPcFileLoader(self.pc_path, self.filename, self.parser)
        success = loader.try_load()

        if not success:
            Utils.log_and_report(f"Failed to parse PC file {self.filepath}", self, "ERROR")
            return {'CANCELLED'}

        Utils.log_and_report(f"Part Configurator Load Success: {self.filepath}", self, "INFO")
        return {'FINISHED'}
