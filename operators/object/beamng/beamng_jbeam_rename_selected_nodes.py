import bpy
import bmesh
import re

from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class OBJECT_OT_BeamngJbeamRenameSelectedNodes(bpy.types.Operator):
    """Renames selected vertices using active node ID as prefix"""
    bl_idname = "object.devtools_beamng_jbeam_rename_selected_nodes"
    bl_label = "DevTools: Rename Selected JBeam Nodes"
    bl_options = {'INTERNAL', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        mesh = obj.data
        active_id = context.scene.beamng_jbeam_active_node.node_id.strip()

        if not active_id:
            self.report({'WARNING'}, "Active Node ID is empty")
            return {'CANCELLED'}

        if obj.mode != 'EDIT':
            self.report({'WARNING'}, "Switch to Edit Mode to assign IDs")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(mesh)
        selected_verts = [v for v in bm.verts if v.select]

        if not selected_verts:
            self.report({'WARNING'}, "No vertices selected")
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
        self.report({'INFO'}, f"Assigned JBeam Node IDs to {len(selected_verts)} vertices")
        return {'FINISHED'}
