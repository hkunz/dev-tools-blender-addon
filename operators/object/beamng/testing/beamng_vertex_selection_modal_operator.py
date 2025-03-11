import bpy
import bmesh

# gn.blend test script for testing selection of nodes, beams, triangles
# Copy paste script into resources/blend/gn.blend and run script before testing object in Edit Mode

class OBJECT_OT_VertexSelectionModalOperator(bpy.types.Operator):
    bl_idname = "wm.vertex_selection_modal_operator"
    bl_label = "Vertex Monitor"
    bl_description = "Monitor selected node vertices"
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

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}
        obj = context.object
        if obj is None or obj.type != 'MESH' or obj.mode != 'EDIT':
            return {'PASS_THROUGH'}

        if bpy.context.tool_settings.mesh_select_mode[0]:
            self.update_vertex_data(context)
        elif bpy.context.tool_settings.mesh_select_mode[1]:
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

    def set_selection_mode(self, m, mode):
        m["Socket_9"] = mode

    def update_vertex_data(self, context):
        obj = context.object
        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()

        previous_vertex_selection = getattr(self, "previous_vertex_selection", None)
        current_selection = {v.index for v in bm.verts if v.select}

        if previous_vertex_selection == current_selection:
            return
        
        self.update_vertex_data_attr(obj, bm, current_selection)

    def update_vertex_data_attr(self, obj, bm, current_selection):
        mesh = obj.data
        self.previous_vertex_selection = current_selection
        attr_name = "selected_vertices"
        named_attr = "attribute_selected_vertices"
        mod = obj.modifiers[0]
        self.set_selection_mode(mod, 1)

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
        mod = obj.modifiers[0]
        self.set_selection_mode(mod, 2)
 
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


def register():
    bpy.utils.register_class(OBJECT_OT_VertexSelectionModalOperator)

def unregister():
    bpy.utils.unregister_class(OBJECT_OT_VertexSelectionModalOperator)

if __name__ == "__main__":
    register()
    bpy.ops.wm.vertex_selection_modal_operator('INVOKE_DEFAULT')