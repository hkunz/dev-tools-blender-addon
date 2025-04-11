import bpy
import re
import os

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

from dev_tools.ui.addon_preferences import MyAddonPreferences as a # type: ignore
from dev_tools.utils.utils import Utils  # type: ignore
from dev_tools.utils.temp_file_manager import TempFileManager  # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore
from dev_tools.utils.jbeam.jbeam_parser import JbeamParser  # type: ignore
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

    def attempt_fix_jbeam_commas(self, content: str) -> str:
        lines = [line for line in content.splitlines() if line.strip() and not line.strip().startswith('//')]
        fixed_lines = []

        # Precompute next significant line for each line
        next_lines = [''] * len(lines)
        for i in range(len(lines) - 1):
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line:
                    next_lines[i] = next_line
                    break

        for i, line in enumerate(lines):
            s = line.rstrip()

            # Ignore empty lines or comment-only lines
            if not s or s.strip().startswith('//'):
                fixed_lines.append(line)
                continue

            s = re.sub(r'\s*//.*$', '', s)  # Remove comments after each code line
            s = re.sub(r'(,\s*){2,}', ',', s)  # Replace multiple commas with a single comma
            s = s.rstrip()

            # Check if this line should have a comma
            if not s.endswith((',', '{', '[', ':')):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                if next_line and not next_line.startswith(('}', ']')):
                    s += ','

            # Remove comma if line ends with ',' but next significant line is a closing bracket
            next_line = next_lines[i]
            if s.endswith(',') and next_line.startswith(('}', ']')):
                s = s.rstrip(',')

            s = re.sub(r'"\s*\{', '",{', s)  # s = s.replace('"{', '",{')  # math "{ and put comma ",{
            s = re.sub(r'\]\s*\{', '],{', s)  # s = s.replace(']{', '],{')  # math "]{ and put comma ],{
            s = re.sub(r'([^"])"\s*"([^\s"])', r'\1"," \2', s) # missing comma in ex: s = 'k""d and also k"  "d'

            # Match only number-like segments (space-separated) NOT inside quotes or dicts
            s = re.sub(r'(\[\s*"[^"]*")(?=\s*-?\d)', r'\1,', s)  # Add comma between quoted string and number (but avoid dicts)
            s = re.sub(r'(-?\d+(?:\.\d+)?)(\s+)(?=-?\d)', r'\1, ', s)  # Add commas between space-separated numbers

            s = re.sub(r'(-?\d+(?:\.\d+)?)(?=\s+-?\d)', r'\1, ', s)  # add missing comma between 2 numbers like 0.00, -1.45
            s = re.sub(r'(\d+\.\d+)\s*(\{)', r'\1,\2', s)  # add missing commas in ex: "value": 5.5 { should be "value": 5.5,{
            s = re.sub(r'(".*?")\s*(?=[\{\[])', r'\1, ', s)  # add missing commas in "key" { should be "key",{ or for "key" [ should be "key",[ # previously #s = re.sub(r'(".*?")\s*(\{)', r'\1,\2', s)
            s = re.sub(r'(-?\d+(?:\.\d+)?)(\s+)(")', r'\1, \3', s)  # fix missing commas in lines like {"nodeWeight":5.5"group":""}], which has missing coma between 5.5"group"
            s = re.sub(r'(\d(?:\.\d+)?)(?="\w)', r'\1,', s)  #  Add commas between numbers and the next string in certain cases similar to missing commas in lines like {"nodeWeight":5.5"group":""}, which has missing comma between 5.5 and "group"

            fixed_lines.append(s)

        return '\n'.join(fixed_lines)

    def extract_json_error_snippet(self, e, raw_content):
        error_message = str(e)
        if 'Expecting' in error_message:
            parts = error_message.split('char')
            char_position = parts[1].strip().split()[0]  # Get the first part before any non-numeric characters
            char_position = ''.join(filter(str.isdigit, char_position))  # Remove non-numeric characters (like ')') from char_position
            try:
                char_position = int(char_position)  # Convert char_position to an integer
            except ValueError:
                print("Failed to extract valid character position.")
                return

            snippet_start = max(0, char_position - 40)  # 40 characters before the error
            snippet_end = min(len(raw_content), char_position + 40)  # 40 characters after
            error_text = raw_content[snippet_start:snippet_end]
            print(f"Error position: {char_position}")
            return error_text
        return

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
            error_text = self.extract_json_error_snippet(e, json_str)
            show_warning = a.is_addon_option_enabled("show_import_warnings")
            Utils.log_and_report(f"Initial load failed with '{e}' Error Text: {error_text}. Trying to auto-fix commas and attempt reload...", self if show_warning else None, "WARNING")
            with open(jbeam_path, "r", encoding="utf-8") as f:
                raw = f.read()
            fixed = self.attempt_fix_jbeam_commas(raw)
            tmp_dir = TempFileManager().create_temp_dir()
            os.makedirs(tmp_dir, exist_ok=True)
            file_path1 = os.path.join(tmp_dir, filename)
            file_path2 = os.path.join(tmp_dir, f"{filename}.json")
            try:
                fix_required = True
                self.parser.load_jbeam_from_string(fixed)
                print(f"Auto-Fix and Load Success {filename}")
            except Exception as e2:
                error_text = self.extract_json_error_snippet(e2, json_str)
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
        nodes_list = self.parser.get_nodes_list()
        mesh_name = f"{os.path.splitext(filename)[0]}_{self.parser.get_part_name()}" 
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object(mesh_name)
        jmc.add_vertices(nodes_list)
        self.parser.parse_data_for_jbeam_object_conversion(obj, False)

        beams_list = self.parser.get_beams_list()
        tris_list = self.parser.get_triangles_list()
        jmc.add_edges(beams_list)
        jmc.add_faces(tris_list)

        JbeamNodeMeshConfigurator.process_node_mesh_props(obj, self.parser)
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        info = f"Auto-Fix and Import Success" if fix_required else f"Import Success"
        Utils.log_and_report(f"{info}: {filename}", self, "INFO")
        return {'FINISHED'}
