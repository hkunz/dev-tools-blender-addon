import bpy
import os
import logging

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_parts_loader import JbeamPartsLoader
from unofficial_jbeam_editor.utils.jbeam.jbeam_pc_file_loader import JbeamPcFileLoader
from unofficial_jbeam_editor.utils.jbeam.jbeam_pc_parser import JbeamPcParser


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

    force_reload: bpy.props.BoolProperty(name="Force Reload", description="Force reloading of all selected files, bypassing the cache", default=True)  # type: ignore
    use_single_object: bpy.props.BoolProperty(name="Join Parts into One Object", description="Combine all parts into one object rather than keeping them separate", default=True)  # type: ignore

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')

        loader = JbeamPcFileLoader(self.filepath, self)
        data = loader.load(self.force_reload)
        
        if loader.model_file_path:
            logging.debug(f"Attempting to load the .jbeam file referenced by 'model': 📄 {loader.model_file_path}")
            bpy.ops.devtools_jbeam_editor.beamng_import_jbeam_file_to_node_mesh('EXEC_DEFAULT', filepath=str(loader.model_file_path), force_reload=self.force_reload)
            return {'FINISHED'}

        if not data:
            return {'CANCELLED'}

        self.parser = JbeamPcParser(self.filepath)
        success = self.parser.parse(data)

        if not success:
            return {'CANCELLED'}

        Utils.log_and_report(f"✅ Part Configurator Load Success: 📄 {self.filepath}", self, "INFO")
        config = JbeamPartsLoader(self.parser, self)
        config.load(self.use_single_object, self.force_reload)

        return {'FINISHED'}

    def draw(self, context: bpy.types.Context) -> None:
        self.options_panel = self.layout.box().column()
        self.options_panel.prop(self, "force_reload")
        self.options_panel.prop(self, "use_single_object")
