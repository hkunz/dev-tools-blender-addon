import bpy
import bmesh
import logging

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.file_utils import FileUtils as f
from unofficial_jbeam_editor.utils.object_utils import ObjectUtils as o
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j

class OBJECT_OT_BeamngJbeamSaveElementsJbeamPath(bpy.types.Operator):
    bl_idname = "object.devtools_beamng_jbeam_save_elements_jbeam_path"
    bl_label = "DevTools: Save Elements Jbeam Path"
    bl_options = {'INTERNAL', 'UNDO'}

    jbeam_source_path: bpy.props.StringProperty(
        name="Save JBeam Path",
        description="Path to match against JBeam source",
        default=""
    )  # type: ignore

    def execute(self, context):
        if not f.is_jbeam_file(self.jbeam_source_path):
            Utils.log_and_report(f"Invalid file format. Expected a '.jbeam' file, but got: '{self.jbeam_source_path}'", self, 'WARNING')
            return {'CANCELLED'}

        if not f.leaf_dir_exists(self.jbeam_source_path):
            Utils.log_and_report(f"directory does not exist '{self.jbeam_source_path}'", self, 'WARNING')
            return {'CANCELLED'}

        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)

        if o.is_vertex_selection_mode():
            domain = "verts"
        elif o.is_edge_selection_mode():
            domain = "edges"
        elif o.is_face_selection_mode():
            domain = "faces"
        else:
            logging.error("Invalid selection domain")
            return {'CANCELLED'}

        count = j.set_jbeam_path_for_selected_elements(obj, self.jbeam_source_path, domain)
        if count:
            Utils.log_and_report(f"Updated {count} {domain}", self, 'INFO')
        else:
            Utils.log_and_report(f"Nothing Selected or Error Occurred", self, 'INFO')

        return {'FINISHED'}
