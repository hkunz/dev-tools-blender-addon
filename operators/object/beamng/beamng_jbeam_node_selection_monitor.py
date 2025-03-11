import bpy
import bmesh

from dev_tools.utils.object_utils import ObjectUtils # type: ignore
from dev_tools.utils.ui_utils import UiUtils # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class OBJECT_OT_BeamngJbeamNodeSelectionMonitor(bpy.types.Operator):
    bl_idname = "wm.devtools_beamng_jbeam_node_selection_monitor"
    bl_label = "Vertex Monitor"
    bl_description = "DevTools: Monitor selected Jbeam node vertices"
    bl_options = {'INTERNAL', 'UNDO'}

    _timer = None
    _handler = None

    def __init__(self):
        self.previous_vertex_selection = set()
        self.previous_edge_selection = set()

    @classmethod
    def is_running(cls):
        return cls._handler is not None

    def modal(self, context, event):
        obj = context.object
        if event.type != 'TIMER' or not j.is_node_mesh(obj) or obj.mode != 'EDIT':
            return {'PASS_THROUGH'}
        self.check_data(context)
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

    def check_data(self, context):
        obj = context.object
        j.set_gn_jbeam_visualizer_selection_mode(obj)
        if ObjectUtils.is_vertex_selection_mode():
            self.update_vertex_data(context)
        elif ObjectUtils.is_edge_selection_mode():
            self.update_edge_data(context)

    def update_vertex_data(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        current_selection = {v.index for v in bm.verts if v.select}

        if self.previous_vertex_selection == current_selection:
            return

        self.previous_vertex_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        ObjectUtils.update_vertex_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_vertices", "selected_vertices", current_selection)
        self.update_nodes_panel(context, bm, current_selection)

    def update_nodes_panel(self, context, bm, current_selection):
        obj = context.object
        active_vert = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMVert) else None
        active_index = active_vert.index if active_vert else (max(current_selection) if current_selection else -1)
        context.scene.beamng_jbeam_active_vertex_idx = active_index
        jbeam_ids = [
            j.get_node_id(obj, v_idx) or f"({v_idx})"
            for v_idx in current_selection
        ]
        context.scene.beamng_jbeam_selected_nodes = ", ".join(jbeam_ids)
        context.scene.beamng_jbeam_active_node = j.get_node_id(obj, active_index) or ""
        bpy.ops.object.devtools_beamng_load_jbeam_node_props()
        UiUtils.force_update_ui(context)

    def update_edge_data(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        current_selection = {e.index for e in bm.edges if e.select}

        if self.previous_edge_selection == current_selection:
            return

        self.previous_edge_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        ObjectUtils.update_edge_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_edges", "selected_edges", current_selection)
        self.update_beams_panel(context, bm)

    def update_beams_panel(self, context, bm):
        pass

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
