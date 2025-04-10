import bpy
import re
import os

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

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

        lines = [line for line in content.splitlines() if line.strip()]
        fixed_lines = []

        def get_next_significant_line(i):
            for j in range(i + 1, len(lines)):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith('//'):
                    return next_line
            return ''

        for i, line in enumerate(lines):
            stripped = line.rstrip()

            # Ignore empty lines or comment-only lines
            if not stripped or stripped.strip().startswith('//'):
                fixed_lines.append(line)
                continue

             # Check if this line should have a comma
            if not stripped.endswith((',', '{', '[', ':')):
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else '' # Check next line to avoid false positives at end of blocks
                if next_line and not next_line.startswith(('}', ']')):
                    stripped += ','

            # Remove comma if line ends with ',' but next significant line is a closing bracket
            next_line = get_next_significant_line(i)
            if stripped.endswith(',') and next_line.startswith(('}', ']')):
                stripped = stripped.rstrip(',')

            stripped = re.sub(r'(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)', r'\1,\2', stripped) # fix missing commas between numbers like ["b31", 0.00, -1.45 0.97], notice there' no comma between 1.45 and 0.97
            stripped = re.sub(r'(\d+\.\d+)\s*(\{)', r'\1,\2', stripped) # add missing commas in ex: "value": 5.5 { should be "value": 5.5,{
            stripped = re.sub(r'(".*?")\s*(\{)', r'\1,\2', stripped) # add missing commas in "key" { should be "key",{
            stripped = re.sub(r'(\d(?:\.\d+)?)(?="\w)', r'\1,', stripped) # fix missing commas in lines like ["b14l", 0.43, 0.56, 0.75,{"nodeWeight":5.5"group":""}], which has missing coma between 5.5"group"

            # Check quoted string followed by dict
            stripped = stripped.replace('"{', '",{')
            stripped = stripped.replace(']{', '],{')

            fixed_lines.append(stripped)

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
        try:
            self.parser.load_jbeam(jbeam_path)
        except Exception as e:
            json_str = self.parser.get_json_str()
            error_text = self.extract_json_error_snippet(e, json_str)
            Utils.log_and_report(f"Initial load failed with '{e}' Error Text: {error_text}. Trying to auto-fix commas and attempt reload...", self, "WARNING")
            with open(jbeam_path, "r", encoding="utf-8") as f:
                raw = f.read()
            fixed = self.attempt_fix_jbeam_commas(raw)
            try:
                fix_required = True
                self.parser.load_jbeam_from_string(fixed)
                print(f"Auto-Fix and Load Success {filename}")
            except Exception as e2:
                tmp_dir = TempFileManager().create_temp_dir()
                os.makedirs(tmp_dir, exist_ok=True)
                file_path1 = os.path.join(tmp_dir, filename)
                file_path2 = os.path.join(tmp_dir, f"{filename}.json")
                json_str = self.parser.get_json_str()
                try:
                    with open(file_path1, 'w') as f:
                        f.write(fixed)
                    with open(file_path2, 'w') as f:
                        f.write(json_str)
                except Exception as write_error:
                    Utils.log_and_report(f"Failed to write the attempted fix file: {write_error}", self, "ERROR")
                error_text = self.extract_json_error_snippet(e2, json_str)
                Utils.log_and_report(f"Failed to fix and load file: '{e2}' Error Text: {error_text}\nWrote attempted fix file to: {file_path1}", self, "ERROR")
                return {'CANCELLED'}

        nodes_list = self.parser.get_nodes_list()
        jmc = JbeamNodeMeshCreator()
        obj = jmc.create_object()
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
