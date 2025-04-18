import bpy
import bmesh
import json

from typing import Optional

from unofficial_jbeam_editor.ui.addon_preferences import MyAddonPreferences as a
from unofficial_jbeam_editor.utils.object_utils import ObjectUtils as o
from unofficial_jbeam_editor.utils.ui_utils import UiUtils
from unofficial_jbeam_editor.utils.jbeam.jbeam_utils import JbeamUtils as j, JbeamRefnodeUtils as jr
from unofficial_jbeam_editor.operators.common.ui.toggle_dynamic_button_operator import ButtonItem

class JbeamSelectionTracker:
    _instance = None

    def __init__(self):
        self.vertex_count: int = -1
        self.edge_count: int = -1
        self.face_count: int = -1
        self.vertex_selection: Optional[set[int]] = None  # set of selected vertex indices
        self.edge_selection: Optional[set[int]] = None  # set of selected edge indices
        self.face_selection: Optional[set[int]] = None  # set of selected face indices
        self.selection_mode: int = -1  # selection modes: 1 (vertex), 2 (edge), or 3 (edge)
        self.instances_selection: set[int] = []  # instances start at 1, 2, 3, etc

    @classmethod
    def get_instance(cls):
        return cls._instance or cls()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self):
        if self.selection_update_handler not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(self.selection_update_handler)

    def unregister(self):
        if self.selection_update_handler in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.remove(self.selection_update_handler)

    def selection_update_handler(self, scene, depsgraph):
        obj = bpy.context.object
        if not j.is_node_mesh(obj) or obj.mode != 'EDIT':
            return
        self.check_selection_change(scene)

    def get_instances_selection_str(self, scene) -> str:
        instances_selection = scene.beamng_jbeam_instance.get_selected_instances()
        self.instances_selection = instances_selection
        return json.dumps(instances_selection)

    def on_instance_buttons_update(self, scene):
        instances = self.get_instances_selection_str(scene)
        if o.is_edge_selection_mode():
            bpy.ops.object.devtools_beamng_load_jbeam_beam_props(instances=instances)
        elif o.is_face_selection_mode():
            bpy.ops.object.devtools_beamng_load_jbeam_triangle_props(instances=instances)

    def on_instance_button_change_add(self, scene):
        self.on_instance_buttons_update(scene)

    def on_instance_button_change_remove(self, scene, instance_selection):
        obj = bpy.context.object
        bm = bmesh.from_edit_mesh(obj.data)
        prop_func = None
        bm_data = None
        if o.is_edge_selection_mode():
            prop_func = j.delete_beam_props
            bm_data = bm.edges
        elif o.is_face_selection_mode():
            prop_func = j.delete_triangle_props
            bm_data = bm.faces
        bm_data.ensure_lookup_table()
        for elem in bm_data:
            if not elem.select:
                continue
            for instance in instance_selection:
                prop_func(obj, elem.index, instance)
        self.on_instance_buttons_update(scene)
        self.reset_selection(scene)
        self.check_selection_change(scene)

    def reset_selection(self, scene, index=-1):
        scene.beamng_jbeam_active_structure.index = index
        self.vertex_selection: set[int] = None
        self.edge_selection = None
        self.face_selection = None

    def check_selection_change(self, scene):
        if scene.beamng_jbeam_active_structure.update_in_progress:  # useless check, doesn't work because it will already be False by now. Supposed to be used in conjunction with beamng_jbeam_node_props_manager.py::update_element_index so we could select the element while setting JbeamStructure::index IntProperty in panel
            return
        obj = bpy.context.object
        mode: int = j.set_gn_jbeam_visualizer_selection_mode(obj)
        reset = False
        if self.selection_mode != mode:
            self.selection_mode = mode
            self.reset_selection(scene)
            reset = True

        bm = bmesh.from_edit_mesh(obj.data)
        num_verts = len(bm.verts)
        num_edges = len(bm.edges)
        num_faces = len(bm.faces)
        scene.beamng_jbeam_hidden_elements.num_hidden_nodes = sum(1 for v in bm.verts if v.hide)
        scene.beamng_jbeam_hidden_elements.num_hidden_beams = sum(1 for e in bm.edges if e.hide)
        scene.beamng_jbeam_hidden_elements.num_hidden_faces =sum(1 for f in bm.faces if f.hide)

        if num_verts > self.vertex_count or num_edges > self.edge_count or num_faces > self.face_count:
            j.validate_and_fix_storage_keys(obj, bm)

        self.vertex_count = num_verts
        self.edge_count = num_edges
        self.face_count = num_faces

        if o.is_vertex_selection_mode():
            self.update_node_data(scene, obj, bm)
        elif o.is_edge_selection_mode():
            self.update_beam_data(scene, obj, bm)
        elif o.is_face_selection_mode():
            self.update_triangle_data(scene, obj, bm)
        elif reset:
            obj.data.update()

    def update_struct(self, scene, obj, bm, name, selection, bmesh_type, get_id, set_gn_index, index = -1):
        struct = scene.beamng_jbeam_active_structure
        if not selection:
            struct.selection = ""
            return
        if index < 0:
            active_elem = bm.select_history.active if isinstance(bm.select_history.active, bmesh_type) else None
            active_index = active_elem.index if active_elem else (max(selection) if selection else -1)
        else:
            active_index = index
        struct.name = name
        struct.index = active_index
        ids = [
            get_id(obj, i, bm) or f"({i})"
            for i in selection
        ]
        struct.selection = ", ".join(ids)
        struct.id = get_id(obj, active_index, bm) or ""
        set_gn_index(obj, active_index)
        return struct

    def update_node_data(self, scene, obj, bm):
        bm.verts.ensure_lookup_table()
        selection = {v.index for v in bm.verts if v.select}

        if self.vertex_selection == selection:
            return

        self.vertex_selection = selection
        if a.is_addon_visualizer_enabled():
            mod = j.get_gn_jbeam_modifier(obj)
            if mod:
                o.update_vertex_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_vertices", "selected_vertices", selection)
        struct = self.update_struct(scene, obj, bm, "Node", selection, bmesh.types.BMVert, j.get_node_id, j.set_gn_jbeam_active_node_index)
        if not selection:
            return
        refnode = jr.get_refnode_id(obj, struct.index)
        if refnode != None:
            struct.refnode_enum = jr.RefNode(refnode).name # example: jr.RefNode.RIGHT_CORNER.name
        x, y, z = o.get_vertex_position_by_index(obj, bm, struct.index)
        struct.position.x = x
        struct.position.y = y
        struct.position.z = z
        bpy.ops.object.devtools_beamng_load_jbeam_node_props()
        UiUtils.force_update_ui(bpy.context)
        obj.data.update()

    def update_instances(self, scene, obj, struct, get_total_instances):
        struct.num_instances = get_total_instances(obj, struct.index)
        scene.beamng_jbeam_instance.buttons.clear()
        bpy.ops.wm.beamng_jbeam_manage_jbeam_instance_buttons(action='ADD', button_name=ButtonItem.BUTTON_NAME, button_amount=struct.num_instances)

    def update_beam_data(self, scene, obj, bm):
        bm.edges.ensure_lookup_table()
        selection = {e.index for e in bm.edges if e.select}
        
        if self.edge_selection == selection:
            return

        self.edge_selection = selection
        if a.is_addon_visualizer_enabled():
            mod = j.get_gn_jbeam_modifier(obj)
            if mod:
                o.update_edge_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_edges", "selected_edges", selection)
        struct = self.update_struct(scene, obj, bm, "Beam", selection, bmesh.types.BMEdge, j.get_beam_id, j.set_gn_jbeam_active_beam_index)
        if not selection:
            return
        if 0 <= struct.index < len(bm.edges):
            struct.calc_info = bm.edges[struct.index].calc_length()
        self.update_instances(scene, obj, struct, j.get_total_beam_instances)
        bpy.ops.object.devtools_beamng_load_jbeam_beam_props()
        UiUtils.force_update_ui(bpy.context)
        obj.data.update()

    def update_triangle_data(self, scene, obj, bm):
        bm.faces.ensure_lookup_table()
        selection = [f.index for f in bm.faces if f.select]

        if self.face_selection == selection:
            return

        self.face_selection = selection
        if a.is_addon_visualizer_enabled():
            mod = j.get_gn_jbeam_modifier(obj)
            if mod:
                o.update_face_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_faces", "selected_faces", selection)
        active_face = bm.faces.active if bm.faces.active and bm.faces.active.index in selection else None

        if not active_face and selection:
            idx = selection[0]
            active_face = bm.faces.active = bm.faces[idx]
            bmesh.update_edit_mesh(obj.data)

        name = {3: "Triangle", 4: "Quad"}.get(len(active_face.verts), "Ngon") if active_face else "Triangle"
        struct = self.update_struct(scene, obj, bm, name, selection, bmesh.types.BMFace, j.get_triangle_id, j.set_gn_jbeam_active_triangle_index, active_face.index if active_face else -1)
        if not selection:
            return
        if 0 <= struct.index < len(bm.faces):
            struct.calc_info = bm.faces[struct.index].calc_area()
        self.update_instances(scene, obj, struct, j.get_total_triangle_instances)
        bpy.ops.object.devtools_beamng_load_jbeam_triangle_props()
        UiUtils.force_update_ui(bpy.context)
        obj.data.update()
