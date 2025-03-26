import bpy
import bmesh

from dev_tools.utils.object_utils import ObjectUtils as o # type: ignore
from dev_tools.utils.ui_utils import UiUtils # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j # type: ignore

class JbeamSelectionTracker:
    _instance = None

    def __init__(self):
        self.previous_vertex_count = -1
        self.previous_edge_count = -1
        self.previous_face_count = -1
        self.previous_vertex_selection = None
        self.previous_edge_selection = None
        self.previous_face_selection = None
        self.previous_selection_mode = -1

    @classmethod
    def get_instance(cls):
        return cls._instance or cls()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self):
        bpy.app.handlers.depsgraph_update_post.append(self.selection_update_handler)

    def unregister(self):
        bpy.app.handlers.depsgraph_update_post.remove(self.selection_update_handler)

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
            scene.beamng_jbeam_active_structure.index = -1
            self.previous_vertex_selection = None
            self.previous_edge_selection = None
            self.previous_face_selection = None
            reset = True

        bm = bmesh.from_edit_mesh(obj.data)
        num_verts = len(bm.verts)
        num_edges = len(bm.edges)
        num_faces = len(bm.faces)
        scene.beamng_jbeam_hidden_elements.num_hidden_nodes = sum(1 for v in bm.verts if v.hide)
        scene.beamng_jbeam_hidden_elements.num_hidden_beams = sum(1 for e in bm.edges if e.hide)
        scene.beamng_jbeam_hidden_elements.num_hidden_faces =sum(1 for f in bm.faces if f.hide)

        if num_verts > self.previous_vertex_count or num_edges > self.previous_edge_count or num_faces > self.previous_face_count:
            j.validate_and_fix_storage_keys(obj, bm)

        #scene.beamng_jbeam_active_instance = 1

        self.previous_vertex_count = num_verts
        self.previous_edge_count = num_edges
        self.previous_face_count = num_faces

        if o.is_vertex_selection_mode():
            self.update_node_data(scene, obj, bm)
        elif o.is_edge_selection_mode():
            self.update_beam_data(scene, obj, bm)
        elif o.is_face_selection_mode():
            self.update_triangle_data(scene, obj, bm)
        elif reset:
            obj.data.update()

    def update_struct(self, scene, obj, bm, current_selection, bmesh_type, get_id, get_index):
        active_elem = bm.select_history.active if isinstance(bm.select_history.active, bmesh_type) else None
        active_index = active_elem.index if active_elem else (max(current_selection) if current_selection else -1)
        struct = scene.beamng_jbeam_active_structure
        struct.index = active_index
        ids = [
            get_id(obj, i) or f"({i})"
            for i in current_selection
        ]
        struct.selection = ", ".join(ids)
        struct.id = get_id(obj, active_index, bm) or ""
        get_index(obj, active_index)
        return struct

    def update_node_data(self, scene, obj, bm):
        bm.verts.ensure_lookup_table()
        current_selection = {v.index for v in bm.verts if v.select}

        if self.previous_vertex_selection == current_selection:
            return

        self.previous_vertex_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        o.update_vertex_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_vertices", "selected_vertices", current_selection)
        struct = self.update_struct(scene, obj, bm, current_selection, bmesh.types.BMVert, j.get_node_id, j.set_gn_jbeam_active_node_index)
        x, y, z = o.get_vertex_position_by_index(obj, bm, struct.index)
        struct.position.x = x
        struct.position.y = y
        struct.position.z = z
        bpy.ops.object.devtools_beamng_load_jbeam_node_props()
        UiUtils.force_update_ui(bpy.context)
        obj.data.update()

    def update_beam_data(self, scene, obj, bm):
        bm.edges.ensure_lookup_table()
        current_selection = {e.index for e in bm.edges if e.select}

        if self.previous_edge_selection == current_selection:
            return

        self.previous_edge_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        o.update_edge_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_edges", "selected_edges", current_selection)
        struct = self.update_struct(scene, obj, bm, current_selection, bmesh.types.BMEdge, j.get_beam_id, j.set_gn_jbeam_active_beam_index)
        struct.num_instances = j.get_total_beam_instances(obj, struct.index)
        bpy.ops.object.devtools_beamng_load_jbeam_beam_props()
        UiUtils.force_update_ui(bpy.context)
        obj.data.update()

    def update_triangle_data(self, scene, obj, bm):
        bm.faces.ensure_lookup_table()
        current_selection = {v.index for v in bm.faces if v.select}

        if self.previous_face_selection == current_selection:
            return

        self.previous_face_selection = current_selection
        mod = j.get_gn_jbeam_modifier(obj)
        o.update_face_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_faces", "selected_faces", current_selection)
        struct = self.update_struct(scene, obj, bm, current_selection, bmesh.types.BMFace, j.get_triangle_id, j.set_gn_jbeam_active_triangle_index)
        struct.num_instances = j.get_total_triangle_instances(obj, struct.index)
        bpy.ops.object.devtools_beamng_load_jbeam_triangle_props()
        UiUtils.force_update_ui(bpy.context)
        obj.data.update()
