import bpy
import bmesh

# Copy paste into gn.blend file to test selection. Still has a FIXME bug where attributes get corrupted when testing this in gn.blend but this logic in jbeam_selection_tracker.py mysteriously works in the addon 

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
        bpy.app.handlers.depsgraph_update_post.clear()
        bpy.app.handlers.depsgraph_update_post.append(self.selection_update_handler)

    def selection_update_handler(self, scene, depsgraph):

        obj = bpy.context.object
        if obj.mode != 'EDIT':
            return

        self.check_selection_change(scene)

    def get_modifier(self, obj):
        return obj.modifiers[0]

    def set_selection_mode(self, obj):
        mode = next(i + 1 for i, v in enumerate(bpy.context.tool_settings.mesh_select_mode) if v) # 1 (vertex), 2 (edge), or 3 (edge)
        mod = self.get_modifier(obj)
        mod["Socket_9"] = mode
        return mode

    def check_selection_change(self, scene):
        obj = bpy.context.object
        mode = self.set_selection_mode(obj)

        if self.previous_selection_mode != mode:
            self.previous_selection_mode = mode
            self.previous_vertex_selection = None
            self.previous_edge_selection = None
            remove_selected_attributes(obj)
            self.check_selection_change(scene) #FIXME: should not do this but setup corrupts attributes when switching modes

        if bpy.context.tool_settings.mesh_select_mode[0]:
            self.update_vertex_data(scene, obj)
        elif bpy.context.tool_settings.mesh_select_mode[1]:
            self.update_edge_data(scene, obj)

    def update_vertex_data(self, scene, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        current_selection = {v.index for v in bm.verts if v.select}

        if self.previous_vertex_selection == current_selection:
            return

        self.previous_vertex_selection = current_selection
        mod = self.get_modifier(obj)
        self.update_vertex_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_vertices", "selected_vertices", current_selection)

    def update_edge_data(self, scene, obj):
        bm = bmesh.from_edit_mesh(obj.data)
        bm.edges.ensure_lookup_table()
        current_selection = {e.index for e in bm.edges if e.select}

        if self.previous_edge_selection == current_selection:
           return

        self.previous_edge_selection = current_selection
        mod = self.get_modifier(obj)
        self.update_edge_bool_attribute_for_gn(mod, obj, bm, "attribute_selected_edges", "selected_edges", current_selection)

    def update_bool_attribute_for_gn(self, mod, obj, bm, named_attr_node_name, attr_name, values, domain):
        mesh = obj.data
        node = mod.node_group.nodes.get(named_attr_node_name)

        newv = bpy.app.version >= (4, 4, 0)
        node.data_type = attr_type = 'BOOLEAN' if newv else 'INT'
        attribute = mesh.attributes.get(attr_name) or mesh.attributes.new(name=attr_name, type=attr_type, domain=domain)

        layers = bm.verts.layers if domain == "POINT" else bm.edges.layers
        layer = layers.bool.get(attribute.name) if newv else layers.int.get(attribute.name)
        selected_value, unselected_value = (True, False) if newv else (1, 0)

        elements = bm.verts if domain == "POINT" else bm.edges
        for elem in elements:
            elem[layer] = selected_value if elem.index in values else unselected_value

    def update_vertex_bool_attribute_for_gn(self, mod, obj, bm, named_attr_node_name, attr_name, values):
        self.update_bool_attribute_for_gn(mod, obj, bm, named_attr_node_name, attr_name, values, "POINT")

    def update_edge_bool_attribute_for_gn(self, mod, obj, bm, named_attr_node_name, attr_name, values):
        self.update_bool_attribute_for_gn(mod, obj, bm, named_attr_node_name, attr_name, values, "EDGE")


def remove_selected_attributes(obj):

    bpy.ops.object.mode_set(mode='OBJECT')

    mesh = obj.data
    if "selected_edges" in mesh.attributes:
        mesh.attributes.remove(mesh.attributes["selected_edges"])
    if "selected_vertices" in mesh.attributes:
        mesh.attributes.remove(mesh.attributes["selected_vertices"])

    bpy.ops.object.mode_set(mode='EDIT')

JbeamSelectionTracker.get_instance().register()