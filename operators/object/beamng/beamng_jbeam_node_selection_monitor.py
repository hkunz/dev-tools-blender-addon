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

    previous_vertex_selection = set()
    previous_edge_selection = set()

    @classmethod
    def is_running(cls):
        return cls._handler is not None

    def modal(self, context, event):
        obj = context.object
        if not obj or obj.type != 'MESH' or obj.mode != 'EDIT':
            return {'PASS_THROUGH'}

        if not j.has_jbeam_node_id(obj):
            return {'PASS_THROUGH'}  # Ignore non-JBeam objects

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}
        obj = context.object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return {'PASS_THROUGH'}
        j.set_gn_jbeam_visualizer_selection_mode(obj)
        if ObjectUtils.is_vertex_selection_mode():
            self.update_vertex_data(context)
        elif ObjectUtils.is_edge_selection_mode():
            self.update_edge_data(context)
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

    def update_vertex_data(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        previous_vertex_selection = getattr(self, "previous_vertex_selection", None)
        current_selection = {v.index for v in bm.verts if v.select}

        if previous_vertex_selection == current_selection:
            return

        self.update_vertex_data_attr(obj, bm, current_selection)

        active_vert = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMVert) else None
        active_index = active_vert.index if active_vert else (max(current_selection) if current_selection else -1)

        current_selection = {v.index for v in bm.verts if v.select}
        context.scene.beamng_jbeam_active_vertex_idx = active_index
        jbeam_ids = [
            j.get_node_id(obj, v_idx) or f"({v_idx})"
            for v_idx in current_selection
        ]
        context.scene.beamng_jbeam_selected_nodes = ", ".join(jbeam_ids)
        context.scene.beamng_jbeam_active_node = j.get_node_id(obj, active_index) or ""

        bpy.ops.object.devtools_beamng_load_jbeam_node_props()

        UiUtils.force_update_ui(context)

    def update_vertex_data_attr(self, obj, bm, current_selection):
        mesh = obj.data
        self.previous_vertex_selection = current_selection
        attr_name = "selected_vertices"
        named_attr = "attribute_selected_vertices"
        mod = j.get_gn_jbeam_modifier(obj)

        if bpy.app.version >= (4, 4, 0):
            mod.node_group.nodes.get(named_attr).data_type = 'BOOLEAN'
            attribute = mesh.attributes.get(attr_name) or mesh.attributes.new(name=attr_name, type="BOOLEAN", domain="POINT")
            layer = bm.verts.layers.bool.get(attribute.name)
            for vert in bm.verts:
                vert[layer] = vert.index in current_selection
        else:
            mod.node_group.nodes.get(named_attr).data_type = 'INT'
            attribute = mesh.attributes.get(attr_name) or mesh.attributes.new(name=attr_name, type="INT", domain="POINT")
            layer = bm.verts.layers.int.get(attribute.name)
            for vert in bm.verts:
                vert[layer] = 1 if vert.index in current_selection else 0

        mesh.update()

    def update_edge_data(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()

        previous_edge_selection = getattr(self, "previous_edge_selection", None)
        current_selection = {e.index for e in bm.edges if e.select}
        
        if previous_edge_selection == current_selection:
            return

        self.update_edge_data_attr(obj, bm, current_selection)
        
    def update_edge_data_attr(self, obj, bm, current_selection):
        mesh = obj.data
        self.previous_edge_selection = current_selection
        attr_name = "selected_edges"
        named_attr = "attribute_selected_edges"
        mod = j.get_gn_jbeam_modifier(obj)
 
        if bpy.app.version >= (4, 4, 0):
            mod.node_group.nodes.get(named_attr).data_type = 'BOOLEAN'
            attribute = mesh.attributes.get(attr_name) or mesh.attributes.new(name=attr_name, type="BOOLEAN", domain="EDGE")
            layer = bm.edges.layers.bool.get(attribute.name)
            for edge in bm.edges:
                edge[layer] = edge.index in current_selection
        else:
            mod.node_group.nodes.get(named_attr).data_type = 'INT'
            attribute = mesh.attributes.get(attr_name) or mesh.attributes.new(name=attr_name, type="INT", domain="EDGE")
            layer = bm.edges.layers.int.get(attribute.name)
            for edge in bm.edges:
                edge[layer] = 1 if edge.index in current_selection else 0

        mesh.update()

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
