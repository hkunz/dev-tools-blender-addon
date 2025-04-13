import bpy
import re
import os
import json

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.json_cleanup import json_cleanup  # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.jbeam.jbeam_pc_parser import JbeamPcParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore

class PartConfig:
    def __init__(self):
        self.format: int = 0
        self.model: str = ""
        self.part_names: dict[str, str] = {}  # key (slot type) value (part name)
    def __repr__(self):
        return f"{self.__class__.__name__}(format={self.format}, model={self.model}, parts={self.part_names})"

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
        success = self.load_pc_file(self.pc_path)
        if not success:
            Utils.log_and_report(f"Failed to parse PC file {self.filepath}", self, "ERROR")
            return {'CANCELLED'}
        # self.create_node_meshes()
        Utils.log_and_report(f"Part Configurator Load Success: {self.filepath}", self, "INFO")
        return {'FINISHED'}

    def load_pc_file(self, filepath):
        success = True
        try:
            self.parser.load_pc_file(filepath)
        except Exception as e:
            pc_fixed_str = self.get_jbeam_file_as_fixed_string(e)
            success = self.load_pc_string(pc_fixed_str)
        return success

    def load_pc_string(self, pc_json):
        success = True
        tmp_dir = TempFileManager().create_temp_dir()
        os.makedirs(tmp_dir, exist_ok=True)
        file_path1 = os.path.join(tmp_dir, self.filename)
        file_path2 = os.path.join(tmp_dir, f"{self.filename}.json")
        try:
            self.parser.load_pc_file_from_string(pc_json)
            print(f"Auto-Fix and Load Success {self.filename}")
        except Exception as e2:
            error_text = JbeamFileHelper.extract_json_error_snippet(e2, pc_json)
            Utils.log_and_report(f"Failed to fix and load file: '{e2}' Error Text: {error_text}\nWrote attempted fix file to: {file_path1}", self, "ERROR")
            success = False
        try:
            json_str = self.parser.get_json_str()
            with open(file_path1, 'w') as f:
                f.write(pc_json)
            with open(file_path2, 'w') as f:
                f.write(json_str)
        except Exception as write_error:
            Utils.log_and_report(f"Failed to write the attempted fix file: {write_error}", self, "ERROR")
        return success
    
    def get_jbeam_file_as_fixed_string(self, e):
        json_str = self.parser.get_json_str()
        error_text = JbeamFileHelper.extract_json_error_snippet(e, json_str)
        show_warning = a.is_addon_option_enabled("show_import_warnings")
        Utils.log_and_report(f"Initial load failed with '{e}' Error Text: {error_text}. Trying to auto-fix commas and attempt reload...", self if show_warning else None, "WARNING")
        with open(self.pc_path, "r", encoding="utf-8") as f:
            raw = f.read()
        return JbeamFileHelper.attempt_fix_jbeam_commas(raw, False)