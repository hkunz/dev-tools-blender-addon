import bpy
import bmesh
import logging

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.object_utils import ObjectUtils as o
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j

class OBJECT_OT_BeamngJbeamSelectElementByJbeamPath(bpy.types.Operator):
    bl_idname = "object.devtools_beamng_jbeam_select_elements_by_jbeam_path"
    bl_label = "DevTools: Select Elements by Jbeam Path"
    bl_description="Search and select all elements with the same specified Jbeam path"
    bl_options = {'INTERNAL', 'UNDO'}

    jbeam_source_path: bpy.props.StringProperty(
        name="JBeam Path",
        description="Path to match against JBeam source",
        default=""
    )  # type: ignore

    def execute(self, context):
        obj = context.object
        bpy.ops.object.mode_set(mode='OBJECT')

        # Deselect all elements
        mesh = obj.data
        for v in mesh.vertices:
            v.select = False
        for e in mesh.edges:
            e.select = False
        for f in mesh.polygons:
            f.select = False

        bpy.ops.object.mode_set(mode='EDIT')
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

        indices = j.find_indices_by_jbeam_path(obj, self.jbeam_source_path, domain)

        if not indices:
            Utils.log_and_report(f"No nodes found with jbeam path '{self.jbeam_source_path}'", self, 'INFO')
            return {'FINISHED'}

        element = None

        bm_collection = getattr(bm, domain)
        bm_collection.ensure_lookup_table()

        element = None
        for idx in indices:
            element = bm_collection[idx]
            element.select = True

        if element:
            bm.select_history.add(element)
            bmesh.update_edit_mesh(obj.data)
            Utils.log_and_report(f"Selected {len(indices)} Node(s)", self, 'INFO')

        return {'FINISHED'}
