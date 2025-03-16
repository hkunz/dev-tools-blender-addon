import bpy
import bmesh

from dev_tools.utils.object_utils import ObjectUtils as o # type: ignore
from dev_tools.utils.ui_utils import UiUtils # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class JbeamSelectionTracker:
    _instance = None

    def __init__(self):
        self.previous_vertex_selection = None
        self.previous_edge_selection = None
        self.previous_selection_mode = -1

    @classmethod
    def get_instance(cls):
        return cls._instance or cls()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self):
        if not self.selection_update_handler in bpy.app.handlers.depsgraph_update_post:
            print(f"JbeamSelectionTracker: Registered {self}")
            bpy.app.handlers.depsgraph_update_post.append(self.selection_update_handler)

    def unregister(self):
        if self.selection_update_handler in bpy.app.handlers.depsgraph_update_post:
            print(f"JbeamSelectionTracker: Unregistered {self}")
            bpy.app.handlers.depsgraph_update_post.remove(self.selection_update_handler)
        else:
            print(f"JbeamSelctionTracker: Nothing to unregister: {len(bpy.app.handlers.depsgraph_update_post)} handlers were found")

    def selection_update_handler(self, scene, depsgraph):
        obj = bpy.context.object
        if not j.is_node_mesh(obj) or obj.mode != 'EDIT':
            return
        self.check_selection_change(scene)

    def check_selection_change(self, scene):
        obj = bpy.context.object
        mode = j.set_gn_jbeam_visualizer_selection_mode(obj)
        reset = False
        if self.previous_selection_mode != mode:
            self.previous_selection_mode = mode
            scene.beamng_jbeam_active_node.vertex_index = -1
            self.previous_vertex_selection = None
            scene.beamng_jbeam_active_edge_idx = -1
            self.previous_edge_selection = None
            reset = True

        if o.is_vertex_selection_mode():
            self.update_vertex_data(scene, obj)
        elif o.is_edge_selection_mode():
            self.update_edge_data(scene, obj)
        elif reset:
            obj.data.update()

    def update_vertex_data(self, scene, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        current_selection = {v.index for v in bm.verts if v.select}

        if self.previous_vertex_selection == current_selection:
            return

        self.previous_vertex_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        o.update_vertex_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_vertices", "selected_vertices", current_selection)
        self.update_nodes_panel(scene, obj, bm, current_selection)
        obj.data.update()

    def update_nodes_panel(self, scene, obj, bm, current_selection):
        active_vert = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMVert) else None
        active_index = active_vert.index if active_vert else (max(current_selection) if current_selection else -1)
        j.set_gn_jbeam_active_node_index(obj, active_index)
        scene.beamng_jbeam_active_node.vertex_index = active_index
        x, y, z = o.get_vertex_position_by_index(obj, bm, active_index)
        scene.beamng_jbeam_active_node.position.x = x
        scene.beamng_jbeam_active_node.position.y = y
        scene.beamng_jbeam_active_node.position.z = z
        jbeam_ids = [
            j.get_node_id(obj, i) or f"({i})"
            for i in current_selection
        ]
        scene.beamng_jbeam_selected_nodes = ", ".join(jbeam_ids)
        scene.beamng_jbeam_active_node.node_id = j.get_node_id(obj, active_index) or ""
        bpy.ops.object.devtools_beamng_load_jbeam_node_props()
        UiUtils.force_update_ui(bpy.context)

    def update_edge_data(self, scene, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        current_selection = {e.index for e in bm.edges if e.select}

        if self.previous_edge_selection == current_selection:
            return

        self.previous_edge_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        o.update_edge_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_edges", "selected_edges", current_selection)
        self.update_beams_panel(scene, obj, bm, current_selection)
        obj.data.update()

    def update_beams_panel(self, scene, obj, bm, current_selection): 
        active_edge = bm.select_history.active if isinstance(bm.select_history.active, bmesh.types.BMEdge) else None
        active_index = active_edge.index if active_edge else (max(current_selection) if current_selection else -1)
        j.set_gn_jbeam_active_beam_index(obj, active_index)
        scene.beamng_jbeam_active_edge_idx = active_index
        jbeam_ids = [
            j.get_beam_id(obj, bm, i) or f"({i})"
            for i in current_selection
        ]
        scene.beamng_jbeam_selected_edges = ", ".join(jbeam_ids)
        scene.beamng_jbeam_active_edge = j.get_beam_id(obj, bm, active_index) or ""
        bpy.ops.object.devtools_beamng_load_jbeam_beam_props()
        UiUtils.force_update_ui(bpy.context)











