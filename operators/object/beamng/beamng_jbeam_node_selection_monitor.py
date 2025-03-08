import bpy
import bmesh

from dev_tools.utils.object_utils import ObjectUtils # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class OBJECT_OT_BeamngJbeamNodeSelectionMonitor(bpy.types.Operator):
    bl_idname = "wm.devtools_beamng_jbeam_node_selection_monitor"
    bl_label = "Vertex Monitor"
    bl_description = "DevTools: Monitor selected Jbeam node vertices"
    bl_options = {'INTERNAL', 'UNDO'}

    _timer = None
    _handler = None
    _last_selected_indices = set()
    
    @classmethod
    def is_running(cls):
        return cls._handler is not None

    def modal(self, context, event):
        obj = context.object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            return {'PASS_THROUGH'}

        if not j.has_jbeam_node_id(obj):
            return {'PASS_THROUGH'}  # Ignore non-JBeam objects

        if event.type == 'TIMER':
            self.update_vertex_data(context)
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        cls = self.__class__
        if cls._handler is not None:
            return {'CANCELLED'}

        wm = context.window_manager

        if cls._timer is None:
            cls._timer = wm.event_timer_add(0.1, window=context.window)
            wm.modal_handler_add(self)
            cls._handler = self

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
        active_vert = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMVert) else None
        active_index = active_vert.index if active_vert else (selected_verts[-1] if selected_verts else -1)

        if set(selected_verts) != self._last_selected_indices:
            self._last_selected_indices = set(selected_verts)
            context.scene.beamng_jbeam_active_vertex_idx = active_index
            jbeam_ids = [
                j.get_node_id(obj, v_idx) or f"({v_idx})"
                for v_idx in selected_verts
            ]
            context.scene.beamng_jbeam_selected_nodes = ", ".join(jbeam_ids)
            context.scene.beamng_jbeam_active_node = j.get_node_id(obj, active_index) or ""

            bpy.ops.object.devtools_beamng_load_jbeam_node_props()
            group_name = "selected_vertices"
            j.set_gn_jbeam_visualizer_selected_vertices(obj, group_name)
            ObjectUtils.assign_vertices_to_group_in_edit_mode(obj, group_name, selected_verts)
            self.force_update_ui()

    def cancel(self, context):
        cls = self.__class__
        wm = context.window_manager
        wm.event_timer_remove(cls._timer)
        cls._timer = None
        cls._handler = None
        print(f"Modal operator {cls.bl_idname} cancelled")
        # cancel gets called when opening or creating new blender file, to prevent, restart operator
        #bpy.app.timers.register(lambda: bpy.ops.wm.devtools_beamng_jbeam_node_selection_monitor('INVOKE_DEFAULT'), first_interval=0.5)
        bpy.app.timers.register(lambda: (bpy.ops.wm.devtools_beamng_jbeam_node_selection_monitor('INVOKE_DEFAULT'), 0.1)[1], first_interval=0.5)


    def __del__(self):
        # Gets called and garbage collected because of https://blender.stackexchange.com/questions/331677/handler-in-load-post-not-called-when-using-bl-info-header-in-addon
        return
        if self._timer is not None:
            wm = bpy.context.window_manager
            wm.event_timer_remove(self._timer)
            self._timer = None
            self._handler = None
