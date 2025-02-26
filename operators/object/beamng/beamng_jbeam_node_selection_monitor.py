import bpy
import bmesh

class OBJECT_OT_BeamngJbeamNodeSelectionMonitor(bpy.types.Operator):
    bl_idname = "wm.devtools_beamng_jbeam_node_selection_monitor"
    bl_label = "Vertex Monitor"
    bl_description = "DevTools: Monitor selected Jbeam node vertices and update JBeam Node IDs"
    bl_options = {'INTERNAL', 'UNDO'}

    _timer = None
    _last_selected_indices = set()
    
    def modal(self, context, event):
        obj = context.object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            return {'PASS_THROUGH'}

        if "jbeam_node_id" not in obj.data.attributes:
            return {'PASS_THROUGH'}  # Ignore non-JBeam objects

        if event.type == 'TIMER':
            self.update_vertex_data(context)
        return {'PASS_THROUGH'}
    
    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}
    
    def force_update_ui(self):
        for area in bpy.context.screen.areas:
            if area.type in {'PROPERTIES', 'VIEW_3D'}:
                for region in area.regions:
                    if region.type in {'WINDOW', 'UI'}:
                        region.tag_redraw()
    
    def update_vertex_data(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return
        
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        selected_verts = [v.index for v in bm.verts if v.select]

        if not selected_verts:
            if self._last_selected_indices:  # Only update if we had a previous selection
                self._last_selected_indices.clear()
                context.scene.active_vertex_idx = -1
                context.scene.selected_nodes = ""
                self.force_update_ui()
                return

        active_vert = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMVert) else None
        active_index = active_vert.index if active_vert else (selected_verts[-1] if selected_verts else -1)

        if set(selected_verts) != self._last_selected_indices:
            self._last_selected_indices = set(selected_verts)
            context.scene.active_vertex_idx = active_index
            layer = bm.verts.layers.string.get("jbeam_node_id")
            if layer:
                jbeam_ids = [
                    bm.verts[v_idx][layer].decode('utf-8') if bm.verts[v_idx][layer] else f"({v_idx})"
                    for v_idx in selected_verts
                ]
                context.scene.selected_nodes = ", ".join(jbeam_ids)
            else:
                context.scene.selected_nodes = ""
            
            context.scene.active_node = bm.verts[active_index][layer].decode("utf-8") if layer else ""
            self.force_update_ui()
    
    def __del__(self):
        print("DEL =============")
        if self._timer is not None:
            print("DEL =============1")
            wm = bpy.context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None
            print("DEL =============2")
    
class OBJECT_OT_BeamngAssignNodeId(bpy.types.Operator):
    """Assigns a new JBeam Node ID to the selected vertex"""
    bl_idname = "object.devtools_beamng_assign_jbeam_id"
    bl_label = "Assign JBeam ID"

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'WARNING'}, "No valid mesh object selected")
            return {'CANCELLED'}

        mesh = obj.data
        index = context.scene.active_vertex_idx
        new_value = context.scene.active_node.encode("utf-8")

        if obj.mode == 'EDIT':
            bm = bmesh.from_edit_mesh(mesh)
            layer = bm.verts.layers.string.get("jbeam_node_id")
            bm.verts[index][layer] = new_value
            bmesh.update_edit_mesh(mesh)

        self.report({'INFO'}, f"Assigned JBeam Node ID: {context.scene.jbeam_node_id}")
        return {'FINISHED'}
