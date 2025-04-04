import bpy
import bmesh
import re
from dev_tools.utils.object_utils import ObjectUtils as o  # type: ignore
from dev_tools.utils.jbeam.jbeam_utils import JbeamUtils as j  # type: ignore

class OBJECT_OT_BeamngJbeamSelectSpecificElement(bpy.types.Operator):
    bl_idname = "object.devtools_beamng_jbeam_select_element_by_id_or_index"
    bl_label = "DevTools: Select Specific Element"
    bl_options = {'INTERNAL', 'UNDO'}
    bl_description = "Search for an element by its ID, or by its index if the ID field is empty or the Shift key is held down."

    element_id: bpy.props.StringProperty(name="Element Index", default="")  # type: ignore
    element_index: bpy.props.IntProperty(name="Element Index", default=-1)  # type: ignore
    is_shift_held: bpy.props.BoolProperty(default=False)  # type: ignore

    def invoke(self, context, event):
        # Check if Shift key is held down during the invocation of the operator
        self.is_shift_held = event.shift
        return self.execute(context)

    def execute(self, context):
        obj = context.object
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.mode_set(mode='EDIT')
        bm = bmesh.from_edit_mesh(obj.data)
        search_by_index = not self.element_id or self.is_shift_held

        def get_element_indices(getter_func, element_type, nodes_str):
            """Helper function to get element indices or handle index-based search."""
            if search_by_index:
                return [self.element_index]
            indices = getter_func()
            if not indices:
                self.report({'WARNING'}, f"{element_type} '{nodes_str}' not found")
            return indices

        def parse_node_ids(node_string):
            """Parse and format node IDs."""
            node_string = node_string.strip().strip('[]').replace('"', '')
            return [node.strip() for node in re.split(r'[;|,]+', node_string)]

        # Deselect all elements
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False

        elements = []
        element_type = None
        nodes_str = None
        indices = []

        if o.is_vertex_selection_mode():
            bm.verts.ensure_lookup_table()
            element_type = "Node"
            nodes_str = j.get_node_id(obj, self.element_index) if search_by_index else self.element_id
            indices = get_element_indices(lambda: j.get_node_indices(obj, self.element_id), element_type, nodes_str)
            elements = [bm.verts[i] for i in indices if 0 <= i < len(bm.verts)]

        elif o.is_edge_selection_mode():
            bm.edges.ensure_lookup_table()
            element_type = "Beam"
            node_ids = parse_node_ids(self.element_id)
            if len(node_ids) != 2:
                self.report({'WARNING'}, f"{element_type} '{self.element_id}' not found")
                return {'CANCELLED'}
            nodes_str = j.get_beam_id(obj, self.element_index) if search_by_index and 0 <= self.element_index < len(bm.edges) else j.format_node_ids(*node_ids)
            indices = get_element_indices(lambda: j.get_beam_indices(obj, *node_ids, bm), element_type, nodes_str)
            elements = [bm.edges[i] for i in indices if 0 <= i < len(bm.edges)]

        elif o.is_face_selection_mode():
            bm.faces.ensure_lookup_table()
            element_type = "Face"
            node_ids = parse_node_ids(self.element_id)
            if len(node_ids) < 3:
                self.report({'WARNING'}, f"{element_type} '{self.element_id}' not found")
                return {'CANCELLED'}
            nodes_str = j.get_triangle_id(obj, self.element_index) if search_by_index and 0 <= self.element_index < len(bm.faces) else j.format_node_ids(*node_ids)
            indices = get_element_indices(lambda: j.get_face_indices(obj, *node_ids, bm=bm), element_type, nodes_str)
            elements = [bm.faces[i] for i in indices if 0 <= i < len(bm.faces)]

        if elements:
            for element in elements:
                element.select = True
                bm.select_history.add(element)
            self.report({'INFO'}, f"Selected {len(elements)} {element_type} elements")
            bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'}
