import bpy
import re
import os

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
from dev_tools.utils.jbeam.jbeam_helper import JbeamFileHelper  # type: ignore
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
        jbeam_path = self.filepath
        filename = os.path.basename(jbeam_path)
        self.parser = JbeamParser()
        fix_required = False
        cancel = False
        try:
            self.parser.load_jbeam(jbeam_path)
        except Exception as e:
            json_str = self.parser.get_json_str()
            error_text = JbeamFileHelper.extract_json_error_snippet(e, json_str)
            show_warning = a.is_addon_option_enabled("show_import_warnings")
            Utils.log_and_report(f"Initial load failed with '{e}' Error Text: {error_text}. Trying to auto-fix commas and attempt reload...", self if show_warning else None, "WARNING")
            with open(jbeam_path, "r", encoding="utf-8") as f:
                raw = f.read()
            fixed = JbeamFileHelper.attempt_fix_jbeam_commas(raw)
            tmp_dir = TempFileManager().create_temp_dir()
            os.makedirs(tmp_dir, exist_ok=True)
            file_path1 = os.path.join(tmp_dir, filename)
            file_path2 = os.path.join(tmp_dir, f"{filename}.json")
            try:
                fix_required = True
                self.parser.load_jbeam_from_string(fixed)
                print(f"Auto-Fix and Load Success {filename}")
            except Exception as e2:
                error_text = JbeamFileHelper.extract_json_error_snippet(e2, json_str)
                Utils.log_and_report(f"Failed to fix and load file: '{e2}' Error Text: {error_text}\nWrote attempted fix file to: {file_path1}", self, "ERROR")
                cancel = True
            try:
                json_str = self.parser.get_json_str()
                with open(file_path1, 'w') as f:
                    f.write(fixed)
                with open(file_path2, 'w') as f:
                    f.write(json_str)
            except Exception as write_error:
                Utils.log_and_report(f"Failed to write the attempted fix file: {write_error}", self, "ERROR")

        if cancel:
            return {'CANCELLED'}

        jbeam_parts: dict[str, object] = self.parser.get_jbeam_parts()

        for part_name, part in jbeam_parts.items():
            print(f"Creating Part with name '{part_name}' ================================>")
            nodes_list = self.parser.get_nodes_list(part_name)
            if not nodes_list:
                Utils.log_and_report(f"No nodes list in part name '{part_name}'", self, "INFO")
                continue
            mesh_name = f"{os.path.splitext(filename)[0]}.{part_name}"
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
        info = f"Auto-Fix and Import Success" if fix_required else f"Import Success"
        Utils.log_and_report(f"{info}: {filename}", self, "INFO")
        return {'FINISHED'}
