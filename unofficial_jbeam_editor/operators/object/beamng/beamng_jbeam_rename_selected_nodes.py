import bpy
import bmesh
import re

from unofficial_jbeam_editor.utils.utils import Utils
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j

class OBJECT_OT_BeamngJbeamRenameSelectedNodes(bpy.types.Operator):
    bl_idname = "object.devtools_beamng_jbeam_rename_selected_nodes"
    bl_label = "DevTools: Rename Selected JBeam Nodes"
    bl_description = "Renames selected Nodes using the Active Node ID as a prefix/suffix. Use # as a number placeholder."
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            Utils.log_and_report("No valid mesh object selected", self, 'WARNING')
            return {'CANCELLED'}

        mesh = obj.data
        active_id = context.scene.beamng_jbeam_active_structure.id.strip()

        if not active_id:
            Utils.log_and_report("Active Node ID is empty", self, 'WARNING')
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            Utils.log_and_report("Switch to Edit Mode to assign IDs", self, 'WARNING')
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(mesh)
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts:
            Utils.log_and_report("No vertices selected", self, 'WARNING')
            return {'CANCELLED'}

        if len(selected_verts) == 1:
            # If only one vertex is selected, assign the exact input without modifications
            j.set_node_id(obj, selected_verts[0].index, active_id) 
        else:
            for i, v in enumerate(selected_verts, 1):
                if "#" in active_id:
                    new_value = active_id.replace("#", str(i))  # Replace # with number
                else:
                    match = re.search(r"(\d+)$", active_id)
                    if match:
                        new_value = f"{active_id}.{i}"  # Append .1, .2, .3
                    else:
                        new_value = f"{active_id}{i}"  # Append 1, 2, 3
                
                j.set_node_id(obj, v.index, new_value)

        bmesh.update_edit_mesh(mesh)
        verts_msg = "Nodes" if len(selected_verts) > 1 else "Node"
        Utils.log_and_report(f"Assigned ID to {len(selected_verts)} selected {verts_msg}", self, 'INFO')
        return {'FINISHED'}
