import bpy

from bpy.types import Operator
from bpy.props import StringProperty
from bpy_extras.io_utils import ImportHelper

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
        lines = content.splitlines()
        fixed_lines = []

        for i, line in enumerate(lines):
            stripped = line.rstrip()

            # Ignore empty lines or comment-only lines
            if not stripped or stripped.strip().startswith('//'):
                fixed_lines.append(line)
                continue

            # Check if this line should have a comma
            if not stripped.endswith((',', '{', '[', ':')):
                # Check next line to avoid false positives at end of blocks
                next_line = lines[i + 1].strip() if i + 1 < len(lines) else ''
                if next_line and not next_line.startswith(('}', ']')):
                    stripped += ','

            fixed_lines.append(stripped)

        return '\n'.join(fixed_lines)

    def execute(self, context):
        bpy.ops.object.select_all(action='DESELECT')
        jbeam_path = self.filepath
        self.parser = JbeamParser()
        try:
            self.parser.load_jbeam(jbeam_path)
        except Exception as e:
            print(f"WARNING: Initial load failed with {e}. Trying to auto-fix commas and attempt reload...")

            with open(jbeam_path, "r", encoding="utf-8") as f:
                raw = f.read()

            fixed = self.attempt_fix_jbeam_commas(raw)

            try:
                self.parser.load_jbeam_from_string(fixed)
                self.report({'INFO'}, f"Successfully loaded Jbeam File")

            except Exception as e2:
                self.report({'ERROR'}, f"Failed to fix and load file: {e2}")
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

        return {'FINISHED'}
